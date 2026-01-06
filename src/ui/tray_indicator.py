# ClamUI Tray Indicator Module
"""
Tray indicator module for ClamUI providing system tray integration.
Uses AyatanaAppIndicator3 for native Linux AppIndicator support.

Note: This module uses GTK3 for menu creation (required by AppIndicator)
while the main application uses GTK4. GTK3 code is isolated to this module.
"""

import logging
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


def _find_clamui_icon() -> str | None:
    """
    Find the ClamUI application icon.

    Searches in common locations for the icon file.

    Returns:
        Absolute path to the icon file, or None if not found
    """
    # Possible icon filenames
    icon_names = ["io.github.Pdzly.ClamUI.svg", "io.github.Pdzly.ClamUI.png"]

    # Search paths relative to this module
    module_dir = Path(__file__).parent
    search_paths = [
        module_dir.parent.parent / "icons",  # src/../icons (development)
        Path("/usr/share/icons/hicolor/scalable/apps"),  # System-wide
        Path("/usr/local/share/icons/hicolor/scalable/apps"),
        Path.home() / ".local/share/icons/hicolor/scalable/apps",
    ]

    for search_path in search_paths:
        for icon_name in icon_names:
            icon_path = search_path / icon_name
            if icon_path.exists():
                logger.debug(f"Found ClamUI icon at: {icon_path}")
                return str(icon_path.absolute())

    logger.debug("ClamUI icon not found, will use theme fallbacks")
    return None


# Cache the icon path
_CLAMUI_ICON_PATH: str | None = None

# Track availability of AppIndicator library
_APPINDICATOR_AVAILABLE = False
_APPINDICATOR_ERROR: str | None = None

# GTK3 imports for AppIndicator (isolated from GTK4 main app)
# These imports are wrapped in try/except to handle missing library gracefully
try:
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("AyatanaAppIndicator3", "0.1")

    from gi.repository import AyatanaAppIndicator3 as AppIndicator
    from gi.repository import Gtk as Gtk3

    _APPINDICATOR_AVAILABLE = True
except ValueError as e:
    # ValueError is raised when GTK version requirements conflict
    # (e.g., GTK4 already loaded, or AyatanaAppIndicator3 not installed)
    _APPINDICATOR_ERROR = f"GTK version conflict: {e}"
    logger.warning(
        f"System tray indicator unavailable: {_APPINDICATOR_ERROR}. Tray features will be disabled."
    )
except ImportError as e:
    # ImportError when gi or required modules are not installed
    _APPINDICATOR_ERROR = f"Missing library: {e}"
    logger.warning(
        f"System tray indicator unavailable: {_APPINDICATOR_ERROR}. "
        "Install libayatana-appindicator3-dev for tray support."
    )


def is_available() -> bool:
    """
    Check if the AppIndicator library is available.

    Returns:
        True if AyatanaAppIndicator3 is available, False otherwise
    """
    return _APPINDICATOR_AVAILABLE


def get_unavailable_reason() -> str | None:
    """
    Get the reason why AppIndicator is unavailable.

    Returns:
        Error message if unavailable, None if available
    """
    return _APPINDICATOR_ERROR


# Default icon size for theme lookups (standard symbolic icon size)
_ICON_SIZE = 24


