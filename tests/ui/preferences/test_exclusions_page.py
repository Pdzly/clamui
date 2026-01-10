# ClamUI Exclusions Page Tests
"""Unit tests for the ExclusionsPage class."""

from unittest import mock

import pytest


class TestExclusionsPageImport:
    """Tests for importing the ExclusionsPage."""

    def test_import_exclusions_page(self, mock_gi_modules):
        """Test that ExclusionsPage can be imported."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        assert ExclusionsPage is not None

    def test_exclusions_page_is_class(self, mock_gi_modules):
        """Test that ExclusionsPage is a class."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        assert isinstance(ExclusionsPage, type)

    def test_exclusions_page_inherits_from_mixin(self, mock_gi_modules):
        """Test that ExclusionsPage inherits from PreferencesPageMixin."""
        from src.ui.preferences.base import PreferencesPageMixin
        from src.ui.preferences.exclusions_page import ExclusionsPage

        assert issubclass(ExclusionsPage, PreferencesPageMixin)

    def test_import_preset_exclusions_constant(self, mock_gi_modules):
        """Test that PRESET_EXCLUSIONS can be imported."""
        from src.ui.preferences.exclusions_page import PRESET_EXCLUSIONS

        assert PRESET_EXCLUSIONS is not None


class TestPresetExclusionsConstant:
    """Tests for PRESET_EXCLUSIONS constant."""

    def test_preset_exclusions_is_list(self, mock_gi_modules):
        """Test that PRESET_EXCLUSIONS is a list."""
        from src.ui.preferences.exclusions_page import PRESET_EXCLUSIONS

        assert isinstance(PRESET_EXCLUSIONS, list)

    def test_preset_exclusions_count(self, mock_gi_modules):
        """Test that PRESET_EXCLUSIONS has expected number of items."""
        from src.ui.preferences.exclusions_page import PRESET_EXCLUSIONS

        # Should have 6 preset exclusions
        assert len(PRESET_EXCLUSIONS) == 6

    def test_preset_exclusions_structure(self, mock_gi_modules):
        """Test that each preset exclusion has required keys."""
        from src.ui.preferences.exclusions_page import PRESET_EXCLUSIONS

        required_keys = {"pattern", "type", "enabled", "description"}
        for preset in PRESET_EXCLUSIONS:
            assert isinstance(preset, dict)
            assert set(preset.keys()) == required_keys

    def test_preset_exclusions_patterns(self, mock_gi_modules):
        """Test that PRESET_EXCLUSIONS contains expected patterns."""
        from src.ui.preferences.exclusions_page import PRESET_EXCLUSIONS

        expected_patterns = [
            "node_modules",
            ".git",
            ".venv",
            "build",
            "dist",
            "__pycache__",
        ]
        actual_patterns = [p["pattern"] for p in PRESET_EXCLUSIONS]
        assert actual_patterns == expected_patterns

    def test_preset_exclusions_all_enabled_by_default(self, mock_gi_modules):
        """Test that all presets are enabled by default."""
        from src.ui.preferences.exclusions_page import PRESET_EXCLUSIONS

        for preset in PRESET_EXCLUSIONS:
            assert preset["enabled"] is True

    def test_preset_exclusions_all_directories(self, mock_gi_modules):
        """Test that all presets are directory type."""
        from src.ui.preferences.exclusions_page import PRESET_EXCLUSIONS

        for preset in PRESET_EXCLUSIONS:
            assert preset["type"] == "directory"


