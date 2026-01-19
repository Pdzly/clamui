# ClamUI Preferences Base Module
"""
Shared base classes and utility functions for preference pages.

This module provides a mixin class with common functionality used across
all preference pages, including dialog helpers, permission indicators,
and file location displays.
"""

import os
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


def populate_bool_field(config, widgets_dict: dict, key: str, default: bool = False) -> None:
    """
    Populate a boolean switch widget from config.

    Args:
        config: Parsed config object with has_key() and get_value() methods
        widgets_dict: Dictionary containing widget references
        key: Config key name (widget key must match)
        default: Default value if key is missing (False = "no", True = "yes")
    """
    if config.has_key(key):
        value = config.get_value(key)
        is_yes = value.lower() == "yes" if value else False
        widgets_dict[key].set_active(is_yes)
    else:
        # Key missing - use default value
        widgets_dict[key].set_active(default)


def populate_int_field(config, widgets_dict: dict, key: str) -> None:
    """
    Populate an integer spin row widget from config.

    Args:
        config: Parsed config object with has_key() and get_value() methods
        widgets_dict: Dictionary containing widget references
        key: Config key name (widget key must match)
    """
    if config.has_key(key):
        try:
            widgets_dict[key].set_value(int(config.get_value(key)))
        except (ValueError, TypeError):
            pass


def populate_text_field(config, widgets_dict: dict, key: str) -> None:
    """
    Populate a text entry widget from config.

    Args:
        config: Parsed config object with has_key() and get_value() methods
        widgets_dict: Dictionary containing widget references
        key: Config key name (widget key must match)
    """
    if config.has_key(key):
        widgets_dict[key].set_text(config.get_value(key))


def populate_multivalue_field(config, widgets_dict: dict, key: str, separator: str = ", ") -> None:
    """
    Populate a text entry widget with comma-separated values from config.

    Args:
        config: Parsed config object with has_key() and get_values() methods
        widgets_dict: Dictionary containing widget references
        key: Config key name (widget key must match)
        separator: Separator to join multiple values (default: ", ")
    """
    if config.has_key(key):
        values = config.get_values(key)
        if values:
            widgets_dict[key].set_text(separator.join(values))


class PreferencesPageMixin:
    """
    Mixin class providing shared utility methods for preference pages.

    This mixin provides common functionality used across multiple preference pages:
    - Permission indicators for admin-required settings
    - File manager integration for configuration files
    - Error and success dialog helpers
    - File location display widgets

    Classes using this mixin should inherit from a GTK window class (like
    Adw.PreferencesWindow) so that dialogs can be presented relative to `self`.
    """

    def _create_permission_indicator(self) -> Gtk.Box:
        """
        Create a permission indicator widget showing a lock icon.

        Used to indicate that modifying settings in a group requires
        administrator (root) privileges via pkexec elevation.

        Icon options:
        - system-lock-screen-symbolic: Standard lock icon (used)
        - changes-allow-symbolic: Alternative shield/lock icon

        Returns:
            A Gtk.Box containing the lock icon with tooltip
        """
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        # Create lock icon - using system-lock-screen-symbolic
        # Alternative: changes-allow-symbolic for a shield-style icon
        lock_icon = Gtk.Image.new_from_icon_name("system-lock-screen-symbolic")
        lock_icon.add_css_class("dim-label")
        lock_icon.set_tooltip_text("Requires administrator privileges to modify")

        box.append(lock_icon)
        return box

    def _open_folder_in_file_manager(self, folder_path: str):
        """
        Open a folder in the system's default file manager.

        Args:
            folder_path: The folder path to open
        """
        if not os.path.exists(folder_path):
            # Show error if folder doesn't exist
            dialog = Adw.AlertDialog()
            dialog.set_heading("Folder Not Found")
            dialog.set_body(f"The folder '{folder_path}' does not exist.")
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)
            return

        try:
            # Use xdg-open on Linux to open folder in default file manager
            subprocess.Popen(
                ["xdg-open", folder_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            # Show error dialog if opening fails
            dialog = Adw.AlertDialog()
            dialog.set_heading("Error Opening Folder")
            dialog.set_body(f"Could not open folder: {str(e)}")
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)

    def _show_error_dialog(self, title: str, message: str):
        """
        Show an error dialog to the user.

        Args:
            title: Dialog title
            message: Error message text
        """
        dialog = Adw.AlertDialog()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)

    def _show_success_dialog(self, title: str, message: str):
        """
        Show a success dialog to the user.

        Args:
            title: Dialog title
            message: Success message text
        """
        dialog = Adw.AlertDialog()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)

    def _create_file_location_group(
        self, page: Adw.PreferencesPage, title: str, file_path: str, description: str
    ):
        """
        Create a group showing the configuration file location.

        Displays the filesystem path to the configuration file so users
        know where to find it, with a button to open the containing folder.

        Args:
            page: The preferences page to add the group to
            title: Title for the group
            file_path: The filesystem path to display
            description: Description text for the group
        """
        group = Adw.PreferencesGroup()
        group.set_title(title)
        group.set_description(description)

        # File path row
        path_row = Adw.ActionRow()
        path_row.set_title("File Location")
        path_row.set_subtitle(file_path)
        path_row.set_subtitle_selectable(True)

        # Add folder icon as prefix
        folder_icon = Gtk.Image.new_from_icon_name("folder-open-symbolic")
        folder_icon.set_margin_start(6)
        path_row.add_prefix(folder_icon)

        # Add "Open folder" button as suffix
        open_folder_button = Gtk.Button()
        open_folder_button.set_label("Open Folder")
        open_folder_button.set_valign(Gtk.Align.CENTER)
        open_folder_button.add_css_class("flat")
        open_folder_button.set_tooltip_text("Open containing folder in file manager")

        # Get the parent directory for the file
        parent_dir = os.path.dirname(file_path)

        # Connect click handler to open folder
        open_folder_button.connect(
            "clicked", lambda btn: self._open_folder_in_file_manager(parent_dir)
        )

        path_row.add_suffix(open_folder_button)

        # Make it look like an informational row
        path_row.add_css_class("property")

        group.add(path_row)
        page.add(group)
