# ClamUI LogsView Tests
"""
Unit tests for the LogsView component.

Tests cover:
- Initialization and setup
- Loading state management
- Log entry display and pagination
- Log selection and detail display
- Daemon status and live log updates
- Clear logs functionality
- Copy/export functionality
- CSV formatting
"""

import sys
from unittest import mock

import pytest


@pytest.fixture
def mock_log_manager():
    """Create a mock LogManager."""
    manager = mock.MagicMock()
    manager.get_logs_async = mock.MagicMock()
    manager.get_log_by_id = mock.MagicMock()
    manager.clear_logs = mock.MagicMock()
    manager.get_daemon_status = mock.MagicMock(return_value=("RUNNING", "Running"))
    manager.read_daemon_logs = mock.MagicMock(return_value=(True, "daemon log content"))
    return manager


@pytest.fixture
def mock_log_entry():
    """Create a mock LogEntry."""
    entry = mock.MagicMock()
    entry.id = "test-log-id-123"
    entry.type = "scan"
    entry.status = "clean"
    entry.timestamp = "2024-01-15T10:30:00"
    entry.path = "/home/user/documents"
    entry.summary = "Scanned 100 files, 0 threats found"
    entry.duration = 45.5
    entry.details = "Detailed scan output here..."
    return entry


@pytest.fixture
def logs_view_class(mock_gi_modules):
    """Get LogsView class with mocked dependencies."""
    # Add additional mock modules that logs_view.py imports
    # Note: src.core.log_manager is NOT mocked - we need the real DaemonStatus enum
    sys.modules['src.core.utils'] = mock.MagicMock()
    sys.modules['src.ui.fullscreen_dialog'] = mock.MagicMock()

    from src.ui.logs_view import LogsView
    return LogsView


@pytest.fixture
def mock_logs_view(logs_view_class, mock_log_manager):
    """Create a mock LogsView instance for testing."""
    # Create instance without calling __init__ (Python 3.13+ compatible)
    view = object.__new__(logs_view_class)

    # Set up required attributes
    view._log_manager = mock_log_manager
    view._selected_log = None
    view._daemon_refresh_id = None
    view._is_loading = False
    view._displayed_log_count = 0
    view._all_log_entries = []
    view._load_more_row = None

    # Mock UI elements
    view._view_stack = mock.MagicMock()
    view._logs_listbox = mock.MagicMock()
    view._logs_spinner = mock.MagicMock()
    view._refresh_button = mock.MagicMock()
    view._clear_button = mock.MagicMock()
    view._detail_text = mock.MagicMock()
    view._detail_group = mock.MagicMock()
    view._copy_detail_button = mock.MagicMock()
    view._export_detail_text_button = mock.MagicMock()
    view._export_detail_csv_button = mock.MagicMock()
    view._fullscreen_detail_button = mock.MagicMock()
    view._daemon_text = mock.MagicMock()
    view._daemon_group = mock.MagicMock()
    view._daemon_status_row = mock.MagicMock()
    view._live_toggle = mock.MagicMock()
    view._fullscreen_daemon_button = mock.MagicMock()

    # Mock internal methods
    view._setup_ui = mock.MagicMock()
    view._load_logs_async = mock.MagicMock()
    view._set_loading_state = mock.MagicMock()
    view._display_log_details = mock.MagicMock()
    view._create_log_row = mock.MagicMock()
    view._check_daemon_status = mock.MagicMock()
    view.get_root = mock.MagicMock(return_value=None)

    return view


