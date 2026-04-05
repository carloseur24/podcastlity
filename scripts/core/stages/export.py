"""Stage 7: Export - Render final videos at full quality."""

from pathlib import Path

from scripts.core.exceptions import StageError
from scripts.utils import ffmpeg
from scripts.utils.session import SessionManager


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

    profile_name = session.profile or "default"

    # Assembled in output/proxies, exports go to output/exports
    proxies_dir = workspace_path / "output" / "proxies" / session_id
    exports_dir = workspace_path / "output" / "exports" / session_id
    exports_dir.mkdir(parents=True, exist_ok=True)

    assembled = proxies_dir / f"assembled_{profile_name}_proxy.mp4"
    if not assembled.exists():
        raise StageError("export", f"Assembled video not found: {assembled}")

    # Default profile exports as youtube_lf
    output = exports_dir / "youtube_lf.mp4"
    ffmpeg.export_full_quality(str(assembled), str(output))
    export_files = [str(output)]

    session.status = "exported"
    session_manager.save_session(session)

    return {
        "export_files": export_files,
        "session_status": "exported",
    }
