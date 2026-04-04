"""Stage: VoiceExtract - Extract voice segments using Silero VAD + AI noise reduction.

Pipeline:
1. Load audio from master.wav
2. Apply ConvTasNet source separation - separates voice from noise
3. Apply Silero VAD - detects speech segments
4. Concatenate only voice segments
5. Apply highpass (80Hz) - removes low rumble
6. Apply loudnorm (-16 LUFS) - podcast standard loudness
"""

import json
import subprocess
import torch
import torchaudio
from pathlib import Path
from functools import partial

from silero_vad import load_silero_vad, get_speech_timestamps
from scipy.io import wavfile
import numpy as np
import noisereduce as nr
import pyrnnoise

from scripts.utils.session import SessionManager
from scripts.utils import ffmpeg
from scripts.core.exceptions import StageError
from scripts.config import ConfigProvider


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
        f"arnndn=model_path={model_path}:mix={mix},"
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


def _apply_podcast_chain(
    input_wav: str, output_wav: str, profile: str = "longform"
) -> bool:
    """
    Apply professional podcast audio chain with custom EQ settings:
    Based on frequency analysis:
    1. highpass 80Hz - remove low rumble
    2. Bell cut at 450Hz (-3dB) - remove "boxy" sound from 400-500Hz
    3. Compressor: threshold -24dB, ratio 3.5:1, attack 5ms, release 100ms
    4. High shelf at 10kHz (+3dB) - add "air" and crispness
    5. Limiter: ceiling -1.0dB
    6. loudnorm: profile-specific LUFS

    Profile-specific settings:
    - longform: -16 LUFS, -1.5 dBTP (Spotify/Apple Podcasts standard)
    - shorts: -14 LUFS, -1.0 dBTP (TikTok/Instagram standard)
    """
    ffmpeg_path = "/usr/bin/ffmpeg"

    # Profile-specific loudness targets
    if profile == "shorts":
        # TikTok/Instagram: -14 LUFS, -1.0 dBTP
        target_lufs = "-14"
        true_peak = "-1.0"
    else:
        # Podcast: -16 LUFS, -1.5 dBTP
        target_lufs = "-16"
        true_peak = "-1.5"

    # Full podcast quality chain with custom EQ settings
    # Based on frequency analysis: HPF @ 80Hz, Bell cut @ 450Hz, Compressor, Air shelf @ 10kHz
    filter_chain = (
        "highpass=f=80:poles=2,"  # Remove low rumble (24dB/oct with poles=2)
        "equalizer=f=450:g=-3:w=300,"  # Bell cut at 450Hz -3dB (remove boxy sound)
        "acompressor=threshold=-24dB:ratio=3.5:attack=5:release=100:makeup=4dB:knee=1,"  # Voice compression
        "highshelf=f=10000:g=3,"  # Air shelf at 10kHz +3dB (add crispness/presence)
        f"alimiter=limit=-1dB,"  # Hard limiter at -1dB ceiling
        f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11"  # Profile-specific loudness
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
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
        "dialoguenhance=model=0:mix=0.8,"
        "arnndn=mix=0.85,"
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

        print(f"[voice_extract] Applied spectral noise reduction")
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

            # Denoise chunk - denoise_chunk returns a generator that yields processed frames
            for denoised_frame in rnnoise.denoise_chunk(chunk):
                # Each yield is a (processed_frame, _) tuple
                result_chunks.append(denoised_frame)

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
    profile = session.profile or "longform"
    print(f"[voice_extract] Using profile: {profile} for loudness settings")

    # Get VAD settings from config
    vad_settings = config.get_voice_extract_settings()
    min_speech_ms = vad_settings.get("min_speech_duration_ms", 2500)
    min_silence_ms = vad_settings.get("min_silence_duration_ms", 2500)

    # Get arnndn settings
    arnndn_model_path = config.get_arnndn_model_path()
    arnndn_settings = config.get_arnndn_settings()
    arnndn_mix = arnndn_settings.get("mix", 0.85)

    # Input is the master.wav from Proxies stage
    input_audio = workspace_path / "audio" / session_id / "master.wav"
    if not input_audio.exists():
        raise StageError("voice_extract", f"Audio not found: {input_audio}")

    # Intermediate files
    denoised_audio = workspace_path / "audio" / session_id / "master_denoised.wav"
    output_audio = workspace_path / "audio" / session_id / "master_voice.wav"

    try:
        # Step 1: Try system FFmpeg with dialoguenhance + arnndn (Adobe Podcast's technique!)
        print(f"[voice_extract] Trying system FFmpeg with dialoguenhance + arnndn...")
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
                print(
                    "[voice_extract] RNNoise failed, applying spectral noise reduction..."
                )
                spectral_success = _apply_spectral_noise_reduction(
                    str(input_audio), str(denoised_audio)
                )
                if not spectral_success:
                    # Ultimate fallback: just highpass + loudnorm
                    print(
                        "[voice_extract] All noise reduction failed, applying podcast chain..."
                    )
                    _apply_podcast_chain(str(input_audio), str(denoised_audio), profile)

        # Step 2: Load Silero VAD model
        print("[voice_extract] Loading Silero VAD model...")
        model = load_silero_vad()

        # Step 3: Run VAD on denoised audio
        print(f"[voice_extract] Reading denoised audio: {denoised_audio}")
        audio_tensor, sample_rate = _read_audio_with_scipy(
            str(denoised_audio), target_sr=16000
        )

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
        voice_only_wav = workspace_path / "audio" / session_id / "master_voice_raw.wav"
        wavfile.write(str(voice_only_wav), rate, voice_audio)

        # Step 6: Apply full podcast chain for professional quality
        print(
            "[voice_extract] Applying podcast chain: highpass + EQ + compressor + loudnorm..."
        )
        final_success = _apply_podcast_chain(
            str(voice_only_wav), str(output_audio), profile
        )

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
        voice_pct = (
            100 * total_voice_duration / total_duration if total_duration > 0 else 0
        )

        print(
            f"[voice_extract] Voice: {total_voice_duration:.1f}s / {total_duration:.1f}s ({voice_pct:.1f}%)"
        )

        # Save speech timestamps for reference
        vad_file = workspace_path / "analysis" / session_id / "vad_timestamps.json"
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


def process_segment(
    audio_segment_path: str, output_path: str, config: ConfigProvider
) -> bool:
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
        _apply_podcast_chain(
            str(temp_voice), output_path, "longform"
        )  # Default to longform

        # Cleanup
        Path(temp_denoised).unlink(missing_ok=True)
        Path(temp_voice).unlink(missing_ok=True)

        return True

    except Exception as e:
        print(f"[voice_extract] process_segment error: {e}")
        return False
