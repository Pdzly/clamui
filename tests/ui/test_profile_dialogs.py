# ClamUI Profile Dialogs Tests
"""Unit tests for the profile dialogs UI components."""

import os

import pytest

# Check if we can use GTK (requires display)
_gtk_available = False
_gtk_init_error = None

try:
    # Set GDK backend for headless testing if no display
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        # Try to use a null/headless backend
        os.environ.setdefault("GDK_BACKEND", "broadway")

    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")

    # Try to initialize Adw to check if display is available
    # Note: In headless CI, this may fail
    _gtk_available = True
except Exception as e:
    _gtk_init_error = str(e)


# Skip all tests in this module if GTK is not available
pytestmark = pytest.mark.skipif(
    not _gtk_available, reason=f"GTK4/Adwaita not available: {_gtk_init_error}"
)


class TestProfileDialogImport:
    """Tests for ProfileDialog import and basic attributes."""

    def test_import_profile_dialog(self):
        """Test that ProfileDialog can be imported."""
        from src.ui.profile_dialogs import ProfileDialog

        assert ProfileDialog is not None

    def test_import_pattern_entry_dialog(self):
        """Test that PatternEntryDialog can be imported."""
        from src.ui.profile_dialogs import PatternEntryDialog

        assert PatternEntryDialog is not None

    def test_import_delete_profile_dialog(self):
        """Test that DeleteProfileDialog can be imported."""
        from src.ui.profile_dialogs import DeleteProfileDialog

        assert DeleteProfileDialog is not None

    def test_import_profile_list_dialog(self):
        """Test that ProfileListDialog can be imported."""
        from src.ui.profile_dialogs import ProfileListDialog

        assert ProfileListDialog is not None

    def test_profile_dialog_has_max_name_length(self):
        """Test that ProfileDialog defines MAX_NAME_LENGTH constant."""
        from src.ui.profile_dialogs import ProfileDialog

        assert hasattr(ProfileDialog, "MAX_NAME_LENGTH")
        assert isinstance(ProfileDialog.MAX_NAME_LENGTH, int)
        assert ProfileDialog.MAX_NAME_LENGTH > 0


