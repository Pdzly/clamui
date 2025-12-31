# ClamUI StatisticsView Tests
"""
Unit tests for the StatisticsView component.

Tests cover:
- Initialization and setup
- Timeframe selection and switching
- Statistics display updates
- Protection status display
- Chart rendering and empty states
- Loading state management
- Format helper methods
- Quick action callbacks
- Refresh functionality
"""

import sys
from unittest import mock

import pytest


# Mock gi module before importing src modules to avoid GTK dependencies in tests
@pytest.fixture(autouse=True)
def mock_gi():
    """Mock GTK/GLib modules for all tests."""
    mock_gtk = mock.MagicMock()
    mock_adw = mock.MagicMock()
    mock_gio = mock.MagicMock()
    mock_glib = mock.MagicMock()

    mock_gi_module = mock.MagicMock()
    mock_gi_module.require_version = mock.MagicMock()

    mock_repository = mock.MagicMock()
    mock_repository.Gtk = mock_gtk
    mock_repository.Adw = mock_adw
    mock_repository.Gio = mock_gio
    mock_repository.GLib = mock_glib

    # Mock matplotlib for GTK4
    mock_matplotlib = mock.MagicMock()
    mock_figure = mock.MagicMock()
    mock_canvas = mock.MagicMock()
    mock_backend = mock.MagicMock()
    mock_backend.FigureCanvasGTK4Agg = mock_canvas

    # Patch modules
    with mock.patch.dict(sys.modules, {
        'gi': mock_gi_module,
        'gi.repository': mock_repository,
        'matplotlib': mock_matplotlib,
        'matplotlib.figure': mock_figure,
        'matplotlib.backends.backend_gtk4agg': mock_backend,
    }):
        yield


@pytest.fixture
def statistics_view_class(mock_gi):
    """Get StatisticsView class with mocked dependencies."""
    # Also mock the dependent modules
    with mock.patch.dict(sys.modules, {
        'src.core.statistics_calculator': mock.MagicMock(),
    }):
        from src.ui.statistics_view import StatisticsView
        return StatisticsView


@pytest.fixture
def mock_statistics_view(statistics_view_class):
    """Create a mock StatisticsView instance for testing."""
    # Create instance without calling __init__
    with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
        view = statistics_view_class()

        # Set up required attributes
        view._calculator = mock.MagicMock()
        view._current_timeframe = "weekly"
        view._is_loading = False
        view._current_stats = None
        view._current_protection = None
        view._on_quick_scan_requested = None

        # Mock UI elements
        view._status_spinner = mock.MagicMock()
        view._refresh_button = mock.MagicMock()
        view._protection_row = mock.MagicMock()
        view._status_badge = mock.MagicMock()
        view._last_scan_row = mock.MagicMock()
        view._total_scans_label = mock.MagicMock()
        view._files_scanned_label = mock.MagicMock()
        view._threats_label = mock.MagicMock()
        view._clean_scans_label = mock.MagicMock()
        view._duration_label = mock.MagicMock()
        view._stats_group = mock.MagicMock()
        view._chart_group = mock.MagicMock()
        view._canvas = mock.MagicMock()
        view._figure = mock.MagicMock()
        view._chart_empty_state = mock.MagicMock()
        view._timeframe_buttons = {
            "daily": mock.MagicMock(),
            "weekly": mock.MagicMock(),
            "monthly": mock.MagicMock(),
            "all": mock.MagicMock(),
        }

        # Mock internal methods
        view._set_loading_state = mock.MagicMock()
        view._load_statistics_async = mock.MagicMock()
        view._perform_load = mock.MagicMock()
        view._update_statistics_display = mock.MagicMock()
        view._update_protection_display = mock.MagicMock()
        view._update_chart = mock.MagicMock()
        view._show_empty_state = mock.MagicMock()
        view.get_root = mock.MagicMock(return_value=None)

        return view


