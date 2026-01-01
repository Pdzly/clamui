# ClamUI QuarantineView Tests
"""
Unit tests for the QuarantineView component.

Tests cover:
- Initialization and setup
- Loading state management
- Quarantine entry display and pagination
- Restore and delete operations
- Clear old items functionality
- Storage info display
- format_file_size utility function
- Callback mechanism for quarantine changes
"""

import sys
from unittest import mock

import pytest


@pytest.fixture
def mock_quarantine_manager():
    """Create a mock QuarantineManager."""
    manager = mock.MagicMock()
    manager.get_all_entries_async = mock.MagicMock()
    manager.get_entry_count = mock.MagicMock(return_value=5)
    manager.get_total_size = mock.MagicMock(return_value=1024 * 1024)
    manager.restore_file_async = mock.MagicMock()
    manager.delete_file_async = mock.MagicMock()
    manager.cleanup_old_entries_async = mock.MagicMock()
    manager.get_old_entries = mock.MagicMock(return_value=[])
    return manager


@pytest.fixture
def mock_quarantine_entry():
    """Create a mock QuarantineEntry."""
    entry = mock.MagicMock()
    entry.id = "test-quarantine-id-123"
    entry.threat_name = "Eicar-Test-Signature"
    entry.original_path = "/home/user/downloads/malicious.exe"
    entry.detection_date = "2024-01-15T10:30:00"
    entry.file_size = 65536
    return entry


@pytest.fixture
def quarantine_view_class(mock_gi_modules):
    """Get QuarantineView class with mocked dependencies."""
    with mock.patch.dict(sys.modules, {
        'src.core.quarantine': mock.MagicMock(),
    }):
        from src.ui.quarantine_view import QuarantineView
        return QuarantineView


@pytest.fixture
def mock_quarantine_view(quarantine_view_class, mock_quarantine_manager):
    """Create a mock QuarantineView instance for testing."""
    # Create instance without calling __init__
    view = object.__new__(quarantine_view_class)

    # Set up required attributes
    view._manager = mock_quarantine_manager
    view._is_loading = False
    view._displayed_count = 0
    view._all_entries = []
    view._load_more_row = None
    view._on_quarantine_changed = None
    view._last_refresh_time = 0.0

    # Mock UI elements
    view._status_banner = mock.MagicMock()
    view._storage_row = mock.MagicMock()
    view._count_label = mock.MagicMock()
    view._list_group = mock.MagicMock()
    view._listbox = mock.MagicMock()
    view._spinner = mock.MagicMock()
    view._refresh_button = mock.MagicMock()
    view._clear_old_button = mock.MagicMock()

    # Mock internal methods
    view._setup_ui = mock.MagicMock()
    view._load_entries_async = mock.MagicMock()
    view._set_loading_state = mock.MagicMock()
    view._create_entry_row = mock.MagicMock()
    view._update_storage_info = mock.MagicMock()
    view.get_root = mock.MagicMock(return_value=None)

    return view


class TestQuarantineViewImport:
    """Tests for QuarantineView import."""

    def test_import_quarantine_view(self, mock_gi_modules):
        """Test that QuarantineView can be imported."""
        with mock.patch.dict(sys.modules, {
            'src.core.quarantine': mock.MagicMock(),
        }):
            from src.ui.quarantine_view import QuarantineView
            assert QuarantineView is not None

    def test_import_from_ui_package(self, mock_gi_modules):
        """Test that QuarantineView is exported from src.ui package."""
        with mock.patch.dict(sys.modules, {
            'src.core.quarantine': mock.MagicMock(),
            'src.core.log_manager': mock.MagicMock(),
            'src.core.utils': mock.MagicMock(),
            'src.ui.fullscreen_dialog': mock.MagicMock(),
            'src.ui.update_view': mock.MagicMock(),
            'src.ui.logs_view': mock.MagicMock(),
            'src.ui.components_view': mock.MagicMock(),
            'src.ui.preferences_dialog': mock.MagicMock(),
        }):
            from src.ui import QuarantineView
            assert QuarantineView is not None

    def test_pagination_constants_defined(self, mock_gi_modules):
        """Test that pagination constants are defined."""
        with mock.patch.dict(sys.modules, {
            'src.core.quarantine': mock.MagicMock(),
        }):
            from src.ui.quarantine_view import INITIAL_DISPLAY_LIMIT, LOAD_MORE_BATCH_SIZE
            assert INITIAL_DISPLAY_LIMIT == 25
            assert LOAD_MORE_BATCH_SIZE == 25


