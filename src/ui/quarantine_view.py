# ClamUI Quarantine View
"""
Quarantine interface component for ClamUI with list display and action buttons.

Provides the quarantine management interface with:
- List of quarantined files with metadata
- Restore and delete actions
- Total storage display
- Cleanup for old entries
"""

import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk, Pango

from ..core.quarantine import (
    QuarantineEntry,
    QuarantineManager,
    QuarantineResult,
    QuarantineStatus,
)
from .pagination import PaginatedListController
from .utils import add_row_icon, resolve_icon_name
from .view_helpers import EmptyStateConfig, create_empty_state, create_loading_row

# Backward compatibility constants for tests
INITIAL_DISPLAY_LIMIT = PaginatedListController.DEFAULT_INITIAL_LIMIT
LOAD_MORE_BATCH_SIZE = PaginatedListController.DEFAULT_BATCH_SIZE


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

        # Pagination state - keep _all_entries for compatibility with search filtering
        self._all_entries: list[QuarantineEntry] = []

        # Search/filter state
        self._search_query: str = ""
        self._filtered_entries: list[QuarantineEntry] = []
        self._search_timeout_id: int | None = None

        # Callback for quarantine content changes (for external notification)
        self._on_quarantine_changed = None

        # Track last refresh time to prevent excessive refreshes
        self._last_refresh_time: float = 0.0

        # Set up the UI (this creates self._listbox and self._scrolled)
        self._setup_ui()

        # Create custom pagination controller that uses view's entries_to_display
        # We need to create a custom controller that can access the view's filtered entries
        class QuarantinePaginationController(PaginatedListController):
            def __init__(controller_self, view, *args, **kwargs):
                super().__init__(*args, **kwargs)
                controller_self._view = view

            @property
            def entries_to_display(controller_self):
                """Use the view's entries_to_display property for filtering support."""
                return controller_self._view._entries_to_display

        self._pagination = QuarantinePaginationController(
            self,
            listbox=self._listbox,
            scrolled_window=self._scrolled,
            row_factory=self._create_entry_row,
        )

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

        # Header box with search and action buttons
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_spacing(12)

        # Search entry
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Search by threat name or path...")
        self._search_entry.set_hexpand(True)
        self._search_entry.connect("search-changed", self._on_search_changed)
        header_box.append(self._search_entry)

        # Action buttons box (right-aligned)
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        action_box.set_halign(Gtk.Align.END)
        action_box.set_spacing(6)

        # Loading spinner (hidden by default)
        self._spinner = Gtk.Spinner()
        self._spinner.set_visible(False)
        action_box.append(self._spinner)

        # Refresh button
        refresh_button = Gtk.Button()
        refresh_button.set_icon_name(resolve_icon_name("view-refresh-symbolic"))
        refresh_button.set_tooltip_text("Refresh quarantine list")
        refresh_button.add_css_class("flat")
        refresh_button.connect("clicked", self._on_refresh_clicked)
        self._refresh_button = refresh_button
        action_box.append(refresh_button)

        # Clear old items button
        clear_old_button = Gtk.Button()
        clear_old_button.set_label("Clear Old Items")
        clear_old_button.set_tooltip_text("Remove quarantined files older than 30 days")
        clear_old_button.add_css_class("flat")
        clear_old_button.connect("clicked", self._on_clear_old_clicked)
        self._clear_old_button = clear_old_button
        action_box.append(clear_old_button)

        header_box.append(action_box)

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
        return create_empty_state(
            EmptyStateConfig(
                icon_name="shield-safe-symbolic",
                title="No Quarantined Files",
                subtitle="Detected threats will be isolated here for review",
                icon_size=64,
                margin_vertical=48,
                title_css_class="title-2",
            )
        )

    def _create_no_results_state(self) -> Gtk.Widget:
        """Create the no search results placeholder widget."""
        return create_empty_state(
            EmptyStateConfig(
                icon_name="edit-find-symbolic",
                title="No matching entries",
                subtitle="Try a different search term",
                icon_size=64,
                margin_vertical=48,
                title_css_class="title-2",
            )
        )

    def _create_loading_state(self) -> Gtk.ListBoxRow:
        """
        Create a loading state placeholder row widget.

        Returns:
            Gtk.ListBoxRow containing spinner and loading text
        """
        return create_loading_row("Loading quarantine entries...", margin_vertical=48)

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
            # Store entries for filtering support
            self._all_entries = entries

            # Update storage info (pass entries to avoid synchronous DB calls on main thread)
            self._update_storage_info(entries)

            # Update last refresh time to prevent duplicate refreshes
            self._last_refresh_time = time.time()

            # Handle empty state - placeholder will be shown automatically
            if not entries:
                self._clear_old_button.set_sensitive(False)
                # Clear the pagination controller
                self._pagination.set_entries([])
                return False

            # If search is active, apply filter to maintain filtered view across refresh
            if self._search_query:
                # Update filtered entries based on current search query
                self._filtered_entries = self._filter_entries()

                # If filtered results are empty, show placeholder and return
                if not self._filtered_entries:
                    self._clear_old_button.set_sensitive(True)
                    # Pass all_entries to controller, controller's entries_to_display will return empty filtered list
                    self._pagination.set_entries(self._all_entries)
                    return False

            # Use controller to display entries with pagination
            # Always pass all_entries - controller's entries_to_display override handles filtering
            entries_label = "filtered entries" if self._search_query else "entries"
            self._pagination.set_entries(self._all_entries, entries_label)

            # Enable clear old button if there are entries
            self._clear_old_button.set_sensitive(True)

        finally:
            self._set_loading_state(False)

            # Invoke callback if registered
            if self._on_quarantine_changed:
                entry_count = len(entries)
                self._on_quarantine_changed(entry_count)

        return False

    @property
    def _entries_to_display(self) -> list[QuarantineEntry]:
        """
        Get the appropriate entry list for display.

        Returns _filtered_entries when search is active (non-empty search query),
        otherwise returns _all_entries.

        Returns:
            List of QuarantineEntry objects to display
        """
        if self._search_query:
            return self._filtered_entries
        return self._all_entries

    # Backward compatibility properties and methods for tests
    @property
    def _displayed_count(self) -> int:
        """Get the current displayed count from pagination controller (backward compatibility)."""
        return self._pagination.displayed_count if hasattr(self, "_pagination") else 0

    @_displayed_count.setter
    def _displayed_count(self, value: int):
        """Set the displayed count on pagination controller (backward compatibility)."""
        if hasattr(self, "_pagination"):
            self._pagination._displayed_count = value

    @property
    def _load_more_row(self):
        """Get the load more row from pagination controller (backward compatibility)."""
        return self._pagination.load_more_row if hasattr(self, "_pagination") else None

    @_load_more_row.setter
    def _load_more_row(self, value):
        """Set the load more row on pagination controller (backward compatibility)."""
        if hasattr(self, "_pagination"):
            self._pagination._load_more_row = value

    def _display_entry_batch(self, start_index: int, count: int):
        """Display a batch of entries (backward compatibility - delegates to pagination controller)."""
        if hasattr(self, "_pagination"):
            self._pagination.display_batch(start_index, count)

    def _add_load_more_button(self, entries_label: str = "entries"):
        """Add load more button (backward compatibility - delegates to pagination controller)."""
        if hasattr(self, "_pagination"):
            self._pagination.add_load_more_button(entries_label)

    def _on_load_more_clicked(self, button):
        """Handle load more button click (backward compatibility - delegates to pagination controller)."""
        if hasattr(self, "_pagination"):
            self._pagination.load_more()

    def _on_show_all_clicked(self, button):
        """Handle show all button click (backward compatibility - delegates to pagination controller)."""
        if hasattr(self, "_pagination"):
            self._pagination.show_all()

    def _on_refresh_clicked(self, button):
        """Handle refresh button click."""
        # Debounce: don't refresh if last refresh was less than 1 second ago
        current_time = time.time()
        if current_time - self._last_refresh_time < 1.0:
            return

        self._load_entries_async()

    def _on_clear_old_clicked(self, button):
        """Handle clear old items button click."""
        self._manager.cleanup_old_entries_async(callback=self._on_cleanup_completed)

    def _on_search_changed(self, search_entry):
        """
        Handle search entry text change with debouncing.

        Cancels any pending search and schedules a new one after 250ms delay
        to avoid filtering on every keystroke.

        Args:
            search_entry: The Gtk.SearchEntry widget
        """
        # Cancel any pending search timeout
        if self._search_timeout_id is not None:
            GLib.source_remove(self._search_timeout_id)
            self._search_timeout_id = None

        # Get the current search query
        self._search_query = search_entry.get_text().strip()

        # Schedule filter update after 250ms delay
        self._search_timeout_id = GLib.timeout_add(250, self._execute_search_filter)

    def _execute_search_filter(self) -> bool:
        """
        Execute the search filter operation.

        This is the callback invoked after the debounce delay. Applies the
        current search filter to the quarantine list.

        Returns:
            False to prevent GLib.timeout_add from repeating
        """
        # Clear timeout ID since the timeout has been consumed
        self._search_timeout_id = None

        # Apply the search filter
        self._apply_search_filter()

        return False

    def _filter_entries(self) -> list[QuarantineEntry]:
        """
        Filter quarantine entries based on current search query.

        Performs case-insensitive substring matching against both the threat name
        and original file path. An empty query returns all entries.

        Returns:
            List of QuarantineEntry objects matching the search query
        """
        # Empty query returns all entries
        if not self._search_query:
            return self._all_entries

        # Normalize search query for case-insensitive comparison
        query_lower = self._search_query.lower()

        # Filter entries matching threat_name or original_path
        filtered = [
            entry
            for entry in self._all_entries
            if query_lower in (entry.threat_name or "").lower()
            or query_lower in (entry.original_path or "").lower()
        ]

        return filtered

    def _apply_search_filter(self):
        """
        Apply current search filter to the quarantine list.

        Filters entries based on _search_query, clears the listbox,
        resets pagination state, and displays filtered results.
        This is the main entry point for triggering a filter update.
        """
        # Update filtered entries based on current search query
        self._filtered_entries = self._filter_entries()

        # Update storage info to reflect filtered count
        self._update_storage_info(self._all_entries)

        # Handle empty filtered results - show appropriate placeholder
        if not self._filtered_entries:
            # If search is active but has no matches (all_entries exists but filtered is empty),
            # show the no-results placeholder
            if self._search_query and self._all_entries:
                self._listbox.set_placeholder(self._create_no_results_state())
            else:
                # Otherwise show empty state placeholder (for when quarantine is actually empty)
                self._listbox.set_placeholder(self._create_empty_state())
            # Reset controller state - pass all_entries so controller maintains full dataset
            # Controller's entries_to_display override will return empty filtered list
            self._pagination.set_entries(self._all_entries)
            return

        # Results exist - ensure empty state placeholder is set (for when all entries are removed later)
        self._listbox.set_placeholder(self._create_empty_state())

        # Reset controller and provide all entries
        # Controller's overridden entries_to_display property will return filtered entries
        # This allows controller to maintain full dataset while displaying filtered results
        entries_label = "filtered entries" if self._search_query else "entries"
        self._pagination.set_entries(self._all_entries, entries_label)

    def _on_cleanup_completed(self, removed_count: int) -> bool:
        """
        Handle completion of cleanup operation.

        Args:
            removed_count: Number of entries removed

        Returns:
            False to prevent GLib.idle_add from repeating
        """
        # Show status message
        if removed_count > 0:
            msg = f"Removed {removed_count} old quarantine entries"
            self._status_banner.set_title(msg)
            self._status_banner.set_revealed(True)

            # Refresh the list
            self._load_entries_async()
        else:
            msg = "No old entries found to remove"
            self._status_banner.set_title(msg)
            self._status_banner.set_revealed(True)

        return False

    def _on_view_mapped(self, widget):
        """
        Handle view being mapped (shown on screen).

        Refreshes the quarantine list when the view becomes visible.

        Args:
            widget: The widget that was mapped
        """
        self._load_entries_async()

    def _set_loading_state(self, is_loading: bool):
        """
        Set the loading state and update UI accordingly.

        Args:
            is_loading: True if loading, False otherwise
        """
        self._is_loading = is_loading
        if is_loading:
            self._spinner.set_visible(True)
            self._spinner.start()
            self._refresh_button.set_sensitive(False)
        else:
            self._spinner.set_visible(False)
            self._spinner.stop()
            self._refresh_button.set_sensitive(True)

    def _update_storage_info(self, entries: list[QuarantineEntry]):
        """
        Update the storage info display with total size and item count.

        When search is active, shows filtered count vs total count (e.g., '5 of 20 items').
        Total size always reflects the full quarantine storage.

        Args:
            entries: List of quarantine entries to calculate size from
        """
        total_size = sum(entry.file_size for entry in entries if entry.file_size)
        total_count = len(entries)

        # Update count label - show filtered vs total when search is active
        if self._search_query and self._filtered_entries is not None:
            filtered_count = len(self._filtered_entries)
            if filtered_count == 1 and total_count == 1:
                item_text = "1 of 1 item"
            elif filtered_count == 1:
                item_text = f"1 of {total_count} items"
            else:
                item_text = f"{filtered_count} of {total_count} items"
        else:
            # No search active - show normal count
            item_text = f"{total_count} item" if total_count == 1 else f"{total_count} items"

        self._count_label.set_text(item_text)

        # Update size display - always shows total quarantine size
        size_str = format_file_size(total_size)
        self._storage_row.set_subtitle(size_str)

    def _create_entry_row(self, entry: QuarantineEntry) -> Gtk.ListBoxRow:
        """
        Create a list row widget for a quarantine entry.

        Args:
            entry: QuarantineEntry object to display

        Returns:
            Gtk.ListBoxRow containing the entry information
        """
        row = Gtk.ListBoxRow()

        # Main container
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.set_margin_top(12)
        container.set_margin_bottom(12)
        container.set_margin_start(12)
        container.set_margin_end(12)
        container.set_spacing(6)

        # Header: threat name
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_spacing(12)

        # Threat icon
        icon = Gtk.Image()
        icon.set_from_icon_name(resolve_icon_name("dialog-warning-symbolic"))
        icon.set_pixel_size(20)
        icon.add_css_class("dim-label")
        header_box.append(icon)

        # Threat name
        threat_label = Gtk.Label()
        threat_label.set_text(entry.threat_name or "Unknown Threat")
        threat_label.set_halign(Gtk.Align.START)
        threat_label.add_css_class("heading")
        header_box.append(threat_label)

        container.append(header_box)

        # Original path
        path_label = Gtk.Label()
        path_label.set_text(f"Path: {entry.original_path}")
        path_label.set_halign(Gtk.Align.START)
        path_label.add_css_class("monospace")
        path_label.add_css_class("dim-label")
        path_label.set_wrap(True)
        path_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        container.append(path_label)

        # Metadata row: date and size
        metadata_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        metadata_box.set_spacing(24)

        # Quarantine date
        date_label = Gtk.Label()
        if entry.detection_date:
            try:
                quarantine_dt = datetime.fromisoformat(entry.detection_date)
                date_str = quarantine_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                date_str = entry.detection_date
        else:
            date_str = "Unknown"
        date_label.set_text(f"Quarantined: {date_str}")
        date_label.add_css_class("dim-label")
        date_label.add_css_class("caption")
        metadata_box.append(date_label)

        # File size
        size_label = Gtk.Label()
        size_label.set_text(f"Size: {format_file_size(entry.file_size)}")
        size_label.add_css_class("dim-label")
        size_label.add_css_class("caption")
        metadata_box.append(size_label)

        container.append(metadata_box)

        # Actions row
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        actions_box.set_spacing(6)
        actions_box.set_halign(Gtk.Align.END)

        # Restore button
        restore_btn = Gtk.Button()
        restore_btn.set_label("Restore")
        restore_btn.add_css_class("pill")
        restore_btn.connect("clicked", self._on_restore_clicked, entry)
        actions_box.append(restore_btn)

        # Delete button
        delete_btn = Gtk.Button()
        delete_btn.set_label("Delete")
        delete_btn.add_css_class("pill")
        delete_btn.add_css_class("destructive-action")
        delete_btn.connect("clicked", self._on_delete_clicked, entry)
        actions_box.append(delete_btn)

        container.append(actions_box)

        row.set_child(container)
        return row

    def _on_restore_clicked(self, button, entry: QuarantineEntry):
        """
        Handle restore button click for a quarantine entry.

        Args:
            button: The button that was clicked
            entry: The QuarantineEntry to restore
        """
        self._manager.restore_file_async(entry.id, callback=self._on_restore_completed)

    def _on_restore_completed(self, result: QuarantineResult) -> bool:
        """
        Handle completion of restore operation.

        Args:
            result: QuarantineResult object with operation status

        Returns:
            False to prevent GLib.idle_add from repeating
        """
        if result.status == QuarantineStatus.SUCCESS:
            self._status_banner.set_title("File restored successfully")
            self._status_banner.set_revealed(True)
            # Refresh the list after successful restore
            GLib.timeout_add(500, self._load_entries_async)
        else:
            self._status_banner.set_title(result.error_message or "Failed to restore file")
            self._status_banner.set_revealed(True)

        return False

    def _on_delete_clicked(self, button, entry: QuarantineEntry):
        """
        Handle delete button click for a quarantine entry.

        Args:
            button: The button that was clicked
            entry: The QuarantineEntry to delete
        """
        self._manager.delete_file_async(entry.id, callback=self._on_delete_completed)

    def _on_delete_completed(self, result: QuarantineResult) -> bool:
        """
        Handle completion of delete operation.

        Args:
            result: QuarantineResult object with operation status

        Returns:
            False to prevent GLib.idle_add from repeating
        """
        if result.status == QuarantineStatus.SUCCESS:
            self._status_banner.set_title("File deleted successfully")
            self._status_banner.set_revealed(True)
            # Refresh the list after successful delete
            GLib.timeout_add(500, self._load_entries_async)
        else:
            self._status_banner.set_title(result.error_message or "Failed to delete file")
            self._status_banner.set_revealed(True)

        return False

    def register_quarantine_changed_callback(self, callback):
        """
        Register a callback to be invoked when quarantine content changes.

        Args:
            callback: Callable that receives entry_count as parameter
        """
        self._on_quarantine_changed = callback
