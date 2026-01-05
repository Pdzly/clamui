# ClamUI Scan Results Dialog
"""
Dialog component for displaying scan results with threat details and actions.
"""

import logging
import os
import threading
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from ..core.quarantine import QuarantineManager, QuarantineStatus
from ..core.scanner import ScanResult, ScanStatus, ThreatDetail
from ..core.utils import copy_to_clipboard, format_flatpak_portal_path

if TYPE_CHECKING:
    from ..core.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

# Pagination constants
INITIAL_DISPLAY_LIMIT = 25
LOAD_MORE_BATCH_SIZE = 25
LARGE_RESULT_THRESHOLD = 50


class ScanResultsDialog(Adw.Dialog):
    """
    A dialog for displaying scan results with threat details and actions.

    Provides:
    - Scan statistics summary
    - List of detected threats with severity badges
    - Per-threat actions (Quarantine, Exclude, Copy Path)
    - Bulk "Quarantine All" action

    Usage:
        dialog = ScanResultsDialog(
            scan_result=result,
            quarantine_manager=quarantine_manager,
            settings_manager=settings_manager
        )
        dialog.present(parent_window)
    """

    def __init__(
        self,
        scan_result: ScanResult,
        quarantine_manager: QuarantineManager,
        settings_manager: "SettingsManager | None" = None,
        **kwargs,
    ):
        """
        Initialize the scan results dialog.

        Args:
            scan_result: The ScanResult to display
            quarantine_manager: QuarantineManager for quarantine operations
            settings_manager: Optional SettingsManager for exclusion patterns
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(**kwargs)

        self._scan_result = scan_result
        self._quarantine_manager = quarantine_manager
        self._settings_manager = settings_manager

        # Pagination state
        self._displayed_threat_count = 0
        self._all_threat_details = scan_result.threat_details or []
        self._load_more_row: Gtk.ListBoxRow | None = None

        # Track unquarantined threats for bulk action
        self._unquarantined_threats: list[ThreatDetail] = list(self._all_threat_details)

        # UI references
        self._quarantine_all_button: Gtk.Button | None = None
        self._threats_list: Gtk.ListBox | None = None

        # Configure and set up the dialog
        self._setup_dialog()
        self._setup_ui()

    def _setup_dialog(self):
        """Configure the dialog properties."""
        self.set_title("Scan Results")
        self.set_content_width(700)
        self.set_content_height(500)
        self.set_can_close(True)

    def _setup_ui(self):
        """Set up the dialog UI layout."""
        # Toast overlay for notifications
        self._toast_overlay = Adw.ToastOverlay()

        # Main container with toolbar view
        toolbar_view = Adw.ToolbarView()

        # Create header bar with actions
        header_bar = Adw.HeaderBar()

        # Export button (left side)
        export_button = Gtk.Button()
        export_button.set_icon_name("document-save-symbolic")
        export_button.set_tooltip_text("Export results")
        export_button.add_css_class("flat")
        export_button.connect("clicked", self._on_export_clicked)
        header_bar.pack_start(export_button)

        # Quarantine All button (right side, only if threats exist)
        if self._scan_result.infected_count > 0:
            self._quarantine_all_button = Gtk.Button()
            count = len(self._unquarantined_threats)
            if count == 1:
                self._quarantine_all_button.set_label("Quarantine 1 Threat")
            else:
                self._quarantine_all_button.set_label(f"Quarantine All ({count})")
            self._quarantine_all_button.add_css_class("suggested-action")
            self._quarantine_all_button.connect("clicked", self._on_quarantine_all_clicked)
            header_bar.pack_end(self._quarantine_all_button)

        toolbar_view.add_top_bar(header_bar)

        # Create scrolled content area
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)

        # Add statistics section
        self._create_stats_section(content_box)

        # Add threats section if there are threats
        if self._scan_result.infected_count > 0:
            self._create_threats_section(content_box)

        scrolled.set_child(content_box)
        toolbar_view.set_content(scrolled)

        self._toast_overlay.set_child(toolbar_view)
        self.set_child(self._toast_overlay)

    def _create_stats_section(self, parent: Gtk.Box):
        """Create the statistics section."""
        stats_group = Adw.PreferencesGroup()
        stats_group.set_title("Statistics")

        # Create expander for detailed stats
        expander = Adw.ExpanderRow()
        expander.set_expanded(True)

        # Set title based on result status
        if self._scan_result.status == ScanStatus.CLEAN:
            expander.set_title("Scan Complete")
            expander.set_subtitle("No threats found")
            icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
            icon.add_css_class("success")
        elif self._scan_result.status == ScanStatus.INFECTED:
            threat_text = (
                "1 threat"
                if self._scan_result.infected_count == 1
                else f"{self._scan_result.infected_count} threats"
            )
            expander.set_title("Threats Detected")
            expander.set_subtitle(f"{threat_text} found")
            icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
            icon.add_css_class("warning")
        else:
            expander.set_title("Scan Error")
            expander.set_subtitle(self._scan_result.error_message or "Unknown error")
            icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
            icon.add_css_class("error")

        expander.add_suffix(icon)

        # Stats content
        stats_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        stats_content.set_margin_start(12)
        stats_content.set_margin_end(12)
        stats_content.set_margin_top(8)
        stats_content.set_margin_bottom(8)

        # Add stat rows
        stats_content.append(
            self._create_stat_row("Files scanned:", f"{self._scan_result.scanned_files:,}")
        )
        stats_content.append(
            self._create_stat_row("Directories:", f"{self._scan_result.scanned_dirs:,}")
        )

        if self._scan_result.infected_count > 0:
            stats_content.append(
                self._create_stat_row("Threats found:", str(self._scan_result.infected_count))
            )

        if self._scan_result.error_message:
            stats_content.append(self._create_stat_row("Error:", self._scan_result.error_message))

        expander.add_row(stats_content)
        stats_group.add(expander)
        parent.append(stats_group)

    def _create_stat_row(self, label: str, value: str) -> Gtk.Box:
        """Create a row for displaying a statistic."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("stats-row")

        label_widget = Gtk.Label()
        label_widget.set_label(label)
        label_widget.set_xalign(0)
        label_widget.add_css_class("dim-label")
        label_widget.set_size_request(120, -1)
        row.append(label_widget)

        value_widget = Gtk.Label()
        value_widget.set_label(value)
        value_widget.set_xalign(0)
        value_widget.add_css_class("heading")
        row.append(value_widget)

        return row

    def _create_threats_section(self, parent: Gtk.Box):
        """Create the threats list section."""
        threats_group = Adw.PreferencesGroup()
        threats_group.set_title("Detected Threats")

        # Warning banner for large result sets
        if len(self._all_threat_details) > LARGE_RESULT_THRESHOLD:
            warning_banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            warning_banner.add_css_class("large-result-warning")
            warning_banner.set_margin_bottom(8)

            warning_label = Gtk.Label()
            warning_label.set_markup(
                f"<b>Large result set:</b> Found {len(self._all_threat_details)} threats. "
                f"Displaying first {INITIAL_DISPLAY_LIMIT}."
            )
            warning_label.set_wrap(True)
            warning_banner.append(warning_label)
            threats_group.add(warning_banner)

        # Threats list
        self._threats_list = Gtk.ListBox()
        self._threats_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._threats_list.add_css_class("boxed-list")

        # Load initial batch
        self._load_more_threats(INITIAL_DISPLAY_LIMIT)

        threats_group.add(self._threats_list)
        parent.append(threats_group)

    def _load_more_threats(self, count: int):
        """Load and display more threats."""
        if self._threats_list is None:
            return

        start_idx = self._displayed_threat_count
        end_idx = min(start_idx + count, len(self._all_threat_details))

        for threat in self._all_threat_details[start_idx:end_idx]:
            threat_row = self._create_threat_row(threat)
            self._threats_list.append(threat_row)
            self._displayed_threat_count += 1

        # Add "Load More" button if there are more threats
        if self._displayed_threat_count < len(self._all_threat_details):
            if self._load_more_row is not None:
                self._threats_list.remove(self._load_more_row)

            load_more_row = Gtk.ListBoxRow()
            load_more_row.add_css_class("load-more-row")
            load_more_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            load_more_box.set_halign(Gtk.Align.CENTER)
            load_more_box.set_margin_top(8)
            load_more_box.set_margin_bottom(8)

            remaining = len(self._all_threat_details) - self._displayed_threat_count
            load_more_btn = Gtk.Button()
            load_more_btn.set_label(f"Show {min(LOAD_MORE_BATCH_SIZE, remaining)} more")
            load_more_btn.add_css_class("flat")
            load_more_btn.connect("clicked", self._on_load_more_clicked)
            load_more_box.append(load_more_btn)

            load_more_row.set_child(load_more_box)
            self._threats_list.append(load_more_row)
            self._load_more_row = load_more_row

    def _on_load_more_clicked(self, button):
        """Handle load more button click."""
        self._load_more_threats(LOAD_MORE_BATCH_SIZE)

    def _create_threat_row(self, threat: ThreatDetail) -> Gtk.ListBoxRow:
        """Create a list row for a single threat."""
        row = Gtk.ListBoxRow()
        row.set_activatable(False)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        content_box.set_margin_top(8)
        content_box.set_margin_bottom(8)

        # Header with threat name and severity
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        name_label = Gtk.Label()
        name_label.set_label(threat.threat_name)
        name_label.set_xalign(0)
        name_label.set_hexpand(True)
        name_label.set_wrap(True)
        name_label.add_css_class("monospace")
        header_box.append(name_label)

        severity_badge = Gtk.Label()
        severity_badge.set_label(threat.severity.upper())
        severity_badge.add_css_class("severity-badge")
        severity_badge.add_css_class(f"severity-{threat.severity}")
        header_box.append(severity_badge)

        content_box.append(header_box)

        # File path (format Flatpak portal paths for readability)
        path_label = Gtk.Label()
        path_label.set_label(format_flatpak_portal_path(threat.file_path))
        path_label.set_xalign(0)
        path_label.set_wrap(True)
        path_label.set_selectable(True)
        path_label.add_css_class("monospace")
        path_label.add_css_class("dim-label")
        path_label.set_size_request(400, -1)
        content_box.append(path_label)

        # Action buttons
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.add_css_class("threat-actions")
        actions_box.set_halign(Gtk.Align.END)
        actions_box.set_margin_top(4)

        # Quarantine button
        quarantine_btn = Gtk.Button()
        quarantine_btn.set_label("Quarantine")
        quarantine_btn.add_css_class("pill")
        quarantine_btn.add_css_class("threat-action-btn")
        quarantine_btn.connect("clicked", lambda btn: self._on_quarantine_single(btn, threat))
        actions_box.append(quarantine_btn)

        # Exclude button
        exclude_btn = Gtk.Button()
        exclude_btn.set_label("Exclude")
        exclude_btn.add_css_class("pill")
        exclude_btn.add_css_class("threat-action-btn")
        exclude_btn.set_tooltip_text("Add file path to exclusion list")
        exclude_btn.connect("clicked", lambda btn: self._on_add_exclusion(btn, threat))
        actions_box.append(exclude_btn)

        # Copy Path button
        copy_btn = Gtk.Button()
        copy_btn.set_label("Copy Path")
        copy_btn.add_css_class("pill")
        copy_btn.add_css_class("flat")
        copy_btn.add_css_class("threat-action-btn")
        copy_btn.connect("clicked", lambda btn: self._on_copy_path(btn, threat))
        actions_box.append(copy_btn)

        content_box.append(actions_box)
        row.set_child(content_box)

        return row

    def _on_quarantine_single(self, button: Gtk.Button, threat: ThreatDetail):
        """Quarantine a single threat file."""
        result = self._quarantine_manager.quarantine_file(threat.file_path, threat.threat_name)

        if result.status == QuarantineStatus.SUCCESS:
            button.set_label("Quarantined")
            button.set_sensitive(False)
            button.add_css_class("quarantined")

            # Remove from unquarantined list and update button
            if threat in self._unquarantined_threats:
                self._unquarantined_threats.remove(threat)
                self._update_quarantine_all_button()

            self._show_toast(f"Quarantined: {os.path.basename(threat.file_path)}")
        else:
            self._show_toast(f"Failed: {result.error_message}")

    def _on_add_exclusion(self, button: Gtk.Button, threat: ThreatDetail):
        """Add threat's file path to exclusion list."""
        if self._settings_manager is None:
            logger.warning("Cannot add exclusion: settings_manager is None")
            self._show_toast("Cannot access settings")
            return

        # Get current exclusion patterns
        exclusions = self._settings_manager.get("exclusion_patterns", [])
        if not isinstance(exclusions, list):
            exclusions = []

        # Check if already excluded
        for excl in exclusions:
            if excl.get("pattern") == threat.file_path:
                button.set_label("Excluded")
                button.set_sensitive(False)
                button.add_css_class("excluded")
                self._show_toast("Path already in exclusion list")
                return

        # Add new exclusion
        new_exclusion = {
            "pattern": threat.file_path,
            "type": "file",
            "enabled": True,
        }
        exclusions.append(new_exclusion)
        self._settings_manager.set("exclusion_patterns", exclusions)

        button.set_label("Excluded")
        button.set_sensitive(False)
        button.add_css_class("excluded")

        self._show_toast(f"Added to exclusions: {os.path.basename(threat.file_path)}")

    def _on_copy_path(self, button: Gtk.Button, threat: ThreatDetail):
        """Copy threat file path to clipboard."""
        copy_to_clipboard(threat.file_path)
        self._show_toast(f"Copied: {threat.file_path}")

    def _on_quarantine_all_clicked(self, button: Gtk.Button):
        """Handle quarantine all button click."""
        if not self._unquarantined_threats:
            return

        button.set_sensitive(False)
        button.set_label("Quarantining...")

        threats_to_quarantine = list(self._unquarantined_threats)

        def quarantine_worker():
            success_count = 0
            error_count = 0

            for threat in threats_to_quarantine:
                result = self._quarantine_manager.quarantine_file(
                    threat.file_path, threat.threat_name
                )
                if result.status == QuarantineStatus.SUCCESS:
                    success_count += 1
                else:
                    error_count += 1
                    logger.warning(
                        f"Failed to quarantine {threat.file_path}: {result.error_message}"
                    )

            GLib.idle_add(self._on_quarantine_all_complete, success_count, error_count)

        thread = threading.Thread(target=quarantine_worker, daemon=True)
        thread.start()

    def _on_quarantine_all_complete(self, success_count: int, error_count: int):
        """Handle completion of bulk quarantine operation."""
        self._unquarantined_threats.clear()

        if self._quarantine_all_button:
            self._quarantine_all_button.set_visible(False)

        if error_count == 0:
            self._show_toast(f"Quarantined {success_count} threat(s)")
        else:
            self._show_toast(f"Quarantined {success_count}, failed {error_count}")

        return False

    def _update_quarantine_all_button(self):
        """Update the quarantine all button label."""
        if self._quarantine_all_button is None:
            return

        count = len(self._unquarantined_threats)
        if count == 0:
            self._quarantine_all_button.set_visible(False)
        elif count == 1:
            self._quarantine_all_button.set_label("Quarantine 1 Threat")
        else:
            self._quarantine_all_button.set_label(f"Quarantine All ({count})")

    def _on_export_clicked(self, button: Gtk.Button):
        """Handle export button click."""
        # Get the scan output and copy to clipboard
        if self._scan_result.stdout:
            copy_to_clipboard(self._scan_result.stdout)
            self._show_toast("Results copied to clipboard")
        else:
            self._show_toast("No results to export")

    def _show_toast(self, message: str):
        """Show a toast notification."""
        toast = Adw.Toast.new(message)
        self._toast_overlay.add_toast(toast)
