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
    
    # Create all required directories
    dirs = [
        "recordings",
        "proxies", 
        "audio",
        "transcripts",
        "analysis",
        "cutmaps",
        "exports",
        "thumbnails/frame_grabs",
        "briefs",
        "metadata",
    ]
    
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    
    # Create default config files
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # settings.json
    (config_dir / "settings.json").write_text(json.dumps({
        "anthropic_api_key": "",
        "replicate_api_key": "",
        "recordings_mount": str(root / "recordings"),
        "workspace_root": str(root),
        "ffmpeg_path": "imageio",
        "ffmpeg_threads": 0,
        "whisper_model": "large-v2",
        "whisper_compute_type": "int8",
        "whisper_device": "cpu",
        "whisper_language": "es",
        "default_profile": "longform",
        "proxy_resolution": "1280x720",
        "logs_level": "INFO"
    }))
    
    # profiles.json
    (config_dir / "profiles.json").write_text(json.dumps({
        "shorts": {
            "silence_threshold_db": -40,
            "silence_min_duration_s": 0.3,
            "collapse_to_s": 0.12,
            "remove_fillers": True,
            "target_duration_s": 90,
            "max_duration_s": 60,
            "aspect_ratio": "9:16",
            "resolution": "1080x1920"
        },
        "longform": {
            "silence_threshold_db": -42,
            "silence_min_duration_s": 0.5,
            "collapse_to_s": 0.25,
            "remove_fillers": False,
            "aspect_ratio": "16:9",
            "resolution": "1920x1080"
        }
    }))
    
    # brand.json
    (config_dir / "brand.json").write_text(json.dumps({
        "channel_name": "TestChannel",
        "tagline": "Test Tagline",
        "primary_color": "#FFDD00",
        "bg_color": "#0A0A0A",
        "accent_color": "#FF4444",
        "font_primary": "Montserrat"
    }))
    
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
        "platform_targets": ["youtube_lf", "shorts"],
        "profile": "longform",
        "goal": "educativo",
        "tone": "directo",
        "cta": "Suscribete",
        "rough_duration_min": 10,
        "camera_file": "",
        "screen_file": "",
        "sync_offset_seconds": 0.0,
        "sync_method": "manual",
        "status": "created"
    }


@pytest.fixture
def session_dir(workspace_root: Path, sample_session_id: str) -> Path:
    """Create a session directory and return its path."""
    session_dir = workspace_root / "recordings" / sample_session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir
