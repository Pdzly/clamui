# ClamUI Main Window
"""
Main application window for ClamUI.
"""

import logging
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .close_behavior_dialog import CloseBehaviorDialog
from .utils import resolve_icon_name

if TYPE_CHECKING:
    pass

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
        self.set_default_size(800, 800)
        self.set_size_request(
            400, 400
        )  # Minimum size - height reduced to fix maximize button on Ubuntu

        # Set up minimize-to-tray handling
        self._setup_minimize_to_tray()

        # Create the main layout
        self._setup_ui()

    def _setup_minimize_to_tray(self) -> None:
        """
        Set up minimize-to-tray and close-to-tray functionality.

        Connects to window state changes to detect minimize events.
        When minimize_to_tray setting is enabled and tray is available,
        the window will hide to tray instead of minimizing to taskbar.

        Also connects to close-request to handle close-to-tray behavior.
        """
        # Track if we're handling minimize-to-tray to prevent recursion
        self._handling_minimize = False

        # Track if a close behavior dialog is currently shown
        self._close_dialog_pending = False

        # Connect to the window's surface to detect state changes
        # We need to do this after the window is realized
        self.connect("realize", self._on_window_realized)

        # Connect to close-request to handle close-to-tray behavior
        self.connect("close-request", self._on_close_request)

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
        if state & Gdk.ToplevelState.MINIMIZED and self._should_minimize_to_tray():
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
        if not hasattr(self._application, "settings_manager"):
            return False

        settings = self._application.settings_manager
        if settings is None:
            return False

        # Check if minimize_to_tray is enabled
        if not settings.get("minimize_to_tray", False):
            return False

        # Check if tray indicator is available
        if not hasattr(self._application, "tray_indicator"):
            return False

        tray = self._application.tray_indicator
        return tray is not None

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
        if hasattr(self._application, "tray_indicator"):
            tray = self._application.tray_indicator
            if tray is not None and hasattr(tray, "update_window_menu_label"):
                tray.update_window_menu_label()

        return False  # Remove from idle queue

    def _on_close_request(self, window) -> bool:
        """
        Handle window close request.

        Depending on the close_behavior setting:
        - None (unset): Show dialog to ask user
        - "ask": Show dialog every time
        - "minimize": Hide to tray
        - "quit": Allow normal close

        Args:
            window: The window requesting close

        Returns:
            True to prevent close, False to allow close
        """
        # If tray is not available, always allow normal close
        if not self._is_tray_available():
            logger.debug("Tray not available, allowing normal close")
            return False

        # If a dialog is already pending, prevent additional close requests
        if self._close_dialog_pending:
            return True

        # Get the close behavior setting
        close_behavior = self._get_close_behavior()

        if close_behavior == "minimize":
            # Hide to tray
            self._do_close_to_tray()
            return True  # Prevent close

        if close_behavior == "quit":
            # Allow normal close
            return False

        # close_behavior is None (first run) or "ask" - show dialog
        self._show_close_behavior_dialog()
        return True  # Prevent close while dialog is shown

    def _is_tray_available(self) -> bool:
        """
        Check if system tray is available.

        Returns:
            True if tray indicator is available and active
        """
        if not hasattr(self._application, "tray_indicator"):
            return False

        tray = self._application.tray_indicator
        return tray is not None

    def _get_close_behavior(self) -> str | None:
        """
        Get the current close behavior setting.

        Returns:
            "minimize", "quit", "ask", or None if not set
        """
        if not hasattr(self._application, "settings_manager"):
            return None

        settings = self._application.settings_manager
        if settings is None:
            return None

        return settings.get("close_behavior", None)

    def _do_close_to_tray(self) -> None:
        """
        Hide the window to the system tray.

        Similar to minimize-to-tray but triggered by close action.
        """
        self.hide_window()

        logger.debug("Window closed to tray")

        # Update tray menu label
        if hasattr(self._application, "tray_indicator"):
            tray = self._application.tray_indicator
            if tray is not None and hasattr(tray, "update_window_menu_label"):
                tray.update_window_menu_label(visible=False)

    def _show_close_behavior_dialog(self) -> None:
        """
        Show the close behavior dialog.

        Presents a dialog asking the user whether to minimize to tray
        or quit completely, with an option to remember the choice.
        """
        self._close_dialog_pending = True

        dialog = CloseBehaviorDialog(callback=self._on_close_behavior_dialog_response)
        dialog.set_transient_for(self)
        dialog.present()

    def _on_close_behavior_dialog_response(
        self, choice: str | None, remember: bool
    ) -> None:
        """
        Handle the close behavior dialog response.

        Args:
            choice: "minimize", "quit", or None if dismissed
            remember: True if user wants to save their choice
        """
        self._close_dialog_pending = False

        if choice is None:
            # User dismissed dialog without choosing - do nothing
            logger.debug("Close dialog dismissed without choice")
            return

        # Save preference if "Remember my choice" was checked
        if remember and hasattr(self._application, "settings_manager"):
            settings = self._application.settings_manager
            if settings is not None:
                settings.set("close_behavior", choice)
                logger.info(f"Saved close behavior preference: {choice}")

        # Execute the chosen action
        if choice == "minimize":
            self._do_close_to_tray()
        elif choice == "quit":
            # Actually quit the application
            self._application.quit()

    def _setup_ui(self):
        """Set up the window UI layout."""
        # Create the header bar
        header_bar = self._create_header_bar()

        # Create the content area
        self._content_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._content_area.set_vexpand(True)
        self._content_area.set_hexpand(True)

        # Add toast overlay for in-app notifications
        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(self._content_area)

        # Use ToolbarView to properly integrate the HeaderBar as a titlebar
        # This makes window control buttons (minimize, maximize, close) functional
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        toolbar_view.set_content(self._toast_overlay)

        self.set_content(toolbar_view)

        # Show placeholder content (will be replaced with ScanView in integration)
        self._show_placeholder()

    def _create_header_bar(self) -> Adw.HeaderBar:
        """
        Create the application header bar.

        Returns:
            Configured Adw.HeaderBar
        """
        header_bar = Adw.HeaderBar()

        # Enable window control buttons (minimize, maximize, close)
        # Start buttons for systems with left-side window controls (e.g., Ubuntu)
        header_bar.set_show_start_title_buttons(True)
        header_bar.set_show_end_title_buttons(True)

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
        self._scan_button.set_icon_name(resolve_icon_name("folder-symbolic"))
        self._scan_button.set_tooltip_text("Scan Files (Ctrl+1)")
        self._scan_button.set_active(True)
        self._scan_button.set_action_name("app.show-scan")
        nav_box.append(self._scan_button)

        # Database update button
        self._database_button = Gtk.ToggleButton()
        self._database_button.set_icon_name(
            resolve_icon_name("software-update-available-symbolic")
        )
        self._database_button.set_tooltip_text("Update Database (Ctrl+2)")
        self._database_button.set_action_name("app.show-update")
        nav_box.append(self._database_button)

        # Logs button
        self._logs_button = Gtk.ToggleButton()
        self._logs_button.set_icon_name(
            resolve_icon_name("document-open-recent-symbolic")
        )
        self._logs_button.set_tooltip_text("View Logs (Ctrl+3)")
        self._logs_button.set_action_name("app.show-logs")
        nav_box.append(self._logs_button)

        # Components button
        self._components_button = Gtk.ToggleButton()
        self._components_button.set_icon_name(
            resolve_icon_name("applications-system-symbolic")
        )
        self._components_button.set_tooltip_text("ClamAV Components (Ctrl+4)")
        self._components_button.set_action_name("app.show-components")
        nav_box.append(self._components_button)

        # Quarantine button
        self._quarantine_button = Gtk.ToggleButton()
        self._quarantine_button.set_icon_name(
            resolve_icon_name("security-medium-symbolic")
        )
        self._quarantine_button.set_tooltip_text("Quarantine (Ctrl+5)")
        self._quarantine_button.set_action_name("app.show-quarantine")
        nav_box.append(self._quarantine_button)

        # Statistics button
        self._statistics_button = Gtk.ToggleButton()
        self._statistics_button.set_icon_name(
            resolve_icon_name("applications-science-symbolic")
        )
        self._statistics_button.set_tooltip_text("Statistics Dashboard (Ctrl+6)")
        self._statistics_button.set_action_name("app.show-statistics")
        nav_box.append(self._statistics_button)

        return nav_box

    def set_active_view(self, view_name: str):
        """
        Update the navigation button states based on the active view.

        Args:
            view_name: The name of the active view ('scan', 'update', 'logs', 'components', 'statistics' or 'quarantine')
        """
        if view_name == "scan":
            self._scan_button.set_active(True)
            self._database_button.set_active(False)
            self._logs_button.set_active(False)
            self._components_button.set_active(False)
            self._quarantine_button.set_active(False)
            self._statistics_button.set_active(False)
        elif view_name == "update":
            self._scan_button.set_active(False)
            self._database_button.set_active(True)
            self._logs_button.set_active(False)
            self._components_button.set_active(False)
            self._quarantine_button.set_active(False)
            self._statistics_button.set_active(False)
        elif view_name == "logs":
            self._scan_button.set_active(False)
            self._database_button.set_active(False)
            self._logs_button.set_active(True)
            self._components_button.set_active(False)
            self._statistics_button.set_active(False)
            self._quarantine_button.set_active(False)
        elif view_name == "components":
            self._scan_button.set_active(False)
            self._database_button.set_active(False)
            self._logs_button.set_active(False)
            self._components_button.set_active(True)
            self._quarantine_button.set_active(False)
            self._statistics_button.set_active(False)
        elif view_name == "quarantine":
            self._scan_button.set_active(False)
            self._database_button.set_active(False)
            self._logs_button.set_active(False)
            self._components_button.set_active(False)
            self._quarantine_button.set_active(True)
            self._statistics_button.set_active(False)
        elif view_name == "statistics":
            self._scan_button.set_active(False)
            self._database_button.set_active(False)
            self._logs_button.set_active(False)
            self._components_button.set_active(False)
            self._statistics_button.set_active(True)
            self._quarantine_button.set_active(False)

    def _create_menu_button(self) -> Gtk.MenuButton:
        """
        Create the primary menu button.

        Returns:
            Configured Gtk.MenuButton
        """
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name(resolve_icon_name("open-menu-symbolic"))
        menu_button.set_tooltip_text("Menu (F10)")

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
        placeholder.set_icon_name(resolve_icon_name("security-high-symbolic"))
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

    def add_toast(self, toast: Adw.Toast) -> None:
        """
        Add a toast notification to the window.

        Args:
            toast: The Adw.Toast instance to display
        """
        self._toast_overlay.add_toast(toast)

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
