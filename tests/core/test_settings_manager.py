# ClamUI SettingsManager Tests
"""Unit tests for the SettingsManager class."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from src.core.settings_manager import SettingsManager


class TestSettingsManagerInit:
    """Tests for SettingsManager initialization."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_init_creates_settings_with_defaults(self, temp_config_dir):
        """Test that SettingsManager initializes with default settings."""
        manager = SettingsManager(config_dir=temp_config_dir)
        assert manager.get("notifications_enabled") is True

    def test_init_with_custom_config_dir(self, temp_config_dir):
        """Test SettingsManager uses custom config directory."""
        custom_dir = Path(temp_config_dir) / "custom"
        manager = SettingsManager(config_dir=custom_dir)
        assert manager._config_dir == custom_dir

    def test_init_with_default_directory(self, monkeypatch):
        """Test SettingsManager uses XDG_CONFIG_HOME by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("XDG_CONFIG_HOME", tmpdir)
            manager = SettingsManager()
            expected_path = Path(tmpdir) / "clamui"
            assert manager._config_dir == expected_path

    def test_init_with_default_xdg_fallback(self, monkeypatch):
        """Test SettingsManager falls back to ~/.config when XDG_CONFIG_HOME unset."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            # We can't easily test home directory without mocking
            # Just verify no crashes when XDG_CONFIG_HOME is unset
            with mock.patch.object(Path, "expanduser", return_value=Path(tmpdir)):
                manager = SettingsManager()
                assert manager._config_dir is not None

    def test_init_loads_existing_settings(self, temp_config_dir):
        """Test that SettingsManager loads existing settings from file."""
        config_dir = Path(temp_config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        settings_file = config_dir / "settings.json"
        settings_file.write_text(json.dumps({"notifications_enabled": False}))

        manager = SettingsManager(config_dir=config_dir)
        assert manager.get("notifications_enabled") is False


class TestSettingsManagerSaveLoad:
    """Tests for SettingsManager save and load operations."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def settings_manager(self, temp_config_dir):
        """Create a SettingsManager with a temporary directory."""
        return SettingsManager(config_dir=temp_config_dir)

    def test_save_creates_settings_file(self, settings_manager, temp_config_dir):
        """Test that save creates the settings file."""
        result = settings_manager.save()
        assert result is True
        settings_file = Path(temp_config_dir) / "settings.json"
        assert settings_file.exists()

    def test_save_creates_config_directory(self, temp_config_dir):
        """Test that save creates the config directory if it doesn't exist."""
        nested_dir = Path(temp_config_dir) / "nested" / "config"
        manager = SettingsManager(config_dir=nested_dir)
        result = manager.save()
        assert result is True
        assert nested_dir.exists()

    def test_save_writes_json_content(self, settings_manager, temp_config_dir):
        """Test that save writes valid JSON content."""
        settings_manager.set("notifications_enabled", False)
        settings_file = Path(temp_config_dir) / "settings.json"

        with open(settings_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["notifications_enabled"] is False

    def test_load_returns_defaults_when_file_missing(self, temp_config_dir):
        """Test that load returns defaults when settings file is missing."""
        manager = SettingsManager(config_dir=temp_config_dir)
        # Defaults should be loaded
        assert manager.get("notifications_enabled") is True

    def test_load_handles_corrupted_json(self, temp_config_dir):
        """Test that load handles corrupted JSON files gracefully."""
        config_dir = Path(temp_config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        settings_file = config_dir / "settings.json"
        settings_file.write_text("{ invalid json content }")

        manager = SettingsManager(config_dir=config_dir)
        # Should fall back to defaults
        assert manager.get("notifications_enabled") is True

    def test_load_handles_empty_file(self, temp_config_dir):
        """Test that load handles empty files gracefully."""
        config_dir = Path(temp_config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        settings_file = config_dir / "settings.json"
        settings_file.write_text("")

        manager = SettingsManager(config_dir=config_dir)
        # Should fall back to defaults
        assert manager.get("notifications_enabled") is True

    def test_load_merges_with_defaults(self, temp_config_dir):
        """Test that load merges existing settings with defaults."""
        config_dir = Path(temp_config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        settings_file = config_dir / "settings.json"
        # Write a partial settings file (missing notifications_enabled)
        settings_file.write_text(json.dumps({"custom_setting": "value"}))

        manager = SettingsManager(config_dir=config_dir)
        # Default should still be present
        assert manager.get("notifications_enabled") is True
        # Custom setting should also be present
        assert manager.get("custom_setting") == "value"

    def test_settings_persist_across_instances(self, temp_config_dir):
        """Test that settings persist across manager instances."""
        manager1 = SettingsManager(config_dir=temp_config_dir)
        manager1.set("notifications_enabled", False)

        manager2 = SettingsManager(config_dir=temp_config_dir)
        assert manager2.get("notifications_enabled") is False


class TestSettingsManagerGetSet:
    """Tests for SettingsManager get and set operations."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def settings_manager(self, temp_config_dir):
        """Create a SettingsManager with a temporary directory."""
        return SettingsManager(config_dir=temp_config_dir)

    def test_get_returns_default_setting(self, settings_manager):
        """Test get returns default settings."""
        assert settings_manager.get("notifications_enabled") is True

    def test_get_returns_custom_default_for_missing_key(self, settings_manager):
        """Test get returns custom default for missing keys."""
        result = settings_manager.get("nonexistent_key", "custom_default")
        assert result == "custom_default"

    def test_get_returns_none_for_missing_key_without_default(self, settings_manager):
        """Test get returns None for missing keys when no default provided."""
        result = settings_manager.get("nonexistent_key")
        assert result is None

    def test_set_updates_value(self, settings_manager):
        """Test set updates the setting value."""
        settings_manager.set("notifications_enabled", False)
        assert settings_manager.get("notifications_enabled") is False

    def test_set_returns_save_result(self, settings_manager):
        """Test set returns the result of save operation."""
        result = settings_manager.set("notifications_enabled", False)
        assert result is True

    def test_set_creates_new_settings(self, settings_manager):
        """Test set can create new setting keys."""
        settings_manager.set("new_setting", "new_value")
        assert settings_manager.get("new_setting") == "new_value"

    def test_set_handles_different_value_types(self, settings_manager):
        """Test set handles various value types correctly."""
        # String
        settings_manager.set("string_setting", "hello")
        assert settings_manager.get("string_setting") == "hello"

        # Integer
        settings_manager.set("int_setting", 42)
        assert settings_manager.get("int_setting") == 42

        # Float
        settings_manager.set("float_setting", 3.14)
        assert settings_manager.get("float_setting") == 3.14

        # Boolean
        settings_manager.set("bool_setting", True)
        assert settings_manager.get("bool_setting") is True

        # List
        settings_manager.set("list_setting", [1, 2, 3])
        assert settings_manager.get("list_setting") == [1, 2, 3]

        # Dictionary
        settings_manager.set("dict_setting", {"key": "value"})
        assert settings_manager.get("dict_setting") == {"key": "value"}

    def test_set_persists_to_file(self, settings_manager, temp_config_dir):
        """Test that set persists changes to file."""
        settings_manager.set("test_key", "test_value")

        # Read directly from file
        settings_file = Path(temp_config_dir) / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["test_key"] == "test_value"


class TestSettingsManagerResetAndGetAll:
    """Tests for SettingsManager reset_to_defaults and get_all methods."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def settings_manager(self, temp_config_dir):
        """Create a SettingsManager with a temporary directory."""
        return SettingsManager(config_dir=temp_config_dir)

    def test_reset_to_defaults_clears_custom_settings(self, settings_manager):
        """Test that reset_to_defaults removes custom settings."""
        settings_manager.set("custom_setting", "custom_value")
        settings_manager.reset_to_defaults()

        assert settings_manager.get("custom_setting") is None

    def test_reset_to_defaults_restores_default_values(self, settings_manager):
        """Test that reset_to_defaults restores default values."""
        settings_manager.set("notifications_enabled", False)
        settings_manager.reset_to_defaults()

        assert settings_manager.get("notifications_enabled") is True

    def test_reset_to_defaults_returns_save_result(self, settings_manager):
        """Test that reset_to_defaults returns the save result."""
        result = settings_manager.reset_to_defaults()
        assert result is True

    def test_reset_to_defaults_persists_to_file(self, settings_manager, temp_config_dir):
        """Test that reset_to_defaults persists changes to file."""
        settings_manager.set("custom_setting", "custom_value")
        settings_manager.reset_to_defaults()

        # Create a new instance to verify persistence
        new_manager = SettingsManager(config_dir=temp_config_dir)
        assert new_manager.get("custom_setting") is None
        assert new_manager.get("notifications_enabled") is True

    def test_get_all_returns_copy(self, settings_manager):
        """Test that get_all returns a copy of settings."""
        all_settings = settings_manager.get_all()
        # Modify the returned dict
        all_settings["notifications_enabled"] = False
        # Original should be unchanged
        assert settings_manager.get("notifications_enabled") is True

    def test_get_all_contains_all_settings(self, settings_manager):
        """Test that get_all contains all current settings."""
        settings_manager.set("custom_key", "custom_value")
        all_settings = settings_manager.get_all()

        assert "notifications_enabled" in all_settings
        assert "custom_key" in all_settings
        assert all_settings["custom_key"] == "custom_value"


class TestSettingsManagerErrorHandling:
    """Tests for SettingsManager error handling."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_save_handles_permission_error(self, temp_config_dir):
        """Test that save handles permission errors gracefully."""
        manager = SettingsManager(config_dir=temp_config_dir)

        with mock.patch("builtins.open", side_effect=PermissionError):
            result = manager.save()
            assert result is False

    def test_save_handles_os_error(self, temp_config_dir):
        """Test that save handles OS errors gracefully."""
        manager = SettingsManager(config_dir=temp_config_dir)

        with mock.patch("builtins.open", side_effect=OSError("Test error")):
            result = manager.save()
            assert result is False

    def test_set_returns_false_on_save_failure(self, temp_config_dir):
        """Test that set returns False when save fails."""
        manager = SettingsManager(config_dir=temp_config_dir)

        with mock.patch.object(manager, "save", return_value=False):
            result = manager.set("key", "value")
            assert result is False

    def test_load_handles_permission_error_on_read(self, temp_config_dir):
        """Test that load handles permission errors when reading file."""
        config_dir = Path(temp_config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        settings_file = config_dir / "settings.json"
        settings_file.write_text(json.dumps({"notifications_enabled": False}))

        with mock.patch("builtins.open", side_effect=PermissionError):
            manager = SettingsManager(config_dir=config_dir)
            # Should fall back to defaults
            assert manager.get("notifications_enabled") is True


class TestSettingsManagerThreadSafety:
    """Tests for thread safety in SettingsManager."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def settings_manager(self, temp_config_dir):
        """Create a SettingsManager with a temporary directory."""
        return SettingsManager(config_dir=temp_config_dir)

    def test_concurrent_get_operations(self, settings_manager):
        """Test that concurrent get operations are thread-safe."""
        import threading

        results = []
        errors = []

        def get_setting(index):
            try:
                value = settings_manager.get("notifications_enabled")
                results.append((index, value))
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(20):
            t = threading.Thread(target=get_setting, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20
        # All results should be True (the default)
        for _, value in results:
            assert value is True

    def test_concurrent_set_operations(self, settings_manager):
        """Test that concurrent set operations are thread-safe."""
        import threading

        errors = []

        def set_setting(index):
            try:
                # Alternate between True and False
                value = index % 2 == 0
                settings_manager.set(f"concurrent_key_{index}", value)
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(20):
            t = threading.Thread(target=set_setting, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0

        # Verify all values were set correctly
        for i in range(20):
            expected = i % 2 == 0
            assert settings_manager.get(f"concurrent_key_{i}") == expected

    def test_concurrent_read_write_operations(self, settings_manager):
        """Test that concurrent read and write operations don't corrupt data."""
        import threading

        errors = []
        read_results = []

        def write_setting(index):
            try:
                settings_manager.set("shared_key", f"value_{index}")
            except Exception as e:
                errors.append(f"Write error: {e}")

        def read_setting(index):
            try:
                value = settings_manager.get("shared_key")
                read_results.append(value)
            except Exception as e:
                errors.append(f"Read error: {e}")

        threads = []
        for i in range(10):
            t = threading.Thread(target=write_setting, args=(i,))
            threads.append(t)
            t = threading.Thread(target=read_setting, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        # All read values should be either None (not yet set) or a valid value
        for value in read_results:
            assert value is None or value.startswith("value_")


class TestSettingsManagerDefaults:
    """Tests for SettingsManager DEFAULT_SETTINGS."""

    def test_default_settings_has_notifications_enabled(self):
        """Test that DEFAULT_SETTINGS contains notifications_enabled."""
        assert "notifications_enabled" in SettingsManager.DEFAULT_SETTINGS
        assert SettingsManager.DEFAULT_SETTINGS["notifications_enabled"] is True

    def test_default_settings_is_not_modified(self):
        """Test that DEFAULT_SETTINGS is not modified by operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_defaults = dict(SettingsManager.DEFAULT_SETTINGS)
            manager = SettingsManager(config_dir=tmpdir)
            manager.set("notifications_enabled", False)
            manager.set("new_key", "new_value")

            # DEFAULT_SETTINGS should be unchanged
            assert SettingsManager.DEFAULT_SETTINGS == original_defaults


class TestSettingsExclusions:
    """Tests for exclusion_patterns settings persistence."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def settings_manager(self, temp_config_dir):
        """Create a SettingsManager with a temporary directory."""
        return SettingsManager(config_dir=temp_config_dir)

    def test_default_exclusion_patterns_is_empty_list(self, settings_manager):
        """Test that default exclusion_patterns is an empty list."""
        patterns = settings_manager.get("exclusion_patterns")
        assert patterns == []
        assert isinstance(patterns, list)

    def test_default_settings_has_exclusion_patterns(self):
        """Test that DEFAULT_SETTINGS contains exclusion_patterns."""
        assert "exclusion_patterns" in SettingsManager.DEFAULT_SETTINGS
        assert SettingsManager.DEFAULT_SETTINGS["exclusion_patterns"] == []

    def test_set_exclusion_patterns_single_pattern(self, settings_manager):
        """Test setting a single exclusion pattern."""
        pattern = {
            "pattern": "*.log",
            "type": "pattern",
            "enabled": True
        }
        settings_manager.set("exclusion_patterns", [pattern])

        patterns = settings_manager.get("exclusion_patterns")
        assert len(patterns) == 1
        assert patterns[0]["pattern"] == "*.log"
        assert patterns[0]["type"] == "pattern"
        assert patterns[0]["enabled"] is True

    def test_set_exclusion_patterns_multiple_patterns(self, settings_manager):
        """Test setting multiple exclusion patterns."""
        patterns = [
            {"pattern": "node_modules", "type": "directory", "enabled": True},
            {"pattern": ".git", "type": "directory", "enabled": True},
            {"pattern": "*.log", "type": "pattern", "enabled": False},
        ]
        settings_manager.set("exclusion_patterns", patterns)

        retrieved = settings_manager.get("exclusion_patterns")
        assert len(retrieved) == 3
        assert retrieved[0]["pattern"] == "node_modules"
        assert retrieved[1]["pattern"] == ".git"
        assert retrieved[2]["pattern"] == "*.log"
        assert retrieved[2]["enabled"] is False

    def test_exclusion_patterns_persist_to_file(self, settings_manager, temp_config_dir):
        """Test that exclusion patterns persist to the settings file."""
        patterns = [
            {"pattern": "*.tmp", "type": "file", "enabled": True},
            {"pattern": "__pycache__", "type": "directory", "enabled": True},
        ]
        settings_manager.set("exclusion_patterns", patterns)

        # Read directly from file
        settings_file = Path(temp_config_dir) / "settings.json"
        with open(settings_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "exclusion_patterns" in data
        assert len(data["exclusion_patterns"]) == 2
        assert data["exclusion_patterns"][0]["pattern"] == "*.tmp"
        assert data["exclusion_patterns"][1]["pattern"] == "__pycache__"

    def test_exclusion_patterns_persist_across_instances(self, temp_config_dir):
        """Test that exclusion patterns persist across manager instances."""
        patterns = [
            {"pattern": ".venv", "type": "directory", "enabled": True},
            {"pattern": "build", "type": "directory", "enabled": False},
        ]

        manager1 = SettingsManager(config_dir=temp_config_dir)
        manager1.set("exclusion_patterns", patterns)

        manager2 = SettingsManager(config_dir=temp_config_dir)
        retrieved = manager2.get("exclusion_patterns")

        assert len(retrieved) == 2
        assert retrieved[0]["pattern"] == ".venv"
        assert retrieved[0]["enabled"] is True
        assert retrieved[1]["pattern"] == "build"
        assert retrieved[1]["enabled"] is False

    def test_exclusion_patterns_load_from_existing_file(self, temp_config_dir):
        """Test loading exclusion patterns from an existing settings file."""
        config_dir = Path(temp_config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        settings_file = config_dir / "settings.json"

        existing_data = {
            "notifications_enabled": True,
            "exclusion_patterns": [
                {"pattern": "dist", "type": "directory", "enabled": True}
            ]
        }
        settings_file.write_text(json.dumps(existing_data))

        manager = SettingsManager(config_dir=config_dir)
        patterns = manager.get("exclusion_patterns")

        assert len(patterns) == 1
        assert patterns[0]["pattern"] == "dist"

    def test_exclusion_patterns_empty_list_after_clear(self, settings_manager):
        """Test clearing exclusion patterns to an empty list."""
        patterns = [{"pattern": "*.log", "type": "pattern", "enabled": True}]
        settings_manager.set("exclusion_patterns", patterns)

        # Clear patterns
        settings_manager.set("exclusion_patterns", [])
        retrieved = settings_manager.get("exclusion_patterns")

        assert retrieved == []

    def test_exclusion_patterns_all_types(self, settings_manager):
        """Test all three exclusion pattern types."""
        patterns = [
            {"pattern": "/path/to/file.txt", "type": "file", "enabled": True},
            {"pattern": "node_modules", "type": "directory", "enabled": True},
            {"pattern": "*.log", "type": "pattern", "enabled": True},
        ]
        settings_manager.set("exclusion_patterns", patterns)

        retrieved = settings_manager.get("exclusion_patterns")
        assert retrieved[0]["type"] == "file"
        assert retrieved[1]["type"] == "directory"
        assert retrieved[2]["type"] == "pattern"

    def test_exclusion_patterns_enabled_toggle(self, settings_manager):
        """Test toggling enabled state of exclusion patterns."""
        patterns = [{"pattern": "*.log", "type": "pattern", "enabled": True}]
        settings_manager.set("exclusion_patterns", patterns)

        # Toggle to disabled
        patterns[0]["enabled"] = False
        settings_manager.set("exclusion_patterns", patterns)

        retrieved = settings_manager.get("exclusion_patterns")
        assert retrieved[0]["enabled"] is False

        # Toggle back to enabled
        patterns[0]["enabled"] = True
        settings_manager.set("exclusion_patterns", patterns)

        retrieved = settings_manager.get("exclusion_patterns")
        assert retrieved[0]["enabled"] is True

    def test_exclusion_patterns_reset_to_defaults(self, settings_manager):
        """Test that reset_to_defaults clears exclusion patterns."""
        patterns = [{"pattern": "*.log", "type": "pattern", "enabled": True}]
        settings_manager.set("exclusion_patterns", patterns)

        settings_manager.reset_to_defaults()

        retrieved = settings_manager.get("exclusion_patterns")
        assert retrieved == []

    def test_exclusion_patterns_in_get_all(self, settings_manager):
        """Test that exclusion_patterns appears in get_all output."""
        patterns = [{"pattern": "*.tmp", "type": "file", "enabled": True}]
        settings_manager.set("exclusion_patterns", patterns)

        all_settings = settings_manager.get_all()

        assert "exclusion_patterns" in all_settings
        assert len(all_settings["exclusion_patterns"]) == 1
        assert all_settings["exclusion_patterns"][0]["pattern"] == "*.tmp"

    def test_exclusion_patterns_merge_with_defaults(self, temp_config_dir):
        """Test that exclusion_patterns merges correctly when file has partial settings."""
        config_dir = Path(temp_config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        settings_file = config_dir / "settings.json"

        # Write settings without exclusion_patterns
        settings_file.write_text(json.dumps({"notifications_enabled": False}))

        manager = SettingsManager(config_dir=config_dir)

        # Should get default empty list
        assert manager.get("exclusion_patterns") == []
        # Other settings should be from file
        assert manager.get("notifications_enabled") is False

    def test_exclusion_patterns_special_characters(self, settings_manager):
        """Test exclusion patterns with special characters."""
        patterns = [
            {"pattern": "path with spaces", "type": "directory", "enabled": True},
            {"pattern": "file[1-9].txt", "type": "pattern", "enabled": True},
            {"pattern": "special_chars!@#", "type": "file", "enabled": True},
        ]
        settings_manager.set("exclusion_patterns", patterns)

        retrieved = settings_manager.get("exclusion_patterns")
        assert retrieved[0]["pattern"] == "path with spaces"
        assert retrieved[1]["pattern"] == "file[1-9].txt"
        assert retrieved[2]["pattern"] == "special_chars!@#"

    def test_exclusion_patterns_preset_development_directories(self, settings_manager):
        """Test saving common development directory exclusion presets."""
        preset_patterns = [
            {"pattern": "node_modules", "type": "directory", "enabled": True},
            {"pattern": ".git", "type": "directory", "enabled": True},
            {"pattern": ".venv", "type": "directory", "enabled": True},
            {"pattern": "build", "type": "directory", "enabled": True},
            {"pattern": "dist", "type": "directory", "enabled": True},
            {"pattern": "__pycache__", "type": "directory", "enabled": True},
        ]
        settings_manager.set("exclusion_patterns", preset_patterns)

        retrieved = settings_manager.get("exclusion_patterns")
        assert len(retrieved) == 6
        pattern_names = [p["pattern"] for p in retrieved]
        assert "node_modules" in pattern_names
        assert ".git" in pattern_names
        assert ".venv" in pattern_names
        assert "__pycache__" in pattern_names
