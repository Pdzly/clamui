# ClamUI ScanView Tests
"""
Unit tests for the ScanView component's multi-path selection functionality.

Tests cover:
- Single path addition and management
- Multiple path addition and ordering
- Path removal operations
- Clearing all paths
- Duplicate path detection
- Drag-and-drop with multiple files
- Profile loading with all targets
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
def scan_view_class(mock_gi_modules):
    """Get ScanView class with mocked dependencies."""
    # Mock core dependencies
    mock_scanner = mock.MagicMock()
    mock_scanner_module = mock.MagicMock()
    mock_scanner_module.Scanner = mock_scanner
    mock_scanner_module.ScanResult = mock.MagicMock()
    mock_scanner_module.ScanStatus = mock.MagicMock()

    mock_quarantine = mock.MagicMock()
    mock_utils = mock.MagicMock()
    mock_utils.format_scan_path = lambda x: x  # Pass through
    mock_utils.is_flatpak = lambda: False
    mock_utils.validate_dropped_files = lambda paths: (
        [p for p in paths if p],
        [],
    )

    with mock.patch.dict(
        sys.modules,
        {
            "src.core.scanner": mock_scanner_module,
            "src.core.quarantine": mock_quarantine,
            "src.core.utils": mock_utils,
            "src.ui.profile_dialogs": mock.MagicMock(),
            "src.ui.scan_results_dialog": mock.MagicMock(),
            "src.ui.utils": mock.MagicMock(),
            "src.ui.view_helpers": mock.MagicMock(),
        },
    ):
        # Clear any cached import
        if "src.ui.scan_view" in sys.modules:
            del sys.modules["src.ui.scan_view"]

        from src.ui.scan_view import ScanView

        yield ScanView

    # Critical: Clear all src.* modules after test to prevent pollution
    _clear_src_modules()


@pytest.fixture
def mock_scan_view(scan_view_class):
    """Create a mock ScanView instance for testing."""
    # Create instance without calling __init__
    view = object.__new__(scan_view_class)

    # Set up required attributes for multi-path functionality
    view._selected_paths = []
    view._normalized_paths = set()
    view._is_scanning = False
    view._cancel_all_requested = False

    # Mock UI elements
    view._path_label = mock.MagicMock()
    view._path_row = mock.MagicMock()
    view._status_banner = mock.MagicMock()
    view._scan_button = mock.MagicMock()
    view._cancel_button = mock.MagicMock()
    view._eicar_button = mock.MagicMock()
    view._progress_section = mock.MagicMock()
    view._progress_bar = mock.MagicMock()
    view._progress_label = mock.MagicMock()
    view._view_results_section = mock.MagicMock()
    view._view_results_button = mock.MagicMock()
    view._profile_dropdown = mock.MagicMock()
    view._profile_list = []
    view._selected_profile = None
    view._backend_label = mock.MagicMock()

    # Mock scanner
    view._scanner = mock.MagicMock()
    view._scanner.get_active_backend.return_value = "clamscan"

    # Mock quarantine manager
    view._quarantine_manager = mock.MagicMock()

    # Mock settings manager
    view._settings_manager = mock.MagicMock()

    # Mock internal methods that interact with GTK
    view.get_root = mock.MagicMock(return_value=None)
    view.add_css_class = mock.MagicMock()
    view.remove_css_class = mock.MagicMock()

    return view


class TestScanViewImport:
    """Tests for ScanView import."""

    def test_import_scan_view(self, mock_gi_modules):
        """Test that ScanView can be imported."""
        mock_scanner_module = mock.MagicMock()
        mock_scanner_module.Scanner = mock.MagicMock()
        mock_scanner_module.ScanResult = mock.MagicMock()
        mock_scanner_module.ScanStatus = mock.MagicMock()

        with mock.patch.dict(
            sys.modules,
            {
                "src.core.scanner": mock_scanner_module,
                "src.core.quarantine": mock.MagicMock(),
                "src.core.utils": mock.MagicMock(),
                "src.ui.profile_dialogs": mock.MagicMock(),
                "src.ui.scan_results_dialog": mock.MagicMock(),
                "src.ui.utils": mock.MagicMock(),
                "src.ui.view_helpers": mock.MagicMock(),
            },
        ):
            from src.ui.scan_view import ScanView

            assert ScanView is not None


class TestAddSinglePath:
    """Tests for adding a single path to the selection."""

    def test_add_single_path_adds_to_list(self, mock_scan_view):
        """Test that adding a single path adds it to the selected paths list."""
        # Mock the UI elements that _add_path interacts with
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._create_path_row = mock.MagicMock()
        mock_scan_view._update_selection_header = mock.MagicMock()

        result = mock_scan_view._add_path("/home/user/documents")

        assert result is True
        assert "/home/user/documents" in mock_scan_view._selected_paths
        assert len(mock_scan_view._selected_paths) == 1

    def test_add_single_path_updates_ui(self, mock_scan_view):
        """Test that adding a path updates the UI elements."""
        # Mock the UI elements that _add_path interacts with
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._create_path_row = mock.MagicMock()
        mock_scan_view._update_selection_header = mock.MagicMock()

        mock_scan_view._add_path("/home/user/documents")

        mock_scan_view._paths_placeholder.set_visible.assert_called_once_with(False)
        mock_scan_view._update_selection_header.assert_called_once()

    def test_add_single_path_preserves_original_path(self, mock_scan_view):
        """Test that the original path string is preserved."""
        # Mock the UI elements that _add_path interacts with
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._create_path_row = mock.MagicMock()
        mock_scan_view._update_selection_header = mock.MagicMock()
        original_path = "/home/user/documents"

        mock_scan_view._add_path(original_path)

        assert mock_scan_view._selected_paths[0] == original_path


class TestAddMultiplePaths:
    """Tests for adding multiple paths to the selection."""

    def test_add_multiple_paths_maintains_order(self, mock_scan_view):
        """Test that adding multiple paths maintains insertion order."""
        # Mock the UI elements that _add_path interacts with
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._create_path_row = mock.MagicMock()
        mock_scan_view._update_selection_header = mock.MagicMock()

        mock_scan_view._add_path("/home/user/documents")
        mock_scan_view._add_path("/home/user/downloads")
        mock_scan_view._add_path("/home/user/pictures")

        assert mock_scan_view._selected_paths == [
            "/home/user/documents",
            "/home/user/downloads",
            "/home/user/pictures",
        ]

    def test_add_multiple_paths_count(self, mock_scan_view):
        """Test that multiple paths are all added."""
        # Mock the UI elements that _add_path interacts with
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._create_path_row = mock.MagicMock()
        mock_scan_view._update_selection_header = mock.MagicMock()

        mock_scan_view._add_path("/path1")
        mock_scan_view._add_path("/path2")
        mock_scan_view._add_path("/path3")
        mock_scan_view._add_path("/path4")

        assert len(mock_scan_view._selected_paths) == 4

    def test_add_multiple_paths_updates_ui_each_time(self, mock_scan_view):
        """Test that UI update is called for each path addition."""
        # Mock the UI elements that _add_path interacts with
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._create_path_row = mock.MagicMock()
        mock_scan_view._update_selection_header = mock.MagicMock()

        mock_scan_view._add_path("/path1")
        mock_scan_view._add_path("/path2")
        mock_scan_view._add_path("/path3")

        assert mock_scan_view._update_selection_header.call_count == 3


class TestRemovePath:
    """Tests for removing paths from the selection."""

    def _setup_remove_path_mocks(self, mock_scan_view):
        """Helper to set up common mocks for remove path tests."""
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._paths_listbox.get_first_child.return_value = None
        mock_scan_view._update_selection_header = mock.MagicMock()

    def test_remove_path_removes_from_list(self, mock_scan_view):
        """Test that removing a path removes it from the list."""
        self._setup_remove_path_mocks(mock_scan_view)
        mock_scan_view._selected_paths = ["/path1", "/path2", "/path3"]
        mock_scan_view._normalized_paths = {"/path1", "/path2", "/path3"}

        result = mock_scan_view._remove_path("/path2")

        assert result is True
        assert "/path2" not in mock_scan_view._selected_paths
        assert len(mock_scan_view._selected_paths) == 2

    def test_remove_path_preserves_other_paths(self, mock_scan_view):
        """Test that removing a path preserves other paths."""
        self._setup_remove_path_mocks(mock_scan_view)
        mock_scan_view._selected_paths = ["/path1", "/path2", "/path3"]
        mock_scan_view._normalized_paths = {"/path1", "/path2", "/path3"}

        mock_scan_view._remove_path("/path2")

        assert mock_scan_view._selected_paths == ["/path1", "/path3"]

    def test_remove_nonexistent_path_returns_false(self, mock_scan_view):
        """Test that removing a non-existent path returns False."""
        self._setup_remove_path_mocks(mock_scan_view)
        mock_scan_view._selected_paths = ["/path1", "/path2"]
        mock_scan_view._normalized_paths = {"/path1", "/path2"}

        result = mock_scan_view._remove_path("/nonexistent")

        assert result is False
        assert len(mock_scan_view._selected_paths) == 2

    def test_remove_path_updates_ui(self, mock_scan_view):
        """Test that removing a path updates the UI."""
        self._setup_remove_path_mocks(mock_scan_view)
        mock_scan_view._selected_paths = ["/path1", "/path2"]
        mock_scan_view._normalized_paths = {"/path1", "/path2"}

        mock_scan_view._remove_path("/path1")

        mock_scan_view._update_selection_header.assert_called()

    def test_remove_path_handles_normalized_paths(self, mock_scan_view):
        """Test that path removal handles path normalization."""
        self._setup_remove_path_mocks(mock_scan_view)
        mock_scan_view._selected_paths = ["/home/user/./documents"]
        # The set stores normalized paths
        mock_scan_view._normalized_paths = {os.path.normpath("/home/user/./documents")}

        # Normalized version should still match
        result = mock_scan_view._remove_path("/home/user/documents")

        assert result is True
        assert len(mock_scan_view._selected_paths) == 0


class TestClearPaths:
    """Tests for clearing all paths from the selection."""

    def _setup_clear_paths_mocks(self, mock_scan_view):
        """Helper to set up common mocks for clear paths tests."""
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._paths_listbox.get_first_child.return_value = None
        mock_scan_view._update_selection_header = mock.MagicMock()

    def test_clear_paths_empties_list(self, mock_scan_view):
        """Test that clearing paths empties the entire list."""
        self._setup_clear_paths_mocks(mock_scan_view)
        mock_scan_view._selected_paths = ["/path1", "/path2", "/path3"]
        mock_scan_view._normalized_paths = {"/path1", "/path2", "/path3"}

        mock_scan_view._clear_paths()

        assert mock_scan_view._selected_paths == []
        assert len(mock_scan_view._selected_paths) == 0

    def test_clear_paths_updates_ui(self, mock_scan_view):
        """Test that clearing paths updates the UI."""
        self._setup_clear_paths_mocks(mock_scan_view)
        mock_scan_view._selected_paths = ["/path1", "/path2"]
        mock_scan_view._normalized_paths = {"/path1", "/path2"}

        mock_scan_view._clear_paths()

        mock_scan_view._update_selection_header.assert_called_once()
        mock_scan_view._paths_placeholder.set_visible.assert_called_with(True)

    def test_clear_paths_on_empty_list(self, mock_scan_view):
        """Test that clearing an empty list works without error."""
        self._setup_clear_paths_mocks(mock_scan_view)
        mock_scan_view._selected_paths = []

        mock_scan_view._clear_paths()

        assert mock_scan_view._selected_paths == []


class TestDuplicateDetection:
    """Tests for duplicate path detection."""

    def _setup_add_path_mocks(self, mock_scan_view):
        """Helper to set up common mocks for add path tests."""
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._create_path_row = mock.MagicMock()
        mock_scan_view._update_selection_header = mock.MagicMock()

    def test_duplicate_exact_path_rejected(self, mock_scan_view):
        """Test that adding the exact same path twice is rejected."""
        self._setup_add_path_mocks(mock_scan_view)

        result1 = mock_scan_view._add_path("/home/user/documents")
        result2 = mock_scan_view._add_path("/home/user/documents")

        assert result1 is True
        assert result2 is False
        assert len(mock_scan_view._selected_paths) == 1

    def test_duplicate_normalized_path_rejected(self, mock_scan_view):
        """Test that normalized duplicate paths are rejected."""
        self._setup_add_path_mocks(mock_scan_view)

        mock_scan_view._add_path("/home/user/documents")
        result = mock_scan_view._add_path("/home/user/./documents")

        assert result is False
        assert len(mock_scan_view._selected_paths) == 1

    def test_different_paths_accepted(self, mock_scan_view):
        """Test that different paths are accepted."""
        self._setup_add_path_mocks(mock_scan_view)

        result1 = mock_scan_view._add_path("/home/user/documents")
        result2 = mock_scan_view._add_path("/home/user/downloads")

        assert result1 is True
        assert result2 is True
        assert len(mock_scan_view._selected_paths) == 2

    def test_case_sensitive_paths(self, mock_scan_view):
        """Test that paths are case-sensitive (on case-sensitive filesystems)."""
        self._setup_add_path_mocks(mock_scan_view)

        result1 = mock_scan_view._add_path("/home/user/Documents")
        result2 = mock_scan_view._add_path("/home/user/documents")

        # On Linux, these are different paths
        assert result1 is True
        assert result2 is True
        assert len(mock_scan_view._selected_paths) == 2


class TestDragDropMultiple:
    """Tests for drag-and-drop with multiple files."""

    def _setup_drop_mocks(self, mock_scan_view):
        """Helper to set up common mocks for drop tests."""
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._create_path_row = mock.MagicMock()
        mock_scan_view._update_selection_header = mock.MagicMock()

    def test_drop_multiple_files_adds_all(self, mock_scan_view):
        """Test that dropping multiple files adds all valid paths."""
        self._setup_drop_mocks(mock_scan_view)
        mock_scan_view._show_drop_error = mock.MagicMock()

        # Mock Gdk.FileList with multiple files
        mock_file1 = mock.MagicMock()
        mock_file1.get_path.return_value = "/home/user/file1.txt"

        mock_file2 = mock.MagicMock()
        mock_file2.get_path.return_value = "/home/user/file2.txt"

        mock_file3 = mock.MagicMock()
        mock_file3.get_path.return_value = "/home/user/file3.txt"

        mock_file_list = mock.MagicMock()
        mock_file_list.get_files.return_value = [mock_file1, mock_file2, mock_file3]

        # Mock validate_dropped_files to return all paths as valid
        with mock.patch("src.ui.scan_view.validate_dropped_files") as mock_validate:
            mock_validate.return_value = (
                ["/home/user/file1.txt", "/home/user/file2.txt", "/home/user/file3.txt"],
                [],
            )

            result = mock_scan_view._on_drop(None, mock_file_list, 0, 0)

        assert result is True
        assert len(mock_scan_view._selected_paths) == 3

    def test_drop_during_scan_rejected(self, mock_scan_view):
        """Test that dropping files during a scan is rejected."""
        mock_scan_view._is_scanning = True
        mock_scan_view._show_drop_error = mock.MagicMock()

        mock_file_list = mock.MagicMock()
        mock_file_list.get_files.return_value = [mock.MagicMock()]

        result = mock_scan_view._on_drop(None, mock_file_list, 0, 0)

        assert result is False
        mock_scan_view._show_drop_error.assert_called()

    def test_drop_removes_css_class(self, mock_scan_view):
        """Test that drop removes the visual feedback CSS class."""
        self._setup_drop_mocks(mock_scan_view)

        mock_file = mock.MagicMock()
        mock_file.get_path.return_value = "/home/user/file.txt"

        mock_file_list = mock.MagicMock()
        mock_file_list.get_files.return_value = [mock_file]

        with mock.patch("src.ui.scan_view.validate_dropped_files") as mock_validate:
            mock_validate.return_value = (["/home/user/file.txt"], [])

            mock_scan_view._on_drop(None, mock_file_list, 0, 0)

        mock_scan_view.remove_css_class.assert_called_with("drop-active")

    def test_drop_empty_file_list_rejected(self, mock_scan_view):
        """Test that dropping an empty file list is rejected."""
        mock_scan_view._show_drop_error = mock.MagicMock()

        mock_file_list = mock.MagicMock()
        mock_file_list.get_files.return_value = []

        result = mock_scan_view._on_drop(None, mock_file_list, 0, 0)

        assert result is False
        mock_scan_view._show_drop_error.assert_called_with("No files were dropped")


class TestProfileLoadsAllTargets:
    """Tests for profile loading all targets."""

    def _setup_profile_mocks(self, mock_scan_view):
        """Helper to set up common mocks for profile tests."""
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._paths_listbox.get_first_child.return_value = None
        mock_scan_view._create_path_row = mock.MagicMock()
        mock_scan_view._update_selection_header = mock.MagicMock()

    def test_profile_selection_loads_all_targets(self, mock_scan_view, tmp_path):
        """Test that selecting a profile loads all its targets."""
        self._setup_profile_mocks(mock_scan_view)
        mock_scan_view._show_toast = mock.MagicMock()

        # Create actual directories for testing
        dir1 = tmp_path / "documents"
        dir2 = tmp_path / "downloads"
        dir3 = tmp_path / "pictures"
        dir1.mkdir()
        dir2.mkdir()
        dir3.mkdir()

        # Create mock profile with multiple targets
        mock_profile = mock.MagicMock()
        mock_profile.name = "Test Profile"
        mock_profile.targets = [str(dir1), str(dir2), str(dir3)]

        mock_scan_view._profile_list = [mock_profile]
        mock_scan_view._selected_profile = None

        # Mock dropdown to return index 1 (first profile after "No Profile")
        mock_dropdown = mock.MagicMock()
        mock_dropdown.get_selected.return_value = 1

        mock_scan_view._on_profile_selected(mock_dropdown, None)

        # All three paths should be added
        assert len(mock_scan_view._selected_paths) == 3
        assert str(dir1) in mock_scan_view._selected_paths
        assert str(dir2) in mock_scan_view._selected_paths
        assert str(dir3) in mock_scan_view._selected_paths

    def test_profile_selection_clears_previous_paths(self, mock_scan_view, tmp_path):
        """Test that selecting a profile clears previously selected paths."""
        self._setup_profile_mocks(mock_scan_view)
        mock_scan_view._show_toast = mock.MagicMock()

        # Pre-populate with some paths
        mock_scan_view._selected_paths = ["/some/old/path"]

        # Create directory for profile target
        profile_dir = tmp_path / "profile_target"
        profile_dir.mkdir()

        # Create mock profile
        mock_profile = mock.MagicMock()
        mock_profile.name = "Test Profile"
        mock_profile.targets = [str(profile_dir)]

        mock_scan_view._profile_list = [mock_profile]

        mock_dropdown = mock.MagicMock()
        mock_dropdown.get_selected.return_value = 1

        mock_scan_view._on_profile_selected(mock_dropdown, None)

        # Should only have the profile target, not the old path
        assert len(mock_scan_view._selected_paths) == 1
        assert "/some/old/path" not in mock_scan_view._selected_paths

    def test_profile_selection_handles_tilde_paths(self, mock_scan_view, tmp_path):
        """Test that selecting a profile expands tilde (~) in paths."""
        self._setup_profile_mocks(mock_scan_view)
        mock_scan_view._show_toast = mock.MagicMock()

        # Create mock profile with tilde path
        mock_profile = mock.MagicMock()
        mock_profile.name = "Test Profile"
        mock_profile.targets = ["~"]  # Home directory always exists

        mock_scan_view._profile_list = [mock_profile]

        mock_dropdown = mock.MagicMock()
        mock_dropdown.get_selected.return_value = 1

        mock_scan_view._on_profile_selected(mock_dropdown, None)

        # Should have expanded path, not literal ~
        assert len(mock_scan_view._selected_paths) == 1
        assert "~" not in mock_scan_view._selected_paths[0]
        assert mock_scan_view._selected_paths[0] == os.path.expanduser("~")

    def test_profile_with_no_valid_targets_shows_toast(self, mock_scan_view):
        """Test that profile with no valid targets shows a warning toast."""
        self._setup_profile_mocks(mock_scan_view)
        mock_scan_view._show_toast = mock.MagicMock()

        # Create mock profile with non-existent targets
        mock_profile = mock.MagicMock()
        mock_profile.name = "Empty Profile"
        mock_profile.targets = ["/nonexistent/path1", "/nonexistent/path2"]

        mock_scan_view._profile_list = [mock_profile]

        mock_dropdown = mock.MagicMock()
        mock_dropdown.get_selected.return_value = 1

        mock_scan_view._on_profile_selected(mock_dropdown, None)

        # Toast should be shown for no valid targets
        mock_scan_view._show_toast.assert_called()
        call_args = mock_scan_view._show_toast.call_args[0][0]
        assert "Empty Profile" in call_args
        assert "no valid targets" in call_args

    def test_no_profile_selection_clears_profile(self, mock_scan_view):
        """Test that selecting 'No Profile' clears the selected profile."""
        self._setup_profile_mocks(mock_scan_view)

        # Set up a selected profile
        mock_scan_view._selected_profile = mock.MagicMock()

        mock_dropdown = mock.MagicMock()
        mock_dropdown.get_selected.return_value = 0  # "No Profile" option

        mock_scan_view._on_profile_selected(mock_dropdown, None)

        assert mock_scan_view._selected_profile is None


class TestGetSelectedPaths:
    """Tests for the get_selected_paths method."""

    def test_get_selected_paths_returns_copy(self, mock_scan_view):
        """Test that get_selected_paths returns a copy of the list."""
        mock_scan_view._selected_paths = ["/path1", "/path2"]

        result = mock_scan_view.get_selected_paths()

        # Should be equal but not the same object
        assert result == mock_scan_view._selected_paths
        assert result is not mock_scan_view._selected_paths

    def test_get_selected_paths_modification_safe(self, mock_scan_view):
        """Test that modifying returned list doesn't affect original."""
        mock_scan_view._selected_paths = ["/path1", "/path2"]

        result = mock_scan_view.get_selected_paths()
        result.append("/path3")

        assert len(mock_scan_view._selected_paths) == 2
        assert "/path3" not in mock_scan_view._selected_paths