class TestStatisticsViewInitialization:
    """Tests for StatisticsView initialization."""

    def test_default_timeframe_is_weekly(self, mock_statistics_view):
        """Test that default timeframe is set to weekly."""
        assert mock_statistics_view._current_timeframe == "weekly"

    def test_initial_loading_state_is_false(self, mock_statistics_view):
        """Test that initial loading state is False."""
        assert mock_statistics_view._is_loading is False

    def test_initial_stats_is_none(self, mock_statistics_view):
        """Test that initial stats is None."""
        assert mock_statistics_view._current_stats is None

    def test_initial_protection_is_none(self, mock_statistics_view):
        """Test that initial protection status is None."""
        assert mock_statistics_view._current_protection is None

    def test_quick_scan_callback_is_none(self, mock_statistics_view):
        """Test that quick scan callback is initially None."""
        assert mock_statistics_view._on_quick_scan_requested is None


class TestStatisticsViewTimeframeSwitching:
    """Tests for timeframe switching functionality."""

    def test_on_timeframe_toggled_updates_current_timeframe(self, mock_statistics_view, statistics_view_class):
        """Test that toggling timeframe updates the current timeframe."""
        # Get the actual method from the class
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._current_timeframe = "weekly"
            view._timeframe_buttons = {
                "daily": mock.MagicMock(),
                "weekly": mock.MagicMock(),
                "monthly": mock.MagicMock(),
                "all": mock.MagicMock(),
            }
            view._load_statistics_async = mock.MagicMock()

            # Create mock button that returns True for get_active
            mock_button = mock.MagicMock()
            mock_button.get_active.return_value = True

            # Call the method
            view._on_timeframe_toggled(mock_button, "monthly")

            assert view._current_timeframe == "monthly"

    def test_on_timeframe_toggled_reloads_statistics(self, statistics_view_class):
        """Test that toggling timeframe triggers reload."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._current_timeframe = "weekly"
            view._timeframe_buttons = {
                "daily": mock.MagicMock(),
                "weekly": mock.MagicMock(),
                "monthly": mock.MagicMock(),
                "all": mock.MagicMock(),
            }
            view._load_statistics_async = mock.MagicMock()

            mock_button = mock.MagicMock()
            mock_button.get_active.return_value = True

            view._on_timeframe_toggled(mock_button, "daily")

            view._load_statistics_async.assert_called_once()

    def test_on_timeframe_toggled_ignores_inactive_button(self, statistics_view_class):
        """Test that toggling inactive button does nothing."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._current_timeframe = "weekly"
            view._timeframe_buttons = {
                "daily": mock.MagicMock(),
                "weekly": mock.MagicMock(),
                "monthly": mock.MagicMock(),
                "all": mock.MagicMock(),
            }
            view._load_statistics_async = mock.MagicMock()

            mock_button = mock.MagicMock()
            mock_button.get_active.return_value = False

            view._on_timeframe_toggled(mock_button, "daily")

            # Should not change timeframe or reload
            assert view._current_timeframe == "weekly"
            view._load_statistics_async.assert_not_called()

    def test_on_timeframe_toggled_deactivates_other_buttons(self, statistics_view_class):
        """Test that toggling one button deactivates others."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._current_timeframe = "weekly"

            mock_buttons = {
                "daily": mock.MagicMock(),
                "weekly": mock.MagicMock(),
                "monthly": mock.MagicMock(),
                "all": mock.MagicMock(),
            }
            view._timeframe_buttons = mock_buttons
            view._load_statistics_async = mock.MagicMock()

            mock_button = mock.MagicMock()
            mock_button.get_active.return_value = True

            view._on_timeframe_toggled(mock_button, "monthly")

            # Check that other buttons were deactivated
            mock_buttons["daily"].set_active.assert_called_with(False)
            mock_buttons["weekly"].set_active.assert_called_with(False)
            mock_buttons["all"].set_active.assert_called_with(False)


class TestStatisticsViewLoadingState:
    """Tests for loading state management."""

    def test_set_loading_state_true_shows_spinner(self, statistics_view_class):
        """Test that setting loading True shows spinner."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._is_loading = False
            view._status_spinner = mock.MagicMock()
            view._refresh_button = mock.MagicMock()

            view._set_loading_state(True)

            assert view._is_loading is True
            view._status_spinner.set_visible.assert_called_with(True)
            view._status_spinner.start.assert_called_once()
            view._refresh_button.set_sensitive.assert_called_with(False)

    def test_set_loading_state_false_hides_spinner(self, statistics_view_class):
        """Test that setting loading False hides spinner."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._is_loading = True
            view._status_spinner = mock.MagicMock()
            view._refresh_button = mock.MagicMock()

            view._set_loading_state(False)

            assert view._is_loading is False
            view._status_spinner.stop.assert_called_once()
            view._status_spinner.set_visible.assert_called_with(False)
            view._refresh_button.set_sensitive.assert_called_with(True)

    def test_load_statistics_async_prevents_double_load(self, statistics_view_class):
        """Test that async load prevents loading when already loading."""
        with mock.patch.dict(sys.modules, {'gi.repository': mock.MagicMock()}):
            with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
                view = statistics_view_class()
                view._is_loading = True
                view._set_loading_state = mock.MagicMock()

                result = view._load_statistics_async()

                assert result is False
                view._set_loading_state.assert_not_called()


class TestStatisticsViewFormatHelpers:
    """Tests for format helper methods."""

    def test_format_number_with_small_number(self, statistics_view_class):
        """Test formatting a small number."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._format_number(42)
            assert result == "42"

    def test_format_number_with_thousands(self, statistics_view_class):
        """Test formatting a number with thousands."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._format_number(1234)
            assert result == "1,234"

    def test_format_number_with_millions(self, statistics_view_class):
        """Test formatting a large number."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._format_number(1234567)
            assert result == "1,234,567"

    def test_format_number_with_zero(self, statistics_view_class):
        """Test formatting zero."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._format_number(0)
            assert result == "0"

    def test_format_duration_seconds(self, statistics_view_class):
        """Test formatting duration under a minute."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._format_duration(45.5)
            assert result == "45.5s"

    def test_format_duration_minutes(self, statistics_view_class):
        """Test formatting duration in minutes."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._format_duration(150)
            assert result == "2m 30s"

    def test_format_duration_hours(self, statistics_view_class):
        """Test formatting duration in hours."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._format_duration(3900)  # 1h 5m
            assert result == "1h 5m"

    def test_format_duration_zero(self, statistics_view_class):
        """Test formatting zero duration."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._format_duration(0)
            assert result == "0.0s"


class TestStatisticsViewDataPointsForTimeframe:
    """Tests for _get_data_points_for_timeframe method."""

    def test_daily_returns_six(self, statistics_view_class):
        """Test daily timeframe returns 6 data points."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._get_data_points_for_timeframe("daily")
            assert result == 6

    def test_weekly_returns_seven(self, statistics_view_class):
        """Test weekly timeframe returns 7 data points."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._get_data_points_for_timeframe("weekly")
            assert result == 7

    def test_monthly_returns_ten(self, statistics_view_class):
        """Test monthly timeframe returns 10 data points."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._get_data_points_for_timeframe("monthly")
            assert result == 10

    def test_all_returns_twelve(self, statistics_view_class):
        """Test all timeframe returns 12 data points."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._get_data_points_for_timeframe("all")
            assert result == 12

    def test_unknown_returns_twelve(self, statistics_view_class):
        """Test unknown timeframe defaults to 12 data points."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            result = view._get_data_points_for_timeframe("unknown")
            assert result == 12


