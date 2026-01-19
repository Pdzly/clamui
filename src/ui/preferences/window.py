# ClamUI Preferences Window
"""
Main preferences window orchestrating all preference pages.

This module provides the PreferencesWindow class which composes all
preference page modules into a cohesive preferences interface.
"""

import logging
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

from ...core.clamav_config import parse_config
from ...core.flatpak import (
    ensure_freshclam_config,
    get_freshclam_config_path,
    is_flatpak,
)
from ...core.scheduler import Scheduler

logger = logging.getLogger(__name__)

from .base import PreferencesPageMixin
from .behavior_page import BehaviorPage
from .database_page import DatabasePage
from .exclusions_page import ExclusionsPage
from .onaccess_page import OnAccessPage
from .save_page import SavePage
from .scanner_page import ScannerPage
from .scheduled_page import ScheduledPage
from .virustotal_page import VirusTotalPage


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

    def __init__(self, settings_manager=None, tray_available: bool = False, **kwargs):
        """
        Initialize the preferences window.

        Args:
            settings_manager: Optional SettingsManager instance for application settings
            tray_available: Whether the system tray is available
            **kwargs: Additional arguments passed to parent, including:
                - transient_for: Parent window to be modal to
                - application: The parent application instance
        """
        super().__init__(**kwargs)

        # Store settings manager reference
        self._settings_manager = settings_manager

        # Store tray availability for behavior page
        self._tray_available = tray_available

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

        # Track config load status for UI feedback
        self._freshclam_load_error = None
        self._clamd_load_error = None

        # Default config file paths - use Flatpak-specific paths when running in Flatpak
        if is_flatpak():
            # In Flatpak, use the generated config in user's config directory
            logger.info("Running in Flatpak, using Flatpak-specific config paths")
            flatpak_config = get_freshclam_config_path()
            if flatpak_config:
                # Ensure the config file exists (generates it if needed)
                generated_path = ensure_freshclam_config()
                if generated_path:
                    logger.info(
                        "Flatpak freshclam config generated at: %s", generated_path
                    )
                    self._freshclam_conf_path = str(generated_path)
                else:
                    # Config generation failed - log detailed error
                    logger.error(
                        "Failed to generate Flatpak freshclam config. "
                        "Check disk space and permissions in ~/.var/app/io.github.linx_systems.ClamUI/"
                    )
                    # Use fallback path, but mark that generation failed
                    self._freshclam_conf_path = str(flatpak_config)
                    self._freshclam_load_error = (
                        "Failed to generate Flatpak configuration. "
                        "This may be due to insufficient disk space or permissions."
                    )
            else:
                logger.warning(
                    "Could not determine Flatpak config path, falling back to system path"
                )
                self._freshclam_conf_path = "/etc/clamav/freshclam.conf"
                self._freshclam_load_error = (
                    "Could not determine Flatpak configuration path"
                )
            # clamd.conf is typically not used in Flatpak (daemon runs on host)
            self._clamd_conf_path = "/etc/clamav/clamd.conf"
        else:
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
            self._clamd_conf_path, self._onaccess_widgets, self._clamd_available, self
        )
        self.add(onaccess_page)

        # Create Scheduled Scans page
        scheduled_page = ScheduledPage.create_page(self._scheduled_widgets)
        self.add(scheduled_page)

        # Create Exclusions page (scan exclusion patterns) - instance-based
        exclusions_page_instance = ExclusionsPage(self._settings_manager)
        exclusions_page = exclusions_page_instance.create_page()
        self.add(exclusions_page)

        # Create VirusTotal page (API key and settings)
        virustotal_page = VirusTotalPage.create_page(self._settings_manager, self)
        self.add(virustotal_page)

        # Create Behavior page (window behavior settings) - instance-based
        behavior_page_instance = BehaviorPage(
            self._settings_manager, self._tray_available, parent_window=self
        )
        behavior_page = behavior_page_instance.create_page()
        self.add(behavior_page)

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
        # Load freshclam.conf
        logger.debug("Loading freshclam config from: %s", self._freshclam_conf_path)
        try:
            self._freshclam_config, error = parse_config(self._freshclam_conf_path)
            if error:
                logger.warning("Failed to load freshclam.conf: %s", error)
                self._freshclam_load_error = error
            elif self._freshclam_config:
                # Log number of options loaded (values is a dict in ClamAVConfig)
                num_options = (
                    len(self._freshclam_config.values)
                    if hasattr(self._freshclam_config, "values")
                    and isinstance(self._freshclam_config.values, dict)
                    else 0
                )
                logger.info("Loaded freshclam.conf with %d options", num_options)
                self._freshclam_load_error = None
            self._populate_freshclam_fields()
        except Exception as e:
            logger.exception("Unexpected error loading freshclam.conf: %s", e)
            self._freshclam_load_error = str(e)

        # Load clamd.conf if available
        if self._clamd_available:
            logger.debug("Loading clamd config from: %s", self._clamd_conf_path)
            try:
                self._clamd_config, error = parse_config(self._clamd_conf_path)
                if error:
                    logger.warning("Failed to load clamd.conf: %s", error)
                    self._clamd_load_error = error
                elif self._clamd_config:
                    # Log number of options loaded (values is a dict in ClamAVConfig)
                    num_options = (
                        len(self._clamd_config.values)
                        if hasattr(self._clamd_config, "values")
                        and isinstance(self._clamd_config.values, dict)
                        else 0
                    )
                    logger.info("Loaded clamd.conf with %d options", num_options)
                    self._clamd_load_error = None
                self._populate_clamd_fields()
                self._populate_onaccess_fields()
            except Exception as e:
                logger.exception("Unexpected error loading clamd.conf: %s", e)
                self._clamd_load_error = str(e)

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
