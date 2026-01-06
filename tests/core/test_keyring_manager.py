# ClamUI Keyring Manager Tests
"""Unit tests for the keyring_manager module."""

import tempfile
from pathlib import Path
from unittest import mock

import pytest

from src.core.keyring_manager import (
    SERVICE_NAME,
    VT_API_KEY_NAME,
    delete_api_key,
    get_api_key,
    has_api_key,
    mask_api_key,
    set_api_key,
    validate_api_key_format,
)
from src.core.settings_manager import SettingsManager


class TestValidateApiKeyFormat:
    """Tests for API key format validation."""

    def test_valid_64_char_hex(self):
        """Test that a valid 64-character hex string is accepted."""
        valid_key = "a" * 64
        is_valid, error = validate_api_key_format(valid_key)
        assert is_valid is True
        assert error is None

    def test_valid_mixed_hex(self):
        """Test that mixed case hex characters are accepted."""
        valid_key = "0123456789abcdefABCDEF" + "a" * 42
        is_valid, error = validate_api_key_format(valid_key)
        assert is_valid is True
        assert error is None

    def test_empty_key(self):
        """Test that empty string is rejected."""
        is_valid, error = validate_api_key_format("")
        assert is_valid is False
        assert "empty" in error.lower() or "required" in error.lower()

    def test_too_short_key(self):
        """Test that key shorter than 64 chars is rejected."""
        is_valid, error = validate_api_key_format("a" * 63)
        assert is_valid is False
        assert "64" in error

    def test_too_long_key(self):
        """Test that key longer than 64 chars is rejected."""
        is_valid, error = validate_api_key_format("a" * 65)
        assert is_valid is False
        assert "64" in error

    def test_non_hex_characters(self):
        """Test that non-hex characters are rejected."""
        invalid_key = "g" * 64  # 'g' is not a hex character
        is_valid, error = validate_api_key_format(invalid_key)
        assert is_valid is False
        assert "hex" in error.lower()

    def test_special_characters(self):
        """Test that special characters are rejected."""
        invalid_key = "a" * 63 + "!"
        is_valid, error = validate_api_key_format(invalid_key)
        assert is_valid is False

    def test_whitespace_is_rejected(self):
        """Test that whitespace in key is rejected."""
        invalid_key = "a" * 32 + " " + "a" * 31
        is_valid, error = validate_api_key_format(invalid_key)
        assert is_valid is False


class TestMaskApiKey:
    """Tests for API key masking."""

    def test_mask_normal_key(self):
        """Test masking a normal length API key."""
        key = "a" * 64
        masked = mask_api_key(key)
        assert masked == "aaaaaaaa..."
        assert len(masked) == 11  # 8 chars + "..."

    def test_mask_short_key(self):
        """Test masking a short key."""
        key = "abc"
        masked = mask_api_key(key)
        assert masked == "****"  # Short keys get masked completely

    def test_mask_empty_key(self):
        """Test masking an empty key."""
        masked = mask_api_key("")
        assert masked == "Not set"  # Empty returns "Not set"

    def test_mask_none_key(self):
        """Test masking None."""
        masked = mask_api_key(None)
        assert masked == "Not set"  # None returns "Not set"