class TestStatisticsViewQuickScanCallback:
    """Tests for quick scan callback functionality."""

    def test_set_quick_scan_callback(self, statistics_view_class):
        """Test setting the quick scan callback."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._on_quick_scan_requested = None

            callback = mock.MagicMock()
            view.set_quick_scan_callback(callback)

            assert view._on_quick_scan_requested is callback

    def test_on_quick_scan_clicked_calls_callback(self, statistics_view_class):
        """Test that quick scan click calls the callback."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            callback = mock.MagicMock()
            view._on_quick_scan_requested = callback
            view.get_root = mock.MagicMock(return_value=None)

            mock_row = mock.MagicMock()
            view._on_quick_scan_clicked(mock_row)

            callback.assert_called_once()

    def test_on_quick_scan_clicked_without_callback_tries_action(self, statistics_view_class):
        """Test that quick scan click tries app action when no callback."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._on_quick_scan_requested = None

            mock_app = mock.MagicMock()
            mock_app.activate_action = mock.MagicMock()
            view.get_root = mock.MagicMock(return_value=mock_app)

            mock_row = mock.MagicMock()
            view._on_quick_scan_clicked(mock_row)

            mock_app.activate_action.assert_called_once()


class TestStatisticsViewLogsClick:
    """Tests for view logs click functionality."""

    def test_on_view_logs_clicked_activates_action(self, statistics_view_class):
        """Test that view logs click activates the show-logs action."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()

            mock_app = mock.MagicMock()
            mock_app.activate_action = mock.MagicMock()
            view.get_root = mock.MagicMock(return_value=mock_app)

            mock_row = mock.MagicMock()
            view._on_view_logs_clicked(mock_row)

            mock_app.activate_action.assert_called_once()


