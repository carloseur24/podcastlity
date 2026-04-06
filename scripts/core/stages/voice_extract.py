"""Stage: VoiceExtract - Extract voice segments using Silero VAD + AI noise reduction.

Pipeline:
1. Load audio from master.wav
2. Apply ConvTasNet source separation - separates voice from noise
3. Apply Silero VAD - detects speech segments
4. Concatenate only voice segments
5. Apply configurable audio chain (highpass, EQ, compressor, limiter, loudnorm)
"""

import json
import subprocess
from pathlib import Path

import noisereduce as nr
import numpy as np
import pyrnnoise
import torch
from scipy.io import wavfile

from scripts.config import ConfigProvider


def build_audio_filter_chain(audio_config: dict) -> str:
    """
    Build FFmpeg filter chain based on audio processing configuration.

    Args:
        audio_config: Dictionary with filter settings from config

    Returns:
        FFmpeg filter chain string
    """
    filters = []

    # 1. Highpass - Remove low rumble
    hp = audio_config.get("highpass", {})
    if hp.get("enabled", True):
        freq = hp.get("frequency", 80)
        poles = hp.get("poles", 2)
        filters.append(f"highpass=f={freq}:poles={poles}")

    # 2. EQ Boxiness - Remove boxy sound
    eq = audio_config.get("eq_boxiness", {})
    if eq.get("enabled", True):
        freq = eq.get("frequency", 450)
        gain = eq.get("gain", -3)
        width = eq.get("width", 300)
        filters.append(f"equalizer=f={freq}:g={gain}:w={width}")

    # 3. Compressor - Voice compression
    comp = audio_config.get("compressor", {})
    if comp.get("enabled", True):
        threshold = comp.get("threshold", -24)
        ratio = comp.get("ratio", 3.5)
        attack = comp.get("attack", 5)
        release = comp.get("release", 100)
        makeup = comp.get("makeup", 4)
        knee = comp.get("knee", 1)
        filters.append(
            f"acompressor=threshold={threshold}dB:ratio={ratio}:attack={attack}:release={release}:makeup={makeup}dB:knee={knee}"
        )

    # 4. High Shelf - Add air/crispness
    hs = audio_config.get("highshelf", {})
    if hs.get("enabled", True):
        freq = hs.get("frequency", 10000)
        gain = hs.get("gain", 3)
        filters.append(f"highshelf=f={freq}:g={gain}")

    # 5. Limiter - Prevent clipping
    lim = audio_config.get("limiter", {})
    if lim.get("enabled", True):
        ceiling = lim.get("ceiling", -1)
        filters.append(f"alimiter=limit={ceiling}dB")

    # 6. Loudnorm - Volume normalization (always last)
    ln = audio_config.get("loudnorm", {})
    if ln.get("enabled", True):
        i_val = ln.get("I", -16)
        tp = ln.get("TP", -1.5)
        lra = ln.get("LRA", 11)
        filters.append(f"loudnorm=I={i_val}:TP={tp}:LRA={lra}")

    return ",".join(filters)


from silero_vad import get_speech_timestamps, load_silero_vad

from scripts.config import ConfigProvider
from scripts.core.exceptions import StageError
from scripts.utils import ffmpeg
from scripts.utils.session import SessionManager


def _read_audio_with_scipy(audio_path: str, target_sr: int = 16000):
    """Read audio using scipy instead of torchaudio (avoids dependency issues)."""
    rate, audio = wavfile.read(audio_path)

    # Convert stereo to mono if needed
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)

    # Convert to float32 in range [-1, 1]
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    elif audio.dtype == np.int32:
        audio = audio.astype(np.float32) / 2147483648.0
    elif audio.dtype == np.uint8:
        audio = (audio.astype(np.float32) - 128) / 128.0
    else:
        audio = audio.astype(np.float32)

    # Resample if needed
    if rate != target_sr:
        from scipy.signal import resample

        num_samples = int(len(audio) * target_sr / rate)
        audio = resample(audio, num_samples)
        rate = target_sr

    # Convert to tensor format expected by Silero VAD
    audio_tensor = torch.FloatTensor(audio).unsqueeze(0)

    return audio_tensor, rate


