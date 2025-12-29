# ClamUI Application
"""
Main Adwaita Application class for ClamUI.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

from .ui.window import MainWindow
from .ui.scan_view import ScanView
from .ui.update_view import UpdateView
from .ui.logs_view import LogsView


class ClamUIApp(Adw.Application):
    """
    ClamUI GTK4/Adwaita Application.

    This is the main application class that handles application lifecycle,
    window management, and global application state.
    """

    def __init__(self):
        """Initialize the ClamUI application."""
        super().__init__(
            application_id="com.github.clamui",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

        # Application metadata
        self._app_name = "ClamUI"
        self._version = "0.1.0"

        # View management
        self._scan_view = None
        self._update_view = None
        self._logs_view = None
        self._current_view = None

    @property
    def app_name(self) -> str:
        """Get the application name."""
        return self._app_name

    @property
    def version(self) -> str:
        """Get the application version."""
        return self._version

    def do_activate(self):
        """
        Handle application activation.

        This method is called when the application is activated (launched).
        It creates and presents the main window with the scan interface.
        """
        # Get existing window or create new one
        win = self.props.active_window

        if not win:
            # Create the main window
            win = MainWindow(application=self)

            # Create all views (kept in memory for state preservation)
            self._scan_view = ScanView()
            self._update_view = UpdateView()
            self._logs_view = LogsView()

            # Set the scan view as the default content
            win.set_content_view(self._scan_view)
            win.set_active_view("scan")
            self._current_view = "scan"

        win.present()

    def do_startup(self):
        """
        Handle application startup.

        This method is called when the application first starts.
        It's used for one-time initialization that should happen
        before any windows are created.
        """
        Adw.Application.do_startup(self)

        # Set up application actions
        self._setup_actions()

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

        # View switching actions
        show_scan_action = Gio.SimpleAction.new("show-scan", None)
        show_scan_action.connect("activate", self._on_show_scan)
        self.add_action(show_scan_action)

        show_update_action = Gio.SimpleAction.new("show-update", None)
        show_update_action.connect("activate", self._on_show_update)
        self.add_action(show_update_action)

        show_logs_action = Gio.SimpleAction.new("show-logs", None)
        show_logs_action.connect("activate", self._on_show_logs)
        self.add_action(show_logs_action)

    def _on_quit(self, action, param):
        """Handle quit action."""
        self.quit()

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