class TestProfileDialogCreation:
    """Tests for ProfileDialog instantiation."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileDialog class."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog

    def test_create_dialog_without_profile(self, dialog_class):
        """Test creating dialog without an existing profile (new profile mode)."""
        dialog = dialog_class()
        assert dialog is not None
        assert dialog.get_title() == "New Profile"

    def test_create_dialog_with_profile_manager_none(self, dialog_class):
        """Test creating dialog with profile_manager=None."""
        dialog = dialog_class(profile_manager=None)
        assert dialog is not None
        assert dialog.get_title() == "New Profile"

    def test_dialog_is_deletable(self, dialog_class):
        """Test that dialog is configured to allow closing (deletable)."""
        dialog = dialog_class()
        assert dialog.get_deletable() is True

    def test_dialog_is_modal(self, dialog_class):
        """Test that dialog is configured as modal."""
        dialog = dialog_class()
        assert dialog.get_modal() is True

    def test_dialog_has_default_size(self, dialog_class):
        """Test that dialog has reasonable default dimensions."""
        dialog = dialog_class()
        width, height = dialog.get_default_size()
        assert width > 0
        assert height > 0

    def test_dialog_default_width_is_500(self, dialog_class):
        """Test that dialog has default width of 500."""
        dialog = dialog_class()
        width, _ = dialog.get_default_size()
        assert width == 500

    def test_dialog_default_height_is_600(self, dialog_class):
        """Test that dialog has default height of 600."""
        dialog = dialog_class()
        _, height = dialog.get_default_size()
        assert height == 600


class TestProfileDialogEditMode:
    """Tests for ProfileDialog edit mode with existing profile."""

    @pytest.fixture
    def mock_profile(self):
        """Create a mock profile object for testing."""

        class MockProfile:
            def __init__(self):
                self.id = "test-profile-123"
                self.name = "Test Profile"
                self.description = "A test profile description"
                self.targets = ["/home/user/documents", "/home/user/downloads"]
                self.exclusions = {
                    "paths": ["/home/user/documents/cache"],
                    "patterns": ["*.tmp", "*.log"],
                }
                self.is_default = False

        return MockProfile()

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileDialog class."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog

    def test_create_dialog_in_edit_mode(self, dialog_class, mock_profile):
        """Test creating dialog with existing profile (edit mode)."""
        dialog = dialog_class(profile=mock_profile)
        assert dialog is not None
        assert dialog.get_title() == "Edit Profile"

    def test_edit_mode_title_is_edit_profile(self, dialog_class, mock_profile):
        """Test that edit mode dialog has 'Edit Profile' title."""
        dialog = dialog_class(profile=mock_profile)
        assert dialog.get_title() == "Edit Profile"

    def test_edit_mode_loads_profile_name(self, dialog_class, mock_profile):
        """Test that edit mode loads the profile name."""
        dialog = dialog_class(profile=mock_profile)
        # The profile data should be accessible through get_profile_data
        data = dialog.get_profile_data()
        assert data["name"] == "Test Profile"

    def test_edit_mode_loads_profile_description(self, dialog_class, mock_profile):
        """Test that edit mode loads the profile description."""
        dialog = dialog_class(profile=mock_profile)
        data = dialog.get_profile_data()
        assert data["description"] == "A test profile description"

    def test_edit_mode_loads_targets(self, dialog_class, mock_profile):
        """Test that edit mode loads targets from profile."""
        dialog = dialog_class(profile=mock_profile)
        data = dialog.get_profile_data()
        assert len(data["targets"]) == 2
        assert "/home/user/documents" in data["targets"]
        assert "/home/user/downloads" in data["targets"]

    def test_edit_mode_loads_exclusion_paths(self, dialog_class, mock_profile):
        """Test that edit mode loads exclusion paths."""
        dialog = dialog_class(profile=mock_profile)
        data = dialog.get_profile_data()
        assert "paths" in data["exclusions"]
        assert "/home/user/documents/cache" in data["exclusions"]["paths"]

    def test_edit_mode_loads_exclusion_patterns(self, dialog_class, mock_profile):
        """Test that edit mode loads exclusion patterns."""
        dialog = dialog_class(profile=mock_profile)
        data = dialog.get_profile_data()
        assert "patterns" in data["exclusions"]
        assert "*.tmp" in data["exclusions"]["patterns"]
        assert "*.log" in data["exclusions"]["patterns"]


class TestProfileDialogGetProfileData:
    """Tests for ProfileDialog.get_profile_data() method."""

    @pytest.fixture
    def dialog(self):
        """Create a ProfileDialog instance for testing."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog()

    def test_get_profile_data_returns_dict(self, dialog):
        """Test that get_profile_data returns a dictionary."""
        data = dialog.get_profile_data()
        assert isinstance(data, dict)

    def test_get_profile_data_has_required_keys(self, dialog):
        """Test that get_profile_data contains required keys."""
        data = dialog.get_profile_data()
        assert "name" in data
        assert "description" in data
        assert "targets" in data
        assert "exclusions" in data

    def test_get_profile_data_name_is_string(self, dialog):
        """Test that name in profile data is a string."""
        data = dialog.get_profile_data()
        assert isinstance(data["name"], str)

    def test_get_profile_data_description_is_string(self, dialog):
        """Test that description in profile data is a string."""
        data = dialog.get_profile_data()
        assert isinstance(data["description"], str)

    def test_get_profile_data_targets_is_list(self, dialog):
        """Test that targets in profile data is a list."""
        data = dialog.get_profile_data()
        assert isinstance(data["targets"], list)

    def test_get_profile_data_exclusions_is_dict(self, dialog):
        """Test that exclusions in profile data is a dictionary."""
        data = dialog.get_profile_data()
        assert isinstance(data["exclusions"], dict)

    def test_new_dialog_has_empty_name(self, dialog):
        """Test that new dialog starts with empty name."""
        data = dialog.get_profile_data()
        assert data["name"] == ""

    def test_new_dialog_has_empty_targets(self, dialog):
        """Test that new dialog starts with empty targets."""
        data = dialog.get_profile_data()
        assert data["targets"] == []

    def test_new_dialog_has_empty_exclusions(self, dialog):
        """Test that new dialog starts with empty exclusions."""
        data = dialog.get_profile_data()
        assert data["exclusions"] == {}


