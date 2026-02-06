# ClamUI Compatibility Module
"""
Factory functions for libadwaita 1.0+ compatibility.

Provides drop-in replacements for widgets introduced in libadwaita 1.2-1.4:
- create_entry_row() → replaces Adw.EntryRow (1.2+)
- create_switch_row() → replaces Adw.SwitchRow (1.4+)
- create_toolbar_view() → replaces Adw.ToolbarView (1.4+)
- create_banner() → replaces Adw.Banner (1.3+)

Each factory returns a standard 1.0+ widget with monkey-patched methods
to match the higher-version API surface, so callers can use the same
method names regardless of libadwaita version.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


def create_entry_row(icon_name: str | None = None) -> Adw.ActionRow:
    """
    Create an entry row compatible with libadwaita 1.0+.

    Replaces Adw.EntryRow (1.2+) with Adw.ActionRow + Gtk.Entry suffix.

    Patched methods: set_text, get_text, set_input_purpose,
    set_show_apply_button, get_delegate, connect (redirects "changed"
    and "entry-activated" signals).

    Args:
        icon_name: Optional prefix icon name (styled with 12px margin, dim-label)

    Returns:
        Adw.ActionRow with entry-row-compatible API
    """
    row = Adw.ActionRow()

    # Add optional prefix icon with GNOME Settings styling
    if icon_name:
        from .utils import resolve_icon_name

        icon = Gtk.Image.new_from_icon_name(resolve_icon_name(icon_name))
        icon.set_margin_start(12)
        icon.add_css_class("dim-label")
        row.add_prefix(icon)

    entry = Gtk.Entry()
    entry.set_valign(Gtk.Align.CENTER)
    entry.set_hexpand(True)
    row.add_suffix(entry)
    row.set_activatable_widget(entry)

    # Store reference for internal use
    row._compat_entry = entry

    # Patch methods
    row.set_text = lambda text: entry.set_text(text)
    row.get_text = lambda: entry.get_text()
    row.set_input_purpose = lambda purpose: entry.set_input_purpose(purpose)
    row.set_show_apply_button = lambda val: None  # No-op, not available in 1.0
    row.get_delegate = lambda: entry

    # Patch connect to redirect entry-specific signals
    _original_connect = row.connect

    def _patched_connect(signal_name, callback, *args):
        if signal_name == "changed":
            return entry.connect("changed", lambda e: callback(row), *args)
        if signal_name == "entry-activated":
            return entry.connect("activate", lambda e: callback(row), *args)
        return _original_connect(signal_name, callback, *args)

    row.connect = _patched_connect

    return row


def create_switch_row(icon_name: str | None = None) -> Adw.ActionRow:
    """
    Create a switch row compatible with libadwaita 1.0+.

    Replaces Adw.SwitchRow (1.4+) with Adw.ActionRow + Gtk.Switch suffix.

    Patched methods: set_active, get_active, connect (redirects
    "notify::active" signal).

    Args:
        icon_name: Optional prefix icon name (styled with 12px margin, dim-label)

    Returns:
        Adw.ActionRow with switch-row-compatible API
    """
    row = Adw.ActionRow()

    # Add optional prefix icon with GNOME Settings styling
    if icon_name:
        from .utils import resolve_icon_name

        icon = Gtk.Image.new_from_icon_name(resolve_icon_name(icon_name))
        icon.set_margin_start(12)
        icon.add_css_class("dim-label")
        row.add_prefix(icon)

    switch = Gtk.Switch()
    switch.set_valign(Gtk.Align.CENTER)
    row.add_suffix(switch)
    row.set_activatable_widget(switch)

    # Store reference for internal use
    row._compat_switch = switch

    # Patch methods
    row.set_active = lambda val: switch.set_active(val)
    row.get_active = lambda: switch.get_active()

    # Patch connect to redirect switch-specific signals
    _original_connect = row.connect
    _switch_handler_ids = set()

    def _patched_connect(signal_name, callback, *args):
        if signal_name == "notify::active":
            handler_id = switch.connect("notify::active", lambda s, p: callback(row, p), *args)
            _switch_handler_ids.add(handler_id)
            return handler_id
        return _original_connect(signal_name, callback, *args)

    row.connect = _patched_connect

    # Patch handler_block/handler_unblock to forward switch-owned handlers
    _original_handler_block = row.handler_block
    _original_handler_unblock = row.handler_unblock

    def _patched_handler_block(handler_id):
        if handler_id in _switch_handler_ids:
            switch.handler_block(handler_id)
        else:
            _original_handler_block(handler_id)

    def _patched_handler_unblock(handler_id):
        if handler_id in _switch_handler_ids:
            switch.handler_unblock(handler_id)
        else:
            _original_handler_unblock(handler_id)

    row.handler_block = _patched_handler_block
    row.handler_unblock = _patched_handler_unblock

    return row


def create_toolbar_view() -> Gtk.Box:
    """
    Create a toolbar view compatible with libadwaita 1.0+.

    Replaces Adw.ToolbarView (1.4+) with a vertical Gtk.Box.

    Patched methods: add_top_bar (prepend), set_content (append with vexpand).

    Returns:
        Gtk.Box with toolbar-view-compatible API
    """
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    def _add_top_bar(widget):
        box.prepend(widget)

    def _set_content(widget):
        widget.set_vexpand(True)
        box.append(widget)

    box.add_top_bar = _add_top_bar
    box.set_content = _set_content

    return box


def create_banner() -> Gtk.Revealer:
    """
    Create a banner compatible with libadwaita 1.0+.

    Replaces Adw.Banner (1.3+) with Gtk.Revealer containing a label
    and optional action button.

    Patched methods: set_title, set_revealed, set_button_label,
    connect (redirects "button-clicked" signal).

    Returns:
        Gtk.Revealer with banner-compatible API
    """
    revealer = Gtk.Revealer()
    revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)

    inner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    inner_box.set_margin_start(12)
    inner_box.set_margin_end(12)
    inner_box.set_margin_top(8)
    inner_box.set_margin_bottom(8)
    inner_box.add_css_class("banner")

    label = Gtk.Label()
    label.set_hexpand(True)
    label.set_xalign(0)
    label.set_wrap(True)
    inner_box.append(label)

    button = Gtk.Button()
    button.set_valign(Gtk.Align.CENTER)
    button.set_visible(False)
    inner_box.append(button)

    revealer.set_child(inner_box)

    # Store references
    revealer._compat_label = label
    revealer._compat_button = button

    # Patch methods
    revealer.set_title = lambda text: label.set_text(text)

    def _set_revealed(val):
        revealer.set_reveal_child(val)

    revealer.set_revealed = _set_revealed

    def _set_button_label(text):
        button.set_label(text)
        button.set_visible(bool(text))

    revealer.set_button_label = _set_button_label

    # Patch connect to redirect banner-specific signals
    _original_connect = revealer.connect

    def _patched_connect(signal_name, callback, *args):
        if signal_name == "button-clicked":
            return button.connect("clicked", lambda b: callback(revealer), *args)
        return _original_connect(signal_name, callback, *args)

    revealer.connect = _patched_connect

    return revealer


# --- Safe method helpers for optional 1.2+/1.3+ methods ---


def safe_add_suffix(row, widget) -> None:
    """Call add_suffix if available, fall back to add_prefix.

    Adw.ActionRow has add_suffix since 1.0, but Adw.ExpanderRow only gained
    it in a later release.  On older libadwaita the widget is placed as a
    prefix instead so the information is still visible.
    """
    if hasattr(row, "add_suffix"):
        row.add_suffix(widget)
    elif hasattr(row, "add_prefix"):
        row.add_prefix(widget)


def safe_add_titled_with_icon(stack, child, name: str, title: str, icon_name: str):
    """Call add_titled_with_icon if available (libadwaita 1.2+).

    Falls back to add_titled() + page.set_icon_name() on older versions.
    """
    if hasattr(stack, "add_titled_with_icon"):
        return stack.add_titled_with_icon(child, name, title, icon_name)
    page = stack.add_titled(child, name, title)
    page.set_icon_name(icon_name)
    return page


def safe_set_subtitle_selectable(row, value: bool) -> None:
    """Call set_subtitle_selectable if available (libadwaita 1.3+)."""
    if hasattr(row, "set_subtitle_selectable"):
        row.set_subtitle_selectable(value)


def safe_set_title_lines(row, value: int) -> None:
    """Call set_title_lines if available (libadwaita 1.2+)."""
    if hasattr(row, "set_title_lines"):
        row.set_title_lines(value)


def safe_set_subtitle_lines(row, value: int) -> None:
    """Call set_subtitle_lines if available (libadwaita 1.2+)."""
    if hasattr(row, "set_subtitle_lines"):
        row.set_subtitle_lines(value)
