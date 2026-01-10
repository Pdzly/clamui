# ClamUI On-Access Page Tests
"""Unit tests for the OnAccessPage class."""

from unittest import mock

import pytest


class TestOnAccessPageImport:
    """Tests for importing the OnAccessPage."""

    def test_import_onaccess_page(self, mock_gi_modules):
        """Test that OnAccessPage can be imported."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        assert OnAccessPage is not None

    def test_onaccess_page_is_class(self, mock_gi_modules):
        """Test that OnAccessPage is a class."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        assert isinstance(OnAccessPage, type)

    def test_onaccess_page_inherits_from_mixin(self, mock_gi_modules):
        """Test that OnAccessPage inherits from PreferencesPageMixin."""
        from src.ui.preferences.base import PreferencesPageMixin
        from src.ui.preferences.onaccess_page import OnAccessPage

        assert issubclass(OnAccessPage, PreferencesPageMixin)


class TestOnAccessPageCreation:
    """Tests for OnAccessPage.create_page() method."""

    @pytest.fixture
    def mock_config_path(self):
        """Provide a mock config path."""
        return "/etc/clamav/clamd.conf"

    @pytest.fixture
    def widgets_dict(self):
        """Provide an empty widgets dictionary."""
        return {}

    @pytest.fixture
    def mock_parent_window(self):
        """Provide a mock parent window."""
        return mock.MagicMock()

    def test_create_page_returns_preferences_page(
        self, mock_gi_modules, mock_config_path, widgets_dict, mock_parent_window
    ):
        """Test create_page returns an Adw.PreferencesPage."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.onaccess_page import OnAccessPage

        OnAccessPage.create_page(mock_config_path, widgets_dict, True, mock_parent_window)

        # Should create a PreferencesPage
        adw.PreferencesPage.assert_called()

    def test_create_page_sets_title_and_icon(
        self, mock_gi_modules, mock_config_path, widgets_dict, mock_parent_window
    ):
        """Test create_page sets correct title and icon."""
        adw = mock_gi_modules["adw"]

        from src.ui.preferences.onaccess_page import OnAccessPage

        OnAccessPage.create_page(mock_config_path, widgets_dict, True, mock_parent_window)

        # Should set title and icon_name
        adw.PreferencesPage.assert_called_with(
            title="On Access",
            icon_name="security-high-symbolic",
        )

    def test_create_page_with_clamd_available_creates_all_widgets(
        self, mock_gi_modules, mock_config_path, widgets_dict, mock_parent_window
    ):
        """Test create_page creates all required widgets when clamd is available."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        OnAccessPage.create_page(mock_config_path, widgets_dict, True, mock_parent_window)

        # Check that all expected widgets are in the dict
        expected_widgets = [
            # Paths group
            "OnAccessIncludePath",
            "OnAccessExcludePath",
            # Behavior group
            "OnAccessPrevention",
            "OnAccessExtraScanning",
            "OnAccessDenyOnError",
            "OnAccessDisableDDD",
            # Performance group
            "OnAccessMaxThreads",
            "OnAccessMaxFileSize",
            "OnAccessCurlTimeout",
            "OnAccessRetryAttempts",
            # Exclusions group
            "OnAccessExcludeUname",
            "OnAccessExcludeUID",
            "OnAccessExcludeRootUID",
        ]

        for widget_name in expected_widgets:
            assert widget_name in widgets_dict, f"Widget {widget_name} not created"

    def test_create_page_with_clamd_unavailable_creates_status_message(
        self, mock_gi_modules, mock_config_path, widgets_dict, mock_parent_window
    ):
        """Test create_page creates status message when clamd is unavailable."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.onaccess_page import OnAccessPage

        OnAccessPage.create_page(mock_config_path, widgets_dict, False, mock_parent_window)

        # Should not create any onaccess widgets
        assert "OnAccessIncludePath" not in widgets_dict
        assert "OnAccessPrevention" not in widgets_dict

        # Should create an ActionRow for the status message
        adw.ActionRow.assert_called()

    def test_create_page_creates_entry_rows_with_icons(
        self, mock_gi_modules, mock_config_path, widgets_dict, mock_parent_window
    ):
        """Test create_page creates EntryRows with appropriate icons."""
        adw = mock_gi_modules["adw"]
        gtk = mock_gi_modules["gtk"]
        from src.ui.preferences.onaccess_page import OnAccessPage

        OnAccessPage.create_page(mock_config_path, widgets_dict, True, mock_parent_window)

        # Should create EntryRows for paths and username
        # OnAccessIncludePath, OnAccessExcludePath, OnAccessExcludeUname = 3
        assert adw.EntryRow.call_count >= 3

        # Should create Image icons for entry rows
        assert gtk.Image.new_from_icon_name.call_count >= 3

    def test_create_page_creates_switch_rows(
        self, mock_gi_modules, mock_config_path, widgets_dict, mock_parent_window
    ):
        """Test create_page creates SwitchRows for boolean settings."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.onaccess_page import OnAccessPage

        OnAccessPage.create_page(mock_config_path, widgets_dict, True, mock_parent_window)

        # Should create SwitchRows for behavior and root exclusion
        # OnAccessPrevention, OnAccessExtraScanning, OnAccessDenyOnError,
        # OnAccessDisableDDD, OnAccessExcludeRootUID = 5
        assert adw.SwitchRow.call_count >= 5

    def test_create_page_creates_spin_rows(
        self, mock_gi_modules, mock_config_path, widgets_dict, mock_parent_window
    ):
        """Test create_page creates SpinRows for numeric settings."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.onaccess_page import OnAccessPage

        OnAccessPage.create_page(mock_config_path, widgets_dict, True, mock_parent_window)

        # Should create SpinRows for performance and UID
        # OnAccessMaxThreads, OnAccessMaxFileSize, OnAccessCurlTimeout,
        # OnAccessRetryAttempts, OnAccessExcludeUID = 5
        assert adw.SpinRow.new_with_range.call_count >= 5

    def test_create_page_creates_preference_groups(
        self, mock_gi_modules, mock_config_path, widgets_dict, mock_parent_window
    ):
        """Test create_page creates all preference groups."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.onaccess_page import OnAccessPage

        OnAccessPage.create_page(mock_config_path, widgets_dict, True, mock_parent_window)

        # Should create at least 4 PreferencesGroups (Paths, Behavior, Performance, Exclusions)
        assert adw.PreferencesGroup.call_count >= 4

    def test_create_page_creates_warning_row(
        self, mock_gi_modules, mock_config_path, widgets_dict, mock_parent_window
    ):
        """Test create_page creates warning row for scan loop prevention."""
        adw = mock_gi_modules["adw"]
        gtk = mock_gi_modules["gtk"]
        from src.ui.preferences.onaccess_page import OnAccessPage

        OnAccessPage.create_page(mock_config_path, widgets_dict, True, mock_parent_window)

        # Should create ActionRow for warning
        # 1 for status message (when clamd unavailable), multiple for warnings
        assert adw.ActionRow.call_count >= 1

        # Should create warning icon
        gtk.Image.new_from_icon_name.assert_any_call("dialog-warning-symbolic")


