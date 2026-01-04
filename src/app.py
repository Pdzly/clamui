# ClamUI Application
"""
Main Adwaita Application class for ClamUI.

This module defines the ClamUIApp class, which is the central GTK4/Adwaita
application that manages the complete lifecycle of the ClamUI antivirus GUI.

Key Responsibilities:
    - Application lifecycle management (startup, activation, shutdown)
    - View management and navigation between different UI panels
    - System tray integration via TrayManager subprocess
    - Profile management integration for scan configurations
    - Settings and notification management coordination
    - GTK action setup for keyboard shortcuts and menu actions

The application uses GLib.idle_add for thread-safe UI updates when handling
callbacks from the tray indicator subprocess, ensuring all GTK operations
occur on the main thread.

Classes:
    ClamUIApp: Main Adw.Application subclass managing the application.

Example:
    from src.app import ClamUIApp

    app = ClamUIApp()
    exit_code = app.run(sys.argv)
"""

import logging
import os
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from .core.notification_manager import NotificationManager
from .core.settings_manager import SettingsManager
from .profiles.models import ScanProfile
from .profiles.profile_manager import ProfileManager
from .ui.components_view import ComponentsView
from .ui.logs_view import LogsView
from .ui.preferences_window import PreferencesWindow
from .ui.quarantine_view import QuarantineView
from .ui.scan_view import ScanView
from .ui.statistics_view import StatisticsView

# Tray manager - uses subprocess to avoid GTK3/GTK4 version conflict
from .ui.tray_manager import TrayManager
from .ui.update_view import UpdateView
from .ui.window import MainWindow

logger = logging.getLogger(__name__)


