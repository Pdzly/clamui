# ClamUI Statistics View
"""
Statistics dashboard component for ClamUI displaying scan metrics and protection status.
"""

from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
# Import matplotlib with GTK4 backend for chart visualization
import matplotlib
from gi.repository import Adw, GLib, Gtk

matplotlib.use("GTK4Agg")
from matplotlib.backends.backend_gtk4agg import FigureCanvasGTK4Agg as FigureCanvas
from matplotlib.figure import Figure

from ..core.statistics_calculator import (
    ProtectionLevel,
    ProtectionStatus,
    ScanStatistics,
    StatisticsCalculator,
    Timeframe,
)
from .utils import add_row_icon
from .view_helpers import (
    EmptyStateConfig,
    StatusLevel,
    clear_status_classes,
    create_empty_state,
    set_status_class,
)


class StatisticsView(Gtk.Box):
    """
    Statistics dashboard component for ClamUI.

    Provides the statistics viewing interface with:
    - Summary cards (total scans, files scanned, threats detected)
    - Timeframe selector (daily/weekly/monthly/all-time)
    - Protection status indicator
    - Average scan duration display
    - Quick action buttons for common operations

    Uses Adw.PreferencesGroup for consistent styling with other views.
    """

    def __init__(self, **kwargs):
        """
        Initialize the statistics view.

        Args:
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        # Initialize statistics calculator
        self._calculator = StatisticsCalculator()

        # Current selected timeframe
        self._current_timeframe: str = Timeframe.WEEKLY.value

        # Loading state
        self._is_loading = False

        # Current statistics and protection status
        self._current_stats: ScanStatistics | None = None
        self._current_protection: ProtectionStatus | None = None

        # Quick action callback (for triggering scans from parent)
        self._on_quick_scan_requested = None

        # Set up the UI
        self._setup_ui()

        # Load statistics on startup asynchronously
        GLib.idle_add(self._load_statistics_async)

    def _setup_ui(self):
        """Set up the statistics view UI layout."""
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_spacing(18)

        # Create scrollable container for the entire view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        # Main content container
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_spacing(18)

        # Create the protection status section
        self._create_protection_status_section(content_box)

        # Create the timeframe selector section
        self._create_timeframe_section(content_box)

        # Create the statistics cards section
        self._create_statistics_section(content_box)

        # Create the chart visualization section
        self._create_chart_section(content_box)

        # Create the quick actions section
        self._create_quick_actions_section(content_box)

        scrolled.set_child(content_box)
        self.append(scrolled)

    def _create_protection_status_section(self, parent: Gtk.Box):
        """
        Create the protection status indicator section.

        Args:
            parent: The parent container to add the section to
        """
        # Protection status group
        status_group = Adw.PreferencesGroup()
        status_group.set_title("Protection Status")
        status_group.set_description("Current system security posture")

        # Header box with refresh button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_halign(Gtk.Align.END)

        # Loading spinner (hidden by default)
        self._status_spinner = Gtk.Spinner()
        self._status_spinner.set_visible(False)

        # Refresh button
        refresh_button = Gtk.Button()
        refresh_button.set_icon_name("view-refresh-symbolic")
        refresh_button.set_tooltip_text("Refresh statistics")
        refresh_button.add_css_class("flat")
        refresh_button.connect("clicked", self._on_refresh_clicked)
        self._refresh_button = refresh_button

        header_box.append(self._status_spinner)
        header_box.append(refresh_button)
        status_group.set_header_suffix(header_box)

        # Protection status row
        self._protection_row = Adw.ActionRow()
        self._protection_row.set_title("System Status")
        self._protection_row.set_subtitle("Checking...")
        self._protection_row_icon = add_row_icon(self._protection_row, "dialog-question-symbolic")

        # Status badge
        self._status_badge = Gtk.Label()
        self._status_badge.set_label("Unknown")
        self._status_badge.add_css_class("dim-label")
        self._status_badge.set_valign(Gtk.Align.CENTER)
        self._protection_row.add_suffix(self._status_badge)

        status_group.add(self._protection_row)

        # Last scan row
        self._last_scan_row = Adw.ActionRow()
        self._last_scan_row.set_title("Last Scan")
        self._last_scan_row.set_subtitle("No scans recorded")
        add_row_icon(self._last_scan_row, "document-open-recent-symbolic")

        status_group.add(self._last_scan_row)

        parent.append(status_group)

    def _create_timeframe_section(self, parent: Gtk.Box):
        """
        Create the timeframe selector section.

        Args:
            parent: The parent container to add the section to
        """
        # Timeframe selector group
        timeframe_group = Adw.PreferencesGroup()
        timeframe_group.set_title("Timeframe")
        timeframe_group.set_description("Select the time period for statistics")

        # Timeframe button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_spacing(6)
        button_box.set_margin_top(6)
        button_box.set_margin_bottom(6)
        button_box.add_css_class("linked")

        # Create timeframe toggle buttons
        self._timeframe_buttons = {}

        timeframes = [
            (Timeframe.DAILY.value, "Day"),
            (Timeframe.WEEKLY.value, "Week"),
            (Timeframe.MONTHLY.value, "Month"),
            (Timeframe.ALL.value, "All Time"),
        ]

        for timeframe, label in timeframes:
            button = Gtk.ToggleButton()
            button.set_label(label)
            button.connect("toggled", self._on_timeframe_toggled, timeframe)
            self._timeframe_buttons[timeframe] = button
            button_box.append(button)

        # Set default active button
        self._timeframe_buttons[self._current_timeframe].set_active(True)

        timeframe_group.add(button_box)
        parent.append(timeframe_group)

    def _create_statistics_section(self, parent: Gtk.Box):
        """
        Create the statistics cards section.

        Args:
            parent: The parent container to add the section to
        """
        # Statistics group
        stats_group = Adw.PreferencesGroup()
        stats_group.set_title("Scan Statistics")
        stats_group.set_description("Aggregated metrics for the selected timeframe")
        self._stats_group = stats_group

        # Total scans row
        self._total_scans_row = Adw.ActionRow()
        self._total_scans_row.set_title("Total Scans")
        self._total_scans_row.set_subtitle("Number of scans performed")
        add_row_icon(self._total_scans_row, "folder-saved-search-symbolic")

        self._total_scans_label = Gtk.Label()
        self._total_scans_label.set_label("0")
        self._total_scans_label.add_css_class("title-1")
        self._total_scans_label.set_valign(Gtk.Align.CENTER)
        self._total_scans_row.add_suffix(self._total_scans_label)

        stats_group.add(self._total_scans_row)

        # Files scanned row
        self._files_scanned_row = Adw.ActionRow()
        self._files_scanned_row.set_title("Files Scanned")
        self._files_scanned_row.set_subtitle("Total files checked")
        add_row_icon(self._files_scanned_row, "document-open-symbolic")

        self._files_scanned_label = Gtk.Label()
        self._files_scanned_label.set_label("0")
        self._files_scanned_label.add_css_class("title-1")
        self._files_scanned_label.set_valign(Gtk.Align.CENTER)
        self._files_scanned_row.add_suffix(self._files_scanned_label)

        stats_group.add(self._files_scanned_row)

        # Threats detected row
        self._threats_row = Adw.ActionRow()
        self._threats_row.set_title("Threats Detected")
        self._threats_row.set_subtitle("Malware and suspicious files found")
        add_row_icon(self._threats_row, "dialog-warning-symbolic")

        self._threats_label = Gtk.Label()
        self._threats_label.set_label("0")
        self._threats_label.add_css_class("title-1")
        self._threats_label.set_valign(Gtk.Align.CENTER)
        self._threats_row.add_suffix(self._threats_label)

        stats_group.add(self._threats_row)

        # Clean scans row
        self._clean_scans_row = Adw.ActionRow()
        self._clean_scans_row.set_title("Clean Scans")
        self._clean_scans_row.set_subtitle("Scans with no threats found")
        add_row_icon(self._clean_scans_row, "object-select-symbolic")

        self._clean_scans_label = Gtk.Label()
        self._clean_scans_label.set_label("0")
        self._clean_scans_label.add_css_class("title-1")
        self._clean_scans_label.set_valign(Gtk.Align.CENTER)
        self._clean_scans_row.add_suffix(self._clean_scans_label)

        stats_group.add(self._clean_scans_row)

        # Average duration row
        self._duration_row = Adw.ActionRow()
        self._duration_row.set_title("Average Scan Duration")
        self._duration_row.set_subtitle("Mean time per scan")
        add_row_icon(self._duration_row, "preferences-system-time-symbolic")

        self._duration_label = Gtk.Label()
        self._duration_label.set_label("--")
        self._duration_label.add_css_class("title-2")
        self._duration_label.set_valign(Gtk.Align.CENTER)
        self._duration_row.add_suffix(self._duration_label)

        stats_group.add(self._duration_row)

        parent.append(stats_group)

    def _create_chart_section(self, parent: Gtk.Box):
        """
        Create the scan activity chart section.

        Uses matplotlib with GTK4 backend to render a bar chart showing
        scan activity trends over time.

        Args:
            parent: The parent container to add the section to
        """
        # Chart group
        chart_group = Adw.PreferencesGroup()
        chart_group.set_title("Scan Activity")
        chart_group.set_description("Scan trends over the selected timeframe")
        self._chart_group = chart_group

        # Create matplotlib figure and canvas
        # Use appropriate figure size for the container
        self._figure = Figure(figsize=(8, 3), dpi=72)
        self._figure.set_facecolor("none")  # Transparent background

        # Create canvas for GTK4 embedding
        self._canvas = FigureCanvas(self._figure)
        self._canvas.set_size_request(-1, 200)  # Set minimum height

        # Create scroll controller to propagate events to parent ScrolledWindow
        # This prevents the matplotlib canvas from hijacking scroll events
        scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL | Gtk.EventControllerScrollFlags.KINETIC
        )
        scroll_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        scroll_controller.connect("scroll", self._on_chart_scroll)
        self._canvas.add_controller(scroll_controller)

        # Create a frame for the chart
        chart_frame = Gtk.Frame()
        chart_frame.add_css_class("card")
        chart_frame.set_child(self._canvas)

        chart_group.add(chart_frame)

        # Create empty state placeholder (shown when no data)
        self._chart_empty_state = self._create_chart_empty_state()
        self._chart_empty_state.set_visible(False)
        chart_group.add(self._chart_empty_state)

        parent.append(chart_group)

        # Initialize chart axes and bar containers (reused across updates)
        self._chart_ax = None
        self._chart_bars_scans = None
        self._chart_bars_threats = None
        self._chart_initialized = False

        # Initialize with empty chart
        self._update_chart([])

    def _create_chart_empty_state(self) -> Gtk.Box:
        """
        Create the empty state widget for the chart section.

        Returns:
            Gtk.Box containing empty state UI
        """
        return create_empty_state(
            EmptyStateConfig(
                icon_name="applications-science-symbolic",
                title="No scan data available",
                subtitle="Run some scans to see activity trends here",
                center_horizontally=True,
            )
        )

    def _update_chart(self, trend_data: list[dict]):
        """
        Update the chart with new trend data using incremental updates.

        This method reuses axes and bar container objects instead of clearing
        and recreating the entire figure, providing ~3-5x faster updates when
        switching timeframes.

        Args:
            trend_data: List of dicts with 'date', 'scans', 'threats' keys
        """
        try:
            # Check if we have any data
            has_data = trend_data and any(d.get("scans", 0) > 0 for d in trend_data)

            if not has_data:
                # Show empty state, hide canvas
                self._canvas.set_visible(False)
                self._chart_empty_state.set_visible(True)
                self._chart_group.set_description("No scan activity recorded")
                return
        except Exception:
            # If data check fails, just hide the chart
            try:
                self._canvas.set_visible(False)
                self._chart_empty_state.set_visible(True)
                self._chart_group.set_description("Unable to render chart")
            except Exception:
                pass
            return

        try:
            # Hide empty state, show canvas
            self._canvas.set_visible(True)
            self._chart_empty_state.set_visible(False)
            self._chart_group.set_description("Scan trends over the selected timeframe")

            # Prepare data for plotting
            dates = []
            scans = []
            threats = []

            for point in trend_data:
                try:
                    # Parse ISO date and format for display
                    dt = datetime.fromisoformat(point["date"].replace("Z", "+00:00").split("+")[0])
                    dates.append(dt.strftime("%m/%d"))
                except (ValueError, KeyError):
                    dates.append("?")

                scans.append(point.get("scans", 0))
                threats.append(point.get("threats", 0))

            num_points = len(dates)
            bar_width = 0.35

            # Check if we need to reinitialize the chart (data point count changed)
            needs_reinit = (
                not self._chart_initialized
                or self._chart_ax is None
                or self._chart_bars_scans is None
                or len(self._chart_bars_scans) != num_points
            )

            if needs_reinit:
                # Full initialization: create axes and bar containers
                self._figure.clear()
                self._chart_ax = self._figure.add_subplot(111)
                ax = self._chart_ax

                x_positions = list(range(num_points))

                # Create grouped bar chart and store bar containers
                self._chart_bars_scans = ax.bar(
                    [x - bar_width / 2 for x in x_positions],
                    scans,
                    bar_width,
                    label="Scans",
                    color="#3584e4",  # GNOME blue
                    alpha=0.8,
                )
                self._chart_bars_threats = ax.bar(
                    [x + bar_width / 2 for x in x_positions],
                    threats,
                    bar_width,
                    label="Threats",
                    color="#e01b24",  # GNOME red
                    alpha=0.8,
                )

                # Configure chart appearance (only needed on init)
                ax.set_xlabel("Date", fontsize=9)
                ax.set_ylabel("Count", fontsize=9)
                ax.legend(fontsize=8, loc="upper right")

                # Style adjustments for GNOME/Adwaita compatibility
                ax.set_facecolor("none")
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)

                self._chart_initialized = True
            else:
                # Incremental update: just update bar heights
                ax = self._chart_ax
                for bar, height in zip(self._chart_bars_scans, scans, strict=True):
                    bar.set_height(height)
                for bar, height in zip(self._chart_bars_threats, threats, strict=True):
                    bar.set_height(height)

            # Always update x-axis labels (they may change with timeframe)
            x_positions = list(range(num_points))
            ax.set_xticks(x_positions)
            ax.set_xticklabels(dates, fontsize=8)

            # Detect dark mode and apply theme colors
            try:
                style_context = self._canvas.get_style_context()
                color = style_context.get_color()
                is_dark = (color.red + color.green + color.blue) > 1.5

                text_color = "#ffffff" if is_dark else "#2e3436"
                spine_color = "#808080" if is_dark else "#d3d7cf"
            except Exception:
                text_color = "#2e3436"
                spine_color = "#d3d7cf"

            ax.tick_params(colors=text_color, labelsize=8)
            ax.xaxis.label.set_color(text_color)
            ax.yaxis.label.set_color(text_color)
            ax.spines["bottom"].set_color(spine_color)
            ax.spines["left"].set_color(spine_color)

            # Recalculate axis limits and ensure integer y-axis ticks
            ax.relim()
            ax.autoscale_view()
            ax.yaxis.get_major_locator().set_params(integer=True)

            # Adjust layout to prevent label cutoff
            self._figure.tight_layout(pad=0.5)

            # Use draw_idle() for deferred rendering (more efficient)
            self._canvas.draw_idle()

        except Exception:
            # If chart rendering fails, reset state and show error
            try:
                self._chart_initialized = False
                self._chart_ax = None
                self._chart_bars_scans = None
                self._chart_bars_threats = None
                self._figure.clear()
                self._canvas.set_visible(False)
                self._chart_empty_state.set_visible(True)
                self._chart_group.set_description("Unable to render chart")
            except Exception:
                pass

    def _on_chart_scroll(self, controller, dx, dy):
        """
        Handle scroll events on the chart canvas.

        Intercepts scroll events in the CAPTURE phase before they reach the
        matplotlib canvas, and forwards them to the parent ScrolledWindow.
        This prevents the chart from hijacking scroll events.

        Args:
            controller: The EventControllerScroll that received the event
            dx: Horizontal scroll delta
            dy: Vertical scroll delta

        Returns:
            True to stop event propagation to the matplotlib canvas
        """
        # Find the parent ScrolledWindow and scroll it
        widget = self._canvas.get_parent()
        while widget is not None:
            if isinstance(widget, Gtk.ScrolledWindow):
                # Get the vertical adjustment and scroll it
                vadj = widget.get_vadjustment()
                if vadj:
                    # Scroll by the delta amount (dy is typically -1 or 1)
                    # Multiply by a scroll step for natural scrolling feel
                    scroll_step = 50  # pixels per scroll unit
                    new_value = vadj.get_value() + (dy * scroll_step)
                    # Clamp to valid range
                    new_value = max(
                        vadj.get_lower(), min(new_value, vadj.get_upper() - vadj.get_page_size())
                    )
                    vadj.set_value(new_value)
                break
            widget = widget.get_parent()

        # Return True to stop the event from reaching the matplotlib canvas
        return True

    def _create_quick_actions_section(self, parent: Gtk.Box):
        """
        Create the quick actions section.

        Args:
            parent: The parent container to add the section to
        """
        # Quick actions group
        actions_group = Adw.PreferencesGroup()
        actions_group.set_title("Quick Actions")
        actions_group.set_description("Common scanning operations")

        # Quick scan row
        quick_scan_row = Adw.ActionRow()
        quick_scan_row.set_title("Quick Scan")
        quick_scan_row.set_subtitle("Scan your home directory")
        add_row_icon(quick_scan_row, "media-playback-start-symbolic")
        quick_scan_row.set_activatable(True)
        quick_scan_row.connect("activated", self._on_quick_scan_clicked)

        # Add chevron to indicate it's activatable
        chevron = Gtk.Image.new_from_icon_name("go-next-symbolic")
        chevron.add_css_class("dim-label")
        quick_scan_row.add_suffix(chevron)

        actions_group.add(quick_scan_row)

        # View logs row
        view_logs_row = Adw.ActionRow()
        view_logs_row.set_title("View Scan Logs")
        view_logs_row.set_subtitle("See detailed scan history")
        add_row_icon(view_logs_row, "document-open-recent-symbolic")
        view_logs_row.set_activatable(True)
        view_logs_row.connect("activated", self._on_view_logs_clicked)

        chevron2 = Gtk.Image.new_from_icon_name("go-next-symbolic")
        chevron2.add_css_class("dim-label")
        view_logs_row.add_suffix(chevron2)

        actions_group.add(view_logs_row)

        parent.append(actions_group)

    def _load_statistics_async(self) -> bool:
        """
        Load statistics asynchronously.

        Returns:
            False to prevent GLib.idle_add from repeating
        """
        if self._is_loading:
            return False

        self._set_loading_state(True)

        # Load statistics in idle callback to not block UI
        GLib.idle_add(self._perform_load)

        return False

    def _perform_load(self) -> bool:
        """
        Perform the actual statistics loading.

        Wraps all loading operations in try/finally to ensure the loading
        state is always reset, even if errors occur during data retrieval.

        Returns:
            False to prevent GLib.idle_add from repeating
        """
        try:
            # Get statistics for current timeframe
            try:
                self._current_stats = self._calculator.get_statistics(self._current_timeframe)
            except Exception:
                self._current_stats = None

            # Get protection status
            try:
                self._current_protection = self._calculator.get_protection_status()
            except Exception:
                self._current_protection = None

            # Get trend data for chart
            # Use appropriate number of data points based on timeframe
            try:
                data_points = self._get_data_points_for_timeframe(self._current_timeframe)
                trend_data = self._calculator.get_scan_trend_data(
                    self._current_timeframe, data_points
                )
            except Exception:
                trend_data = []

            # Check if we have any valid data
            has_data = self._current_stats is not None and self._current_stats.total_scans > 0

            if has_data:
                # Update UI with loaded data
                self._update_statistics_display()
                self._update_protection_display()
                self._update_chart(trend_data)
            elif self._current_stats is None and self._current_protection is None:
                # Complete failure to load any data - show error state
                self._show_error_state("Failed to load statistics data")
                self._update_chart([])
            else:
                # No scan history but loading succeeded - show empty state
                self._show_empty_state()
                self._update_protection_display()
                self._update_chart([])

        except Exception:
            # Catch-all for any unexpected errors
            self._show_error_state("An unexpected error occurred")
            self._update_chart([])
        finally:
            # ALWAYS reset loading state to prevent stuck spinner
            self._set_loading_state(False)

        return False

    def _get_data_points_for_timeframe(self, timeframe: str) -> int:
        """
        Get the appropriate number of chart data points for a timeframe.

        Args:
            timeframe: The timeframe value ('daily', 'weekly', 'monthly', 'all')

        Returns:
            Number of data points to display
        """
        if timeframe == Timeframe.DAILY.value:
            return 6  # Hourly intervals for a day (4-hour blocks)
        elif timeframe == Timeframe.WEEKLY.value:
            return 7  # Daily intervals for a week
        elif timeframe == Timeframe.MONTHLY.value:
            return 10  # 3-day intervals for a month
        else:  # ALL
            return 12  # Monthly intervals for all-time

    def _update_statistics_display(self):
        """Update the statistics display with current data."""
        if self._current_stats is None:
            self._show_empty_state()
            return

        stats = self._current_stats

        # Update total scans
        self._total_scans_label.set_label(str(stats.total_scans))

        # Update files scanned
        self._files_scanned_label.set_label(self._format_number(stats.files_scanned))

        # Update threats detected
        self._threats_label.set_label(str(stats.threats_detected))

        # Update styling based on threat count
        if stats.threats_detected > 0:
            self._threats_label.add_css_class("error")
        else:
            self._threats_label.remove_css_class("error")

        # Update clean scans
        self._clean_scans_label.set_label(str(stats.clean_scans))

        # Update average duration
        if stats.average_duration > 0:
            self._duration_label.set_label(self._format_duration(stats.average_duration))
        else:
            self._duration_label.set_label("--")

        # Update group description with date range
        if stats.start_date and stats.end_date:
            try:
                from datetime import datetime

                start = datetime.fromisoformat(stats.start_date)
                end = datetime.fromisoformat(stats.end_date)
                date_range = f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
                self._stats_group.set_description(f"Statistics for: {date_range}")
            except (ValueError, AttributeError):
                self._stats_group.set_description("Aggregated metrics for the selected timeframe")
        else:
            self._stats_group.set_description("Aggregated metrics for all time")

    def _update_protection_display(self):
        """Update the protection status display."""
        if self._current_protection is None:
            self._protection_row.set_subtitle("Unable to determine status")
            self._protection_row_icon.set_from_icon_name("dialog-question-symbolic")
            self._status_badge.set_label("Unknown")
            return

        status = self._current_protection

        # Update protection row
        self._protection_row.set_subtitle(status.message)

        # Update icon and badge based on protection level
        if status.level == ProtectionLevel.PROTECTED.value:
            self._protection_row_icon.set_from_icon_name("object-select-symbolic")
            self._status_badge.set_label("Protected")
            set_status_class(self._status_badge, StatusLevel.SUCCESS)
        elif status.level == ProtectionLevel.AT_RISK.value:
            self._protection_row_icon.set_from_icon_name("dialog-warning-symbolic")
            self._status_badge.set_label("At Risk")
            set_status_class(self._status_badge, StatusLevel.WARNING)
        elif status.level == ProtectionLevel.UNPROTECTED.value:
            self._protection_row_icon.set_from_icon_name("dialog-error-symbolic")
            self._status_badge.set_label("Unprotected")
            set_status_class(self._status_badge, StatusLevel.ERROR)
        else:
            self._protection_row_icon.set_from_icon_name("dialog-question-symbolic")
            self._status_badge.set_label("Unknown")
            clear_status_classes(self._status_badge)

        # Update last scan row
        if status.last_scan_timestamp:
            try:
                from datetime import datetime

                last_scan = datetime.fromisoformat(
                    status.last_scan_timestamp.replace("Z", "+00:00").split("+")[0]
                )
                time_str = last_scan.strftime("%Y-%m-%d %H:%M")

                if status.last_scan_age_hours is not None:
                    if status.last_scan_age_hours < 1:
                        age_str = "less than an hour ago"
                    elif status.last_scan_age_hours < 24:
                        hours = int(status.last_scan_age_hours)
                        age_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
                    elif status.last_scan_age_hours < 24 * 7:
                        days = int(status.last_scan_age_hours / 24)
                        age_str = f"{days} day{'s' if days != 1 else ''} ago"
                    else:
                        weeks = int(status.last_scan_age_hours / (24 * 7))
                        age_str = f"{weeks} week{'s' if weeks != 1 else ''} ago"

                    self._last_scan_row.set_subtitle(f"{time_str} ({age_str})")
                else:
                    self._last_scan_row.set_subtitle(time_str)
            except (ValueError, AttributeError):
                self._last_scan_row.set_subtitle(status.last_scan_timestamp)
        else:
            self._last_scan_row.set_subtitle("No scans recorded")

    def _create_empty_state(self) -> Gtk.Box:
        """
        Create the empty state placeholder widget.

        Returns:
            Gtk.Box containing the empty state UI
        """
        return create_empty_state(
            EmptyStateConfig(
                icon_name="folder-saved-search-symbolic",
                title="No scan history yet",
                subtitle="Run your first scan to see statistics and protection status",
                margin_vertical=48,
                title_css_class="title-2",
                center_horizontally=True,
                wrap_subtitle=True,
                max_subtitle_chars=40,
            )
        )

    def _create_error_state(self, error_message: str = "Unable to load statistics") -> Gtk.Box:
        """
        Create an error state placeholder widget.

        Args:
            error_message: The error message to display

        Returns:
            Gtk.Box containing the error state UI
        """
        error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        error_box.set_valign(Gtk.Align.CENTER)
        error_box.set_halign(Gtk.Align.CENTER)
        error_box.set_margin_top(48)
        error_box.set_margin_bottom(48)
        error_box.set_spacing(12)

        # Error icon
        icon = Gtk.Image()
        icon.set_from_icon_name("dialog-error-symbolic")
        icon.set_pixel_size(48)
        icon.add_css_class("dim-label")
        error_box.append(icon)

        # Error message
        label = Gtk.Label()
        label.set_label(error_message)
        label.add_css_class("dim-label")
        error_box.append(label)

        sublabel = Gtk.Label()
        sublabel.set_label("Try refreshing or check that ClamAV is installed correctly")
        sublabel.add_css_class("dim-label")
        sublabel.add_css_class("caption")
        sublabel.set_wrap(True)
        sublabel.set_max_width_chars(40)
        sublabel.set_justify(Gtk.Justification.CENTER)
        error_box.append(sublabel)

        return error_box

    def _show_empty_state(self):
        """Display empty state when no statistics are available."""
        self._total_scans_label.set_label("0")
        self._files_scanned_label.set_label("0")
        self._threats_label.set_label("0")
        self._clean_scans_label.set_label("0")
        self._duration_label.set_label("--")

        # Clear any error/warning styling from threats label
        self._threats_label.remove_css_class("error")

        self._protection_row.set_subtitle("No scan history available")
        self._protection_row_icon.set_from_icon_name("dialog-information-symbolic")
        self._status_badge.set_label("No Data")
        self._status_badge.remove_css_class("success")
        self._status_badge.remove_css_class("warning")
        self._status_badge.remove_css_class("error")

        self._last_scan_row.set_subtitle("Run a scan to see statistics")

        self._stats_group.set_description("Run your first scan to see statistics here")

    def _show_error_state(self, error_message: str = "Unable to load statistics"):
        """
        Display error state when statistics loading fails.

        Args:
            error_message: The error message to display
        """
        self._total_scans_label.set_label("--")
        self._files_scanned_label.set_label("--")
        self._threats_label.set_label("--")
        self._clean_scans_label.set_label("--")
        self._duration_label.set_label("--")

        # Clear any styling from labels
        self._threats_label.remove_css_class("error")

        self._protection_row.set_subtitle("Unable to determine status")
        self._protection_row_icon.set_from_icon_name("dialog-error-symbolic")
        self._status_badge.set_label("Error")
        set_status_class(self._status_badge, StatusLevel.ERROR)

        self._last_scan_row.set_subtitle("Could not load scan history")

        self._stats_group.set_description(error_message)

    def _format_number(self, number: int) -> str:
        """
        Format a number with thousand separators.

        Args:
            number: Number to format

        Returns:
            Formatted string (e.g., "1,234")
        """
        return f"{number:,}"

    def _format_duration(self, seconds: float) -> str:
        """
        Format a duration in seconds to a human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "2m 30s")
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            return f"{hours}h {remaining_minutes}m"

    def _set_loading_state(self, is_loading: bool):
        """
        Update UI to reflect loading state.

        Shows a loading spinner in the header when loading, and disables
        the refresh button to prevent duplicate requests.

        Args:
            is_loading: Whether statistics are currently being loaded
        """
        self._is_loading = is_loading

        try:
            if is_loading:
                # Show loading state in header
                self._status_spinner.set_visible(True)
                self._status_spinner.start()
                self._refresh_button.set_sensitive(False)

                # Disable timeframe buttons during load
                for button in self._timeframe_buttons.values():
                    button.set_sensitive(False)
            else:
                # Restore normal header state
                self._status_spinner.stop()
                self._status_spinner.set_visible(False)
                self._refresh_button.set_sensitive(True)

                # Re-enable timeframe buttons
                for button in self._timeframe_buttons.values():
                    button.set_sensitive(True)
        except Exception:
            # Ensure loading flag is reset even if widget operations fail
            # This prevents stuck loading state
            self._is_loading = False

    def _on_refresh_clicked(self, button: Gtk.Button):
        """Handle refresh button click."""
        self._load_statistics_async()

    def _on_timeframe_toggled(self, button: Gtk.ToggleButton, timeframe: str):
        """
        Handle timeframe button toggle.

        Args:
            button: The toggled button
            timeframe: The timeframe value associated with the button
        """
        if not button.get_active():
            return

        # Deactivate other buttons
        for tf, btn in self._timeframe_buttons.items():
            if tf != timeframe:
                btn.set_active(False)

        # Update current timeframe and reload
        self._current_timeframe = timeframe
        self._load_statistics_async()

    def _on_quick_scan_clicked(self, row: Adw.ActionRow):
        """Handle quick scan action click."""
        if self._on_quick_scan_requested:
            self._on_quick_scan_requested()
        else:
            # Try to activate the show-scan action
            app = self.get_root()
            if app and hasattr(app, "activate_action"):
                app.activate_action("app.show-scan", None)

    def _on_view_logs_clicked(self, row: Adw.ActionRow):
        """Handle view logs action click."""
        # Try to activate the show-logs action
        app = self.get_root()
        if app and hasattr(app, "activate_action"):
            app.activate_action("app.show-logs", None)

    def set_quick_scan_callback(self, callback):
        """
        Set callback for quick scan requests.

        Args:
            callback: Callable to invoke when quick scan is requested
        """
        self._on_quick_scan_requested = callback

    def refresh_statistics(self):
        """
        Public method to refresh the statistics display.

        Can be called externally when scans complete.
        """
        GLib.idle_add(self._load_statistics_async)

    @property
    def calculator(self) -> StatisticsCalculator:
        """
        Get the statistics calculator instance.

        Returns:
            The StatisticsCalculator instance used by this view
        """
        return self._calculator