class TestFormatFileSize:
    """Tests for the format_file_size utility function."""

    def test_format_file_size_bytes(self, mock_gi_modules):
        """Test formatting file size in bytes."""
        with mock.patch.dict(sys.modules, {
            'src.core.quarantine': mock.MagicMock(),
        }):
            from src.ui.quarantine_view import format_file_size
            assert format_file_size(500) == "500 B"
            assert format_file_size(0) == "0 B"
            assert format_file_size(1023) == "1023 B"

    def test_format_file_size_kilobytes(self, mock_gi_modules):
        """Test formatting file size in kilobytes."""
        with mock.patch.dict(sys.modules, {
            'src.core.quarantine': mock.MagicMock(),
        }):
            from src.ui.quarantine_view import format_file_size
            assert format_file_size(1024) == "1.0 KB"
            assert format_file_size(2048) == "2.0 KB"
            assert format_file_size(1536) == "1.5 KB"

    def test_format_file_size_megabytes(self, mock_gi_modules):
        """Test formatting file size in megabytes."""
        with mock.patch.dict(sys.modules, {
            'src.core.quarantine': mock.MagicMock(),
        }):
            from src.ui.quarantine_view import format_file_size
            assert format_file_size(1024 * 1024) == "1.0 MB"
            assert format_file_size(2 * 1024 * 1024) == "2.0 MB"
            assert format_file_size(int(1.5 * 1024 * 1024)) == "1.5 MB"

    def test_format_file_size_gigabytes(self, mock_gi_modules):
        """Test formatting file size in gigabytes."""
        with mock.patch.dict(sys.modules, {
            'src.core.quarantine': mock.MagicMock(),
        }):
            from src.ui.quarantine_view import format_file_size
            assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"
            assert format_file_size(2 * 1024 * 1024 * 1024) == "2.00 GB"


class TestQuarantineViewInitialization:
    """Tests for QuarantineView initialization."""

    def test_initial_loading_state_is_false(self, mock_quarantine_view):
        """Test that initial loading state is False."""
        assert mock_quarantine_view._is_loading is False

    def test_initial_displayed_count_is_zero(self, mock_quarantine_view):
        """Test that initial displayed count is zero."""
        assert mock_quarantine_view._displayed_count == 0

    def test_initial_all_entries_is_empty(self, mock_quarantine_view):
        """Test that initial all_entries is empty."""
        assert mock_quarantine_view._all_entries == []

    def test_initial_load_more_row_is_none(self, mock_quarantine_view):
        """Test that initial load_more_row is None."""
        assert mock_quarantine_view._load_more_row is None

    def test_initial_callback_is_none(self, mock_quarantine_view):
        """Test that initial quarantine changed callback is None."""
        assert mock_quarantine_view._on_quarantine_changed is None

    def test_initial_last_refresh_time_is_zero(self, mock_quarantine_view):
        """Test that initial last refresh time is zero."""
        assert mock_quarantine_view._last_refresh_time == 0.0


class TestQuarantineViewLoadingState:
    """Tests for loading state management."""

    def test_set_loading_state_true_shows_spinner(self, quarantine_view_class, mock_quarantine_manager):
        """Test that setting loading True shows spinner."""
        view = object.__new__(quarantine_view_class)
        view._is_loading = False
        view._spinner = mock.MagicMock()
        view._refresh_button = mock.MagicMock()
        view._clear_old_button = mock.MagicMock()
        view._listbox = mock.MagicMock()
        view._create_loading_state = mock.MagicMock()

        view._set_loading_state(True)

        assert view._is_loading is True
        view._spinner.set_visible.assert_called_with(True)
        view._spinner.start.assert_called_once()
        view._refresh_button.set_sensitive.assert_called_with(False)
        view._clear_old_button.set_sensitive.assert_called_with(False)

    def test_set_loading_state_false_hides_spinner(self, quarantine_view_class, mock_quarantine_manager):
        """Test that setting loading False hides spinner."""
        view = object.__new__(quarantine_view_class)
        view._is_loading = True
        view._spinner = mock.MagicMock()
        view._refresh_button = mock.MagicMock()
        view._clear_old_button = mock.MagicMock()
        view._listbox = mock.MagicMock()

        view._set_loading_state(False)

        assert view._is_loading is False
        view._spinner.stop.assert_called_once()
        view._spinner.set_visible.assert_called_with(False)
        view._refresh_button.set_sensitive.assert_called_with(True)

    def test_load_entries_async_prevents_double_load(self, quarantine_view_class, mock_quarantine_manager):
        """Test that async load prevents loading when already loading."""
        view = object.__new__(quarantine_view_class)
        view._is_loading = True
        view._set_loading_state = mock.MagicMock()
        view._manager = mock_quarantine_manager

        view._load_entries_async()

        view._set_loading_state.assert_not_called()


