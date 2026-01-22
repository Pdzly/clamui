# ClamUI Behavior Page
"""
Behavior preference page for window and application behavior settings.

This module provides the BehaviorPage class which handles the UI and logic
for managing window behavior settings like close behavior and tray integration.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ...core.flatpak import is_flatpak
from ..utils import resolve_icon_name
from .base import PreferencesPageMixin


class BehaviorPage(PreferencesPageMixin):
    """
    Behavior preference page for window and application behavior.

    This class creates and manages the UI for window behavior settings,
    including close behavior (minimize to tray vs quit) and tray integration.

    The page includes:
    - Close behavior setting (minimize to tray, quit, or always ask)
    - File manager integration (Flatpak only)
    - All settings are auto-saved when modified

    Note: This page is only shown when a system tray is available.
    """

    # Mapping between close_behavior setting values and ComboRow indices
    CLOSE_BEHAVIOR_OPTIONS = ["minimize", "quit", "ask"]
    CLOSE_BEHAVIOR_LABELS = ["Minimize to tray", "Quit completely", "Always ask"]

    def __init__(
        self,
        settings_manager=None,
        tray_available: bool = False,
        parent_window=None,
    ):
        """
        Initialize the BehaviorPage.

        Args:
            settings_manager: Optional SettingsManager instance for storing settings
            tray_available: Whether the system tray is available
            parent_window: Parent window for presenting dialogs
        """
        self._settings_manager = settings_manager
        self._tray_available = tray_available
        self._parent_window = parent_window
        self._close_behavior_row = None
        self._close_behavior_handler_id = None

    def create_page(self) -> Adw.PreferencesPage:
        """
        Create the Behavior preference page.

        Returns:
            Configured Adw.PreferencesPage ready to be added to preferences window
        """
        page = Adw.PreferencesPage(
            title="Behavior",
            icon_name=resolve_icon_name("preferences-system-symbolic"),
        )

        # Window Behavior group (only if tray is available)
        if self._tray_available:
            window_group = self._create_window_behavior_group()
            page.add(window_group)
        else:
            # Show info message when tray is not available
            info_group = Adw.PreferencesGroup()
            info_group.set_title("Window Behavior")
            info_group.set_description(
                "System tray is not available. Window behavior settings "
                "require a system tray to be active."
            )
            page.add(info_group)

        # File Manager Integration group (only in Flatpak)
        if is_flatpak():
            file_manager_group = self._create_file_manager_group()
            page.add(file_manager_group)

        return page

    def _create_window_behavior_group(self) -> Adw.PreferencesGroup:
        """
        Create the Window Behavior preferences group.

        Returns:
            Configured Adw.PreferencesGroup for window behavior settings
        """
        group = Adw.PreferencesGroup()
        group.set_title("Window Behavior")
        group.set_description("Configure what happens when closing the window")

        # Close behavior combo row
        self._close_behavior_row = Adw.ComboRow()
        self._close_behavior_row.set_title("When closing window")
        self._close_behavior_row.set_subtitle(
            "Choose what happens when you close the main window"
        )

        # Create string list model for options
        model = Gtk.StringList()
        for label in self.CLOSE_BEHAVIOR_LABELS:
            model.append(label)
        self._close_behavior_row.set_model(model)

        # Connect signal
        self._close_behavior_handler_id = self._close_behavior_row.connect(
            "notify::selected", self._on_close_behavior_changed
        )

        # Load current value
        self._load_close_behavior()

        group.add(self._close_behavior_row)

        return group

    def _create_file_manager_group(self) -> Adw.PreferencesGroup:
        """
        Create the File Manager Integration preferences group.

        Returns:
            Configured Adw.PreferencesGroup for file manager integration settings
        """
        group = Adw.PreferencesGroup()
        group.set_title("File Manager Integration")
        group.set_description(
            "Add context menu actions to scan files directly from your file manager"
        )

        row = Adw.ActionRow()
        row.set_title("Configure Integration")
        row.set_subtitle("Install or manage 'Scan with ClamUI' menu actions")
        row.set_activatable(True)
        row.connect("activated", self._on_file_manager_integration_clicked)

        # Icon prefix
        icon = Gtk.Image.new_from_icon_name(
            resolve_icon_name("system-file-manager-symbolic")
        )
        icon.add_css_class("dim-label")
        row.add_prefix(icon)

        # Chevron suffix
        chevron = Gtk.Image.new_from_icon_name(resolve_icon_name("go-next-symbolic"))
        chevron.add_css_class("dim-label")
        row.add_suffix(chevron)

        group.add(row)
        return group

    def _on_file_manager_integration_clicked(self, _row):
        """Handle file manager integration row click."""
        from ..file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog(
            settings_manager=self._settings_manager,
        )
        dialog.set_transient_for(self._parent_window)
        dialog.present()

    def _load_close_behavior(self):
        """Load the current close behavior setting into the ComboRow."""
        if self._settings_manager is None or self._close_behavior_row is None:
            return

        close_behavior = self._settings_manager.get("close_behavior", None)
        # Map setting value to ComboRow index, default to "ask" if not set
        if close_behavior in self.CLOSE_BEHAVIOR_OPTIONS:
            index = self.CLOSE_BEHAVIOR_OPTIONS.index(close_behavior)
        else:
            # Default to "ask" (index 2) for unset or invalid values
            index = 2

        # Block signal during load to avoid triggering save
        handler_id = self._close_behavior_handler_id
        if handler_id is not None:
            self._close_behavior_row.handler_block(handler_id)
        self._close_behavior_row.set_selected(index)
        if handler_id is not None:
            self._close_behavior_row.handler_unblock(handler_id)

    def _on_close_behavior_changed(self, row, pspec):
        """
        Handle close behavior ComboRow changes.

        Args:
            row: The ComboRow that was changed
            pspec: The property specification (unused)
        """
        if self._settings_manager is None:
            return

        selected_index = row.get_selected()
        if 0 <= selected_index < len(self.CLOSE_BEHAVIOR_OPTIONS):
            value = self.CLOSE_BEHAVIOR_OPTIONS[selected_index]
            self._settings_manager.set("close_behavior", value)
