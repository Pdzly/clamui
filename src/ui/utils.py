"""UI utility functions for ClamUI."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


def add_row_icon(row: Adw.ActionRow | Adw.ExpanderRow, icon_name: str) -> Gtk.Image:
    """
    Add an icon to an ActionRow or ExpanderRow as a prefix widget.

    This is the modern replacement for the deprecated set_icon_name() method
    which was deprecated in libadwaita 1.3.

    Args:
        row: The ActionRow or ExpanderRow to add the icon to
        icon_name: The symbolic icon name (e.g., "folder-symbolic")

    Returns:
        The Gtk.Image widget, useful for dynamic icon updates
    """
    icon = Gtk.Image.new_from_icon_name(icon_name)
    row.add_prefix(icon)
    return icon