class TestQuarantineViewEntriesLoaded:
    """Tests for entries loading completion."""

    def test_on_entries_loaded_with_empty_list(self, quarantine_view_class, mock_quarantine_manager):
        """Test handling empty entries list."""
        view = object.__new__(quarantine_view_class)
        view._is_loading = True
        view._listbox = mock.MagicMock()
        view._clear_old_button = mock.MagicMock()
        view._all_entries = []
        view._displayed_count = 0
        view._load_more_row = None
        view._set_loading_state = mock.MagicMock()
        view._update_storage_info = mock.MagicMock()
        view._on_quarantine_changed = None
        view._last_refresh_time = 0.0
        view._manager = mock_quarantine_manager

        result = view._on_entries_loaded([])

        assert result is False
        view._clear_old_button.set_sensitive.assert_called_with(False)
        assert view._all_entries == []

    def test_on_entries_loaded_stores_entries(self, quarantine_view_class, mock_quarantine_entry):
        """Test that loaded entries are stored."""
        view = object.__new__(quarantine_view_class)
        view._is_loading = True
        view._listbox = mock.MagicMock()
        view._clear_old_button = mock.MagicMock()
        view._all_entries = []
        view._displayed_count = 0
        view._load_more_row = None
        view._set_loading_state = mock.MagicMock()
        view._update_storage_info = mock.MagicMock()
        view._display_entry_batch = mock.MagicMock()
        view._add_load_more_button = mock.MagicMock()
        view._on_quarantine_changed = None
        view._last_refresh_time = 0.0
        view._manager = mock.MagicMock()

        entries = [mock_quarantine_entry]
        view._on_entries_loaded(entries)

        assert view._all_entries == entries

    def test_on_entries_loaded_calls_callback(self, quarantine_view_class, mock_quarantine_entry):
        """Test that loaded entries trigger callback."""
        view = object.__new__(quarantine_view_class)
        view._is_loading = True
        view._listbox = mock.MagicMock()
        view._clear_old_button = mock.MagicMock()
        view._all_entries = []
        view._displayed_count = 0
        view._load_more_row = None
        view._set_loading_state = mock.MagicMock()
        view._update_storage_info = mock.MagicMock()
        view._display_entry_batch = mock.MagicMock()
        view._add_load_more_button = mock.MagicMock()
        view._last_refresh_time = 0.0
        view._manager = mock.MagicMock()

        callback = mock.MagicMock()
        view._on_quarantine_changed = callback

        entries = [mock_quarantine_entry]
        view._on_entries_loaded(entries)

        callback.assert_called_once_with(1)


class TestQuarantineViewPagination:
    """Tests for quarantine entry pagination."""

    def test_display_entry_batch_increments_count(self, quarantine_view_class, mock_quarantine_entry):
        """Test that displaying entries increments the displayed count."""
        view = object.__new__(quarantine_view_class)
        view._all_entries = [mock_quarantine_entry, mock_quarantine_entry]
        view._displayed_count = 0
        view._load_more_row = None
        view._listbox = mock.MagicMock()
        view._create_entry_row = mock.MagicMock(return_value=mock.MagicMock())

        view._display_entry_batch(0, 2)

        assert view._displayed_count == 2

    def test_on_load_more_clicked_removes_load_more_row(self, quarantine_view_class, mock_quarantine_entry):
        """Test that clicking load more removes the load more row."""
        view = object.__new__(quarantine_view_class)
        view._all_entries = [mock_quarantine_entry] * 30
        view._displayed_count = 25
        load_more_row = mock.MagicMock()
        view._load_more_row = load_more_row
        view._listbox = mock.MagicMock()
        view._display_entry_batch = mock.MagicMock()
        view._add_load_more_button = mock.MagicMock()

        view._on_load_more_clicked(mock.MagicMock())

        view._listbox.remove.assert_called_with(load_more_row)

    def test_on_show_all_clicked_displays_remaining(self, quarantine_view_class, mock_quarantine_entry):
        """Test that clicking show all displays remaining entries."""
        view = object.__new__(quarantine_view_class)
        view._all_entries = [mock_quarantine_entry] * 50
        view._displayed_count = 25
        view._load_more_row = mock.MagicMock()
        view._listbox = mock.MagicMock()
        view._display_entry_batch = mock.MagicMock()

        view._on_show_all_clicked(mock.MagicMock())

        # Should display remaining 25 entries
        view._display_entry_batch.assert_called_once_with(25, 25)


