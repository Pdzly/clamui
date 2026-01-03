# ClamUI TrayIndicator Tests
"""Unit tests for the TrayIndicator class."""

import sys
from unittest import mock

import pytest

# Mock the gi module before importing tray_indicator to avoid GTK version conflicts
# Since TrayIndicator uses GTK3 for AppIndicator menus and the test environment may
# have GTK4 or no GTK at all, we need to mock the dependencies.

# Check if gi module exists
_gi_available = "gi" in sys.modules or True  # We'll mock it anyway

# Create mock modules for GTK3 and AppIndicator
_mock_gtk3 = mock.MagicMock()
_mock_appindicator = mock.MagicMock()
_mock_gi = mock.MagicMock()

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


@pytest.fixture(autouse=True)
def mock_gtk_modules(monkeypatch):
    """Mock GTK modules for all tests."""
    # Store original modules if they exist
    original_modules = {}
    for mod_name in [
        "gi",
        "gi.repository",
        "gi.repository.Gtk",
        "gi.repository.AyatanaAppIndicator3",
    ]:
        if mod_name in sys.modules:
            original_modules[mod_name] = sys.modules[mod_name]

    # Install mocks
    mock_repo = mock.MagicMock()
    mock_repo.Gtk = _mock_gtk3
    mock_repo.AyatanaAppIndicator3 = _mock_appindicator

    monkeypatch.setitem(sys.modules, "gi", _mock_gi)
    monkeypatch.setitem(sys.modules, "gi.repository", mock_repo)

    # Mock require_version to do nothing
    _mock_gi.require_version = mock.MagicMock()

    yield

    # Restore original modules if needed (monkeypatch handles cleanup)


class TestTrayIndicatorModuleFunctions:
    """Tests for module-level functions."""

    def test_is_available_returns_boolean(self, mock_gtk_modules):
        """Test is_available returns a boolean value."""
        # Re-import with mocks in place
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        result = tray_indicator.is_available()
        assert isinstance(result, bool)

    def test_get_unavailable_reason_returns_string_or_none(self, mock_gtk_modules):
        """Test get_unavailable_reason returns string when unavailable."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        result = tray_indicator.get_unavailable_reason()
        if not tray_indicator.is_available():
            assert isinstance(result, str)
            assert len(result) > 0
        else:
            assert result is None


class TestTrayIndicatorClassConstants:
    """Tests for TrayIndicator class constants."""

    def test_icon_map_contains_required_statuses(self, mock_gtk_modules):
        """Test ICON_MAP contains all expected status keys."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)
        TrayIndicator = tray_indicator.TrayIndicator

        required_statuses = ["protected", "warning", "scanning", "threat"]
        for status in required_statuses:
            assert status in TrayIndicator.ICON_MAP
            assert isinstance(TrayIndicator.ICON_MAP[status], str)

    def test_icon_fallbacks_contains_required_statuses(self, mock_gtk_modules):
        """Test ICON_FALLBACKS contains all expected status keys."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)
        TrayIndicator = tray_indicator.TrayIndicator

        required_statuses = ["protected", "warning", "scanning", "threat"]
        for status in required_statuses:
            assert status in TrayIndicator.ICON_FALLBACKS
            assert isinstance(TrayIndicator.ICON_FALLBACKS[status], list)
            assert len(TrayIndicator.ICON_FALLBACKS[status]) > 0

    def test_default_icon_is_defined(self, mock_gtk_modules):
        """Test DEFAULT_ICON is a non-empty string."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)
        TrayIndicator = tray_indicator.TrayIndicator

        assert isinstance(TrayIndicator.DEFAULT_ICON, str)
        assert len(TrayIndicator.DEFAULT_ICON) > 0

    def test_indicator_id_is_defined(self, mock_gtk_modules):
        """Test INDICATOR_ID is a non-empty string."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)
        TrayIndicator = tray_indicator.TrayIndicator

        assert isinstance(TrayIndicator.INDICATOR_ID, str)
        assert len(TrayIndicator.INDICATOR_ID) > 0


class TestTrayIndicatorInit:
    """Tests for TrayIndicator initialization."""

    def test_init_creates_instance(self, mock_gtk_modules):
        """Test TrayIndicator can be instantiated."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        assert indicator is not None

    def test_init_sets_default_status(self, mock_gtk_modules):
        """Test TrayIndicator initializes with 'protected' status."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        assert indicator.current_status == "protected"

    def test_init_callbacks_are_none(self, mock_gtk_modules):
        """Test TrayIndicator initializes with no callbacks set."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        assert indicator._on_quick_scan is None
        assert indicator._on_full_scan is None
        assert indicator._on_update is None
        assert indicator._on_quit is None

    def test_init_window_callbacks_are_none(self, mock_gtk_modules):
        """Test TrayIndicator initializes with no window callbacks set."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        assert indicator._on_window_toggle is None
        assert indicator._get_window_visible is None

    def test_is_library_available_property(self, mock_gtk_modules):
        """Test is_library_available property returns boolean."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        assert isinstance(indicator.is_library_available, bool)


