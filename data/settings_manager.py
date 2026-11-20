"""
BINGO-BD Settings Manager
Persists and manages user settings such as sound toggle, volume, and animation/AI speed.
Pure Python - resilient to missing/corrupt files.
"""

from __future__ import annotations
import json
import os
import tempfile
from typing import Dict, Any


DEFAULT_SETTINGS: Dict[str, Any] = {
    "sound_enabled": True,
    "sound_volume": 0.7,
    "ai_speed": "Normal",  # "Normal" (0.8s) or "Fast" (0.2s)
}


class SettingsManager:
    """Manages audio and gameplay settings."""

    def __init__(self, filepath: str = "data/settings.json"):
        self.filepath = filepath
        self._ensure_directory()
        self.settings = self.load()

    def _ensure_directory(self) -> None:
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception:
                pass

    def load(self) -> Dict[str, Any]:
        """Loads settings from disk; defaults safely if missing or corrupt."""
        if not os.path.exists(self.filepath):
            return dict(DEFAULT_SETTINGS)
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in DEFAULT_SETTINGS.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            return dict(DEFAULT_SETTINGS)

    def save(self) -> None:
        """Atomic write of settings."""
        try:
            self._ensure_directory()
            dir_name = os.path.dirname(self.filepath) or "."
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                json.dump(self.settings, tf, indent=2)
                temp_name = tf.name
            os.replace(temp_name, self.filepath)
        except Exception:
            pass

    @property
    def sound_enabled(self) -> bool:
        return bool(self.settings.get("sound_enabled", True))

    @sound_enabled.setter
    def sound_enabled(self, val: bool) -> None:
        self.settings["sound_enabled"] = bool(val)
        self.save()

    @property
    def sound_volume(self) -> float:
        return float(self.settings.get("sound_volume", 0.7))

    @sound_volume.setter
    def sound_volume(self, val: float) -> None:
        self.settings["sound_volume"] = max(0.0, min(1.0, float(val)))
        self.save()

    @property
    def ai_speed(self) -> str:
        return str(self.settings.get("ai_speed", "Normal"))

    @ai_speed.setter
    def ai_speed(self, val: str) -> None:
        self.settings["ai_speed"] = val
        self.save()