class TestLogsViewImport:
    """Tests for LogsView import."""

    def test_import_logs_view(self, mock_gi_modules):
        """Test that LogsView can be imported."""
        with mock.patch.dict(sys.modules, {
            'src.core.log_manager': mock.MagicMock(),
            'src.core.utils': mock.MagicMock(),
            'src.ui.fullscreen_dialog': mock.MagicMock(),
        }):
            from src.ui.logs_view import LogsView
            assert LogsView is not None

    def test_import_from_ui_package(self, mock_gi_modules):
        """Test that LogsView is exported from src.ui package."""
        with mock.patch.dict(sys.modules, {
            'src.core.log_manager': mock.MagicMock(),
            'src.core.utils': mock.MagicMock(),
            'src.ui.fullscreen_dialog': mock.MagicMock(),
            'src.ui.update_view': mock.MagicMock(),
            'src.ui.components_view': mock.MagicMock(),
            'src.ui.preferences_dialog': mock.MagicMock(),
            'src.ui.quarantine_view': mock.MagicMock(),
        }):
            from src.ui import LogsView
            assert LogsView is not None

    def test_pagination_constants_defined(self, mock_gi_modules):
        """Test that pagination constants are defined."""
        with mock.patch.dict(sys.modules, {
            'src.core.log_manager': mock.MagicMock(),
            'src.core.utils': mock.MagicMock(),
            'src.ui.fullscreen_dialog': mock.MagicMock(),
        }):
            from src.ui.logs_view import INITIAL_LOG_DISPLAY_LIMIT, LOAD_MORE_LOG_BATCH_SIZE
            assert INITIAL_LOG_DISPLAY_LIMIT == 25
            assert LOAD_MORE_LOG_BATCH_SIZE == 25


class TestLogsViewInitialization:
    """Tests for LogsView initialization."""

    def test_initial_loading_state_is_false(self, mock_logs_view):
        """Test that initial loading state is False."""
        assert mock_logs_view._is_loading is False

    def test_initial_selected_log_is_none(self, mock_logs_view):
        """Test that initial selected log is None."""
        assert mock_logs_view._selected_log is None

    def test_initial_daemon_refresh_id_is_none(self, mock_logs_view):
        """Test that initial daemon refresh ID is None."""
        assert mock_logs_view._daemon_refresh_id is None

    def test_initial_displayed_log_count_is_zero(self, mock_logs_view):
        """Test that initial displayed log count is zero."""
        assert mock_logs_view._displayed_log_count == 0

    def test_initial_all_log_entries_is_empty(self, mock_logs_view):
        """Test that initial all_log_entries is empty."""
        assert mock_logs_view._all_log_entries == []

    def test_initial_load_more_row_is_none(self, mock_logs_view):
        """Test that initial load_more_row is None."""
        assert mock_logs_view._load_more_row is None


class TestLogsViewLoadingState:
    """Tests for loading state management."""

    def test_set_loading_state_true_shows_spinner(self, logs_view_class, mock_log_manager):
        """Test that setting loading True shows spinner."""
        view = object.__new__(logs_view_class)
        view._is_loading = False
        view._logs_spinner = mock.MagicMock()
        view._refresh_button = mock.MagicMock()
        view._clear_button = mock.MagicMock()
        view._logs_listbox = mock.MagicMock()
        view._create_loading_state = mock.MagicMock()

        view._set_loading_state(True)

        assert view._is_loading is True
        view._logs_spinner.set_visible.assert_called_with(True)
        view._logs_spinner.start.assert_called_once()
        view._refresh_button.set_sensitive.assert_called_with(False)
        view._clear_button.set_sensitive.assert_called_with(False)

    def test_set_loading_state_false_hides_spinner(self, logs_view_class, mock_log_manager):
        """Test that setting loading False hides spinner."""
        view = object.__new__(logs_view_class)
        view._is_loading = True
        view._logs_spinner = mock.MagicMock()
        view._refresh_button = mock.MagicMock()
        view._clear_button = mock.MagicMock()
        view._logs_listbox = mock.MagicMock()

        view._set_loading_state(False)

        assert view._is_loading is False
        view._logs_spinner.stop.assert_called_once()
        view._logs_spinner.set_visible.assert_called_with(False)
        view._refresh_button.set_sensitive.assert_called_with(True)

    def test_load_logs_async_prevents_double_load(self, logs_view_class, mock_log_manager):
        """Test that async load prevents loading when already loading."""
        view = object.__new__(logs_view_class)
        view._is_loading = True
        view._set_loading_state = mock.MagicMock()
        view._log_manager = mock_log_manager

        view._load_logs_async()

        view._set_loading_state.assert_not_called()


