import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from scripts.utils import ffmpeg


class TestGetFFmpegPath:
    def test_get_ffmpeg_path_returns_string(self):
        path = ffmpeg.get_ffmpeg_path()
        assert isinstance(path, str)
        assert "ffmpeg" in path.lower()


class TestRunFFmpeg:
    @patch("scripts.utils.ffmpeg.subprocess.run")
    def test_run_ffmpeg_calls_subprocess(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        ffmpeg.run_ffmpeg(["-version"], capture_output=False)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args[0].lower()

    @patch("scripts.utils.ffmpeg.get_ffmpeg_path")
    @patch("scripts.utils.ffmpeg.subprocess.run")
    def test_run_ffmpeg_with_verbose(self, mock_run, mock_get_path):
        mock_get_path.return_value = "/usr/bin/ffmpeg"
        mock_result = MagicMock()
        mock_result.stdout = "test"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        ffmpeg.run_ffmpeg(["-version"], capture_output=True, verbose=True)

        mock_run.assert_called_once()


class TestGetDuration:
    @patch("scripts.utils.ffmpeg.subprocess.run")
    def test_get_duration_parses_correctly(self, mock_run):
        mock_result = MagicMock()
        mock_result.stderr = "Duration: 00:05:30.50, start: 0.000, bitrate: 5000 kb/s"
        mock_run.return_value = mock_result

        duration = ffmpeg.get_duration("/fake/video.mp4")

        assert duration == 330.5

    @patch("scripts.utils.ffmpeg.subprocess.run")
    def test_get_duration_returns_zero_on_error(self, mock_run):
        mock_result = MagicMock()
        mock_result.stderr = "Invalid input"
        mock_run.return_value = mock_result

        duration = ffmpeg.get_duration("/fake/video.mp4")

        assert duration == 0.0

    @patch("scripts.utils.ffmpeg.subprocess.run")
    def test_get_duration_hours(self, mock_run):
        mock_result = MagicMock()
        mock_result.stderr = "Duration: 01:30:00.00"
        mock_run.return_value = mock_result

        duration = ffmpeg.get_duration("/fake/video.mp4")

        assert duration == 5400.0


class TestExtractAudio:
    @patch("scripts.utils.ffmpeg.run_ffmpeg")
    def test_extract_audio_mono_16k(self, mock_run):
        ffmpeg.extract_audio("/input.mp3", "/output.wav")

        call_args = mock_run.call_args[0][0]
        assert "-vn" in call_args
        assert "-ac" in call_args
        assert "1" in call_args
        assert "-ar" in call_args
        assert "48000" in call_args  # Default is now 48kHz for better quality

    @patch("scripts.utils.ffmpeg.run_ffmpeg")
    def test_extract_audio_stereo(self, mock_run):
        ffmpeg.extract_audio("/input.mp3", "/output.wav", mono=False, sample_rate=44100)

        call_args = mock_run.call_args[0][0]
        assert "-ar" in call_args
        assert "44100" in call_args


class TestCreateProxy:
    @patch("scripts.utils.ffmpeg.run_ffmpeg")
    def test_create_proxy_with_defaults(self, mock_run):
        ffmpeg.create_proxy("/input.mp4", "/output.mp4")

        call_args = mock_run.call_args[0][0]
        assert "-vf" in call_args
        assert "scale=1280:720" in call_args
        assert "-preset" in call_args
        assert "ultrafast" in call_args
        assert "-crf" in call_args
        assert "28" in call_args

    @patch("scripts.utils.ffmpeg.run_ffmpeg")
    def test_create_proxy_custom_resolution(self, mock_run):
        ffmpeg.create_proxy("/input.mp4", "/output.mp4", resolution="1920x1080")

        call_args = mock_run.call_args[0][0]
        assert "scale=1920:1080" in call_args


class TestTrimVideo:
    @patch("scripts.utils.ffmpeg.run_ffmpeg")
    def test_trim_video_copy_mode(self, mock_run):
        ffmpeg.trim_video("/input.mp4", "/output.mp4", 10.0, 30.0, copy=True)

        call_args = mock_run.call_args[0][0]
        assert "-ss" in call_args
        assert "10.0" in call_args
        assert "-to" in call_args
        assert "30.0" in call_args
        assert "-c" in call_args
        assert "copy" in call_args

    @patch("scripts.utils.ffmpeg.run_ffmpeg")
    def test_trim_video_reencode_mode(self, mock_run):
        ffmpeg.trim_video("/input.mp4", "/output.mp4", 10.0, 30.0, copy=False)

        call_args = mock_run.call_args[0][0]
        assert "-c:v" in call_args
        assert "libx264" in call_args


class TestConcatVideos:
    @patch("scripts.utils.ffmpeg.run_ffmpeg")
    @patch("scripts.utils.ffmpeg.Path")
    def test_concat_videos_creates_list_file(self, mock_path_cls, mock_run):
        mock_path = MagicMock()
        mock_path.parent = MagicMock()
        mock_path.parent.__truediv__ = MagicMock(return_value=mock_path)
        mock_path_cls.return_value = mock_path

        mock_path.parent.__truediv__.return_value = MagicMock()
        mock_list_file = MagicMock()
        mock_list_file.parent = MagicMock()

        ffmpeg.concat_videos(["/video1.mp4", "/video2.mp4"], "/output.mp4")

        mock_run.assert_called_once()


class TestBurnSubtitles:
    @patch("scripts.utils.ffmpeg.run_ffmpeg")
    def test_burn_subtitles(self, mock_run):
        ffmpeg.burn_subtitles("/input.mp4", "/subs.ass", "/output.mp4")

        call_args = mock_run.call_args[0][0]
        assert "-vf" in call_args
        assert "ass=/subs.ass" in call_args
        assert "-crf" in call_args
        assert "22" in call_args


class TestGetResolution:
    @patch("scripts.utils.ffmpeg.subprocess.run")
    def test_get_resolution_parses_json(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = '{"streams": [{"width": 1920, "height": 1080}]}'
        mock_run.return_value = mock_result

        width, height = ffmpeg.get_resolution("/fake/video.mp4")

        assert width == 1920
        assert height == 1080

    @patch("scripts.utils.ffmpeg.subprocess.run")
    def test_get_resolution_returns_default_on_error(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = "invalid"
        mock_run.return_value = mock_result

        width, height = ffmpeg.get_resolution("/fake/video.mp4")

        assert width == 1920
        assert height == 1080


class TestExtractFrame:
    @patch("scripts.utils.ffmpeg.run_ffmpeg")
    def test_extract_frame(self, mock_run):
        ffmpeg.extract_frame("/input.mp4", "/frame.jpg", 5.0)

        call_args = mock_run.call_args[0][0]
        assert "-ss" in call_args
        assert "5.0" in call_args
        assert "-vframes" in call_args
        assert "1" in call_args


class TestApplyLoudnorm:
    @patch("scripts.utils.ffmpeg.run_ffmpeg")
    def test_apply_loudnorm(self, mock_run):
        ffmpeg.apply_loudnorm("/input.mp4", "/output.mp4", target_lufs=-16.0)

        call_args = mock_run.call_args[0][0]
        assert "-af" in call_args
        assert "loudnorm=I=-16.0:TP=-1:LRA=7" in call_args


class TestGetFrameCount:
    @patch("scripts.utils.ffmpeg.subprocess.run")
    def test_get_frame_count_parses_output(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = "1234"
        mock_run.return_value = mock_result

        count = ffmpeg.get_frame_count("/fake/video.mp4")

        assert count == 1234

    @patch("scripts.utils.ffmpeg.subprocess.run")
    def test_get_frame_count_returns_zero_on_error(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = "invalid"
        mock_run.return_value = mock_result

        count = ffmpeg.get_frame_count("/fake/video.mp4")

        assert count == 0
