"""Stage 4: Analyze - Silence, filler, and energy detection."""

import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from scripts.core.exceptions import StageError
from scripts.utils import ffmpeg
from scripts.utils.session import SessionManager


def run(session_id: str, workspace: str) -> dict:
    """
    Analyze audio: silence detection, filler detection, energy analysis.

    Args:
        session_id: The session identifier
        workspace: Path to workspace root

    Returns:
        dict with keys: silence_map, filler_map, energy_map, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)

    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("analyze", f"Session '{session_id}' not found")

    audio_path = workspace_path / "output" / "audio" / session_id / "master_voice.wav"
    if not audio_path.exists():
        audio_path = workspace_path / "output" / "audio" / session_id / "master.wav"

    # Analysis goes in output/analysis
    analysis_dir = workspace_path / "output" / "analysis" / session_id
    analysis_dir.mkdir(parents=True, exist_ok=True)

    if not audio_path.exists():
        raise StageError("analyze", f"Audio not found: {audio_path}")

    filler_words = _load_filler_words(workspace_path)
    transcript = _load_transcript(workspace_path, session_id)

    silence_map = _detect_silence(audio_path)
    (analysis_dir / "silence_map.json").write_text(json.dumps(silence_map, indent=2))

    filler_map = _detect_fillers(transcript, filler_words)
    (analysis_dir / "filler_map.json").write_text(json.dumps(filler_map, indent=2))

    try:
        energy_map = _analyze_energy(audio_path)
        (analysis_dir / "energy_map.json").write_text(json.dumps(energy_map, indent=2))
    except Exception:
        energy_map = {"windows": [], "low_energy_intervals": []}

    session.status = "analyzed"
    session_manager.save_session(session)

    return {
        "silence_map": str(analysis_dir / "silence_map.json"),
        "filler_map": str(analysis_dir / "filler_map.json"),
        "energy_map": str(analysis_dir / "energy_map.json"),
        "session_status": "analyzed",
    }


def _load_filler_words(workspace_path: Path) -> list[str]:
    filler_file = workspace_path / "config" / "filler_words_es.txt"
    if filler_file.exists():
        return [w.strip().lower() for w in filler_file.read_text().splitlines() if w.strip()]
    return []


def _load_transcript(workspace_path: Path, session_id: str) -> list:
    transcript_file = workspace_path / "output" / "transcripts" / session_id / "segments.json"
    if transcript_file.exists():
        return json.loads(transcript_file.read_text())
    return []


def _detect_silence(audio_path: Path) -> dict:
    ff = ffmpeg
    ffmpeg_path = ff.get_ffmpeg_path()

    noise_result = subprocess.run(
        [
            ffmpeg_path,
            "-i",
            str(audio_path),
            "-af",
            "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )

    rms_values = []
    for line in noise_result.stderr.splitlines():
        if "Overall.RMS_level=" in line:
            try:
                val = line.split("=")[-1].strip()
                if val != "nan":
                    rms_values.append(float(val))
            except (ValueError, IndexError):
                pass

    if rms_values:
        noise_floor = min(rms_values)
    else:
        noise_floor = -60.0

    silence_threshold = noise_floor + 8

    result = subprocess.run(
        [
            ffmpeg_path,
            "-i",
            str(audio_path),
            "-af",
            f"silencedetect=noise={silence_threshold:.1f}dB:d=0.2",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )

    silence_intervals = []
    in_silence = False
    silence_start_time = 0.0

    for line in result.stderr.split("\n"):
        if "silencedetect" in line and "silence_start" in line:
            silence_start_time = float(line.split("silence_start: ")[1].split()[0])
            in_silence = True
        elif in_silence and "silence_end" in line:
            parts = line.split("silence_end: ")[1].split()
            end = float(parts[0])
            duration = end - silence_start_time
            silence_type = (
                "leading"
                if not silence_intervals and silence_start_time < 1.0
                else "between_sentences"
            )
            silence_intervals.append(
                {
                    "start": silence_start_time,
                    "end": end,
                    "duration": duration,
                    "type": silence_type,
                }
            )
            in_silence = False

    total_silence = sum(s["duration"] for s in silence_intervals)

    return {
        "total_silence_s": total_silence,
        "silence_intervals": silence_intervals,
        "potential_time_saved_s": total_silence * 0.8,
    }


def _detect_fillers(transcript: list, filler_words: list[str]) -> dict:
    fillers_found = []
    for seg in transcript:
        for word_data in seg.get("words", []):
            word = word_data.get("word", "").lower().strip(".,!?")
            if word in filler_words:
                fillers_found.append(
                    {
                        "word": word_data.get("word", ""),
                        "start": word_data.get("start", 0),
                        "end": word_data.get("end", 0),
                        "segment_id": seg.get("id", 0),
                        "confidence": word_data.get("probability", 0.9),
                    }
                )

    return {
        "total_fillers": len(fillers_found),
        "filler_rate_per_minute": len(fillers_found) / 10,
        "fillers": fillers_found,
    }


def _analyze_energy(audio_path: Path) -> dict:
    sr, audio = wavfile.read(str(audio_path))
    audio = audio.astype(np.float32) / 32768.0

    window_size = int(sr * 0.5)
    windows = []
    for i in range(0, len(audio) - window_size, window_size):
        window = audio[i : i + window_size]
        rms = float(np.sqrt(np.mean(window**2)))
        windows.append(
            {
                "t": float(i / sr),
                "rms_norm": min(rms * 10, 1.0),
                "low_energy": rms < 0.03,
            }
        )

    return {"windows": windows, "low_energy_intervals": []}
