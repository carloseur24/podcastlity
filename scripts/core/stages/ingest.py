"""Stage 1: Ingest - Copy source files to session directory."""

import shutil
from pathlib import Path
from typing import Optional

from scripts.utils.session import SessionManager
from scripts.core.exceptions import StageError


def run(session_id: str, workspace: str) -> dict:
    """
    Copy camera and screen files to session directory.
    
    Args:
        session_id: The session identifier
        workspace: Path to workspace root
        
    Returns:
        dict with keys: camera_path, screen_path, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)
    
    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("ingest", f"Session '{session_id}' not found")
    
    session_dir = workspace_path / "recordings" / session_id
    
    camera_path: Optional[str] = None
    screen_path: Optional[str] = None
    
    if session.camera_file:
        dest_cam = session_dir / "camera.mp4"
        if not dest_cam.exists():
            shutil.copy(session.camera_file, dest_cam)
        camera_path = str(dest_cam)
        session.camera_file = camera_path
    
    if session.screen_file:
        dest_screen = session_dir / "screen.mp4"
        if not dest_screen.exists():
            shutil.copy(session.screen_file, dest_screen)
        screen_path = str(dest_screen)
        session.screen_file = screen_path
    
    session.status = "ingested"
    session_manager.save_session(session)
    
    return {
        "camera_path": camera_path,
        "screen_path": screen_path,
        "session_status": "ingested",
    }
