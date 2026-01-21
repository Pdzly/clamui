# ClamUI ClamAV Detection Tests
"""Unit tests for the clamav_detection module functions."""

import subprocess
from unittest import mock

from src.core import clamav_detection


class TestCheckClamavInstalled:
    """Tests for check_clamav_installed() function."""

    def test_check_clamav_installed_found_and_working(self):
        """Test check_clamav_installed returns (True, version) when installed."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0,
                    stdout="ClamAV 1.2.3/27421/Mon Dec 30 09:00:00 2024\n",
                    stderr="",
                )
                installed, version = clamav_detection.check_clamav_installed()
                assert installed is True
                assert "ClamAV" in version

    def test_check_clamav_not_installed(self):
        """Test check_clamav_installed returns (False, message) when not installed."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value=None
        ):
            installed, message = clamav_detection.check_clamav_installed()
            assert installed is False
            assert "not installed" in message.lower()

    def test_check_clamav_timeout(self):
        """Test check_clamav_installed handles timeout gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired(
                    cmd="clamscan", timeout=10
                )
                installed, message = clamav_detection.check_clamav_installed()
                assert installed is False
                assert "timed out" in message.lower()

    def test_check_clamav_permission_denied(self):
        """Test check_clamav_installed handles permission errors gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = PermissionError("Permission denied")
                installed, message = clamav_detection.check_clamav_installed()
                assert installed is False
                assert "permission denied" in message.lower()

    def test_check_clamav_file_not_found(self):
        """Test check_clamav_installed handles FileNotFoundError gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("File not found")
                installed, message = clamav_detection.check_clamav_installed()
                assert installed is False
                assert "not found" in message.lower()

    def test_check_clamav_returns_error(self):
        """Test check_clamav_installed when command returns non-zero exit code."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=1,
                    stdout="",
                    stderr="Some error occurred",
                )
                installed, message = clamav_detection.check_clamav_installed()
                assert installed is False
                assert "error" in message.lower()

    def test_check_clamav_generic_exception(self):
        """Test check_clamav_installed handles generic exceptions gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = Exception("Unexpected error")
                installed, message = clamav_detection.check_clamav_installed()
                assert installed is False
                assert "error" in message.lower()

    def test_check_clamav_uses_wrap_host_command(self):
        """Test check_clamav_installed uses wrap_host_command for Flatpak support."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamscan"
        ):
            with mock.patch.object(
                clamav_detection,
                "wrap_host_command",
                return_value=["clamscan", "--version"],
            ) as mock_wrap:
                with mock.patch("subprocess.run") as mock_run:
                    mock_run.return_value = mock.Mock(
                        returncode=0,
                        stdout="ClamAV 1.2.3\n",
                        stderr="",
                    )
                    clamav_detection.check_clamav_installed()
                    mock_wrap.assert_called_once_with(["clamscan", "--version"])


