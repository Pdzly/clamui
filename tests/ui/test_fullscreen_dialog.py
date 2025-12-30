# ClamUI FullscreenLogDialog Tests
"""Unit tests for the FullscreenLogDialog component."""

import os
import pytest

# Check if we can use GTK (requires display)
_gtk_available = False
_gtk_init_error = None

try:
    # Set GDK backend for headless testing if no display
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        # Try to use a null/headless backend
        os.environ.setdefault("GDK_BACKEND", "broadway")

    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw

    # Try to initialize Adw to check if display is available
    # Note: In headless CI, this may fail
    _gtk_available = True
except Exception as e:
    _gtk_init_error = str(e)


# Skip all tests in this module if GTK is not available
pytestmark = pytest.mark.skipif(
    not _gtk_available,
    reason=f"GTK4/Adwaita not available: {_gtk_init_error}"
)


class TestFullscreenLogDialogImport:
    """Tests for FullscreenLogDialog import and basic attributes."""

    def test_import_fullscreen_log_dialog(self):
        """Test that FullscreenLogDialog can be imported."""
        from src.ui.fullscreen_dialog import FullscreenLogDialog
        assert FullscreenLogDialog is not None

    def test_import_from_ui_package(self):
        """Test that FullscreenLogDialog is exported from src.ui package."""
        from src.ui import FullscreenLogDialog
        assert FullscreenLogDialog is not None

    def test_class_has_empty_placeholder(self):
        """Test that FullscreenLogDialog defines EMPTY_PLACEHOLDER constant."""
        from src.ui.fullscreen_dialog import FullscreenLogDialog
        assert hasattr(FullscreenLogDialog, 'EMPTY_PLACEHOLDER')
        assert isinstance(FullscreenLogDialog.EMPTY_PLACEHOLDER, str)
        assert len(FullscreenLogDialog.EMPTY_PLACEHOLDER) > 0


class TestFullscreenLogDialogCreation:
    """Tests for FullscreenLogDialog instantiation."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the FullscreenLogDialog class."""
        from src.ui.fullscreen_dialog import FullscreenLogDialog
        return FullscreenLogDialog

    def test_create_with_title_and_content(self, dialog_class):
        """Test creating dialog with title and content."""
        dialog = dialog_class(
            title="Test Title",
            content="Test content here"
        )
        assert dialog is not None
        assert dialog.get_title() == "Test Title"

    def test_create_with_title_only(self, dialog_class):
        """Test creating dialog with title only (no content)."""
        dialog = dialog_class(title="Empty Dialog")
        assert dialog is not None
        assert dialog.get_title() == "Empty Dialog"

    def test_create_with_empty_content(self, dialog_class):
        """Test creating dialog with explicitly empty content."""
        dialog = dialog_class(title="Test", content="")
        assert dialog is not None
        # Empty content should show placeholder
        assert dialog.get_content() == ""

    def test_dialog_can_close(self, dialog_class):
        """Test that dialog is configured to allow closing."""
        dialog = dialog_class(title="Test", content="Content")
        assert dialog.get_can_close() is True

    def test_dialog_has_content_dimensions(self, dialog_class):
        """Test that dialog has reasonable default dimensions."""
        dialog = dialog_class(title="Test", content="Content")
        # Should have content width/height set
        assert dialog.get_content_width() > 0
        assert dialog.get_content_height() > 0