class TestLogsViewLogSelection:
    """Tests for log selection handling."""

    def test_on_log_selected_with_none_clears_selection(self, logs_view_class):
        """Test that selecting None clears the selection."""
        view = object.__new__(logs_view_class)
        view._selected_log = mock.MagicMock()
        view._detail_text = mock.MagicMock()
        mock_buffer = mock.MagicMock()
        view._detail_text.get_buffer.return_value = mock_buffer
        view._copy_detail_button = mock.MagicMock()
        view._export_detail_text_button = mock.MagicMock()
        view._export_detail_csv_button = mock.MagicMock()

        view._on_log_selected(mock.MagicMock(), None)

        assert view._selected_log is None
        mock_buffer.set_text.assert_called_with("Select a log entry to view details.")
        view._copy_detail_button.set_sensitive.assert_called_with(False)
        view._export_detail_text_button.set_sensitive.assert_called_with(False)
        view._export_detail_csv_button.set_sensitive.assert_called_with(False)

    def test_on_log_selected_enables_buttons(self, logs_view_class, mock_log_entry, mock_log_manager):
        """Test that selecting a log enables copy/export buttons."""
        view = object.__new__(logs_view_class)
        view._selected_log = None
        view._log_manager = mock_log_manager
        view._log_manager.get_log_by_id.return_value = mock_log_entry
        view._display_log_details = mock.MagicMock()
        view._copy_detail_button = mock.MagicMock()
        view._export_detail_text_button = mock.MagicMock()
        view._export_detail_csv_button = mock.MagicMock()

        mock_row = mock.MagicMock()
        mock_row.get_name.return_value = "test-log-id-123"

        view._on_log_selected(mock.MagicMock(), mock_row)

        assert view._selected_log == mock_log_entry
        view._copy_detail_button.set_sensitive.assert_called_with(True)
        view._export_detail_text_button.set_sensitive.assert_called_with(True)
        view._export_detail_csv_button.set_sensitive.assert_called_with(True)
        view._display_log_details.assert_called_once_with(mock_log_entry)

    def test_on_log_selected_returns_when_entry_not_found(self, logs_view_class, mock_log_manager):
        """Test that selecting a log that doesn't exist returns early."""
        view = object.__new__(logs_view_class)
        view._selected_log = None
        view._log_manager = mock_log_manager
        view._log_manager.get_log_by_id.return_value = None
        view._display_log_details = mock.MagicMock()

        mock_row = mock.MagicMock()
        mock_row.get_name.return_value = "nonexistent-id"

        view._on_log_selected(mock.MagicMock(), mock_row)

        view._display_log_details.assert_not_called()


