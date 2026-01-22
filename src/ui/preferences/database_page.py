# ClamUI Database Updates Page
"""
Database Updates preference page for freshclam.conf settings.

This module provides the DatabasePage class which handles the UI and logic
for configuring ClamAV database update settings (freshclam.conf).
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..utils import resolve_icon_name
from .base import PreferencesPageMixin, populate_bool_field, populate_int_field, populate_text_field


class DatabasePage(PreferencesPageMixin):
    """
    Database Updates preference page for freshclam.conf configuration.

    This class creates and manages the UI for configuring ClamAV database
    update settings, including paths, update behavior, and proxy settings.

    The page includes:
    - File location display for freshclam.conf
    - Paths group (database directory, log files, clamd notification)
    - Update behavior group (check frequency, database mirrors)
    - Proxy settings group (HTTP proxy configuration)

    Note: This class uses PreferencesPageMixin for shared utilities like
    permission indicators and file location displays.
    """

    @staticmethod
    def create_page(config_path: str, widgets_dict: dict) -> Adw.PreferencesPage:
        """
        Create the Database Updates preference page.

        Args:
            config_path: Path to the freshclam.conf file
            widgets_dict: Dictionary to store widget references for later access

        Returns:
            Configured Adw.PreferencesPage ready to be added to preferences window
        """
        page = Adw.PreferencesPage(
            title="Database Updates",
            icon_name=resolve_icon_name("software-update-available-symbolic"),
        )

        # Create a temporary instance to use mixin methods
        # This is a workaround since these are class methods using mixin
        temp_instance = _DatabasePageHelper()

        # Create file location group
        temp_instance._create_file_location_group(
            page, "Configuration File", config_path, "freshclam.conf location"
        )

        # Create paths group
        DatabasePage._create_paths_group(page, widgets_dict, temp_instance)

        # Create update behavior group
        DatabasePage._create_updates_group(page, widgets_dict, temp_instance)

        # Create proxy settings group
        DatabasePage._create_proxy_group(page, widgets_dict, temp_instance)

        return page

    @staticmethod
    def _create_paths_group(page: Adw.PreferencesPage, widgets_dict: dict, helper):
        """
        Create the Paths preferences group.

        Contains settings for:
        - DatabaseDirectory: Where virus databases are stored
        - UpdateLogFile: Log file for update operations
        - NotifyClamd: Path to clamd.conf for reload notification
        - LogVerbose: Enable verbose logging
        - LogSyslog: Enable syslog logging

        Args:
            page: The preferences page to add the group to
            widgets_dict: Dictionary to store widget references
            helper: Helper instance with _create_permission_indicator method
        """
        group = Adw.PreferencesGroup()
        group.set_title("Paths")
        group.set_description("Configure database and log file locations")
        group.set_header_suffix(helper._create_permission_indicator())

        # DatabaseDirectory row
        database_dir_row = Adw.EntryRow()
        database_dir_row.set_title("Database Directory")
        database_dir_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        database_dir_row.set_show_apply_button(False)
        # Add folder icon as prefix
        folder_icon = Gtk.Image.new_from_icon_name(resolve_icon_name("folder-symbolic"))
        folder_icon.set_margin_start(6)
        database_dir_row.add_prefix(folder_icon)
        widgets_dict["DatabaseDirectory"] = database_dir_row
        group.add(database_dir_row)

        # UpdateLogFile row
        log_file_row = Adw.EntryRow()
        log_file_row.set_title("Update Log File")
        log_file_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        log_file_row.set_show_apply_button(False)
        # Add document icon as prefix
        log_icon = Gtk.Image.new_from_icon_name(
            resolve_icon_name("text-x-generic-symbolic")
        )
        log_icon.set_margin_start(6)
        log_file_row.add_prefix(log_icon)
        widgets_dict["UpdateLogFile"] = log_file_row
        group.add(log_file_row)

        # NotifyClamd row
        notify_clamd_row = Adw.EntryRow()
        notify_clamd_row.set_title("Notify ClamD Config")
        notify_clamd_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        notify_clamd_row.set_show_apply_button(False)
        # Add settings icon as prefix
        notify_icon = Gtk.Image.new_from_icon_name(
            resolve_icon_name("emblem-system-symbolic")
        )
        notify_icon.set_margin_start(6)
        notify_clamd_row.add_prefix(notify_icon)
        widgets_dict["NotifyClamd"] = notify_clamd_row
        group.add(notify_clamd_row)

        # LogVerbose switch row
        log_verbose_row = Adw.SwitchRow()
        log_verbose_row.set_title("Verbose Logging")
        log_verbose_row.set_subtitle("Enable detailed logging for database updates")
        widgets_dict["LogVerbose"] = log_verbose_row
        group.add(log_verbose_row)

        # LogSyslog switch row
        log_syslog_row = Adw.SwitchRow()
        log_syslog_row.set_title("Syslog Logging")
        log_syslog_row.set_subtitle("Send log messages to system log")
        widgets_dict["LogSyslog"] = log_syslog_row
        group.add(log_syslog_row)

        page.add(group)

    @staticmethod
    def _create_updates_group(page: Adw.PreferencesPage, widgets_dict: dict, helper):
        """
        Create the Update Behavior preferences group.

        Contains settings for:
        - Checks: Number of database update checks per day (0-50)
        - DatabaseMirror: Mirror URLs for database downloads

        Args:
            page: The preferences page to add the group to
            widgets_dict: Dictionary to store widget references
            helper: Helper instance with _create_permission_indicator method
        """
        group = Adw.PreferencesGroup()
        group.set_title("Update Behavior")
        group.set_description("Configure how often and where to check for updates")
        group.set_header_suffix(helper._create_permission_indicator())

        # Checks spin row (0-50 updates per day)
        checks_row = Adw.SpinRow.new_with_range(0, 50, 1)
        checks_row.set_title("Checks Per Day")
        checks_row.set_subtitle("Number of update checks per day (0 to disable)")
        checks_row.set_numeric(True)
        checks_row.set_snap_to_ticks(True)
        widgets_dict["Checks"] = checks_row
        group.add(checks_row)

        # DatabaseMirror entry row (primary mirror)
        mirror_row = Adw.EntryRow()
        mirror_row.set_title("Database Mirror")
        mirror_row.set_input_purpose(Gtk.InputPurpose.URL)
        mirror_row.set_show_apply_button(False)
        # Add network icon as prefix
        mirror_icon = Gtk.Image.new_from_icon_name(
            resolve_icon_name("network-server-symbolic")
        )
        mirror_icon.set_margin_start(6)
        mirror_row.add_prefix(mirror_icon)
        widgets_dict["DatabaseMirror"] = mirror_row
        group.add(mirror_row)

        page.add(group)

    @staticmethod
    def _create_proxy_group(page: Adw.PreferencesPage, widgets_dict: dict, helper):
        """
        Create the Proxy Settings preferences group.

        Contains settings for:
        - HTTPProxyServer: Proxy server hostname
        - HTTPProxyPort: Proxy port number
        - HTTPProxyUsername: Proxy authentication username
        - HTTPProxyPassword: Proxy authentication password

        Args:
            page: The preferences page to add the group to
            widgets_dict: Dictionary to store widget references
            helper: Helper instance with _create_permission_indicator method
        """
        group = Adw.PreferencesGroup()
        group.set_title("Proxy Settings")
        group.set_description("Configure HTTP proxy for database downloads (optional)")
        group.set_header_suffix(helper._create_permission_indicator())

        # HTTPProxyServer entry row
        proxy_server_row = Adw.EntryRow()
        proxy_server_row.set_title("Proxy Server")
        proxy_server_row.set_input_purpose(Gtk.InputPurpose.URL)
        proxy_server_row.set_show_apply_button(False)
        # Add network icon as prefix
        server_icon = Gtk.Image.new_from_icon_name(
            resolve_icon_name("network-workgroup-symbolic")
        )
        server_icon.set_margin_start(6)
        proxy_server_row.add_prefix(server_icon)
        widgets_dict["HTTPProxyServer"] = proxy_server_row
        group.add(proxy_server_row)

        # HTTPProxyPort spin row (1-65535)
        proxy_port_row = Adw.SpinRow.new_with_range(0, 65535, 1)
        proxy_port_row.set_title("Proxy Port")
        proxy_port_row.set_subtitle("Proxy server port number (0 to disable)")
        proxy_port_row.set_numeric(True)
        proxy_port_row.set_snap_to_ticks(True)
        widgets_dict["HTTPProxyPort"] = proxy_port_row
        group.add(proxy_port_row)

        # HTTPProxyUsername entry row
        proxy_user_row = Adw.EntryRow()
        proxy_user_row.set_title("Proxy Username")
        proxy_user_row.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        proxy_user_row.set_show_apply_button(False)
        # Add user icon as prefix
        user_icon = Gtk.Image.new_from_icon_name(
            resolve_icon_name("avatar-default-symbolic")
        )
        user_icon.set_margin_start(6)
        proxy_user_row.add_prefix(user_icon)
        widgets_dict["HTTPProxyUsername"] = proxy_user_row
        group.add(proxy_user_row)

        # HTTPProxyPassword entry row (with password input)
        proxy_pass_row = Adw.PasswordEntryRow()
        proxy_pass_row.set_title("Proxy Password")
        widgets_dict["HTTPProxyPassword"] = proxy_pass_row
        group.add(proxy_pass_row)

        page.add(group)

    @staticmethod
    def populate_fields(config, widgets_dict: dict):
        """
        Populate freshclam configuration fields from loaded config.

        Updates UI widgets with values from the parsed freshclam.conf file.

        Args:
            config: Parsed config object with has_key() and get_value() methods
            widgets_dict: Dictionary containing widget references
        """
        if not config:
            return

        # Populate text entry fields
        for key in (
            "DatabaseDirectory",
            "UpdateLogFile",
            "NotifyClamd",
            "DatabaseMirror",
            "HTTPProxyServer",
            "HTTPProxyUsername",
            "HTTPProxyPassword",
        ):
            populate_text_field(config, widgets_dict, key)

        # Populate boolean switches
        for key in ("LogVerbose", "LogSyslog"):
            populate_bool_field(config, widgets_dict, key)

        # Populate integer spin rows
        for key in ("Checks", "HTTPProxyPort"):
            populate_int_field(config, widgets_dict, key)

    @staticmethod
    def collect_data(widgets_dict: dict) -> dict:
        """
        Collect freshclam configuration data from form widgets.

        Args:
            widgets_dict: Dictionary containing widget references

        Returns:
            Dictionary of configuration key-value pairs to save
        """
        updates = {}

        # Collect DatabaseDirectory
        db_dir = widgets_dict["DatabaseDirectory"].get_text()
        if db_dir:
            updates["DatabaseDirectory"] = db_dir

        # Collect UpdateLogFile
        log_file = widgets_dict["UpdateLogFile"].get_text()
        if log_file:
            updates["UpdateLogFile"] = log_file

        # Collect NotifyClamd
        notify_clamd = widgets_dict["NotifyClamd"].get_text()
        if notify_clamd:
            updates["NotifyClamd"] = notify_clamd

        # Collect LogVerbose
        updates["LogVerbose"] = "yes" if widgets_dict["LogVerbose"].get_active() else "no"

        # Collect LogSyslog
        updates["LogSyslog"] = "yes" if widgets_dict["LogSyslog"].get_active() else "no"

        # Collect Checks
        checks_value = int(widgets_dict["Checks"].get_value())
        updates["Checks"] = str(checks_value)

        # Collect DatabaseMirror
        mirror = widgets_dict["DatabaseMirror"].get_text()
        if mirror:
            updates["DatabaseMirror"] = mirror

        # Collect proxy settings
        proxy_server = widgets_dict["HTTPProxyServer"].get_text()
        if proxy_server:
            updates["HTTPProxyServer"] = proxy_server

        proxy_port = int(widgets_dict["HTTPProxyPort"].get_value())
        if proxy_port > 0:
            updates["HTTPProxyPort"] = str(proxy_port)

        proxy_user = widgets_dict["HTTPProxyUsername"].get_text()
        if proxy_user:
            updates["HTTPProxyUsername"] = proxy_user

        proxy_pass = widgets_dict["HTTPProxyPassword"].get_text()
        if proxy_pass:
            updates["HTTPProxyPassword"] = proxy_pass

        return updates


class _DatabasePageHelper(PreferencesPageMixin):
    """
    Helper class to provide access to mixin methods for static context.

    This is a workaround to allow static methods in DatabasePage to use
    the mixin utilities (like _create_permission_indicator). In the future,
    when DatabasePage is integrated into the full PreferencesWindow, this
    helper won't be needed.
    """

    pass
