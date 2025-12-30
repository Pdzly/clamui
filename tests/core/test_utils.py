# ClamUI Utils Tests
"""Unit tests for the utils module functions."""

import sys
from unittest import mock

import pytest

# Store original gi modules to restore later (if they exist)
_original_gi = sys.modules.get("gi")
_original_gi_repository = sys.modules.get("gi.repository")

# Mock gi module before importing src.core to avoid GTK dependencies in tests
sys.modules["gi"] = mock.MagicMock()
sys.modules["gi.repository"] = mock.MagicMock()

from src.core.utils import (
    check_clamav_installed,
    check_clamdscan_installed,
    check_freshclam_installed,
    format_scan_path,
    get_clamav_path,
    get_freshclam_path,
    get_path_info,
    validate_dropped_files,
    validate_path,
)

# Restore original gi modules after imports are done
if _original_gi is not None:
    sys.modules["gi"] = _original_gi
else:
    del sys.modules["gi"]
if _original_gi_repository is not None:
    sys.modules["gi.repository"] = _original_gi_repository
else:
    del sys.modules["gi.repository"]


class TestCheckClamdscanInstalled:
    """Tests for the check_clamdscan_installed function."""

    def test_check_clamdscan_installed(self):
        """Test clamdscan check returns (True, version) when installed."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0,
                    stdout="ClamAV 1.2.3/27421/Mon Dec 30 09:00:00 2024\n",
                    stderr="",
                )
                installed, version = check_clamdscan_installed()
                assert installed is True
                assert "ClamAV" in version

    def test_check_clamdscan_not_installed(self):
        """Test clamdscan check returns (False, message) when not installed."""
        with mock.patch("shutil.which", return_value=None):
            installed, message = check_clamdscan_installed()
            assert installed is False
            assert "not installed" in message.lower()

    def test_check_clamdscan_timeout(self):
        """Test clamdscan check handles timeout gracefully."""
        import subprocess

        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired(
                    cmd="clamdscan", timeout=10
                )
                installed, message = check_clamdscan_installed()
                assert installed is False
                assert "timed out" in message.lower()

    def test_check_clamdscan_permission_denied(self):
        """Test clamdscan check handles permission errors gracefully."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = PermissionError("Permission denied")
                installed, message = check_clamdscan_installed()
                assert installed is False
                assert "permission denied" in message.lower()

    def test_check_clamdscan_file_not_found(self):
        """Test clamdscan check handles FileNotFoundError gracefully."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("File not found")
                installed, message = check_clamdscan_installed()
                assert installed is False
                assert "not found" in message.lower()

    def test_check_clamdscan_returns_error(self):
        """Test clamdscan check when command returns non-zero exit code."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=1,
                    stdout="",
                    stderr="Some error occurred",
                )
                installed, message = check_clamdscan_installed()
                assert installed is False
                assert "error" in message.lower()

    def test_check_clamdscan_generic_exception(self):
        """Test clamdscan check handles generic exceptions gracefully."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = Exception("Unexpected error")
                installed, message = check_clamdscan_installed()
                assert installed is False
                assert "error" in message.lower()


class TestCheckClamavInstalled:
    """Tests for the check_clamav_installed function."""

    def test_check_clamav_installed(self):
        """Test clamscan check returns (True, version) when installed."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0,
                    stdout="ClamAV 1.2.3/27421/Mon Dec 30 09:00:00 2024\n",
                    stderr="",
                )
                installed, version = check_clamav_installed()
                assert installed is True
                assert "ClamAV" in version

    def test_check_clamav_not_installed(self):
        """Test clamscan check returns (False, message) when not installed."""
        with mock.patch("shutil.which", return_value=None):
            installed, message = check_clamav_installed()
            assert installed is False
            assert "not installed" in message.lower()


class TestCheckFreshclamInstalled:
    """Tests for the check_freshclam_installed function."""

    def test_check_freshclam_installed(self):
        """Test freshclam check returns (True, version) when installed."""
        with mock.patch("shutil.which", return_value="/usr/bin/freshclam"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0,
                    stdout="ClamAV 1.2.3/27421/Mon Dec 30 09:00:00 2024\n",
                    stderr="",
                )
                installed, version = check_freshclam_installed()
                assert installed is True
                assert "ClamAV" in version

    def test_check_freshclam_not_installed(self):
        """Test freshclam check returns (False, message) when not installed."""
        with mock.patch("shutil.which", return_value=None):
            installed, message = check_freshclam_installed()
            assert installed is False
            assert "not installed" in message.lower()


