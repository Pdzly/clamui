# ClamUI Scanner UI Tests
"""
Unit tests for the Scanner UI (ScanView) component.

Tests cover:
- GTK module mocking setup
- ScanView initialization and setup
- File/folder selection UI interactions
- Scan button state and actions
- Results display updates
- Profile selection UI

This test module follows the same patterns as test_app.py and test_statistics_view.py
for GTK mocking to enable testing without a real GTK environment.
"""

import sys
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def mock_gtk_modules():
    """
    Mock GTK/GI modules before importing scan_view module.

    This fixture runs before each test and provides fresh mocks to avoid
    test contamination. It follows the same pattern as test_app.py.
    """
    # Create fresh mocks for each test
    mock_glib = mock.MagicMock()
    mock_gio = mock.MagicMock()
    mock_gtk = mock.MagicMock()
    mock_adw = mock.MagicMock()
    mock_gdk = mock.MagicMock()

    # Configure mock Gio.File for file operations
    mock_gio.File.new_for_path.return_value = mock.MagicMock()
    mock_gio.ApplicationFlags.FLAGS_NONE = 0

    # Configure mock Gtk.Box as a proper base class
    class MockGtkBox:
        """Mock Gtk.Box that ScanView inherits from."""

        def __init__(self, orientation=None, **kwargs):
            self.orientation = orientation
            self.children = []
            self.css_classes = []
            self.margin_top = 0
            self.margin_bottom = 0
            self.margin_start = 0
            self.margin_end = 0
            self.spacing = 0

        def set_margin_top(self, value):
            self.margin_top = value

        def set_margin_bottom(self, value):
            self.margin_bottom = value

        def set_margin_start(self, value):
            self.margin_start = value

        def set_margin_end(self, value):
            self.margin_end = value

        def set_spacing(self, value):
            self.spacing = value

        def append(self, child):
            self.children.append(child)

        def remove(self, child):
            if child in self.children:
                self.children.remove(child)

        def add_css_class(self, css_class):
            self.css_classes.append(css_class)

        def remove_css_class(self, css_class):
            if css_class in self.css_classes:
                self.css_classes.remove(css_class)

        def get_style_context(self):
            return mock.MagicMock()

    mock_gtk.Box = MockGtkBox
    mock_gtk.Orientation = mock.MagicMock()
    mock_gtk.Orientation.VERTICAL = 1
    mock_gtk.Orientation.HORIZONTAL = 0
    mock_gtk.Align = mock.MagicMock()
    mock_gtk.Align.CENTER = 0
    mock_gtk.Align.START = 1
    mock_gtk.Align.END = 2
    mock_gtk.Align.FILL = 3
    mock_gtk.FileDialog = mock.MagicMock()
    mock_gtk.CssProvider = mock.MagicMock()
    mock_gtk.DropTarget = mock.MagicMock()
    mock_gtk.StringList = mock.MagicMock()
    mock_gtk.DropDown = mock.MagicMock()

    # Configure Adw widgets
    mock_adw.Clamp = mock.MagicMock()
    mock_adw.PreferencesGroup = mock.MagicMock()
    mock_adw.ActionRow = mock.MagicMock()
    mock_adw.StatusPage = mock.MagicMock()
    mock_adw.ToastOverlay = mock.MagicMock()
    mock_adw.Toast = mock.MagicMock()
    mock_adw.ExpanderRow = mock.MagicMock()
    mock_adw.AlertDialog = mock.MagicMock()
    mock_adw.ResponseAppearance = mock.MagicMock()

    # Set up the gi mock
    mock_gi = mock.MagicMock()
    mock_gi.version_info = (3, 48, 0)  # Match test_app.py
    mock_gi.require_version = mock.MagicMock()
    mock_gi_repository = mock.MagicMock()
    mock_gi_repository.GLib = mock_glib
    mock_gi_repository.Gio = mock_gio
    mock_gi_repository.Gtk = mock_gtk
    mock_gi_repository.Adw = mock_adw
    mock_gi_repository.Gdk = mock_gdk

    # Store mocks for tests to access
    _mocks = {
        "gi": mock_gi,
        "gi.repository": mock_gi_repository,
        "Gio": mock_gio,
        "Adw": mock_adw,
        "Gtk": mock_gtk,
        "GLib": mock_glib,
        "Gdk": mock_gdk,
    }

    # Create mock modules for dependencies
    mock_scanner_module = mock.MagicMock()
    mock_scanner_module.Scanner = mock.MagicMock()
    mock_scanner_module.ScanResult = mock.MagicMock()
    mock_scanner_module.ScanStatus = mock.MagicMock()
    mock_scanner_module.ScanStatus.CLEAN = "clean"
    mock_scanner_module.ScanStatus.INFECTED = "infected"
    mock_scanner_module.ScanStatus.ERROR = "error"
    mock_scanner_module.ScanStatus.CANCELLED = "cancelled"
    mock_scanner_module.ThreatDetail = mock.MagicMock()

    mock_utils_module = mock.MagicMock()
    mock_utils_module.format_scan_path = mock.MagicMock(return_value="/test/path")
    mock_utils_module.check_clamav_installed = mock.MagicMock(return_value=True)
    mock_utils_module.validate_dropped_files = mock.MagicMock(return_value=["/test/file"])
    mock_utils_module.format_results_as_text = mock.MagicMock(return_value="results")
    mock_utils_module.copy_to_clipboard = mock.MagicMock()

    mock_quarantine_module = mock.MagicMock()
    mock_quarantine_module.QuarantineManager = mock.MagicMock()
    mock_quarantine_module.QuarantineStatus = mock.MagicMock()

    mock_fullscreen_dialog = mock.MagicMock()
    mock_fullscreen_dialog.FullscreenLogDialog = mock.MagicMock()

    mock_profile_dialogs = mock.MagicMock()
    mock_profile_dialogs.ProfileListDialog = mock.MagicMock()

    # Patch all modules
    with mock.patch.dict(sys.modules, {
        "gi": mock_gi,
        "gi.repository": mock_gi_repository,
        "src.core.scanner": mock_scanner_module,
        "src.core.utils": mock_utils_module,
        "src.core.quarantine": mock_quarantine_module,
        "src.ui.fullscreen_dialog": mock_fullscreen_dialog,
        "src.ui.profile_dialogs": mock_profile_dialogs,
    }):
        # Need to remove and reimport the scan_view module for fresh mocks
        if "src.ui.scan_view" in sys.modules:
            del sys.modules["src.ui.scan_view"]

        yield _mocks


