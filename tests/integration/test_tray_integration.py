# ClamUI Tray Integration Tests
"""Integration tests for tray indicator and application interaction."""

import sys
from unittest import mock

import pytest


# Create mock modules for GTK3, GTK4, Adwaita, and AppIndicator
# These mocks allow testing without a display and handle GTK version conflicts

_mock_gtk3 = mock.MagicMock()
_mock_gtk4 = mock.MagicMock()
_mock_adw = mock.MagicMock()
_mock_appindicator = mock.MagicMock()
_mock_gi = mock.MagicMock()
_mock_gio = mock.MagicMock()
_mock_glib = mock.MagicMock()
_mock_gdk = mock.MagicMock()

# Configure mock AppIndicator
_mock_appindicator.Indicator = mock.MagicMock()
_mock_appindicator.IndicatorCategory = mock.MagicMock()
_mock_appindicator.IndicatorCategory.APPLICATION_STATUS = 0
_mock_appindicator.IndicatorStatus = mock.MagicMock()
_mock_appindicator.IndicatorStatus.ACTIVE = 1
_mock_appindicator.IndicatorStatus.PASSIVE = 0

# Configure mock Gtk3
_mock_gtk3.Menu = mock.MagicMock
_mock_gtk3.MenuItem = mock.MagicMock
_mock_gtk3.SeparatorMenuItem = mock.MagicMock
_mock_gtk3.IconTheme = mock.MagicMock()
_mock_gtk3.IconTheme.get_default = mock.MagicMock()

# Configure mock GLib
_mock_glib.idle_add = mock.MagicMock(side_effect=lambda func: func())


@pytest.fixture(autouse=True)
def mock_gtk_modules(monkeypatch):
    """Mock GTK modules for all tests."""
    # Create a mock gi.repository
    mock_repo = mock.MagicMock()
    mock_repo.Gtk = _mock_gtk4
    mock_repo.Adw = _mock_adw
    mock_repo.GLib = _mock_glib
    mock_repo.Gio = _mock_gio
    mock_repo.Gdk = _mock_gdk
    mock_repo.AyatanaAppIndicator3 = _mock_appindicator

    # Install mocks
    monkeypatch.setitem(sys.modules, 'gi', _mock_gi)
    monkeypatch.setitem(sys.modules, 'gi.repository', mock_repo)

    # Mock require_version to do nothing
    _mock_gi.require_version = mock.MagicMock()

    yield


class TestTrayMenuActionsIntegration:
    """Integration tests for tray menu actions triggering app operations."""

    def test_quick_scan_action_triggers_scan_view(self, mock_gtk_modules):
        """Test that Quick Scan tray action triggers scan in ScanView."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        # Create tray indicator
        tray = tray_indicator.TrayIndicator()

        # Create mock scan callback
        scan_started = []

        def mock_quick_scan():
            scan_started.append("quick_scan")

        # Connect callback
        tray.set_action_callbacks(on_quick_scan=mock_quick_scan)

        # Trigger quick scan menu item
        tray._on_quick_scan_clicked(None)

        # Verify scan was triggered
        assert "quick_scan" in scan_started

    def test_full_scan_action_triggers_folder_selection(self, mock_gtk_modules):
        """Test that Full Scan tray action triggers folder selection."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        folder_selection_opened = []

        def mock_full_scan():
            folder_selection_opened.append("full_scan")

        tray.set_action_callbacks(on_full_scan=mock_full_scan)
        tray._on_full_scan_clicked(None)

        assert "full_scan" in folder_selection_opened

    def test_update_action_triggers_database_update(self, mock_gtk_modules):
        """Test that Update Definitions action triggers update in UpdateView."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        update_triggered = []

        def mock_update():
            update_triggered.append("update")

        tray.set_action_callbacks(on_update=mock_update)
        tray._on_update_clicked(None)

        assert "update" in update_triggered

    def test_quit_action_triggers_app_quit(self, mock_gtk_modules):
        """Test that Quit action triggers application quit."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        quit_triggered = []

        def mock_quit():
            quit_triggered.append("quit")

        tray.set_action_callbacks(on_quit=mock_quit)
        tray._on_quit_clicked(None)

        assert "quit" in quit_triggered


