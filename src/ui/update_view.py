# ClamUI Update View
"""
Database update interface component for ClamUI with update button, progress display, and results.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..core.updater import FreshclamUpdater, UpdateResult, UpdateStatus
from ..core.utils import check_freshclam_installed
from .utils import add_row_icon
from .view_helpers import StatusLevel, set_status_class


class UpdateView(Gtk.Box):
    """
    Database update interface component for ClamUI.

    Provides the database update interface with:
    - Freshclam availability status
    - Update button with progress indication
    - Results display area
    """

    def __init__(self, **kwargs):
        """
        Initialize the update view.

        Args:
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        # Initialize updater
        self._updater = FreshclamUpdater()

        # Updating state
        self._is_updating = False

        # Freshclam availability
        self._freshclam_available = False

        # Set up the UI
        self._setup_ui()

        # Check freshclam availability on load (synchronous to avoid race conditions)
        self._check_freshclam_status()

    def _setup_ui(self):
        """Set up the update view UI layout."""
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_spacing(18)

        # Create the info section
        self._create_info_section()

        # Create the update button section
        self._create_update_section()

        # Create the results section
        self._create_results_section()

        # Create the status bar
        self._create_status_bar()

    def _create_info_section(self):
        """Create the info/description section."""
        # Info frame
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Database Update")
        info_group.set_description(
            "Update ClamAV virus definitions to detect the latest threats"
        )

        # Info row explaining the update process
        info_row = Adw.ActionRow()
        info_row.set_title("Virus Definitions")
        info_row.set_subtitle(
            "Click 'Update Database' to download the latest virus signatures"
        )
        add_row_icon(info_row, "software-update-available-symbolic")

        info_group.add(info_row)
        self.append(info_group)

    def _create_update_section(self):
        """Create the update button section."""
        # Update button container
        update_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        update_box.set_halign(Gtk.Align.CENTER)
        update_box.set_spacing(12)

        # Spinner for update progress (hidden by default)
        self._update_spinner = Gtk.Spinner()
        self._update_spinner.set_visible(False)

        # Update button
        self._update_button = Gtk.Button()
        self._update_button.set_label("Update Database")
        self._update_button.set_tooltip_text("Update Database (F6)")
        self._update_button.add_css_class("suggested-action")
        self._update_button.add_css_class("pill")
        self._update_button.set_sensitive(False)  # Disabled until freshclam is verified
        self._update_button.connect("clicked", self._on_update_clicked)

        # Make the button larger
        self._update_button.set_size_request(160, 40)

        # Force Update button - less prominent than main Update button
        self._force_update_button = Gtk.Button()
        self._force_update_button.set_label("Force Update")
        self._force_update_button.set_tooltip_text(
            "Force update: Backs up local databases, deletes them, then downloads fresh copies "
            "from mirrors. Automatically restores from backup if update fails."
        )
        self._force_update_button.add_css_class("pill")
        self._force_update_button.set_sensitive(
            False
        )  # Disabled until freshclam is verified
        self._force_update_button.connect("clicked", self._on_force_update_clicked)

        # Cancel button (hidden by default)
        self._cancel_button = Gtk.Button()
        self._cancel_button.set_label("Cancel")
        self._cancel_button.add_css_class("destructive-action")
        self._cancel_button.add_css_class("pill")
        self._cancel_button.set_visible(False)
        self._cancel_button.connect("clicked", self._on_cancel_clicked)

        update_box.append(self._update_spinner)
        update_box.append(self._update_button)
        update_box.append(self._force_update_button)
        update_box.append(self._cancel_button)

        self.append(update_box)

    def _create_results_section(self):
        """Create the results display section."""
        # Results frame
        results_group = Adw.PreferencesGroup()
        results_group.set_title("Update Results")
        results_group.set_description("Results will appear here after updating")
        self._results_group = results_group

        # Results container
        results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        results_box.set_spacing(12)

        # Status banner (hidden by default)
        self._status_banner = Adw.Banner()
        self._status_banner.set_revealed(False)
        self._status_banner.set_button_label("Dismiss")
        self._status_banner.connect("button-clicked", self._on_status_banner_dismissed)
        results_box.append(self._status_banner)

        # Results text view in a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.set_vexpand(True)
        scrolled.add_css_class("card")

        self._results_text = Gtk.TextView()
        self._results_text.set_editable(False)
        self._results_text.set_cursor_visible(False)
        self._results_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._results_text.set_left_margin(12)
        self._results_text.set_right_margin(12)
        self._results_text.set_top_margin(12)
        self._results_text.set_bottom_margin(12)
        self._results_text.add_css_class("monospace")

        # Set placeholder text
        buffer = self._results_text.get_buffer()
        buffer.set_text(
            "No update results yet.\n\nClick 'Update Database' to download the latest virus definitions."
        )

        scrolled.set_child(self._results_text)
        results_box.append(scrolled)

        results_group.add(results_box)
        self.append(results_group)

    def _create_status_bar(self):
        """Create the status bar at the bottom."""
        # Status bar
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.set_halign(Gtk.Align.CENTER)
        status_box.set_spacing(6)

        # Freshclam status icon
        self._freshclam_status_icon = Gtk.Image()
        self._freshclam_status_icon.set_from_icon_name("dialog-question-symbolic")

        # Freshclam status label
        self._freshclam_status_label = Gtk.Label()
        self._freshclam_status_label.set_text("Checking freshclam...")
        self._freshclam_status_label.add_css_class("dim-label")

        status_box.append(self._freshclam_status_icon)
        status_box.append(self._freshclam_status_label)

        self.append(status_box)

    def _check_freshclam_status(self):
        """Check freshclam installation status and update UI."""
        is_installed, version_or_error = check_freshclam_installed()

        if is_installed:
            self._freshclam_available = True
            self._freshclam_status_icon.set_from_icon_name("object-select-symbolic")
            self._freshclam_status_icon.add_css_class("success")
            self._freshclam_status_label.set_text(f"freshclam: {version_or_error}")

            # Enable update buttons
            self._update_button.set_sensitive(True)
            self._force_update_button.set_sensitive(True)
        else:
            self._freshclam_available = False
            self._freshclam_status_icon.set_from_icon_name("dialog-warning-symbolic")
            self._freshclam_status_icon.add_css_class("warning")
            self._freshclam_status_label.set_text(
                version_or_error or "freshclam not found"
            )

            # Disable update buttons and show error banner
            self._update_button.set_sensitive(False)
            self._force_update_button.set_sensitive(False)
            self._status_banner.set_title(version_or_error or "freshclam not installed")
            self._status_banner.set_revealed(True)

        return False  # Don't repeat

    def _on_status_banner_dismissed(self, banner):
        """
        Handle status banner dismiss button click.

        Hides the status banner when the user clicks the Dismiss button.

        Args:
            banner: The Adw.Banner that was dismissed
        """
        banner.set_revealed(False)

    def _on_update_clicked(self, button):
        """Handle update button click."""
        if not self._freshclam_available:
            return

        self._start_update(force=False)

    def _on_force_update_clicked(self, button):
        """Handle force update button click."""
        if not self._freshclam_available:
            return

        self._start_update(force=True)

    def _on_cancel_clicked(self, button):
        """Handle cancel button click."""
        self._updater.cancel()
        self._set_updating_state(False)

    def _start_update(self, force: bool = False):
        """
        Start the database update process.

        Args:
            force: If True, backup local databases, delete them, then download
                   fresh copies from mirrors.
        """
        self._set_updating_state(True)
        self._clear_results()

        # Update results text with appropriate message
        buffer = self._results_text.get_buffer()
        if force:
            buffer.set_text(
                "Force updating virus database...\n\n"
                "Backing up local databases, then deleting them to force fresh downloads from mirrors.\n"
                "Previous databases will be restored if the update fails.\n\n"
                "Please wait, this may take a few minutes."
            )
        else:
            buffer.set_text(
                "Updating virus database...\n\nPlease wait, this may take a few minutes."
            )

        # Hide any previous status banner
        self._status_banner.set_revealed(False)

        # Start async update
        self._updater.update_async(callback=self._on_update_complete, force=force)

    def _set_updating_state(self, is_updating: bool):
        """
        Update UI to reflect updating state.

        Args:
            is_updating: Whether an update is in progress
        """
        self._is_updating = is_updating

        if is_updating:
            # Show updating state
            self._update_button.set_label("Updating...")
            self._update_button.set_sensitive(False)
            self._force_update_button.set_sensitive(False)
            self._update_spinner.set_visible(True)
            self._update_spinner.start()
            self._cancel_button.set_visible(True)
        else:
            # Restore normal state
            self._update_button.set_label("Update Database")
            self._update_button.set_sensitive(self._freshclam_available)
            self._force_update_button.set_sensitive(self._freshclam_available)
            self._update_spinner.stop()
            self._update_spinner.set_visible(False)
            self._cancel_button.set_visible(False)

    def _on_update_complete(self, result: UpdateResult):
        """
        Handle update completion.

        Args:
            result: The update result from the updater
        """
        self._set_updating_state(False)
        self._display_results(result)

        # Send notification only on actual updates, not when already up-to-date
        root = self.get_root()
        if root:
            app = root.get_application()
            if app and hasattr(app, "notification_manager"):
                if (
                    result.status == UpdateStatus.SUCCESS
                    and result.databases_updated > 0
                ):
                    app.notification_manager.notify_update_complete(
                        success=True, databases_updated=result.databases_updated
                    )
                elif result.status == UpdateStatus.ERROR:
                    app.notification_manager.notify_update_complete(
                        success=False, databases_updated=0
                    )

        return False  # Don't repeat GLib.idle_add

    def _clear_results(self):
        """Clear the results display."""
        buffer = self._results_text.get_buffer()
        buffer.set_text("")
        self._status_banner.set_revealed(False)

    def _display_results(self, result: UpdateResult):
        """
        Display update results in the UI.

        Args:
            result: The update result to display
        """
        # Update status banner based on result
        if result.status == UpdateStatus.SUCCESS:
            self._status_banner.set_title(
                f"Database updated successfully ({result.databases_updated} database(s) updated)"
            )
            set_status_class(self._status_banner, StatusLevel.SUCCESS)
        elif result.status == UpdateStatus.UP_TO_DATE:
            self._status_banner.set_title("Database is already up to date")
            set_status_class(self._status_banner, StatusLevel.INFO)
        elif result.status == UpdateStatus.CANCELLED:
            self._status_banner.set_title("Update cancelled")
            set_status_class(self._status_banner, StatusLevel.WARNING)
        else:  # ERROR
            self._status_banner.set_title(
                result.error_message or "Update error occurred"
            )
            set_status_class(self._status_banner, StatusLevel.ERROR)

        self._status_banner.set_revealed(True)

        # Build results text
        lines = []

        # Header with update status
        if result.status == UpdateStatus.SUCCESS:
            lines.append("UPDATE COMPLETE - DATABASE UPDATED")
        elif result.status == UpdateStatus.UP_TO_DATE:
            lines.append("UPDATE COMPLETE - ALREADY UP TO DATE")
        elif result.status == UpdateStatus.CANCELLED:
            lines.append("UPDATE CANCELLED")
        else:
            lines.append("UPDATE ERROR")

        lines.append("=" * 50)
        lines.append("")

        # Summary
        lines.append("Summary:")
        lines.append(f"  Status: {result.status.value}")
        if result.databases_updated > 0:
            lines.append(f"  Databases updated: {result.databases_updated}")
        lines.append("")

        # Error message if present
        if result.error_message:
            lines.append(f"Error: {result.error_message}")
            lines.append("")

        # Raw output section
        if result.stdout:
            lines.append("-" * 50)
            lines.append("freshclam Output:")
            lines.append("-" * 50)
            lines.append(result.stdout)

        if result.stderr and result.status == UpdateStatus.ERROR:
            lines.append("-" * 50)
            lines.append("Error Output:")
            lines.append("-" * 50)
            lines.append(result.stderr)

        # Update the text view
        buffer = self._results_text.get_buffer()
        buffer.set_text("\n".join(lines))

    @property
    def updater(self) -> FreshclamUpdater:
        """
        Get the updater instance.

        Returns:
            The FreshclamUpdater instance used by this view
        """
        return self._updater
