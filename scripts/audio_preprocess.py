"""
Audio preprocessing module.
Runs before silence detection to clean audio.
Input:  audio/{session_id}/master.wav
Output: audio/{session_id}/master_clean.wav

Uses AudioEngineer to diagnose recording and build adaptive filter chain.
"""

from pathlib import Path
from scripts.domain.audio_engineer import AudioEngineer
from scripts.config import get_config


def run(session_id: str, mode: str = "default", workspace: str = "."):
    config = get_config(workspace)
    audio_engineer = AudioEngineer(config)
    
    input_wav = Path(workspace) / "audio" / session_id / "master.wav"
    output_wav = Path(workspace) / "audio" / session_id / "master_clean.wav"
    
    if not input_wav.exists():
        raise FileNotFoundError(f"Input audio not found: {input_wav}")
    
    target = "longform"
    if mode == "shorts":
        target = "shorts"
    
    report = audio_engineer.preprocess(input_wav, output_wav, target)
    
    _write_report(session_id, mode, report, workspace)
    
    for error in report.get("errors", []):
        print(f"[preprocess] ERROR: {error}")
    
    for warning in report.get("warnings", []):
        print(f"[preprocess] WARNING: {warning}")
    
    before = report.get("before", {})
    after = report.get("after", {})
    print(f"[preprocess] RMS: {before.get('rms_db', 0):.1f}dB → {after.get('rms_db', 0):.1f}dB")
    print(f"[preprocess] Noise floor: {before.get('noise_floor_db', 0):.1f}dB → {after.get('noise_floor_db', 0):.1f}dB")
    print(f"[preprocess] SNR: {before.get('snr_estimate_db', 0):.1f}dB → {after.get('snr_estimate_db', 0):.1f}dB")


def _write_report(session_id: str, mode: str, report: dict, workspace: str):
    import json
    
    report_data = {
        "session_id": session_id,
        "mode": mode,
        "target": report.get("target"),
        "before": report.get("before"),
        "after": report.get("after"),
        "filter_chain": report.get("filter_chain"),
        "errors": report.get("errors", []),
        "warnings": report.get("warnings", [])
    }
    
    analysis_dir = Path(workspace) / "analysis" / session_id
    analysis_dir.mkdir(parents=True, exist_ok=True)
    (analysis_dir / "preprocess_report.json").write_text(json.dumps(report_data, indent=2))
