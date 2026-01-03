# ClamUI Quarantine View
"""
Quarantine interface component for ClamUI with list display and action buttons.

Provides the quarantine management interface with:
- List of quarantined files with metadata
- Restore and delete actions
- Total storage display
- Cleanup for old entries
"""

import time
from datetime import datetime

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from ..core.quarantine import (
    QuarantineManager,
    QuarantineEntry,
    QuarantineResult,
    QuarantineStatus,
)
from .utils import add_row_icon

# Pagination thresholds for quarantine list
INITIAL_DISPLAY_LIMIT = 25
LOAD_MORE_BATCH_SIZE = 25


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class QuarantineView(Gtk.Box):
    """
    Quarantine interface component for ClamUI.

    Provides the quarantine management interface with:
    - List of quarantined files showing threat name, original path, date, size
    - Restore button to recover files to original location
    - Delete button to permanently remove files
    - Total quarantine size display
    - Clear old items functionality (removes files older than 30 days)
    """

    def __init__(self, **kwargs):
        """
        Initialize the quarantine view.

        Args:
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        # Initialize quarantine manager
        self._manager = QuarantineManager()

        # Loading state
        self._is_loading = False

        # Pagination state
        self._displayed_count: int = 0
        self._all_entries: list[QuarantineEntry] = []
        self._load_more_row: Gtk.ListBoxRow | None = None
        self._scrolled: Gtk.ScrolledWindow | None = None

        # Callback for quarantine content changes (for external notification)
        self._on_quarantine_changed = None

        # Track last refresh time to prevent excessive refreshes
        self._last_refresh_time: float = 0.0

        # Set up the UI
        self._setup_ui()

        # Connect to map signal to refresh when view becomes visible
        self.connect("map", self._on_view_mapped)

        # Load entries on startup asynchronously
        GLib.idle_add(self._load_entries_async)

    def _setup_ui(self):
        """Set up the quarantine view UI layout."""
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_spacing(18)

        # Create the status banner (hidden by default)
        self._status_banner = Adw.Banner()
        self._status_banner.set_revealed(False)
        self._status_banner.set_button_label("Dismiss")
        self._status_banner.connect("button-clicked", self._on_status_banner_dismissed)
        self.append(self._status_banner)

        # Create the storage info section
        self._create_storage_info_section()

        # Create the quarantine list section
        self._create_quarantine_list_section()

    def _create_storage_info_section(self):
        """Create the storage information section."""
        # Storage info group
        storage_group = Adw.PreferencesGroup()
        storage_group.set_title("Quarantine Storage")
        storage_group.set_description("Secure storage for isolated threats")

        # Storage info row
        self._storage_row = Adw.ActionRow()
        self._storage_row.set_title("Total Size")
        self._storage_row.set_subtitle("Calculating...")
        add_row_icon(self._storage_row, "drive-harddisk-symbolic")

        # Count indicator
        self._count_label = Gtk.Label()
        self._count_label.set_text("0 items")
        self._count_label.add_css_class("dim-label")
        self._count_label.set_valign(Gtk.Align.CENTER)
        self._storage_row.add_suffix(self._count_label)

        storage_group.add(self._storage_row)
        self.append(storage_group)

    def _create_quarantine_list_section(self):
        """Create the quarantine list section."""
        # Quarantine list group
        list_group = Adw.PreferencesGroup()
        list_group.set_title("Quarantined Files")
        list_group.set_description("Detected threats isolated from your system")
        self._list_group = list_group

        # Header box with action buttons
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_halign(Gtk.Align.END)
        header_box.set_spacing(6)

        # Loading spinner (hidden by default)
        self._spinner = Gtk.Spinner()
        self._spinner.set_visible(False)
        header_box.append(self._spinner)

        # Refresh button
        refresh_button = Gtk.Button()
        refresh_button.set_icon_name("view-refresh-symbolic")
        refresh_button.set_tooltip_text("Refresh quarantine list")
        refresh_button.add_css_class("flat")
        refresh_button.connect("clicked", self._on_refresh_clicked)
        self._refresh_button = refresh_button
        header_box.append(refresh_button)

        # Clear old items button
        clear_old_button = Gtk.Button()
        clear_old_button.set_label("Clear Old Items")
        clear_old_button.set_tooltip_text("Remove quarantined files older than 30 days")
        clear_old_button.add_css_class("flat")
        clear_old_button.connect("clicked", self._on_clear_old_clicked)
        self._clear_old_button = clear_old_button
        header_box.append(clear_old_button)

        list_group.set_header_suffix(header_box)

        # Scrolled window for quarantine entries
        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.set_min_content_height(300)
        self._scrolled.set_vexpand(True)
        self._scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._scrolled.add_css_class("card")

        # ListBox for quarantine entries
        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._listbox.add_css_class("boxed-list")
        self._listbox.set_placeholder(self._create_empty_state())

        self._scrolled.set_child(self._listbox)
        list_group.add(self._scrolled)
        self.append(list_group)

    def _create_empty_state(self) -> Gtk.Widget:
        """Create the empty state placeholder widget."""
        empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        empty_box.set_valign(Gtk.Align.CENTER)
        empty_box.set_margin_top(48)
        empty_box.set_margin_bottom(48)
        empty_box.set_spacing(12)

        # Empty state icon
        icon = Gtk.Image()
        icon.set_from_icon_name("shield-safe-symbolic")
        icon.set_pixel_size(64)
        icon.add_css_class("dim-label")
        empty_box.append(icon)

        # Empty state title
        title = Gtk.Label()
        title.set_text("No Quarantined Files")
        title.add_css_class("title-2")
        title.add_css_class("dim-label")
        empty_box.append(title)

        # Empty state subtitle
        subtitle = Gtk.Label()
        subtitle.set_text("Detected threats will be isolated here for review")
        subtitle.add_css_class("dim-label")
        subtitle.add_css_class("caption")
        empty_box.append(subtitle)

        return empty_box

    def _create_loading_state(self) -> Gtk.ListBoxRow:
        """
        Create a loading state placeholder row widget.

        Returns:
            Gtk.ListBoxRow containing spinner and loading text
        """
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)

        loading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        loading_box.set_halign(Gtk.Align.CENTER)
        loading_box.set_valign(Gtk.Align.CENTER)
        loading_box.set_margin_top(48)
        loading_box.set_margin_bottom(48)
        loading_box.set_spacing(12)

        # Loading spinner
        spinner = Gtk.Spinner()
        spinner.set_spinning(True)
        loading_box.append(spinner)

        # Loading message
        label = Gtk.Label()
        label.set_text("Loading quarantine entries...")
        label.add_css_class("dim-label")
        loading_box.append(label)

        row.set_child(loading_box)

        return row

    def _on_status_banner_dismissed(self, banner):
        """
        Handle status banner dismiss button click.

        Hides the status banner when the user clicks the Dismiss button.

        Args:
            banner: The Adw.Banner that was dismissed
        """
        banner.set_revealed(False)

    def _load_entries_async(self):
        """
        Load and display quarantine entries asynchronously.

        This method is safe to call multiple times - it will prevent
        duplicate requests via the _is_loading flag.
        """
        if self._is_loading:
            return

        self._set_loading_state(True)

        # Get entries from manager asynchronously
        self._manager.get_all_entries_async(callback=self._on_entries_loaded)

    def _on_entries_loaded(self, entries: list[QuarantineEntry]) -> bool:
        """
        Handle completion of async entries loading.

        Args:
            entries: List of QuarantineEntry objects

        Returns:
            False to prevent GLib.idle_add from repeating
        """
        try:
            # Clear existing rows
            try:
                self._listbox.remove_all()
            except Exception:
                return False

            # Reset pagination state
            self._all_entries = entries
            self._displayed_count = 0
            self._load_more_row = None

            # Update storage info (pass entries to avoid synchronous DB calls on main thread)
            self._update_storage_info(entries)

            # Update last refresh time to prevent duplicate refreshes
            self._last_refresh_time = time.time()

            # Handle empty state - placeholder will be shown automatically
            if not entries:
                self._clear_old_button.set_sensitive(False)
                return False

            # Display initial batch with pagination
            initial_limit = min(INITIAL_DISPLAY_LIMIT, len(entries))
            self._display_entry_batch(0, initial_limit)

            # Add "Load More" button if there are more entries
            if len(entries) > INITIAL_DISPLAY_LIMIT:
                self._add_load_more_button()

            # Enable clear old button if there are entries
            self._clear_old_button.set_sensitive(True)

        finally:
            self._set_loading_state(False)

            # Invoke callback if registered
            if self._on_quarantine_changed:
                entry_count = len(entries)
                self._on_quarantine_changed(entry_count)

        return False

    def _display_entry_batch(self, start_index: int, count: int):
        """
        Display a batch of entry rows starting from the given index.

        Args:
            start_index: Index in _all_entries to start from
            count: Number of entries to display
        """
        end_index = min(start_index + count, len(self._all_entries))

        for i in range(start_index, end_index):
            entry = self._all_entries[i]
            try:
                row = self._create_entry_row(entry)
                # Insert before the "Load More" button if it exists
                if self._load_more_row:
                    self._listbox.insert(row, self._displayed_count)
                else:
                    self._listbox.append(row)
                self._displayed_count += 1
            except Exception:
                # Skip entries that fail to render
                continue

    def _add_load_more_button(self):
        """Add a 'Show More' button row to load additional entries."""
        load_more_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        load_more_box.set_halign(Gtk.Align.CENTER)
        load_more_box.set_margin_top(12)
        load_more_box.set_margin_bottom(12)

        # Progress label
        remaining = len(self._all_entries) - self._displayed_count
        progress_label = Gtk.Label()
        progress_label.set_markup(
            f"<span size='small'>Showing {self._displayed_count} of "
            f"{len(self._all_entries)} entries</span>"
        )
        progress_label.add_css_class("dim-label")
        load_more_box.append(progress_label)

        # Button row
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.CENTER)

        # "Show More" button
        show_more_btn = Gtk.Button()
        show_more_btn.set_label(f"Show {min(LOAD_MORE_BATCH_SIZE, remaining)} More")
        show_more_btn.add_css_class("pill")
        show_more_btn.connect("clicked", self._on_load_more_clicked)
        button_box.append(show_more_btn)

        # "Show All" button (only if many remaining)
        if remaining > LOAD_MORE_BATCH_SIZE:
            show_all_btn = Gtk.Button()
            show_all_btn.set_label(f"Show All ({remaining} remaining)")
            show_all_btn.add_css_class("pill")
            show_all_btn.connect("clicked", self._on_show_all_clicked)
            button_box.append(show_all_btn)

        load_more_box.append(button_box)

        # Wrap in ListBoxRow to ensure proper parent-child relationship
        load_more_row = Gtk.ListBoxRow()
        load_more_row.set_child(load_more_box)
        load_more_row.set_activatable(False)
        load_more_row.set_selectable(False)
        self._load_more_row = load_more_row
        self._listbox.append(load_more_row)

    def _on_load_more_clicked(self, button):
        """Handle 'Show More' button click."""
        # Preserve scroll position
        scroll_pos = None
        if self._scrolled:
            vadj = self._scrolled.get_vadjustment()
            scroll_pos = vadj.get_value()

        if self._load_more_row:
            self._listbox.remove(self._load_more_row)
            self._load_more_row = None

        remaining = len(self._all_entries) - self._displayed_count
        batch_size = min(LOAD_MORE_BATCH_SIZE, remaining)
        self._display_entry_batch(self._displayed_count, batch_size)

        if self._displayed_count < len(self._all_entries):
            self._add_load_more_button()

        # Restore scroll position after layout
        if scroll_pos is not None:
            GLib.idle_add(lambda: vadj.set_value(scroll_pos))

    def _on_show_all_clicked(self, button):
        """Handle 'Show All' button click."""
        # Preserve scroll position
        scroll_pos = None
        if self._scrolled:
            vadj = self._scrolled.get_vadjustment()
            scroll_pos = vadj.get_value()

        if self._load_more_row:
            self._listbox.remove(self._load_more_row)
            self._load_more_row = None

        remaining = len(self._all_entries) - self._displayed_count
        self._display_entry_batch(self._displayed_count, remaining)

        # Restore scroll position after layout
        if scroll_pos is not None:
            GLib.idle_add(lambda: vadj.set_value(scroll_pos))

    def _create_entry_row(self, entry: QuarantineEntry) -> Adw.ExpanderRow:
        """
        Create a list row for a quarantine entry.

        Args:
            entry: The QuarantineEntry to create a row for

        Returns:
            Adw.ExpanderRow widget
        """
        row = Adw.ExpanderRow()

        # Set title as threat name
        row.set_title(entry.threat_name)

        # Format and set subtitle with original path
        original_path = entry.original_path
        if len(original_path) > 50:
            display_path = "..." + original_path[-47:]
        else:
            display_path = original_path
        row.set_subtitle(display_path)

        # Set icon
        add_row_icon(row, "dialog-warning-symbolic")

        # Create info label with date and size
        try:
            detection_date = datetime.fromisoformat(entry.detection_date)
            date_str = detection_date.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            date_str = entry.detection_date

        size_str = format_file_size(entry.file_size)

        info_label = Gtk.Label()
        info_label.set_text(f"{date_str} • {size_str}")
        info_label.add_css_class("dim-label")
        info_label.add_css_class("caption")
        info_label.set_valign(Gtk.Align.CENTER)
        row.add_suffix(info_label)

        # Create expanded content with details and action buttons
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        content_box.set_margin_top(8)
        content_box.set_margin_bottom(8)

        # File details section
        details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Original path row
        path_row = Adw.ActionRow()
        path_row.set_title("Original Path")
        path_row.set_subtitle(entry.original_path)
        path_row.set_subtitle_selectable(True)
        add_row_icon(path_row, "folder-symbolic")
        details_box.append(path_row)

        # Detection date row
        date_row = Adw.ActionRow()
        date_row.set_title("Detection Date")
        date_row.set_subtitle(date_str)
        add_row_icon(date_row, "x-office-calendar-symbolic")
        details_box.append(date_row)

        # File size row
        size_row = Adw.ActionRow()
        size_row.set_title("File Size")
        size_row.set_subtitle(f"{size_str} ({entry.file_size:,} bytes)")
        add_row_icon(size_row, "drive-harddisk-symbolic")
        details_box.append(size_row)

        content_box.append(details_box)

        # Action buttons section
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(8)

        # Restore button
        restore_button = Gtk.Button()
        restore_button.set_label("Restore")
        restore_button.set_icon_name("document-revert-symbolic")
        restore_button.set_tooltip_text("Restore file to original location")
        restore_button.add_css_class("suggested-action")
        restore_button.connect("clicked", self._on_restore_clicked, entry)
        button_box.append(restore_button)

        # Delete button
        delete_button = Gtk.Button()
        delete_button.set_label("Delete")
        delete_button.set_icon_name("user-trash-symbolic")
        delete_button.set_tooltip_text("Permanently delete this file")
        delete_button.add_css_class("destructive-action")
        delete_button.connect("clicked", self._on_delete_clicked, entry)
        button_box.append(delete_button)

        content_box.append(button_box)

        row.add_row(content_box)

        # Store entry ID for later use
        row.set_name(str(entry.id))

        return row

    def _update_storage_info(self, entries: list[QuarantineEntry] = None):
        """
        Update the storage information display.

        Args:
            entries: Optional list of QuarantineEntry objects to calculate stats from.
                    If provided, avoids synchronous database calls on the main thread.
                    If None, falls back to database queries (not recommended on main thread).
        """
        if entries is not None:
            # Calculate from provided entries (avoids blocking database calls)
            total_size = sum(entry.file_size for entry in entries)
            entry_count = len(entries)
        else:
            # Fallback to database queries (may block main thread)
            total_size = self._manager.get_total_size()
            entry_count = self._manager.get_entry_count()

        self._storage_row.set_subtitle(format_file_size(total_size))

        if entry_count == 1:
            self._count_label.set_text("1 item")
        else:
            self._count_label.set_text(f"{entry_count} items")

    def _set_loading_state(self, is_loading: bool):
        """
        Update UI to reflect loading state.

        Args:
            is_loading: Whether entries are currently being loaded
        """
        self._is_loading = is_loading

        try:
            if is_loading:
                self._spinner.set_visible(True)
                self._spinner.start()
                self._refresh_button.set_sensitive(False)
                self._clear_old_button.set_sensitive(False)

                # Clear existing rows and show loading placeholder
                self._listbox.remove_all()
                loading_row = self._create_loading_state()
                self._listbox.append(loading_row)
            else:
                self._spinner.stop()
                self._spinner.set_visible(False)
                self._refresh_button.set_sensitive(True)
        except Exception:
            self._is_loading = False

    def _on_refresh_clicked(self, button):
        """Handle refresh button click."""
        self._load_entries_async()

    def _on_restore_clicked(self, button, entry: QuarantineEntry):
        """
        Handle restore button click.

        Shows a confirmation dialog before restoring.

        Args:
            button: The clicked button
            entry: The QuarantineEntry to restore
        """
        dialog = Adw.MessageDialog()
        dialog.set_heading("Restore File?")
        dialog.set_body(
            f"This will restore the file to its original location:\n\n"
            f"{entry.original_path}\n\n"
            f"Warning: This file was detected as a threat ({entry.threat_name}). "
            f"Only restore if you are certain it is a false positive."
        )
        dialog.set_transient_for(self.get_root())
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("restore", "Restore")
        dialog.set_response_appearance("restore", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_restore_dialog_response, entry)
        dialog.present()

    def _on_restore_dialog_response(
        self, dialog: Adw.MessageDialog, response: str, entry: QuarantineEntry
    ):
        """Handle restore confirmation dialog response."""
        if response == "restore":
            self._perform_restore(entry)

    def _perform_restore(self, entry: QuarantineEntry):
        """
        Perform the restore operation.

        Args:
            entry: The QuarantineEntry to restore
        """
        # Show operation in progress
        self._status_banner.set_title(f"Restoring {entry.threat_name}...")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("error")
        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

        # Perform restore asynchronously
        self._manager.restore_file_async(entry.id, self._on_restore_complete)

    def _on_restore_complete(self, result: QuarantineResult):
        """
        Handle restore operation completion.

        Args:
            result: The QuarantineResult from the restore operation
        """
        if result.is_success:
            self._status_banner.set_title("File restored successfully")
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("error")
            # Refresh the list
            self._load_entries_async()
        else:
            error_msg = result.error_message or "Unknown error"
            if result.status == QuarantineStatus.RESTORE_DESTINATION_EXISTS:
                error_msg = "Cannot restore: A file already exists at the original location"
            self._status_banner.set_title(f"Restore failed: {error_msg}")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")

        self._status_banner.set_button_label("Dismiss")
        self._status_banner.set_revealed(True)

    def _on_delete_clicked(self, button, entry: QuarantineEntry):
        """
        Handle delete button click.

        Shows a confirmation dialog before deleting.

        Args:
            button: The clicked button
            entry: The QuarantineEntry to delete
        """
        dialog = Adw.MessageDialog()
        dialog.set_heading("Permanently Delete File?")
        dialog.set_body(
            f"This will permanently delete the quarantined file:\n\n"
            f"Threat: {entry.threat_name}\n"
            f"Size: {format_file_size(entry.file_size)}\n\n"
            f"This action cannot be undone."
        )
        dialog.set_transient_for(self.get_root())
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_delete_dialog_response, entry)
        dialog.present()

    def _on_delete_dialog_response(
        self, dialog: Adw.MessageDialog, response: str, entry: QuarantineEntry
    ):
        """Handle delete confirmation dialog response."""
        if response == "delete":
            self._perform_delete(entry)

    def _perform_delete(self, entry: QuarantineEntry):
        """
        Perform the delete operation.

        Args:
            entry: The QuarantineEntry to delete
        """
        # Show operation in progress
        self._status_banner.set_title(f"Deleting {entry.threat_name}...")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("error")
        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

        # Perform delete asynchronously
        self._manager.delete_file_async(entry.id, self._on_delete_complete)

    def _on_delete_complete(self, result: QuarantineResult):
        """
        Handle delete operation completion.

        Args:
            result: The QuarantineResult from the delete operation
        """
        if result.is_success:
            self._status_banner.set_title("File deleted permanently")
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("error")
            # Refresh the list
            self._load_entries_async()
        else:
            error_msg = result.error_message or "Unknown error"
            self._status_banner.set_title(f"Delete failed: {error_msg}")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")

        self._status_banner.set_button_label("Dismiss")
        self._status_banner.set_revealed(True)

    def _on_clear_old_clicked(self, button):
        """Handle clear old items button click."""
        # Get count of old entries first
        old_entries = self._manager.get_old_entries(days=30)
        if not old_entries:
            self._status_banner.set_title("No items older than 30 days")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.set_button_label("Dismiss")
            self._status_banner.set_revealed(True)
            return

        # Show confirmation dialog
        dialog = Adw.MessageDialog()
        dialog.set_heading("Clear Old Items?")
        dialog.set_body(
            f"This will permanently delete {len(old_entries)} quarantined file(s) "
            f"that are older than 30 days.\n\n"
            f"This action cannot be undone."
        )
        dialog.set_transient_for(self.get_root())
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear Old Items")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_clear_old_dialog_response)
        dialog.present()

    def _on_clear_old_dialog_response(self, dialog: Adw.MessageDialog, response: str):
        """Handle clear old items confirmation dialog response."""
        if response == "clear":
            self._perform_clear_old()

    def _perform_clear_old(self):
        """Perform the clear old entries operation."""
        # Show operation in progress
        self._status_banner.set_title("Clearing old items...")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("error")
        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

        # Perform cleanup asynchronously
        self._manager.cleanup_old_entries_async(days=30, callback=self._on_clear_old_complete)

    def _on_clear_old_complete(self, removed_count: int):
        """
        Handle clear old entries operation completion.

        Args:
            removed_count: Number of entries removed
        """
        if removed_count > 0:
            self._status_banner.set_title(
                f"Removed {removed_count} old item(s)"
            )
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("error")
            # Refresh the list
            self._load_entries_async()
        else:
            self._status_banner.set_title("No items were removed")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")

        self._status_banner.set_button_label("Dismiss")
        self._status_banner.set_revealed(True)

    def refresh(self):
        """
        Public method to refresh the quarantine list.

        Can be called externally when files are added to quarantine.
        """
        GLib.idle_add(self._load_entries_async)

    @property
    def manager(self) -> QuarantineManager:
        """
        Get the quarantine manager instance.

        Returns:
            The QuarantineManager instance used by this view
        """
        return self._manager

    def _on_view_mapped(self, widget):
        """
        Handle view becoming visible (mapped).

        Refreshes the quarantine list when the view becomes visible to ensure
        newly quarantined files appear immediately without manual refresh.
        Uses a debounce mechanism to prevent excessive refreshes.

        Args:
            widget: The widget that was mapped (self)
        """
        # Debounce: only refresh if more than 0.5 seconds since last refresh
        # This prevents excessive refreshes when rapidly switching tabs
        current_time = time.time()
        if current_time - self._last_refresh_time < 0.5:
            return

        self._last_refresh_time = current_time

        # Trigger async refresh
        self._load_entries_async()

    def set_quarantine_changed_callback(self, callback):
        """
        Set callback for quarantine content changes.

        The callback is invoked when quarantine operations complete
        (file added, restored, or deleted). This allows external code
        to react to quarantine changes.

        Signature: callback(entry_count: int)
        - entry_count: Current number of entries in quarantine

        Args:
            callback: Callable to invoke on quarantine changes
        """
        self._on_quarantine_changed = callback

    def notify_quarantine_changed(self):
        """
        Notify that quarantine content has changed.

        Call this method when files are added to quarantine from external
        code (e.g., scan view) to trigger a refresh of the quarantine list.
        """
        self.refresh()

        # Invoke callback if registered
        if self._on_quarantine_changed:
            entry_count = self._manager.get_entry_count()
            self._on_quarantine_changed(entry_count)
