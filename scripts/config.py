"""
ConfigProvider - Centralized configuration management for the pipeline.
Loads settings from config/ JSON files and provides typed access.
"""

import json
import warnings as _warnings
from pathlib import Path

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
            with open(path) as f:
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
        return "default"

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

    # === Audio Processing Settings ===

    def get_audio_processing_config(self) -> dict:
        """Get global audio processing configuration with all filters."""
        audio_config_file = self._config_dir / "audio_processing.json"
        if audio_config_file.exists():
            return json.loads(audio_config_file.read_text())
        return {}

    def get_audio_filter(self, filter_name: str) -> dict:
        """Get a specific audio filter config."""
        config = self.get_audio_processing_config()
        return config.get(filter_name, {})

    def get_audio_filter_enabled(self, filter_name: str) -> bool:
        """Check if an audio filter is enabled."""
        filter_config = self.get_audio_filter(filter_name)
        return filter_config.get("enabled", False)

    def save_audio_processing_config(self, config: dict) -> None:
        """Save audio processing configuration."""
        audio_config_file = self._config_dir / "audio_processing.json"
        audio_config_file.write_text(json.dumps(config, indent=2))

    def update_audio_filter(self, filter_name: str, updates: dict) -> None:
        """Update a specific audio filter configuration."""
        config = self.get_audio_processing_config()
        if filter_name in config:
            config[filter_name].update(updates)
        else:
            config[filter_name] = updates
        self.save_audio_processing_config(config)

    def toggle_audio_filter(self, filter_name: str, enabled: bool) -> None:
        """Toggle a specific audio filter on/off."""
        self.update_audio_filter(filter_name, {"enabled": enabled})

    def get_session_audio_config(self, workspace: str, session_id: str) -> dict:
        """Get session-specific audio config, falls back to global defaults."""
        workspace_path = Path(workspace)
        session_audio_config = (
            workspace_path / "data" / "recordings" / session_id / "audio_config.json"
        )

        if session_audio_config.exists():
            return json.loads(session_audio_config.read_text())

        # Fall back to global config
        return self.get_audio_processing_config()

    def save_session_audio_config(self, workspace: str, session_id: str, config: dict) -> None:
        """Save session-specific audio configuration."""
        workspace_path = Path(workspace)
        session_audio_config = (
            workspace_path / "data" / "recordings" / session_id / "audio_config.json"
        )
        session_audio_config.parent.mkdir(parents=True, exist_ok=True)
        session_audio_config.write_text(json.dumps(config, indent=2))

    def toggle_audio_filter(self, workspace: str, session_id: str, filter_name: str) -> None:
        """Toggle a session-specific audio filter on/off."""
        audio_config = self.get_session_audio_config(workspace, session_id)
        current = audio_config.get(filter_name, {}).get("enabled", True)
        audio_config[filter_name] = audio_config.get(filter_name, {})
        audio_config[filter_name]["enabled"] = not current
        self.save_session_audio_config(workspace, session_id, audio_config)

    def update_audio_filter(
        self, workspace: str, session_id: str, filter_name: str, updates: dict
    ) -> None:
        """Update session-specific audio filter parameters."""
        audio_config = self.get_session_audio_config(workspace, session_id)
        audio_config[filter_name] = audio_config.get(filter_name, {})
        audio_config[filter_name].update(updates)
        self.save_session_audio_config(workspace, session_id, audio_config)

    def reset_audio_processing_to_defaults(self) -> None:
        """Reset audio processing to default configuration."""
        self.save_audio_processing_config(
            json.loads(
                (Path(__file__).parent.parent / "config" / "audio_processing.json").read_text()
            )
        )

    # === Profile Settings (now uses single "default" profile) ===

    def get_profile(self, profile_name: str = "default") -> dict:
        """Get profile settings, falls back to default."""
        profile = self._profiles.get(profile_name, {})
        if not profile:
            profile = self._profiles.get("default", {})
        return profile

    def get_profile_voice_extract_settings(self, profile_name: str = "default") -> dict:
        """Get voice_extract settings for profile, with fallback to global settings."""
        profile = self.get_profile(profile_name)
        voice_extract_settings = profile.get("voice_extract", {})

        # Fall back to global settings if not specified in profile
        if not voice_extract_settings:
            voice_extract_settings = self.get_voice_extract_settings()

        return voice_extract_settings

    def get_all_profiles(self) -> list[str]:
        return list(self._profiles.keys())

    def get_profile_silence_threshold(self, profile_name: str = "default") -> float:
        return self.get_profile(profile_name).get("silence_threshold_db", -40)

    def get_profile_silence_min_duration(self, profile_name: str = "default") -> float:
        return self.get_profile(profile_name).get("silence_min_duration_s", 0.8)

    def get_profile_enable_cutting(self, profile_name: str = "default") -> bool:
        """Whether silence cutting is enabled (default: False)."""
        return self.get_profile(profile_name).get("enable_cutting", False)

    def get_profile_collapse_to(self, profile_name: str = "default") -> float:
        return self.get_profile(profile_name).get("collapse_to_s", 0.25)

    def get_profile_trim_pad_before(self, profile_name: str = "default") -> float:
        return self.get_profile(profile_name).get("trim_pad_before_s", 0.1)

    def get_profile_trim_pad_after(self, profile_name: str = "default") -> float:
        return self.get_profile(profile_name).get("trim_pad_after_s", 0.12)

    def get_profile_remove_fillers(self, profile_name: str = "default") -> bool:
        return self.get_profile(profile_name).get("remove_fillers", False)

    def get_profile_filler_confidence_threshold(self, profile_name: str = "default") -> float:
        return self.get_profile(profile_name).get("filler_confidence_threshold", 0.9)

    def get_profile_low_energy_min_duration(self, profile_name: str = "default") -> float:
        return self.get_profile(profile_name).get("low_energy_min_duration_s", 5.0)

    def get_profile_target_duration(self, profile_name: str = "default") -> float | None:
        return self.get_profile(profile_name).get("target_duration_s")

    def get_profile_max_duration(self, profile_name: str = "default") -> float | None:
        return self.get_profile(profile_name).get("max_duration_s")

    def get_profile_caption_words_per_line(self, profile_name: str = "default") -> int:
        return self.get_profile(profile_name).get("caption_words_per_line", 7)

    def get_profile_caption_style(self, profile_name: str = "default") -> str:
        return self.get_profile(profile_name).get("caption_style", "default")

    def get_profile_pip_position(self, profile_name: str = "default") -> str:
        return self.get_profile(profile_name).get("pip_position", "bottom_right")

    def get_profile_pip_size_ratio(self, profile_name: str = "default") -> float:
        return self.get_profile(profile_name).get("pip_size_ratio", 0.167)

    def get_profile_aspect_ratio(self, profile_name: str) -> str:
        return self.get_profile(profile_name).get("aspect_ratio", "16:9")

    def get_profile_resolution(self, profile_name: str) -> str:
        return self.get_profile(profile_name).get("resolution", "1920x1080")

    # === Loudnorm Targets ===

    def get_loudnorm_targets(self, profile_name: str) -> dict:
        loudnorm = self.get_loudnorm_settings()
        return loudnorm.get(
            profile_name, loudnorm.get("default", {"I": -16, "TP": -1.5, "LRA": 11})
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