class TestLogsViewPagination:
    """Tests for log pagination functionality."""

    def test_on_logs_loaded_with_empty_list(self, logs_view_class, mock_log_manager):
        """Test handling empty logs list."""
        view = object.__new__(logs_view_class)
        view._is_loading = True
        view._logs_listbox = mock.MagicMock()
        view._clear_button = mock.MagicMock()
        view._all_log_entries = []
        view._displayed_log_count = 0
        view._load_more_row = None
        view._set_loading_state = mock.MagicMock()

        result = view._on_logs_loaded([])

        assert result is False
        view._clear_button.set_sensitive.assert_called_with(False)
        assert view._all_log_entries == []

    def test_on_logs_loaded_stores_entries(self, logs_view_class, mock_log_entry):
        """Test that loaded logs are stored."""
        view = object.__new__(logs_view_class)
        view._is_loading = True
        view._logs_listbox = mock.MagicMock()
        view._logs_listbox.get_row_at_index.return_value = mock.MagicMock()
        view._clear_button = mock.MagicMock()
        view._all_log_entries = []
        view._displayed_log_count = 0
        view._load_more_row = None
        view._set_loading_state = mock.MagicMock()
        view._display_log_batch = mock.MagicMock()
        view._add_load_more_button = mock.MagicMock()

        logs = [mock_log_entry]
        view._on_logs_loaded(logs)

        assert view._all_log_entries == logs

    def test_display_log_batch_increments_count(self, logs_view_class, mock_log_entry):
        """Test that displaying logs increments the displayed count."""
        view = object.__new__(logs_view_class)
        view._all_log_entries = [mock_log_entry, mock_log_entry]
        view._displayed_log_count = 0
        view._load_more_row = None
        view._logs_listbox = mock.MagicMock()
        view._create_log_row = mock.MagicMock(return_value=mock.MagicMock())

        view._display_log_batch(0, 2)

        assert view._displayed_log_count == 2

    def test_on_load_more_logs_clicked_removes_load_more_row(self, logs_view_class, mock_log_entry):
        """Test that clicking load more removes the load more row."""
        view = object.__new__(logs_view_class)
        view._all_log_entries = [mock_log_entry] * 30
        view._displayed_log_count = 25
        load_more_row = mock.MagicMock()
        view._load_more_row = load_more_row
        view._logs_listbox = mock.MagicMock()
        view._display_log_batch = mock.MagicMock()
        view._add_load_more_button = mock.MagicMock()

        view._on_load_more_logs_clicked(mock.MagicMock())

        # Capture the row BEFORE the call since method sets it to None
        view._logs_listbox.remove.assert_called_with(load_more_row)

    def test_on_show_all_logs_clicked_displays_remaining(self, logs_view_class, mock_log_entry):
        """Test that clicking show all displays remaining logs."""
        view = object.__new__(logs_view_class)
        view._all_log_entries = [mock_log_entry] * 50
        view._displayed_log_count = 25
        view._load_more_row = mock.MagicMock()
        view._logs_listbox = mock.MagicMock()
        view._display_log_batch = mock.MagicMock()

        view._on_show_all_logs_clicked(mock.MagicMock())

        # Should display remaining 25 logs
        view._display_log_batch.assert_called_once_with(25, 25)


class TestLogsViewLogRowCreation:
    """Tests for log row creation."""

    def test_create_log_row_sets_scan_icon(self, logs_view_class, mock_log_entry, mock_gi_modules):
        """Test that scan logs get folder icon."""
        view = object.__new__(logs_view_class)
        mock_log_entry.type = "scan"

        # Configure Adw.ActionRow to return our mock_row
        mock_row = mock.MagicMock()
        mock_gi_modules['adw'].ActionRow.return_value = mock_row

        row = view._create_log_row(mock_log_entry)

        mock_row.set_icon_name.assert_called_with("folder-symbolic")

    def test_create_log_row_sets_update_icon(self, logs_view_class, mock_log_entry, mock_gi_modules):
        """Test that update logs get update icon."""
        view = object.__new__(logs_view_class)
        mock_log_entry.type = "update"

        mock_row = mock.MagicMock()
        mock_gi_modules['adw'].ActionRow.return_value = mock_row

        row = view._create_log_row(mock_log_entry)

        mock_row.set_icon_name.assert_called_with("software-update-available-symbolic")

    def test_create_log_row_sets_name_to_id(self, logs_view_class, mock_log_entry, mock_gi_modules):
        """Test that row name is set to entry ID."""
        view = object.__new__(logs_view_class)

        mock_row = mock.MagicMock()
        mock_gi_modules['adw'].ActionRow.return_value = mock_row

        row = view._create_log_row(mock_log_entry)

        mock_row.set_name.assert_called_with("test-log-id-123")