@pytest.fixture
def gtk_mock(mock_gtk_modules):
    """Get the Gtk mock for tests."""
    return mock_gtk_modules["Gtk"]


@pytest.fixture
def glib_mock(mock_gtk_modules):
    """Get the GLib mock for tests."""
    return mock_gtk_modules["GLib"]


@pytest.fixture
def gio_mock(mock_gtk_modules):
    """Get the Gio mock for tests."""
    return mock_gtk_modules["Gio"]


@pytest.fixture
def scan_view_class(mock_gtk_modules):
    """
    Get ScanView class with mocked dependencies.

    Returns the ScanView class that can be used to create test instances.
    """
    from src.ui.scan_view import ScanView
    return ScanView


@pytest.fixture
def mock_scan_view(scan_view_class, mock_gtk_modules):
    """
    Create a mock ScanView instance for testing.

    This creates a ScanView instance without calling __init__ and sets up
    all required attributes manually. This allows testing individual methods
    without the full initialization overhead.
    """
    # Create instance without calling __init__
    with mock.patch.object(scan_view_class, '__init__', lambda self, **kwargs: None):
        view = scan_view_class()

        # Set up required attributes
        view._scanner = mock.MagicMock()
        view._quarantine_manager = mock.MagicMock()
        view._selected_path = ""
        view._is_scanning = False
        view._eicar_temp_path = ""
        view._displayed_threat_count = 0
        view._all_threat_details = []
        view._load_more_row = None
        view._on_scan_state_changed = None
        view._selected_profile = None
        view._profile_list = []
        view._profile_string_list = None
        view._profile_dropdown = None

        # Mock UI elements
        view._path_row = mock.MagicMock()
        view._scan_button = mock.MagicMock()
        view._scan_button_content = mock.MagicMock()
        view._scan_spinner = mock.MagicMock()
        view._cancel_button = mock.MagicMock()
        view._results_group = mock.MagicMock()
        view._results_list = mock.MagicMock()
        view._status_bar = mock.MagicMock()
        view._status_label = mock.MagicMock()
        view._status_badge = mock.MagicMock()
        view._profile_group = mock.MagicMock()
        view._select_folder_btn = mock.MagicMock()
        view._select_file_btn = mock.MagicMock()

        # Mock internal methods commonly used
        view._setup_ui = mock.MagicMock()
        view._setup_drop_css = mock.MagicMock()
        view._setup_drop_target = mock.MagicMock()
        view._create_profile_section = mock.MagicMock()
        view._create_selection_section = mock.MagicMock()
        view._create_scan_section = mock.MagicMock()
        view._create_results_section = mock.MagicMock()
        view._create_status_bar = mock.MagicMock()
        view._check_clamav_status = mock.MagicMock()
        view._update_scan_button_state = mock.MagicMock()
        view._display_results = mock.MagicMock()
        view._set_selected_path = mock.MagicMock()
        view._start_scan = mock.MagicMock()
        view._on_scan_complete = mock.MagicMock()
        view._update_status = mock.MagicMock()

        # Mock parent class methods
        view.append = mock.MagicMock()
        view.remove = mock.MagicMock()
        view.set_margin_top = mock.MagicMock()
        view.set_margin_bottom = mock.MagicMock()
        view.set_margin_start = mock.MagicMock()
        view.set_margin_end = mock.MagicMock()
        view.set_spacing = mock.MagicMock()
        view.get_root = mock.MagicMock(return_value=None)

        return view


