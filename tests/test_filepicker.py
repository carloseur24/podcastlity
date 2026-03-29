import os
from pathlib import Path
import pytest

from scripts.utils import filepicker


class TestScanDirectory:
    def test_scan_directory_returns_empty_for_nonexistent(self, tmp_path):
        videos = filepicker.scan_directory(str(tmp_path))
        assert videos == []

    def test_scan_directory_finds_videos(self, tmp_path):
        (tmp_path / "video1.mp4").write_text("fake")
        (tmp_path / "video2.mov").write_text("fake")
        (tmp_path / "image.jpg").write_text("fake")

        videos = filepicker.scan_directory(str(tmp_path))

        assert len(videos) == 2
        names = [v.name for v in videos]
        assert "video1.mp4" in names
        assert "video2.mov" in names
        assert "image.jpg" not in names

    def test_scan_directory_filters_by_extension(self, tmp_path):
        (tmp_path / "video.mp4").write_text("fake")
        (tmp_path / "video.avi").write_text("fake")

        videos = filepicker.scan_directory(str(tmp_path), extensions=[".mp4"])

        assert len(videos) == 1
        assert videos[0].name == "video.mp4"

    def test_scan_directory_calculates_size(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"x" * 1024 * 1024)

        videos = filepicker.scan_directory(str(tmp_path))

        assert len(videos) == 1
        assert videos[0].size_mb >= 0.9
        assert videos[0].size_mb <= 1.1


class TestFindVideosInMount:
    def test_find_videos_returns_empty_for_nonexistent(self):
        videos = filepicker.find_videos_in_mount("/nonexistent/path")
        assert videos == []

    def test_find_videos_in_existing_mount(self, tmp_path):
        (tmp_path / "test.mp4").write_text("fake")
        videos = filepicker.find_videos_in_mount(str(tmp_path))
        assert len(videos) == 1


class TestSelectVideo:
    def test_select_video_no_exclude(self):
        videos = [
            filepicker.VideoFile(path="/a.mp4", name="a.mp4", size_mb=1.0),
            filepicker.VideoFile(path="/b.mp4", name="b.mp4", size_mb=2.0),
        ]
        result = filepicker.select_video(videos)
        assert len(result) == 2

    def test_select_video_with_exclude(self):
        videos = [
            filepicker.VideoFile(path="/a.mp4", name="a.mp4", size_mb=1.0),
            filepicker.VideoFile(path="/b.mp4", name="b.mp4", size_mb=2.0),
        ]
        result = filepicker.select_video(videos, exclude="/a.mp4")
        assert len(result) == 1
        assert result[0].path == "/b.mp4"


class TestValidateVideo:
    def test_validate_video_exists_and_valid_ext(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_text("fake")
        assert filepicker.validate_video(str(video)) is True

    def test_validate_video_nonexistent(self):
        assert filepicker.validate_video("/nonexistent/video.mp4") is False

    def test_validate_video_invalid_ext(self, tmp_path):
        video = tmp_path / "test.txt"
        video.write_text("fake")
        assert filepicker.validate_video(str(video)) is False

    def test_validate_video_case_insensitive(self, tmp_path):
        video = tmp_path / "test.MP4"
        video.write_text("fake")
        assert filepicker.validate_video(str(video)) is True


class TestBrowseDirectory:
    def test_browse_directory_nonexistent_uses_home(self):
        entries, path = filepicker.browse_directory("/nonexistent/path")
        assert path == str(Path.home())

    def test_browse_directory_lists_dirs_and_videos(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        (tmp_path / "video.mp4").write_text("fake")
        (tmp_path / "readme.txt").write_text("fake")

        entries, path = filepicker.browse_directory(str(tmp_path))

        assert path == str(tmp_path)
        display_entries = [e[0] for e in entries]
        assert any("[DIR] subdir/" in e for e in display_entries)
        assert any("video.mp4" in e for e in display_entries)
        assert not any("readme.txt" in e for e in display_entries)

    def test_browse_directory_shows_video_size(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"x" * 1024 * 1024)

        entries, _ = filepicker.browse_directory(str(tmp_path))

        display_entries = [e[0] for e in entries]
        assert any("MB)" in e for e in display_entries)

    def test_browse_directory_filters_hidden(self, tmp_path):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / "visible.mp4").write_text("fake")

        entries, _ = filepicker.browse_directory(str(tmp_path), show_hidden=False)
        display = [e[0] for e in entries]
        assert not any(".hidden" in e for e in display)
        assert any("visible.mp4" in e for e in display)

    def test_browse_directory_shows_hidden_when_enabled(self, tmp_path):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / "visible.mp4").write_text("fake")

        entries, _ = filepicker.browse_directory(str(tmp_path), show_hidden=True)
        display = [e[0] for e in entries]
        assert any(".hidden" in e for e in display)


class TestNavigateToParent:
    def test_navigate_to_parent(self, tmp_path):
        parent = tmp_path / "parent"
        child = parent / "child"
        parent.mkdir()
        child.mkdir()

        result = filepicker.navigate_to_parent(str(child))
        assert result == str(parent)

    def test_navigate_to_parent_of_root(self):
        result = filepicker.navigate_to_parent("/")
        assert result == "/"


class TestIsVideoFile:
    def test_is_video_file_true(self):
        assert filepicker.is_video_file("video.mp4") is True
        assert filepicker.is_video_file("video.MOV") is True
        assert filepicker.is_video_file("video.mkv") is True

    def test_is_video_file_false(self):
        assert filepicker.is_video_file("readme.txt") is False
        assert filepicker.is_video_file("image.jpg") is False
        assert filepicker.is_video_file("noextension") is False
