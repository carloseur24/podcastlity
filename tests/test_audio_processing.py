"""Tests for audio processing config."""

import json
from pathlib import Path
import pytest

from scripts.config import ConfigProvider


class TestAudioProcessingConfig:
    """Test audio processing configuration methods."""

    def test_get_audio_processing_config(self, workspace_root):
        """Test loading global audio processing defaults."""
        config = ConfigProvider(str(workspace_root))
        audio_config = config.get_audio_processing_config()

        assert "highpass" in audio_config
        assert "eq_boxiness" in audio_config
        assert "compressor" in audio_config
        assert "highshelf" in audio_config
        assert "limiter" in audio_config
        assert "loudnorm" in audio_config

    def test_audio_processing_defaults_enabled(self, workspace_root):
        """Test that all filters are enabled by default."""
        config = ConfigProvider(str(workspace_root))
        audio_config = config.get_audio_processing_config()

        for filter_key in [
            "highpass",
            "eq_boxiness",
            "compressor",
            "highshelf",
            "limiter",
            "loudnorm",
        ]:
            assert audio_config[filter_key].get("enabled") is True, (
                f"{filter_key} should be enabled by default"
            )

    def test_audio_processing_highpass_params(self, workspace_root):
        """Test highpass filter parameters."""
        config = ConfigProvider(str(workspace_root))
        audio_config = config.get_audio_processing_config()

        hp = audio_config["highpass"]
        assert hp["frequency"] == 80
        assert hp["poles"] == 2

    def test_audio_processing_compressor_params(self, workspace_root):
        """Test compressor filter parameters."""
        config = ConfigProvider(str(workspace_root))
        audio_config = config.get_audio_processing_config()

        comp = audio_config["compressor"]
        assert comp["threshold"] == -24
        assert comp["ratio"] == 3.5
        assert comp["attack"] == 5
        assert comp["release"] == 100

    def test_audio_processing_loudnorm_params(self, workspace_root):
        """Test loudnorm filter parameters."""
        config = ConfigProvider(str(workspace_root))
        audio_config = config.get_audio_processing_config()

        ln = audio_config["loudnorm"]
        assert ln["I"] == -16
        assert ln["TP"] == -1.5
        assert ln["LRA"] == 11


class TestSessionAudioConfig:
    """Test session-specific audio configuration."""

    def test_get_session_audio_config_no_override(self, workspace_root, sample_session_id):
        """Test session audio config falls back to global when no override exists."""
        config = ConfigProvider(str(workspace_root))
        session_config = config.get_session_audio_config(str(workspace_root), sample_session_id)

        # Should return global defaults when no session override
        assert session_config["highpass"]["enabled"] is True
        assert session_config["loudnorm"]["I"] == -16

    def test_save_and_get_session_audio_config(self, workspace_root, sample_session_id):
        """Test saving and retrieving session-specific audio config."""
        config = ConfigProvider(str(workspace_root))

        # Create custom config
        custom_config = {
            "highpass": {"enabled": False, "frequency": 60},
            "eq_boxiness": {"enabled": True, "gain": -6},
            "compressor": {"enabled": False},
            "highshelf": {"enabled": True},
            "limiter": {"enabled": True},
            "loudnorm": {"enabled": True, "I": -14},
        }

        # Save session config
        config.save_session_audio_config(str(workspace_root), sample_session_id, custom_config)

        # Retrieve and verify
        retrieved = config.get_session_audio_config(str(workspace_root), sample_session_id)

        assert retrieved["highpass"]["enabled"] is False
        assert retrieved["highpass"]["frequency"] == 60
        assert retrieved["eq_boxiness"]["gain"] == -6
        assert retrieved["compressor"]["enabled"] is False
        assert retrieved["loudnorm"]["I"] == -14

    def test_toggle_audio_filter(self, workspace_root, sample_session_id):
        """Test toggling a single audio filter."""
        config = ConfigProvider(str(workspace_root))

        # Start with defaults
        original = config.get_session_audio_config(str(workspace_root), sample_session_id)
        original_highpass = original["highpass"]["enabled"]

        # Toggle highpass
        config.toggle_audio_filter(str(workspace_root), sample_session_id, "highpass")

        # Verify toggled
        toggled = config.get_session_audio_config(str(workspace_root), sample_session_id)
        assert toggled["highpass"]["enabled"] is not original_highpass

    def test_update_audio_filter_params(self, workspace_root, sample_session_id):
        """Test updating filter parameters."""
        config = ConfigProvider(str(workspace_root))

        # Update loudnorm target
        config.update_audio_filter(
            str(workspace_root), sample_session_id, "loudnorm", {"I": -18, "TP": -2.0}
        )

        updated = config.get_session_audio_config(str(workspace_root), sample_session_id)
        assert updated["loudnorm"]["I"] == -18
        assert updated["loudnorm"]["TP"] == -2.0