class TestSetSelectedPath:
    """Tests for the _set_selected_path convenience method."""

    def test_set_selected_path_clears_and_adds(self, mock_scan_view):
        """Test that _set_selected_path clears existing and adds new path."""
        # Mock the UI elements that _add_path/_clear_paths interacts with
        mock_scan_view._paths_placeholder = mock.MagicMock()
        mock_scan_view._paths_listbox = mock.MagicMock()
        mock_scan_view._paths_listbox.get_first_child.return_value = None
        mock_scan_view._create_path_row = mock.MagicMock()
        mock_scan_view._update_selection_header = mock.MagicMock()
        mock_scan_view._selected_paths = ["/old/path1", "/old/path2"]

        mock_scan_view._set_selected_path("/new/path")

        assert mock_scan_view._selected_paths == ["/new/path"]
        assert len(mock_scan_view._selected_paths) == 1


# Basic verification test
def test_scan_view_multi_path_basic(mock_gi_modules):
    """
    Basic test function for pytest verification command.

    This test verifies the core multi-path functionality
    using a minimal mock setup.
    """
    mock_scanner_module = mock.MagicMock()
    mock_scanner_module.Scanner = mock.MagicMock()
    mock_scanner_module.ScanResult = mock.MagicMock()
    mock_scanner_module.ScanStatus = mock.MagicMock()

    mock_utils = mock.MagicMock()
    mock_utils.format_scan_path = lambda x: x  # Pass through as string

    with mock.patch.dict(
        sys.modules,
        {
            "src.core.scanner": mock_scanner_module,
            "src.core.quarantine": mock.MagicMock(),
            "src.core.utils": mock_utils,
            "src.ui.profile_dialogs": mock.MagicMock(),
            "src.ui.scan_results_dialog": mock.MagicMock(),
            "src.ui.utils": mock.MagicMock(),
            "src.ui.view_helpers": mock.MagicMock(),
        },
    ):
        from src.ui.scan_view import ScanView

        # Test 1: Class can be imported
        assert ScanView is not None

        # Test 2: Create mock instance and test basic path methods
        view = object.__new__(ScanView)
        view._selected_paths = []
        view._normalized_paths = set()
        # Mock UI elements used by _add_path and _remove_path
        view._paths_placeholder = mock.MagicMock()
        view._paths_listbox = mock.MagicMock()
        view._paths_listbox.get_first_child.return_value = None
        view._create_path_row = mock.MagicMock()
        view._update_selection_header = mock.MagicMock()

        # Test _add_path
        result = view._add_path("/test/path1")
        assert result is True
        assert len(view._selected_paths) == 1

        # Test duplicate detection
        result = view._add_path("/test/path1")
        assert result is False
        assert len(view._selected_paths) == 1

        # Test _add_path with second path
        result = view._add_path("/test/path2")
        assert result is True
        assert len(view._selected_paths) == 2

        # Test _remove_path
        result = view._remove_path("/test/path1")
        assert result is True
        assert len(view._selected_paths) == 1
        assert view._selected_paths == ["/test/path2"]

        # Test _clear_paths
        view._add_path("/test/path3")
        view._clear_paths()
        assert view._selected_paths == []
        # Note: _normalized_paths is NOT cleared by _clear_paths as per implementation

        # Test get_selected_paths returns copy
        view._selected_paths = ["/a", "/b"]
        view._normalized_paths = {"/a", "/b"}
        paths_copy = view.get_selected_paths()
        assert paths_copy == ["/a", "/b"]
        assert paths_copy is not view._selected_paths

        # All tests passed
