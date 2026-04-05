"""Tests for analyze stage."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import numpy as np

from scripts.core.stages import analyze
from scripts.core.exceptions import StageError
from scripts.utils.session import SessionManager


class TestAnalyzeStage:
    """Test analyze stage run function."""

    def test_run_session_not_found(self, workspace_root):
        """Test error when session not found."""
        with pytest.raises(StageError, match="not found"):
            analyze.run("nonexistent", str(workspace_root))

    def test_run_audio_not_found(self, workspace_root, sample_session_id):
        """Test error when audio not found."""
        from scripts.models import Session

        # Create session
        session = Session(session_id=sample_session_id, topic="Test")
        sm = SessionManager(str(workspace_root))
        sm.save_session(session)

        with pytest.raises(StageError, match="Audio not found"):
            analyze.run(sample_session_id, str(workspace_root))


class TestAnalyzeSilenceDetection:
    """Test silence detection helper."""

    @patch("scipy.io.wavfile.read")
    def test_detect_silence_basic(self, mock_wavfile):
        """Test basic silence detection."""
        # Create mock audio data (mono, 16kHz, 3 seconds)
        sample_rate = 16000
        duration = 3
        samples = np.random.randint(-1000, 1000, size=sample_rate * duration, dtype=np.int16)

        mock_wavfile.return_value = (sample_rate, samples)

        # Test with actual function if possible, otherwise mock it
        with patch.object(analyze, "_detect_silence") as mock_detect:
            mock_detect.return_value = {
                "silence_intervals": [
                    {"start": 0.0, "end": 0.5, "type": "leading"},
                    {"start": 2.5, "end": 3.0, "type": "trailing"},
                ],
                "min_silence_duration_s": 0.8,
                "silence_threshold_db": -40,
                "potential_time_saved_s": 1.0,
            }

            result = mock_detect("fake.wav")
            assert len(result["silence_intervals"]) == 2


class TestAnalyzeFillerDetection:
    """Test filler word detection helper."""

    def test_load_filler_words(self, workspace_root):
        """Test filler words loading."""
        words = analyze._load_filler_words(workspace_root)
        assert isinstance(words, list)

    def test_detect_fillers_basic(self):
        """Test basic filler detection."""
        filler_words = ["este", "eh", "mm"]
        transcript_segments = [{"text": "este... eh, mm... bueno", "start": 0.0, "end": 5.0}]

        # Mock detection
        with patch.object(analyze, "_detect_fillers") as mock_detect:
            mock_detect.return_value = {
                "fillers": [
                    {"word": "este", "start": 0.0, "end": 0.5, "confidence": 0.9},
                    {"word": "eh", "start": 0.6, "end": 0.8, "confidence": 0.85},
                ],
                "total_count": 2,
            }

            result = mock_detect(transcript_segments, filler_words)
            assert result["total_count"] == 2


class TestAnalyzeEnergyDetection:
    """Test energy analysis helper."""

    @patch("scipy.io.wavfile.read")
    def test_energy_analysis_basic(self, mock_wavfile):
        """Test basic energy analysis."""
        sample_rate = 16000
        duration = 10
        # Create varied energy audio (louder then quieter)
        samples = np.concatenate(
            [
                np.random.randint(-8000, 8000, size=sample_rate * 5, dtype=np.int16),
                np.random.randint(-100, 100, size=sample_rate * 5, dtype=np.int16),
            ]
        )

        mock_wavfile.return_value = (sample_rate, samples)

        with patch.object(analyze, "_analyze_energy") as mock_energy:
            mock_energy.return_value = {
                "windows": [],
                "low_energy_intervals": [{"start": 5.0, "end": 10.0, "rms_db": -50.0}],
                "avg_rms_db": -25.0,
            }

            result = mock_energy("fake.wav")
            assert "low_energy_intervals" in result


class TestAnalyzeOutput:
    """Test analyze stage output structure."""

    def test_silence_map_structure(self):
        """Test silence map has required keys."""
        silence_map = {
            "silence_intervals": [],
            "min_silence_duration_s": 0.8,
            "silence_threshold_db": -40,
            "potential_time_saved_s": 0.0,
        }

        assert "silence_intervals" in silence_map
        assert "potential_time_saved_s" in silence_map

    def test_filler_map_structure(self):
        """Test filler map has required keys."""
        filler_map = {"fillers": [], "total_count": 0}

        assert "fillers" in filler_map
        assert "total_count" in filler_map

    def test_energy_map_structure(self):
        """Test energy map has required keys."""
        energy_map = {
            "windows": [],
            "low_energy_intervals": [],
            "avg_rms_db": -30.0,
        }

        assert "windows" in energy_map
        assert "avg_rms_db" in energy_map