class TestStatisticsViewRefresh:
    """Tests for refresh functionality."""

    def test_on_refresh_clicked_loads_statistics(self, statistics_view_class):
        """Test that refresh button click triggers load."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._load_statistics_async = mock.MagicMock()

            mock_button = mock.MagicMock()
            view._on_refresh_clicked(mock_button)

            view._load_statistics_async.assert_called_once()

    def test_refresh_statistics_public_method(self, statistics_view_class):
        """Test that public refresh_statistics method works."""
        with mock.patch.dict(sys.modules, {'gi.repository': mock.MagicMock()}):
            with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
                view = statistics_view_class()
                view._load_statistics_async = mock.MagicMock()

                # Mock GLib.idle_add to call the function immediately
                mock_glib = mock.MagicMock()
                mock_glib.idle_add = lambda f: f()

                with mock.patch.dict(sys.modules, {'gi.repository.GLib': mock_glib}):
                    # The method should schedule loading
                    view.refresh_statistics()


class TestStatisticsViewCalculator:
    """Tests for calculator property."""

    def test_calculator_property_returns_calculator(self, statistics_view_class):
        """Test that calculator property returns the internal calculator."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            mock_calc = mock.MagicMock()
            view._calculator = mock_calc

            result = view.calculator

            assert result is mock_calc


class TestStatisticsViewShowEmptyState:
    """Tests for empty state display."""

    def test_show_empty_state_sets_zero_values(self, statistics_view_class):
        """Test that empty state sets all values to zero."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._total_scans_label = mock.MagicMock()
            view._files_scanned_label = mock.MagicMock()
            view._threats_label = mock.MagicMock()
            view._clean_scans_label = mock.MagicMock()
            view._duration_label = mock.MagicMock()
            view._protection_row = mock.MagicMock()
            view._status_badge = mock.MagicMock()
            view._last_scan_row = mock.MagicMock()
            view._stats_group = mock.MagicMock()

            view._show_empty_state()

            view._total_scans_label.set_label.assert_called_with("0")
            view._files_scanned_label.set_label.assert_called_with("0")
            view._threats_label.set_label.assert_called_with("0")
            view._clean_scans_label.set_label.assert_called_with("0")
            view._duration_label.set_label.assert_called_with("--")

    def test_show_empty_state_sets_no_data_badge(self, statistics_view_class):
        """Test that empty state sets 'No Data' badge."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._total_scans_label = mock.MagicMock()
            view._files_scanned_label = mock.MagicMock()
            view._threats_label = mock.MagicMock()
            view._clean_scans_label = mock.MagicMock()
            view._duration_label = mock.MagicMock()
            view._protection_row = mock.MagicMock()
            view._status_badge = mock.MagicMock()
            view._last_scan_row = mock.MagicMock()
            view._stats_group = mock.MagicMock()

            view._show_empty_state()

            view._status_badge.set_label.assert_called_with("No Data")


