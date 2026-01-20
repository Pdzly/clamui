# ClamUI Tray Integration Tests
"""Integration tests for tray indicator and application interaction.

The tray system uses TrayManager to spawn tray_service.py as a subprocess.
The tray_service.py implements the StatusNotifierItem D-Bus protocol and
communicates with the main app via JSON over stdin/stdout.

IMPORTANT: This module does NOT use module-level mocking to avoid test pollution.
All GTK mocking is done inside pytest fixtures that properly save and restore
sys.modules state.
"""

import sys
from unittest import mock

import pytest


@pytest.fixture
def tray_manager_with_mocks():
    """
    Fixture that properly mocks GTK/GLib and imports TrayManager.

    This fixture:
    1. Saves the current state of sys.modules for GTK-related modules
    2. Installs mocks for gi, gi.repository, GLib, Gtk
    3. Imports TrayManager with the mocked environment
    4. Yields TrayManager class for tests
    5. Restores sys.modules to original state on cleanup

    This prevents test pollution by ensuring mocks don't leak to other tests.
    """
    # Save original module state
    modules_to_mock = [
        "gi",
        "gi.repository",
        "gi.repository.Gtk",
        "gi.repository.GLib",
        "gi.repository.Adw",
        "gi.repository.Gio",
    ]
    original_modules = {mod: sys.modules.get(mod) for mod in modules_to_mock}

    # Also save any src.ui modules that may have been imported
    src_modules_to_clear = [mod for mod in sys.modules if mod.startswith("src.ui")]
    original_src_modules = {mod: sys.modules.get(mod) for mod in src_modules_to_clear}

    # Clear src.ui modules so they reimport with our mocks
    for mod in src_modules_to_clear:
        del sys.modules[mod]

    # Create mocks
    mock_gi = mock.MagicMock()
    mock_glib = mock.MagicMock()
    mock_glib.idle_add = mock.MagicMock(side_effect=lambda func, *args: func(*args))

    mock_gtk = mock.MagicMock()
    mock_gtk.get_minor_version = mock.MagicMock(return_value=14)
    mock_gtk.get_major_version = mock.MagicMock(return_value=4)

    mock_adw = mock.MagicMock()
    mock_gio = mock.MagicMock()

    mock_repo = mock.MagicMock()
    mock_repo.GLib = mock_glib
    mock_repo.Gtk = mock_gtk
    mock_repo.Adw = mock_adw
    mock_repo.Gio = mock_gio

    mock_gi.require_version = mock.MagicMock()

    # Install mocks
    sys.modules["gi"] = mock_gi
    sys.modules["gi.repository"] = mock_repo
    sys.modules["gi.repository.Gtk"] = mock_gtk
    sys.modules["gi.repository.GLib"] = mock_glib
    sys.modules["gi.repository.Adw"] = mock_adw
    sys.modules["gi.repository.Gio"] = mock_gio

    # Import TrayManager with mocked environment
    from src.ui.tray_manager import TrayManager

    # Yield the class for tests
    yield TrayManager

    # Cleanup: remove src.ui modules that were imported with mocks
    src_modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.ui")]
    for mod in src_modules_to_remove:
        if mod in sys.modules:
            del sys.modules[mod]

    # Restore original src.ui modules
    for mod, original in original_src_modules.items():
        if original is not None:
            sys.modules[mod] = original

    # Restore original gi modules
    for mod, original in original_modules.items():
        if original is not None:
            sys.modules[mod] = original
        elif mod in sys.modules:
            del sys.modules[mod]


@pytest.fixture
def tray_indicator_with_mocks(tray_manager_with_mocks):
    """
    Fixture that provides tray_indicator module with mocked GTK.

    Depends on tray_manager_with_mocks to ensure proper mock setup.
    """
    # The fixture parameter is used for its side effects (installing mocks)
    _ = tray_manager_with_mocks  # Suppress unused warning
    from src.ui import tray_indicator

    return tray_indicator


