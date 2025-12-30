# ClamUI Preferences Window
"""
Preferences window for ClamUI with ClamAV configuration settings.
"""

import threading
import time

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

    def _setup_ui(self):
        """Set up the preferences window UI layout."""
        # Create Database Updates page (freshclam.conf)
        self._create_database_page()

        # Create Scanner Settings page (clamd.conf)
        self._create_scanner_page()

        # Create Scheduled Scans page
        self._create_scheduled_scans_page()

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

        If clamd.conf doesn't exist, shows an informational status page
        instead of the settings. This handles systems without clamd installed.
        """
        import os

        page = Adw.PreferencesPage()
        page.set_title("Scanner Settings")
        page.set_icon_name("system-search-symbolic")

        # Check if clamd.conf exists
        clamd_conf_path = "/etc/clamav/clamd.conf"
        if not os.path.exists(clamd_conf_path):
            self._clamd_available = False
            # Show status group for missing config
            self._create_scanner_unavailable_group(page)
        else:
            self._clamd_available = True

            # Create file location group
            self._create_file_location_group(
                page,
                "Configuration File",
                self._clamd_conf_path,
                "clamd.conf location"
            )

            # Create logging group
            self._create_scanner_logging_group(page)

            # Create limits group
            self._create_scanner_limits_group(page)

            # Create scan options group
            self._create_scanner_options_group(page)

        self.add(page)

    def _create_scanner_unavailable_group(self, page: Adw.PreferencesPage):
        """
        Create a status group showing that clamd.conf is not available.

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Scanner Configuration")
        group.set_description("ClamAV daemon configuration")

        # Create an ActionRow to show the unavailable message
        status_row = Adw.ActionRow()
        status_row.set_title("ClamAV Daemon Not Configured")
        status_row.set_subtitle(
            "The clamd.conf file was not found. Install clamav-daemon "
            "to enable scanner configuration."
        )
        status_row.set_icon_name("dialog-information-symbolic")
        status_row.add_css_class("property")

        group.add(status_row)
        page.add(group)

    def _create_scanner_logging_group(self, page: Adw.PreferencesPage):
        """
        Create the Logging preferences group for clamd.conf.

        Contains settings for:
        - LogFile: Scanner log file path
        - LogVerbose: Enable verbose logging

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Logging")
        group.set_description("Configure scanner logging settings")
        group.set_header_suffix(self._create_permission_indicator())

        # LogFile entry row
        log_file_row = Adw.EntryRow()
        log_file_row.set_title("Log File")
        log_file_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        log_file_row.set_show_apply_button(False)
        # Add document icon as prefix
        log_icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
        log_icon.set_margin_start(6)
        log_file_row.add_prefix(log_icon)
        self._clamd_widgets['LogFile'] = log_file_row
        group.add(log_file_row)

        # LogVerbose switch row
        log_verbose_row = Adw.SwitchRow()
        log_verbose_row.set_title("Verbose Logging")
        log_verbose_row.set_subtitle("Enable detailed logging for scanner operations")
        self._clamd_widgets['LogVerbose'] = log_verbose_row
        group.add(log_verbose_row)

        page.add(group)

    def _create_scanner_limits_group(self, page: Adw.PreferencesPage):
        """
        Create the Scan Limits preferences group for clamd.conf.

        Contains settings for:
        - MaxScanSize: Maximum data size to scan (e.g., 100M)
        - MaxFileSize: Maximum file size to scan (e.g., 25M)
        - MaxRecursion: Maximum archive recursion depth
        - MaxFiles: Maximum files to scan in archive
        - MaxThreads: Maximum scanning threads

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Scan Limits")
        group.set_description("Configure maximum sizes and resource limits")
        group.set_header_suffix(self._create_permission_indicator())

        # MaxScanSize entry row (size with suffix like 100M)
        max_scan_size_row = Adw.EntryRow()
        max_scan_size_row.set_title("Maximum Scan Size")
        max_scan_size_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        max_scan_size_row.set_show_apply_button(False)
        # Add size icon as prefix
        scan_size_icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")
        scan_size_icon.set_margin_start(6)
        max_scan_size_row.add_prefix(scan_size_icon)
        self._clamd_widgets['MaxScanSize'] = max_scan_size_row
        group.add(max_scan_size_row)

        # MaxFileSize entry row (size with suffix like 25M)
        max_file_size_row = Adw.EntryRow()
        max_file_size_row.set_title("Maximum File Size")
        max_file_size_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        max_file_size_row.set_show_apply_button(False)
        # Add file icon as prefix
        file_size_icon = Gtk.Image.new_from_icon_name("document-properties-symbolic")
        file_size_icon.set_margin_start(6)
        max_file_size_row.add_prefix(file_size_icon)
        self._clamd_widgets['MaxFileSize'] = max_file_size_row
        group.add(max_file_size_row)

        # MaxRecursion spin row (depth 0-100)
        max_recursion_row = Adw.SpinRow.new_with_range(0, 100, 1)
        max_recursion_row.set_title("Maximum Recursion Depth")
        max_recursion_row.set_subtitle("Maximum depth for archive extraction")
        max_recursion_row.set_numeric(True)
        max_recursion_row.set_snap_to_ticks(True)
        self._clamd_widgets['MaxRecursion'] = max_recursion_row
        group.add(max_recursion_row)

        # MaxFiles spin row (0-100000)
        max_files_row = Adw.SpinRow.new_with_range(0, 100000, 100)
        max_files_row.set_title("Maximum Files in Archive")
        max_files_row.set_subtitle("Maximum number of files to scan in archive")
        max_files_row.set_numeric(True)
        max_files_row.set_snap_to_ticks(True)
        self._clamd_widgets['MaxFiles'] = max_files_row
        group.add(max_files_row)

        # MaxThreads spin row (1-256)
        max_threads_row = Adw.SpinRow.new_with_range(1, 256, 1)
        max_threads_row.set_title("Maximum Threads")
        max_threads_row.set_subtitle("Maximum number of scanning threads")
        max_threads_row.set_numeric(True)
        max_threads_row.set_snap_to_ticks(True)
        self._clamd_widgets['MaxThreads'] = max_threads_row
        group.add(max_threads_row)

        page.add(group)

    def _create_scanner_options_group(self, page: Adw.PreferencesPage):
        """
        Create the Scan Options preferences group for clamd.conf.

        Contains settings for:
        - ScanArchive: Scan inside archives
        - ScanPDF: Scan PDF files
        - DetectPUA: Detect potentially unwanted applications

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Scan Options")
        group.set_description("Configure what the scanner checks")
        group.set_header_suffix(self._create_permission_indicator())

        # ScanArchive switch row
        scan_archive_row = Adw.SwitchRow()
        scan_archive_row.set_title("Scan Archives")
        scan_archive_row.set_subtitle("Scan inside archive files (ZIP, RAR, etc.)")
        self._clamd_widgets['ScanArchive'] = scan_archive_row
        group.add(scan_archive_row)

        # ScanPDF switch row
        scan_pdf_row = Adw.SwitchRow()
        scan_pdf_row.set_title("Scan PDF Files")
        scan_pdf_row.set_subtitle("Scan inside PDF documents for embedded threats")
        self._clamd_widgets['ScanPDF'] = scan_pdf_row
        group.add(scan_pdf_row)

        # DetectPUA switch row
        detect_pua_row = Adw.SwitchRow()
        detect_pua_row.set_title("Detect PUA")
        detect_pua_row.set_subtitle("Detect potentially unwanted applications")
        self._clamd_widgets['DetectPUA'] = detect_pua_row
        group.add(detect_pua_row)

        page.add(group)

    def _create_scheduled_scans_page(self):
        """
        Create the Scheduled Scans page for automatic scanning configuration.

        Contains settings for:
        - Enable/disable scheduled scans
        - Schedule frequency (daily, weekly, monthly)
        - Time of day for scans
        - Day of week/month selection
        - Target directories to scan
        - Battery skip option
        - Auto-quarantine option
        """
        import os

        page = Adw.PreferencesPage()
        page.set_title("Scheduled Scans")
        page.set_icon_name("alarm-symbolic")

        # Create scheduler status group
        self._create_scheduler_status_group(page)

        # Create schedule configuration group
        self._create_schedule_config_group(page)

        # Create scan targets group
        self._create_scan_targets_group(page)

        # Create scan options group
        self._create_scheduled_options_group(page)

        self.add(page)

    def _create_scheduler_status_group(self, page: Adw.PreferencesPage):
        """
        Create the scheduler status and enable/disable group.

        Shows the current scheduler backend (systemd/cron) and provides
        a switch to enable or disable scheduled scanning.

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Scheduled Scanning")
        group.set_description("Automatically scan your system at scheduled times")

        # Backend status row
        backend_row = Adw.ActionRow()
        backend_row.set_title("Scheduler Backend")

        if self._scheduler.is_available:
            backend_name = self._scheduler.get_backend_name()
            backend_row.set_subtitle(f"Using {backend_name}")
            backend_row.set_icon_name("emblem-ok-symbolic")
        else:
            backend_row.set_subtitle("No scheduler available (install systemd or cron)")
            backend_row.set_icon_name("dialog-warning-symbolic")
            backend_row.add_css_class("warning")

        backend_row.add_css_class("property")
        group.add(backend_row)

        # Enable scheduled scans switch
        enable_row = Adw.SwitchRow()
        enable_row.set_title("Enable Scheduled Scans")
        enable_row.set_subtitle("Run antivirus scans automatically at scheduled times")
        enable_row.set_sensitive(self._scheduler.is_available)
        self._scheduled_widgets['enabled'] = enable_row
        group.add(enable_row)

        page.add(group)

    def _create_schedule_config_group(self, page: Adw.PreferencesPage):
        """
        Create the schedule configuration group.

        Contains settings for:
        - Frequency (daily, weekly, monthly)
        - Time of day (HH:MM)
        - Day of week (for weekly scans)
        - Day of month (for monthly scans)

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Schedule Configuration")
        group.set_description("Configure when scheduled scans should run")

        # Frequency combo row
        frequency_row = Adw.ComboRow()
        frequency_row.set_title("Frequency")
        frequency_row.set_subtitle("How often to run scheduled scans")

        # Create string list for frequency options
        frequency_model = Gtk.StringList()
        frequency_model.append("Daily")
        frequency_model.append("Weekly")
        frequency_model.append("Monthly")
        frequency_row.set_model(frequency_model)
        frequency_row.connect("notify::selected", self._on_frequency_changed)
        self._scheduled_widgets['frequency'] = frequency_row
        group.add(frequency_row)

        # Time entry row
        time_row = Adw.EntryRow()
        time_row.set_title("Time")
        time_row.set_text("02:00")
        time_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        time_row.set_show_apply_button(False)

        # Add clock icon as prefix
        time_icon = Gtk.Image.new_from_icon_name("preferences-system-time-symbolic")
        time_icon.set_margin_start(6)
        time_row.add_prefix(time_icon)

        # Add hint label as suffix
        time_hint = Gtk.Label()
        time_hint.set_text("HH:MM (24-hour)")
        time_hint.add_css_class("dim-label")
        time_hint.set_margin_end(6)
        time_row.add_suffix(time_hint)

        self._scheduled_widgets['time'] = time_row
        group.add(time_row)

        # Day of week combo row (for weekly scans)
        day_of_week_row = Adw.ComboRow()
        day_of_week_row.set_title("Day of Week")
        day_of_week_row.set_subtitle("Which day to run weekly scans")

        # Create string list for days
        days_model = Gtk.StringList()
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in days:
            days_model.append(day)
        day_of_week_row.set_model(days_model)
        day_of_week_row.set_visible(False)  # Hidden by default (show only for weekly)
        self._scheduled_widgets['day_of_week'] = day_of_week_row
        group.add(day_of_week_row)

        # Day of month spin row (for monthly scans)
        day_of_month_row = Adw.SpinRow.new_with_range(1, 28, 1)
        day_of_month_row.set_title("Day of Month")
        day_of_month_row.set_subtitle("Which day to run monthly scans (1-28)")
        day_of_month_row.set_numeric(True)
        day_of_month_row.set_snap_to_ticks(True)
        day_of_month_row.set_visible(False)  # Hidden by default (show only for monthly)
        self._scheduled_widgets['day_of_month'] = day_of_month_row
        group.add(day_of_month_row)

        page.add(group)

    def _on_frequency_changed(self, combo_row, param_spec):
        """
        Handle frequency selection change.

        Shows/hides the day of week or day of month widgets based on
        the selected frequency.

        Args:
            combo_row: The Adw.ComboRow that changed
            param_spec: The parameter specification (unused)
        """
        selected = combo_row.get_selected()

        day_of_week_row = self._scheduled_widgets.get('day_of_week')
        day_of_month_row = self._scheduled_widgets.get('day_of_month')

        if day_of_week_row:
            # Show only for weekly (index 1)
            day_of_week_row.set_visible(selected == 1)

        if day_of_month_row:
            # Show only for monthly (index 2)
            day_of_month_row.set_visible(selected == 2)

    def _create_scan_targets_group(self, page: Adw.PreferencesPage):
        """
        Create the scan targets configuration group.

        Allows users to add/remove directories to scan during scheduled scans.

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Scan Targets")
        group.set_description("Directories to scan during scheduled scans")

        # Targets list box
        self._targets_listbox = Gtk.ListBox()
        self._targets_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._targets_listbox.add_css_class("boxed-list")

        # Placeholder row for empty list
        self._empty_targets_row = Adw.ActionRow()
        self._empty_targets_row.set_title("No targets configured")
        self._empty_targets_row.set_subtitle("Add directories to scan using the button below")
        self._empty_targets_row.set_icon_name("folder-symbolic")
        self._empty_targets_row.add_css_class("property")
        self._targets_listbox.append(self._empty_targets_row)

        group.add(self._targets_listbox)

        # Add target button row
        add_row = Adw.ActionRow()
        add_row.set_title("Add Target Directory")
        add_row.set_subtitle("Select a directory to include in scheduled scans")
        add_row.set_icon_name("list-add-symbolic")
        add_row.set_activatable(True)
        add_row.connect("activated", self._on_add_target_clicked)

        # Add chevron icon as suffix
        chevron = Gtk.Image.new_from_icon_name("go-next-symbolic")
        chevron.add_css_class("dim-label")
        add_row.add_suffix(chevron)

        group.add(add_row)

        # Store widget references
        self._scheduled_widgets['targets_listbox'] = self._targets_listbox

        page.add(group)

    def _on_add_target_clicked(self, row):
        """
        Handle add target button click.

        Opens a file chooser dialog to select a directory to add to
        the scan targets list.

        Args:
            row: The ActionRow that was clicked
        """
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Directory to Scan")
        dialog.set_modal(True)

        # We need to select folders
        dialog.select_folder(self, None, self._on_target_folder_selected)

    def _on_target_folder_selected(self, dialog, result):
        """
        Handle folder selection result.

        Adds the selected folder to the targets list.

        Args:
            dialog: The file dialog
            result: The async result
        """
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                if path:
                    self._add_target_to_list(path)
        except GLib.Error:
            # User cancelled the dialog
            pass

    def _add_target_to_list(self, path: str):
        """
        Add a target directory to the list.

        Creates a new row for the target with a remove button.

        Args:
            path: The directory path to add
        """
        import os

        # Check if already exists
        for row in self._get_target_rows():
            if hasattr(row, 'target_path') and row.target_path == path:
                return  # Already in list

        # Hide empty placeholder if visible
        self._empty_targets_row.set_visible(False)

        # Create new target row
        target_row = Adw.ActionRow()
        target_row.set_title(os.path.basename(path) or path)
        target_row.set_subtitle(path)
        target_row.set_subtitle_selectable(True)
        target_row.target_path = path  # Store path for later retrieval

        # Add folder icon as prefix
        folder_icon = Gtk.Image.new_from_icon_name("folder-symbolic")
        folder_icon.set_margin_start(6)
        target_row.add_prefix(folder_icon)

        # Add warning if directory doesn't exist
        if not os.path.isdir(path):
            warning_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
            warning_icon.set_tooltip_text("Directory does not exist")
            warning_icon.add_css_class("warning")
            target_row.add_prefix(warning_icon)

        # Add remove button as suffix
        remove_button = Gtk.Button()
        remove_button.set_icon_name("user-trash-symbolic")
        remove_button.set_valign(Gtk.Align.CENTER)
        remove_button.add_css_class("flat")
        remove_button.add_css_class("circular")
        remove_button.set_tooltip_text("Remove from scan targets")
        remove_button.connect("clicked", lambda btn: self._remove_target_row(target_row))
        target_row.add_suffix(remove_button)

        # Insert before the empty row
        self._targets_listbox.insert(target_row, 0)

    def _remove_target_row(self, row):
        """
        Remove a target row from the list.

        Args:
            row: The row to remove
        """
        self._targets_listbox.remove(row)

        # Show empty placeholder if no targets left
        if not self._get_target_rows():
            self._empty_targets_row.set_visible(True)

    def _get_target_rows(self):
        """
        Get all target rows (excluding the empty placeholder).

        Returns:
            List of target rows
        """
        rows = []
        child = self._targets_listbox.get_first_child()
        while child:
            if hasattr(child, 'target_path'):
                rows.append(child)
            child = child.get_next_sibling()
        return rows

    def _get_targets_list(self) -> list:
        """
        Get the list of target paths from the UI.

        Returns:
            List of directory path strings
        """
        return [row.target_path for row in self._get_target_rows()]

    def _create_scheduled_options_group(self, page: Adw.PreferencesPage):
        """
        Create the scheduled scan options group.

        Contains settings for:
        - Skip scan when on battery power
        - Automatically quarantine detected threats

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Scan Options")
        group.set_description("Configure scheduled scan behavior")

        # Skip on battery switch
        battery_row = Adw.SwitchRow()
        battery_row.set_title("Skip When on Battery")
        battery_row.set_subtitle("Don't run scheduled scans when running on battery power")
        battery_row.set_active(True)  # Default to True
        self._scheduled_widgets['skip_on_battery'] = battery_row
        group.add(battery_row)

        # Auto-quarantine switch
        quarantine_row = Adw.SwitchRow()
        quarantine_row.set_title("Auto-Quarantine Threats")
        quarantine_row.set_subtitle("Automatically move detected threats to quarantine")
        quarantine_row.set_active(False)  # Default to False for safety
        self._scheduled_widgets['auto_quarantine'] = quarantine_row
        group.add(quarantine_row)

        page.add(group)

    def _create_save_page(self):
        """
        Create the Save & Apply page for saving configuration changes.

        Contains:
        - Status banner for save feedback
        - Save button to trigger configuration write
        - Information about restart requirements
        """
        page = Adw.PreferencesPage()
        page.set_title("Save & Apply")
        page.set_icon_name("document-save-symbolic")

        # Status banner group
        status_group = Adw.PreferencesGroup()

        # Status banner for save feedback
        self._status_banner = Adw.Banner()
        self._status_banner.set_revealed(False)

        # Wrap banner in a clamp for proper sizing
        banner_clamp = Adw.Clamp()
        banner_clamp.set_maximum_size(600)
        banner_clamp.set_child(self._status_banner)

        status_group.add(banner_clamp)
        page.add(status_group)

        # Save changes group
        save_group = Adw.PreferencesGroup()
        save_group.set_title("Apply Changes")
        save_group.set_description(
            "Save your configuration changes. This requires administrator "
            "privileges to write to system configuration files."
        )

        # Information row about restart
        info_row = Adw.ActionRow()
        info_row.set_title("Service Restart Required")
        info_row.set_subtitle(
            "After saving, restart clamav-freshclam or clamav-daemon "
            "for changes to take effect"
        )
        info_row.set_icon_name("dialog-information-symbolic")
        info_row.add_css_class("property")
        save_group.add(info_row)

        # Save button row
        save_row = Adw.ActionRow()
        save_row.set_title("Save Configuration")
        save_row.set_subtitle("Write changes to ClamAV configuration files")
        save_row.set_icon_name("document-save-symbolic")

        # Save button
        self._save_button = Gtk.Button()
        self._save_button.set_label("Save")
        self._save_button.set_valign(Gtk.Align.CENTER)
        self._save_button.add_css_class("suggested-action")
        self._save_button.connect("clicked", self._on_save_clicked)

        # Spinner for save progress (hidden by default)
        self._save_spinner = Gtk.Spinner()
        self._save_spinner.set_visible(False)

        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_valign(Gtk.Align.CENTER)
        button_box.append(self._save_spinner)
        button_box.append(self._save_button)

        save_row.add_suffix(button_box)
        save_group.add(save_row)

        page.add(save_group)
        self.add(page)

    def _on_save_clicked(self, button):
        """
        Handle save button click.

        Validates the configuration and saves it with privilege elevation.
        Shows appropriate feedback for success, error, or cancellation.
        """
        if self._is_saving:
            return

        # Hide any previous banner
        self._status_banner.set_revealed(False)

        # Start save operation in background thread
        self._set_saving_state(True)

        thread = threading.Thread(target=self._save_configs_thread, daemon=True)
        thread.start()

    def _set_saving_state(self, is_saving: bool):
        """
        Update UI to reflect saving state.

        Args:
            is_saving: Whether a save operation is in progress
        """
        self._is_saving = is_saving

        if is_saving:
            self._save_button.set_label("Saving...")
            self._save_button.set_sensitive(False)
            self._save_spinner.set_visible(True)
            self._save_spinner.start()
        else:
            self._save_button.set_label("Save")
            self._save_button.set_sensitive(True)
            self._save_spinner.stop()
            self._save_spinner.set_visible(False)

    def _save_configs_thread(self):
        """
        Save configuration files in background thread.

        Updates configs from form values, validates them, creates backups,
        and writes them using pkexec elevation. UI updates are dispatched
        to the main thread via GLib.idle_add.
        """
        errors = []
        backup_warnings = []

        # Save freshclam.conf if loaded
        if self._freshclam_config is not None:
            # Update config from form values
            GLib.idle_add(self._update_freshclam_config_from_widgets)
            # Small delay to ensure UI thread processes the update
            time.sleep(0.05)

            # Validate freshclam config
            is_valid, validation_errors = validate_config(self._freshclam_config)
            if not is_valid:
                errors.extend([f"freshclam.conf: {e}" for e in validation_errors])
            else:
                # Create backup before writing
                backup_success, backup_result = backup_config(self._freshclam_conf_path)
                if not backup_success:
                    backup_warnings.append(f"freshclam.conf backup failed: {backup_result}")

                # Write freshclam config
                success, error = write_config_with_elevation(self._freshclam_config)
                if not success:
                    if error == "Authentication cancelled":
                        GLib.idle_add(self._show_cancelled_banner)
                        GLib.idle_add(self._set_saving_state, False)
                        return
                    errors.append(f"freshclam.conf: {error}")

        # Save clamd.conf if loaded
        if self._clamd_config is not None and self._clamd_available:
            # Update config from form values
            GLib.idle_add(self._update_clamd_config_from_widgets)
            # Small delay to ensure UI thread processes the update
            time.sleep(0.05)

            # Validate clamd config
            is_valid, validation_errors = validate_config(self._clamd_config)
            if not is_valid:
                errors.extend([f"clamd.conf: {e}" for e in validation_errors])
            else:
                # Create backup before writing
                backup_success, backup_result = backup_config(self._clamd_conf_path)
                if not backup_success:
                    backup_warnings.append(f"clamd.conf backup failed: {backup_result}")

                # Write clamd config
                success, error = write_config_with_elevation(self._clamd_config)
                if not success:
                    if error == "Authentication cancelled":
                        GLib.idle_add(self._show_cancelled_banner)
                        GLib.idle_add(self._set_saving_state, False)
                        return
                    errors.append(f"clamd.conf: {error}")

        # Save scheduled scan settings (no elevation required)
        if self._settings_manager is not None:
            # Reset scheduler error before saving
            self._scheduler_error = None
            # Save scheduled settings in UI thread
            GLib.idle_add(self._save_scheduled_settings)
            # Small delay to ensure UI thread processes the update
            time.sleep(0.1)
            # Check for scheduler errors
            if self._scheduler_error is not None:
                errors.append(f"Schedule: {self._scheduler_error}")

        # Show result in UI thread
        if errors:
            GLib.idle_add(self._show_error_banner, "; ".join(errors))
        elif backup_warnings:
            # Save succeeded but backup failed - show warning
            GLib.idle_add(
                self._show_warning_banner,
                f"Saved with warnings: {'; '.join(backup_warnings)}"
            )
        else:
            GLib.idle_add(self._show_success_banner)

        GLib.idle_add(self._set_saving_state, False)

    def _update_freshclam_config_from_widgets(self):
        """
        Update freshclam config object from form widget values.

        Called from the UI thread to safely access widget values.
        """
        if self._freshclam_config is None:
            return

        # Update entry row values (string/path)
        entry_keys = ['DatabaseDirectory', 'UpdateLogFile', 'NotifyClamd',
                      'DatabaseMirror', 'HTTPProxyServer', 'HTTPProxyUsername']
        for key in entry_keys:
            if key in self._freshclam_widgets:
                value = self._freshclam_widgets[key].get_text()
                if value:
                    self._freshclam_config.set_value(
                        key, value,
                        self._get_line_number(self._freshclam_config, key)
                    )

        # Update password entry row
        if 'HTTPProxyPassword' in self._freshclam_widgets:
            value = self._freshclam_widgets['HTTPProxyPassword'].get_text()
            if value:
                self._freshclam_config.set_value(
                    'HTTPProxyPassword', value,
                    self._get_line_number(self._freshclam_config, 'HTTPProxyPassword')
                )

        # Update switch row values (boolean)
        switch_keys = ['LogVerbose', 'LogSyslog']
        for key in switch_keys:
            if key in self._freshclam_widgets:
                is_active = self._freshclam_widgets[key].get_active()
                value = "yes" if is_active else "no"
                self._freshclam_config.set_value(
                    key, value,
                    self._get_line_number(self._freshclam_config, key)
                )

        # Update spin row values (integer)
        if 'Checks' in self._freshclam_widgets:
            value = int(self._freshclam_widgets['Checks'].get_value())
            self._freshclam_config.set_value(
                'Checks', str(value),
                self._get_line_number(self._freshclam_config, 'Checks')
            )

        if 'HTTPProxyPort' in self._freshclam_widgets:
            value = int(self._freshclam_widgets['HTTPProxyPort'].get_value())
            if value > 0:
                self._freshclam_config.set_value(
                    'HTTPProxyPort', str(value),
                    self._get_line_number(self._freshclam_config, 'HTTPProxyPort')
                )

    def _update_clamd_config_from_widgets(self):
        """
        Update clamd config object from form widget values.

        Called from the UI thread to safely access widget values.
        """
        if self._clamd_config is None:
            return

        # Update entry row values (string/path/size)
        entry_keys = ['LogFile', 'MaxScanSize', 'MaxFileSize']
        for key in entry_keys:
            if key in self._clamd_widgets:
                value = self._clamd_widgets[key].get_text()
                if value:
                    self._clamd_config.set_value(
                        key, value,
                        self._get_line_number(self._clamd_config, key)
                    )

        # Update switch row values (boolean)
        switch_keys = ['LogVerbose', 'ScanArchive', 'ScanPDF', 'DetectPUA']
        for key in switch_keys:
            if key in self._clamd_widgets:
                is_active = self._clamd_widgets[key].get_active()
                value = "yes" if is_active else "no"
                self._clamd_config.set_value(
                    key, value,
                    self._get_line_number(self._clamd_config, key)
                )

        # Update spin row values (integer)
        spin_keys = ['MaxRecursion', 'MaxFiles', 'MaxThreads']
        for key in spin_keys:
            if key in self._clamd_widgets:
                value = int(self._clamd_widgets[key].get_value())
                self._clamd_config.set_value(
                    key, str(value),
                    self._get_line_number(self._clamd_config, key)
                )

    def _get_line_number(self, config: ClamAVConfig, key: str) -> int:
        """
        Get the original line number for a config key.

        Args:
            config: The ClamAVConfig object
            key: The configuration key

        Returns:
            The line number if found, 0 otherwise (new value)
        """
        if key in config.values and config.values[key]:
            return config.values[key][0].line_number
        return 0

    def _show_success_banner(self):
        """Show success banner after successful save and prompt for restart."""
        self._status_banner.set_title(
            "Configuration saved successfully. Restart ClamAV services "
            "for changes to take effect."
        )
        self._status_banner.remove_css_class("error")
        self._status_banner.remove_css_class("warning")
        self._status_banner.add_css_class("success")
        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

        # Show restart confirmation dialog
        self._show_restart_dialog()

    def _show_restart_dialog(self):
        """
        Show a confirmation dialog prompting user to restart ClamAV services.

        This dialog informs the user which services need to be restarted for
        the configuration changes to take effect. It does NOT actually execute
        the restart - it just provides the commands the user can run.
        """
        dialog = Adw.AlertDialog()
        dialog.set_heading("Restart Required")

        # Build body text based on which configs were modified
        services = []
        if self._freshclam_config is not None:
            services.append("clamav-freshclam")
        if self._clamd_config is not None and self._clamd_available:
            services.append("clamav-daemon")

        if services:
            service_list = ", ".join(services)
            body_text = (
                f"Configuration changes have been saved successfully.\n\n"
                f"To apply these changes, restart the following services:\n"
                f"• {service_list}\n\n"
                f"You can restart them by running:\n"
                f"sudo systemctl restart {' '.join(services)}"
            )
        else:
            body_text = (
                "Configuration changes have been saved successfully.\n\n"
                "Restart the relevant ClamAV services for changes to take effect."
            )

        dialog.set_body(body_text)

        # Add response buttons
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")

        # Present the dialog
        dialog.present(self)

    def _show_error_banner(self, error_message: str):
        """
        Show error banner after save failure.

        Args:
            error_message: The error message to display
        """
        self._status_banner.set_title(f"Save failed: {error_message}")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("warning")
        self._status_banner.add_css_class("error")
        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

    def _show_cancelled_banner(self):
        """Show cancelled banner when user dismisses authentication dialog."""
        self._status_banner.set_title("Save cancelled - authentication was dismissed")
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("error")
        self._status_banner.add_css_class("warning")
        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

    def _show_warning_banner(self, warning_message: str):
        """
        Show warning banner when save succeeded with warnings.

        Args:
            warning_message: The warning message to display
        """
        self._status_banner.set_title(warning_message)
        self._status_banner.remove_css_class("success")
        self._status_banner.remove_css_class("error")
        self._status_banner.add_css_class("warning")
        self._status_banner.set_button_label(None)
        self._status_banner.set_revealed(True)

    def _load_configs(self):
        """
        Load ClamAV configuration files and populate form fields.

        Loads both freshclam.conf and clamd.conf (if available) and populates
        the corresponding form widgets with the parsed values. Also loads
        scheduled scan settings from the settings manager.
        """
        # Load freshclam.conf
        config, error = parse_config(self._freshclam_conf_path)
        if config is not None:
            self._freshclam_config = config
            self._populate_freshclam_widgets(config)

        # Load clamd.conf (only if available)
        if self._clamd_available:
            config, error = parse_config(self._clamd_conf_path)
            if config is not None:
                self._clamd_config = config
                self._populate_clamd_widgets(config)

        # Load scheduled scan settings from settings manager
        if self._settings_manager is not None:
            self._populate_scheduled_widgets()

    def _populate_freshclam_widgets(self, config: ClamAVConfig):
        """
        Populate freshclam.conf form widgets with configuration values.

        Maps ClamAV configuration options to their corresponding UI widgets
        and sets the appropriate values based on widget type.

        Args:
            config: The parsed freshclam.conf configuration
        """
        # Populate entry rows (string/path values)
        entry_keys = ['DatabaseDirectory', 'UpdateLogFile', 'NotifyClamd',
                      'DatabaseMirror', 'HTTPProxyServer', 'HTTPProxyUsername']
        for key in entry_keys:
            if key in self._freshclam_widgets:
                value = config.get_value(key)
                if value is not None:
                    self._freshclam_widgets[key].set_text(value)

        # Populate password entry row
        if 'HTTPProxyPassword' in self._freshclam_widgets:
            value = config.get_value('HTTPProxyPassword')
            if value is not None:
                self._freshclam_widgets['HTTPProxyPassword'].set_text(value)

        # Populate switch rows (boolean values)
        switch_keys = ['LogVerbose', 'LogSyslog']
        for key in switch_keys:
            if key in self._freshclam_widgets:
                value = config.get_bool(key)
                if value is not None:
                    self._freshclam_widgets[key].set_active(value)

        # Populate spin rows (integer values)
        if 'Checks' in self._freshclam_widgets:
            value = config.get_int('Checks')
            if value is not None:
                self._freshclam_widgets['Checks'].set_value(float(value))

        if 'HTTPProxyPort' in self._freshclam_widgets:
            value = config.get_int('HTTPProxyPort')
            if value is not None:
                self._freshclam_widgets['HTTPProxyPort'].set_value(float(value))

    def _populate_clamd_widgets(self, config: ClamAVConfig):
        """
        Populate clamd.conf form widgets with configuration values.

        Maps ClamAV daemon configuration options to their corresponding UI
        widgets and sets the appropriate values based on widget type.

        Args:
            config: The parsed clamd.conf configuration
        """
        # Populate entry rows (string/path/size values)
        entry_keys = ['LogFile', 'MaxScanSize', 'MaxFileSize']
        for key in entry_keys:
            if key in self._clamd_widgets:
                value = config.get_value(key)
                if value is not None:
                    self._clamd_widgets[key].set_text(value)

        # Populate switch rows (boolean values)
        switch_keys = ['LogVerbose', 'ScanArchive', 'ScanPDF', 'DetectPUA']
        for key in switch_keys:
            if key in self._clamd_widgets:
                value = config.get_bool(key)
                if value is not None:
                    self._clamd_widgets[key].set_active(value)

        # Populate spin rows (integer values)
        spin_keys = ['MaxRecursion', 'MaxFiles', 'MaxThreads']
        for key in spin_keys:
            if key in self._clamd_widgets:
                value = config.get_int(key)
                if value is not None:
                    self._clamd_widgets[key].set_value(float(value))

    def _populate_scheduled_widgets(self):
        """
        Populate scheduled scan widgets from settings manager.

        Loads saved schedule configuration and populates the UI widgets.
        """
        if self._settings_manager is None:
            return

        # Populate enable switch
        if 'enabled' in self._scheduled_widgets:
            enabled = self._settings_manager.get('scheduled_scans_enabled', False)
            self._scheduled_widgets['enabled'].set_active(enabled)

        # Populate frequency combo
        if 'frequency' in self._scheduled_widgets:
            frequency = self._settings_manager.get('schedule_frequency', 'weekly')
            frequency_map = {'daily': 0, 'weekly': 1, 'monthly': 2}
            index = frequency_map.get(frequency, 1)
            self._scheduled_widgets['frequency'].set_selected(index)

            # Trigger visibility update for day of week/month
            self._on_frequency_changed(self._scheduled_widgets['frequency'], None)

        # Populate time entry
        if 'time' in self._scheduled_widgets:
            time_value = self._settings_manager.get('schedule_time', '02:00')
            self._scheduled_widgets['time'].set_text(time_value)

        # Populate day of week combo
        if 'day_of_week' in self._scheduled_widgets:
            day_of_week = self._settings_manager.get('schedule_day_of_week', 0)
            self._scheduled_widgets['day_of_week'].set_selected(day_of_week)

        # Populate day of month spin
        if 'day_of_month' in self._scheduled_widgets:
            day_of_month = self._settings_manager.get('schedule_day_of_month', 1)
            self._scheduled_widgets['day_of_month'].set_value(float(day_of_month))

        # Populate targets
        targets = self._settings_manager.get('schedule_targets', [])
        for target in targets:
            self._add_target_to_list(target)

        # Populate skip on battery switch
        if 'skip_on_battery' in self._scheduled_widgets:
            skip_on_battery = self._settings_manager.get('schedule_skip_on_battery', True)
            self._scheduled_widgets['skip_on_battery'].set_active(skip_on_battery)

        # Populate auto-quarantine switch
        if 'auto_quarantine' in self._scheduled_widgets:
            auto_quarantine = self._settings_manager.get('schedule_auto_quarantine', False)
            self._scheduled_widgets['auto_quarantine'].set_active(auto_quarantine)

    def _save_scheduled_settings(self) -> bool:
        """
        Save scheduled scan settings to settings manager.

        Reads values from UI widgets and saves them to the settings manager.
        Also enables/disables the schedule with the system scheduler.

        Returns:
            True if saved successfully, False otherwise
        """
        if self._settings_manager is None:
            return False

        # Get enabled state
        enabled = False
        if 'enabled' in self._scheduled_widgets:
            enabled = self._scheduled_widgets['enabled'].get_active()
        self._settings_manager.set('scheduled_scans_enabled', enabled)

        # Get frequency
        frequency = 'weekly'
        if 'frequency' in self._scheduled_widgets:
            selected = self._scheduled_widgets['frequency'].get_selected()
            frequency_map = {0: 'daily', 1: 'weekly', 2: 'monthly'}
            frequency = frequency_map.get(selected, 'weekly')
        self._settings_manager.set('schedule_frequency', frequency)

        # Get time
        time_value = '02:00'
        if 'time' in self._scheduled_widgets:
            time_value = self._scheduled_widgets['time'].get_text() or '02:00'
        self._settings_manager.set('schedule_time', time_value)

        # Get day of week
        day_of_week = 0
        if 'day_of_week' in self._scheduled_widgets:
            day_of_week = self._scheduled_widgets['day_of_week'].get_selected()
        self._settings_manager.set('schedule_day_of_week', day_of_week)

        # Get day of month
        day_of_month = 1
        if 'day_of_month' in self._scheduled_widgets:
            day_of_month = int(self._scheduled_widgets['day_of_month'].get_value())
        self._settings_manager.set('schedule_day_of_month', day_of_month)

        # Get targets
        targets = self._get_targets_list()
        self._settings_manager.set('schedule_targets', targets)

        # Get skip on battery
        skip_on_battery = True
        if 'skip_on_battery' in self._scheduled_widgets:
            skip_on_battery = self._scheduled_widgets['skip_on_battery'].get_active()
        self._settings_manager.set('schedule_skip_on_battery', skip_on_battery)

        # Get auto-quarantine
        auto_quarantine = False
        if 'auto_quarantine' in self._scheduled_widgets:
            auto_quarantine = self._scheduled_widgets['auto_quarantine'].get_active()
        self._settings_manager.set('schedule_auto_quarantine', auto_quarantine)

        # Enable or disable the schedule with the system scheduler
        if enabled and self._scheduler.is_available:
            success, error = self._scheduler.enable_schedule(
                frequency=frequency,
                time=time_value,
                targets=targets,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                skip_on_battery=skip_on_battery,
                auto_quarantine=auto_quarantine
            )
            if not success:
                self._scheduler_error = error or "Failed to enable schedule"
                return False
        elif not enabled and self._scheduler.is_available:
            success, error = self._scheduler.disable_schedule()
            if not success:
                self._scheduler_error = error or "Failed to disable schedule"
                return False

        return self._settings_manager.save()
