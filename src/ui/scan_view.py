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

from ..core.quarantine import QuarantineManager, QuarantineStatus
from ..core.scanner import Scanner, ScanResult, ScanStatus, ThreatDetail
from ..core.utils import (
    check_clamav_installed,
    copy_to_clipboard,
    format_results_as_text,
    format_scan_path,
    validate_dropped_files,
)
from .fullscreen_dialog import FullscreenLogDialog
from .profile_dialogs import ProfileListDialog
from .utils import add_row_icon

if TYPE_CHECKING:
    from ..profiles.models import ScanProfile
    from ..profiles.profile_manager import ProfileManager

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

        # Raw scan output and current result (for export functionality)
        self._raw_output: str = ""
        self._current_result: ScanResult | None = None

        # Scan state change callback (for tray integration)
        self._on_scan_state_changed = None

        # Profile management state
        self._selected_profile: "ScanProfile | None" = None
        self._profile_list: list["ScanProfile"] = []
        self._profile_string_list: Gtk.StringList | None = None
        self._profile_dropdown: Gtk.DropDown | None = None

        # Set up the UI
        self._setup_ui()

        # Check backend status on load
        GLib.idle_add(self._update_backend_status)

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
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
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

        # Backend status row
        backend_row = Adw.ActionRow()
        backend_row.set_title("Scan Backend")
        backend_row.set_activatable(False)
        add_row_icon(backend_row, "system-run-symbolic")

        # Status suffix with icon + label
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_box.set_valign(Gtk.Align.CENTER)
        self._backend_status_icon = Gtk.Image.new_from_icon_name("content-loading-symbolic")
        self._backend_status_label = Gtk.Label(label="Checking...")
        self._backend_status_label.add_css_class("dim-label")
        status_box.append(self._backend_status_icon)
        status_box.append(self._backend_status_label)
        backend_row.add_suffix(status_box)
        profile_group.add(backend_row)

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

    def _update_backend_status(self):
        """
        Check and update the scan backend status.

        Updates the backend status indicator in the profile section
        to show the current state of the antivirus backend.
        """
        is_available = check_clamav_installed()

        if is_available:
            self._backend_status_label.set_label("Ready")
            self._backend_status_icon.set_from_icon_name("emblem-ok-symbolic")
            self._backend_status_label.remove_css_class("error")
            self._backend_status_label.add_css_class("success")
        else:
            self._backend_status_label.set_label("Not Available")
            self._backend_status_icon.set_from_icon_name("dialog-warning-symbolic")
            self._backend_status_label.add_css_class("error")
            self._backend_status_label.remove_css_class("success")

        return False

    def _create_selection_section(self):
        """Create the file/folder selection UI section."""
        # Container for selection UI
        selection_group = Adw.PreferencesGroup()
        selection_group.set_title("Scan Target")
        selection_group.set_description("Choose a folder or file to scan")

        # Path display row
        self._path_row = Adw.ActionRow()
        self._path_row.set_title("Selected Path")
        self._path_row.set_subtitle("No path selected")
        add_row_icon(self._path_row, "folder-symbolic")

        # Path label for displaying selected path
        self._path_label = Gtk.Label()
        self._path_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        self._path_label.add_css_class("monospace")

        # Button box for file/folder selection
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_valign(Gtk.Align.CENTER)

        # Select File button
        self._select_file_button = Gtk.Button()
        self._select_file_button.set_icon_name("document-open-symbolic")
        self._select_file_button.set_tooltip_text("Select File")
        self._select_file_button.add_css_class("flat")
        self._select_file_button.connect("clicked", self._on_select_file_clicked)
        button_box.append(self._select_file_button)

        # Select Folder button
        self._select_folder_button = Gtk.Button()
        self._select_folder_button.set_icon_name("folder-open-symbolic")
        self._select_folder_button.set_tooltip_text("Select Folder")
        self._select_folder_button.add_css_class("flat")
        self._select_folder_button.connect("clicked", self._on_select_folder_clicked)
        button_box.append(self._select_folder_button)

        self._path_row.add_suffix(self._path_label)
        self._path_row.add_suffix(button_box)

        selection_group.add(self._path_row)

        self.append(selection_group)

    def _on_select_file_clicked(self, button):
        """
        Handle select file button click.

        Opens a file chooser dialog to select a file.

        Args:
            button: The Gtk.Button that was clicked
        """
        root = self.get_root()
        if root is None or not isinstance(root, Gtk.Window):
            return

        dialog = Gtk.FileDialog()
        dialog.set_title("Select File to Scan")

        # Set initial folder if a path is already selected
        if self._selected_path:
            parent_dir = os.path.dirname(self._selected_path) if os.path.isfile(self._selected_path) else self._selected_path
            if os.path.isdir(parent_dir):
                dialog.set_initial_folder(Gio.File.new_for_path(parent_dir))

        def on_file_selected(dialog, result):
            try:
                file = dialog.open_finish(result)
                if file:
                    path = file.get_path()
                    if path:
                        self._set_selected_path(path)
            except GLib.GError:
                pass  # User cancelled

        dialog.open(root, None, on_file_selected)

    def _on_select_folder_clicked(self, button):
        """
        Handle select folder button click.

        Opens a file chooser dialog to select a folder.

        Args:
            button: The Gtk.Button that was clicked
        """
        root = self.get_root()
        if root is None or not isinstance(root, Gtk.Window):
            return

        dialog = Gtk.FileDialog()
        dialog.set_title("Select Folder to Scan")

        # Set initial folder if a path is already selected
        if self._selected_path:
            initial_dir = self._selected_path if os.path.isdir(self._selected_path) else os.path.dirname(self._selected_path)
            if os.path.isdir(initial_dir):
                dialog.set_initial_folder(Gio.File.new_for_path(initial_dir))

        def on_folder_selected(dialog, result):
            try:
                file = dialog.select_folder_finish(result)
                if file:
                    path = file.get_path()
                    if path:
                        self._set_selected_path(path)
            except GLib.GError:
                pass  # User cancelled

        dialog.select_folder(root, None, on_folder_selected)

    def _set_selected_path(self, path: str):
        """
        Set the selected path and update the UI.

        Args:
            path: The file or folder path to scan
        """
        self._selected_path = path
        formatted_path = format_scan_path(path)
        self._path_label.set_label(formatted_path)
        self._path_label.set_tooltip_text(path)
        # Update subtitle to show path type
        if os.path.isdir(path):
            self._path_row.set_subtitle("Folder selected")
        else:
            self._path_row.set_subtitle("File selected")

    def _create_scan_section(self):
        """Create the scan control section."""
        scan_group = Adw.PreferencesGroup()

        # Button container
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_spacing(12)
        button_box.set_margin_top(12)
        button_box.set_margin_bottom(12)

        # Scan button
        self._scan_button = Gtk.Button()
        self._scan_button.set_label("Start Scan")
        self._scan_button.add_css_class("suggested-action")
        self._scan_button.set_size_request(150, -1)
        self._scan_button.connect("clicked", self._on_scan_clicked)
        button_box.append(self._scan_button)

        # EICAR Test button
        self._eicar_button = Gtk.Button()
        self._eicar_button.set_label("EICAR Test")
        self._eicar_button.set_tooltip_text("Run a scan with EICAR test file to verify antivirus detection")
        self._eicar_button.set_size_request(120, -1)
        self._eicar_button.connect("clicked", self._on_eicar_test_clicked)
        button_box.append(self._eicar_button)

        scan_group.add(button_box)

        self.append(scan_group)

    def _on_scan_clicked(self, button):
        """
        Handle scan button click.

        Starts the scan operation if a path is selected.

        Args:
            button: The Gtk.Button that was clicked
        """
        if not self._selected_path:
            self._status_banner.set_title("Please select a file or folder to scan")
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")
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
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                prefix="eicar_test_",
                delete=False
            ) as f:
                f.write(EICAR_TEST_STRING)
                self._eicar_temp_path = f.name

            # Set the EICAR file as scan target and start scan
            self._selected_path = self._eicar_temp_path
            self._path_label.set_label("EICAR Test File")
            self._path_row.set_subtitle("Testing antivirus detection")
            self._start_scanning()

        except (OSError, IOError) as e:
            logger.error(f"Failed to create EICAR test file: {e}")
            self._status_banner.set_title(f"Failed to create EICAR test file: {e}")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")
            self._status_banner.set_revealed(True)

    def _start_scanning(self):
        """Start the scanning process."""
        self._is_scanning = True
        self._scan_button.set_sensitive(False)
        self._eicar_button.set_sensitive(False)
        self._path_row.set_sensitive(False)

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
        Perform the actual scan.

        This runs in a background thread to avoid blocking the UI.
        """
        try:
            result = self._scanner.scan_sync(self._selected_path)
            # Schedule UI update on main thread
            GLib.idle_add(self._on_scan_complete, result)
        except Exception as e:
            logger.error(f"Scan error: {e}")
            GLib.idle_add(self._on_scan_error, str(e))

    def _on_scan_complete(self, result: ScanResult):
        """
        Handle scan completion.

        Updates the UI with scan results and manages quarantine if needed.

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

        # Update scanning state
        self._is_scanning = False
        self._scan_button.set_sensitive(True)
        self._eicar_button.set_sensitive(True)
        self._path_row.set_sensitive(True)

        # Notify external handlers
        if self._on_scan_state_changed:
            self._on_scan_state_changed(self._is_scanning)

        # Check if threats were found
        if result.status == ScanStatus.INFECTED:
            self._display_scan_results(result)

            # Show quarantine offer if there are threats
            if result.infected_count > 0:
                self._show_quarantine_dialog(result)
        elif result.status == ScanStatus.CLEAN:
            self._status_banner.set_title("✓ Scan complete - No threats found")
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("warning")
            self._status_banner.remove_css_class("error")
            self._status_banner.set_revealed(True)
            self._clear_results()
        else:
            # Error or other status
            self._status_banner.set_title(f"Scan completed with status: {result.status.value}")
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")
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

        self._is_scanning = False
        self._scan_button.set_sensitive(True)
        self._eicar_button.set_sensitive(True)
        self._path_row.set_sensitive(True)

        # Notify external handlers
        if self._on_scan_state_changed:
            self._on_scan_state_changed(self._is_scanning)

        self._status_banner.set_title(f"Scan error: {error_msg}")
        self._status_banner.add_css_class("error")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("warning")
        self._status_banner.set_revealed(True)

    def _display_scan_results(self, result: ScanResult):
        """
        Display scan results in the results area.

        Populates the threats list with results and implements pagination
        for large result sets.

        Args:
            result: The ScanResult object containing threat details
        """
        # Clear previous results
        self._clear_results()

        # Store current result for export functionality
        self._current_result = result
        self._raw_output = result.stdout

        # Store threat details for pagination
        self._all_threat_details = result.threat_details

        # Show large result warning if needed
        if len(result.threat_details) > LARGE_RESULT_THRESHOLD:
            warning_banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            warning_banner.add_css_class("large-result-warning")
            warning_banner.set_margin_bottom(12)

            warning_label = Gtk.Label()
            warning_label.set_markup(
                f"<b>Large result set:</b> Found {len(result.threat_details)} threats. "
                f"Displaying first {INITIAL_DISPLAY_LIMIT}."
            )
            warning_label.set_wrap(True)
            warning_banner.append(warning_label)

            self._results_container.append(warning_banner)

        # Display initial batch of threats
        self._displayed_threat_count = 0
        self._load_more_threats(INITIAL_DISPLAY_LIMIT)

        # Update status
        self._status_banner.set_title(
            f"⚠ Scan complete - {result.infected_count} threat(s) detected"
        )
        self._status_banner.add_css_class("warning")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("error")
        self._status_banner.set_revealed(True)

    def _load_more_threats(self, count: int):
        """
        Load and display more threats from the results.

        Used for pagination of large result sets.

        Args:
            count: Number of threats to load and display
        """
        start_idx = self._displayed_threat_count
        end_idx = min(start_idx + count, len(self._all_threat_details))

        for threat in self._all_threat_details[start_idx:end_idx]:
            threat_box = self._create_threat_box(threat)
            self._threats_list.append(threat_box)
            self._displayed_threat_count += 1

        # Add "Load More" button if there are more threats to display
        if self._displayed_threat_count < len(self._all_threat_details):
            # Remove previous load more button if it exists
            if self._load_more_row is not None:
                self._threats_list.remove(self._load_more_row)

            load_more_row = Gtk.ListBoxRow()
            load_more_row.add_css_class("load-more-row")
            load_more_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            load_more_box.set_halign(Gtk.Align.CENTER)

            remaining = len(self._all_threat_details) - self._displayed_threat_count
            load_more_label = Gtk.Label()
            load_more_label.set_markup(
                f"<span size='small'>Show {min(LOAD_MORE_BATCH_SIZE, remaining)} more threats</span>"
            )
            load_more_box.append(load_more_label)
            load_more_row.set_child(load_more_box)
            load_more_row.set_activatable(True)
            load_more_row.connect("activated", self._on_load_more_clicked)

            self._threats_list.append(load_more_row)
            self._load_more_row = load_more_row

    def _on_load_more_clicked(self, row):
        """
        Handle load more button click.

        Loads the next batch of threats.

        Args:
            row: The Gtk.ListBoxRow that was activated
        """
        self._load_more_threats(LOAD_MORE_BATCH_SIZE)

    def _create_threat_box(self, threat: ThreatDetail) -> Gtk.Widget:
        """
        Create a UI widget for a single threat.

        Args:
            threat: The ThreatDetail to display

        Returns:
            A Gtk.Widget containing the threat information
        """
        threat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        threat_box.add_css_class("threat-card")
        threat_box.set_margin_start(12)
        threat_box.set_margin_end(12)
        threat_box.set_margin_top(6)
        threat_box.set_margin_bottom(6)

        # Threat name and severity
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_bottom(4)

        name_label = Gtk.Label()
        name_label.set_label(threat.threat_name)
        name_label.set_xalign(0)
        name_label.set_wrap(True)
        name_label.add_css_class("monospace")

        severity_badge = Gtk.Label()
        severity_badge.set_label(threat.severity.upper())
        severity_badge.add_css_class("severity-badge")
        severity_badge.add_css_class(f"severity-{threat.severity}")
        severity_badge.set_halign(Gtk.Align.END)

        header_box.append(name_label)
        header_box.append(severity_badge)

        threat_box.append(header_box)

        # Threat path
        path_label = Gtk.Label()
        path_label.set_label(threat.file_path)
        path_label.set_xalign(0)
        path_label.set_wrap(True)
        path_label.set_selectable(True)
        path_label.add_css_class("monospace")
        path_label.add_css_class("dim-label")
        path_label.set_size_request(400, -1)

        threat_box.append(path_label)

        return threat_box

    def _clear_results(self):
        """Clear all scan results from the display."""
        # Clear any extra children from results container (like warning banners)
        # Keep only the threats scrolled window
        child = self._results_container.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            if child != self._threats_scrolled:
                self._results_container.remove(child)
            child = next_child

        # Clear threat list
        child = self._threats_list.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._threats_list.remove(child)
            child = next_child

        # Reset pagination state
        self._displayed_threat_count = 0
        self._all_threat_details = []
        self._load_more_row = None

    def _show_quarantine_dialog(self, result: ScanResult):
        """
        Show the quarantine offer dialog.

        Prompts the user to quarantine detected threats.

        Args:
            result: The ScanResult containing threats to quarantine
        """
        root = self.get_root()
        if root is None or not isinstance(root, Gtk.Window):
            return

        dialog = Gtk.AlertDialog()
        dialog.set_modal(True)
        dialog.set_message("Quarantine Threats?")
        dialog.set_detail(
            f"Found {result.infected_count} threat(s). "
            "Do you want to move them to quarantine for safety?"
        )
        dialog.set_buttons(["Cancel", "Quarantine"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(1)

        def on_choose(dialog, result_async):
            try:
                choice = dialog.choose_finish(result_async)
                if choice == 1:  # "Quarantine" was selected
                    self._quarantine_threats(result)
            except Exception as e:
                logger.error(f"Error in quarantine dialog: {e}")

        dialog.choose(root, None, on_choose)

    def _quarantine_threats(self, result: ScanResult):
        """
        Quarantine the detected threats.

        Args:
            result: The ScanResult containing threats to quarantine
        """
        quarantined = []
        failed = []

        for threat in result.threat_details:
            try:
                qresult = self._quarantine_manager.quarantine_file(
                    threat.file_path, threat.threat_name
                )
                if qresult.status == QuarantineStatus.SUCCESS:
                    quarantined.append(threat.threat_name)
                else:
                    # Capture both status and error message for better diagnostics
                    error_info = qresult.error_message or str(qresult.status.value)
                    failed.append((threat.threat_name, error_info))
                    logger.warning(
                        f"Failed to quarantine {threat.file_path}: "
                        f"status={qresult.status.value}, error={qresult.error_message}"
                    )
            except Exception as e:
                failed.append((threat.threat_name, str(e)))
                logger.error(f"Exception quarantining {threat.file_path}: {e}")

        # Show result message
        if quarantined and not failed:
            msg = f"✓ Successfully quarantined {len(quarantined)} threat(s)"
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("warning")
            self._status_banner.remove_css_class("error")
        elif failed and not quarantined:
            # Show more specific error information
            first_error = failed[0][1] if failed else "Unknown error"
            msg = f"✗ Failed to quarantine: {first_error}"
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("warning")
            self._status_banner.remove_css_class("success")
        else:
            msg = f"⚠ Quarantined {len(quarantined)}, failed {len(failed)}"
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")

        self._status_banner.set_title(msg)
        self._status_banner.set_revealed(True)

    def _create_results_section(self):
        """Create the results display section."""
        results_group = Adw.PreferencesGroup()
        results_group.set_title("Scan Results")
        results_group.set_description("Detected threats")

        # Results container (for warnings, etc.)
        self._results_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._results_container.set_margin_top(12)
        self._results_container.set_margin_start(12)
        self._results_container.set_margin_end(12)

        # Create scrolled window for threats list
        self._threats_scrolled = Gtk.ScrolledWindow()
        self._threats_scrolled.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )
        self._threats_scrolled.set_min_content_height(300)

        # Create list box for threats
        self._threats_list = Gtk.ListBox()
        self._threats_list.set_selection_mode(Gtk.SelectionMode.NONE)

        self._threats_scrolled.set_child(self._threats_list)
        self._results_container.append(self._threats_scrolled)

        results_group.add(self._results_container)

        self.append(results_group)

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
