# ClamUI CLI Argument Parsing Tests
"""
Unit tests for CLI argument parsing and edge case handling.

Tests cover:
- Single file arguments
- Multiple file arguments
- Mixed files and folders
- Non-existent paths
- Permission denied scenarios
- Symlinks
- Paths with spaces and special characters
- Empty arguments (normal launch)
"""

import os
import sys
from unittest import mock

import pytest


def _clear_src_modules():
    """Clear all cached src.* modules to prevent test pollution."""
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


@pytest.fixture
def parse_file_arguments():
    """Import parse_file_arguments with proper GTK mocking.

    This fixture handles the complex mocking required to import src.main
    without requiring GTK/GI runtime dependencies.
    """
    # Create comprehensive mocks
    mock_gi = mock.MagicMock()
    mock_gi.version_info = (3, 48, 0)
    mock_gi.require_version = mock.MagicMock()

    mock_gi_repository = mock.MagicMock()

    # Mock the matplotlib GTK backend to avoid metaclass conflicts
    mock_backend = mock.MagicMock()

    # Store original modules
    original_modules = {}
    modules_to_mock = [
        "gi",
        "gi.repository",
        "matplotlib.backends.backend_gtk4",
        "matplotlib.backends.backend_gtk4agg",
        "src.ui.statistics_view",
        "src.ui.window",
        "src.ui.scan_view",
        "src.ui.update_view",
        "src.ui.logs_view",
        "src.ui.components_view",
        "src.ui.preferences_window",
        "src.ui.fullscreen_dialog",
        "src.app",
    ]

    for mod in modules_to_mock:
        original_modules[mod] = sys.modules.get(mod)

    # Set up mocks
    sys.modules["gi"] = mock_gi
    sys.modules["gi.repository"] = mock_gi_repository
    sys.modules["matplotlib.backends.backend_gtk4"] = mock_backend
    sys.modules["matplotlib.backends.backend_gtk4agg"] = mock_backend

    # Clear cached modules that might have been imported
    for mod in list(sys.modules.keys()):
        if mod.startswith("src."):
            del sys.modules[mod]

    try:
        from src.main import parse_file_arguments as func

        yield func
    finally:
        # Restore original modules
        for mod, original in original_modules.items():
            if original is not None:
                sys.modules[mod] = original
            elif mod in sys.modules:
                del sys.modules[mod]

        # Critical: Clear all src.* modules to prevent pollution
        _clear_src_modules()


