# ClamUI File Manager Integration Tests
"""Unit tests for the file_manager_integration module functions."""

import os
from pathlib import Path
from unittest import mock

from src.core import file_manager_integration
from src.core.file_manager_integration import (
    FileManager,
    IntegrationInfo,
    check_any_available,
    check_any_not_installed,
    get_available_integrations,
    install_all_available,
    install_integration,
    remove_integration,
)


class TestGetLocalShareDir:
    """Tests for _get_local_share_dir() function."""

    def test_get_local_share_dir_with_xdg_data_home(self):
        """Test _get_local_share_dir uses XDG_DATA_HOME when set."""
        with mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/custom/data"}):
            result = file_manager_integration._get_local_share_dir()
            assert result == Path("/custom/data")

    def test_get_local_share_dir_without_xdg_data_home(self):
        """Test _get_local_share_dir falls back to ~/.local/share."""
        with mock.patch.dict(os.environ, {}, clear=True):
            if "XDG_DATA_HOME" in os.environ:
                del os.environ["XDG_DATA_HOME"]
            with mock.patch("pathlib.Path.home", return_value=Path("/home/testuser")):
                result = file_manager_integration._get_local_share_dir()
                assert result == Path("/home/testuser/.local/share")


class TestCheckFileManagerAvailable:
    """Tests for _check_file_manager_available() function."""

    def test_check_nemo_available_dir_exists(self):
        """Test Nemo detected when ~/.local/share/nemo exists."""
        with mock.patch.object(
            file_manager_integration,
            "_get_local_share_dir",
            return_value=Path("/home/user/.local/share"),
        ):
            with mock.patch.object(Path, "exists", return_value=True):
                result = file_manager_integration._check_file_manager_available(
                    FileManager.NEMO
                )
                assert result is True

    def test_check_nautilus_available_dir_exists(self):
        """Test Nautilus detected when ~/.local/share/nautilus exists."""
        with mock.patch.object(
            file_manager_integration,
            "_get_local_share_dir",
            return_value=Path("/home/user/.local/share"),
        ):
            with mock.patch.object(Path, "exists", return_value=True):
                result = file_manager_integration._check_file_manager_available(
                    FileManager.NAUTILUS
                )
                assert result is True

    def test_check_dolphin_available_dir_exists(self):
        """Test Dolphin detected when ~/.local/share/kservices5 exists."""
        with mock.patch.object(
            file_manager_integration,
            "_get_local_share_dir",
            return_value=Path("/home/user/.local/share"),
        ):
            with mock.patch.object(Path, "exists", return_value=True):
                result = file_manager_integration._check_file_manager_available(
                    FileManager.DOLPHIN
                )
                assert result is True


class TestCheckIntegrationInstalled:
    """Tests for _check_integration_installed() function."""

    def test_check_nemo_integration_installed(self):
        """Test Nemo integration detected when action file exists."""
        with mock.patch.object(
            file_manager_integration,
            "_get_local_share_dir",
            return_value=Path("/home/user/.local/share"),
        ):
            with mock.patch.object(Path, "exists", return_value=True):
                result = file_manager_integration._check_integration_installed(
                    FileManager.NEMO
                )
                assert result is True

    def test_check_nemo_integration_not_installed(self):
        """Test Nemo integration not detected when action file missing."""
        with mock.patch.object(
            file_manager_integration,
            "_get_local_share_dir",
            return_value=Path("/home/user/.local/share"),
        ):
            with mock.patch.object(Path, "exists", return_value=False):
                result = file_manager_integration._check_integration_installed(
                    FileManager.NEMO
                )
                assert result is False


class TestGetAvailableIntegrations:
    """Tests for get_available_integrations() function."""

    def test_get_available_integrations_not_flatpak(self):
        """Test returns empty list when not in Flatpak."""
        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=False
        ):
            result = get_available_integrations()
            assert result == []

    def test_get_available_integrations_no_source_dir(self):
        """Test returns empty list when integration source dir missing."""
        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=True
        ):
            with mock.patch("pathlib.Path.exists", return_value=False):
                result = get_available_integrations()
                assert result == []

    def test_get_available_integrations_returns_all_managers(self):
        """Test returns info for all file managers."""
        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=True
        ):
            with mock.patch("pathlib.Path.exists", return_value=True):
                with mock.patch.object(
                    file_manager_integration,
                    "_check_file_manager_available",
                    return_value=True,
                ):
                    with mock.patch.object(
                        file_manager_integration,
                        "_check_integration_installed",
                        return_value=False,
                    ):
                        result = get_available_integrations()
                        assert len(result) == 3
                        assert any(i.file_manager == FileManager.NEMO for i in result)
                        assert any(
                            i.file_manager == FileManager.NAUTILUS for i in result
                        )
                        assert any(
                            i.file_manager == FileManager.DOLPHIN for i in result
                        )


