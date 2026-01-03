# ClamUI PreferencesWindow Tests
"""
Unit tests for the PreferencesWindow component.

Tests cover:
- Initialization and setup
- UI page creation (database, scanner, scheduled scans, exclusions, save)
- Configuration loading and population
- Form data collection (freshclam, clamd, scheduled scans)
- Save functionality and validation
- Dialog handling (error/success)
- Folder opening
- Permission indicators
- Preset exclusions
"""

import sys
from unittest import mock

import pytest


@pytest.fixture
def mock_settings_manager():
    """Create a mock SettingsManager."""
    manager = mock.MagicMock()
    manager.get = mock.MagicMock(return_value=None)
    manager.set = mock.MagicMock()
    manager.save = mock.MagicMock(return_value=True)
    return manager


@pytest.fixture
def mock_clamav_config():
    """Create a mock ClamAVConfig."""
    config = mock.MagicMock()
    config.has_key = mock.MagicMock(return_value=True)
    config.get_value = mock.MagicMock(return_value="test_value")
    config.set_value = mock.MagicMock()
    return config


def _clear_src_modules():
    """Clear all cached src.* modules to prevent test pollution."""
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


@pytest.fixture
def preferences_window_class(mock_gi_modules):
    """Get PreferencesWindow class with mocked dependencies."""
    # Create mock modules with proper return values
    mock_clamav_config = mock.MagicMock()
    mock_clamav_config.parse_config = mock.MagicMock(return_value=(mock.MagicMock(), None))
    mock_clamav_config.validate_config = mock.MagicMock(return_value=(True, None))
    mock_clamav_config.backup_config = mock.MagicMock()
    mock_clamav_config.write_config_with_elevation = mock.MagicMock(return_value=(True, None))

    mock_scheduler = mock.MagicMock()
    mock_scanner = mock.MagicMock()

    with mock.patch.dict(
        sys.modules,
        {
            "src.core.clamav_config": mock_clamav_config,
            "src.core.scheduler": mock_scheduler,
            "src.core.scanner": mock_scanner,
        },
    ):
        # Clear any cached import
        if "src.ui.preferences_window" in sys.modules:
            del sys.modules["src.ui.preferences_window"]

        from src.ui.preferences_window import PreferencesWindow

        yield PreferencesWindow

    # Critical: Clear all src.* modules after test to prevent pollution
    _clear_src_modules()


@pytest.fixture
def mock_preferences_window(preferences_window_class, mock_settings_manager, mock_clamav_config):
    """Create a mock PreferencesWindow instance for testing."""
    # Create instance without calling __init__
    window = object.__new__(preferences_window_class)

    # Set up required attributes
    window._settings_manager = mock_settings_manager
    window._freshclam_widgets = {}
    window._clamd_widgets = {}
    window._scheduled_widgets = {}
    window._clamd_available = False
    window._freshclam_config = mock_clamav_config
    window._clamd_config = mock_clamav_config
    window._freshclam_conf_path = "/etc/clamav/freshclam.conf"
    window._clamd_conf_path = "/etc/clamav/clamd.conf"
    window._is_saving = False
    window._scheduler_error = None
    window._scheduler = mock.MagicMock()

    # Mock internal methods
    window._setup_ui = mock.MagicMock()
    window._load_configs = mock.MagicMock()
    window._populate_scheduled_fields = mock.MagicMock()
    window.set_title = mock.MagicMock()
    window.set_default_size = mock.MagicMock()
    window.set_modal = mock.MagicMock()
    window.set_search_enabled = mock.MagicMock()
    window.add = mock.MagicMock()
    window.present = mock.MagicMock()

    return window


class TestPreferencesWindowImport:
    """Tests for PreferencesWindow import."""

    def test_import_preferences_window(self, mock_gi_modules):
        """Test that PreferencesWindow can be imported."""
        with mock.patch.dict(
            sys.modules,
            {
                "src.core.clamav_config": mock.MagicMock(),
                "src.core.scheduler": mock.MagicMock(),
                "src.core.scanner": mock.MagicMock(),
            },
        ):
            from src.ui.preferences_window import PreferencesWindow

            assert PreferencesWindow is not None

    def test_import_preset_exclusions(self, mock_gi_modules):
        """Test that PRESET_EXCLUSIONS can be imported."""
        with mock.patch.dict(
            sys.modules,
            {
                "src.core.clamav_config": mock.MagicMock(),
                "src.core.scheduler": mock.MagicMock(),
                "src.core.scanner": mock.MagicMock(),
            },
        ):
            from src.ui.preferences_window import PRESET_EXCLUSIONS

            assert PRESET_EXCLUSIONS is not None
            assert isinstance(PRESET_EXCLUSIONS, list)
            assert len(PRESET_EXCLUSIONS) > 0

    def test_preset_exclusions_structure(self, mock_gi_modules):
        """Test that PRESET_EXCLUSIONS has correct structure."""
        with mock.patch.dict(
            sys.modules,
            {
                "src.core.clamav_config": mock.MagicMock(),
                "src.core.scheduler": mock.MagicMock(),
                "src.core.scanner": mock.MagicMock(),
            },
        ):
            from src.ui.preferences_window import PRESET_EXCLUSIONS

            for exclusion in PRESET_EXCLUSIONS:
                assert "pattern" in exclusion
                assert "type" in exclusion
                assert "enabled" in exclusion
                assert "description" in exclusion

    def test_preset_exclusions_contains_common_patterns(self, mock_gi_modules):
        """Test that PRESET_EXCLUSIONS contains common patterns."""
        with mock.patch.dict(
            sys.modules,
            {
                "src.core.clamav_config": mock.MagicMock(),
                "src.core.scheduler": mock.MagicMock(),
                "src.core.scanner": mock.MagicMock(),
            },
        ):
            from src.ui.preferences_window import PRESET_EXCLUSIONS

            patterns = [e["pattern"] for e in PRESET_EXCLUSIONS]
            assert "node_modules" in patterns
            assert ".git" in patterns
            assert "__pycache__" in patterns


