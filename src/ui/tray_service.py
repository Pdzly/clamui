#!/usr/bin/env python3
# ClamUI Tray Service - Subprocess Script
"""
Standalone tray indicator service that runs in a separate subprocess.

This script MUST be run as a separate Python process to avoid GTK3/GTK4
version conflicts. It loads GTK3 first (required by AyatanaAppIndicator3)
and communicates with the main GTK4 application via JSON messages on stdin/stdout.

Protocol:
- Input (stdin): JSON commands like {"action": "update_status", "status": "scanning"}
- Output (stdout): JSON responses like {"event": "menu_action", "action": "quick_scan"}

Usage:
    python -m src.ui.tray_service
"""

import json
import logging
import os
import sys
import threading
from typing import Optional

# Configure logging to stderr (stdout is used for IPC)
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("CLAMUI_DEBUG") else logging.INFO,
    format="[TrayService] %(levelname)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# GTK3 imports MUST happen before any GTK4 contamination
# This is why this runs in a separate subprocess
try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
    from gi.repository import Gtk as Gtk3
    from gi.repository import GLib
    APPINDICATOR_AVAILABLE = True
    logger.info("AyatanaAppIndicator3 loaded successfully")
except (ValueError, ImportError) as e:
    logger.error(f"Failed to load AppIndicator: {e}")
    APPINDICATOR_AVAILABLE = False
    # Exit with error - the main app should handle this
    print(json.dumps({"event": "error", "message": str(e)}), flush=True)
    sys.exit(1)