def _apply_arnndn(input_wav: str, output_wav: str, model_path: str, mix: float) -> bool:
    """Apply arnndn AI noise reduction using FFmpeg."""
    ffmpeg_path = ffmpeg.get_ffmpeg_path()

    # Build filter: arnndn with custom model + highpass + loudnorm
    filter_chain = (
        f"arnndn=model_path={model_path}:mix={mix},highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11"
    )

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        input_wav,
        "-af",
        filter_chain,
        "-ac",
        "1",  # Mono output
        "-ar",
        "48000",
        output_wav,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"[voice_extract] arnndn warning: {result.stderr}")
            # Fall back to just highpass + loudnorm if arnndn fails
            return False
        return True
    except Exception as e:
        print(f"[voice_extract] arnndn error: {e}")
        return False


def _apply_podcast_chain(input_wav: str, output_wav: str, audio_config: dict | None = None) -> bool:
    """
    Apply professional podcast audio chain with configurable filters.

    The filter chain is built dynamically based on audio_config:
    1. highpass - remove low rumble
    2. eq_boxiness - remove "boxy" sound
    3. compressor - voice compression
    4. highshelf - add "air" and crispness
    5. limiter - prevent clipping
    6. loudnorm - volume normalization

    Args:
        input_wav: Input audio file path
        output_wav: Output audio file path
        audio_config: Optional audio processing config dict. If None, uses defaults.
    """
    ffmpeg_path = "/usr/bin/ffmpeg"

    # Use provided config or load defaults
    if audio_config is None:
        config_provider = ConfigProvider(".")
        audio_config = config_provider.get_audio_processing_config()

    # Build filter chain from config
    filter_chain = build_audio_filter_chain(audio_config)

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        input_wav,
        "-af",
        filter_chain,
        "-ac",
        "1",
        "-ar",
        "48000",
        output_wav,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
            # Extract loudnorm target for log message
            ln = audio_config.get("loudnorm", {})
            target_lufs = ln.get("I", -16)
            print(
                f"[voice_extract] Applied podcast chain: HPF(80Hz) + BellCut(450Hz,-3dB) + Compressor(threshold=-24dB,ratio=3.5) + AirShelf(10kHz,+3dB) + Limiter(-1dB) + loudnorm({target_lufs}LUFS)"
            )
            return True
        else:
            print(f"[voice_extract] Podcast chain warning: {result.stderr[:200]}")
            # Fall back to simpler chain
            return _apply_highpass_and_loudnorm_simple(input_wav, output_wav)
    except Exception as e:
        print(f"[voice_extract] Podcast chain error: {e}")
        return False


def _apply_highpass_and_loudnorm_simple(input_wav: str, output_wav: str) -> bool:
    """Simple fallback: highpass + loudnorm."""
    ffmpeg_path = "/usr/bin/ffmpeg"

    filter_chain = "highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11"

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        input_wav,
        "-af",
        filter_chain,
        "-ac",
        "1",
        "-ar",
        "48000",
        output_wav,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        print(f"[voice_extract] highpass+loudnorm error: {e}")
        return False


def _apply_arnndn_system(input_wav: str, output_wav: str) -> bool:
    """
    Apply arnndn AI noise reduction using system FFmpeg.

    Uses the RNNoise-based filter built into FFmpeg for voice denoising.
    """
    ffmpeg_path = "/usr/bin/ffmpeg"

    # Build filter chain: arnndn + highpass + loudnorm
    # mix=0.85 balances noise reduction with voice quality
    filter_chain = (
        "arnndn=model_path=/usr/share/ffmpeg/rnnoise models/model.bin:mix=0.85,"
        "highpass=f=80,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        input_wav,
        "-af",
        filter_chain,
        "-ac",
        "1",
        "-ar",
        "48000",
        output_wav,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"[voice_extract] arnndn warning: {result.stderr[:500]}")
            return False
        return True
    except Exception as e:
        print(f"[voice_extract] arnndn error: {e}")
        return False


def _apply_dialogue_enhance(input_wav: str, output_wav: str) -> bool:
    """
    Apply dialoguenhance using system FFmpeg.

    This is the EXACT filter Adobe Podcast uses! It enhances speech quality
    and reduces background noise simultaneously.
    """
    ffmpeg_path = "/usr/bin/ffmpeg"

    # dialoguenhance: model=0 is default, helps enhance dialog/speech
    # Combined with arnndn for best results
    filter_chain = (
        "dialoguenhance=model=0:mix=0.8,arnndn=mix=0.85,highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11"
    )

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        input_wav,
        "-af",
        filter_chain,
        "-ac",
        "1",
        "-ar",
        "48000",
        output_wav,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"[voice_extract] dialoguenhance warning: {result.stderr[:500]}")
            return False
        return True
    except Exception as e:
        print(f"[voice_extract] dialoguenhance error: {e}")
        return False
        return False


