# ClamUI File Manager Integration Dialog
"""
Dialog for configuring file manager context menu integration.

Shown on first Flatpak launch to offer installation of context menu
actions for supported file managers (Nemo, Nautilus, Dolphin).
"""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..core.file_manager_integration import (
    FileManager,
    IntegrationInfo,
    get_available_integrations,
    install_integration,
)
from .utils import resolve_icon_name

if TYPE_CHECKING:
    from ..core.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class FileManagerIntegrationDialog(Adw.Window):
    """
    A dialog for configuring file manager integration.

    Shown on first Flatpak launch when file manager integrations are available
    but not yet installed. Allows the user to select which file managers to
    integrate with.

    Uses Adw.Window instead of Adw.Dialog for compatibility with
    libadwaita < 1.5 (Ubuntu 22.04, Pop!_OS 22.04).

    Usage:
        dialog = FileManagerIntegrationDialog(
            settings_manager=settings_manager,
            on_complete=lambda: print("Done"),
        )
        dialog.set_transient_for(parent_window)
        dialog.present()
    """

    def __init__(
        self,
        settings_manager: "SettingsManager | None" = None,
        on_complete: Callable[[], None] | None = None,
        **kwargs,
    ):
        """
        Initialize the file manager integration dialog.

        Args:
            settings_manager: SettingsManager for saving preferences.
            on_complete: Callback when dialog is closed (installed or skipped).
            **kwargs: Additional arguments passed to parent.
        """
        super().__init__(**kwargs)

        self._settings_manager = settings_manager
        self._on_complete = on_complete
        self._integration_rows: dict[FileManager, Adw.SwitchRow] = {}

        # Configure and set up the dialog
        self._setup_dialog()
        self._setup_ui()

    def _setup_dialog(self):
        """Configure the dialog properties."""
        self.set_title("File Manager Integration")
        self.set_default_size(500, 450)

        # Configure as modal dialog
        self.set_modal(True)
        self.set_deletable(True)

    def _setup_ui(self):
        """Set up the dialog UI layout."""
        # Toast overlay for notifications
        self._toast_overlay = Adw.ToastOverlay()

        # Main container with toolbar view
        toolbar_view = Adw.ToolbarView()

        # Create header bar
        header_bar = Adw.HeaderBar()
        toolbar_view.add_top_bar(header_bar)

        # Create scrolled content area
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Preferences page
        preferences_page = Adw.PreferencesPage()

        # Info section
        self._create_info_section(preferences_page)

        # File managers section
        self._create_file_managers_section(preferences_page)

        # Actions section
        self._create_actions_section(preferences_page)

        scrolled.set_child(preferences_page)
        toolbar_view.set_content(scrolled)

        self._toast_overlay.set_child(toolbar_view)
        self.set_content(self._toast_overlay)

    def _create_info_section(self, preferences_page: Adw.PreferencesPage):
        """Create the information section."""
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Add Context Menu Actions")
        info_group.set_description(
            "ClamUI can add 'Scan with ClamUI' options to your file manager's "
            "right-click menu. This makes it easy to scan files and folders "
            "directly from your file browser."
        )

        # Info row about what gets installed
        info_row = Adw.ActionRow()
        info_row.set_title("What gets installed?")
        info_row.set_subtitle(
            "Small configuration files are added to your user profile. "
            "No system files are modified."
        )

        info_icon = Gtk.Image.new_from_icon_name(
            resolve_icon_name("dialog-information-symbolic")
        )
        info_icon.add_css_class("dim-label")
        info_row.add_prefix(info_icon)

        info_group.add(info_row)
        preferences_page.add(info_group)

    def _create_file_managers_section(self, preferences_page: Adw.PreferencesPage):
        """Create the file managers selection section."""
        fm_group = Adw.PreferencesGroup()
        fm_group.set_title("Available File Managers")
        fm_group.set_description("Select which file managers to integrate with:")

        # Get available integrations
        integrations = get_available_integrations()
        available_count = 0

        for integration in integrations:
            if integration.is_available:
                available_count += 1
                row = self._create_file_manager_row(integration)
                fm_group.add(row)
                self._integration_rows[integration.file_manager] = row

        if available_count == 0:
            # No file managers detected
            no_fm_row = Adw.ActionRow()
            no_fm_row.set_title("No supported file managers detected")
            no_fm_row.set_subtitle(
                "ClamUI supports Nemo, Nautilus, and Dolphin file managers."
            )

            warning_icon = Gtk.Image.new_from_icon_name(
                resolve_icon_name("dialog-warning-symbolic")
            )
            warning_icon.add_css_class("dim-label")
            no_fm_row.add_prefix(warning_icon)

            fm_group.add(no_fm_row)

        preferences_page.add(fm_group)

    def _create_file_manager_row(self, integration: IntegrationInfo) -> Adw.SwitchRow:
        """
        Create a switch row for a file manager integration.

        Args:
            integration: The integration info.

        Returns:
            The created SwitchRow widget.
        """
        row = Adw.SwitchRow()
        row.set_title(integration.display_name)

        if integration.is_installed:
            row.set_subtitle(f"{integration.description} (already installed)")
            row.set_active(True)
            row.set_sensitive(False)
        else:
            row.set_subtitle(integration.description)
            row.set_active(True)  # Default to enabled

        # Add file manager icon
        icon_name = self._get_file_manager_icon(integration.file_manager)
        icon = Gtk.Image.new_from_icon_name(resolve_icon_name(icon_name))
        icon.add_css_class("dim-label")
        row.add_prefix(icon)

        return row

    def _get_file_manager_icon(self, file_manager: FileManager) -> str:
        """
        Get the icon name for a file manager.

        Args:
            file_manager: The file manager.

        Returns:
            Icon name string.
        """
        icons = {
            FileManager.NEMO: "folder-symbolic",
            FileManager.NAUTILUS: "folder-symbolic",
            FileManager.DOLPHIN: "folder-symbolic",
        }
        return icons.get(file_manager, "folder-symbolic")

    def _create_actions_section(self, preferences_page: Adw.PreferencesPage):
        """Create the action buttons section."""
        actions_group = Adw.PreferencesGroup()

        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(12)
        button_box.set_margin_bottom(12)

        # Skip button
        skip_button = Gtk.Button()
        skip_button.set_label("Skip")
        skip_button.connect("clicked", self._on_skip_clicked)
        button_box.append(skip_button)

        # Install button
        install_button = Gtk.Button()
        install_button.set_label("Install Integration")
        install_button.add_css_class("suggested-action")
        install_button.connect("clicked", self._on_install_clicked)
        button_box.append(install_button)

        actions_group.add(button_box)

        preferences_page.add(actions_group)

    def _on_skip_clicked(self, _button: Gtk.Button):
        """Handle skip button click."""
        self._save_preference_and_close()

    def _on_install_clicked(self, _button: Gtk.Button):
        """Handle install button click."""
        installed_count = 0
        error_count = 0

        for file_manager, row in self._integration_rows.items():
            # Skip if not selected or already installed (not sensitive)
            if not row.get_active() or not row.get_sensitive():
                continue

            success, error = install_integration(file_manager)
            if success:
                installed_count += 1
                logger.info(f"Installed {file_manager.value} integration")
            else:
                error_count += 1
                logger.error(f"Failed to install {file_manager.value}: {error}")

        # Show result
        if error_count > 0:
            self._show_toast(f"Installed {installed_count}, failed {error_count}")
        elif installed_count > 0:
            self._show_toast(f"Installed {installed_count} integration(s)")

        self._save_preference_and_close()

    def _save_preference_and_close(self):
        """Save the prompted preference and close."""
        if self._settings_manager:
            self._settings_manager.set("file_manager_integration_prompted", True)

        self.close()

        if self._on_complete:
            self._on_complete()

    def _show_toast(self, message: str):
        """Show a toast notification."""
        toast = Adw.Toast.new(message)
        self._toast_overlay.add_toast(toast)