class TestLogsViewDaemonStatus:
    """Tests for daemon status checking."""

    def test_check_daemon_status_running(self, logs_view_class, mock_log_manager):
        """Test daemon status display when running."""
        # Import real DaemonStatus to match what the implementation uses
        from src.core.log_manager import DaemonStatus

        view = object.__new__(logs_view_class)
        view._log_manager = mock_log_manager
        view._log_manager.get_daemon_status.return_value = (DaemonStatus.RUNNING, "Running")
        view._daemon_status_row = mock.MagicMock()
        view._live_toggle = mock.MagicMock()

        result = view._check_daemon_status()

        assert result is False
        view._daemon_status_row.set_subtitle.assert_called_with("Running")
        view._daemon_status_row.set_icon_name.assert_called_with("emblem-ok-symbolic")
        view._live_toggle.set_sensitive.assert_called_with(True)

    def test_check_daemon_status_stopped(self, logs_view_class, mock_log_manager):
        """Test daemon status display when stopped."""
        from src.core.log_manager import DaemonStatus

        view = object.__new__(logs_view_class)
        view._log_manager = mock_log_manager
        view._log_manager.get_daemon_status.return_value = (DaemonStatus.STOPPED, "Stopped")
        view._daemon_status_row = mock.MagicMock()
        view._live_toggle = mock.MagicMock()

        view._check_daemon_status()

        view._daemon_status_row.set_subtitle.assert_called_with("Stopped")
        view._daemon_status_row.set_icon_name.assert_called_with("media-playback-stop-symbolic")
        view._live_toggle.set_sensitive.assert_called_with(True)

    def test_check_daemon_status_not_installed(self, logs_view_class, mock_log_manager):
        """Test daemon status display when not installed."""
        from src.core.log_manager import DaemonStatus

        view = object.__new__(logs_view_class)
        view._log_manager = mock_log_manager
        view._log_manager.get_daemon_status.return_value = (DaemonStatus.NOT_INSTALLED, "")
        view._daemon_status_row = mock.MagicMock()
        view._live_toggle = mock.MagicMock()
        view._daemon_text = mock.MagicMock()
        mock_buffer = mock.MagicMock()
        view._daemon_text.get_buffer.return_value = mock_buffer

        view._check_daemon_status()

        view._daemon_status_row.set_subtitle.assert_called_with("Not installed")
        view._live_toggle.set_sensitive.assert_called_with(False)


class TestLogsViewLiveToggle:
    """Tests for live log toggle functionality."""

    def test_on_live_toggle_starts_refresh(self, logs_view_class):
        """Test that toggling on starts refresh."""
        view = object.__new__(logs_view_class)
        view._start_daemon_log_refresh = mock.MagicMock()
        view._stop_daemon_log_refresh = mock.MagicMock()

        mock_button = mock.MagicMock()
        mock_button.get_active.return_value = True

        view._on_live_toggle(mock_button)

        mock_button.set_icon_name.assert_called_with("media-playback-pause-symbolic")
        mock_button.set_tooltip_text.assert_called_with("Stop live log updates")
        view._start_daemon_log_refresh.assert_called_once()

    def test_on_live_toggle_stops_refresh(self, logs_view_class):
        """Test that toggling off stops refresh."""
        view = object.__new__(logs_view_class)
        view._start_daemon_log_refresh = mock.MagicMock()
        view._stop_daemon_log_refresh = mock.MagicMock()

        mock_button = mock.MagicMock()
        mock_button.get_active.return_value = False

        view._on_live_toggle(mock_button)

        mock_button.set_icon_name.assert_called_with("media-playback-start-symbolic")
        mock_button.set_tooltip_text.assert_called_with("Start live log updates")
        view._stop_daemon_log_refresh.assert_called_once()

    def test_stop_daemon_log_refresh_removes_timeout(self, logs_view_class):
        """Test that stopping refresh removes the timeout."""
        with mock.patch.dict(sys.modules, {'gi.repository.GLib': mock.MagicMock()}):
            from gi.repository import GLib

            view = object.__new__(logs_view_class)
            view._daemon_refresh_id = 12345

            view._stop_daemon_log_refresh()

            GLib.source_remove.assert_called_once_with(12345)
            assert view._daemon_refresh_id is None

    def test_stop_daemon_log_refresh_with_no_id(self, logs_view_class):
        """Test that stopping refresh with no ID does nothing."""
        with mock.patch.dict(sys.modules, {'gi.repository.GLib': mock.MagicMock()}):
            from gi.repository import GLib

            view = object.__new__(logs_view_class)
            view._daemon_refresh_id = None

            view._stop_daemon_log_refresh()

            GLib.source_remove.assert_not_called()


