# ClamUI TrayManager Tests
"""Unit tests for the TrayManager class (subprocess-based tray)."""

import json
import sys
from unittest import mock

import pytest


# Mock gi and GTK before any imports
_mock_gi = mock.MagicMock()
_mock_glib = mock.MagicMock()
_mock_glib.idle_add = mock.MagicMock(side_effect=lambda func, *args: func(*args))

_mock_repo = mock.MagicMock()
_mock_repo.GLib = _mock_glib


@pytest.fixture(autouse=True)
def mock_gtk_modules(monkeypatch):
    """Mock GTK modules for all tests."""
    monkeypatch.setitem(sys.modules, 'gi', _mock_gi)
    monkeypatch.setitem(sys.modules, 'gi.repository', _mock_repo)
    _mock_gi.require_version = mock.MagicMock()
    yield


class TestTrayManagerModuleFunctions:
    """Tests for module-level functions."""

    def test_is_available_returns_true(self, mock_gtk_modules):
        """Test is_available returns True (subprocess always available)."""
        from src.ui.tray_manager import is_available
        assert is_available() is True

    def test_get_unavailable_reason_returns_none(self, mock_gtk_modules):
        """Test get_unavailable_reason returns None (subprocess handles it)."""
        from src.ui.tray_manager import get_unavailable_reason
        assert get_unavailable_reason() is None


class TestTrayManagerInit:
    """Tests for TrayManager initialization."""

    def test_init_creates_instance(self, mock_gtk_modules):
        """Test TrayManager can be instantiated."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()
        assert manager is not None

    def test_init_has_no_process(self, mock_gtk_modules):
        """Test TrayManager starts with no process."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()
        assert manager._process is None

    def test_init_callbacks_are_none(self, mock_gtk_modules):
        """Test TrayManager initializes with no callbacks."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()
        assert manager._on_quick_scan is None
        assert manager._on_full_scan is None
        assert manager._on_update is None
        assert manager._on_quit is None
        assert manager._on_window_toggle is None
        assert manager._on_profile_select is None

    def test_init_not_running(self, mock_gtk_modules):
        """Test TrayManager starts as not running."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()
        assert manager._running is False
        assert manager._ready is False


class TestTrayManagerCallbacks:
    """Tests for TrayManager callback methods."""

    def test_set_action_callbacks_stores_callbacks(self, mock_gtk_modules):
        """Test set_action_callbacks stores the callback references."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        quick_scan = mock.Mock()
        full_scan = mock.Mock()
        update = mock.Mock()
        quit_cb = mock.Mock()

        manager.set_action_callbacks(
            on_quick_scan=quick_scan,
            on_full_scan=full_scan,
            on_update=update,
            on_quit=quit_cb
        )

        assert manager._on_quick_scan is quick_scan
        assert manager._on_full_scan is full_scan
        assert manager._on_update is update
        assert manager._on_quit is quit_cb

    def test_set_window_toggle_callback_stores_callback(self, mock_gtk_modules):
        """Test set_window_toggle_callback stores the callback."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        toggle_cb = mock.Mock()
        manager.set_window_toggle_callback(toggle_cb)

        assert manager._on_window_toggle is toggle_cb

    def test_set_profile_select_callback_stores_callback(self, mock_gtk_modules):
        """Test set_profile_select_callback stores the callback."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        profile_cb = mock.Mock()
        manager.set_profile_select_callback(profile_cb)

        assert manager._on_profile_select is profile_cb


class TestTrayManagerHandleMenuAction:
    """Tests for TrayManager._handle_menu_action method."""

    def test_handle_quick_scan_action(self, mock_gtk_modules):
        """Test handling quick_scan action invokes callback."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        callback = mock.Mock()
        manager._on_quick_scan = callback

        manager._handle_menu_action("quick_scan", {})

        callback.assert_called_once()

    def test_handle_full_scan_action(self, mock_gtk_modules):
        """Test handling full_scan action invokes callback."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        callback = mock.Mock()
        manager._on_full_scan = callback

        manager._handle_menu_action("full_scan", {})

        callback.assert_called_once()

    def test_handle_update_action(self, mock_gtk_modules):
        """Test handling update action invokes callback."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        callback = mock.Mock()
        manager._on_update = callback

        manager._handle_menu_action("update", {})

        callback.assert_called_once()

    def test_handle_quit_action(self, mock_gtk_modules):
        """Test handling quit action invokes callback."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        callback = mock.Mock()
        manager._on_quit = callback

        manager._handle_menu_action("quit", {})

        callback.assert_called_once()

    def test_handle_toggle_window_action(self, mock_gtk_modules):
        """Test handling toggle_window action invokes callback."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        callback = mock.Mock()
        manager._on_window_toggle = callback

        manager._handle_menu_action("toggle_window", {})

        callback.assert_called_once()

    def test_handle_select_profile_action(self, mock_gtk_modules):
        """Test handling select_profile action invokes callback with profile_id."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        callback = mock.Mock()
        manager._on_profile_select = callback

        # Simulate message with profile_id
        message = {"action": "select_profile", "profile_id": "test-profile-123"}
        manager._handle_menu_action("select_profile", message)

        callback.assert_called_once_with("test-profile-123")

    def test_handle_select_profile_action_updates_current_profile(self, mock_gtk_modules):
        """Test handling select_profile updates current_profile_id."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        callback = mock.Mock()
        manager._on_profile_select = callback

        message = {"action": "select_profile", "profile_id": "new-profile-id"}
        manager._handle_menu_action("select_profile", message)

        assert manager._current_profile_id == "new-profile-id"

    def test_handle_select_profile_action_no_profile_id(self, mock_gtk_modules):
        """Test handling select_profile without profile_id doesn't invoke callback."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        callback = mock.Mock()
        manager._on_profile_select = callback

        # Message without profile_id
        message = {"action": "select_profile"}
        manager._handle_menu_action("select_profile", message)

        callback.assert_not_called()

    def test_handle_unknown_action_does_not_crash(self, mock_gtk_modules):
        """Test handling unknown action doesn't crash."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        # Should not raise
        manager._handle_menu_action("unknown_action", {})


