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


def get_ffprobe_path() -> str:
    """Get ffprobe path - uses bundled or system ffprobe."""
    # Try system ffprobe first (more reliable)
    system_ffprobe = "/usr/bin/ffprobe"
    if Path(system_ffprobe).exists():
        return system_ffprobe

    # Fall back to imageio-ffmpeg's ffprobe
    ffmpeg_path = get_ffmpeg_path()
    return ffmpeg_path.replace("ffmpeg", "ffprobe")


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
    cmd = [get_ffmpeg_path(), "-i", video_path, "-f", "null", "-"]
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
    sample_rate: int = 48000,
) -> None:
    args = ["-y", "-i", video_path]
    if mono:
        args.extend(["-vn", "-ac", "1"])
    args.extend(["-ar", str(sample_rate), "-sample_fmt", "s16", output_path])
    run_ffmpeg(args)


def extract_audio_segment(
    audio_path: str,
    output_path: str,
    start: float,
    end: float,
    sample_rate: int = 48000,
) -> None:
    """Extract a segment from an audio file (like trim_video but for audio)."""
    duration = end - start
    args = [
        "-y",
        "-ss",
        str(start),
        "-t",
        str(duration),
        "-i",
        audio_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-sample_fmt",
        "s16",
        output_path,
    ]
    run_ffmpeg(args)


def create_proxy(
    input_path: str,
    output_path: str,
    resolution: str = "1280x720",
    crf: int = 28,
    preset: str = "ultrafast",
) -> None:
    args = [
        "-y",
        "-i",
        input_path,
        "-vf",
        f"scale={resolution.replace('x', ':')}",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        output_path,
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
        args.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                output_path,
            ]
        )
    run_ffmpeg(args)


def concat_videos(
    input_list: list[str],
    output_path: str,
) -> None:
    list_file = Path(output_path).parent / "concat_temp.txt"
    with open(list_file, "w") as f:
        for path in input_list:
            # Use absolute path to avoid directory issues
            abs_path = str(Path(path).resolve())
            f.write(f"file '{abs_path}'\n")

    args = [
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        output_path,
    ]
    run_ffmpeg(args)
    list_file.unlink(missing_ok=True)


def concat_audio(
    input_list: list[str],
    output_path: str,
) -> None:
    """Concatenate multiple audio files into one."""
    list_file = Path(output_path).parent / "concat_audio_temp.txt"
    with open(list_file, "w") as f:
        for path in input_list:
            # Use absolute path to avoid directory issues
            abs_path = str(Path(path).resolve())
            f.write(f"file '{abs_path}'\n")

    args = [
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c:a",
        "pcm_s16le",
        output_path,
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
        "-y",
        "-i",
        video_path,
        "-vf",
        f"ass={subtitle_path}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        str(crf),
        "-c:a",
        "copy",
        output_path,
    ]
    run_ffmpeg(args)


def get_resolution(video_path: str) -> tuple[int, int]:
    """Get video resolution using ffprobe."""
    cmd = [
        get_ffprobe_path(),
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        return data["streams"][0]["width"], data["streams"][0]["height"]
    except Exception:
        return 1920, 1080


def get_video_codec(video_path: str) -> str:
    """Get the video codec name (e.g., 'h264', 'hevc')."""
    cmd = [
        get_ffprobe_path(),
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "json",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        return data["streams"][0].get("codec_name", "unknown")
    except Exception:
        return "unknown"


def transcode_to_h264(input_path: str, output_path: str) -> None:
    """Transcode video to H.264 codec (Remotion-compatible, browser-friendly)."""
    transcode_to_h264_baseline(input_path, output_path)


def transcode_to_h264_baseline(input_path: str, output_path: str) -> None:
    """Transcode video to H.264 baseline profile for maximum browser compatibility."""
    # Use system ffmpeg with baseline profile for maximum browser compatibility
    cmd = [
        "/usr/bin/ffmpeg",
        "-y",
        "-i",
        input_path,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-profile:v",
        "baseline",  # Baseline profile for max compatibility
        "-level",
        "3.0",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",  # Enable streaming
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ffmpeg] Transcode stderr: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd)
    print(f"[ffmpeg] Transcoded to H.264 baseline: {output_path}")


def extract_frame(
    video_path: str,
    output_path: str,
    timestamp: float,
    quality: int = 2,
) -> None:
    args = [
        "-y",
        "-ss",
        str(timestamp),
        "-i",
        video_path,
        "-vframes",
        "1",
        "-q:v",
        str(quality),
        output_path,
    ]
    run_ffmpeg(args)


def apply_loudnorm(
    input_path: str,
    output_path: str,
    target_lufs: float = -14.0,
) -> None:
    args = [
        "-y",
        "-i",
        input_path,
        "-af",
        f"loudnorm=I={target_lufs}:TP=-1:LRA=7",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output_path,
    ]
    run_ffmpeg(args)


def get_frame_count(video_path: str) -> int:
    cmd = [
        get_ffprobe_path(),
        "-v",
        "error",
        "-count_frames",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=nb_read_frames",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
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
        filters.append("equalizer=f=100:t=h:g=3")  # Bass +3dB
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
        "-i",
        input_path,
        "-af",
        filter_chain,
        "-c:a",
        "pcm_s16le",
        "-c:v",
        "copy",
        output_path,
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
    args.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-movflags",
            "+faststart",
            output_path,
        ]
    )
    run_ffmpeg(args)


def replace_audio(
    video_path: str, audio_path: str, output_path: str, stereo_widen: bool = False
) -> None:
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
            "-i",
            video_path,
            "-i",
            audio_path,
            "-c:v",
            "copy",
            "-af",
            f"extrastereo=m={m_val}",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            output_path,
        ]
    else:
        args = [
            "-y",
            "-i",
            video_path,
            "-i",
            audio_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            output_path,
        ]
    run_ffmpeg(args)


def convert_to_vertical(input_path: str, output_path: str) -> None:
    """
    Convert 16:9 video to 9:16 vertical (center crop).
    """
    args = [
        "-y",
        "-i",
        input_path,
        "-vf",
        "crop=ih*9/16:ih:(iw-iw*9/16)/2:0,scale=1080:1920",
        "-c:a",
        "copy",
        output_path,
    ]
    run_ffmpeg(args)


def adjust_video_colors(
    input_path: str,
    output_path: str,
    brightness: float = 0.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    temperature: float = 0.0,
) -> None:
    """
    Adjust video colors using FFmpeg eq filter.

    Args:
        input_path: Input video path
        output_path: Output video path
        brightness: Brightness adjustment (-1 to 1, default 0)
        contrast: Contrast adjustment (0 to 2, default 1)
        saturation: Saturation adjustment (0 to 3, default 1)
        temperature: Color temperature adjustment (-100 to 100, default 0)
    """
    # Build eq filter string
    filters = []

    if brightness != 0:
        filters.append(f"brightness={brightness}")

    if contrast != 1.0:
        filters.append(f"contrast={contrast}")

    if saturation != 1.0:
        filters.append(f"saturation={saturation}")

    if temperature != 0:
        # Simple temperature shift using colorbalance
        # Positive = warmer (more red/yellow), Negative = cooler (more blue)
        filters.append(f"colorbalance=rs={temperature / 100}")

    if not filters:
        # No adjustments, just copy
        args = [
            "-y",
            "-i",
            input_path,
            "-c",
            "copy",
            output_path,
        ]
    else:
        filter_str = ",".join(filters)
        args = [
            "-y",
            "-i",
            input_path,
            "-vf",
            f"eq={filter_str}",
            "-c:a",
            "copy",
            output_path,
        ]

    run_ffmpeg(args)
