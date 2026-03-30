"""Stage 6: Assemble - Trim and concatenate video segments."""

import json
from pathlib import Path

from scripts.utils.session import SessionManager
from scripts.utils import ffmpeg
from scripts.core.exceptions import StageError


def run(session_id: str, workspace: str) -> dict:
    """
    Assemble video from cutmap using original (not proxy) for best quality.
    
    Args:
        session_id: The session identifier
        workspace: Path to workspace root
        
    Returns:
        dict with keys: assembled_file, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)
    
    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("assemble", f"Session '{session_id}' not found")
    
    profile_name = session.profile or "longform"
    
    cutmap_file = workspace_path / "cutmaps" / session_id / f"{profile_name}.json"
    if not cutmap_file.exists():
        raise StageError("assemble", f"Cutmap not found: {cutmap_file}")
    
    cutmap = json.loads(cutmap_file.read_text())
    
    proxies_dir = workspace_path / "proxies" / session_id
    proxies_dir.mkdir(parents=True, exist_ok=True)
    
    camera_original = workspace_path / "recordings" / session_id / "camera.mp4"
    camera_proxy = proxies_dir / "camera_proxy.mp4"
    
    source_video = camera_original if camera_original.exists() else camera_proxy
    
    if not source_video.exists():
        raise StageError("assemble", f"Source video not found")
    
    segments = []
    for i, interval in enumerate(cutmap["keep_intervals"]):
        seg_file = proxies_dir / f"seg_{i:04d}.mp4"
        ffmpeg.trim_video(
            str(source_video),
            str(seg_file),
            interval["start"],
            interval["end"],
        )
        segments.append(str(seg_file))
    
    assembled_file = None
    if segments:
        output_file = proxies_dir / f"assembled_{profile_name}_proxy.mp4"
        ffmpeg.concat_videos(segments, str(output_file))
        
        clean_audio = workspace_path / "audio" / session_id / "master_clean.wav"
        if clean_audio.exists():
            temp_with_audio = proxies_dir / f"assembled_{profile_name}_temp.mp4"
            ffmpeg.replace_audio(str(output_file), str(clean_audio), str(temp_with_audio), stereo_widen=True)
            Path(temp_with_audio).replace(output_file)
        
        if profile_name == "shorts":
            vertical_file = proxies_dir / f"assembled_{profile_name}_vertical.mp4"
            ffmpeg.convert_to_vertical(str(output_file), str(vertical_file))
            vertical_file.replace(output_file)
        
        assembled_file = str(output_file)
    
    session.status = "assembled"
    session_manager.save_session(session)
    
    return {
        "assembled_file": assembled_file,
        "session_status": "assembled",
    }
