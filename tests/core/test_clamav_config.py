# ClamUI ClamAV Config Tests
"""Unit tests for the ClamAV configuration module."""

import contextlib
import os
import stat
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

from src.core.clamav_config import (
    ClamAVConfig,
    ClamAVConfigValue,
    parse_config,
    validate_option,
    write_config,
)


class TestBackupConfig:
    """Tests for the backup_config function."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".conf", delete=False, encoding="utf-8"
        ) as f:
            f.write("# Test ClamAV config file\n")
            f.write("DatabaseDirectory /var/lib/clamav\n")
            f.write("LogVerbose yes\n")
            temp_path = f.name
        yield temp_path
        # Cleanup
        try:
            Path(temp_path).unlink(missing_ok=True)
            # Also cleanup any backup files
            for backup in Path(temp_path).parent.glob(f"{Path(temp_path).name}.backup.*"):
                backup.unlink(missing_ok=True)
        except (OSError, PermissionError):
            pass

    def test_backup_creates_timestamped_file(self, temp_config_file):
        """Test that backup_config creates a file with timestamp in name."""
        success, result = backup_config(temp_config_file)

        assert success is True
        assert ".backup." in result
        assert Path(result).exists()

        # Verify timestamp format (YYYYMMDD_HHMMSS)
        backup_suffix = result.split(".backup.")[-1]
        assert len(backup_suffix) == 15  # YYYYMMDD_HHMMSS
        assert backup_suffix[8] == "_"

    def test_backup_preserves_content(self, temp_config_file):
        """Test that backup file has identical content to original."""
        success, backup_path = backup_config(temp_config_file)

        assert success is True

        with open(temp_config_file) as f:
            original_content = f.read()
        with open(backup_path) as f:
            backup_content = f.read()

        assert original_content == backup_content

    def test_backup_preserves_metadata(self, temp_config_file):
        """Test that backup preserves file metadata (mode, timestamps)."""
        # Set specific modification time on original
        original_stat = os.stat(temp_config_file)

        success, backup_path = backup_config(temp_config_file)

        assert success is True

        backup_stat = os.stat(backup_path)
        # shutil.copy2 preserves mode and modification time
        assert stat.S_IMODE(original_stat.st_mode) == stat.S_IMODE(backup_stat.st_mode)
        # Modification time should be preserved (with some tolerance)
        assert abs(original_stat.st_mtime - backup_stat.st_mtime) < 1.0

    def test_backup_returns_correct_path(self, temp_config_file):
        """Test that backup returns the actual path to the backup file."""
        success, backup_path = backup_config(temp_config_file)

        assert success is True
        assert backup_path.startswith(temp_config_file)
        assert Path(backup_path).is_file()

    def test_backup_creates_unique_filenames(self, temp_config_file):
        """Test that multiple backups create unique filenames."""
        success1, backup1 = backup_config(temp_config_file)
        time.sleep(1.1)  # Wait to ensure different timestamp
        success2, backup2 = backup_config(temp_config_file)

        assert success1 is True
        assert success2 is True
        assert backup1 != backup2
        assert Path(backup1).exists()
        assert Path(backup2).exists()

    def test_backup_empty_path_fails(self):
        """Test that backup fails gracefully with empty path."""
        success, error = backup_config("")

        assert success is False
        assert "no configuration file path" in error.lower()

    def test_backup_whitespace_path_fails(self):
        """Test that backup fails gracefully with whitespace-only path."""
        success, error = backup_config("   ")

        assert success is False
        assert "no configuration file path" in error.lower()

    def test_backup_nonexistent_file_fails(self):
        """Test that backup fails gracefully for non-existent file."""
        success, error = backup_config("/nonexistent/path/config.conf")

        assert success is False
        assert "not found" in error.lower()

    def test_backup_directory_fails(self, tmp_path):
        """Test that backup fails gracefully when path is a directory."""
        success, error = backup_config(str(tmp_path))

        assert success is False
        assert "not a file" in error.lower()

    def test_backup_permission_denied_read(self, temp_config_file):
        """Test that backup fails gracefully when file is not readable."""
        # Remove read permission
        os.chmod(temp_config_file, 0o000)

        try:
            success, error = backup_config(temp_config_file)

            assert success is False
            assert "permission denied" in error.lower() or "cannot read" in error.lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_config_file, 0o644)

    def test_backup_permission_denied_write(self, temp_config_file):
        """Test that backup fails gracefully when destination not writable."""
        # Mock shutil.copy2 to raise PermissionError
        with mock.patch("shutil.copy2") as mock_copy:
            mock_copy.side_effect = PermissionError("Permission denied")

            success, error = backup_config(temp_config_file)

            assert success is False
            assert "permission denied" in error.lower()

    def test_backup_handles_oserror(self, temp_config_file):
        """Test that backup handles OSError gracefully."""
        with mock.patch("shutil.copy2") as mock_copy:
            mock_copy.side_effect = OSError("Disk full")

            success, error = backup_config(temp_config_file)

            assert success is False
            assert "disk full" in error.lower() or "failed to create backup" in error.lower()

    def test_backup_handles_unexpected_error(self, temp_config_file):
        """Test that backup handles unexpected exceptions gracefully."""
        with mock.patch("shutil.copy2") as mock_copy:
            mock_copy.side_effect = RuntimeError("Unexpected error")

            success, error = backup_config(temp_config_file)

            assert success is False
            assert "unexpected error" in error.lower()


class TestClamAVConfigValue:
    """Tests for the ClamAVConfigValue dataclass."""

    def test_create_default_values(self):
        """Test ClamAVConfigValue with default values."""
        config_value = ClamAVConfigValue(value="test")

        assert config_value.value == "test"
        assert config_value.comment is None
        assert config_value.line_number == 0

    def test_create_with_all_fields(self):
        """Test ClamAVConfigValue with all fields specified."""
        config_value = ClamAVConfigValue(
            value="/var/lib/clamav", comment="Database directory", line_number=5
        )

        assert config_value.value == "/var/lib/clamav"
        assert config_value.comment == "Database directory"
        assert config_value.line_number == 5


class TestClamAVConfig:
    """Tests for the ClamAVConfig dataclass."""

    def test_create_empty_config(self):
        """Test creating an empty ClamAVConfig."""
        config = ClamAVConfig(file_path=Path("/etc/clamav/freshclam.conf"))

        assert config.file_path == Path("/etc/clamav/freshclam.conf")
        assert config.values == {}
        assert config.raw_lines == []

    def test_get_value_existing(self):
        """Test get_value for existing key."""
        config = ClamAVConfig(file_path=Path("/test"))
        config.values["DatabaseDirectory"] = [ClamAVConfigValue(value="/var/lib/clamav")]

        assert config.get_value("DatabaseDirectory") == "/var/lib/clamav"

    def test_get_value_missing(self):
        """Test get_value for missing key."""
        config = ClamAVConfig(file_path=Path("/test"))

        assert config.get_value("NonExistent") is None

    def test_get_values_multiple(self):
        """Test get_values for multi-value option."""
        config = ClamAVConfig(file_path=Path("/test"))
        config.values["DatabaseMirror"] = [
            ClamAVConfigValue(value="database.clamav.net"),
            ClamAVConfigValue(value="db.local.clamav.net"),
        ]

        values = config.get_values("DatabaseMirror")
        assert len(values) == 2
        assert "database.clamav.net" in values
        assert "db.local.clamav.net" in values

    def test_set_value(self):
        """Test set_value replaces existing values."""
        config = ClamAVConfig(file_path=Path("/test"))
        config.values["LogVerbose"] = [ClamAVConfigValue(value="no")]

        config.set_value("LogVerbose", "yes")

        assert config.get_value("LogVerbose") == "yes"
        assert len(config.values["LogVerbose"]) == 1

    def test_add_value(self):
        """Test add_value appends to existing values."""
        config = ClamAVConfig(file_path=Path("/test"))
        config.add_value("DatabaseMirror", "mirror1.clamav.net")
        config.add_value("DatabaseMirror", "mirror2.clamav.net")

        values = config.get_values("DatabaseMirror")
        assert len(values) == 2

    def test_has_key_true(self):
        """Test has_key returns True for existing key."""
        config = ClamAVConfig(file_path=Path("/test"))
        config.set_value("LogVerbose", "yes")

        assert config.has_key("LogVerbose") is True

    def test_has_key_false(self):
        """Test has_key returns False for missing key."""
        config = ClamAVConfig(file_path=Path("/test"))

        assert config.has_key("NonExistent") is False

    def test_get_bool_yes(self):
        """Test get_bool returns True for 'yes'."""
        config = ClamAVConfig(file_path=Path("/test"))
        config.set_value("LogVerbose", "yes")

        assert config.get_bool("LogVerbose") is True

    def test_get_bool_no(self):
        """Test get_bool returns False for 'no'."""
        config = ClamAVConfig(file_path=Path("/test"))
        config.set_value("LogVerbose", "no")

        assert config.get_bool("LogVerbose") is False

    def test_get_bool_missing(self):
        """Test get_bool returns None for missing key."""
        config = ClamAVConfig(file_path=Path("/test"))

        assert config.get_bool("LogVerbose") is None

    def test_get_int_valid(self):
        """Test get_int returns integer for valid value."""
        config = ClamAVConfig(file_path=Path("/test"))
        config.set_value("Checks", "24")

        assert config.get_int("Checks") == 24

    def test_get_int_invalid(self):
        """Test get_int returns None for non-integer value."""
        config = ClamAVConfig(file_path=Path("/test"))
        config.set_value("Checks", "invalid")

        assert config.get_int("Checks") is None


class TestParseConfig:
    """Tests for the parse_config function."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".conf", delete=False, encoding="utf-8"
        ) as f:
            f.write("# ClamAV configuration\n")
            f.write("DatabaseDirectory /var/lib/clamav\n")
            f.write("LogVerbose yes\n")
            f.write("\n")
            f.write("Checks 24\n")
            temp_path = f.name
        yield temp_path
        with contextlib.suppress(OSError, PermissionError):
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_valid_config(self, temp_config_file):
        """Test parsing a valid config file."""
        config, error = parse_config(temp_config_file)

        assert error is None
        assert config is not None
        assert config.get_value("DatabaseDirectory") == "/var/lib/clamav"
        assert config.get_value("LogVerbose") == "yes"
        assert config.get_value("Checks") == "24"

    def test_parse_empty_path(self):
        """Test parse_config with empty path."""
        config, error = parse_config("")

        assert config is None
        assert "no configuration file path" in error.lower()

    def test_parse_nonexistent_file(self):
        """Test parse_config with non-existent file."""
        config, error = parse_config("/nonexistent/config.conf")

        assert config is None
        assert "not found" in error.lower()

    def test_parse_directory_fails(self, tmp_path):
        """Test parse_config fails for directory path."""
        config, error = parse_config(str(tmp_path))

        assert config is None
        assert "not a file" in error.lower()

    def test_parse_preserves_raw_lines(self, temp_config_file):
        """Test that parse_config preserves raw lines."""
        config, error = parse_config(temp_config_file)

        assert error is None
        assert len(config.raw_lines) > 0


