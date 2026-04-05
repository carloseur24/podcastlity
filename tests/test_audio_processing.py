"""
Audio processing tests - verify filter chains produce correct output.

These tests run actual FFmpeg commands to verify audio quality,
not just that the code calls FFmpeg correctly.
"""

import subprocess
import json
from pathlib import Path

import pytest
import imageio_ffmpeg

from scripts.config import ConfigProvider
from scripts.domain.audio_engineer import AudioEngineer


def get_ffmpeg_path() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def measure_lufs(audio_path: str) -> float:
    """Measure integrated loudness (LUFS) using ebur128."""
    ffmpeg = get_ffmpeg_path()
    result = subprocess.run(
        [ffmpeg, "-i", audio_path, "-af", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    lines = [l for l in result.stderr.splitlines() if "I:" in l]
    if not lines:
        raise ValueError(f"Could not measure LUFS for {audio_path}")
    return float(lines[-1].split()[1])


def run_filter_chain(
    input_path: str,
    filter_chain: str,
    output_path: str,
    sample_rate: int = 48000,
    channels: int = 1,
):
    """Run FFmpeg with a filter chain."""
    ffmpeg = get_ffmpeg_path()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            input_path,
            "-af",
            filter_chain,
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            output_path,
        ],
        check=True,
        capture_output=True,
    )


class TestLoudnormProcessing:
    """Test loudnorm produces correct LUFS output."""

    @pytest.fixture
    def master_audio_path(self) -> Path:
        """Path to test audio file."""
        return Path("audio/study/master.wav")

    def test_longform_loudnorm_target(self, master_audio_path, tmp_path):
        """
        Test that loudnorm with longform settings produces ~-16 LUFS output.

        This is the key test that caught the bug where LRA=9 was too low
        for voice with natural LRA=20, causing loudnorm to produce -24 LUFS.
        """
        if not master_audio_path.exists():
            pytest.skip(f"Test audio not found: {master_audio_path}")

        output_path = tmp_path / "longform_normalized.wav"

        # Get config settings
        config = ConfigProvider(".")
        loudnorm_targets = config.get_loudnorm_targets("longform")

        filter_chain = f"loudnorm=I={loudnorm_targets.get('I', -16)}:TP={loudnorm_targets.get('TP', -1.5)}:LRA={loudnorm_targets.get('LRA', 14)}"

        run_filter_chain(str(master_audio_path), filter_chain, str(output_path))

        # Measure actual output loudness
        lufs = measure_lufs(str(output_path))

        # Assert within acceptable range
        target_i = loudnorm_targets.get("I", -16)
        tolerance = 2.0  # Allow ±2 LUFS tolerance

        assert lufs >= target_i - tolerance, (
            f"Output LUFS {lufs} is too low. "
            f"Expected ~{target_i}, got {lufs}. "
            f"Check loudnorm LRA setting - may be too low for voice dynamic range."
        )
        assert lufs <= target_i + tolerance, (
            f"Output LUFS {lufs} is too high. Expected ~{target_i}, got {lufs}."
        )

    def test_shorts_loudnorm_target(self, master_audio_path, tmp_path):
        """Test that shorts loudnorm targets -14 LUFS."""
        if not master_audio_path.exists():
            pytest.skip(f"Test audio not found: {master_audio_path}")

        output_path = tmp_path / "shorts_normalized.wav"

        config = ConfigProvider(".")
        loudnorm_targets = config.get_loudnorm_targets("shorts")

        filter_chain = f"loudnorm=I={loudnorm_targets.get('I', -14)}:TP={loudnorm_targets.get('TP', -1)}:LRA={loudnorm_targets.get('LRA', 6)}"

        run_filter_chain(str(master_audio_path), filter_chain, str(output_path))

        lufs = measure_lufs(str(output_path))

        target_i = loudnorm_targets.get("I", -14)
        tolerance = 2.0

        assert target_i - tolerance <= lufs <= target_i + tolerance, (
            f"Output LUFS {lufs} not within {tolerance} of target {target_i}"
        )


