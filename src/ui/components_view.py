# ClamUI Components View
"""
Components status view for ClamUI displaying ClamAV component availability and setup guides.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from ..core.utils import check_clamav_installed, check_freshclam_installed, check_clamdscan_installed
from ..core.log_manager import LogManager, DaemonStatus


# Setup guide content for each component
SETUP_GUIDES = {
    "clamscan": {
        "title": "clamscan Installation",
        "commands": [
            ("Ubuntu/Debian", "sudo apt install clamav"),
            ("Fedora", "sudo dnf install clamav"),
            ("Arch Linux", "sudo pacman -S clamav"),
        ],
        "notes": "clamscan is the on-demand virus scanner. After installation, update the virus database with freshclam.",
    },
    "freshclam": {
        "title": "freshclam Installation",
        "commands": [
            ("Ubuntu/Debian", "sudo apt install clamav-freshclam"),
            ("Fedora", "sudo dnf install clamav-update"),
            ("Arch Linux", "sudo pacman -S clamav"),
        ],
        "notes": "freshclam updates the virus database. Enable the service for automatic updates:\nsudo systemctl enable clamav-freshclam\nsudo systemctl start clamav-freshclam",
    },
    "clamdscan": {
        "title": "clamdscan Installation",
        "commands": [
            ("Ubuntu/Debian", "sudo apt install clamav-daemon"),
            ("Fedora", "sudo dnf install clamd"),
            ("Arch Linux", "sudo pacman -S clamav"),
        ],
        "notes": "clamdscan is a client for the clamd daemon, providing faster scanning. Requires clamd daemon to be running.",
    },
    "clamd": {
        "title": "clamd Daemon Setup",
        "commands": [
            ("Ubuntu/Debian", "sudo apt install clamav-daemon\nsudo systemctl enable clamav-daemon\nsudo systemctl start clamav-daemon"),
            ("Fedora", "sudo dnf install clamd\nsudo systemctl enable clamd@scan\nsudo systemctl start clamd@scan"),
            ("Arch Linux", "sudo pacman -S clamav\nsudo systemctl enable clamav-daemon\nsudo systemctl start clamav-daemon"),
        ],
        "notes": "clamd is the ClamAV daemon for faster scanning. Configuration file: /etc/clamav/clamd.conf",
    },
}


class ComponentsView(Gtk.Box):
    """
    Components status view for ClamUI.

    Provides the components status interface with:
    - Status display for each ClamAV component
    - Expandable setup guides with installation commands
    - Refresh button to re-check component status
    """

    def __init__(self, **kwargs):
        """
        Initialize the components view.

        Args:
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        # Log manager for daemon status checking
        self._log_manager = LogManager()

        # Is checking state
        self._is_checking = False

        # Component status widgets storage
        self._component_rows = {}
        self._status_icons = {}
        self._status_labels = {}

        # Set up the UI
        self._setup_ui()

        # Check component status on load
        GLib.idle_add(self._check_all_components)

    def _setup_ui(self):
        """Set up the components view UI layout."""
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_spacing(18)

        # Create the info section
        self._create_info_section()

        # Create the components status section (includes refresh button in header)
        self._create_components_section()

    def _create_info_section(self):
        """Create the info/description section."""
        info_group = Adw.PreferencesGroup()
        info_group.set_title("ClamAV Components")
        info_group.set_description("Check the status of ClamAV components and get setup instructions")

        # Info row explaining the view
        info_row = Adw.ActionRow()
        info_row.set_title("Component Status")
        info_row.set_subtitle("View installation status and setup guides for ClamAV tools")
        info_row.set_icon_name("applications-system-symbolic")

        info_group.add(info_row)
        self.append(info_group)

    def _create_components_section(self):
        """Create the components status section with expandable rows."""
        # Create scrolled window to contain components with max height
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_max_content_height(400)
        scrolled.set_propagate_natural_height(True)

        components_group = Adw.PreferencesGroup()
        components_group.set_title("Components Status")
        components_group.set_description("Expand each component for installation instructions")
        self._components_group = components_group

        # Add refresh button to the header
        self._create_refresh_header_widget(components_group)

        # Create component rows
        self._create_component_row(components_group, "clamscan", "Virus Scanner", "security-high-symbolic")
        self._create_component_row(components_group, "freshclam", "Database Updater", "software-update-available-symbolic")
        self._create_component_row(components_group, "clamdscan", "Daemon Scanner Client", "network-server-symbolic")
        self._create_component_row(components_group, "clamd", "Scanner Daemon", "system-run-symbolic")

        scrolled.set_child(components_group)
        self.append(scrolled)

    def _create_component_row(self, group: Adw.PreferencesGroup, component_id: str, title: str, icon_name: str):
        """
        Create an expandable row for a component with status and setup guide.

        Args:
            group: The PreferencesGroup to add the row to
            component_id: Identifier for the component (clamscan, freshclam, etc.)
            title: Display title for the component
            icon_name: Icon name for the component
        """
        # Create expander row
        expander = Adw.ExpanderRow()
        expander.set_title(title)
        expander.set_subtitle("Checking...")
        expander.set_icon_name(icon_name)

        # Add status suffix widget
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_box.set_valign(Gtk.Align.CENTER)

        status_icon = Gtk.Image()
        status_icon.set_from_icon_name("dialog-question-symbolic")
        status_box.append(status_icon)

        status_label = Gtk.Label()
        status_label.set_text("Checking")
        status_label.add_css_class("dim-label")
        status_box.append(status_label)

        expander.add_suffix(status_box)

        # Store references for updating
        self._component_rows[component_id] = expander
        self._status_icons[component_id] = status_icon
        self._status_labels[component_id] = status_label

        # Add setup guide content
        self._add_setup_guide(expander, component_id)

        group.add(expander)

    def _add_setup_guide(self, expander: Adw.ExpanderRow, component_id: str):
        """
        Add setup guide content to an expander row.

        Args:
            expander: The ExpanderRow to add content to
            component_id: Component identifier for guide lookup
        """
        guide = SETUP_GUIDES.get(component_id, {})

        # Create inner content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)

        # Add installation commands for each distro
        commands = guide.get("commands", [])
        for distro, command in commands:
            command_row = self._create_command_row(distro, command)
            content_box.append(command_row)

        # Add notes if present
        notes = guide.get("notes", "")
        if notes:
            notes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            notes_box.set_margin_top(6)

            notes_label = Gtk.Label()
            notes_label.set_markup(f"<small><i>{GLib.markup_escape_text(notes)}</i></small>")
            notes_label.set_wrap(True)
            notes_label.set_xalign(0)
            notes_label.add_css_class("dim-label")

            notes_box.append(notes_label)
            content_box.append(notes_box)

        # Wrap in ActionRow for proper styling
        guide_row = Adw.ActionRow()
        guide_row.set_activatable(False)
        guide_row.set_child(content_box)

        expander.add_row(guide_row)

    def _create_command_row(self, distro: str, command: str) -> Gtk.Box:
        """
        Create a row displaying a command with copy button.

        Args:
            distro: Distribution name
            command: Command(s) to display

        Returns:
            Box widget containing the command display
        """
        row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        # Distro label
        distro_label = Gtk.Label()
        distro_label.set_markup(f"<b>{GLib.markup_escape_text(distro)}:</b>")
        distro_label.set_xalign(0)
        row_box.append(distro_label)

        # Command box with copy button
        cmd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Command label in a frame
        cmd_frame = Gtk.Frame()
        cmd_frame.add_css_class("card")

        cmd_label = Gtk.Label()
        cmd_label.set_text(command)
        cmd_label.set_xalign(0)
        cmd_label.set_selectable(True)
        cmd_label.add_css_class("monospace")
        cmd_label.set_margin_top(6)
        cmd_label.set_margin_bottom(6)
        cmd_label.set_margin_start(8)
        cmd_label.set_margin_end(8)

        cmd_frame.set_child(cmd_label)
        cmd_box.append(cmd_frame)

        # Copy button
        copy_button = Gtk.Button()
        copy_button.set_icon_name("edit-copy-symbolic")
        copy_button.set_tooltip_text("Copy to clipboard")
        copy_button.set_valign(Gtk.Align.CENTER)
        copy_button.add_css_class("flat")
        copy_button.connect("clicked", self._on_copy_clicked, command)
        cmd_box.append(copy_button)

        row_box.append(cmd_box)

        return row_box

    def _on_copy_clicked(self, button: Gtk.Button, command: str):
        """
        Handle copy button click.

        Args:
            button: The clicked button
            command: Command text to copy
        """
        clipboard = button.get_clipboard()
        clipboard.set(command)

        # Visual feedback - change icon temporarily
        button.set_icon_name("emblem-ok-symbolic")
        GLib.timeout_add(1500, lambda: button.set_icon_name("edit-copy-symbolic"))

    def _create_refresh_header_widget(self, group: Adw.PreferencesGroup):
        """
        Create and add refresh button to the preferences group header.

        Args:
            group: The PreferencesGroup to add the header widget to
        """
        # Create container for refresh button and spinner
        refresh_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        refresh_box.set_valign(Gtk.Align.CENTER)

        # Refresh spinner (hidden by default)
        self._refresh_spinner = Gtk.Spinner()
        self._refresh_spinner.set_visible(False)
        refresh_box.append(self._refresh_spinner)

        # Refresh button
        self._refresh_button = Gtk.Button()
        self._refresh_button.set_icon_name("view-refresh-symbolic")
        self._refresh_button.set_tooltip_text("Refresh Status")
        self._refresh_button.add_css_class("flat")
        self._refresh_button.connect("clicked", self._on_refresh_clicked)
        refresh_box.append(self._refresh_button)

        group.set_header_suffix(refresh_box)

    def _on_refresh_clicked(self, button: Gtk.Button):
        """Handle refresh button click."""
        if self._is_checking:
            return

        self._set_checking_state(True)
        GLib.idle_add(self._check_all_components)

    def _set_checking_state(self, is_checking: bool):
        """
        Update UI to reflect checking state.

        Args:
            is_checking: Whether status check is in progress
        """
        self._is_checking = is_checking

        if is_checking:
            self._refresh_button.set_sensitive(False)
            self._refresh_spinner.set_visible(True)
            self._refresh_spinner.start()
        else:
            self._refresh_button.set_sensitive(True)
            self._refresh_spinner.stop()
            self._refresh_spinner.set_visible(False)

    def _check_all_components(self):
        """Check status of all ClamAV components."""
        # Check clamscan
        is_installed, version_or_error = check_clamav_installed()
        self._update_component_status("clamscan", is_installed, version_or_error)

        # Check freshclam
        is_installed, version_or_error = check_freshclam_installed()
        self._update_component_status("freshclam", is_installed, version_or_error)

        # Check clamdscan
        is_installed, version_or_error = check_clamdscan_installed()
        self._update_component_status("clamdscan", is_installed, version_or_error)

        # Check clamd daemon
        daemon_status, daemon_message = self._log_manager.get_daemon_status()
        self._update_daemon_status("clamd", daemon_status, daemon_message)

        # Reset checking state
        self._set_checking_state(False)

        return False  # Don't repeat

    def _update_component_status(self, component_id: str, is_installed: bool, message: str):
        """
        Update the status display for a component.

        Args:
            component_id: Component identifier
            is_installed: Whether component is installed
            message: Version string or error message
        """
        expander = self._component_rows.get(component_id)
        status_icon = self._status_icons.get(component_id)
        status_label = self._status_labels.get(component_id)

        if not expander or not status_icon or not status_label:
            return

        # Remove previous CSS classes
        status_icon.remove_css_class("success")
        status_icon.remove_css_class("warning")
        status_icon.remove_css_class("error")

        if is_installed:
            status_icon.set_from_icon_name("emblem-ok-symbolic")
            status_icon.add_css_class("success")
            status_label.set_text("Installed")
            expander.set_subtitle(message or "Installed")
        else:
            status_icon.set_from_icon_name("dialog-warning-symbolic")
            status_icon.add_css_class("warning")
            status_label.set_text("Not installed")
            expander.set_subtitle("Not installed - expand for setup instructions")

    def _update_daemon_status(self, component_id: str, status: DaemonStatus, message: str):
        """
        Update the status display for the clamd daemon.

        Args:
            component_id: Component identifier (should be "clamd")
            status: DaemonStatus enum value
            message: Status message
        """
        expander = self._component_rows.get(component_id)
        status_icon = self._status_icons.get(component_id)
        status_label = self._status_labels.get(component_id)

        if not expander or not status_icon or not status_label:
            return

        # Remove previous CSS classes
        status_icon.remove_css_class("success")
        status_icon.remove_css_class("warning")
        status_icon.remove_css_class("error")

        if status == DaemonStatus.RUNNING:
            status_icon.set_from_icon_name("emblem-ok-symbolic")
            status_icon.add_css_class("success")
            status_label.set_text("Running")
            expander.set_subtitle("Daemon is running")
        elif status == DaemonStatus.STOPPED:
            status_icon.set_from_icon_name("media-playback-stop-symbolic")
            status_icon.add_css_class("warning")
            status_label.set_text("Stopped")
            expander.set_subtitle("Daemon is installed but not running")
        elif status == DaemonStatus.NOT_INSTALLED:
            status_icon.set_from_icon_name("dialog-warning-symbolic")
            status_icon.add_css_class("warning")
            status_label.set_text("Not installed")
            expander.set_subtitle("Not installed - expand for setup instructions")
        else:  # UNKNOWN
            status_icon.set_from_icon_name("dialog-question-symbolic")
            status_label.set_text("Unknown")
            expander.set_subtitle(message or "Unable to determine status")