class TestAudioFilterChainBuilding:
    """Test building audio filter chains from config."""

    def test_build_filter_chain_all_enabled(self, workspace_root):
        """Test filter chain when all filters are enabled."""
        config = ConfigProvider(str(workspace_root))
        audio_config = config.get_audio_processing_config()

        # Build filter chain
        filters = []
        if audio_config.get("highpass", {}).get("enabled"):
            hp = audio_config["highpass"]
            filters.append(f"highpass=frequency={hp['frequency']}:poles={hp['poles']}")

        if audio_config.get("eq_boxiness", {}).get("enabled"):
            eq = audio_config["eq_boxiness"]
            filters.append(
                f"equalizer=frequency={eq['frequency']}:width_type=hertz:width={eq.get('width', 300)}:gain={eq['gain']}"
            )

        if audio_config.get("compressor", {}).get("enabled"):
            comp = audio_config["compressor"]
            filters.append(
                f"acompressor=threshold={comp['threshold']}:ratio={comp['ratio']}:attack={comp['attack']}:release={comp['release']}"
            )

        if audio_config.get("highshelf", {}).get("enabled"):
            hs = audio_config["highshelf"]
            filters.append(f"highshelf=frequency={hs['frequency']}:gain={hs['gain']}")

        if audio_config.get("limiter", {}).get("enabled"):
            lim = audio_config["limiter"]
            filters.append(f"alimiter=limit={lim['ceiling']}")

        if audio_config.get("loudnorm", {}).get("enabled"):
            ln = audio_config["loudnorm"]
            filters.append(f"loudnorm=I={ln['I']}:TP={ln['TP']}:LRA={ln['LRA']}")

        filter_chain = ",".join(filters)

        assert "highpass" in filter_chain
        assert "equalizer" in filter_chain
        assert "acompressor" in filter_chain
        assert "highshelf" in filter_chain
        assert "alimiter" in filter_chain
        assert "loudnorm" in filter_chain

    def test_build_filter_chain_some_disabled(self, workspace_root):
        """Test filter chain when some filters are disabled."""
        config = ConfigProvider(str(workspace_root))

        # Disable highpass and compressor
        partial_config = {
            "highpass": {"enabled": False},
            "eq_boxiness": {"enabled": False},
            "compressor": {"enabled": True},
            "highshelf": {"enabled": True},
            "limiter": {"enabled": False},
            "loudnorm": {"enabled": True},
        }

        filters = []
        if partial_config.get("highpass", {}).get("enabled"):
            filters.append("highpass=frequency=80:poles=2")
        if partial_config.get("eq_boxiness", {}).get("enabled"):
            filters.append("equalizer=frequency=450:width_type=hertz:width=300:gain=-3")
        if partial_config.get("compressor", {}).get("enabled"):
            filters.append("acompressor=threshold=-24:ratio=3.5:attack=5:release=100")
        if partial_config.get("highshelf", {}).get("enabled"):
            filters.append("highshelf=frequency=10000:gain=3")
        if partial_config.get("limiter", {}).get("enabled"):
            filters.append("alimiter=limit=-1")
        if partial_config.get("loudnorm", {}).get("enabled"):
            filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

        filter_chain = ",".join(filters)

        assert "highpass" not in filter_chain
        assert "equalizer" not in filter_chain
        assert "acompressor" in filter_chain
        assert "highshelf" in filter_chain
        assert "alimiter" not in filter_chain
        assert "loudnorm" in filter_chain