class TestCheckFreshclamInstalled:
    """Tests for check_freshclam_installed() function."""

    def test_check_freshclam_installed_found_and_working(self):
        """Test check_freshclam_installed returns (True, version) when installed."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/freshclam"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0,
                    stdout="ClamAV 1.2.3/27421/Mon Dec 30 09:00:00 2024\n",
                    stderr="",
                )
                installed, version = clamav_detection.check_freshclam_installed()
                assert installed is True
                assert "ClamAV" in version

    def test_check_freshclam_not_installed(self):
        """Test check_freshclam_installed returns (False, message) when not installed."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value=None
        ):
            installed, message = clamav_detection.check_freshclam_installed()
            assert installed is False
            assert "not installed" in message.lower()

    def test_check_freshclam_timeout(self):
        """Test check_freshclam_installed handles timeout gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/freshclam"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired(
                    cmd="freshclam", timeout=10
                )
                installed, message = clamav_detection.check_freshclam_installed()
                assert installed is False
                assert "timed out" in message.lower()

    def test_check_freshclam_permission_denied(self):
        """Test check_freshclam_installed handles permission errors gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/freshclam"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = PermissionError("Permission denied")
                installed, message = clamav_detection.check_freshclam_installed()
                assert installed is False
                assert "permission denied" in message.lower()

    def test_check_freshclam_file_not_found(self):
        """Test check_freshclam_installed handles FileNotFoundError gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/freshclam"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("File not found")
                installed, message = clamav_detection.check_freshclam_installed()
                assert installed is False
                assert "not found" in message.lower()

    def test_check_freshclam_returns_error(self):
        """Test check_freshclam_installed when command returns non-zero exit code."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/freshclam"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=1,
                    stdout="",
                    stderr="Some error occurred",
                )
                installed, message = clamav_detection.check_freshclam_installed()
                assert installed is False
                assert "error" in message.lower()

    def test_check_freshclam_generic_exception(self):
        """Test check_freshclam_installed handles generic exceptions gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/freshclam"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = Exception("Unexpected error")
                installed, message = clamav_detection.check_freshclam_installed()
                assert installed is False
                assert "error" in message.lower()

    def test_check_freshclam_uses_wrap_host_command(self):
        """Test check_freshclam_installed uses wrap_host_command for Flatpak support."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/freshclam"
        ):
            with mock.patch.object(
                clamav_detection,
                "wrap_host_command",
                return_value=["freshclam", "--version"],
            ) as mock_wrap:
                with mock.patch("subprocess.run") as mock_run:
                    mock_run.return_value = mock.Mock(
                        returncode=0,
                        stdout="ClamAV 1.2.3\n",
                        stderr="",
                    )
                    clamav_detection.check_freshclam_installed()
                    mock_wrap.assert_called_once_with(["freshclam", "--version"])


class TestCheckClamdscanInstalled:
    """Tests for check_clamdscan_installed() function."""

    def test_check_clamdscan_installed_found_and_working(self):
        """Test check_clamdscan_installed returns (True, version) when installed."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamdscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0,
                    stdout="ClamAV 1.2.3/27421/Mon Dec 30 09:00:00 2024\n",
                    stderr="",
                )
                installed, version = clamav_detection.check_clamdscan_installed()
                assert installed is True
                assert "ClamAV" in version

    def test_check_clamdscan_not_installed(self):
        """Test check_clamdscan_installed returns (False, message) when not installed."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value=None
        ):
            installed, message = clamav_detection.check_clamdscan_installed()
            assert installed is False
            assert "not installed" in message.lower()

    def test_check_clamdscan_timeout(self):
        """Test check_clamdscan_installed handles timeout gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamdscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired(
                    cmd="clamdscan", timeout=10
                )
                installed, message = clamav_detection.check_clamdscan_installed()
                assert installed is False
                assert "timed out" in message.lower()

    def test_check_clamdscan_permission_denied(self):
        """Test check_clamdscan_installed handles permission errors gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamdscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = PermissionError("Permission denied")
                installed, message = clamav_detection.check_clamdscan_installed()
                assert installed is False
                assert "permission denied" in message.lower()

    def test_check_clamdscan_file_not_found(self):
        """Test check_clamdscan_installed handles FileNotFoundError gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamdscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("File not found")
                installed, message = clamav_detection.check_clamdscan_installed()
                assert installed is False
                assert "not found" in message.lower()

    def test_check_clamdscan_returns_error(self):
        """Test check_clamdscan_installed when command returns non-zero exit code."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamdscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=1,
                    stdout="",
                    stderr="Some error occurred",
                )
                installed, message = clamav_detection.check_clamdscan_installed()
                assert installed is False
                assert "error" in message.lower()

    def test_check_clamdscan_generic_exception(self):
        """Test check_clamdscan_installed handles generic exceptions gracefully."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamdscan"
        ):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = Exception("Unexpected error")
                installed, message = clamav_detection.check_clamdscan_installed()
                assert installed is False
                assert "error" in message.lower()

    def test_check_clamdscan_uses_wrap_host_command(self):
        """Test check_clamdscan_installed uses wrap_host_command for Flatpak support."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamdscan"
        ):
            with mock.patch.object(
                clamav_detection,
                "wrap_host_command",
                return_value=["clamdscan", "--version"],
            ) as mock_wrap:
                with mock.patch("subprocess.run") as mock_run:
                    mock_run.return_value = mock.Mock(
                        returncode=0,
                        stdout="ClamAV 1.2.3\n",
                        stderr="",
                    )
                    clamav_detection.check_clamdscan_installed()
                    mock_wrap.assert_called_once_with(["clamdscan", "--version"])