class TestProfileDialogCallback:
    """Tests for ProfileDialog callback management."""

    @pytest.fixture
    def dialog(self):
        """Create a ProfileDialog instance for testing."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog()

    def test_set_on_profile_saved(self, dialog):
        """Test setting the on_profile_saved callback."""
        callback_called = []

        def callback(profile):
            callback_called.append(profile)

        dialog.set_on_profile_saved(callback)
        # The callback should be stored (we can verify by checking internal state)
        assert dialog._on_profile_saved is callback

    def test_set_on_profile_saved_with_none(self, dialog):
        """Test setting on_profile_saved callback to None."""
        dialog.set_on_profile_saved(None)
        assert dialog._on_profile_saved is None


class TestPatternEntryDialogCreation:
    """Tests for PatternEntryDialog instantiation."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the PatternEntryDialog class."""
        from src.ui.profile_dialogs import PatternEntryDialog

        return PatternEntryDialog

    def test_create_dialog(self, dialog_class):
        """Test creating PatternEntryDialog."""
        dialog = dialog_class()
        assert dialog is not None

    def test_dialog_title(self, dialog_class):
        """Test that dialog has correct title."""
        dialog = dialog_class()
        assert dialog.get_title() == "Add Exclusion Pattern"

    def test_dialog_is_deletable(self, dialog_class):
        """Test that dialog is configured to allow closing (deletable)."""
        dialog = dialog_class()
        assert dialog.get_deletable() is True

    def test_dialog_is_modal(self, dialog_class):
        """Test that dialog is configured as modal."""
        dialog = dialog_class()
        assert dialog.get_modal() is True

    def test_dialog_default_width(self, dialog_class):
        """Test that dialog has default width of 400."""
        dialog = dialog_class()
        width, _ = dialog.get_default_size()
        assert width == 400

    def test_dialog_default_height(self, dialog_class):
        """Test that dialog has default height of 200."""
        dialog = dialog_class()
        _, height = dialog.get_default_size()
        assert height == 200


class TestPatternEntryDialogGetPattern:
    """Tests for PatternEntryDialog.get_pattern() method."""

    @pytest.fixture
    def dialog(self):
        """Create a PatternEntryDialog instance for testing."""
        from src.ui.profile_dialogs import PatternEntryDialog

        return PatternEntryDialog()

    def test_get_pattern_returns_string(self, dialog):
        """Test that get_pattern returns a string."""
        result = dialog.get_pattern()
        assert isinstance(result, str)

    def test_get_pattern_initial_is_empty(self, dialog):
        """Test that get_pattern returns empty string initially."""
        result = dialog.get_pattern()
        assert result == ""


class TestDeleteProfileDialogCreation:
    """Tests for DeleteProfileDialog instantiation."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the DeleteProfileDialog class."""
        from src.ui.profile_dialogs import DeleteProfileDialog

        return DeleteProfileDialog

    def test_create_dialog_with_profile_name(self, dialog_class):
        """Test creating DeleteProfileDialog with profile name."""
        dialog = dialog_class(profile_name="My Profile")
        assert dialog is not None

    def test_dialog_heading(self, dialog_class):
        """Test that dialog has correct heading."""
        dialog = dialog_class(profile_name="My Profile")
        assert dialog.get_heading() == "Delete Profile?"

    def test_dialog_body_contains_profile_name(self, dialog_class):
        """Test that dialog body contains the profile name."""
        dialog = dialog_class(profile_name="My Profile")
        body = dialog.get_body()
        assert "My Profile" in body

    def test_dialog_body_warns_about_undo(self, dialog_class):
        """Test that dialog body warns about irreversible action."""
        dialog = dialog_class(profile_name="My Profile")
        body = dialog.get_body()
        assert "cannot be undone" in body

    def test_dialog_is_modal(self, dialog_class):
        """Test that dialog is configured as modal."""
        dialog = dialog_class(profile_name="Test")
        # Adw.Window-based dialog should be modal
        assert dialog.get_modal() is True

    def test_dialog_is_deletable(self, dialog_class):
        """Test that dialog is deletable (can be closed)."""
        dialog = dialog_class(profile_name="Test")
        # Adw.Window-based dialog should be deletable
        assert dialog.get_deletable() is True


