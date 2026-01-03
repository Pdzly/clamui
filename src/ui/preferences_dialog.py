# ClamUI Preferences Dialog
"""
Preferences dialog component for ClamUI user settings.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from typing import TYPE_CHECKING

from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from ..core.settings_manager import SettingsManager


class PreferencesDialog(Adw.Dialog):
    """
    A preferences dialog for configuring ClamUI settings.

    Provides a user interface for toggling application preferences
    such as desktop notifications.

    Usage:
        dialog = PreferencesDialog(settings_manager=app.settings_manager)
        dialog.present(parent_window)
    """

    def __init__(self, settings_manager: "SettingsManager" = None, **kwargs):
        """
        Initialize the preferences dialog.

        Args:
            settings_manager: The SettingsManager instance for reading/writing settings.
                              If None, changes won't be persisted.
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(**kwargs)

        self._settings_manager = settings_manager

        # Configure the dialog
        self._setup_dialog()

        # Set up the UI
        self._setup_ui()

        # Load current settings
        self._load_settings()

    def _setup_dialog(self):
        """Configure the dialog properties."""
        self.set_title("Preferences")
        self.set_content_width(400)
        self.set_content_height(300)
        self.set_can_close(True)

    def _setup_ui(self):
        """Set up the dialog UI layout."""
        # Create main container with toolbar view for header bar
        toolbar_view = Adw.ToolbarView()

        # Create header bar
        header_bar = Adw.HeaderBar()
        toolbar_view.add_top_bar(header_bar)

        # Create scrolled window for content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Create preferences page using Adwaita patterns
        preferences_page = Adw.PreferencesPage()

        # Notifications group
        notifications_group = Adw.PreferencesGroup()
        notifications_group.set_title("Notifications")
        notifications_group.set_description("Configure desktop notification behavior")

        # Notifications enabled switch row
        self._notifications_row = Adw.SwitchRow()
        self._notifications_row.set_title("Desktop Notifications")
        self._notifications_row.set_subtitle(
            "Show notifications when scans complete or updates finish"
        )
        self._notifications_row.connect("notify::active", self._on_notifications_toggled)

        notifications_group.add(self._notifications_row)
        preferences_page.add(notifications_group)

        scrolled.set_child(preferences_page)
        toolbar_view.set_content(scrolled)

        # Set the toolbar view as the dialog child
        self.set_child(toolbar_view)

    def _load_settings(self):
        """Load current settings into UI widgets."""
        if self._settings_manager is not None:
            notifications_enabled = self._settings_manager.get("notifications_enabled", True)
            # Block signal during initial load to avoid triggering save
            self._notifications_row.handler_block_by_func(self._on_notifications_toggled)
            self._notifications_row.set_active(notifications_enabled)
            self._notifications_row.handler_unblock_by_func(self._on_notifications_toggled)
        else:
            # Default to enabled if no settings manager
            self._notifications_row.set_active(True)

    def _on_notifications_toggled(self, row, pspec):
        """
        Handle notification toggle changes.

        Args:
            row: The SwitchRow that was toggled
            pspec: The property specification (unused)
        """
        if self._settings_manager is not None:
            is_active = row.get_active()
            self._settings_manager.set("notifications_enabled", is_active)

    def get_notifications_enabled(self) -> bool:
        """
        Get the current notifications enabled state.

        Returns:
            True if notifications are enabled, False otherwise
        """
        return self._notifications_row.get_active()

    def set_notifications_enabled(self, enabled: bool) -> None:
        """
        Set the notifications enabled state.

        Args:
            enabled: Whether notifications should be enabled
        """
        self._notifications_row.set_active(enabled)
