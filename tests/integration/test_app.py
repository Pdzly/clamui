# ClamUI App Tests
"""Unit tests for the ClamUIApp application class."""

import sys
from unittest import mock

import pytest


# Create a mock setup function to prepare mocks before each test
@pytest.fixture(autouse=True)
def mock_gtk_modules():
    """Mock GTK/GI modules before importing app module."""
    # Create fresh mocks for each test
    mock_glib = mock.MagicMock()
    mock_gio = mock.MagicMock()
    mock_gtk = mock.MagicMock()
    mock_adw = mock.MagicMock()

    # Configure mock Gio.SimpleAction
    mock_gio.SimpleAction.new.return_value = mock.MagicMock()
    mock_gio.ApplicationFlags.FLAGS_NONE = 0

    # Configure mock Adw.Application as a proper base class
    class MockAdwApplication:
        def __init__(self, **kwargs):
            self.application_id = kwargs.get("application_id", "")
            self.flags = kwargs.get("flags", 0)
            self.add_action = mock.MagicMock()
            self.set_accels_for_action = mock.MagicMock()
            self.quit = mock.MagicMock()
            self.props = mock.MagicMock()

    mock_adw.Application = MockAdwApplication
    mock_adw.AboutDialog = mock.MagicMock

    # Set up the gi mock
    mock_gi = mock.MagicMock()
    mock_gi.version_info = (3, 48, 0)  # Required for matplotlib backend_gtk4.py comparison
    mock_gi.require_version = mock.MagicMock()
    mock_gi_repository = mock.MagicMock()
    mock_gi_repository.GLib = mock_glib
    mock_gi_repository.Gio = mock_gio
    mock_gi_repository.Gtk = mock_gtk
    mock_gi_repository.Adw = mock_adw

    # Store mocks for tests to access
    _mocks = {
        "gi": mock_gi,
        "gi.repository": mock_gi_repository,
        "Gio": mock_gio,
        "Adw": mock_adw,
        "Gtk": mock_gtk,
        "GLib": mock_glib,
    }

    # Mock matplotlib gtk backend to avoid import issues
    mock_backend = mock.MagicMock()

    # Patch modules
    with mock.patch.dict(
        sys.modules,
        {
            "gi": mock_gi,
            "gi.repository": mock_gi_repository,
            "matplotlib.backends.backend_gtk4": mock_backend,
            "matplotlib.backends.backend_gtk4agg": mock_backend,
            "src.ui.window": mock.MagicMock(),
            "src.ui.scan_view": mock.MagicMock(),
            "src.ui.update_view": mock.MagicMock(),
            "src.ui.logs_view": mock.MagicMock(),
            "src.ui.components_view": mock.MagicMock(),
            "src.ui.preferences": mock.MagicMock(),
            "src.ui.statistics_view": mock.MagicMock(),
        },
    ):
        # Need to remove and reimport the app module for fresh mocks
        if "src.app" in sys.modules:
            del sys.modules["src.app"]

        yield _mocks


@pytest.fixture
def gio_mock(mock_gtk_modules):
    """Get the Gio mock for tests."""
    return mock_gtk_modules["Gio"]


@pytest.fixture
def app(mock_gtk_modules):
    """Create a ClamUIApp instance for testing."""
    from src.app import ClamUIApp

    return ClamUIApp()


class TestClamUIAppSetup:
    """Tests for ClamUIApp initialization and setup."""

    def test_app_has_correct_application_id(self, app):
        """Test that the application has the correct application ID."""
        assert app.application_id == "io.github.linx_systems.ClamUI"

    def test_app_has_version(self, app):
        """Test that the application has a version string."""
        assert hasattr(app, "version")
        assert isinstance(app.version, str)
        assert len(app.version) > 0

    def test_app_has_app_name(self, app):
        """Test that the application has an app name."""
        assert hasattr(app, "app_name")
        assert app.app_name == "ClamUI"


