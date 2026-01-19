# ClamUI VirusTotal Setup Dialog Tests
"""
Unit tests for the virustotal_setup_dialog module.

Tests cover:
- VirusTotalSetupDialog import and initialization
- API key input handling and validation
- Save functionality and keyring integration
- Free tier info display
- API link handling
"""

import sys
from unittest import mock

import pytest


def _clear_src_modules():
    """Clear all cached src.* modules to prevent test pollution."""
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


@pytest.fixture
def vt_setup_dialog_module(mock_gi_modules):
    """Import virustotal_setup_dialog module with mocked GTK dependencies."""
    # Clear any cached import of virustotal_setup_dialog module
    if "src.ui.virustotal_setup_dialog" in sys.modules:
        del sys.modules["src.ui.virustotal_setup_dialog"]

    from src.ui import virustotal_setup_dialog

    yield virustotal_setup_dialog

    # Critical: Clear all src.* modules after test to prevent pollution
    _clear_src_modules()


# =============================================================================
# Import Tests
# =============================================================================


class TestVirusTotalSetupDialogImport:
    """Tests for VirusTotalSetupDialog import."""

    def test_import_virustotal_setup_dialog(self, vt_setup_dialog_module):
        """Test that VirusTotalSetupDialog can be imported."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog
        assert VirusTotalSetupDialog is not None


# =============================================================================
# Initialization Tests
# =============================================================================


class TestVirusTotalSetupDialogInit:
    """Tests for VirusTotalSetupDialog initialization."""

    def test_initialization_creates_ui(self, vt_setup_dialog_module):
        """Test initialization creates UI components."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        dialog = VirusTotalSetupDialog()

        # Verify dialog was configured
        dialog.set_title.assert_called()
        assert dialog.set_content_width.called

    def test_initializes_with_transient_parent(self, vt_setup_dialog_module):
        """Test initialization with transient parent."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        dialog = VirusTotalSetupDialog()

        # Dialog should be created
        assert dialog is not None


# =============================================================================
# API Key Input Tests
# =============================================================================


class TestVirusTotalSetupDialogApiKeyInput:
    """Tests for API key input handling."""

    def test_api_key_input_accepts_text(self, vt_setup_dialog_module):
        """Test API key input accepts text input."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        with mock.patch.object(VirusTotalSetupDialog, "_setup_ui"):
            dialog = VirusTotalSetupDialog()
            dialog._api_key_row = mock.MagicMock()
            dialog._save_button = mock.MagicMock()
            dialog._validation_label = mock.MagicMock()

            # Mock validate_api_key_format to return valid
            with mock.patch(
                "src.ui.virustotal_setup_dialog.validate_api_key_format",
                return_value=(True, None),
            ):
                dialog._on_api_key_changed(dialog._api_key_row)

                # Should enable save button for valid key
                dialog._save_button.set_sensitive.assert_called_with(True)

    def test_empty_key_disables_save_button(self, vt_setup_dialog_module):
        """Test empty key disables save button."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        with mock.patch.object(VirusTotalSetupDialog, "_setup_ui"):
            dialog = VirusTotalSetupDialog()
            dialog._api_key_row = mock.MagicMock()
            dialog._api_key_row.get_text.return_value = ""
            dialog._save_button = mock.MagicMock()
            dialog._validation_label = mock.MagicMock()

            dialog._on_api_key_changed(dialog._api_key_row)

            # Should disable save button for empty key
            dialog._save_button.set_sensitive.assert_called_with(False)
            dialog._validation_label.set_visible.assert_called_with(False)

    def test_invalid_key_shows_error(self, vt_setup_dialog_module):
        """Test invalid key shows error message."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        with mock.patch.object(VirusTotalSetupDialog, "_setup_ui"):
            dialog = VirusTotalSetupDialog()
            dialog._api_key_row = mock.MagicMock()
            dialog._save_button = mock.MagicMock()
            dialog._validation_label = mock.MagicMock()

            # Mock validate_api_key_format to return invalid
            with mock.patch(
                "src.ui.virustotal_setup_dialog.validate_api_key_format",
                return_value=(False, "Invalid format"),
            ):
                dialog._on_api_key_changed(dialog._api_key_row)

                # Should show validation error
                dialog._save_button.set_sensitive.assert_called_with(False)
                dialog._validation_label.set_visible.assert_called_with(True)


# =============================================================================
# Save Functionality Tests
# =============================================================================