class TestValidatePath:
    """Tests for the validate_path function."""

    def test_validate_path_empty(self):
        """Test validate_path returns error for empty path."""
        is_valid, error = validate_path("")
        assert is_valid is False
        assert "no path" in error.lower()

    def test_validate_path_whitespace_only(self):
        """Test validate_path returns error for whitespace-only path."""
        is_valid, error = validate_path("   ")
        assert is_valid is False
        assert "no path" in error.lower()

    def test_validate_path_nonexistent(self):
        """Test validate_path returns error for non-existent path."""
        is_valid, error = validate_path("/nonexistent/path/that/does/not/exist")
        assert is_valid is False
        assert "does not exist" in error.lower()

    def test_validate_path_existing_file(self, tmp_path):
        """Test validate_path returns success for existing readable file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        is_valid, error = validate_path(str(test_file))
        assert is_valid is True
        assert error is None

    def test_validate_path_existing_directory(self, tmp_path):
        """Test validate_path returns success for existing readable directory."""
        is_valid, error = validate_path(str(tmp_path))
        assert is_valid is True
        assert error is None


class TestGetClamavPath:
    """Tests for the get_clamav_path function."""

    def test_get_clamav_path_found(self):
        """Test get_clamav_path returns path when clamscan is found."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamscan"):
            path = get_clamav_path()
            assert path == "/usr/bin/clamscan"

    def test_get_clamav_path_not_found(self):
        """Test get_clamav_path returns None when clamscan is not found."""
        with mock.patch("shutil.which", return_value=None):
            path = get_clamav_path()
            assert path is None


class TestGetFreshclamPath:
    """Tests for the get_freshclam_path function."""

    def test_get_freshclam_path_found(self):
        """Test get_freshclam_path returns path when freshclam is found."""
        with mock.patch("shutil.which", return_value="/usr/bin/freshclam"):
            path = get_freshclam_path()
            assert path == "/usr/bin/freshclam"

    def test_get_freshclam_path_not_found(self):
        """Test get_freshclam_path returns None when freshclam is not found."""
        with mock.patch("shutil.which", return_value=None):
            path = get_freshclam_path()
            assert path is None


class TestFormatScanPath:
    """Tests for the format_scan_path function."""

    def test_format_scan_path_empty(self):
        """Test format_scan_path handles empty path."""
        result = format_scan_path("")
        assert "no path" in result.lower()

    def test_format_scan_path_none(self):
        """Test format_scan_path handles None path."""
        result = format_scan_path(None)
        assert "no path" in result.lower()

    def test_format_scan_path_absolute(self, tmp_path):
        """Test format_scan_path handles absolute path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        result = format_scan_path(str(test_file))
        # Should return a valid path string
        assert str(tmp_path) in result or "~" in result


class TestGetPathInfo:
    """Tests for the get_path_info function."""

    def test_get_path_info_empty(self):
        """Test get_path_info handles empty path."""
        info = get_path_info("")
        assert info["type"] == "unknown"
        assert info["exists"] is False
        assert info["readable"] is False

    def test_get_path_info_nonexistent(self):
        """Test get_path_info handles non-existent path."""
        info = get_path_info("/nonexistent/path/that/does/not/exist")
        assert info["exists"] is False

    def test_get_path_info_existing_file(self, tmp_path):
        """Test get_path_info returns correct info for existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        info = get_path_info(str(test_file))
        assert info["type"] == "file"
        assert info["exists"] is True
        assert info["readable"] is True
        assert info["size"] == len("test content")

    def test_get_path_info_existing_directory(self, tmp_path):
        """Test get_path_info returns correct info for existing directory."""
        info = get_path_info(str(tmp_path))
        assert info["type"] == "directory"
        assert info["exists"] is True
        assert info["readable"] is True
        assert info["size"] is None