class TestDeleteProfileDialogWithSpecialNames:
    """Tests for DeleteProfileDialog with special profile names."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the DeleteProfileDialog class."""
        from src.ui.profile_dialogs import DeleteProfileDialog

        return DeleteProfileDialog

    def test_dialog_with_empty_name(self, dialog_class):
        """Test dialog with empty profile name."""
        dialog = dialog_class(profile_name="")
        dialog.get_body()
        # Should still create dialog, even with empty name
        assert dialog is not None

    def test_dialog_with_special_characters(self, dialog_class):
        """Test dialog with special characters in profile name."""
        dialog = dialog_class(profile_name='Test "Profile" <>&')
        body = dialog.get_body()
        assert 'Test "Profile" <>&' in body

    def test_dialog_with_unicode_name(self, dialog_class):
        """Test dialog with unicode characters in profile name."""
        dialog = dialog_class(profile_name="Test Profile \u2713 \u2764")
        body = dialog.get_body()
        assert "Test Profile" in body

    def test_dialog_with_long_name(self, dialog_class):
        """Test dialog with very long profile name."""
        long_name = "A" * 200
        dialog = dialog_class(profile_name=long_name)
        body = dialog.get_body()
        assert long_name in body


class TestProfileListDialogCreation:
    """Tests for ProfileListDialog instantiation."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileListDialog class."""
        from src.ui.profile_dialogs import ProfileListDialog

        return ProfileListDialog

    def test_create_dialog(self, dialog_class):
        """Test creating ProfileListDialog."""
        dialog = dialog_class()
        assert dialog is not None

    def test_create_dialog_without_profile_manager(self, dialog_class):
        """Test creating dialog without profile manager."""
        dialog = dialog_class(profile_manager=None)
        assert dialog is not None

    def test_dialog_title(self, dialog_class):
        """Test that dialog has correct title."""
        dialog = dialog_class()
        assert dialog.get_title() == "Manage Profiles"

    def test_dialog_is_deletable(self, dialog_class):
        """Test that dialog is configured to allow closing (deletable)."""
        dialog = dialog_class()
        assert dialog.get_deletable() is True

    def test_dialog_is_modal(self, dialog_class):
        """Test that dialog is configured as modal."""
        dialog = dialog_class()
        assert dialog.get_modal() is True

    def test_dialog_default_width(self, dialog_class):
        """Test that dialog has default width of 500."""
        dialog = dialog_class()
        width, _ = dialog.get_default_size()
        assert width == 500

    def test_dialog_default_height(self, dialog_class):
        """Test that dialog has default height of 500."""
        dialog = dialog_class()
        _, height = dialog.get_default_size()
        assert height == 500


class TestProfileListDialogCallback:
    """Tests for ProfileListDialog callback management."""

    @pytest.fixture
    def dialog(self):
        """Create a ProfileListDialog instance for testing."""
        from src.ui.profile_dialogs import ProfileListDialog

        return ProfileListDialog()

    def test_set_on_profile_selected(self, dialog):
        """Test setting the on_profile_selected callback."""
        callback_called = []

        def callback(profile):
            callback_called.append(profile)

        dialog.set_on_profile_selected(callback)
        assert dialog._on_profile_selected is callback

    def test_set_on_profile_selected_with_none(self, dialog):
        """Test setting on_profile_selected callback to None."""
        dialog.set_on_profile_selected(None)
        assert dialog._on_profile_selected is None


class TestProfileListDialogWithMockManager:
    """Tests for ProfileListDialog with mock profile manager."""

    @pytest.fixture
    def mock_profile_manager(self):
        """Create a mock profile manager for testing."""

        class MockProfile:
            def __init__(
                self, id, name, description="", targets=None, is_default=False
            ):
                self.id = id
                self.name = name
                self.description = description
                self.targets = targets or []
                self.exclusions = {}
                self.is_default = is_default

        class MockProfileManager:
            def __init__(self):
                self._profiles = [
                    MockProfile("1", "Quick Scan", "A quick scan", ["/home"], False),
                    MockProfile("2", "Full Scan", "Complete system scan", ["/"], True),
                    MockProfile(
                        "3", "Custom Scan", "", ["/home/user/downloads"], False
                    ),
                ]

            def list_profiles(self):
                return self._profiles

            def get_profile(self, profile_id):
                for p in self._profiles:
                    if p.id == profile_id:
                        return p
                return None

            def delete_profile(self, profile_id):
                self._profiles = [p for p in self._profiles if p.id != profile_id]

            def export_profile(self, profile_id, path):
                pass

            def import_profile(self, path):
                pass

        return MockProfileManager()

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileListDialog class."""
        from src.ui.profile_dialogs import ProfileListDialog

        return ProfileListDialog

    def test_dialog_with_profile_manager(self, dialog_class, mock_profile_manager):
        """Test creating dialog with profile manager."""
        dialog = dialog_class(profile_manager=mock_profile_manager)
        assert dialog is not None


class TestProfileDialogMaxNameLength:
    """Tests for ProfileDialog MAX_NAME_LENGTH validation."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileDialog class."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog

    def test_max_name_length_is_50(self, dialog_class):
        """Test that MAX_NAME_LENGTH is 50."""
        assert dialog_class.MAX_NAME_LENGTH == 50

    def test_max_name_length_is_positive(self, dialog_class):
        """Test that MAX_NAME_LENGTH is positive."""
        assert dialog_class.MAX_NAME_LENGTH > 0