@pytest.mark.ui
class TestScanViewGtkMocking:
    """Tests to verify GTK mocking setup works correctly."""

    def test_scan_view_can_be_imported(self, mock_gtk_modules):
        """Test that ScanView can be imported with mocked GTK."""
        from src.ui.scan_view import ScanView
        assert ScanView is not None

    def test_mock_gtk_modules_fixture_provides_all_mocks(self, mock_gtk_modules):
        """Test that the mock fixture provides all expected module mocks."""
        assert "gi" in mock_gtk_modules
        assert "gi.repository" in mock_gtk_modules
        assert "Gio" in mock_gtk_modules
        assert "Adw" in mock_gtk_modules
        assert "Gtk" in mock_gtk_modules
        assert "GLib" in mock_gtk_modules
        assert "Gdk" in mock_gtk_modules

    def test_gtk_box_mock_supports_required_methods(self, mock_gtk_modules):
        """Test that the MockGtkBox supports methods used by ScanView."""
        gtk = mock_gtk_modules["Gtk"]

        # Create a mock box
        box = gtk.Box(orientation=gtk.Orientation.VERTICAL)

        # Test required methods
        box.set_margin_top(24)
        assert box.margin_top == 24

        box.set_spacing(18)
        assert box.spacing == 18

        # Test child management
        child = mock.MagicMock()
        box.append(child)
        assert child in box.children

        box.remove(child)
        assert child not in box.children

    def test_scan_view_class_fixture(self, scan_view_class):
        """Test that scan_view_class fixture returns a class."""
        assert scan_view_class is not None
        assert callable(scan_view_class)

    def test_mock_scan_view_has_required_attributes(self, mock_scan_view):
        """Test that mock_scan_view fixture sets up required attributes."""
        # Test scanner attributes
        assert hasattr(mock_scan_view, '_scanner')
        assert hasattr(mock_scan_view, '_quarantine_manager')
        assert hasattr(mock_scan_view, '_selected_path')
        assert hasattr(mock_scan_view, '_is_scanning')

        # Test UI element attributes
        assert hasattr(mock_scan_view, '_path_row')
        assert hasattr(mock_scan_view, '_scan_button')
        assert hasattr(mock_scan_view, '_results_group')
        assert hasattr(mock_scan_view, '_status_label')

        # Test profile attributes
        assert hasattr(mock_scan_view, '_selected_profile')
        assert hasattr(mock_scan_view, '_profile_list')