def _apply_spectral_noise_reduction(input_wav: str, output_wav: str) -> bool:
    """
    Apply spectral gating noise reduction using noisereduce library.

    This uses the stationary spectral gating method which is effective for
    removing consistent background noise like AC, fans, etc.
    """
    try:
        # Read audio
        rate, audio = wavfile.read(input_wav)

        # Convert stereo to mono if needed
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Convert to float32 in range [-1, 1]
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype == np.int32:
            audio = audio.astype(np.float32) / 2147483648.0
        else:
            audio = audio.astype(np.float32)

        # Apply spectral gating noise reduction
        # stationary=True uses noise profile from the beginning of the file
        # n_std_thresh_stationary=1.5 - threshold for stationar
        reduced_audio = nr.reduce_noise(
            y=audio,
            sr=rate,
            stationary=True,
            n_fft=2048,
            n_std_thresh_stationary=1.5,
            prop_decrease=1.0,  # Full noise reduction
            time_constant_s=2.0,
            chunk_size=rate * 10,  # Process in 10s chunks to manage memory
        )

        # Convert back to int16
        reduced_audio = np.clip(reduced_audio, -1.0, 1.0)
        reduced_audio = (reduced_audio * 32767).astype(np.int16)

        # Write output
        wavfile.write(output_wav, rate, reduced_audio)

        print("[voice_extract] Applied spectral noise reduction")
        return True

    except Exception as e:
        print(f"[voice_extract] Spectral noise reduction error: {e}")
        return False


# RNNoise model instance (lazy loaded)
_rnnoise_model = None


def _get_rnnoise_model(sample_rate: int = 48000):
    """Lazy load RNNoise model."""
    global _rnnoise_model
    if _rnnoise_model is None:
        print("[voice_extract] Loading RNNoise model...")
        _rnnoise_model = pyrnnoise.RNNoise(sample_rate=sample_rate)
        print("[voice_extract] RNNoise model loaded")
    return _rnnoise_model