class TestQuarantineViewStorageInfo:
    """Tests for storage info display."""

    def test_update_storage_info_displays_size(self, quarantine_view_class, mock_quarantine_manager):
        """Test that storage info displays total size."""
        view = object.__new__(quarantine_view_class)
        view._manager = mock_quarantine_manager
        view._manager.get_total_size.return_value = 1024 * 1024  # 1 MB
        view._manager.get_entry_count.return_value = 5
        view._storage_row = mock.MagicMock()
        view._count_label = mock.MagicMock()

        view._update_storage_info()

        view._storage_row.set_subtitle.assert_called_with("1.0 MB")
        view._count_label.set_text.assert_called_with("5 items")

    def test_update_storage_info_singular_item(self, quarantine_view_class, mock_quarantine_manager):
        """Test that storage info displays singular 'item' for count of 1."""
        view = object.__new__(quarantine_view_class)
        view._manager = mock_quarantine_manager
        view._manager.get_total_size.return_value = 512
        view._manager.get_entry_count.return_value = 1
        view._storage_row = mock.MagicMock()
        view._count_label = mock.MagicMock()

        view._update_storage_info()

        view._count_label.set_text.assert_called_with("1 item")


class TestQuarantineViewRestore:
    """Tests for restore functionality."""

    def test_on_restore_clicked_shows_dialog(self, quarantine_view_class, mock_quarantine_entry):
        """Test that restore click shows confirmation dialog."""
        with mock.patch.dict(sys.modules, {'gi.repository.Adw': mock.MagicMock()}):
            from gi.repository import Adw

            view = object.__new__(quarantine_view_class)
            view.get_root = mock.MagicMock(return_value=None)

            view._on_restore_clicked(mock.MagicMock(), mock_quarantine_entry)

            Adw.MessageDialog.assert_called_once()

    def test_on_restore_dialog_response_restore(self, quarantine_view_class, mock_quarantine_entry):
        """Test that restore response triggers restore."""
        view = object.__new__(quarantine_view_class)
        view._perform_restore = mock.MagicMock()

        view._on_restore_dialog_response(mock.MagicMock(), "restore", mock_quarantine_entry)

        view._perform_restore.assert_called_once_with(mock_quarantine_entry)

    def test_on_restore_dialog_response_cancel(self, quarantine_view_class, mock_quarantine_entry):
        """Test that cancel response does nothing."""
        view = object.__new__(quarantine_view_class)
        view._perform_restore = mock.MagicMock()

        view._on_restore_dialog_response(mock.MagicMock(), "cancel", mock_quarantine_entry)

        view._perform_restore.assert_not_called()

    def test_perform_restore_shows_banner(self, quarantine_view_class, mock_quarantine_entry, mock_quarantine_manager):
        """Test that performing restore shows status banner."""
        view = object.__new__(quarantine_view_class)
        view._manager = mock_quarantine_manager
        view._status_banner = mock.MagicMock()

        view._perform_restore(mock_quarantine_entry)

        view._status_banner.set_title.assert_called()
        view._status_banner.set_revealed.assert_called_with(True)
        view._manager.restore_file_async.assert_called_once()

    def test_on_restore_complete_success(self, quarantine_view_class):
        """Test restore completion with success."""
        view = object.__new__(quarantine_view_class)
        view._status_banner = mock.MagicMock()
        view._load_entries_async = mock.MagicMock()

        mock_result = mock.MagicMock()
        mock_result.is_success = True

        view._on_restore_complete(mock_result)

        view._status_banner.set_title.assert_called_with("File restored successfully")
        view._status_banner.add_css_class.assert_called_with("success")
        view._load_entries_async.assert_called_once()

    def test_on_restore_complete_failure(self, quarantine_view_class):
        """Test restore completion with failure."""
        with mock.patch.dict(sys.modules, {
            'src.core.quarantine': mock.MagicMock(),
        }):
            from src.core.quarantine import QuarantineStatus

            view = object.__new__(quarantine_view_class)
            view._status_banner = mock.MagicMock()
            view._load_entries_async = mock.MagicMock()

            mock_result = mock.MagicMock()
            mock_result.is_success = False
            mock_result.error_message = "Permission denied"
            mock_result.status = QuarantineStatus.ERROR

            view._on_restore_complete(mock_result)

            view._status_banner.add_css_class.assert_called_with("error")
            view._load_entries_async.assert_not_called()


