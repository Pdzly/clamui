# ClamUI Profile Dialogs
"""
Dialog components for creating and editing scan profiles.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..profiles.models import ScanProfile
    from ..profiles.profile_manager import ProfileManager


class ProfileDialog(Adw.Dialog):
    """
    A dialog for creating or editing scan profiles.

    Provides a form interface for configuring profile settings including:
    - Profile name and description
    - Target directories/files to scan
    - Exclusion paths and patterns

    Usage:
        # Create new profile
        dialog = ProfileDialog(profile_manager=app.profile_manager)
        dialog.present(parent_window)

        # Edit existing profile
        dialog = ProfileDialog(profile_manager=app.profile_manager, profile=existing_profile)
        dialog.present(parent_window)
    """

    # Maximum profile name length
    MAX_NAME_LENGTH = 50

    def __init__(
        self,
        profile_manager: "ProfileManager" = None,
        profile: "ScanProfile" = None,
        **kwargs
    ):
        """
        Initialize the profile dialog.

        Args:
            profile_manager: The ProfileManager instance for saving profiles.
                             If None, changes won't be persisted.
            profile: Optional existing profile to edit. If None, creates a new profile.
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(**kwargs)

        self._profile_manager = profile_manager
        self._profile = profile
        self._is_edit_mode = profile is not None

        # Target and exclusion lists
        self._targets: list[str] = []
        self._exclusion_paths: list[str] = []
        self._exclusion_patterns: list[str] = []

        # Callback for when a profile is saved
        self._on_profile_saved = None

        # Configure the dialog
        self._setup_dialog()

        # Set up the UI
        self._setup_ui()

        # Load existing profile data if editing
        if self._is_edit_mode:
            self._load_profile_data()

    def _setup_dialog(self):
        """Configure the dialog properties."""
        if self._is_edit_mode:
            self.set_title("Edit Profile")
        else:
            self.set_title("New Profile")

        self.set_content_width(500)
        self.set_content_height(600)
        self.set_can_close(True)

    def _setup_ui(self):
        """Set up the dialog UI layout."""
        # Create main container with toolbar view for header bar
        toolbar_view = Adw.ToolbarView()

        # Create header bar with save button
        header_bar = Adw.HeaderBar()

        # Cancel button
        cancel_button = Gtk.Button()
        cancel_button.set_label("Cancel")
        cancel_button.connect("clicked", self._on_cancel_clicked)
        header_bar.pack_start(cancel_button)

        # Save button
        self._save_button = Gtk.Button()
        self._save_button.set_label("Save")
        self._save_button.add_css_class("suggested-action")
        self._save_button.connect("clicked", self._on_save_clicked)
        header_bar.pack_end(self._save_button)

        toolbar_view.add_top_bar(header_bar)

        # Create scrolled window for content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Create preferences page using Adwaita patterns
        preferences_page = Adw.PreferencesPage()

        # Basic info group
        self._create_basic_info_group(preferences_page)

        # Targets group
        self._create_targets_group(preferences_page)

        # Exclusions group
        self._create_exclusions_group(preferences_page)

        scrolled.set_child(preferences_page)
        toolbar_view.set_content(scrolled)

        # Set the toolbar view as the dialog child
        self.set_child(toolbar_view)

    def _create_basic_info_group(self, preferences_page: Adw.PreferencesPage):
        """Create the basic profile info group."""
        basic_group = Adw.PreferencesGroup()
        basic_group.set_title("Profile Information")
        basic_group.set_description("Basic profile settings")

        # Profile name entry row
        # Note: Adw.EntryRow doesn't have set_max_length - validation is done in _on_name_changed
        self._name_row = Adw.EntryRow()
        self._name_row.set_title("Name")
        self._name_row.connect("changed", self._on_name_changed)
        basic_group.add(self._name_row)

        # Description entry row
        self._description_row = Adw.EntryRow()
        self._description_row.set_title("Description")
        basic_group.add(self._description_row)

        # Validation message (hidden by default)
        self._validation_label = Gtk.Label()
        self._validation_label.set_halign(Gtk.Align.START)
        self._validation_label.set_margin_start(12)
        self._validation_label.set_margin_top(6)
        self._validation_label.add_css_class("error")
        self._validation_label.set_visible(False)
        basic_group.add(self._validation_label)

        preferences_page.add(basic_group)

    def _create_targets_group(self, preferences_page: Adw.PreferencesPage):
        """Create the scan targets group."""
        targets_group = Adw.PreferencesGroup()
        targets_group.set_title("Scan Targets")
        targets_group.set_description("Directories and files to scan")

        # Add target buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)

        add_folder_btn = Gtk.Button()
        add_folder_btn.set_icon_name("folder-new-symbolic")
        add_folder_btn.set_tooltip_text("Add folder")
        add_folder_btn.add_css_class("flat")
        add_folder_btn.connect("clicked", self._on_add_target_folder_clicked)
        button_box.append(add_folder_btn)

        add_file_btn = Gtk.Button()
        add_file_btn.set_icon_name("document-new-symbolic")
        add_file_btn.set_tooltip_text("Add file")
        add_file_btn.add_css_class("flat")
        add_file_btn.connect("clicked", self._on_add_target_file_clicked)
        button_box.append(add_file_btn)

        targets_group.set_header_suffix(button_box)

        # Targets list box
        self._targets_listbox = Gtk.ListBox()
        self._targets_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._targets_listbox.add_css_class("boxed-list")

        # Placeholder for empty list
        self._targets_placeholder = Adw.ActionRow()
        self._targets_placeholder.set_title("No targets added")
        self._targets_placeholder.set_subtitle("Click the folder or file button to add scan targets")
        self._targets_placeholder.set_icon_name("folder-symbolic")
        self._targets_placeholder.add_css_class("dim-label")
        self._targets_listbox.append(self._targets_placeholder)

        targets_group.add(self._targets_listbox)
        preferences_page.add(targets_group)

    def _create_exclusions_group(self, preferences_page: Adw.PreferencesPage):
        """Create the exclusions group."""
        exclusions_group = Adw.PreferencesGroup()
        exclusions_group.set_title("Exclusions")
        exclusions_group.set_description("Paths and patterns to skip during scan")

        # Add exclusion buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)

        add_path_btn = Gtk.Button()
        add_path_btn.set_icon_name("folder-new-symbolic")
        add_path_btn.set_tooltip_text("Add exclusion path")
        add_path_btn.add_css_class("flat")
        add_path_btn.connect("clicked", self._on_add_exclusion_path_clicked)
        button_box.append(add_path_btn)

        add_pattern_btn = Gtk.Button()
        add_pattern_btn.set_icon_name("edit-symbolic")
        add_pattern_btn.set_tooltip_text("Add exclusion pattern")
        add_pattern_btn.add_css_class("flat")
        add_pattern_btn.connect("clicked", self._on_add_exclusion_pattern_clicked)
        button_box.append(add_pattern_btn)

        exclusions_group.set_header_suffix(button_box)

        # Exclusions list box
        self._exclusions_listbox = Gtk.ListBox()
        self._exclusions_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._exclusions_listbox.add_css_class("boxed-list")

        # Placeholder for empty list
        self._exclusions_placeholder = Adw.ActionRow()
        self._exclusions_placeholder.set_title("No exclusions added")
        self._exclusions_placeholder.set_subtitle("Add paths or patterns to exclude from scanning")
        self._exclusions_placeholder.set_icon_name("action-unavailable-symbolic")
        self._exclusions_placeholder.add_css_class("dim-label")
        self._exclusions_listbox.append(self._exclusions_placeholder)

        exclusions_group.add(self._exclusions_listbox)
        preferences_page.add(exclusions_group)

    def _load_profile_data(self):
        """Load existing profile data into the form."""
        if self._profile is None:
            return

        # Set basic info
        self._name_row.set_text(self._profile.name)
        self._description_row.set_text(self._profile.description or "")

        # Load targets
        for target in self._profile.targets:
            self._add_target_to_list(target)

        # Load exclusions
        exclusions = self._profile.exclusions or {}
        for path in exclusions.get("paths", []):
            self._add_exclusion_path_to_list(path)
        for pattern in exclusions.get("patterns", []):
            self._add_exclusion_pattern_to_list(pattern)

    def _on_name_changed(self, entry_row):
        """Handle name entry changes for validation."""
        name = entry_row.get_text().strip()

        if not name:
            self._show_validation_error("Profile name is required")
            self._save_button.set_sensitive(False)
        elif len(name) > self.MAX_NAME_LENGTH:
            self._show_validation_error(f"Name must be {self.MAX_NAME_LENGTH} characters or less")
            self._save_button.set_sensitive(False)
        else:
            self._hide_validation_error()
            self._save_button.set_sensitive(True)

    def _show_validation_error(self, message: str):
        """Show a validation error message."""
        self._validation_label.set_text(message)
        self._validation_label.set_visible(True)

    def _hide_validation_error(self):
        """Hide the validation error message."""
        self._validation_label.set_visible(False)

    def _on_add_target_folder_clicked(self, button):
        """Handle add target folder button click."""
        self._open_file_dialog(select_folder=True, callback=self._on_target_selected)

    def _on_add_target_file_clicked(self, button):
        """Handle add target file button click."""
        self._open_file_dialog(select_folder=False, callback=self._on_target_selected)

    def _on_add_exclusion_path_clicked(self, button):
        """Handle add exclusion path button click."""
        self._open_file_dialog(select_folder=True, callback=self._on_exclusion_path_selected)

    def _on_add_exclusion_pattern_clicked(self, button):
        """Handle add exclusion pattern button click."""
        # Show pattern entry dialog
        dialog = PatternEntryDialog()
        dialog.connect("response", self._on_pattern_dialog_response)
        dialog.present(self.get_root())

    def _on_pattern_dialog_response(self, dialog, response):
        """Handle pattern entry dialog response."""
        if response == "add":
            pattern = dialog.get_pattern()
            if pattern and pattern not in self._exclusion_patterns:
                self._add_exclusion_pattern_to_list(pattern)

    def _open_file_dialog(self, select_folder: bool, callback):
        """
        Open a file/folder selection dialog.

        Args:
            select_folder: True to select folders, False for files
            callback: Callback function to handle the selection
        """
        dialog = Gtk.FileDialog()

        if select_folder:
            dialog.set_title("Select Folder")
        else:
            dialog.set_title("Select File")

        # Get the parent window
        window = self.get_root()

        if select_folder:
            dialog.select_folder(window, None, callback)
        else:
            dialog.open(window, None, callback)

    def _on_target_selected(self, dialog, result):
        """Handle target selection result."""
        try:
            if hasattr(dialog, 'select_folder_finish'):
                try:
                    folder = dialog.select_folder_finish(result)
                    if folder:
                        path = folder.get_path()
                        if path and path not in self._targets:
                            self._add_target_to_list(path)
                    return
                except GLib.Error:
                    pass

            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                if path and path not in self._targets:
                    self._add_target_to_list(path)
        except GLib.Error:
            pass  # User cancelled

    def _on_exclusion_path_selected(self, dialog, result):
        """Handle exclusion path selection result."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                if path and path not in self._exclusion_paths:
                    self._add_exclusion_path_to_list(path)
        except GLib.Error:
            pass  # User cancelled

    def _add_target_to_list(self, path: str):
        """Add a target path to the list UI."""
        # Remove placeholder if this is the first target
        if not self._targets:
            self._targets_listbox.remove(self._targets_placeholder)

        self._targets.append(path)

        # Create target row
        row = self._create_path_row(
            path=path,
            icon_name="folder-symbolic",
            on_remove=lambda: self._remove_target(path)
        )
        self._targets_listbox.append(row)

    def _add_exclusion_path_to_list(self, path: str):
        """Add an exclusion path to the list UI."""
        # Remove placeholder if this is the first exclusion
        if not self._exclusion_paths and not self._exclusion_patterns:
            self._exclusions_listbox.remove(self._exclusions_placeholder)

        self._exclusion_paths.append(path)

        # Create exclusion row
        row = self._create_path_row(
            path=path,
            icon_name="folder-symbolic",
            on_remove=lambda: self._remove_exclusion_path(path),
            subtitle="Path"
        )
        self._exclusions_listbox.append(row)

    def _add_exclusion_pattern_to_list(self, pattern: str):
        """Add an exclusion pattern to the list UI."""
        # Remove placeholder if this is the first exclusion
        if not self._exclusion_paths and not self._exclusion_patterns:
            self._exclusions_listbox.remove(self._exclusions_placeholder)

        self._exclusion_patterns.append(pattern)

        # Create pattern row
        row = self._create_path_row(
            path=pattern,
            icon_name="edit-symbolic",
            on_remove=lambda: self._remove_exclusion_pattern(pattern),
            subtitle="Pattern"
        )
        self._exclusions_listbox.append(row)

    def _create_path_row(
        self,
        path: str,
        icon_name: str,
        on_remove,
        subtitle: str = None
    ) -> Adw.ActionRow:
        """
        Create a row for displaying a path with remove button.

        Args:
            path: The path or pattern to display
            icon_name: Icon name to show
            on_remove: Callback when remove is clicked
            subtitle: Optional subtitle text

        Returns:
            Configured Adw.ActionRow
        """
        row = Adw.ActionRow()
        row.set_title(path)
        if subtitle:
            row.set_subtitle(subtitle)
        row.set_icon_name(icon_name)

        # Remove button
        remove_btn = Gtk.Button()
        remove_btn.set_icon_name("user-trash-symbolic")
        remove_btn.set_tooltip_text("Remove")
        remove_btn.add_css_class("flat")
        remove_btn.add_css_class("error")
        remove_btn.set_valign(Gtk.Align.CENTER)
        remove_btn.connect("clicked", lambda btn: self._handle_remove(row, on_remove))

        row.add_suffix(remove_btn)
        return row

    def _handle_remove(self, row: Adw.ActionRow, on_remove):
        """Handle remove button click."""
        # Get the parent listbox
        parent = row.get_parent()
        if parent:
            parent.remove(row)
        on_remove()

        # Restore placeholder if lists are empty
        self._update_placeholders()

    def _remove_target(self, path: str):
        """Remove a target path."""
        if path in self._targets:
            self._targets.remove(path)

    def _remove_exclusion_path(self, path: str):
        """Remove an exclusion path."""
        if path in self._exclusion_paths:
            self._exclusion_paths.remove(path)

    def _remove_exclusion_pattern(self, pattern: str):
        """Remove an exclusion pattern."""
        if pattern in self._exclusion_patterns:
            self._exclusion_patterns.remove(pattern)

    def _update_placeholders(self):
        """Update placeholder visibility for empty lists."""
        # Targets placeholder
        if not self._targets:
            # Check if placeholder already exists
            first_row = self._targets_listbox.get_row_at_index(0)
            if first_row is None:
                self._targets_listbox.append(self._targets_placeholder)

        # Exclusions placeholder
        if not self._exclusion_paths and not self._exclusion_patterns:
            first_row = self._exclusions_listbox.get_row_at_index(0)
            if first_row is None:
                self._exclusions_listbox.append(self._exclusions_placeholder)

    def _on_cancel_clicked(self, button):
        """Handle cancel button click."""
        self.close()

    def _on_save_clicked(self, button):
        """Handle save button click."""
        name = self._name_row.get_text().strip()
        description = self._description_row.get_text().strip()

        # Validate name
        if not name:
            self._show_validation_error("Profile name is required")
            return

        # Build exclusions dictionary
        exclusions = {}
        if self._exclusion_paths:
            exclusions["paths"] = self._exclusion_paths.copy()
        if self._exclusion_patterns:
            exclusions["patterns"] = self._exclusion_patterns.copy()

        # Save profile
        if self._profile_manager is not None:
            try:
                if self._is_edit_mode and self._profile:
                    # Update existing profile
                    self._profile_manager.update_profile(
                        self._profile.id,
                        name=name,
                        description=description,
                        targets=self._targets.copy(),
                        exclusions=exclusions
                    )
                    saved_profile = self._profile_manager.get_profile(self._profile.id)
                else:
                    # Create new profile
                    saved_profile = self._profile_manager.create_profile(
                        name=name,
                        targets=self._targets.copy(),
                        exclusions=exclusions,
                        description=description
                    )

                # Notify callback
                if self._on_profile_saved:
                    self._on_profile_saved(saved_profile)

                self.close()

            except ValueError as e:
                self._show_validation_error(str(e))
        else:
            self.close()

    def set_on_profile_saved(self, callback):
        """
        Set callback for when a profile is saved.

        Args:
            callback: Callable that receives the saved ScanProfile
        """
        self._on_profile_saved = callback

    def get_profile_data(self) -> dict:
        """
        Get the current profile data from the form.

        Returns:
            Dictionary with profile data
        """
        exclusions = {}
        if self._exclusion_paths:
            exclusions["paths"] = self._exclusion_paths.copy()
        if self._exclusion_patterns:
            exclusions["patterns"] = self._exclusion_patterns.copy()

        return {
            "name": self._name_row.get_text().strip(),
            "description": self._description_row.get_text().strip(),
            "targets": self._targets.copy(),
            "exclusions": exclusions,
        }


class PatternEntryDialog(Adw.Dialog):
    """
    A simple dialog for entering exclusion patterns.

    Usage:
        dialog = PatternEntryDialog()
        dialog.connect("response", on_response)
        dialog.present(parent_window)
    """

    def __init__(self, **kwargs):
        """Initialize the pattern entry dialog."""
        super().__init__(**kwargs)

        self.set_title("Add Exclusion Pattern")
        self.set_content_width(400)
        self.set_content_height(200)
        self.set_can_close(True)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Create main container
        toolbar_view = Adw.ToolbarView()

        # Header bar
        header_bar = Adw.HeaderBar()

        cancel_button = Gtk.Button()
        cancel_button.set_label("Cancel")
        cancel_button.connect("clicked", self._on_cancel_clicked)
        header_bar.pack_start(cancel_button)

        add_button = Gtk.Button()
        add_button.set_label("Add")
        add_button.add_css_class("suggested-action")
        add_button.connect("clicked", self._on_add_clicked)
        self._add_button = add_button
        header_bar.pack_end(add_button)

        toolbar_view.add_top_bar(header_bar)

        # Content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)

        # Pattern entry group
        pattern_group = Adw.PreferencesGroup()
        pattern_group.set_description(
            "Enter a glob pattern to exclude (e.g., *.tmp, .git/*, cache/*)"
        )

        self._pattern_row = Adw.EntryRow()
        self._pattern_row.set_title("Pattern")
        self._pattern_row.connect("changed", self._on_pattern_changed)
        self._pattern_row.connect("entry-activated", lambda r: self._on_add_clicked(None))
        pattern_group.add(self._pattern_row)

        content_box.append(pattern_group)

        toolbar_view.set_content(content_box)
        self.set_child(toolbar_view)

    def _on_pattern_changed(self, entry_row):
        """Handle pattern entry changes."""
        pattern = entry_row.get_text().strip()
        self._add_button.set_sensitive(bool(pattern))

    def _on_cancel_clicked(self, button):
        """Handle cancel button click."""
        self.emit("response", "cancel")
        self.close()

    def _on_add_clicked(self, button):
        """Handle add button click."""
        pattern = self._pattern_row.get_text().strip()
        if pattern:
            self.emit("response", "add")
            self.close()

    def get_pattern(self) -> str:
        """Get the entered pattern."""
        return self._pattern_row.get_text().strip()


class DeleteProfileDialog(Adw.AlertDialog):
    """
    Confirmation dialog for deleting a profile.

    Usage:
        dialog = DeleteProfileDialog(profile_name="Quick Scan")
        dialog.connect("response", on_response)
        dialog.present(parent_window)
    """

    def __init__(self, profile_name: str, **kwargs):
        """
        Initialize the delete confirmation dialog.

        Args:
            profile_name: Name of the profile to delete
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(**kwargs)

        self.set_heading("Delete Profile?")
        self.set_body(
            f'Are you sure you want to delete the profile "{profile_name}"?\n\n'
            "This action cannot be undone."
        )

        self.add_response("cancel", "Cancel")
        self.add_response("delete", "Delete")

        self.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        self.set_default_response("cancel")
        self.set_close_response("cancel")


