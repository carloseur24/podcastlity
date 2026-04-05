"""
Pytest configuration and fixtures for content-os tests.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Generator

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def workspace_root(tmp_path) -> Path:
    """
    Create a temporary workspace with all required directories.
    This is the base fixture for most tests.
    """
    root = tmp_path / "test_workspace"

    # Create all required directories (new structure: data/ and output/)
    dirs = [
        "data/recordings",
        "data/footage",
        "output/proxies",
        "output/audio",
        "output/transcripts",
        "output/analysis",
        "output/cutmaps",
        "output/exports",
        "output/thumbnails/frame_grabs",
        "output/briefs",
        "output/metadata",
    ]

    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # Create default config files
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # settings.json
    (config_dir / "settings.json").write_text(
        json.dumps(
            {
                "anthropic_api_key": "",
                "replicate_api_key": "",
                "recordings_mount": str(root / "data" / "recordings"),
                "workspace_root": str(root),
                "ffmpeg_path": "imageio",
                "ffmpeg_threads": 0,
                "whisper_model": "large-v2",
                "whisper_compute_type": "int8",
                "whisper_device": "cpu",
                "whisper_language": "es",
                "default_profile": "default",
                "proxy_resolution": "1280x720",
                "logs_level": "INFO",
            }
        )
    )

    # profiles.json (single default profile)
    (config_dir / "profiles.json").write_text(
        json.dumps(
            {
                "default": {
                    "silence_threshold_db": -40,
                    "silence_min_duration_s": 0.8,
                    "collapse_to_s": 0.25,
                    "trim_pad_before_s": 0.1,
                    "trim_pad_after_s": 0.12,
                    "enable_cutting": False,
                    "remove_fillers": False,
                    "filler_confidence_threshold": 0.9,
                    "low_energy_min_duration_s": 5.0,
                    "target_duration_s": None,
                    "max_duration_s": None,
                    "caption_words_per_line": 7,
                    "caption_style": "default",
                    "pip_position": "bottom_right",
                    "pip_size_ratio": 0.167,
                    "aspect_ratio": "16:9",
                    "resolution": "1920x1080",
                }
            }
        )
    )

    # brand.json
    (config_dir / "brand.json").write_text(
        json.dumps(
            {
                "channel_name": "TestChannel",
                "tagline": "Test Tagline",
                "primary_color": "#FFDD00",
                "bg_color": "#0A0A0A",
                "accent_color": "#FF4444",
                "font_primary": "Montserrat",
            }
        )
    )

    # filters.json
    (config_dir / "filters.json").write_text(
        json.dumps(
            {
                "highpass": {"default_freq": 80, "deep_voice_freq": 60},
                "afftdn": {"nr_mild": 10, "nr_moderate": 18, "nr_heavy": 25},
                "loudnorm": {"default": {"I": -16, "TP": -1.5, "LRA": 11}},
            }
        )
    )

    # filler_words_es.txt
    (config_dir / "filler_words_es.txt").write_text("""este
eh
mm
bueno
entonces
pues
""")

    # Create templates directory
    templates_dir = root / "templates" / "subtitles"
    templates_dir.mkdir(parents=True, exist_ok=True)

    (templates_dir / "default.ass").write_text("""[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Style: Default,Montserrat,68,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,1,3,0,2,80,80,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")

    (templates_dir / "kinetic.ass").write_text("""[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Style: Base,Montserrat,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,1,2,1,2,80,80,200,1
Style: Highlight,Montserrat,72,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,1,2,1,2,80,80,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")

    return root


@pytest.fixture
def sample_session_id() -> str:
    """Return a consistent test session ID."""
    return "20250628_test_session"


@pytest.fixture
def sample_video_path(workspace_root: Path) -> Path:
    """
    Return path to sample video for testing.
    Uses the fulldeco.mp4 if available, otherwise returns None.
    """
    footage_path = PROJECT_ROOT / "footage" / "fulldeco.mp4"
    if footage_path.exists():
        return footage_path
    return None


@pytest.fixture
def mock_session(workspace_root: Path, sample_session_id: str) -> dict:
    """Create a mock session dict for testing."""
    return {
        "session_id": sample_session_id,
        "topic": "Test Topic",
        "platform_targets": ["youtube_lf"],
        "profile": "default",
        "cta": "Suscribete",
        "rough_duration_min": 10,
        "video_file": "",
    }


@pytest.fixture
def session_dir(workspace_root: Path, sample_session_id: str) -> Path:
    """Create a session directory and return its path."""
    session_dir = workspace_root / "data" / "recordings" / sample_session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir
