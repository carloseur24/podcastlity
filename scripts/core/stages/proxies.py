"""Stage: Proxies - Create proxy videos and extract audio (output/proxies, output/audio)."""

from pathlib import Path

from scripts.core.exceptions import StageError
from scripts.utils import ffmpeg
from scripts.utils.session import SessionManager


def run(session_id: str, workspace: str) -> dict:
    """
    Create proxy video and extract audio.
    Now uses output/ directories.

    Args:
        session_id: The session identifier
        workspace: Path to workspace root

    Returns:
        dict with keys: proxy_path, audio_path, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)

    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("proxies", f"Session '{session_id}' not found")

    # Input video is in data/recordings
    input_video = workspace_path / "data" / "recordings" / session_id / "input.mp4"
    if not input_video.exists():
        raise StageError("proxies", f"Input video not found: {input_video}")

    # Proxies go in output/proxies
    proxy_path = None
    audio_path = None

    proxy = workspace_path / "output" / "proxies" / session_id / "proxy.mp4"
    proxy.parent.mkdir(parents=True, exist_ok=True)

    if not proxy.exists():
        ffmpeg.create_proxy(str(input_video), str(proxy))
    proxy_path = str(proxy)

    # Audio goes in output/audio
    audio_dir = workspace_path / "output" / "audio" / session_id
    audio_dir.mkdir(parents=True, exist_ok=True)
    master_wav = audio_dir / "master.wav"

    if not master_wav.exists():
        ffmpeg.extract_audio(str(input_video), str(master_wav), sample_rate=48000)
    audio_path = str(master_wav)

    session.status = "proxied"
    session_manager.save_session(session)

    return {
        "proxy_path": proxy_path,
        "audio_path": audio_path,
        "session_status": "proxied",
    }