class TestProfileDialogWithEmptyProfile:
    """Tests for ProfileDialog with profile that has empty/None values."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileDialog class."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog

    @pytest.fixture
    def empty_profile(self):
        """Create a profile with minimal/empty values."""

        class EmptyProfile:
            def __init__(self):
                self.id = "empty-profile"
                self.name = "Empty"
                self.description = None
                self.targets = []
                self.exclusions = None
                self.is_default = False

        return EmptyProfile()

    def test_edit_mode_handles_none_description(self, dialog_class, empty_profile):
        """Test that edit mode handles None description gracefully."""
        dialog = dialog_class(profile=empty_profile)
        data = dialog.get_profile_data()
        assert data["description"] == ""

    def test_edit_mode_handles_empty_targets(self, dialog_class, empty_profile):
        """Test that edit mode handles empty targets list."""
        dialog = dialog_class(profile=empty_profile)
        data = dialog.get_profile_data()
        assert data["targets"] == []

    def test_edit_mode_handles_none_exclusions(self, dialog_class, empty_profile):
        """Test that edit mode handles None exclusions gracefully."""
        dialog = dialog_class(profile=empty_profile)
        data = dialog.get_profile_data()
        assert data["exclusions"] == {}


class TestProfileDialogWithPartialExclusions:
    """Tests for ProfileDialog with partial exclusion data."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileDialog class."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog

    @pytest.fixture
    def profile_with_paths_only(self):
        """Create a profile with only exclusion paths (no patterns)."""

        class Profile:
            def __init__(self):
                self.id = "paths-only"
                self.name = "Paths Only"
                self.description = ""
                self.targets = ["/home"]
                self.exclusions = {"paths": ["/home/cache"]}
                self.is_default = False

        return Profile()

    @pytest.fixture
    def profile_with_patterns_only(self):
        """Create a profile with only exclusion patterns (no paths)."""

        class Profile:
            def __init__(self):
                self.id = "patterns-only"
                self.name = "Patterns Only"
                self.description = ""
                self.targets = ["/home"]
                self.exclusions = {"patterns": ["*.tmp"]}
                self.is_default = False

        return Profile()

    def test_loads_exclusion_paths_only(self, dialog_class, profile_with_paths_only):
        """Test loading profile with only exclusion paths."""
        dialog = dialog_class(profile=profile_with_paths_only)
        data = dialog.get_profile_data()
        assert "paths" in data["exclusions"]
        assert "/home/cache" in data["exclusions"]["paths"]
        assert "patterns" not in data["exclusions"]

    def test_loads_exclusion_patterns_only(
        self, dialog_class, profile_with_patterns_only
    ):
        """Test loading profile with only exclusion patterns."""
        dialog = dialog_class(profile=profile_with_patterns_only)
        data = dialog.get_profile_data()
        assert "patterns" in data["exclusions"]
        assert "*.tmp" in data["exclusions"]["patterns"]
        assert "paths" not in data["exclusions"]