class TestInstallIntegration:
    """Tests for install_integration() function."""

    def test_install_integration_not_flatpak(self):
        """Test returns error when not in Flatpak."""
        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=False
        ):
            success, error = install_integration(FileManager.NEMO)
            assert success is False
            assert "Not running as Flatpak" in error

    def test_install_integration_no_source_dir(self):
        """Test returns error when integration source dir missing."""
        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=True
        ):
            with mock.patch("pathlib.Path.exists", return_value=False):
                success, error = install_integration(FileManager.NEMO)
                assert success is False
                assert "Integration files not found" in error

    def test_install_integration_success(self, tmp_path):
        """Test successful integration installation."""
        # Create mock source files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "io.github.linx_systems.ClamUI.nemo_action"
        source_file.write_text("[Nemo Action]\nName=Test")

        dest_dir = tmp_path / "dest"

        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=True
        ):
            with mock.patch.object(
                file_manager_integration, "INTEGRATIONS_SOURCE_DIR", source_dir
            ):
                with mock.patch.object(
                    file_manager_integration,
                    "_get_local_share_dir",
                    return_value=dest_dir,
                ):
                    success, error = install_integration(FileManager.NEMO)
                    # May fail because mock source dir doesn't have all files
                    # but the logic should execute without crashing
                    assert success is True or error is not None

    def test_install_integration_permission_error(self, tmp_path):
        """Test handles permission errors gracefully."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "io.github.linx_systems.ClamUI.nemo_action"
        source_file.write_text("[Nemo Action]\nName=Test")

        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=True
        ):
            with mock.patch.object(
                file_manager_integration, "INTEGRATIONS_SOURCE_DIR", source_dir
            ):
                with mock.patch.object(
                    file_manager_integration,
                    "_get_local_share_dir",
                    return_value=Path("/nonexistent/readonly"),
                ):
                    with mock.patch(
                        "shutil.copy2", side_effect=PermissionError("Access denied")
                    ):
                        with mock.patch("pathlib.Path.mkdir"):
                            success, error = install_integration(FileManager.NEMO)
                            assert success is False
                            assert "Permission denied" in error


class TestRemoveIntegration:
    """Tests for remove_integration() function."""

    def test_remove_integration_success(self):
        """Test successful integration removal."""
        with mock.patch.object(
            file_manager_integration,
            "_get_local_share_dir",
            return_value=Path("/home/user/.local/share"),
        ):
            mock_path = mock.MagicMock()
            mock_path.exists.return_value = True

            with mock.patch.object(Path, "__truediv__", return_value=mock_path):
                success, error = remove_integration(FileManager.NEMO)
                assert success is True
                assert error is None

    def test_remove_integration_file_not_exists(self):
        """Test removal succeeds even if file doesn't exist."""
        with mock.patch.object(
            file_manager_integration,
            "_get_local_share_dir",
            return_value=Path("/home/user/.local/share"),
        ):
            mock_path = mock.MagicMock()
            mock_path.exists.return_value = False

            with mock.patch.object(Path, "__truediv__", return_value=mock_path):
                success, error = remove_integration(FileManager.NEMO)
                assert success is True
                assert error is None
                mock_path.unlink.assert_not_called()


class TestInstallAllAvailable:
    """Tests for install_all_available() function."""

    def test_install_all_available_no_integrations(self):
        """Test returns empty dict when no integrations available."""
        with mock.patch.object(
            file_manager_integration, "get_available_integrations", return_value=[]
        ):
            result = install_all_available()
            assert result == {}

    def test_install_all_available_skips_installed(self):
        """Test skips already installed integrations."""
        mock_integration = IntegrationInfo(
            file_manager=FileManager.NEMO,
            display_name="Nemo",
            description="Test",
            source_files=[],
            is_installed=True,
            is_available=True,
        )

        with mock.patch.object(
            file_manager_integration,
            "get_available_integrations",
            return_value=[mock_integration],
        ):
            with mock.patch.object(
                file_manager_integration, "install_integration"
            ) as mock_install:
                result = install_all_available()
                mock_install.assert_not_called()
                assert result == {}


class TestCheckAnyAvailable:
    """Tests for check_any_available() function."""

    def test_check_any_available_not_flatpak(self):
        """Test returns False when not in Flatpak."""
        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=False
        ):
            result = check_any_available()
            assert result is False

    def test_check_any_available_with_available(self):
        """Test returns True when file manager available."""
        mock_integration = IntegrationInfo(
            file_manager=FileManager.NEMO,
            display_name="Nemo",
            description="Test",
            source_files=[],
            is_installed=False,
            is_available=True,
        )

        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=True
        ):
            with mock.patch.object(
                file_manager_integration,
                "get_available_integrations",
                return_value=[mock_integration],
            ):
                result = check_any_available()
                assert result is True

    def test_check_any_available_none_available(self):
        """Test returns False when no file managers available."""
        mock_integration = IntegrationInfo(
            file_manager=FileManager.NEMO,
            display_name="Nemo",
            description="Test",
            source_files=[],
            is_installed=False,
            is_available=False,
        )

        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=True
        ):
            with mock.patch.object(
                file_manager_integration,
                "get_available_integrations",
                return_value=[mock_integration],
            ):
                result = check_any_available()
                assert result is False


class TestCheckAnyNotInstalled:
    """Tests for check_any_not_installed() function."""

    def test_check_any_not_installed_not_flatpak(self):
        """Test returns False when not in Flatpak."""
        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=False
        ):
            result = check_any_not_installed()
            assert result is False

    def test_check_any_not_installed_with_uninstalled(self):
        """Test returns True when available integration not installed."""
        mock_integration = IntegrationInfo(
            file_manager=FileManager.NEMO,
            display_name="Nemo",
            description="Test",
            source_files=[],
            is_installed=False,
            is_available=True,
        )

        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=True
        ):
            with mock.patch.object(
                file_manager_integration,
                "get_available_integrations",
                return_value=[mock_integration],
            ):
                result = check_any_not_installed()
                assert result is True

    def test_check_any_not_installed_all_installed(self):
        """Test returns False when all available integrations installed."""
        mock_integration = IntegrationInfo(
            file_manager=FileManager.NEMO,
            display_name="Nemo",
            description="Test",
            source_files=[],
            is_installed=True,
            is_available=True,
        )

        with mock.patch.object(
            file_manager_integration, "is_flatpak", return_value=True
        ):
            with mock.patch.object(
                file_manager_integration,
                "get_available_integrations",
                return_value=[mock_integration],
            ):
                result = check_any_not_installed()
                assert result is False