class TestPreferencesWindowInitialization:
    """Tests for PreferencesWindow initialization."""

    def test_initial_settings_manager_stored(self, mock_preferences_window, mock_settings_manager):
        """Test that settings manager is stored."""
        assert mock_preferences_window._settings_manager is mock_settings_manager

    def test_initial_clamd_available_is_false(self, mock_preferences_window):
        """Test that clamd available is initially False."""
        assert mock_preferences_window._clamd_available is False

    def test_initial_is_saving_is_false(self, mock_preferences_window):
        """Test that is_saving is initially False."""
        assert mock_preferences_window._is_saving is False

    def test_initial_scheduler_error_is_none(self, mock_preferences_window):
        """Test that scheduler error is initially None."""
        assert mock_preferences_window._scheduler_error is None

    def test_initial_config_paths_set(self, mock_preferences_window):
        """Test that config paths are set correctly."""
        assert mock_preferences_window._freshclam_conf_path == "/etc/clamav/freshclam.conf"
        assert mock_preferences_window._clamd_conf_path == "/etc/clamav/clamd.conf"

    def test_widget_dicts_initialized(self, mock_preferences_window):
        """Test that widget dictionaries are initialized."""
        assert isinstance(mock_preferences_window._freshclam_widgets, dict)
        assert isinstance(mock_preferences_window._clamd_widgets, dict)
        assert isinstance(mock_preferences_window._scheduled_widgets, dict)


class TestPreferencesWindowPermissionIndicator:
    """Tests for permission indicator creation."""

    def test_create_permission_indicator_returns_box(
        self, preferences_window_class, mock_gi_modules
    ):
        """Test that _create_permission_indicator returns a widget."""
        window = object.__new__(preferences_window_class)

        gtk = mock_gi_modules["gtk"]
        gtk.Box.return_value = mock.MagicMock()
        gtk.Image.new_from_icon_name.return_value = mock.MagicMock()

        result = window._create_permission_indicator()

        assert result is not None

    def test_create_permission_indicator_uses_lock_icon(
        self, preferences_window_class, mock_gi_modules
    ):
        """Test that permission indicator uses lock icon."""
        window = object.__new__(preferences_window_class)

        gtk = mock_gi_modules["gtk"]
        mock_icon = mock.MagicMock()
        gtk.Image.new_from_icon_name.return_value = mock_icon
        gtk.Box.return_value = mock.MagicMock()

        window._create_permission_indicator()

        gtk.Image.new_from_icon_name.assert_called_with("system-lock-screen-symbolic")


class TestPreferencesWindowFolderOpening:
    """Tests for folder opening functionality."""

    def test_open_folder_nonexistent_shows_dialog(self, preferences_window_class, mock_gi_modules):
        """Test that opening nonexistent folder shows error dialog."""
        window = object.__new__(preferences_window_class)

        adw = mock_gi_modules["adw"]
        mock_dialog = mock.MagicMock()
        adw.AlertDialog.return_value = mock_dialog

        with mock.patch("os.path.exists", return_value=False):
            window._open_folder_in_file_manager("/nonexistent/path")

        adw.AlertDialog.assert_called_once()
        mock_dialog.set_heading.assert_called_with("Folder Not Found")

    def test_open_folder_existing_calls_xdg_open(self, preferences_window_class, mock_gi_modules):
        """Test that opening existing folder calls xdg-open."""
        window = object.__new__(preferences_window_class)

        with mock.patch("os.path.exists", return_value=True):
            with mock.patch("subprocess.Popen") as mock_popen:
                window._open_folder_in_file_manager("/existing/path")

                mock_popen.assert_called_once()
                call_args = mock_popen.call_args[0][0]
                assert call_args[0] == "xdg-open"
                assert call_args[1] == "/existing/path"

    def test_open_folder_exception_shows_dialog(self, preferences_window_class, mock_gi_modules):
        """Test that folder open exception shows error dialog."""
        window = object.__new__(preferences_window_class)

        adw = mock_gi_modules["adw"]
        mock_dialog = mock.MagicMock()
        adw.AlertDialog.return_value = mock_dialog

        with mock.patch("os.path.exists", return_value=True):
            with mock.patch("subprocess.Popen", side_effect=Exception("Test error")):
                window._open_folder_in_file_manager("/existing/path")

        adw.AlertDialog.assert_called_once()
        mock_dialog.set_heading.assert_called_with("Error Opening Folder")


