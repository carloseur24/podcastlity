"""Tests for ConfigProvider."""

import json
from pathlib import Path
import pytest

from scripts.config import ConfigProvider


class TestConfigProvider:
    """Test ConfigProvider basic functionality."""

    def test_init_loads_all_configs(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config._workspace == workspace_root
        assert config._config_dir == workspace_root / "config"

    def test_get_workspace_root(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        root = config.get_workspace_root()
        assert root == str(workspace_root)

    def test_get_ffmpeg_path(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_ffmpeg_path() == "imageio"

    def test_get_whisper_model(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_whisper_model() == "large-v2"

    def test_get_default_profile(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_default_profile() == "default"

    def test_get_profile_default(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        profile = config.get_profile("default")
        assert profile["silence_threshold_db"] == -40

    def test_get_profile_fallback(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        profile = config.get_profile("nonexistent")
        assert profile["silence_threshold_db"] == -40

    def test_get_profile_silence_threshold(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_silence_threshold("default") == -40

    def test_get_profile_silence_min_duration(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_silence_min_duration("default") == 0.8

    def test_get_profile_enable_cutting(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_enable_cutting("default") is False

    def test_get_profile_collapse_to(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_collapse_to("default") == 0.25

    def test_get_profile_trim_pad_before(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_trim_pad_before("default") == 0.1

    def test_get_profile_trim_pad_after(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_trim_pad_after("default") == 0.12

    def test_get_profile_remove_fillers(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_remove_fillers("default") is False

    def test_get_profile_caption_words_per_line(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_caption_words_per_line("default") == 7

    def test_get_profile_caption_style(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_caption_style("default") == "default"

    def test_get_profile_pip_position(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_pip_position("default") == "bottom_right"

    def test_get_profile_pip_size_ratio(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_pip_size_ratio("default") == 0.167

    def test_get_profile_aspect_ratio(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_aspect_ratio("default") == "16:9"

    def test_get_profile_resolution(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        assert config.get_profile_resolution("default") == "1920x1080"

    def test_get_all_profiles(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        profiles = config.get_all_profiles()
        assert "default" in profiles


class TestConfigFilters:
    """Test filter configuration methods."""

    def test_get_highpass_settings(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        hp = config.get_highpass_settings()
        assert hp["default_freq"] == 80

    def test_get_afftdn_settings(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        afftdn = config.get_afftdn_settings()
        assert afftdn["nr_mild"] == 10

    def test_get_egate_settings(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        gate = config.get_egate_settings()
        assert "above_floor_db" in gate

    def test_get_loudnorm_settings(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        loud = config.get_loudnorm_settings()
        assert "default" in loud

    def test_get_loudnorm_targets(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        targets = config.get_loudnorm_targets("default")
        assert targets["I"] == -16
        assert targets["TP"] == -1.5
        assert targets["LRA"] == 11


class TestConfigBrand:
    """Test brand configuration methods."""

    def test_get_brand(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        brand = config.get_brand()
        assert brand["channel_name"] == "TestChannel"

    def test_get_brand_font(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        font = config.get_brand_font()
        assert font == "Montserrat"

    def test_get_brand_colors(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        colors = config.get_brand_colors()
        assert colors["primary_color"] == "#FFDD00"


class TestConfigVoiceExtract:
    """Test voice extraction configuration."""

    def test_get_voice_extract_settings(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        ve = config.get_voice_extract_settings()
        assert "min_speech_duration_ms" in ve


class TestConfigArnndn:
    """Test ARNNDN noise reduction configuration."""

    def test_get_arnndn_model_path(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        path = config.get_arnndn_model_path()
        assert path

    def test_get_arnndn_settings(self, workspace_root):
        config = ConfigProvider(str(workspace_root))
        settings = config.get_arnndn_settings()
        assert "mix" in settings


class TestConfigValidation:
    """Test configuration validation."""

    def test_invalid_filters_raises(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        (config_dir / "settings.json").write_text("{}")
        (config_dir / "filters.json").write_text('{"invalid": true}')
        (config_dir / "profiles.json").write_text("{}")
        (config_dir / "brand.json").write_text("{}")

        with pytest.raises(ValueError, match="CONFIG ERROR"):
            ConfigProvider(str(tmp_path))