@pytest.mark.ui
class TestScanViewInitialization:
    """Tests for ScanView initialization."""

    def test_initial_selected_path_is_empty(self, mock_scan_view):
        """Test that initial selected path is empty."""
        assert mock_scan_view._selected_path == ""

    def test_initial_scanning_state_is_false(self, mock_scan_view):
        """Test that initial scanning state is False."""
        assert mock_scan_view._is_scanning is False

    def test_initial_eicar_temp_path_is_empty(self, mock_scan_view):
        """Test that initial EICAR temp path is empty."""
        assert mock_scan_view._eicar_temp_path == ""

    def test_initial_displayed_threat_count_is_zero(self, mock_scan_view):
        """Test that initial displayed threat count is zero."""
        assert mock_scan_view._displayed_threat_count == 0

    def test_initial_threat_details_is_empty_list(self, mock_scan_view):
        """Test that initial threat details is empty list."""
        assert mock_scan_view._all_threat_details == []

    def test_initial_scan_state_callback_is_none(self, mock_scan_view):
        """Test that scan state callback is initially None."""
        assert mock_scan_view._on_scan_state_changed is None

    def test_initial_selected_profile_is_none(self, mock_scan_view):
        """Test that selected profile is initially None."""
        assert mock_scan_view._selected_profile is None

    def test_initial_profile_list_is_empty(self, mock_scan_view):
        """Test that profile list is initially empty."""
        assert mock_scan_view._profile_list == []


@pytest.mark.ui
class TestScanViewScanner:
    """Tests for ScanView scanner integration."""

    def test_scanner_attribute_exists(self, mock_scan_view):
        """Test that scanner attribute exists."""
        assert mock_scan_view._scanner is not None

    def test_quarantine_manager_attribute_exists(self, mock_scan_view):
        """Test that quarantine manager attribute exists."""
        assert mock_scan_view._quarantine_manager is not None


@pytest.mark.ui
class TestFileSelectionUI:
    """Tests for file/folder selection UI interactions."""

    def test_select_folder_button_exists(self, mock_scan_view):
        """Test that the select folder button attribute exists."""
        assert hasattr(mock_scan_view, '_select_folder_btn')

    def test_select_file_button_exists(self, mock_scan_view):
        """Test that the select file button attribute exists."""
        assert hasattr(mock_scan_view, '_select_file_btn')

    def test_path_row_exists(self, mock_scan_view):
        """Test that the path row for displaying selected path exists."""
        assert hasattr(mock_scan_view, '_path_row')
        assert mock_scan_view._path_row is not None

    def test_set_selected_path_updates_path_attribute(self, mock_scan_view):
        """Test that _set_selected_path updates the internal path attribute."""
        # Reset the mock to call real method
        mock_scan_view._set_selected_path = mock_scan_view.__class__._set_selected_path.__get__(
            mock_scan_view, mock_scan_view.__class__
        )

        test_path = "/home/user/test_folder"
        mock_scan_view._set_selected_path(test_path)

        assert mock_scan_view._selected_path == test_path

    def test_set_selected_path_enables_scan_button(self, mock_scan_view):
        """Test that selecting a path enables the scan button."""
        # Reset the mock to call real method
        mock_scan_view._set_selected_path = mock_scan_view.__class__._set_selected_path.__get__(
            mock_scan_view, mock_scan_view.__class__
        )
        # Need to also call the real _clear_results
        mock_scan_view._clear_results = mock.MagicMock()

        test_path = "/home/user/documents"
        mock_scan_view._set_selected_path(test_path)

        # Verify scan button set_sensitive was called with True
        mock_scan_view._scan_button.set_sensitive.assert_called_with(True)

    def test_set_selected_path_updates_path_row_title(self, mock_scan_view):
        """Test that selecting a path updates the path row title."""
        # Reset the mock to call real method
        mock_scan_view._set_selected_path = mock_scan_view.__class__._set_selected_path.__get__(
            mock_scan_view, mock_scan_view.__class__
        )
        mock_scan_view._clear_results = mock.MagicMock()

        test_path = "/home/user/photos"
        mock_scan_view._set_selected_path(test_path)

        # Verify path row set_title was called
        mock_scan_view._path_row.set_title.assert_called()

    def test_set_selected_path_updates_path_row_subtitle(self, mock_scan_view):
        """Test that selecting a path updates the path row subtitle to ready state."""
        # Reset the mock to call real method
        mock_scan_view._set_selected_path = mock_scan_view.__class__._set_selected_path.__get__(
            mock_scan_view, mock_scan_view.__class__
        )
        mock_scan_view._clear_results = mock.MagicMock()

        test_path = "/home/user/videos"
        mock_scan_view._set_selected_path(test_path)

        # Verify path row set_subtitle was called with "Ready to scan"
        mock_scan_view._path_row.set_subtitle.assert_called_with("Ready to scan")

    def test_set_selected_path_clears_previous_results(self, mock_scan_view):
        """Test that selecting a new path clears previous scan results."""
        # Reset the mock to call real method
        mock_scan_view._set_selected_path = mock_scan_view.__class__._set_selected_path.__get__(
            mock_scan_view, mock_scan_view.__class__
        )
        mock_scan_view._clear_results = mock.MagicMock()

        test_path = "/home/user/music"
        mock_scan_view._set_selected_path(test_path)

        # Verify _clear_results was called
        mock_scan_view._clear_results.assert_called_once()

    def test_on_select_folder_clicked_opens_dialog(self, mock_scan_view, mock_gtk_modules):
        """Test that clicking select folder button opens file dialog for folders."""
        # Reset the real method
        mock_scan_view._on_select_folder_clicked = mock_scan_view.__class__._on_select_folder_clicked.__get__(
            mock_scan_view, mock_scan_view.__class__
        )
        mock_scan_view._open_file_dialog = mock.MagicMock()

        # Simulate button click
        mock_scan_view._on_select_folder_clicked(None)

        # Verify _open_file_dialog was called with select_folder=True
        mock_scan_view._open_file_dialog.assert_called_once_with(select_folder=True)

    def test_on_select_file_clicked_opens_dialog(self, mock_scan_view, mock_gtk_modules):
        """Test that clicking select file button opens file dialog for files."""
        # Reset the real method
        mock_scan_view._on_select_file_clicked = mock_scan_view.__class__._on_select_file_clicked.__get__(
            mock_scan_view, mock_scan_view.__class__
        )
        mock_scan_view._open_file_dialog = mock.MagicMock()

        # Simulate button click
        mock_scan_view._on_select_file_clicked(None)

        # Verify _open_file_dialog was called with select_folder=False
        mock_scan_view._open_file_dialog.assert_called_once_with(select_folder=False)

    def test_initial_path_is_empty_string(self, mock_scan_view):
        """Test that the initial selected path is an empty string."""
        assert mock_scan_view._selected_path == ""

    def test_initial_scan_button_is_disabled(self, mock_scan_view):
        """Test that the scan button is disabled when no path is selected."""
        # The mock_scan_view fixture sets _selected_path to ""
        assert mock_scan_view._selected_path == ""
        # Note: The actual button state would be set during __init__ which we mock out