class TestFullscreenLogDialogContent:
    """Tests for FullscreenLogDialog content management."""

    @pytest.fixture
    def dialog(self):
        """Create a FullscreenLogDialog instance for testing."""
        from src.ui.fullscreen_dialog import FullscreenLogDialog
        return FullscreenLogDialog(title="Test Dialog", content="Initial content")

    @pytest.fixture
    def empty_dialog(self):
        """Create a FullscreenLogDialog instance with empty content."""
        from src.ui.fullscreen_dialog import FullscreenLogDialog
        return FullscreenLogDialog(title="Empty Dialog", content="")

    def test_get_content_returns_initial(self, dialog):
        """Test that get_content returns the initial content."""
        assert dialog.get_content() == "Initial content"

    def test_set_content_updates_content(self, dialog):
        """Test that set_content updates the displayed content."""
        dialog.set_content("New content here")
        assert dialog.get_content() == "New content here"

    def test_set_content_with_multiline(self, dialog):
        """Test set_content with multiline content."""
        multiline_content = "Line 1\nLine 2\nLine 3"
        dialog.set_content(multiline_content)
        assert dialog.get_content() == multiline_content

    def test_set_content_with_empty_string(self, dialog):
        """Test that setting empty content shows placeholder."""
        dialog.set_content("")
        # get_content returns empty string when placeholder is shown
        assert dialog.get_content() == ""

    def test_get_content_empty_returns_empty_string(self, empty_dialog):
        """Test that get_content returns empty string for empty dialog."""
        assert empty_dialog.get_content() == ""

    def test_set_content_after_empty(self, empty_dialog):
        """Test setting content after dialog was empty."""
        empty_dialog.set_content("Now has content")
        assert empty_dialog.get_content() == "Now has content"

    def test_set_content_with_special_characters(self, dialog):
        """Test set_content with special characters."""
        special_content = "Path: /home/user/test\nStatus: OK ✓\nTime: 10:30:00"
        dialog.set_content(special_content)
        assert dialog.get_content() == special_content

    def test_set_content_with_long_lines(self, dialog):
        """Test set_content with long lines."""
        long_line = "A" * 1000
        dialog.set_content(long_line)
        assert dialog.get_content() == long_line


class TestFullscreenLogDialogBuffer:
    """Tests for FullscreenLogDialog text buffer access."""

    @pytest.fixture
    def dialog(self):
        """Create a FullscreenLogDialog instance for testing."""
        from src.ui.fullscreen_dialog import FullscreenLogDialog
        return FullscreenLogDialog(title="Buffer Test", content="Buffer content")

    def test_get_text_buffer_returns_buffer(self, dialog):
        """Test that get_text_buffer returns a Gtk.TextBuffer."""
        from gi.repository import Gtk
        buffer = dialog.get_text_buffer()
        assert buffer is not None
        assert isinstance(buffer, Gtk.TextBuffer)

    def test_text_buffer_contains_content(self, dialog):
        """Test that the buffer contains the expected content."""
        buffer = dialog.get_text_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, False)
        assert text == "Buffer content"

    def test_buffer_modification_reflects_in_get_content(self, dialog):
        """Test that direct buffer modification is reflected in get_content."""
        buffer = dialog.get_text_buffer()
        buffer.set_text("Modified via buffer")
        assert dialog.get_content() == "Modified via buffer"

    def test_set_content_updates_buffer(self, dialog):
        """Test that set_content updates the underlying buffer."""
        dialog.set_content("New via set_content")
        buffer = dialog.get_text_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, False)
        assert text == "New via set_content"


class TestFullscreenLogDialogPlaceholder:
    """Tests for FullscreenLogDialog placeholder behavior."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the FullscreenLogDialog class."""
        from src.ui.fullscreen_dialog import FullscreenLogDialog
        return FullscreenLogDialog

    def test_empty_content_shows_placeholder_in_buffer(self, dialog_class):
        """Test that empty content shows placeholder text in the buffer."""
        dialog = dialog_class(title="Test", content="")
        buffer = dialog.get_text_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, False)
        # Buffer should contain the placeholder text
        assert text == dialog_class.EMPTY_PLACEHOLDER

    def test_get_content_returns_empty_for_placeholder(self, dialog_class):
        """Test that get_content returns empty string when placeholder shown."""
        dialog = dialog_class(title="Test", content="")
        # get_content should return "" even though buffer has placeholder
        assert dialog.get_content() == ""

    def test_set_content_replaces_placeholder(self, dialog_class):
        """Test that setting content replaces the placeholder."""
        dialog = dialog_class(title="Test", content="")
        # Verify placeholder is shown
        buffer = dialog.get_text_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        assert buffer.get_text(start, end, False) == dialog_class.EMPTY_PLACEHOLDER

        # Set real content
        dialog.set_content("Real content")

        # Verify placeholder is replaced
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        assert buffer.get_text(start, end, False) == "Real content"

    def test_clearing_content_shows_placeholder_again(self, dialog_class):
        """Test that clearing content shows placeholder again."""
        dialog = dialog_class(title="Test", content="Some content")
        assert dialog.get_content() == "Some content"

        # Clear content
        dialog.set_content("")

        # Check buffer shows placeholder
        buffer = dialog.get_text_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        assert buffer.get_text(start, end, False) == dialog_class.EMPTY_PLACEHOLDER

        # get_content should return empty string
        assert dialog.get_content() == ""