class TestClamUIAppActions:
    """Tests for ClamUIApp actions including preferences."""

    def test_setup_actions_creates_quit_action(self, app, gio_mock):
        """Test that _setup_actions creates a quit action."""
        gio_mock.SimpleAction.new.reset_mock()
        app._setup_actions()

        # Find call to SimpleAction.new with "quit"
        quit_calls = [
            call for call in gio_mock.SimpleAction.new.call_args_list if call[0][0] == "quit"
        ]
        assert len(quit_calls) == 1

    def test_setup_actions_creates_about_action(self, app, gio_mock):
        """Test that _setup_actions creates an about action."""
        gio_mock.SimpleAction.new.reset_mock()
        app._setup_actions()

        # Find call to SimpleAction.new with "about"
        about_calls = [
            call for call in gio_mock.SimpleAction.new.call_args_list if call[0][0] == "about"
        ]
        assert len(about_calls) == 1

    def test_setup_actions_creates_preferences_action(self, app, gio_mock):
        """Test that _setup_actions creates a preferences action."""
        gio_mock.SimpleAction.new.reset_mock()
        app._setup_actions()

        # Find call to SimpleAction.new with "preferences"
        preferences_calls = [
            call for call in gio_mock.SimpleAction.new.call_args_list if call[0][0] == "preferences"
        ]
        assert len(preferences_calls) == 1

    def test_preferences_action_is_added_to_app(self, app):
        """Test that the preferences action is added to the application."""
        app._setup_actions()

        # Verify add_action was called
        app.add_action.assert_called()

    def test_preferences_keyboard_shortcut_set(self, app):
        """Test that Ctrl+, shortcut is set for preferences action."""
        app._setup_actions()

        # Find call to set_accels_for_action with "app.preferences"
        accel_calls = [
            call
            for call in app.set_accels_for_action.call_args_list
            if call[0][0] == "app.preferences"
        ]
        assert len(accel_calls) == 1
        # Verify the shortcut is Ctrl+comma
        assert accel_calls[0][0][1] == ["<Control>comma"]

    def test_quit_keyboard_shortcut_set(self, app):
        """Test that Ctrl+q shortcut is set for quit action."""
        app._setup_actions()

        # Find call to set_accels_for_action with "app.quit"
        accel_calls = [
            call for call in app.set_accels_for_action.call_args_list if call[0][0] == "app.quit"
        ]
        assert len(accel_calls) == 1
        assert accel_calls[0][0][1] == ["<Control>q"]


class TestClamUIAppPreferencesHandler:
    """Tests for the preferences action handler."""

    def test_on_preferences_handler_exists(self, app):
        """Test that the _on_preferences handler method exists."""
        assert hasattr(app, "_on_preferences")
        assert callable(app._on_preferences)

    def test_on_preferences_callable_without_error(self, app, mock_gtk_modules):
        """Test that _on_preferences can be called without raising errors."""
        # Set up mock active_window
        app.props = mock.MagicMock()
        app.props.active_window = mock.MagicMock()

        # Should not raise any exceptions
        app._on_preferences(None, None)


class TestClamUIAppViewSwitching:
    """Tests for view switching actions."""

    def test_setup_actions_creates_show_scan_action(self, app, gio_mock):
        """Test that _setup_actions creates a show-scan action."""
        gio_mock.SimpleAction.new.reset_mock()
        app._setup_actions()

        show_scan_calls = [
            call for call in gio_mock.SimpleAction.new.call_args_list if call[0][0] == "show-scan"
        ]
        assert len(show_scan_calls) == 1

    def test_setup_actions_creates_show_update_action(self, app, gio_mock):
        """Test that _setup_actions creates a show-update action."""
        gio_mock.SimpleAction.new.reset_mock()
        app._setup_actions()

        show_update_calls = [
            call for call in gio_mock.SimpleAction.new.call_args_list if call[0][0] == "show-update"
        ]
        assert len(show_update_calls) == 1

    def test_setup_actions_creates_show_logs_action(self, app, gio_mock):
        """Test that _setup_actions creates a show-logs action."""
        gio_mock.SimpleAction.new.reset_mock()
        app._setup_actions()

        show_logs_calls = [
            call for call in gio_mock.SimpleAction.new.call_args_list if call[0][0] == "show-logs"
        ]
        assert len(show_logs_calls) == 1

    def test_setup_actions_creates_show_components_action(self, app, gio_mock):
        """Test that _setup_actions creates a show-components action."""
        gio_mock.SimpleAction.new.reset_mock()
        app._setup_actions()

        show_components_calls = [
            call
            for call in gio_mock.SimpleAction.new.call_args_list
            if call[0][0] == "show-components"
        ]
        assert len(show_components_calls) == 1

    def test_on_show_scan_handler_exists(self, app):
        """Test that the _on_show_scan handler method exists."""
        assert hasattr(app, "_on_show_scan")
        assert callable(app._on_show_scan)

    def test_on_show_update_handler_exists(self, app):
        """Test that the _on_show_update handler method exists."""
        assert hasattr(app, "_on_show_update")
        assert callable(app._on_show_update)

    def test_on_show_logs_handler_exists(self, app):
        """Test that the _on_show_logs handler method exists."""
        assert hasattr(app, "_on_show_logs")
        assert callable(app._on_show_logs)

    def test_on_show_components_handler_exists(self, app):
        """Test that the _on_show_components handler method exists."""
        assert hasattr(app, "_on_show_components")
        assert callable(app._on_show_components)