class TestGetClamdSocketPath:
    """Tests for get_clamd_socket_path() function."""

    def test_get_clamd_socket_path_ubuntu_default(self):
        """Test get_clamd_socket_path returns Ubuntu/Debian default path."""
        with mock.patch("os.path.exists") as mock_exists:

            def exists_check(path):
                return path == "/var/run/clamav/clamd.ctl"

            mock_exists.side_effect = exists_check
            socket_path = clamav_detection.get_clamd_socket_path()
            assert socket_path == "/var/run/clamav/clamd.ctl"

    def test_get_clamd_socket_path_alternative_location(self):
        """Test get_clamd_socket_path returns alternative location."""
        with mock.patch("os.path.exists") as mock_exists:

            def exists_check(path):
                return path == "/run/clamav/clamd.ctl"

            mock_exists.side_effect = exists_check
            socket_path = clamav_detection.get_clamd_socket_path()
            assert socket_path == "/run/clamav/clamd.ctl"

    def test_get_clamd_socket_path_fedora_location(self):
        """Test get_clamd_socket_path returns Fedora location."""
        with mock.patch("os.path.exists") as mock_exists:

            def exists_check(path):
                return path == "/var/run/clamd.scan/clamd.sock"

            mock_exists.side_effect = exists_check
            socket_path = clamav_detection.get_clamd_socket_path()
            assert socket_path == "/var/run/clamd.scan/clamd.sock"

    def test_get_clamd_socket_path_not_found(self):
        """Test get_clamd_socket_path returns None when socket not found."""
        with mock.patch("os.path.exists", return_value=False):
            socket_path = clamav_detection.get_clamd_socket_path()
            assert socket_path is None

    def test_get_clamd_socket_path_priority_order(self):
        """Test get_clamd_socket_path returns first found socket in priority order."""
        with mock.patch("os.path.exists") as mock_exists:
            # All sockets exist, should return first one
            mock_exists.return_value = True
            socket_path = clamav_detection.get_clamd_socket_path()
            # Should return the first one in the list
            assert socket_path == "/var/run/clamav/clamd.ctl"


