# ClamUI Scan View
"""
Scan interface component for ClamUI with folder picker, scan button, and results display.
"""

import os
import tempfile

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from ..core.scanner import Scanner, ScanResult, ScanStatus
from ..core.utils import format_scan_path, check_clamav_installed, validate_dropped_files
from .fullscreen_dialog import FullscreenLogDialog

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
        """Set up CSS styling for drag-and-drop visual feedback."""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string("""
            .drop-active {
                border: 2px dashed @accent_color;
                border-radius: 12px;
                background-color: alpha(@accent_bg_color, 0.1);
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

        # Header box with fullscreen button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_halign(Gtk.Align.END)

        # Fullscreen button
        fullscreen_button = Gtk.Button()
        fullscreen_button.set_icon_name("view-fullscreen-symbolic")
        fullscreen_button.set_tooltip_text("View fullscreen")
        fullscreen_button.add_css_class("flat")
        fullscreen_button.connect("clicked", self._on_fullscreen_results_clicked)
        self._fullscreen_button = fullscreen_button

        header_box.append(fullscreen_button)
        results_group.set_header_suffix(header_box)

        # Results container
        results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        results_box.set_spacing(12)

        # Status banner (hidden by default)
        self._status_banner = Adw.Banner()
        self._status_banner.set_revealed(False)
        results_box.append(self._status_banner)

        # Results text view in a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.set_vexpand(True)
        scrolled.add_css_class("card")

        self._results_text = Gtk.TextView()
        self._results_text.set_editable(False)
        self._results_text.set_cursor_visible(False)
        self._results_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._results_text.set_left_margin(12)
        self._results_text.set_right_margin(12)
        self._results_text.set_top_margin(12)
        self._results_text.set_bottom_margin(12)
        self._results_text.add_css_class("monospace")

        # Set placeholder text
        buffer = self._results_text.get_buffer()
        buffer.set_text("No scan results yet.\n\nSelect a folder or file and click 'Scan' to begin.")

        scrolled.set_child(self._results_text)
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

        # Update results text
        buffer = self._results_text.get_buffer()
        buffer.set_text(f"Scanning: {self._selected_path}\n\nPlease wait...")

        # Hide any previous status banner
        self._status_banner.set_revealed(False)

        # Start async scan
        self._scanner.scan_async(
            self._selected_path,
            callback=self._on_scan_complete
        )

    def _set_scanning_state(self, is_scanning: bool):
        """
        Update UI to reflect scanning state.

        Args:
            is_scanning: Whether a scan is in progress
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

    def _on_scan_complete(self, result: ScanResult):
        """
        Handle scan completion.

        Args:
            result: The scan result from the scanner
        """
        self._set_scanning_state(False)
        self._display_results(result)
        return False  # Don't repeat GLib.idle_add

    def _clear_results(self):
        """Clear the results display."""
        buffer = self._results_text.get_buffer()
        buffer.set_text("")
        self._status_banner.set_revealed(False)

    def _display_results(self, result: ScanResult):
        """
        Display scan results in the UI.

        Args:
            result: The scan result to display
        """
        # Update status banner based on result
        if result.status == ScanStatus.CLEAN:
            self._status_banner.set_title("No threats found")
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.remove_css_class("warning")
        elif result.status == ScanStatus.INFECTED:
            self._status_banner.set_title(f"Threats detected: {result.infected_count} infected file(s)")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")
        elif result.status == ScanStatus.CANCELLED:
            self._status_banner.set_title("Scan cancelled")
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")
        else:  # ERROR
            self._status_banner.set_title(result.error_message or "Scan error occurred")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")

        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

        # Build results text
        lines = []

        # Header with scan status
        if result.status == ScanStatus.CLEAN:
            lines.append("SCAN COMPLETE - NO THREATS FOUND")
        elif result.status == ScanStatus.INFECTED:
            lines.append("WARNING: THREATS DETECTED")
        elif result.status == ScanStatus.CANCELLED:
            lines.append("SCAN CANCELLED")
        else:
            lines.append("SCAN ERROR")

        lines.append("=" * 50)
        lines.append("")

        # Path scanned
        lines.append(f"Scanned: {result.path}")
        lines.append("")

        # Summary statistics
        lines.append("Summary:")
        lines.append(f"  Scanned files: {result.scanned_files}")
        lines.append(f"  Scanned directories: {result.scanned_dirs}")
        lines.append(f"  Infected files: {result.infected_count}")
        lines.append("")

        # Infected files list
        if result.infected_files:
            lines.append("Infected Files:")
            for infected_file in result.infected_files:
                lines.append(f"  - {infected_file}")
            lines.append("")

        # Error message if present
        if result.error_message:
            lines.append(f"Error: {result.error_message}")
            lines.append("")

        # Raw output section
        if result.stdout:
            lines.append("-" * 50)
            lines.append("Full ClamAV Output:")
            lines.append("-" * 50)
            lines.append(result.stdout)

        if result.stderr and result.status == ScanStatus.ERROR:
            lines.append("-" * 50)
            lines.append("Error Output:")
            lines.append("-" * 50)
            lines.append(result.stderr)

        # Update the text view
        buffer = self._results_text.get_buffer()
        buffer.set_text("\n".join(lines))

    def _on_fullscreen_results_clicked(self, button: Gtk.Button):
        """Handle fullscreen button click for scan results."""
        # Get current content from results text view
        buffer = self._results_text.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        content = buffer.get_text(start, end, False)

        # Create and present the fullscreen dialog
        dialog = FullscreenLogDialog(
            title="Scan Results",
            content=content
        )
        dialog.present(self.get_root())

    @property
    def scanner(self) -> Scanner:
        """
        Get the scanner instance.

        Returns:
            The Scanner instance used by this view
        """
        return self._scanner

    def _on_test_clamav_clicked(self, button):
        """Handle Test ClamAV button click."""
        self._start_eicar_test()

    def _start_eicar_test(self):
        """Start the EICAR test scan."""
        # Create a temporary file with EICAR test string
        try:
            # Create temp file in a secure manner
            fd, temp_path = tempfile.mkstemp(suffix=".com", prefix="eicar_test_")
            self._eicar_temp_path = temp_path

            # Write the EICAR test string
            with os.fdopen(fd, 'w') as f:
                f.write(EICAR_TEST_STRING)

        except OSError as e:
            # Show error if temp file creation fails
            buffer = self._results_text.get_buffer()
            buffer.set_text(f"Failed to create test file: {e}")
            self._status_banner.set_title("Test failed - could not create test file")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")
            self._status_banner.set_revealed(True)
            return

        self._set_scanning_state(True)
        self._clear_results()

        # Update results text
        buffer = self._results_text.get_buffer()
        buffer.set_text(
            "Testing ClamAV with EICAR test file...\n\n"
            "The EICAR test file is an industry-standard antivirus test pattern.\n"
            "If ClamAV is working correctly, it should detect this as infected.\n\n"
            "Please wait..."
        )

        # Hide any previous status banner
        self._status_banner.set_revealed(False)

        # Start async scan with EICAR-specific callback
        self._scanner.scan_async(
            self._eicar_temp_path,
            callback=self._on_eicar_scan_complete
        )

    def _on_eicar_scan_complete(self, result: ScanResult):
        """
        Handle EICAR test scan completion.

        Args:
            result: The scan result from the scanner
        """
        # Clean up temp file first (always, regardless of result)
        self._cleanup_eicar_temp_file()

        self._set_scanning_state(False)
        self._display_eicar_results(result)
        return False  # Don't repeat GLib.idle_add

    def _cleanup_eicar_temp_file(self):
        """Clean up the temporary EICAR test file."""
        if self._eicar_temp_path and os.path.exists(self._eicar_temp_path):
            try:
                os.remove(self._eicar_temp_path)
            except OSError:
                pass  # Ignore cleanup errors
        self._eicar_temp_path = ""

    def _display_eicar_results(self, result: ScanResult):
        """
        Display EICAR test results in the UI.

        Args:
            result: The scan result to display
        """
        # Determine if the test was successful (EICAR detected)
        test_passed = result.status == ScanStatus.INFECTED

        # Update status banner
        if test_passed:
            self._status_banner.set_title("ClamAV is working correctly!")
            self._status_banner.add_css_class("success")
            self._status_banner.remove_css_class("error")
            self._status_banner.remove_css_class("warning")
        elif result.status == ScanStatus.CANCELLED:
            self._status_banner.set_title("Test cancelled")
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")
        elif result.status == ScanStatus.ERROR:
            self._status_banner.set_title(result.error_message or "Test error occurred")
            self._status_banner.add_css_class("error")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("warning")
        else:
            # CLEAN status means EICAR wasn't detected - this is a problem
            self._status_banner.set_title("Warning: ClamAV did not detect test file")
            self._status_banner.add_css_class("warning")
            self._status_banner.remove_css_class("success")
            self._status_banner.remove_css_class("error")

        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

        # Build results text
        lines = []

        if test_passed:
            lines.append("CLAMAV TEST PASSED")
            lines.append("=" * 50)
            lines.append("")
            lines.append("ClamAV correctly detected the EICAR test file as infected.")
            lines.append("Your antivirus installation is working properly.")
        elif result.status == ScanStatus.CANCELLED:
            lines.append("TEST CANCELLED")
            lines.append("=" * 50)
        elif result.status == ScanStatus.ERROR:
            lines.append("TEST ERROR")
            lines.append("=" * 50)
            lines.append("")
            if result.error_message:
                lines.append(f"Error: {result.error_message}")
        else:
            lines.append("CLAMAV TEST WARNING")
            lines.append("=" * 50)
            lines.append("")
            lines.append("ClamAV did NOT detect the EICAR test file.")
            lines.append("This may indicate a problem with your ClamAV installation")
            lines.append("or virus database.")

        lines.append("")

        # Detection details if infected
        if result.infected_files:
            lines.append("Detection Details:")
            for infected_file in result.infected_files:
                lines.append(f"  - {infected_file}")
            lines.append("")

        # Raw output section
        if result.stdout:
            lines.append("-" * 50)
            lines.append("ClamAV Output:")
            lines.append("-" * 50)
            lines.append(result.stdout)

        if result.stderr and result.status == ScanStatus.ERROR:
            lines.append("-" * 50)
            lines.append("Error Output:")
            lines.append("-" * 50)
            lines.append(result.stderr)

        # Update the text view
        buffer = self._results_text.get_buffer()
        buffer.set_text("\n".join(lines))
