# ClamUI View Helpers
"""
Shared UI utility functions and classes for ClamUI views.

This module provides common patterns extracted from multiple views:
- Empty state placeholders
- Loading state indicators
- Status banner CSS class management
- Header button box creation

These utilities ensure consistent behavior and styling across the application.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk

# =============================================================================
# Status Level Enum and Banner Helper
# =============================================================================


class StatusLevel(Enum):
    """Status levels for banners and badges with associated CSS classes."""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


# All status CSS classes for removal operations
_STATUS_CSS_CLASSES = frozenset(level.value for level in StatusLevel)


def set_status_class(widget: Gtk.Widget, level: StatusLevel) -> None:
    """
    Set the appropriate status CSS class on a widget, removing other status classes.

    This is the primary function for managing success/warning/error styling on
    status banners, badges, icons, and other widgets.

    Args:
        widget: The GTK widget to update (banner, label, icon, etc.)
        level: The status level to apply (SUCCESS, WARNING, or ERROR)

    Example:
        set_status_class(self._status_banner, StatusLevel.SUCCESS)
        # Equivalent to:
        # self._status_banner.add_css_class("success")
        # self._status_banner.remove_css_class("warning")
        # self._status_banner.remove_css_class("error")
    """
    # Add the new class first, then remove the others
    widget.add_css_class(level.value)
    for css_class in _STATUS_CSS_CLASSES:
        if css_class != level.value:
            widget.remove_css_class(css_class)


def clear_status_classes(widget: Gtk.Widget) -> None:
    """
    Remove all status CSS classes from a widget.

    Args:
        widget: The GTK widget to clear status classes from
    """
    for css_class in _STATUS_CSS_CLASSES:
        widget.remove_css_class(css_class)


# =============================================================================
# Empty State Placeholder Factory
# =============================================================================


@dataclass
class EmptyStateConfig:
    """Configuration for creating an empty state placeholder widget."""

    icon_name: str
    title: str
    subtitle: str | None = None
    icon_size: int = 48
    margin_vertical: int = 24
    title_css_class: str | None = None
    center_horizontally: bool = False
    wrap_subtitle: bool = False
    max_subtitle_chars: int | None = None


def create_empty_state(config: EmptyStateConfig) -> Gtk.Box:
    """
    Create an empty state placeholder widget.

    This creates a vertical box with an icon, title, and optional subtitle,
    styled consistently for use as list placeholders or empty content indicators.

    Args:
        config: Configuration for the empty state appearance

    Returns:
        A Gtk.Box containing the empty state UI

    Example:
        empty_state = create_empty_state(EmptyStateConfig(
            icon_name="document-open-recent-symbolic",
            title="No logs yet",
            subtitle="Logs from scans and updates will appear here",
        ))
        self._listbox.set_placeholder(empty_state)
    """
    empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    empty_box.set_valign(Gtk.Align.CENTER)
    empty_box.set_margin_top(config.margin_vertical)
    empty_box.set_margin_bottom(config.margin_vertical)
    empty_box.set_spacing(12)

    if config.center_horizontally:
        empty_box.set_halign(Gtk.Align.CENTER)

    # Empty state icon
    icon = Gtk.Image()
    icon.set_from_icon_name(config.icon_name)
    icon.set_pixel_size(config.icon_size)
    icon.add_css_class("dim-label")
    empty_box.append(icon)

    # Title label
    title_label = Gtk.Label()
    title_label.set_text(config.title)
    title_label.add_css_class("dim-label")
    if config.title_css_class:
        title_label.add_css_class(config.title_css_class)
    empty_box.append(title_label)

    # Optional subtitle
    if config.subtitle:
        subtitle_label = Gtk.Label()
        subtitle_label.set_text(config.subtitle)
        subtitle_label.add_css_class("dim-label")
        subtitle_label.add_css_class("caption")
        if config.wrap_subtitle:
            subtitle_label.set_wrap(True)
        if config.max_subtitle_chars:
            subtitle_label.set_max_width_chars(config.max_subtitle_chars)
            subtitle_label.set_justify(Gtk.Justification.CENTER)
        empty_box.append(subtitle_label)

    return empty_box


# =============================================================================
# Loading State Factory
# =============================================================================


def create_loading_row(message: str, margin_vertical: int = 24) -> Gtk.ListBoxRow:
    """
    Create a loading state placeholder row for a ListBox.

    This creates a non-selectable, non-activatable row with a spinner
    and loading message, suitable for showing while data is being loaded.

    Args:
        message: The loading message to display (e.g., "Loading logs...")
        margin_vertical: Top and bottom margin in pixels (default: 24)

    Returns:
        A Gtk.ListBoxRow containing spinner and loading text

    Example:
        loading_row = create_loading_row("Loading quarantine entries...")
        self._listbox.append(loading_row)
    """
    row = Gtk.ListBoxRow()
    row.set_selectable(False)
    row.set_activatable(False)

    loading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    loading_box.set_halign(Gtk.Align.CENTER)
    loading_box.set_valign(Gtk.Align.CENTER)
    loading_box.set_margin_top(margin_vertical)
    loading_box.set_margin_bottom(margin_vertical)
    loading_box.set_spacing(12)

    # Loading spinner
    spinner = Gtk.Spinner()
    spinner.set_spinning(True)
    loading_box.append(spinner)

    # Loading message
    label = Gtk.Label()
    label.set_text(message)
    label.add_css_class("dim-label")
    loading_box.append(label)

    row.set_child(loading_box)

    return row


# =============================================================================
# Loading State Controller
# =============================================================================


class SpinnerWidget(Protocol):
    """Protocol for widgets that support spinner operations."""

    def set_visible(self, visible: bool) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...


class SensitiveWidget(Protocol):
    """Protocol for widgets that can be enabled/disabled."""

    def set_sensitive(self, sensitive: bool) -> None: ...


@dataclass
class LoadingStateController:
    """
    Controls loading state UI for views with spinners and disableable buttons.

    This helper manages the common pattern of:
    - Showing/hiding a spinner
    - Starting/stopping the spinner animation
    - Enabling/disabling buttons during loading

    Attributes:
        spinner: The spinner widget to control
        buttons: List of buttons to disable during loading
        extra_buttons: Optional additional buttons to disable during loading

    Example:
        self._loading_controller = LoadingStateController(
            spinner=self._refresh_spinner,
            buttons=[self._refresh_button],
            extra_buttons=[self._clear_button, self._export_button],
        )

        def _set_loading_state(self, is_loading: bool):
            self._is_loading = is_loading
            self._loading_controller.set_loading(is_loading)
    """

    spinner: SpinnerWidget
    buttons: list[SensitiveWidget]
    extra_buttons: list[SensitiveWidget] | None = None

    def set_loading(self, is_loading: bool) -> None:
        """
        Update the UI to reflect the loading state.

        Args:
            is_loading: True to show loading state, False to restore normal state
        """
        if is_loading:
            self.spinner.set_visible(True)
            self.spinner.start()
            for button in self.buttons:
                button.set_sensitive(False)
            if self.extra_buttons:
                for button in self.extra_buttons:
                    button.set_sensitive(False)
        else:
            self.spinner.stop()
            self.spinner.set_visible(False)
            for button in self.buttons:
                button.set_sensitive(True)
            if self.extra_buttons:
                for button in self.extra_buttons:
                    button.set_sensitive(True)


# =============================================================================
# Header Button Box Builder
# =============================================================================


@dataclass
class HeaderButton:
    """Configuration for a header button."""

    icon_name: str | None = None
    label: str | None = None
    tooltip: str | None = None
    callback: Callable[[Gtk.Button], None] | None = None
    css_classes: list[str] | None = None
    sensitive: bool = True


def create_header_button_box(
    buttons: list[HeaderButton | Gtk.Widget],
    spacing: int = 6,
    include_spinner: bool = False,
) -> tuple[Gtk.Box, Gtk.Spinner | None]:
    """
    Create a header button box with optional spinner.

    This creates a horizontal box with buttons aligned to the end,
    suitable for use as a header suffix on PreferencesGroup widgets.

    Args:
        buttons: List of HeaderButton configs or pre-created widgets
        spacing: Spacing between buttons in pixels (default: 6)
        include_spinner: Whether to include a hidden spinner at the start

    Returns:
        Tuple of (header_box, spinner or None)

    Example:
        header_box, spinner = create_header_button_box(
            buttons=[
                HeaderButton(
                    icon_name="view-refresh-symbolic",
                    tooltip="Refresh",
                    callback=self._on_refresh_clicked,
                ),
                HeaderButton(
                    icon_name="edit-clear-all-symbolic",
                    tooltip="Clear all",
                    callback=self._on_clear_clicked,
                ),
            ],
            include_spinner=True,
        )
        self._refresh_spinner = spinner
        group.set_header_suffix(header_box)
    """
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    header_box.set_halign(Gtk.Align.END)
    header_box.set_spacing(spacing)

    spinner = None
    if include_spinner:
        spinner = Gtk.Spinner()
        spinner.set_visible(False)
        header_box.append(spinner)

    for button_config in buttons:
        if isinstance(button_config, Gtk.Widget):
            # Pre-created widget, just append it
            header_box.append(button_config)
        else:
            # Create button from config
            button = Gtk.Button()
            if button_config.icon_name:
                button.set_icon_name(button_config.icon_name)
            if button_config.label:
                button.set_label(button_config.label)
            if button_config.tooltip:
                button.set_tooltip_text(button_config.tooltip)
            button.add_css_class("flat")
            if button_config.css_classes:
                for css_class in button_config.css_classes:
                    button.add_css_class(css_class)
            button.set_sensitive(button_config.sensitive)
            if button_config.callback:
                button.connect("clicked", button_config.callback)
            header_box.append(button)

    return header_box, spinner


def create_refresh_header(
    on_refresh_clicked: Callable[[Gtk.Button], None],
    tooltip: str = "Refresh",
) -> tuple[Gtk.Box, Gtk.Spinner, Gtk.Button]:
    """
    Create a standard refresh header with spinner and refresh button.

    This is a convenience function for the most common header pattern:
    a refresh spinner followed by a refresh button.

    Args:
        on_refresh_clicked: Callback for refresh button clicks
        tooltip: Tooltip text for the refresh button

    Returns:
        Tuple of (header_box, spinner, refresh_button)

    Example:
        header_box, spinner, refresh_btn = create_refresh_header(
            self._on_refresh_clicked,
            tooltip="Refresh statistics",
        )
        self._status_spinner = spinner
        self._refresh_button = refresh_btn
        group.set_header_suffix(header_box)
    """
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    header_box.set_halign(Gtk.Align.END)
    header_box.set_spacing(6)

    spinner = Gtk.Spinner()
    spinner.set_visible(False)
    header_box.append(spinner)

    refresh_button = Gtk.Button()
    refresh_button.set_icon_name("view-refresh-symbolic")
    refresh_button.set_tooltip_text(tooltip)
    refresh_button.add_css_class("flat")
    refresh_button.connect("clicked", on_refresh_clicked)
    header_box.append(refresh_button)

    return header_box, spinner, refresh_button