def _apply_rnnoise(input_wav: str, output_wav: str) -> bool:
    """
    Apply RNNoise neural noise suppression to clean voice audio.

    RNNoise uses deep learning to suppress noise while preserving voice quality.
    It's specifically designed for voice/podcast audio with background noise.
    """
    try:
        # Read audio
        original_rate, audio = wavfile.read(input_wav)
        print(f"[voice_extract] Read audio: {original_rate}Hz, {len(audio)} samples")

        # Convert stereo to mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Convert to float32 in range [-1, 1]
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        else:
            audio = audio.astype(np.float32)

        # Get RNNoise model (works at 48kHz natively)
        rnnoise = _get_rnnoise_model(sample_rate=original_rate)

        # Process in 1-second chunks
        chunk_size = original_rate  # 1 second at original sample rate
        result_chunks = []

        total_chunks = len(audio) // chunk_size + (1 if len(audio) % chunk_size else 0)
        print(f"[voice_extract] Running RNNoise ({total_chunks} chunks)...")

        for i in range(0, len(audio), chunk_size):
            chunk = audio[i : i + chunk_size]

            # Pad if needed
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)))

            # Reshape to 2D [channels, samples] - pyrnnoise expects 2D input
            # For mono audio: shape must be (1, chunk_size)
            chunk_2d = chunk.reshape(1, -1)

            # Denoise chunk - denoise_chunk yields (speech_prob, denoised_frame) tuples
            for speech_prob, denoised_frame in rnnoise.denoise_chunk(chunk_2d):
                # denoised_frame has shape (1, 480) - squeeze to 1D for concatenation
                result_chunks.append(denoised_frame.squeeze(0))

            if (i // chunk_size + 1) % 10 == 0:
                print(f"  Processed {i // chunk_size + 1}/{total_chunks}...")

        # Concatenate ALL frames and trim to original length
        result = np.concatenate(result_chunks)[: len(audio)]
        print(f"[voice_extract] RNNoise processed: {len(result)} samples")

        # Convert back to int16
        result = np.clip(result, -1.0, 1.0)
        result = (result * 32767).astype(np.int16)

        # Save
        wavfile.write(output_wav, original_rate, result)
        print(f"[voice_extract] Saved RNNoise processed audio: {output_wav}")
        return True

    except Exception as e:
        print(f"[voice_extract] RNNoise processing error: {e}")
        return False


def run(session_id: str, workspace: str) -> dict:
    """
    Extract voice segments using Silero VAD with AI noise reduction.

    Pipeline:
    1. Load audio from master.wav
    2. Apply arnndn (AI noise reduction) - removes AC, fan, background noise
    3. Apply Silero VAD - detects speech segments
    4. Concatenate only voice segments
    5. Apply highpass (80Hz) - removes low rumble
    6. Apply loudnorm (-16 LUFS) - podcast standard loudness

    Args:
        session_id: The session identifier
        workspace: Path to workspace root

    Returns:
        dict with keys: input_audio, output_audio, segments_count, total_duration, voice_duration, session_status
    """
    workspace_path = Path(workspace)
    session_manager = SessionManager(workspace)
    config = ConfigProvider(workspace)

    try:
        session = session_manager.load_session(session_id)
    except FileNotFoundError:
        raise StageError("voice_extract", f"Session '{session_id}' not found")

    # Get profile for loudness settings
    profile = session.profile or "default"
    print(f"[voice_extract] Using profile: {profile} for loudness settings")

    # Get session-specific audio processing config (or fallback to global defaults)
    audio_config = config.get_session_audio_config(workspace, session_id)
    print(f"[voice_filter] Audio processing config loaded: {len(audio_config)} filters configured")

    # Get VAD settings from config
    vad_settings = config.get_voice_extract_settings()
    min_speech_ms = vad_settings.get("min_speech_duration_ms", 2500)
    min_silence_ms = vad_settings.get("min_silence_duration_ms", 2500)

    # Get arnndn settings
    arnndn_model_path = config.get_arnndn_model_path()
    arnndn_settings = config.get_arnndn_settings()
    arnndn_mix = arnndn_settings.get("mix", 0.85)

    # Input is the master.wav from Proxies stage (output/audio)
    input_audio = workspace_path / "output" / "audio" / session_id / "master.wav"
    if not input_audio.exists():
        raise StageError("voice_extract", f"Audio not found: {input_audio}")

    # Intermediate files go in output/audio
    denoised_audio = workspace_path / "output" / "audio" / session_id / "master_denoised.wav"
    output_audio = workspace_path / "output" / "audio" / session_id / "master_voice.wav"

    try:
        # Step 1: Try system FFmpeg with dialoguenhance + arnndn (Adobe Podcast's technique!)
        print("[voice_extract] Trying system FFmpeg with dialoguenhance + arnndn...")
        ff_success = _apply_dialogue_enhance(str(input_audio), str(denoised_audio))

        if not ff_success:
            # Fall back: try arnndn only
            print("[voice_extract] dialoguenhance failed, trying arnndn only...")
            ff_success = _apply_arnndn_system(str(input_audio), str(denoised_audio))

        if not ff_success:
            # Fall back: try RNNoise Python library
            print("[voice_extract] FFmpeg filters failed, applying RNNoise Python...")
            rnnoise_success = _apply_rnnoise(str(input_audio), str(denoised_audio))

            if not rnnoise_success:
                # Final fallback: spectral noise reduction
                print("[voice_extract] RNNoise failed, applying spectral noise reduction...")
                spectral_success = _apply_spectral_noise_reduction(
                    str(input_audio), str(denoised_audio)
                )
                if not spectral_success:
                    # Ultimate fallback: just highpass + loudnorm
                    print("[voice_extract] All noise reduction failed, applying podcast chain...")
                    _apply_podcast_chain(str(input_audio), str(denoised_audio), audio_config)

        # Step 2: Load Silero VAD model
        print("[voice_extract] Loading Silero VAD model...")
        model = load_silero_vad()

        # Step 3: Run VAD on denoised audio
        print(f"[voice_extract] Reading denoised audio: {denoised_audio}")
        audio_tensor, sample_rate = _read_audio_with_scipy(str(denoised_audio), target_sr=16000)

        print(
            f"[voice_extract] Detecting voice segments (min_speech={min_speech_ms}ms, min_silence={min_silence_ms}ms)..."
        )
        speech_timestamps = get_speech_timestamps(
            audio_tensor,
            model,
            return_seconds=True,
            min_speech_duration_ms=min_speech_ms,
            min_silence_duration_ms=min_silence_ms,
        )

        if not speech_timestamps:
            raise StageError("voice_extract", "No voice segments detected")

        print(f"[voice_extract] Found {len(speech_timestamps)} voice segments")

        # Step 4: Read denoised audio for concatenation (at original 48kHz rate)
        rate, audio_data = wavfile.read(denoised_audio)

        # NOTE: We keep the FULL audio duration, not just voice segments.
        # The denoised audio has noise removed but maintains original timing.
        # VAD timestamps are saved for reference but we don't slice audio.
        voice_audio = audio_data

        # Calculate total voice duration for reporting
        total_voice_duration = sum(
            segment["end"] - segment["start"] for segment in speech_timestamps
        )

        # Write intermediate voice-only audio
        voice_only_wav = workspace_path / "output" / "audio" / session_id / "master_voice_raw.wav"
        wavfile.write(str(voice_only_wav), rate, voice_audio)

        # Step 6: Apply full podcast chain for professional quality
        print("[voice_extract] Applying podcast chain: highpass + EQ + compressor + loudnorm...")
        final_success = _apply_podcast_chain(str(voice_only_wav), str(output_audio), audio_config)

        if not final_success:
            # If final processing fails, use the raw voice audio
            import shutil

            shutil.copy(str(voice_only_wav), str(output_audio))

        # Clean up intermediate files
        if denoised_audio.exists():
            denoised_audio.unlink()
        if voice_only_wav.exists():
            voice_only_wav.unlink()

        # Calculate durations
        total_duration = len(audio_data) / rate
        voice_pct = 100 * total_voice_duration / total_duration if total_duration > 0 else 0

        print(
            f"[voice_extract] Voice: {total_voice_duration:.1f}s / {total_duration:.1f}s ({voice_pct:.1f}%)"
        )

        # Save speech timestamps for reference (output/analysis)
        vad_file = workspace_path / "output" / "analysis" / session_id / "vad_timestamps.json"
        vad_file.parent.mkdir(parents=True, exist_ok=True)
        vad_file.write_text(json.dumps(speech_timestamps, indent=2))

        # Update session status
        session.status = "voice_extracted"
        session_manager.save_session(session)

        return {
            "input_audio": str(input_audio),
            "output_audio": str(output_audio),
            "segments_count": len(speech_timestamps),
            "total_duration": total_duration,
            "voice_duration": total_voice_duration,
            "session_status": "voice_extracted",
        }

    except StageError:
        raise
    except Exception as e:
        raise StageError("voice_extract", f"VAD processing failed: {e}")


def process_segment(audio_segment_path: str, output_path: str, config: ConfigProvider) -> bool:
    """
    Process a single audio segment (for use in assemble.py for per-segment processing).

    Args:
        audio_segment_path: Path to input audio segment
        output_path: Path to output cleaned audio
        config: ConfigProvider instance

    Returns:
        True if successful, False otherwise
    """
    vad_settings = config.get_voice_extract_settings()
    min_speech_ms = vad_settings.get("min_speech_duration_ms", 2500)
    min_silence_ms = vad_settings.get("min_silence_duration_ms", 2500)

    arnndn_model_path = config.get_arnndn_model_path()
    arnndn_settings = config.get_arnndn_settings()
    arnndn_mix = arnndn_settings.get("mix", 0.85)

    try:
        # Step 1: Apply AI noise reduction
        temp_denoised = output_path.replace(".wav", "_denoised.wav")
        _apply_arnndn(audio_segment_path, temp_denoised, arnndn_model_path, arnndn_mix)

        # Step 2: Load VAD model and process
        model = load_silero_vad()
        audio_tensor, _ = _read_audio_with_scipy(temp_denoised, target_sr=16000)

        speech_timestamps = get_speech_timestamps(
            audio_tensor,
            model,
            return_seconds=True,
            min_speech_duration_ms=min_speech_ms,
            min_silence_duration_ms=min_silence_ms,
        )

        if not speech_timestamps:
            # No voice detected - use silence or original
            return False

        # Step 3: Extract voice segments
        rate, audio_data = wavfile.read(temp_denoised)
        voice_segments = []

        for segment in speech_timestamps:
            start_sample = int(segment["start"] * rate)
            end_sample = int(segment["end"] * rate)
            voice_segments.append(audio_data[start_sample:end_sample])

        if not voice_segments:
            return False

        voice_audio = np.concatenate(voice_segments)

        # Step 4: Apply final podcast chain for professional quality
        temp_voice = output_path.replace(".wav", "_voice.wav")
        wavfile.write(str(temp_voice), rate, voice_audio)

        # Use default audio config for segment processing
        config_provider = ConfigProvider(".")
        default_audio_config = config_provider.get_audio_processing_config()
        _apply_podcast_chain(str(temp_voice), output_path, default_audio_config)

        # Cleanup
        Path(temp_denoised).unlink(missing_ok=True)
        Path(temp_voice).unlink(missing_ok=True)

        return True

    except Exception as e:
        print(f"[voice_extract] process_segment error: {e}")
        return False