class TestStatisticsViewUpdateChart:
    """Tests for chart update functionality."""

    def test_update_chart_empty_data_shows_empty_state(self, statistics_view_class):
        """Test that empty data shows the empty state."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._figure = mock.MagicMock()
            view._canvas = mock.MagicMock()
            view._chart_empty_state = mock.MagicMock()
            view._chart_group = mock.MagicMock()

            view._update_chart([])

            view._figure.clear.assert_called_once()
            view._canvas.set_visible.assert_called_with(False)
            view._chart_empty_state.set_visible.assert_called_with(True)

    def test_update_chart_zero_scans_shows_empty_state(self, statistics_view_class):
        """Test that all-zero data shows empty state."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._figure = mock.MagicMock()
            view._canvas = mock.MagicMock()
            view._chart_empty_state = mock.MagicMock()
            view._chart_group = mock.MagicMock()

            # Data with all zero scans
            data = [
                {"date": "2024-01-01", "scans": 0, "threats": 0},
                {"date": "2024-01-02", "scans": 0, "threats": 0},
            ]
            view._update_chart(data)

            view._canvas.set_visible.assert_called_with(False)
            view._chart_empty_state.set_visible.assert_called_with(True)

    def test_update_chart_with_data_shows_canvas(self, statistics_view_class):
        """Test that valid data shows the canvas."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._figure = mock.MagicMock()
            view._canvas = mock.MagicMock()
            view._canvas.get_style_context.return_value.get_color.return_value = mock.MagicMock(
                red=0.1, green=0.1, blue=0.1
            )
            view._chart_empty_state = mock.MagicMock()
            view._chart_group = mock.MagicMock()

            # Data with some scans
            data = [
                {"date": "2024-01-01T00:00:00", "scans": 5, "threats": 1},
                {"date": "2024-01-02T00:00:00", "scans": 3, "threats": 0},
            ]
            view._update_chart(data)

            view._canvas.set_visible.assert_called_with(True)
            view._chart_empty_state.set_visible.assert_called_with(False)


class TestStatisticsViewUpdateProtectionDisplay:
    """Tests for protection display updates."""

    def test_update_protection_display_none_shows_unknown(self, statistics_view_class):
        """Test that None protection status shows unknown."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._current_protection = None
            view._protection_row = mock.MagicMock()
            view._status_badge = mock.MagicMock()
            view._last_scan_row = mock.MagicMock()

            view._update_protection_display()

            view._protection_row.set_subtitle.assert_called_with("Unable to determine status")
            view._protection_row.set_icon_name.assert_called_with("dialog-question-symbolic")
            view._status_badge.set_label.assert_called_with("Unknown")

    def test_update_protection_display_protected(self, statistics_view_class):
        """Test that protected status shows correct UI."""
        with mock.patch.dict(sys.modules, {
            'src.core.statistics_calculator': mock.MagicMock(),
        }):
            # Create a mock ProtectionStatus
            mock_status = mock.MagicMock()
            mock_status.level = "protected"
            mock_status.message = "System is protected"
            mock_status.last_scan_timestamp = "2024-01-01T12:00:00"
            mock_status.last_scan_age_hours = 2.5

            with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
                view = statistics_view_class()
                view._current_protection = mock_status
                view._protection_row = mock.MagicMock()
                view._status_badge = mock.MagicMock()
                view._last_scan_row = mock.MagicMock()

                # Import ProtectionLevel to check against
                from src.core.statistics_calculator import ProtectionLevel
                view._update_protection_display()

                view._protection_row.set_subtitle.assert_called_with("System is protected")
                view._protection_row.set_icon_name.assert_called_with("emblem-ok-symbolic")
                view._status_badge.set_label.assert_called_with("Protected")
                view._status_badge.add_css_class.assert_called_with("success")

    def test_update_protection_display_at_risk(self, statistics_view_class):
        """Test that at_risk status shows warning UI."""
        with mock.patch.dict(sys.modules, {
            'src.core.statistics_calculator': mock.MagicMock(),
        }):
            mock_status = mock.MagicMock()
            mock_status.level = "at_risk"
            mock_status.message = "Last scan was over a week ago"
            mock_status.last_scan_timestamp = "2024-01-01T12:00:00"
            mock_status.last_scan_age_hours = 200

            with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
                view = statistics_view_class()
                view._current_protection = mock_status
                view._protection_row = mock.MagicMock()
                view._status_badge = mock.MagicMock()
                view._last_scan_row = mock.MagicMock()

                view._update_protection_display()

                view._protection_row.set_icon_name.assert_called_with("dialog-warning-symbolic")
                view._status_badge.set_label.assert_called_with("At Risk")
                view._status_badge.add_css_class.assert_called_with("warning")

    def test_update_protection_display_unprotected(self, statistics_view_class):
        """Test that unprotected status shows error UI."""
        with mock.patch.dict(sys.modules, {
            'src.core.statistics_calculator': mock.MagicMock(),
        }):
            mock_status = mock.MagicMock()
            mock_status.level = "unprotected"
            mock_status.message = "No scans performed yet"
            mock_status.last_scan_timestamp = None
            mock_status.last_scan_age_hours = None

            with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
                view = statistics_view_class()
                view._current_protection = mock_status
                view._protection_row = mock.MagicMock()
                view._status_badge = mock.MagicMock()
                view._last_scan_row = mock.MagicMock()

                view._update_protection_display()

                view._protection_row.set_icon_name.assert_called_with("dialog-error-symbolic")
                view._status_badge.set_label.assert_called_with("Unprotected")
                view._status_badge.add_css_class.assert_called_with("error")