class TestTrayMenuActionsIntegration:
    """Integration tests for tray menu actions triggering app operations."""

    def test_quick_scan_action_triggers_callback(self, tray_manager_with_mocks):
        """Test that Quick Scan tray action triggers the callback."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        scan_started = []

        def mock_quick_scan():
            scan_started.append("quick_scan")

        manager.set_action_callbacks(on_quick_scan=mock_quick_scan)
        manager._handle_menu_action("quick_scan", {"action": "quick_scan"})

        assert "quick_scan" in scan_started

    def test_full_scan_action_triggers_callback(self, tray_manager_with_mocks):
        """Test that Full Scan tray action triggers the callback."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        folder_selection_opened = []

        def mock_full_scan():
            folder_selection_opened.append("full_scan")

        manager.set_action_callbacks(on_full_scan=mock_full_scan)
        manager._handle_menu_action("full_scan", {"action": "full_scan"})

        assert "full_scan" in folder_selection_opened

    def test_update_action_triggers_callback(self, tray_manager_with_mocks):
        """Test that Update Definitions action triggers the callback."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        update_triggered = []

        def mock_update():
            update_triggered.append("update")

        manager.set_action_callbacks(on_update=mock_update)
        manager._handle_menu_action("update", {"action": "update"})

        assert "update" in update_triggered

    def test_quit_action_triggers_callback(self, tray_manager_with_mocks):
        """Test that Quit action triggers the callback."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        quit_triggered = []

        def mock_quit():
            quit_triggered.append("quit")

        manager.set_action_callbacks(on_quit=mock_quit)
        manager._handle_menu_action("quit", {"action": "quit"})

        assert "quit" in quit_triggered


class TestScanStateToTrayPropagation:
    """Integration tests for scan state changes updating tray status."""

    def test_scan_start_updates_status(self, tray_manager_with_mocks):
        """Test that starting a scan updates tray to scanning state."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        manager._process.stdin = mock.MagicMock()

        manager.update_status("scanning")

        assert manager.current_status == "scanning"

    def test_scan_complete_clean_updates_status(self, tray_manager_with_mocks):
        """Test that clean scan result updates tray to protected state."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        manager._process.stdin = mock.MagicMock()
        manager._current_status = "scanning"

        manager.update_status("protected")

        assert manager.current_status == "protected"

    def test_scan_complete_threats_updates_status(self, tray_manager_with_mocks):
        """Test that threat detection updates tray to threat state."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        manager._process.stdin = mock.MagicMock()
        manager._current_status = "scanning"

        manager.update_status("threat")

        assert manager.current_status == "threat"

    def test_scan_error_updates_status(self, tray_manager_with_mocks):
        """Test that scan error updates tray to warning state."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        manager._process.stdin = mock.MagicMock()
        manager._current_status = "scanning"

        manager.update_status("warning")

        assert manager.current_status == "warning"

    def test_scan_progress_sends_command(self, tray_manager_with_mocks):
        """Test that scan progress sends command to subprocess."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        mock_stdin = mock.MagicMock()
        manager._process.stdin = mock_stdin

        manager.update_scan_progress(50)

        mock_stdin.write.assert_called()
        mock_stdin.flush.assert_called()

    def test_scan_complete_clears_progress(self, tray_manager_with_mocks):
        """Test that scan completion clears progress (percentage 0)."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        mock_stdin = mock.MagicMock()
        manager._process.stdin = mock_stdin

        manager.update_scan_progress(0)

        mock_stdin.write.assert_called()


