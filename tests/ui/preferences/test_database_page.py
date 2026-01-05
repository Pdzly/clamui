# ClamUI Database Page Tests
"""Unit tests for the DatabasePage class."""

import sys
from unittest import mock

import pytest


class TestDatabasePageImport:
    """Tests for importing the DatabasePage."""

    def test_import_database_page(self, mock_gi_modules):
        """Test that DatabasePage can be imported."""
        from src.ui.preferences.database_page import DatabasePage

        assert DatabasePage is not None

    def test_database_page_is_class(self, mock_gi_modules):
        """Test that DatabasePage is a class."""
        from src.ui.preferences.database_page import DatabasePage

        assert isinstance(DatabasePage, type)

    def test_database_page_inherits_from_mixin(self, mock_gi_modules):
        """Test that DatabasePage inherits from PreferencesPageMixin."""
        from src.ui.preferences.base import PreferencesPageMixin
        from src.ui.preferences.database_page import DatabasePage

        assert issubclass(DatabasePage, PreferencesPageMixin)


class TestDatabasePageCreation:
    """Tests for DatabasePage.create_page() method."""

    @pytest.fixture
    def mock_config_path(self):
        """Provide a mock config path."""
        return "/etc/clamav/freshclam.conf"

    @pytest.fixture
    def widgets_dict(self):
        """Provide an empty widgets dictionary."""
        return {}

    def test_create_page_returns_preferences_page(
        self, mock_gi_modules, mock_config_path, widgets_dict
    ):
        """Test create_page returns an Adw.PreferencesPage."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.database_page import DatabasePage

        result = DatabasePage.create_page(mock_config_path, widgets_dict)

        # Should create a PreferencesPage
        adw.PreferencesPage.assert_called()

    def test_create_page_sets_title_and_icon(
        self, mock_gi_modules, mock_config_path, widgets_dict
    ):
        """Test create_page sets correct title and icon."""
        adw = mock_gi_modules["adw"]
        mock_page = mock.MagicMock()
        adw.PreferencesPage.return_value = mock_page

        from src.ui.preferences.database_page import DatabasePage

        result = DatabasePage.create_page(mock_config_path, widgets_dict)

        # Should set title and icon_name
        adw.PreferencesPage.assert_called_with(
            title="Database Updates",
            icon_name="software-update-available-symbolic",
        )

    def test_create_page_creates_file_location_group(
        self, mock_gi_modules, mock_config_path, widgets_dict
    ):
        """Test create_page creates file location group."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.database_page import DatabasePage

        # We need to mock the helper's method
        with mock.patch(
            "src.ui.preferences.database_page._DatabasePageHelper._create_file_location_group"
        ) as mock_create_file_location:
            result = DatabasePage.create_page(mock_config_path, widgets_dict)

            # Should call _create_file_location_group
            mock_create_file_location.assert_called_once()

    def test_create_page_creates_all_widgets(
        self, mock_gi_modules, mock_config_path, widgets_dict
    ):
        """Test create_page creates all required widgets."""
        from src.ui.preferences.database_page import DatabasePage

        DatabasePage.create_page(mock_config_path, widgets_dict)

        # Check that all expected widgets are in the dict
        expected_widgets = [
            # Paths group
            "DatabaseDirectory",
            "UpdateLogFile",
            "NotifyClamd",
            "LogVerbose",
            "LogSyslog",
            # Updates group
            "Checks",
            "DatabaseMirror",
            # Proxy group
            "HTTPProxyServer",
            "HTTPProxyPort",
            "HTTPProxyUsername",
            "HTTPProxyPassword",
        ]

        for widget_name in expected_widgets:
            assert widget_name in widgets_dict, f"Widget {widget_name} not created"

    def test_create_page_creates_entry_rows_with_icons(
        self, mock_gi_modules, mock_config_path, widgets_dict
    ):
        """Test create_page creates EntryRows with appropriate icons."""
        adw = mock_gi_modules["adw"]
        gtk = mock_gi_modules["gtk"]
        from src.ui.preferences.database_page import DatabasePage

        DatabasePage.create_page(mock_config_path, widgets_dict)

        # Should create multiple EntryRows
        assert adw.EntryRow.call_count >= 5  # DatabaseDirectory, UpdateLogFile, NotifyClamd, DatabaseMirror, HTTPProxyServer

        # Should create multiple Image icons
        assert gtk.Image.new_from_icon_name.call_count >= 5

    def test_create_page_creates_switch_rows(
        self, mock_gi_modules, mock_config_path, widgets_dict
    ):
        """Test create_page creates SwitchRows for boolean settings."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.database_page import DatabasePage

        DatabasePage.create_page(mock_config_path, widgets_dict)

        # Should create SwitchRows for LogVerbose and LogSyslog
        assert adw.SwitchRow.call_count >= 2

    def test_create_page_creates_spin_rows(
        self, mock_gi_modules, mock_config_path, widgets_dict
    ):
        """Test create_page creates SpinRows for numeric settings."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.database_page import DatabasePage

        DatabasePage.create_page(mock_config_path, widgets_dict)

        # Should create SpinRows for Checks and HTTPProxyPort
        assert adw.SpinRow.new_with_range.call_count >= 2

    def test_create_page_creates_password_entry_row(
        self, mock_gi_modules, mock_config_path, widgets_dict
    ):
        """Test create_page creates PasswordEntryRow for proxy password."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.database_page import DatabasePage

        DatabasePage.create_page(mock_config_path, widgets_dict)

        # Should create a PasswordEntryRow for HTTPProxyPassword
        adw.PasswordEntryRow.assert_called()

    def test_create_page_creates_preference_groups(
        self, mock_gi_modules, mock_config_path, widgets_dict
    ):
        """Test create_page creates all preference groups."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.database_page import DatabasePage

        DatabasePage.create_page(mock_config_path, widgets_dict)

        # Should create at least 3 PreferencesGroups (Paths, Updates, Proxy)
        assert adw.PreferencesGroup.call_count >= 3