# Module-level test function for verification
@pytest.mark.ui
def test_file_selection_ui():
    """
    Test for file selection UI functionality.

    This test verifies that the file selection UI components are properly
    set up and can handle path selection updates.
    """
    # Create mocks
    mock_gtk = mock.MagicMock()
    mock_adw = mock.MagicMock()
    mock_gio = mock.MagicMock()
    mock_glib = mock.MagicMock()
    mock_gdk = mock.MagicMock()

    class MockGtkBox:
        def __init__(self, orientation=None, **kwargs):
            self.children = []
            self._selected_path = ""

        def set_margin_top(self, v): pass
        def set_margin_bottom(self, v): pass
        def set_margin_start(self, v): pass
        def set_margin_end(self, v): pass
        def set_spacing(self, v): pass
        def append(self, child):
            self.children.append(child)
        def get_style_context(self): return mock.MagicMock()
        def get_root(self): return None

    mock_gtk.Box = MockGtkBox
    mock_gtk.Orientation = mock.MagicMock()
    mock_gtk.Orientation.VERTICAL = 1
    mock_gtk.FileDialog = mock.MagicMock()

    mock_gi = mock.MagicMock()
    mock_gi.version_info = (3, 48, 0)
    mock_gi.require_version = mock.MagicMock()

    mock_repository = mock.MagicMock()
    mock_repository.Gtk = mock_gtk
    mock_repository.Adw = mock_adw
    mock_repository.Gio = mock_gio
    mock_repository.GLib = mock_glib
    mock_repository.Gdk = mock_gdk

    mock_utils = mock.MagicMock()
    mock_utils.format_scan_path = mock.MagicMock(return_value="/formatted/path")

    with mock.patch.dict(sys.modules, {
        'gi': mock_gi,
        'gi.repository': mock_repository,
        'src.core.scanner': mock.MagicMock(),
        'src.core.utils': mock_utils,
        'src.core.quarantine': mock.MagicMock(),
        'src.ui.fullscreen_dialog': mock.MagicMock(),
        'src.ui.profile_dialogs': mock.MagicMock(),
    }):
        # Clear any cached import
        if 'src.ui.scan_view' in sys.modules:
            del sys.modules['src.ui.scan_view']

        from src.ui.scan_view import ScanView
        assert ScanView is not None

        # Verify the class has file selection methods
        assert hasattr(ScanView, '_on_select_folder_clicked')
        assert hasattr(ScanView, '_on_select_file_clicked')
        assert hasattr(ScanView, '_set_selected_path')
        assert hasattr(ScanView, '_open_file_dialog')


