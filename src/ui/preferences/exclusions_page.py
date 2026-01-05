# ClamUI Exclusions Page
"""
Exclusions preference page for scan exclusion patterns.

This module provides the ExclusionsPage class which handles the UI and logic
for managing scan exclusion patterns, including preset and custom exclusions.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from .base import PreferencesPageMixin

# Preset exclusion templates for common development directories
# These are directory patterns commonly excluded from scans for performance
PRESET_EXCLUSIONS = [
    {
        "pattern": "node_modules",
        "type": "directory",
        "enabled": True,
        "description": "Node.js dependencies",
    },
    {"pattern": ".git", "type": "directory", "enabled": True, "description": "Git repository data"},
    {
        "pattern": ".venv",
        "type": "directory",
        "enabled": True,
        "description": "Python virtual environment",
    },
    {
        "pattern": "build",
        "type": "directory",
        "enabled": True,
        "description": "Build output directory",
    },
    {
        "pattern": "dist",
        "type": "directory",
        "enabled": True,
        "description": "Distribution output directory",
    },
    {
        "pattern": "__pycache__",
        "type": "directory",
        "enabled": True,
        "description": "Python bytecode cache",
    },
]


class ExclusionsPage(PreferencesPageMixin):
    """
    Exclusions preference page for scan exclusion patterns.

    This class creates and manages the UI for scan exclusion patterns,
    including preset exclusions for common development directories and
    custom user-defined patterns.

    The page includes:
    - Preset exclusions (common patterns like node_modules, .git, etc.)
    - Custom exclusions with add/remove/toggle functionality
    - Auto-save for all exclusion changes

    Note: This class uses PreferencesPageMixin for shared utilities. Exclusion
    patterns are stored in ClamUI settings (not ClamAV config files) and are
    auto-saved when modified.
    """

    def __init__(self, settings_manager=None):
        """
        Initialize the ExclusionsPage.

        Args:
            settings_manager: Optional SettingsManager instance for storing exclusion patterns
        """
        self._settings_manager = settings_manager
        self._custom_exclusions_group = None
        self._custom_entry_row = None

    def create_page(self) -> Adw.PreferencesPage:
        """
        Create the Exclusions preference page.

        Returns:
            Configured Adw.PreferencesPage ready to be added to preferences window
        """
        page = Adw.PreferencesPage(
            title="Exclusions",
            icon_name="action-unavailable-symbolic",
        )

        # Preset exclusions group
        preset_group = Adw.PreferencesGroup()
        preset_group.set_title("Preset Exclusions (Auto-Saved)")
        preset_group.set_description("Common patterns to exclude. Auto-saved.")

        for preset in PRESET_EXCLUSIONS:
            # Create a row for each preset
            row = Adw.SwitchRow()
            row.set_title(preset["description"])
            row.set_subtitle(preset["pattern"])
            row.set_active(preset["enabled"])
            preset_group.add(row)

        page.add(preset_group)

        # Custom exclusions group
        self._custom_exclusions_group = Adw.PreferencesGroup()
        self._custom_exclusions_group.set_title("Custom Exclusions (Auto-Saved)")
        self._custom_exclusions_group.set_description("Your exclusion patterns. Auto-saved.")

        # Custom exclusion entry row
        self._custom_entry_row = Adw.EntryRow()
        self._custom_entry_row.set_title("Add Pattern (e.g., /path/to/exclude or *.tmp)")
        self._custom_entry_row.set_show_apply_button(False)

        # Add button for custom exclusions
        add_button = Gtk.Button()
        add_button.set_label("Add")
        add_button.set_valign(Gtk.Align.CENTER)
        add_button.set_tooltip_text("Add custom exclusion pattern")
        add_button.connect("clicked", self._on_add_custom_exclusion)
        self._custom_entry_row.add_suffix(add_button)

        self._custom_exclusions_group.add(self._custom_entry_row)

        # Load and display existing custom exclusions
        self._load_custom_exclusions()

        page.add(self._custom_exclusions_group)

        return page

    def _load_custom_exclusions(self):
        """Load and display custom exclusions from settings."""
        if self._settings_manager is None:
            return

        exclusions = self._settings_manager.get("exclusion_patterns", [])
        if not isinstance(exclusions, list):
            return

        for exclusion in exclusions:
            pattern = exclusion.get("pattern", "")
            if pattern:
                self._add_custom_exclusion_row(pattern, exclusion.get("enabled", True))

    def _add_custom_exclusion_row(self, pattern: str, enabled: bool = True):
        """
        Add a row for a custom exclusion pattern.

        Args:
            pattern: The exclusion pattern to add
            enabled: Whether the exclusion is enabled (default: True)
        """
        row = Adw.SwitchRow()
        row.set_title(pattern)
        row.set_active(enabled)

        # Connect switch to save enabled state
        row.connect("notify::active", self._on_exclusion_toggled, pattern)

        # Remove button
        remove_button = Gtk.Button()
        remove_button.set_icon_name("user-trash-symbolic")
        remove_button.set_valign(Gtk.Align.CENTER)
        remove_button.add_css_class("flat")
        remove_button.set_tooltip_text("Remove exclusion")
        remove_button.connect("clicked", self._on_remove_custom_exclusion, row, pattern)
        row.add_suffix(remove_button)

        # Insert before the entry row (which is always last)
        self._custom_exclusions_group.add(row)

    def _on_exclusion_toggled(self, row, param_spec, pattern: str):
        """
        Handle exclusion toggle state change.

        Args:
            row: The SwitchRow that was toggled
            param_spec: Parameter specification (unused)
            pattern: The pattern that was toggled
        """
        if self._settings_manager is None:
            return

        enabled = row.get_active()
        exclusions = self._settings_manager.get("exclusion_patterns", [])
        if isinstance(exclusions, list):
            for excl in exclusions:
                if excl.get("pattern") == pattern:
                    excl["enabled"] = enabled
                    break
            self._settings_manager.set("exclusion_patterns", exclusions)

    def _on_add_custom_exclusion(self, button):
        """
        Handle adding a new custom exclusion.

        Args:
            button: The button that was clicked (unused)
        """
        pattern = self._custom_entry_row.get_text().strip()
        if not pattern:
            return

        if self._settings_manager is None:
            return

        # Get current exclusions
        exclusions = self._settings_manager.get("exclusion_patterns", [])
        if not isinstance(exclusions, list):
            exclusions = []

        # Check if already exists
        for excl in exclusions:
            if excl.get("pattern") == pattern:
                return  # Already exists

        # Add new exclusion
        new_exclusion = {
            "pattern": pattern,
            "type": "file" if pattern.startswith("/") else "pattern",
            "enabled": True,
        }
        exclusions.append(new_exclusion)
        self._settings_manager.set("exclusion_patterns", exclusions)

        # Add row to UI
        self._add_custom_exclusion_row(pattern, True)

        # Clear entry
        self._custom_entry_row.set_text("")

    def _on_remove_custom_exclusion(self, button, row, pattern: str):
        """
        Handle removing a custom exclusion.

        Args:
            button: The button that was clicked (unused)
            row: The row to remove
            pattern: The pattern to remove
        """
        if self._settings_manager is None:
            return

        # Remove from settings
        exclusions = self._settings_manager.get("exclusion_patterns", [])
        if isinstance(exclusions, list):
            exclusions = [e for e in exclusions if e.get("pattern") != pattern]
            self._settings_manager.set("exclusion_patterns", exclusions)

        # Remove row from UI
        self._custom_exclusions_group.remove(row)