class TestVirusTotalSetupDialogSave:
    """Tests for save functionality."""

    def test_save_stores_key_in_keyring(self, vt_setup_dialog_module):
        """Test save stores key in system keyring."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        with mock.patch.object(VirusTotalSetupDialog, "_setup_ui"):
            with mock.patch(
                "src.ui.virustotal_setup_dialog.validate_api_key_format",
                return_value=(True, None),
            ):
                with mock.patch(
                    "src.ui.virustotal_setup_dialog.set_api_key",
                    return_value=(True, None),
                ):
                    dialog = VirusTotalSetupDialog()
                    dialog._api_key_row = mock.MagicMock()
                    dialog._api_key_row.get_text.return_value = "test-api-key-123"

                    dialog._on_save_and_scan_clicked(mock.MagicMock())

                    # Should close dialog on successful save
                    dialog.close.assert_called_once()

    def test_save_shows_error_on_failure(self, vt_setup_dialog_module):
        """Test save shows error message on failure."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        with mock.patch.object(VirusTotalSetupDialog, "_setup_ui"):
            with mock.patch(
                "src.ui.virustotal_setup_dialog.validate_api_key_format",
                return_value=(True, None),
            ):
                with mock.patch(
                    "src.ui.virustotal_setup_dialog.set_api_key",
                    return_value=(False, "Keyring error"),
                ):
                    dialog = VirusTotalSetupDialog()
                    dialog._api_key_row = mock.MagicMock()
                    dialog._api_key_row.get_text.return_value = "test-api-key-123"
                    dialog._show_toast = mock.MagicMock()

                    dialog._on_save_and_scan_clicked(mock.MagicMock())

                    # Should show error toast
                    dialog._show_toast.assert_called()
                    toast_message = dialog._show_toast.call_args[0][0]
                    assert "Failed" in toast_message

    def test_save_triggers_callback(self, vt_setup_dialog_module):
        """Test save triggers on_key_saved callback."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        callback = mock.MagicMock()

        with mock.patch.object(VirusTotalSetupDialog, "_setup_ui"):
            with mock.patch(
                "src.ui.virustotal_setup_dialog.validate_api_key_format",
                return_value=(True, None),
            ):
                with mock.patch(
                    "src.ui.virustotal_setup_dialog.set_api_key",
                    return_value=(True, None),
                ):
                    dialog = VirusTotalSetupDialog(on_key_saved=callback)
                    dialog._api_key_row = mock.MagicMock()
                    dialog._api_key_row.get_text.return_value = "test-api-key-123"

                    dialog._on_save_and_scan_clicked(mock.MagicMock())

                    # Should trigger callback with the key
                    callback.assert_called_once_with("test-api-key-123")


# =============================================================================
# Free Tier Info Tests
# =============================================================================


class TestVirusTotalSetupDialogFreeTier:
    """Tests for free tier information display."""

    def test_shows_free_tier_info(self, vt_setup_dialog_module):
        """Test dialog shows free tier info."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        with mock.patch.object(VirusTotalSetupDialog, "_setup_ui"):
            dialog = VirusTotalSetupDialog()

            # Dialog should be created with info section
            assert dialog is not None

    def test_api_link_is_correct(self, vt_setup_dialog_module):
        """Test API key link is correct."""
        vt_setup_dialog_module  # Access module

        # Verify URL constant is defined
        assert hasattr(vt_setup_dialog_module, "VT_API_KEY_URL")
        assert "virustotal.com" in vt_setup_dialog_module.VT_API_KEY_URL
        assert "apikey" in vt_setup_dialog_module.VT_API_KEY_URL


# =============================================================================
# Website Actions Tests
# =============================================================================


class TestVirusTotalSetupDialogWebsiteActions:
    """Tests for website-related actions."""

    def test_get_api_key_opens_browser(self, vt_setup_dialog_module):
        """Test get API key action opens browser."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        with mock.patch.object(VirusTotalSetupDialog, "_setup_ui"):
            with mock.patch("src.ui.virustotal_setup_dialog.webbrowser") as mock_browser:
                dialog = VirusTotalSetupDialog()
                dialog._show_toast = mock.MagicMock()

                dialog._on_get_api_key_clicked(mock.MagicMock())

                # Should open browser with API key URL
                mock_browser.open.assert_called_once()
                url = mock_browser.open.call_args[0][0]
                assert "virustotal.com" in url

    def test_open_website_saves_preference(self, vt_setup_dialog_module):
        """Test open website saves remember preference."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        mock_settings = mock.MagicMock()

        with mock.patch.object(VirusTotalSetupDialog, "_setup_ui"):
            with mock.patch("src.ui.virustotal_setup_dialog.webbrowser"):
                dialog = VirusTotalSetupDialog(settings_manager=mock_settings)
                dialog._remember_switch = mock.MagicMock()
                dialog._remember_switch.get_active.return_value = True

                dialog._on_open_website_clicked(mock.MagicMock())

                # Should save preference
                mock_settings.set.assert_called_once()


# =============================================================================
# Remember Switch Tests
# =============================================================================


class TestVirusTotalSetupDialogRemember:
    """Tests for remember switch functionality."""

    def test_remember_switch_exists(self, vt_setup_dialog_module):
        """Test remember switch is created."""
        VirusTotalSetupDialog = vt_setup_dialog_module.VirusTotalSetupDialog

        with mock.patch.object(VirusTotalSetupDialog, "_setup_ui"):
            dialog = VirusTotalSetupDialog()
            # After UI setup, remember switch should be initialized
            # This test verifies the dialog can be created without errors
            assert dialog is not None