class TestAudioEngineerFilterChain:
    """Test AudioEngineer produces correct output."""

    @pytest.fixture
    def audio_engineer(self):
        config = ConfigProvider(".")
        return AudioEngineer(config)

    @pytest.fixture
    def master_audio_path(self) -> Path:
        return Path("audio/study/master.wav")

    def test_preprocess_longform_output_lufs(self, audio_engineer, master_audio_path, tmp_path):
        """Test AudioEngineer.preprocess produces correct LUFS for longform."""
        if not master_audio_path.exists():
            pytest.skip(f"Test audio not found: {master_audio_path}")

        output_path = tmp_path / "preprocessed.wav"

        result = audio_engineer.preprocess(master_audio_path, output_path, "longform")

        # Check for errors
        assert not result.get("errors"), f"Preprocessing errors: {result.get('errors')}"

        # Verify output loudness
        lufs = measure_lufs(str(output_path))

        config = ConfigProvider(".")
        targets = config.get_loudnorm_targets("longform")
        target_i = targets.get("I", -16)
        tolerance = 2.5  # Slightly larger tolerance for full chain

        assert lufs >= target_i - tolerance, (
            f"Output LUFS {lufs} too low. Expected ~{target_i}. "
            f"Filter chain: {result.get('filter_chain')}"
        )

    def test_preprocess_preserves_sample_rate(self, audio_engineer, master_audio_path, tmp_path):
        """Test that preprocess outputs at 48kHz (not 16kHz)."""
        if not master_audio_path.exists():
            pytest.skip(f"Test audio not found: {master_audio_path}")

        output_path = tmp_path / "preprocessed_48k.wav"

        audio_engineer.preprocess(master_audio_path, output_path, "longform")

        # Verify sample rate is 48kHz
        ffmpeg = get_ffmpeg_path()
        result = subprocess.run(
            [ffmpeg, "-i", str(output_path), "-hide_banner"],
            capture_output=True,
            text=True,
        )

        assert "48000 Hz" in result.stderr, (
            f"Expected 48000 Hz output, got different sample rate. "
            f"Output will cause loudnorm measurement issues if different from input."
        )


class TestStereoProcessing:
    """Test stereo widening for export."""

    @pytest.fixture
    def mono_audio_path(self) -> Path:
        return Path("audio/study/master.wav")

    def test_extrastereo_produces_stereo(self, mono_audio_path, tmp_path):
        """Test that extrastereo filter converts mono to stereo."""
        if not mono_audio_path.exists():
            pytest.skip(f"Test audio not found: {mono_audio_path}")

        output_path = tmp_path / "stereo.wav"

        run_filter_chain(str(mono_audio_path), "extrastereo=m=1.5", str(output_path), channels=2)

        # Verify stereo output
        ffmpeg = get_ffmpeg_path()
        result = subprocess.run([ffmpeg, "-i", str(output_path)], capture_output=True, text=True)

        # Should contain "stereo" not "mono"
        assert "stereo" in result.stderr.lower() or "2 channels" in result.stderr.lower(), (
            "extrastereo should produce stereo output"
        )


class TestConfigSettings:
    """Test that config provides correct filter settings."""

    def test_longform_loudnorm_settings(self):
        """Verify longform loudnorm config matches requirements."""
        config = ConfigProvider(".")
        targets = config.get_loudnorm_targets("longform")

        # These are the requirements for voice with high dynamic range
        assert targets.get("I") == -16, (
            f"Longform I should be -16, got {targets.get('I')}. "
            "-14 is too high for recordings already at -13.47 LUFS."
        )
        assert targets.get("TP") == -1.5, f"Longform TP should be -1.5, got {targets.get('TP')}"
        assert targets.get("LRA") == 11, (
            f"Longform LRA should be 11, got {targets.get('LRA')}. "
            "This matches the skill recommendation for long-form content."
        )

    def test_shorts_loudnorm_settings(self):
        """Verify shorts loudnorm config."""
        config = ConfigProvider(".")
        targets = config.get_loudnorm_targets("shorts")

        # Shorts typically use tighter loudness
        assert targets.get("I") == -14
        assert targets.get("TP") == -1
        assert targets.get("LRA") == 6
