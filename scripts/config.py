"""
ConfigProvider - Centralized configuration management for the pipeline.
Loads settings from config/ JSON files and provides typed access.
"""

import json
import warnings as _warnings
from pathlib import Path
from typing import Any

from scripts.config_models import validate_filters_config


class ConfigProvider:
    def __init__(self, workspace_root: str = "."):
        self._workspace = Path(workspace_root)
        self._config_dir = self._workspace / "config"

        self._settings = self._load_json("settings.json")
        self._filters = self._load_json("filters.json")
        self._profiles = self._load_json("profiles.json")
        self._brand = self._load_json("brand.json")

        self._validate_filters()

    def _validate_filters(self):
        errors, warnings = validate_filters_config(self._filters)
        for err in errors:
            raise ValueError(f"[CONFIG ERROR] {err}")
        for warn in warnings:
            _warnings.warn(f"[CONFIG WARNING] {warn}", UserWarning)

    def _load_json(self, filename: str) -> dict:
        path = self._config_dir / filename
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return {}

    # === General Settings ===

    def get_workspace_root(self) -> str:
        return str(self._settings.get("workspace_root", "."))

    def get_recordings_mount(self) -> str:
        return self._settings.get("recordings_mount", "")

    def get_ffmpeg_path(self) -> str:
        return self._settings.get("ffmpeg_path", "imageio")

    def get_ffmpeg_threads(self) -> int:
        return self._settings.get("ffmpeg_threads", 0)

    def get_whisper_model(self) -> str:
        return self._settings.get("whisper_model", "whisper")

    def get_whisper_compute_type(self) -> str:
        return self._settings.get("whisper_compute_type", "int8")

    def get_whisper_device(self) -> str:
        return self._settings.get("whisper_device", "cpu")

    def get_whisper_language(self) -> str:
        return self._settings.get("whisper_language", "es")

    def get_whisper_beam_size(self) -> int:
        return self._settings.get("whisper_beam_size", 5)

    def get_whisper_word_timestamps(self) -> bool:
        return self._settings.get("whisper_word_timestamps", True)

    def get_whisper_vad_filter(self) -> bool:
        return self._settings.get("whisper_vad_filter", True)

    def get_whisper_vad_min_silence_duration_ms(self) -> int:
        return self._settings.get("whisper_vad_min_silence_duration_ms", 500)

    def get_default_profile(self) -> str:
        return self._settings.get("default_profile", "longform")

    def get_proxy_resolution(self) -> str:
        return self._settings.get("proxy_resolution", "1280x720")

    def get_logs_level(self) -> str:
        return self._settings.get("logs_level", "INFO")

    def get_voice_extract_settings(self) -> dict:
        return self._settings.get(
            "voice_extract",
            {"min_speech_duration_ms": 2500, "min_silence_duration_ms": 2500},
        )

    def get_arnndn_model_path(self) -> str:
        return self._settings.get(
            "arnndn_model_path",
            "/home/carlos/side-projects/mvp-editing-pipeline/models/arnndn/std.rnnn",
        )

    def get_arnndn_settings(self) -> dict:
        return self._settings.get("arnndn", {"mix": 0.8})

    def get_anthropic_api_key(self) -> str:
        return self._settings.get("anthropic_api_key", "")

    def get_replicate_api_key(self) -> str:
        return self._settings.get("replicate_api_key", "")

    # === Filter Settings ===

    def get_filter(self, category: str) -> dict:
        return self._filters.get(category, {})

    def get_highpass_settings(self) -> dict:
        return self._filters.get("highpass", {})

    def get_afftdn_settings(self) -> dict:
        return self._filters.get("afftdn", {})

    def get_agate_settings(self) -> dict:
        return self._filters.get("agate", {})

    def get_eq_settings(self) -> dict:
        return self._filters.get("eq", {})

    def get_loudnorm_settings(self) -> dict:
        return self._filters.get("loudnorm", {})

    def get_stereo_settings(self) -> dict:
        return self._filters.get("stereo", {})

    def get_compressor_settings(self) -> dict:
        return self._filters.get("compressor", {})

    def get_diagnostic_settings(self) -> dict:
        return self._filters.get("diagnostic", {})

    # === Profile Settings ===

    def get_profile(self, profile_name: str) -> dict:
        return self._profiles.get(profile_name, {})

    def get_profile_voice_extract_settings(self, profile_name: str) -> dict:
        """Get voice_extract settings for a specific profile, with fallback to global settings."""
        profile = self.get_profile(profile_name)
        voice_extract_settings = profile.get("voice_extract", {})

        # Fall back to global settings if not specified in profile
        if not voice_extract_settings:
            voice_extract_settings = self.get_voice_extract_settings()

        return voice_extract_settings

    def get_all_profiles(self) -> list[str]:
        return list(self._profiles.keys())

    def get_profile_silence_threshold(self, profile_name: str) -> float:
        return self.get_profile(profile_name).get("silence_threshold_db", -40)

    def get_profile_silence_min_duration(self, profile_name: str) -> float:
        return self.get_profile(profile_name).get("silence_min_duration_s", 0.5)

    def get_profile_collapse_to(self, profile_name: str) -> float:
        return self.get_profile(profile_name).get("collapse_to_s", 0.25)

    def get_profile_trim_pad_before(self, profile_name: str) -> float:
        return self.get_profile(profile_name).get("trim_pad_before_s", 0.1)

    def get_profile_trim_pad_after(self, profile_name: str) -> float:
        return self.get_profile(profile_name).get("trim_pad_after_s", 0.12)

    def get_profile_remove_fillers(self, profile_name: str) -> bool:
        return self.get_profile(profile_name).get("remove_fillers", False)

    def get_profile_filler_confidence_threshold(self, profile_name: str) -> float:
        return self.get_profile(profile_name).get("filler_confidence_threshold", 0.9)

    def get_profile_low_energy_min_duration(self, profile_name: str) -> float:
        return self.get_profile(profile_name).get("low_energy_min_duration_s", 5.0)

    def get_profile_target_duration(self, profile_name: str) -> float | None:
        return self.get_profile(profile_name).get("target_duration_s")

    def get_profile_max_duration(self, profile_name: str) -> float | None:
        return self.get_profile(profile_name).get("max_duration_s")

    def get_profile_caption_words_per_line(self, profile_name: str) -> int:
        return self.get_profile(profile_name).get("caption_words_per_line", 7)

    def get_profile_caption_style(self, profile_name: str) -> str:
        return self.get_profile(profile_name).get("caption_style", "default")

    def get_profile_pip_position(self, profile_name: str) -> str:
        return self.get_profile(profile_name).get("pip_position", "bottom_right")

    def get_profile_pip_size_ratio(self, profile_name: str) -> float:
        return self.get_profile(profile_name).get("pip_size_ratio", 0.167)

    def get_profile_aspect_ratio(self, profile_name: str) -> str:
        return self.get_profile(profile_name).get("aspect_ratio", "16:9")

    def get_profile_resolution(self, profile_name: str) -> str:
        return self.get_profile(profile_name).get("resolution", "1920x1080")

    # === Loudnorm Targets ===

    def get_loudnorm_targets(self, profile_name: str) -> dict:
        loudnorm = self.get_loudnorm_settings()
        return loudnorm.get(
            profile_name, loudnorm.get("longform", {"I": -16, "TP": -1.5, "LRA": 11})
        )

    # === Brand Settings ===

    def get_brand(self) -> dict:
        return self._brand

    def get_brand_font(self) -> str:
        return self._brand.get("font", "Inter")

    def get_brand_colors(self) -> dict:
        return self._brand.get("colors", {})


# Global singleton instance - initialized lazily
_config: ConfigProvider | None = None


def get_config(workspace_root: str = ".") -> ConfigProvider:
    global _config
    if _config is None:
        _config = ConfigProvider(workspace_root)
    return _config


def reset_config():
    global _config
    _config = None