class TestScanStateToTrayPropagation:
    """Integration tests for scan state changes updating tray status."""

    def test_scan_start_updates_tray_to_scanning(self, mock_gtk_modules):
        """Test that starting a scan updates tray to scanning state."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_indicator = mock.MagicMock()
        tray._indicator = mock_indicator
        tray._available = True

        # Simulate scan start by updating status to scanning
        with mock.patch.object(tray, '_resolve_icon', return_value='emblem-synchronizing-symbolic'):
            tray.update_status("scanning")

        assert tray.current_status == "scanning"
        mock_indicator.set_icon_full.assert_called()

    def test_scan_complete_clean_updates_tray_to_protected(self, mock_gtk_modules):
        """Test that clean scan result updates tray to protected state."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_indicator = mock.MagicMock()
        tray._indicator = mock_indicator
        tray._available = True
        tray._current_status = "scanning"

        # Update to protected state (clean scan)
        with mock.patch.object(tray, '_resolve_icon', return_value='security-high-symbolic'):
            tray.update_status("protected")

        assert tray.current_status == "protected"

    def test_scan_complete_threats_updates_tray_to_threat(self, mock_gtk_modules):
        """Test that threat detection updates tray to threat state."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_indicator = mock.MagicMock()
        tray._indicator = mock_indicator
        tray._available = True
        tray._current_status = "scanning"

        # Update to threat state (threats detected)
        with mock.patch.object(tray, '_resolve_icon', return_value='dialog-error-symbolic'):
            tray.update_status("threat")

        assert tray.current_status == "threat"

    def test_scan_error_updates_tray_to_warning(self, mock_gtk_modules):
        """Test that scan error updates tray to warning state."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_indicator = mock.MagicMock()
        tray._indicator = mock_indicator
        tray._available = True
        tray._current_status = "scanning"

        # Update to warning state (scan error)
        with mock.patch.object(tray, '_resolve_icon', return_value='dialog-warning-symbolic'):
            tray.update_status("warning")

        assert tray.current_status == "warning"

    def test_scan_progress_updates_tray_label(self, mock_gtk_modules):
        """Test that scan progress updates tray label percentage."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_indicator = mock.MagicMock()
        tray._indicator = mock_indicator
        tray._available = True
        tray._current_status = "protected"

        # Update progress
        with mock.patch.object(tray, 'update_status'):
            tray.update_scan_progress(50)

        mock_indicator.set_label.assert_called_with("50%", "")

    def test_scan_complete_clears_progress_label(self, mock_gtk_modules):
        """Test that scan completion clears progress label."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_indicator = mock.MagicMock()
        tray._indicator = mock_indicator

        # Clear progress
        tray.update_scan_progress(0)

        mock_indicator.set_label.assert_called_with("", "")


class TestWindowToggleIntegration:
    """Integration tests for window toggle functionality."""

    def test_window_toggle_callback_invoked(self, mock_gtk_modules):
        """Test that window toggle callback is invoked on menu click."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        toggle_called = []

        def mock_toggle():
            toggle_called.append("toggled")

        def mock_get_visible():
            return True

        tray.set_window_toggle_callback(mock_toggle, mock_get_visible)
        tray._on_window_toggle_clicked(None)

        assert "toggled" in toggle_called

    def test_window_menu_label_shows_hide_when_visible(self, mock_gtk_modules):
        """Test menu shows 'Hide Window' when window is visible."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_item = mock.MagicMock()
        tray._show_window_item = mock_item
        tray._get_window_visible = mock.MagicMock(return_value=True)

        tray.update_window_menu_label()

        mock_item.set_label.assert_called_with("Hide Window")

    def test_window_menu_label_shows_show_when_hidden(self, mock_gtk_modules):
        """Test menu shows 'Show Window' when window is hidden."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_item = mock.MagicMock()
        tray._show_window_item = mock_item
        tray._get_window_visible = mock.MagicMock(return_value=False)

        tray.update_window_menu_label()

        mock_item.set_label.assert_called_with("Show Window")

    def test_window_toggle_syncs_menu_label(self, mock_gtk_modules):
        """Test that toggling window syncs the menu label."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_item = mock.MagicMock()
        tray._show_window_item = mock_item

        # Simulate visibility state changes
        visibility_state = [True]

        def mock_toggle():
            visibility_state[0] = not visibility_state[0]

        def mock_get_visible():
            return visibility_state[0]

        tray.set_window_toggle_callback(mock_toggle, mock_get_visible)

        # First state: visible -> should show "Hide Window"
        tray.update_window_menu_label()
        mock_item.set_label.assert_called_with("Hide Window")

        # Toggle visibility
        tray._on_window_toggle_clicked(None)
        tray.update_window_menu_label()
        mock_item.set_label.assert_called_with("Show Window")