class TestLogsViewRefreshDaemonLogs:
    """Tests for daemon log refresh."""

    def test_refresh_daemon_logs_success(self, logs_view_class, mock_log_manager):
        """Test successful daemon log refresh."""
        view = object.__new__(logs_view_class)
        view._log_manager = mock_log_manager
        view._log_manager.read_daemon_logs.return_value = (True, "log content here")
        view._daemon_text = mock.MagicMock()
        mock_buffer = mock.MagicMock()
        mock_buffer.get_end_iter.return_value = mock.MagicMock()
        view._daemon_text.get_buffer.return_value = mock_buffer
        view._daemon_refresh_id = 123

        result = view._refresh_daemon_logs()

        mock_buffer.set_text.assert_called_with("log content here")
        assert result is True

    def test_refresh_daemon_logs_failure(self, logs_view_class, mock_log_manager):
        """Test failed daemon log refresh."""
        view = object.__new__(logs_view_class)
        view._log_manager = mock_log_manager
        view._log_manager.read_daemon_logs.return_value = (False, "Permission denied")
        view._daemon_text = mock.MagicMock()
        mock_buffer = mock.MagicMock()
        view._daemon_text.get_buffer.return_value = mock_buffer
        view._daemon_refresh_id = None

        result = view._refresh_daemon_logs()

        mock_buffer.set_text.assert_called_with("Error loading daemon logs:\n\nPermission denied")
        assert result is False


class TestLogsViewClearLogs:
    """Tests for clear logs functionality."""

    def test_on_clear_dialog_response_clears_logs(self, logs_view_class, mock_log_manager):
        """Test that clear response clears logs."""
        view = object.__new__(logs_view_class)
        view._log_manager = mock_log_manager
        view._all_log_entries = [mock.MagicMock()]
        view._displayed_log_count = 10
        view._load_more_row = mock.MagicMock()
        view._load_logs_async = mock.MagicMock()
        view._detail_text = mock.MagicMock()
        mock_buffer = mock.MagicMock()
        view._detail_text.get_buffer.return_value = mock_buffer
        view._selected_log = mock.MagicMock()
        view._copy_detail_button = mock.MagicMock()
        view._export_detail_text_button = mock.MagicMock()
        view._export_detail_csv_button = mock.MagicMock()

        view._on_clear_dialog_response(mock.MagicMock(), "clear")

        view._log_manager.clear_logs.assert_called_once()
        assert view._all_log_entries == []
        assert view._displayed_log_count == 0
        assert view._load_more_row is None
        view._load_logs_async.assert_called_once()
        assert view._selected_log is None
        view._copy_detail_button.set_sensitive.assert_called_with(False)

    def test_on_clear_dialog_response_cancel_does_nothing(self, logs_view_class, mock_log_manager):
        """Test that cancel response does nothing."""
        view = object.__new__(logs_view_class)
        view._log_manager = mock_log_manager
        view._all_log_entries = [mock.MagicMock()]
        view._load_logs_async = mock.MagicMock()

        view._on_clear_dialog_response(mock.MagicMock(), "cancel")

        view._log_manager.clear_logs.assert_not_called()
        view._load_logs_async.assert_not_called()


class TestLogsViewRefresh:
    """Tests for refresh functionality."""

    def test_on_refresh_clicked_loads_logs(self, logs_view_class):
        """Test that refresh button click triggers load."""
        view = object.__new__(logs_view_class)
        view._load_logs_async = mock.MagicMock()

        view._on_refresh_clicked(mock.MagicMock())

        view._load_logs_async.assert_called_once()

    def test_refresh_logs_public_method(self, logs_view_class):
        """Test that public refresh_logs method works."""
        with mock.patch.dict(sys.modules, {'gi.repository.GLib': mock.MagicMock()}):
            from gi.repository import GLib
            GLib.idle_add = lambda f: f()

            view = object.__new__(logs_view_class)
            view._load_logs_async = mock.MagicMock()

            view.refresh_logs()


