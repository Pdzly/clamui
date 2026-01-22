# ClamUI Database Missing Dialog Tests
"""
Tests for the DatabaseMissingDialog component.
"""

import sys
from unittest.mock import MagicMock


def _clear_src_modules():
    """Clear all cached src.* modules to prevent test pollution."""
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestDatabaseMissingDialogImport:
    """Test that DatabaseMissingDialog can be imported correctly."""

    def test_import_database_missing_dialog(self, mock_gi_modules):
        """Test that DatabaseMissingDialog can be imported."""
        from src.ui.database_missing_dialog import DatabaseMissingDialog

        assert DatabaseMissingDialog is not None
        _clear_src_modules()


class TestDatabaseMissingDialogInit:
    """Test DatabaseMissingDialog initialization."""

    def test_init_with_callback(self, mock_gi_modules):
        """Test dialog initialization with callback function."""
        callback = MagicMock()

        from src.ui.database_missing_dialog import DatabaseMissingDialog

        dialog = DatabaseMissingDialog(callback=callback)

        assert dialog._callback is callback
        assert dialog._choice is None
        _clear_src_modules()

    def test_init_stores_callback(self, mock_gi_modules):
        """Test that dialog stores the callback function."""
        callback = MagicMock()

        from src.ui.database_missing_dialog import DatabaseMissingDialog

        dialog = DatabaseMissingDialog(callback=callback)

        # Verify callback is stored
        assert dialog._callback is callback
        # Verify initial state
        assert dialog._choice is None
        _clear_src_modules()


class TestDatabaseMissingDialogButtons:
    """Test dialog button actions."""

    def test_download_button_sets_choice(self, mock_gi_modules):
        """Test clicking Download Now sets choice to 'download'."""
        callback = MagicMock()

        from src.ui.database_missing_dialog import DatabaseMissingDialog

        dialog = DatabaseMissingDialog(callback=callback)

        # Simulate download button click
        dialog._on_download_clicked(None)

        assert dialog._choice == "download"
        _clear_src_modules()

    def test_cancel_button_sets_none_choice(self, mock_gi_modules):
        """Test clicking Cancel sets choice to None."""
        callback = MagicMock()

        from src.ui.database_missing_dialog import DatabaseMissingDialog

        dialog = DatabaseMissingDialog(callback=callback)

        # Set an initial choice to verify it gets reset
        dialog._choice = "download"

        # Simulate cancel button click
        dialog._on_cancel_clicked(None)

        assert dialog._choice is None
        _clear_src_modules()


class TestDatabaseMissingDialogCallback:
    """Test dialog callback invocation."""

    def test_callback_called_on_dialog_close(self, mock_gi_modules):
        """Test callback is called when dialog closes."""
        callback = MagicMock()

        from src.ui.database_missing_dialog import DatabaseMissingDialog

        dialog = DatabaseMissingDialog(callback=callback)

        # Set a choice
        dialog._choice = "download"

        # Simulate dialog close
        dialog._on_dialog_close_request(dialog)

        callback.assert_called_once_with("download")
        _clear_src_modules()

    def test_callback_with_none_choice(self, mock_gi_modules):
        """Test callback passes None when cancelled."""
        callback = MagicMock()

        from src.ui.database_missing_dialog import DatabaseMissingDialog

        dialog = DatabaseMissingDialog(callback=callback)

        # Cancel sets choice to None
        dialog._choice = None

        # Simulate dialog close
        dialog._on_dialog_close_request(dialog)

        callback.assert_called_once_with(None)
        _clear_src_modules()

    def test_callback_not_called_when_none(self, mock_gi_modules):
        """Test that no callback is made if callback is None."""
        from src.ui.database_missing_dialog import DatabaseMissingDialog

        dialog = DatabaseMissingDialog(callback=None)

        dialog._choice = "download"

        # Should not raise an error
        dialog._on_dialog_close_request(dialog)
        _clear_src_modules()


class TestDatabaseMissingDialogFlow:
    """Test the complete dialog flow."""

    def test_download_flow(self, mock_gi_modules):
        """Test complete flow: download click -> close -> callback."""
        callback = MagicMock()

        from src.ui.database_missing_dialog import DatabaseMissingDialog

        dialog = DatabaseMissingDialog(callback=callback)

        # User clicks Download Now
        dialog._on_download_clicked(None)
        assert dialog._choice == "download"

        # Dialog closes
        dialog._on_dialog_close_request(dialog)

        callback.assert_called_once_with("download")
        _clear_src_modules()

    def test_cancel_flow(self, mock_gi_modules):
        """Test complete flow: cancel click -> close -> callback."""
        callback = MagicMock()

        from src.ui.database_missing_dialog import DatabaseMissingDialog

        dialog = DatabaseMissingDialog(callback=callback)

        # User clicks Cancel
        dialog._on_cancel_clicked(None)
        assert dialog._choice is None

        # Dialog closes
        dialog._on_dialog_close_request(dialog)

        callback.assert_called_once_with(None)
        _clear_src_modules()

    def test_dismiss_without_action(self, mock_gi_modules):
        """Test flow when dialog is dismissed without clicking any button."""
        callback = MagicMock()

        from src.ui.database_missing_dialog import DatabaseMissingDialog

        dialog = DatabaseMissingDialog(callback=callback)

        # Choice remains None (user dismissed dialog)
        assert dialog._choice is None

        # Dialog closes
        dialog._on_dialog_close_request(dialog)

        callback.assert_called_once_with(None)
        _clear_src_modules()