class TestExclusionsPageCreation:
    """Tests for ExclusionsPage.create_page() method."""

    @pytest.fixture
    def mock_settings_manager(self):
        """Provide a mock settings manager."""
        manager = mock.MagicMock()
        manager.get.return_value = []
        return manager

    def test_create_page_returns_preferences_page(self, mock_gi_modules, mock_settings_manager):
        """Test create_page returns an Adw.PreferencesPage."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page.create_page()

        # Should create a PreferencesPage
        adw.PreferencesPage.assert_called()

    def test_create_page_sets_title_and_icon(self, mock_gi_modules, mock_settings_manager):
        """Test create_page sets correct title and icon."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page.create_page()

        # Should set title and icon_name
        adw.PreferencesPage.assert_called_with(
            title="Exclusions",
            icon_name="action-unavailable-symbolic",
        )

    def test_create_page_creates_preference_groups(self, mock_gi_modules, mock_settings_manager):
        """Test create_page creates preference groups."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page.create_page()

        # Should create 2 PreferencesGroups (preset and custom)
        assert adw.PreferencesGroup.call_count == 2

    def test_create_page_creates_preset_switch_rows(self, mock_gi_modules, mock_settings_manager):
        """Test create_page creates SwitchRows for preset exclusions."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.exclusions_page import PRESET_EXCLUSIONS, ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page.create_page()

        # Should create one SwitchRow per preset exclusion
        assert adw.SwitchRow.call_count >= len(PRESET_EXCLUSIONS)

    def test_create_page_creates_custom_entry_row(self, mock_gi_modules, mock_settings_manager):
        """Test create_page creates EntryRow for adding custom exclusions."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page.create_page()

        # Should create an EntryRow for custom exclusions
        adw.EntryRow.assert_called()

    def test_create_page_creates_add_button(self, mock_gi_modules, mock_settings_manager):
        """Test create_page creates add button for custom exclusions."""
        gtk = mock_gi_modules["gtk"]
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page.create_page()

        # Should create a Button
        assert gtk.Button.call_count >= 1

    def test_create_page_loads_custom_exclusions(self, mock_gi_modules, mock_settings_manager):
        """Test create_page loads existing custom exclusions."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        # Set up mock to return custom exclusions
        mock_settings_manager.get.return_value = [
            {"pattern": "/custom/path", "enabled": True},
            {"pattern": "*.tmp", "enabled": False},
        ]

        page = ExclusionsPage(mock_settings_manager)
        page.create_page()

        # Should call settings_manager.get to load exclusions
        mock_settings_manager.get.assert_called_with("exclusion_patterns", [])

    def test_create_page_without_settings_manager(self, mock_gi_modules):
        """Test create_page works without settings manager."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(None)
        # Should not raise exception
        result = page.create_page()
        assert result is not None


class TestExclusionsPageLoadCustomExclusions:
    """Tests for ExclusionsPage._load_custom_exclusions() method."""

    @pytest.fixture
    def mock_settings_manager(self):
        """Provide a mock settings manager."""
        manager = mock.MagicMock()
        manager.get.return_value = []
        return manager

    def test_load_custom_exclusions_with_no_settings_manager(self, mock_gi_modules):
        """Test _load_custom_exclusions handles None settings manager."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(None)
        # Should not raise exception
        page._load_custom_exclusions()

    def test_load_custom_exclusions_with_empty_list(self, mock_gi_modules, mock_settings_manager):
        """Test _load_custom_exclusions with empty exclusion list."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = []

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()
        page._load_custom_exclusions()

        mock_settings_manager.get.assert_called_with("exclusion_patterns", [])

    def test_load_custom_exclusions_with_valid_patterns(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _load_custom_exclusions loads valid patterns."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = [
            {"pattern": "/custom/path", "enabled": True},
            {"pattern": "*.tmp", "enabled": False},
        ]

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()

        with mock.patch.object(page, "_add_custom_exclusion_row") as mock_add:
            page._load_custom_exclusions()
            # Should call _add_custom_exclusion_row for each pattern
            assert mock_add.call_count == 2
            mock_add.assert_any_call("/custom/path", True)
            mock_add.assert_any_call("*.tmp", False)

    def test_load_custom_exclusions_skips_empty_patterns(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _load_custom_exclusions skips empty patterns."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = [
            {"pattern": "/valid/path", "enabled": True},
            {"pattern": "", "enabled": True},  # Empty pattern
            {"pattern": "/another/path", "enabled": False},
        ]

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()

        with mock.patch.object(page, "_add_custom_exclusion_row") as mock_add:
            page._load_custom_exclusions()
            # Should only add valid patterns
            assert mock_add.call_count == 2

    def test_load_custom_exclusions_handles_missing_pattern_key(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _load_custom_exclusions handles missing pattern key."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = [
            {"pattern": "/valid/path", "enabled": True},
            {"enabled": True},  # Missing pattern key
        ]

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()

        with mock.patch.object(page, "_add_custom_exclusion_row") as mock_add:
            page._load_custom_exclusions()
            # Should only add valid patterns
            assert mock_add.call_count == 1

    def test_load_custom_exclusions_handles_non_list(self, mock_gi_modules, mock_settings_manager):
        """Test _load_custom_exclusions handles non-list return value."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = "not a list"

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()

        # Should not raise exception
        page._load_custom_exclusions()