class TestTrayManagerHandleMessage:
    """Tests for TrayManager._handle_message method."""

    def test_handle_ready_message(self, mock_gtk_modules):
        """Test handling ready message sets ready flag."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()
        assert manager._ready is False

        manager._handle_message({"event": "ready"})

        assert manager._ready is True

    def test_handle_pong_message(self, mock_gtk_modules):
        """Test handling pong message doesn't crash."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        # Should not raise
        manager._handle_message({"event": "pong"})

    def test_handle_error_message(self, mock_gtk_modules):
        """Test handling error message logs error."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        # Should not raise
        manager._handle_message({"event": "error", "message": "test error"})

    def test_handle_menu_action_message(self, mock_gtk_modules):
        """Test handling menu_action message invokes action handler."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        callback = mock.Mock()
        manager._on_quick_scan = callback

        manager._handle_message({"event": "menu_action", "action": "quick_scan"})

        callback.assert_called_once()


class TestTrayManagerSendCommand:
    """Tests for TrayManager._send_command method."""

    def test_send_command_returns_false_without_process(self, mock_gtk_modules):
        """Test _send_command returns False when no process."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        result = manager._send_command({"action": "test"})

        assert result is False

    def test_send_command_writes_to_stdin(self, mock_gtk_modules):
        """Test _send_command writes JSON to process stdin."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        mock_stdin = mock.Mock()
        mock_process = mock.Mock()
        mock_process.stdin = mock_stdin
        manager._process = mock_process

        command = {"action": "update_status", "status": "scanning"}
        result = manager._send_command(command)

        assert result is True
        mock_stdin.write.assert_called_once()
        mock_stdin.flush.assert_called_once()

        # Verify JSON format
        written_data = mock_stdin.write.call_args[0][0]
        assert json.loads(written_data.strip()) == command