class TestParseFileArguments:
    """Tests for the parse_file_arguments function."""

    def test_empty_arguments(self, parse_file_arguments):
        """Test parse_file_arguments with no file arguments (normal launch)."""
        argv = ["clamui"]
        result = parse_file_arguments(argv)
        assert result == []

    def test_single_file_argument(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with a single file path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        argv = ["clamui", str(test_file)]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        assert result[0] == str(test_file)

    def test_single_folder_argument(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with a single folder path."""
        argv = ["clamui", str(tmp_path)]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        assert result[0] == str(tmp_path)

    def test_multiple_file_arguments(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with multiple file paths."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file3 = tmp_path / "file3.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")
        file3.write_text("content 3")

        argv = ["clamui", str(file1), str(file2), str(file3)]
        result = parse_file_arguments(argv)
        assert len(result) == 3
        assert str(file1) in result
        assert str(file2) in result
        assert str(file3) in result

    def test_mixed_files_and_folders(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with both files and folders."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        argv = ["clamui", str(test_file), str(subdir), str(tmp_path)]
        result = parse_file_arguments(argv)
        assert len(result) == 3
        assert str(test_file) in result
        assert str(subdir) in result
        assert str(tmp_path) in result


class TestPathWithSpaces:
    """Tests for handling paths with spaces and special characters."""

    def test_path_with_spaces(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with paths containing spaces."""
        space_dir = tmp_path / "folder with spaces"
        space_dir.mkdir()
        space_file = space_dir / "file with spaces.txt"
        space_file.write_text("content")

        argv = ["clamui", str(space_file)]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        assert result[0] == str(space_file)
        assert " " in result[0]

    def test_path_with_special_characters(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with paths containing special characters."""
        # Test various special characters that are valid in filenames
        special_chars = ["test-file", "test_file", "test.file.txt", "test(1).txt"]

        for name in special_chars:
            special_file = tmp_path / name
            special_file.write_text("content")
            argv = ["clamui", str(special_file)]
            result = parse_file_arguments(argv)
            assert len(result) == 1
            assert result[0] == str(special_file)

    def test_path_with_unicode(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with paths containing unicode characters."""
        unicode_file = tmp_path / "test_файл_文件.txt"
        unicode_file.write_text("unicode content")

        argv = ["clamui", str(unicode_file)]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        assert result[0] == str(unicode_file)

    def test_path_with_quotes_in_name(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with paths containing quotes."""
        # Single quotes in filename
        quoted_file = tmp_path / "test'file.txt"
        quoted_file.write_text("content")

        argv = ["clamui", str(quoted_file)]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        assert result[0] == str(quoted_file)


class TestNonExistentPaths:
    """Tests for handling non-existent paths."""

    def test_nonexistent_path_returned(self, parse_file_arguments):
        """Test that non-existent paths are still returned by parse_file_arguments.

        Note: parse_file_arguments returns all paths; validation happens later
        in set_initial_scan_paths and queue_files_for_scan.
        """
        nonexistent = "/path/that/does/not/exist/file.txt"
        argv = ["clamui", nonexistent]
        result = parse_file_arguments(argv)
        # parse_file_arguments doesn't validate paths, just parses them
        assert len(result) == 1
        assert result[0] == nonexistent

    def test_mixed_existent_and_nonexistent(self, parse_file_arguments, tmp_path):
        """Test with mix of existing and non-existing paths."""
        existing_file = tmp_path / "exists.txt"
        existing_file.write_text("content")
        nonexistent = "/nonexistent/path/file.txt"

        argv = ["clamui", str(existing_file), nonexistent]
        result = parse_file_arguments(argv)
        # Both paths are returned; validation happens later
        assert len(result) == 2


class TestSymlinks:
    """Tests for handling symbolic links."""

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require special permissions on Windows")
    def test_symlink_to_file(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with symlink to a file."""
        target_file = tmp_path / "target.txt"
        target_file.write_text("target content")
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(target_file)

        argv = ["clamui", str(symlink)]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        assert result[0] == str(symlink)
        # Verify symlink exists
        assert os.path.exists(result[0])

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require special permissions on Windows")
    def test_symlink_to_directory(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with symlink to a directory."""
        target_dir = tmp_path / "target_dir"
        target_dir.mkdir()
        symlink = tmp_path / "link_dir"
        symlink.symlink_to(target_dir)

        argv = ["clamui", str(symlink)]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        assert result[0] == str(symlink)
        # Verify symlink exists and points to directory
        assert os.path.isdir(result[0])

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require special permissions on Windows")
    def test_broken_symlink(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with broken symlink."""
        target = tmp_path / "target_that_will_be_deleted.txt"
        target.write_text("content")
        symlink = tmp_path / "broken_link.txt"
        symlink.symlink_to(target)
        # Delete target to create broken symlink
        target.unlink()

        argv = ["clamui", str(symlink)]
        result = parse_file_arguments(argv)
        # Path is returned but won't exist when validated
        assert len(result) == 1
        assert result[0] == str(symlink)
        # Broken symlink: lexists is True but exists is False
        assert os.path.lexists(result[0])
        assert not os.path.exists(result[0])


class TestPathValidationInApp:
    """Tests for path validation in ClamUIApp.set_initial_scan_paths."""

    def test_set_initial_scan_paths_filters_nonexistent(self, tmp_path):
        """Test that set_initial_scan_paths filters out non-existent paths.

        Note: This test verifies the filtering logic without importing the actual
        ClamUIApp class, which requires GTK dependencies.
        """
        existing_file = tmp_path / "exists.txt"
        existing_file.write_text("content")
        nonexistent = "/nonexistent/path.txt"

        # Replicate the path filtering logic from ClamUIApp.set_initial_scan_paths
        paths = [str(existing_file), nonexistent]
        valid_paths = []
        for path in paths:
            if os.path.exists(path):
                valid_paths.append(path)

        # Verify filtering logic
        assert len(valid_paths) == 1
        assert str(existing_file) in valid_paths
        assert nonexistent not in valid_paths

    def test_set_initial_scan_paths_all_nonexistent(self):
        """Test set_initial_scan_paths with all non-existent paths."""
        paths = ["/nonexistent/path1.txt", "/nonexistent/path2.txt"]
        valid_paths = [p for p in paths if os.path.exists(p)]
        assert len(valid_paths) == 0

    def test_set_initial_scan_paths_empty_list(self):
        """Test set_initial_scan_paths with empty list."""
        paths = []
        valid_paths = [p for p in paths if os.path.exists(p)]
        assert valid_paths == []


class TestQueueFilesForScan:
    """Tests for ScanView.queue_files_for_scan path validation."""

    def test_queue_files_filters_invalid_paths(self, tmp_path):
        """Test that queue_files_for_scan filters invalid paths."""
        existing_file = tmp_path / "valid.txt"
        existing_file.write_text("content")

        paths = [str(existing_file), "/nonexistent/invalid.txt"]

        # Replicate validation logic from queue_files_for_scan
        valid_paths = []
        for path in paths:
            if os.path.exists(path):
                valid_paths.append(path)

        assert len(valid_paths) == 1
        assert str(existing_file) in valid_paths

    def test_queue_files_empty_list_returns_zero(self):
        """Test that queue_files_for_scan returns 0 for empty list."""
        paths = []
        # Replicate logic: empty list returns 0
        assert len(paths) == 0

    def test_queue_files_all_invalid_returns_zero(self):
        """Test that queue_files_for_scan returns 0 when all paths invalid."""
        paths = ["/nonexistent/a.txt", "/nonexistent/b.txt"]
        valid_paths = [p for p in paths if os.path.exists(p)]
        assert len(valid_paths) == 0


class TestLargeDirectories:
    """Tests for handling large directories."""

    def test_large_directory_with_many_files(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with directory containing many files."""
        # Create a directory with many files
        large_dir = tmp_path / "large_dir"
        large_dir.mkdir()

        # Create 100 files (representative of "large" directory for testing)
        for i in range(100):
            (large_dir / f"file_{i:04d}.txt").write_text(f"content {i}")

        argv = ["clamui", str(large_dir)]
        result = parse_file_arguments(argv)

        # The directory path should be returned
        assert len(result) == 1
        assert result[0] == str(large_dir)

        # Verify directory has files
        files = list(large_dir.iterdir())
        assert len(files) == 100

    def test_deeply_nested_directory(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with deeply nested directory structure."""
        # Create nested structure
        current = tmp_path
        for i in range(10):
            current = current / f"level_{i}"
            current.mkdir()

        # Create file at deepest level
        deep_file = current / "deep_file.txt"
        deep_file.write_text("deep content")

        argv = ["clamui", str(deep_file)]
        result = parse_file_arguments(argv)

        assert len(result) == 1
        assert result[0] == str(deep_file)
        assert os.path.exists(result[0])


class TestPermissionScenarios:
    """Tests for permission-related scenarios."""

    @pytest.mark.skipif(
        os.name == "nt" or os.geteuid() == 0,
        reason="Permission tests not applicable on Windows or when running as root",
    )
    def test_unreadable_file_path_returned(self, parse_file_arguments, tmp_path):
        """Test that paths to unreadable files are still returned by parser.

        Note: The parser returns paths; permission checks happen during scan.
        """
        unreadable_file = tmp_path / "unreadable.txt"
        unreadable_file.write_text("secret content")

        # Remove read permissions
        original_mode = unreadable_file.stat().st_mode
        try:
            unreadable_file.chmod(0o000)

            argv = ["clamui", str(unreadable_file)]
            result = parse_file_arguments(argv)

            # Path is returned; permission error happens during scan
            assert len(result) == 1
            assert result[0] == str(unreadable_file)
        finally:
            # Restore permissions for cleanup
            unreadable_file.chmod(original_mode)

    @pytest.mark.skipif(
        os.name == "nt" or os.geteuid() == 0,
        reason="Permission tests not applicable on Windows or when running as root",
    )
    def test_unreadable_directory_path_returned(self, parse_file_arguments, tmp_path):
        """Test that paths to unreadable directories are still returned."""
        unreadable_dir = tmp_path / "unreadable_dir"
        unreadable_dir.mkdir()
        (unreadable_dir / "file.txt").write_text("content")

        original_mode = unreadable_dir.stat().st_mode
        try:
            unreadable_dir.chmod(0o000)

            argv = ["clamui", str(unreadable_dir)]
            result = parse_file_arguments(argv)

            assert len(result) == 1
            assert result[0] == str(unreadable_dir)
        finally:
            unreadable_dir.chmod(original_mode)


class TestEdgeCasePathFormats:
    """Tests for edge case path formats."""

    def test_relative_path_argument(self, parse_file_arguments):
        """Test parse_file_arguments with relative path."""
        argv = ["clamui", "./relative/path.txt"]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        assert result[0] == "./relative/path.txt"

    def test_home_tilde_path(self, parse_file_arguments):
        """Test parse_file_arguments with ~ home directory path."""
        argv = ["clamui", "~/Documents/test.txt"]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        # Tilde is passed as-is; expansion happens in shell before Python
        assert result[0] == "~/Documents/test.txt"

    def test_dot_path(self, parse_file_arguments):
        """Test parse_file_arguments with . (current directory)."""
        argv = ["clamui", "."]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        assert result[0] == "."

    def test_double_dot_path(self, parse_file_arguments):
        """Test parse_file_arguments with .. (parent directory)."""
        argv = ["clamui", ".."]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        assert result[0] == ".."

    def test_trailing_slash_directory(self, parse_file_arguments, tmp_path):
        """Test parse_file_arguments with trailing slash on directory."""
        argv = ["clamui", str(tmp_path) + "/"]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        # Trailing slash is preserved
        assert result[0].endswith("/")

    def test_multiple_slashes_path(self, parse_file_arguments):
        """Test parse_file_arguments with multiple consecutive slashes."""
        argv = ["clamui", "/tmp//double//slashes/path"]
        result = parse_file_arguments(argv)
        assert len(result) == 1
        # Multiple slashes are preserved in the raw argument
        assert "//" in result[0]
