"""Stage 5: Cutmap - Generate edit decision map."""

import json
from pathlib import Path

from scripts.utils.session import SessionManager
from scripts.utils import ffmpeg
from scripts.core.exceptions import StageError


def run(session_id: str, workspace: str) -> dict:
    """
    Generate cutmap from analysis data.
    
    Args:
        session_id: The session identifier
        workspace: Path to workspace root
        
    Returns:
        dict with keys: cutmap_file, output_duration, input_duration, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)
    
    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("cutmap", f"Session '{session_id}' not found")
    
    profile_name = session.profile or "longform"
    
    analysis_dir = workspace_path / "analysis" / session_id
    cutmap_dir = workspace_path / "cutmaps" / session_id
    cutmap_dir.mkdir(parents=True, exist_ok=True)
    
    silence_map = json.loads((analysis_dir / "silence_map.json").read_text())
    filler_map = json.loads((analysis_dir / "filler_map.json").read_text())
    
    profiles_file = workspace_path / "config" / "profiles.json"
    profiles = json.loads(profiles_file.read_text())
    profile = profiles.get(profile_name, profiles["longform"])
    
    camera_proxy = workspace_path / "proxies" / session_id / "camera_proxy.mp4"
    if camera_proxy.exists():
        duration = ffmpeg.get_duration(str(camera_proxy))
    else:
        duration = 600
    
    energy_map = {"windows": [], "low_energy_intervals": []}
    energy_file = analysis_dir / "energy_map.json"
    if energy_file.exists():
        energy_map = json.loads(energy_file.read_text())
    
    cutmap = _build_cutmap(
        silence_map=silence_map,
        filler_map=filler_map,
        energy_map=energy_map,
        duration=duration,
        profile_name=profile_name,
    )
    
    (cutmap_dir / f"{profile_name}.json").write_text(json.dumps(cutmap, indent=2))
    
    session.status = "cutmapped"
    session_manager.save_session(session)
    
    return {
        "cutmap_file": str(cutmap_dir / f"{profile_name}.json"),
        "output_duration": cutmap["total_output_duration_s"],
        "input_duration": cutmap["total_input_duration_s"],
        "session_status": "cutmapped",
    }


def _build_cutmap(
    silence_map: dict,
    filler_map: dict,
    energy_map: dict,
    duration: float,
    profile_name: str,
) -> dict:
    cut_points = []
    
    for silence in silence_map.get("silence_intervals", []):
        if silence["duration"] >= 0.2:
            cut_points.append((silence["start"], "silence", silence["duration"]))
    
    low_energy_windows = energy_map.get("windows", [])
    consecutive_low = 0
    low_energy_start = 0.0
    
    for i, w in enumerate(low_energy_windows):
        if w.get("low_energy") and w["t"] > 3.0:
            if consecutive_low == 0:
                low_energy_start = w["t"]
            consecutive_low += 1
            
            if consecutive_low >= 3:
                is_new = True
                for cp_time, _, _ in cut_points:
                    if abs(cp_time - low_energy_start) < 1.5:
                        is_new = False
                        break
                if is_new:
                    cut_points.append((low_energy_start, "low_energy", 1.5))
        else:
            consecutive_low = 0
    
    cut_points.sort(key=lambda x: x[0])
    
    if profile_name == "shorts":
        strict_cut_points = [(t, ty, d) for t, ty, d in cut_points if d >= 0.5]
        if len(strict_cut_points) < 1:
            keep_intervals = [{"start": 0, "end": duration, "type": "content"}]
            duration_saved = 0
        else:
            cut_points = strict_cut_points
            duration_saved = sum(d for _, _, d in cut_points)
            keep_intervals = []
            current_pos = 0.0
            min_segment = 1.5
            for cp_time, cp_type, cp_duration in cut_points:
                if cp_time > current_pos + min_segment:
                    keep_intervals.append({
                        "start": current_pos,
                        "end": cp_time,
                        "type": "content",
                    })
                    current_pos = cp_time + cp_duration
            if current_pos < duration:
                keep_intervals.append({
                    "start": current_pos,
                    "end": duration,
                    "type": "content",
                })
    else:
        duration_saved = sum(d for _, _, d in cut_points)
        keep_intervals = []
        current_pos = 0.0
        
        if silence_map.get("silence_intervals"):
            first_silence = silence_map["silence_intervals"][0]
            if first_silence.get("type") == "leading":
                current_pos = first_silence["end"]
        
        min_segment = 2.0
        for cp_time, cp_type, cp_duration in cut_points:
            if cp_time > current_pos + min_segment:
                keep_intervals.append({
                    "start": current_pos,
                    "end": cp_time,
                    "type": "content",
                })
                current_pos = cp_time + cp_duration
        
        if current_pos < duration:
            keep_intervals.append({
                "start": current_pos,
                "end": duration,
                "type": "content",
            })
    
    output_duration = sum(i["end"] - i["start"] for i in keep_intervals)
    
    return {
        "profile": profile_name,
        "total_input_duration_s": duration,
        "total_output_duration_s": output_duration,
        "keep_intervals": keep_intervals,
        "removed_silence_s": silence_map.get("potential_time_saved_s", 0),
        "removed_fillers": len(filler_map.get("fillers", [])),
        "hook_start_s": keep_intervals[0]["start"] if keep_intervals else 0,
        "agent_notes": "Algorithmic cutmap - no agent refinement",
    }
