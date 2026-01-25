# ClamUI Close Behavior Dialog Tests
"""
Tests for the CloseBehaviorDialog component.
"""

import sys
from unittest.mock import MagicMock


def _clear_src_modules():
    """Clear all cached src.* modules to prevent test pollution."""
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestCloseBehaviorDialogImport:
    """Test that CloseBehaviorDialog can be imported correctly."""

    def test_import_close_behavior_dialog(self, mock_gi_modules):
        """Test that CloseBehaviorDialog can be imported."""
        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        assert CloseBehaviorDialog is not None
        _clear_src_modules()


class TestCloseBehaviorDialogInit:
    """Test CloseBehaviorDialog initialization."""

    def test_init_with_callback(self, mock_gi_modules):
        """Test dialog initialization with callback function."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        # Create dialog with callback
        dialog = CloseBehaviorDialog(callback=callback)

        assert dialog._callback is callback
        assert dialog._choice is None
        _clear_src_modules()

    def test_init_stores_callback(self, mock_gi_modules):
        """Test that dialog stores the callback function."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Verify callback is stored
        assert dialog._callback is callback
        # Verify initial state
        assert dialog._choice is None
        _clear_src_modules()


class TestCloseBehaviorDialogOptions:
    """Test dialog option selection."""

    def test_minimize_option_sets_choice(self, mock_gi_modules):
        """Test selecting minimize option sets correct choice."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Simulate selecting minimize
        dialog._minimize_check = MagicMock()
        dialog._minimize_check.get_active.return_value = True
        dialog._quit_check = MagicMock()
        dialog._quit_check.get_active.return_value = False

        # Simulate confirm click
        dialog._on_confirm_clicked(None)

        assert dialog._choice == "minimize"
        _clear_src_modules()

    def test_quit_option_sets_choice(self, mock_gi_modules):
        """Test selecting quit option sets correct choice."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Simulate selecting quit
        dialog._minimize_check = MagicMock()
        dialog._minimize_check.get_active.return_value = False
        dialog._quit_check = MagicMock()
        dialog._quit_check.get_active.return_value = True

        # Simulate confirm click
        dialog._on_confirm_clicked(None)

        assert dialog._choice == "quit"
        _clear_src_modules()

    def test_no_selection_sets_none_choice(self, mock_gi_modules):
        """Test no selection sets None choice."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Simulate no selection
        dialog._minimize_check = MagicMock()
        dialog._minimize_check.get_active.return_value = False
        dialog._quit_check = MagicMock()
        dialog._quit_check.get_active.return_value = False

        # Simulate confirm click
        dialog._on_confirm_clicked(None)

        assert dialog._choice is None
        _clear_src_modules()


class TestCloseBehaviorDialogCallback:
    """Test dialog callback invocation."""

    def test_callback_called_on_dialog_close(self, mock_gi_modules):
        """Test callback is called when dialog closes."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Set up mock remember checkbox
        dialog._remember_check = MagicMock()
        dialog._remember_check.get_active.return_value = False

        # Set a choice
        dialog._choice = "minimize"

        # Simulate dialog close (Adw.Window uses close-request signal)
        dialog._on_dialog_close_request(dialog)

        callback.assert_called_once_with("minimize", False)
        _clear_src_modules()

    def test_callback_with_remember_true(self, mock_gi_modules):
        """Test callback passes remember=True when checkbox checked."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Set up mock remember checkbox as checked
        dialog._remember_check = MagicMock()
        dialog._remember_check.get_active.return_value = True

        # Set a choice
        dialog._choice = "quit"

        # Simulate dialog close (Adw.Window uses close-request signal)
        dialog._on_dialog_close_request(dialog)

        callback.assert_called_once_with("quit", True)
        _clear_src_modules()

    def test_cancel_sets_none_choice(self, mock_gi_modules):
        """Test that cancel click sets choice to None."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Set an initial choice to verify it gets reset
        dialog._choice = "minimize"

        # Simulate cancel click (sets choice to None)
        dialog._on_cancel_clicked(None)

        # Choice should be set to None
        assert dialog._choice is None
        _clear_src_modules()


class TestCloseBehaviorDialogDefaultState:
    """Test dialog default state - quit option selected, confirm enabled."""

    def test_quit_option_selected_by_default(self, mock_gi_modules):
        """Test that quit option is pre-selected when dialog opens."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Verify quit checkbox was set to active (True) during init
        dialog._quit_check.set_active.assert_called_with(True)
        _clear_src_modules()

    def test_confirm_button_enabled_by_default(self, mock_gi_modules):
        """Test that confirm button is enabled when dialog opens (quit is default)."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Verify confirm button was enabled (True) during init
        # The last call should be set_sensitive(True)
        dialog._confirm_button.set_sensitive.assert_called_with(True)
        _clear_src_modules()

    def test_default_confirm_results_in_quit(self, mock_gi_modules):
        """Test that confirming without changing selection results in quit action."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Configure mocks to return the default state (quit selected)
        dialog._minimize_check = MagicMock()
        dialog._minimize_check.get_active.return_value = False
        dialog._quit_check = MagicMock()
        dialog._quit_check.get_active.return_value = True  # Default selection

        # Simulate immediate confirm click (user accepts default)
        dialog._on_confirm_clicked(None)

        # Should result in quit choice
        assert dialog._choice == "quit"
        _clear_src_modules()


class TestCloseBehaviorDialogUI:
    """Test dialog UI elements."""

    def test_option_toggle_enables_confirm(self, mock_gi_modules):
        """Test selecting an option enables confirm button."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Set up mock check buttons and confirm button
        dialog._minimize_check = MagicMock()
        dialog._minimize_check.get_active.return_value = True
        dialog._quit_check = MagicMock()
        dialog._quit_check.get_active.return_value = False
        dialog._confirm_button = MagicMock()

        # Simulate option toggle
        dialog._on_option_toggled(dialog._minimize_check)

        dialog._confirm_button.set_sensitive.assert_called_with(True)
        _clear_src_modules()

    def test_no_selection_disables_confirm(self, mock_gi_modules):
        """Test no selection disables confirm button."""
        callback = MagicMock()

        from src.ui.close_behavior_dialog import CloseBehaviorDialog

        dialog = CloseBehaviorDialog(callback=callback)

        # Set up mock check buttons and confirm button
        dialog._minimize_check = MagicMock()
        dialog._minimize_check.get_active.return_value = False
        dialog._quit_check = MagicMock()
        dialog._quit_check.get_active.return_value = False
        dialog._confirm_button = MagicMock()

        # Simulate option toggle with no selection
        dialog._on_option_toggled(dialog._minimize_check)

        dialog._confirm_button.set_sensitive.assert_called_with(False)
        _clear_src_modules()