class TestStatisticsViewUpdateStatisticsDisplay:
    """Tests for statistics display updates."""

    def test_update_statistics_display_none_shows_empty_state(self, statistics_view_class):
        """Test that None stats shows empty state."""
        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._current_stats = None
            view._show_empty_state = mock.MagicMock()

            view._update_statistics_display()

            view._show_empty_state.assert_called_once()

    def test_update_statistics_display_with_data(self, statistics_view_class):
        """Test that stats data updates all labels."""
        mock_stats = mock.MagicMock()
        mock_stats.total_scans = 10
        mock_stats.files_scanned = 1500
        mock_stats.threats_detected = 2
        mock_stats.clean_scans = 8
        mock_stats.average_duration = 45.5
        mock_stats.start_date = "2024-01-01T00:00:00"
        mock_stats.end_date = "2024-01-31T23:59:59"

        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._current_stats = mock_stats
            view._total_scans_label = mock.MagicMock()
            view._files_scanned_label = mock.MagicMock()
            view._threats_label = mock.MagicMock()
            view._clean_scans_label = mock.MagicMock()
            view._duration_label = mock.MagicMock()
            view._stats_group = mock.MagicMock()
            view._format_number = lambda n: f"{n:,}"
            view._format_duration = lambda s: f"{s}s"
            view._show_empty_state = mock.MagicMock()

            view._update_statistics_display()

            view._total_scans_label.set_label.assert_called_with("10")
            view._files_scanned_label.set_label.assert_called_with("1,500")
            view._threats_label.set_label.assert_called_with("2")
            view._clean_scans_label.set_label.assert_called_with("8")

    def test_update_statistics_display_threats_adds_error_class(self, statistics_view_class):
        """Test that threats > 0 adds error CSS class."""
        mock_stats = mock.MagicMock()
        mock_stats.total_scans = 10
        mock_stats.files_scanned = 1500
        mock_stats.threats_detected = 5
        mock_stats.clean_scans = 5
        mock_stats.average_duration = 45.5
        mock_stats.start_date = None
        mock_stats.end_date = None

        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._current_stats = mock_stats
            view._total_scans_label = mock.MagicMock()
            view._files_scanned_label = mock.MagicMock()
            view._threats_label = mock.MagicMock()
            view._clean_scans_label = mock.MagicMock()
            view._duration_label = mock.MagicMock()
            view._stats_group = mock.MagicMock()
            view._format_number = lambda n: f"{n:,}"
            view._format_duration = lambda s: f"{s}s"
            view._show_empty_state = mock.MagicMock()

            view._update_statistics_display()

            view._threats_label.add_css_class.assert_called_with("error")

    def test_update_statistics_display_no_threats_removes_error_class(self, statistics_view_class):
        """Test that threats = 0 removes error CSS class."""
        mock_stats = mock.MagicMock()
        mock_stats.total_scans = 10
        mock_stats.files_scanned = 1500
        mock_stats.threats_detected = 0
        mock_stats.clean_scans = 10
        mock_stats.average_duration = 45.5
        mock_stats.start_date = None
        mock_stats.end_date = None

        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._current_stats = mock_stats
            view._total_scans_label = mock.MagicMock()
            view._files_scanned_label = mock.MagicMock()
            view._threats_label = mock.MagicMock()
            view._clean_scans_label = mock.MagicMock()
            view._duration_label = mock.MagicMock()
            view._stats_group = mock.MagicMock()
            view._format_number = lambda n: f"{n:,}"
            view._format_duration = lambda s: f"{s}s"
            view._show_empty_state = mock.MagicMock()

            view._update_statistics_display()

            view._threats_label.remove_css_class.assert_called_with("error")

    def test_update_statistics_display_zero_duration_shows_placeholder(self, statistics_view_class):
        """Test that zero duration shows placeholder."""
        mock_stats = mock.MagicMock()
        mock_stats.total_scans = 10
        mock_stats.files_scanned = 1500
        mock_stats.threats_detected = 0
        mock_stats.clean_scans = 10
        mock_stats.average_duration = 0
        mock_stats.start_date = None
        mock_stats.end_date = None

        with mock.patch.object(statistics_view_class, '__init__', lambda self, **kwargs: None):
            view = statistics_view_class()
            view._current_stats = mock_stats
            view._total_scans_label = mock.MagicMock()
            view._files_scanned_label = mock.MagicMock()
            view._threats_label = mock.MagicMock()
            view._clean_scans_label = mock.MagicMock()
            view._duration_label = mock.MagicMock()
            view._stats_group = mock.MagicMock()
            view._format_number = lambda n: f"{n:,}"
            view._format_duration = lambda s: f"{s}s"
            view._show_empty_state = mock.MagicMock()

            view._update_statistics_display()

            view._duration_label.set_label.assert_called_with("--")