class TestDatabasePagePopulateFields:
    """Tests for DatabasePage.populate_fields() method."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config object."""
        config = mock.MagicMock()
        config.has_key = mock.MagicMock(return_value=True)
        config.get_value = mock.MagicMock(return_value="test_value")
        return config

    @pytest.fixture
    def mock_widgets(self):
        """Create mock widgets dictionary."""
        return {
            "DatabaseDirectory": mock.MagicMock(),
            "UpdateLogFile": mock.MagicMock(),
            "NotifyClamd": mock.MagicMock(),
            "LogVerbose": mock.MagicMock(),
            "LogSyslog": mock.MagicMock(),
            "Checks": mock.MagicMock(),
            "DatabaseMirror": mock.MagicMock(),
            "HTTPProxyServer": mock.MagicMock(),
            "HTTPProxyPort": mock.MagicMock(),
            "HTTPProxyUsername": mock.MagicMock(),
            "HTTPProxyPassword": mock.MagicMock(),
        }

    def test_populate_fields_handles_none_config(self, mock_gi_modules, mock_widgets):
        """Test populate_fields handles None config gracefully."""
        from src.ui.preferences.database_page import DatabasePage

        # Should not raise exception
        DatabasePage.populate_fields(None, mock_widgets)

    def test_populate_fields_sets_text_entries(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields sets text entry values."""
        from src.ui.preferences.database_page import DatabasePage

        mock_config.get_value.return_value = "/var/lib/clamav"

        DatabasePage.populate_fields(mock_config, mock_widgets)

        # Should call set_text on entry widgets
        mock_widgets["DatabaseDirectory"].set_text.assert_called_with("/var/lib/clamav")
        mock_widgets["UpdateLogFile"].set_text.assert_called_with("/var/lib/clamav")
        mock_widgets["NotifyClamd"].set_text.assert_called_with("/var/lib/clamav")
        mock_widgets["DatabaseMirror"].set_text.assert_called_with("/var/lib/clamav")

    def test_populate_fields_sets_switch_states(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields sets switch states correctly."""
        from src.ui.preferences.database_page import DatabasePage

        # Test "yes" value
        mock_config.get_value.return_value = "yes"
        DatabasePage.populate_fields(mock_config, mock_widgets)
        mock_widgets["LogVerbose"].set_active.assert_called_with(True)

        # Reset mocks
        mock_widgets["LogVerbose"].reset_mock()
        mock_widgets["LogSyslog"].reset_mock()

        # Test "no" value
        mock_config.get_value.return_value = "no"
        DatabasePage.populate_fields(mock_config, mock_widgets)
        mock_widgets["LogVerbose"].set_active.assert_called_with(False)
        mock_widgets["LogSyslog"].set_active.assert_called_with(False)

    def test_populate_fields_sets_numeric_values(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields sets numeric spin row values."""
        from src.ui.preferences.database_page import DatabasePage

        mock_config.get_value.return_value = "24"

        DatabasePage.populate_fields(mock_config, mock_widgets)

        # Should call set_value with integer
        mock_widgets["Checks"].set_value.assert_called_with(24)
        mock_widgets["HTTPProxyPort"].set_value.assert_called_with(24)

    def test_populate_fields_handles_invalid_numeric_values(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields handles invalid numeric values gracefully."""
        from src.ui.preferences.database_page import DatabasePage

        mock_config.get_value.return_value = "not_a_number"

        # Should not raise exception
        DatabasePage.populate_fields(mock_config, mock_widgets)

    def test_populate_fields_sets_proxy_credentials(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields sets proxy username and password."""
        from src.ui.preferences.database_page import DatabasePage

        mock_config.get_value.return_value = "proxy_user"

        DatabasePage.populate_fields(mock_config, mock_widgets)

        # Should call set_text on proxy widgets
        mock_widgets["HTTPProxyUsername"].set_text.assert_called_with("proxy_user")
        mock_widgets["HTTPProxyPassword"].set_text.assert_called_with("proxy_user")

    def test_populate_fields_skips_missing_keys(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields skips keys not in config."""
        from src.ui.preferences.database_page import DatabasePage

        # Simulate missing keys
        mock_config.has_key.return_value = False

        DatabasePage.populate_fields(mock_config, mock_widgets)

        # Should not call set_text/set_active for missing keys
        mock_widgets["DatabaseDirectory"].set_text.assert_not_called()


class TestDatabasePageCollectData:
    """Tests for DatabasePage.collect_data() method."""

    @pytest.fixture
    def mock_widgets(self):
        """Create mock widgets dictionary with default return values."""
        widgets = {
            "DatabaseDirectory": mock.MagicMock(),
            "UpdateLogFile": mock.MagicMock(),
            "NotifyClamd": mock.MagicMock(),
            "LogVerbose": mock.MagicMock(),
            "LogSyslog": mock.MagicMock(),
            "Checks": mock.MagicMock(),
            "DatabaseMirror": mock.MagicMock(),
            "HTTPProxyServer": mock.MagicMock(),
            "HTTPProxyPort": mock.MagicMock(),
            "HTTPProxyUsername": mock.MagicMock(),
            "HTTPProxyPassword": mock.MagicMock(),
        }

        # Set default return values
        widgets["DatabaseDirectory"].get_text.return_value = "/var/lib/clamav"
        widgets["UpdateLogFile"].get_text.return_value = "/var/log/clamav/freshclam.log"
        widgets["NotifyClamd"].get_text.return_value = "/etc/clamav/clamd.conf"
        widgets["LogVerbose"].get_active.return_value = True
        widgets["LogSyslog"].get_active.return_value = False
        widgets["Checks"].get_value.return_value = 24
        widgets["DatabaseMirror"].get_text.return_value = "database.clamav.net"
        widgets["HTTPProxyServer"].get_text.return_value = "proxy.example.com"
        widgets["HTTPProxyPort"].get_value.return_value = 8080
        widgets["HTTPProxyUsername"].get_text.return_value = "proxyuser"
        widgets["HTTPProxyPassword"].get_text.return_value = "proxypass"

        return widgets

    def test_collect_data_returns_dict(self, mock_gi_modules, mock_widgets):
        """Test collect_data returns a dictionary."""
        from src.ui.preferences.database_page import DatabasePage

        result = DatabasePage.collect_data(mock_widgets)

        assert isinstance(result, dict)

    def test_collect_data_includes_all_text_fields(self, mock_gi_modules, mock_widgets):
        """Test collect_data includes all text entry fields."""
        from src.ui.preferences.database_page import DatabasePage

        result = DatabasePage.collect_data(mock_widgets)

        assert result["DatabaseDirectory"] == "/var/lib/clamav"
        assert result["UpdateLogFile"] == "/var/log/clamav/freshclam.log"
        assert result["NotifyClamd"] == "/etc/clamav/clamd.conf"
        assert result["DatabaseMirror"] == "database.clamav.net"

    def test_collect_data_converts_switch_to_yes_no(self, mock_gi_modules, mock_widgets):
        """Test collect_data converts switch states to yes/no strings."""
        from src.ui.preferences.database_page import DatabasePage

        result = DatabasePage.collect_data(mock_widgets)

        # LogVerbose is True -> "yes"
        assert result["LogVerbose"] == "yes"
        # LogSyslog is False -> "no"
        assert result["LogSyslog"] == "no"

    def test_collect_data_converts_numeric_to_string(self, mock_gi_modules, mock_widgets):
        """Test collect_data converts numeric values to strings."""
        from src.ui.preferences.database_page import DatabasePage

        result = DatabasePage.collect_data(mock_widgets)

        assert result["Checks"] == "24"
        assert isinstance(result["Checks"], str)

    def test_collect_data_includes_proxy_settings(self, mock_gi_modules, mock_widgets):
        """Test collect_data includes all proxy settings."""
        from src.ui.preferences.database_page import DatabasePage

        result = DatabasePage.collect_data(mock_widgets)

        assert result["HTTPProxyServer"] == "proxy.example.com"
        assert result["HTTPProxyPort"] == "8080"
        assert result["HTTPProxyUsername"] == "proxyuser"
        assert result["HTTPProxyPassword"] == "proxypass"

    def test_collect_data_excludes_empty_text_fields(self, mock_gi_modules, mock_widgets):
        """Test collect_data excludes empty text fields."""
        from src.ui.preferences.database_page import DatabasePage

        # Set some fields to empty
        mock_widgets["DatabaseDirectory"].get_text.return_value = ""
        mock_widgets["DatabaseMirror"].get_text.return_value = ""

        result = DatabasePage.collect_data(mock_widgets)

        # Empty fields should not be in result
        assert "DatabaseDirectory" not in result
        assert "DatabaseMirror" not in result

    def test_collect_data_excludes_zero_proxy_port(self, mock_gi_modules, mock_widgets):
        """Test collect_data excludes proxy port when set to 0."""
        from src.ui.preferences.database_page import DatabasePage

        # Set proxy port to 0
        mock_widgets["HTTPProxyPort"].get_value.return_value = 0

        result = DatabasePage.collect_data(mock_widgets)

        # Port 0 should not be in result
        assert "HTTPProxyPort" not in result

    def test_collect_data_excludes_empty_proxy_credentials(self, mock_gi_modules, mock_widgets):
        """Test collect_data excludes empty proxy credentials."""
        from src.ui.preferences.database_page import DatabasePage

        # Set proxy credentials to empty
        mock_widgets["HTTPProxyUsername"].get_text.return_value = ""
        mock_widgets["HTTPProxyPassword"].get_text.return_value = ""

        result = DatabasePage.collect_data(mock_widgets)

        # Empty credentials should not be in result
        assert "HTTPProxyUsername" not in result
        assert "HTTPProxyPassword" not in result

    def test_collect_data_always_includes_switches(self, mock_gi_modules, mock_widgets):
        """Test collect_data always includes switch values."""
        from src.ui.preferences.database_page import DatabasePage

        result = DatabasePage.collect_data(mock_widgets)

        # Switches should always be present
        assert "LogVerbose" in result
        assert "LogSyslog" in result


class TestDatabasePageHelper:
    """Tests for _DatabasePageHelper class."""

    def test_helper_inherits_from_mixin(self, mock_gi_modules):
        """Test that _DatabasePageHelper inherits from PreferencesPageMixin."""
        from src.ui.preferences.base import PreferencesPageMixin
        from src.ui.preferences.database_page import _DatabasePageHelper

        assert issubclass(_DatabasePageHelper, PreferencesPageMixin)

    def test_helper_has_mixin_methods(self, mock_gi_modules):
        """Test that _DatabasePageHelper has mixin methods."""
        from src.ui.preferences.database_page import _DatabasePageHelper

        # Should have all mixin methods
        assert hasattr(_DatabasePageHelper, "_create_permission_indicator")
        assert hasattr(_DatabasePageHelper, "_create_file_location_group")

    def test_helper_can_be_instantiated(self, mock_gi_modules):
        """Test that _DatabasePageHelper can be instantiated."""
        from src.ui.preferences.database_page import _DatabasePageHelper

        # Should be able to create an instance
        instance = _DatabasePageHelper()
        assert instance is not None
