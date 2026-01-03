#!/usr/bin/env python3
# ClamUI Tray Service - Subprocess Script
"""
Standalone tray indicator service that runs in a separate subprocess.

This script MUST be run as a separate Python process to avoid GTK3/GTK4
version conflicts. It loads GTK3 first (required by AyatanaAppIndicator3)
and communicates with the main GTK4 application via JSON messages on stdin/stdout.

For detailed architecture documentation including process boundaries, IPC protocol,
threading model, and sequence diagrams, see: docs/architecture/tray-subprocess.md

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
from pathlib import Path

# Configure logging to stderr (stdout is used for IPC)
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("CLAMUI_DEBUG") else logging.INFO,
    format="[TrayService] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# GTK3 imports MUST happen before any GTK4 contamination
# This is why this runs in a separate subprocess
APPINDICATOR_AVAILABLE = False
AppIndicator = None

try:
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib
    from gi.repository import Gtk as Gtk3

    # Try AyatanaAppIndicator3 first (newer), then AppIndicator3 (legacy)
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppIndicator

        APPINDICATOR_AVAILABLE = True
        logger.info("AyatanaAppIndicator3 loaded successfully")
    except (ValueError, ImportError):
        try:
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3 as AppIndicator

            APPINDICATOR_AVAILABLE = True
            logger.info("AppIndicator3 (legacy) loaded successfully")
        except (ValueError, ImportError) as e:
            logger.error(f"No AppIndicator library available: {e}")

except (ValueError, ImportError) as e:
    logger.error(f"Failed to load GTK3: {e}")

if not APPINDICATOR_AVAILABLE:
    print(
        json.dumps({"event": "error", "message": "No AppIndicator library available"}), flush=True
    )
    sys.exit(1)

# Import tray icon generator (after GTK3 loads successfully)
CUSTOM_ICONS_AVAILABLE = False
TrayIconGenerator = None
find_clamui_base_icon = None
get_tray_icon_cache_dir = None

# Try to import tray_icons - handles both module and standalone script execution
# When running as a standalone script, we can't use relative imports and must
# avoid importing src.ui (which loads GTK4 views and conflicts with GTK3)
try:
    try:
        # Try relative import first (when run as a module)
        from .tray_icons import (
            TrayIconGenerator,
            find_clamui_base_icon,
            get_tray_icon_cache_dir,
        )
        from .tray_icons import (
            is_available as icons_available,
        )
    except ImportError:
        # Running as standalone script - import tray_icons directly from same directory
        # to avoid triggering src/ui/__init__.py which imports GTK4 views
        import importlib.util

        tray_icons_path = Path(__file__).parent / "tray_icons.py"
        spec = importlib.util.spec_from_file_location("tray_icons", tray_icons_path)
        tray_icons_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tray_icons_module)
        TrayIconGenerator = tray_icons_module.TrayIconGenerator
        find_clamui_base_icon = tray_icons_module.find_clamui_base_icon
        get_tray_icon_cache_dir = tray_icons_module.get_tray_icon_cache_dir
        icons_available = tray_icons_module.is_available

    CUSTOM_ICONS_AVAILABLE = icons_available()
    if CUSTOM_ICONS_AVAILABLE:
        logger.info("Custom tray icon generation available")
    else:
        logger.info("Custom tray icons not available (PIL or base icon missing)")
except Exception as e:
    logger.warning(f"Could not import tray_icons module: {e}")


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
        self._indicator: AppIndicator.Indicator | None = None
        self._menu: Gtk3.Menu | None = None
        self._current_status = "protected"
        self._icon_theme: Gtk3.IconTheme | None = None
        self._window_visible = True
        self._show_window_item: Gtk3.MenuItem | None = None
        self._running = True

        # Profile menu state
        self._profiles: list[dict] = []
        self._profiles_menu: Gtk3.Menu | None = None
        self._profiles_menu_item: Gtk3.MenuItem | None = None
        self._current_profile_id: str | None = None

        # Custom icon generator
        self._icon_generator: TrayIconGenerator | None = None
        self._icon_cache_dir: str | None = None
        self._using_custom_icons = False

        # Set up custom icons if available
        self._setup_custom_icons()

        # Create indicator
        self._create_indicator()

    def _setup_custom_icons(self) -> None:
        """Set up custom ClamUI icon generation."""
        if not CUSTOM_ICONS_AVAILABLE:
            logger.debug("Custom icons not available, using theme icons")
            return

        base_icon = find_clamui_base_icon()
        if not base_icon:
            logger.info("ClamUI base icon not found, using theme icons")
            return

        try:
            self._icon_cache_dir = get_tray_icon_cache_dir()
            self._icon_generator = TrayIconGenerator(base_icon, self._icon_cache_dir)

            # Pre-generate all status icons for responsiveness
            self._icon_generator.pregenerate_all()

            self._using_custom_icons = True
            logger.info("Custom tray icons enabled")
            logger.info(f"  Icon dir: {self._icon_cache_dir}")
        except Exception as e:
            logger.warning(f"Failed to set up custom icons: {e}, using theme icons")
            self._using_custom_icons = False
            self._icon_generator = None

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
        if self._using_custom_icons and self._icon_generator:
            # Use custom generated icon with ClamUI logo
            # Generate the icon first to ensure it exists
            icon_path = self._icon_generator.get_icon_path(self._current_status)
            icon_name = self._icon_generator.get_icon_name(self._current_status)

            # Create indicator with the custom icon
            # Icons are in ~/.local/share/icons/hicolor/ which is in GTK3's search path
            self._indicator = AppIndicator.Indicator.new(
                self.INDICATOR_ID,
                icon_name,  # GTK3 will find this in XDG icon directories
                AppIndicator.IndicatorCategory.APPLICATION_STATUS,
            )

            logger.info(f"Tray indicator created with custom icon: {icon_name}")
            logger.info(f"  Icon file: {icon_path}")
        else:
            # Fall back to theme icons
            initial_icon = self._resolve_icon(self._current_status)

            self._indicator = AppIndicator.Indicator.new(
                self.INDICATOR_ID,
                initial_icon,
                AppIndicator.IndicatorCategory.APPLICATION_STATUS,
            )
            logger.info(f"Tray indicator created with theme icon: {initial_icon}")

        # Build menu
        self._menu = self._build_menu()
        self._indicator.set_menu(self._menu)

        # Set tooltip/title
        self._indicator.set_title("ClamUI")

        # Activate to show icon
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

    def _build_menu(self) -> Gtk3.Menu:
        """Build the GTK3 context menu."""
        menu = Gtk3.Menu()

        # Show/Hide Window
        self._show_window_item = Gtk3.MenuItem(label="Hide Window")
        self._show_window_item.connect("activate", self._on_toggle_window)
        menu.append(self._show_window_item)

        menu.append(Gtk3.SeparatorMenuItem())

        # Profiles submenu
        self._profiles_menu_item = Gtk3.MenuItem(label="Profiles")
        self._profiles_menu = self._build_profiles_menu()
        self._profiles_menu_item.set_submenu(self._profiles_menu)
        menu.append(self._profiles_menu_item)

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

    def _build_profiles_menu(self) -> Gtk3.Menu:
        """Build the profiles submenu."""
        menu = Gtk3.Menu()

        if not self._profiles:
            # Show placeholder when no profiles loaded
            no_profiles_item = Gtk3.MenuItem(label="(No profiles)")
            no_profiles_item.set_sensitive(False)
            menu.append(no_profiles_item)
        else:
            # Add each profile as a menu item
            for profile in self._profiles:
                profile_id = profile.get("id", "")
                profile_name = profile.get("name", "Unknown")
                is_default = profile.get("is_default", False)

                # Add indicator for default profiles
                label = f"• {profile_name}" if is_default else profile_name

                # Mark currently selected profile
                if profile_id == self._current_profile_id:
                    label = f"✓ {profile_name}"

                item = Gtk3.MenuItem(label=label)
                # Use a closure to capture profile_id properly
                item.connect("activate", lambda w, pid=profile_id: self._on_profile_selected(pid))
                menu.append(item)

        menu.show_all()
        return menu

    def _on_profile_selected(self, profile_id: str) -> None:
        """Handle profile selection from menu."""
        self._current_profile_id = profile_id
        message = {"event": "menu_action", "action": "select_profile", "profile_id": profile_id}
        self._send_message(message)
        # Rebuild menu to update checkmark
        self._rebuild_profiles_menu()

    def _rebuild_profiles_menu(self) -> None:
        """Rebuild the profiles submenu to reflect current state."""
        if self._profiles_menu_item is None:
            return

        # Build new submenu
        new_menu = self._build_profiles_menu()
        self._profiles_menu = new_menu
        self._profiles_menu_item.set_submenu(new_menu)

    def update_profiles(self, profiles: list[dict], current_profile_id: str | None = None) -> None:
        """Update the profiles list in the tray menu."""
        self._profiles = profiles
        if current_profile_id is not None:
            self._current_profile_id = current_profile_id
        self._rebuild_profiles_menu()
        logger.debug(f"Updated profiles: {len(profiles)} profiles")

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

        tooltip = f"ClamUI - {status.capitalize()}"

        if self._using_custom_icons and self._icon_generator:
            # Use custom generated icon with ClamUI logo
            self._icon_generator.get_icon_path(status)  # Ensure icon exists
            icon_name = self._icon_generator.get_icon_name(status)
            self._indicator.set_icon_full(icon_name, tooltip)
        else:
            # Fall back to theme icons
            icon_name = self._resolve_icon(status)
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

        elif action == "update_profiles":
            profiles = command.get("profiles", [])
            current_profile_id = command.get("current_profile_id")
            GLib.idle_add(self.update_profiles, profiles, current_profile_id)

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
