# ClamUI Clipboard Helper
"""
UI helper for clipboard operations with feedback.

Provides a high-level interface for clipboard operations that:
- Validates content size before attempting copy
- Shows appropriate toast notifications
- Handles async operations for medium-sized content
- Redirects to file export for very large content

This follows the same pattern as FileExportHelper for consistency.
"""

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..core.clipboard import (
    CLIPBOARD_ASYNC_THRESHOLD,
    CLIPBOARD_SYNC_THRESHOLD,
    ClipboardOperationResult,
    copy_to_clipboard_async,
    copy_to_clipboard_with_result,
    format_size,
    get_text_size,
)


class ClipboardHelper:
    """
    Helper class for clipboard operations with user feedback.

    Handles the common pattern of:
    1. Validating content size
    2. Choosing appropriate copy method (sync/async)
    3. Showing toast notifications for feedback
    4. Redirecting to file export for oversized content

    Example usage:
        helper = ClipboardHelper(parent_widget=self)
        helper.copy_with_feedback(
            text=log_content,
            success_message="Log copied to clipboard",
            on_too_large=lambda: self._show_export_dialog(),
        )
    """

    def __init__(
        self,
        parent_widget: Gtk.Widget,
        toast_manager: Adw.ToastOverlay | None = None,
    ):
        """
        Initialize the clipboard helper.

        Args:
            parent_widget: Widget to get the parent window from (for toast display)
            toast_manager: Optional ToastOverlay for notifications. If None,
                          attempts to find one via parent_widget.get_root().
        """
        self._parent_widget = parent_widget
        self._toast_manager = toast_manager
        # Track active copying toast for async operations
        self._copying_toast: Adw.Toast | None = None

    def copy_with_feedback(
        self,
        text: str,
        success_message: str = "Copied to clipboard",
        error_message: str = "Failed to copy to clipboard",
        copying_message: str = "Copying...",
        too_large_message: str | None = None,
        on_too_large: Callable[[], None] | None = None,
    ) -> None:
        """
        Copy text to clipboard with appropriate feedback based on size.

        Behavior by size:
        - < 1 MB: Synchronous copy, instant feedback
        - 1-10 MB: Async copy with "Copying..." toast, then success/error
        - > 10 MB: Shows too_large_message and calls on_too_large callback

        Args:
            text: The text content to copy
            success_message: Toast message on successful copy
            error_message: Toast message on copy failure
            copying_message: Toast message shown during async copy
            too_large_message: Message for oversized content. If None, auto-generates
                              a message with the content size.
            on_too_large: Optional callback when content is too large.
                         Typically shows an export dialog.
        """
        if not text:
            self._show_toast(error_message)
            return

        size_bytes = get_text_size(text)

        # Determine which tier this falls into
        if size_bytes > CLIPBOARD_ASYNC_THRESHOLD:
            # Content too large - suggest export
            self._handle_too_large(text, too_large_message, on_too_large)
        elif size_bytes > CLIPBOARD_SYNC_THRESHOLD:
            # Medium size - use async with feedback
            self._copy_async(text, success_message, error_message, copying_message)
        else:
            # Small content - sync copy
            self._copy_sync(text, success_message, error_message)

    def _copy_sync(
        self,
        text: str,
        success_message: str,
        error_message: str,
    ) -> None:
        """
        Perform synchronous clipboard copy with immediate feedback.

        Used for content < 1 MB where the operation is instant.
        """
        result = copy_to_clipboard_with_result(text)

        if result.is_success:
            self._show_toast(success_message)
        else:
            self._show_toast(error_message)

    def _copy_async(
        self,
        text: str,
        success_message: str,
        error_message: str,
        copying_message: str,
    ) -> None:
        """
        Perform async clipboard copy with progress feedback.

        Used for content 1-10 MB where the operation may take 10-100ms.
        Shows a "Copying..." toast while the operation is in progress.
        """
        # Show "Copying..." toast
        self._copying_toast = Adw.Toast.new(copying_message)
        self._copying_toast.set_timeout(0)  # Don't auto-dismiss
        self._add_toast(self._copying_toast)

        def on_complete(result: ClipboardOperationResult) -> None:
            """Handle async copy completion."""
            # Dismiss the copying toast
            if self._copying_toast is not None:
                self._copying_toast.dismiss()
                self._copying_toast = None

            # Show result toast
            if result.is_success:
                self._show_toast(success_message)
            else:
                self._show_toast(error_message)

        copy_to_clipboard_async(text, on_complete)

    def _handle_too_large(
        self,
        text: str,
        too_large_message: str | None,
        on_too_large: Callable[[], None] | None,
    ) -> None:
        """
        Handle content that's too large for clipboard.

        Shows an informative message and optionally triggers
        the on_too_large callback (typically to show an export dialog).
        """
        size_bytes = get_text_size(text)

        # Generate message if not provided
        if too_large_message is None:
            too_large_message = (
                f"Content too large ({format_size(size_bytes)}). "
                "Use export to save to file."
            )

        self._show_toast(too_large_message)

        # Call the callback if provided
        if on_too_large is not None:
            on_too_large()

    def _show_toast(self, message: str) -> None:
        """
        Show a toast notification.

        Args:
            message: The message to display
        """
        toast = Adw.Toast.new(message)
        self._add_toast(toast)

    def _add_toast(self, toast: Adw.Toast) -> None:
        """
        Add a toast to the appropriate toast overlay.

        Args:
            toast: The toast to add
        """
        # First try the explicit toast_manager
        if self._toast_manager is not None:
            self._toast_manager.add_toast(toast)
            return

        # Fall back to finding add_toast on the root window
        window = self._parent_widget.get_root()
        if hasattr(window, "add_toast"):
            window.add_toast(toast)
