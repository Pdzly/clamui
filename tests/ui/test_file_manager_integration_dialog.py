# ClamUI File Manager Integration Dialog Tests
"""Unit tests for the FileManagerIntegrationDialog class."""

from unittest import mock


class TestFileManagerIntegrationDialog:
    """Tests for FileManagerIntegrationDialog class."""

    def test_dialog_initialization(self, mock_gi_modules):
        """Test dialog initializes correctly."""
        # Import after mocking
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        dialog = FileManagerIntegrationDialog(
            settings_manager=mock_settings,
            on_complete=lambda: None,
        )

        assert dialog._settings_manager == mock_settings
        assert dialog._on_complete is not None

    def test_dialog_title_set(self, mock_gi_modules):
        """Test dialog sets correct title."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        dialog.set_title.assert_called_with("File Manager Integration")

    def test_dialog_dimensions(self, mock_gi_modules):
        """Test dialog sets correct dimensions."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        dialog.set_content_width.assert_called_with(500)
        dialog.set_content_height.assert_called_with(450)

    def test_on_skip_saves_preference(self, mock_gi_modules):
        """Test skip button saves 'prompted' preference."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()
        completed = []

        dialog = FileManagerIntegrationDialog(
            settings_manager=mock_settings,
            on_complete=lambda: completed.append(True),
        )

        # Simulate the dont_ask_switch being inactive
        dialog._dont_ask_switch = mock.MagicMock()
        dialog._dont_ask_switch.get_active.return_value = False

        dialog._on_skip_clicked(mock.MagicMock())

        # Should set prompted to True
        mock_settings.set.assert_called_with("file_manager_integration_prompted", True)

    def test_on_install_installs_selected_integrations(self, mock_gi_modules):
        """Test install button installs selected integrations."""
        from src.core.file_manager_integration import FileManager
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        with mock.patch(
            "src.ui.file_manager_integration_dialog.install_integration"
        ) as mock_install:
            mock_install.return_value = (True, None)

            dialog = FileManagerIntegrationDialog(settings_manager=mock_settings)

            # Create mock switch row that is active and sensitive
            mock_row = mock.MagicMock()
            mock_row.get_active.return_value = True
            mock_row.get_sensitive.return_value = True

            dialog._integration_rows = {FileManager.NEMO: mock_row}
            dialog._dont_ask_switch = mock.MagicMock()
            dialog._dont_ask_switch.get_active.return_value = False

            dialog._on_install_clicked(mock.MagicMock())

            mock_install.assert_called_once_with(FileManager.NEMO)

    def test_on_install_skips_disabled_rows(self, mock_gi_modules):
        """Test install button skips disabled (already installed) rows."""
        from src.core.file_manager_integration import FileManager
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        with mock.patch(
            "src.ui.file_manager_integration_dialog.install_integration"
        ) as mock_install:
            dialog = FileManagerIntegrationDialog(settings_manager=mock_settings)

            # Create mock switch row that is not sensitive (already installed)
            mock_row = mock.MagicMock()
            mock_row.get_active.return_value = True
            mock_row.get_sensitive.return_value = False

            dialog._integration_rows = {FileManager.NEMO: mock_row}
            dialog._dont_ask_switch = mock.MagicMock()
            dialog._dont_ask_switch.get_active.return_value = False

            dialog._on_install_clicked(mock.MagicMock())

            mock_install.assert_not_called()

    def test_on_install_skips_unchecked_rows(self, mock_gi_modules):
        """Test install button skips unchecked rows."""
        from src.core.file_manager_integration import FileManager
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()

        with mock.patch(
            "src.ui.file_manager_integration_dialog.install_integration"
        ) as mock_install:
            dialog = FileManagerIntegrationDialog(settings_manager=mock_settings)

            # Create mock switch row that is not active (unchecked)
            mock_row = mock.MagicMock()
            mock_row.get_active.return_value = False
            mock_row.get_sensitive.return_value = True

            dialog._integration_rows = {FileManager.NEMO: mock_row}
            dialog._dont_ask_switch = mock.MagicMock()
            dialog._dont_ask_switch.get_active.return_value = False

            dialog._on_install_clicked(mock.MagicMock())

            mock_install.assert_not_called()

    def test_get_file_manager_icon_nemo(self, mock_gi_modules):
        """Test returns correct icon for Nemo."""
        from src.core.file_manager_integration import FileManager
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        icon = dialog._get_file_manager_icon(FileManager.NEMO)
        assert icon == "system-file-manager-symbolic"

    def test_get_file_manager_icon_nautilus(self, mock_gi_modules):
        """Test returns correct icon for Nautilus."""
        from src.core.file_manager_integration import FileManager
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        icon = dialog._get_file_manager_icon(FileManager.NAUTILUS)
        assert icon == "org.gnome.Nautilus-symbolic"

    def test_get_file_manager_icon_dolphin(self, mock_gi_modules):
        """Test returns correct icon for Dolphin."""
        from src.core.file_manager_integration import FileManager
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        icon = dialog._get_file_manager_icon(FileManager.DOLPHIN)
        assert icon == "system-file-manager-symbolic"

    def test_on_complete_callback_called(self, mock_gi_modules):
        """Test on_complete callback is called after dialog closes."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        mock_settings = mock.MagicMock()
        completed = []

        dialog = FileManagerIntegrationDialog(
            settings_manager=mock_settings,
            on_complete=lambda: completed.append(True),
        )

        dialog._dont_ask_switch = mock.MagicMock()
        dialog._dont_ask_switch.get_active.return_value = False

        dialog._save_preference_and_close()

        assert len(completed) == 1

    def test_show_toast(self, mock_gi_modules):
        """Test toast notification is shown."""
        from src.ui.file_manager_integration_dialog import FileManagerIntegrationDialog

        dialog = FileManagerIntegrationDialog()

        dialog._show_toast("Test message")

        # Verify add_toast was called on the toast overlay
        dialog._toast_overlay.add_toast.assert_called_once()
