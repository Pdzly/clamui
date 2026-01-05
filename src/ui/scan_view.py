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

        # Current selected path
        self._selected_path: str = ""

        # Scanning state
        self._is_scanning = False

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
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
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
                # Apply profile's targets to the selected path
                if self._selected_profile.targets:
                    first_target = self._selected_profile.targets[0]
                    # Expand ~ in paths
                    if first_target.startswith("~"):
                        first_target = os.path.expanduser(first_target)
                    if os.path.exists(first_target):
                        self._set_selected_path(first_target)
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

    def _create_selection_section(self):
        """Create the file/folder selection UI section."""
        # Container for selection UI
        selection_group = Adw.PreferencesGroup()
        selection_group.set_title("Scan Target")

        # Path display row
        self._path_row = Adw.ActionRow()
        self._path_row.set_title("Selected Path")
        self._path_row.set_subtitle("Drop files here or select on the right")
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
            parent_dir = (
                os.path.dirname(self._selected_path)
                if os.path.isfile(self._selected_path)
                else self._selected_path
            )
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
            initial_dir = (
                self._selected_path
                if os.path.isdir(self._selected_path)
                else os.path.dirname(self._selected_path)
            )
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

        # Check if this is a portal path that couldn't be fully resolved
        if formatted_path.startswith("[Portal]"):
            self._path_label.set_tooltip_text(
                "The exact location cannot be displayed in Flatpak mode, "
                "but scanning will work normally."
            )
            # Update subtitle to indicate portal access
            if os.path.isdir(path):
                self._path_row.set_subtitle("Folder selected (via Flatpak portal)")
            else:
                self._path_row.set_subtitle("File selected (via Flatpak portal)")
        else:
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
            # In Flatpak, use /tmp explicitly so the host's clamdscan can access it
            temp_dir = "/tmp" if is_flatpak() else None
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", prefix="eicar_test_", delete=False, dir=temp_dir
            ) as f:
                f.write(EICAR_TEST_STRING)
                self._eicar_temp_path = f.name

            # Set the EICAR file as scan target and start scan
            self._selected_path = self._eicar_temp_path
            self._path_label.set_label("EICAR Test File")
            self._path_row.set_subtitle("Testing antivirus detection")
            self._start_scanning()

        except OSError as e:
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

        # Dismiss any previous status banner
        self._status_banner.set_revealed(False)

        # Hide previous results button
        self._hide_view_results()

        # Show progress section with status message
        if self._progress_section is not None:
            # Format path for display (handles Flatpak portal paths and truncation)
            display_path = format_scan_path(self._selected_path)
            if len(display_path) > 50:
                display_path = "..." + display_path[-47:]
            self._progress_label.set_label(f"Scanning {display_path}")
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
        self._path_row.set_sensitive(True)

        # Notify external handlers
        if self._on_scan_state_changed:
            self._on_scan_state_changed(self._is_scanning)

        # Show view results button and update status banner
        if result.status == ScanStatus.INFECTED:
            self._show_view_results(result.infected_count)
            self._status_banner.set_title(
                f"Scan complete - {result.infected_count} threat(s) detected"
            )
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.set_revealed(True)
        elif result.status == ScanStatus.CLEAN:
            self._show_view_results(0)
            self._status_banner.set_title("Scan complete - No threats found")
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("warning")
            self._status_banner.remove_css_class("error")
            self._status_banner.set_revealed(True)
        elif result.status == ScanStatus.ERROR:
            self._show_view_results(0)
            error_detail = result.error_message or result.stderr or "Unknown error"
            self._status_banner.set_title(f"Scan error: {error_detail}")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")
            self._status_banner.set_revealed(True)
            logger.error(
                f"Scan failed: {error_detail}, stdout={result.stdout!r}, stderr={result.stderr!r}"
            )
        else:
            self._show_view_results(0)
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

        # Stop progress animation and hide progress section
        self._stop_progress_pulse()

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