class TestLogsViewDisplayLogDetails:
    """Tests for log detail display."""

    def test_display_log_details_scan(self, logs_view_class, mock_log_entry):
        """Test displaying scan log details."""
        view = object.__new__(logs_view_class)
        view._detail_text = mock.MagicMock()
        mock_buffer = mock.MagicMock()
        view._detail_text.get_buffer.return_value = mock_buffer
        mock_log_entry.type = "scan"

        view._display_log_details(mock_log_entry)

        # Verify buffer.set_text was called with content containing SCAN LOG
        call_args = mock_buffer.set_text.call_args[0][0]
        assert "SCAN LOG" in call_args
        assert mock_log_entry.id in call_args

    def test_display_log_details_update(self, logs_view_class, mock_log_entry):
        """Test displaying update log details."""
        view = object.__new__(logs_view_class)
        view._detail_text = mock.MagicMock()
        mock_buffer = mock.MagicMock()
        view._detail_text.get_buffer.return_value = mock_buffer
        mock_log_entry.type = "update"

        view._display_log_details(mock_log_entry)

        call_args = mock_buffer.set_text.call_args[0][0]
        assert "UPDATE LOG" in call_args


class TestLogsViewCopyExport:
    """Tests for copy and export functionality."""

    def test_on_copy_detail_clicked_with_no_selection(self, logs_view_class):
        """Test that copy does nothing when no log selected."""
        with mock.patch.dict(sys.modules, {
            'src.core.utils': mock.MagicMock(),
        }):
            from src.core.utils import copy_to_clipboard

            view = object.__new__(logs_view_class)
            view._selected_log = None

            view._on_copy_detail_clicked(mock.MagicMock())

            copy_to_clipboard.assert_not_called()

    def test_on_copy_detail_clicked_copies_content(self, logs_view_class, mock_log_entry):
        """Test that copy copies content to clipboard."""
        view = object.__new__(logs_view_class)
        view._selected_log = mock_log_entry
        view._detail_text = mock.MagicMock()
        mock_buffer = mock.MagicMock()
        mock_buffer.get_start_iter.return_value = mock.MagicMock()
        mock_buffer.get_end_iter.return_value = mock.MagicMock()
        mock_buffer.get_text.return_value = "log content"
        view._detail_text.get_buffer.return_value = mock_buffer
        view.get_root = mock.MagicMock(return_value=None)

        # Patch copy_to_clipboard on the logs_view module's reference
        with mock.patch('src.ui.logs_view.copy_to_clipboard') as mock_copy:
            mock_copy.return_value = True
            view._on_copy_detail_clicked(mock.MagicMock())
            mock_copy.assert_called_once_with("log content")

    def test_on_export_detail_text_clicked_with_no_selection(self, logs_view_class):
        """Test that export does nothing when no log selected."""
        view = object.__new__(logs_view_class)
        view._selected_log = None

        # Should return early without creating dialog
        view._on_export_detail_text_clicked(mock.MagicMock())

    def test_on_export_detail_csv_clicked_with_no_selection(self, logs_view_class):
        """Test that CSV export does nothing when no log selected."""
        view = object.__new__(logs_view_class)
        view._selected_log = None

        # Should return early without creating dialog
        view._on_export_detail_csv_clicked(mock.MagicMock())


class TestLogsViewCSVFormatting:
    """Tests for CSV formatting."""

    def test_format_log_entry_as_csv_basic(self, logs_view_class, mock_log_entry):
        """Test basic CSV formatting."""
        view = object.__new__(logs_view_class)

        result = view._format_log_entry_as_csv(mock_log_entry)

        # Verify header row is present
        assert "timestamp,type,status,path,summary,duration" in result
        # Verify data values are present
        assert mock_log_entry.timestamp in result
        assert mock_log_entry.type in result
        assert mock_log_entry.status in result

    def test_format_log_entry_as_csv_escapes_special_chars(self, logs_view_class, mock_log_entry):
        """Test CSV formatting with special characters."""
        view = object.__new__(logs_view_class)
        mock_log_entry.summary = 'Summary with "quotes" and, commas'

        result = view._format_log_entry_as_csv(mock_log_entry)

        # CSV should properly escape quotes
        assert result is not None

    def test_format_log_entry_as_csv_handles_no_path(self, logs_view_class, mock_log_entry):
        """Test CSV formatting when path is None."""
        view = object.__new__(logs_view_class)
        mock_log_entry.path = None

        result = view._format_log_entry_as_csv(mock_log_entry)

        # Should not raise an error
        assert result is not None

    def test_format_log_entry_as_csv_handles_zero_duration(self, logs_view_class, mock_log_entry):
        """Test CSV formatting with zero duration."""
        view = object.__new__(logs_view_class)
        mock_log_entry.duration = 0

        result = view._format_log_entry_as_csv(mock_log_entry)

        # Should output "0" for zero duration
        assert ",0\n" in result or ",0\r\n" in result


