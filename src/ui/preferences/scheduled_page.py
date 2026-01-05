# ClamUI Scheduled Scans Page
"""
Scheduled Scans preference page for automatic scan configuration.

This module provides the ScheduledPage class which handles the UI and logic
for configuring scheduled scans using systemd timers or cron.
"""

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from .base import PreferencesPageMixin


class ScheduledPage(PreferencesPageMixin):
    """
    Scheduled Scans preference page for automatic scan configuration.

    This class creates and manages the UI for configuring scheduled scans,
    including frequency, time, targets, and options like battery-aware scanning
    and auto-quarantine.

    The page includes:
    - Enable/disable scheduled scans switch
    - Frequency selection (hourly, daily, weekly, monthly)
    - Time picker for scan execution
    - Day of week selection (for weekly scans)
    - Day of month selection (for monthly scans)
    - Scan targets (comma-separated paths)
    - Skip on battery option
    - Auto-quarantine option

    Note: This class uses PreferencesPageMixin for shared utilities. Unlike
    other pages, scheduled scans are configured in ClamUI settings (not ClamAV
    config files) and must be saved via the Save & Apply page.
    """

    @staticmethod
    def create_page(widgets_dict: dict) -> Adw.PreferencesPage:
        """
        Create the Scheduled Scans preference page.

        Args:
            widgets_dict: Dictionary to store widget references for later access

        Returns:
            Configured Adw.PreferencesPage ready to be added to preferences window
        """
        page = Adw.PreferencesPage(
            title="Scheduled Scans",
            icon_name="alarm-symbolic",
        )

        # Create scheduled scans configuration group
        ScheduledPage._create_scheduled_config_group(page, widgets_dict)

        return page

    @staticmethod
    def _create_scheduled_config_group(page: Adw.PreferencesPage, widgets_dict: dict):
        """
        Create the Scheduled Scans Configuration group.

        Contains settings for:
        - Enable scheduled scans switch
        - Scan frequency (hourly, daily, weekly, monthly)
        - Scan time (24-hour format)
        - Day of week (for weekly scans)
        - Day of month (for monthly scans)
        - Scan targets (comma-separated paths)
        - Skip on battery option
        - Auto-quarantine option

        Args:
            page: The preferences page to add the group to
            widgets_dict: Dictionary to store widget references
        """
        group = Adw.PreferencesGroup()
        group.set_title("Scheduled Scans Configuration")
        group.set_description("Configure automatic scanning. Save with 'Save &amp; Apply'.")

        # Enable scheduled scans switch
        enable_scheduled_row = Adw.SwitchRow()
        enable_scheduled_row.set_title("Enable Scheduled Scans")
        enable_scheduled_row.set_subtitle("Run automatic scans at specified intervals")
        widgets_dict["enabled"] = enable_scheduled_row
        group.add(enable_scheduled_row)

        # Schedule frequency dropdown
        frequency_row = Adw.ComboRow()
        frequency_model = Gtk.StringList()
        frequency_model.append("Hourly")
        frequency_model.append("Daily")
        frequency_model.append("Weekly")
        frequency_model.append("Monthly")
        frequency_row.set_model(frequency_model)
        frequency_row.set_selected(1)  # Default to Daily
        frequency_row.set_title("Scan Frequency")
        widgets_dict["frequency"] = frequency_row
        group.add(frequency_row)

        # Time picker (schedule_time)
        time_row = Adw.EntryRow()
        time_row.set_title("Scan Time (24-hour format, e.g. 02:00)")
        time_row.set_text("02:00")
        widgets_dict["time"] = time_row
        group.add(time_row)

        # Day of week dropdown (for weekly scans)
        day_of_week_row = Adw.ComboRow()
        day_of_week_model = Gtk.StringList()
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            day_of_week_model.append(day)
        day_of_week_row.set_model(day_of_week_model)
        day_of_week_row.set_selected(0)  # Default to Monday
        day_of_week_row.set_title("Day of Week")
        day_of_week_row.set_subtitle("For weekly scans")
        widgets_dict["day_of_week"] = day_of_week_row
        group.add(day_of_week_row)

        # Day of month spinner (for monthly scans)
        day_of_month_row = Adw.SpinRow()
        day_of_month_row.set_title("Day of Month")
        day_of_month_row.set_subtitle("For monthly scans (1-28)")
        adjustment = Gtk.Adjustment(
            value=1, lower=1, upper=28, step_increment=1, page_increment=5, page_size=0
        )
        day_of_month_row.set_adjustment(adjustment)
        widgets_dict["day_of_month"] = day_of_month_row
        group.add(day_of_month_row)

        # Scan targets entry (schedule_targets)
        targets_row = Adw.EntryRow()
        targets_row.set_title("Scan Targets (comma-separated paths)")
        targets_row.set_text(str(Path.home()))
        widgets_dict["targets"] = targets_row
        group.add(targets_row)

        # Skip on battery switch
        skip_battery_row = Adw.SwitchRow()
        skip_battery_row.set_title("Skip on Battery")
        skip_battery_row.set_subtitle("Don't run scheduled scans when on battery power")
        skip_battery_row.set_active(True)
        widgets_dict["skip_on_battery"] = skip_battery_row
        group.add(skip_battery_row)

        # Auto-quarantine switch
        auto_quarantine_row = Adw.SwitchRow()
        auto_quarantine_row.set_title("Auto-Quarantine")
        auto_quarantine_row.set_subtitle("Automatically quarantine detected threats")
        auto_quarantine_row.set_active(False)
        widgets_dict["auto_quarantine"] = auto_quarantine_row
        group.add(auto_quarantine_row)

        page.add(group)

    @staticmethod
    def populate_fields(config: dict, widgets_dict: dict):
        """
        Populate scheduled scan widgets from settings.

        Loads settings from the provided config dictionary and updates
        the UI widgets with current values.

        Args:
            config: Dictionary containing scheduled scan settings from SettingsManager
            widgets_dict: Dictionary of widget references to populate
        """
        if config is None:
            config = {}

        # Enable/disable switch
        widgets_dict["enabled"].set_active(config.get("scheduled_scans_enabled", False))

        # Frequency dropdown
        freq = config.get("schedule_frequency", "daily")
        freq_map = {"hourly": 0, "daily": 1, "weekly": 2, "monthly": 3}
        widgets_dict["frequency"].set_selected(freq_map.get(freq, 1))

        # Time entry
        widgets_dict["time"].set_text(config.get("schedule_time", "02:00"))

        # Targets entry
        targets = config.get("schedule_targets", [])
        if targets:
            widgets_dict["targets"].set_text(", ".join(targets))
        else:
            widgets_dict["targets"].set_text(str(Path.home()))

        # Day of week dropdown
        widgets_dict["day_of_week"].set_selected(config.get("schedule_day_of_week", 0))

        # Day of month spinner
        widgets_dict["day_of_month"].set_value(config.get("schedule_day_of_month", 1))

        # Skip on battery switch
        widgets_dict["skip_on_battery"].set_active(config.get("schedule_skip_on_battery", True))

        # Auto-quarantine switch
        widgets_dict["auto_quarantine"].set_active(config.get("schedule_auto_quarantine", False))

    @staticmethod
    def collect_data(widgets_dict: dict) -> dict:
        """
        Collect scheduled scan configuration from form widgets.

        Reads the current state of all widgets and returns a dictionary
        of scheduled scan settings ready to be saved.

        Args:
            widgets_dict: Dictionary of widget references

        Returns:
            Dictionary of scheduled scan settings to save
        """
        frequency_map = ["hourly", "daily", "weekly", "monthly"]
        selected_frequency = widgets_dict["frequency"].get_selected()

        # Parse targets from comma-separated string
        targets_text = widgets_dict["targets"].get_text()
        targets = [t.strip() for t in targets_text.split(",") if t.strip()]

        return {
            "scheduled_scans_enabled": widgets_dict["enabled"].get_active(),
            "schedule_frequency": frequency_map[selected_frequency]
            if selected_frequency < len(frequency_map)
            else "daily",
            "schedule_time": widgets_dict["time"].get_text().strip() or "02:00",
            "schedule_targets": targets,
            "schedule_day_of_week": widgets_dict["day_of_week"].get_selected(),
            "schedule_day_of_month": int(widgets_dict["day_of_month"].get_value()),
            "schedule_skip_on_battery": widgets_dict["skip_on_battery"].get_active(),
            "schedule_auto_quarantine": widgets_dict["auto_quarantine"].get_active(),
        }
