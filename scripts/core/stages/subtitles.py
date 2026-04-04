"""Stage: Subtitles - Apply Remotion kinetic subtitles to video."""

import json
import subprocess
from pathlib import Path

from scripts.utils.session import SessionManager
from scripts.utils import ffmpeg
from scripts.utils.transcript_adapter import (
    load_transcript,
    convert_to_remotion_captions,
    get_preset_for_profile,
    export_captions_json,
)
from scripts.core.exceptions import StageError


def run(session_id: str, workspace: str) -> dict:
    """
    Apply Remotion kinetic subtitles to video.

    Pipeline:
    1. Load transcript and preset for profile
    2. Convert transcript to Remotion Caption format
    3. Export captions and preset to JSON
    4. Run Remotion render with Python HTTP server
    5. Replace raw video with final

    Args:
        session_id: The session identifier
        workspace: Path to workspace root

    Returns:
        dict with keys: subtitle_file, preset_used, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)

    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("subtitles", f"Session '{session_id}' not found")

    profile = session.profile or "longform"

    # Load preset for this profile
    preset_name, preset_config = get_preset_for_profile(workspace, profile)
    print(f"[subtitles] Using preset: {preset_name} for profile: {profile}")

    # Load and convert transcript
    transcript = load_transcript(workspace, session_id)

    # Convert to Remotion format
    captions = convert_to_remotion_captions(transcript)

    print(f"[subtitles] Converted {len(captions)} caption tokens")

    # Export captions and preset to temp JSON files
    captions_file = workspace_path / "temp" / f"{session_id}_captions.json"
    presets_file = workspace_path / "temp" / f"{session_id}_preset.json"

    captions_file.parent.mkdir(parents=True, exist_ok=True)
    export_captions_json(captions, str(captions_file))
    presets_file.write_text(json.dumps(preset_config))

    print(f"[subtitles] Captions file: {captions_file}")
    print(f"[subtitles] Presets file: {presets_file}")
    print(f"[subtitles] Captions file exists: {captions_file.exists()}")
    print(f"[subtitles] Presets file exists: {presets_file.exists()}")

    # Find input video (from Assemble stage)
    proxies_dir = workspace_path / "proxies" / session_id
    exports_dir = workspace_path / "exports" / session_id
    exports_dir.mkdir(parents=True, exist_ok=True)

    # Use assembled video as input
    assembled_file = proxies_dir / f"assembled_{profile}_proxy.mp4"

    if not assembled_file.exists():
        raise StageError("subtitles", f"Assembled video not found: {assembled_file}")

    # Check and transcode video if needed (Remotion needs H.264)
    video_codec = ffmpeg.get_video_codec(str(assembled_file))
    print(f"[subtitles] Input video codec: {video_codec}")

    remotion_dir = workspace_path / "remotion"
    input_video = remotion_dir / "input_video.mp4"

    if video_codec != "h264":
        print(f"[subtitles] Transcoding to H.264 for Remotion compatibility...")
        ffmpeg.transcode_to_h264_baseline(str(assembled_file), str(input_video))
    else:
        import shutil

        shutil.copy(str(assembled_file), str(input_video))

    # Get video properties
    duration = ffmpeg.get_duration(str(assembled_file))
    width, height = ffmpeg.get_resolution(str(assembled_file))

    print(f"[subtitles] Input video: {assembled_file}")
    print(f"[subtitles] Duration: {duration}s, Resolution: {width}x{height}")

    # Output file - use absolute path
    output_file = (exports_dir / f"final_{profile}.mp4").resolve()

    # Run Remotion render
    render_script = remotion_dir / "render.js"

    if not render_script.exists():
        raise StageError(
            "subtitles", f"Remotion render script not found: {render_script}"
        )

    # Build command
    cmd = [
        "node",
        str(render_script),
        str(input_video),
        str(output_file),
        str(captions_file),
        str(presets_file),
        "30",
        str(duration),
        str(width),
        str(height),
    ]

    print(f"[subtitles] Running Remotion render...")
    print(f"[subtitles] Command: {' '.join(cmd)}")
    print(f"[subtitles] Working dir: {workspace_path}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(workspace_path),
            capture_output=True,
            text=True,
            timeout=600,
        )

        print(f"[subtitles] Return code: {result.returncode}")
        if result.stdout:
            print(f"[subtitles] Stdout (first 500): {result.stdout[:500]}")
        if result.stderr:
            print(f"[subtitles] Stderr (first 500): {result.stderr[:500]}")

        if result.returncode != 0:
            print(f"[subtitles] Remotion stderr: {result.stderr}")
            raise StageError("subtitles", f"Remotion render failed: {result.stderr}")

        print(f"[subtitles] Render complete: {output_file}")

    except subprocess.TimeoutExpired:
        raise StageError("subtitles", "Remotion render timed out after 10 minutes")

    # Clean up temp files
    if captions_file.exists():
        captions_file.unlink()
    if presets_file.exists():
        presets_file.unlink()
    if input_video.exists():
        input_video.unlink()

    # Update session status
    session.status = "subtitled"
    session_manager.save_session(session)

    return {
        "subtitle_file": str(output_file),
        "preset_used": preset_name,
        "captions_count": len(captions),
        "session_status": "subtitled",
    }