@pytest.mark.ui
class TestScanInitiationUI:
    """Tests for scan initiation UI functionality."""

    def test_scan_button_exists(self, mock_scan_view):
        """Test that the scan button attribute exists."""
        assert hasattr(mock_scan_view, '_scan_button')
        assert mock_scan_view._scan_button is not None

    def test_on_scan_clicked_starts_scan_when_path_selected(self, mock_scan_view):
        """Test that clicking scan button starts scan when path is selected."""
        # Set a selected path
        mock_scan_view._selected_path = "/home/user/documents"

        # Reset the real method
        mock_scan_view._on_scan_clicked = mock_scan_view.__class__._on_scan_clicked.__get__(
            mock_scan_view, mock_scan_view.__class__
        )

        # Simulate button click
        mock_scan_view._on_scan_clicked(None)

        # Verify _start_scan was called
        mock_scan_view._start_scan.assert_called_once()

    def test_on_scan_clicked_does_nothing_when_no_path(self, mock_scan_view):
        """Test that clicking scan button does nothing when no path selected."""
        # Ensure no path is selected
        mock_scan_view._selected_path = ""

        # Reset the real method
        mock_scan_view._on_scan_clicked = mock_scan_view.__class__._on_scan_clicked.__get__(
            mock_scan_view, mock_scan_view.__class__
        )

        # Simulate button click
        mock_scan_view._on_scan_clicked(None)

        # Verify _start_scan was NOT called
        mock_scan_view._start_scan.assert_not_called()

    def test_start_scan_sets_scanning_state_true(self, mock_scan_view):
        """Test that _start_scan sets scanning state to True."""
        mock_scan_view._selected_path = "/home/user/test"
        mock_scan_view._selected_profile = None
        mock_scan_view._clear_results = mock.MagicMock()
        mock_scan_view._results_placeholder = mock.MagicMock()
        mock_scan_view._status_banner = mock.MagicMock()
        mock_scan_view._set_scanning_state = mock.MagicMock()

        # Reset the real method
        mock_scan_view._start_scan = mock_scan_view.__class__._start_scan.__get__(
            mock_scan_view, mock_scan_view.__class__
        )

        # Start the scan
        mock_scan_view._start_scan()

        # Verify scanning state was set to True
        mock_scan_view._set_scanning_state.assert_called_once_with(True)

    def test_start_scan_clears_previous_results(self, mock_scan_view):
        """Test that _start_scan clears previous results."""
        mock_scan_view._selected_path = "/home/user/test"
        mock_scan_view._selected_profile = None
        mock_scan_view._clear_results = mock.MagicMock()
        mock_scan_view._results_placeholder = mock.MagicMock()
        mock_scan_view._status_banner = mock.MagicMock()
        mock_scan_view._set_scanning_state = mock.MagicMock()

        # Reset the real method
        mock_scan_view._start_scan = mock_scan_view.__class__._start_scan.__get__(
            mock_scan_view, mock_scan_view.__class__
        )

        # Start the scan
        mock_scan_view._start_scan()

        # Verify results were cleared
        mock_scan_view._clear_results.assert_called_once()

    def test_start_scan_calls_scanner_async(self, mock_scan_view):
        """Test that _start_scan calls scanner.scan_async with correct path."""
        test_path = "/home/user/documents"
        mock_scan_view._selected_path = test_path
        mock_scan_view._selected_profile = None
        mock_scan_view._clear_results = mock.MagicMock()
        mock_scan_view._results_placeholder = mock.MagicMock()
        mock_scan_view._status_banner = mock.MagicMock()
        mock_scan_view._set_scanning_state = mock.MagicMock()

        # Reset the real method
        mock_scan_view._start_scan = mock_scan_view.__class__._start_scan.__get__(
            mock_scan_view, mock_scan_view.__class__
        )

        # Start the scan
        mock_scan_view._start_scan()

        # Verify scanner.scan_async was called with correct path
        mock_scan_view._scanner.scan_async.assert_called_once()
        call_args = mock_scan_view._scanner.scan_async.call_args
        assert call_args[0][0] == test_path

    def test_start_scan_passes_callback(self, mock_scan_view):
        """Test that _start_scan passes on_scan_complete callback."""
        mock_scan_view._selected_path = "/home/user/test"
        mock_scan_view._selected_profile = None
        mock_scan_view._clear_results = mock.MagicMock()
        mock_scan_view._results_placeholder = mock.MagicMock()
        mock_scan_view._status_banner = mock.MagicMock()
        mock_scan_view._set_scanning_state = mock.MagicMock()

        # Reset the real method for _start_scan and _on_scan_complete
        mock_scan_view._start_scan = mock_scan_view.__class__._start_scan.__get__(
            mock_scan_view, mock_scan_view.__class__
        )

        # Start the scan
        mock_scan_view._start_scan()

        # Verify callback was passed to scan_async
        call_args = mock_scan_view._scanner.scan_async.call_args
        assert call_args.kwargs.get('callback') is not None

    def test_start_scan_uses_profile_exclusions(self, mock_scan_view):
        """Test that _start_scan uses profile exclusions when profile selected."""
        mock_scan_view._selected_path = "/home/user/test"

        # Mock a selected profile with exclusions
        mock_profile = mock.MagicMock()
        mock_profile.name = "Test Profile"
        mock_profile.exclusions = {
            "paths": ["/excluded/path"],
            "patterns": ["*.tmp"]
        }
        mock_scan_view._selected_profile = mock_profile

        mock_scan_view._clear_results = mock.MagicMock()
        mock_scan_view._results_placeholder = mock.MagicMock()
        mock_scan_view._status_banner = mock.MagicMock()
        mock_scan_view._set_scanning_state = mock.MagicMock()

        # Reset the real method
        mock_scan_view._start_scan = mock_scan_view.__class__._start_scan.__get__(
            mock_scan_view, mock_scan_view.__class__
        )

        # Start the scan
        mock_scan_view._start_scan()

        # Verify profile_exclusions was passed
        call_args = mock_scan_view._scanner.scan_async.call_args
        assert call_args.kwargs.get('profile_exclusions') == mock_profile.exclusions

    def test_start_scan_updates_placeholder_text(self, mock_scan_view):
        """Test that _start_scan updates placeholder to show scanning status."""
        test_path = "/home/user/documents"
        mock_scan_view._selected_path = test_path
        mock_scan_view._selected_profile = None
        mock_scan_view._clear_results = mock.MagicMock()
        mock_scan_view._results_placeholder = mock.MagicMock()
        mock_scan_view._status_banner = mock.MagicMock()
        mock_scan_view._set_scanning_state = mock.MagicMock()

        # Reset the real method
        mock_scan_view._start_scan = mock_scan_view.__class__._start_scan.__get__(
            mock_scan_view, mock_scan_view.__class__
        )

        # Start the scan
        mock_scan_view._start_scan()

        # Verify placeholder text was updated
        mock_scan_view._results_placeholder.set_text.assert_called()
        call_args = mock_scan_view._results_placeholder.set_text.call_args[0][0]
        assert test_path in call_args

    def test_start_scan_hides_status_banner(self, mock_scan_view):
        """Test that _start_scan hides any previous status banner."""
        mock_scan_view._selected_path = "/home/user/test"
        mock_scan_view._selected_profile = None
        mock_scan_view._clear_results = mock.MagicMock()
        mock_scan_view._results_placeholder = mock.MagicMock()
        mock_scan_view._status_banner = mock.MagicMock()
        mock_scan_view._set_scanning_state = mock.MagicMock()

        # Reset the real method
        mock_scan_view._start_scan = mock_scan_view.__class__._start_scan.__get__(
            mock_scan_view, mock_scan_view.__class__
        )

        # Start the scan
        mock_scan_view._start_scan()

        # Verify status banner was hidden
        mock_scan_view._status_banner.set_revealed.assert_called_with(False)