class TestProfileDialogMultiFileSelection:
    """Tests for ProfileDialog multi-file selection functionality."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileDialog class."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog

    def test_targets_selected_adds_multiple_files(self, dialog_class):
        """Test that selecting multiple files via dialog adds all to targets."""
        from unittest.mock import MagicMock

        from gi.repository import GLib

        dialog = dialog_class()

        # Mock GLib.Error for successful case
        mock_result = MagicMock()

        # Create mock file list with multiple files
        mock_file1 = MagicMock()
        mock_file1.get_path.return_value = "/home/user/file1.txt"

        mock_file2 = MagicMock()
        mock_file2.get_path.return_value = "/home/user/file2.txt"

        mock_file3 = MagicMock()
        mock_file3.get_path.return_value = "/home/user/file3.txt"

        mock_files = MagicMock()
        mock_files.get_n_items.return_value = 3
        mock_files.get_item.side_effect = [mock_file1, mock_file2, mock_file3]

        # Create mock dialog that returns our files
        mock_file_dialog = MagicMock()
        # First try select_multiple_folders_finish (will fail), then open_multiple_finish
        mock_file_dialog.select_multiple_folders_finish.side_effect = GLib.Error(
            "not folder selection"
        )
        mock_file_dialog.open_multiple_finish.return_value = mock_files

        dialog._on_targets_selected(mock_file_dialog, mock_result)

        data = dialog.get_profile_data()
        assert len(data["targets"]) == 3
        assert "/home/user/file1.txt" in data["targets"]
        assert "/home/user/file2.txt" in data["targets"]
        assert "/home/user/file3.txt" in data["targets"]


class TestProfileDialogMultiFolderSelection:
    """Tests for ProfileDialog multi-folder selection functionality."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileDialog class."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog

    def test_folders_selected_adds_multiple_folders(self, dialog_class):
        """Test that selecting multiple folders via dialog adds all to targets."""
        from unittest.mock import MagicMock

        dialog = dialog_class()

        # Mock result
        mock_result = MagicMock()

        # Create mock folder list with multiple folders
        mock_folder1 = MagicMock()
        mock_folder1.get_path.return_value = "/home/user/documents"

        mock_folder2 = MagicMock()
        mock_folder2.get_path.return_value = "/home/user/downloads"

        mock_folders = MagicMock()
        mock_folders.get_n_items.return_value = 2
        mock_folders.get_item.side_effect = [mock_folder1, mock_folder2]

        # Create mock dialog that returns our folders
        mock_file_dialog = MagicMock()
        mock_file_dialog.select_multiple_folders_finish.return_value = mock_folders

        dialog._on_targets_selected(mock_file_dialog, mock_result)

        data = dialog.get_profile_data()
        assert len(data["targets"]) == 2
        assert "/home/user/documents" in data["targets"]
        assert "/home/user/downloads" in data["targets"]


