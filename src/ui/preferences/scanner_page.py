# ClamUI Scanner Settings Page
"""
Scanner Settings preference page for clamd.conf and scan backend settings.

This module provides the ScannerPage class which handles the UI and logic
for configuring ClamAV scanner settings and scan backend selection.
"""

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ...core.flatpak import is_flatpak
from ..utils import add_row_icon
from .base import (
    PreferencesPageMixin,
    populate_bool_field,
    populate_int_field,
    populate_text_field,
)


class ScannerPage(PreferencesPageMixin):
    """
    Scanner Settings preference page for scan backend and clamd.conf configuration.

    This class creates and manages the UI for configuring ClamAV scanner
    settings, including scan backend selection, file type scanning, performance,
    and logging settings.

    The page includes:
    - Scan backend selection (auto, daemon, clamscan) with auto-save
    - File location display for clamd.conf
    - File type scanning group (PE, ELF, OLE2, PDF, HTML, Archive)
    - Performance group (file size limits, recursion, max files)
    - Logging group (log file, verbose, syslog)

    Note: This class uses PreferencesPageMixin for shared utilities like
    permission indicators and file location displays.
    """

    @staticmethod
    def create_page(
        config_path: str,
        widgets_dict: dict,
        settings_manager,
        clamd_available: bool,
        parent_window,
    ) -> Adw.PreferencesPage:
        """
        Create the Scanner Settings preference page.

        Args:
            config_path: Path to the clamd.conf file
            widgets_dict: Dictionary to store widget references for later access
            settings_manager: SettingsManager instance for auto-save backend settings
            clamd_available: Whether clamd.conf exists and is available
            parent_window: Parent window for presenting dialogs

        Returns:
            Configured Adw.PreferencesPage ready to be added to preferences window
        """
        page = Adw.PreferencesPage(
            title="Scanner Settings",
            icon_name="document-properties-symbolic",
        )

        # Create a temporary instance to use mixin methods
        temp_instance = _ScannerPageHelper()
        temp_instance._parent_window = parent_window

        # Create scan backend settings group (ClamUI settings, auto-saved)
        ScannerPage._create_scan_backend_group(
            page, widgets_dict, settings_manager, temp_instance
        )

        # Create file location group
        temp_instance._create_file_location_group(
            page, "Configuration File", config_path, "clamd.conf location"
        )

        if clamd_available:
            # Create file type scanning group
            ScannerPage._create_scanning_group(page, widgets_dict, temp_instance)

            # Create performance group
            ScannerPage._create_performance_group(page, widgets_dict, temp_instance)

            # Create logging group
            ScannerPage._create_logging_group(page, widgets_dict, temp_instance)
        else:
            # Show message that clamd.conf is not available
            group = Adw.PreferencesGroup()
            group.set_title("Configuration Status")
            row = Adw.ActionRow()
            row.set_title("ClamD Configuration")
            row.set_subtitle("clamd.conf not found - Scanner settings unavailable")
            group.add(row)
            page.add(group)

        return page

    @staticmethod
    def _create_scan_backend_group(
        page: Adw.PreferencesPage, widgets_dict: dict, settings_manager, helper
    ):
        """
        Create the Scan Backend preferences group.

        Allows users to select between different scan backends:
        - Auto: Prefer daemon if available, fallback to clamscan
        - Daemon: Use clamd daemon only (faster, requires daemon running)
        - Clamscan: Use standalone clamscan only

        In Flatpak mode, only clamscan is available (daemon cannot be accessed
        from inside the sandbox), so a simplified informational view is shown.

        This group auto-saves changes immediately to settings.

        Args:
            page: The preferences page to add the group to
            widgets_dict: Dictionary to store widget references
            settings_manager: SettingsManager for auto-saving backend selection
            helper: Helper instance with _create_permission_indicator method
        """
        group = Adw.PreferencesGroup()
        group.set_title("Scan Backend")

        # In Flatpak, only clamscan is supported - show informational view
        if is_flatpak():
            group.set_description(
                "Flatpak uses the bundled standalone scanner for reliable, self-contained operation."
            )

            # Show current backend (always clamscan in Flatpak)
            backend_row = Adw.ActionRow()
            backend_row.set_title("Scan Backend")
            backend_row.set_subtitle(
                "Standalone Scanner (clamscan) — Bundled with Flatpak"
            )
            add_row_icon(backend_row, "security-high-symbolic")

            # Add info badge
            info_badge = Gtk.Label()
            info_badge.set_text("Flatpak")
            info_badge.add_css_class("dim-label")
            info_badge.add_css_class("caption")
            backend_row.add_suffix(info_badge)

            group.add(backend_row)

            # Info about why daemon is not available
            info_row = Adw.ActionRow()
            info_row.set_title("Daemon Scanner")
            info_row.set_subtitle("Not available in Flatpak (sandbox restriction)")
            add_row_icon(info_row, "dialog-information-symbolic")

            unavailable_label = Gtk.Label()
            unavailable_label.set_text("N/A")
            unavailable_label.add_css_class("dim-label")
            info_row.add_suffix(unavailable_label)

            group.add(info_row)

            page.add(group)
            return

        # Native installation - show full backend selection UI
        from ...core.utils import check_clamd_connection

        group.set_description("Select how ClamUI performs scans. Auto-saved.")

        # Scan backend dropdown
        backend_row = Adw.ComboRow()
        backend_model = Gtk.StringList()
        backend_model.append("Auto (prefer daemon)")
        backend_model.append("ClamAV Daemon (clamd)")
        backend_model.append("Standalone Scanner (clamscan)")
        backend_row.set_model(backend_model)
        backend_row.set_title("Scan Backend")

        # Set current selection from settings
        current_backend = settings_manager.get("scan_backend", "auto")
        backend_map = {"auto": 0, "daemon": 1, "clamscan": 2}
        backend_row.set_selected(backend_map.get(current_backend, 0))

        # Set initial subtitle based on current selection
        ScannerPage._update_backend_subtitle(
            backend_row, backend_map.get(current_backend, 0)
        )

        # Connect to selection changes - pass settings_manager in lambda
        backend_row.connect(
            "notify::selected",
            lambda row, pspec: ScannerPage._on_backend_changed(row, settings_manager),
        )

        widgets_dict["backend_row"] = backend_row
        group.add(backend_row)

        # Daemon status indicator
        status_row = Adw.ActionRow()
        status_row.set_title("Daemon Status")

        # Check daemon connection
        is_connected, message = check_clamd_connection()
        if is_connected:
            status_row.set_subtitle("✓ Daemon available")
            status_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
            status_icon.add_css_class("success")
        else:
            status_row.set_subtitle(f"⚠ Not available: {message}")
            status_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
            status_icon.add_css_class("warning")

        status_row.add_suffix(status_icon)
        widgets_dict["daemon_status_row"] = status_row
        group.add(status_row)

        # Refresh button
        refresh_button = Gtk.Button()
        refresh_button.set_label("Refresh Status")
        refresh_button.set_valign(Gtk.Align.CENTER)
        refresh_button.add_css_class("flat")
        refresh_button.connect(
            "clicked",
            lambda btn: ScannerPage._on_refresh_daemon_status(
                widgets_dict["daemon_status_row"]
            ),
        )
        status_row.add_suffix(refresh_button)

        # Learn more row - links to documentation
        learn_more_row = Adw.ActionRow()
        learn_more_row.set_title("Documentation")
        learn_more_row.set_subtitle("About scan backends")
        add_row_icon(learn_more_row, "help-about-symbolic")
        learn_more_row.set_activatable(True)
        learn_more_row.connect(
            "activated",
            lambda row: ScannerPage._on_learn_more_clicked(helper._parent_window),
        )

        # Add chevron to indicate it's clickable
        chevron = Gtk.Image.new_from_icon_name("go-next-symbolic")
        chevron.add_css_class("dim-label")
        learn_more_row.add_suffix(chevron)

        group.add(learn_more_row)

        page.add(group)

    @staticmethod
    def _update_backend_subtitle(row: Adw.ComboRow, selected: int):
        """
        Update the backend row subtitle based on the selected backend.

        Args:
            row: The ComboRow widget to update
            selected: Index of the selected backend (0=auto, 1=daemon, 2=clamscan)
        """
        subtitles = {
            0: "Recommended — Automatically uses daemon if available, falls back to clamscan for reliability",
            1: "Fastest — Instant startup with in-memory database, requires clamd service running",
            2: "Most compatible — Works anywhere, loads database each scan (3-10 sec startup)",
        }
        row.set_subtitle(subtitles.get(selected, subtitles[0]))

    @staticmethod
    def _on_backend_changed(row: Adw.ComboRow, settings_manager):
        """
        Handle scan backend selection change.

        Auto-saves the selected backend to settings.

        Args:
            row: The ComboRow that changed
            settings_manager: SettingsManager to save the selection
        """
        backend_reverse_map = {0: "auto", 1: "daemon", 2: "clamscan"}
        selected = row.get_selected()
        backend = backend_reverse_map.get(selected, "auto")
        settings_manager.set("scan_backend", backend)

        # Update subtitle to reflect the selected backend's characteristics
        ScannerPage._update_backend_subtitle(row, selected)

    @staticmethod
    def _on_refresh_daemon_status(status_row: Adw.ActionRow):
        """
        Refresh the daemon connection status.

        Args:
            status_row: The ActionRow displaying daemon status
        """
        from ...core.utils import check_clamd_connection

        is_connected, message = check_clamd_connection()

        # Update status row
        if is_connected:
            status_row.set_subtitle("✓ Daemon available")
            # Update icon
            for child in list(status_row):
                if isinstance(child, Gtk.Image):
                    child.set_from_icon_name("emblem-ok-symbolic")
                    child.remove_css_class("warning")
                    child.add_css_class("success")
                    break
        else:
            status_row.set_subtitle(f"⚠ Not available: {message}")
            for child in list(status_row):
                if isinstance(child, Gtk.Image):
                    child.set_from_icon_name("dialog-warning-symbolic")
                    child.remove_css_class("success")
                    child.add_css_class("warning")
                    break

    @staticmethod
    def _on_learn_more_clicked(parent_window):
        """
        Open the scan backends documentation file.

        Opens docs/SCAN_BACKENDS.md in the user's default application
        (typically a web browser or text editor) using xdg-open.

        Args:
            parent_window: Parent window to present error dialogs on
        """
        import subprocess

        # Get the path to the documentation file
        # From src/ui/preferences/scanner_page.py -> src/ui/preferences/ -> src/ui/ -> src/ -> project_root/
        docs_path = (
            Path(__file__).parent.parent.parent.parent / "docs" / "SCAN_BACKENDS.md"
        )

        # Check if file exists
        if not docs_path.exists():
            # Show error if documentation doesn't exist
            dialog = Adw.AlertDialog()
            dialog.set_heading("Documentation Not Found")
            dialog.set_body(
                "The scan backends documentation file could not be found. "
                "It may have been moved or deleted."
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(parent_window)
            return

        try:
            # Use xdg-open on Linux to open file in default application
            subprocess.Popen(
                ["xdg-open", str(docs_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            # Show error dialog if opening fails
            dialog = Adw.AlertDialog()
            dialog.set_heading("Error Opening Documentation")
            dialog.set_body(f"Could not open documentation file: {str(e)}")
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(parent_window)

    @staticmethod
    def _create_scanning_group(page: Adw.PreferencesPage, widgets_dict: dict, helper):
        """
        Create the File Type Scanning preferences group for clamd.conf.

        Contains settings for:
        - ScanPE: Scan PE files (Windows/DOS executables)
        - ScanELF: Scan ELF files (Unix/Linux executables)
        - ScanOLE2: Scan OLE2 files (Microsoft Office documents)
        - ScanPDF: Scan PDF files
        - ScanHTML: Scan HTML files
        - ScanArchive: Scan archive files (ZIP, RAR, etc.)

        Args:
            page: The preferences page to add the group to
            widgets_dict: Dictionary to store widget references
            helper: Helper instance with _create_permission_indicator method
        """
        group = Adw.PreferencesGroup()
        group.set_title("File Type Scanning")
        group.set_description("Enable or disable scanning for specific file types")
        group.set_header_suffix(helper._create_permission_indicator())

        # ScanPE switch
        scan_pe_row = Adw.SwitchRow()
        scan_pe_row.set_title("Scan PE Files")
        scan_pe_row.set_subtitle("Scan Windows/DOS executable files")
        widgets_dict["ScanPE"] = scan_pe_row
        group.add(scan_pe_row)

        # ScanELF switch
        scan_elf_row = Adw.SwitchRow()
        scan_elf_row.set_title("Scan ELF Files")
        scan_elf_row.set_subtitle("Scan Unix/Linux executable files")
        widgets_dict["ScanELF"] = scan_elf_row
        group.add(scan_elf_row)

        # ScanOLE2 switch
        scan_ole2_row = Adw.SwitchRow()
        scan_ole2_row.set_title("Scan OLE2 Files")
        scan_ole2_row.set_subtitle("Scan Microsoft Office documents")
        widgets_dict["ScanOLE2"] = scan_ole2_row
        group.add(scan_ole2_row)

        # ScanPDF switch
        scan_pdf_row = Adw.SwitchRow()
        scan_pdf_row.set_title("Scan PDF Files")
        scan_pdf_row.set_subtitle("Scan PDF documents")
        widgets_dict["ScanPDF"] = scan_pdf_row
        group.add(scan_pdf_row)

        # ScanHTML switch
        scan_html_row = Adw.SwitchRow()
        scan_html_row.set_title("Scan HTML Files")
        scan_html_row.set_subtitle("Scan HTML documents")
        widgets_dict["ScanHTML"] = scan_html_row
        group.add(scan_html_row)

        # ScanArchive switch
        scan_archive_row = Adw.SwitchRow()
        scan_archive_row.set_title("Scan Archive Files")
        scan_archive_row.set_subtitle("Scan compressed archives (ZIP, RAR, etc.)")
        widgets_dict["ScanArchive"] = scan_archive_row
        group.add(scan_archive_row)

        page.add(group)

    @staticmethod
    def _create_performance_group(
        page: Adw.PreferencesPage, widgets_dict: dict, helper
    ):
        """
        Create the Performance preferences group for clamd.conf.

        Contains settings for:
        - MaxFileSize: Maximum file size to scan (in MB)
        - MaxScanSize: Maximum total scan size (in MB)
        - MaxRecursion: Maximum recursion depth for archives
        - MaxFiles: Maximum number of files to scan in an archive

        Args:
            page: The preferences page to add the group to
            widgets_dict: Dictionary to store widget references
            helper: Helper instance with _create_permission_indicator method
        """
        group = Adw.PreferencesGroup()
        group.set_title("Performance and Limits")
        group.set_description("Configure scanning limits and performance settings")
        group.set_header_suffix(helper._create_permission_indicator())

        # MaxFileSize spin row (in MB, 0-4000)
        max_file_size_row = Adw.SpinRow.new_with_range(0, 4000, 1)
        max_file_size_row.set_title("Max File Size (MB)")
        max_file_size_row.set_subtitle("Maximum file size to scan (0 = unlimited)")
        max_file_size_row.set_numeric(True)
        max_file_size_row.set_snap_to_ticks(True)
        widgets_dict["MaxFileSize"] = max_file_size_row
        group.add(max_file_size_row)

        # MaxScanSize spin row (in MB, 0-4000)
        max_scan_size_row = Adw.SpinRow.new_with_range(0, 4000, 1)
        max_scan_size_row.set_title("Max Scan Size (MB)")
        max_scan_size_row.set_subtitle("Maximum total scan size (0 = unlimited)")
        max_scan_size_row.set_numeric(True)
        max_scan_size_row.set_snap_to_ticks(True)
        widgets_dict["MaxScanSize"] = max_scan_size_row
        group.add(max_scan_size_row)

        # MaxRecursion spin row (0-255)
        max_recursion_row = Adw.SpinRow.new_with_range(0, 255, 1)
        max_recursion_row.set_title("Max Archive Recursion")
        max_recursion_row.set_subtitle("Maximum recursion depth for archives")
        max_recursion_row.set_numeric(True)
        max_recursion_row.set_snap_to_ticks(True)
        widgets_dict["MaxRecursion"] = max_recursion_row
        group.add(max_recursion_row)

        # MaxFiles spin row (0-1000000)
        max_files_row = Adw.SpinRow.new_with_range(0, 1000000, 1)
        max_files_row.set_title("Max Files in Archive")
        max_files_row.set_subtitle(
            "Maximum number of files to scan in archive (0 = unlimited)"
        )
        max_files_row.set_numeric(True)
        max_files_row.set_snap_to_ticks(True)
        widgets_dict["MaxFiles"] = max_files_row
        group.add(max_files_row)

        page.add(group)

    @staticmethod
    def _create_logging_group(page: Adw.PreferencesPage, widgets_dict: dict, helper):
        """
        Create the Logging preferences group for clamd.conf.

        Contains settings for:
        - LogFile: Log file path
        - LogVerbose: Enable verbose logging
        - LogSyslog: Enable syslog logging

        Args:
            page: The preferences page to add the group to
            widgets_dict: Dictionary to store widget references
            helper: Helper instance with _create_permission_indicator method
        """
        group = Adw.PreferencesGroup()
        group.set_title("Logging")
        group.set_description("Configure logging options for the scanner")
        group.set_header_suffix(helper._create_permission_indicator())

        # LogFile entry row
        log_file_row = Adw.EntryRow()
        log_file_row.set_title("Log File Path")
        log_file_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        log_file_row.set_show_apply_button(False)
        # Add document icon as prefix
        log_icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
        log_icon.set_margin_start(6)
        log_file_row.add_prefix(log_icon)
        widgets_dict["LogFile"] = log_file_row
        group.add(log_file_row)

        # LogVerbose switch
        log_verbose_row = Adw.SwitchRow()
        log_verbose_row.set_title("Verbose Logging")
        log_verbose_row.set_subtitle("Enable detailed scanner logging")
        widgets_dict["LogVerbose"] = log_verbose_row
        group.add(log_verbose_row)

        # LogSyslog switch
        log_syslog_row = Adw.SwitchRow()
        log_syslog_row.set_title("Syslog Logging")
        log_syslog_row.set_subtitle("Send log messages to system log")
        widgets_dict["LogSyslog"] = log_syslog_row
        group.add(log_syslog_row)

        page.add(group)

    @staticmethod
    def populate_fields(config, widgets_dict: dict):
        """
        Populate clamd configuration fields from loaded config.

        Updates UI widgets with values from the parsed clamd.conf file.
        Only populates scanner-related fields (file type scanning, performance, logging).

        Args:
            config: Parsed config object with has_key() and get_value() methods
            widgets_dict: Dictionary containing widget references
        """
        if not config:
            return

        # Populate file type scanning switches
        for key in (
            "ScanPE",
            "ScanELF",
            "ScanOLE2",
            "ScanPDF",
            "ScanHTML",
            "ScanArchive",
        ):
            populate_bool_field(config, widgets_dict, key)

        # Populate performance settings
        for key in ("MaxFileSize", "MaxScanSize", "MaxRecursion", "MaxFiles"):
            populate_int_field(config, widgets_dict, key)

        # Populate logging settings
        populate_text_field(config, widgets_dict, "LogFile")
        populate_bool_field(config, widgets_dict, "LogVerbose")
        populate_bool_field(config, widgets_dict, "LogSyslog")

    @staticmethod
    def collect_data(widgets_dict: dict, clamd_available: bool) -> dict:
        """
        Collect clamd configuration data from form widgets.

        Collects scanner-related settings (file type scanning, performance, logging).
        Does not include scan backend settings as those are auto-saved.

        Args:
            widgets_dict: Dictionary containing widget references
            clamd_available: Whether clamd.conf is available

        Returns:
            Dictionary of configuration key-value pairs to save
        """
        if not clamd_available:
            return {}

        updates = {}

        # Collect file type scanning settings
        updates["ScanPE"] = "yes" if widgets_dict["ScanPE"].get_active() else "no"
        updates["ScanELF"] = "yes" if widgets_dict["ScanELF"].get_active() else "no"
        updates["ScanOLE2"] = "yes" if widgets_dict["ScanOLE2"].get_active() else "no"
        updates["ScanPDF"] = "yes" if widgets_dict["ScanPDF"].get_active() else "no"
        updates["ScanHTML"] = "yes" if widgets_dict["ScanHTML"].get_active() else "no"
        updates["ScanArchive"] = (
            "yes" if widgets_dict["ScanArchive"].get_active() else "no"
        )

        # Collect performance settings
        updates["MaxFileSize"] = str(int(widgets_dict["MaxFileSize"].get_value()))
        updates["MaxScanSize"] = str(int(widgets_dict["MaxScanSize"].get_value()))
        updates["MaxRecursion"] = str(int(widgets_dict["MaxRecursion"].get_value()))
        updates["MaxFiles"] = str(int(widgets_dict["MaxFiles"].get_value()))

        # Collect logging settings
        log_file = widgets_dict["LogFile"].get_text()
        if log_file:
            updates["LogFile"] = log_file

        updates["LogVerbose"] = (
            "yes" if widgets_dict["LogVerbose"].get_active() else "no"
        )
        updates["LogSyslog"] = "yes" if widgets_dict["LogSyslog"].get_active() else "no"

        return updates


class _ScannerPageHelper(PreferencesPageMixin):
    """
    Helper class to provide access to mixin methods for static context.

    This is a workaround to allow static methods in ScannerPage to use
    the mixin utilities (like _create_permission_indicator). In the future,
    when ScannerPage is integrated into the full PreferencesWindow, this
    helper won't be needed.
    """

    def __init__(self):
        """Initialize helper with a parent window reference."""
        self._parent_window = None