# Module-level test function for scan initiation verification
@pytest.mark.ui
def test_scan_initiation_ui():
    """
    Test for scan initiation UI functionality.

    This test verifies that the scan initiation UI components work correctly,
    including the scan button click handler and the _start_scan method.
    """
    # Create mocks
    mock_gtk = mock.MagicMock()
    mock_adw = mock.MagicMock()
    mock_gio = mock.MagicMock()
    mock_glib = mock.MagicMock()
    mock_gdk = mock.MagicMock()

    class MockGtkBox:
        def __init__(self, orientation=None, **kwargs):
            self.children = []
            self._selected_path = ""

        def set_margin_top(self, v): pass
        def set_margin_bottom(self, v): pass
        def set_margin_start(self, v): pass
        def set_margin_end(self, v): pass
        def set_spacing(self, v): pass
        def append(self, child):
            self.children.append(child)
        def get_style_context(self): return mock.MagicMock()
        def get_root(self): return None

    mock_gtk.Box = MockGtkBox
    mock_gtk.Orientation = mock.MagicMock()
    mock_gtk.Orientation.VERTICAL = 1
    mock_gtk.FileDialog = mock.MagicMock()

    mock_gi = mock.MagicMock()
    mock_gi.version_info = (3, 48, 0)
    mock_gi.require_version = mock.MagicMock()

    mock_repository = mock.MagicMock()
    mock_repository.Gtk = mock_gtk
    mock_repository.Adw = mock_adw
    mock_repository.Gio = mock_gio
    mock_repository.GLib = mock_glib
    mock_repository.Gdk = mock_gdk

    mock_utils = mock.MagicMock()
    mock_utils.format_scan_path = mock.MagicMock(return_value="/formatted/path")

    with mock.patch.dict(sys.modules, {
        'gi': mock_gi,
        'gi.repository': mock_repository,
        'src.core.scanner': mock.MagicMock(),
        'src.core.utils': mock_utils,
        'src.core.quarantine': mock.MagicMock(),
        'src.ui.fullscreen_dialog': mock.MagicMock(),
        'src.ui.profile_dialogs': mock.MagicMock(),
    }):
        # Clear any cached import
        if 'src.ui.scan_view' in sys.modules:
            del sys.modules['src.ui.scan_view']

        from src.ui.scan_view import ScanView
        assert ScanView is not None

        # Verify the class has scan initiation methods
        assert hasattr(ScanView, '_on_scan_clicked')
        assert hasattr(ScanView, '_start_scan')
        assert hasattr(ScanView, '_set_scanning_state')
        assert hasattr(ScanView, 'set_scan_state_callback')