class TestProfileDialogTargetDuplicateDetection:
    """Tests for ProfileDialog target duplicate detection."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileDialog class."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog

    def test_duplicate_target_not_added(self, dialog_class):
        """Test that adding a duplicate target path is rejected."""
        from unittest.mock import MagicMock

        dialog = dialog_class()

        # First, add a target manually
        dialog._add_target_to_list("/home/user/documents")

        # Now try to add the same target via selection
        mock_result = MagicMock()

        mock_folder = MagicMock()
        mock_folder.get_path.return_value = "/home/user/documents"

        mock_folders = MagicMock()
        mock_folders.get_n_items.return_value = 1
        mock_folders.get_item.return_value = mock_folder

        mock_file_dialog = MagicMock()
        mock_file_dialog.select_multiple_folders_finish.return_value = mock_folders

        dialog._on_targets_selected(mock_file_dialog, mock_result)

        data = dialog.get_profile_data()
        # Should still only have one entry, not two
        assert len(data["targets"]) == 1

    def test_mixed_new_and_duplicate_targets(self, dialog_class):
        """Test that duplicates are rejected while new targets are added."""
        from unittest.mock import MagicMock

        dialog = dialog_class()

        # Add initial target
        dialog._add_target_to_list("/home/user/documents")

        # Now try to add mix of duplicate and new targets
        mock_result = MagicMock()

        mock_folder1 = MagicMock()
        mock_folder1.get_path.return_value = "/home/user/documents"  # Duplicate

        mock_folder2 = MagicMock()
        mock_folder2.get_path.return_value = "/home/user/downloads"  # New

        mock_folders = MagicMock()
        mock_folders.get_n_items.return_value = 2
        mock_folders.get_item.side_effect = [mock_folder1, mock_folder2]

        mock_file_dialog = MagicMock()
        mock_file_dialog.select_multiple_folders_finish.return_value = mock_folders

        dialog._on_targets_selected(mock_file_dialog, mock_result)

        data = dialog.get_profile_data()
        # Should have 2 targets (original + new one, but not duplicate)
        assert len(data["targets"]) == 2
        assert "/home/user/documents" in data["targets"]
        assert "/home/user/downloads" in data["targets"]


class TestProfileDialogExclusionPathMultiSelection:
    """Tests for ProfileDialog exclusion path multi-selection."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileDialog class."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog

    def test_multiple_exclusion_paths_added(self, dialog_class):
        """Test that selecting multiple exclusion paths adds all."""
        from unittest.mock import MagicMock

        dialog = dialog_class()

        mock_result = MagicMock()

        mock_folder1 = MagicMock()
        mock_folder1.get_path.return_value = "/home/user/.cache"

        mock_folder2 = MagicMock()
        mock_folder2.get_path.return_value = "/home/user/.local"

        mock_folders = MagicMock()
        mock_folders.get_n_items.return_value = 2
        mock_folders.get_item.side_effect = [mock_folder1, mock_folder2]

        mock_file_dialog = MagicMock()
        mock_file_dialog.select_multiple_folders_finish.return_value = mock_folders

        dialog._on_exclusion_paths_selected(mock_file_dialog, mock_result)

        data = dialog.get_profile_data()
        assert "paths" in data["exclusions"]
        assert len(data["exclusions"]["paths"]) == 2
        assert "/home/user/.cache" in data["exclusions"]["paths"]
        assert "/home/user/.local" in data["exclusions"]["paths"]

    def test_duplicate_exclusion_path_not_added(self, dialog_class):
        """Test that duplicate exclusion paths are rejected."""
        from unittest.mock import MagicMock

        dialog = dialog_class()

        # Add initial exclusion path
        dialog._add_exclusion_path_to_list("/home/user/.cache")

        # Try to add duplicate
        mock_result = MagicMock()

        mock_folder = MagicMock()
        mock_folder.get_path.return_value = "/home/user/.cache"

        mock_folders = MagicMock()
        mock_folders.get_n_items.return_value = 1
        mock_folders.get_item.return_value = mock_folder

        mock_file_dialog = MagicMock()
        mock_file_dialog.select_multiple_folders_finish.return_value = mock_folders

        dialog._on_exclusion_paths_selected(mock_file_dialog, mock_result)

        data = dialog.get_profile_data()
        assert len(data["exclusions"]["paths"]) == 1


class TestProfileDialogOpenFileDialogParams:
    """Tests for ProfileDialog file dialog parameter handling."""

    @pytest.fixture
    def dialog_class(self):
        """Import and return the ProfileDialog class."""
        from src.ui.profile_dialogs import ProfileDialog

        return ProfileDialog

    def test_add_target_folder_uses_multiple_selection(self, dialog_class):
        """Test that add target folder button uses multi-selection."""
        from unittest.mock import MagicMock, patch

        dialog = dialog_class()

        # Mock get_root to return a window
        dialog.get_root = MagicMock()

        with patch.object(dialog, "_open_file_dialog") as mock_open:
            dialog._on_add_target_folder_clicked(MagicMock())

            mock_open.assert_called_once()
            call_kwargs = mock_open.call_args
            assert call_kwargs[1]["select_folder"] is True
            assert call_kwargs[1]["multiple"] is True

    def test_add_target_file_uses_multiple_selection(self, dialog_class):
        """Test that add target file button uses multi-selection."""
        from unittest.mock import MagicMock, patch

        dialog = dialog_class()

        dialog.get_root = MagicMock()

        with patch.object(dialog, "_open_file_dialog") as mock_open:
            dialog._on_add_target_file_clicked(MagicMock())

            mock_open.assert_called_once()
            call_kwargs = mock_open.call_args
            assert call_kwargs[1]["select_folder"] is False
            assert call_kwargs[1]["multiple"] is True

    def test_add_exclusion_path_uses_multiple_selection(self, dialog_class):
        """Test that add exclusion path button uses multi-selection."""
        from unittest.mock import MagicMock, patch

        dialog = dialog_class()

        dialog.get_root = MagicMock()

        with patch.object(dialog, "_open_file_dialog") as mock_open:
            dialog._on_add_exclusion_path_clicked(MagicMock())

            mock_open.assert_called_once()
            call_kwargs = mock_open.call_args
            assert call_kwargs[1]["select_folder"] is True
            assert call_kwargs[1]["multiple"] is True