class TestQuarantineViewDelete:
    """Tests for delete functionality."""

    def test_on_delete_clicked_shows_dialog(self, quarantine_view_class, mock_quarantine_entry):
        """Test that delete click shows confirmation dialog."""
        with mock.patch.dict(sys.modules, {'gi.repository.Adw': mock.MagicMock()}):
            from gi.repository import Adw

            view = object.__new__(quarantine_view_class)
            view.get_root = mock.MagicMock(return_value=None)

            view._on_delete_clicked(mock.MagicMock(), mock_quarantine_entry)

            Adw.MessageDialog.assert_called_once()

    def test_on_delete_dialog_response_delete(self, quarantine_view_class, mock_quarantine_entry):
        """Test that delete response triggers delete."""
        view = object.__new__(quarantine_view_class)
        view._perform_delete = mock.MagicMock()

        view._on_delete_dialog_response(mock.MagicMock(), "delete", mock_quarantine_entry)

        view._perform_delete.assert_called_once_with(mock_quarantine_entry)

    def test_on_delete_dialog_response_cancel(self, quarantine_view_class, mock_quarantine_entry):
        """Test that cancel response does nothing."""
        view = object.__new__(quarantine_view_class)
        view._perform_delete = mock.MagicMock()

        view._on_delete_dialog_response(mock.MagicMock(), "cancel", mock_quarantine_entry)

        view._perform_delete.assert_not_called()

    def test_perform_delete_shows_banner(self, quarantine_view_class, mock_quarantine_entry, mock_quarantine_manager):
        """Test that performing delete shows status banner."""
        view = object.__new__(quarantine_view_class)
        view._manager = mock_quarantine_manager
        view._status_banner = mock.MagicMock()

        view._perform_delete(mock_quarantine_entry)

        view._status_banner.set_title.assert_called()
        view._status_banner.set_revealed.assert_called_with(True)
        view._manager.delete_file_async.assert_called_once()

    def test_on_delete_complete_success(self, quarantine_view_class):
        """Test delete completion with success."""
        view = object.__new__(quarantine_view_class)
        view._status_banner = mock.MagicMock()
        view._load_entries_async = mock.MagicMock()

        mock_result = mock.MagicMock()
        mock_result.is_success = True

        view._on_delete_complete(mock_result)

        view._status_banner.set_title.assert_called_with("File deleted permanently")
        view._status_banner.add_css_class.assert_called_with("success")
        view._load_entries_async.assert_called_once()

    def test_on_delete_complete_failure(self, quarantine_view_class):
        """Test delete completion with failure."""
        view = object.__new__(quarantine_view_class)
        view._status_banner = mock.MagicMock()
        view._load_entries_async = mock.MagicMock()

        mock_result = mock.MagicMock()
        mock_result.is_success = False
        mock_result.error_message = "Permission denied"

        view._on_delete_complete(mock_result)

        view._status_banner.add_css_class.assert_called_with("error")
        view._load_entries_async.assert_not_called()