class TestExclusionsPageAddCustomExclusionRow:
    """Tests for ExclusionsPage._add_custom_exclusion_row() method."""

    @pytest.fixture
    def mock_settings_manager(self):
        """Provide a mock settings manager."""
        manager = mock.MagicMock()
        manager.get.return_value = []
        return manager

    def test_add_custom_exclusion_row_creates_switch_row(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _add_custom_exclusion_row creates a SwitchRow."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()

        page._add_custom_exclusion_row("/test/path", True)

        # Should create a SwitchRow
        adw.SwitchRow.assert_called()

    def test_add_custom_exclusion_row_sets_title(self, mock_gi_modules, mock_settings_manager):
        """Test _add_custom_exclusion_row sets row title to pattern."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_row = mock.MagicMock()
        adw.SwitchRow.side_effect = lambda *args, **kwargs: mock_row

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()

        page._add_custom_exclusion_row("/test/path", True)

        mock_row.set_title.assert_called_with("/test/path")

    def test_add_custom_exclusion_row_sets_active_state(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _add_custom_exclusion_row sets enabled state."""
        adw = mock_gi_modules["adw"]
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_row = mock.MagicMock()
        adw.SwitchRow.side_effect = lambda *args, **kwargs: mock_row

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()

        # Test enabled=True
        page._add_custom_exclusion_row("/test/path", True)
        mock_row.set_active.assert_called_with(True)

        # Test enabled=False
        mock_row.reset_mock()
        page._add_custom_exclusion_row("/another/path", False)
        mock_row.set_active.assert_called_with(False)

    def test_add_custom_exclusion_row_creates_remove_button(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _add_custom_exclusion_row creates remove button."""
        gtk = mock_gi_modules["gtk"]
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()

        page._add_custom_exclusion_row("/test/path", True)

        # Should create a Button for removal
        gtk.Button.assert_called()

    def test_add_custom_exclusion_row_adds_to_group(self, mock_gi_modules, mock_settings_manager):
        """Test _add_custom_exclusion_row adds row to group."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()

        page._add_custom_exclusion_row("/test/path", True)

        # Should add row to custom exclusions group
        page._custom_exclusions_group.add.assert_called()


class TestExclusionsPageAddCustomExclusion:
    """Tests for ExclusionsPage._on_add_custom_exclusion() method."""

    @pytest.fixture
    def mock_settings_manager(self):
        """Provide a mock settings manager."""
        manager = mock.MagicMock()
        manager.get.return_value = []
        return manager

    def test_on_add_custom_exclusion_ignores_empty_pattern(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_add_custom_exclusion ignores empty pattern."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page._custom_entry_row = mock.MagicMock()
        page._custom_entry_row.get_text.return_value = "   "  # Whitespace only

        page._on_add_custom_exclusion(None)

        # Should not call settings manager
        mock_settings_manager.set.assert_not_called()

    def test_on_add_custom_exclusion_ignores_without_settings_manager(self, mock_gi_modules):
        """Test _on_add_custom_exclusion ignores when no settings manager."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(None)
        page._custom_entry_row = mock.MagicMock()
        page._custom_entry_row.get_text.return_value = "/test/path"

        # Should not raise exception
        page._on_add_custom_exclusion(None)

    def test_on_add_custom_exclusion_adds_file_pattern(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_add_custom_exclusion adds file pattern (path starting with /)."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page._custom_entry_row = mock.MagicMock()
        page._custom_entry_row.get_text.return_value = "/test/path"
        page._custom_exclusions_group = mock.MagicMock()

        with mock.patch.object(page, "_add_custom_exclusion_row"):
            page._on_add_custom_exclusion(None)

        # Should add pattern with type "file"
        call_args = mock_settings_manager.set.call_args[0]
        assert call_args[0] == "exclusion_patterns"
        assert len(call_args[1]) == 1
        assert call_args[1][0]["pattern"] == "/test/path"
        assert call_args[1][0]["type"] == "file"
        assert call_args[1][0]["enabled"] is True

    def test_on_add_custom_exclusion_adds_generic_pattern(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_add_custom_exclusion adds generic pattern (not starting with /)."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page._custom_entry_row = mock.MagicMock()
        page._custom_entry_row.get_text.return_value = "*.tmp"
        page._custom_exclusions_group = mock.MagicMock()

        with mock.patch.object(page, "_add_custom_exclusion_row"):
            page._on_add_custom_exclusion(None)

        # Should add pattern with type "pattern"
        call_args = mock_settings_manager.set.call_args[0]
        assert call_args[1][0]["type"] == "pattern"

    def test_on_add_custom_exclusion_strips_whitespace(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_add_custom_exclusion strips whitespace from pattern."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page._custom_entry_row = mock.MagicMock()
        page._custom_entry_row.get_text.return_value = "  *.tmp  "
        page._custom_exclusions_group = mock.MagicMock()

        with mock.patch.object(page, "_add_custom_exclusion_row"):
            page._on_add_custom_exclusion(None)

        # Should strip whitespace
        call_args = mock_settings_manager.set.call_args[0]
        assert call_args[1][0]["pattern"] == "*.tmp"

    def test_on_add_custom_exclusion_avoids_duplicates(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_add_custom_exclusion avoids duplicate patterns."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = [
            {"pattern": "*.tmp", "type": "pattern", "enabled": True}
        ]

        page = ExclusionsPage(mock_settings_manager)
        page._custom_entry_row = mock.MagicMock()
        page._custom_entry_row.get_text.return_value = "*.tmp"
        page._custom_exclusions_group = mock.MagicMock()

        page._on_add_custom_exclusion(None)

        # Should not add duplicate
        mock_settings_manager.set.assert_not_called()

    def test_on_add_custom_exclusion_adds_to_ui(self, mock_gi_modules, mock_settings_manager):
        """Test _on_add_custom_exclusion adds row to UI."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page._custom_entry_row = mock.MagicMock()
        page._custom_entry_row.get_text.return_value = "/test/path"
        page._custom_exclusions_group = mock.MagicMock()

        with mock.patch.object(page, "_add_custom_exclusion_row") as mock_add:
            page._on_add_custom_exclusion(None)

        # Should call _add_custom_exclusion_row
        mock_add.assert_called_with("/test/path", True)

    def test_on_add_custom_exclusion_clears_entry(self, mock_gi_modules, mock_settings_manager):
        """Test _on_add_custom_exclusion clears entry field after adding."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(mock_settings_manager)
        page._custom_entry_row = mock.MagicMock()
        page._custom_entry_row.get_text.return_value = "/test/path"
        page._custom_exclusions_group = mock.MagicMock()

        with mock.patch.object(page, "_add_custom_exclusion_row"):
            page._on_add_custom_exclusion(None)

        # Should clear the entry
        page._custom_entry_row.set_text.assert_called_with("")

    def test_on_add_custom_exclusion_handles_non_list_settings(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_add_custom_exclusion handles non-list settings gracefully."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = "not a list"

        page = ExclusionsPage(mock_settings_manager)
        page._custom_entry_row = mock.MagicMock()
        page._custom_entry_row.get_text.return_value = "/test/path"
        page._custom_exclusions_group = mock.MagicMock()

        with mock.patch.object(page, "_add_custom_exclusion_row"):
            page._on_add_custom_exclusion(None)

        # Should convert to empty list and add pattern
        call_args = mock_settings_manager.set.call_args[0]
        assert len(call_args[1]) == 1


class TestExclusionsPageRemoveCustomExclusion:
    """Tests for ExclusionsPage._on_remove_custom_exclusion() method."""

    @pytest.fixture
    def mock_settings_manager(self):
        """Provide a mock settings manager."""
        manager = mock.MagicMock()
        manager.get.return_value = []
        return manager

    def test_on_remove_custom_exclusion_ignores_without_settings_manager(self, mock_gi_modules):
        """Test _on_remove_custom_exclusion ignores when no settings manager."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(None)
        mock_row = mock.MagicMock()

        # Should not raise exception
        page._on_remove_custom_exclusion(None, mock_row, "/test/path")

    def test_on_remove_custom_exclusion_removes_from_settings(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_remove_custom_exclusion removes pattern from settings."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = [
            {"pattern": "/test/path", "type": "file", "enabled": True},
            {"pattern": "*.tmp", "type": "pattern", "enabled": True},
        ]

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()
        mock_row = mock.MagicMock()

        page._on_remove_custom_exclusion(None, mock_row, "/test/path")

        # Should save updated list without the removed pattern
        call_args = mock_settings_manager.set.call_args[0]
        assert call_args[0] == "exclusion_patterns"
        assert len(call_args[1]) == 1
        assert call_args[1][0]["pattern"] == "*.tmp"

    def test_on_remove_custom_exclusion_removes_from_ui(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_remove_custom_exclusion removes row from UI."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = [
            {"pattern": "/test/path", "type": "file", "enabled": True}
        ]

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()
        mock_row = mock.MagicMock()

        page._on_remove_custom_exclusion(None, mock_row, "/test/path")

        # Should remove row from group
        page._custom_exclusions_group.remove.assert_called_with(mock_row)

    def test_on_remove_custom_exclusion_handles_non_list_settings(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_remove_custom_exclusion handles non-list settings."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = "not a list"

        page = ExclusionsPage(mock_settings_manager)
        page._custom_exclusions_group = mock.MagicMock()
        mock_row = mock.MagicMock()

        # Should not raise exception
        page._on_remove_custom_exclusion(None, mock_row, "/test/path")


class TestExclusionsPageToggleExclusion:
    """Tests for ExclusionsPage._on_exclusion_toggled() method."""

    @pytest.fixture
    def mock_settings_manager(self):
        """Provide a mock settings manager."""
        manager = mock.MagicMock()
        manager.get.return_value = []
        return manager

    def test_on_exclusion_toggled_ignores_without_settings_manager(self, mock_gi_modules):
        """Test _on_exclusion_toggled ignores when no settings manager."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        page = ExclusionsPage(None)
        mock_row = mock.MagicMock()
        mock_row.get_active.return_value = True

        # Should not raise exception
        page._on_exclusion_toggled(mock_row, None, "/test/path")

    def test_on_exclusion_toggled_updates_enabled_state(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_exclusion_toggled updates enabled state in settings."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = [
            {"pattern": "/test/path", "type": "file", "enabled": True},
            {"pattern": "*.tmp", "type": "pattern", "enabled": False},
        ]

        page = ExclusionsPage(mock_settings_manager)
        mock_row = mock.MagicMock()
        mock_row.get_active.return_value = False

        page._on_exclusion_toggled(mock_row, None, "/test/path")

        # Should update enabled state
        call_args = mock_settings_manager.set.call_args[0]
        assert call_args[0] == "exclusion_patterns"
        # Find the updated exclusion
        for excl in call_args[1]:
            if excl["pattern"] == "/test/path":
                assert excl["enabled"] is False

    def test_on_exclusion_toggled_preserves_other_patterns(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_exclusion_toggled preserves other patterns."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = [
            {"pattern": "/test/path", "type": "file", "enabled": True},
            {"pattern": "*.tmp", "type": "pattern", "enabled": False},
        ]

        page = ExclusionsPage(mock_settings_manager)
        mock_row = mock.MagicMock()
        mock_row.get_active.return_value = False

        page._on_exclusion_toggled(mock_row, None, "/test/path")

        # Should preserve other patterns
        call_args = mock_settings_manager.set.call_args[0]
        assert len(call_args[1]) == 2

    def test_on_exclusion_toggled_handles_non_list_settings(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_exclusion_toggled handles non-list settings."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = "not a list"

        page = ExclusionsPage(mock_settings_manager)
        mock_row = mock.MagicMock()
        mock_row.get_active.return_value = True

        # Should not raise exception (but won't update since not a list)
        page._on_exclusion_toggled(mock_row, None, "/test/path")

    def test_on_exclusion_toggled_handles_pattern_not_found(
        self, mock_gi_modules, mock_settings_manager
    ):
        """Test _on_exclusion_toggled handles pattern not in settings."""
        from src.ui.preferences.exclusions_page import ExclusionsPage

        mock_settings_manager.get.return_value = [
            {"pattern": "*.tmp", "type": "pattern", "enabled": False},
        ]

        page = ExclusionsPage(mock_settings_manager)
        mock_row = mock.MagicMock()
        mock_row.get_active.return_value = True

        # Should not raise exception
        page._on_exclusion_toggled(mock_row, None, "/test/path")
