"""Type stubs for scripts.utils.ffmpeg module."""

from typing import Optional

def get_duration(video_path: str) -> float: ...
def get_resolution(video_path: str) -> tuple[int, int]: ...
def get_frame_count(video_path: str) -> int: ...
def get_fps(video_path: str) -> float: ...
def get_bitrate(video_path: str) -> int: ...
def get_codec(video_path: str) -> str: ...
def extract_audio(
    input_video: str,
    output_wav: str,
    mono: bool = ...,
    sample_rate: int = ...,
) -> None: ...
def create_proxy(
    input_video: str,
    output_proxy: str,
    width: Optional[int] = ...,
    height: Optional[int] = ...,
    codec: str = ...,
    crf: int = ...,
) -> None: ...
def trim_video(
    input_video: str,
    output_video: str,
    start: float,
    end: float,
) -> None: ...
def concatenate_videos(
    input_videos: list[str],
    output_video: str,
) -> None: ...
def apply_loudnorm(
    input_wav: str,
    output_wav: str,
    profile: str = ...,
) -> None: ...
def export_full_quality(
    input_video: str,
    output_video: str,
) -> None: ...
def replace_audio(
    input_video: str,
    input_audio: str,
    output_video: str,
    stereo_widen: bool = ...,
) -> None: ...
def convert_to_vertical(
    input_video: str,
    output_video: str,
) -> None: ...
def extract_frame(
    input_video: str,
    output_image: str,
    timestamp: float = ...,
) -> None: ...
def create_thumbnail(
    input_video: str,
    output_image: str,
    timestamp: float = ...,
    width: int = ...,
    height: int = ...,
) -> None: ...
