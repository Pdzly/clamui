# ClamUI Settings Manager Module
"""
Settings manager module for ClamUI providing user preferences storage.
Stores user settings in JSON format following XDG conventions.
"""

import json
import os
import threading
from pathlib import Path
from typing import Any, Optional


class SettingsManager:
    """
    Manager for user settings persistence.

    Provides methods for saving and loading user preferences
    stored in JSON format at ~/.config/clamui/settings.json.
    """

    DEFAULT_SETTINGS = {
        "notifications_enabled": True,
        "minimize_to_tray": False,
        "start_minimized": False,
        # Quarantine settings
        "quarantine_directory": "",  # Empty string means use default (~/.local/share/clamui/quarantine)
        # Scheduled scan settings
        "scheduled_scans_enabled": False,
        "schedule_frequency": "weekly",  # "daily", "weekly", "monthly"
        "schedule_time": "02:00",  # 24-hour format HH:MM
        "schedule_targets": [],  # List of directory paths to scan
        "schedule_skip_on_battery": True,
        "schedule_auto_quarantine": False,
        "schedule_day_of_week": 0,  # 0=Monday, 6=Sunday (for weekly scans)
        "schedule_day_of_month": 1,  # 1-28 (for monthly scans)
        "exclusion_patterns": [],
        # Scan backend settings
        "scan_backend": "auto",  # "auto", "daemon", "clamscan"
        "daemon_socket_path": "",  # Empty = auto-detect
    }

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the SettingsManager.

        Args:
            config_dir: Optional custom config directory.
                        Defaults to XDG_CONFIG_HOME/clamui or ~/.config/clamui
        """
        if config_dir is not None:
            self._config_dir = Path(config_dir)
        else:
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "~/.config")
            self._config_dir = Path(xdg_config_home).expanduser() / "clamui"

        self._settings_file = self._config_dir / "settings.json"

        # Thread lock for safe concurrent access
        self._lock = threading.Lock()

        # Load settings on initialization
        self._settings = self._load()

    def _load(self) -> dict:
        """
        Load settings from file.

        Returns:
            Dictionary of settings merged with defaults
        """
        with self._lock:
            try:
                if self._settings_file.exists():
                    with open(self._settings_file, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        # Merge with defaults to ensure all keys exist
                        return {**self.DEFAULT_SETTINGS, **loaded}
            except (json.JSONDecodeError, OSError, PermissionError):
                # Handle corrupted files or permission issues silently
                pass
            return dict(self.DEFAULT_SETTINGS)

    def save(self) -> bool:
        """
        Save settings to file.

        Returns:
            True if saved successfully, False otherwise
        """
        with self._lock:
            try:
                self._config_dir.mkdir(parents=True, exist_ok=True)
                with open(self._settings_file, "w", encoding="utf-8") as f:
                    json.dump(self._settings, f, indent=2)
                return True
            except (OSError, PermissionError):
                return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.

        Args:
            key: The setting key to retrieve
            default: Default value if key not found

        Returns:
            The setting value or default
        """
        with self._lock:
            return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """
        Set a setting value and save to file.

        Args:
            key: The setting key to set
            value: The value to store

        Returns:
            True if saved successfully, False otherwise
        """
        with self._lock:
            self._settings[key] = value
        return self.save()

    def reset_to_defaults(self) -> bool:
        """
        Reset all settings to defaults and save.

        Returns:
            True if saved successfully, False otherwise
        """
        with self._lock:
            self._settings = dict(self.DEFAULT_SETTINGS)
        return self.save()

    def get_all(self) -> dict:
        """
        Get a copy of all settings.

        Returns:
            Dictionary with all current settings
        """
        with self._lock:
            return dict(self._settings)