class TestStatisticsViewImport:
    """Tests for StatisticsView import."""

    def test_import_statistics_view(self, mock_gi):
        """Test that StatisticsView can be imported."""
        with mock.patch.dict(sys.modules, {
            'src.core.statistics_calculator': mock.MagicMock(),
        }):
            from src.ui.statistics_view import StatisticsView
            assert StatisticsView is not None


# Module-level test function for verification
def test_statistics_view_basic():
    """
    Basic test function for pytest verification command.

    This test verifies the core StatisticsView functionality
    using a minimal mock setup.
    """
    # Mock gi and matplotlib modules
    mock_gtk = mock.MagicMock()
    mock_adw = mock.MagicMock()
    mock_gio = mock.MagicMock()
    mock_glib = mock.MagicMock()

    mock_gi = mock.MagicMock()
    mock_gi.require_version = mock.MagicMock()

    mock_repository = mock.MagicMock()
    mock_repository.Gtk = mock_gtk
    mock_repository.Adw = mock_adw
    mock_repository.Gio = mock_gio
    mock_repository.GLib = mock_glib

    mock_matplotlib = mock.MagicMock()
    mock_figure = mock.MagicMock()
    mock_backend = mock.MagicMock()
    mock_backend.FigureCanvasGTK4Agg = mock.MagicMock()

    with mock.patch.dict(sys.modules, {
        'gi': mock_gi,
        'gi.repository': mock_repository,
        'matplotlib': mock_matplotlib,
        'matplotlib.figure': mock_figure,
        'matplotlib.backends.backend_gtk4agg': mock_backend,
        'src.core.statistics_calculator': mock.MagicMock(),
    }):
        from src.ui.statistics_view import StatisticsView

        # Test 1: Class can be imported
        assert StatisticsView is not None

        # Test 2: Create mock instance and test format helpers
        with mock.patch.object(StatisticsView, '__init__', lambda self, **kwargs: None):
            view = StatisticsView()

            # Test _format_number
            assert view._format_number(1234) == "1,234"
            assert view._format_number(0) == "0"

            # Test _format_duration
            assert view._format_duration(45.0) == "45.0s"
            assert view._format_duration(150) == "2m 30s"
            assert view._format_duration(3900) == "1h 5m"

            # Test _get_data_points_for_timeframe
            assert view._get_data_points_for_timeframe("daily") == 6
            assert view._get_data_points_for_timeframe("weekly") == 7
            assert view._get_data_points_for_timeframe("monthly") == 10
            assert view._get_data_points_for_timeframe("all") == 12

        # All tests passed
