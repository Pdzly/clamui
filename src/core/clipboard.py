# ClamUI Clipboard Operations
"""
Clipboard operations for ClamUI.

This module provides functions for:
- Copying text to the system clipboard using GTK4 clipboard API
- Supporting both regular desktop and Flatpak environments
"""


def copy_to_clipboard(text: str) -> bool:
    """
    Copy text to the system clipboard using GTK 4 clipboard API.

    Uses the default display's clipboard to copy text content.
    This works in both regular desktop and Flatpak environments.

    Args:
        text: The text content to copy to the clipboard

    Returns:
        True if the text was successfully copied, False otherwise

    Example:
        >>> copy_to_clipboard("Hello, World!")
        True

        >>> copy_to_clipboard("")
        False
    """
    if not text:
        return False

    try:
        # Import GTK/GDK for clipboard access
        import gi

        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk

        # Get the default display
        display = Gdk.Display.get_default()
        if display is None:
            return False

        # Get the clipboard
        clipboard = display.get_clipboard()
        if clipboard is None:
            return False

        # Set the text content
        clipboard.set(text)

        return True

    except Exception:
        return False