class TrayIndicator:
    """
    Manager for system tray indicator.

    Provides a persistent tray icon with status awareness,
    right-click menu for quick actions, and window toggle support.
    Uses AyatanaAppIndicator3 for Linux AppIndicator integration.
    """

    # Icon mapping for different protection states
    # Each status has a primary icon that should be used
    ICON_MAP = {
        "protected": "security-high-symbolic",
        "warning": "dialog-warning-symbolic",
        "scanning": "emblem-synchronizing-symbolic",
        "threat": "dialog-error-symbolic",
    }

    # Fallback chains for each status if primary icon not found in theme
    # Each list is ordered by preference: custom app icon -> theme icon -> generic fallback
    ICON_FALLBACKS = {
        "protected": [
            "clamui-protected-symbolic",  # Custom ClamUI icon (if installed)
            "security-high-symbolic",  # Standard security icon
            "emblem-ok-symbolic",  # Generic OK indicator
            "emblem-default-symbolic",  # Very generic fallback
        ],
        "warning": [
            "clamui-warning-symbolic",  # Custom ClamUI icon (if installed)
            "dialog-warning-symbolic",  # Standard warning icon
            "emblem-important-symbolic",  # Alternative warning
            "dialog-information-symbolic",  # Generic info fallback
        ],
        "scanning": [
            "clamui-scanning-symbolic",  # Custom ClamUI icon (if installed)
            "emblem-synchronizing-symbolic",  # Standard sync icon
            "process-working-symbolic",  # Alternative sync/working
            "view-refresh-symbolic",  # Generic refresh fallback
        ],
        "threat": [
            "clamui-threat-symbolic",  # Custom ClamUI icon (if installed)
            "dialog-error-symbolic",  # Standard error icon
            "emblem-unreadable-symbolic",  # Alternative danger icon
            "security-low-symbolic",  # Security-related fallback
        ],
    }

    # Ultimate fallback icon if no icons in chain are found
    DEFAULT_ICON = "security-high-symbolic"

    # Application indicator ID
    INDICATOR_ID = "clamui-tray"

    def __init__(self) -> None:
        """
        Initialize the TrayIndicator.

        Creates an AppIndicator instance with a basic menu.
        The indicator is not visible until activate() is called.

        If AppIndicator library is not available, creates a stub instance
        that logs warnings but doesn't crash the application.
        """
        self._indicator = None
        self._menu = None
        self._current_status: str = "protected"
        self._icon_theme = None
        self._available: bool = _APPINDICATOR_AVAILABLE

        # Action callbacks (set via set_action_callbacks)
        self._on_quick_scan: Callable[[], None] | None = None
        self._on_full_scan: Callable[[], None] | None = None
        self._on_update: Callable[[], None] | None = None
        self._on_quit: Callable[[], None] | None = None

        # Window toggle callback (set via set_window_toggle_callback)
        self._on_window_toggle: Callable[[], None] | None = None
        self._get_window_visible: Callable[[], bool] | None = None
        self._show_window_item = None

        # Create the indicator only if library is available
        if self._available:
            self._create_indicator()
        else:
            logger.info("TrayIndicator created in stub mode (AppIndicator unavailable)")

    def _get_icon_theme(self):
        """
        Get the current GTK icon theme.

        Caches the icon theme instance for efficiency.

        Returns:
            The current Gtk3.IconTheme instance, or None if unavailable
        """
        if not self._available:
            return None
        if self._icon_theme is None:
            self._icon_theme = Gtk3.IconTheme.get_default()
        return self._icon_theme

    def _icon_exists(self, icon_name: str) -> bool:
        """
        Check if an icon exists in the current theme.

        Args:
            icon_name: Name of the icon to check

        Returns:
            True if icon exists in theme, False otherwise
        """
        theme = self._get_icon_theme()
        if theme is None:
            return False
        return theme.has_icon(icon_name)

    def _resolve_icon(self, status: str) -> str:
        """
        Resolve the best available icon for a given status.

        Walks through the fallback chain for the status and returns
        the first icon that exists in the current theme. If no icons
        in the chain are found, returns the DEFAULT_ICON.

        Args:
            status: Protection status ('protected', 'warning', 'scanning', 'threat')

        Returns:
            Icon name that exists in the current theme
        """
        # Get fallback chain for this status
        fallback_chain = self.ICON_FALLBACKS.get(status, [])

        # Check each icon in the fallback chain
        for icon_name in fallback_chain:
            if self._icon_exists(icon_name):
                if icon_name != fallback_chain[0]:
                    logger.debug(f"Using fallback icon '{icon_name}' for status '{status}'")
                return icon_name

        # If no icons in chain found, use the direct ICON_MAP value
        primary_icon = self.ICON_MAP.get(status, self.DEFAULT_ICON)
        if self._icon_exists(primary_icon):
            return primary_icon

        # Ultimate fallback
        if self._icon_exists(self.DEFAULT_ICON):
            logger.warning(
                f"No icons found for status '{status}', using default '{self.DEFAULT_ICON}'"
            )
            return self.DEFAULT_ICON

        # If even DEFAULT_ICON doesn't exist, return it anyway
        # (AppIndicator will handle missing icon gracefully)
        logger.warning(
            f"Default icon '{self.DEFAULT_ICON}' not found in theme, icon may not display"
        )
        return self.DEFAULT_ICON

    def _get_clamui_icon(self) -> str | None:
        """
        Get the ClamUI application icon path.

        Uses cached path or finds the icon on first call.

        Returns:
            Absolute path to the ClamUI icon, or None if not found
        """
        global _CLAMUI_ICON_PATH
        if _CLAMUI_ICON_PATH is None:
            _CLAMUI_ICON_PATH = _find_clamui_icon()
        return _CLAMUI_ICON_PATH

    def _create_indicator(self) -> None:
        """
        Create and configure the AppIndicator instance.

        Uses the ClamUI application icon if found, otherwise falls back
        to theme icons.
        Does nothing if AppIndicator library is not available.
        """
        if not self._available:
            return

        # Try to use the ClamUI icon first, fall back to theme icon
        clamui_icon = self._get_clamui_icon()
        if clamui_icon:
            initial_icon = clamui_icon
            logger.info(f"Using ClamUI icon: {clamui_icon}")
        else:
            initial_icon = self._resolve_icon(self._current_status)
            logger.info(f"Using theme icon: {initial_icon}")

        self._indicator = AppIndicator.Indicator.new(
            self.INDICATOR_ID,
            initial_icon,
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )

        # If using a file path, set the icon theme path for AppIndicator
        if clamui_icon:
            icon_dir = str(Path(clamui_icon).parent)
            self._indicator.set_icon_theme_path(icon_dir)

        # Build initial menu (required before activating)
        self._menu = self._build_menu()
        self._indicator.set_menu(self._menu)

        # Set tooltip/title
        self._indicator.set_title("ClamUI")
        logger.debug(f"Tray indicator created with icon: {initial_icon}")

    def _build_menu(self):
        """
        Build the GTK3 context menu for the indicator.

        Returns:
            GTK3 Menu with action items connected to callbacks,
            or None if AppIndicator is unavailable
        """
        if not self._available:
            return None

        menu = Gtk3.Menu()

        # Show/Hide Window item (at top for easy access)
        self._show_window_item = Gtk3.MenuItem(label="Show Window")
        self._show_window_item.connect("activate", self._on_window_toggle_clicked)
        menu.append(self._show_window_item)

        menu.append(Gtk3.SeparatorMenuItem())

        # Quick Scan item
        quick_scan_item = Gtk3.MenuItem(label="Quick Scan")
        quick_scan_item.connect("activate", self._on_quick_scan_clicked)
        menu.append(quick_scan_item)

        # Full Scan item
        full_scan_item = Gtk3.MenuItem(label="Full Scan")
        full_scan_item.connect("activate", self._on_full_scan_clicked)
        menu.append(full_scan_item)

        menu.append(Gtk3.SeparatorMenuItem())

        # Update Definitions item
        update_item = Gtk3.MenuItem(label="Update Definitions")
        update_item.connect("activate", self._on_update_clicked)
        menu.append(update_item)

        menu.append(Gtk3.SeparatorMenuItem())

        # Quit item
        quit_item = Gtk3.MenuItem(label="Quit")
        quit_item.connect("activate", self._on_quit_clicked)
        menu.append(quit_item)

        # Show all menu items
        menu.show_all()

        return menu

    def _on_window_toggle_clicked(self, menu_item) -> None:
        """Handle Show/Hide Window menu item activation."""
        if self._on_window_toggle:
            self._on_window_toggle()
        else:
            logger.warning("Window toggle callback not set")

    def _on_quick_scan_clicked(self, menu_item) -> None:
        """Handle Quick Scan menu item activation."""
        if self._on_quick_scan:
            self._on_quick_scan()
        else:
            logger.warning("Quick Scan callback not set")

    def _on_full_scan_clicked(self, menu_item) -> None:
        """Handle Full Scan menu item activation."""
        if self._on_full_scan:
            self._on_full_scan()
        else:
            logger.warning("Full Scan callback not set")

    def _on_update_clicked(self, menu_item) -> None:
        """Handle Update Definitions menu item activation."""
        if self._on_update:
            self._on_update()
        else:
            logger.warning("Update callback not set")

    def _on_quit_clicked(self, menu_item) -> None:
        """Handle Quit menu item activation."""
        if self._on_quit:
            self._on_quit()
        else:
            logger.warning("Quit callback not set")

    def set_action_callbacks(
        self,
        on_quick_scan: Callable[[], None] | None = None,
        on_full_scan: Callable[[], None] | None = None,
        on_update: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        """
        Set callbacks for menu actions.

        Args:
            on_quick_scan: Callback for Quick Scan action
            on_full_scan: Callback for Full Scan action
            on_update: Callback for Update Definitions action
            on_quit: Callback for Quit action
        """
        self._on_quick_scan = on_quick_scan
        self._on_full_scan = on_full_scan
        self._on_update = on_update
        self._on_quit = on_quit
        logger.debug("Tray action callbacks configured")

    def set_window_toggle_callback(
        self, on_toggle: Callable[[], None], get_visible: Callable[[], bool]
    ) -> None:
        """
        Set the callback for window show/hide toggle.

        Args:
            on_toggle: Callback to invoke when toggling window visibility
            get_visible: Callback to query current window visibility state
        """
        self._on_window_toggle = on_toggle
        self._get_window_visible = get_visible
        logger.debug("Window toggle callback configured")

    def update_window_menu_label(self) -> None:
        """
        Update the Show/Hide Window menu item label based on current state.

        Call this after window visibility changes to keep menu label in sync.
        """
        if self._show_window_item is None:
            return

        if self._get_window_visible and self._get_window_visible():
            self._show_window_item.set_label("Hide Window")
        else:
            self._show_window_item.set_label("Show Window")

    def activate(self) -> None:
        """
        Activate the indicator to make it visible in the system tray.

        Must be called after initialization for the icon to appear.
        """
        if self._indicator is not None:
            self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            logger.debug("Tray indicator activated")

    def deactivate(self) -> None:
        """
        Deactivate the indicator to hide it from the system tray.
        """
        if self._indicator is not None:
            self._indicator.set_status(AppIndicator.IndicatorStatus.PASSIVE)
            logger.debug("Tray indicator deactivated")

    def update_status(self, status: str) -> None:
        """
        Update the tray icon based on protection status.

        Uses the ClamUI application icon if available, otherwise falls back
        to theme icons for the status.

        Args:
            status: One of 'protected', 'warning', 'scanning', 'threat'
        """
        if self._indicator is None:
            return

        # Validate status and use fallback for unknown values
        if status not in self.ICON_MAP:
            logger.warning(f"Unknown status '{status}', using 'protected'")
            status = "protected"

        tooltip = f"ClamUI - {status.capitalize()}"

        # Use ClamUI icon if available, otherwise use theme icon
        clamui_icon = self._get_clamui_icon()
        if clamui_icon:
            # Use the ClamUI icon - extract icon name without path/extension
            icon_name = Path(clamui_icon).stem
            self._indicator.set_icon_full(icon_name, tooltip)
        else:
            # Fall back to theme icons
            icon_name = self._resolve_icon(status)
            self._indicator.set_icon_full(icon_name, tooltip)

        self._current_status = status
        logger.debug(f"Tray status updated to: {status} (icon: {icon_name})")

    def update_scan_progress(self, percentage: int) -> None:
        """
        Show scan progress percentage in the tray.

        Args:
            percentage: Progress percentage (0-100). Use 0 to clear.
        """
        if self._indicator is None:
            return

        if 0 < percentage <= 100:
            self._indicator.set_label(f"{percentage}%", "")
            # Update icon to scanning state if not already
            if self._current_status != "scanning":
                self.update_status("scanning")
        else:
            # Clear the label when not scanning
            self._indicator.set_label("", "")

    def cleanup(self) -> None:
        """
        Clean up resources and remove the indicator from tray.

        Should be called before application exit to prevent ghost icons.
        Clears all references to prevent circular reference leaks.
        """
        # Deactivate first to hide the icon immediately
        self.deactivate()

        # Clear action callbacks to break circular references
        self._on_quick_scan = None
        self._on_full_scan = None
        self._on_update = None
        self._on_quit = None

        # Clear window toggle callbacks
        self._on_window_toggle = None
        self._get_window_visible = None
        self._show_window_item = None

        # Clear GTK resources
        self._menu = None
        self._indicator = None
        self._icon_theme = None

        logger.debug("Tray indicator cleaned up")

    @property
    def is_active(self) -> bool:
        """
        Check if the indicator is currently visible.

        Returns:
            True if indicator is active, False otherwise.
            Always returns False if AppIndicator is unavailable.
        """
        if not self._available or self._indicator is None:
            return False
        return self._indicator.get_status() == AppIndicator.IndicatorStatus.ACTIVE

    @property
    def is_library_available(self) -> bool:
        """
        Check if the AppIndicator library is available.

        Returns:
            True if AyatanaAppIndicator3 is available, False otherwise
        """
        return self._available

    @property
    def current_status(self) -> str:
        """
        Get the current protection status.

        Returns:
            Current status string ('protected', 'warning', 'scanning', 'threat')
        """
        return self._current_status
