# ClamUI Preferences Window
"""
Preferences window for ClamUI with ClamAV configuration settings.
"""

import threading
import time
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from src.core.clamav_config import (
    parse_config,
    ClamAVConfig,
    validate_config,
    write_config_with_elevation,
    backup_config,
)
from src.core.scheduler import Scheduler, ScheduleFrequency
from src.core.scanner import validate_pattern
from src.ui.utils import add_row_icon


# Preset exclusion templates for common development directories
# These are directory patterns commonly excluded from scans for performance
PRESET_EXCLUSIONS = [
    {
        "pattern": "node_modules",
        "type": "directory",
        "enabled": True,
        "description": "Node.js dependencies"
    },
    {
        "pattern": ".git",
        "type": "directory",
        "enabled": True,
        "description": "Git repository data"
    },
    {
        "pattern": ".venv",
        "type": "directory",
        "enabled": True,
        "description": "Python virtual environment"
    },
    {
        "pattern": "build",
        "type": "directory",
        "enabled": True,
        "description": "Build output directory"
    },
    {
        "pattern": "dist",
        "type": "directory",
        "enabled": True,
        "description": "Distribution output directory"
    },
    {
        "pattern": "__pycache__",
        "type": "directory",
        "enabled": True,
        "description": "Python bytecode cache"
    },
]


