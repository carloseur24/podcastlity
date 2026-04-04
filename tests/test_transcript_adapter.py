"""Tests for transcript adapter utilities."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from scripts.utils.transcript_adapter import (
    load_transcript,
    convert_to_remotion_captions,
    get_preset_for_profile,
    load_subtitle_preset,
)


class TestLoadTranscript:
    """Test transcript loading."""

    def test_load_transcript_success(self, workspace_root, sample_session_id):
        """Test successful transcript loading."""
        # Create transcript file
        transcript_dir = workspace_root / "output" / "transcripts" / sample_session_id
        transcript_dir.mkdir(parents=True, exist_ok=True)

        transcript_data = [
            {
                "id": 0,
                "start": 0.0,
                "end": 5.0,
                "text": "Hello world",
                "words": [{"word": "Hello", "start": 0.0, "end": 1.0, "probability": 0.9}],
            }
        ]
        (transcript_dir / "segments.json").write_text(json.dumps(transcript_data))

        result = load_transcript(str(workspace_root), sample_session_id)
        assert len(result) == 1
        assert result[0]["text"] == "Hello world"

    def test_load_transcript_not_found(self, workspace_root):
        """Test transcript not found error."""
        with pytest.raises(FileNotFoundError):
            load_transcript(str(workspace_root), "nonexistent")


class TestConvertToRemotionCaptions:
    """Test caption conversion."""

    def test_convert_basic(self):
        """Test basic conversion."""
        transcript = [
            {
                "id": 0,
                "start": 0.0,
                "end": 5.0,
                "text": "Hello world",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 1.0, "probability": 0.9},
                    {"word": "world", "start": 1.0, "end": 2.0, "probability": 0.95},
                ],
            }
        ]

        result = convert_to_remotion_captions(transcript)
        assert len(result) > 0
        assert "text" in result[0]
        assert "startMs" in result[0]

    def test_convert_empty_transcript(self):
        """Test empty transcript."""
        result = convert_to_remotion_captions([])
        assert result == []

    def test_convert_timestamps_in_milliseconds(self):
        """Test timestamps are in milliseconds."""
        transcript = [
            {
                "id": 0,
                "start": 1.5,
                "end": 3.0,
                "text": "Test",
                "words": [{"word": "Test", "start": 1.5, "end": 3.0, "probability": 0.9}],
            }
        ]

        result = convert_to_remotion_captions(transcript)
        assert result[0]["startMs"] == 1500
        assert result[0]["endMs"] == 3000


class TestGetPresetForProfile:
    """Test preset loading for profiles."""

    def test_get_preset_for_default_profile(self, workspace_root):
        """Test preset loading for default profile."""
        # Create preset files with correct structure
        config_dir = workspace_root / "config"
        (config_dir / "subtitle_presets.json").write_text(
            json.dumps(
                {
                    "presets": {
                        "minimal_fade": {
                            "name": "Minimal Fade",
                            "font_family": "Poppins",
                            "font_size": 60,
                        }
                    },
                    "profiles": {"default": "minimal_fade"},
                }
            )
        )

        preset_name, preset_config = get_preset_for_profile(str(workspace_root), "default")
        assert preset_name == "minimal_fade"
        assert "font_family" in preset_config


class TestLoadPreset:
    """Test preset loading."""

    def test_load_preset_success(self, workspace_root):
        """Test successful preset loading."""
        config_dir = workspace_root / "config"
        (config_dir / "subtitle_presets.json").write_text(
            json.dumps(
                {
                    "presets": {
                        "custom": {
                            "name": "Custom",
                            "font_size": 48,
                        }
                    }
                }
            )
        )

        preset = load_subtitle_preset(str(workspace_root), "custom")
        assert preset is not None
        assert preset["name"] == "Custom"

    def test_load_preset_not_found(self, workspace_root):
        """Test preset not found raises error."""
        config_dir = workspace_root / "config"
        (config_dir / "subtitle_presets.json").write_text(json.dumps({"presets": {}}))

        with pytest.raises(ValueError, match="not found"):
            load_subtitle_preset(str(workspace_root), "nonexistent")
