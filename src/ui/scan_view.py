# ClamUI Scan View
"""
Scan interface component for ClamUI with folder picker, scan button, and results display.
"""

import logging
import os
import tempfile
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from ..core.quarantine import QuarantineManager
from ..core.scanner import Scanner, ScanResult, ScanStatus
from ..core.utils import (
    format_scan_path,
    is_flatpak,
    validate_dropped_files,
)
from .profile_dialogs import ProfileListDialog
from .scan_results_dialog import ScanResultsDialog
from .utils import add_row_icon
from .view_helpers import StatusLevel, set_status_class

if TYPE_CHECKING:
    from ..core.settings_manager import SettingsManager
    from ..profiles.models import ScanProfile
    from ..profiles.profile_manager import ProfileManager

logger = logging.getLogger(__name__)

# EICAR test string - industry-standard antivirus test pattern
# This is NOT malware - it's a safe test string recognized by all AV software
EICAR_TEST_STRING = r"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class ScanView(Gtk.Box):
    """
    Scan interface component for ClamUI.

    Provides the main scanning interface with:
    - Folder/file selection
    - Scan button with progress indication
    - Results display area
    """

    def __init__(self, settings_manager: "SettingsManager | None" = None, **kwargs):
        """
        Initialize the scan view.

        Args:
            settings_manager: Optional SettingsManager for exclusion patterns
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        # Store settings manager
        self._settings_manager = settings_manager

        # Initialize scanner with settings manager for exclusion patterns
        self._scanner = Scanner(settings_manager=settings_manager)

        # Initialize quarantine manager
        self._quarantine_manager = QuarantineManager()

        # Current selected paths (supports multiple targets)
        self._selected_paths: list[str] = []
        # Normalized paths for O(1) duplicate checking
        self._normalized_paths: set[str] = set()

        # Scanning state
        self._is_scanning = False
        self._cancel_all_requested = False

        # Temp file path for EICAR test (for cleanup)
        self._eicar_temp_path: str = ""

        # Current scan result (for dialog)
        self._current_result: ScanResult | None = None

        # Scan state change callback (for tray integration)
        self._on_scan_state_changed = None

        # Progress section state
        self._progress_section: Gtk.Box | None = None
        self._progress_bar: Gtk.ProgressBar | None = None
        self._progress_label: Gtk.Label | None = None
        self._pulse_timeout_id: int | None = None

        # View results section state
        self._view_results_section: Gtk.Box | None = None
        self._view_results_button: Gtk.Button | None = None

        # Profile management state
        self._selected_profile: ScanProfile | None = None
        self._profile_list: list[ScanProfile] = []
        self._profile_string_list: Gtk.StringList | None = None
        self._profile_dropdown: Gtk.DropDown | None = None

        # Set up the UI
        self._setup_ui()

    def _setup_ui(self):
        """Set up the scan view UI layout."""
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_spacing(12)

        # Set up CSS for drag-and-drop visual feedback
        self._setup_drop_css()

        # Create the profile selector section
        self._create_profile_section()

        # Create the selection section
        self._create_selection_section()

        # Create the scan button section
        self._create_scan_section()

        # Create the progress section (hidden initially)
        self._create_progress_section()

        # Create the view results button (hidden initially)
        self._create_view_results_section()

        # Create the backend indicator
        self._create_backend_indicator()

        # Create the status bar
        self._create_status_bar()

        # Set up drag-and-drop support
        self._setup_drop_target()

    def _setup_drop_css(self):
        """Set up CSS styling for drag-and-drop visual feedback and severity badges."""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(
            """
            .drop-active {
                border: 2px dashed @accent_color;
                border-radius: 12px;
                background-color: alpha(@accent_bg_color, 0.1);
            }

            /* Severity badge styles */
            .severity-badge {
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.85em;
                font-weight: bold;
            }

            /* Critical severity: Ransomware, rootkits, bootkits - most dangerous threats
               Uses @error_bg_color (red) to indicate danger and urgency
               Adapts to theme (darker in light mode, lighter in dark mode) */
            .severity-critical {
                background-color: @error_bg_color;
                color: white;
            }

            /* High severity: Trojans, worms, backdoors, exploits - serious threats
               Uses lighter(@error_bg_color) to create orange tone (between red and yellow)
               Semantically between critical error and medium warning */
            .severity-high {
                background-color: lighter(@error_bg_color);
                color: white;
            }

            /* Medium severity: Adware, PUAs (Potentially Unwanted Applications), spyware
               Uses @warning_bg_color and @warning_fg_color (yellow/amber) for caution
               Standard warning semantics for concerning but less severe threats */
            .severity-medium {
                background-color: @warning_bg_color;
                color: @warning_fg_color;
            }

            /* Low severity: Test signatures (EICAR), generic/heuristic detections
               Uses @accent_bg_color (blue) for informational, low-risk items
               Accent color indicates "note this" without alarm */
            .severity-low {
                background-color: @accent_bg_color;
                color: white;
            }

            /* Threat card styling */
            .threat-card {
                margin: 4px 0;
            }

            .recommended-action {
                padding: 8px 12px;
                background-color: alpha(@card_bg_color, 0.5);
                border-radius: 6px;
                margin: 4px 0;
            }

            /* Large result warning banner */
            .large-result-warning {
                background-color: alpha(@warning_color, 0.15);
                border: 1px solid @warning_color;
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 8px;
            }

            /* Load more button styling */
            .load-more-row {
                padding: 12px;
            }

            /* Progress section styling */
            .progress-section {
                padding: 12px 0;
            }

            .progress-bar-compact {
                min-height: 6px;
                border-radius: 3px;
            }

            .progress-status {
                font-size: 0.9em;
                margin-top: 6px;
            }

            /* Stats section styling */
            .stats-row {
                padding: 4px 12px;
            }

            .stats-label {
                min-width: 120px;
            }

            .stats-value {
                font-weight: bold;
            }

            .stats-icon-success {
                color: @success_color;
            }

            .stats-icon-warning {
                color: @warning_color;
            }

            .stats-icon-error {
                color: @error_color;
            }

            /* Threat action buttons */
            .threat-actions {
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px solid alpha(@borders, 0.3);
            }

            .threat-action-btn {
                min-height: 24px;
                padding: 4px 10px;
                font-size: 0.85em;
            }

            .threat-action-btn.quarantined {
                opacity: 0.6;
            }

            .threat-action-btn.excluded {
                opacity: 0.6;
            }
        """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _setup_drop_target(self):
        """Set up drag-and-drop file handling."""
        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect("drop", self._on_drop)
        drop_target.connect("enter", self._on_drag_enter)
        drop_target.connect("leave", self._on_drag_leave)
        # Set propagation phase to CAPTURE so events are intercepted before
        # reaching child widgets (like TextView) that might swallow them
        drop_target.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        # Add drop target to the entire ScanView widget
        self.add_controller(drop_target)

    def _on_drop(self, target, value, x, y) -> bool:
        """
        Handle file drop.

        Extracts file paths from the dropped Gdk.FileList and adds all valid
        paths as scan targets.

        Args:
            target: The DropTarget controller
            value: The dropped value (Gdk.FileList)
            x: X coordinate of drop location
            y: Y coordinate of drop location

        Returns:
            True if drop was accepted, False otherwise
        """
        # Remove visual feedback (leave signal is not emitted on drop)
        self.remove_css_class("drop-active")

        # Reject drops during active scan
        if self._is_scanning:
            self._show_drop_error("Scan in progress - please wait until the current scan completes")
            return False

        # Extract files from Gdk.FileList
        files = value.get_files()
        if not files:
            self._show_drop_error("No files were dropped")
            return False

        # Get paths from Gio.File objects (None for remote files)
        paths = [gio_file.get_path() for gio_file in files]

        # Validate paths using utility function
        valid_paths, errors = validate_dropped_files(paths)

        if valid_paths:
            # Add all valid paths to the selection
            for path in valid_paths:
                self._add_path(path)
            return True

        # No valid paths - show error and reject drop
        if errors:
            # Show the first error (most relevant for user)
            self._show_drop_error(errors[0])
        else:
            self._show_drop_error("Unable to accept dropped files")
        return False

    def _on_drag_enter(self, target, x, y) -> Gdk.DragAction:
        """
        Visual feedback when drag enters the drop zone.

        Adds the 'drop-active' CSS class to highlight the widget
        as a valid drop target.

        Args:
            target: The DropTarget controller
            x: X coordinate of drag position
            y: Y coordinate of drag position

        Returns:
            Gdk.DragAction.COPY to indicate the drop is accepted
        """
        self.add_css_class("drop-active")
        return Gdk.DragAction.COPY

    def _on_drag_leave(self, target):
        """
        Cleanup visual feedback when drag leaves the drop zone.

        Removes the 'drop-active' CSS class to restore normal appearance.

        Args:
            target: The DropTarget controller
        """
        self.remove_css_class("drop-active")

    def _on_status_banner_dismissed(self, banner):
        """
        Handle status banner dismiss button click.

        Hides the status banner when the user clicks the Dismiss button.

        Args:
            banner: The Adw.Banner that was dismissed
        """
        banner.set_revealed(False)

    def _show_drop_error(self, message: str):
        """
        Display an error message for invalid file drops.

        Uses the status banner to show a user-friendly error message
        when dropped files cannot be accepted (remote files, permission
        errors, non-existent paths, etc.).

        Args:
            message: The error message to display
        """
        self._status_banner.set_title(message)
        set_status_class(self._status_banner, StatusLevel.ERROR)
        self._status_banner.set_revealed(True)
        self._show_toast(message)

    def _show_toast(self, message: str) -> None:
        """
        Show a toast notification for user feedback.

        Args:
            message: The message to display in the toast
        """
        root = self.get_root()
        if root is None:
            return
        if hasattr(root, "add_toast"):
            toast = Adw.Toast.new(message)
            root.add_toast(toast)

    def _create_profile_section(self):
        """Create the scan profile selector section."""
        # Profile selection frame
        profile_group = Adw.PreferencesGroup()
        profile_group.set_title("Scan Profile")
        self._profile_group = profile_group

        # Profile selection row
        profile_row = Adw.ActionRow()
        profile_row.set_title("Profile")
        add_row_icon(profile_row, "document-properties-symbolic")
        self._profile_row = profile_row

        # Create string list for dropdown
        self._profile_string_list = Gtk.StringList()
        self._profile_string_list.append("No Profile (Manual)")

        # Create the dropdown
        self._profile_dropdown = Gtk.DropDown()
        self._profile_dropdown.set_model(self._profile_string_list)
        self._profile_dropdown.set_selected(0)  # Default to "No Profile"
        self._profile_dropdown.set_valign(Gtk.Align.CENTER)
        self._profile_dropdown.connect("notify::selected", self._on_profile_selected)

        # Create manage profiles button
        manage_profiles_btn = Gtk.Button()
        manage_profiles_btn.set_icon_name("emblem-system-symbolic")
        manage_profiles_btn.set_tooltip_text("Manage profiles")
        manage_profiles_btn.add_css_class("flat")
        manage_profiles_btn.set_valign(Gtk.Align.CENTER)
        manage_profiles_btn.connect("clicked", self._on_manage_profiles_clicked)
        self._manage_profiles_btn = manage_profiles_btn

        # Button box to contain dropdown and manage button
        profile_control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        profile_control_box.set_valign(Gtk.Align.CENTER)
        profile_control_box.append(self._profile_dropdown)
        profile_control_box.append(manage_profiles_btn)

        profile_row.add_suffix(profile_control_box)
        profile_group.add(profile_row)

        self.append(profile_group)

        # Load profiles after widget is realized (to access profile manager)
        self.connect("realize", self._on_realize_load_profiles)

    def _on_realize_load_profiles(self, widget):
        """Load profiles when the widget is realized and has access to the application."""
        self.refresh_profiles()

    def _get_profile_manager(self) -> "ProfileManager | None":
        """
        Get the ProfileManager from the application.

        Returns:
            ProfileManager instance or None if not available
        """
        root = self.get_root()
        if root is None:
            return None

        app = root.get_application() if hasattr(root, "get_application") else None
        if app is None:
            return None

        if hasattr(app, "profile_manager"):
            return app.profile_manager

        return None

    def refresh_profiles(self):
        """
        Refresh the profile dropdown with current profiles from ProfileManager.

        This method can be called externally to update the dropdown when
        profiles are added, edited, or deleted.
        """
        profile_manager = self._get_profile_manager()
        if profile_manager is None:
            logger.debug("ProfileManager not available, skipping profile refresh")
            return

        # Store current selection to restore if possible
        current_selection = self._profile_dropdown.get_selected() if self._profile_dropdown else 0
        current_profile_id = None
        if current_selection > 0 and current_selection - 1 < len(self._profile_list):
            current_profile_id = self._profile_list[current_selection - 1].id

        # Get updated profile list
        self._profile_list = profile_manager.list_profiles()

        # Clear and rebuild the string list
        # GTK4 StringList doesn't have a clear method, so rebuild
        n_items = self._profile_string_list.get_n_items()
        for _ in range(n_items):
            self._profile_string_list.remove(0)

        # Add "No Profile" option
        self._profile_string_list.append("No Profile (Manual)")

        # Add each profile
        for profile in self._profile_list:
            self._profile_string_list.append(profile.name)

        # Restore selection
        if current_profile_id:
            for i, profile in enumerate(self._profile_list):
                if profile.id == current_profile_id:
                    self._profile_dropdown.set_selected(i + 1)  # +1 for "No Profile" option
                    return

        # Default to "No Profile"
        self._profile_dropdown.set_selected(0)

    def _on_profile_selected(self, dropdown, param_spec):
        """
        Handle profile selection change.

        Args:
            dropdown: The Gtk.DropDown that was changed
            param_spec: The GParamSpec for the 'selected' property
        """
        selected_idx = dropdown.get_selected()

        if selected_idx == 0:
            # "No Profile" selected
            self._selected_profile = None
        else:
            # Profile selected
            profile_idx = selected_idx - 1  # Adjust for "No Profile" option
            if 0 <= profile_idx < len(self._profile_list):
                self._selected_profile = self._profile_list[profile_idx]
                # Apply all profile targets to the path list
                if self._selected_profile.targets:
                    self._clear_paths()
                    valid_count = 0
                    for target in self._selected_profile.targets:
                        # Expand ~ in paths
                        expanded = os.path.expanduser(target) if target.startswith("~") else target
                        if os.path.exists(expanded):
                            self._add_path(expanded)
                            valid_count += 1
                    # Warn if no valid targets were found
                    if valid_count == 0:
                        self._show_toast(
                            f"Profile '{self._selected_profile.name}' has no valid targets"
                        )
            else:
                self._selected_profile = None

    def _on_manage_profiles_clicked(self, button):
        """
        Handle manage profiles button click.

        Opens the profile management dialog.

        Args:
            button: The Gtk.Button that was clicked
        """
        root = self.get_root()
        if root is not None and isinstance(root, Gtk.Window):
            profile_manager = self._get_profile_manager()
            dialog = ProfileListDialog(profile_manager=profile_manager)
            # Set callback for when a profile is selected to run
            dialog.set_on_profile_selected(self._on_profile_run_from_dialog)
            # Refresh profiles when dialog is closed
            dialog.connect("closed", self._on_profiles_dialog_closed)
            dialog.present(root)

    def _on_profiles_dialog_closed(self, dialog):
        """
        Handle profile dialog closed.

        Refreshes the profile dropdown to reflect any changes.

        Args:
            dialog: The ProfileListDialog that was closed
        """
        self.refresh_profiles()

    def _on_profile_run_from_dialog(self, profile: "ScanProfile"):
        """
        Handle profile selection from manage profiles dialog.

        Selects the profile in the dropdown and starts the scan.

        Args:
            profile: The ScanProfile that was selected to run
        """
        # Refresh profiles first to ensure the list is up to date
        self.refresh_profiles()
        # Select the profile in the dropdown
        self.set_selected_profile(profile.id)
        # Start the scan with the selected profile
        self._start_scan()

    def _create_selection_section(self):
        """Create the file/folder selection UI section with multi-path support."""
        # Container for selection UI
        self._selection_group = Adw.PreferencesGroup()
        self._selection_group.set_title("Scan Targets")
        self._selection_group.set_description("Drop files here or click Add")

        # Header suffix with Add buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)

        # Add Files button
        self._add_files_button = Gtk.Button()
        self._add_files_button.set_icon_name("document-new-symbolic")
        self._add_files_button.set_tooltip_text("Add files")
        self._add_files_button.add_css_class("flat")
        self._add_files_button.connect("clicked", self._on_select_file_clicked)
        button_box.append(self._add_files_button)

        # Add Folders button
        self._add_folders_button = Gtk.Button()
        self._add_folders_button.set_icon_name("folder-new-symbolic")
        self._add_folders_button.set_tooltip_text("Add folders")
        self._add_folders_button.add_css_class("flat")
        self._add_folders_button.connect("clicked", self._on_select_folder_clicked)
        button_box.append(self._add_folders_button)

        # Clear All button (visible when multiple paths exist)
        self._clear_all_button = Gtk.Button()
        self._clear_all_button.set_icon_name("edit-clear-all-symbolic")
        self._clear_all_button.set_tooltip_text("Clear all")
        self._clear_all_button.add_css_class("flat")
        self._clear_all_button.connect("clicked", self._on_clear_all_clicked)
        self._clear_all_button.set_visible(False)
        button_box.append(self._clear_all_button)

        self._selection_group.set_header_suffix(button_box)

        # Paths list box
        self._paths_listbox = Gtk.ListBox()
        self._paths_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._paths_listbox.add_css_class("boxed-list")

        # Placeholder row for empty list
        self._paths_placeholder = Adw.ActionRow()
        self._paths_placeholder.set_title("No targets added")
        self._paths_placeholder.set_subtitle("Drop files here or click Add Files/Folders")
        add_row_icon(self._paths_placeholder, "folder-symbolic")
        self._paths_placeholder.add_css_class("dim-label")
        self._paths_listbox.append(self._paths_placeholder)

        self._selection_group.add(self._paths_listbox)
        self.append(self._selection_group)

    def _create_path_row(self, path: str) -> Adw.ActionRow:
        """
        Create a row for displaying a scan target path.

        Args:
            path: The file or folder path to display

        Returns:
            Configured Adw.ActionRow with path and remove button
        """
        row = Adw.ActionRow()

        # Format path for display
        formatted_path = format_scan_path(path)
        row.set_title(formatted_path)

        # Set tooltip with full path
        row.set_tooltip_text(path)

        # Choose icon based on path type
        icon_name = "folder-symbolic" if os.path.isdir(path) else "text-x-generic-symbolic"
        add_row_icon(row, icon_name)

        # Remove button
        remove_btn = Gtk.Button()
        remove_btn.set_icon_name("edit-delete-symbolic")
        remove_btn.set_tooltip_text("Remove")
        remove_btn.add_css_class("flat")
        remove_btn.add_css_class("error")
        remove_btn.set_valign(Gtk.Align.CENTER)
        remove_btn.connect("clicked", lambda btn: self._on_remove_path_clicked(path, row))

        row.add_suffix(remove_btn)

        # Store the path as data on the row for later reference
        row.path = path

        return row

    def _on_remove_path_clicked(self, path: str, row: Adw.ActionRow):
        """
        Handle remove button click for a path row.

        Args:
            path: The path to remove
            row: The row widget to remove from the listbox
        """
        self._remove_path(path)

    def _on_clear_all_clicked(self, button):
        """Handle clear all button click."""
        self._clear_paths()

    def _on_select_file_clicked(self, button):
        """
        Handle select file button click.

        Opens a file chooser dialog to select one or more files.

        Args:
            button: The Gtk.Button that was clicked
        """
        root = self.get_root()
        if root is None or not isinstance(root, Gtk.Window):
            return

        dialog = Gtk.FileDialog()
        dialog.set_title("Select Files to Scan")

        # Set initial folder if a path is already selected
        if self._selected_paths:
            first_path = self._selected_paths[0]
            parent_dir = os.path.dirname(first_path) if os.path.isfile(first_path) else first_path
            if os.path.isdir(parent_dir):
                dialog.set_initial_folder(Gio.File.new_for_path(parent_dir))

        def on_files_selected(dialog, result):
            try:
                files = dialog.open_multiple_finish(result)
                if files:
                    # Clear existing selection before adding new files
                    self._clear_paths()
                    for i in range(files.get_n_items()):
                        file = files.get_item(i)
                        path = file.get_path()
                        if path:
                            self._add_path(path)
            except GLib.GError:
                pass  # User cancelled

        dialog.open_multiple(root, None, on_files_selected)

    def _on_select_folder_clicked(self, button):
        """
        Handle select folder button click.

        Opens a file chooser dialog to select one or more folders.

        Args:
            button: The Gtk.Button that was clicked
        """
        root = self.get_root()
        if root is None or not isinstance(root, Gtk.Window):
            return

        dialog = Gtk.FileDialog()
        dialog.set_title("Select Folders to Scan")

        # Set initial folder if a path is already selected
        if self._selected_paths:
            first_path = self._selected_paths[0]
            initial_dir = first_path if os.path.isdir(first_path) else os.path.dirname(first_path)
            if os.path.isdir(initial_dir):
                dialog.set_initial_folder(Gio.File.new_for_path(initial_dir))

        def on_folders_selected(dialog, result):
            try:
                files = dialog.select_multiple_folders_finish(result)
                if files:
                    # Clear existing selection before adding new folders
                    self._clear_paths()
                    for i in range(files.get_n_items()):
                        file = files.get_item(i)
                        path = file.get_path()
                        if path:
                            self._add_path(path)
            except GLib.GError:
                pass  # User cancelled

        dialog.select_multiple_folders(root, None, on_folders_selected)

    def _set_selected_path(self, path: str):
        """
        Set a single selected path, replacing any existing selection.

        This is a convenience method that clears the current selection
        and adds a single path. For adding multiple paths, use _add_path().

        Args:
            path: The file or folder path to scan
        """
        self._clear_paths()
        self._add_path(path)

    def _add_path(self, path: str) -> bool:
        """
        Add a path to the selection if not already present.

        Args:
            path: The file or folder path to add

        Returns:
            True if the path was added, False if it was a duplicate
        """
        # Normalize path for O(1) duplicate check
        normalized = os.path.normpath(path)
        if normalized in self._normalized_paths:
            return False

        self._normalized_paths.add(normalized)
        self._selected_paths.append(path)

        # Hide placeholder and add path row to listbox
        self._paths_placeholder.set_visible(False)
        row = self._create_path_row(path)
        self._paths_listbox.append(row)

        self._update_selection_header()
        return True

    def _remove_path(self, path: str) -> bool:
        """
        Remove a path from the selection.

        Args:
            path: The file or folder path to remove

        Returns:
            True if the path was removed, False if it wasn't in the list
        """
        normalized = os.path.normpath(path)
        if normalized not in self._normalized_paths:
            return False

        self._normalized_paths.discard(normalized)
        for i, existing in enumerate(self._selected_paths):
            if os.path.normpath(existing) == normalized:
                self._selected_paths.pop(i)

                # Find and remove the corresponding row from listbox
                child = self._paths_listbox.get_first_child()
                while child:
                    next_child = child.get_next_sibling()
                    # Check if this is a path row (not the placeholder)
                    if hasattr(child, "path") and os.path.normpath(child.path) == normalized:
                        self._paths_listbox.remove(child)
                        break
                    child = next_child

                # Show placeholder if no paths remain
                if not self._selected_paths:
                    self._paths_placeholder.set_visible(True)

                self._update_selection_header()
                return True
        return False

    def _clear_paths(self):
        """Clear all selected paths and reset the listbox."""
        self._selected_paths.clear()
        self._normalized_paths.clear()

        # Remove all path rows from listbox (keep placeholder)
        child = self._paths_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            # Remove only path rows, not the placeholder
            if child != self._paths_placeholder:
                self._paths_listbox.remove(child)
            child = next_child

        # Show placeholder
        self._paths_placeholder.set_visible(True)
        self._update_selection_header()

    def get_selected_paths(self) -> list[str]:
        """
        Get the list of currently selected paths.

        Returns:
            A copy of the selected paths list
        """
        return self._selected_paths.copy()

    def _update_selection_header(self):
        """Update the selection group header and Clear All button visibility."""
        path_count = len(self._selected_paths)

        # Update group title with count
        if path_count == 0:
            self._selection_group.set_title("Scan Targets")
            self._selection_group.set_description("Drop files here or click Add")
        elif path_count == 1:
            self._selection_group.set_title("Scan Target (1)")
            self._selection_group.set_description("")
        else:
            self._selection_group.set_title(f"Scan Targets ({path_count})")
            self._selection_group.set_description("")

        # Show/hide Clear All button
        self._clear_all_button.set_visible(path_count > 1)

    def _create_scan_section(self):
        """Create the scan control section."""
        scan_group = Adw.PreferencesGroup()

        # Button container
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_spacing(12)
        button_box.set_margin_top(8)
        button_box.set_margin_bottom(8)

        # Scan button
        self._scan_button = Gtk.Button()
        self._scan_button.set_label("Start Scan")
        self._scan_button.set_tooltip_text("Start Scan (F5)")
        self._scan_button.add_css_class("suggested-action")
        self._scan_button.set_size_request(150, -1)
        self._scan_button.connect("clicked", self._on_scan_clicked)
        button_box.append(self._scan_button)

        # EICAR Test button
        self._eicar_button = Gtk.Button()
        self._eicar_button.set_label("EICAR Test")
        self._eicar_button.set_tooltip_text(
            "Run a scan with EICAR test file to verify antivirus detection"
        )
        self._eicar_button.set_size_request(120, -1)
        self._eicar_button.connect("clicked", self._on_eicar_test_clicked)
        button_box.append(self._eicar_button)

        # Cancel button - hidden initially, shown during scanning
        self._cancel_button = Gtk.Button()
        self._cancel_button.set_label("Cancel")
        self._cancel_button.set_tooltip_text("Cancel the current scan")
        self._cancel_button.add_css_class("destructive-action")
        self._cancel_button.set_size_request(120, -1)
        self._cancel_button.set_visible(False)
        self._cancel_button.connect("clicked", self._on_cancel_clicked)
        button_box.append(self._cancel_button)

        scan_group.add(button_box)

        self.append(scan_group)

    def _create_progress_section(self):
        """Create the progress bar section (initially hidden)."""
        self._progress_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._progress_section.add_css_class("progress-section")
        self._progress_section.set_margin_start(12)
        self._progress_section.set_margin_end(12)
        self._progress_section.set_visible(False)

        # Pulsing progress bar
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.add_css_class("progress-bar-compact")
        self._progress_section.append(self._progress_bar)

        # Status label
        self._progress_label = Gtk.Label()
        self._progress_label.set_label("Scanning...")
        self._progress_label.add_css_class("progress-status")
        self._progress_label.add_css_class("dim-label")
        self._progress_label.set_xalign(0)
        self._progress_section.append(self._progress_label)

        self.append(self._progress_section)

    def _start_progress_pulse(self):
        """Start the progress bar pulsing animation."""
        if self._pulse_timeout_id is not None:
            return  # Already pulsing

        def pulse_callback():
            if self._progress_bar is not None:
                self._progress_bar.pulse()
            return True  # Continue pulsing

        self._pulse_timeout_id = GLib.timeout_add(100, pulse_callback)

    def _stop_progress_pulse(self):
        """Stop the progress bar pulsing animation and hide progress section."""
        if self._pulse_timeout_id is not None:
            GLib.source_remove(self._pulse_timeout_id)
            self._pulse_timeout_id = None

        if self._progress_section is not None:
            self._progress_section.set_visible(False)

    def _create_view_results_section(self):
        """Create the view results button section (initially hidden)."""
        self._view_results_section = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._view_results_section.set_halign(Gtk.Align.CENTER)
        self._view_results_section.set_margin_top(8)
        self._view_results_section.set_margin_bottom(8)
        self._view_results_section.set_visible(False)

        self._view_results_button = Gtk.Button()
        self._view_results_button.set_label("View Results")
        self._view_results_button.add_css_class("suggested-action")
        self._view_results_button.add_css_class("pill")
        self._view_results_button.set_size_request(200, -1)
        self._view_results_button.connect("clicked", self._on_view_results_clicked)
        self._view_results_section.append(self._view_results_button)

        self.append(self._view_results_section)

    def _show_view_results(self, threat_count: int):
        """Show the view results button with appropriate label."""
        if self._view_results_button is None or self._view_results_section is None:
            return

        if threat_count > 0:
            self._view_results_button.set_label(f"View Results ({threat_count} Threats)")
            self._view_results_button.remove_css_class("suggested-action")
            self._view_results_button.add_css_class("destructive-action")
        else:
            self._view_results_button.set_label("View Results")
            self._view_results_button.remove_css_class("destructive-action")
            self._view_results_button.add_css_class("suggested-action")

        self._view_results_section.set_visible(True)

    def _hide_view_results(self):
        """Hide the view results button."""
        if self._view_results_section is not None:
            self._view_results_section.set_visible(False)

    def _on_view_results_clicked(self, button):
        """Open the scan results dialog."""
        if self._current_result is None:
            return

        root = self.get_root()
        if root is None:
            return

        dialog = ScanResultsDialog(
            scan_result=self._current_result,
            quarantine_manager=self._quarantine_manager,
            settings_manager=self._settings_manager,
        )
        dialog.present(root)

    def _on_scan_clicked(self, button):
        """
        Handle scan button click.

        Starts the scan operation if a path is selected.

        Args:
            button: The Gtk.Button that was clicked
        """
        if not self._selected_paths:
            self._status_banner.set_title("Please select a file or folder to scan")
            set_status_class(self._status_banner, StatusLevel.WARNING)
            self._status_banner.set_revealed(True)
            return

        self._start_scanning()

    def _on_eicar_test_clicked(self, button):
        """
        Handle EICAR test button click.

        Creates an EICAR test file in a temp directory and scans it to verify
        antivirus detection is working properly.

        Args:
            button: The Gtk.Button that was clicked
        """
        try:
            # Create EICAR test file in system temp directory
            # In Flatpak, use /tmp explicitly so the host's clamdscan can access it
            temp_dir = "/tmp" if is_flatpak() else None
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                prefix="eicar_test_",
                delete=False,
                dir=temp_dir,
            ) as f:
                f.write(EICAR_TEST_STRING)
                self._eicar_temp_path = f.name

            # Set the EICAR file as scan target and start scan
            self._set_selected_path(self._eicar_temp_path)
            # The EICAR test path will be shown in the listbox via _set_selected_path
            self._start_scanning()

        except OSError as e:
            logger.error(f"Failed to create EICAR test file: {e}")
            self._status_banner.set_title(f"Failed to create EICAR test file: {e}")
            set_status_class(self._status_banner, StatusLevel.ERROR)
            self._status_banner.set_revealed(True)

    def _start_scanning(self):
        """Start the scanning process."""
        self._is_scanning = True
        self._cancel_all_requested = False
        self._scan_button.set_sensitive(False)
        self._eicar_button.set_sensitive(False)
        self._selection_group.set_sensitive(False)
        self._cancel_button.set_visible(True)

        # Update cancel button text based on number of targets
        path_count = len(self._selected_paths)
        if path_count > 1:
            self._cancel_button.set_label("Cancel All")
            self._cancel_button.set_tooltip_text("Cancel all remaining scans")
        else:
            self._cancel_button.set_label("Cancel")
            self._cancel_button.set_tooltip_text("Cancel the current scan")

        # Dismiss any previous status banner
        self._status_banner.set_revealed(False)

        # Hide previous results button
        self._hide_view_results()

        # Show progress section with status message
        if self._progress_section is not None:
            # Format path for display (handles Flatpak portal paths and truncation)
            if path_count == 1:
                display_path = format_scan_path(self._selected_paths[0])
                if len(display_path) > 50:
                    display_path = "..." + display_path[-47:]
                self._progress_label.set_label(f"Scanning {display_path}")
            else:
                self._progress_label.set_label(f"Scanning {path_count} items...")
            self._progress_section.set_visible(True)
            self._start_progress_pulse()

        # Notify external handlers (e.g., tray menu)
        if self._on_scan_state_changed:
            self._on_scan_state_changed(self._is_scanning)

        # Run scan in background
        GLib.idle_add(self._run_scan_async)

    def _run_scan_async(self):
        """Run the scan in a background thread."""
        import threading

        thread = threading.Thread(target=self._scan_worker, daemon=True)
        thread.start()
        return False

    def _scan_worker(self):
        """
        Perform the actual scan on all selected paths.

        This runs in a background thread to avoid blocking the UI.
        Scans each selected path sequentially and aggregates results.
        """
        try:
            if not self._selected_paths:
                # Should not happen, but handle gracefully
                result = ScanResult(
                    status=ScanStatus.ERROR,
                    path="",
                    stdout="",
                    stderr="",
                    exit_code=2,
                    infected_files=[],
                    scanned_files=0,
                    scanned_dirs=0,
                    infected_count=0,
                    error_message="No paths selected for scanning",
                    threat_details=[],
                )
                GLib.idle_add(self._on_scan_complete, result)
                return

            # Track aggregated results
            total_scanned_files = 0
            total_scanned_dirs = 0
            total_infected_count = 0
            all_infected_files: list[str] = []
            all_threat_details: list = []
            all_stdout: list[str] = []
            all_stderr: list[str] = []
            has_errors = False
            error_messages: list[str] = []
            final_status = ScanStatus.CLEAN

            target_count = len(self._selected_paths)

            for idx, target_path in enumerate(self._selected_paths, start=1):
                # Check if cancel all was requested before starting next target
                if self._cancel_all_requested:
                    logger.info(f"Cancel all requested, skipping target {idx}/{target_count}")
                    final_status = ScanStatus.CANCELLED
                    break

                # Update progress to show current target
                GLib.idle_add(self._update_scan_progress, idx, target_count, target_path)

                # Scan this target
                result = self._scanner.scan_sync(target_path)

                # Check if scan was cancelled (either this target or cancel all)
                if result.status == ScanStatus.CANCELLED or self._cancel_all_requested:
                    final_status = ScanStatus.CANCELLED
                    break

                # Aggregate results
                total_scanned_files += result.scanned_files
                total_scanned_dirs += result.scanned_dirs
                total_infected_count += result.infected_count
                all_infected_files.extend(result.infected_files)
                all_threat_details.extend(result.threat_details)

                if result.stdout:
                    all_stdout.append(f"=== {target_path} ===\n{result.stdout}")
                if result.stderr:
                    all_stderr.append(f"=== {target_path} ===\n{result.stderr}")

                # Track status
                if result.status == ScanStatus.ERROR:
                    has_errors = True
                    if result.error_message:
                        error_messages.append(f"{target_path}: {result.error_message}")
                elif result.status == ScanStatus.INFECTED:
                    final_status = ScanStatus.INFECTED

            # Determine final status if not cancelled
            if final_status != ScanStatus.CANCELLED:
                if total_infected_count > 0:
                    final_status = ScanStatus.INFECTED
                elif has_errors:
                    final_status = ScanStatus.ERROR
                else:
                    final_status = ScanStatus.CLEAN

            # Build aggregated result
            aggregated_result = ScanResult(
                status=final_status,
                path=(
                    ", ".join(self._selected_paths) if target_count > 1 else self._selected_paths[0]
                ),
                stdout="\n\n".join(all_stdout),
                stderr="\n\n".join(all_stderr),
                exit_code=(1 if final_status == ScanStatus.INFECTED else (2 if has_errors else 0)),
                infected_files=all_infected_files,
                scanned_files=total_scanned_files,
                scanned_dirs=total_scanned_dirs,
                infected_count=total_infected_count,
                error_message="; ".join(error_messages) if error_messages else None,
                threat_details=all_threat_details,
            )

            # Schedule UI update on main thread
            GLib.idle_add(self._on_scan_complete, aggregated_result)
        except Exception as e:
            logger.error(f"Scan error: {e}")
            GLib.idle_add(self._on_scan_error, str(e))

    def _update_scan_progress(self, current_idx: int, total_count: int, current_path: str):
        """
        Update the progress display with current scan target.

        This is called from the scan worker thread via GLib.idle_add
        to update the UI on the main thread.

        Args:
            current_idx: Current target index (1-based)
            total_count: Total number of targets
            current_path: Path currently being scanned
        """
        if self._progress_label is None:
            return

        # Format path for display
        display_path = format_scan_path(current_path)
        if len(display_path) > 40:
            display_path = "..." + display_path[-37:]

        if total_count == 1:
            self._progress_label.set_label(f"Scanning {display_path}")
        else:
            self._progress_label.set_label(
                f"Scanning target {current_idx}/{total_count}: {display_path}"
            )

    def _on_scan_complete(self, result: ScanResult):
        """
        Handle scan completion.

        Updates the UI with scan results and shows the view results button.

        Args:
            result: The ScanResult object containing scan findings
        """
        # Clean up temp EICAR file
        if self._eicar_temp_path and os.path.exists(self._eicar_temp_path):
            try:
                os.remove(self._eicar_temp_path)
            except OSError as e:
                logger.warning(f"Failed to clean up EICAR file: {e}")
            self._eicar_temp_path = ""

        # Stop progress animation and hide progress section
        self._stop_progress_pulse()

        # Store the result for dialog
        self._current_result = result

        # Update scanning state
        self._is_scanning = False
        self._scan_button.set_sensitive(True)
        self._eicar_button.set_sensitive(True)
        self._selection_group.set_sensitive(True)
        self._cancel_button.set_visible(False)

        # Notify external handlers
        if self._on_scan_state_changed:
            self._on_scan_state_changed(self._is_scanning)

        # Show view results button and update status banner
        if result.status == ScanStatus.INFECTED:
            self._show_view_results(result.infected_count)
            self._status_banner.set_title(
                f"Scan complete - {result.infected_count} threat(s) detected"
            )
            set_status_class(self._status_banner, StatusLevel.WARNING)
            self._status_banner.set_revealed(True)
        elif result.status == ScanStatus.CLEAN:
            self._show_view_results(0)
            self._status_banner.set_title("Scan complete - No threats found")
            set_status_class(self._status_banner, StatusLevel.SUCCESS)
            self._status_banner.set_revealed(True)
        elif result.status == ScanStatus.ERROR:
            self._show_view_results(0)
            error_detail = result.error_message or result.stderr or "Unknown error"
            self._status_banner.set_title(f"Scan error: {error_detail}")
            set_status_class(self._status_banner, StatusLevel.ERROR)
            self._status_banner.set_revealed(True)
            logger.error(
                f"Scan failed: {error_detail}, stdout={result.stdout!r}, stderr={result.stderr!r}"
            )
        else:
            self._show_view_results(0)
            self._status_banner.set_title(f"Scan completed with status: {result.status.value}")
            set_status_class(self._status_banner, StatusLevel.WARNING)
            self._status_banner.set_revealed(True)

    def _on_scan_error(self, error_msg: str):
        """
        Handle scan errors.

        Args:
            error_msg: The error message to display
        """
        # Clean up temp EICAR file if it exists
        if self._eicar_temp_path and os.path.exists(self._eicar_temp_path):
            try:
                os.remove(self._eicar_temp_path)
            except OSError:
                pass
            self._eicar_temp_path = ""

        # Stop progress animation and hide progress section
        self._stop_progress_pulse()

        self._is_scanning = False
        self._scan_button.set_sensitive(True)
        self._eicar_button.set_sensitive(True)
        self._selection_group.set_sensitive(True)
        self._cancel_button.set_visible(False)

        # Notify external handlers
        if self._on_scan_state_changed:
            self._on_scan_state_changed(self._is_scanning)

        self._status_banner.set_title(f"Scan error: {error_msg}")
        set_status_class(self._status_banner, StatusLevel.ERROR)
        self._status_banner.set_revealed(True)

    def _on_cancel_clicked(self, button: Gtk.Button) -> None:
        """Handle cancel button click.

        For multi-target scans, this sets _cancel_all_requested to skip
        remaining targets after the current scan completes or is cancelled.
        """
        logger.info("Scan cancelled by user")
        self._cancel_all_requested = True
        self._scanner.cancel()
        # The scan thread will check _cancel_all_requested and skip remaining targets
        # _on_scan_complete will handle the UI update

    def _create_backend_indicator(self):
        """Create a small indicator showing the active scan backend."""
        self._backend_label = Gtk.Label()
        self._backend_label.set_halign(Gtk.Align.CENTER)
        self._backend_label.add_css_class("dim-label")
        self._backend_label.add_css_class("caption")
        self._update_backend_label()
        self.append(self._backend_label)

    def _update_backend_label(self):
        """Update the backend label with the current backend name."""
        backend = self._scanner.get_active_backend()
        backend_names = {
            "daemon": "clamd (daemon)",
            "clamscan": "clamscan (standalone)",
        }
        backend_display = backend_names.get(backend, backend)
        self._backend_label.set_label(f"Backend: {backend_display}")

    def _create_status_bar(self):
        """Create the status banner."""
        self._status_banner = Adw.Banner()
        self._status_banner.set_title("Ready to scan")
        self._status_banner.set_button_label("Dismiss")
        self._status_banner.connect("button-clicked", self._on_status_banner_dismissed)
        self.append(self._status_banner)

    def set_on_scan_state_changed(self, callback):
        """
        Set a callback for scan state changes.

        Used by the main window to update the tray menu when scanning starts/stops.

        Args:
            callback: Function to call with (is_scanning: bool) parameter
        """
        self._on_scan_state_changed = callback

    def set_scan_state_changed_callback(self, callback):
        """Alias for set_on_scan_state_changed for backwards compatibility."""
        self.set_on_scan_state_changed(callback)

    def get_selected_profile(self) -> "ScanProfile | None":
        """Return the currently selected scan profile."""
        return self._selected_profile

    def set_selected_profile(self, profile_id: str) -> bool:
        """
        Set the selected profile by ID.

        Args:
            profile_id: The ID of the profile to select

        Returns:
            True if the profile was found and selected, False otherwise
        """
        if not self._profile_dropdown or not self._profile_list:
            return False

        for idx, profile in enumerate(self._profile_list):
            if profile.id == profile_id:
                # Add 1 to account for "No Profile" option at index 0
                self._profile_dropdown.set_selected(idx + 1)
                self._selected_profile = profile
                return True

        return False

    def _start_scan(self):
        """Start the scan operation programmatically."""
        self._on_scan_clicked(None)