class TestTrayIndicatorUnavailable:
    """Tests for TrayIndicator when AppIndicator is unavailable."""

    def test_unavailable_indicator_can_be_created(self, mock_gtk_modules):
        """Test TrayIndicator can be created when library is unavailable."""
        import importlib

        from src.ui import tray_indicator

        # Force unavailable state
        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        assert indicator is not None
        assert indicator.is_library_available is False

    def test_unavailable_indicator_has_no_internal_indicator(self, mock_gtk_modules):
        """Test unavailable TrayIndicator has no _indicator."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        assert indicator._indicator is None

    def test_unavailable_indicator_has_no_menu(self, mock_gtk_modules):
        """Test unavailable TrayIndicator has no menu."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        assert indicator._menu is None

    def test_unavailable_activate_does_not_crash(self, mock_gtk_modules):
        """Test activate method handles unavailable library gracefully."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        # Should not raise any exception
        indicator.activate()
        assert indicator.is_active is False

    def test_unavailable_deactivate_does_not_crash(self, mock_gtk_modules):
        """Test deactivate method handles unavailable library gracefully."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        # Should not raise any exception
        indicator.deactivate()

    def test_unavailable_update_status_does_not_crash(self, mock_gtk_modules):
        """Test update_status handles unavailable library gracefully."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        # Should not raise any exception
        indicator.update_status("scanning")

    def test_unavailable_update_scan_progress_does_not_crash(self, mock_gtk_modules):
        """Test update_scan_progress handles unavailable library gracefully."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        # Should not raise any exception
        indicator.update_scan_progress(50)

    def test_unavailable_cleanup_does_not_crash(self, mock_gtk_modules):
        """Test cleanup handles unavailable library gracefully."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        # Should not raise any exception
        indicator.cleanup()


class TestTrayIndicatorSetActionCallbacks:
    """Tests for TrayIndicator.set_action_callbacks method."""

    def test_set_action_callbacks_stores_callbacks(self, mock_gtk_modules):
        """Test set_action_callbacks stores the callback references."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        quick_scan = mock.Mock()
        full_scan = mock.Mock()
        update = mock.Mock()
        quit_cb = mock.Mock()

        indicator.set_action_callbacks(
            on_quick_scan=quick_scan, on_full_scan=full_scan, on_update=update, on_quit=quit_cb
        )

        assert indicator._on_quick_scan is quick_scan
        assert indicator._on_full_scan is full_scan
        assert indicator._on_update is update
        assert indicator._on_quit is quit_cb

    def test_set_action_callbacks_partial(self, mock_gtk_modules):
        """Test set_action_callbacks with partial callbacks."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        quick_scan = mock.Mock()

        indicator.set_action_callbacks(on_quick_scan=quick_scan)

        assert indicator._on_quick_scan is quick_scan
        assert indicator._on_full_scan is None
        assert indicator._on_update is None
        assert indicator._on_quit is None

    def test_set_action_callbacks_can_be_updated(self, mock_gtk_modules):
        """Test set_action_callbacks can update existing callbacks."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        callback1 = mock.Mock()
        callback2 = mock.Mock()

        indicator.set_action_callbacks(on_quick_scan=callback1)
        assert indicator._on_quick_scan is callback1

        indicator.set_action_callbacks(on_quick_scan=callback2)
        assert indicator._on_quick_scan is callback2