class TestWindowToggleIntegration:
    """Integration tests for window toggle functionality."""

    def test_window_toggle_callback_invoked(self, tray_manager_with_mocks):
        """Test that window toggle callback is invoked on menu action."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        toggle_called = []

        def mock_toggle():
            toggle_called.append("toggled")

        def mock_get_visible():
            return True

        manager.set_window_toggle_callback(mock_toggle, mock_get_visible)
        manager._handle_menu_action("toggle_window", {"action": "toggle_window"})

        assert "toggled" in toggle_called

    def test_window_menu_label_sends_command(self, tray_manager_with_mocks):
        """Test that window menu label update sends command."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        mock_stdin = mock.MagicMock()
        manager._process.stdin = mock_stdin

        manager.update_window_menu_label(visible=True)

        mock_stdin.write.assert_called()

    def test_window_toggle_syncs_label(self, tray_manager_with_mocks):
        """Test that toggling window sends visibility update."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        mock_stdin = mock.MagicMock()
        manager._process.stdin = mock_stdin

        visibility_state = [True]

        def mock_toggle():
            visibility_state[0] = not visibility_state[0]

        def mock_get_visible():
            return visibility_state[0]

        manager.set_window_toggle_callback(mock_toggle, mock_get_visible)

        # Toggle visibility
        manager._handle_menu_action("toggle_window", {"action": "toggle_window"})
        manager.update_window_menu_label(visible=visibility_state[0])

        assert mock_stdin.write.called


class TestMinimizeToTrayIntegration:
    """Integration tests for minimize-to-tray functionality."""

    def test_tray_availability_check(self, tray_indicator_with_mocks):
        """Test tray availability check."""
        tray_indicator = tray_indicator_with_mocks

        # Tray is always available with D-Bus SNI
        assert tray_indicator.is_available() is True
        assert tray_indicator.get_unavailable_reason() is None

    def test_minimize_triggers_toggle_callback(self, tray_manager_with_mocks):
        """Test that minimizing to tray triggers toggle callback."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        window_hidden = []

        def mock_toggle():
            window_hidden.append("hidden")

        def mock_get_visible():
            return len(window_hidden) == 0

        manager.set_window_toggle_callback(mock_toggle, mock_get_visible)

        # Initially window is visible
        assert mock_get_visible() is True

        # Simulate minimize-to-tray
        manager._handle_menu_action("toggle_window", {"action": "toggle_window"})

        # Verify window was hidden
        assert "hidden" in window_hidden

    def test_restore_from_tray_triggers_toggle(self, tray_manager_with_mocks):
        """Test that clicking tray when minimized triggers toggle."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        # Start with window hidden
        visibility_state = [False]

        def mock_toggle():
            visibility_state[0] = not visibility_state[0]

        def mock_get_visible():
            return visibility_state[0]

        manager.set_window_toggle_callback(mock_toggle, mock_get_visible)

        # Initially window is hidden
        assert mock_get_visible() is False

        # Click tray to show window
        manager._handle_menu_action("toggle_window", {"action": "toggle_window"})

        # Verify window is now visible
        assert mock_get_visible() is True


class TestTrayCleanupIntegration:
    """Integration tests for tray cleanup during app shutdown."""

    def test_cleanup_clears_all_callbacks(self, tray_manager_with_mocks):
        """Test that cleanup clears all registered callbacks."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        # Set up all callbacks
        manager.set_action_callbacks(
            on_quick_scan=mock.MagicMock(),
            on_full_scan=mock.MagicMock(),
            on_update=mock.MagicMock(),
            on_quit=mock.MagicMock(),
        )
        manager.set_window_toggle_callback(mock.MagicMock(), mock.MagicMock())
        manager.set_profile_select_callback(mock.MagicMock())

        # Verify callbacks are set
        assert manager._on_quick_scan is not None
        assert manager._on_window_toggle is not None

        # Cleanup
        manager.cleanup()

        # Verify all callbacks are cleared
        assert manager._on_quick_scan is None
        assert manager._on_full_scan is None
        assert manager._on_update is None
        assert manager._on_quit is None
        assert manager._on_window_toggle is None

    def test_stop_sends_quit_command(self, tray_manager_with_mocks):
        """Test that stop sends quit command to subprocess."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        mock_stdin = mock.MagicMock()
        manager._process.stdin = mock_stdin
        manager._running = True

        manager.stop()

        assert manager._running is False
        mock_stdin.write.assert_called()


class TestTrayAppCallbackChain:
    """Integration tests for callback chain between tray and app."""

    def test_complete_scan_workflow_updates_status(self, tray_manager_with_mocks):
        """Test complete scan workflow: start -> progress -> complete -> status."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        manager._process.stdin = mock.MagicMock()

        status_changes = []

        # Track status changes
        def tracking_update(status):
            status_changes.append(status)
            manager._current_status = status

        manager.update_status = tracking_update

        # Simulate scan workflow
        manager.update_status("scanning")  # Scan starts
        manager.update_scan_progress(25)
        manager.update_scan_progress(50)
        manager.update_scan_progress(75)
        manager.update_scan_progress(100)
        manager.update_scan_progress(0)  # Clear progress
        manager.update_status("protected")  # Scan complete (clean)

        # Verify status progression
        assert "scanning" in status_changes
        assert "protected" in status_changes

    def test_multiple_callbacks_can_be_set_and_replaced(self, tray_manager_with_mocks):
        """Test that callbacks can be set and replaced without issues."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        call_log = []

        # First set of callbacks
        def callback1():
            call_log.append("callback1")

        manager.set_action_callbacks(on_quick_scan=callback1)
        manager._handle_menu_action("quick_scan", {"action": "quick_scan"})

        # Replace with second set
        def callback2():
            call_log.append("callback2")

        manager.set_action_callbacks(on_quick_scan=callback2)
        manager._handle_menu_action("quick_scan", {"action": "quick_scan"})

        # Verify both were called in order
        assert call_log == ["callback1", "callback2"]

    def test_callbacks_work_independently(self, tray_manager_with_mocks):
        """Test that different callbacks work independently."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        actions = []

        def quick_scan():
            actions.append("quick")

        def full_scan():
            actions.append("full")

        def update():
            actions.append("update")

        def quit_app():
            actions.append("quit")

        manager.set_action_callbacks(
            on_quick_scan=quick_scan,
            on_full_scan=full_scan,
            on_update=update,
            on_quit=quit_app,
        )

        # Trigger each action
        manager._handle_menu_action("update", {"action": "update"})
        manager._handle_menu_action("quick_scan", {"action": "quick_scan"})
        manager._handle_menu_action("quit", {"action": "quit"})
        manager._handle_menu_action("full_scan", {"action": "full_scan"})

        # Verify all were called in correct order
        assert actions == ["update", "quick", "quit", "full"]