class TestValidateConfigValue:
    """Tests for the validate_config_value function."""

    def test_validate_path_valid(self):
        """Test validation passes for valid absolute path."""
        is_valid, error = validate_config_value("DatabaseDirectory", "/var/lib/clamav")

        assert is_valid is True
        assert error is None

    def test_validate_path_invalid_relative(self):
        """Test validation fails for relative path."""
        is_valid, error = validate_config_value("DatabaseDirectory", "var/lib/clamav")

        assert is_valid is False
        assert "absolute" in error.lower()

    def test_validate_integer_valid(self):
        """Test validation passes for valid integer in range."""
        is_valid, error = validate_config_value("Checks", "24")

        assert is_valid is True
        assert error is None

    def test_validate_integer_out_of_range(self):
        """Test validation fails for integer out of range."""
        is_valid, error = validate_config_value("Checks", "100")

        assert is_valid is False
        assert "at most" in error.lower()

    def test_validate_boolean_valid(self):
        """Test validation passes for valid boolean."""
        is_valid, error = validate_config_value("LogVerbose", "yes")

        assert is_valid is True
        assert error is None

    def test_validate_boolean_invalid(self):
        """Test validation fails for invalid boolean."""
        is_valid, error = validate_config_value("LogVerbose", "maybe")

        assert is_valid is False
        assert "invalid boolean" in error.lower()

    def test_validate_size_valid(self):
        """Test validation passes for valid size value."""
        is_valid, error = validate_config_value("MaxScanSize", "100M")

        assert is_valid is True
        assert error is None

    def test_validate_unknown_key(self):
        """Test validation for unknown configuration key."""
        is_valid, error = validate_config_value("UnknownKey", "value")

        assert is_valid is False
        assert "unknown" in error.lower()