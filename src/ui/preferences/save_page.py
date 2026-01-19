# ClamUI Save & Apply Page
"""
Save & Apply preference page for configuration persistence.

This module provides the SavePage class which handles saving all
preference changes to ClamAV configuration files and ClamUI settings.
"""

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from ...core.clamav_config import (
    backup_config,
    validate_config,
    write_config_with_elevation,
)
from .base import PreferencesPageMixin
from .database_page import DatabasePage
from .onaccess_page import OnAccessPage
from .scanner_page import ScannerPage
from .scheduled_page import ScheduledPage


class SavePage(PreferencesPageMixin):
    """
    Save & Apply preference page for configuration persistence.

    This class creates and manages the UI for saving all preference changes,
    including ClamAV configuration files (freshclam.conf, clamd.conf) and
    ClamUI application settings (scheduled scans).

    The page includes:
    - Information banners explaining auto-save vs manual save
    - Save & Apply button
    - Background thread processing with progress feedback
    - Error/success dialog handling

    Note: This class uses PreferencesPageMixin for shared dialog utilities.
    The save process validates configs, backs them up, writes with elevation,
    and handles scheduled scan enablement/disablement.
    """

    def __init__(
        self,
        window,
        freshclam_config,
        clamd_config,
        freshclam_conf_path: str,
        clamd_conf_path: str,
        clamd_available: bool,
        settings_manager,
        scheduler,
        freshclam_widgets: dict,
        clamd_widgets: dict,
        onaccess_widgets: dict,
        scheduled_widgets: dict,
    ):
        """
        Initialize the SavePage.

        Args:
            window: Parent PreferencesWindow instance (for dialog presentation and config access)
            freshclam_config: (Deprecated) Now accessed from window._freshclam_config
            clamd_config: (Deprecated) Now accessed from window._clamd_config
            freshclam_conf_path: Path to freshclam.conf file
            clamd_conf_path: Path to clamd.conf file
            clamd_available: Whether clamd.conf is available
            settings_manager: SettingsManager instance for app settings
            scheduler: Scheduler instance for scheduled scan management
            freshclam_widgets: Dictionary of freshclam form widgets
            clamd_widgets: Dictionary of clamd form widgets
            onaccess_widgets: Dictionary of on-access form widgets
            scheduled_widgets: Dictionary of scheduled scan form widgets

        Note:
            SavePage now accesses configs from window._freshclam_config and window._clamd_config
            to ensure it always has the latest loaded configs (not None from init time).
        """
        self._window = window
        # Note: Configs are accessed from window._freshclam_config and window._clamd_config
        # to ensure we always have the latest loaded configs (not None from init time)
        self._freshclam_conf_path = freshclam_conf_path
        self._clamd_conf_path = clamd_conf_path
        self._clamd_available = clamd_available
        self._settings_manager = settings_manager
        self._scheduler = scheduler

        # Store widget dictionaries for data collection
        self._freshclam_widgets = freshclam_widgets
        self._clamd_widgets = clamd_widgets
        self._onaccess_widgets = onaccess_widgets
        self._scheduled_widgets = scheduled_widgets

        # Track saving state
        self._is_saving = False
        self._scheduler_error = None

        # Store reference to save button
        self._save_button = None

    def _show_error_dialog(self, title: str, message: str):
        """
        Show an error dialog to the user.

        Overrides PreferencesPageMixin to use self._window as parent
        since SavePage is not a GTK widget.

        Args:
            title: Dialog title
            message: Error message text
        """
        dialog = Adw.AlertDialog()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self._window)

    def _show_success_dialog(self, title: str, message: str):
        """
        Show a success dialog to the user.

        Overrides PreferencesPageMixin to use self._window as parent
        since SavePage is not a GTK widget.

        Args:
            title: Dialog title
            message: Success message text
        """
        dialog = Adw.AlertDialog()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self._window)

    def create_page(self) -> Adw.PreferencesPage:
        """
        Create the Save & Apply preference page.

        This page provides information about save behavior and a button
        to save all configuration changes.

        Returns:
            Configured Adw.PreferencesPage ready to be added to preferences window
        """
        page = Adw.PreferencesPage(
            title="Save & Apply",
            icon_name="document-save-symbolic",
        )

        # Information banner explaining what needs to be saved
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Save Behavior")

        # Auto-save settings info row
        auto_save_row = Adw.ActionRow()
        auto_save_row.set_title("Auto-Saved")
        auto_save_row.set_subtitle("Scan Backend, Exclusions")
        auto_save_icon = Gtk.Image.new_from_icon_name("emblem-default-symbolic")
        auto_save_icon.add_css_class("success")
        auto_save_row.add_prefix(auto_save_icon)
        info_group.add(auto_save_row)

        # Manual save settings info row
        manual_save_row = Adw.ActionRow()
        manual_save_row.set_title("Manual Save Required")
        manual_save_row.set_title_lines(1)
        manual_save_row.set_subtitle(
            "Database Updates, Scanner, On-Access, Scheduled Scans"
        )
        manual_save_row.set_subtitle_lines(1)
        lock_icon = Gtk.Image.new_from_icon_name("system-lock-screen-symbolic")
        lock_icon.add_css_class("warning")
        manual_save_row.add_prefix(lock_icon)
        info_group.add(manual_save_row)

        page.add(info_group)

        # Save & apply button group
        button_group = Adw.PreferencesGroup()
        button_group.set_title("Apply Configuration")

        # Save button row - using ActionRow to properly contain the button
        save_action_row = Adw.ActionRow()
        save_action_row.set_title("Save Configuration")

        # Create the save button
        self._save_button = Gtk.Button()
        self._save_button.set_label("Save & Apply")
        self._save_button.add_css_class("suggested-action")
        self._save_button.set_valign(Gtk.Align.CENTER)
        self._save_button.connect("clicked", self._on_save_clicked)

        # Add button as suffix to the row
        save_action_row.add_suffix(self._save_button)

        button_group.add(save_action_row)
        page.add(button_group)

        return page

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

        # Collect form data from all pages
        freshclam_updates = DatabasePage.collect_data(self._freshclam_widgets)
        clamd_updates = ScannerPage.collect_data(
            self._clamd_widgets, self._clamd_available
        )
        onaccess_updates = OnAccessPage.collect_data(
            self._onaccess_widgets, self._clamd_available
        )
        scheduled_updates = ScheduledPage.collect_data(self._scheduled_widgets)

        # Validate configurations
        if freshclam_updates:
            if not self._window._freshclam_config:
                self._show_error_dialog(
                    "Configuration Error",
                    "Cannot save freshclam settings: Configuration failed to load.\n\n"
                    "This may be due to:\n"
                    "• Missing configuration file\n"
                    "• Insufficient permissions\n"
                    "• Disk space issues (Flatpak)\n\n"
                    "Check the application logs for details.",
                )
                self._is_saving = False
                button.set_sensitive(True)
                return

            is_valid, errors = validate_config(self._window._freshclam_config)
            if not is_valid:
                self._show_error_dialog("Validation Error", "\n".join(errors))
                self._is_saving = False
                button.set_sensitive(True)
                return

        if clamd_updates and self._clamd_available:
            if not self._window._clamd_config:
                self._show_error_dialog(
                    "Configuration Error",
                    "Cannot save clamd settings: Configuration failed to load.\n\n"
                    "Check that /etc/clamav/clamd.conf exists and is readable.",
                )
                self._is_saving = False
                button.set_sensitive(True)
                return

            is_valid, errors = validate_config(self._window._clamd_config)
            if not is_valid:
                self._show_error_dialog("Validation Error", "\n".join(errors))
                self._is_saving = False
                button.set_sensitive(True)
                return

        # Run save in background thread
        save_thread = threading.Thread(
            target=self._save_configs_thread,
            args=(
                freshclam_updates,
                clamd_updates,
                onaccess_updates,
                scheduled_updates,
                button,
            ),
        )
        save_thread.daemon = True
        save_thread.start()

    def _save_configs_thread(
        self,
        freshclam_updates: dict,
        clamd_updates: dict,
        onaccess_updates: dict,
        scheduled_updates: dict,
        button: Gtk.Button,
    ):
        """
        Save configuration files in a background thread.

        Uses elevated privileges (pkexec) to write configuration files
        and manages error handling with thread-safe communication.

        Args:
            freshclam_updates: Dictionary of freshclam.conf updates
            clamd_updates: Dictionary of clamd.conf updates
            onaccess_updates: Dictionary of On-Access scanning settings (clamd.conf)
            scheduled_updates: Dictionary of scheduled scan settings
            button: The save button to re-enable after completion
        """
        try:
            # Backup configurations
            backup_config(self._freshclam_conf_path)
            if self._clamd_available:
                backup_config(self._clamd_conf_path)

            # Save freshclam.conf
            if freshclam_updates and self._window._freshclam_config:
                # Apply updates to config using set_value
                for key, value in freshclam_updates.items():
                    self._window._freshclam_config.set_value(key, value)

                success, error = write_config_with_elevation(
                    self._window._freshclam_config
                )
                if not success:
                    raise Exception(f"Failed to save freshclam.conf: {error}")

            # Save clamd.conf (includes both scanner settings and On-Access settings)
            if (clamd_updates or onaccess_updates) and self._window._clamd_config:
                # Apply scanner updates to config using set_value
                for key, value in clamd_updates.items():
                    self._window._clamd_config.set_value(key, value)
                # Apply On-Access updates to config using set_value
                for key, value in onaccess_updates.items():
                    self._window._clamd_config.set_value(key, value)
                success, error = write_config_with_elevation(self._window._clamd_config)
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
                "Configuration changes have been applied successfully.",
            )
        except Exception as e:
            # Store error for thread-safe handling
            self._scheduler_error = str(e)
            GLib.idle_add(self._show_error_dialog, "Save Failed", str(e))
        finally:
            self._is_saving = False
            GLib.idle_add(button.set_sensitive, True)
