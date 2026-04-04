"""Stage: Ingest - Copy source file to session directory (data/recordings)."""

import shutil
from pathlib import Path

from scripts.core.exceptions import StageError
from scripts.utils.session import SessionManager


def run(session_id: str, workspace: str) -> dict:
    """
    Copy video file to session directory.
    Now uses data/recordings/ for session files.

    Args:
        session_id: The session identifier
        workspace: Path to workspace root

    Returns:
        dict with keys: video_path, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)

    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("ingest", f"Session '{session_id}' not found")

    # Session files go in data/recordings
    session_dir = workspace_path / "data" / "recordings" / session_id

    video_path: str | None = None

    if session.video_file:
        dest_video = session_dir / "input.mp4"
        if not dest_video.exists():
            shutil.copy(session.video_file, dest_video)
        video_path = str(dest_video)
        session.video_file = video_path

    session.status = "ingested"
    session_manager.save_session(session)

    return {
        "video_path": video_path,
        "session_status": "ingested",
    }
