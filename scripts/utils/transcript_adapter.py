"""Transcript adapter - converts pipeline transcript to Remotion Caption format."""

import json
from pathlib import Path


def load_transcript(workspace: str, session_id: str) -> list[dict]:
    """
    Load transcript from pipeline format.

    Pipeline format:
    [
        {
            "id": 0,
            "start": 15.58,
            "end": 21.7,
            "text": " Estamos en carnaval...",
            "words": [
                {"word": "...", "start": 15.58, "end": 16.22, "probability": 0.99}
            ],
            "avg_logprob": -0.26,
            "no_speech_prob": 0.29
        }
    ]

    Returns:
        List of transcript segments with word-level timestamps
    """
    workspace_path = Path(workspace)
    transcript_file = workspace_path / "output" / "transcripts" / session_id / "segments.json"

    if not transcript_file.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_file}")

    return json.loads(transcript_file.read_text())


def convert_to_remotion_captions(transcript: list[dict]) -> list[dict]:
    """
    Convert pipeline transcript to Remotion Caption format.

    Remotion Caption format:
    [
        {
            "text": "word",
            "startMs": 15580,
            "endMs": 21700,
            "timestampMs": 18640,
            "confidence": 0.99
        }
    ]

    Note: Remotion uses milliseconds, pipeline uses seconds.
    """
    captions = []

    for segment in transcript:
        words = segment.get("words", [])

        if not words:
            # No word-level timestamps, use segment-level
            captions.append(
                {
                    "text": segment.get("text", "").strip(),
                    "startMs": int(segment.get("start", 0) * 1000),
                    "endMs": int(segment.get("end", 0) * 1000),
                    "timestampMs": int(
                        (segment.get("start", 0) + segment.get("end", 0)) / 2 * 1000
                    ),
                    "confidence": 1.0 - segment.get("no_speech_prob", 0),
                }
            )
        else:
            # Use word-level timestamps for kinetic animations
            for word in words:
                captions.append(
                    {
                        "text": word.get("word", "").strip(),
                        "startMs": int(word.get("start", 0) * 1000),
                        "endMs": int(word.get("end", 0) * 1000),
                        "timestampMs": int((word.get("start", 0) + word.get("end", 0)) / 2 * 1000),
                        "confidence": word.get("probability", 1.0),
                    }
                )

    return captions


def convert_to_remotion_captions_simple(transcript: list[dict]) -> list[dict]:
    """
    Convert pipeline transcript to Remotion Caption format (segment-level).

    Uses full segment as one caption - simpler but less precise timing.
    Good for minimal_fade preset.
    """
    captions = []

    for segment in transcript:
        captions.append(
            {
                "text": segment.get("text", "").strip(),
                "startMs": int(segment.get("start", 0) * 1000),
                "endMs": int(segment.get("end", 0) * 1000),
                "timestampMs": int((segment.get("start", 0) + segment.get("end", 0)) / 2 * 1000),
                "confidence": 1.0 - segment.get("no_speech_prob", 0),
            }
        )

    return captions


def convert_to_srt(transcript: list[dict]) -> str:
    """
    Convert pipeline transcript to SRT format for FFmpeg.

    SRT format:
    1
    00:00:15,580 --> 00:00:21,700
    We're at the carnival...

    """
    srt_lines = []

    for i, segment in enumerate(transcript, 1):
        start_time = _format_srt_time(segment.get("start", 0))
        end_time = _format_srt_time(segment.get("end", 0))
        text = segment.get("text", "").strip()

        srt_lines.append(f"{i}")
        srt_lines.append(f"{start_time} --> {end_time}")
        srt_lines.append(text)
        srt_lines.append("")  # Empty line between entries

    return "\n".join(srt_lines)


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT time format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def load_subtitle_preset(workspace: str, preset_name: str) -> dict:
    """Load subtitle preset configuration."""
    workspace_path = Path(workspace)
    presets_file = workspace_path / "config" / "subtitle_presets.json"

    if not presets_file.exists():
        raise FileNotFoundError(f"Presets not found: {presets_file}")

    presets_config = json.loads(presets_file.read_text())
    presets = presets_config.get("presets", {})

    if preset_name not in presets:
        raise ValueError(f"Preset '{preset_name}' not found. Available: {list(presets.keys())}")

    return presets[preset_name]


def get_preset_for_profile(workspace: str, profile: str) -> tuple[str, dict]:
    """Get preset name and config for a given profile."""
    workspace_path = Path(workspace)
    presets_file = workspace_path / "config" / "subtitle_presets.json"

    if not presets_file.exists():
        raise FileNotFoundError(f"Presets not found: {presets_file}")

    presets_config = json.loads(presets_file.read_text())
    profiles = presets_config.get("profiles", {})

    preset_name = profiles.get(profile, "minimal_fade")
    presets = presets_config.get("presets", {})
    preset_config = presets.get(preset_name, presets.get("minimal_fade"))

    return preset_name, preset_config


def export_captions_json(captions: list[dict], output_path: str) -> None:
    """Export captions to JSON file for Remotion."""
    with open(output_path, "w") as f:
        json.dump(captions, f, indent=2)


def export_srt(captions: list[dict], output_path: str) -> None:
    """Export captions to SRT format."""
    with open(output_path, "w") as f:
        for i, caption in enumerate(captions, 1):
            start = format_srt_time(caption["startMs"])
            end = format_srt_time(caption["endMs"])
            text = caption["text"]

            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")


def format_srt_time(ms: int) -> str:
    """Format milliseconds to SRT time format (HH:MM:SS,mmm)."""
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    millis = ms % 1000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
