# ClamUI Logs View
"""
Logs interface component for ClamUI with historical logs list and daemon logs section.
"""

import os

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from ..core.log_manager import LogManager, LogEntry, DaemonStatus
from ..core.utils import copy_to_clipboard
from .fullscreen_dialog import FullscreenLogDialog


class LogsView(Gtk.Box):
    """
    Logs interface component for ClamUI.

    Provides the logs viewing interface with:
    - Historical logs list (scan and update operations)
    - Log detail view
    - Daemon status and live logs
    - Clear logs functionality

    Uses a tabbed interface to separate historical logs from daemon logs.
    """

    def __init__(self, **kwargs):
        """
        Initialize the logs view.

        Args:
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        # Initialize log manager
        self._log_manager = LogManager()

        # Currently selected log entry
        self._selected_log: LogEntry | None = None

        # Daemon log refresh timeout ID
        self._daemon_refresh_id: int | None = None

        # Set up the UI
        self._setup_ui()

        # Load logs on startup
        GLib.idle_add(self._load_logs)

    def _setup_ui(self):
        """Set up the logs view UI layout with tabbed interface."""
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_spacing(0)

        # Create view stack for tab content
        self._view_stack = Adw.ViewStack()
        self._view_stack.set_vexpand(True)
        self._view_stack.set_hexpand(True)

        # Create view switcher for tab navigation
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self._view_stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        switcher.set_margin_bottom(12)

        self.append(switcher)
        self.append(self._view_stack)

        # Create the historical logs tab (with list and details)
        self._create_historical_logs_tab()

        # Create the daemon logs tab
        self._create_daemon_logs_tab()

    def _create_historical_logs_tab(self):
        """Create the historical logs tab containing log list and details."""
        # Container for historical logs tab content
        tab_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        tab_content.set_spacing(18)
        tab_content.set_margin_top(12)
        tab_content.set_margin_bottom(12)
        tab_content.set_margin_start(12)
        tab_content.set_margin_end(12)

        # Create scrollable container for the entire tab
        scrolled_container = Gtk.ScrolledWindow()
        scrolled_container.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_container.set_vexpand(True)
        scrolled_container.set_child(tab_content)

        # Create the historical logs section
        self._create_historical_logs_section(tab_content)

        # Create the log detail section
        self._create_log_detail_section(tab_content)

        # Add to view stack
        self._view_stack.add_titled_with_icon(
            scrolled_container,
            "historical",
            "Historical Logs",
            "document-open-recent-symbolic"
        )

    def _create_daemon_logs_tab(self):
        """Create the daemon logs tab."""
        # Container for daemon logs tab content
        tab_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        tab_content.set_spacing(18)
        tab_content.set_margin_top(12)
        tab_content.set_margin_bottom(12)
        tab_content.set_margin_start(12)
        tab_content.set_margin_end(12)
        tab_content.set_vexpand(True)

        # Create the daemon logs section
        self._create_daemon_logs_section(tab_content)

        # Add to view stack
        self._view_stack.add_titled_with_icon(
            tab_content,
            "daemon",
            "ClamAV Daemon",
            "utilities-terminal-symbolic"
        )

    def _create_historical_logs_section(self, parent: Gtk.Box):
        """
        Create the historical logs list section.

        Args:
            parent: The parent container to add the section to
        """
        # Historical logs group
        logs_group = Adw.PreferencesGroup()
        logs_group.set_title("Historical Logs")
        logs_group.set_description("Previous scan and update operations")

        # Header box with Clear button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_halign(Gtk.Align.END)

        # Clear logs button
        clear_button = Gtk.Button()
        clear_button.set_label("Clear All")
        clear_button.add_css_class("flat")
        clear_button.connect("clicked", self._on_clear_logs_clicked)
        self._clear_button = clear_button

        # Refresh button
        refresh_button = Gtk.Button()
        refresh_button.set_icon_name("view-refresh-symbolic")
        refresh_button.set_tooltip_text("Refresh logs")
        refresh_button.add_css_class("flat")
        refresh_button.connect("clicked", self._on_refresh_clicked)

        header_box.append(refresh_button)
        header_box.append(clear_button)
        logs_group.set_header_suffix(header_box)

        # Scrolled window for log entries
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(150)
        scrolled.set_max_content_height(250)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add_css_class("card")

        # ListBox for log entries
        self._logs_listbox = Gtk.ListBox()
        self._logs_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._logs_listbox.add_css_class("boxed-list")
        self._logs_listbox.connect("row-selected", self._on_log_selected)
        self._logs_listbox.set_placeholder(self._create_empty_state())

        scrolled.set_child(self._logs_listbox)

        logs_group.add(scrolled)
        parent.append(logs_group)

    def _create_empty_state(self) -> Gtk.Widget:
        """Create the empty state placeholder widget."""
        empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        empty_box.set_valign(Gtk.Align.CENTER)
        empty_box.set_margin_top(24)
        empty_box.set_margin_bottom(24)
        empty_box.set_spacing(12)

        # Empty state icon
        icon = Gtk.Image()
        icon.set_from_icon_name("document-open-recent-symbolic")
        icon.set_pixel_size(48)
        icon.add_css_class("dim-label")
        empty_box.append(icon)

        # Empty state message
        label = Gtk.Label()
        label.set_text("No logs yet")
        label.add_css_class("dim-label")
        empty_box.append(label)

        sublabel = Gtk.Label()
        sublabel.set_text("Logs from scans and updates will appear here")
        sublabel.add_css_class("dim-label")
        sublabel.add_css_class("caption")
        empty_box.append(sublabel)

        return empty_box

    def _create_log_detail_section(self, parent: Gtk.Box):
        """
        Create the log detail display section.

        Args:
            parent: The parent container to add the section to
        """
        # Log detail group
        detail_group = Adw.PreferencesGroup()
        detail_group.set_title("Log Details")
        detail_group.set_description("Select a log entry above to view details")
        self._detail_group = detail_group

        # Header box with copy, export, and fullscreen buttons
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_halign(Gtk.Align.END)
        header_box.set_spacing(6)

        # Copy to Clipboard button
        copy_button = Gtk.Button()
        copy_button.set_icon_name("edit-copy-symbolic")
        copy_button.set_tooltip_text("Copy to clipboard")
        copy_button.add_css_class("flat")
        copy_button.set_sensitive(False)  # Disabled until log selected
        copy_button.connect("clicked", self._on_copy_detail_clicked)
        self._copy_detail_button = copy_button

        # Export to Text button
        export_text_button = Gtk.Button()
        export_text_button.set_icon_name("document-save-symbolic")
        export_text_button.set_tooltip_text("Export to text file")
        export_text_button.add_css_class("flat")
        export_text_button.set_sensitive(False)  # Disabled until log selected
        export_text_button.connect("clicked", self._on_export_detail_text_clicked)
        self._export_detail_text_button = export_text_button

        # Export to CSV button
        export_csv_button = Gtk.Button()
        export_csv_button.set_icon_name("x-office-spreadsheet-symbolic")
        export_csv_button.set_tooltip_text("Export to CSV file")
        export_csv_button.add_css_class("flat")
        export_csv_button.set_sensitive(False)  # Disabled until log selected
        export_csv_button.connect("clicked", self._on_export_detail_csv_clicked)
        self._export_detail_csv_button = export_csv_button

        # Fullscreen button
        fullscreen_button = Gtk.Button()
        fullscreen_button.set_icon_name("view-fullscreen-symbolic")
        fullscreen_button.set_tooltip_text("View fullscreen")
        fullscreen_button.add_css_class("flat")
        fullscreen_button.connect("clicked", self._on_fullscreen_detail_clicked)
        self._fullscreen_detail_button = fullscreen_button

        header_box.append(copy_button)
        header_box.append(export_text_button)
        header_box.append(export_csv_button)
        header_box.append(fullscreen_button)
        detail_group.set_header_suffix(header_box)

        # Detail container
        detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        detail_box.set_spacing(12)

        # Log detail text view in a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.set_vexpand(False)
        scrolled.add_css_class("card")

        self._detail_text = Gtk.TextView()
        self._detail_text.set_editable(False)
        self._detail_text.set_cursor_visible(False)
        self._detail_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._detail_text.set_left_margin(12)
        self._detail_text.set_right_margin(12)
        self._detail_text.set_top_margin(12)
        self._detail_text.set_bottom_margin(12)
        self._detail_text.add_css_class("monospace")

        # Set placeholder text
        buffer = self._detail_text.get_buffer()
        buffer.set_text("Select a log entry to view details.")

        scrolled.set_child(self._detail_text)
        detail_box.append(scrolled)

        detail_group.add(detail_box)
        parent.append(detail_group)

    def _create_daemon_logs_section(self, parent: Gtk.Box):
        """
        Create the daemon logs section.

        Args:
            parent: The parent container to add the section to
        """
        # Daemon logs group
        daemon_group = Adw.PreferencesGroup()
        daemon_group.set_title("ClamAV Daemon Logs")
        daemon_group.set_description("Live logs from the clamd daemon")
        self._daemon_group = daemon_group

        # Header box with fullscreen button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_halign(Gtk.Align.END)

        # Fullscreen button
        fullscreen_button = Gtk.Button()
        fullscreen_button.set_icon_name("view-fullscreen-symbolic")
        fullscreen_button.set_tooltip_text("View fullscreen")
        fullscreen_button.add_css_class("flat")
        fullscreen_button.connect("clicked", self._on_fullscreen_daemon_clicked)
        self._fullscreen_daemon_button = fullscreen_button

        header_box.append(fullscreen_button)
        daemon_group.set_header_suffix(header_box)

        # Status row
        self._daemon_status_row = Adw.ActionRow()
        self._daemon_status_row.set_title("Daemon Status")
        self._daemon_status_row.set_subtitle("Checking...")
        self._daemon_status_row.set_icon_name("dialog-question-symbolic")

        # Refresh toggle button for live updates
        self._live_toggle = Gtk.ToggleButton()
        self._live_toggle.set_icon_name("media-playback-start-symbolic")
        self._live_toggle.set_tooltip_text("Start live log updates")
        self._live_toggle.set_valign(Gtk.Align.CENTER)
        self._live_toggle.connect("toggled", self._on_live_toggle)
        self._daemon_status_row.add_suffix(self._live_toggle)

        daemon_group.add(self._daemon_status_row)

        # Daemon log text view in a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(300)
        scrolled.set_vexpand(True)
        scrolled.add_css_class("card")
        scrolled.set_margin_top(12)

        self._daemon_text = Gtk.TextView()
        self._daemon_text.set_editable(False)
        self._daemon_text.set_cursor_visible(False)
        self._daemon_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._daemon_text.set_left_margin(12)
        self._daemon_text.set_right_margin(12)
        self._daemon_text.set_top_margin(12)
        self._daemon_text.set_bottom_margin(12)
        self._daemon_text.add_css_class("monospace")

        # Set placeholder text
        buffer = self._daemon_text.get_buffer()
        buffer.set_text("Daemon logs will appear here.\n\nClick the play button to start live updates.")

        scrolled.set_child(self._daemon_text)

        daemon_group.add(scrolled)
        parent.append(daemon_group)

        # Check daemon status on load
        GLib.idle_add(self._check_daemon_status)

    def _load_logs(self) -> bool:
        """Load and display historical logs."""
        # Clear existing rows
        while True:
            row = self._logs_listbox.get_row_at_index(0)
            if row is None:
                break
            self._logs_listbox.remove(row)

        # Get logs from log manager
        logs = self._log_manager.get_logs(limit=100)

        # Add log entries to list
        for entry in logs:
            row = self._create_log_row(entry)
            self._logs_listbox.append(row)

        # Update clear button sensitivity
        self._clear_button.set_sensitive(len(logs) > 0)

        return False  # Don't repeat

    def _create_log_row(self, entry: LogEntry) -> Adw.ActionRow:
        """
        Create a list row for a log entry.

        Args:
            entry: The LogEntry to create a row for

        Returns:
            Adw.ActionRow widget
        """
        row = Adw.ActionRow()

        # Set icon based on log type
        if entry.type == "scan":
            row.set_icon_name("folder-symbolic")
        else:  # update
            row.set_icon_name("software-update-available-symbolic")

        # Set title with summary
        row.set_title(entry.summary)

        # Set subtitle with timestamp and status
        try:
            from datetime import datetime
            timestamp = datetime.fromisoformat(entry.timestamp)
            time_str = timestamp.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            time_str = entry.timestamp

        subtitle = f"{time_str} \u2022 {entry.status}"
        if entry.path:
            # Truncate long paths
            path_display = entry.path
            if len(path_display) > 40:
                path_display = "..." + path_display[-37:]
            subtitle += f" \u2022 {path_display}"
        row.set_subtitle(subtitle)

        # Add status indicator
        status_icon = Gtk.Image()
        if entry.status in ("clean", "success", "up_to_date"):
            status_icon.set_from_icon_name("emblem-ok-symbolic")
            status_icon.add_css_class("success")
        elif entry.status in ("infected", "error"):
            status_icon.set_from_icon_name("dialog-warning-symbolic")
            status_icon.add_css_class("error")
        else:
            status_icon.set_from_icon_name("dialog-information-symbolic")
        status_icon.set_valign(Gtk.Align.CENTER)
        row.add_suffix(status_icon)

        # Store entry ID in row for later retrieval
        row.set_name(entry.id)

        return row

    def _on_log_selected(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None):
        """Handle log entry selection."""
        if row is None:
            self._selected_log = None
            buffer = self._detail_text.get_buffer()
            buffer.set_text("Select a log entry to view details.")
            # Disable copy/export buttons when no log is selected
            self._copy_detail_button.set_sensitive(False)
            self._export_detail_text_button.set_sensitive(False)
            self._export_detail_csv_button.set_sensitive(False)
            return

        log_id = row.get_name()
        entry = self._log_manager.get_log_by_id(log_id)

        if entry is None:
            return

        self._selected_log = entry
        self._display_log_details(entry)
        # Enable copy/export buttons when a log is selected
        self._copy_detail_button.set_sensitive(True)
        self._export_detail_text_button.set_sensitive(True)
        self._export_detail_csv_button.set_sensitive(True)

    def _display_log_details(self, entry: LogEntry):
        """
        Display the full details of a log entry.

        Args:
            entry: The LogEntry to display
        """
        lines = []

        # Header
        if entry.type == "scan":
            lines.append("SCAN LOG")
        else:
            lines.append("UPDATE LOG")

        lines.append("=" * 50)
        lines.append("")

        # Metadata
        lines.append(f"ID: {entry.id}")
        lines.append(f"Timestamp: {entry.timestamp}")
        lines.append(f"Type: {entry.type}")
        lines.append(f"Status: {entry.status}")

        if entry.path:
            lines.append(f"Path: {entry.path}")

        if entry.duration > 0:
            lines.append(f"Duration: {entry.duration:.2f} seconds")

        lines.append("")

        # Summary
        lines.append("Summary:")
        lines.append(f"  {entry.summary}")
        lines.append("")

        # Full details
        if entry.details:
            lines.append("-" * 50)
            lines.append("Full Output:")
            lines.append("-" * 50)
            lines.append(entry.details)

        # Update the text view
        buffer = self._detail_text.get_buffer()
        buffer.set_text("\n".join(lines))

    def _on_fullscreen_detail_clicked(self, button: Gtk.Button):
        """Handle fullscreen button click for log details."""
        # Get current content from detail text view
        buffer = self._detail_text.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        content = buffer.get_text(start, end, False)

        # Create and present the fullscreen dialog
        dialog = FullscreenLogDialog(
            title="Log Details",
            content=content
        )
        dialog.present(self.get_root())

    def _on_copy_detail_clicked(self, button: Gtk.Button):
        """
        Handle copy to clipboard button click for log details.

        Copies the currently displayed log details to the system clipboard.
        """
        if self._selected_log is None:
            return

        # Get current content from detail text view
        buffer = self._detail_text.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        content = buffer.get_text(start, end, False)

        # Copy to clipboard
        success = copy_to_clipboard(content)

        # Show feedback via toast (find the parent window to show toast)
        window = self.get_root()
        if hasattr(window, 'add_toast'):
            if success:
                toast = Adw.Toast.new("Log details copied to clipboard")
            else:
                toast = Adw.Toast.new("Failed to copy to clipboard")
            window.add_toast(toast)

    def _on_export_detail_text_clicked(self, button: Gtk.Button):
        """
        Handle export to text file button click for log details.

        Opens a file save dialog to let the user choose a location,
        then writes the log details to a text file.
        """
        if self._selected_log is None:
            return

        # Create save dialog
        dialog = Gtk.FileDialog()
        dialog.set_title("Export Log Details")

        # Generate default filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dialog.set_initial_name(f"clamui_log_{timestamp}.txt")

        # Set up file filter for text files
        text_filter = Gtk.FileFilter()
        text_filter.set_name("Text Files")
        text_filter.add_mime_type("text/plain")
        text_filter.add_pattern("*.txt")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(text_filter)
        dialog.set_filters(filters)
        dialog.set_default_filter(text_filter)

        # Get the parent window
        window = self.get_root()

        # Open save dialog
        dialog.save(window, None, self._on_text_export_file_selected)

    def _on_text_export_file_selected(self, dialog, result):
        """
        Handle text export file selection result.

        Writes the log details to the selected file.

        Args:
            dialog: The FileDialog that was used
            result: The async result from the save dialog
        """
        try:
            file = dialog.save_finish(result)
            if file is None:
                return  # User cancelled

            file_path = file.get_path()
            if file_path is None:
                self._show_export_toast("Invalid file path selected", is_error=True)
                return

            # Ensure .txt extension
            if not file_path.endswith('.txt'):
                file_path += '.txt'

            # Get current content from detail text view
            buffer = self._detail_text.get_buffer()
            start = buffer.get_start_iter()
            end = buffer.get_end_iter()
            content = buffer.get_text(start, end, False)

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Show success feedback
            self._show_export_toast(f"Log exported to {os.path.basename(file_path)}")

        except GLib.Error:
            # User cancelled the dialog
            pass
        except PermissionError:
            self._show_export_toast("Permission denied - cannot write to selected location", is_error=True)
        except OSError as e:
            self._show_export_toast(f"Error writing file: {str(e)}", is_error=True)

    def _on_export_detail_csv_clicked(self, button: Gtk.Button):
        """
        Handle export to CSV file button click for log details.

        Opens a file save dialog to let the user choose a location,
        then writes the log entry in CSV format.
        """
        if self._selected_log is None:
            return

        # Create save dialog
        dialog = Gtk.FileDialog()
        dialog.set_title("Export Log Details as CSV")

        # Generate default filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dialog.set_initial_name(f"clamui_log_{timestamp}.csv")

        # Set up file filter for CSV files
        csv_filter = Gtk.FileFilter()
        csv_filter.set_name("CSV Files")
        csv_filter.add_mime_type("text/csv")
        csv_filter.add_pattern("*.csv")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(csv_filter)
        dialog.set_filters(filters)
        dialog.set_default_filter(csv_filter)

        # Get the parent window
        window = self.get_root()

        # Open save dialog
        dialog.save(window, None, self._on_csv_export_file_selected)

    def _on_csv_export_file_selected(self, dialog, result):
        """
        Handle CSV export file selection result.

        Writes the log entry in CSV format to the selected file.

        Args:
            dialog: The FileDialog that was used
            result: The async result from the save dialog
        """
        try:
            file = dialog.save_finish(result)
            if file is None:
                return  # User cancelled

            file_path = file.get_path()
            if file_path is None:
                self._show_export_toast("Invalid file path selected", is_error=True)
                return

            # Ensure .csv extension
            if not file_path.endswith('.csv'):
                file_path += '.csv'

            # Format the log entry as CSV
            csv_content = self._format_log_entry_as_csv(self._selected_log)

            # Write to file
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(csv_content)

            # Show success feedback
            self._show_export_toast(f"Log exported to {os.path.basename(file_path)}")

        except GLib.Error:
            # User cancelled the dialog
            pass
        except PermissionError:
            self._show_export_toast("Permission denied - cannot write to selected location", is_error=True)
        except OSError as e:
            self._show_export_toast(f"Error writing file: {str(e)}", is_error=True)

    def _format_log_entry_as_csv(self, entry: LogEntry) -> str:
        """
        Format a log entry as CSV with proper escaping.

        CSV schema: timestamp, type, status, path, summary, duration

        Args:
            entry: The LogEntry to format

        Returns:
            CSV formatted string
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Write header row
        writer.writerow(["timestamp", "type", "status", "path", "summary", "duration"])

        # Write data row
        writer.writerow([
            entry.timestamp,
            entry.type,
            entry.status,
            entry.path or "",
            entry.summary,
            f"{entry.duration:.2f}" if entry.duration > 0 else "0"
        ])

        return output.getvalue()

    def _show_export_toast(self, message: str, is_error: bool = False):
        """
        Show a toast notification for export operations.

        Args:
            message: The message to display
            is_error: Whether this is an error message
        """
        window = self.get_root()
        if hasattr(window, 'add_toast'):
            toast = Adw.Toast.new(message)
            window.add_toast(toast)

    def _on_fullscreen_daemon_clicked(self, button: Gtk.Button):
        """Handle fullscreen button click for daemon logs."""
        # Get current content from daemon text view
        buffer = self._daemon_text.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        content = buffer.get_text(start, end, False)

        # Create and present the fullscreen dialog
        dialog = FullscreenLogDialog(
            title="Daemon Logs",
            content=content
        )
        dialog.present(self.get_root())

    def _on_clear_logs_clicked(self, button: Gtk.Button):
        """Handle clear logs button click."""
        # Show confirmation dialog
        dialog = Adw.MessageDialog()
        dialog.set_heading("Clear All Logs?")
        dialog.set_body("This will permanently delete all historical logs. This action cannot be undone.")
        dialog.set_transient_for(self.get_root())
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear All")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_clear_dialog_response)
        dialog.present()

    def _on_clear_dialog_response(self, dialog: Adw.MessageDialog, response: str):
        """Handle clear confirmation dialog response."""
        if response == "clear":
            self._log_manager.clear_logs()
            self._load_logs()

            # Clear detail view
            buffer = self._detail_text.get_buffer()
            buffer.set_text("Select a log entry to view details.")
            self._selected_log = None

            # Disable copy/export buttons when logs are cleared
            self._copy_detail_button.set_sensitive(False)
            self._export_detail_text_button.set_sensitive(False)
            self._export_detail_csv_button.set_sensitive(False)

    def _on_refresh_clicked(self, button: Gtk.Button):
        """Handle refresh button click."""
        self._load_logs()

    def _check_daemon_status(self) -> bool:
        """Check and display daemon status."""
        status, message = self._log_manager.get_daemon_status()

        if status == DaemonStatus.RUNNING:
            self._daemon_status_row.set_subtitle("Running")
            self._daemon_status_row.set_icon_name("emblem-ok-symbolic")
            # Remove any warning/error classes and add success
            self._daemon_status_row.remove_css_class("warning")
            self._daemon_status_row.remove_css_class("error")
            self._live_toggle.set_sensitive(True)
        elif status == DaemonStatus.STOPPED:
            self._daemon_status_row.set_subtitle("Stopped")
            self._daemon_status_row.set_icon_name("media-playback-stop-symbolic")
            self._live_toggle.set_sensitive(True)
        elif status == DaemonStatus.NOT_INSTALLED:
            self._daemon_status_row.set_subtitle("Not installed")
            self._daemon_status_row.set_icon_name("dialog-information-symbolic")
            self._live_toggle.set_sensitive(False)
            # Update daemon text with helpful message
            buffer = self._daemon_text.get_buffer()
            buffer.set_text("ClamAV daemon (clamd) is not installed.\n\n"
                          "The daemon is optional and provides faster scanning.\n"
                          "You can still use ClamUI for on-demand scanning without it.")
        else:  # UNKNOWN
            self._daemon_status_row.set_subtitle(message or "Unknown")
            self._daemon_status_row.set_icon_name("dialog-question-symbolic")
            self._live_toggle.set_sensitive(False)

        return False  # Don't repeat

    def _on_live_toggle(self, button: Gtk.ToggleButton):
        """Handle live log toggle button."""
        if button.get_active():
            # Start live updates
            button.set_icon_name("media-playback-pause-symbolic")
            button.set_tooltip_text("Stop live log updates")
            self._start_daemon_log_refresh()
        else:
            # Stop live updates
            button.set_icon_name("media-playback-start-symbolic")
            button.set_tooltip_text("Start live log updates")
            self._stop_daemon_log_refresh()

    def _start_daemon_log_refresh(self):
        """Start periodic daemon log refresh."""
        # Initial load
        self._refresh_daemon_logs()

        # Set up periodic refresh (every 3 seconds)
        self._daemon_refresh_id = GLib.timeout_add(3000, self._refresh_daemon_logs)

    def _stop_daemon_log_refresh(self):
        """Stop periodic daemon log refresh."""
        if self._daemon_refresh_id is not None:
            GLib.source_remove(self._daemon_refresh_id)
            self._daemon_refresh_id = None

    def _refresh_daemon_logs(self) -> bool:
        """Refresh daemon logs display."""
        success, content = self._log_manager.read_daemon_logs(num_lines=100)

        buffer = self._daemon_text.get_buffer()

        if success:
            buffer.set_text(content)
            # Scroll to bottom
            end_iter = buffer.get_end_iter()
            self._daemon_text.scroll_to_iter(end_iter, 0.0, False, 0.0, 0.0)
        else:
            buffer.set_text(f"Error loading daemon logs:\n\n{content}")

        # Return True to continue periodic refresh, False otherwise
        return self._daemon_refresh_id is not None

    def refresh_logs(self):
        """
        Public method to refresh the logs display.

        Can be called externally when new logs are added.
        """
        GLib.idle_add(self._load_logs)

    def do_unmap(self):
        """Handle widget unmapping (being hidden)."""
        # Stop daemon log refresh when view is hidden
        self._stop_daemon_log_refresh()
        if self._live_toggle.get_active():
            self._live_toggle.set_active(False)

        # Call parent implementation
        Gtk.Box.do_unmap(self)

    @property
    def log_manager(self) -> LogManager:
        """
        Get the log manager instance.

        Returns:
            The LogManager instance used by this view
        """
        return self._log_manager