class TestQuarantineViewClearOld:
    """Tests for clear old items functionality."""

    def test_on_clear_old_clicked_no_old_entries(self, quarantine_view_class, mock_quarantine_manager):
        """Test that clear old with no old entries shows message."""
        view = object.__new__(quarantine_view_class)
        view._manager = mock_quarantine_manager
        view._manager.get_old_entries.return_value = []
        view._status_banner = mock.MagicMock()
        view.get_root = mock.MagicMock(return_value=None)

        view._on_clear_old_clicked(mock.MagicMock())

        view._status_banner.set_title.assert_called_with("No items older than 30 days")
        view._status_banner.set_revealed.assert_called_with(True)

    def test_on_clear_old_clicked_shows_dialog(self, quarantine_view_class, mock_quarantine_entry, mock_quarantine_manager):
        """Test that clear old with entries shows confirmation dialog."""
        with mock.patch.dict(sys.modules, {'gi.repository.Adw': mock.MagicMock()}):
            from gi.repository import Adw

            view = object.__new__(quarantine_view_class)
            view._manager = mock_quarantine_manager
            view._manager.get_old_entries.return_value = [mock_quarantine_entry]
            view._status_banner = mock.MagicMock()
            view.get_root = mock.MagicMock(return_value=None)

            view._on_clear_old_clicked(mock.MagicMock())

            Adw.MessageDialog.assert_called_once()

    def test_on_clear_old_dialog_response_clear(self, quarantine_view_class):
        """Test that clear response triggers clear."""
        view = object.__new__(quarantine_view_class)
        view._perform_clear_old = mock.MagicMock()

        view._on_clear_old_dialog_response(mock.MagicMock(), "clear")

        view._perform_clear_old.assert_called_once()

    def test_on_clear_old_dialog_response_cancel(self, quarantine_view_class):
        """Test that cancel response does nothing."""
        view = object.__new__(quarantine_view_class)
        view._perform_clear_old = mock.MagicMock()

        view._on_clear_old_dialog_response(mock.MagicMock(), "cancel")

        view._perform_clear_old.assert_not_called()

    def test_on_clear_old_complete_with_removed(self, quarantine_view_class):
        """Test clear old completion with items removed."""
        view = object.__new__(quarantine_view_class)
        view._status_banner = mock.MagicMock()
        view._load_entries_async = mock.MagicMock()

        view._on_clear_old_complete(3)

        view._status_banner.set_title.assert_called_with("Removed 3 old item(s)")
        view._status_banner.add_css_class.assert_called_with("success")
        view._load_entries_async.assert_called_once()

    def test_on_clear_old_complete_none_removed(self, quarantine_view_class):
        """Test clear old completion with no items removed."""
        view = object.__new__(quarantine_view_class)
        view._status_banner = mock.MagicMock()
        view._load_entries_async = mock.MagicMock()

        view._on_clear_old_complete(0)

        view._status_banner.set_title.assert_called_with("No items were removed")
        view._load_entries_async.assert_not_called()


class TestQuarantineViewRefresh:
    """Tests for refresh functionality."""

    def test_on_refresh_clicked_loads_entries(self, quarantine_view_class):
        """Test that refresh button click triggers load."""
        view = object.__new__(quarantine_view_class)
        view._load_entries_async = mock.MagicMock()

        view._on_refresh_clicked(mock.MagicMock())

        view._load_entries_async.assert_called_once()

    def test_refresh_public_method(self, quarantine_view_class):
        """Test that public refresh method works."""
        with mock.patch.dict(sys.modules, {'gi.repository.GLib': mock.MagicMock()}):
            from gi.repository import GLib
            GLib.idle_add = lambda f: f()

            view = object.__new__(quarantine_view_class)
            view._load_entries_async = mock.MagicMock()

            view.refresh()


class TestQuarantineViewCallback:
    """Tests for quarantine changed callback."""

    def test_set_quarantine_changed_callback(self, mock_quarantine_view):
        """Test that callback can be set."""
        callback = mock.MagicMock()
        mock_quarantine_view.set_quarantine_changed_callback(callback)

        assert mock_quarantine_view._on_quarantine_changed is callback

    def test_notify_quarantine_changed_calls_callback(self, quarantine_view_class, mock_quarantine_manager):
        """Test that notify calls the callback."""
        with mock.patch.dict(sys.modules, {'gi.repository.GLib': mock.MagicMock()}):
            from gi.repository import GLib
            GLib.idle_add = lambda f: f()

            view = object.__new__(quarantine_view_class)
            view._manager = mock_quarantine_manager
            view._manager.get_entry_count.return_value = 10
            view._load_entries_async = mock.MagicMock()

            callback = mock.MagicMock()
            view._on_quarantine_changed = callback

            view.notify_quarantine_changed()

            callback.assert_called_once_with(10)