class TestClamUIAppLifecycle:
    """Tests for application lifecycle methods."""

    def test_do_activate_method_exists(self, app):
        """Test that do_activate method exists."""
        assert hasattr(app, "do_activate")
        assert callable(app.do_activate)

    def test_do_startup_method_exists(self, app):
        """Test that do_startup method exists."""
        assert hasattr(app, "do_startup")
        assert callable(app.do_startup)

    def test_on_quit_handler_exists(self, app):
        """Test that the _on_quit handler method exists."""
        assert hasattr(app, "_on_quit")
        assert callable(app._on_quit)

    def test_on_about_handler_exists(self, app):
        """Test that the _on_about handler method exists."""
        assert hasattr(app, "_on_about")
        assert callable(app._on_about)


class TestClamUIAppQuickScanProfile:
    """Tests for Quick Scan profile retrieval and application."""

    def test_get_quick_scan_profile_method_exists(self, app):
        """Test that the _get_quick_scan_profile helper method exists."""
        assert hasattr(app, "_get_quick_scan_profile")
        assert callable(app._get_quick_scan_profile)

    def test_get_quick_scan_profile_calls_profile_manager(self, app):
        """Test that _get_quick_scan_profile retrieves profile from profile manager."""
        # Mock the profile manager
        app._profile_manager = mock.MagicMock()
        mock_profile = mock.MagicMock()
        mock_profile.id = "quick-scan-profile-id"
        mock_profile.name = "Quick Scan"
        app._profile_manager.get_profile_by_name.return_value = mock_profile

        result = app._get_quick_scan_profile()

        app._profile_manager.get_profile_by_name.assert_called_once_with("Quick Scan")
        assert result == mock_profile

    def test_get_quick_scan_profile_returns_none_when_not_found(self, app):
        """Test that _get_quick_scan_profile returns None when profile not found."""
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        result = app._get_quick_scan_profile()

        assert result is None

    def test_on_statistics_quick_scan_handler_exists(self, app):
        """Test that the _on_statistics_quick_scan handler method exists."""
        assert hasattr(app, "_on_statistics_quick_scan")
        assert callable(app._on_statistics_quick_scan)

    def test_on_statistics_quick_scan_switches_to_scan_view(self, app, mock_gtk_modules):
        """Test that _on_statistics_quick_scan switches to scan view."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (fallback path)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Call the handler
        app._on_statistics_quick_scan()

        # Verify view switch
        mock_window.set_content_view.assert_called_once_with(mock_scan_view)
        mock_window.set_active_view.assert_called_once_with("scan")
        assert app._current_view == "scan"

    def test_on_statistics_quick_scan_applies_quick_scan_profile(self, app, mock_gtk_modules):
        """Test that _on_statistics_quick_scan applies the Quick Scan profile."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return a profile
        mock_profile = mock.MagicMock()
        mock_profile.id = "quick-scan-profile-id"
        mock_profile.name = "Quick Scan"
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = mock_profile

        # Call the handler
        app._on_statistics_quick_scan()

        # Verify profile is applied
        mock_scan_view.refresh_profiles.assert_called_once()
        mock_scan_view.set_selected_profile.assert_called_once_with("quick-scan-profile-id")

    def test_on_statistics_quick_scan_falls_back_to_home_when_profile_missing(
        self, app, mock_gtk_modules
    ):
        """Test that _on_statistics_quick_scan falls back to home directory when profile not found."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Call the handler
        with mock.patch("src.app.os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "/home/testuser"
            app._on_statistics_quick_scan()

            # Verify fallback to home directory
            mock_scan_view._set_selected_path.assert_called_once_with("/home/testuser")
        # Verify set_selected_profile was NOT called
        mock_scan_view.set_selected_profile.assert_not_called()

    def test_on_statistics_quick_scan_does_not_auto_start_scan(self, app, mock_gtk_modules):
        """Test that _on_statistics_quick_scan does NOT auto-start the scan."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval
        mock_profile = mock.MagicMock()
        mock_profile.id = "quick-scan-profile-id"
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = mock_profile

        # Call the handler
        app._on_statistics_quick_scan()

        # Verify _start_scan was NOT called (user must click Start Scan)
        mock_scan_view._start_scan.assert_not_called()

    def test_on_statistics_quick_scan_no_action_without_window(self, app, mock_gtk_modules):
        """Test that _on_statistics_quick_scan does nothing without active window."""
        app.props = mock.MagicMock()
        app.props.active_window = None

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view

        # Call the handler
        app._on_statistics_quick_scan()

        # Verify no scan view methods were called
        mock_scan_view.refresh_profiles.assert_not_called()
        mock_scan_view.set_selected_profile.assert_not_called()

    def test_on_statistics_quick_scan_lazy_loads_scan_view(self, app, mock_gtk_modules):
        """Test that _on_statistics_quick_scan lazily loads scan view if not created."""
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window
        # With lazy loading, even if _scan_view is None, accessing the property creates it
        app._scan_view = None

        # Mock profile manager to return no quick scan profile
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Call the handler - should create scan view via lazy loading
        app._on_statistics_quick_scan()

        # set_content_view should be called since lazy loading creates the view
        mock_window.set_content_view.assert_called_once()


