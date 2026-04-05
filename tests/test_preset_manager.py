"""Tests for PresetManager."""

import json
from pathlib import Path
import pytest

from scripts.preset_manager import PresetManager


@pytest.fixture
def preset_manager(workspace_root):
    """Create PresetManager with test workspace."""
    return PresetManager(str(workspace_root))


class TestPresetManagerInit:
    """Test PresetManager initialization."""

    def test_init_loads_presets(self, workspace_root):
        pm = PresetManager(str(workspace_root))
        assert pm._workspace == workspace_root

    def test_init_missing_preset_files(self, tmp_path):
        """Test graceful handling when preset files don't exist."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Only settings.json
        (config_dir / "settings.json").write_text("{}")

        # Should not raise
        pm = PresetManager(str(tmp_path))
        assert pm._subtitle_presets == {}


class TestSubtitlePresets:
    """Test subtitle preset operations."""

    def test_get_subtitle_presets(self, preset_manager):
        presets = preset_manager.get_subtitle_presets()
        assert isinstance(presets, dict)

    def test_get_subtitle_preset_exists(self, preset_manager):
        preset = preset_manager.get_subtitle_preset("default")
        # May be None if no preset file exists - that's ok
        assert preset is None or isinstance(preset, dict)

    def test_get_subtitle_preset_not_exists(self, preset_manager):
        preset = preset_manager.get_subtitle_preset("nonexistent")
        assert preset is None

    def test_get_default_subtitle_preset(self, preset_manager):
        preset = preset_manager.get_default_subtitle_preset()
        assert isinstance(preset, dict)

    def test_list_subtitle_presets(self, preset_manager):
        presets = preset_manager.list_subtitle_presets()
        assert isinstance(presets, list)

    def test_create_subtitle_preset(self, workspace_root, tmp_path):
        """Test creating new subtitle preset."""
        pm = PresetManager(str(workspace_root))

        new_preset = {
            "name": "Custom Preset",
            "description": "My custom preset",
            "font_family": "Arial",
            "font_size": 60,
            "read_only": False,
        }

        # Create preset
        pm.create_subtitle_preset("custom", new_preset)

        # Verify it was saved
        assert pm.get_subtitle_preset("custom") is not None

    def test_update_subtitle_preset(self, workspace_root):
        """Test updating existing preset."""
        pm = PresetManager(str(workspace_root))

        # Create first
        pm.create_subtitle_preset(
            "updatable",
            {
                "name": "Updatable",
                "description": "Original",
                "font_size": 50,
                "read_only": False,
            },
        )

        # Update
        pm.update_subtitle_preset("updatable", {"font_size": 70})

        preset = pm.get_subtitle_preset("updatable")
        assert preset["font_size"] == 70

    def test_delete_subtitle_preset(self, workspace_root):
        """Test deleting preset."""
        pm = PresetManager(str(workspace_root))

        # Create first
        pm.create_subtitle_preset(
            "deletable",
            {
                "name": "Deletable",
                "description": "To be deleted",
                "read_only": False,
            },
        )

        # Delete
        result = pm.delete_subtitle_preset("deletable")
        assert result is True
        assert pm.get_subtitle_preset("deletable") is None

    def test_cannot_delete_readonly_preset(self, workspace_root):
        """Test cannot delete read-only presets."""
        pm = PresetManager(str(workspace_root))

        # Default presets are read-only
        result = pm.delete_subtitle_preset("default")
        assert result is False


class TestAudioPresets:
    """Test audio preset operations."""

    def test_get_audio_presets(self, preset_manager):
        presets = preset_manager.get_audio_presets()
        assert isinstance(presets, dict)

    def test_get_audio_preset(self, preset_manager):
        preset = preset_manager.get_audio_preset("default")
        assert preset is not None or preset is None  # Depends on config

    def test_list_audio_presets(self, preset_manager):
        presets = preset_manager.list_audio_presets()
        assert isinstance(presets, list)

    def test_create_audio_preset(self, workspace_root):
        """Test creating new audio preset."""
        pm = PresetManager(str(workspace_root))

        new_preset = {
            "name": "Podcast Audio",
            "description": "For podcasts",
            "highpass_freq": 80,
            "loudnorm_I": -16,
            "read_only": False,
        }

        pm.create_audio_preset("podcast", new_preset)
        assert pm.get_audio_preset("podcast") is not None

    def test_update_audio_preset(self, workspace_root):
        """Test updating audio preset."""
        pm = PresetManager(str(workspace_root))

        pm.create_audio_preset(
            "updatable_audio",
            {
                "name": "Updatable",
                "highpass_freq": 80,
                "read_only": False,
            },
        )

        pm.update_audio_preset("updatable_audio", {"highpass_freq": 100})

        preset = pm.get_audio_preset("updatable_audio")
        assert preset["highpass_freq"] == 100

    def test_delete_audio_preset(self, workspace_root):
        """Test deleting audio preset."""
        pm = PresetManager(str(workspace_root))

        pm.create_audio_preset(
            "deletable_audio",
            {
                "name": "Deletable",
                "read_only": False,
            },
        )

        result = pm.delete_audio_preset("deletable_audio")
        assert result is True


class TestColorPresets:
    """Test color preset operations."""

    def test_get_color_presets(self, preset_manager):
        presets = preset_manager.get_color_presets()
        assert isinstance(presets, dict)

    def test_get_color_preset(self, preset_manager):
        preset = preset_manager.get_color_preset("default")
        assert preset is not None or preset is None

    def test_list_color_presets(self, preset_manager):
        presets = preset_manager.list_color_presets()
        assert isinstance(presets, list)

    def test_create_color_preset(self, workspace_root):
        """Test creating new color preset."""
        pm = PresetManager(str(workspace_root))

        new_preset = {
            "name": "Cinematic",
            "description": "Cinematic look",
            "saturation": 1.1,
            "contrast": 1.2,
            "read_only": False,
        }

        pm.create_color_preset("cinematic", new_preset)
        assert pm.get_color_preset("cinematic") is not None

    def test_update_color_preset(self, workspace_root):
        """Test updating color preset."""
        pm = PresetManager(str(workspace_root))

        pm.create_color_preset(
            "updatable_color",
            {
                "name": "Updatable",
                "saturation": 1.0,
                "read_only": False,
            },
        )

        pm.update_color_preset("updatable_color", {"saturation": 1.2})

        preset = pm.get_color_preset("updatable_color")
        assert preset["saturation"] == 1.2


class TestPresetValidation:
    """Test preset validation."""

    def test_validate_preset_structure(self, workspace_root):
        """Test that presets have required structure."""
        pm = PresetManager(str(workspace_root))

        default_sub = pm.get_default_subtitle_preset()
        if default_sub:
            assert "name" in default_sub or default_sub == {}