class ClamUIApp(Adw.Application):
    """
    ClamUI GTK4/Adwaita Application.

    This is the main application class that handles application lifecycle,
    window management, and global application state.
    """

    def __init__(self):
        """Initialize the ClamUI application."""
        super().__init__(
            application_id="com.github.rooki.clamui", flags=Gio.ApplicationFlags.FLAGS_NONE
        )

        # Application metadata
        self._app_name = "ClamUI"
        self._version = "0.1.0"

        # Settings and notification management
        self._settings_manager = SettingsManager()
        self._notification_manager = NotificationManager(self._settings_manager)

        # Profile management
        # Use XDG config directory (same location as settings)
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "~/.config")
        config_dir = Path(xdg_config_home).expanduser() / "clamui"
        self._profile_manager = ProfileManager(config_dir)

        # View management
        self._scan_view = None
        self._update_view = None
        self._logs_view = None
        self._components_view = None
        self._statistics_view = None
        self._quarantine_view = None
        self._current_view = None

        # Tray indicator (initialized in do_startup if available)
        self._tray_indicator = None

        # Track first activation for start-minimized functionality
        self._first_activation = True

    @property
    def app_name(self) -> str:
        """Get the application name."""
        return self._app_name

    @property
    def version(self) -> str:
        """Get the application version."""
        return self._version

    @property
    def notification_manager(self) -> NotificationManager:
        """Get the notification manager instance."""
        return self._notification_manager

    @property
    def settings_manager(self) -> SettingsManager:
        """Get the settings manager instance."""
        return self._settings_manager

    @property
    def profile_manager(self) -> ProfileManager:
        """Get the profile manager instance."""
        return self._profile_manager

    @property
    def tray_indicator(self):
        """Get the tray indicator instance (may be None if not available)."""
        return self._tray_indicator

    def do_activate(self):
        """
        Handle application activation.

        This method is called when the application is activated (launched).
        It creates and presents the main window with the scan interface.

        If start_minimized is enabled and tray indicator is available,
        the window is created but not presented on first activation,
        allowing the app to run in the tray without showing a window.
        """
        # Get existing window or create new one
        win = self.props.active_window
        is_new_window = win is None

        if not win:
            # Create the main window
            win = MainWindow(application=self)

            # Create all views (kept in memory for state preservation)
            self._scan_view = ScanView(settings_manager=self._settings_manager)
            self._update_view = UpdateView()
            self._logs_view = LogsView()
            self._components_view = ComponentsView()
            self._statistics_view = StatisticsView()

            # Connect statistics view quick scan callback
            self._statistics_view.set_quick_scan_callback(self._on_statistics_quick_scan)
            self._quarantine_view = QuarantineView()

            # Connect scan state callback for tray integration
            self._scan_view.set_scan_state_changed_callback(self._on_scan_state_changed)

            # Set the scan view as the default content
            win.set_content_view(self._scan_view)
            win.set_active_view("scan")
            self._current_view = "scan"

            # Sync profiles to tray menu
            self._sync_profiles_to_tray()

        # Check if we should start minimized (only on first activation)
        start_minimized = (
            self._first_activation
            and is_new_window
            and self._settings_manager.get("start_minimized", False)
            and self._tray_indicator is not None
        )

        if start_minimized:
            # First activation with start_minimized enabled - don't show window
            # The tray indicator is already active from do_startup
            logger.info("Starting minimized to system tray")
        else:
            win.present()

        # Mark first activation as complete
        self._first_activation = False

    def do_startup(self):
        """
        Handle application startup.

        This method is called when the application first starts.
        It's used for one-time initialization that should happen
        before any windows are created.
        """
        Adw.Application.do_startup(self)

        # Set application reference for notification manager
        self._notification_manager.set_application(self)

        # Set up application actions
        self._setup_actions()

        # Initialize tray indicator if available
        self._setup_tray_indicator()

    def _setup_actions(self):
        """Set up application-level actions."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        # Preferences action
        preferences_action = Gio.SimpleAction.new("preferences", None)
        preferences_action.connect("activate", self._on_preferences)
        self.add_action(preferences_action)
        self.set_accels_for_action("app.preferences", ["<Control>comma"])

        # View switching actions
        show_scan_action = Gio.SimpleAction.new("show-scan", None)
        show_scan_action.connect("activate", self._on_show_scan)
        self.add_action(show_scan_action)
        self.set_accels_for_action("app.show-scan", ["<Control>1"])

        show_update_action = Gio.SimpleAction.new("show-update", None)
        show_update_action.connect("activate", self._on_show_update)
        self.add_action(show_update_action)
        self.set_accels_for_action("app.show-update", ["<Control>2"])

        show_logs_action = Gio.SimpleAction.new("show-logs", None)
        show_logs_action.connect("activate", self._on_show_logs)
        self.add_action(show_logs_action)
        self.set_accels_for_action("app.show-logs", ["<Control>3"])

        show_components_action = Gio.SimpleAction.new("show-components", None)
        show_components_action.connect("activate", self._on_show_components)
        self.add_action(show_components_action)
        self.set_accels_for_action("app.show-components", ["<Control>4"])

        show_quarantine_action = Gio.SimpleAction.new("show-quarantine", None)
        show_quarantine_action.connect("activate", self._on_show_quarantine)
        self.add_action(show_quarantine_action)
        self.set_accels_for_action("app.show-quarantine", ["<Control>5"])

        show_statistics_action = Gio.SimpleAction.new("show-statistics", None)
        show_statistics_action.connect("activate", self._on_show_statistics)
        self.add_action(show_statistics_action)
        self.set_accels_for_action("app.show-statistics", ["<Control>6"])

        # Scan action - start scan with F5
        start_scan_action = Gio.SimpleAction.new("start-scan", None)
        start_scan_action.connect("activate", self._on_start_scan)
        self.add_action(start_scan_action)
        self.set_accels_for_action("app.start-scan", ["F5"])

        # Update action - start database update with F6
        start_update_action = Gio.SimpleAction.new("start-update", None)
        start_update_action.connect("activate", self._on_start_update)
        self.add_action(start_update_action)
        self.set_accels_for_action("app.start-update", ["F6"])

    def _setup_tray_indicator(self):
        """Initialize the system tray indicator subprocess."""
        try:
            self._tray_indicator = TrayManager()

            # Connect tray menu actions to handler methods
            self._tray_indicator.set_action_callbacks(
                on_quick_scan=self._on_tray_quick_scan,
                on_full_scan=self._on_tray_full_scan,
                on_update=self._on_tray_update,
                on_quit=self._on_tray_quit,
            )

            # Set window toggle callback
            self._tray_indicator.set_window_toggle_callback(on_toggle=self._on_tray_window_toggle)

            # Set profile selection callback
            self._tray_indicator.set_profile_select_callback(on_select=self._on_tray_profile_select)

            # Start the tray subprocess
            if self._tray_indicator.start():
                logger.info("Tray indicator subprocess started")
            else:
                logger.warning("Failed to start tray indicator subprocess")
                self._tray_indicator = None
        except Exception as e:
            logger.warning(f"Failed to initialize tray indicator: {e}")
            self._tray_indicator = None

    def _sync_profiles_to_tray(self) -> None:
        """
        Sync the profile list to the tray menu.

        Retrieves all profiles from the profile manager and sends them
        to the tray indicator for display in the profiles submenu.
        """
        if self._tray_indicator is None:
            return

        try:
            profiles = self._profile_manager.list_profiles()

            # Format profiles for tray (list of dicts with id, name, is_default)
            profile_data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "is_default": p.is_default,
                }
                for p in profiles
            ]

            # Get current profile ID from scan view if available
            current_profile_id = None
            if self._scan_view:
                selected_profile = self._scan_view.get_selected_profile()
                if selected_profile:
                    current_profile_id = selected_profile.id

            self._tray_indicator.update_profiles(profile_data, current_profile_id)
            logger.debug(f"Synced {len(profile_data)} profiles to tray menu")

        except Exception as e:
            logger.warning(f"Failed to sync profiles to tray: {e}")

    def _get_quick_scan_profile(self) -> ScanProfile | None:
        """
        Retrieve the Quick Scan profile by name.

        Returns the Quick Scan profile if it exists, or None if not found.
        This allows graceful fallback behavior when the profile is unavailable.

        Returns:
            The Quick Scan ScanProfile if found, None otherwise.
        """
        return self._profile_manager.get_profile_by_name("Quick Scan")

    def _on_quit(self, action, param):
        """Handle quit action."""
        self.quit()

    def _on_preferences(self, action, param):
        """Handle preferences action - show preferences window."""
        win = self.props.active_window
        if win:
            preferences = PreferencesWindow(
                transient_for=win, settings_manager=self._settings_manager
            )
            preferences.present()

    def _on_show_scan(self, action, param):
        """Handle show-scan action - switch to scan view."""
        if self._current_view == "scan":
            return

        win = self.props.active_window
        if win and self._scan_view:
            win.set_content_view(self._scan_view)
            win.set_active_view("scan")
            self._current_view = "scan"

    def _on_show_update(self, action, param):
        """Handle show-update action - switch to update view."""
        if self._current_view == "update":
            return

        win = self.props.active_window
        if win and self._update_view:
            win.set_content_view(self._update_view)
            win.set_active_view("update")
            self._current_view = "update"

    def _on_show_logs(self, action, param):
        """Handle show-logs action - switch to logs view."""
        if self._current_view == "logs":
            return

        win = self.props.active_window
        if win and self._logs_view:
            win.set_content_view(self._logs_view)
            win.set_active_view("logs")
            self._current_view = "logs"

    def _on_show_components(self, action, param):
        """Handle show-components action - switch to components view."""
        if self._current_view == "components":
            return

        win = self.props.active_window
        if win and self._components_view:
            win.set_content_view(self._components_view)
            win.set_active_view("components")
            self._current_view = "components"

    def _on_show_statistics(self, action, param):
        """Handle show-statistics action - switch to statistics view."""
        if self._current_view == "statistics":
            return

        win = self.props.active_window
        if win and self._statistics_view:
            win.set_content_view(self._statistics_view)
            win.set_active_view("statistics")
            self._current_view = "statistics"

    def _on_start_scan(self, action, param):
        """
        Handle start-scan action - start scan with F5.

        If not on scan view, switches to it first, then triggers the scan.
        """
        win = self.props.active_window
        if win and self._scan_view:
            # Switch to scan view if not already there
            if self._current_view != "scan":
                win.set_content_view(self._scan_view)
                win.set_active_view("scan")
                self._current_view = "scan"

            # Trigger the scan
            self._scan_view._start_scan()

    def _on_start_update(self, action, param):
        """
        Handle start-update action - start database update with F6.

        If not on update view, switches to it first, then triggers the update
        if freshclam is available and not already updating.
        """
        win = self.props.active_window
        if win and self._update_view:
            # Switch to update view if not already there
            if self._current_view != "update":
                win.set_content_view(self._update_view)
                win.set_active_view("update")
                self._current_view = "update"

            # Trigger the update if freshclam is available and not already updating
            if self._update_view._freshclam_available and not self._update_view._is_updating:
                self._update_view._start_update()

    def _on_statistics_quick_scan(self):
        """
        Handle Quick Scan action from statistics view.

        Switches to scan view and applies the Quick Scan profile.
        Falls back to home directory if the profile is not found.
        Does not automatically start the scan - user must click Start Scan.
        """
        win = self.props.active_window
        if win and self._scan_view:
            # Switch to scan view
            win.set_content_view(self._scan_view)
            win.set_active_view("scan")
            self._current_view = "scan"

            # Try to use Quick Scan profile
            quick_scan_profile = self._get_quick_scan_profile()
            if quick_scan_profile:
                # Refresh profiles to ensure list is up to date
                self._scan_view.refresh_profiles()
                # Apply the Quick Scan profile
                self._scan_view.set_selected_profile(quick_scan_profile.id)
                logger.info(
                    f"Quick scan configured with Quick Scan profile from statistics view "
                    f"(profile_id={quick_scan_profile.id})"
                )
            else:
                # Fallback to home directory if profile not found
                home_dir = os.path.expanduser("~")
                self._scan_view._set_selected_path(home_dir)
                logger.warning(
                    f"Quick Scan profile not found, falling back to home directory "
                    f"scan from statistics view (path={home_dir})"
                )

    def _on_show_quarantine(self, action, param):
        """Handle show-quarantine action - switch to quarantine view."""
        if self._current_view == "quarantine":
            return

        win = self.props.active_window
        if win and self._quarantine_view:
            win.set_content_view(self._quarantine_view)
            win.set_active_view("quarantine")
            self._current_view = "quarantine"

    def _on_about(self, action, param):
        """Handle about action - show about dialog."""
        about = Adw.AboutDialog()
        about.set_application_name(self._app_name)
        about.set_version(self._version)
        about.set_developer_name("ClamUI Contributors")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_comments("A graphical interface for ClamAV antivirus")
        about.set_website("https://github.com/clamui/clamui")
        about.set_issue_url("https://github.com/clamui/clamui/issues")
        about.set_application_icon("security-high-symbolic")
        about.present(self.props.active_window)

    # Tray indicator action handlers

    def _on_tray_quick_scan(self) -> None:
        """
        Handle Quick Scan action from tray menu.

        Presents the window, switches to scan view, applies the Quick Scan
        profile, and starts the scan. Falls back to home directory if the
        Quick Scan profile is not found.
        """
        # Use GLib.idle_add to ensure GTK4 operations run on main thread
        GLib.idle_add(self._do_tray_quick_scan)

    def _do_tray_quick_scan(self) -> bool:
        """Execute quick scan on main thread."""
        # Activate the application (creates window if needed)
        self.activate()

        win = self.props.active_window
        if win and self._scan_view:
            # Switch to scan view
            win.set_content_view(self._scan_view)
            win.set_active_view("scan")
            self._current_view = "scan"

            # Try to use Quick Scan profile
            quick_scan_profile = self._get_quick_scan_profile()
            if quick_scan_profile:
                # Refresh profiles to ensure list is up to date
                self._scan_view.refresh_profiles()
                # Apply the Quick Scan profile
                self._scan_view.set_selected_profile(quick_scan_profile.id)
                # Start the scan
                self._scan_view._start_scan()
                logger.info(
                    f"Quick scan started with Quick Scan profile from tray menu "
                    f"(profile_id={quick_scan_profile.id})"
                )
            else:
                # Fallback to home directory if profile not found
                home_dir = os.path.expanduser("~")
                self._scan_view._set_selected_path(home_dir)
                self._scan_view._start_scan()
                logger.warning(
                    f"Quick Scan profile not found, falling back to home directory "
                    f"scan from tray menu (path={home_dir})"
                )

        return False  # Don't repeat

    def _on_tray_full_scan(self) -> None:
        """
        Handle Full Scan action from tray menu.

        Presents the window and switches to scan view, allowing the user
        to select a folder for scanning.
        """
        # Use GLib.idle_add to ensure GTK4 operations run on main thread
        GLib.idle_add(self._do_tray_full_scan)

    def _do_tray_full_scan(self) -> bool:
        """Execute full scan setup on main thread."""
        # Activate the application (creates window if needed)
        self.activate()

        win = self.props.active_window
        if win and self._scan_view:
            # Switch to scan view
            win.set_content_view(self._scan_view)
            win.set_active_view("scan")
            self._current_view = "scan"

            # Open folder selection dialog
            self._scan_view._on_select_folder_clicked(None)

            logger.info("Full scan folder selection opened from tray menu")

        return False  # Don't repeat

    def _on_tray_update(self) -> None:
        """
        Handle Update Definitions action from tray menu.

        Presents the window, switches to update view, and starts the
        database update process.
        """
        # Use GLib.idle_add to ensure GTK4 operations run on main thread
        GLib.idle_add(self._do_tray_update)

    def _do_tray_update(self) -> bool:
        """Execute database update on main thread."""
        # Activate the application (creates window if needed)
        self.activate()

        win = self.props.active_window
        if win and self._update_view:
            # Switch to update view
            win.set_content_view(self._update_view)
            win.set_active_view("update")
            self._current_view = "update"

            # Start the update if freshclam is available
            if self._update_view._freshclam_available and not self._update_view._is_updating:
                self._update_view._start_update()
                logger.info("Database update started from tray menu")
            else:
                logger.info("Database update view opened from tray menu (update not started)")

        return False  # Don't repeat

    def _on_tray_quit(self) -> None:
        """
        Handle Quit action from tray menu.

        Quits the application cleanly.
        """
        # Use GLib.idle_add to ensure GTK4 operations run on main thread
        GLib.idle_add(self._do_tray_quit)

    def _do_tray_quit(self) -> bool:
        """Execute quit on main thread."""
        self.quit()
        return False  # Don't repeat

    def _on_tray_window_toggle(self) -> None:
        """
        Handle window toggle action from tray menu.

        Shows or hides the main window.
        """
        win = self.props.active_window
        if win is None:
            # No window exists, create one
            self.activate()
        elif win.get_visible():
            # Window visible, hide it
            win.hide()
            if self._tray_indicator:
                self._tray_indicator.update_window_menu_label(visible=False)
        else:
            # Window hidden, show it
            win.present()
            if self._tray_indicator:
                self._tray_indicator.update_window_menu_label(visible=True)

    def _on_tray_profile_select(self, profile_id: str) -> None:
        """
        Handle profile selection from tray menu.

        Shows the main window, switches to scan view, and updates the
        profile selection to the chosen profile.

        Args:
            profile_id: The ID of the selected profile
        """
        # Use GLib.idle_add to ensure GTK4 operations run on main thread
        GLib.idle_add(self._do_tray_profile_select, profile_id)

    def _do_tray_profile_select(self, profile_id: str) -> bool:
        """Execute profile selection on main thread."""
        # Activate the application (creates window if needed)
        self.activate()

        win = self.props.active_window
        if win and self._scan_view:
            # Switch to scan view
            win.set_content_view(self._scan_view)
            win.set_active_view("scan")
            self._current_view = "scan"

            # Refresh profiles to ensure list is up to date
            self._scan_view.refresh_profiles()

            # Select the profile by ID
            if self._scan_view.set_selected_profile(profile_id):
                logger.info(f"Profile selected from tray menu: {profile_id}")
            else:
                logger.warning(f"Failed to select profile from tray: {profile_id}")

        return False  # Don't repeat

    # Scan state change handler (for tray integration)

    def _on_scan_state_changed(self, is_scanning: bool, result=None) -> None:
        """
        Handle scan state changes for tray indicator updates.

        Called by ScanView when scanning starts or stops.

        Args:
            is_scanning: True when scan starts, False when scan ends
            result: ScanResult when scan completes (None when starting)
        """
        if self._tray_indicator is None:
            return

        if is_scanning:
            # Update tray to scanning state
            self._tray_indicator.update_status("scanning")
            # Show indeterminate progress (tray doesn't get real-time %)
            # Clear any previous label, icon change indicates scanning
            self._tray_indicator.update_scan_progress(0)
            logger.debug("Tray updated to scanning state")
        else:
            # Clear progress label
            self._tray_indicator.update_scan_progress(0)

            # Update tray icon based on scan result
            if result is not None:
                if result.has_threats:
                    # Threats detected - show alert/threat status
                    self._tray_indicator.update_status("threat")
                    logger.debug(f"Tray updated to threat state ({result.infected_count} threats)")
                elif result.is_clean:
                    # No threats - show protected status
                    self._tray_indicator.update_status("protected")
                    logger.debug("Tray updated to protected state (scan clean)")
                else:
                    # Error or cancelled - show warning status
                    self._tray_indicator.update_status("warning")
                    logger.debug(f"Tray updated to warning state (status: {result.status.value})")
            else:
                # No result provided, default to protected
                self._tray_indicator.update_status("protected")
                logger.debug("Tray updated to protected state (no result)")

    def do_shutdown(self):
        """
        Handle application shutdown.

        This method is called when the application is about to terminate.
        It performs cleanup of resources including:
        - Tray indicator
        - Active scans
        - Database connections
        """
        logger.info("Application shutdown initiated")

        # Cancel any active scans
        if self._scan_view is not None:
            try:
                # Cancel any ongoing scan
                if hasattr(self._scan_view, "_scanner") and self._scan_view._scanner is not None:
                    self._scan_view._scanner.cancel()
                    logger.debug("Active scan cancelled during shutdown")
            except Exception as e:
                logger.warning(f"Error cancelling scan during shutdown: {e}")

        # Clean up tray indicator to prevent ghost icons
        if self._tray_indicator is not None:
            try:
                self._tray_indicator.cleanup()
                self._tray_indicator = None
                logger.debug("Tray indicator cleanup completed during shutdown")
            except Exception as e:
                logger.warning(f"Error cleaning up tray indicator: {e}")

        # Clear view references to allow garbage collection
        self._scan_view = None
        self._update_view = None
        self._logs_view = None
        self._components_view = None
        self._statistics_view = None
        self._quarantine_view = None
        self._current_view = None

        logger.info("Application shutdown cleanup completed")

        # Call parent shutdown
        Adw.Application.do_shutdown(self)