class TestClamUIAppTrayQuickScan:
    """Tests for Tray Menu Quick Scan profile retrieval and application."""

    def test_on_tray_quick_scan_handler_exists(self, app):
        """Test that the _on_tray_quick_scan handler method exists."""
        assert hasattr(app, "_on_tray_quick_scan")
        assert callable(app._on_tray_quick_scan)

    def test_do_tray_quick_scan_handler_exists(self, app):
        """Test that the _do_tray_quick_scan handler method exists."""
        assert hasattr(app, "_do_tray_quick_scan")
        assert callable(app._do_tray_quick_scan)

    def test_do_tray_quick_scan_switches_to_scan_view(self, app, mock_gtk_modules):
        """Test that _do_tray_quick_scan switches to scan view."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (fallback path)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Mock activate to just set up the window
        app.activate = mock.MagicMock()

        # Call the handler
        app._do_tray_quick_scan()

        # Verify view switch
        mock_window.set_content_view.assert_called_once_with(mock_scan_view)
        mock_window.set_active_view.assert_called_once_with("scan")
        assert app._current_view == "scan"

    def test_do_tray_quick_scan_applies_quick_scan_profile(self, app, mock_gtk_modules):
        """Test that _do_tray_quick_scan applies the Quick Scan profile."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return a profile
        mock_profile = mock.MagicMock()
        mock_profile.id = "quick-scan-profile-id"
        mock_profile.name = "Quick Scan"
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = mock_profile

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler
        app._do_tray_quick_scan()

        # Verify profile is applied
        mock_scan_view.refresh_profiles.assert_called_once()
        mock_scan_view.set_selected_profile.assert_called_once_with("quick-scan-profile-id")

    def test_do_tray_quick_scan_starts_scan_after_profile_application(self, app, mock_gtk_modules):
        """Test that _do_tray_quick_scan starts the scan after applying profile."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return a profile
        mock_profile = mock.MagicMock()
        mock_profile.id = "quick-scan-profile-id"
        mock_profile.name = "Quick Scan"
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = mock_profile

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler
        app._do_tray_quick_scan()

        # Verify scan is started (unlike statistics quick scan, tray auto-starts)
        mock_scan_view._start_scan.assert_called_once()

    def test_do_tray_quick_scan_falls_back_to_home_when_profile_missing(
        self, app, mock_gtk_modules
    ):
        """Test that _do_tray_quick_scan falls back to home directory when profile not found."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler
        with mock.patch("src.app.os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "/home/testuser"
            app._do_tray_quick_scan()

            # Verify fallback to home directory
            mock_scan_view._set_selected_path.assert_called_once_with("/home/testuser")
        # Verify set_selected_profile was NOT called
        mock_scan_view.set_selected_profile.assert_not_called()

    def test_do_tray_quick_scan_starts_scan_in_fallback_case(self, app, mock_gtk_modules):
        """Test that _do_tray_quick_scan starts scan even when falling back to home directory."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler
        app._do_tray_quick_scan()

        # Verify scan is started even in fallback case
        mock_scan_view._start_scan.assert_called_once()

    def test_do_tray_quick_scan_calls_activate(self, app, mock_gtk_modules):
        """Test that _do_tray_quick_scan activates the application."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view

        # Mock profile retrieval
        mock_profile = mock.MagicMock()
        mock_profile.id = "quick-scan-profile-id"
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = mock_profile

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler
        app._do_tray_quick_scan()

        # Verify activate was called
        app.activate.assert_called_once()

    def test_do_tray_quick_scan_no_action_without_window(self, app, mock_gtk_modules):
        """Test that _do_tray_quick_scan does nothing without active window."""
        app.props = mock.MagicMock()
        app.props.active_window = None

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler
        app._do_tray_quick_scan()

        # Verify no scan view methods were called
        mock_scan_view.refresh_profiles.assert_not_called()
        mock_scan_view.set_selected_profile.assert_not_called()
        mock_scan_view._start_scan.assert_not_called()

    def test_do_tray_quick_scan_lazy_loads_scan_view(self, app, mock_gtk_modules):
        """Test that _do_tray_quick_scan lazily loads scan view if not created."""
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window
        # With lazy loading, even if _scan_view is None, accessing the property creates it
        app._scan_view = None

        # Mock activate
        app.activate = mock.MagicMock()

        # Mock profile manager to return no quick scan profile
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Call the handler - should create scan view via lazy loading
        result = app._do_tray_quick_scan()

        # Verify returns False (don't repeat)
        assert result is False

        # set_content_view should be called since lazy loading creates the view
        mock_window.set_content_view.assert_called_once()

    def test_do_tray_quick_scan_returns_false(self, app, mock_gtk_modules):
        """Test that _do_tray_quick_scan returns False (to prevent GLib.idle_add repeat)."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view

        # Mock profile retrieval
        mock_profile = mock.MagicMock()
        mock_profile.id = "quick-scan-profile-id"
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = mock_profile

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler
        result = app._do_tray_quick_scan()

        # Verify returns False (to stop GLib.idle_add repetition)
        assert result is False

    def test_on_tray_quick_scan_uses_glib_idle_add(self, app, mock_gtk_modules):
        """Test that _on_tray_quick_scan delegates to _do_tray_quick_scan via GLib.idle_add."""
        # This test verifies the thread-safety mechanism
        mock_glib = mock_gtk_modules["GLib"]

        # Call the handler
        app._on_tray_quick_scan()

        # Verify GLib.idle_add was called with _do_tray_quick_scan
        mock_glib.idle_add.assert_called_once_with(app._do_tray_quick_scan)


class TestClamUIAppQuickScanFallback:
    """Dedicated tests for Quick Scan fallback behavior when profile is not found."""

    def test_statistics_fallback_uses_expanduser_with_tilde(self, app, mock_gtk_modules):
        """Test that statistics quick scan fallback uses os.path.expanduser with '~'."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (trigger fallback)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Call the handler and verify expanduser is called with "~"
        with mock.patch("src.app.os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "/home/testuser"
            app._on_statistics_quick_scan()

            # Verify expanduser was called with "~" to get home directory
            mock_expanduser.assert_called_once_with("~")

    def test_tray_fallback_uses_expanduser_with_tilde(self, app, mock_gtk_modules):
        """Test that tray quick scan fallback uses os.path.expanduser with '~'."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (trigger fallback)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler and verify expanduser is called with "~"
        with mock.patch("src.app.os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "/home/testuser"
            app._do_tray_quick_scan()

            # Verify expanduser was called with "~" to get home directory
            mock_expanduser.assert_called_once_with("~")

    def test_statistics_fallback_does_not_call_refresh_profiles(self, app, mock_gtk_modules):
        """Test that statistics quick scan fallback does not call refresh_profiles."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (trigger fallback)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Call the handler
        app._on_statistics_quick_scan()

        # Verify refresh_profiles was NOT called (only called when profile found)
        mock_scan_view.refresh_profiles.assert_not_called()

    def test_tray_fallback_does_not_call_refresh_profiles(self, app, mock_gtk_modules):
        """Test that tray quick scan fallback does not call refresh_profiles."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (trigger fallback)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler
        app._do_tray_quick_scan()

        # Verify refresh_profiles was NOT called (only called when profile found)
        mock_scan_view.refresh_profiles.assert_not_called()

    def test_statistics_fallback_logs_warning(self, app, mock_gtk_modules):
        """Test that statistics quick scan fallback logs a warning message."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (trigger fallback)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Call the handler and verify logging
        with mock.patch("src.app.logger") as mock_logger:
            app._on_statistics_quick_scan()

            # Verify warning was logged about fallback
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Quick Scan profile not found" in warning_call
            assert "falling back" in warning_call.lower()

    def test_tray_fallback_logs_warning(self, app, mock_gtk_modules):
        """Test that tray quick scan fallback logs a warning message."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (trigger fallback)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler and verify logging
        with mock.patch("src.app.logger") as mock_logger:
            app._do_tray_quick_scan()

            # Verify warning was logged about fallback
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Quick Scan profile not found" in warning_call
            assert "falling back" in warning_call.lower()

    def test_statistics_fallback_still_switches_to_scan_view(self, app, mock_gtk_modules):
        """Test that statistics quick scan fallback still switches to scan view."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (trigger fallback)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Call the handler
        app._on_statistics_quick_scan()

        # Verify view switch still happens
        mock_window.set_content_view.assert_called_once_with(mock_scan_view)
        mock_window.set_active_view.assert_called_once_with("scan")
        assert app._current_view == "scan"

    def test_tray_fallback_still_switches_to_scan_view(self, app, mock_gtk_modules):
        """Test that tray quick scan fallback still switches to scan view."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (trigger fallback)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler
        app._do_tray_quick_scan()

        # Verify view switch still happens
        mock_window.set_content_view.assert_called_once_with(mock_scan_view)
        mock_window.set_active_view.assert_called_once_with("scan")
        assert app._current_view == "scan"

    def test_statistics_fallback_path_is_set_correctly(self, app, mock_gtk_modules):
        """Test that statistics quick scan fallback sets the correct home path."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (trigger fallback)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Call the handler with a specific home directory
        with mock.patch("src.app.os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "/home/specific_user"
            app._on_statistics_quick_scan()

            # Verify the expanded path is passed to _set_selected_path
            mock_scan_view._set_selected_path.assert_called_once_with("/home/specific_user")

    def test_tray_fallback_path_is_set_correctly(self, app, mock_gtk_modules):
        """Test that tray quick scan fallback sets the correct home path."""
        # Set up mocks
        mock_window = mock.MagicMock()
        app.props = mock.MagicMock()
        app.props.active_window = mock_window

        mock_scan_view = mock.MagicMock()
        app._scan_view = mock_scan_view
        app._current_view = "statistics"

        # Mock profile retrieval to return None (trigger fallback)
        app._profile_manager = mock.MagicMock()
        app._profile_manager.get_profile_by_name.return_value = None

        # Mock activate
        app.activate = mock.MagicMock()

        # Call the handler with a specific home directory
        with mock.patch("src.app.os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "/home/specific_user"
            app._do_tray_quick_scan()

            # Verify the expanded path is passed to _set_selected_path
            mock_scan_view._set_selected_path.assert_called_once_with("/home/specific_user")