class PreferencesWindow(Adw.PreferencesWindow):
    """
    Preferences window for ClamUI.

    Provides a settings interface for ClamAV configuration with:
    - Database update settings (freshclam.conf)
    - Scanner settings (clamd.conf)
    - Save functionality with permission elevation

    The window is displayed as a modal dialog transient to the main window.
    """

    def __init__(self, settings_manager=None, **kwargs):
        """
        Initialize the preferences window.

        Args:
            settings_manager: Optional SettingsManager instance for application settings
            **kwargs: Additional arguments passed to parent, including:
                - transient_for: Parent window to be modal to
                - application: The parent application instance
        """
        super().__init__(**kwargs)

        # Store settings manager reference (not currently used but available for future)
        self._settings_manager = settings_manager

        # Set window properties
        self.set_title("Preferences")
        self.set_default_size(600, 500)
        self.set_modal(True)
        self.set_search_enabled(False)

        # Store references to form widgets for later access
        self._freshclam_widgets = {}
        self._clamd_widgets = {}
        self._scheduled_widgets = {}

        # Track if clamd.conf exists
        self._clamd_available = False

        # Initialize scheduler for scheduled scans
        self._scheduler = Scheduler()

        # Store loaded configurations
        self._freshclam_config = None
        self._clamd_config = None

        # Default config file paths
        self._freshclam_conf_path = "/etc/clamav/freshclam.conf"
        self._clamd_conf_path = "/etc/clamav/clamd.conf"

        # Saving state
        self._is_saving = False

        # Scheduler error storage (for thread-safe error passing)
        self._scheduler_error = None

        # Set up the UI
        self._setup_ui()

        # Load configurations and populate form fields
        self._load_configs()

        # Populate scheduled scan fields from saved settings
        self._populate_scheduled_fields()

    def _setup_ui(self):
        """Set up the preferences window UI layout."""
        # Create Database Updates page (freshclam.conf)
        self._create_database_page()

        # Create Scanner Settings page (clamd.conf)
        self._create_scanner_page()

        # Create Scheduled Scans page
        self._create_scheduled_scans_page()

        # Create Exclusions page (scan exclusion patterns)
        self._create_exclusions_page()

        # Create Save & Apply page
        self._create_save_page()

    def _create_permission_indicator(self) -> Gtk.Box:
        """
        Create a permission indicator widget showing a lock icon.

        Used to indicate that modifying settings in a group requires
        administrator (root) privileges via pkexec elevation.

        Icon options:
        - system-lock-screen-symbolic: Standard lock icon (used)
        - changes-allow-symbolic: Alternative shield/lock icon

        Returns:
            A Gtk.Box containing the lock icon with tooltip
        """
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        # Create lock icon - using system-lock-screen-symbolic
        # Alternative: changes-allow-symbolic for a shield-style icon
        lock_icon = Gtk.Image.new_from_icon_name("system-lock-screen-symbolic")
        lock_icon.add_css_class("dim-label")
        lock_icon.set_tooltip_text("Requires administrator privileges to modify")

        box.append(lock_icon)
        return box

    def _create_database_page(self):
        """Create the Database Updates page for freshclam.conf settings."""
        page = Adw.PreferencesPage()
        page.set_title("Database Updates")
        page.set_icon_name("software-update-available-symbolic")

        # Create file location group
        self._create_file_location_group(
            page,
            "Configuration File",
            self._freshclam_conf_path,
            "freshclam.conf location"
        )

        # Create paths group
        self._create_paths_group(page)

        # Create update behavior group
        self._create_updates_group(page)

        # Create proxy settings group
        self._create_proxy_group(page)

        self.add(page)

    def _create_file_location_group(
        self,
        page: Adw.PreferencesPage,
        title: str,
        file_path: str,
        description: str
    ):
        """
        Create a group showing the configuration file location.

        Displays the filesystem path to the configuration file so users
        know where to find it, with a button to open the containing folder.

        Args:
            page: The preferences page to add the group to
            title: Title for the group
            file_path: The filesystem path to display
            description: Description text for the group
        """
        import os

        group = Adw.PreferencesGroup()
        group.set_title(title)
        group.set_description(description)

        # File path row
        path_row = Adw.ActionRow()
        path_row.set_title("File Location")
        path_row.set_subtitle(file_path)
        path_row.set_subtitle_selectable(True)

        # Add folder icon as prefix
        folder_icon = Gtk.Image.new_from_icon_name("folder-open-symbolic")
        folder_icon.set_margin_start(6)
        path_row.add_prefix(folder_icon)

        # Add "Open folder" button as suffix
        open_folder_button = Gtk.Button()
        open_folder_button.set_label("Open Folder")
        open_folder_button.set_valign(Gtk.Align.CENTER)
        open_folder_button.add_css_class("flat")
        open_folder_button.set_tooltip_text("Open containing folder in file manager")

        # Get the parent directory for the file
        parent_dir = os.path.dirname(file_path)

        # Connect click handler to open folder
        open_folder_button.connect(
            "clicked",
            lambda btn: self._open_folder_in_file_manager(parent_dir)
        )

        path_row.add_suffix(open_folder_button)

        # Make it look like an informational row
        path_row.add_css_class("property")

        group.add(path_row)
        page.add(group)

    def _open_folder_in_file_manager(self, folder_path: str):
        """
        Open a folder in the system's default file manager.

        Args:
            folder_path: The folder path to open
        """
        import subprocess
        import os

        if not os.path.exists(folder_path):
            # Show error if folder doesn't exist
            dialog = Adw.AlertDialog()
            dialog.set_heading("Folder Not Found")
            dialog.set_body(f"The folder '{folder_path}' does not exist.")
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)
            return

        try:
            # Use xdg-open on Linux to open folder in default file manager
            subprocess.Popen(
                ['xdg-open', folder_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            # Show error dialog if opening fails
            dialog = Adw.AlertDialog()
            dialog.set_heading("Error Opening Folder")
            dialog.set_body(f"Could not open folder: {str(e)}")
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)

    def _create_paths_group(self, page: Adw.PreferencesPage):
        """
        Create the Paths preferences group.

        Contains settings for:
        - DatabaseDirectory: Where virus databases are stored
        - UpdateLogFile: Log file for update operations
        - LogVerbose: Enable verbose logging
        - NotifyClamd: Path to clamd.conf for reload notification

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Paths")
        group.set_description("Configure database and log file locations")
        group.set_header_suffix(self._create_permission_indicator())

        # DatabaseDirectory row
        database_dir_row = Adw.EntryRow()
        database_dir_row.set_title("Database Directory")
        database_dir_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        database_dir_row.set_show_apply_button(False)
        # Add folder icon as prefix
        folder_icon = Gtk.Image.new_from_icon_name("folder-symbolic")
        folder_icon.set_margin_start(6)
        database_dir_row.add_prefix(folder_icon)
        self._freshclam_widgets['DatabaseDirectory'] = database_dir_row
        group.add(database_dir_row)

        # UpdateLogFile row
        log_file_row = Adw.EntryRow()
        log_file_row.set_title("Update Log File")
        log_file_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        log_file_row.set_show_apply_button(False)
        # Add document icon as prefix
        log_icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
        log_icon.set_margin_start(6)
        log_file_row.add_prefix(log_icon)
        self._freshclam_widgets['UpdateLogFile'] = log_file_row
        group.add(log_file_row)

        # NotifyClamd row
        notify_clamd_row = Adw.EntryRow()
        notify_clamd_row.set_title("Notify ClamD Config")
        notify_clamd_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        notify_clamd_row.set_show_apply_button(False)
        # Add settings icon as prefix
        notify_icon = Gtk.Image.new_from_icon_name("emblem-system-symbolic")
        notify_icon.set_margin_start(6)
        notify_clamd_row.add_prefix(notify_icon)
        self._freshclam_widgets['NotifyClamd'] = notify_clamd_row
        group.add(notify_clamd_row)

        # LogVerbose switch row
        log_verbose_row = Adw.SwitchRow()
        log_verbose_row.set_title("Verbose Logging")
        log_verbose_row.set_subtitle("Enable detailed logging for database updates")
        self._freshclam_widgets['LogVerbose'] = log_verbose_row
        group.add(log_verbose_row)

        # LogSyslog switch row
        log_syslog_row = Adw.SwitchRow()
        log_syslog_row.set_title("Syslog Logging")
        log_syslog_row.set_subtitle("Send log messages to system log")
        self._freshclam_widgets['LogSyslog'] = log_syslog_row
        group.add(log_syslog_row)

        page.add(group)

    def _create_updates_group(self, page: Adw.PreferencesPage):
        """
        Create the Update Behavior preferences group.

        Contains settings for:
        - Checks: Number of database update checks per day (0-50)
        - DatabaseMirror: Mirror URLs for database downloads

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Update Behavior")
        group.set_description("Configure how often and where to check for updates")
        group.set_header_suffix(self._create_permission_indicator())

        # Checks spin row (0-50 updates per day)
        checks_row = Adw.SpinRow.new_with_range(0, 50, 1)
        checks_row.set_title("Checks Per Day")
        checks_row.set_subtitle("Number of update checks per day (0 to disable)")
        checks_row.set_numeric(True)
        checks_row.set_snap_to_ticks(True)
        self._freshclam_widgets['Checks'] = checks_row
        group.add(checks_row)

        # DatabaseMirror entry row (primary mirror)
        mirror_row = Adw.EntryRow()
        mirror_row.set_title("Database Mirror")
        mirror_row.set_input_purpose(Gtk.InputPurpose.URL)
        mirror_row.set_show_apply_button(False)
        # Add network icon as prefix
        mirror_icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
        mirror_icon.set_margin_start(6)
        mirror_row.add_prefix(mirror_icon)
        self._freshclam_widgets['DatabaseMirror'] = mirror_row
        group.add(mirror_row)

        page.add(group)

    def _create_proxy_group(self, page: Adw.PreferencesPage):
        """
        Create the Proxy Settings preferences group.

        Contains settings for:
        - HTTPProxyServer: Proxy server hostname
        - HTTPProxyPort: Proxy port number
        - HTTPProxyUsername: Proxy authentication username
        - HTTPProxyPassword: Proxy authentication password

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Proxy Settings")
        group.set_description("Configure HTTP proxy for database downloads (optional)")
        group.set_header_suffix(self._create_permission_indicator())

        # HTTPProxyServer entry row
        proxy_server_row = Adw.EntryRow()
        proxy_server_row.set_title("Proxy Server")
        proxy_server_row.set_input_purpose(Gtk.InputPurpose.URL)
        proxy_server_row.set_show_apply_button(False)
        # Add network icon as prefix
        server_icon = Gtk.Image.new_from_icon_name("network-workgroup-symbolic")
        server_icon.set_margin_start(6)
        proxy_server_row.add_prefix(server_icon)
        self._freshclam_widgets['HTTPProxyServer'] = proxy_server_row
        group.add(proxy_server_row)

        # HTTPProxyPort spin row (1-65535)
        proxy_port_row = Adw.SpinRow.new_with_range(0, 65535, 1)
        proxy_port_row.set_title("Proxy Port")
        proxy_port_row.set_subtitle("Proxy server port number (0 to disable)")
        proxy_port_row.set_numeric(True)
        proxy_port_row.set_snap_to_ticks(True)
        self._freshclam_widgets['HTTPProxyPort'] = proxy_port_row
        group.add(proxy_port_row)

        # HTTPProxyUsername entry row
        proxy_user_row = Adw.EntryRow()
        proxy_user_row.set_title("Proxy Username")
        proxy_user_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        proxy_user_row.set_show_apply_button(False)
        # Add user icon as prefix
        user_icon = Gtk.Image.new_from_icon_name("avatar-default-symbolic")
        user_icon.set_margin_start(6)
        proxy_user_row.add_prefix(user_icon)
        self._freshclam_widgets['HTTPProxyUsername'] = proxy_user_row
        group.add(proxy_user_row)

        # HTTPProxyPassword entry row (with password input)
        proxy_pass_row = Adw.PasswordEntryRow()
        proxy_pass_row.set_title("Proxy Password")
        self._freshclam_widgets['HTTPProxyPassword'] = proxy_pass_row
        group.add(proxy_pass_row)

        page.add(group)

    def _create_scanner_page(self):
        """
        Create the Scanner Settings page for clamd.conf settings.
        """
        page = Adw.PreferencesPage()
        page.set_title("Scanner Settings")
        page.set_icon_name("document-properties-symbolic")

        # Check if clamd.conf exists and create appropriate content
        try:
            with open(self._clamd_conf_path, 'r') as f:
                self._clamd_available = True
        except FileNotFoundError:
            self._clamd_available = False

        # Create scan backend settings group (ClamUI settings)
        self._create_scan_backend_group(page)

        # Create file location group
        self._create_file_location_group(
            page,
            "Configuration File",
            self._clamd_conf_path,
            "clamd.conf location"
        )

        if self._clamd_available:
            # Create scanning group
            self._create_scanning_group(page)

            # Create performance group
            self._create_performance_group(page)

            # Create logging group
            self._create_logging_group(page)
        else:
            # Show message that clamd.conf is not available
            group = Adw.PreferencesGroup()
            group.set_title("Configuration Status")
            row = Adw.ActionRow()
            row.set_title("ClamD Configuration")
            row.set_subtitle("clamd.conf not found - Scanner settings unavailable")
            group.add(row)
            page.add(group)

        self.add(page)

    def _create_scanning_group(self, page: Adw.PreferencesPage):
        """
        Create the Scanning preferences group for clamd.conf.

        Contains settings for:
        - ScanPE: Scan PE files
        - ScanELF: Scan ELF files
        - ScanOLE2: Scan OLE2 files
        - ScanPDF: Scan PDF files
        - ScanHTML: Scan HTML files
        - ScanArchive: Scan archive files

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("File Type Scanning")
        group.set_description("Enable or disable scanning for specific file types")
        group.set_header_suffix(self._create_permission_indicator())

        # ScanPE switch
        scan_pe_row = Adw.SwitchRow()
        scan_pe_row.set_title("Scan PE Files")
        scan_pe_row.set_subtitle("Scan Windows/DOS executable files")
        self._clamd_widgets['ScanPE'] = scan_pe_row
        group.add(scan_pe_row)

        # ScanELF switch
        scan_elf_row = Adw.SwitchRow()
        scan_elf_row.set_title("Scan ELF Files")
        scan_elf_row.set_subtitle("Scan Unix/Linux executable files")
        self._clamd_widgets['ScanELF'] = scan_elf_row
        group.add(scan_elf_row)

        # ScanOLE2 switch
        scan_ole2_row = Adw.SwitchRow()
        scan_ole2_row.set_title("Scan OLE2 Files")
        scan_ole2_row.set_subtitle("Scan Microsoft Office documents")
        self._clamd_widgets['ScanOLE2'] = scan_ole2_row
        group.add(scan_ole2_row)

        # ScanPDF switch
        scan_pdf_row = Adw.SwitchRow()
        scan_pdf_row.set_title("Scan PDF Files")
        scan_pdf_row.set_subtitle("Scan PDF documents")
        self._clamd_widgets['ScanPDF'] = scan_pdf_row
        group.add(scan_pdf_row)

        # ScanHTML switch
        scan_html_row = Adw.SwitchRow()
        scan_html_row.set_title("Scan HTML Files")
        scan_html_row.set_subtitle("Scan HTML documents")
        self._clamd_widgets['ScanHTML'] = scan_html_row
        group.add(scan_html_row)

        # ScanArchive switch
        scan_archive_row = Adw.SwitchRow()
        scan_archive_row.set_title("Scan Archive Files")
        scan_archive_row.set_subtitle("Scan compressed archives (ZIP, RAR, etc.)")
        self._clamd_widgets['ScanArchive'] = scan_archive_row
        group.add(scan_archive_row)

        page.add(group)

    def _create_performance_group(self, page: Adw.PreferencesPage):
        """
        Create the Performance preferences group for clamd.conf.

        Contains settings for:
        - MaxFileSize: Maximum file size to scan
        - MaxScanSize: Maximum total scan size
        - MaxRecursion: Maximum recursion depth for archives
        - MaxFiles: Maximum number of files to scan in an archive

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Performance and Limits")
        group.set_description("Configure scanning limits and performance settings")
        group.set_header_suffix(self._create_permission_indicator())

        # MaxFileSize spin row (in MB, 0-4000)
        max_file_size_row = Adw.SpinRow.new_with_range(0, 4000, 1)
        max_file_size_row.set_title("Max File Size (MB)")
        max_file_size_row.set_subtitle("Maximum file size to scan (0 = unlimited)")
        max_file_size_row.set_numeric(True)
        max_file_size_row.set_snap_to_ticks(True)
        self._clamd_widgets['MaxFileSize'] = max_file_size_row
        group.add(max_file_size_row)

        # MaxScanSize spin row (in MB, 0-4000)
        max_scan_size_row = Adw.SpinRow.new_with_range(0, 4000, 1)
        max_scan_size_row.set_title("Max Scan Size (MB)")
        max_scan_size_row.set_subtitle("Maximum total scan size (0 = unlimited)")
        max_scan_size_row.set_numeric(True)
        max_scan_size_row.set_snap_to_ticks(True)
        self._clamd_widgets['MaxScanSize'] = max_scan_size_row
        group.add(max_scan_size_row)

        # MaxRecursion spin row (0-255)
        max_recursion_row = Adw.SpinRow.new_with_range(0, 255, 1)
        max_recursion_row.set_title("Max Archive Recursion")
        max_recursion_row.set_subtitle("Maximum recursion depth for archives")
        max_recursion_row.set_numeric(True)
        max_recursion_row.set_snap_to_ticks(True)
        self._clamd_widgets['MaxRecursion'] = max_recursion_row
        group.add(max_recursion_row)

        # MaxFiles spin row (0-1000000)
        max_files_row = Adw.SpinRow.new_with_range(0, 1000000, 1)
        max_files_row.set_title("Max Files in Archive")
        max_files_row.set_subtitle("Maximum number of files to scan in archive (0 = unlimited)")
        max_files_row.set_numeric(True)
        max_files_row.set_snap_to_ticks(True)
        self._clamd_widgets['MaxFiles'] = max_files_row
        group.add(max_files_row)

        page.add(group)

    def _create_logging_group(self, page: Adw.PreferencesPage):
        """
        Create the Logging preferences group for clamd.conf.

        Contains settings for:
        - LogFile: Log file path
        - LogVerbose: Enable verbose logging
        - LogSyslog: Enable syslog logging

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Logging")
        group.set_description("Configure logging options for the scanner")
        group.set_header_suffix(self._create_permission_indicator())

        # LogFile entry row
        log_file_row = Adw.EntryRow()
        log_file_row.set_title("Log File Path")
        log_file_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        log_file_row.set_show_apply_button(False)
        # Add document icon as prefix
        log_icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
        log_icon.set_margin_start(6)
        log_file_row.add_prefix(log_icon)
        self._clamd_widgets['LogFile'] = log_file_row
        group.add(log_file_row)

        # LogVerbose switch
        log_verbose_row = Adw.SwitchRow()
        log_verbose_row.set_title("Verbose Logging")
        log_verbose_row.set_subtitle("Enable detailed scanner logging")
        self._clamd_widgets['LogVerbose'] = log_verbose_row
        group.add(log_verbose_row)

        # LogSyslog switch
        log_syslog_row = Adw.SwitchRow()
        log_syslog_row.set_title("Syslog Logging")
        log_syslog_row.set_subtitle("Send log messages to system log")
        self._clamd_widgets['LogSyslog'] = log_syslog_row
        group.add(log_syslog_row)

        page.add(group)

    def _create_scan_backend_group(self, page: Adw.PreferencesPage):
        """
        Create the Scan Backend preferences group.

        Allows users to select between different scan backends:
        - Auto: Prefer daemon if available, fallback to clamscan
        - Daemon: Use clamd daemon only (faster, requires daemon running)
        - Clamscan: Use standalone clamscan only

        Args:
            page: The preferences page to add the group to
        """
        from src.core.utils import check_clamd_connection

        group = Adw.PreferencesGroup()
        group.set_title("Scan Backend")
        group.set_description(
            "Choose how ClamUI communicates with ClamAV to perform virus scans. "
            "The backend affects scan speed, memory usage, and setup requirements. "
            "Auto mode (recommended) intelligently selects the best available backend."
        )

        # Scan backend dropdown
        backend_row = Adw.ComboRow()
        backend_model = Gtk.StringList()
        backend_model.append("Auto (prefer daemon)")
        backend_model.append("ClamAV Daemon (clamd)")
        backend_model.append("Standalone Scanner (clamscan)")
        backend_row.set_model(backend_model)
        backend_row.set_title("Scan Backend")

        # Set current selection from settings
        current_backend = self._settings_manager.get("scan_backend", "auto")
        backend_map = {"auto": 0, "daemon": 1, "clamscan": 2}
        backend_row.set_selected(backend_map.get(current_backend, 0))

        # Set initial subtitle based on current selection
        self._update_backend_subtitle(backend_row, backend_map.get(current_backend, 0))

        # Connect to selection changes
        backend_row.connect("notify::selected", self._on_backend_changed)

        self._backend_row = backend_row
        group.add(backend_row)

        # Daemon status indicator
        status_row = Adw.ActionRow()
        status_row.set_title("Daemon Status")

        # Check daemon connection
        is_connected, message = check_clamd_connection()
        if is_connected:
            status_row.set_subtitle(
                "✓ Daemon is running and accessible — Auto mode will use daemon for faster scans"
            )
            status_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
            status_icon.add_css_class("success")
        else:
            status_row.set_subtitle(
                f"⚠ Daemon not available ({message}) — Auto mode will use clamscan backend"
            )
            status_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
            status_icon.add_css_class("warning")

        status_row.add_suffix(status_icon)
        self._daemon_status_row = status_row
        group.add(status_row)

        # Refresh button
        refresh_button = Gtk.Button()
        refresh_button.set_label("Refresh Status")
        refresh_button.set_valign(Gtk.Align.CENTER)
        refresh_button.add_css_class("flat")
        refresh_button.connect("clicked", self._on_refresh_daemon_status)
        status_row.add_suffix(refresh_button)

        # Learn more row - links to documentation
        learn_more_row = Adw.ActionRow()
        learn_more_row.set_title("Learn More")
        learn_more_row.set_subtitle("View detailed documentation about scan backends")
        add_row_icon(learn_more_row, "help-about-symbolic")
        learn_more_row.set_activatable(True)
        learn_more_row.connect("activated", self._on_learn_more_clicked)

        # Add chevron to indicate it's clickable
        chevron = Gtk.Image.new_from_icon_name("go-next-symbolic")
        chevron.add_css_class("dim-label")
        learn_more_row.add_suffix(chevron)

        group.add(learn_more_row)

        page.add(group)

    def _update_backend_subtitle(self, row: Adw.ComboRow, selected: int):
        """
        Update the backend row subtitle based on the selected backend.

        Args:
            row: The ComboRow widget to update
            selected: Index of the selected backend (0=auto, 1=daemon, 2=clamscan)
        """
        subtitles = {
            0: "Recommended — Automatically uses daemon if available, falls back to clamscan for reliability",
            1: "Fastest — Instant startup with in-memory database, requires clamd service running",
            2: "Most compatible — Works anywhere, loads database each scan (3-10 sec startup)"
        }
        row.set_subtitle(subtitles.get(selected, subtitles[0]))

    def _on_backend_changed(self, row: Adw.ComboRow, _pspec):
        """Handle scan backend selection change."""
        backend_reverse_map = {0: "auto", 1: "daemon", 2: "clamscan"}
        selected = row.get_selected()
        backend = backend_reverse_map.get(selected, "auto")
        self._settings_manager.set("scan_backend", backend)

        # Update subtitle to reflect the selected backend's characteristics
        self._update_backend_subtitle(row, selected)

    def _on_refresh_daemon_status(self, button: Gtk.Button):
        """Refresh the daemon connection status."""
        from src.core.utils import check_clamd_connection

        is_connected, message = check_clamd_connection()

        # Update status row
        if is_connected:
            self._daemon_status_row.set_subtitle(
                "✓ Daemon is running and accessible — Auto mode will use daemon for faster scans"
            )
            # Update icon
            for child in list(self._daemon_status_row):
                if isinstance(child, Gtk.Image):
                    child.set_from_icon_name("emblem-ok-symbolic")
                    child.remove_css_class("warning")
                    child.add_css_class("success")
                    break
        else:
            self._daemon_status_row.set_subtitle(
                f"⚠ Daemon not available ({message}) — Auto mode will use clamscan backend"
            )
            for child in list(self._daemon_status_row):
                if isinstance(child, Gtk.Image):
                    child.set_from_icon_name("dialog-warning-symbolic")
                    child.remove_css_class("success")
                    child.add_css_class("warning")
                    break

    def _on_learn_more_clicked(self, row: Adw.ActionRow):
        """
        Open the scan backends documentation file.

        Opens docs/SCAN_BACKENDS.md in the user's default application
        (typically a web browser or text editor) using xdg-open.

        Args:
            row: The ActionRow that was activated (unused but required by signal)
        """
        import subprocess

        # Get the path to the documentation file
        # From src/ui/preferences_window.py -> src/ui/ -> src/ -> project_root/
        docs_path = Path(__file__).parent.parent.parent / "docs" / "SCAN_BACKENDS.md"

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
            dialog.present(self)
            return

        try:
            # Use xdg-open on Linux to open file in default application
            subprocess.Popen(
                ['xdg-open', str(docs_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            # Show error dialog if opening fails
            dialog = Adw.AlertDialog()
            dialog.set_heading("Error Opening Documentation")
            dialog.set_body(f"Could not open documentation file: {str(e)}")
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)

    def _create_scheduled_scans_page(self):
        """
        Create the Scheduled Scans configuration page.

        Allows users to:
        - Enable/disable scheduled scans
        - Set scan frequency (hourly, daily, weekly, monthly)
        - Configure scan paths
        """
        page = Adw.PreferencesPage()
        page.set_title("Scheduled Scans")
        page.set_icon_name("media-playback-start-symbolic")

        # Scheduled scans enabled group
        group = Adw.PreferencesGroup()
        group.set_title("Scheduled Scans Configuration")
        group.set_description("Configure automatic virus scanning")

        # Enable scheduled scans switch
        enable_scheduled_row = Adw.SwitchRow()
        enable_scheduled_row.set_title("Enable Scheduled Scans")
        enable_scheduled_row.set_subtitle("Run automatic scans at specified intervals")
        self._scheduled_widgets['enabled'] = enable_scheduled_row
        group.add(enable_scheduled_row)

        # Schedule frequency dropdown
        frequency_row = Adw.ComboRow()
        frequency_model = Gtk.StringList()
        frequency_model.append("Hourly")
        frequency_model.append("Daily")
        frequency_model.append("Weekly")
        frequency_model.append("Monthly")
        frequency_row.set_model(frequency_model)
        frequency_row.set_selected(1)  # Default to Daily
        frequency_row.set_title("Scan Frequency")
        self._scheduled_widgets['frequency'] = frequency_row
        group.add(frequency_row)

        # Time picker (schedule_time)
        time_row = Adw.EntryRow()
        time_row.set_title("Scan Time (24-hour format, e.g. 02:00)")
        time_row.set_text("02:00")
        self._scheduled_widgets['time'] = time_row
        group.add(time_row)

        # Day of week dropdown (for weekly scans)
        day_of_week_row = Adw.ComboRow()
        day_of_week_model = Gtk.StringList()
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            day_of_week_model.append(day)
        day_of_week_row.set_model(day_of_week_model)
        day_of_week_row.set_selected(0)  # Default to Monday
        day_of_week_row.set_title("Day of Week")
        day_of_week_row.set_subtitle("For weekly scans")
        self._scheduled_widgets['day_of_week'] = day_of_week_row
        group.add(day_of_week_row)

        # Day of month spinner (for monthly scans)
        day_of_month_row = Adw.SpinRow()
        day_of_month_row.set_title("Day of Month")
        day_of_month_row.set_subtitle("For monthly scans (1-28)")
        adjustment = Gtk.Adjustment(value=1, lower=1, upper=28, step_increment=1, page_increment=5, page_size=0)
        day_of_month_row.set_adjustment(adjustment)
        self._scheduled_widgets['day_of_month'] = day_of_month_row
        group.add(day_of_month_row)

        # Scan targets entry (schedule_targets)
        targets_row = Adw.EntryRow()
        targets_row.set_title("Scan Targets (comma-separated paths)")
        targets_row.set_text(str(Path.home()))
        self._scheduled_widgets['targets'] = targets_row
        group.add(targets_row)

        # Skip on battery switch
        skip_battery_row = Adw.SwitchRow()
        skip_battery_row.set_title("Skip on Battery")
        skip_battery_row.set_subtitle("Don't run scheduled scans when on battery power")
        skip_battery_row.set_active(True)
        self._scheduled_widgets['skip_on_battery'] = skip_battery_row
        group.add(skip_battery_row)

        # Auto-quarantine switch
        auto_quarantine_row = Adw.SwitchRow()
        auto_quarantine_row.set_title("Auto-Quarantine")
        auto_quarantine_row.set_subtitle("Automatically quarantine detected threats")
        auto_quarantine_row.set_active(False)
        self._scheduled_widgets['auto_quarantine'] = auto_quarantine_row
        group.add(auto_quarantine_row)

        page.add(group)
        self.add(page)

    def _create_exclusions_page(self):
        """
        Create the Exclusions page for scan exclusion patterns.

        Allows users to:
        - View preset exclusion patterns
        - Add custom exclusion patterns
        - Enable/disable individual exclusions
        - Remove custom exclusions
        """
        page = Adw.PreferencesPage()
        page.set_title("Exclusions")
        page.set_icon_name("emblem-photos-symbolic")

        # Preset exclusions group
        preset_group = Adw.PreferencesGroup()
        preset_group.set_title("Preset Exclusions")
        preset_group.set_description("Common directories and patterns to exclude from scanning")

        for preset in PRESET_EXCLUSIONS:
            # Create a row for each preset
            row = Adw.SwitchRow()
            row.set_title(preset["description"])
            row.set_subtitle(preset["pattern"])
            row.set_active(preset["enabled"])
            preset_group.add(row)

        page.add(preset_group)

        # Custom exclusions group
        custom_group = Adw.PreferencesGroup()
        custom_group.set_title("Custom Exclusions")
        custom_group.set_description("Add your own exclusion patterns")

        # Custom exclusion entry row
        custom_entry_row = Adw.EntryRow()
        custom_entry_row.set_title("Add Pattern (e.g., /path/to/exclude or *.tmp)")
        custom_entry_row.set_show_apply_button(False)

        # Add button for custom exclusions
        add_button = Gtk.Button()
        add_button.set_label("Add")
        add_button.set_valign(Gtk.Align.CENTER)
        add_button.set_tooltip_text("Add custom exclusion pattern")
        custom_entry_row.add_suffix(add_button)

        custom_group.add(custom_entry_row)
        page.add(custom_group)

        self.add(page)

    def _create_save_page(self):
        """
        Create the Save & Apply page.

        This page provides options to save configuration changes
        and view the current configuration status.
        """
        page = Adw.PreferencesPage()
        page.set_title("Save & Apply")
        page.set_icon_name("document-save-symbolic")

        # Configuration status group
        status_group = Adw.PreferencesGroup()
        status_group.set_title("Configuration Status")

        # Status indicator row
        status_row = Adw.ActionRow()
        status_row.set_title("Current Status")
        status_row.set_subtitle("Ready")

        # Status indicator widget
        status_indicator = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        status_indicator.add_css_class("success")
        status_row.add_suffix(status_indicator)

        status_group.add(status_row)
        page.add(status_group)

        # Save & apply button group
        button_group = Adw.PreferencesGroup()
        button_group.set_title("Apply Changes")
        button_group.set_description("Save configuration changes to ClamAV")

        # Save button
        save_button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        save_button_row.set_margin_top(12)
        save_button_row.set_margin_bottom(12)
        save_button_row.set_margin_start(12)
        save_button_row.set_margin_end(12)

        save_button = Gtk.Button()
        save_button.set_label("Save & Apply")
        save_button.add_css_class("suggested-action")
        save_button.set_hexpand(True)
        save_button.connect("clicked", self._on_save_clicked)
        save_button_row.append(save_button)

        button_group.add(save_button_row)
        page.add(button_group)

        self.add(page)

    def _load_configs(self):
        """
        Load ClamAV configuration files and populate form fields.

        Loads both freshclam.conf and clamd.conf (if available),
        parses them, and updates the UI with current values.
        """
        try:
            # Load freshclam.conf
            self._freshclam_config, error = parse_config(self._freshclam_conf_path)
            self._populate_freshclam_fields()
        except Exception as e:
            print(f"Error loading freshclam.conf: {e}")

        # Load clamd.conf if available
        if self._clamd_available:
            try:
                self._clamd_config, error = parse_config(self._clamd_conf_path)
                self._populate_clamd_fields()
            except Exception as e:
                print(f"Error loading clamd.conf: {e}")

    def _populate_freshclam_fields(self):
        """
        Populate freshclam configuration fields from loaded config.

        Updates UI widgets with values from the parsed freshclam.conf file.
        """
        if not self._freshclam_config:
            return

        # Populate DatabaseDirectory
        if self._freshclam_config.has_key('DatabaseDirectory'):
            self._freshclam_widgets['DatabaseDirectory'].set_text(
                self._freshclam_config.get_value('DatabaseDirectory')
            )

        # Populate UpdateLogFile
        if self._freshclam_config.has_key('UpdateLogFile'):
            self._freshclam_widgets['UpdateLogFile'].set_text(
                self._freshclam_config.get_value('UpdateLogFile')
            )

        # Populate NotifyClamd
        if self._freshclam_config.has_key('NotifyClamd'):
            self._freshclam_widgets['NotifyClamd'].set_text(
                self._freshclam_config.get_value('NotifyClamd')
            )

        # Populate LogVerbose
        if self._freshclam_config.has_key('LogVerbose'):
            self._freshclam_widgets['LogVerbose'].set_active(
                self._freshclam_config.get_value('LogVerbose').lower() == 'yes'
            )

        # Populate LogSyslog
        if self._freshclam_config.has_key('LogSyslog'):
            self._freshclam_widgets['LogSyslog'].set_active(
                self._freshclam_config.get_value('LogSyslog').lower() == 'yes'
            )

        # Populate Checks
        if self._freshclam_config.has_key('Checks'):
            try:
                checks_value = int(self._freshclam_config.get_value('Checks'))
                self._freshclam_widgets['Checks'].set_value(checks_value)
            except (ValueError, TypeError):
                pass

        # Populate DatabaseMirror
        if self._freshclam_config.has_key('DatabaseMirror'):
            self._freshclam_widgets['DatabaseMirror'].set_text(
                self._freshclam_config.get_value('DatabaseMirror')
            )

        # Populate proxy settings
        if self._freshclam_config.has_key('HTTPProxyServer'):
            self._freshclam_widgets['HTTPProxyServer'].set_text(
                self._freshclam_config.get_value('HTTPProxyServer')
            )

        if self._freshclam_config.has_key('HTTPProxyPort'):
            try:
                port_value = int(self._freshclam_config.get_value('HTTPProxyPort'))
                self._freshclam_widgets['HTTPProxyPort'].set_value(port_value)
            except (ValueError, TypeError):
                pass

        if self._freshclam_config.has_key('HTTPProxyUsername'):
            self._freshclam_widgets['HTTPProxyUsername'].set_text(
                self._freshclam_config.get_value('HTTPProxyUsername')
            )

        if self._freshclam_config.has_key('HTTPProxyPassword'):
            self._freshclam_widgets['HTTPProxyPassword'].set_text(
                self._freshclam_config.get_value('HTTPProxyPassword')
            )

    def _populate_clamd_fields(self):
        """
        Populate clamd configuration fields from loaded config.

        Updates UI widgets with values from the parsed clamd.conf file.
        """
        if not self._clamd_config:
            return

        # Populate ScanPE
        if self._clamd_config.has_key('ScanPE'):
            self._clamd_widgets['ScanPE'].set_active(
                self._clamd_config.get_value('ScanPE').lower() == 'yes'
            )

        # Populate ScanELF
        if self._clamd_config.has_key('ScanELF'):
            self._clamd_widgets['ScanELF'].set_active(
                self._clamd_config.get_value('ScanELF').lower() == 'yes'
            )

        # Populate ScanOLE2
        if self._clamd_config.has_key('ScanOLE2'):
            self._clamd_widgets['ScanOLE2'].set_active(
                self._clamd_config.get_value('ScanOLE2').lower() == 'yes'
            )

        # Populate ScanPDF
        if self._clamd_config.has_key('ScanPDF'):
            self._clamd_widgets['ScanPDF'].set_active(
                self._clamd_config.get_value('ScanPDF').lower() == 'yes'
            )

        # Populate ScanHTML
        if self._clamd_config.has_key('ScanHTML'):
            self._clamd_widgets['ScanHTML'].set_active(
                self._clamd_config.get_value('ScanHTML').lower() == 'yes'
            )

        # Populate ScanArchive
        if self._clamd_config.has_key('ScanArchive'):
            self._clamd_widgets['ScanArchive'].set_active(
                self._clamd_config.get_value('ScanArchive').lower() == 'yes'
            )

        # Populate MaxFileSize
        if self._clamd_config.has_key('MaxFileSize'):
            try:
                size_value = int(self._clamd_config.get_value('MaxFileSize'))
                self._clamd_widgets['MaxFileSize'].set_value(size_value)
            except (ValueError, TypeError):
                pass

        # Populate MaxScanSize
        if self._clamd_config.has_key('MaxScanSize'):
            try:
                scan_size_value = int(self._clamd_config.get_value('MaxScanSize'))
                self._clamd_widgets['MaxScanSize'].set_value(scan_size_value)
            except (ValueError, TypeError):
                pass

        # Populate MaxRecursion
        if self._clamd_config.has_key('MaxRecursion'):
            try:
                recursion_value = int(self._clamd_config.get_value('MaxRecursion'))
                self._clamd_widgets['MaxRecursion'].set_value(recursion_value)
            except (ValueError, TypeError):
                pass

        # Populate MaxFiles
        if self._clamd_config.has_key('MaxFiles'):
            try:
                files_value = int(self._clamd_config.get_value('MaxFiles'))
                self._clamd_widgets['MaxFiles'].set_value(files_value)
            except (ValueError, TypeError):
                pass

        # Populate LogFile
        if self._clamd_config.has_key('LogFile'):
            self._clamd_widgets['LogFile'].set_text(self._clamd_config.get_value('LogFile'))

        # Populate LogVerbose
        if self._clamd_config.has_key('LogVerbose'):
            self._clamd_widgets['LogVerbose'].set_active(
                self._clamd_config.get_value('LogVerbose').lower() == 'yes'
            )

        # Populate LogSyslog
        if self._clamd_config.has_key('LogSyslog'):
            self._clamd_widgets['LogSyslog'].set_active(
                self._clamd_config.get_value('LogSyslog').lower() == 'yes'
            )

    def _on_save_clicked(self, button: Gtk.Button):
        """
        Handle save button click event.

        Validates configuration, backs up current configs, and saves
        changes using elevated privileges (pkexec) if needed.

        Args:
            button: The clicked button widget
        """
        # Prevent multiple simultaneous saves
        if self._is_saving:
            return

        self._is_saving = True
        button.set_sensitive(False)

        # Collect form data
        freshclam_updates = self._collect_freshclam_data()
        clamd_updates = self._collect_clamd_data()
        scheduled_updates = self._collect_scheduled_data()

        # Validate configurations
        if freshclam_updates:
            is_valid, errors = validate_config(self._freshclam_config)
            if not is_valid:
                self._show_error_dialog("Validation Error", errors)
                self._is_saving = False
                button.set_sensitive(True)
                return

        if clamd_updates and self._clamd_available:
            is_valid, errors = validate_config(self._clamd_config)
            if not is_valid:
                self._show_error_dialog("Validation Error", errors)
                self._is_saving = False
                button.set_sensitive(True)
                return

        # Run save in background thread
        save_thread = threading.Thread(
            target=self._save_configs_thread,
            args=(freshclam_updates, clamd_updates, scheduled_updates, button)
        )
        save_thread.daemon = True
        save_thread.start()

    def _collect_freshclam_data(self) -> dict:
        """
        Collect freshclam configuration data from form widgets.

        Returns:
            Dictionary of configuration key-value pairs to save
        """
        updates = {}

        # Collect DatabaseDirectory
        db_dir = self._freshclam_widgets['DatabaseDirectory'].get_text()
        if db_dir:
            updates['DatabaseDirectory'] = db_dir

        # Collect UpdateLogFile
        log_file = self._freshclam_widgets['UpdateLogFile'].get_text()
        if log_file:
            updates['UpdateLogFile'] = log_file

        # Collect NotifyClamd
        notify_clamd = self._freshclam_widgets['NotifyClamd'].get_text()
        if notify_clamd:
            updates['NotifyClamd'] = notify_clamd

        # Collect LogVerbose
        updates['LogVerbose'] = 'yes' if self._freshclam_widgets['LogVerbose'].get_active() else 'no'

        # Collect LogSyslog
        updates['LogSyslog'] = 'yes' if self._freshclam_widgets['LogSyslog'].get_active() else 'no'

        # Collect Checks
        checks_value = int(self._freshclam_widgets['Checks'].get_value())
        updates['Checks'] = str(checks_value)

        # Collect DatabaseMirror
        mirror = self._freshclam_widgets['DatabaseMirror'].get_text()
        if mirror:
            updates['DatabaseMirror'] = mirror

        # Collect proxy settings
        proxy_server = self._freshclam_widgets['HTTPProxyServer'].get_text()
        if proxy_server:
            updates['HTTPProxyServer'] = proxy_server

        proxy_port = int(self._freshclam_widgets['HTTPProxyPort'].get_value())
        if proxy_port > 0:
            updates['HTTPProxyPort'] = str(proxy_port)

        proxy_user = self._freshclam_widgets['HTTPProxyUsername'].get_text()
        if proxy_user:
            updates['HTTPProxyUsername'] = proxy_user

        proxy_pass = self._freshclam_widgets['HTTPProxyPassword'].get_text()
        if proxy_pass:
            updates['HTTPProxyPassword'] = proxy_pass

        return updates

    def _collect_clamd_data(self) -> dict:
        """
        Collect clamd configuration data from form widgets.

        Returns:
            Dictionary of configuration key-value pairs to save
        """
        if not self._clamd_available:
            return {}

        updates = {}

        # Collect scan settings
        updates['ScanPE'] = 'yes' if self._clamd_widgets['ScanPE'].get_active() else 'no'
        updates['ScanELF'] = 'yes' if self._clamd_widgets['ScanELF'].get_active() else 'no'
        updates['ScanOLE2'] = 'yes' if self._clamd_widgets['ScanOLE2'].get_active() else 'no'
        updates['ScanPDF'] = 'yes' if self._clamd_widgets['ScanPDF'].get_active() else 'no'
        updates['ScanHTML'] = 'yes' if self._clamd_widgets['ScanHTML'].get_active() else 'no'
        updates['ScanArchive'] = 'yes' if self._clamd_widgets['ScanArchive'].get_active() else 'no'

        # Collect performance settings
        updates['MaxFileSize'] = str(int(self._clamd_widgets['MaxFileSize'].get_value()))
        updates['MaxScanSize'] = str(int(self._clamd_widgets['MaxScanSize'].get_value()))
        updates['MaxRecursion'] = str(int(self._clamd_widgets['MaxRecursion'].get_value()))
        updates['MaxFiles'] = str(int(self._clamd_widgets['MaxFiles'].get_value()))

        # Collect logging settings
        log_file = self._clamd_widgets['LogFile'].get_text()
        if log_file:
            updates['LogFile'] = log_file

        updates['LogVerbose'] = 'yes' if self._clamd_widgets['LogVerbose'].get_active() else 'no'
        updates['LogSyslog'] = 'yes' if self._clamd_widgets['LogSyslog'].get_active() else 'no'

        return updates

    def _collect_scheduled_data(self) -> dict:
        """
        Collect scheduled scan configuration from form widgets.

        Returns:
            Dictionary of scheduled scan settings to save
        """
        frequency_map = ["hourly", "daily", "weekly", "monthly"]
        selected_frequency = self._scheduled_widgets['frequency'].get_selected()

        # Parse targets from comma-separated string
        targets_text = self._scheduled_widgets['targets'].get_text()
        targets = [t.strip() for t in targets_text.split(",") if t.strip()]

        return {
            "scheduled_scans_enabled": self._scheduled_widgets['enabled'].get_active(),
            "schedule_frequency": frequency_map[selected_frequency] if selected_frequency < len(frequency_map) else "daily",
            "schedule_time": self._scheduled_widgets['time'].get_text().strip() or "02:00",
            "schedule_targets": targets,
            "schedule_day_of_week": self._scheduled_widgets['day_of_week'].get_selected(),
            "schedule_day_of_month": int(self._scheduled_widgets['day_of_month'].get_value()),
            "schedule_skip_on_battery": self._scheduled_widgets['skip_on_battery'].get_active(),
            "schedule_auto_quarantine": self._scheduled_widgets['auto_quarantine'].get_active(),
        }

    def _populate_scheduled_fields(self):
        """
        Populate scheduled scan widgets from saved settings.

        Loads settings from the settings manager and updates the UI widgets.
        """
        # Enable/disable switch
        self._scheduled_widgets['enabled'].set_active(
            self._settings_manager.get("scheduled_scans_enabled", False)
        )

        # Frequency dropdown
        freq = self._settings_manager.get("schedule_frequency", "daily")
        freq_map = {"hourly": 0, "daily": 1, "weekly": 2, "monthly": 3}
        self._scheduled_widgets['frequency'].set_selected(freq_map.get(freq, 1))

        # Time entry
        self._scheduled_widgets['time'].set_text(
            self._settings_manager.get("schedule_time", "02:00")
        )

        # Targets entry
        targets = self._settings_manager.get("schedule_targets", [])
        if targets:
            self._scheduled_widgets['targets'].set_text(", ".join(targets))
        else:
            self._scheduled_widgets['targets'].set_text(str(Path.home()))

        # Day of week dropdown
        self._scheduled_widgets['day_of_week'].set_selected(
            self._settings_manager.get("schedule_day_of_week", 0)
        )

        # Day of month spinner
        self._scheduled_widgets['day_of_month'].set_value(
            self._settings_manager.get("schedule_day_of_month", 1)
        )

        # Skip on battery switch
        self._scheduled_widgets['skip_on_battery'].set_active(
            self._settings_manager.get("schedule_skip_on_battery", True)
        )

        # Auto-quarantine switch
        self._scheduled_widgets['auto_quarantine'].set_active(
            self._settings_manager.get("schedule_auto_quarantine", False)
        )

    def _save_configs_thread(
        self,
        freshclam_updates: dict,
        clamd_updates: dict,
        scheduled_updates: dict,
        button: Gtk.Button
    ):
        """
        Save configuration files in a background thread.

        Uses elevated privileges (pkexec) to write configuration files
        and manages error handling with thread-safe communication.

        Args:
            freshclam_updates: Dictionary of freshclam.conf updates
            clamd_updates: Dictionary of clamd.conf updates
            scheduled_updates: Dictionary of scheduled scan settings
            button: The save button to re-enable after completion
        """
        try:
            # Backup configurations
            backup_config(self._freshclam_conf_path)
            if self._clamd_available:
                backup_config(self._clamd_conf_path)

            # Save freshclam.conf
            if freshclam_updates and self._freshclam_config:
                # Apply updates to config using set_value
                for key, value in freshclam_updates.items():
                    self._freshclam_config.set_value(key, value)
                success, error = write_config_with_elevation(self._freshclam_config)
                if not success:
                    raise Exception(f"Failed to save freshclam.conf: {error}")

            # Save clamd.conf
            if clamd_updates and self._clamd_config:
                # Apply updates to config using set_value
                for key, value in clamd_updates.items():
                    self._clamd_config.set_value(key, value)
                success, error = write_config_with_elevation(self._clamd_config)
                if not success:
                    raise Exception(f"Failed to save clamd.conf: {error}")

            # Save scheduled scan settings
            if scheduled_updates:
                for key, value in scheduled_updates.items():
                    self._settings_manager.set(key, value)
                if not self._settings_manager.save():
                    raise Exception("Failed to save scheduled scan settings")

                # Enable or disable scheduler based on settings
                if scheduled_updates.get("scheduled_scans_enabled"):
                    success, error = self._scheduler.enable_schedule(
                        frequency=scheduled_updates["schedule_frequency"],
                        time=scheduled_updates["schedule_time"],
                        targets=scheduled_updates["schedule_targets"],
                        day_of_week=scheduled_updates["schedule_day_of_week"],
                        day_of_month=scheduled_updates["schedule_day_of_month"],
                        skip_on_battery=scheduled_updates["schedule_skip_on_battery"],
                        auto_quarantine=scheduled_updates["schedule_auto_quarantine"],
                    )
                    if not success:
                        raise Exception(f"Failed to enable scheduled scans: {error}")
                else:
                    # Disable scheduler if it was previously enabled
                    self._scheduler.disable_schedule()

            # Show success message
            GLib.idle_add(
                self._show_success_dialog,
                "Configuration Saved",
                "Configuration changes have been applied successfully."
            )
        except Exception as e:
            # Store error for thread-safe handling
            self._scheduler_error = str(e)
            GLib.idle_add(
                self._show_error_dialog,
                "Save Failed",
                str(e)
            )
        finally:
            self._is_saving = False
            GLib.idle_add(button.set_sensitive, True)

    def _show_error_dialog(self, title: str, message: str):
        """
        Show an error dialog to the user.

        Args:
            title: Dialog title
            message: Error message text
        """
        dialog = Adw.AlertDialog()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)

    def _show_success_dialog(self, title: str, message: str):
        """
        Show a success dialog to the user.

        Args:
            title: Dialog title
            message: Success message text
        """
        dialog = Adw.AlertDialog()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)