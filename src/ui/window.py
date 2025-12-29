# ClamUI Main Window
"""
Main application window for ClamUI.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio


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

        # Set window properties
        self.set_title("ClamUI")
        self.set_default_size(800, 700)
        self.set_size_request(400, 700)  # Minimum size to keep ClamAV status bar visible

        # Create the main layout
        self._setup_ui()

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

        return nav_box

    def set_active_view(self, view_name: str):
        """
        Update the navigation button states based on the active view.

        Args:
            view_name: The name of the active view ('scan', 'update', or 'logs')
        """
        if view_name == "scan":
            self._scan_button.set_active(True)
            self._database_button.set_active(False)
            self._logs_button.set_active(False)
        elif view_name == "update":
            self._scan_button.set_active(False)
            self._database_button.set_active(True)
            self._logs_button.set_active(False)
        elif view_name == "logs":
            self._scan_button.set_active(False)
            self._database_button.set_active(False)
            self._logs_button.set_active(True)

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
