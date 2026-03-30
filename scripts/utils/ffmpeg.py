import subprocess
import json
import re
from pathlib import Path
from typing import Optional
import imageio_ffmpeg

from scripts.config import get_config


def get_ffmpeg_path() -> str:
    config = get_config()
    ffmpeg_path = config.get_ffmpeg_path()
    
    if ffmpeg_path == "imageio":
        return imageio_ffmpeg.get_ffmpeg_exe()
    return ffmpeg_path


def run_ffmpeg(
    args: list,
    capture_output: bool = False,
    check: bool = True,
    verbose: bool = False,
) -> subprocess.CompletedProcess:
    cmd = [get_ffmpeg_path()] + args
    if verbose:
        print(f"[FFmpeg] {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        check=check,
    )
    if capture_output and verbose:
        if result.stdout:
            print(f"[stdout] {result.stdout[:500]}")
        if result.stderr:
            print(f"[stderr] {result.stderr[:500]}")
    return result


def get_duration(video_path: str) -> float:
    cmd = [
        get_ffmpeg_path(),
        "-i", video_path,
        "-f", "null", "-"
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = float(match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    return 0.0


def extract_audio(
    video_path: str,
    output_path: str,
    mono: bool = True,
    sample_rate: int = 16000,
) -> None:
    args = ["-y", "-i", video_path]
    if mono:
        args.extend(["-vn", "-ac", "1"])
    args.extend([
        "-ar", str(sample_rate),
        "-sample_fmt", "s16",
        output_path
    ])
    run_ffmpeg(args)


def create_proxy(
    input_path: str,
    output_path: str,
    resolution: str = "1280x720",
    crf: int = 28,
    preset: str = "ultrafast",
) -> None:
    args = [
        "-y", "-i", input_path,
        "-vf", f"scale={resolution.replace('x', ':')}",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ]
    run_ffmpeg(args)


def trim_video(
    input_path: str,
    output_path: str,
    start: float,
    end: float,
    copy: bool = True,
) -> None:
    args = ["-y", "-ss", str(start), "-to", str(end), "-i", input_path]
    if copy:
        args.extend(["-c", "copy", output_path])
    else:
        args.extend([
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ])
    run_ffmpeg(args)


def concat_videos(
    input_list: list[str],
    output_path: str,
) -> None:
    list_file = Path(output_path).parent / "concat_temp.txt"
    with open(list_file, "w") as f:
        for path in input_list:
            f.write(f"file '{path}'\n")
    
    args = [
        "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        output_path
    ]
    run_ffmpeg(args)
    list_file.unlink(missing_ok=True)


def burn_subtitles(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    crf: int = 22,
) -> None:
    args = [
        "-y", "-i", video_path,
        "-vf", f"ass={subtitle_path}",
        "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
        "-c:a", "copy",
        output_path
    ]
    run_ffmpeg(args)


def get_resolution(video_path: str) -> tuple[int, int]:
    cmd = [
        get_ffmpeg_path(),
        "-i", video_path,
        "-f", "ffmetadata", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Use ffprobe for cleaner solution
    cmd = [
        get_ffmpeg_path().replace("ffmpeg", "ffprobe"),
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        return data["streams"][0]["width"], data["streams"][0]["height"]
    except Exception:
        return 1920, 1080


def extract_frame(
    video_path: str,
    output_path: str,
    timestamp: float,
    quality: int = 2,
) -> None:
    args = [
        "-y", "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", str(quality),
        output_path
    ]
    run_ffmpeg(args)


def apply_loudnorm(
    input_path: str,
    output_path: str,
    target_lufs: float = -14.0,
) -> None:
    args = [
        "-y", "-i", input_path,
        "-af", f"loudnorm=I={target_lufs}:TP=-1:LRA=7",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    run_ffmpeg(args)


def get_frame_count(video_path: str) -> int:
    cmd = [
        get_ffmpeg_path().replace("ffmpeg", "ffprobe"),
        "-v", "error",
        "-count_frames",
        "-select_streams", "v:0",
        "-show_entries", "stream=nb_read_frames",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return int(result.stdout.strip())
    except Exception:
        return 0


def enhance_audio(
    input_path: str,
    output_path: str,
    noise_reduce: bool = True,
    normalize: bool = True,
    eq: bool = True,
    ensure_stereo: bool = True,
) -> None:
    """
    Enhance audio with:
    - Noise reduction (highpass + lowpass + denoise)
    - Volume normalization (loudnorm)
    - Simple EQ (bass/treble)
    - Ensure stereo
    """
    filters = []
    
    # Noise reduction: highpass to remove rumble, lowpass to remove hiss
    if noise_reduce:
        filters.append("highpass=f=80")
        filters.append("lowpass=f=8000")
        filters.append("afftdn=nf=-25")  # Noise floor -25dB
    
    # Simple EQ - boost bass slightly, gentle presence
    if eq:
        filters.append("equalizer=f=100:t=h:g=3")   # Bass +3dB
        filters.append("equalizer=f=3000:t=h:g=-1")  # Slight cut at 3kHz
    
    # Normalize loudness to -16 LUFS (standard for speech)
    if normalize:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    
    # Ensure stereo
    if ensure_stereo:
        filters.append("aresample=matrix_encoding=dplii")
    
    # Build filter chain
    filter_chain = ",".join(filters)
    
    args = [
        "-y",
        "-i", input_path,
        "-af", filter_chain,
        "-c:a", "pcm_s16le",
        "-c:v", "copy",
        output_path
    ]
    run_ffmpeg(args)


def export_full_quality(
    input_path: str,
    output_path: str,
    start: Optional[float] = None,
    end: Optional[float] = None,
) -> None:
    """
    Export in full quality (or original) quality.
    Uses CRF 18 (high quality) instead of proxy quality.
    """
    args = ["-y"]
    
    if start is not None and end is not None:
        args.extend(["-ss", str(start), "-to", str(end)])
    
    args.extend(["-i", input_path])
    
    # High quality encode
    args.extend([
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "256k",
        "-movflags", "+faststart",
        output_path
    ])
    run_ffmpeg(args)


def replace_audio(video_path: str, audio_path: str, output_path: str, stereo_widen: bool = False) -> None:
    """
    Replace audio track in video with new audio file.
    
    Args:
        video_path: Input video file
        audio_path: Input audio file (mono)
        output_path: Output video file
        stereo_widen: If True, apply extrastereo for wider sound
    """
    if stereo_widen:
        from scripts.config import get_config
        config = get_config()
        stereo_cfg = config.get_stereo_settings()
        m_val = stereo_cfg.get("extrastereo_m", 1.5)
        
        args = [
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-af", f"extrastereo=m={m_val}",
            "-c:a", "aac", "-b:a", "256k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]
    else:
        args = [
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "256k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]
    run_ffmpeg(args)


def convert_to_vertical(input_path: str, output_path: str) -> None:
    """
    Convert 16:9 video to 9:16 vertical (center crop).
    """
    args = [
        "-y",
        "-i", input_path,
        "-vf", "crop=ih*9/16:ih:(iw-iw*9/16)/2:0,scale=1080:1920",
        "-c:a", "copy",
        output_path
    ]
    run_ffmpeg(args)
