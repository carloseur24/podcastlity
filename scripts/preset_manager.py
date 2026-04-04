"""
PresetManager - Unified preset management for Audio, Subtitles, and Color.
Loads presets from config JSON files and provides CRUD operations.
"""

import json
import shutil
from pathlib import Path
from typing import Any


class PresetManager:
    """Manages presets for audio, subtitles, and color with default read-only presets."""

    def __init__(self, workspace_root: str = "."):
        self._workspace = Path(workspace_root)
        self._config_dir = self._workspace / "config"

        # Load all preset types
        self._subtitle_presets = self._load_presets("subtitle_presets.json")
        self._audio_presets = self._load_presets("audio_presets.json")
        self._color_presets = self._load_presets("color_presets.json")

    def _load_presets(self, filename: str) -> dict:
        """Load presets from JSON file."""
        path = self._config_dir / filename
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return {}

    def _save_presets(self, filename: str, presets: dict) -> None:
        """Save presets to JSON file."""
        path = self._config_dir / filename
        with open(path, "w") as f:
            json.dump(presets, f, indent=2)

    # === Subtitle Presets ===

    def get_subtitle_presets(self) -> dict:
        """Get all subtitle presets."""
        return self._subtitle_presets

    def get_subtitle_preset(self, name: str) -> dict | None:
        """Get a specific subtitle preset by name."""
        return self._subtitle_presets.get(name)

    def get_default_subtitle_preset(self) -> dict:
        """Get the default subtitle preset (read-only)."""
        return self._subtitle_presets.get("default", {})

    def list_subtitle_presets(self) -> list[dict]:
        """List all subtitle presets with metadata."""
        return [
            {
                "name": name,
                "display_name": data.get("name", name),
                "description": data.get("description", ""),
                "read_only": data.get("read_only", False),
                "is_default": data.get("is_default", False),
            }
            for name, data in self._subtitle_presets.items()
            if name != "profiles"
        ]

    def create_subtitle_preset(self, name: str, data: dict) -> bool:
        """Create a new subtitle preset."""
        if name in self._subtitle_presets:
            return False

        # Add metadata
        data["name"] = data.get("name", name)
        data["read_only"] = False
        data["is_default"] = False
        data["type"] = "subtitle"
        data["engine"] = "remotion"

        self._subtitle_presets[name] = data
        self._save_presets("subtitle_presets.json", self._subtitle_presets)
        return True

    def update_subtitle_preset(self, name: str, data: dict) -> bool:
        """Update an existing subtitle preset (cannot update default)."""
        if name not in self._subtitle_presets:
            return False

        existing = self._subtitle_presets[name]
        if existing.get("read_only", False):
            return False

        # Preserve metadata
        data["name"] = data.get("name", existing.get("name", name))
        data["read_only"] = False
        data["is_default"] = False
        data["type"] = "subtitle"
        data["engine"] = "remotion"

        self._subtitle_presets[name] = data
        self._save_presets("subtitle_presets.json", self._subtitle_presets)
        return True

    def delete_subtitle_preset(self, name: str) -> bool:
        """Delete a subtitle preset (cannot delete default)."""
        if name not in self._subtitle_presets:
            return False

        if self._subtitle_presets[name].get("read_only", False):
            return False

        del self._subtitle_presets[name]
        self._save_presets("subtitle_presets.json", self._subtitle_presets)
        return True

    # === Audio Presets ===

    def get_audio_presets(self) -> dict:
        """Get all audio presets."""
        return self._audio_presets

    def get_audio_preset(self, name: str) -> dict | None:
        """Get a specific audio preset by name."""
        return self._audio_presets.get(name)

    def get_default_audio_preset(self) -> dict:
        """Get the default audio preset."""
        return self._audio_presets.get("default", {})

    def list_audio_presets(self) -> list[dict]:
        """List all audio presets with metadata."""
        return [
            {
                "name": name,
                "display_name": data.get("name", name),
                "description": data.get("description", ""),
                "read_only": data.get("read_only", False),
                "is_default": data.get("is_default", False),
            }
            for name, data in self._audio_presets.items()
        ]

    def create_audio_preset(self, name: str, data: dict) -> bool:
        """Create a new audio preset."""
        if name in self._audio_presets:
            return False

        data["name"] = data.get("name", name)
        data["read_only"] = False
        data["is_default"] = False
        data["type"] = "audio"

        self._audio_presets[name] = data
        self._save_presets("audio_presets.json", self._audio_presets)
        return True

    def update_audio_preset(self, name: str, data: dict) -> bool:
        """Update an existing audio preset."""
        if name not in self._audio_presets:
            return False

        if self._audio_presets[name].get("read_only", False):
            return False

        data["read_only"] = False
        data["is_default"] = False
        data["type"] = "audio"

        self._audio_presets[name] = data
        self._save_presets("audio_presets.json", self._audio_presets)
        return True

    def delete_audio_preset(self, name: str) -> bool:
        """Delete an audio preset."""
        if name not in self._audio_presets:
            return False

        if self._audio_presets[name].get("read_only", False):
            return False

        del self._audio_presets[name]
        self._save_presets("audio_presets.json", self._audio_presets)
        return True

    # === Color Presets ===

    def get_color_presets(self) -> dict:
        """Get all color presets."""
        return self._color_presets

    def get_color_preset(self, name: str) -> dict | None:
        """Get a specific color preset by name."""
        return self._color_presets.get(name)

    def get_default_color_preset(self) -> dict:
        """Get the default color preset."""
        return self._color_presets.get("default", {})

    def list_color_presets(self) -> list[dict]:
        """List all color presets with metadata."""
        return [
            {
                "name": name,
                "display_name": data.get("name", name),
                "description": data.get("description", ""),
                "read_only": data.get("read_only", False),
                "is_default": data.get("is_default", False),
            }
            for name, data in self._color_presets.items()
        ]

    def get_color_scales(self) -> dict:
        """Get available color scales from default preset."""
        default = self.get_default_color_preset()
        return default.get("scales", {})

    def get_color_subpresets(self, preset_name: str) -> dict:
        """Get sub-presets (balanced, cold, warm) for a color preset."""
        preset = self.get_color_preset(preset_name)
        if preset:
            return preset.get("presets", {})
        return {}

    def create_color_preset(self, name: str, data: dict) -> bool:
        """Create a new color preset."""
        if name in self._color_presets:
            return False

        data["name"] = data.get("name", name)
        data["read_only"] = False
        data["is_default"] = False
        data["type"] = "color"

        self._color_presets[name] = data
        self._save_presets("color_presets.json", self._color_presets)
        return True

    def update_color_preset(self, name: str, data: dict) -> bool:
        """Update an existing color preset."""
        if name not in self._color_presets:
            return False

        if self._color_presets[name].get("read_only", False):
            return False

        data["read_only"] = False
        data["is_default"] = False
        data["type"] = "color"

        self._color_presets[name] = data
        self._save_presets("color_presets.json", self._color_presets)
        return True

    def delete_color_preset(self, name: str) -> bool:
        """Delete a color preset."""
        if name not in self._color_presets:
            return False

        if self._color_presets[name].get("read_only", False):
            return False

        del self._color_presets[name]
        self._save_presets("color_presets.json", self._color_presets)
        return True

    # === Utility ===

    def export_preset_to_file(
        self, preset_type: str, name: str, output_path: str
    ) -> bool:
        """Export a preset to a file."""
        if preset_type == "subtitle":
            preset = self.get_subtitle_preset(name)
        elif preset_type == "audio":
            preset = self.get_audio_preset(name)
        elif preset_type == "color":
            preset = self.get_color_preset(name)
        else:
            return False

        if not preset:
            return False

        output = Path(output_path)
        output.write_text(json.dumps(preset, indent=2))
        return True

    def import_preset_from_file(self, preset_type: str, file_path: str) -> bool:
        """Import a preset from a file."""
        path = Path(file_path)
        if not path.exists():
            return False

        try:
            data = json.loads(path.read_text())
            name = path.stem  # Use filename as preset name

            if preset_type == "subtitle":
                return self.create_subtitle_preset(name, data)
            elif preset_type == "audio":
                return self.create_audio_preset(name, data)
            elif preset_type == "color":
                return self.create_color_preset(name, data)
        except json.JSONDecodeError:
            return False

        return False


# Global singleton
_preset_manager: PresetManager | None = None


def get_preset_manager(workspace_root: str = ".") -> PresetManager:
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager(workspace_root)
    return _preset_manager


def reset_preset_manager():
    global _preset_manager
    _preset_manager = None