class TestTrayStatusIntegration:
    """Integration tests for status updates."""

    def test_status_transitions_are_tracked(self, tray_manager_with_mocks):
        """Test that status transitions are properly tracked."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        manager._process.stdin = mock.MagicMock()

        # Initial status
        assert manager.current_status == "protected"

        # Transition through states
        states = ["scanning", "threat", "warning", "protected"]

        for state in states:
            manager.update_status(state)
            assert manager.current_status == state

    def test_invalid_status_still_tracked(self, tray_manager_with_mocks):
        """Test that invalid status is still tracked (validation in subprocess)."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        manager._process.stdin = mock.MagicMock()

        # Invalid status is sent to subprocess which handles validation
        manager.update_status("invalid_status")
        assert manager.current_status == "invalid_status"


class TestTrayLifecycle:
    """Integration tests for tray lifecycle with application."""

    def test_manager_can_be_created_without_subprocess(self, tray_manager_with_mocks):
        """Test that TrayManager can be created before subprocess starts."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        # Should work without errors
        assert manager is not None
        assert manager.current_status == "protected"
        assert manager.is_active is False

    def test_callbacks_can_be_set_before_subprocess(self, tray_manager_with_mocks):
        """Test that callbacks can be set before subprocess is started."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        # Set callbacks before start
        manager.set_action_callbacks(on_quick_scan=mock.MagicMock())
        manager.set_window_toggle_callback(mock.MagicMock(), mock.MagicMock())

        # Callbacks should be stored
        assert manager._on_quick_scan is not None
        assert manager._on_window_toggle is not None

    def test_cleanup_is_idempotent(self, tray_manager_with_mocks):
        """Test that cleanup can be called multiple times safely."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        # Set up some state
        manager.set_action_callbacks(on_quick_scan=mock.MagicMock())

        # Multiple cleanups should be safe
        for _ in range(5):
            manager.cleanup()

        # Final state should be clean
        assert manager._on_quick_scan is None


class TestTrayAvailability:
    """Integration tests for tray availability."""

    def test_tray_module_availability(self, tray_indicator_with_mocks):
        """Test that tray module reports availability correctly."""
        tray_indicator = tray_indicator_with_mocks

        # D-Bus SNI is always available with GTK4/GIO
        assert tray_indicator.is_available() is True

    def test_tray_unavailable_reason_is_none(self, tray_indicator_with_mocks):
        """Test that unavailable reason is None when available."""
        tray_indicator = tray_indicator_with_mocks

        assert tray_indicator.get_unavailable_reason() is None


class TestProfileSelectIntegration:
    """Integration tests for profile selection from tray."""

    def test_profile_select_callback_invoked(self, tray_manager_with_mocks):
        """Test that profile select callback is invoked."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()

        selected_profiles = []

        def mock_select(profile_id):
            selected_profiles.append(profile_id)

        manager.set_profile_select_callback(mock_select)
        manager._handle_menu_action(
            "select_profile", {"action": "select_profile", "profile_id": "profile-123"}
        )

        assert "profile-123" in selected_profiles

    def test_profiles_update_sends_command(self, tray_manager_with_mocks):
        """Test that updating profiles sends command to subprocess."""
        TrayManager = tray_manager_with_mocks
        manager = TrayManager()
        manager._process = mock.MagicMock()
        mock_stdin = mock.MagicMock()
        manager._process.stdin = mock_stdin

        profiles = [
            {"id": "1", "name": "Quick Scan"},
            {"id": "2", "name": "Full Scan"},
        ]

        manager.update_profiles(profiles, current_profile_id="1")

        mock_stdin.write.assert_called()
        assert manager._current_profile_id == "1"