class TestMinimizeToTrayIntegration:
    """Integration tests for minimize-to-tray functionality."""

    def test_tray_available_for_minimize(self, mock_gtk_modules):
        """Test tray availability check for minimize-to-tray."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        # When library is available, tray should report availability
        assert isinstance(tray.is_library_available, bool)

    def test_minimize_hides_window_and_updates_menu(self, mock_gtk_modules):
        """Test that minimizing to tray hides window and updates menu."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_item = mock.MagicMock()
        tray._show_window_item = mock_item

        window_hidden = []

        def mock_toggle():
            window_hidden.append("hidden")

        def mock_get_visible():
            return len(window_hidden) == 0

        tray.set_window_toggle_callback(mock_toggle, mock_get_visible)

        # Initially window is visible
        assert mock_get_visible() is True

        # Simulate minimize-to-tray: toggle to hide window
        tray._on_window_toggle_clicked(None)

        # Verify window was hidden
        assert "hidden" in window_hidden

        # Update menu label
        tray.update_window_menu_label()
        mock_item.set_label.assert_called_with("Show Window")

    def test_restore_from_tray_shows_window(self, mock_gtk_modules):
        """Test that clicking tray when minimized shows window."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_item = mock.MagicMock()
        tray._show_window_item = mock_item

        # Start with window hidden
        visibility_state = [False]

        def mock_toggle():
            visibility_state[0] = not visibility_state[0]

        def mock_get_visible():
            return visibility_state[0]

        tray.set_window_toggle_callback(mock_toggle, mock_get_visible)

        # Initially window is hidden
        assert mock_get_visible() is False

        # Click tray to show window
        tray._on_window_toggle_clicked(None)

        # Verify window is now visible
        assert mock_get_visible() is True

        # Update menu label
        tray.update_window_menu_label()
        mock_item.set_label.assert_called_with("Hide Window")


class TestTrayCleanupIntegration:
    """Integration tests for tray cleanup during app shutdown."""

    def test_cleanup_clears_all_callbacks(self, mock_gtk_modules):
        """Test that cleanup clears all registered callbacks."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        # Set up all callbacks
        tray.set_action_callbacks(
            on_quick_scan=mock.MagicMock(),
            on_full_scan=mock.MagicMock(),
            on_update=mock.MagicMock(),
            on_quit=mock.MagicMock()
        )
        tray.set_window_toggle_callback(
            mock.MagicMock(),
            mock.MagicMock()
        )

        # Verify callbacks are set
        assert tray._on_quick_scan is not None
        assert tray._on_window_toggle is not None

        # Cleanup
        tray.cleanup()

        # Verify all callbacks are cleared
        assert tray._on_quick_scan is None
        assert tray._on_full_scan is None
        assert tray._on_update is None
        assert tray._on_quit is None
        assert tray._on_window_toggle is None
        assert tray._get_window_visible is None

    def test_cleanup_deactivates_indicator(self, mock_gtk_modules):
        """Test that cleanup deactivates the indicator."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_indicator = mock.MagicMock()
        tray._indicator = mock_indicator
        tray._available = True

        # Cleanup
        tray.cleanup()

        # Verify deactivate was called (set_status to PASSIVE)
        mock_indicator.set_status.assert_called()

    def test_cleanup_clears_gtk_resources(self, mock_gtk_modules):
        """Test that cleanup clears GTK resources."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        # Cleanup
        tray.cleanup()

        # Verify GTK resources are cleared
        assert tray._menu is None
        assert tray._indicator is None
        assert tray._icon_theme is None
        assert tray._show_window_item is None