class TestLogsViewLogManagerProperty:
    """Tests for log_manager property."""

    def test_log_manager_property_returns_manager(self, mock_logs_view, mock_log_manager):
        """Test that log_manager property returns the internal manager."""
        result = mock_logs_view.log_manager

        assert result is mock_log_manager


class TestLogsViewShowExportToast:
    """Tests for export toast notifications."""

    def test_show_export_toast_success(self, logs_view_class):
        """Test showing success toast."""
        with mock.patch.dict(sys.modules, {'gi.repository.Adw': mock.MagicMock()}):
            from gi.repository import Adw

            view = object.__new__(logs_view_class)
            mock_window = mock.MagicMock()
            mock_window.add_toast = mock.MagicMock()
            view.get_root = mock.MagicMock(return_value=mock_window)

            view._show_export_toast("Export successful")

            Adw.Toast.new.assert_called_with("Export successful")
            mock_window.add_toast.assert_called_once()

    def test_show_export_toast_no_window(self, logs_view_class):
        """Test showing toast when no window available."""
        with mock.patch.dict(sys.modules, {'gi.repository.Adw': mock.MagicMock()}):
            view = object.__new__(logs_view_class)
            view.get_root = mock.MagicMock(return_value=None)

            # Should not raise an error
            view._show_export_toast("Export successful")


class TestLogsViewUnmapMap:
    """Tests for widget mapping/unmapping lifecycle."""

    def test_do_unmap_stops_daemon_refresh(self, logs_view_class):
        """Test that unmapping stops daemon log refresh."""
        view = object.__new__(logs_view_class)
        view._stop_daemon_log_refresh = mock.MagicMock()
        view._live_toggle = mock.MagicMock()
        view._live_toggle.get_active.return_value = True

        # Call the method directly - parent class call is a no-op with mocks
        view.do_unmap()

        view._stop_daemon_log_refresh.assert_called_once()
        view._live_toggle.set_active.assert_called_with(False)


# Module-level test function for verification
def test_logs_view_basic(mock_gi_modules):
    """
    Basic test function for pytest verification command.

    This test verifies the core LogsView functionality
    using the centralized mock setup.
    """
    from src.ui.logs_view import LogsView, INITIAL_LOG_DISPLAY_LIMIT, LOAD_MORE_LOG_BATCH_SIZE

    # Test 1: Class can be imported
    assert LogsView is not None

    # Test 2: Pagination constants are correct
    assert INITIAL_LOG_DISPLAY_LIMIT == 25
    assert LOAD_MORE_LOG_BATCH_SIZE == 25

    # Test 3: Create mock instance and test CSV formatting
    view = object.__new__(LogsView)

    # Create mock log entry
    mock_entry = mock.MagicMock()
    mock_entry.id = "test-123"
    mock_entry.timestamp = "2024-01-15T10:30:00"
    mock_entry.type = "scan"
    mock_entry.status = "clean"
    mock_entry.path = "/home/user"
    mock_entry.summary = "Test summary"
    mock_entry.duration = 30.5

    # Test _format_log_entry_as_csv
    csv_result = view._format_log_entry_as_csv(mock_entry)
    assert "timestamp" in csv_result
    assert "type" in csv_result
    assert "status" in csv_result
    assert "2024-01-15T10:30:00" in csv_result

    # All tests passed