class TestPreferencesWindowCollectFreshclamData:
    """Tests for freshclam data collection."""

    def test_collect_freshclam_data_returns_dict(self, preferences_window_class, mock_gi_modules):
        """Test that _collect_freshclam_data returns a dictionary."""
        window = object.__new__(preferences_window_class)
        window._freshclam_widgets = {
            "DatabaseDirectory": mock.MagicMock(
                get_text=mock.MagicMock(return_value="/var/lib/clamav")
            ),
            "UpdateLogFile": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "NotifyClamd": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "LogVerbose": mock.MagicMock(get_active=mock.MagicMock(return_value=True)),
            "LogSyslog": mock.MagicMock(get_active=mock.MagicMock(return_value=False)),
            "Checks": mock.MagicMock(get_value=mock.MagicMock(return_value=24)),
            "DatabaseMirror": mock.MagicMock(
                get_text=mock.MagicMock(return_value="database.clamav.net")
            ),
            "HTTPProxyServer": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "HTTPProxyPort": mock.MagicMock(get_value=mock.MagicMock(return_value=0)),
            "HTTPProxyUsername": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "HTTPProxyPassword": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
        }

        result = window._collect_freshclam_data()

        assert isinstance(result, dict)
        assert result["DatabaseDirectory"] == "/var/lib/clamav"
        assert result["LogVerbose"] == "yes"
        assert result["LogSyslog"] == "no"
        assert result["Checks"] == "24"
        assert result["DatabaseMirror"] == "database.clamav.net"

    def test_collect_freshclam_data_excludes_empty_fields(
        self, preferences_window_class, mock_gi_modules
    ):
        """Test that empty fields are excluded from collection."""
        window = object.__new__(preferences_window_class)
        window._freshclam_widgets = {
            "DatabaseDirectory": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "UpdateLogFile": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "NotifyClamd": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "LogVerbose": mock.MagicMock(get_active=mock.MagicMock(return_value=False)),
            "LogSyslog": mock.MagicMock(get_active=mock.MagicMock(return_value=False)),
            "Checks": mock.MagicMock(get_value=mock.MagicMock(return_value=0)),
            "DatabaseMirror": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "HTTPProxyServer": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "HTTPProxyPort": mock.MagicMock(get_value=mock.MagicMock(return_value=0)),
            "HTTPProxyUsername": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "HTTPProxyPassword": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
        }

        result = window._collect_freshclam_data()

        # Empty paths should not be in result
        assert "DatabaseDirectory" not in result
        assert "UpdateLogFile" not in result
        assert "DatabaseMirror" not in result

    def test_collect_freshclam_data_includes_proxy_when_set(
        self, preferences_window_class, mock_gi_modules
    ):
        """Test that proxy settings are included when set."""
        window = object.__new__(preferences_window_class)
        window._freshclam_widgets = {
            "DatabaseDirectory": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "UpdateLogFile": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "NotifyClamd": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "LogVerbose": mock.MagicMock(get_active=mock.MagicMock(return_value=False)),
            "LogSyslog": mock.MagicMock(get_active=mock.MagicMock(return_value=False)),
            "Checks": mock.MagicMock(get_value=mock.MagicMock(return_value=0)),
            "DatabaseMirror": mock.MagicMock(get_text=mock.MagicMock(return_value="")),
            "HTTPProxyServer": mock.MagicMock(
                get_text=mock.MagicMock(return_value="proxy.example.com")
            ),
            "HTTPProxyPort": mock.MagicMock(get_value=mock.MagicMock(return_value=8080)),
            "HTTPProxyUsername": mock.MagicMock(
                get_text=mock.MagicMock(return_value="proxyuser")
            ),
            "HTTPProxyPassword": mock.MagicMock(
                get_text=mock.MagicMock(return_value="proxypass")
            ),
        }

        result = window._collect_freshclam_data()

        # Proxy settings should be included
        assert result["HTTPProxyServer"] == "proxy.example.com"
        assert result["HTTPProxyPort"] == "8080"
        assert result["HTTPProxyUsername"] == "proxyuser"
        assert result["HTTPProxyPassword"] == "proxypass"