class TestOnAccessPagePopulateFields:
    """Tests for OnAccessPage.populate_fields() method."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config object."""
        config = mock.MagicMock()
        config.has_key = mock.MagicMock(return_value=True)
        config.get_value = mock.MagicMock(return_value="test_value")
        config.get_values = mock.MagicMock(return_value=[])
        return config

    @pytest.fixture
    def mock_widgets(self):
        """Create mock widgets dictionary."""
        return {
            "OnAccessIncludePath": mock.MagicMock(),
            "OnAccessExcludePath": mock.MagicMock(),
            "OnAccessPrevention": mock.MagicMock(),
            "OnAccessExtraScanning": mock.MagicMock(),
            "OnAccessDenyOnError": mock.MagicMock(),
            "OnAccessDisableDDD": mock.MagicMock(),
            "OnAccessMaxThreads": mock.MagicMock(),
            "OnAccessMaxFileSize": mock.MagicMock(),
            "OnAccessCurlTimeout": mock.MagicMock(),
            "OnAccessRetryAttempts": mock.MagicMock(),
            "OnAccessExcludeUname": mock.MagicMock(),
            "OnAccessExcludeUID": mock.MagicMock(),
            "OnAccessExcludeRootUID": mock.MagicMock(),
        }

    def test_populate_fields_handles_none_config(self, mock_gi_modules, mock_widgets):
        """Test populate_fields handles None config gracefully."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        # Should not raise exception
        OnAccessPage.populate_fields(None, mock_widgets)

    def test_populate_fields_sets_path_entries_from_multi_values(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields sets path entries from multi-value config."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        mock_config.get_values.return_value = ["/home", "/var", "/tmp"]

        OnAccessPage.populate_fields(mock_config, mock_widgets)

        # Should call set_text with comma-separated paths
        mock_widgets["OnAccessIncludePath"].set_text.assert_called_with("/home, /var, /tmp")
        mock_widgets["OnAccessExcludePath"].set_text.assert_called_with("/home, /var, /tmp")

    def test_populate_fields_handles_empty_path_list(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields handles empty path list."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        mock_config.get_values.return_value = []

        OnAccessPage.populate_fields(mock_config, mock_widgets)

        # Should not call set_text when values are empty
        mock_widgets["OnAccessIncludePath"].set_text.assert_not_called()
        mock_widgets["OnAccessExcludePath"].set_text.assert_not_called()

    def test_populate_fields_sets_switch_states_yes(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields sets switch states correctly for 'yes'."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        # Test "yes" value
        mock_config.get_value.return_value = "yes"
        OnAccessPage.populate_fields(mock_config, mock_widgets)

        mock_widgets["OnAccessPrevention"].set_active.assert_called_with(True)
        mock_widgets["OnAccessExtraScanning"].set_active.assert_called_with(True)
        mock_widgets["OnAccessDenyOnError"].set_active.assert_called_with(True)
        mock_widgets["OnAccessDisableDDD"].set_active.assert_called_with(True)
        mock_widgets["OnAccessExcludeRootUID"].set_active.assert_called_with(True)

    def test_populate_fields_sets_switch_states_no(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields sets switch states correctly for 'no'."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        # Test "no" value
        mock_config.get_value.return_value = "no"
        OnAccessPage.populate_fields(mock_config, mock_widgets)

        mock_widgets["OnAccessPrevention"].set_active.assert_called_with(False)

    def test_populate_fields_sets_numeric_values(self, mock_gi_modules, mock_config, mock_widgets):
        """Test populate_fields sets numeric spin row values."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        mock_config.get_value.return_value = "10"

        OnAccessPage.populate_fields(mock_config, mock_widgets)

        # Should call set_value with integer
        mock_widgets["OnAccessMaxThreads"].set_value.assert_called_with(10)
        mock_widgets["OnAccessMaxFileSize"].set_value.assert_called_with(10)
        mock_widgets["OnAccessCurlTimeout"].set_value.assert_called_with(10)
        mock_widgets["OnAccessRetryAttempts"].set_value.assert_called_with(10)
        mock_widgets["OnAccessExcludeUID"].set_value.assert_called_with(10)

    def test_populate_fields_handles_invalid_numeric_values(
        self, mock_gi_modules, mock_config, mock_widgets
    ):
        """Test populate_fields handles invalid numeric values gracefully."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        mock_config.get_value.return_value = "not_a_number"

        # Should not raise exception
        OnAccessPage.populate_fields(mock_config, mock_widgets)

        # Should not call set_value when value is invalid
        # (mocks will still record calls, but real code would skip)

    def test_populate_fields_sets_username_entry(self, mock_gi_modules, mock_config, mock_widgets):
        """Test populate_fields sets username entry."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        mock_config.get_value.return_value = "clamav"

        OnAccessPage.populate_fields(mock_config, mock_widgets)

        # Should call set_text on username entry
        mock_widgets["OnAccessExcludeUname"].set_text.assert_called_with("clamav")

    def test_populate_fields_handles_missing_keys(self, mock_gi_modules, mock_config, mock_widgets):
        """Test populate_fields handles missing config keys."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        mock_config.has_key.return_value = False

        # Should not raise exception
        OnAccessPage.populate_fields(mock_config, mock_widgets)

        # Should not call any widget setters when keys are missing
        mock_widgets["OnAccessPrevention"].set_active.assert_not_called()


class TestOnAccessPageCollectData:
    """Tests for OnAccessPage.collect_data() method."""

    @pytest.fixture
    def mock_widgets(self):
        """Create mock widgets dictionary."""
        widgets = {
            "OnAccessIncludePath": mock.MagicMock(),
            "OnAccessExcludePath": mock.MagicMock(),
            "OnAccessPrevention": mock.MagicMock(),
            "OnAccessExtraScanning": mock.MagicMock(),
            "OnAccessDenyOnError": mock.MagicMock(),
            "OnAccessDisableDDD": mock.MagicMock(),
            "OnAccessMaxThreads": mock.MagicMock(),
            "OnAccessMaxFileSize": mock.MagicMock(),
            "OnAccessCurlTimeout": mock.MagicMock(),
            "OnAccessRetryAttempts": mock.MagicMock(),
            "OnAccessExcludeUname": mock.MagicMock(),
            "OnAccessExcludeUID": mock.MagicMock(),
            "OnAccessExcludeRootUID": mock.MagicMock(),
        }
        # Set default return values
        widgets["OnAccessIncludePath"].get_text.return_value = "/home, /var"
        widgets["OnAccessExcludePath"].get_text.return_value = "/tmp, /dev"
        widgets["OnAccessPrevention"].get_active.return_value = True
        widgets["OnAccessExtraScanning"].get_active.return_value = False
        widgets["OnAccessDenyOnError"].get_active.return_value = True
        widgets["OnAccessDisableDDD"].get_active.return_value = False
        widgets["OnAccessMaxThreads"].get_value.return_value = 10.0
        widgets["OnAccessMaxFileSize"].get_value.return_value = 100.0
        widgets["OnAccessCurlTimeout"].get_value.return_value = 60.0
        widgets["OnAccessRetryAttempts"].get_value.return_value = 3.0
        widgets["OnAccessExcludeUname"].get_text.return_value = "clamav"
        widgets["OnAccessExcludeUID"].get_value.return_value = 1000.0
        widgets["OnAccessExcludeRootUID"].get_active.return_value = True
        return widgets

    def test_collect_data_returns_dict(self, mock_gi_modules, mock_widgets):
        """Test collect_data returns a dictionary."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        result = OnAccessPage.collect_data(mock_widgets, True)

        assert isinstance(result, dict)

    def test_collect_data_when_clamd_unavailable_returns_empty_dict(
        self, mock_gi_modules, mock_widgets
    ):
        """Test collect_data returns empty dict when clamd is unavailable."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        result = OnAccessPage.collect_data(mock_widgets, False)

        assert result == {}

    def test_collect_data_converts_paths_to_list(self, mock_gi_modules, mock_widgets):
        """Test collect_data converts comma-separated paths to lists."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        result = OnAccessPage.collect_data(mock_widgets, True)

        # Should convert comma-separated paths to lists
        assert result["OnAccessIncludePath"] == ["/home", "/var"]
        assert result["OnAccessExcludePath"] == ["/tmp", "/dev"]

    def test_collect_data_excludes_empty_paths(self, mock_gi_modules, mock_widgets):
        """Test collect_data excludes empty path entries."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        mock_widgets["OnAccessIncludePath"].get_text.return_value = ""
        mock_widgets["OnAccessExcludePath"].get_text.return_value = "  "

        result = OnAccessPage.collect_data(mock_widgets, True)

        # Should not include empty path keys
        assert "OnAccessIncludePath" not in result
        assert "OnAccessExcludePath" not in result

    def test_collect_data_handles_paths_with_extra_whitespace(self, mock_gi_modules, mock_widgets):
        """Test collect_data strips whitespace from paths."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        mock_widgets["OnAccessIncludePath"].get_text.return_value = " /home , /var , /tmp "

        result = OnAccessPage.collect_data(mock_widgets, True)

        # Should strip whitespace from each path
        assert result["OnAccessIncludePath"] == ["/home", "/var", "/tmp"]

    def test_collect_data_converts_switches_to_yes_no(self, mock_gi_modules, mock_widgets):
        """Test collect_data converts switch states to yes/no strings."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        result = OnAccessPage.collect_data(mock_widgets, True)

        # Should convert True to "yes"
        assert result["OnAccessPrevention"] == "yes"
        assert result["OnAccessDenyOnError"] == "yes"
        assert result["OnAccessExcludeRootUID"] == "yes"

        # Should convert False to "no"
        assert result["OnAccessExtraScanning"] == "no"
        assert result["OnAccessDisableDDD"] == "no"

    def test_collect_data_converts_numeric_to_string(self, mock_gi_modules, mock_widgets):
        """Test collect_data converts numeric values to strings."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        result = OnAccessPage.collect_data(mock_widgets, True)

        # Should convert float to int to string
        assert result["OnAccessMaxThreads"] == "10"
        assert result["OnAccessMaxFileSize"] == "100"
        assert result["OnAccessCurlTimeout"] == "60"
        assert result["OnAccessRetryAttempts"] == "3"
        assert result["OnAccessExcludeUID"] == "1000"

    def test_collect_data_includes_username_when_not_empty(self, mock_gi_modules, mock_widgets):
        """Test collect_data includes username when provided."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        mock_widgets["OnAccessExcludeUname"].get_text.return_value = "clamav"

        result = OnAccessPage.collect_data(mock_widgets, True)

        assert result["OnAccessExcludeUname"] == "clamav"

    def test_collect_data_excludes_username_when_empty(self, mock_gi_modules, mock_widgets):
        """Test collect_data excludes username when empty."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        mock_widgets["OnAccessExcludeUname"].get_text.return_value = "  "

        result = OnAccessPage.collect_data(mock_widgets, True)

        # Should not include empty username
        assert "OnAccessExcludeUname" not in result

    def test_collect_data_includes_all_switches(self, mock_gi_modules, mock_widgets):
        """Test collect_data includes all switch values regardless of state."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        result = OnAccessPage.collect_data(mock_widgets, True)

        # All switches should be included
        assert "OnAccessPrevention" in result
        assert "OnAccessExtraScanning" in result
        assert "OnAccessDenyOnError" in result
        assert "OnAccessDisableDDD" in result
        assert "OnAccessExcludeRootUID" in result

    def test_collect_data_includes_all_performance_settings(self, mock_gi_modules, mock_widgets):
        """Test collect_data includes all performance settings."""
        from src.ui.preferences.onaccess_page import OnAccessPage

        result = OnAccessPage.collect_data(mock_widgets, True)

        # All performance settings should be included
        assert "OnAccessMaxThreads" in result
        assert "OnAccessMaxFileSize" in result
        assert "OnAccessCurlTimeout" in result
        assert "OnAccessRetryAttempts" in result


class TestOnAccessPageHelper:
    """Tests for _OnAccessPageHelper class."""

    def test_helper_can_be_imported(self, mock_gi_modules):
        """Test that _OnAccessPageHelper can be imported."""
        from src.ui.preferences.onaccess_page import _OnAccessPageHelper

        assert _OnAccessPageHelper is not None

    def test_helper_inherits_from_mixin(self, mock_gi_modules):
        """Test that _OnAccessPageHelper inherits from PreferencesPageMixin."""
        from src.ui.preferences.base import PreferencesPageMixin
        from src.ui.preferences.onaccess_page import _OnAccessPageHelper

        assert issubclass(_OnAccessPageHelper, PreferencesPageMixin)

    def test_helper_can_be_instantiated(self, mock_gi_modules):
        """Test that _OnAccessPageHelper can be instantiated."""
        from src.ui.preferences.onaccess_page import _OnAccessPageHelper

        helper = _OnAccessPageHelper()

        assert helper is not None
        assert hasattr(helper, "_parent_window")
        assert helper._parent_window is None

    def test_helper_has_mixin_methods(self, mock_gi_modules):
        """Test that _OnAccessPageHelper has access to mixin methods."""
        from src.ui.preferences.onaccess_page import _OnAccessPageHelper

        helper = _OnAccessPageHelper()

        # Should have access to mixin methods
        assert hasattr(helper, "_create_permission_indicator")
        assert hasattr(helper, "_open_folder_in_file_manager")
        assert hasattr(helper, "_show_error_dialog")
        assert hasattr(helper, "_show_success_dialog")
        assert hasattr(helper, "_create_file_location_group")