class TestCheckClamdConnection:
    """Tests for check_clamd_connection() function."""

    def test_check_clamd_connection_clamdscan_not_installed(self):
        """Test check_clamd_connection fails when clamdscan not installed."""
        with mock.patch.object(
            clamav_detection,
            "check_clamdscan_installed",
            return_value=(False, "Not installed"),
        ):
            is_connected, message = clamav_detection.check_clamd_connection()
            assert is_connected is False
            assert "not installed" in message.lower()

    def test_check_clamd_connection_socket_not_found_not_flatpak(self):
        """Test check_clamd_connection fails when socket not found (not in Flatpak)."""
        with mock.patch.object(
            clamav_detection,
            "check_clamdscan_installed",
            return_value=(True, "ClamAV 1.2.3"),
        ):
            with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
                with mock.patch.object(
                    clamav_detection, "get_clamd_socket_path", return_value=None
                ):
                    is_connected, message = clamav_detection.check_clamd_connection()
                    assert is_connected is False
                    assert "socket" in message.lower()

    def test_check_clamd_connection_socket_provided(self):
        """Test check_clamd_connection uses provided socket path."""
        with mock.patch.object(
            clamav_detection,
            "check_clamdscan_installed",
            return_value=(True, "ClamAV 1.2.3"),
        ):
            with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
                with mock.patch.object(
                    clamav_detection,
                    "wrap_host_command",
                    return_value=["clamdscan", "--ping", "3"],
                ):
                    with mock.patch("subprocess.run") as mock_run:
                        mock_run.return_value = mock.Mock(
                            returncode=0,
                            stdout="PONG\n",
                            stderr="",
                        )
                        is_connected, message = clamav_detection.check_clamd_connection(
                            socket_path="/custom/socket.sock"
                        )
                        assert is_connected is True
                        assert message == "PONG"

    def test_check_clamd_connection_successful_pong(self):
        """Test check_clamd_connection returns (True, 'PONG') when daemon responds."""
        with mock.patch.object(
            clamav_detection,
            "check_clamdscan_installed",
            return_value=(True, "ClamAV 1.2.3"),
        ):
            with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
                with mock.patch.object(
                    clamav_detection,
                    "get_clamd_socket_path",
                    return_value="/var/run/clamav/clamd.ctl",
                ):
                    with mock.patch.object(
                        clamav_detection,
                        "wrap_host_command",
                        return_value=["clamdscan", "--ping", "3"],
                    ):
                        with mock.patch("subprocess.run") as mock_run:
                            mock_run.return_value = mock.Mock(
                                returncode=0,
                                stdout="PONG\n",
                                stderr="",
                            )
                            is_connected, message = (
                                clamav_detection.check_clamd_connection()
                            )
                            assert is_connected is True
                            assert message == "PONG"

    def test_check_clamd_connection_daemon_not_responding(self):
        """Test check_clamd_connection when daemon is not responding."""
        with mock.patch.object(
            clamav_detection,
            "check_clamdscan_installed",
            return_value=(True, "ClamAV 1.2.3"),
        ):
            with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
                with mock.patch.object(
                    clamav_detection,
                    "get_clamd_socket_path",
                    return_value="/var/run/clamav/clamd.ctl",
                ):
                    with mock.patch.object(
                        clamav_detection,
                        "wrap_host_command",
                        return_value=["clamdscan", "--ping", "3"],
                    ):
                        with mock.patch("subprocess.run") as mock_run:
                            mock_run.return_value = mock.Mock(
                                returncode=1,
                                stdout="",
                                stderr="Can't connect to clamd",
                            )
                            is_connected, message = (
                                clamav_detection.check_clamd_connection()
                            )
                            assert is_connected is False
                            assert "not responding" in message.lower()

    def test_check_clamd_connection_timeout(self):
        """Test check_clamd_connection handles timeout."""
        with mock.patch.object(
            clamav_detection,
            "check_clamdscan_installed",
            return_value=(True, "ClamAV 1.2.3"),
        ):
            with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
                with mock.patch.object(
                    clamav_detection,
                    "get_clamd_socket_path",
                    return_value="/var/run/clamav/clamd.ctl",
                ):
                    with mock.patch.object(
                        clamav_detection,
                        "wrap_host_command",
                        return_value=["clamdscan", "--ping", "3"],
                    ):
                        with mock.patch("subprocess.run") as mock_run:
                            mock_run.side_effect = subprocess.TimeoutExpired(
                                cmd="clamdscan", timeout=10
                            )
                            is_connected, message = (
                                clamav_detection.check_clamd_connection()
                            )
                            assert is_connected is False
                            assert "timed out" in message.lower()

    def test_check_clamd_connection_file_not_found(self):
        """Test check_clamd_connection handles FileNotFoundError."""
        with mock.patch.object(
            clamav_detection,
            "check_clamdscan_installed",
            return_value=(True, "ClamAV 1.2.3"),
        ):
            with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
                with mock.patch.object(
                    clamav_detection,
                    "get_clamd_socket_path",
                    return_value="/var/run/clamav/clamd.ctl",
                ):
                    with mock.patch.object(
                        clamav_detection,
                        "wrap_host_command",
                        return_value=["clamdscan", "--ping", "3"],
                    ):
                        with mock.patch("subprocess.run") as mock_run:
                            mock_run.side_effect = FileNotFoundError("File not found")
                            is_connected, message = (
                                clamav_detection.check_clamd_connection()
                            )
                            assert is_connected is False
                            assert "not found" in message.lower()

    def test_check_clamd_connection_generic_exception(self):
        """Test check_clamd_connection handles generic exceptions."""
        with mock.patch.object(
            clamav_detection,
            "check_clamdscan_installed",
            return_value=(True, "ClamAV 1.2.3"),
        ):
            with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
                with mock.patch.object(
                    clamav_detection,
                    "get_clamd_socket_path",
                    return_value="/var/run/clamav/clamd.ctl",
                ):
                    with mock.patch.object(
                        clamav_detection,
                        "wrap_host_command",
                        return_value=["clamdscan", "--ping", "3"],
                    ):
                        with mock.patch("subprocess.run") as mock_run:
                            mock_run.side_effect = Exception("Unexpected error")
                            is_connected, message = (
                                clamav_detection.check_clamd_connection()
                            )
                            assert is_connected is False
                            assert "error" in message.lower()

    def test_check_clamd_connection_in_flatpak(self):
        """Test check_clamd_connection skips socket check in Flatpak."""
        with mock.patch.object(
            clamav_detection,
            "check_clamdscan_installed",
            return_value=(True, "ClamAV 1.2.3"),
        ):
            with mock.patch.object(clamav_detection, "is_flatpak", return_value=True):
                with mock.patch.object(
                    clamav_detection,
                    "wrap_host_command",
                    return_value=["clamdscan", "--ping", "3"],
                ):
                    with mock.patch("subprocess.run") as mock_run:
                        mock_run.return_value = mock.Mock(
                            returncode=0,
                            stdout="PONG\n",
                            stderr="",
                        )
                        is_connected, message = (
                            clamav_detection.check_clamd_connection()
                        )
                        assert is_connected is True
                        assert message == "PONG"

    def test_check_clamd_connection_uses_wrap_host_command(self):
        """Test check_clamd_connection uses wrap_host_command for Flatpak support."""
        with mock.patch.object(
            clamav_detection,
            "check_clamdscan_installed",
            return_value=(True, "ClamAV 1.2.3"),
        ):
            with mock.patch.object(clamav_detection, "is_flatpak", return_value=True):
                with mock.patch.object(
                    clamav_detection,
                    "wrap_host_command",
                    return_value=["clamdscan", "--ping", "3"],
                ) as mock_wrap:
                    with mock.patch("subprocess.run") as mock_run:
                        mock_run.return_value = mock.Mock(
                            returncode=0,
                            stdout="PONG\n",
                            stderr="",
                        )
                        clamav_detection.check_clamd_connection()
                        mock_wrap.assert_called_once_with(["clamdscan", "--ping", "3"])


