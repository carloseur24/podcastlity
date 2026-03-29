"""
End-to-end test using fulldeco.mp4 footage.
This tests the full pipeline programmatically.
"""
import json
import subprocess
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
FOOTAGE_PATH = PROJECT_ROOT / "footage" / "fulldeco.mp4"


@pytest.fixture
def e2e_workspace(tmp_path):
    root = tmp_path / "e2e_workspace"
    dirs = [
        "recordings", "proxies", "audio", "transcripts",
        "analysis", "cutmaps", "exports", "thumbnails/frame_grabs",
        "briefs", "metadata",
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "settings.json").write_text(json.dumps({
        "recordings_mount": str(root / "recordings"),
        "workspace_root": str(root),
        "ffmpeg_path": "imageio",
        "default_profile": "longform",
    }))
    (config_dir / "profiles.json").write_text(json.dumps({
        "longform": {"silence_threshold_db": -42, "silence_min_duration_s": 0.5},
        "shorts": {"silence_threshold_db": -40, "silence_min_duration_s": 0.3}
    }))
    (config_dir / "brand.json").write_text(json.dumps({
        "channel_name": "TestChannel",
        "primary_color": "#FFDD00"
    }))
    (config_dir / "filler_words_es.txt").write_text("este\neh\nmm")
    
    return root


@pytest.fixture
def e2e_session_id():
    return "e2e_test_session"


class TestE2EIngest:
    def test_copy_footage_to_session(self, e2e_workspace, e2e_session_id):
        from scripts.utils import session
        session.ensure_session_dirs(str(e2e_workspace), e2e_session_id)
        
        src = FOOTAGE_PATH
        dst = e2e_workspace / "recordings" / e2e_session_id / "camera.mp4"
        
        result = subprocess.run(
            ["cp", str(src), str(dst)],
            capture_output=True
        )
        
        assert result.returncode == 0
        assert dst.exists()
        assert dst.stat().st_size > 0


class TestE2EProxy:
    def test_create_proxy_video(self, e2e_workspace, e2e_session_id):
        from scripts.utils import ffmpeg
        from scripts.utils import session
        import shutil
        
        session.ensure_session_dirs(str(e2e_workspace), e2e_session_id)
        
        src = FOOTAGE_PATH
        camera_file = e2e_workspace / "recordings" / e2e_session_id / "camera.mp4"
        shutil.copy(src, camera_file)
        
        proxy_file = e2e_workspace / "proxies" / e2e_session_id / "camera_proxy.mp4"
        
        ffmpeg.create_proxy(str(camera_file), str(proxy_file))
        
        assert proxy_file.exists()
        assert proxy_file.stat().st_size > 0


class TestE2EFFmpegBasics:
    def test_get_video_duration(self):
        from scripts.utils import ffmpeg
        
        duration = ffmpeg.get_duration(str(FOOTAGE_PATH))
        
        assert duration > 0
        assert duration < 60

    def test_extract_audio(self, e2e_workspace):
        from scripts.utils import ffmpeg
        
        audio_file = e2e_workspace / "test_audio.wav"
        ffmpeg.extract_audio(str(FOOTAGE_PATH), str(audio_file))
        
        assert audio_file.exists()
        assert audio_file.stat().st_size > 0

    def test_extract_frame(self, e2e_workspace):
        from scripts.utils import ffmpeg
        
        frame_file = e2e_workspace / "test_frame.jpg"
        ffmpeg.extract_frame(str(FOOTAGE_PATH), str(frame_file), 0.0)
        
        assert frame_file.exists()
        assert frame_file.stat().st_size > 0


class TestE2EIdempotency:
    def test_proxy_creation_idempotent(self, e2e_workspace, e2e_session_id):
        from scripts.utils import ffmpeg
        from scripts.utils import session
        import shutil
        
        session.ensure_session_dirs(str(e2e_workspace), e2e_session_id)
        
        src = FOOTAGE_PATH
        camera_file = e2e_workspace / "recordings" / e2e_session_id / "camera.mp4"
        shutil.copy(src, camera_file)
        
        proxy_file = e2e_workspace / "proxies" / e2e_session_id / "camera_proxy.mp4"
        
        ffmpeg.create_proxy(str(camera_file), str(proxy_file))
        size_after_first = proxy_file.stat().st_size
        
        ffmpeg.create_proxy(str(camera_file), str(proxy_file))
        size_after_second = proxy_file.stat().st_size
        
        assert size_after_first == size_after_second
