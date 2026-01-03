# ClamUI Preferences Window
"""
Preferences window for ClamUI with ClamAV configuration settings.
"""

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from src.core.clamav_config import (
    backup_config,
    parse_config,
    validate_config,
    write_config_with_elevation,
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
        "description": "Node.js dependencies",
    },
    {
        "pattern": ".git",
        "type": "directory",
        "enabled": True,
        "description": "Git repository data",
    },
    {
        "pattern": ".venv",
        "type": "directory",
        "enabled": True,
        "description": "Python virtual environment",
    },
    {
        "pattern": "build",
        "type": "directory",
        "enabled": True,
        "description": "Build output directory",
    },
    {
        "pattern": "dist",
        "type": "directory",
        "enabled": True,
        "description": "Distribution output directory",
    },
    {
        "pattern": "__pycache__",
        "type": "directory",
        "enabled": True,
        "description": "Python bytecode cache",
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
        self._onaccess_widgets = {}

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

        # Create On-Access Scanning page (clamd.conf on-access settings)
        self._create_onaccess_page()

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
            page, "Configuration File", self._freshclam_conf_path, "freshclam.conf location"
        )

        # Create paths group
        self._create_paths_group(page)

        # Create update behavior group
        self._create_updates_group(page)

        # Create proxy settings group
        self._create_proxy_group(page)

        self.add(page)

    def _create_file_location_group(
        self, page: Adw.PreferencesPage, title: str, file_path: str, description: str
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
            "clicked", lambda btn: self._open_folder_in_file_manager(parent_dir)
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
        import os
        import subprocess

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
                ["xdg-open", folder_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
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
        self._freshclam_widgets["DatabaseDirectory"] = database_dir_row
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
        self._freshclam_widgets["UpdateLogFile"] = log_file_row
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
        self._freshclam_widgets["NotifyClamd"] = notify_clamd_row
        group.add(notify_clamd_row)

        # LogVerbose switch row
        log_verbose_row = Adw.SwitchRow()
        log_verbose_row.set_title("Verbose Logging")
        log_verbose_row.set_subtitle("Enable detailed logging for database updates")
        self._freshclam_widgets["LogVerbose"] = log_verbose_row
        group.add(log_verbose_row)

        # LogSyslog switch row
        log_syslog_row = Adw.SwitchRow()
        log_syslog_row.set_title("Syslog Logging")
        log_syslog_row.set_subtitle("Send log messages to system log")
        self._freshclam_widgets["LogSyslog"] = log_syslog_row
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
        self._freshclam_widgets["Checks"] = checks_row
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
        self._freshclam_widgets["DatabaseMirror"] = mirror_row
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
        self._freshclam_widgets["HTTPProxyServer"] = proxy_server_row
        group.add(proxy_server_row)

        # HTTPProxyPort spin row (1-65535)
        proxy_port_row = Adw.SpinRow.new_with_range(0, 65535, 1)
        proxy_port_row.set_title("Proxy Port")
        proxy_port_row.set_subtitle("Proxy server port number (0 to disable)")
        proxy_port_row.set_numeric(True)
        proxy_port_row.set_snap_to_ticks(True)
        self._freshclam_widgets["HTTPProxyPort"] = proxy_port_row
        group.add(proxy_port_row)

        # HTTPProxyUsername entry row
        proxy_username_row = Adw.EntryRow()
        proxy_username_row.set_title("Proxy Username")
        proxy_username_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        proxy_username_row.set_show_apply_button(False)
        # Add user icon as prefix
        username_icon = Gtk.Image.new_from_icon_name("system-users-symbolic")
        username_icon.set_margin_start(6)
        proxy_username_row.add_prefix(username_icon)
        self._freshclam_widgets["HTTPProxyUsername"] = proxy_username_row
        group.add(proxy_username_row)

        # HTTPProxyPassword entry row
        proxy_password_row = Adw.PasswordEntryRow()
        proxy_password_row.set_title("Proxy Password")
        proxy_password_row.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        proxy_password_row.set_show_apply_button(False)
        # Add password icon as prefix
        password_icon = Gtk.Image.new_from_icon_name("dialog-password-symbolic")
        password_icon.set_margin_start(6)
        proxy_password_row.add_prefix(password_icon)
        self._freshclam_widgets["HTTPProxyPassword"] = proxy_password_row
        group.add(proxy_password_row)

        page.add(group)