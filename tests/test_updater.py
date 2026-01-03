# ClamUI Updater Tests
"""Unit tests for the updater module, including Flatpak integration."""

import sys
from unittest import mock

import pytest


def _clear_src_modules():
    """Clear all cached src.* modules to ensure clean imports."""
    modules_to_remove = [mod for mod in list(sys.modules.keys()) if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


@pytest.fixture(autouse=True)
def ensure_fresh_updater_import():
    """Ensure updater module is freshly imported for each test.

    This fixture clears cached src modules and exposes fresh class references
    as globals so tests can use FreshclamUpdater, UpdateResult, UpdateStatus.
    """
    global FreshclamUpdater, UpdateResult, UpdateStatus

    # Clear any cached src modules before test
    _clear_src_modules()

    # Import fresh
    from src.core.updater import FreshclamUpdater as _FU
    from src.core.updater import UpdateResult as _UR
    from src.core.updater import UpdateStatus as _US

    FreshclamUpdater = _FU
    UpdateResult = _UR
    UpdateStatus = _US

    yield

    # Clear after test
    _clear_src_modules()


# Declare globals for type checkers
FreshclamUpdater = None
UpdateResult = None
UpdateStatus = None


class TestUpdaterBuildCommand:
    """Tests for the FreshclamUpdater._build_command method."""

    def test_build_command_with_pkexec(self):
        """Test _build_command uses pkexec for privilege elevation."""
        updater = FreshclamUpdater()

        with mock.patch("src.core.updater.get_freshclam_path", return_value="/usr/bin/freshclam"):
            with mock.patch("src.core.updater.get_pkexec_path", return_value="/usr/bin/pkexec"):
                with mock.patch("src.core.updater.wrap_host_command", side_effect=lambda x: x):
                    cmd = updater._build_command()

        # Should be pkexec freshclam --verbose
        assert cmd[0] == "/usr/bin/pkexec"
        assert cmd[1] == "/usr/bin/freshclam"
        assert "--verbose" in cmd

    def test_build_command_without_pkexec(self):
        """Test _build_command falls back when pkexec not available."""
        updater = FreshclamUpdater()

        with mock.patch("src.core.updater.get_freshclam_path", return_value="/usr/bin/freshclam"):
            with mock.patch("src.core.updater.get_pkexec_path", return_value=None):
                with mock.patch("src.core.updater.wrap_host_command", side_effect=lambda x: x):
                    cmd = updater._build_command()

        # Should be just freshclam --verbose without pkexec
        assert cmd[0] == "/usr/bin/freshclam"
        assert "--verbose" in cmd
        assert "/usr/bin/pkexec" not in cmd

    def test_build_command_fallback_to_freshclam(self):
        """Test _build_command falls back to 'freshclam' when path not found."""
        updater = FreshclamUpdater()

        with mock.patch("src.core.updater.get_freshclam_path", return_value=None):
            with mock.patch("src.core.updater.get_pkexec_path", return_value=None):
                with mock.patch("src.core.updater.wrap_host_command", side_effect=lambda x: x):
                    cmd = updater._build_command()

        # Should fall back to 'freshclam'
        assert cmd[0] == "freshclam"
        assert "--verbose" in cmd

    def test_build_command_wraps_with_flatpak_spawn(self):
        """Test _build_command wraps command with flatpak-spawn when in Flatpak."""
        updater = FreshclamUpdater()

        # Mock wrap_host_command to add flatpak-spawn prefix (simulating Flatpak environment)
        def mock_wrap(cmd):
            return ["flatpak-spawn", "--host"] + cmd

        with mock.patch("src.core.updater.get_freshclam_path", return_value="/usr/bin/freshclam"):
            with mock.patch("src.core.updater.get_pkexec_path", return_value="/usr/bin/pkexec"):
                with mock.patch("src.core.updater.wrap_host_command", side_effect=mock_wrap):
                    cmd = updater._build_command()

        # Should be prefixed with flatpak-spawn --host
        assert cmd[0] == "flatpak-spawn"
        assert cmd[1] == "--host"
        assert cmd[2] == "/usr/bin/pkexec"
        assert cmd[3] == "/usr/bin/freshclam"
        assert "--verbose" in cmd

    def test_build_command_no_wrap_outside_flatpak(self):
        """Test _build_command does NOT wrap when not in Flatpak."""
        updater = FreshclamUpdater()

        # Mock wrap_host_command to return command unchanged (not in Flatpak)
        with mock.patch("src.core.updater.get_freshclam_path", return_value="/usr/bin/freshclam"):
            with mock.patch("src.core.updater.get_pkexec_path", return_value="/usr/bin/pkexec"):
                with mock.patch("src.core.updater.wrap_host_command", side_effect=lambda x: x):
                    cmd = updater._build_command()

        # Should NOT be prefixed with flatpak-spawn
        assert cmd[0] == "/usr/bin/pkexec"
        assert "flatpak-spawn" not in cmd


class TestUpdaterFlatpakIntegration:
    """Tests for Flatpak integration in FreshclamUpdater."""

    def test_updater_uses_wrap_host_command(self):
        """Test that FreshclamUpdater._build_command calls wrap_host_command."""
        updater = FreshclamUpdater()

        with mock.patch("src.core.updater.get_freshclam_path", return_value="/usr/bin/freshclam"):
            with mock.patch("src.core.updater.get_pkexec_path", return_value="/usr/bin/pkexec"):
                with mock.patch("src.core.updater.wrap_host_command") as mock_wrap:
                    mock_wrap.return_value = ["/usr/bin/pkexec", "/usr/bin/freshclam", "--verbose"]
                    updater._build_command()

        # Verify wrap_host_command was called
        mock_wrap.assert_called_once()
        # Verify it was called with the expected base command
        call_args = mock_wrap.call_args[0][0]
        assert call_args[0] == "/usr/bin/pkexec"
        assert call_args[1] == "/usr/bin/freshclam"

    def test_updater_flatpak_spawn_with_pkexec_command(self):
        """Test flatpak-spawn wraps the entire pkexec command in Flatpak."""
        updater = FreshclamUpdater()

        # Simulate Flatpak environment
        def mock_wrap(cmd):
            return ["flatpak-spawn", "--host"] + cmd

        with mock.patch("src.core.updater.get_freshclam_path", return_value="/usr/bin/freshclam"):
            with mock.patch("src.core.updater.get_pkexec_path", return_value="/usr/bin/pkexec"):
                with mock.patch("src.core.updater.wrap_host_command", side_effect=mock_wrap):
                    cmd = updater._build_command()

        # The full command should be: flatpak-spawn --host pkexec freshclam --verbose
        assert cmd == [
            "flatpak-spawn",
            "--host",
            "/usr/bin/pkexec",
            "/usr/bin/freshclam",
            "--verbose",
        ]


class TestUpdateResult:
    """Tests for the UpdateResult dataclass."""

    def test_update_result_success(self):
        """Test UpdateResult.is_success property with SUCCESS status."""
        result = UpdateResult(
            status=UpdateStatus.SUCCESS,
            stdout="Database updated",
            stderr="",
            exit_code=0,
            databases_updated=3,
            error_message=None,
        )
        assert result.is_success is True
        assert result.has_error is False

    def test_update_result_up_to_date(self):
        """Test UpdateResult.is_success property with UP_TO_DATE status."""
        result = UpdateResult(
            status=UpdateStatus.UP_TO_DATE,
            stdout="Database is up to date",
            stderr="",
            exit_code=0,
            databases_updated=0,
            error_message=None,
        )
        assert result.is_success is True
        assert result.has_error is False

    def test_update_result_error(self):
        """Test UpdateResult with error status."""
        result = UpdateResult(
            status=UpdateStatus.ERROR,
            stdout="",
            stderr="Connection failed",
            exit_code=1,
            databases_updated=0,
            error_message="Connection failed",
        )
        assert result.is_success is False
        assert result.has_error is True

    def test_update_result_cancelled(self):
        """Test UpdateResult with cancelled status."""
        result = UpdateResult(
            status=UpdateStatus.CANCELLED,
            stdout="",
            stderr="",
            exit_code=-1,
            databases_updated=0,
            error_message="Update cancelled by user",
        )
        assert result.is_success is False
        assert result.has_error is False


class TestUpdateStatus:
    """Tests for the UpdateStatus enum."""

    def test_update_status_values(self):
        """Test UpdateStatus enum has expected values."""
        assert UpdateStatus.SUCCESS.value == "success"
        assert UpdateStatus.UP_TO_DATE.value == "up_to_date"
        assert UpdateStatus.ERROR.value == "error"
        assert UpdateStatus.CANCELLED.value == "cancelled"


class TestUpdaterParseResults:
    """Tests for the FreshclamUpdater._parse_results method."""

    def test_parse_results_success(self):
        """Test _parse_results with successful update output."""
        updater = FreshclamUpdater()

        stdout = """
ClamAV update process started at Mon Dec 30 12:00:00 2025
daily.cvd updated (version: 27000, sigs: 1000000, f-level: 90, builder: test)
main.cvd updated (version: 62, sigs: 6000000, f-level: 90, builder: test)
bytecode.cvd updated (version: 333, sigs: 90, f-level: 63, builder: test)
"""
        result = updater._parse_results(stdout, "", 0)

        assert result.status == UpdateStatus.SUCCESS
        assert result.databases_updated == 3
        assert result.is_success is True

    def test_parse_results_up_to_date(self):
        """Test _parse_results with up-to-date output."""
        updater = FreshclamUpdater()

        stdout = """
ClamAV update process started at Mon Dec 30 12:00:00 2025
daily.cvd database is up-to-date (version: 27000, sigs: 1000000, f-level: 90, builder: test)
main.cvd database is up-to-date (version: 62, sigs: 6000000, f-level: 90, builder: test)
"""
        result = updater._parse_results(stdout, "", 0)

        assert result.status == UpdateStatus.UP_TO_DATE
        assert result.databases_updated == 0
        assert result.is_success is True

    def test_parse_results_error(self):
        """Test _parse_results with error exit code."""
        updater = FreshclamUpdater()

        result = updater._parse_results("", "Can't connect to server", 1)

        assert result.status == UpdateStatus.ERROR
        assert result.error_message is not None
        assert result.has_error is True

    def test_parse_results_partial_update(self):
        """Test _parse_results with partial update (some databases updated)."""
        updater = FreshclamUpdater()

        stdout = """
ClamAV update process started at Mon Dec 30 12:00:00 2025
daily.cvd updated (version: 27000, sigs: 1000000, f-level: 90, builder: test)
main.cvd database is up-to-date (version: 62, sigs: 6000000, f-level: 90, builder: test)
"""
        result = updater._parse_results(stdout, "", 0)

        assert result.status == UpdateStatus.SUCCESS
        assert result.databases_updated == 1


class TestUpdaterErrorExtraction:
    """Tests for the FreshclamUpdater._extract_error_message method."""

    def test_extract_pkexec_dismissed_error(self):
        """Test error extraction for pkexec authentication dismissed."""
        updater = FreshclamUpdater()

        error_msg = updater._extract_error_message("", "", exit_code=126)

        assert "cancelled" in error_msg.lower() or "authentication" in error_msg.lower()

    def test_extract_pkexec_not_authorized_error(self):
        """Test error extraction for pkexec not authorized."""
        updater = FreshclamUpdater()

        error_msg = updater._extract_error_message("", "pkexec error", exit_code=127)

        assert "authorization" in error_msg.lower() or "authorized" in error_msg.lower()

    def test_extract_permission_denied_error(self):
        """Test error extraction for permission denied."""
        updater = FreshclamUpdater()

        error_msg = updater._extract_error_message("", "Permission denied", exit_code=1)

        assert "permission" in error_msg.lower()

    def test_extract_connection_error(self):
        """Test error extraction for connection errors."""
        updater = FreshclamUpdater()

        error_msg = updater._extract_error_message("Can't connect to server", "", exit_code=1)

        assert "connection" in error_msg.lower()

    def test_extract_lock_error(self):
        """Test error extraction for database locked error."""
        updater = FreshclamUpdater()

        error_msg = updater._extract_error_message(
            "Database is locked by another process", "", exit_code=1
        )

        assert "locked" in error_msg.lower()

    def test_extract_fallback_to_stderr(self):
        """Test error extraction falls back to stderr content."""
        updater = FreshclamUpdater()

        error_msg = updater._extract_error_message("", "Some random error message", exit_code=1)

        assert error_msg == "Some random error message"
