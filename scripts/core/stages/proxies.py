"""Stage 2: Proxies - Create proxy videos and extract audio."""

from pathlib import Path

from scripts.utils.session import SessionManager
from scripts.utils import ffmpeg
from scripts.core.exceptions import StageError


def run(session_id: str, workspace: str) -> dict:
    """
    Create proxy videos and extract audio.
    
    Args:
        session_id: The session identifier
        workspace: Path to workspace root
        
    Returns:
        dict with keys: camera_proxy, screen_proxy, audio_path, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)
    
    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("proxies", f"Session '{session_id}' not found")
    
    camera_proxy_path = None
    screen_proxy_path = None
    audio_path = None
    
    camera_proxy = workspace_path / "proxies" / session_id / "camera_proxy.mp4"
    screen_proxy = workspace_path / "proxies" / session_id / "screen_proxy.mp4"
    camera_proxy.parent.mkdir(parents=True, exist_ok=True)
    
    if session.camera_file and not camera_proxy.exists():
        ffmpeg.create_proxy(session.camera_file, str(camera_proxy))
        camera_proxy_path = str(camera_proxy)
    
    if session.screen_file and not screen_proxy.exists():
        ffmpeg.create_proxy(session.screen_file, str(screen_proxy))
        screen_proxy_path = str(screen_proxy)
    
    audio_dir = workspace_path / "audio" / session_id
    audio_dir.mkdir(parents=True, exist_ok=True)
    master_wav = audio_dir / "master.wav"
    
    if session.camera_file and not master_wav.exists():
        ffmpeg.extract_audio(session.camera_file, str(master_wav))
        audio_path = str(master_wav)
    
    session.status = "proxied"
    session_manager.save_session(session)
    
    return {
        "camera_proxy": camera_proxy_path,
        "screen_proxy": screen_proxy_path,
        "audio_path": audio_path,
        "session_status": "proxied",
    }
