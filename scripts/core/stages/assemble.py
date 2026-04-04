"""Stage 6: Assemble - Trim and concatenate video segments.

Pipeline flow:
1. Read cutmap to get keep intervals
2. For each interval:
   - Trim video segment
   - Extract corresponding audio segment from master_voice.wav
3. Concatenate audio segments (matches video timing perfectly)
4. Replace audio in final video
"""

import json
from pathlib import Path

from scripts.utils.session import SessionManager
from scripts.utils import ffmpeg
from scripts.core.exceptions import StageError


def run(session_id: str, workspace: str) -> dict:
    """
    Assemble video from cutmap using original video for best quality.
    Audio is extracted from master_voice.wav to match video segment timing.

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

    profile_name = session.profile or "default"

    # Cutmap in output/cutmaps
    cutmap_file = (
        workspace_path / "output" / "cutmaps" / session_id / f"{profile_name}.json"
    )
    if not cutmap_file.exists():
        raise StageError("assemble", f"Cutmap not found: {cutmap_file}")

    cutmap = json.loads(cutmap_file.read_text())
    keep_intervals = cutmap.get("keep_intervals", [])

    # Assembled goes in output/proxies
    proxies_dir = workspace_path / "output" / "proxies" / session_id
    proxies_dir.mkdir(parents=True, exist_ok=True)

    # Use original camera video for best quality (data/recordings)
    camera_original = workspace_path / "data" / "recordings" / session_id / "camera.mp4"
    camera_proxy = proxies_dir / "camera_proxy.mp4"
    source_video = camera_original if camera_original.exists() else camera_proxy

    if not source_video.exists():
        raise StageError("assemble", f"Source video not found")

    # Get the cleaned audio from output/audio
    voice_audio = workspace_path / "output" / "audio" / session_id / "master_voice.wav"
    if not voice_audio.exists():
        raise StageError("assemble", f"Cleaned audio not found: {voice_audio}")

    print(f"[assemble] Source video: {source_video}")
    print(f"[assemble] Cleaned audio: {voice_audio}")
    print(f"[assemble] Keep intervals: {len(keep_intervals)}")

    # Build video segments from cutmap
    video_segments = []
    audio_segments = []

    for i, interval in enumerate(keep_intervals):
        start = interval["start"]
        end = interval["end"]

        # Trim video segment
        seg_file = proxies_dir / f"seg_{i:04d}.mp4"
        ffmpeg.trim_video(str(source_video), str(seg_file), start, end)
        video_segments.append(str(seg_file))

        # Extract corresponding audio segment from master_voice.wav
        # This ensures perfect sync with video timing
        audio_seg_file = proxies_dir / f"seg_{i:04d}.wav"
        ffmpeg.extract_audio_segment(
            str(voice_audio), str(audio_seg_file), start, end, sample_rate=48000
        )
        audio_segments.append(str(audio_seg_file))
        print(f"[assemble] Segment {i}: video {start}s-{end}s, audio extracted")

    assembled_file = None
    if video_segments:
        # Concatenate video segments
        output_file = proxies_dir / f"assembled_{profile_name}_proxy.mp4"
        ffmpeg.concat_videos(video_segments, str(output_file))

        # Concatenate audio segments to match video timing
        if audio_segments:
            concatenated_audio = proxies_dir / f"assembled_{profile_name}_audio.wav"
            if len(audio_segments) == 1:
                import shutil

                shutil.copy(audio_segments[0], str(concatenated_audio))
            else:
                ffmpeg.concat_audio(audio_segments, str(concatenated_audio))

            print(f"[assemble] Concatenated audio: {concatenated_audio}")

            # Replace video audio with concatenated cleaned audio
            temp_with_audio = proxies_dir / f"assembled_{profile_name}_temp.mp4"
            ffmpeg.replace_audio(
                str(output_file),
                str(concatenated_audio),
                str(temp_with_audio),
                stereo_widen=True,
            )
            Path(temp_with_audio).replace(output_file)

        assembled_file = str(output_file)

    session.status = "assembled"
    session_manager.save_session(session)

    return {
        "assembled_file": assembled_file,
        "session_status": "assembled",
    }
