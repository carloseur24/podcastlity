"""Stage 5: Cutmap - Generate edit decision map using transcript + analysis."""

import json
from pathlib import Path

from scripts.utils.session import SessionManager
from scripts.utils import ffmpeg
from scripts.core.exceptions import StageError
from scripts.config import get_config


def run(session_id: str, workspace: str) -> dict:
    """
    Generate cutmap from analysis data and transcript.

    Uses transcript-aware cutting to keep complete sentences/phrases
    instead of cutting mid-sentence at silence points.

    CAN be disabled via profile config (enable_cutting: false).

    Args:
        session_id: The session identifier
        workspace: Path to workspace root

    Returns:
        dict with keys: cutmap_file, output_duration, input_duration, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)
    config = get_config(workspace)

    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("cutmap", f"Session '{session_id}' not found")

    profile_name = session.profile or "longform"

    # Check if cutting is enabled (default: disabled)
    enable_cutting = config.get_profile_enable_cutting(profile_name)

    if not enable_cutting:
        # No cutting - keep full video
        analysis_dir = workspace_path / "output" / "analysis" / session_id
        cutmap_dir = workspace_path / "output" / "cutmaps" / session_id
        cutmap_dir.mkdir(parents=True, exist_ok=True)

        # Get video duration
        camera_proxy = (
            workspace_path / "output" / "proxies" / session_id / "camera_proxy.mp4"
        )
        if camera_proxy.exists():
            duration = ffmpeg.get_duration(str(camera_proxy))
        else:
            duration = 600  # Default 10 minutes

        # Create a "no-cut" cutmap
        cutmap = {
            "profile": profile_name,
            "enable_cutting": False,
            "total_input_duration_s": duration,
            "total_output_duration_s": duration,
            "keep_intervals": [{"start": 0, "end": duration, "type": "content"}],
            "cut_points": [],
        }

        (cutmap_dir / f"{profile_name}.json").write_text(json.dumps(cutmap, indent=2))

        session.status = "cutmapped"
        session_manager.save_session(session)

        return {
            "cutmap_file": str(cutmap_dir / f"{profile_name}.json"),
            "output_duration": duration,
            "input_duration": duration,
            "session_status": "cutmapped",
        }

    # Cutting is enabled - proceed with normal logic
    analysis_dir = workspace_path / "output" / "analysis" / session_id
    cutmap_dir = workspace_path / "output" / "cutmaps" / session_id
    cutmap_dir.mkdir(parents=True, exist_ok=True)

    silence_map = json.loads((analysis_dir / "silence_map.json").read_text())
    filler_map = json.loads((analysis_dir / "filler_map.json").read_text())

    # Load transcript for smart cutting (output/transcripts)
    transcript_file = (
        workspace_path / "output" / "transcripts" / session_id / "segments.json"
    )
    transcript_segments = []
    if transcript_file.exists():
        transcript_segments = json.loads(transcript_file.read_text())

    profiles_file = workspace_path / "config" / "profiles.json"
    profiles = json.loads(profiles_file.read_text())
    profile = profiles.get(profile_name, profiles["longform"])

    # Camera proxy in output/proxies
    camera_proxy = (
        workspace_path / "output" / "proxies" / session_id / "camera_proxy.mp4"
    )
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
        transcript_segments=transcript_segments,
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
    transcript_segments: list,
    duration: float,
    profile_name: str,
) -> dict:
    """
    Build cutmap using transcript-aware cutting.

    Strategy:
    1. Use silence/low_energy for cut points
    2. Snap cut points to nearest sentence/phrase boundaries from transcript
    3. Keep complete sentences, don't cut mid-thought
    """
    cut_points = []

    # Add silence cut points
    for silence in silence_map.get("silence_intervals", []):
        if silence["duration"] >= 0.2:
            cut_points.append((silence["start"], "silence", silence["duration"]))

    # Add low energy cut points
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

    # If we have transcript, snap cut points to sentence boundaries
    if transcript_segments:
        cut_points = _snap_to_sentence_boundaries(cut_points, transcript_segments)

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
                    keep_intervals.append(
                        {
                            "start": current_pos,
                            "end": cp_time,
                            "type": "content",
                        }
                    )
                    current_pos = cp_time + cp_duration
            if current_pos < duration:
                keep_intervals.append(
                    {
                        "start": current_pos,
                        "end": duration,
                        "type": "content",
                    }
                )
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
                keep_intervals.append(
                    {
                        "start": current_pos,
                        "end": cp_time,
                        "type": "content",
                    }
                )
                current_pos = cp_time + cp_duration

        if current_pos < duration:
            keep_intervals.append(
                {
                    "start": current_pos,
                    "end": duration,
                    "type": "content",
                }
            )

    output_duration = sum(i["end"] - i["start"] for i in keep_intervals)

    # Generate topic/title from first few segments
    title = _generate_title(transcript_segments, keep_intervals)

    return {
        "profile": profile_name,
        "total_input_duration_s": duration,
        "total_output_duration_s": output_duration,
        "keep_intervals": keep_intervals,
        "removed_silence_s": silence_map.get("potential_time_saved_s", 0),
        "removed_fillers": len(filler_map.get("fillers", [])),
        "hook_start_s": keep_intervals[0]["start"] if keep_intervals else 0,
        "title": title,
        "agent_notes": "Transcript-aware cutmap"
        if transcript_segments
        else "Algorithmic cutmap",
    }


def _snap_to_sentence_boundaries(cut_points: list, transcript_segments: list) -> list:
    """
    Snap cut points to nearest sentence/phrase boundaries from transcript.

    This ensures we cut at natural pauses (end of sentences) rather than
    cutting mid-sentence.
    """
    if not cut_points or not transcript_segments:
        return cut_points

    # Build list of sentence boundaries from transcript
    sentence_ends = []
    for seg in transcript_segments:
        # Use segment end as a sentence boundary
        sentence_ends.append(seg["end"])
        # Also check for punctuation in text to find sentence boundaries
        text = seg.get("text", "")
        if text:
            # Simple heuristic: periods, commas at word boundaries
            words = seg.get("words", [])
            for i, w in enumerate(words):
                word = w.get("word", "")
                # If word ends with sentence punctuation
                if any(p in word for p in ".!?"):
                    sentence_ends.append(w["end"])

    sentence_ends = sorted(set(sentence_ends))

    # Snap each cut point to nearest sentence boundary (within 2 seconds)
    snapped_points = []
    for cp_time, cp_type, cp_duration in cut_points:
        best_boundary = cp_time
        min_dist = float("inf")

        for boundary in sentence_ends:
            # Only snap forward (don't cut before the original point)
            if boundary >= cp_time - 0.5:
                dist = abs(boundary - cp_time)
                if dist < min_dist and dist < 2.0:  # Within 2 seconds
                    min_dist = dist
                    best_boundary = boundary

        snapped_points.append((best_boundary, cp_type, cp_duration))

    return snapped_points


def _generate_title(transcript_segments: list, keep_intervals: list) -> str:
    """Generate a simple title from transcript."""
    if not transcript_segments or not keep_intervals:
        return "Untitled"

    # Get first few words from first kept segment
    start_time = keep_intervals[0]["start"]

    for seg in transcript_segments:
        if seg["start"] >= start_time:
            text = seg.get("text", "").strip()
            if text:
                # Clean and truncate
                title = text[:100].strip()
                if len(text) > 100:
                    title += "..."
                return title

    return "Untitled"