class TestTrayIndicatorSetWindowToggleCallback:
    """Tests for TrayIndicator.set_window_toggle_callback method."""

    def test_set_window_toggle_callback_stores_callbacks(self, mock_gtk_modules):
        """Test set_window_toggle_callback stores both callbacks."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        toggle_cb = mock.Mock()
        visible_cb = mock.Mock(return_value=True)

        indicator.set_window_toggle_callback(toggle_cb, visible_cb)

        assert indicator._on_window_toggle is toggle_cb
        assert indicator._get_window_visible is visible_cb

    def test_set_window_toggle_callback_can_be_updated(self, mock_gtk_modules):
        """Test set_window_toggle_callback can update callbacks."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        toggle1 = mock.Mock()
        visible1 = mock.Mock(return_value=True)
        toggle2 = mock.Mock()
        visible2 = mock.Mock(return_value=False)

        indicator.set_window_toggle_callback(toggle1, visible1)
        assert indicator._on_window_toggle is toggle1

        indicator.set_window_toggle_callback(toggle2, visible2)
        assert indicator._on_window_toggle is toggle2
        assert indicator._get_window_visible is visible2


class TestTrayIndicatorMenuCallbacks:
    """Tests for TrayIndicator menu callback handlers."""

    def test_quick_scan_callback_invoked(self, mock_gtk_modules):
        """Test _on_quick_scan_clicked invokes the callback."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        callback = mock.Mock()
        indicator.set_action_callbacks(on_quick_scan=callback)

        indicator._on_quick_scan_clicked(None)

        callback.assert_called_once()

    def test_quick_scan_callback_not_set_logs_warning(self, mock_gtk_modules):
        """Test _on_quick_scan_clicked handles missing callback."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        # Should not raise, just log warning
        indicator._on_quick_scan_clicked(None)

    def test_full_scan_callback_invoked(self, mock_gtk_modules):
        """Test _on_full_scan_clicked invokes the callback."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        callback = mock.Mock()
        indicator.set_action_callbacks(on_full_scan=callback)

        indicator._on_full_scan_clicked(None)

        callback.assert_called_once()

    def test_update_callback_invoked(self, mock_gtk_modules):
        """Test _on_update_clicked invokes the callback."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        callback = mock.Mock()
        indicator.set_action_callbacks(on_update=callback)

        indicator._on_update_clicked(None)

        callback.assert_called_once()

    def test_quit_callback_invoked(self, mock_gtk_modules):
        """Test _on_quit_clicked invokes the callback."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        callback = mock.Mock()
        indicator.set_action_callbacks(on_quit=callback)

        indicator._on_quit_clicked(None)

        callback.assert_called_once()

    def test_window_toggle_callback_invoked(self, mock_gtk_modules):
        """Test _on_window_toggle_clicked invokes the callback."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        toggle_cb = mock.Mock()
        visible_cb = mock.Mock(return_value=True)
        indicator.set_window_toggle_callback(toggle_cb, visible_cb)

        indicator._on_window_toggle_clicked(None)

        toggle_cb.assert_called_once()

    def test_window_toggle_callback_not_set_logs_warning(self, mock_gtk_modules):
        """Test _on_window_toggle_clicked handles missing callback."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        # Should not raise, just log warning
        indicator._on_window_toggle_clicked(None)


class TestTrayIndicatorProperties:
    """Tests for TrayIndicator properties."""

    def test_current_status_initial_value(self, mock_gtk_modules):
        """Test current_status returns initial 'protected' status."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        assert indicator.current_status == "protected"

    def test_is_active_false_when_unavailable(self, mock_gtk_modules):
        """Test is_active returns False when library unavailable."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        assert indicator.is_active is False


class TestTrayIndicatorCleanup:
    """Tests for TrayIndicator.cleanup method."""

    def test_cleanup_clears_action_callbacks(self, mock_gtk_modules):
        """Test cleanup clears all action callbacks."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        indicator.set_action_callbacks(
            on_quick_scan=mock.Mock(),
            on_full_scan=mock.Mock(),
            on_update=mock.Mock(),
            on_quit=mock.Mock(),
        )

        indicator.cleanup()

        assert indicator._on_quick_scan is None
        assert indicator._on_full_scan is None
        assert indicator._on_update is None
        assert indicator._on_quit is None

    def test_cleanup_clears_window_callbacks(self, mock_gtk_modules):
        """Test cleanup clears window toggle callbacks."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        indicator.set_window_toggle_callback(mock.Mock(), mock.Mock())

        indicator.cleanup()

        assert indicator._on_window_toggle is None
        assert indicator._get_window_visible is None

    def test_cleanup_clears_internal_references(self, mock_gtk_modules):
        """Test cleanup clears internal GTK references."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        indicator.cleanup()

        assert indicator._menu is None
        assert indicator._indicator is None
        assert indicator._icon_theme is None
        assert indicator._show_window_item is None

    def test_cleanup_can_be_called_multiple_times(self, mock_gtk_modules):
        """Test cleanup can be safely called multiple times."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        # Should not raise on multiple calls
        indicator.cleanup()
        indicator.cleanup()
        indicator.cleanup()


class TestTrayIndicatorUpdateWindowMenuLabel:
    """Tests for TrayIndicator.update_window_menu_label method."""

    def test_update_window_menu_label_without_item(self, mock_gtk_modules):
        """Test update_window_menu_label handles missing menu item."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        indicator._show_window_item = None

        # Should not raise
        indicator.update_window_menu_label()

    def test_update_window_menu_label_without_callback(self, mock_gtk_modules):
        """Test update_window_menu_label handles missing callback."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        mock_item = mock.Mock()
        indicator._show_window_item = mock_item
        indicator._get_window_visible = None

        # Should not raise, should show "Show Window" as default
        indicator.update_window_menu_label()
        mock_item.set_label.assert_called_once_with("Show Window")

    def test_update_window_menu_label_shows_hide_when_visible(self, mock_gtk_modules):
        """Test update_window_menu_label sets 'Hide Window' when visible."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        mock_item = mock.Mock()
        indicator._show_window_item = mock_item
        indicator._get_window_visible = mock.Mock(return_value=True)

        indicator.update_window_menu_label()

        mock_item.set_label.assert_called_once_with("Hide Window")

    def test_update_window_menu_label_shows_show_when_hidden(self, mock_gtk_modules):
        """Test update_window_menu_label sets 'Show Window' when hidden."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        mock_item = mock.Mock()
        indicator._show_window_item = mock_item
        indicator._get_window_visible = mock.Mock(return_value=False)

        indicator.update_window_menu_label()

        mock_item.set_label.assert_called_once_with("Show Window")


class TestTrayIndicatorActivateDeactivate:
    """Tests for TrayIndicator activate/deactivate methods."""

    def test_activate_with_no_indicator(self, mock_gtk_modules):
        """Test activate handles missing indicator gracefully."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        indicator._indicator = None

        # Should not raise
        indicator.activate()

    def test_deactivate_with_no_indicator(self, mock_gtk_modules):
        """Test deactivate handles missing indicator gracefully."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        indicator._indicator = None

        # Should not raise
        indicator.deactivate()


class TestTrayIndicatorUpdateStatus:
    """Tests for TrayIndicator.update_status method."""

    def test_update_status_with_no_indicator(self, mock_gtk_modules):
        """Test update_status handles missing indicator gracefully."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        indicator._indicator = None

        # Should not raise
        indicator.update_status("scanning")

    def test_update_status_unknown_status_defaults_to_protected(self, mock_gtk_modules):
        """Test update_status uses 'protected' for unknown status."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        mock_indicator = mock.Mock()
        indicator._indicator = mock_indicator
        indicator._available = True

        # Mock _get_clamui_icon to return None so _resolve_icon path is taken
        with mock.patch.object(indicator, "_get_clamui_icon", return_value=None):
            with mock.patch.object(
                indicator, "_resolve_icon", return_value="security-high-symbolic"
            ) as mock_resolve:
                indicator.update_status("unknown_status")
                # Should be called with 'protected' after falling back
                mock_resolve.assert_called_with("protected")

    def test_update_status_valid_statuses(self, mock_gtk_modules):
        """Test update_status accepts all valid statuses."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        mock_indicator = mock.Mock()
        indicator._indicator = mock_indicator
        indicator._available = True

        valid_statuses = ["protected", "warning", "scanning", "threat"]

        # Mock _get_clamui_icon to return None so theme icon path is taken
        with mock.patch.object(indicator, "_get_clamui_icon", return_value=None):
            for status in valid_statuses:
                with mock.patch.object(indicator, "_resolve_icon", return_value="icon-name"):
                    indicator.update_status(status)
                    assert indicator._current_status == status


