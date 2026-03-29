import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class VideoFile:
    path: str
    name: str
    size_mb: float


def scan_directory(path: str, extensions: list[str] = None) -> list[VideoFile]:
    if extensions is None:
        extensions = [".mp4", ".mkv", ".avi", ".mov", ".webm"]
    
    videos = []
    try:
        for entry in sorted(Path(path).iterdir()):
            if entry.is_file() and entry.suffix.lower() in extensions:
                size_mb = entry.stat().st_size / (1024 * 1024)
                videos.append(VideoFile(
                    path=str(entry),
                    name=entry.name,
                    size_mb=round(size_mb, 1)
                ))
    except Exception:
        pass
    return videos


def find_videos_in_mount(mount_path: str) -> list[VideoFile]:
    if not Path(mount_path).exists():
        return []
    return scan_directory(mount_path)


def select_video(videos: list[VideoFile], exclude: Optional[str] = None) -> list[VideoFile]:
    filtered = [v for v in videos if exclude is None or v.path != exclude]
    return filtered


def validate_video(path: str) -> bool:
    p = Path(path)
    return p.exists() and p.suffix.lower() in [".mp4", ".mkv", ".avi", ".mov", ".webm"]


def browse_directory(base_path: str, show_hidden: bool = False) -> tuple[list[tuple[str, str, bool]], str]:
    """
    Returns list of (display, path, is_dir) tuples for intuitive browsing.
    """
    current = Path(base_path)
    if not current.exists():
        current = Path.home()
    
    entries = []
    try:
        for entry in sorted(current.iterdir()):
            # Skip hidden files/dirs unless explicitly requested
            if not show_hidden and entry.name.startswith("."):
                continue
            
            if entry.is_dir():
                entries.append((f"[DIR] {entry.name}/", str(entry), True))
            elif entry.is_file() and entry.suffix.lower() in [".mp4", ".mkv", ".avi", ".mov", ".webm"]:
                size_mb = entry.stat().st_size / (1024 * 1024)
                entries.append((f"{entry.name} ({size_mb:.1f} MB)", str(entry), False))
    except Exception:
        pass
    
    return entries, str(current)


def browse_directory_simple(base_path: str) -> tuple[list[str], str]:
    """Legacy function for compatibility - converts to simple string list."""
    entries_with_meta, current = browse_directory(base_path)
    return [e[0] for e in entries_with_meta], current


def navigate_to_parent(current: str) -> str:
    parent = Path(current).parent
    return str(parent)


def is_video_file(name: str) -> bool:
    return any(name.lower().endswith(ext) for ext in [".mp4", ".mkv", ".avi", ".mov", ".webm"])
