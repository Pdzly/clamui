# ClamUI VirusTotal Preferences Page
"""
VirusTotal Settings preference page for API key configuration.

This module provides the VirusTotalPage class which handles the UI and logic
for configuring VirusTotal API key and behavior settings.
"""

import logging
import webbrowser
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ...core.keyring_manager import (
    delete_api_key,
    get_api_key,
    mask_api_key,
    set_api_key,
    validate_api_key_format,
)

if TYPE_CHECKING:
    from ...core.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

# VirusTotal URLs
VT_API_KEY_URL = "https://www.virustotal.com/gui/my-apikey"


class VirusTotalPage:
    """
    VirusTotal Settings preference page for API key configuration.

    This class creates and manages the UI for configuring VirusTotal
    settings, including API key management and behavior options.

    The page includes:
    - API key status and configuration
    - Link to get free API key
    - "When no API key" behavior dropdown
    - Delete API key button
    """

    @staticmethod
    def create_page(
        settings_manager: "SettingsManager",
        parent_window=None,
    ) -> Adw.PreferencesPage:
        """
        Create the VirusTotal Settings preference page.

        Args:
            settings_manager: SettingsManager instance for saving settings
            parent_window: Parent window for presenting dialogs

        Returns:
            Configured Adw.PreferencesPage ready to be added to preferences window
        """
        page = Adw.PreferencesPage(
            title="VirusTotal",
            icon_name="network-server-symbolic",
        )

        # Store references for callbacks
        page._settings_manager = settings_manager
        page._parent_window = parent_window

        # Toast overlay reference (will be set when added to window)
        page._toast_overlay = None

        # Create API key status group
        VirusTotalPage._create_api_key_group(page, settings_manager)

        # Create behavior settings group
        VirusTotalPage._create_behavior_group(page, settings_manager)

        # Create info group
        VirusTotalPage._create_info_group(page)

        return page

    @staticmethod
    def _create_api_key_group(
        page: Adw.PreferencesPage,
        settings_manager: "SettingsManager",
    ):
        """
        Create the API Key configuration group.

        Shows current API key status and allows setting/updating the key.

        Args:
            page: The preferences page to add the group to
            settings_manager: SettingsManager for API key storage
        """
        group = Adw.PreferencesGroup()
        group.set_title("API Key")
        group.set_description("Configure your VirusTotal API key for file scanning")

        # Current status row
        status_row = Adw.ActionRow()
        status_row.set_title("Status")

        # Check if API key is configured
        current_key = get_api_key(settings_manager)
        if current_key:
            status_row.set_subtitle(f"Configured ({mask_api_key(current_key)})")
            status_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
            status_icon.add_css_class("success")
        else:
            status_row.set_subtitle("Not configured")
            status_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
            status_icon.add_css_class("warning")

        status_row.add_suffix(status_icon)
        page._status_row = status_row
        page._status_icon = status_icon
        group.add(status_row)

        # API key entry row
        api_key_row = Adw.PasswordEntryRow()
        api_key_row.set_title("API Key")
        api_key_row.connect(
            "changed", lambda row: VirusTotalPage._on_api_key_changed(page, row)
        )
        page._api_key_row = api_key_row
        group.add(api_key_row)

        # Validation message (hidden by default)
        validation_label = Gtk.Label()
        validation_label.set_halign(Gtk.Align.START)
        validation_label.set_margin_start(12)
        validation_label.set_margin_top(6)
        validation_label.add_css_class("error")
        validation_label.set_visible(False)
        page._validation_label = validation_label
        group.add(validation_label)

        # Button box for Save and Delete
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(12)

        # Delete button (only shown if key exists)
        delete_button = Gtk.Button()
        delete_button.set_label("Delete Key")
        delete_button.add_css_class("destructive-action")
        delete_button.set_sensitive(current_key is not None)
        delete_button.connect(
            "clicked",
            lambda btn: VirusTotalPage._on_delete_clicked(page, settings_manager),
        )
        page._delete_button = delete_button
        button_box.append(delete_button)

        # Save button
        save_button = Gtk.Button()
        save_button.set_label("Save Key")
        save_button.add_css_class("suggested-action")
        save_button.set_sensitive(False)
        save_button.connect(
            "clicked",
            lambda btn: VirusTotalPage._on_save_clicked(page, settings_manager),
        )
        page._save_button = save_button
        button_box.append(save_button)

        group.add(button_box)

        # Get API key link
        link_row = Adw.ActionRow()
        link_row.set_title("Get a free API key")
        link_row.set_subtitle("Create an account at virustotal.com")
        link_row.set_activatable(True)
        link_row.connect(
            "activated", lambda row: VirusTotalPage._on_get_api_key_clicked()
        )

        link_icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
        link_icon.add_css_class("dim-label")
        link_row.add_prefix(link_icon)

        chevron = Gtk.Image.new_from_icon_name("go-next-symbolic")
        chevron.add_css_class("dim-label")
        link_row.add_suffix(chevron)

        group.add(link_row)

        page.add(group)

    @staticmethod
    def _create_behavior_group(
        page: Adw.PreferencesPage,
        settings_manager: "SettingsManager",
    ):
        """
        Create the behavior settings group.

        Configures what happens when user tries to scan without API key.

        Args:
            page: The preferences page to add the group to
            settings_manager: SettingsManager for saving preferences
        """
        group = Adw.PreferencesGroup()
        group.set_title("Behavior")
        group.set_description("Configure VirusTotal scanning behavior")

        # "When no API key" dropdown
        no_key_row = Adw.ComboRow()
        no_key_model = Gtk.StringList()
        no_key_model.append("Always ask")
        no_key_model.append("Open VirusTotal website")
        no_key_model.append("Show notification only")
        no_key_row.set_model(no_key_model)
        no_key_row.set_title("When API key is missing")
        no_key_row.set_subtitle("Action to take when scanning without API key")

        # Set current selection from settings
        current_action = settings_manager.get(
            "virustotal_remember_no_key_action", "none"
        )
        action_map = {"none": 0, "open_website": 1, "prompt": 2}
        no_key_row.set_selected(action_map.get(current_action, 0))

        # Connect to selection changes
        no_key_row.connect(
            "notify::selected",
            lambda row, pspec: VirusTotalPage._on_no_key_action_changed(
                row, settings_manager
            ),
        )

        group.add(no_key_row)
        page.add(group)

    @staticmethod
    def _create_info_group(page: Adw.PreferencesPage):
        """
        Create the information group with rate limit details.

        Args:
            page: The preferences page to add the group to
        """
        group = Adw.PreferencesGroup()
        group.set_title("Information")

        # Rate limit info
        rate_limit_row = Adw.ActionRow()
        rate_limit_row.set_title("Rate Limit")
        rate_limit_row.set_subtitle("Free tier: 4 requests per minute, 500 per day")

        info_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        info_icon.add_css_class("dim-label")
        rate_limit_row.add_prefix(info_icon)

        group.add(rate_limit_row)

        # File size limit info
        size_limit_row = Adw.ActionRow()
        size_limit_row.set_title("Maximum File Size")
        size_limit_row.set_subtitle("Files up to 650 MB can be scanned")

        size_icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")
        size_icon.add_css_class("dim-label")
        size_limit_row.add_prefix(size_icon)

        group.add(size_limit_row)

        page.add(group)

    @staticmethod
    def _on_api_key_changed(page: Adw.PreferencesPage, entry_row: Adw.PasswordEntryRow):
        """Handle API key entry changes for validation."""
        api_key = entry_row.get_text().strip()

        if not api_key:
            page._save_button.set_sensitive(False)
            page._validation_label.set_visible(False)
            return

        # Validate API key format
        is_valid, error_msg = validate_api_key_format(api_key)

        if is_valid:
            page._save_button.set_sensitive(True)
            page._validation_label.set_visible(False)
        else:
            page._save_button.set_sensitive(False)
            page._validation_label.set_label(error_msg or "Invalid API key format")
            page._validation_label.set_visible(True)

    @staticmethod
    def _on_save_clicked(
        page: Adw.PreferencesPage, settings_manager: "SettingsManager"
    ):
        """Save the API key."""
        api_key = page._api_key_row.get_text().strip()

        if not api_key:
            return

        # Validate again
        is_valid, error_msg = validate_api_key_format(api_key)
        if not is_valid:
            VirusTotalPage._show_toast(page, error_msg or "Invalid API key")
            return

        # Save to keyring
        success, error = set_api_key(api_key, settings_manager)

        if success:
            VirusTotalPage._show_toast(page, "API key saved")

            # Update status
            page._status_row.set_subtitle(f"Configured ({mask_api_key(api_key)})")
            page._status_icon.set_from_icon_name("emblem-ok-symbolic")
            page._status_icon.remove_css_class("warning")
            page._status_icon.add_css_class("success")

            # Clear entry and enable delete button
            page._api_key_row.set_text("")
            page._save_button.set_sensitive(False)
            page._delete_button.set_sensitive(True)
        else:
            VirusTotalPage._show_toast(
                page, f"Failed to save: {error}" if error else "Failed"
            )

    @staticmethod
    def _on_delete_clicked(
        page: Adw.PreferencesPage, settings_manager: "SettingsManager"
    ):
        """Delete the API key after confirmation."""
        # Show confirmation dialog
        dialog = Adw.AlertDialog()
        dialog.set_heading("Delete API Key?")
        dialog.set_body(
            "This will remove your VirusTotal API key. "
            "You'll need to enter it again to use VirusTotal scanning."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(dialog, response):
            if response == "delete":
                success = delete_api_key(settings_manager)

                if success:
                    VirusTotalPage._show_toast(page, "API key deleted")

                    # Update status
                    page._status_row.set_subtitle("Not configured")
                    page._status_icon.set_from_icon_name("dialog-warning-symbolic")
                    page._status_icon.remove_css_class("success")
                    page._status_icon.add_css_class("warning")

                    # Disable delete button
                    page._delete_button.set_sensitive(False)
                else:
                    VirusTotalPage._show_toast(page, "Failed to delete API key")

        dialog.connect("response", on_response)
        dialog.present(page._parent_window)

    @staticmethod
    def _on_no_key_action_changed(
        row: Adw.ComboRow, settings_manager: "SettingsManager"
    ):
        """Handle no-key action selection change."""
        action_reverse_map = {0: "none", 1: "open_website", 2: "prompt"}
        selected = row.get_selected()
        action = action_reverse_map.get(selected, "none")
        settings_manager.set("virustotal_remember_no_key_action", action)

    @staticmethod
    def _on_get_api_key_clicked():
        """Open VirusTotal API key page."""
        try:
            webbrowser.open(VT_API_KEY_URL)
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")

    @staticmethod
    def _show_toast(page: Adw.PreferencesPage, message: str):
        """Show a toast notification if toast overlay is available."""
        # Try to find the toast overlay from parent window
        parent = page.get_root()
        if parent and hasattr(parent, "_toast_overlay"):
            toast = Adw.Toast.new(message)
            parent._toast_overlay.add_toast(toast)
        else:
            logger.debug("Toast notification fallback (overlay not available)")
