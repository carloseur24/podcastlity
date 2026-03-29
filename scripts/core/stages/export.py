"""Stage 7: Export - Render final videos at full quality."""

import json
from pathlib import Path

from scripts.utils.session import SessionManager
from scripts.utils import ffmpeg
from scripts.core.exceptions import StageError


def run(session_id: str, workspace: str) -> dict:
    """
    Export final videos in full quality.
    
    Args:
        session_id: The session identifier
        workspace: Path to workspace root
        
    Returns:
        dict with keys: export_files, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)
    
    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("export", f"Session '{session_id}' not found")
    
    profile_name = session.profile or "longform"
    
    proxies_dir = workspace_path / "proxies" / session_id
    exports_dir = workspace_path / "exports" / session_id
    exports_dir.mkdir(parents=True, exist_ok=True)
    
    assembled = proxies_dir / f"assembled_{profile_name}_proxy.mp4"
    if not assembled.exists():
        raise StageError("export", f"Assembled video not found: {assembled}")
    
    if profile_name == "both":
        targets = ["youtube_lf", "shorts"]
    elif profile_name == "longform":
        targets = ["youtube_lf"]
    else:
        targets = ["shorts"]
    
    export_files = []
    for target in targets:
        output = exports_dir / f"{target}.mp4"
        ffmpeg.export_full_quality(str(assembled), str(output))
        export_files.append(str(output))
    
    session.status = "exported"
    session_manager.save_session(session)
    
    return {
        "export_files": export_files,
        "session_status": "exported",
    }