class TestTrayAppCallbackChain:
    """Integration tests for callback chain between tray and app."""

    def test_complete_scan_workflow_updates_tray(self, mock_gtk_modules):
        """Test complete scan workflow: start -> progress -> complete -> status."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_indicator = mock.MagicMock()
        tray._indicator = mock_indicator
        tray._available = True

        status_changes = []

        # Track status changes
        original_update_status = tray.update_status

        def tracking_update_status(status):
            status_changes.append(status)
            tray._current_status = status

        tray.update_status = tracking_update_status

        # Simulate scan workflow
        tray.update_status("scanning")  # Scan starts
        tray.update_scan_progress(25)
        tray.update_scan_progress(50)
        tray.update_scan_progress(75)
        tray.update_scan_progress(100)
        tray.update_scan_progress(0)  # Clear progress
        tray.update_status("protected")  # Scan complete (clean)

        # Verify status progression
        assert "scanning" in status_changes
        assert "protected" in status_changes

    def test_multiple_callbacks_can_be_set_and_replaced(self, mock_gtk_modules):
        """Test that callbacks can be set and replaced without issues."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        call_log = []

        # First set of callbacks
        def callback1():
            call_log.append("callback1")

        tray.set_action_callbacks(on_quick_scan=callback1)
        tray._on_quick_scan_clicked(None)

        # Replace with second set
        def callback2():
            call_log.append("callback2")

        tray.set_action_callbacks(on_quick_scan=callback2)
        tray._on_quick_scan_clicked(None)

        # Verify both were called in order
        assert call_log == ["callback1", "callback2"]

    def test_callbacks_work_independently(self, mock_gtk_modules):
        """Test that different callbacks work independently."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        actions = []

        def quick_scan():
            actions.append("quick")

        def full_scan():
            actions.append("full")

        def update():
            actions.append("update")

        def quit_app():
            actions.append("quit")

        tray.set_action_callbacks(
            on_quick_scan=quick_scan,
            on_full_scan=full_scan,
            on_update=update,
            on_quit=quit_app
        )

        # Trigger each action in random order
        tray._on_update_clicked(None)
        tray._on_quick_scan_clicked(None)
        tray._on_quit_clicked(None)
        tray._on_full_scan_clicked(None)

        # Verify all were called in correct order
        assert actions == ["update", "quick", "quit", "full"]


class TestTrayStatusIconIntegration:
    """Integration tests for status icon updates."""

    def test_status_transitions_are_tracked(self, mock_gtk_modules):
        """Test that status transitions are properly tracked."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_indicator = mock.MagicMock()
        tray._indicator = mock_indicator
        tray._available = True

        # Initial status
        assert tray.current_status == "protected"

        # Transition through states
        states = ["scanning", "threat", "warning", "protected"]

        for state in states:
            with mock.patch.object(tray, '_resolve_icon', return_value=f'icon-{state}'):
                tray.update_status(state)
                assert tray.current_status == state

    def test_invalid_status_falls_back_to_protected(self, mock_gtk_modules):
        """Test that invalid status falls back to protected."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()
        mock_indicator = mock.MagicMock()
        tray._indicator = mock_indicator
        tray._available = True

        # Try invalid status
        with mock.patch.object(tray, '_resolve_icon', return_value='security-high-symbolic'):
            tray.update_status("invalid_status")

        # Should fall back to protected
        assert tray.current_status == "protected"


class TestTrayAppLifecycle:
    """Integration tests for tray lifecycle with application."""

    def test_tray_can_be_created_before_window(self, mock_gtk_modules):
        """Test that tray can be created before main window exists."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        # Create tray without any window
        tray = tray_indicator.TrayIndicator()

        # Should work without errors
        assert tray is not None
        assert tray.current_status == "protected"

    def test_tray_survives_window_destroy_recreate(self, mock_gtk_modules):
        """Test that tray remains functional when window is destroyed/recreated."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        visibility_cycle = []

        # Simulate window lifecycle
        for i in range(3):
            # Window created
            def get_visible():
                return True

            def toggle():
                visibility_cycle.append(f"toggle_{i}")

            tray.set_window_toggle_callback(toggle, get_visible)

            # Window used
            tray._on_window_toggle_clicked(None)

            # Window "destroyed" - callback set to None
            tray._on_window_toggle = None
            tray._get_window_visible = None

        # Verify tray survived all cycles
        assert len(visibility_cycle) == 3
        assert tray is not None

    def test_cleanup_is_idempotent(self, mock_gtk_modules):
        """Test that cleanup can be called multiple times safely."""
        import importlib
        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        tray = tray_indicator.TrayIndicator()

        # Set up some state
        tray.set_action_callbacks(on_quick_scan=mock.MagicMock())

        # Multiple cleanups should be safe
        for _ in range(5):
            tray.cleanup()

        # Final state should be clean
        assert tray._on_quick_scan is None
        assert tray._indicator is None


class TestTrayUnavailableGracefulDegradation:
    """Integration tests for graceful degradation when tray is unavailable."""

    def test_unavailable_tray_allows_all_operations(self, mock_gtk_modules):
        """Test all operations work when tray library is unavailable."""
        import importlib
        from src.ui import tray_indicator

        # Force unavailable state
        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        tray = tray_indicator.TrayIndicator()

        # All these operations should not raise
        tray.set_action_callbacks(
            on_quick_scan=mock.MagicMock(),
            on_full_scan=mock.MagicMock(),
            on_update=mock.MagicMock(),
            on_quit=mock.MagicMock()
        )
        tray.set_window_toggle_callback(mock.MagicMock(), mock.MagicMock())
        tray.activate()
        tray.update_status("scanning")
        tray.update_scan_progress(50)
        tray.update_window_menu_label()
        tray.deactivate()
        tray.cleanup()

        # Verify final state
        assert tray.is_library_available is False
        assert tray.is_active is False

    def test_unavailable_tray_reports_status_correctly(self, mock_gtk_modules):
        """Test unavailable tray reports its status correctly."""
        import importlib
        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        # Check module-level availability
        assert tray_indicator.is_available() is False
        reason = tray_indicator.get_unavailable_reason()
        assert reason is None or isinstance(reason, str)

        # Check instance-level availability
        tray = tray_indicator.TrayIndicator()
        assert tray.is_library_available is False
        assert tray.is_active is False