class ProfileListDialog(Adw.Dialog):
    """
    A dialog for managing scan profiles.

    Displays a list of all profiles with options to create, edit, and delete profiles.

    Usage:
        dialog = ProfileListDialog(profile_manager=app.profile_manager)
        dialog.present(parent_window)
    """

    def __init__(
        self,
        profile_manager: "ProfileManager" = None,
        **kwargs
    ):
        """
        Initialize the profile list dialog.

        Args:
            profile_manager: The ProfileManager instance for profile operations.
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(**kwargs)

        self._profile_manager = profile_manager

        # Callback for when a profile is selected for use
        self._on_profile_selected = None

        # Configure the dialog
        self._setup_dialog()

        # Set up the UI
        self._setup_ui()

        # Load profiles
        self._refresh_profile_list()

    def _setup_dialog(self):
        """Configure the dialog properties."""
        self.set_title("Manage Profiles")
        self.set_content_width(500)
        self.set_content_height(500)
        self.set_can_close(True)

    def _setup_ui(self):
        """Set up the dialog UI layout."""
        # Create main container with toolbar view for header bar
        toolbar_view = Adw.ToolbarView()

        # Create header bar with new profile button
        header_bar = Adw.HeaderBar()

        # Close button
        close_button = Gtk.Button()
        close_button.set_label("Close")
        close_button.connect("clicked", self._on_close_clicked)
        header_bar.pack_start(close_button)

        # Import profile button
        import_button = Gtk.Button()
        import_button.set_icon_name("document-open-symbolic")
        import_button.set_tooltip_text("Import profile from file")
        import_button.connect("clicked", self._on_import_clicked)
        header_bar.pack_end(import_button)

        # New profile button
        new_profile_button = Gtk.Button()
        new_profile_button.set_icon_name("list-add-symbolic")
        new_profile_button.set_tooltip_text("Create new profile")
        new_profile_button.add_css_class("suggested-action")
        new_profile_button.connect("clicked", self._on_new_profile_clicked)
        header_bar.pack_end(new_profile_button)

        toolbar_view.add_top_bar(header_bar)

        # Create scrolled window for content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Create preferences page using Adwaita patterns
        preferences_page = Adw.PreferencesPage()

        # Profiles group
        self._profiles_group = Adw.PreferencesGroup()
        self._profiles_group.set_title("Scan Profiles")
        self._profiles_group.set_description("Select a profile to edit or use for scanning")

        # Profiles list box
        self._profiles_listbox = Gtk.ListBox()
        self._profiles_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._profiles_listbox.add_css_class("boxed-list")

        # Placeholder for empty list
        self._profiles_placeholder = Adw.ActionRow()
        self._profiles_placeholder.set_title("No profiles available")
        self._profiles_placeholder.set_subtitle("Click the + button to create a new profile")
        self._profiles_placeholder.set_icon_name("document-new-symbolic")
        self._profiles_placeholder.add_css_class("dim-label")

        self._profiles_group.add(self._profiles_listbox)
        preferences_page.add(self._profiles_group)

        scrolled.set_child(preferences_page)
        toolbar_view.set_content(scrolled)

        # Set the toolbar view as the dialog child
        self.set_child(toolbar_view)

    def _refresh_profile_list(self):
        """Refresh the profile list from the profile manager."""
        # Clear existing rows
        while True:
            row = self._profiles_listbox.get_row_at_index(0)
            if row is None:
                break
            self._profiles_listbox.remove(row)

        # Get profiles from manager
        if self._profile_manager is None:
            self._profiles_listbox.append(self._profiles_placeholder)
            return

        profiles = self._profile_manager.list_profiles()

        if not profiles:
            self._profiles_listbox.append(self._profiles_placeholder)
            return

        # Add profile rows
        for profile in profiles:
            row = self._create_profile_row(profile)
            self._profiles_listbox.append(row)

    def _create_profile_row(self, profile: "ScanProfile") -> Adw.ActionRow:
        """
        Create a row for displaying a profile with action buttons.

        Args:
            profile: The ScanProfile to display

        Returns:
            Configured Adw.ActionRow
        """
        row = Adw.ActionRow()
        row.set_title(profile.name)

        # Build subtitle with profile details
        subtitle_parts = []
        if profile.description:
            subtitle_parts.append(profile.description)
        target_count = len(profile.targets) if profile.targets else 0
        if target_count > 0:
            subtitle_parts.append(f"{target_count} target(s)")
        if profile.is_default:
            subtitle_parts.append("Default profile")

        if subtitle_parts:
            row.set_subtitle(" • ".join(subtitle_parts))

        # Set icon based on profile type
        if profile.is_default:
            row.set_icon_name("emblem-default-symbolic")
        else:
            row.set_icon_name("document-properties-symbolic")

        # Action buttons container
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_valign(Gtk.Align.CENTER)

        # Use profile button
        use_button = Gtk.Button()
        use_button.set_icon_name("media-playback-start-symbolic")
        use_button.set_tooltip_text("Use this profile")
        use_button.add_css_class("flat")
        use_button.add_css_class("success")
        use_button.connect("clicked", lambda btn, p=profile: self._on_use_profile_clicked(p))
        button_box.append(use_button)

        # Edit button
        edit_button = Gtk.Button()
        edit_button.set_icon_name("document-edit-symbolic")
        edit_button.set_tooltip_text("Edit profile")
        edit_button.add_css_class("flat")
        edit_button.connect("clicked", lambda btn, p=profile: self._on_edit_profile_clicked(p))
        button_box.append(edit_button)

        # Delete button (disabled for default profiles)
        delete_button = Gtk.Button()
        delete_button.set_icon_name("user-trash-symbolic")
        delete_button.set_tooltip_text("Delete profile")
        delete_button.add_css_class("flat")
        if profile.is_default:
            delete_button.set_sensitive(False)
            delete_button.set_tooltip_text("Cannot delete default profile")
        else:
            delete_button.add_css_class("error")
            delete_button.connect(
                "clicked", lambda btn, p=profile: self._on_delete_profile_clicked(p)
            )
        button_box.append(delete_button)

        # Export button
        export_button = Gtk.Button()
        export_button.set_icon_name("document-save-symbolic")
        export_button.set_tooltip_text("Export profile")
        export_button.add_css_class("flat")
        export_button.connect("clicked", lambda btn, p=profile: self._on_export_profile_clicked(p))
        button_box.append(export_button)

        row.add_suffix(button_box)
        row.set_activatable(True)
        row.connect("activated", lambda r, p=profile: self._on_use_profile_clicked(p))

        return row

    def _on_close_clicked(self, button):
        """Handle close button click."""
        self.close()

    def _on_import_clicked(self, button):
        """Handle import button click."""
        self.import_profile()

    def _on_new_profile_clicked(self, button):
        """Handle new profile button click."""
        dialog = ProfileDialog(profile_manager=self._profile_manager)
        dialog.set_on_profile_saved(self._on_profile_saved)
        dialog.present(self.get_root())

    def _on_edit_profile_clicked(self, profile: "ScanProfile"):
        """
        Handle edit profile button click.

        Args:
            profile: The profile to edit
        """
        dialog = ProfileDialog(profile_manager=self._profile_manager, profile=profile)
        dialog.set_on_profile_saved(self._on_profile_saved)
        dialog.present(self.get_root())

    def _on_delete_profile_clicked(self, profile: "ScanProfile"):
        """
        Handle delete profile button click.

        Args:
            profile: The profile to delete
        """
        dialog = DeleteProfileDialog(profile_name=profile.name)
        dialog.connect("response", lambda d, r, p=profile: self._on_delete_response(r, p))
        dialog.present(self.get_root())

    def _on_delete_response(self, response: str, profile: "ScanProfile"):
        """
        Handle delete confirmation dialog response.

        Args:
            response: The dialog response ("delete" or "cancel")
            profile: The profile to delete
        """
        if response == "delete" and self._profile_manager is not None:
            try:
                self._profile_manager.delete_profile(profile.id)
                self._refresh_profile_list()
            except ValueError:
                # Cannot delete default profile - should not happen since button is disabled
                pass

    def _on_use_profile_clicked(self, profile: "ScanProfile"):
        """
        Handle use profile button click.

        Args:
            profile: The profile to use
        """
        if self._on_profile_selected:
            self._on_profile_selected(profile)
        self.close()

    def _on_export_profile_clicked(self, profile: "ScanProfile"):
        """
        Handle export profile button click.

        Args:
            profile: The profile to export
        """
        if self._profile_manager is None:
            return

        # Create save dialog
        dialog = Gtk.FileDialog()
        dialog.set_title("Export Profile")

        # Generate default filename from profile name
        safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in profile.name)
        dialog.set_initial_name(f"{safe_name}.json")

        # Set up file filter for JSON files
        json_filter = Gtk.FileFilter()
        json_filter.set_name("JSON Files")
        json_filter.add_mime_type("application/json")
        json_filter.add_pattern("*.json")

        from gi.repository import Gio
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(json_filter)
        dialog.set_filters(filters)
        dialog.set_default_filter(json_filter)

        # Get the parent window
        window = self.get_root()

        # Store profile ID for callback
        self._exporting_profile_id = profile.id

        # Open save dialog
        dialog.save(window, None, self._on_export_file_selected)

    def _on_export_file_selected(self, dialog, result):
        """
        Handle export file selection result.

        Args:
            dialog: The FileDialog that was used
            result: The async result from the save dialog
        """
        try:
            file = dialog.save_finish(result)
            if file is None:
                return  # User cancelled

            file_path = file.get_path()
            if file_path is None:
                return

            # Ensure .json extension
            if not file_path.endswith('.json'):
                file_path += '.json'

            # Export the profile
            from pathlib import Path
            self._profile_manager.export_profile(
                self._exporting_profile_id,
                Path(file_path)
            )

        except GLib.Error:
            # User cancelled the dialog
            pass
        except (ValueError, OSError):
            # Export failed - could show an error dialog
            pass

    def _on_profile_saved(self, profile: "ScanProfile"):
        """
        Handle profile saved callback from ProfileDialog.

        Args:
            profile: The saved profile
        """
        self._refresh_profile_list()

    def set_on_profile_selected(self, callback):
        """
        Set callback for when a profile is selected for use.

        Args:
            callback: Callable that receives the selected ScanProfile
        """
        self._on_profile_selected = callback

    def import_profile(self):
        """Open file dialog to import a profile."""
        if self._profile_manager is None:
            return

        # Create open dialog
        dialog = Gtk.FileDialog()
        dialog.set_title("Import Profile")

        # Set up file filter for JSON files
        json_filter = Gtk.FileFilter()
        json_filter.set_name("JSON Files")
        json_filter.add_mime_type("application/json")
        json_filter.add_pattern("*.json")

        from gi.repository import Gio
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(json_filter)
        dialog.set_filters(filters)
        dialog.set_default_filter(json_filter)

        # Get the parent window
        window = self.get_root()

        # Open file dialog
        dialog.open(window, None, self._on_import_file_selected)

    def _on_import_file_selected(self, dialog, result):
        """
        Handle import file selection result.

        Args:
            dialog: The FileDialog that was used
            result: The async result from the open dialog
        """
        try:
            file = dialog.open_finish(result)
            if file is None:
                return  # User cancelled

            file_path = file.get_path()
            if file_path is None:
                return

            # Import the profile
            from pathlib import Path
            self._profile_manager.import_profile(Path(file_path))
            self._refresh_profile_list()

        except GLib.Error:
            # User cancelled the dialog
            pass
        except (ValueError, OSError):
            # Import failed - could show an error dialog
            pass
