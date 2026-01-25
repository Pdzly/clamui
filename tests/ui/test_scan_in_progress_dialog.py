# ClamUI Scan In Progress Dialog Tests
"""
Tests for the ScanInProgressDialog component.
"""

import sys
from unittest.mock import MagicMock


def _clear_src_modules():
    """Clear all cached src.* modules to prevent test pollution."""
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestScanInProgressDialogImport:
    """Test that ScanInProgressDialog can be imported correctly."""

    def test_import_scan_in_progress_dialog(self, mock_gi_modules):
        """Test that ScanInProgressDialog can be imported."""
        from src.ui.scan_in_progress_dialog import ScanInProgressDialog

        assert ScanInProgressDialog is not None
        _clear_src_modules()


class TestScanInProgressDialogInit:
    """Test ScanInProgressDialog initialization."""

    def test_init_with_callback(self, mock_gi_modules):
        """Test dialog initialization with callback function."""
        callback = MagicMock()

        from src.ui.scan_in_progress_dialog import ScanInProgressDialog

        # Create dialog with callback
        dialog = ScanInProgressDialog(callback=callback)

        assert dialog._callback is callback
        assert dialog._choice is None
        _clear_src_modules()

    def test_init_stores_callback(self, mock_gi_modules):
        """Test that dialog stores the callback function."""
        callback = MagicMock()

        from src.ui.scan_in_progress_dialog import ScanInProgressDialog

        dialog = ScanInProgressDialog(callback=callback)

        # Verify callback is stored
        assert dialog._callback is callback
        # Verify initial state
        assert dialog._choice is None
        _clear_src_modules()


class TestScanInProgressDialogButtons:
    """Test dialog button actions."""

    def test_keep_scanning_sets_none_choice(self, mock_gi_modules):
        """Test clicking Keep Scanning sets None choice."""
        callback = MagicMock()

        from src.ui.scan_in_progress_dialog import ScanInProgressDialog

        dialog = ScanInProgressDialog(callback=callback)

        # Simulate Keep Scanning click
        dialog._on_keep_scanning_clicked(None)

        assert dialog._choice is None
        _clear_src_modules()

    def test_cancel_and_close_sets_choice(self, mock_gi_modules):
        """Test clicking Cancel Scan and Close sets correct choice."""
        callback = MagicMock()

        from src.ui.scan_in_progress_dialog import ScanInProgressDialog

        dialog = ScanInProgressDialog(callback=callback)

        # Simulate Cancel and Close click
        dialog._on_cancel_and_close_clicked(None)

        assert dialog._choice == "cancel_and_close"
        _clear_src_modules()


class TestScanInProgressDialogCallback:
    """Test dialog callback invocation."""

    def test_callback_called_on_dialog_close(self, mock_gi_modules):
        """Test callback is called when dialog closes."""
        callback = MagicMock()

        from src.ui.scan_in_progress_dialog import ScanInProgressDialog

        dialog = ScanInProgressDialog(callback=callback)

        # Set a choice
        dialog._choice = "cancel_and_close"

        # Simulate dialog close
        dialog._on_dialog_close_request(dialog)

        callback.assert_called_once_with("cancel_and_close")
        _clear_src_modules()

    def test_callback_with_none_choice(self, mock_gi_modules):
        """Test callback passes None when user keeps scanning."""
        callback = MagicMock()

        from src.ui.scan_in_progress_dialog import ScanInProgressDialog

        dialog = ScanInProgressDialog(callback=callback)

        # Simulate Keep Scanning then close
        dialog._on_keep_scanning_clicked(None)
        dialog._on_dialog_close_request(dialog)

        callback.assert_called_once_with(None)
        _clear_src_modules()

    def test_callback_on_dismiss_without_choice(self, mock_gi_modules):
        """Test callback passes None when dialog is dismissed."""
        callback = MagicMock()

        from src.ui.scan_in_progress_dialog import ScanInProgressDialog

        dialog = ScanInProgressDialog(callback=callback)

        # Simulate dialog close without making a choice
        dialog._on_dialog_close_request(dialog)

        callback.assert_called_once_with(None)
        _clear_src_modules()


class TestScanInProgressDialogNoCallback:
    """Test dialog behavior when callback is None."""

    def test_no_error_with_none_callback(self, mock_gi_modules):
        """Test dialog handles None callback gracefully."""
        from src.ui.scan_in_progress_dialog import ScanInProgressDialog

        dialog = ScanInProgressDialog(callback=None)

        # Should not raise an error
        dialog._choice = "cancel_and_close"
        result = dialog._on_dialog_close_request(dialog)

        # Should return False to allow window close
        assert result is False
        _clear_src_modules()
