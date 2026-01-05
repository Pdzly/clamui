# ClamUI Path Validation Tests
"""Unit tests for the path_validation module functions."""

import stat
from pathlib import Path
from unittest import mock

import pytest

from src.core.path_validation import (
    check_symlink_safety,
    format_scan_path,
    get_path_info,
    validate_dropped_files,
    validate_path,
)


class TestCheckSymlinkSafety:
    """Tests for the check_symlink_safety function."""

    def test_check_symlink_safety_not_a_symlink(self, tmp_path):
        """Test check_symlink_safety returns (True, None) for regular file."""
        test_file = tmp_path / "regular.txt"
        test_file.write_text("test content")

        is_safe, message = check_symlink_safety(test_file)
        assert is_safe is True
        assert message is None

    def test_check_symlink_safety_not_a_symlink_directory(self, tmp_path):
        """Test check_symlink_safety returns (True, None) for regular directory."""
        is_safe, message = check_symlink_safety(tmp_path)
        assert is_safe is True
        assert message is None

    def test_check_symlink_safety_safe_symlink_in_user_dir(self, tmp_path):
        """Test check_symlink_safety returns (True, warning) for safe symlink in user directory."""
        # Create a file in the user's directory
        target_file = tmp_path / "target.txt"
        target_file.write_text("target content")

        # Create a symlink to it in the same user directory
        symlink_file = tmp_path / "symlink.txt"
        symlink_file.symlink_to(target_file)

        is_safe, message = check_symlink_safety(symlink_file)
        assert is_safe is True
        assert message is not None
        assert "symlink" in message.lower()
        assert str(target_file) in message

    def test_check_symlink_safety_symlink_to_nonexistent_target(self, tmp_path):
        """Test check_symlink_safety returns (False, error) when symlink target doesn't exist."""
        # Create a symlink to a non-existent target
        symlink_file = tmp_path / "broken_symlink.txt"
        target_file = tmp_path / "nonexistent.txt"
        symlink_file.symlink_to(target_file)

        is_safe, message = check_symlink_safety(symlink_file)
        assert is_safe is False
        assert message is not None
        assert "does not exist" in message.lower()

    def test_check_symlink_safety_escapes_to_protected_dir(self, tmp_path):
        """Test check_symlink_safety detects symlink escaping to protected directory."""
        # Create a symlink that appears to be in /home but points to /etc
        # We'll mock the path resolution to simulate this
        symlink_path = Path("/home/user/malicious_link")

        with mock.patch.object(Path, "is_symlink", return_value=True):
            with mock.patch.object(Path, "resolve", return_value=Path("/etc/passwd")):
                with mock.patch.object(Path, "exists", return_value=True):
                    # Mock parent.resolve() to return /home/user
                    with mock.patch.object(Path, "parent", new_callable=mock.PropertyMock) as mock_parent:
                        mock_parent_obj = mock.MagicMock()
                        mock_parent_obj.resolve.return_value = Path("/home/user")
                        mock_parent.return_value = mock_parent_obj

                        is_safe, message = check_symlink_safety(symlink_path)
                        assert is_safe is False
                        assert message is not None
                        assert "protected directory" in message.lower()

    def test_check_symlink_safety_escapes_to_var(self, tmp_path):
        """Test check_symlink_safety detects symlink escaping to /var."""
        symlink_path = Path("/home/user/malicious_link")

        with mock.patch.object(Path, "is_symlink", return_value=True):
            with mock.patch.object(Path, "resolve", return_value=Path("/var/log/sensitive.log")):
                with mock.patch.object(Path, "exists", return_value=True):
                    with mock.patch.object(Path, "parent", new_callable=mock.PropertyMock) as mock_parent:
                        mock_parent_obj = mock.MagicMock()
                        mock_parent_obj.resolve.return_value = Path("/home/user")
                        mock_parent.return_value = mock_parent_obj

                        is_safe, message = check_symlink_safety(symlink_path)
                        assert is_safe is False
                        assert message is not None
                        assert "protected directory" in message.lower()

    def test_check_symlink_safety_escapes_to_usr(self, tmp_path):
        """Test check_symlink_safety detects symlink escaping to /usr."""
        symlink_path = Path("/tmp/malicious_link")

        with mock.patch.object(Path, "is_symlink", return_value=True):
            with mock.patch.object(Path, "resolve", return_value=Path("/usr/bin/bash")):
                with mock.patch.object(Path, "exists", return_value=True):
                    with mock.patch.object(Path, "parent", new_callable=mock.PropertyMock) as mock_parent:
                        mock_parent_obj = mock.MagicMock()
                        mock_parent_obj.resolve.return_value = Path("/tmp")
                        mock_parent.return_value = mock_parent_obj

                        is_safe, message = check_symlink_safety(symlink_path)
                        assert is_safe is False
                        assert message is not None
                        assert "protected directory" in message.lower()

    def test_check_symlink_safety_symlink_outside_user_dirs(self, tmp_path):
        """Test check_symlink_safety allows symlinks outside user directories."""
        # Symlink in /opt pointing to /srv should be allowed (both are non-user dirs)
        symlink_path = Path("/opt/app/link")

        with mock.patch.object(Path, "is_symlink", return_value=True):
            with mock.patch.object(Path, "resolve", return_value=Path("/srv/data/file.txt")):
                with mock.patch.object(Path, "exists", return_value=True):
                    with mock.patch.object(Path, "parent", new_callable=mock.PropertyMock) as mock_parent:
                        mock_parent_obj = mock.MagicMock()
                        mock_parent_obj.resolve.return_value = Path("/opt/app")
                        mock_parent.return_value = mock_parent_obj

                        is_safe, message = check_symlink_safety(symlink_path)
                        assert is_safe is True
                        assert message is not None
                        assert "symlink" in message.lower()

    def test_check_symlink_safety_oserror(self, tmp_path):
        """Test check_symlink_safety handles OSError gracefully."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with mock.patch.object(Path, "is_symlink", side_effect=OSError("Permission denied")):
            is_safe, message = check_symlink_safety(test_file)
            assert is_safe is False
            assert message is not None
            assert "error" in message.lower()

    def test_check_symlink_safety_runtimeerror(self, tmp_path):
        """Test check_symlink_safety handles RuntimeError gracefully."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with mock.patch.object(Path, "is_symlink", side_effect=RuntimeError("Symlink loop")):
            is_safe, message = check_symlink_safety(test_file)
            assert is_safe is False
            assert message is not None
            assert "error" in message.lower()

    def test_check_symlink_safety_symlink_within_home(self, tmp_path):
        """Test check_symlink_safety allows symlinks within home directory."""
        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Create target file in subdirectory
        target_file = subdir / "target.txt"
        target_file.write_text("target content")

        # Create symlink in parent directory pointing to subdirectory file
        symlink_file = tmp_path / "link_to_subdir_file.txt"
        symlink_file.symlink_to(target_file)

        is_safe, message = check_symlink_safety(symlink_file)
        assert is_safe is True
        assert message is not None
        assert "symlink" in message.lower()


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

    def test_validate_path_dangerous_symlink(self, tmp_path):
        """Test validate_path rejects dangerous symlinks."""
        # Create a broken symlink
        symlink_file = tmp_path / "broken_symlink.txt"
        target_file = tmp_path / "nonexistent.txt"
        symlink_file.symlink_to(target_file)

        is_valid, error = validate_path(str(symlink_file))
        assert is_valid is False
        assert error is not None

    def test_validate_path_permission_denied_file(self, tmp_path):
        """Test validate_path handles permission denied for files."""
        # Create a file and remove read permissions
        test_file = tmp_path / "unreadable.txt"
        test_file.write_text("test content")

        # Remove read permissions
        original_mode = test_file.stat().st_mode
        test_file.chmod(stat.S_IWUSR)  # Write-only

        try:
            is_valid, error = validate_path(str(test_file))
            assert is_valid is False
            assert error is not None
            assert "permission" in error.lower()
        finally:
            # Restore permissions for cleanup
            test_file.chmod(original_mode)

    def test_validate_path_permission_denied_directory(self, tmp_path):
        """Test validate_path handles permission denied for directories."""
        # Create a directory and remove read permissions
        test_dir = tmp_path / "unreadable_dir"
        test_dir.mkdir()

        # Remove read permissions
        original_mode = test_dir.stat().st_mode
        test_dir.chmod(stat.S_IWUSR | stat.S_IXUSR)  # Write+Execute only

        try:
            is_valid, error = validate_path(str(test_dir))
            assert is_valid is False
            assert error is not None
            assert "permission" in error.lower()
        finally:
            # Restore permissions for cleanup
            test_dir.chmod(original_mode)

    def test_validate_path_invalid_path_format(self):
        """Test validate_path handles invalid path formats."""
        # Test with null bytes which are invalid in paths
        with mock.patch.object(Path, "resolve", side_effect=OSError("Invalid path")):
            is_valid, error = validate_path("some/path")
            assert is_valid is False
            assert "invalid path" in error.lower()

    def test_validate_path_symlink_loop(self):
        """Test validate_path handles symlink loops."""
        with mock.patch.object(Path, "resolve", side_effect=RuntimeError("Symlink loop detected")):
            is_valid, error = validate_path("some/path")
            assert is_valid is False
            assert "invalid path" in error.lower()


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
        valid_paths, errors = validate_dropped_files([str(test_file), "/nonexistent/path", None])
        assert len(valid_paths) == 1
        assert len(errors) == 2

    def test_validate_dropped_files_permission_denied(self, tmp_path):
        """Test validate_dropped_files handles permission errors."""
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

    def test_validate_dropped_files_resolve_error(self, tmp_path):
        """Test validate_dropped_files handles path resolution errors."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with mock.patch.object(Path, "resolve", side_effect=OSError("Resolution error")):
            valid_paths, errors = validate_dropped_files([str(test_file)])
            # The validation will pass but resolution will fail
            assert valid_paths == []
            assert len(errors) == 1
            assert "error resolving" in errors[0].lower()


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

    def test_format_scan_path_home_directory(self, tmp_path):
        """Test format_scan_path formats home directory paths with ~."""
        # Mock Path.home() to return tmp_path for testing
        with mock.patch.object(Path, "home", return_value=tmp_path):
            test_file = tmp_path / "Documents" / "test.txt"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("test content")

            result = format_scan_path(str(test_file))
            assert result.startswith("~/")
            assert "Documents/test.txt" in result

    def test_format_scan_path_flatpak_portal_path(self):
        """Test format_scan_path handles Flatpak document portal paths."""
        portal_path = "/run/user/1000/doc/abc123/test.txt"

        # Mock format_flatpak_portal_path to simulate portal path formatting
        with mock.patch("src.core.path_validation.format_flatpak_portal_path", return_value="[Portal] test.txt"):
            result = format_scan_path(portal_path)
            assert result == "[Portal] test.txt"

    def test_format_scan_path_already_formatted_with_tilde(self):
        """Test format_scan_path returns already formatted paths with ~ as-is."""
        formatted_path = "~/Documents/test.txt"
        result = format_scan_path(formatted_path)
        # Should return as-is since it already has ~ notation
        assert result == formatted_path

    def test_format_scan_path_already_formatted_with_portal(self):
        """Test format_scan_path returns already formatted portal paths as-is."""
        portal_formatted = "[Portal] test.txt"

        with mock.patch("src.core.path_validation.format_flatpak_portal_path", return_value=portal_formatted):
            result = format_scan_path("/some/path")
            assert result == portal_formatted

    def test_format_scan_path_oserror(self):
        """Test format_scan_path handles OSError gracefully."""
        with mock.patch.object(Path, "resolve", side_effect=OSError("Error")):
            result = format_scan_path("/some/path")
            # Should return the original path
            assert "/some/path" in result

    def test_format_scan_path_runtimeerror(self):
        """Test format_scan_path handles RuntimeError gracefully."""
        with mock.patch.object(Path, "resolve", side_effect=RuntimeError("Symlink loop")):
            result = format_scan_path("/some/path")
            # Should return the original path
            assert "/some/path" in result


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

    def test_get_path_info_display_path(self, tmp_path):
        """Test get_path_info includes formatted display_path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        info = get_path_info(str(test_file))
        assert "display_path" in info
        assert info["display_path"] is not None

    def test_get_path_info_unreadable_file(self, tmp_path):
        """Test get_path_info handles unreadable files."""
        test_file = tmp_path / "unreadable.txt"
        test_file.write_text("test content")

        # Remove read permissions
        original_mode = test_file.stat().st_mode
        test_file.chmod(stat.S_IWUSR)  # Write-only

        try:
            info = get_path_info(str(test_file))
            assert info["exists"] is True
            assert info["type"] == "file"
            assert info["readable"] is False
        finally:
            # Restore permissions for cleanup
            test_file.chmod(original_mode)

    def test_get_path_info_oserror_on_stat(self, tmp_path):
        """Test get_path_info handles OSError when getting file size."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with mock.patch.object(Path, "stat", side_effect=OSError("Stat error")):
            info = get_path_info(str(test_file))
            # Should still return basic info
            assert "type" in info
            assert "exists" in info

    def test_get_path_info_oserror_on_resolve(self):
        """Test get_path_info handles OSError when resolving path."""
        with mock.patch.object(Path, "resolve", side_effect=OSError("Resolve error")):
            info = get_path_info("/some/path")
            assert info["type"] == "unknown"
            assert info["exists"] is False

    def test_get_path_info_runtimeerror(self):
        """Test get_path_info handles RuntimeError gracefully."""
        with mock.patch.object(Path, "resolve", side_effect=RuntimeError("Symlink loop")):
            info = get_path_info("/some/path")
            assert info["type"] == "unknown"
            assert info["exists"] is False

    def test_get_path_info_symlink_file(self, tmp_path):
        """Test get_path_info handles symlinks to files."""
        # Create target file
        target_file = tmp_path / "target.txt"
        target_file.write_text("target content")

        # Create symlink
        symlink_file = tmp_path / "symlink.txt"
        symlink_file.symlink_to(target_file)

        info = get_path_info(str(symlink_file))
        assert info["type"] == "file"
        assert info["exists"] is True
        assert info["readable"] is True
        assert info["size"] == len("target content")

    def test_get_path_info_symlink_directory(self, tmp_path):
        """Test get_path_info handles symlinks to directories."""
        # Create target directory
        target_dir = tmp_path / "target_dir"
        target_dir.mkdir()

        # Create symlink
        symlink_dir = tmp_path / "symlink_dir"
        symlink_dir.symlink_to(target_dir)

        info = get_path_info(str(symlink_dir))
        assert info["type"] == "directory"
        assert info["exists"] is True
        assert info["readable"] is True
        assert info["size"] is None