class TestGetClamavPath:
    """Tests for get_clamav_path() function."""

    def test_get_clamav_path_found(self):
        """Test get_clamav_path returns path when clamscan is found."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamscan"
        ) as mock_which:
            path = clamav_detection.get_clamav_path()
            assert path == "/usr/bin/clamscan"
            mock_which.assert_called_once_with("clamscan")

    def test_get_clamav_path_not_found(self):
        """Test get_clamav_path returns None when clamscan is not found."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value=None
        ):
            path = clamav_detection.get_clamav_path()
            assert path is None

    def test_get_clamav_path_uses_which_host_command(self):
        """Test get_clamav_path uses which_host_command for Flatpak support."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/clamscan"
        ) as mock_which:
            clamav_detection.get_clamav_path()
            mock_which.assert_called_once_with("clamscan")


class TestGetFreshclamPath:
    """Tests for get_freshclam_path() function."""

    def test_get_freshclam_path_found(self):
        """Test get_freshclam_path returns path when freshclam is found."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/freshclam"
        ) as mock_which:
            path = clamav_detection.get_freshclam_path()
            assert path == "/usr/bin/freshclam"
            mock_which.assert_called_once_with("freshclam")

    def test_get_freshclam_path_not_found(self):
        """Test get_freshclam_path returns None when freshclam is not found."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value=None
        ):
            path = clamav_detection.get_freshclam_path()
            assert path is None

    def test_get_freshclam_path_uses_which_host_command(self):
        """Test get_freshclam_path uses which_host_command for Flatpak support."""
        with mock.patch.object(
            clamav_detection, "which_host_command", return_value="/usr/bin/freshclam"
        ) as mock_which:
            clamav_detection.get_freshclam_path()
            mock_which.assert_called_once_with("freshclam")


class TestCheckDatabaseAvailable:
    """Tests for check_database_available() function."""

    def test_check_database_available_with_cvd_file(self, tmp_path):
        """Test check_database_available returns True when .cvd file exists."""
        # Create a mock database file
        db_file = tmp_path / "main.cvd"
        db_file.write_text("mock database content")

        with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
            with mock.patch("pathlib.Path", return_value=tmp_path) as mock_path:
                # Make Path("/var/lib/clamav") return tmp_path
                mock_path.return_value = tmp_path
                is_available, error = clamav_detection.check_database_available()
                assert is_available is True
                assert error is None

    def test_check_database_available_with_cld_file(self, tmp_path):
        """Test check_database_available returns True when .cld file exists."""
        db_file = tmp_path / "daily.cld"
        db_file.write_text("mock database content")

        with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
            with mock.patch("pathlib.Path", return_value=tmp_path):
                is_available, error = clamav_detection.check_database_available()
                assert is_available is True
                assert error is None

    def test_check_database_available_with_cud_file(self, tmp_path):
        """Test check_database_available returns True when .cud file exists."""
        db_file = tmp_path / "bytecode.cud"
        db_file.write_text("mock database content")

        with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
            with mock.patch("pathlib.Path", return_value=tmp_path):
                is_available, error = clamav_detection.check_database_available()
                assert is_available is True
                assert error is None

    def test_check_database_available_empty_directory(self, tmp_path):
        """Test check_database_available returns False when directory is empty."""
        with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
            with mock.patch("pathlib.Path", return_value=tmp_path):
                is_available, error = clamav_detection.check_database_available()
                assert is_available is False
                assert "No virus database files found" in error

    def test_check_database_available_no_database_files(self, tmp_path):
        """Test check_database_available returns False when no .cvd/.cld/.cud files exist."""
        # Create some non-database files
        (tmp_path / "readme.txt").write_text("readme")
        (tmp_path / "config.conf").write_text("config")

        with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
            with mock.patch("pathlib.Path", return_value=tmp_path):
                is_available, error = clamav_detection.check_database_available()
                assert is_available is False
                assert "No virus database files found" in error

    def test_check_database_available_directory_not_exists(self, tmp_path):
        """Test check_database_available returns False when directory doesn't exist."""
        non_existent = tmp_path / "non_existent"

        with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
            with mock.patch("pathlib.Path", return_value=non_existent):
                is_available, error = clamav_detection.check_database_available()
                assert is_available is False
                assert "does not exist" in error

    def test_check_database_available_permission_error(self, tmp_path):
        """Test check_database_available handles permission errors."""
        # Create a mock Path object that raises PermissionError on iterdir()
        mock_path = mock.MagicMock()
        mock_path.exists.return_value = True
        mock_path.iterdir.side_effect = PermissionError("Access denied")

        with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
            with mock.patch("pathlib.Path", return_value=mock_path):
                is_available, error = clamav_detection.check_database_available()
                assert is_available is False
                assert "Permission denied" in error

    def test_check_database_available_oserror(self, tmp_path):
        """Test check_database_available handles OS errors."""
        # Create a mock Path object that raises OSError on iterdir()
        mock_path = mock.MagicMock()
        mock_path.exists.return_value = True
        mock_path.iterdir.side_effect = OSError("Disk error")

        with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
            with mock.patch("pathlib.Path", return_value=mock_path):
                is_available, error = clamav_detection.check_database_available()
                assert is_available is False
                assert "Error accessing database" in error

    def test_check_database_available_flatpak_with_database(self, tmp_path):
        """Test check_database_available in Flatpak environment with database."""
        db_file = tmp_path / "main.cvd"
        db_file.write_text("mock database content")

        with mock.patch.object(clamav_detection, "is_flatpak", return_value=True):
            with mock.patch(
                "src.core.flatpak.get_clamav_database_dir",
                return_value=tmp_path,
            ):
                is_available, error = clamav_detection.check_database_available()
                assert is_available is True
                assert error is None

    def test_check_database_available_flatpak_no_database_dir(self):
        """Test check_database_available in Flatpak when database dir is None."""
        with mock.patch.object(clamav_detection, "is_flatpak", return_value=True):
            with mock.patch(
                "src.core.flatpak.get_clamav_database_dir", return_value=None
            ):
                is_available, error = clamav_detection.check_database_available()
                assert is_available is False
                assert "Could not determine Flatpak database directory" in error

    def test_check_database_available_case_insensitive_extension(self, tmp_path):
        """Test check_database_available handles uppercase extensions."""
        db_file = tmp_path / "main.CVD"
        db_file.write_text("mock database content")

        with mock.patch.object(clamav_detection, "is_flatpak", return_value=False):
            with mock.patch("pathlib.Path", return_value=tmp_path):
                is_available, error = clamav_detection.check_database_available()
                assert is_available is True
                assert error is None