class TestTrayManagerUpdateMethods:
    """Tests for TrayManager update methods."""

    def test_update_status_sends_command(self, mock_gtk_modules):
        """Test update_status sends correct command."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        with mock.patch.object(manager, '_send_command') as mock_send:
            manager.update_status("scanning")

            mock_send.assert_called_once_with({
                "action": "update_status",
                "status": "scanning"
            })

    def test_update_status_tracks_current_status(self, mock_gtk_modules):
        """Test update_status tracks current status."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        with mock.patch.object(manager, '_send_command'):
            manager.update_status("threat")

        assert manager._current_status == "threat"

    def test_update_scan_progress_sends_command(self, mock_gtk_modules):
        """Test update_scan_progress sends correct command."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        with mock.patch.object(manager, '_send_command') as mock_send:
            manager.update_scan_progress(75)

            mock_send.assert_called_once_with({
                "action": "update_progress",
                "percentage": 75
            })

    def test_update_window_menu_label_sends_command(self, mock_gtk_modules):
        """Test update_window_menu_label sends correct command."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        with mock.patch.object(manager, '_send_command') as mock_send:
            manager.update_window_menu_label(visible=True)

            mock_send.assert_called_once_with({
                "action": "update_window_visible",
                "visible": True
            })

    def test_update_profiles_sends_command(self, mock_gtk_modules):
        """Test update_profiles sends correct command with profiles list."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        profiles = [
            {"id": "profile-1", "name": "Quick Scan", "is_default": True},
            {"id": "profile-2", "name": "Full Scan", "is_default": True},
        ]

        with mock.patch.object(manager, '_send_command') as mock_send:
            manager.update_profiles(profiles, "profile-1")

            mock_send.assert_called_once_with({
                "action": "update_profiles",
                "profiles": profiles,
                "current_profile_id": "profile-1"
            })

    def test_update_profiles_stores_current_profile_id(self, mock_gtk_modules):
        """Test update_profiles stores current_profile_id."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        profiles = [{"id": "test-id", "name": "Test", "is_default": False}]

        with mock.patch.object(manager, '_send_command'):
            manager.update_profiles(profiles, "test-id")

        assert manager._current_profile_id == "test-id"


class TestTrayManagerProperties:
    """Tests for TrayManager properties."""

    def test_is_active_false_when_not_running(self, mock_gtk_modules):
        """Test is_active is False when not running."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        assert manager.is_active is False

    def test_is_active_false_when_not_ready(self, mock_gtk_modules):
        """Test is_active is False when not ready."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()
        manager._running = True
        manager._process = mock.Mock()
        manager._ready = False

        assert manager.is_active is False

    def test_is_active_true_when_running_and_ready(self, mock_gtk_modules):
        """Test is_active is True when running and ready."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()
        manager._running = True
        manager._process = mock.Mock()
        manager._ready = True

        assert manager.is_active is True

    def test_is_library_available_depends_on_process(self, mock_gtk_modules):
        """Test is_library_available depends on running process."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        assert manager.is_library_available is False

        manager._running = True
        manager._process = mock.Mock()

        assert manager.is_library_available is True

    def test_current_status_returns_status(self, mock_gtk_modules):
        """Test current_status returns current status."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        assert manager.current_status == "protected"

        manager._current_status = "scanning"
        assert manager.current_status == "scanning"


class TestTrayManagerCleanup:
    """Tests for TrayManager cleanup methods."""

    def test_cleanup_clears_callbacks(self, mock_gtk_modules):
        """Test cleanup clears all callbacks."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        manager._on_quick_scan = mock.Mock()
        manager._on_full_scan = mock.Mock()
        manager._on_update = mock.Mock()
        manager._on_quit = mock.Mock()
        manager._on_window_toggle = mock.Mock()
        manager._on_profile_select = mock.Mock()

        manager.cleanup()

        assert manager._on_quick_scan is None
        assert manager._on_full_scan is None
        assert manager._on_update is None
        assert manager._on_quit is None
        assert manager._on_window_toggle is None
        assert manager._on_profile_select is None

    def test_stop_sends_quit_command(self, mock_gtk_modules):
        """Test stop sends quit command to subprocess."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        mock_process = mock.Mock()
        mock_process.wait = mock.Mock()
        manager._process = mock_process
        manager._running = True

        with mock.patch.object(manager, '_send_command') as mock_send:
            manager.stop()

            mock_send.assert_called_with({"action": "quit"})

    def test_stop_sets_running_false(self, mock_gtk_modules):
        """Test stop sets running to False."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()
        manager._running = True

        manager.stop()

        assert manager._running is False

    def test_cleanup_can_be_called_multiple_times(self, mock_gtk_modules):
        """Test cleanup can be called multiple times safely."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        # Should not raise
        manager.cleanup()
        manager.cleanup()
        manager.cleanup()


class TestTrayManagerStart:
    """Tests for TrayManager.start method."""

    def test_start_returns_false_without_service_path(self, mock_gtk_modules):
        """Test start returns False if service path not found."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()

        with mock.patch.object(manager, '_get_service_path', return_value=None):
            result = manager.start()

        assert result is False

    def test_start_already_running_returns_true(self, mock_gtk_modules):
        """Test start returns True if already running."""
        from src.ui.tray_manager import TrayManager
        manager = TrayManager()
        manager._process = mock.Mock()

        result = manager.start()

        assert result is True
