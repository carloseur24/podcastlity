"""
AudioEngineer - Sound engineer skill for voice audio analysis and adaptive FFmpeg filter chain.
Implements: diagnose → build_filter_chain → validate
"""

import subprocess
import math
import json
from pathlib import Path
from typing import Any

import imageio_ffmpeg

from scripts.config import ConfigProvider, get_config, reset_config


def _get_ffmpeg_path() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


class AudioEngineer:
    def __init__(self, config: ConfigProvider | None = None):
        self._config = config or get_config()
    
    def diagnose(self, input_wav: Path) -> dict[str, Any]:
        """
        Step 1: Diagnose the recording.
        Measure RMS, peak, noise floor, and frequency bands for problem detection.
        
        Returns diagnosis dict with:
        - rms_db: Overall RMS level in dB
        - peak_db: Peak level in dB
        - noise_floor_db: Measured noise floor
        - headroom_db: Peak - RMS
        - snr_estimate_db: RMS - noise floor
        - muffled_ratio: Ratio of lows to highs (for underwater detection)
        - problems_detected: List of identified problems
        - problems_not_present: List of confirmed absent problems
        """
        ffmpeg_path = _get_ffmpeg_path()
        
        result = subprocess.run(
            [ffmpeg_path, "-i", str(input_wav),
             "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:key=lavfi.astats.Overall.Peak_level:key=lavfi.astats.Overall.Noise_floor",
             "-f", "null", "-"],
            capture_output=True,
            text=True
        )
        
        rms_db = None
        peak_db = None
        noise_floor_db = None
        
        for line in result.stderr.splitlines():
            if "RMS level dB:" in line:
                try:
                    rms_db = float(line.split(":")[-1].strip())
                except (ValueError, IndexError):
                    pass
            elif "Peak level dB:" in line:
                try:
                    peak_db = float(line.split(":")[-1].strip())
                except (ValueError, IndexError):
                    pass
            elif "Noise floor dB:" in line:
                try:
                    val = line.split(":")[-1].strip()
                    if val != "nan":
                        noise_floor_db = float(val)
                except (ValueError, IndexError):
                    pass
        
        if rms_db is None or noise_floor_db is None:
            return {
                "rms_db": -30.0,
                "peak_db": -6.0,
                "noise_floor_db": -50.0,
                "headroom_db": 24.0,
                "snr_estimate_db": 20.0,
                "muffled_ratio": 1.0,
                "problems_detected": [],
                "problems_not_present": [],
                "environment_guess": "unknown"
            }
        
        headroom_db = peak_db - rms_db if peak_db else 0
        snr_estimate = rms_db - noise_floor_db if noise_floor_db else 0
        
        muffled_ratio = self._analyze_frequency_bands(input_wav, ffmpeg_path)
        
        problems_detected = []
        problems_not_present = []
        
        diag_config = self._config.get_diagnostic_settings()
        
        if noise_floor_db > diag_config.get("noise_moderate_below", -40):
            problems_detected.append("heavy_noise")
        elif noise_floor_db > diag_config.get("noise_mild_below", -50):
            problems_detected.append("moderate_noise")
        elif noise_floor_db > diag_config.get("noise_clean_below", -65):
            problems_detected.append("mild_noise")
        else:
            problems_not_present.append("noise")
        
        if headroom_db < 3:
            problems_detected.append("low_headroom")
        else:
            problems_not_present.append("clipping")
        
        if snr_estimate < diag_config.get("snr_minimum", 18):
            problems_detected.append("low_snr")
        
        if muffled_ratio > diag_config.get("muffled_ratio_threshold", 2.0):
            problems_detected.append("muffled")
        
        if rms_db < diag_config.get("quiet_voice_rms", -25):
            if snr_estimate > diag_config.get("snr_minimum", 18):
                problems_detected.append("quiet_voice")
        
        if noise_floor_db > -45 and muffled_ratio > 1.5:
            problems_detected.append("underwater")
        
        environment = "quiet_room"
        if noise_floor_db > -40:
            environment = "noisy_environment"
        elif noise_floor_db > -50:
            environment = "moderate_room"
        
        return {
            "rms_db": rms_db,
            "peak_db": peak_db,
            "noise_floor_db": noise_floor_db,
            "headroom_db": headroom_db,
            "snr_estimate_db": snr_estimate,
            "muffled_ratio": muffled_ratio,
            "problems_detected": problems_detected,
            "problems_not_present": problems_not_present,
            "environment_guess": environment
        }
    
    def _analyze_frequency_bands(self, input_wav: Path, ffmpeg_path: str) -> float:
        """
        Analyze frequency bands to detect muffled/underwater recordings.
        Compares energy in lows (100-500Hz) vs highs (2-5kHz).
        """
        low_result = subprocess.run(
            [ffmpeg_path, "-i", str(input_wav),
             "-af", "highpass=f=100:highpass=f=500,silencedetect=noise=-60dB:d=0.1",
             "-f", "null", "-"],
            capture_output=True,
            text=True
        )
        
        high_result = subprocess.run(
            [ffmpeg_path, "-i", str(input_wav),
             "-af", "lowpass=f=2000:lowpass=f=5000,silencedetect=noise=-60dB:d=0.1",
             "-f", "null", "-"],
            capture_output=True,
            text=True
        )
        
        low_db = -50
        high_db = -50
        
        for line in low_result.stderr.splitlines():
            if "RMS dB" in line:
                try:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        val = parts[-1].strip().split()[0]
                        low_db = float(val)
                except (ValueError, IndexError):
                    pass
        
        for line in high_result.stderr.splitlines():
            if "RMS dB" in line:
                try:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        val = parts[-1].strip().split()[0]
                        high_db = float(val)
                except (ValueError, IndexError):
                    pass
        
        if high_db < -60:
            return 2.0
        
        return low_db - high_db
    
    def build_filter_chain(self, diagnosis: dict[str, Any], target: str = "analysis") -> str:
        """
        Step 2: Build adaptive filter chain based on diagnosis.
        
        Order (professional podcast chain):
        1. highpass (remove rumble)
        2. afftdn (spectral denoising)
        3. agate (noise gate) - BEFORE compressor to avoid pumping
        4. equalizer (grave + mud_cut + presence) - professional warmth
        5. compressor (dynamics)
        6. loudnorm (always last, platform-safe -14 LUFS)
        
        Args:
            diagnosis: Output from diagnose()
            target: "shorts", "longform", or "analysis"
        
        Returns:
            FFmpeg filter chain string
        """
        filters = []
        problems = diagnosis.get("problems_detected", [])
        
        hp_config = self._config.get_highpass_settings()
        
        if "muffled" in problems or "underwater" in problems:
            hp_freq = hp_config.get("muffled_voice_freq", 120)
        elif "heavy_noise" in problems:
            hp_freq = hp_config.get("aggressive_freq", 100)
        else:
            hp_freq = hp_config.get("default_freq", 80)
        
        hp_poles = hp_config.get("poles", 2)
        filters.append(f"highpass=f={hp_freq}:poles={hp_poles}")
        
        nf = diagnosis.get("noise_floor_db", -50)
        if nf > -65:
            afftdn_config = self._config.get_afftdn_settings()
            if nf > -40:
                nr = afftdn_config.get("nr_heavy", 35)
            elif nf > -50:
                nr = afftdn_config.get("nr_moderate", 25)
            else:
                nr = afftdn_config.get("nr_mild", 15)
            
            if "heavy_noise" in problems:
                nr = min(nr + 5, afftdn_config.get("nr_max_voice", 40))
            
            nf_offset = afftdn_config.get("noise_floor_offset", 5)
            filters.append(f"afftdn=nr={nr}:nf={nf + nf_offset}")
        
        if nf > -50:
            agate_config = self._config.get_agate_settings()
            above_floor = agate_config.get("above_floor_db", 6)
            linear_threshold = 10 ** ((nf + above_floor) / 20)
            ratio = agate_config.get("ratio_heavy", 16) if nf > -40 else agate_config.get("ratio_mild", 8)
            attack = agate_config.get("attack_ms", 10)
            release = agate_config.get("release_ms", 60)
            filters.append(f"agate=threshold={linear_threshold:.4f}:ratio={ratio}:attack={attack}:release={release}")
        
        eq_config = self._config.get_eq_settings()
        
        grave = eq_config.get("grave", {})
        filters.append(f"equalizer=f={grave.get('freq', 160)}:t=q:w={grave.get('width', 0.8)}:g={grave.get('gain', 3)}")
        
        mud_cut = eq_config.get("mud_cut", {})
        filters.append(f"equalizer=f={mud_cut.get('freq', 350)}:t=q:w={mud_cut.get('width', 1.2)}:g={mud_cut.get('gain', -2)}")
        
        pres = eq_config.get("presence", {})
        filters.append(f"equalizer=f={pres.get('freq', 3500)}:t=q:w={pres.get('width', 1.0)}:g={pres.get('gain', 3)}")
        
        if "muffled" in problems or "underwater" in problems:
            clarity = eq_config.get("voice_clarity", {})
            filters.append(f"equalizer=f={clarity.get('freq', 4000)}:t=q:w={clarity.get('width', 0.8)}:g={clarity.get('gain', 2)}")
        
        if "proximity_effect" in problems:
            prox = eq_config.get("proximity", {})
            filters.append(f"equalizer=f={prox.get('freq', 120)}:t=q:w={prox.get('width', 1.0)}:g={prox.get('gain', -3)}")
        
        if "boxiness" in problems:
            box = eq_config.get("boxiness", {})
            filters.append(f"equalizer=f={box.get('freq', 400)}:t=q:w={box.get('width', 1.5)}:g={box.get('gain', -2)}")
        
        if "sibilance" in problems:
            sib = eq_config.get("sibilance", {})
            filters.append(f"equalizer=f={sib.get('freq', 7000)}:t=q:w={sib.get('width', 1.0)}:g={sib.get('gain', -3)}")
        
        comp_config = self._config.get_compressor_settings()
        comp_threshold_linear = 10 ** (comp_config.get("threshold_db", -25) / 20)
        comp_ratio = comp_config.get("ratio", 4)
        comp_attack = comp_config.get("attack_ms", 20)
        comp_release = comp_config.get("release_ms", 250)
        comp_makeup = comp_config.get("makeup_db", 4)
        comp_knee = comp_config.get("knee", 0.5)
        
        if "quiet_voice" in problems:
            comp_makeup = comp_makeup + 4
        
        if "heavy_noise" in problems or "moderate_noise" in problems:
            comp_threshold_linear = comp_threshold_linear * 1.5
        
        filters.append(f"acompressor=threshold={comp_threshold_linear:.4f}:ratio={comp_ratio}:attack={comp_attack}:release={comp_release}:makeup={comp_makeup}:knee={comp_knee}")
        
        loudnorm_targets = self._config.get_loudnorm_targets(target)
        filters.append(f"loudnorm=I={loudnorm_targets.get('I', -14)}:TP={loudnorm_targets.get('TP', -1)}:LRA={loudnorm_targets.get('LRA', 9)}")
        
        return ",".join(filters)
    
    def validate(self, before_report: dict[str, Any], after_report: dict[str, Any]) -> tuple[list[str], list[str]]:
        """
        Step 3: Quality gates - validate preprocessing didn't make things worse.
        
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        diag_config = self._config.get_diagnostic_settings()
        
        noise_before = before_report.get("noise_floor_db", -50)
        noise_after = after_report.get("noise_floor_db", -50)
        
        if noise_after > noise_before:
            errors.append(f"FAIL: noise floor increased from {noise_before:.1f}dB to {noise_after:.1f}dB")
        
        rms_before = before_report.get("rms_db", -30)
        rms_after = after_report.get("rms_db", -30)
        rms_delta = abs(rms_after - rms_before)
        
        if rms_delta > diag_config.get("rms_delta_max", 12):
            errors.append(f"FAIL: RMS changed by {rms_delta:.1f}dB — voice likely damaged")
        
        if noise_after > diag_config.get("noise_floor_warn", -48):
            warnings.append(f"WARN: noise floor still {noise_after:.1f}dB — try --mode heavy")
        
        snr_after = rms_after - noise_after
        if snr_after < diag_config.get("snr_minimum", 18):
            warnings.append(f"WARN: SNR is {snr_after:.1f}dB — silence detection may be unreliable")
        
        return errors, warnings
    
    def preprocess(self, input_wav: Path, output_wav: Path, target: str = "analysis") -> dict[str, Any]:
        """
        Main entry point: diagnose → build filter chain → apply → validate.
        
        Args:
            input_wav: Input WAV file path
            output_wav: Output WAV file path
            target: "shorts", "longform", or "analysis"
        
        Returns:
            Report dict with diagnosis, filter chain, validation results
        """
        if not input_wav.exists():
            raise FileNotFoundError(f"Input audio not found: {input_wav}")
        
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        
        before_diagnosis = self.diagnose(input_wav)
        
        filter_chain = self.build_filter_chain(before_diagnosis, target)
        
        ffmpeg_path = _get_ffmpeg_path()
        
        mono_wav = output_wav.with_suffix('.mono.wav')
        subprocess.run(
            [ffmpeg_path, "-y", "-i", str(input_wav),
             "-af", filter_chain,
             "-ar", "16000", "-ac", "1",
             str(mono_wav)],
            check=True
        )
        
        subprocess.run(
            [ffmpeg_path, "-y", "-i", str(mono_wav),
             "-af", "aformat=channel_layouts=stereo",
             "-ac", "2",
             str(output_wav)],
            check=True
        )
        mono_wav.unlink(missing_ok=True)
        
        after_diagnosis = self.diagnose(output_wav)
        
        errors, warnings = self.validate(before_diagnosis, after_diagnosis)
        
        return {
            "input_path": str(input_wav),
            "output_path": str(output_wav),
            "target": target,
            "before": before_diagnosis,
            "after": after_diagnosis,
            "filter_chain": filter_chain,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_silence_threshold(self, processed_wav: Path) -> float:
        """
        After preprocessing, measure new noise floor and calculate silence threshold.
        threshold = noise_floor + 8dB
        """
        diagnosis = self.diagnose(processed_wav)
        noise_floor = diagnosis.get("noise_floor_db", -50)
        return noise_floor + 8