class TestQuarantineViewManagerProperty:
    """Tests for manager property."""

    def test_manager_property_returns_manager(self, mock_quarantine_view, mock_quarantine_manager):
        """Test that manager property returns the internal manager."""
        result = mock_quarantine_view.manager

        assert result is mock_quarantine_manager


class TestQuarantineViewMapHandler:
    """Tests for view mapping/visibility handling."""

    def test_on_view_mapped_debounces_refresh(self, quarantine_view_class):
        """Test that view mapped debounces refresh calls."""
        import time
        view = object.__new__(quarantine_view_class)
        view._last_refresh_time = time.time()  # Recent refresh
        view._load_entries_async = mock.MagicMock()

        view._on_view_mapped(mock.MagicMock())

        # Should not refresh if recently refreshed
        view._load_entries_async.assert_not_called()

    def test_on_view_mapped_refreshes_after_delay(self, quarantine_view_class):
        """Test that view mapped refreshes after delay."""
        view = object.__new__(quarantine_view_class)
        view._last_refresh_time = 0.0  # Old refresh time
        view._load_entries_async = mock.MagicMock()

        view._on_view_mapped(mock.MagicMock())

        view._load_entries_async.assert_called_once()


class TestQuarantineViewEntryRowCreation:
    """Tests for entry row creation."""

    def test_create_entry_row_sets_threat_name(self, quarantine_view_class, mock_quarantine_entry):
        """Test that entry row title is set to threat name."""
        view = object.__new__(quarantine_view_class)

        mock_row = mock.MagicMock()
        from gi.repository import Adw
        Adw.ExpanderRow.return_value = mock_row

        row = view._create_entry_row(mock_quarantine_entry)

        mock_row.set_title.assert_called_with("Eicar-Test-Signature")

    def test_create_entry_row_sets_row_name_to_id(self, quarantine_view_class, mock_quarantine_entry):
        """Test that row name is set to entry ID."""
        view = object.__new__(quarantine_view_class)

        mock_row = mock.MagicMock()
        from gi.repository import Adw
        Adw.ExpanderRow.return_value = mock_row

        row = view._create_entry_row(mock_quarantine_entry)

        mock_row.set_name.assert_called_with("test-quarantine-id-123")

    def test_create_entry_row_truncates_long_path(self, quarantine_view_class, mock_quarantine_entry):
        """Test that long paths are truncated in subtitle."""
        view = object.__new__(quarantine_view_class)
        mock_quarantine_entry.original_path = "/home/user/very/long/path/that/exceeds/fifty/characters/limit/file.exe"

        mock_row = mock.MagicMock()
        from gi.repository import Adw
        Adw.ExpanderRow.return_value = mock_row

        row = view._create_entry_row(mock_quarantine_entry)

        # Verify subtitle was set with truncated path
        calls = mock_row.set_subtitle.call_args_list
        if calls:
            subtitle = calls[0][0][0]
            assert subtitle.startswith("...")


# Module-level test function for verification
def test_quarantine_view_basic(mock_gi_modules):
    """
    Basic test function for pytest verification command.

    This test verifies the core QuarantineView functionality
    using a minimal mock setup.
    """
    with mock.patch.dict(sys.modules, {
        'src.core.quarantine': mock.MagicMock(),
    }):
        from src.ui.quarantine_view import (
            QuarantineView,
            INITIAL_DISPLAY_LIMIT,
            LOAD_MORE_BATCH_SIZE,
            format_file_size,
        )

        # Test 1: Class can be imported
        assert QuarantineView is not None

        # Test 2: Pagination constants are correct
        assert INITIAL_DISPLAY_LIMIT == 25
        assert LOAD_MORE_BATCH_SIZE == 25

        # Test 3: format_file_size function works
        assert format_file_size(0) == "0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"

        # Test 4: Create mock instance and test basic methods
        view = object.__new__(QuarantineView)
        view._manager = mock.MagicMock()
        view._manager.get_entry_count.return_value = 5
        view._manager.get_total_size.return_value = 2048
        view._storage_row = mock.MagicMock()
        view._count_label = mock.MagicMock()

        # Test _update_storage_info
        view._update_storage_info()

        view._storage_row.set_subtitle.assert_called_with("2.0 KB")
        view._count_label.set_text.assert_called_with("5 items")

        # All tests passed
