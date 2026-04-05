"""Tests for proxies stage."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from scripts.core.stages import proxies
from scripts.core.exceptions import StageError
from scripts.models import Session
from scripts.utils.session import SessionManager


class TestProxiesStage:
    """Test proxies stage run function."""

    def test_run_session_not_found(self, workspace_root):
        """Test error when session not found."""
        with pytest.raises(StageError, match="not found"):
            proxies.run("nonexistent", str(workspace_root))

    def test_run_creates_directories(self, workspace_root, sample_session_id):
        """Test directories are created."""
        # Create session directory with input video
        session_dir = workspace_root / "data" / "recordings" / sample_session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Create mock input video
        input_video = session_dir / "input.mp4"
        input_video.write_text("mock video")

        session = Session(
            session_id=sample_session_id,
            topic="Test",
            video_file=str(input_video),
        )
        sm = SessionManager(str(workspace_root))
        sm.save_session(session)

        # Run with mocked ffmpeg
        with patch("scripts.core.stages.proxies.ffmpeg") as mock_ffmpeg:
            mock_ffmpeg.create_proxy.return_value = None
            mock_ffmpeg.extract_audio.return_value = None

            proxies.run(sample_session_id, str(workspace_root))

        # Verify directories were created
        assert (workspace_root / "output" / "proxies" / sample_session_id).exists()
        assert (workspace_root / "output" / "audio" / sample_session_id).exists()

    def test_run_updates_status(self, workspace_root, sample_session_id):
        """Test session status is updated."""
        session_dir = workspace_root / "data" / "recordings" / sample_session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        input_video = session_dir / "input.mp4"
        input_video.write_text("mock video")

        session = Session(
            session_id=sample_session_id,
            topic="Test",
            video_file=str(input_video),
        )
        sm = SessionManager(str(workspace_root))
        sm.save_session(session)

        with patch("scripts.core.stages.proxies.ffmpeg") as mock_ffmpeg:
            mock_ffmpeg.create_proxy.return_value = None
            mock_ffmpeg.extract_audio.return_value = None

            result = proxies.run(sample_session_id, str(workspace_root))

        assert result["session_status"] == "proxied"

    def test_run_returns_proxy_paths(self, workspace_root, sample_session_id):
        """Test proxy paths returned."""
        session_dir = workspace_root / "data" / "recordings" / sample_session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        input_video = session_dir / "input.mp4"
        input_video.write_text("mock video")

        session = Session(
            session_id=sample_session_id,
            topic="Test",
            video_file=str(input_video),
        )
        sm = SessionManager(str(workspace_root))
        sm.save_session(session)

        with patch("scripts.core.stages.proxies.ffmpeg") as mock_ffmpeg:
            mock_ffmpeg.create_proxy.return_value = None
            mock_ffmpeg.extract_audio.return_value = None

            result = proxies.run(sample_session_id, str(workspace_root))

        assert "proxy_path" in result
        assert "audio_path" in result


class TestProxiesFFmpegCalls:
    """Test FFmpeg calls in proxies stage."""

    @patch("scripts.core.stages.proxies.ffmpeg")
    def test_create_proxy_called(self, mock_ffmpeg, workspace_root, sample_session_id):
        """Test create_proxy is called."""
        mock_ffmpeg.create_proxy.return_value = None
        mock_ffmpeg.extract_audio.return_value = None

        session_dir = workspace_root / "data" / "recordings" / sample_session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        input_video = session_dir / "input.mp4"
        input_video.write_text("mock video")

        session = Session(
            session_id=sample_session_id,
            topic="Test",
            video_file=str(input_video),
        )
        sm = SessionManager(str(workspace_root))
        sm.save_session(session)

        proxies.run(sample_session_id, str(workspace_root))

        mock_ffmpeg.create_proxy.assert_called()

    @patch("scripts.core.stages.proxies.ffmpeg")
    def test_extract_audio_called(self, mock_ffmpeg, workspace_root, sample_session_id):
        """Test extract_audio is called."""
        mock_ffmpeg.create_proxy.return_value = None
        mock_ffmpeg.extract_audio.return_value = None

        session_dir = workspace_root / "data" / "recordings" / sample_session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        input_video = session_dir / "input.mp4"
        input_video.write_text("mock video")

        session = Session(
            session_id=sample_session_id,
            topic="Test",
            video_file=str(input_video),
        )
        sm = SessionManager(str(workspace_root))
        sm.save_session(session)

        proxies.run(sample_session_id, str(workspace_root))

        mock_ffmpeg.extract_audio.assert_called()

    @patch("scripts.core.stages.proxies.ffmpeg")
    def test_input_not_found_raises(self, mock_ffmpeg, workspace_root, sample_session_id):
        """Test error when input video not found."""
        session = Session(
            session_id=sample_session_id,
            topic="Test",
            video_file="",
        )
        sm = SessionManager(str(workspace_root))
        sm.save_session(session)

        with pytest.raises(StageError, match="Input video not found"):
            proxies.run(sample_session_id, str(workspace_root))


class TestProxiesOutput:
    """Test proxies output structure."""

    def test_output_keys(self):
        """Test output has required keys."""
        output = {
            "proxy_path": "/path/to/proxy.mp4",
            "audio_path": "/path/to/audio.wav",
            "session_status": "proxied",
        }

        assert "proxy_path" in output
        assert "audio_path" in output
        assert "session_status" in output

    def test_output_status_value(self):
        """Test status is correct."""
        output = {"session_status": "proxied"}
        assert output["session_status"] == "proxied"
