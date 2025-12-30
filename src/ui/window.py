# ClamUI Main Window
"""
Main application window for ClamUI.
"""

import logging
from typing import TYPE_CHECKING

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib

if TYPE_CHECKING:
    from ..core.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class MainWindow(Adw.ApplicationWindow):
    """
    Main application window for ClamUI.

    This window provides the main layout with an Adwaita header bar
    and a content area for the scan interface.
    """

    def __init__(self, application: Adw.Application, **kwargs):
        """
        Initialize the main window.

        Args:
            application: The parent Adw.Application instance
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(application=application, **kwargs)

        # Store application reference for settings access
        self._application = application

        # Set window properties
        self.set_title("ClamUI")
        self.set_default_size(800, 700)
        self.set_size_request(400, 700)  # Minimum size to keep ClamAV status bar visible

        # Set up minimize-to-tray handling
        self._setup_minimize_to_tray()

        # Create the main layout
        self._setup_ui()

    def _setup_minimize_to_tray(self) -> None:
        """
        Set up minimize-to-tray functionality.

        Connects to window state changes to detect minimize events.
        When minimize_to_tray setting is enabled and tray is available,
        the window will hide to tray instead of minimizing to taskbar.
        """
        # Track if we're handling minimize-to-tray to prevent recursion
        self._handling_minimize = False

        # Connect to the window's surface to detect state changes
        # We need to do this after the window is realized
        self.connect("realize", self._on_window_realized)

    def _on_window_realized(self, window) -> None:
        """
        Handle window realization.

        Connects to the surface state notify signal to detect minimize events.
        """
        surface = self.get_surface()
        if surface is not None:
            # Connect to surface state changes to detect minimize
            surface.connect("notify::state", self._on_surface_state_changed)

    def _on_surface_state_changed(self, surface, pspec) -> None:
        """
        Handle surface state changes.

        When the window is minimized (MINIMIZED state set) and
        minimize_to_tray is enabled, hide the window to tray instead.

        Args:
            surface: The Gdk.Surface whose state changed
            pspec: The property specification
        """
        if self._handling_minimize:
            return

        state = surface.get_state()

        # Check if minimized state was just set
        if state & Gdk.ToplevelState.MINIMIZED:
            if self._should_minimize_to_tray():
                self._handling_minimize = True
                try:
                    # Unminimize first, then hide to tray
                    # Use idle_add to defer after state change completes
                    GLib.idle_add(self._do_minimize_to_tray)
                finally:
                    self._handling_minimize = False

    def _should_minimize_to_tray(self) -> bool:
        """
        Check if minimize-to-tray should be used.

        Returns:
            True if minimize_to_tray setting is enabled and tray is available
        """
        # Check if we have access to settings manager
        if not hasattr(self._application, 'settings_manager'):
            return False

        settings = self._application.settings_manager
        if settings is None:
            return False

        # Check if minimize_to_tray is enabled
        if not settings.get('minimize_to_tray', False):
            return False

        # Check if tray indicator is available
        if not hasattr(self._application, 'tray_indicator'):
            return False

        tray = self._application.tray_indicator
        if tray is None:
            return False

        return True

    def _do_minimize_to_tray(self) -> bool:
        """
        Perform the minimize-to-tray action.

        Called from idle to ensure state changes have completed.

        Returns:
            False to remove from idle queue
        """
        # Restore window from minimized state first
        self.unminimize()

        # Then hide to tray
        self.hide_window()

        logger.debug("Window minimized to tray")

        # Update tray menu label if tray is available
        if hasattr(self._application, 'tray_indicator'):
            tray = self._application.tray_indicator
            if tray is not None and hasattr(tray, 'update_window_menu_label'):
                tray.update_window_menu_label()

        return False  # Remove from idle queue

    def _setup_ui(self):
        """Set up the window UI layout."""
        # Main vertical box to hold all content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Create the header bar
        header_bar = self._create_header_bar()
        main_box.append(header_bar)

        # Create the content area
        self._content_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._content_area.set_vexpand(True)
        self._content_area.set_hexpand(True)
        main_box.append(self._content_area)

        # Set the main box as window content
        self.set_content(main_box)

        # Show placeholder content (will be replaced with ScanView in integration)
        self._show_placeholder()

    def _create_header_bar(self) -> Adw.HeaderBar:
        """
        Create the application header bar.

        Returns:
            Configured Adw.HeaderBar
        """
        header_bar = Adw.HeaderBar()

        # Add title widget
        title_label = Gtk.Label(label="ClamUI")
        title_label.add_css_class("title")
        header_bar.set_title_widget(title_label)

        # Add navigation buttons on the left
        nav_box = self._create_navigation_buttons()
        header_bar.pack_start(nav_box)

        # Add menu button on the right
        menu_button = self._create_menu_button()
        header_bar.pack_end(menu_button)

        return header_bar

    def _create_navigation_buttons(self) -> Gtk.Box:
        """
        Create navigation buttons for switching between views.

        Returns:
            Gtk.Box containing the navigation toggle buttons
        """
        # Create a linked button box for navigation
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        nav_box.add_css_class("linked")

        # Scan button (default active)
        self._scan_button = Gtk.ToggleButton()
        self._scan_button.set_icon_name("folder-symbolic")
        self._scan_button.set_tooltip_text("Scan Files")
        self._scan_button.set_active(True)
        self._scan_button.set_action_name("app.show-scan")
        nav_box.append(self._scan_button)

        # Database update button
        self._database_button = Gtk.ToggleButton()
        self._database_button.set_icon_name("software-update-available-symbolic")
        self._database_button.set_tooltip_text("Update Database")
        self._database_button.set_action_name("app.show-update")
        nav_box.append(self._database_button)

        # Logs button
        self._logs_button = Gtk.ToggleButton()
        self._logs_button.set_icon_name("document-open-recent-symbolic")
        self._logs_button.set_tooltip_text("View Logs")
        self._logs_button.set_action_name("app.show-logs")
        nav_box.append(self._logs_button)

        # Components button
        self._components_button = Gtk.ToggleButton()
        self._components_button.set_icon_name("applications-system-symbolic")
        self._components_button.set_tooltip_text("ClamAV Components")
        self._components_button.set_action_name("app.show-components")
        nav_box.append(self._components_button)

        return nav_box

    def set_active_view(self, view_name: str):
        """
        Update the navigation button states based on the active view.

        Args:
            view_name: The name of the active view ('scan', 'update', 'logs', or 'components')
        """
        if view_name == "scan":
            self._scan_button.set_active(True)
            self._database_button.set_active(False)
            self._logs_button.set_active(False)
            self._components_button.set_active(False)
        elif view_name == "update":
            self._scan_button.set_active(False)
            self._database_button.set_active(True)
            self._logs_button.set_active(False)
            self._components_button.set_active(False)
        elif view_name == "logs":
            self._scan_button.set_active(False)
            self._database_button.set_active(False)
            self._logs_button.set_active(True)
            self._components_button.set_active(False)
        elif view_name == "components":
            self._scan_button.set_active(False)
            self._database_button.set_active(False)
            self._logs_button.set_active(False)
            self._components_button.set_active(True)

    def _create_menu_button(self) -> Gtk.MenuButton:
        """
        Create the primary menu button.

        Returns:
            Configured Gtk.MenuButton
        """
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Menu")

        # Create menu model
        menu = Gio.Menu()
        menu.append("Preferences", "app.preferences")
        menu.append("About ClamUI", "app.about")
        menu.append("Quit", "app.quit")

        menu_button.set_menu_model(menu)

        return menu_button

    def _show_placeholder(self):
        """Show placeholder content in the content area."""
        placeholder = Adw.StatusPage()
        placeholder.set_title("ClamUI")
        placeholder.set_description("ClamAV Desktop Scanner")
        placeholder.set_icon_name("security-high-symbolic")
        placeholder.set_vexpand(True)

        self._content_area.append(placeholder)

    def set_content_view(self, view: Gtk.Widget):
        """
        Set the main content view.

        Removes any existing content and sets the new view.

        Args:
            view: The widget to display in the content area
        """
        # Remove existing content
        child = self._content_area.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._content_area.remove(child)
            child = next_child

        # Add the new view
        view.set_vexpand(True)
        view.set_hexpand(True)
        self._content_area.append(view)

    @property
    def content_area(self) -> Gtk.Box:
        """
        Get the content area widget.

        Returns:
            The content area Gtk.Box
        """
        return self._content_area

    def toggle_visibility(self) -> None:
        """
        Toggle the window's visibility.

        If the window is visible, hide it. If hidden, show and present it.
        """
        if self.is_visible():
            self.hide_window()
        else:
            self.show_window()

    def show_window(self) -> None:
        """
        Show the window and bring it to front.

        Restores the window from hidden state and presents it to the user.
        """
        self.set_visible(True)
        self.present()

    def hide_window(self) -> None:
        """
        Hide the window.

        The window remains in memory but is not visible to the user.
        """
        self.set_visible(False)
