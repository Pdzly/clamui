# ClamUI Preferences Window
"""
Main preferences window orchestrating all preference pages.

This module provides the PreferencesWindow class which composes all
preference page modules into a cohesive preferences interface.
"""

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

from src.core.clamav_config import parse_config
from src.core.scheduler import Scheduler

from .base import PreferencesPageMixin
from .database_page import DatabasePage
from .exclusions_page import ExclusionsPage
from .onaccess_page import OnAccessPage
from .save_page import SavePage
from .scanner_page import ScannerPage
from .scheduled_page import ScheduledPage


class PreferencesWindow(Adw.PreferencesWindow, PreferencesPageMixin):
    """
    Preferences window for ClamUI.

    Provides a settings interface for ClamAV configuration with:
    - Database update settings (freshclam.conf)
    - Scanner settings (clamd.conf)
    - On-Access scanning settings (clamd.conf)
    - Scheduled scans configuration
    - Scan exclusion patterns
    - Save & Apply functionality with permission elevation

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

        # Store settings manager reference
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

        # Check if clamd.conf exists
        if Path(self._clamd_conf_path).exists():
            self._clamd_available = True

        # Saving state (used by SavePage)
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
        database_page = DatabasePage.create_page(
            self._freshclam_conf_path, self._freshclam_widgets
        )
        self.add(database_page)

        # Create Scanner Settings page (clamd.conf)
        scanner_page = ScannerPage.create_page(
            self._clamd_conf_path,
            self._clamd_widgets,
            self._settings_manager,
            self._clamd_available,
            self,
        )
        self.add(scanner_page)

        # Create On-Access Scanning page (clamd.conf on-access settings)
        onaccess_page = OnAccessPage.create_page(
            self._clamd_conf_path, self._onaccess_widgets, self._clamd_available
        )
        self.add(onaccess_page)

        # Create Scheduled Scans page
        scheduled_page = ScheduledPage.create_page(
            self._scheduled_widgets, self._settings_manager
        )
        self.add(scheduled_page)

        # Create Exclusions page (scan exclusion patterns) - instance-based
        exclusions_page_instance = ExclusionsPage(self._settings_manager)
        exclusions_page = exclusions_page_instance.create_page()
        self.add(exclusions_page)

        # Create Save & Apply page - instance-based
        save_page_instance = SavePage(
            self,
            self._freshclam_config,
            self._clamd_config,
            self._freshclam_conf_path,
            self._clamd_conf_path,
            self._clamd_available,
            self._settings_manager,
            self._scheduler,
            self._freshclam_widgets,
            self._clamd_widgets,
            self._onaccess_widgets,
            self._scheduled_widgets,
        )
        save_page = save_page_instance.create_page()
        self.add(save_page)

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
                self._populate_onaccess_fields()
            except Exception as e:
                print(f"Error loading clamd.conf: {e}")

    def _populate_freshclam_fields(self):
        """
        Populate freshclam configuration fields from loaded config.

        Updates UI widgets with values from the parsed freshclam.conf file.
        """
        if not self._freshclam_config:
            return

        DatabasePage.populate_fields(self._freshclam_config, self._freshclam_widgets)

    def _populate_clamd_fields(self):
        """
        Populate clamd configuration fields from loaded config.

        Updates UI widgets with values from the parsed clamd.conf file.
        """
        if not self._clamd_config:
            return

        ScannerPage.populate_fields(self._clamd_config, self._clamd_widgets)

    def _populate_onaccess_fields(self):
        """
        Populate on-access configuration fields from loaded config.

        Updates UI widgets with values from the parsed clamd.conf file.
        """
        if not self._clamd_config:
            return

        OnAccessPage.populate_fields(self._clamd_config, self._onaccess_widgets)

    def _populate_scheduled_fields(self):
        """
        Populate scheduled scan widgets from saved settings.

        Loads settings from the settings manager and updates the UI widgets.
        """
        if not self._settings_manager:
            return

        ScheduledPage.populate_fields(self._settings_manager, self._scheduled_widgets)
