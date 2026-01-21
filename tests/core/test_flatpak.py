# ClamUI Flatpak Tests
"""Unit tests for the flatpak module functions."""

import subprocess
import threading
from pathlib import Path
from unittest import mock

from src.core import flatpak


class TestIsFlatpak:
    """Tests for is_flatpak() function."""

    def test_is_flatpak_when_flatpak_info_exists(self):
        """Test is_flatpak returns True when /.flatpak-info exists."""
        # Reset cache
        flatpak._flatpak_detected = None

        with mock.patch("os.path.exists", return_value=True) as mock_exists:
            result = flatpak.is_flatpak()
            assert result is True
            mock_exists.assert_called_once_with("/.flatpak-info")

    def test_is_flatpak_when_flatpak_info_missing(self):
        """Test is_flatpak returns False when /.flatpak-info does not exist."""
        # Reset cache
        flatpak._flatpak_detected = None

        with mock.patch("os.path.exists", return_value=False) as mock_exists:
            result = flatpak.is_flatpak()
            assert result is False
            mock_exists.assert_called_once_with("/.flatpak-info")

    def test_is_flatpak_caching(self):
        """Test is_flatpak caches the result after first check."""
        # Reset cache
        flatpak._flatpak_detected = None

        with mock.patch("os.path.exists", return_value=True) as mock_exists:
            # First call should check filesystem
            result1 = flatpak.is_flatpak()
            assert result1 is True
            assert mock_exists.call_count == 1

            # Second call should use cached value
            result2 = flatpak.is_flatpak()
            assert result2 is True
            # Still only called once
            assert mock_exists.call_count == 1

    def test_is_flatpak_thread_safety(self):
        """Test is_flatpak is thread-safe."""
        # Reset cache
        flatpak._flatpak_detected = None

        results = []

        def check_flatpak():
            result = flatpak.is_flatpak()
            results.append(result)

        with mock.patch("os.path.exists", return_value=True):
            threads = [threading.Thread(target=check_flatpak) for _ in range(10)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        # All threads should get the same result
        assert len(results) == 10
        assert all(r is True for r in results)


class TestWrapHostCommand:
    """Tests for wrap_host_command() function."""

    def test_wrap_host_command_not_in_flatpak(self):
        """Test wrap_host_command returns original command when not in Flatpak."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            command = ["clamscan", "--version"]
            result = flatpak.wrap_host_command(command)
            assert result == ["clamscan", "--version"]

    def test_wrap_host_command_in_flatpak(self):
        """Test wrap_host_command wraps command when in Flatpak."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=True):
            command = ["clamscan", "--version"]
            result = flatpak.wrap_host_command(command)
            assert result == ["flatpak-spawn", "--host", "clamscan", "--version"]

    def test_wrap_host_command_empty_command(self):
        """Test wrap_host_command handles empty command."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=True):
            command = []
            result = flatpak.wrap_host_command(command)
            assert result == []

    def test_wrap_host_command_preserves_list(self):
        """Test wrap_host_command returns a new list."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            command = ["clamscan", "--version"]
            result = flatpak.wrap_host_command(command)
            assert result == command
            assert result is not command  # New list object

    def test_wrap_host_command_with_arguments(self):
        """Test wrap_host_command handles commands with many arguments."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=True):
            command = [
                "clamscan",
                "-r",
                "/home/user",
                "--verbose",
                "--max-filesize=100M",
            ]
            result = flatpak.wrap_host_command(command)
            assert result == [
                "flatpak-spawn",
                "--host",
                "clamscan",
                "-r",
                "/home/user",
                "--verbose",
                "--max-filesize=100M",
            ]


class TestWhichHostCommand:
    """Tests for which_host_command() function."""

    def test_which_host_command_not_in_flatpak_found(self):
        """Test which_host_command uses shutil.which when not in Flatpak."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            with mock.patch(
                "shutil.which", return_value="/usr/bin/clamscan"
            ) as mock_which:
                result = flatpak.which_host_command("clamscan")
                assert result == "/usr/bin/clamscan"
                mock_which.assert_called_once_with("clamscan")

    def test_which_host_command_not_in_flatpak_not_found(self):
        """Test which_host_command returns None when binary not found."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            with mock.patch("shutil.which", return_value=None):
                result = flatpak.which_host_command("nonexistent")
                assert result is None

    def test_which_host_command_in_flatpak_found(self):
        """Test which_host_command uses flatpak-spawn when in Flatpak."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=True):
            mock_result = mock.Mock()
            mock_result.returncode = 0
            mock_result.stdout = "/usr/bin/clamscan\n"

            with mock.patch("subprocess.run", return_value=mock_result) as mock_run:
                result = flatpak.which_host_command("clamscan")
                assert result == "/usr/bin/clamscan"
                mock_run.assert_called_once_with(
                    ["flatpak-spawn", "--host", "which", "clamscan"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

    def test_which_host_command_in_flatpak_not_found(self):
        """Test which_host_command returns None when binary not found in Flatpak."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=True):
            mock_result = mock.Mock()
            mock_result.returncode = 1

            with mock.patch("subprocess.run", return_value=mock_result):
                result = flatpak.which_host_command("nonexistent")
                assert result is None

    def test_which_host_command_in_flatpak_timeout(self):
        """Test which_host_command handles timeout gracefully."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=True):
            with mock.patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="which", timeout=5),
            ):
                result = flatpak.which_host_command("clamscan")
                assert result is None

    def test_which_host_command_in_flatpak_exception(self):
        """Test which_host_command handles exceptions gracefully."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=True):
            with mock.patch(
                "subprocess.run", side_effect=Exception("Unexpected error")
            ):
                result = flatpak.which_host_command("clamscan")
                assert result is None


class TestResolvePortalPathViaXattr:
    """Tests for _resolve_portal_path_via_xattr() function."""

    def test_resolve_portal_path_via_xattr_success(self):
        """Test _resolve_portal_path_via_xattr resolves path via xattr."""
        mock_xattr = mock.MagicMock()
        mock_xattr.getxattr.return_value = b"/home/user/Documents/file.txt\x00"

        with mock.patch.dict("sys.modules", {"xattr": mock_xattr}):
            result = flatpak._resolve_portal_path_via_xattr(
                "/run/user/1000/doc/abc123/file.txt"
            )
            assert result == "/home/user/Documents/file.txt"

    def test_resolve_portal_path_via_xattr_tries_multiple_attrs(self):
        """Test _resolve_portal_path_via_xattr tries multiple attribute names."""
        mock_xattr = mock.MagicMock()
        # First two attrs fail, third succeeds
        mock_xattr.getxattr.side_effect = [
            OSError(),
            KeyError(),
            b"/home/user/file.txt\x00",
        ]

        with mock.patch.dict("sys.modules", {"xattr": mock_xattr}):
            result = flatpak._resolve_portal_path_via_xattr(
                "/run/user/1000/doc/abc123/file.txt"
            )
            assert result == "/home/user/file.txt"

    def test_resolve_portal_path_via_xattr_not_found(self):
        """Test _resolve_portal_path_via_xattr returns None when attrs not found."""
        mock_xattr = mock.MagicMock()
        mock_xattr.getxattr.side_effect = OSError()

        with mock.patch.dict("sys.modules", {"xattr": mock_xattr}):
            result = flatpak._resolve_portal_path_via_xattr(
                "/run/user/1000/doc/abc123/file.txt"
            )
            assert result is None

    def test_resolve_portal_path_via_xattr_no_xattr_module(self):
        """Test _resolve_portal_path_via_xattr returns None when xattr not available."""
        with mock.patch.dict("sys.modules", {"xattr": None}):
            with mock.patch("builtins.__import__", side_effect=ImportError()):
                result = flatpak._resolve_portal_path_via_xattr(
                    "/run/user/1000/doc/abc123/file.txt"
                )
                assert result is None

    def test_resolve_portal_path_via_xattr_generic_exception(self):
        """Test _resolve_portal_path_via_xattr handles generic exceptions."""
        mock_xattr = mock.MagicMock()
        mock_xattr.getxattr.side_effect = Exception("Unexpected error")

        with mock.patch.dict("sys.modules", {"xattr": mock_xattr}):
            result = flatpak._resolve_portal_path_via_xattr(
                "/run/user/1000/doc/abc123/file.txt"
            )
            assert result is None


class TestResolvePortalPathViaGio:
    """Tests for _resolve_portal_path_via_gio() function."""

    def test_resolve_portal_path_via_gio_target_uri(self):
        """Test _resolve_portal_path_via_gio resolves via target-uri."""
        mock_gio = mock.MagicMock()
        mock_gfile = mock.MagicMock()
        mock_info = mock.MagicMock()
        mock_info.get_attribute_string.side_effect = lambda attr: (
            "file:///home/user/Documents/file.txt"
            if attr == "standard::target-uri"
            else None
        )

        mock_gio.File.new_for_path.return_value = mock_gfile
        mock_gfile.query_info.return_value = mock_info

        mock_gi_repository = mock.MagicMock()
        mock_gi_repository.Gio = mock_gio
        with mock.patch.dict("sys.modules", {"gi.repository": mock_gi_repository}):
            result = flatpak._resolve_portal_path_via_gio(
                "/run/user/1000/doc/abc123/file.txt"
            )
            assert result == "/home/user/Documents/file.txt"

    def test_resolve_portal_path_via_gio_symlink_target(self):
        """Test _resolve_portal_path_via_gio resolves via symlink-target."""
        mock_gio = mock.MagicMock()
        mock_gfile = mock.MagicMock()
        mock_info = mock.MagicMock()

        def get_attr(attr):
            if attr == "standard::target-uri":
                return None
            elif attr == "standard::symlink-target":
                return "/home/user/Documents/file.txt"
            return None

        mock_info.get_attribute_string.side_effect = get_attr
        mock_gio.File.new_for_path.return_value = mock_gfile
        mock_gfile.query_info.return_value = mock_info

        mock_gi_repository = mock.MagicMock()
        mock_gi_repository.Gio = mock_gio
        with mock.patch.dict("sys.modules", {"gi.repository": mock_gi_repository}):
            result = flatpak._resolve_portal_path_via_gio(
                "/run/user/1000/doc/abc123/file.txt"
            )
            assert result == "/home/user/Documents/file.txt"

    def test_resolve_portal_path_via_gio_skips_run_symlink(self):
        """Test _resolve_portal_path_via_gio skips symlinks starting with /run/."""
        mock_gio = mock.MagicMock()
        mock_gfile = mock.MagicMock()
        mock_info = mock.MagicMock()

        def get_attr(attr):
            if attr == "standard::target-uri":
                return None
            elif attr == "standard::symlink-target":
                return "/run/user/1000/doc/xyz789/file.txt"
            return None

        mock_info.get_attribute_string.side_effect = get_attr
        mock_gio.File.new_for_path.return_value = mock_gfile
        mock_gfile.query_info.return_value = mock_info

        mock_gi_repository = mock.MagicMock()
        mock_gi_repository.Gio = mock_gio
        with mock.patch.dict("sys.modules", {"gi.repository": mock_gi_repository}):
            result = flatpak._resolve_portal_path_via_gio(
                "/run/user/1000/doc/abc123/file.txt"
            )
            assert result is None

    def test_resolve_portal_path_via_gio_exception(self):
        """Test _resolve_portal_path_via_gio handles exceptions gracefully."""
        with mock.patch.dict("sys.modules", {"gi.repository": None}):
            with mock.patch("builtins.__import__", side_effect=ImportError()):
                result = flatpak._resolve_portal_path_via_gio(
                    "/run/user/1000/doc/abc123/file.txt"
                )
                assert result is None


class TestResolvePortalPathViaDBus:
    """Tests for _resolve_portal_path_via_dbus() function."""

    def test_resolve_portal_path_via_dbus_success(self):
        """Test _resolve_portal_path_via_dbus resolves path via D-Bus."""
        mock_gio = mock.MagicMock()
        mock_glib = mock.MagicMock()
        mock_bus = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.unpack.return_value = (b"/home/user/Documents/file.txt\x00", {})

        mock_gio.bus_get_sync.return_value = mock_bus
        mock_bus.call_sync.return_value = mock_result

        mock_gi_repository = mock.MagicMock()
        mock_gi_repository.Gio = mock_gio
        mock_gi_repository.GLib = mock_glib
        with mock.patch.dict("sys.modules", {"gi.repository": mock_gi_repository}):
            result = flatpak._resolve_portal_path_via_dbus(
                "/run/user/1000/doc/abc123/file.txt"
            )
            assert result == "/home/user/Documents/file.txt"

    def test_resolve_portal_path_via_dbus_flatpak_doc(self):
        """Test _resolve_portal_path_via_dbus handles /run/flatpak/doc/ paths."""
        mock_gio = mock.MagicMock()
        mock_glib = mock.MagicMock()
        mock_bus = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.unpack.return_value = (b"/home/user/file.txt\x00", {})

        mock_gio.bus_get_sync.return_value = mock_bus
        mock_bus.call_sync.return_value = mock_result

        mock_gi_repository = mock.MagicMock()
        mock_gi_repository.Gio = mock_gio
        mock_gi_repository.GLib = mock_glib
        with mock.patch.dict("sys.modules", {"gi.repository": mock_gi_repository}):
            result = flatpak._resolve_portal_path_via_dbus(
                "/run/flatpak/doc/def456/file.txt"
            )
            assert result == "/home/user/file.txt"

    def test_resolve_portal_path_via_dbus_list_of_bytes(self):
        """Test _resolve_portal_path_via_dbus handles list of byte values."""
        mock_gio = mock.MagicMock()
        mock_glib = mock.MagicMock()
        mock_bus = mock.MagicMock()
        mock_result = mock.MagicMock()
        # Return as list of integers (byte values)
        path_bytes = [ord(c) for c in "/home/user/file.txt\x00"]
        mock_result.unpack.return_value = (path_bytes, {})

        mock_gio.bus_get_sync.return_value = mock_bus
        mock_bus.call_sync.return_value = mock_result

        mock_gi_repository = mock.MagicMock()
        mock_gi_repository.Gio = mock_gio
        mock_gi_repository.GLib = mock_glib
        with mock.patch.dict("sys.modules", {"gi.repository": mock_gi_repository}):
            result = flatpak._resolve_portal_path_via_dbus(
                "/run/user/1000/doc/abc123/file.txt"
            )
            assert result == "/home/user/file.txt"

    def test_resolve_portal_path_via_dbus_invalid_path(self):
        """Test _resolve_portal_path_via_dbus returns None for invalid paths."""
        result = flatpak._resolve_portal_path_via_dbus("/home/user/Documents/file.txt")
        assert result is None

        result = flatpak._resolve_portal_path_via_dbus("/run/user/1000/file.txt")
        assert result is None

    def test_resolve_portal_path_via_dbus_exception(self):
        """Test _resolve_portal_path_via_dbus handles exceptions gracefully."""
        with mock.patch.dict("sys.modules", {"gi.repository": None}):
            with mock.patch("builtins.__import__", side_effect=ImportError()):
                result = flatpak._resolve_portal_path_via_dbus(
                    "/run/user/1000/doc/abc123/file.txt"
                )
                assert result is None


class TestFormatFlatpakPortalPath:
    """Tests for format_flatpak_portal_path() function."""

    def test_format_flatpak_portal_path_home_subdir_downloads(self):
        """Test format_flatpak_portal_path formats Downloads path."""
        result = flatpak.format_flatpak_portal_path(
            "/run/user/1000/doc/abc123/Downloads/file.txt"
        )
        assert result == "~/Downloads/file.txt"

    def test_format_flatpak_portal_path_home_subdir_documents(self):
        """Test format_flatpak_portal_path formats Documents path."""
        result = flatpak.format_flatpak_portal_path(
            "/run/user/1000/doc/def456/Documents/report.pdf"
        )
        assert result == "~/Documents/report.pdf"

    def test_format_flatpak_portal_path_home_username(self):
        """Test format_flatpak_portal_path formats home/username paths."""
        result = flatpak.format_flatpak_portal_path(
            "/run/user/1000/doc/abc123/home/john/file.txt"
        )
        assert result == "~/file.txt"

    def test_format_flatpak_portal_path_media(self):
        """Test format_flatpak_portal_path formats /media paths."""
        result = flatpak.format_flatpak_portal_path(
            "/run/user/1000/doc/abc123/media/data/nextcloud/file.txt"
        )
        assert result == "/media/data/nextcloud/file.txt"

    def test_format_flatpak_portal_path_mnt(self):
        """Test format_flatpak_portal_path formats /mnt paths."""
        result = flatpak.format_flatpak_portal_path(
            "/run/flatpak/doc/def456/mnt/storage/file.txt"
        )
        assert result == "/mnt/storage/file.txt"

    def test_format_flatpak_portal_path_flatpak_doc(self):
        """Test format_flatpak_portal_path handles /run/flatpak/doc/ paths."""
        # Patch resolution methods to prevent actual resolution attempts
        with mock.patch.object(
            flatpak, "_resolve_portal_path_via_xattr", return_value=None
        ):
            with mock.patch.object(
                flatpak, "_resolve_portal_path_via_gio", return_value=None
            ):
                with mock.patch.object(
                    flatpak, "_resolve_portal_path_via_dbus", return_value=None
                ):
                    result = flatpak.format_flatpak_portal_path(
                        "/run/flatpak/doc/def789/Downloads/file.txt"
                    )
                    assert result == "~/Downloads/file.txt"

    def test_format_flatpak_portal_path_non_portal_path(self):
        """Test format_flatpak_portal_path returns original path for non-portal paths."""
        original = "/home/user/Documents/file.txt"
        result = flatpak.format_flatpak_portal_path(original)
        assert result == original

    def test_format_flatpak_portal_path_with_dbus_resolution(self):
        """Test format_flatpak_portal_path uses D-Bus resolution as fallback."""
        # Mock resolution methods - D-Bus returns resolved path, others return None
        with mock.patch.object(
            flatpak, "_resolve_portal_path_via_xattr", return_value=None
        ):
            with mock.patch.object(
                flatpak, "_resolve_portal_path_via_gio", return_value=None
            ):
                with mock.patch.object(
                    flatpak,
                    "_resolve_portal_path_via_dbus",
                    return_value="/home/user/CustomFolder/file.txt",
                ):
                    with mock.patch(
                        "src.core.flatpak.Path.home", return_value=Path("/home/user")
                    ):
                        result = flatpak.format_flatpak_portal_path(
                            "/run/user/1000/doc/abc123/CustomFolder/file.txt"
                        )
                        assert result == "~/CustomFolder/file.txt"

    def test_format_flatpak_portal_path_fallback_to_portal_indicator(self):
        """Test format_flatpak_portal_path shows [Portal] when resolution fails."""
        with mock.patch.object(
            flatpak, "_resolve_portal_path_via_xattr", return_value=None
        ):
            with mock.patch.object(
                flatpak, "_resolve_portal_path_via_gio", return_value=None
            ):
                with mock.patch.object(
                    flatpak, "_resolve_portal_path_via_dbus", return_value=None
                ):
                    result = flatpak.format_flatpak_portal_path(
                        "/run/user/1000/doc/abc123/UnknownFolder/file.txt"
                    )
                    assert result == "[Portal] UnknownFolder/file.txt"

    def test_format_flatpak_portal_path_all_home_subdirs(self):
        """Test format_flatpak_portal_path handles all known home subdirs."""
        home_subdirs = [
            "Downloads",
            "Documents",
            "Desktop",
            "Pictures",
            "Videos",
            "Music",
            ".config",
            ".local",
            ".cache",
        ]

        for subdir in home_subdirs:
            result = flatpak.format_flatpak_portal_path(
                f"/run/user/1000/doc/abc123/{subdir}/file.txt"
            )
            assert result == f"~/{subdir}/file.txt"

    def test_format_flatpak_portal_path_all_abs_indicators(self):
        """Test format_flatpak_portal_path handles all absolute path indicators."""
        abs_indicators = ["media", "mnt", "run", "tmp", "opt", "var", "usr", "srv"]

        for indicator in abs_indicators:
            result = flatpak.format_flatpak_portal_path(
                f"/run/user/1000/doc/abc123/{indicator}/somepath/file.txt"
            )
            assert result == f"/{indicator}/somepath/file.txt"

    def test_format_flatpak_portal_path_resolved_absolute_path(self):
        """Test format_flatpak_portal_path handles resolved absolute paths."""
        with mock.patch.object(
            flatpak, "_resolve_portal_path_via_xattr", return_value=None
        ):
            with mock.patch.object(
                flatpak, "_resolve_portal_path_via_gio", return_value=None
            ):
                with mock.patch.object(
                    flatpak,
                    "_resolve_portal_path_via_dbus",
                    return_value="/opt/app/file.txt",
                ):
                    result = flatpak.format_flatpak_portal_path(
                        "/run/user/1000/doc/abc123/CustomFolder/file.txt"
                    )
                    assert result == "/opt/app/file.txt"

    def test_format_flatpak_portal_path_complex_nested_path(self):
        """Test format_flatpak_portal_path handles complex nested paths."""
        result = flatpak.format_flatpak_portal_path(
            "/run/user/1000/doc/abc123/Documents/Work/Projects/2024/report.pdf"
        )
        assert result == "~/Documents/Work/Projects/2024/report.pdf"


class TestGetXdgUserDir:
    """Tests for get_xdg_user_dir() function."""

    def test_get_xdg_user_dir_download(self):
        """Test get_xdg_user_dir returns Download path."""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/home/user/Downloads\n"

        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            with mock.patch("subprocess.run", return_value=mock_result) as mock_run:
                result = flatpak.get_xdg_user_dir("DOWNLOAD")
                assert result == "/home/user/Downloads"
                mock_run.assert_called_once_with(
                    ["xdg-user-dir", "DOWNLOAD"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

    def test_get_xdg_user_dir_documents(self):
        """Test get_xdg_user_dir returns Documents path."""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/home/user/Dokumente\n"  # German locale

        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            with mock.patch("subprocess.run", return_value=mock_result):
                result = flatpak.get_xdg_user_dir("DOCUMENTS")
                assert result == "/home/user/Dokumente"

    def test_get_xdg_user_dir_invalid_type(self):
        """Test get_xdg_user_dir returns None for invalid type."""
        result = flatpak.get_xdg_user_dir("INVALID_TYPE")
        assert result is None

    def test_get_xdg_user_dir_command_not_found(self):
        """Test get_xdg_user_dir returns None when command not found."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            with mock.patch(
                "subprocess.run",
                side_effect=FileNotFoundError("xdg-user-dir not found"),
            ):
                result = flatpak.get_xdg_user_dir("DOWNLOAD")
                assert result is None

    def test_get_xdg_user_dir_timeout(self):
        """Test get_xdg_user_dir returns None on timeout."""
        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            with mock.patch(
                "subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)
            ):
                result = flatpak.get_xdg_user_dir("DOWNLOAD")
                assert result is None

    def test_get_xdg_user_dir_command_fails(self):
        """Test get_xdg_user_dir returns None when command fails."""
        mock_result = mock.Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            with mock.patch("subprocess.run", return_value=mock_result):
                result = flatpak.get_xdg_user_dir("DOWNLOAD")
                assert result is None

    def test_get_xdg_user_dir_empty_output(self):
        """Test get_xdg_user_dir returns None for empty output."""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            with mock.patch("subprocess.run", return_value=mock_result):
                result = flatpak.get_xdg_user_dir("DOWNLOAD")
                assert result is None

    def test_get_xdg_user_dir_in_flatpak(self):
        """Test get_xdg_user_dir uses flatpak-spawn in Flatpak."""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/home/user/Downloads\n"

        with mock.patch.object(flatpak, "is_flatpak", return_value=True):
            with mock.patch("subprocess.run", return_value=mock_result) as mock_run:
                result = flatpak.get_xdg_user_dir("DOWNLOAD")
                assert result == "/home/user/Downloads"
                mock_run.assert_called_once_with(
                    ["flatpak-spawn", "--host", "xdg-user-dir", "DOWNLOAD"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

    def test_get_xdg_user_dir_all_valid_types(self):
        """Test get_xdg_user_dir accepts all valid XDG types."""
        valid_types = [
            "DOWNLOAD",
            "DOCUMENTS",
            "DESKTOP",
            "MUSIC",
            "PICTURES",
            "VIDEOS",
            "TEMPLATES",
            "PUBLICSHARE",
        ]

        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/home/user/test\n"

        with mock.patch.object(flatpak, "is_flatpak", return_value=False):
            with mock.patch("subprocess.run", return_value=mock_result):
                for dir_type in valid_types:
                    result = flatpak.get_xdg_user_dir(dir_type)
                    assert result == "/home/user/test"