class TestKeyringManager:
    """Tests for keyring manager functions with mocked keyring."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def settings_manager(self, temp_config_dir):
        """Create a SettingsManager with a temporary directory."""
        return SettingsManager(config_dir=temp_config_dir)

    @pytest.fixture
    def mock_keyring(self):
        """Create a mock keyring module."""
        mock_kr = mock.Mock()
        mock_kr.get_password = mock.Mock(return_value=None)
        mock_kr.set_password = mock.Mock()
        mock_kr.delete_password = mock.Mock()
        return mock_kr

    def test_get_api_key_from_keyring(self, settings_manager, mock_keyring):
        """Test getting API key from keyring."""
        test_key = "a" * 64
        mock_keyring.get_password.return_value = test_key

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            result = get_api_key(settings_manager)

        assert result == test_key
        mock_keyring.get_password.assert_called_once_with(SERVICE_NAME, VT_API_KEY_NAME)

    def test_get_api_key_fallback_to_settings(self, settings_manager, mock_keyring):
        """Test falling back to settings when keyring fails."""
        test_key = "b" * 64
        settings_manager.set("virustotal_api_key", test_key)
        mock_keyring.get_password.side_effect = Exception("Keyring error")

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            result = get_api_key(settings_manager)

        assert result == test_key

    def test_get_api_key_no_key_found(self, settings_manager, mock_keyring):
        """Test when no API key is found anywhere."""
        mock_keyring.get_password.return_value = None

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            result = get_api_key(settings_manager)

        assert result is None

    def test_set_api_key_to_keyring(self, settings_manager, mock_keyring):
        """Test setting API key in keyring."""
        test_key = "c" * 64

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            success, error = set_api_key(test_key, settings_manager)

        assert success is True
        assert error is None
        mock_keyring.set_password.assert_called_once_with(SERVICE_NAME, VT_API_KEY_NAME, test_key)

    def test_set_api_key_fallback_to_settings(self, settings_manager, mock_keyring):
        """Test falling back to settings when keyring fails."""
        test_key = "d" * 64
        mock_keyring.set_password.side_effect = Exception("Keyring error")

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            success, error = set_api_key(test_key, settings_manager)

        # Should succeed with fallback
        assert success is True
        assert settings_manager.get("virustotal_api_key") == test_key

    def test_set_api_key_invalid_format(self, settings_manager):
        """Test that invalid key format is rejected."""
        invalid_key = "short"

        success, error = set_api_key(invalid_key, settings_manager)

        assert success is False
        assert error is not None

    def test_delete_api_key(self, settings_manager, mock_keyring):
        """Test deleting API key from both keyring and settings."""
        settings_manager.set("virustotal_api_key", "e" * 64)

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            result = delete_api_key(settings_manager)

        assert result is True
        mock_keyring.delete_password.assert_called_once_with(SERVICE_NAME, VT_API_KEY_NAME)
        assert settings_manager.get("virustotal_api_key") is None

    def test_delete_api_key_keyring_error_still_clears_settings(self, settings_manager, mock_keyring):
        """Test that settings are cleared even if keyring deletion fails."""
        settings_manager.set("virustotal_api_key", "f" * 64)
        mock_keyring.delete_password.side_effect = Exception("Keyring error")

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            result = delete_api_key(settings_manager)

        # Should still return True (settings cleared)
        assert result is True
        assert settings_manager.get("virustotal_api_key") is None

    def test_has_api_key_true(self, settings_manager, mock_keyring):
        """Test has_api_key returns True when key exists."""
        mock_keyring.get_password.return_value = "g" * 64

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            result = has_api_key(settings_manager)

        assert result is True

    def test_has_api_key_false(self, settings_manager, mock_keyring):
        """Test has_api_key returns False when no key."""
        mock_keyring.get_password.return_value = None

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            result = has_api_key(settings_manager)

        assert result is False


class TestKeyringManagerNoSettingsManager:
    """Tests for keyring manager without settings manager."""

    @pytest.fixture
    def mock_keyring(self):
        """Create a mock keyring module."""
        mock_kr = mock.Mock()
        mock_kr.get_password = mock.Mock(return_value=None)
        mock_kr.set_password = mock.Mock()
        mock_kr.delete_password = mock.Mock()
        return mock_kr

    def test_get_api_key_without_settings_manager(self, mock_keyring):
        """Test getting API key when no settings manager provided."""
        test_key = "h" * 64
        mock_keyring.get_password.return_value = test_key

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            result = get_api_key(None)

        assert result == test_key

    def test_get_api_key_no_keyring_uses_new_settings_manager(self, mock_keyring, tmp_path, monkeypatch):
        """Test that a new settings manager is created when None is provided."""
        mock_keyring.get_password.return_value = None
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        with mock.patch("src.core.keyring_manager._get_keyring", return_value=mock_keyring):
            result = get_api_key(None)

        assert result is None