class TestValidateDroppedFiles:
    """Tests for the validate_dropped_files function."""

    def test_validate_dropped_files_empty_list(self):
        """Test validate_dropped_files returns error for empty list."""
        valid_paths, errors = validate_dropped_files([])
        assert valid_paths == []
        assert len(errors) == 1
        assert "no files" in errors[0].lower()

    def test_validate_dropped_files_valid_file(self, tmp_path):
        """Test validate_dropped_files returns valid path for existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        valid_paths, errors = validate_dropped_files([str(test_file)])
        assert len(valid_paths) == 1
        assert str(test_file.resolve()) in valid_paths[0]
        assert errors == []

    def test_validate_dropped_files_valid_directory(self, tmp_path):
        """Test validate_dropped_files returns valid path for existing directory."""
        valid_paths, errors = validate_dropped_files([str(tmp_path)])
        assert len(valid_paths) == 1
        assert str(tmp_path.resolve()) in valid_paths[0]
        assert errors == []

    def test_validate_dropped_files_multiple_valid(self, tmp_path):
        """Test validate_dropped_files handles multiple valid paths."""
        file1 = tmp_path / "test1.txt"
        file1.write_text("content 1")
        file2 = tmp_path / "test2.txt"
        file2.write_text("content 2")
        valid_paths, errors = validate_dropped_files([str(file1), str(file2)])
        assert len(valid_paths) == 2
        assert errors == []

    def test_validate_dropped_files_none_path_remote(self):
        """Test validate_dropped_files handles None paths (remote files)."""
        valid_paths, errors = validate_dropped_files([None])
        assert valid_paths == []
        assert len(errors) == 1
        assert "remote" in errors[0].lower()

    def test_validate_dropped_files_multiple_none_paths(self):
        """Test validate_dropped_files handles multiple None paths."""
        valid_paths, errors = validate_dropped_files([None, None])
        assert valid_paths == []
        assert len(errors) == 2
        assert all("remote" in error.lower() for error in errors)

    def test_validate_dropped_files_mixed_none_and_valid(self, tmp_path):
        """Test validate_dropped_files handles mixed None and valid paths."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        valid_paths, errors = validate_dropped_files([None, str(test_file)])
        assert len(valid_paths) == 1
        assert len(errors) == 1
        assert "remote" in errors[0].lower()

    def test_validate_dropped_files_nonexistent_path(self):
        """Test validate_dropped_files handles non-existent paths."""
        valid_paths, errors = validate_dropped_files(["/nonexistent/path/that/does/not/exist"])
        assert valid_paths == []
        assert len(errors) == 1
        assert "does not exist" in errors[0].lower()

    def test_validate_dropped_files_mixed_valid_and_invalid(self, tmp_path):
        """Test validate_dropped_files handles mix of valid and invalid paths."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        valid_paths, errors = validate_dropped_files([
            str(test_file),
            "/nonexistent/path",
            None
        ])
        assert len(valid_paths) == 1
        assert len(errors) == 2

    def test_validate_dropped_files_permission_denied(self, tmp_path):
        """Test validate_dropped_files handles permission errors."""
        import os
        import stat

        # Create a file and remove read permissions
        test_file = tmp_path / "unreadable.txt"
        test_file.write_text("test content")

        # Remove read permissions
        original_mode = test_file.stat().st_mode
        test_file.chmod(stat.S_IWUSR)  # Write-only

        try:
            valid_paths, errors = validate_dropped_files([str(test_file)])
            assert valid_paths == []
            assert len(errors) == 1
            assert "permission" in errors[0].lower()
        finally:
            # Restore permissions for cleanup
            test_file.chmod(original_mode)

    def test_validate_dropped_files_unreadable_directory(self, tmp_path):
        """Test validate_dropped_files handles unreadable directories."""
        import os
        import stat

        # Create a directory and remove read permissions
        test_dir = tmp_path / "unreadable_dir"
        test_dir.mkdir()

        # Remove read permissions
        original_mode = test_dir.stat().st_mode
        test_dir.chmod(stat.S_IWUSR | stat.S_IXUSR)  # Write+Execute only

        try:
            valid_paths, errors = validate_dropped_files([str(test_dir)])
            assert valid_paths == []
            assert len(errors) == 1
            assert "permission" in errors[0].lower()
        finally:
            # Restore permissions for cleanup
            test_dir.chmod(original_mode)
