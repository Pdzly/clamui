# ClamUI PreferencesWindow Integration Tests
"""Integration tests for the PreferencesWindow class."""

from unittest import mock

import pytest


class TestPreferencesWindowImport:
    """Tests for importing the PreferencesWindow."""

    def test_import_preferences_window(self, mock_gi_modules):
        """Test that PreferencesWindow can be imported."""
        from src.ui.preferences.window import PreferencesWindow

        assert PreferencesWindow is not None

    def test_preferences_window_is_class(self, mock_gi_modules):
        """Test that PreferencesWindow is a class."""
        from src.ui.preferences.window import PreferencesWindow

        assert isinstance(PreferencesWindow, type)

    def test_preferences_window_inherits_from_adw_preferences_window(self, mock_gi_modules):
        """Test that PreferencesWindow inherits from Adw.PreferencesWindow."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.window import PreferencesWindow

        # Check inheritance from Adw.PreferencesWindow
        assert issubclass(PreferencesWindow, adw.PreferencesWindow)

    def test_preferences_window_inherits_from_mixin(self, mock_gi_modules):
        """Test that PreferencesWindow inherits from PreferencesPageMixin."""
        from src.ui.preferences.base import PreferencesPageMixin
        from src.ui.preferences.window import PreferencesWindow

        assert issubclass(PreferencesWindow, PreferencesPageMixin)


class TestPreferencesWindowInitialization:
    """Tests for PreferencesWindow initialization."""

    @pytest.fixture
    def mock_settings_manager(self):
        """Provide a mock settings manager."""
        manager = mock.MagicMock()
        manager.get_setting.return_value = None
        return manager

    @pytest.fixture
    def mock_parse_config(self):
        """Mock parse_config function."""
        with mock.patch("src.ui.preferences.window.parse_config") as mock_func:
            mock_func.return_value = ({}, None)
            yield mock_func

    @pytest.fixture
    def mock_path_exists(self):
        """Mock Path.exists to control clamd availability."""
        with mock.patch("src.ui.preferences.window.Path.exists") as mock_exists:
            mock_exists.return_value = True
            yield mock_exists

    @pytest.fixture
    def mock_scheduler(self):
        """Mock Scheduler class."""
        with mock.patch("src.ui.preferences.window.Scheduler") as mock_sched:
            yield mock_sched

    @pytest.fixture
    def mock_page_modules(self):
        """Mock all page modules."""
        with (
            mock.patch("src.ui.preferences.window.DatabasePage") as mock_db,
            mock.patch("src.ui.preferences.window.ScannerPage") as mock_scanner,
            mock.patch("src.ui.preferences.window.OnAccessPage") as mock_onaccess,
            mock.patch("src.ui.preferences.window.ScheduledPage") as mock_scheduled,
            mock.patch("src.ui.preferences.window.ExclusionsPage") as mock_exclusions,
            mock.patch("src.ui.preferences.window.SavePage") as mock_save,
        ):
            # Configure static page mocks to return page objects
            mock_db.create_page.return_value = mock.MagicMock()
            mock_scanner.create_page.return_value = mock.MagicMock()
            mock_onaccess.create_page.return_value = mock.MagicMock()
            mock_scheduled.create_page.return_value = mock.MagicMock()

            # Configure instance-based page mocks
            mock_exclusions_instance = mock.MagicMock()
            mock_exclusions_instance.create_page.return_value = mock.MagicMock()
            mock_exclusions.return_value = mock_exclusions_instance

            mock_save_instance = mock.MagicMock()
            mock_save_instance.create_page.return_value = mock.MagicMock()
            mock_save.return_value = mock_save_instance

            # Configure populate_fields as no-op
            mock_db.populate_fields = mock.MagicMock()
            mock_scanner.populate_fields = mock.MagicMock()
            mock_onaccess.populate_fields = mock.MagicMock()
            mock_scheduled.populate_fields = mock.MagicMock()

            yield {
                "database": mock_db,
                "scanner": mock_scanner,
                "onaccess": mock_onaccess,
                "scheduled": mock_scheduled,
                "exclusions": mock_exclusions,
                "save": mock_save,
            }

    def test_window_initializes_with_settings_manager(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window initializes with settings manager."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        assert _window._settings_manager == mock_settings_manager

    def test_window_sets_title(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window sets correct title."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        _window.set_title.assert_called_with("Preferences")

    def test_window_sets_default_size(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window sets correct default size."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        _window.set_default_size.assert_called_with(600, 500)

    def test_window_sets_modal(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window sets modal property."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        _window.set_modal.assert_called_with(True)

    def test_window_disables_search(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window disables search."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        _window.set_search_enabled.assert_called_with(False)

    def test_window_initializes_widget_dicts(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window initializes all widget dictionaries."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        assert isinstance(_window._freshclam_widgets, dict)
        assert isinstance(_window._clamd_widgets, dict)
        assert isinstance(_window._scheduled_widgets, dict)
        assert isinstance(_window._onaccess_widgets, dict)

    def test_window_initializes_scheduler(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window initializes scheduler."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        mock_scheduler.assert_called_once()
        assert _window._scheduler is not None

    def test_window_detects_clamd_available(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window detects clamd availability."""
        with mock.patch("src.ui.preferences.window.Path") as mock_path_class:
            mock_path_instance = mock.MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_class.return_value = mock_path_instance

            from src.ui.preferences.window import PreferencesWindow

            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            assert _window._clamd_available is True

    def test_window_detects_clamd_unavailable(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window detects clamd unavailability."""
        with mock.patch("src.ui.preferences.window.Path") as mock_path_class:
            mock_path_instance = mock.MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path_class.return_value = mock_path_instance

            from src.ui.preferences.window import PreferencesWindow

            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            assert _window._clamd_available is False

    def test_window_initializes_saving_state(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window initializes saving state."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        assert _window._is_saving is False
        assert _window._scheduler_error is None


class TestPreferencesWindowPageComposition:
    """Tests for PreferencesWindow page composition."""

    @pytest.fixture
    def mock_settings_manager(self):
        """Provide a mock settings manager."""
        manager = mock.MagicMock()
        manager.get_setting.return_value = None
        return manager

    @pytest.fixture
    def mock_parse_config(self):
        """Mock parse_config function."""
        with mock.patch("src.ui.preferences.window.parse_config") as mock_func:
            mock_func.return_value = ({}, None)
            yield mock_func

    @pytest.fixture
    def mock_path_exists(self):
        """Mock Path.exists to control clamd availability."""
        with mock.patch("src.ui.preferences.window.Path.exists") as mock_exists:
            mock_exists.return_value = True
            yield mock_exists

    @pytest.fixture
    def mock_scheduler(self):
        """Mock Scheduler class."""
        with mock.patch("src.ui.preferences.window.Scheduler") as mock_sched:
            yield mock_sched

    @pytest.fixture
    def mock_page_modules(self):
        """Mock all page modules."""
        with (
            mock.patch("src.ui.preferences.window.DatabasePage") as mock_db,
            mock.patch("src.ui.preferences.window.ScannerPage") as mock_scanner,
            mock.patch("src.ui.preferences.window.OnAccessPage") as mock_onaccess,
            mock.patch("src.ui.preferences.window.ScheduledPage") as mock_scheduled,
            mock.patch("src.ui.preferences.window.ExclusionsPage") as mock_exclusions,
            mock.patch("src.ui.preferences.window.SavePage") as mock_save,
        ):
            # Configure static page mocks to return page objects
            mock_db.create_page.return_value = mock.MagicMock()
            mock_scanner.create_page.return_value = mock.MagicMock()
            mock_onaccess.create_page.return_value = mock.MagicMock()
            mock_scheduled.create_page.return_value = mock.MagicMock()

            # Configure instance-based page mocks
            mock_exclusions_instance = mock.MagicMock()
            mock_exclusions_instance.create_page.return_value = mock.MagicMock()
            mock_exclusions.return_value = mock_exclusions_instance

            mock_save_instance = mock.MagicMock()
            mock_save_instance.create_page.return_value = mock.MagicMock()
            mock_save.return_value = mock_save_instance

            # Configure populate_fields as no-op
            mock_db.populate_fields = mock.MagicMock()
            mock_scanner.populate_fields = mock.MagicMock()
            mock_onaccess.populate_fields = mock.MagicMock()
            mock_scheduled.populate_fields = mock.MagicMock()

            yield {
                "database": mock_db,
                "scanner": mock_scanner,
                "onaccess": mock_onaccess,
                "scheduled": mock_scheduled,
                "exclusions": mock_exclusions,
                "save": mock_save,
            }

    def test_window_creates_database_page(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window creates database page."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        mock_page_modules["database"].create_page.assert_called_once_with(
            "/etc/clamav/freshclam.conf", _window._freshclam_widgets
        )

    def test_window_creates_scanner_page(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window creates scanner page."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        mock_page_modules["scanner"].create_page.assert_called_once_with(
            "/etc/clamav/clamd.conf",
            _window._clamd_widgets,
            mock_settings_manager,
            _window._clamd_available,
            _window,
        )

    def test_window_creates_onaccess_page(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window creates on-access page."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        mock_page_modules["onaccess"].create_page.assert_called_once_with(
            "/etc/clamav/clamd.conf",
            _window._onaccess_widgets,
            _window._clamd_available,
            _window,
        )

    def test_window_creates_scheduled_page(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window creates scheduled page."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        mock_page_modules["scheduled"].create_page.assert_called_once_with(
            _window._scheduled_widgets
        )

    def test_window_creates_exclusions_page(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window creates exclusions page."""
        from src.ui.preferences.window import PreferencesWindow

        PreferencesWindow(settings_manager=mock_settings_manager)

        # Should instantiate ExclusionsPage
        mock_page_modules["exclusions"].assert_called_once_with(mock_settings_manager)
        # Should call create_page on the instance
        mock_page_modules["exclusions"].return_value.create_page.assert_called_once()

    def test_window_creates_save_page(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window creates save page."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        # Should instantiate SavePage with all required arguments
        mock_page_modules["save"].assert_called_once()
        call_args = mock_page_modules["save"].call_args

        # Verify all required arguments are passed
        # Note: _freshclam_config and _clamd_config are None when SavePage is called
        # because _setup_ui() runs before _load_configs()
        assert call_args[0][0] == _window  # window reference
        assert call_args[0][1] is None  # freshclam_config (not yet loaded)
        assert call_args[0][2] is None  # clamd_config (not yet loaded)
        assert call_args[0][3] == "/etc/clamav/freshclam.conf"
        assert call_args[0][4] == "/etc/clamav/clamd.conf"
        assert call_args[0][5] == _window._clamd_available
        assert call_args[0][6] == mock_settings_manager
        assert call_args[0][7] == _window._scheduler
        assert call_args[0][8] == _window._freshclam_widgets
        assert call_args[0][9] == _window._clamd_widgets
        assert call_args[0][10] == _window._onaccess_widgets
        assert call_args[0][11] == _window._scheduled_widgets

        # Should call create_page on the instance
        mock_page_modules["save"].return_value.create_page.assert_called_once()

    def test_window_adds_all_pages(
        self,
        mock_gi_modules,
        mock_settings_manager,
        mock_parse_config,
        mock_path_exists,
        mock_scheduler,
        mock_page_modules,
    ):
        """Test that window adds all 8 pages."""
        from src.ui.preferences.window import PreferencesWindow

        _window = PreferencesWindow(settings_manager=mock_settings_manager)

        # Should call add() 8 times (one for each page)
        assert _window.add.call_count == 8


class TestPreferencesWindowConfigLoading:
    """Tests for PreferencesWindow configuration loading."""

    @pytest.fixture
    def mock_settings_manager(self):
        """Provide a mock settings manager."""
        manager = mock.MagicMock()
        manager.get_setting.return_value = None
        return manager

    @pytest.fixture
    def mock_scheduler(self):
        """Mock Scheduler class."""
        with mock.patch("src.ui.preferences.window.Scheduler") as mock_sched:
            yield mock_sched

    @pytest.fixture
    def mock_page_modules(self):
        """Mock all page modules."""
        with (
            mock.patch("src.ui.preferences.window.DatabasePage") as mock_db,
            mock.patch("src.ui.preferences.window.ScannerPage") as mock_scanner,
            mock.patch("src.ui.preferences.window.OnAccessPage") as mock_onaccess,
            mock.patch("src.ui.preferences.window.ScheduledPage") as mock_scheduled,
            mock.patch("src.ui.preferences.window.ExclusionsPage") as mock_exclusions,
            mock.patch("src.ui.preferences.window.SavePage") as mock_save,
        ):
            # Configure static page mocks to return page objects
            mock_db.create_page.return_value = mock.MagicMock()
            mock_scanner.create_page.return_value = mock.MagicMock()
            mock_onaccess.create_page.return_value = mock.MagicMock()
            mock_scheduled.create_page.return_value = mock.MagicMock()

            # Configure instance-based page mocks
            mock_exclusions_instance = mock.MagicMock()
            mock_exclusions_instance.create_page.return_value = mock.MagicMock()
            mock_exclusions.return_value = mock_exclusions_instance

            mock_save_instance = mock.MagicMock()
            mock_save_instance.create_page.return_value = mock.MagicMock()
            mock_save.return_value = mock_save_instance

            # Configure populate_fields as no-op
            mock_db.populate_fields = mock.MagicMock()
            mock_scanner.populate_fields = mock.MagicMock()
            mock_onaccess.populate_fields = mock.MagicMock()
            mock_scheduled.populate_fields = mock.MagicMock()

            yield {
                "database": mock_db,
                "scanner": mock_scanner,
                "onaccess": mock_onaccess,
                "scheduled": mock_scheduled,
                "exclusions": mock_exclusions,
                "save": mock_save,
            }

    def test_window_loads_freshclam_config(
        self, mock_gi_modules, mock_settings_manager, mock_scheduler, mock_page_modules
    ):
        """Test that window loads freshclam.conf."""
        with (
            mock.patch("src.ui.preferences.window.parse_config") as mock_parse,
            mock.patch("src.ui.preferences.window.Path.exists") as mock_exists,
        ):
            mock_exists.return_value = False  # No clamd
            mock_freshclam_config = {"DatabaseDirectory": "/var/lib/clamav"}
            mock_parse.return_value = (mock_freshclam_config, None)

            from src.ui.preferences.window import PreferencesWindow

            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            # Should parse freshclam.conf
            assert mock_parse.call_count >= 1
            mock_parse.assert_any_call("/etc/clamav/freshclam.conf")
            assert _window._freshclam_config == mock_freshclam_config

    def test_window_loads_clamd_config_when_available(
        self, mock_gi_modules, mock_settings_manager, mock_scheduler, mock_page_modules
    ):
        """Test that window loads clamd.conf when available."""
        with (
            mock.patch("src.ui.preferences.window.parse_config") as mock_parse,
            mock.patch("src.ui.preferences.window.Path") as mock_path_class,
        ):
            mock_path_instance = mock.MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_class.return_value = mock_path_instance

            mock_freshclam_config = {"DatabaseDirectory": "/var/lib/clamav"}
            mock_clamd_config = {"LogFile": "/var/log/clamav/clamav.log"}

            def parse_side_effect(path):
                if "freshclam" in path:
                    return (mock_freshclam_config, None)
                else:
                    return (mock_clamd_config, None)

            mock_parse.side_effect = parse_side_effect

            from src.ui.preferences.window import PreferencesWindow

            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            # Should parse both configs
            assert mock_parse.call_count == 2
            assert _window._clamd_config == mock_clamd_config

    def test_window_populates_freshclam_fields(
        self, mock_gi_modules, mock_settings_manager, mock_scheduler, mock_page_modules
    ):
        """Test that window populates freshclam fields."""
        with (
            mock.patch("src.ui.preferences.window.parse_config") as mock_parse,
            mock.patch("src.ui.preferences.window.Path.exists") as mock_exists,
        ):
            mock_exists.return_value = False  # No clamd
            mock_freshclam_config = {"DatabaseDirectory": "/var/lib/clamav"}
            mock_parse.return_value = (mock_freshclam_config, None)

            from src.ui.preferences.window import PreferencesWindow

            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            # Should populate freshclam fields
            mock_page_modules["database"].populate_fields.assert_called_once_with(
                mock_freshclam_config, _window._freshclam_widgets
            )

    def test_window_populates_clamd_fields_when_available(
        self, mock_gi_modules, mock_settings_manager, mock_scheduler, mock_page_modules
    ):
        """Test that window populates clamd fields when available."""
        with (
            mock.patch("src.ui.preferences.window.parse_config") as mock_parse,
            mock.patch("src.ui.preferences.window.Path") as mock_path_class,
        ):
            mock_path_instance = mock.MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_class.return_value = mock_path_instance

            mock_freshclam_config = {"DatabaseDirectory": "/var/lib/clamav"}
            mock_clamd_config = {"LogFile": "/var/log/clamav/clamav.log"}

            def parse_side_effect(path):
                if "freshclam" in path:
                    return (mock_freshclam_config, None)
                else:
                    return (mock_clamd_config, None)

            mock_parse.side_effect = parse_side_effect

            from src.ui.preferences.window import PreferencesWindow

            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            # Should populate scanner fields
            mock_page_modules["scanner"].populate_fields.assert_called_once_with(
                mock_clamd_config, _window._clamd_widgets
            )

    def test_window_populates_onaccess_fields_when_available(
        self, mock_gi_modules, mock_settings_manager, mock_scheduler, mock_page_modules
    ):
        """Test that window populates on-access fields when available."""
        with (
            mock.patch("src.ui.preferences.window.parse_config") as mock_parse,
            mock.patch("src.ui.preferences.window.Path") as mock_path_class,
        ):
            mock_path_instance = mock.MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_class.return_value = mock_path_instance

            mock_freshclam_config = {"DatabaseDirectory": "/var/lib/clamav"}
            mock_clamd_config = {
                "LogFile": "/var/log/clamav/clamav.log",
                "OnAccessIncludePath": "/home",
            }

            def parse_side_effect(path):
                if "freshclam" in path:
                    return (mock_freshclam_config, None)
                else:
                    return (mock_clamd_config, None)

            mock_parse.side_effect = parse_side_effect

            from src.ui.preferences.window import PreferencesWindow

            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            # Should populate on-access fields
            mock_page_modules["onaccess"].populate_fields.assert_called_once_with(
                mock_clamd_config, _window._onaccess_widgets
            )

    def test_window_populates_scheduled_fields(
        self, mock_gi_modules, mock_settings_manager, mock_scheduler, mock_page_modules
    ):
        """Test that window populates scheduled scan fields."""
        with (
            mock.patch("src.ui.preferences.window.parse_config") as mock_parse,
            mock.patch("src.ui.preferences.window.Path.exists") as mock_exists,
        ):
            mock_exists.return_value = False  # No clamd
            mock_parse.return_value = ({}, None)

            from src.ui.preferences.window import PreferencesWindow

            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            # Should populate scheduled fields
            mock_page_modules["scheduled"].populate_fields.assert_called_once_with(
                mock_settings_manager, _window._scheduled_widgets
            )

    def test_window_handles_freshclam_load_error(
        self, mock_gi_modules, mock_settings_manager, mock_scheduler, mock_page_modules
    ):
        """Test that window handles freshclam config load errors gracefully."""
        with (
            mock.patch("src.ui.preferences.window.parse_config") as mock_parse,
            mock.patch("src.ui.preferences.window.Path.exists") as mock_exists,
        ):
            mock_exists.return_value = False  # No clamd
            mock_parse.side_effect = Exception("Config file not found")

            from src.ui.preferences.window import PreferencesWindow

            # Should not raise exception
            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            # Config should be None
            assert _window._freshclam_config is None

    def test_window_handles_clamd_load_error(
        self, mock_gi_modules, mock_settings_manager, mock_scheduler, mock_page_modules
    ):
        """Test that window handles clamd config load errors gracefully."""
        with (
            mock.patch("src.ui.preferences.window.parse_config") as mock_parse,
            mock.patch("src.ui.preferences.window.Path") as mock_path_class,
        ):
            mock_path_instance = mock.MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_class.return_value = mock_path_instance

            def parse_side_effect(path):
                if "freshclam" in path:
                    return ({}, None)
                else:
                    raise Exception("Config file not readable")

            mock_parse.side_effect = parse_side_effect

            from src.ui.preferences.window import PreferencesWindow

            # Should not raise exception
            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            # Config should be None
            assert _window._clamd_config is None

    def test_window_skips_populate_when_config_is_none(
        self, mock_gi_modules, mock_settings_manager, mock_scheduler, mock_page_modules
    ):
        """Test that window skips field population when config is None."""
        with (
            mock.patch("src.ui.preferences.window.parse_config") as mock_parse,
            mock.patch("src.ui.preferences.window.Path.exists") as mock_exists,
        ):
            mock_exists.return_value = False  # No clamd
            # Return None config (simulating empty or invalid config)
            mock_parse.return_value = (None, "Error")

            from src.ui.preferences.window import PreferencesWindow

            _window = PreferencesWindow(settings_manager=mock_settings_manager)

            # Should NOT call populate_fields with None config
            # The populate_fields should not be called or should handle None gracefully
            assert _window._freshclam_config is None


class TestPreferencesWindowPackageExport:
    """Tests for PreferencesWindow package export."""

    def test_preferences_window_exported_from_package(self, mock_gi_modules):
        """Test that PreferencesWindow is exported from package __init__.py."""
        from src.ui.preferences import PreferencesWindow

        assert PreferencesWindow is not None

    def test_preset_exclusions_exported_from_package(self, mock_gi_modules):
        """Test that PRESET_EXCLUSIONS is exported from package __init__.py."""
        from src.ui.preferences import PRESET_EXCLUSIONS

        assert PRESET_EXCLUSIONS is not None
        assert isinstance(PRESET_EXCLUSIONS, list)

    def test_package_all_export(self, mock_gi_modules):
        """Test that __all__ in package init contains expected exports."""
        from src.ui.preferences import __all__

        assert "PreferencesWindow" in __all__
        assert "PRESET_EXCLUSIONS" in __all__