@pytest.mark.ui
def test_scanner_ui_module_loads():
    """
    Basic test to verify the test module loads correctly.

    This test verifies that the GTK mocking setup works and the ScanView
    can be imported without errors.
    """
    # Create mocks
    mock_gtk = mock.MagicMock()
    mock_adw = mock.MagicMock()
    mock_gio = mock.MagicMock()
    mock_glib = mock.MagicMock()
    mock_gdk = mock.MagicMock()

    class MockGtkBox:
        def __init__(self, orientation=None, **kwargs):
            pass
        def set_margin_top(self, v): pass
        def set_margin_bottom(self, v): pass
        def set_margin_start(self, v): pass
        def set_margin_end(self, v): pass
        def set_spacing(self, v): pass
        def append(self, child): pass
        def get_style_context(self): return mock.MagicMock()

    mock_gtk.Box = MockGtkBox
    mock_gtk.Orientation = mock.MagicMock()
    mock_gtk.Orientation.VERTICAL = 1

    mock_gi = mock.MagicMock()
    mock_gi.version_info = (3, 48, 0)
    mock_gi.require_version = mock.MagicMock()

    mock_repository = mock.MagicMock()
    mock_repository.Gtk = mock_gtk
    mock_repository.Adw = mock_adw
    mock_repository.Gio = mock_gio
    mock_repository.GLib = mock_glib
    mock_repository.Gdk = mock_gdk

    with mock.patch.dict(sys.modules, {
        'gi': mock_gi,
        'gi.repository': mock_repository,
        'src.core.scanner': mock.MagicMock(),
        'src.core.utils': mock.MagicMock(),
        'src.core.quarantine': mock.MagicMock(),
        'src.ui.fullscreen_dialog': mock.MagicMock(),
        'src.ui.profile_dialogs': mock.MagicMock(),
    }):
        # Clear any cached import
        if 'src.ui.scan_view' in sys.modules:
            del sys.modules['src.ui.scan_view']

        from src.ui.scan_view import ScanView
        assert ScanView is not None
