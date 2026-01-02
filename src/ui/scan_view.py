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
from ..core.quarantine import QuarantineManager, QuarantineStatus
from .fullscreen_dialog import FullscreenLogDialog
from .utils import add_row_icon
from .profile_dialogs import ProfileListDialog

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

        # Initialize quarantine manager
        self._quarantine_manager = QuarantineManager()

        # Current selected path
        self._selected_path: str = ""

        # Scanning state
        self._is_scanning = False

        # Temp file path for EICAR test (for cleanup)
        self._eicar_temp_path: str = ""

        # Pagination state for large result sets
        self._displayed_threat_count: int = 0
        self._all_threat_details: list = []
        self._load_more_row: Gtk.ListBoxRow | None = None
        self._threats_scrolled: Gtk.ScrolledWindow | None = None

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
                background-color: @error_bg_color;
                color: white;
            }

            .severity-high {
                background-color: lighter(@error_bg_color);
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
        self._status_banner.add_css_class("error")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("warning")
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
        the scan target UI. Profile exclusions are passed to the scanner at scan time.

        Args:
            dropdown: The DropDown widget
            pspec: Property spec (unused)
        """
        selected_index = dropdown.get_selected()

        if selected_index == 0:
            # "No Profile" selected - clear selected profile
            self._selected_profile = None
            logger.debug("No profile selected")
        else:
            # Profile selected - store profile for use at scan time
            profile_idx = selected_index - 1  # -1 for "No Profile" option
            if 0 <= profile_idx < len(self._profile_list):
                self._selected_profile = self._profile_list[profile_idx]
                # Set first target path if available
                if self._selected_profile.targets:
                    first_target = self._selected_profile.targets[0]
                    self._set_selected_path(first_target)
                logger.debug(f"Profile selected: {self._selected_profile.name}")

    def _on_manage_profiles_clicked(self, button):
        """
        Handle manage profiles button click.

        Opens the profile list dialog for managing profiles.

        Args:
            button: The clicked button
        """
        root = self.get_root()
        if root is None:
            return

        # Open profile list dialog
        profile_manager = self._get_profile_manager()
        dialog = ProfileListDialog(profile_manager=profile_manager)
        dialog.connect("closed", self._on_profiles_dialog_closed)
        dialog.present(root)

    def _on_profiles_dialog_closed(self, dialog):
        """
        Handle profile dialog closed.

        Refreshes the profile dropdown when the profile dialog is closed.

        Args:
            dialog: The ProfileListDialog that was closed
        """
        self.refresh_profiles()

    def _create_selection_section(self):
        """Create the folder/file selection section."""
        # Selection group
        selection_group = Adw.PreferencesGroup()
        selection_group.set_title("Scan Target")
        selection_group.set_description("Choose a folder or file to scan")

        # Path display row
        self._path_row = Adw.ActionRow()
        self._path_row.set_title("Selected Path")
        self._path_row.set_subtitle("No path selected")
        add_row_icon(self._path_row, "folder-symbolic")

        # Browse button
        self._browse_button = Gtk.Button(label="Browse")
        self._browse_button.set_valign(Gtk.Align.CENTER)
        self._browse_button.connect("clicked", self._on_browse_clicked)
        self._path_row.add_suffix(self._browse_button)

        selection_group.add(self._path_row)
        self.append(selection_group)

    def _on_browse_clicked(self, button):
        """
        Handle browse button click.

        Opens a file/folder selection dialog.

        Args:
            button: The clicked button
        """
        root = self.get_root()
        if root is None:
            return

        # Create file dialog
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Folder or File to Scan")

        # Open async - use a callback
        def on_file_selected(dialog, result):
            try:
                file = dialog.select_folder_finish(result)
                if file:
                    path = file.get_path()
                    if path:
                        self._set_selected_path(path)
            except GLib.GError as e:
                if e.code != Gio.IOErrorEnum.CANCELLED:
                    logger.error(f"Error selecting file: {e}")

        dialog.select_folder(root, None, on_file_selected)

    def _set_selected_path(self, path: str):
        """
        Set the selected scan path.

        Updates the UI display with the selected path.

        Args:
            path: The file or folder path to scan
        """
        self._selected_path = path
        formatted_path = format_scan_path(path)
        self._path_row.set_subtitle(formatted_path)
        self._path_row.remove_css_class("error")
        logger.debug(f"Selected path: {path}")

    def _create_scan_section(self):
        """Create the scan button section."""
        # Scan button group
        scan_group = Adw.PreferencesGroup()

        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(12)
        button_box.set_margin_bottom(12)

        # Scan button
        self._scan_button = Gtk.Button(label="Scan")
        self._scan_button.add_css_class("suggested-action")
        self._scan_button.set_size_request(120, -1)
        self._scan_button.connect("clicked", self._on_scan_clicked)
        button_box.append(self._scan_button)

        # EICAR test button
        self._eicar_button = Gtk.Button(label="Test (EICAR)")
        self._eicar_button.set_tooltip_text(
            "Run antivirus test with EICAR test file\n"
            "(This is NOT malware - industry-standard AV test pattern)"
        )
        self._eicar_button.set_size_request(120, -1)
        self._eicar_button.connect("clicked", self._on_eicar_test_clicked)
        button_box.append(self._eicar_button)

        scan_group.add(button_box)
        self.append(scan_group)

    def _on_scan_clicked(self, button):
        """
        Handle scan button click.

        Starts a scan of the selected path.

        Args:
            button: The clicked button
        """
        if not self._selected_path:
            self._status_banner.set_title("Please select a path to scan")
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.set_revealed(True)
            return

        self._start_scan(self._selected_path)

    def _on_eicar_test_clicked(self, button):
        """
        Handle EICAR test button click.

        Creates a temporary EICAR test file and runs a scan.
        This is used to verify antivirus functionality without
        risking real malware exposure.

        Args:
            button: The clicked button
        """
        try:
            # Create temporary file with EICAR test string
            with tempfile.NamedTemporaryFile(
                mode='w',
                delete=False,
                suffix='.txt',
                prefix='eicar_test_'
            ) as f:
                f.write(EICAR_TEST_STRING)
                self._eicar_temp_path = f.name

            # Scan the temporary file
            self._start_scan(self._eicar_temp_path)
        except IOError as e:
            logger.error(f"Error creating EICAR test file: {e}")
            self._status_banner.set_title("Error: Could not create test file")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")
            self._status_banner.set_revealed(True)

    def _start_scan(self, path: str):
        """
        Start a scan operation.

        Sets up the UI for scanning and starts an async scan operation.

        Args:
            path: The path to scan
        """
        self._is_scanning = True
        self._scan_button.set_sensitive(False)
        self._eicar_button.set_sensitive(False)
        self._browse_button.set_sensitive(False)
        self._profile_dropdown.set_sensitive(False)
        self._manage_profiles_btn.set_sensitive(False)

        # Show scanning message
        self._status_banner.set_title("Scanning...")
        self._status_banner.remove_css_class("error")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("warning")
        self._status_banner.set_revealed(True)

        # Update tray if callback is set
        if self._on_scan_state_changed:
            self._on_scan_state_changed(True)

        # Start async scan
        GLib.idle_add(self._run_scan, path)

    def _run_scan(self, path: str):
        """
        Run the scan operation.

        Performs the actual scan and updates results display.

        Args:
            path: The path to scan

        Returns:
            False to prevent GLib.idle_add from repeating
        """
        try:
            logger.info(f"Starting scan of: {path}")
            # Get profile exclusions if a profile is selected
            profile_exclusions = None
            if self._selected_profile and self._selected_profile.exclusions:
                profile_exclusions = self._selected_profile.exclusions
            result = self._scanner.scan_sync(path, profile_exclusions=profile_exclusions)

            # Process scan results
            self._display_scan_results(result)

            # Log summary
            logger.info(
                f"Scan complete: {result.infected_count} threats found, "
                f"{result.scanned_files} files scanned"
            )
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self._status_banner.set_title(f"Scan error: {str(e)}")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")
            self._status_banner.set_revealed(True)
        finally:
            # Clean up
            self._is_scanning = False
            self._scan_button.set_sensitive(True)
            self._eicar_button.set_sensitive(True)
            self._browse_button.set_sensitive(True)
            self._profile_dropdown.set_sensitive(True)
            self._manage_profiles_btn.set_sensitive(True)

            # Clean up EICAR temp file if it was created
            if self._eicar_temp_path and os.path.exists(self._eicar_temp_path):
                try:
                    os.remove(self._eicar_temp_path)
                    self._eicar_temp_path = ""
                except OSError as e:
                    logger.warning(f"Could not remove EICAR temp file: {e}")

            # Update tray if callback is set
            if self._on_scan_state_changed:
                self._on_scan_state_changed(False)

        return False

    def _create_results_section(self):
        """Create the results display section."""
        results_group = Adw.PreferencesGroup()
        results_group.set_title("Scan Results")
        results_group.set_margin_top(12)

        # Create scrolled window for threats list
        self._threats_scrolled = Gtk.ScrolledWindow()
        self._threats_scrolled.set_vexpand(True)
        self._threats_scrolled.set_hexpand(True)
        self._threats_scrolled.set_min_content_height(200)

        # Create list box for threat items
        self._threats_list = Gtk.ListBox()
        self._threats_list.add_css_class("boxed-list")
        self._threats_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._threats_scrolled.set_child(self._threats_list)

        results_group.add(self._threats_scrolled)
        self.append(results_group)

    def _display_scan_results(self, result: ScanResult):
        """
        Display scan results in the results section.

        Shows threat details, clean count, and provides actions for each threat.

        Args:
            result: The ScanResult object containing scan details
        """
        # Clear previous results
        while True:
            child = self._threats_list.get_first_child()
            if child is None:
                break
            self._threats_list.remove(child)

        # Store all threat details for pagination
        self._all_threat_details = result.threat_details or []
        self._displayed_threat_count = 0
        self._load_more_row = None

        # Check if result set is large
        if len(self._all_threat_details) > LARGE_RESULT_THRESHOLD:
            # Show warning banner
            warning_row = Gtk.ListBoxRow()
            warning_row.set_selectable(False)
            warning_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            warning_box.set_margin_top(8)
            warning_box.set_margin_bottom(8)
            warning_box.set_margin_start(12)
            warning_box.set_margin_end(12)

            warning_label = Gtk.Label()
            warning_label.set_markup(
                f"<b>Large Result Set</b>\n"
                f"Found <b>{len(self._all_threat_details)}</b> threats. "
                f"Showing first <b>{INITIAL_DISPLAY_LIMIT}</b>."
            )
            warning_label.set_wrap(True)
            warning_label.set_justify(Gtk.Justification.CENTER)
            warning_box.append(warning_label)

            warning_row.set_child(warning_box)
            warning_row.add_css_class("large-result-warning")
            self._threats_list.append(warning_row)

        # Display initial batch of threats
        self._load_more_threats(INITIAL_DISPLAY_LIMIT)

        # Update status banner
        if result.infected_count > 0:
            self._status_banner.set_title(
                f"Scan complete: {result.infected_count} threat(s) found"
            )
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")
        else:
            self._status_banner.set_title(
                f"Scan complete: No threats found ({result.scanned_files} files scanned)"
            )
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.remove_css_class("warning")
        self._status_banner.set_revealed(True)

    def _load_more_threats(self, limit: int):
        """
        Load more threat items up to the specified limit.

        Args:
            limit: Maximum number of threats to display
        """
        # Remove previous "Load More" row if it exists
        if self._load_more_row:
            self._threats_list.remove(self._load_more_row)
            self._load_more_row = None

        # Display threats up to the limit
        while (
            self._displayed_threat_count < limit
            and self._displayed_threat_count < len(self._all_threat_details)
        ):
            threat = self._all_threat_details[self._displayed_threat_count]
            self._add_threat_row(threat)
            self._displayed_threat_count += 1

        # Add "Load More" button if there are more threats
        if self._displayed_threat_count < len(self._all_threat_details):
            self._load_more_row = Gtk.ListBoxRow()
            self._load_more_row.set_selectable(False)

            load_more_btn = Gtk.Button(
                label=f"Show More ({len(self._all_threat_details) - self._displayed_threat_count} remaining)"
            )
            load_more_btn.set_margin_top(6)
            load_more_btn.set_margin_bottom(6)
            load_more_btn.set_margin_start(6)
            load_more_btn.set_margin_end(6)
            load_more_btn.add_css_class("load-more-row")
            load_more_btn.connect(
                "clicked",
                lambda btn: self._load_more_threats(
                    self._displayed_threat_count + LOAD_MORE_BATCH_SIZE
                )
            )

            self._load_more_row.set_child(load_more_btn)
            self._threats_list.append(self._load_more_row)

    def _add_threat_row(self, threat: ThreatDetail):
        """
        Add a threat detail row to the results list.

        Args:
            threat: The ThreatDetail object to display
        """
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.add_css_class("threat-card")

        # Main container
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        container.set_margin_top(8)
        container.set_margin_bottom(8)
        container.set_margin_start(12)
        container.set_margin_end(12)

        # Header box (threat name + severity badge)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # Threat name
        name_label = Gtk.Label(label=threat.threat_name)
        name_label.set_halign(Gtk.Align.START)
        name_label.set_hexpand(True)
        name_label.add_css_class("title-3")
        header_box.append(name_label)

        # Severity badge
        severity_badge = Gtk.Label(label=threat.severity.upper())
        severity_badge.add_css_class("severity-badge")
        severity_badge.add_css_class(f"severity-{threat.severity}")
        header_box.append(severity_badge)

        container.append(header_box)

        # File path
        path_label = Gtk.Label(label=threat.file_path)
        path_label.set_wrap(True)
        path_label.set_selectable(True)
        path_label.set_halign(Gtk.Align.START)
        path_label.add_css_class("monospace")
        path_label.add_css_class("dim-label")
        container.append(path_label)

        # Category info
        if threat.category:
            category_label = Gtk.Label(label=f"Category: {threat.category}")
            category_label.set_halign(Gtk.Align.START)
            category_label.add_css_class("dim-label")
            container.append(category_label)

        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.START)
        button_box.set_margin_top(4)

        # Quarantine button
        quarantine_btn = Gtk.Button(label="Quarantine")
        quarantine_btn.set_size_request(100, -1)
        quarantine_btn.connect(
            "clicked",
            self._on_quarantine_clicked,
            threat
        )
        button_box.append(quarantine_btn)

        # Copy path button
        copy_btn = Gtk.Button(label="Copy Path")
        copy_btn.set_size_request(100, -1)
        copy_btn.connect(
            "clicked",
            lambda btn: copy_to_clipboard(threat.file_path)
        )
        button_box.append(copy_btn)

        container.append(button_box)

        row.set_child(container)
        self._threats_list.append(row)

    def _on_quarantine_clicked(self, button, threat: ThreatDetail):
        """
        Handle quarantine button click.

        Moves the threat file to quarantine.

        Args:
            button: The clicked button
            threat: The ThreatDetail to quarantine
        """
        try:
            result = self._quarantine_manager.quarantine_file(
                threat.file_path, threat.threat_name
            )

            if result.status == QuarantineStatus.SUCCESS:
                self._status_banner.set_title(f"Quarantined: {threat.threat_name}")
                self._status_banner.add_css_class("success")
                self._status_banner.remove_css_class("error")
                self._status_banner.remove_css_class("warning")
                # Disable button after successful quarantine
                button.set_sensitive(False)
                button.set_label("Quarantined")
            else:
                error_msg = result.error_message or "Unknown error"
                is_handled = False

                if result.status == QuarantineStatus.ALREADY_QUARANTINED:
                    error_msg = "File is already quarantined"
                    is_handled = True
                elif result.status == QuarantineStatus.FILE_NOT_FOUND:
                    # File may have been removed by ClamAV daemon's on-access scanning
                    error_msg = "File not found - may have been handled by ClamAV daemon"
                    is_handled = True
                    button.set_sensitive(False)
                    button.set_label("Handled")
                elif result.status == QuarantineStatus.PERMISSION_DENIED:
                    error_msg = "Permission denied"

                if is_handled:
                    self._status_banner.set_title(error_msg)
                    self._status_banner.add_css_class("warning")
                    self._status_banner.remove_css_class("success")
                    self._status_banner.remove_css_class("error")
                else:
                    self._status_banner.set_title(f"Quarantine failed: {error_msg}")
                    self._status_banner.add_css_class("error")
                    self._status_banner.remove_css_class("success")
                    self._status_banner.remove_css_class("warning")

            self._status_banner.set_revealed(True)
        except Exception as e:
            logger.error(f"Error quarantining file: {e}")
            self._status_banner.set_title(f"Error: {str(e)}")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")
            self._status_banner.set_revealed(True)

    def _create_status_bar(self):
        """Create the status banner."""
        self._status_banner = Adw.Banner()
        self._status_banner.set_title("Ready to scan")
        self._status_banner.set_button_label("Dismiss")
        self._status_banner.connect("button-clicked", self._on_status_banner_dismissed)
        self.append(self._status_banner)

    def _check_clamav_status(self):
        """
        Check ClamAV installation status.

        Shows a warning if ClamAV is not installed.

        Returns:
            False to prevent GLib.idle_add from repeating
        """
        if not check_clamav_installed():
            self._status_banner.set_title(
                "Warning: ClamAV is not installed. Please install it to use the scanner."
            )
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.set_revealed(True)
            self._scan_button.set_sensitive(False)
            self._eicar_button.set_sensitive(False)

        return False

    def set_scan_state_changed_callback(self, callback):
        """
        Set a callback for scan state changes.

        Used by the tray integration to update the tray icon when scanning.

        Args:
            callback: Function to call with (is_scanning: bool) when state changes
        """
        self._on_scan_state_changed = callback

    def get_selected_profile(self):
        """
        Get the currently selected scan profile.

        Returns:
            The selected ScanProfile, or None if no profile is selected.
        """
        return self._selected_profile

    def get_scan_results_text(self) -> str:
        """
        Get scan results formatted as text.

        Used for copying/sharing results.

        Returns:
            Formatted text representation of scan results
        """
        return format_results_as_text(self._all_threat_details)