"""Stage 3: Transcribe - Whisper speech-to-text."""

import json
from pathlib import Path

from scripts.utils.session import SessionManager
from scripts.core.exceptions import StageError


def run(session_id: str, workspace: str) -> dict:
    """
    Transcribe audio using Whisper.
    
    Args:
        session_id: The session identifier
        workspace: Path to workspace root
        
    Returns:
        dict with keys: transcript_file, segment_count, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)
    
    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("transcribe", f"Session '{session_id}' not found")
    
    audio_path = workspace_path / "audio" / session_id / "master.wav"
    
    if not audio_path.exists():
        raise StageError("transcribe", f"Audio not found: {audio_path}")
    
    transcript_dir = workspace_path / "transcripts" / session_id
    transcript_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        from faster_whisper import WhisperModel
        
        model = WhisperModel(
            "large-v2",
            device="cpu",
            compute_type="int8"
        )
        
        segments, info = model.transcribe(
            str(audio_path),
            language="es",
            word_timestamps=True,
            vad_filter=True,
        )
        
        segments_list = []
        for seg in segments:
            segments_list.append({
                "id": len(segments_list),
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "words": [
                    {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                    for w in (seg.words or [])
                ],
                "avg_logprob": seg.avg_logprob,
                "no_speech_prob": seg.no_speech_prob,
            })
        
        raw_file = transcript_dir / "raw.json"
        raw_file.write_text(json.dumps({
            "language": "es",
            "duration": info.duration or 0,
            "segments": segments_list,
        }, indent=2))
        
        cleaned = [s for s in segments_list if s["no_speech_prob"] < 0.6]
        segments_file = transcript_dir / "segments.json"
        segments_file.write_text(json.dumps(cleaned, indent=2))
        
        session.status = "transcribed"
        session_manager.save_session(session)
        
        return {
            "transcript_file": str(segments_file),
            "segment_count": len(cleaned),
            "session_status": "transcribed",
        }
        
    except Exception as e:
        raise StageError("transcribe", f"Whisper transcription failed: {e}")
