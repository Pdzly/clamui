# ClamUI Scan View
"""
Scan interface component for ClamUI with folder picker, scan button, and results display.
"""

import logging
import os
import tempfile
from typing import TYPE_CHECKING

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from ..core.scanner import Scanner, ScanResult, ScanStatus, ThreatDetail
from ..core.utils import (
    format_scan_path,
    check_clamav_installed,
    validate_dropped_files,
    format_results_as_text,
    copy_to_clipboard,
)
from .fullscreen_dialog import FullscreenLogDialog

if TYPE_CHECKING:
    from ..profiles.profile_manager import ProfileManager
    from ..profiles.models import ScanProfile

logger = logging.getLogger(__name__)

# EICAR test string - industry-standard antivirus test pattern
# This is NOT malware - it's a safe test string recognized by all AV software
EICAR_TEST_STRING = r"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

# Large result set thresholds for pagination
LARGE_RESULT_THRESHOLD = 50  # Show warning banner above this count
INITIAL_DISPLAY_LIMIT = 25  # Number of threats to display initially
LOAD_MORE_BATCH_SIZE = 25  # Number of threats to load per "Show More" click


class ScanView(Gtk.Box):
    """
    Scan interface component for ClamUI.

    Provides the main scanning interface with:
    - Folder/file selection
    - Scan button with progress indication
    - Results display area
    """

    def __init__(self, **kwargs):
        """
        Initialize the scan view.

        Args:
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        # Initialize scanner
        self._scanner = Scanner()

        # Current selected path
        self._selected_path: str = ""

        # Scanning state
        self._is_scanning = False

        # Temp file path for EICAR test (for cleanup)
        self._eicar_temp_path: str = ""

        # Pagination state for large result sets
        self._displayed_threat_count: int = 0
        self._all_threat_details: list = []
        self._load_more_row: Gtk.Box | None = None

        # Scan state change callback (for tray integration)
        self._on_scan_state_changed = None

        # Profile management state
        self._selected_profile: "ScanProfile | None" = None
        self._profile_list: list["ScanProfile"] = []
        self._profile_string_list: Gtk.StringList | None = None
        self._profile_dropdown: Gtk.DropDown | None = None

        # Set up the UI
        self._setup_ui()

        # Check ClamAV availability on load
        GLib.idle_add(self._check_clamav_status)

    def _setup_ui(self):
        """Set up the scan view UI layout."""
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_spacing(18)

        # Set up CSS for drag-and-drop visual feedback
        self._setup_drop_css()

        # Create the profile selector section
        self._create_profile_section()

        # Create the selection section
        self._create_selection_section()

        # Create the scan button section
        self._create_scan_section()

        # Create the results section
        self._create_results_section()

        # Create the status bar
        self._create_status_bar()

        # Set up drag-and-drop support
        self._setup_drop_target()

    def _setup_drop_css(self):
        """Set up CSS styling for drag-and-drop visual feedback and severity badges."""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string("""
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

            .severity-critical {
                background-color: #e01b24;
                color: white;
            }

            .severity-high {
                background-color: #ff7800;
                color: white;
            }

            .severity-medium {
                background-color: #f5c211;
                color: #3d3846;
            }

            .severity-low {
                background-color: #3584e4;
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
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _setup_drop_target(self):
        """Set up drag-and-drop file handling."""
        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect('drop', self._on_drop)
        drop_target.connect('enter', self._on_drag_enter)
        drop_target.connect('leave', self._on_drag_leave)
        # Set propagation phase to CAPTURE so events are intercepted before
        # reaching child widgets (like TextView) that might swallow them
        drop_target.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        # Add drop target to the entire ScanView widget
        self.add_controller(drop_target)

    def _on_drop(self, target, value, x, y) -> bool:
        """
        Handle file drop.

        Extracts file paths from the dropped Gdk.FileList and sets the first
        valid path as the scan target.

        Args:
            target: The DropTarget controller
            value: The dropped value (Gdk.FileList)
            x: X coordinate of drop location
            y: Y coordinate of drop location

        Returns:
            True if drop was accepted, False otherwise
        """
        # Remove visual feedback (leave signal is not emitted on drop)
        self.remove_css_class('drop-active')

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
            # Use the first valid path
            self._set_selected_path(valid_paths[0])
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
        self.add_css_class('drop-active')
        return Gdk.DragAction.COPY

    def _on_drag_leave(self, target):
        """
        Cleanup visual feedback when drag leaves the drop zone.

        Removes the 'drop-active' CSS class to restore normal appearance.

        Args:
            target: The DropTarget controller
        """
        self.remove_css_class('drop-active')

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
        self._status_banner.add_css_class("error")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("warning")
        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

    def _create_profile_section(self):
        """Create the scan profile selector section."""
        # Profile selection frame
        profile_group = Adw.PreferencesGroup()
        profile_group.set_title("Scan Profile")
        profile_group.set_description("Select a predefined scan configuration")
        self._profile_group = profile_group

        # Profile selection row
        profile_row = Adw.ActionRow()
        profile_row.set_title("Profile")
        profile_row.set_subtitle("Choose a scan profile or use manual selection")
        profile_row.set_icon_name("document-properties-symbolic")
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

        profile_row.add_suffix(self._profile_dropdown)
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

        app = root.get_application() if hasattr(root, 'get_application') else None
        if app is None:
            return None

        if hasattr(app, 'profile_manager'):
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

        # Add "No Profile" option first
        self._profile_string_list.append("No Profile (Manual)")

        # Add each profile
        for profile in self._profile_list:
            # Format: "Profile Name" or "Profile Name (Default)" for built-in profiles
            display_name = profile.name
            if profile.is_default:
                display_name = f"{profile.name} (Default)"
            self._profile_string_list.append(display_name)

        # Restore selection if the profile still exists
        new_selection = 0  # Default to "No Profile"
        if current_profile_id:
            for i, profile in enumerate(self._profile_list):
                if profile.id == current_profile_id:
                    new_selection = i + 1  # +1 for "No Profile" option
                    break

        self._profile_dropdown.set_selected(new_selection)
        logger.debug(f"Profile dropdown refreshed with {len(self._profile_list)} profiles")

    def _on_profile_selected(self, dropdown, pspec):
        """
        Handle profile selection from dropdown.

        When a profile is selected, the first target path is populated into
        the scan target UI, and the profile's exclusions are stored for use
        during the scan.

        Args:
            dropdown: The Gtk.DropDown widget
            pspec: The property specification
        """
        selected_index = dropdown.get_selected()

        if selected_index == 0:
            # "No Profile" selected - clear selected profile
            self._selected_profile = None
            self._profile_row.set_subtitle("Choose a scan profile or use manual selection")
            logger.debug("Profile cleared - using manual selection")
            # Don't clear path selection - user may have manually selected a path
        elif selected_index - 1 < len(self._profile_list):
            # A profile is selected
            profile = self._profile_list[selected_index - 1]
            self._selected_profile = profile

            # Update subtitle with profile description or target count
            if profile.description:
                subtitle = profile.description
            else:
                target_count = len(profile.targets)
                subtitle = f"{target_count} target(s) configured"
            self._profile_row.set_subtitle(subtitle)

            # Populate scan target from profile
            self._apply_profile_targets(profile)

            logger.debug(f"Profile selected: {profile.name} (ID: {profile.id})")

    def _apply_profile_targets(self, profile: "ScanProfile"):
        """
        Apply profile targets to the scan target UI.

        Expands the first target path (handling ~ for home directory) and
        sets it as the current scan target. The profile's exclusions are
        stored for use during scanning.

        Args:
            profile: The ScanProfile to apply
        """
        if not profile.targets:
            # Profile has no targets - update UI to indicate this
            self._path_row.set_title("No targets in profile")
            self._path_row.set_subtitle("Add targets to this profile or select manually")
            self._path_row.set_icon_name("dialog-warning-symbolic")
            self._selected_path = ""
            self._scan_button.set_sensitive(False)
            return

        # Use the first target from the profile
        # Future enhancement: support multiple targets with sequential scanning
        first_target = profile.targets[0]

        # Expand ~ to home directory
        expanded_path = self._expand_path(first_target)

        # Check if path exists and is accessible
        if os.path.exists(expanded_path):
            self._set_selected_path(expanded_path)

            # Update path row to indicate this came from profile
            display_path = format_scan_path(expanded_path)
            self._path_row.set_title(display_path)
            if len(profile.targets) > 1:
                self._path_row.set_subtitle(
                    f"From profile '{profile.name}' ({len(profile.targets)} targets, scanning first)"
                )
            else:
                self._path_row.set_subtitle(f"From profile '{profile.name}'")
            self._path_row.set_icon_name("folder-symbolic")
        else:
            # Path doesn't exist - show warning but still allow selection
            display_path = format_scan_path(expanded_path)
            self._path_row.set_title(display_path)
            self._path_row.set_subtitle(f"Path not found - from profile '{profile.name}'")
            self._path_row.set_icon_name("dialog-warning-symbolic")
            self._selected_path = expanded_path
            # Still enable scan button - path might become available or user can fix
            self._scan_button.set_sensitive(True)

        logger.debug(f"Applied profile target: {first_target} -> {expanded_path}")

    def _expand_path(self, path: str) -> str:
        """
        Expand a path, handling ~ for home directory.

        Args:
            path: The path string to expand

        Returns:
            The expanded absolute path
        """
        if path.startswith("~"):
            return os.path.expanduser(path)
        return os.path.abspath(path)

    def get_selected_profile(self) -> "ScanProfile | None":
        """
        Get the currently selected scan profile.

        Returns:
            The selected ScanProfile or None if no profile is selected
        """
        return self._selected_profile

    def set_selected_profile(self, profile_id: str) -> bool:
        """
        Set the selected profile by ID.

        Args:
            profile_id: The profile ID to select

        Returns:
            True if profile was found and selected, False otherwise
        """
        for i, profile in enumerate(self._profile_list):
            if profile.id == profile_id:
                self._profile_dropdown.set_selected(i + 1)  # +1 for "No Profile" option
                return True
        return False

    def _create_selection_section(self):
        """Create the folder/file selection section."""
        # Selection frame
        selection_group = Adw.PreferencesGroup()
        selection_group.set_title("Scan Target")
        selection_group.set_description("Select a folder or file to scan for viruses")

        # Path selection row
        self._path_row = Adw.ActionRow()
        self._path_row.set_title("No folder selected")
        self._path_row.set_subtitle("Click 'Select Folder' to choose a location")
        self._path_row.set_icon_name("folder-symbolic")

        # Select folder button
        select_folder_btn = Gtk.Button()
        select_folder_btn.set_label("Select Folder")
        select_folder_btn.set_valign(Gtk.Align.CENTER)
        select_folder_btn.add_css_class("suggested-action")
        select_folder_btn.connect("clicked", self._on_select_folder_clicked)
        self._select_folder_btn = select_folder_btn

        # Select file button
        select_file_btn = Gtk.Button()
        select_file_btn.set_label("Select File")
        select_file_btn.set_valign(Gtk.Align.CENTER)
        select_file_btn.connect("clicked", self._on_select_file_clicked)
        self._select_file_btn = select_file_btn

        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_valign(Gtk.Align.CENTER)
        button_box.append(select_folder_btn)
        button_box.append(select_file_btn)

        self._path_row.add_suffix(button_box)
        selection_group.add(self._path_row)

        self.append(selection_group)

    def _create_scan_section(self):
        """Create the scan button section."""
        # Scan button container
        scan_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        scan_box.set_halign(Gtk.Align.CENTER)
        scan_box.set_spacing(12)

        # Scan button
        self._scan_button = Gtk.Button()
        self._scan_button.set_label("Scan")
        self._scan_button.add_css_class("suggested-action")
        self._scan_button.add_css_class("pill")
        self._scan_button.set_sensitive(False)  # Disabled until path selected
        self._scan_button.connect("clicked", self._on_scan_clicked)

        # Make the button larger
        self._scan_button.set_size_request(120, 40)

        # Spinner for scan progress (hidden by default)
        self._scan_spinner = Gtk.Spinner()
        self._scan_spinner.set_visible(False)

        # Cancel button (hidden by default)
        self._cancel_button = Gtk.Button()
        self._cancel_button.set_label("Cancel")
        self._cancel_button.add_css_class("destructive-action")
        self._cancel_button.add_css_class("pill")
        self._cancel_button.set_visible(False)
        self._cancel_button.connect("clicked", self._on_cancel_clicked)

        # Test ClamAV button
        self._test_clamav_button = Gtk.Button()
        self._test_clamav_button.set_label("Test ClamAV")
        self._test_clamav_button.add_css_class("pill")
        self._test_clamav_button.set_tooltip_text(
            "Scan an EICAR test file to verify ClamAV is working correctly"
        )
        self._test_clamav_button.connect("clicked", self._on_test_clamav_clicked)

        scan_box.append(self._scan_spinner)
        scan_box.append(self._scan_button)
        scan_box.append(self._cancel_button)
        scan_box.append(self._test_clamav_button)

        self.append(scan_box)

    def _create_results_section(self):
        """Create the results display section."""
        # Results frame
        results_group = Adw.PreferencesGroup()
        results_group.set_title("Scan Results")
        results_group.set_description("Results will appear here after scanning")
        self._results_group = results_group

        # Header box with export and fullscreen buttons
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_halign(Gtk.Align.END)
        header_box.set_spacing(6)

        # Copy to Clipboard button
        copy_button = Gtk.Button()
        copy_button.set_icon_name("edit-copy-symbolic")
        copy_button.set_tooltip_text("Copy to clipboard")
        copy_button.add_css_class("flat")
        copy_button.set_sensitive(False)  # Disabled until results available
        copy_button.connect("clicked", self._on_copy_results_clicked)
        self._copy_button = copy_button

        # Export to Text button
        export_text_button = Gtk.Button()
        export_text_button.set_icon_name("document-save-symbolic")
        export_text_button.set_tooltip_text("Export to text file")
        export_text_button.add_css_class("flat")
        export_text_button.set_sensitive(False)  # Disabled until results available
        export_text_button.connect("clicked", self._on_export_text_clicked)
        self._export_text_button = export_text_button

        # Export to CSV button
        export_csv_button = Gtk.Button()
        export_csv_button.set_icon_name("x-office-spreadsheet-symbolic")
        export_csv_button.set_tooltip_text("Export to CSV file")
        export_csv_button.add_css_class("flat")
        export_csv_button.set_sensitive(False)  # Disabled until results available
        export_csv_button.connect("clicked", self._on_export_csv_clicked)
        self._export_csv_button = export_csv_button

        # Fullscreen button
        fullscreen_button = Gtk.Button()
        fullscreen_button.set_icon_name("view-fullscreen-symbolic")
        fullscreen_button.set_tooltip_text("View fullscreen")
        fullscreen_button.add_css_class("flat")
        fullscreen_button.connect("clicked", self._on_fullscreen_results_clicked)
        self._fullscreen_button = fullscreen_button

        header_box.append(copy_button)
        header_box.append(export_text_button)
        header_box.append(export_csv_button)
        header_box.append(fullscreen_button)
        results_group.set_header_suffix(header_box)

        # Results container
        results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        results_box.set_spacing(12)

        # Status banner (hidden by default)
        self._status_banner = Adw.Banner()
        self._status_banner.set_revealed(False)
        results_box.append(self._status_banner)

        # Scrolled window for threat cards ListBox
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.set_vexpand(True)
        scrolled.add_css_class("card")

        # Container for ListBox and placeholder
        self._results_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Threats ListBox for threat cards display
        self._threats_listbox = Gtk.ListBox()
        self._threats_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._threats_listbox.add_css_class("boxed-list")
        self._threats_listbox.set_visible(False)  # Hidden until threats are found
        self._results_container.append(self._threats_listbox)

        # Placeholder label (shown when no results)
        self._results_placeholder = Gtk.Label()
        self._results_placeholder.set_text("No scan results yet.\n\nSelect a folder or file and click 'Scan' to begin.")
        self._results_placeholder.set_wrap(True)
        self._results_placeholder.set_justify(Gtk.Justification.CENTER)
        self._results_placeholder.add_css_class("dim-label")
        self._results_placeholder.set_margin_top(24)
        self._results_placeholder.set_margin_bottom(24)
        self._results_placeholder.set_margin_start(12)
        self._results_placeholder.set_margin_end(12)
        self._results_placeholder.set_vexpand(True)
        self._results_placeholder.set_valign(Gtk.Align.CENTER)
        self._results_container.append(self._results_placeholder)

        # Store raw output for fullscreen dialog
        self._raw_output: str = ""

        # Store current result for export functionality
        self._current_result: ScanResult | None = None

        scrolled.set_child(self._results_container)
        results_box.append(scrolled)

        results_group.add(results_box)
        self.append(results_group)

    def _create_status_bar(self):
        """Create the status bar at the bottom."""
        # Status bar
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.set_halign(Gtk.Align.CENTER)
        status_box.set_spacing(6)

        # ClamAV status icon
        self._clamav_status_icon = Gtk.Image()
        self._clamav_status_icon.set_from_icon_name("dialog-question-symbolic")

        # ClamAV status label
        self._clamav_status_label = Gtk.Label()
        self._clamav_status_label.set_text("Checking ClamAV...")
        self._clamav_status_label.add_css_class("dim-label")

        status_box.append(self._clamav_status_icon)
        status_box.append(self._clamav_status_label)

        self.append(status_box)

    def _check_clamav_status(self):
        """Check ClamAV installation status and update UI."""
        is_installed, version_or_error = check_clamav_installed()

        if is_installed:
            self._clamav_status_icon.set_from_icon_name("emblem-ok-symbolic")
            self._clamav_status_icon.add_css_class("success")
            self._clamav_status_label.set_text(f"ClamAV: {version_or_error}")
        else:
            self._clamav_status_icon.set_from_icon_name("dialog-warning-symbolic")
            self._clamav_status_icon.add_css_class("warning")
            self._clamav_status_label.set_text(version_or_error or "ClamAV not found")

            # Show error banner
            self._status_banner.set_title(version_or_error or "ClamAV not installed")
            self._status_banner.set_button_label(None)
            self._status_banner.set_revealed(True)

        return False  # Don't repeat

    def _on_select_folder_clicked(self, button):
        """Handle folder selection button click."""
        self._open_file_dialog(select_folder=True)

    def _on_select_file_clicked(self, button):
        """Handle file selection button click."""
        self._open_file_dialog(select_folder=False)

    def _open_file_dialog(self, select_folder: bool):
        """
        Open a file/folder selection dialog.

        Args:
            select_folder: True to select folders, False for files
        """
        dialog = Gtk.FileDialog()

        if select_folder:
            dialog.set_title("Select Folder to Scan")
        else:
            dialog.set_title("Select File to Scan")

        # Get the parent window
        window = self.get_root()

        if select_folder:
            dialog.select_folder(window, None, self._on_folder_selected)
        else:
            dialog.open(window, None, self._on_file_selected)

    def _on_folder_selected(self, dialog, result):
        """Handle folder selection result."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self._set_selected_path(path)
        except GLib.Error:
            pass  # User cancelled

    def _on_file_selected(self, dialog, result):
        """Handle file selection result."""
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                self._set_selected_path(path)
        except GLib.Error:
            pass  # User cancelled

    def _set_selected_path(self, path: str):
        """
        Set the selected path and update the UI.

        Args:
            path: The selected filesystem path
        """
        self._selected_path = path
        display_path = format_scan_path(path)

        # Update the path row
        self._path_row.set_title(display_path)
        self._path_row.set_subtitle("Ready to scan")

        # Enable the scan button
        self._scan_button.set_sensitive(True)

        # Clear previous results
        self._clear_results()

    def _on_scan_clicked(self, button):
        """Handle scan button click."""
        if not self._selected_path:
            return

        self._start_scan()

    def _on_cancel_clicked(self, button):
        """Handle cancel button click."""
        self._scanner.cancel()
        self._set_scanning_state(False)

    def _start_scan(self):
        """Start the scanning process."""
        self._set_scanning_state(True)
        self._clear_results()

        # Update placeholder to show scanning status
        self._results_placeholder.set_text(f"Scanning: {self._selected_path}\n\nPlease wait...")

        # Hide any previous status banner
        self._status_banner.set_revealed(False)

        # Get profile exclusions if a profile is selected
        profile_exclusions = None
        if self._selected_profile is not None:
            profile_exclusions = self._selected_profile.exclusions
            logger.debug(
                f"Scanning with profile '{self._selected_profile.name}' exclusions: "
                f"{len(profile_exclusions.get('paths', []))} paths, "
                f"{len(profile_exclusions.get('patterns', []))} patterns"
            )

        # Start async scan with profile exclusions
        self._scanner.scan_async(
            self._selected_path,
            callback=self._on_scan_complete,
            profile_exclusions=profile_exclusions
        )

    def set_scan_state_callback(self, callback):
        """
        Set callback for scan state changes.

        The callback is invoked when scanning starts or stops.
        Signature: callback(is_scanning: bool, result: Optional[ScanResult])
        - When scan starts: is_scanning=True, result=None
        - When scan ends: is_scanning=False, result=ScanResult

        Args:
            callback: Callable to invoke on state changes
        """
        self._on_scan_state_changed = callback

    def _set_scanning_state(self, is_scanning: bool, result=None):
        """
        Update UI to reflect scanning state.

        Args:
            is_scanning: Whether a scan is in progress
            result: ScanResult when scan completes (None when starting)
        """
        self._is_scanning = is_scanning

        if is_scanning:
            # Show scanning state
            self._scan_button.set_label("Scanning...")
            self._scan_button.set_sensitive(False)
            self._scan_spinner.set_visible(True)
            self._scan_spinner.start()
            self._cancel_button.set_visible(True)

            # Disable path selection and test button
            self._select_folder_btn.set_sensitive(False)
            self._select_file_btn.set_sensitive(False)
            self._test_clamav_button.set_sensitive(False)

            # Disable export buttons during scan
            self._copy_button.set_sensitive(False)
            self._export_text_button.set_sensitive(False)
            self._export_csv_button.set_sensitive(False)
        else:
            # Restore normal state
            self._scan_button.set_label("Scan")
            self._scan_button.set_sensitive(bool(self._selected_path))
            self._scan_spinner.stop()
            self._scan_spinner.set_visible(False)
            self._cancel_button.set_visible(False)

            # Enable path selection and test button
            self._select_folder_btn.set_sensitive(True)
            self._select_file_btn.set_sensitive(True)
            self._test_clamav_button.set_sensitive(True)

        # Notify callback of state change
        if self._on_scan_state_changed:
            self._on_scan_state_changed(is_scanning, result)

    def _on_scan_complete(self, result: ScanResult):
        """
        Handle scan completion.

        Args:
            result: The scan result from the scanner
        """
        self._set_scanning_state(False, result)
        self._display_results(result)
        return False  # Don't repeat GLib.idle_add

    def _clear_results(self):
        """Clear the results display."""
        # Clear the threats ListBox
        while True:
            row = self._threats_listbox.get_row_at_index(0)
            if row is None:
                break
            self._threats_listbox.remove(row)

        # Hide ListBox and show placeholder
        self._threats_listbox.set_visible(False)
        self._results_placeholder.set_visible(True)
        self._results_placeholder.set_text("No scan results yet.\n\nSelect a folder or file and click 'Scan' to begin.")

        # Clear raw output and current result
        self._raw_output = ""
        self._current_result = None

        # Reset pagination state
        self._displayed_threat_count = 0
        self._all_threat_details = []
        self._load_more_row = None

        # Disable export buttons when no results
        self._copy_button.set_sensitive(False)
        self._export_text_button.set_sensitive(False)
        self._export_csv_button.set_sensitive(False)

        self._status_banner.set_revealed(False)

    def _display_results(self, result: ScanResult):
        """
        Display scan results in the UI.

        For large result sets (100+ threats), displays a warning banner and
        implements pagination to keep the UI responsive. Initially shows a
        limited number of threats with a "Show More" button to load additional
        results in batches.

        Args:
            result: The scan result to display
        """
        # Store raw output for fullscreen dialog
        self._raw_output = result.stdout

        # Store the current result for export functionality
        self._current_result = result

        # Store all threat details for pagination
        self._all_threat_details = result.threat_details if result.threat_details else []
        self._displayed_threat_count = 0
        self._load_more_row = None

        # Update status banner based on result
        if result.status == ScanStatus.CLEAN:
            self._status_banner.set_title("No threats found")
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.remove_css_class("warning")
        elif result.status == ScanStatus.INFECTED:
            threat_count = len(self._all_threat_details)
            # Show warning for large result sets
            if threat_count >= LARGE_RESULT_THRESHOLD:
                self._status_banner.set_title(
                    f"Large result set: {threat_count} threats detected. "
                    f"Showing first {INITIAL_DISPLAY_LIMIT} results."
                )
                self._status_banner.add_css_class("warning")
                self._status_banner.remove_css_class("success")
                self._status_banner.remove_css_class("error")
            else:
                self._status_banner.set_title(f"Threats detected: {result.infected_count} infected file(s)")
                self._status_banner.add_css_class("error")
                self._status_banner.remove_css_class("success")
                self._status_banner.remove_css_class("warning")
        else:  # ERROR status
            self._status_banner.set_title(f"Scan error: {result.error_message}")
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")

        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

        # Clear previous results from ListBox
        while True:
            row = self._threats_listbox.get_row_at_index(0)
            if row is None:
                break
            self._threats_listbox.remove(row)

        # Display results based on status
        if result.status == ScanStatus.INFECTED and self._all_threat_details:
            # Hide placeholder, show ListBox with threat cards
            self._results_placeholder.set_visible(False)
            self._threats_listbox.set_visible(True)

            threat_count = len(self._all_threat_details)

            # For large result sets, show warning banner and paginate
            if threat_count >= LARGE_RESULT_THRESHOLD:
                # Add warning info row at the top
                warning_row = self._create_large_result_warning_row(threat_count)
                self._threats_listbox.append(warning_row)

                # Display initial batch of threats
                initial_limit = min(INITIAL_DISPLAY_LIMIT, threat_count)
                self._display_threat_batch(0, initial_limit)

                # Add "Show More" button if there are more threats
                if threat_count > INITIAL_DISPLAY_LIMIT:
                    self._add_load_more_button()
            else:
                # For smaller result sets, display all threats
                for threat_detail in self._all_threat_details:
                    threat_card = self._create_threat_card(threat_detail)
                    self._threats_listbox.append(threat_card)
                self._displayed_threat_count = threat_count

                # Add clean files summary row at the end
                clean_count = result.scanned_files - result.infected_count
                if clean_count > 0:
                    summary_row = self._create_clean_files_summary_row(
                        clean_count, result.scanned_files, result.scanned_dirs
                    )
                    self._threats_listbox.append(summary_row)

        elif result.status == ScanStatus.CLEAN:
            # Show ListBox with clean files summary only
            self._results_placeholder.set_visible(False)
            self._threats_listbox.set_visible(True)

            summary_row = self._create_clean_files_summary_row(
                result.scanned_files, result.scanned_files, result.scanned_dirs
            )
            self._threats_listbox.append(summary_row)

        else:
            # ERROR status - show error message in placeholder
            self._threats_listbox.set_visible(False)
            self._results_placeholder.set_visible(True)
            self._results_placeholder.set_text(
                f"Scan failed: {result.error_message}\n\nPlease check the fullscreen log for details."
            )

        # Enable export buttons when results are available
        # (for both successful scans and error states, so user can export error details)
        self._copy_button.set_sensitive(True)
        self._export_text_button.set_sensitive(True)
        self._export_csv_button.set_sensitive(True)

    def _create_large_result_warning_row(self, threat_count: int) -> Gtk.Box:
        """
        Create a warning row displayed at the top of large result sets.

        Args:
            threat_count: Total number of threats detected

        Returns:
            Gtk.Box widget containing the warning message
        """
        warning_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        warning_box.add_css_class("large-result-warning")
        warning_box.set_margin_start(8)
        warning_box.set_margin_end(8)
        warning_box.set_margin_top(8)

        # Warning icon
        warning_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        warning_box.append(warning_icon)

        # Warning text
        warning_label = Gtk.Label()
        warning_label.set_markup(
            f"<b>Large Result Set:</b> {threat_count} threats detected. "
            f"Results are paginated to maintain UI responsiveness. "
            f"Use Export to save all results."
        )
        warning_label.set_wrap(True)
        warning_label.set_xalign(0)
        warning_label.set_hexpand(True)
        warning_box.append(warning_label)

        return warning_box

    def _display_threat_batch(self, start_index: int, count: int):
        """
        Display a batch of threat cards starting from the given index.

        Uses GLib.idle_add to add cards incrementally for better UI responsiveness
        with very large result sets.

        Args:
            start_index: Index in _all_threat_details to start from
            count: Number of threats to display
        """
        end_index = min(start_index + count, len(self._all_threat_details))

        for i in range(start_index, end_index):
            threat_detail = self._all_threat_details[i]
            threat_card = self._create_threat_card(threat_detail)

            # Insert before the "Load More" button if it exists
            if self._load_more_row:
                # Find the index of the load more row
                row_index = 0
                while True:
                    row = self._threats_listbox.get_row_at_index(row_index)
                    if row is None:
                        break
                    row_index += 1
                # Insert at position just before the last row (load more button)
                self._threats_listbox.insert(threat_card, row_index - 1)
            else:
                self._threats_listbox.append(threat_card)

        self._displayed_threat_count = end_index

    def _add_load_more_button(self):
        """
        Add a "Show More" button row to load additional threats.
        """
        # Container box for the load more button
        load_more_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        load_more_box.add_css_class("load-more-row")
        load_more_box.set_halign(Gtk.Align.CENTER)
        load_more_box.set_margin_top(12)
        load_more_box.set_margin_bottom(12)

        # Progress label showing how many are displayed
        remaining = len(self._all_threat_details) - self._displayed_threat_count
        progress_label = Gtk.Label()
        progress_label.set_markup(
            f"<span size='small'>Showing {self._displayed_threat_count} of "
            f"{len(self._all_threat_details)} threats</span>"
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

        # "Show All" button (only if there are many remaining)
        if remaining > LOAD_MORE_BATCH_SIZE:
            show_all_btn = Gtk.Button()
            show_all_btn.set_label(f"Show All ({remaining} remaining)")
            show_all_btn.add_css_class("pill")
            show_all_btn.connect("clicked", self._on_show_all_clicked)
            button_box.append(show_all_btn)

        load_more_box.append(button_box)

        self._load_more_row = load_more_box
        self._threats_listbox.append(load_more_box)

    def _on_load_more_clicked(self, button):
        """
        Handle "Show More" button click to load the next batch of threats.
        """
        # Remove the current load more row
        if self._load_more_row:
            self._threats_listbox.remove(self._load_more_row)
            self._load_more_row = None

        # Display next batch
        remaining = len(self._all_threat_details) - self._displayed_threat_count
        batch_size = min(LOAD_MORE_BATCH_SIZE, remaining)
        self._display_threat_batch(self._displayed_threat_count, batch_size)

        # Add new load more button if there are still more threats
        if self._displayed_threat_count < len(self._all_threat_details):
            self._add_load_more_button()
        else:
            # All threats displayed, add summary row
            self._add_final_summary_row()

        # Update status banner
        self._update_pagination_status()

    def _on_show_all_clicked(self, button):
        """
        Handle "Show All" button click to load all remaining threats.

        Uses incremental loading with GLib.idle_add to keep UI responsive.
        """
        # Remove the current load more row
        if self._load_more_row:
            self._threats_listbox.remove(self._load_more_row)
            self._load_more_row = None

        # Display all remaining threats
        remaining = len(self._all_threat_details) - self._displayed_threat_count
        self._display_threat_batch(self._displayed_threat_count, remaining)

        # Add summary row
        self._add_final_summary_row()

        # Update status banner
        self._update_pagination_status()

    def _add_final_summary_row(self):
        """
        Add the clean files summary row after all threats are displayed.
        """
        if self._current_result:
            clean_count = self._current_result.scanned_files - self._current_result.infected_count
            if clean_count > 0:
                summary_row = self._create_clean_files_summary_row(
                    clean_count,
                    self._current_result.scanned_files,
                    self._current_result.scanned_dirs
                )
                self._threats_listbox.append(summary_row)

    def _update_pagination_status(self):
        """
        Update the status banner to reflect current pagination state.
        """
        total = len(self._all_threat_details)
        displayed = self._displayed_threat_count

        if displayed >= total:
            # All threats displayed
            self._status_banner.set_title(f"Threats detected: {total} infected file(s)")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("warning")
            self._status_banner.remove_css_class("success")
        else:
            # Still paginated
            self._status_banner.set_title(
                f"Large result set: {total} threats detected. "
                f"Showing {displayed} of {total} results."
            )

    def _create_clean_files_summary_row(
        self, clean_count: int, total_files: int, total_dirs: int
    ) -> Adw.ActionRow:
        """
        Create a summary row showing clean file count (not individual files).

        Args:
            clean_count: Number of clean files
            total_files: Total number of files scanned
            total_dirs: Total number of directories scanned

        Returns:
            Adw.ActionRow widget showing the summary
        """
        summary_row = Adw.ActionRow()
        summary_row.set_title("Scan Summary")

        # Build subtitle with scan statistics
        subtitle_parts = []
        subtitle_parts.append(f"{clean_count} clean file(s)")
        if total_dirs > 0:
            subtitle_parts.append(f"{total_dirs} directories scanned")
        subtitle_parts.append(f"{total_files} total files checked")
        summary_row.set_subtitle(" • ".join(subtitle_parts))

        summary_row.set_icon_name("emblem-ok-symbolic")
        summary_row.add_css_class("success")

        return summary_row

    def _on_test_clamav_clicked(self, button):
        """Handle test ClamAV button click."""
        # Create a temporary file with EICAR test string
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(EICAR_TEST_STRING)
                self._eicar_temp_path = f.name

            # Scan the test file
            self._selected_path = self._eicar_temp_path
            self._start_scan()
        except Exception as e:
            self._status_banner.set_title(f"Error creating test file: {str(e)}")
            self._status_banner.add_css_class("error")
            self._status_banner.set_revealed(True)

    def _on_fullscreen_results_clicked(self, button):
        """Handle fullscreen results button click."""
        # Use stored raw output for fullscreen view
        text = self._raw_output if self._raw_output else "No scan results available."

        dialog = FullscreenLogDialog(
            transient_for=self.get_root(),
            modal=True,
            text=text
        )
        dialog.present()

    def _create_threat_card(self, threat_detail: ThreatDetail) -> Adw.ExpanderRow:
        """
        Create an expandable threat card widget for a detected threat.

        The card displays:
        - File path as title (with tooltip for long paths)
        - Threat name and category as subtitle
        - Color-coded severity badge
        - Expandable section with recommended actions

        Args:
            threat_detail: ThreatDetail object containing threat information

        Returns:
            Adw.ExpanderRow widget configured as a threat card
        """
        # Create the expander row
        expander = Adw.ExpanderRow()
        expander.add_css_class("threat-card")

        # Format file path for display (truncate if too long)
        file_path = threat_detail.file_path
        display_path = file_path
        if len(file_path) > 60:
            # Show first 20 and last 35 characters
            display_path = file_path[:20] + "..." + file_path[-35:]

        expander.set_title(display_path)
        expander.set_tooltip_text(file_path)  # Full path in tooltip

        # Subtitle with threat name and category
        subtitle = f"{threat_detail.threat_name} ({threat_detail.category})"
        expander.set_subtitle(subtitle)

        # Set icon based on severity
        severity_icons = {
            "critical": "dialog-error-symbolic",
            "high": "dialog-warning-symbolic",
            "medium": "emblem-important-symbolic",
            "low": "dialog-information-symbolic"
        }
        icon_name = severity_icons.get(threat_detail.severity, "emblem-important-symbolic")
        expander.set_icon_name(icon_name)

        # Create severity badge
        severity_badge = Gtk.Label()
        severity_badge.set_label(threat_detail.severity.upper())
        severity_badge.add_css_class("severity-badge")
        severity_badge.add_css_class(f"severity-{threat_detail.severity}")
        severity_badge.set_valign(Gtk.Align.CENTER)

        # Add badge as prefix
        expander.add_prefix(severity_badge)

        # Create expanded content with recommended actions
        action_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        action_box.set_margin_start(12)
        action_box.set_margin_end(12)
        action_box.set_margin_top(8)
        action_box.set_margin_bottom(8)

        # Recommended action label
        action_header = Gtk.Label()
        action_header.set_markup("<b>Recommended Action:</b>")
        action_header.set_halign(Gtk.Align.START)
        action_box.append(action_header)

        # Get and display the recommended action
        recommended_action = self._get_recommended_action(threat_detail)
        action_label = Gtk.Label()
        action_label.set_text(recommended_action)
        action_label.set_wrap(True)
        action_label.set_halign(Gtk.Align.START)
        action_label.add_css_class("recommended-action")
        action_box.append(action_label)

        # Add file path details row
        path_row = Adw.ActionRow()
        path_row.set_title("Full Path")
        path_row.set_subtitle(file_path)
        path_row.set_subtitle_selectable(True)
        action_box.append(path_row)

        expander.add_row(action_box)

        return expander

    def _get_recommended_action(self, threat_detail: ThreatDetail) -> str:
        """
        Get the recommended action for a threat based on its severity and category.

        Args:
            threat_detail: ThreatDetail object containing threat information

        Returns:
            String describing the recommended action for this threat
        """
        severity = threat_detail.severity
        category = threat_detail.category

        # Actions based on category first (more specific)
        if category == "Test":
            return (
                "This is a test file (EICAR) used to verify antivirus functionality. "
                "It is safe and can be deleted. No action required unless it appeared unexpectedly."
            )

        if category == "Ransomware":
            return (
                "URGENT: Disconnect from network immediately. Do not pay any ransom. "
                "Delete the infected file, run a full system scan, and restore affected files "
                "from backup. Consider professional assistance."
            )

        if category == "Rootkit":
            return (
                "CRITICAL: This threat can hide itself and other malware. "
                "Boot from a clean rescue disk and run a full scan. "
                "Consider reinstalling the operating system if compromise is confirmed."
            )

        if category == "Trojan" or category == "Backdoor":
            return (
                "Delete the infected file immediately. Run a full system scan to check for "
                "additional compromises. Change passwords for sensitive accounts and monitor "
                "for unauthorized access."
            )

        if category == "Worm":
            return (
                "Delete the infected file and run a full system scan. "
                "Check network-connected devices for infection. "
                "Update all software and operating system patches."
            )

        if category == "Exploit":
            return (
                "Delete the infected file. Update all software to the latest versions. "
                "Apply security patches immediately. Check for signs of successful exploitation."
            )

        if category in ["Adware", "PUA"]:
            return (
                "This is a Potentially Unwanted Application. Delete the file if not intentionally "
                "installed. Review installed programs and browser extensions for unwanted additions."
            )

        if category == "Spyware":
            return (
                "Delete the infected file immediately. Change passwords for all accounts. "
                "Check for keyloggers and review recent account activity for unauthorized access."
            )

        # Fall back to severity-based recommendations
        if severity == "critical":
            return (
                "URGENT: Delete the infected file immediately and isolate this system. "
                "Run a full system scan and consider professional security assistance."
            )

        if severity == "high":
            return (
                "Delete the infected file and run a full system scan. "
                "Monitor for unusual system behavior and review security logs."
            )

        if severity == "medium":
            return (
                "Delete the infected file if not needed. Run a targeted scan on the affected "
                "directory. Review how this file arrived on your system."
            )

        # Low severity or default
        return (
            "Review the file and delete if not recognized or needed. "
            "This is likely a low-risk detection but should still be investigated."
        )

    def _on_copy_results_clicked(self, button):
        """
        Handle copy to clipboard button click.

        Formats the current scan results as human-readable text and copies
        them to the system clipboard. Shows a success or error banner.
        """
        if self._current_result is None:
            self._status_banner.set_title("No results to copy")
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.set_button_label(None)
            self._status_banner.set_revealed(True)
            return

        # Format the results as text
        formatted_text = format_results_as_text(self._current_result)

        # Copy to clipboard
        success = copy_to_clipboard(formatted_text)

        if success:
            self._status_banner.set_title("Results copied to clipboard")
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.remove_css_class("warning")
        else:
            self._status_banner.set_title("Failed to copy to clipboard")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")

        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

    def _on_export_text_clicked(self, button):
        """
        Handle export to text file button click.

        Opens a file save dialog to let the user choose a location,
        then writes the formatted scan results to a text file.
        """
        if self._current_result is None:
            self._status_banner.set_title("No results to export")
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.set_button_label(None)
            self._status_banner.set_revealed(True)
            return

        # Create save dialog
        dialog = Gtk.FileDialog()
        dialog.set_title("Export Scan Results")

        # Generate default filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dialog.set_initial_name(f"clamui_scan_{timestamp}.txt")

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

        Writes the formatted scan results to the selected file.

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
                self._show_export_error("Invalid file path selected")
                return

            # Ensure .txt extension
            if not file_path.endswith('.txt'):
                file_path += '.txt'

            # Format the results as text
            formatted_text = format_results_as_text(self._current_result)

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)

            # Show success feedback
            self._status_banner.set_title(f"Results exported to {os.path.basename(file_path)}")
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.remove_css_class("warning")
            self._status_banner.set_button_label(None)
            self._status_banner.set_revealed(True)

        except GLib.Error:
            # User cancelled the dialog
            pass
        except PermissionError:
            self._show_export_error("Permission denied - cannot write to selected location")
        except OSError as e:
            self._show_export_error(f"Error writing file: {str(e)}")

    def _show_export_error(self, message: str):
        """
        Display an error message for export failures.

        Args:
            message: The error message to display
        """
        self._status_banner.set_title(message)
        self._status_banner.add_css_class("error")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("warning")
        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

    def _on_export_csv_clicked(self, button):
        """
        Handle export to CSV file button click.

        Opens a file save dialog to let the user choose a location,
        then writes the scan results in CSV format for spreadsheet analysis.
        """
        if self._current_result is None:
            self._status_banner.set_title("No results to export")
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.set_button_label(None)
            self._status_banner.set_revealed(True)
            return

        # Create save dialog
        dialog = Gtk.FileDialog()
        dialog.set_title("Export Scan Results as CSV")

        # Generate default filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dialog.set_initial_name(f"clamui_scan_{timestamp}.csv")

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

        Writes the scan results in CSV format to the selected file.

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
                self._show_export_error("Invalid file path selected")
                return

            # Ensure .csv extension
            if not file_path.endswith('.csv'):
                file_path += '.csv'

            # Import the CSV formatting utility
            from ..core.utils import format_results_as_csv

            # Format the results as CSV
            csv_content = format_results_as_csv(self._current_result)

            # Write to file
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(csv_content)

            # Show success feedback
            self._status_banner.set_title(f"Results exported to {os.path.basename(file_path)}")
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.remove_css_class("warning")
            self._status_banner.set_button_label(None)
            self._status_banner.set_revealed(True)

        except GLib.Error:
            # User cancelled the dialog
            pass
        except PermissionError:
            self._show_export_error("Permission denied - cannot write to selected location")
        except OSError as e:
            self._show_export_error(f"Error writing file: {str(e)}")