class TestTrayIndicatorUpdateScanProgress:
    """Tests for TrayIndicator.update_scan_progress method."""

    def test_update_scan_progress_with_no_indicator(self, mock_gtk_modules):
        """Test update_scan_progress handles missing indicator gracefully."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        indicator._indicator = None

        # Should not raise
        indicator.update_scan_progress(50)

    def test_update_scan_progress_sets_label(self, mock_gtk_modules):
        """Test update_scan_progress sets percentage label."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        mock_indicator = mock.Mock()
        indicator._indicator = mock_indicator
        indicator._available = True
        indicator._current_status = "protected"

        with mock.patch.object(indicator, "update_status"):
            indicator.update_scan_progress(75)

            mock_indicator.set_label.assert_called_once_with("75%", "")

    def test_update_scan_progress_zero_clears_label(self, mock_gtk_modules):
        """Test update_scan_progress with 0 clears the label."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        mock_indicator = mock.Mock()
        indicator._indicator = mock_indicator

        indicator.update_scan_progress(0)

        mock_indicator.set_label.assert_called_once_with("", "")

    def test_update_scan_progress_negative_clears_label(self, mock_gtk_modules):
        """Test update_scan_progress with negative value clears the label."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        mock_indicator = mock.Mock()
        indicator._indicator = mock_indicator

        indicator.update_scan_progress(-1)

        mock_indicator.set_label.assert_called_once_with("", "")

    def test_update_scan_progress_updates_status_to_scanning(self, mock_gtk_modules):
        """Test update_scan_progress changes status to scanning."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        mock_indicator = mock.Mock()
        indicator._indicator = mock_indicator
        indicator._available = True
        indicator._current_status = "protected"

        with mock.patch.object(indicator, "update_status") as mock_update:
            indicator.update_scan_progress(50)

            mock_update.assert_called_once_with("scanning")


class TestTrayIndicatorIconResolution:
    """Tests for TrayIndicator icon resolution methods."""

    def test_icon_exists_returns_false_when_unavailable(self, mock_gtk_modules):
        """Test _icon_exists returns False when library unavailable."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        result = indicator._icon_exists("some-icon")

        assert result is False

    def test_get_icon_theme_returns_none_when_unavailable(self, mock_gtk_modules):
        """Test _get_icon_theme returns None when library unavailable."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        result = indicator._get_icon_theme()

        assert result is None

    def test_resolve_icon_returns_default_for_unknown_status(self, mock_gtk_modules):
        """Test _resolve_icon returns default icon for unknown status."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()
        indicator._available = True

        # Mock _icon_exists to return True for default icon
        with mock.patch.object(indicator, "_icon_exists", return_value=True):
            result = indicator._resolve_icon("unknown_status")

            assert result == tray_indicator.TrayIndicator.DEFAULT_ICON

    def test_resolve_icon_uses_fallback_chain(self, mock_gtk_modules):
        """Test _resolve_icon walks through fallback chain."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)
        TrayIndicator = tray_indicator.TrayIndicator

        indicator = TrayIndicator()
        indicator._available = True

        # First two icons don't exist, third does
        exists_map = {
            TrayIndicator.ICON_FALLBACKS["protected"][0]: False,
            TrayIndicator.ICON_FALLBACKS["protected"][1]: False,
            TrayIndicator.ICON_FALLBACKS["protected"][2]: True,
        }

        def mock_exists(icon_name):
            return exists_map.get(icon_name, False)

        with mock.patch.object(indicator, "_icon_exists", side_effect=mock_exists):
            result = indicator._resolve_icon("protected")

            assert result == TrayIndicator.ICON_FALLBACKS["protected"][2]


class TestTrayIndicatorIntegration:
    """Integration tests for TrayIndicator with mocked AppIndicator."""

    def test_full_lifecycle_unavailable(self, mock_gtk_modules):
        """Test complete lifecycle when library is unavailable."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()

        # Set callbacks
        indicator.set_action_callbacks(
            on_quick_scan=mock.Mock(),
            on_full_scan=mock.Mock(),
            on_update=mock.Mock(),
            on_quit=mock.Mock(),
        )
        indicator.set_window_toggle_callback(mock.Mock(), mock.Mock())

        # Lifecycle operations should all be safe
        indicator.activate()
        indicator.update_status("scanning")
        indicator.update_scan_progress(50)
        indicator.update_window_menu_label()
        indicator.deactivate()
        indicator.cleanup()

        # Verify final state
        assert indicator._on_quick_scan is None
        assert indicator._indicator is None

    def test_callback_invocation_chain(self, mock_gtk_modules):
        """Test that callbacks are properly invoked through menu handlers."""
        import importlib

        from src.ui import tray_indicator

        importlib.reload(tray_indicator)

        indicator = tray_indicator.TrayIndicator()

        # Track callback invocations
        invocations = []

        def make_callback(name):
            def callback():
                invocations.append(name)

            return callback

        indicator.set_action_callbacks(
            on_quick_scan=make_callback("quick"),
            on_full_scan=make_callback("full"),
            on_update=make_callback("update"),
            on_quit=make_callback("quit"),
        )
        indicator.set_window_toggle_callback(make_callback("toggle"), mock.Mock(return_value=True))

        # Trigger all menu handlers
        indicator._on_quick_scan_clicked(None)
        indicator._on_full_scan_clicked(None)
        indicator._on_update_clicked(None)
        indicator._on_quit_clicked(None)
        indicator._on_window_toggle_clicked(None)

        assert invocations == ["quick", "full", "update", "quit", "toggle"]


class TestTrayIndicatorBuildMenu:
    """Tests for TrayIndicator._build_menu method."""

    def test_build_menu_returns_none_when_unavailable(self, mock_gtk_modules):
        """Test _build_menu returns None when library unavailable."""
        import importlib

        from src.ui import tray_indicator

        tray_indicator._APPINDICATOR_AVAILABLE = False
        importlib.reload(tray_indicator)
        tray_indicator._APPINDICATOR_AVAILABLE = False

        indicator = tray_indicator.TrayIndicator()
        result = indicator._build_menu()

        assert result is None