class TrayService:
    """
    System tray indicator service.

    Runs in a separate subprocess with GTK3 and communicates
    with the main GTK4 application via JSON IPC.
    """

    # Icon mapping for different protection states
    ICON_MAP = {
        "protected": "security-high-symbolic",
        "warning": "dialog-warning-symbolic",
        "scanning": "emblem-synchronizing-symbolic",
        "threat": "dialog-error-symbolic",
    }

    # Fallback chains for each status
    ICON_FALLBACKS = {
        "protected": [
            "clamui-protected-symbolic",
            "security-high-symbolic",
            "emblem-ok-symbolic",
            "emblem-default-symbolic",
        ],
        "warning": [
            "clamui-warning-symbolic",
            "dialog-warning-symbolic",
            "emblem-important-symbolic",
            "dialog-information-symbolic",
        ],
        "scanning": [
            "clamui-scanning-symbolic",
            "emblem-synchronizing-symbolic",
            "process-working-symbolic",
            "view-refresh-symbolic",
        ],
        "threat": [
            "clamui-threat-symbolic",
            "dialog-error-symbolic",
            "emblem-unreadable-symbolic",
            "security-low-symbolic",
        ],
    }

    DEFAULT_ICON = "security-high-symbolic"
    INDICATOR_ID = "clamui-tray"

    def __init__(self):
        """Initialize the tray service."""
        self._indicator: Optional[AppIndicator.Indicator] = None
        self._menu: Optional[Gtk3.Menu] = None
        self._current_status = "protected"
        self._icon_theme: Optional[Gtk3.IconTheme] = None
        self._window_visible = True
        self._show_window_item: Optional[Gtk3.MenuItem] = None
        self._running = True

        # Create indicator
        self._create_indicator()

    def _get_icon_theme(self) -> Gtk3.IconTheme:
        """Get the current GTK icon theme."""
        if self._icon_theme is None:
            self._icon_theme = Gtk3.IconTheme.get_default()
        return self._icon_theme

    def _icon_exists(self, icon_name: str) -> bool:
        """Check if an icon exists in the current theme."""
        theme = self._get_icon_theme()
        return theme.has_icon(icon_name)

    def _resolve_icon(self, status: str) -> str:
        """Resolve the best available icon for a given status."""
        fallback_chain = self.ICON_FALLBACKS.get(status, [])

        for icon_name in fallback_chain:
            if self._icon_exists(icon_name):
                return icon_name

        primary_icon = self.ICON_MAP.get(status, self.DEFAULT_ICON)
        if self._icon_exists(primary_icon):
            return primary_icon

        return self.DEFAULT_ICON

    def _create_indicator(self) -> None:
        """Create and configure the AppIndicator instance."""
        initial_icon = self._resolve_icon(self._current_status)

        self._indicator = AppIndicator.Indicator.new(
            self.INDICATOR_ID,
            initial_icon,
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )

        # Build menu
        self._menu = self._build_menu()
        self._indicator.set_menu(self._menu)

        # Set tooltip/title
        self._indicator.set_title("ClamUI")

        # Activate to show icon
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        logger.info(f"Tray indicator created with icon: {initial_icon}")

    def _build_menu(self) -> Gtk3.Menu:
        """Build the GTK3 context menu."""
        menu = Gtk3.Menu()

        # Show/Hide Window
        self._show_window_item = Gtk3.MenuItem(label="Hide Window")
        self._show_window_item.connect("activate", self._on_toggle_window)
        menu.append(self._show_window_item)

        menu.append(Gtk3.SeparatorMenuItem())

        # Quick Scan
        quick_scan_item = Gtk3.MenuItem(label="Quick Scan")
        quick_scan_item.connect("activate", lambda w: self._send_action("quick_scan"))
        menu.append(quick_scan_item)

        # Full Scan
        full_scan_item = Gtk3.MenuItem(label="Full Scan")
        full_scan_item.connect("activate", lambda w: self._send_action("full_scan"))
        menu.append(full_scan_item)

        menu.append(Gtk3.SeparatorMenuItem())

        # Update Definitions
        update_item = Gtk3.MenuItem(label="Update Definitions")
        update_item.connect("activate", lambda w: self._send_action("update"))
        menu.append(update_item)

        menu.append(Gtk3.SeparatorMenuItem())

        # Quit
        quit_item = Gtk3.MenuItem(label="Quit")
        quit_item.connect("activate", lambda w: self._send_action("quit"))
        menu.append(quit_item)

        menu.show_all()
        return menu

    def _on_toggle_window(self, widget) -> None:
        """Handle window toggle menu item."""
        self._send_action("toggle_window")

    def _send_action(self, action: str) -> None:
        """Send an action event to the main application."""
        message = {"event": "menu_action", "action": action}
        self._send_message(message)

    def _send_message(self, message: dict) -> None:
        """Send a JSON message to stdout."""
        try:
            print(json.dumps(message), flush=True)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    def update_status(self, status: str) -> None:
        """Update the tray icon based on protection status."""
        if self._indicator is None:
            return

        if status not in self.ICON_MAP:
            logger.warning(f"Unknown status '{status}', using 'protected'")
            status = "protected"

        icon_name = self._resolve_icon(status)
        tooltip = f"ClamUI - {status.capitalize()}"

        self._indicator.set_icon_full(icon_name, tooltip)
        self._current_status = status
        logger.debug(f"Status updated to: {status}")

    def update_progress(self, percentage: int) -> None:
        """Show scan progress percentage."""
        if self._indicator is None:
            return

        if 0 < percentage <= 100:
            self._indicator.set_label(f"{percentage}%", "")
        else:
            self._indicator.set_label("", "")

    def update_window_visible(self, visible: bool) -> None:
        """Update window visibility state and menu label."""
        self._window_visible = visible
        if self._show_window_item:
            label = "Hide Window" if visible else "Show Window"
            self._show_window_item.set_label(label)

    def handle_command(self, command: dict) -> None:
        """Handle a command from the main application."""
        action = command.get("action")

        if action == "update_status":
            status = command.get("status", "protected")
            GLib.idle_add(self.update_status, status)

        elif action == "update_progress":
            percentage = command.get("percentage", 0)
            GLib.idle_add(self.update_progress, percentage)

        elif action == "update_window_visible":
            visible = command.get("visible", True)
            GLib.idle_add(self.update_window_visible, visible)

        elif action == "quit":
            logger.info("Received quit command")
            GLib.idle_add(self._quit)

        elif action == "ping":
            self._send_message({"event": "pong"})

        else:
            logger.warning(f"Unknown command: {action}")

    def _quit(self) -> None:
        """Quit the service."""
        self._running = False
        if self._indicator:
            self._indicator.set_status(AppIndicator.IndicatorStatus.PASSIVE)
        Gtk3.main_quit()

    def run(self) -> None:
        """Run the tray service main loop."""
        # Send ready event
        self._send_message({"event": "ready"})

        # Start stdin reader thread
        reader_thread = threading.Thread(target=self._read_stdin, daemon=True)
        reader_thread.start()

        # Run GTK main loop
        logger.info("Starting GTK main loop")
        Gtk3.main()
        logger.info("GTK main loop ended")

    def _read_stdin(self) -> None:
        """Read commands from stdin in a background thread."""
        try:
            for line in sys.stdin:
                if not self._running:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    command = json.loads(line)
                    self.handle_command(command)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")

        except Exception as e:
            logger.error(f"Error reading stdin: {e}")
        finally:
            # If stdin closes, quit the service
            GLib.idle_add(self._quit)


def main():
    """Main entry point for the tray service."""
    if not APPINDICATOR_AVAILABLE:
        logger.error("AppIndicator not available, exiting")
        sys.exit(1)

    try:
        service = TrayService()
        service.run()
    except Exception as e:
        logger.error(f"Tray service error: {e}")
        print(json.dumps({"event": "error", "message": str(e)}), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
