# ClamUI Scanner Tests
"""Unit tests for the scanner module, including Flatpak integration."""

import sys
from unittest import mock

import pytest

# Store original gi modules to restore later (if they exist)
_original_gi = sys.modules.get("gi")
_original_gi_repository = sys.modules.get("gi.repository")

# Mock gi module before importing src.core to avoid GTK dependencies in tests
sys.modules["gi"] = mock.MagicMock()
sys.modules["gi.repository"] = mock.MagicMock()

from src.core.scanner import Scanner, ScanResult, ScanStatus

# Restore original gi modules after imports are done
if _original_gi is not None:
    sys.modules["gi"] = _original_gi
else:
    del sys.modules["gi"]
if _original_gi_repository is not None:
    sys.modules["gi.repository"] = _original_gi_repository
else:
    del sys.modules["gi.repository"]


class TestScannerBuildCommand:
    """Tests for the Scanner._build_command method."""

    def test_build_command_basic_file(self, tmp_path):
        """Test _build_command for a basic file scan without Flatpak."""
        # Create a temporary file for testing
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(test_file), recursive=False)

        # Should be clamscan with -i flag and path
        assert cmd[0] == "/usr/bin/clamscan"
        assert "-i" in cmd
        assert str(test_file) in cmd
        # Should NOT have -r flag for file (non-recursive)
        assert "-r" not in cmd

    def test_build_command_directory_recursive(self, tmp_path):
        """Test _build_command for recursive directory scan."""
        scanner = Scanner()

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(tmp_path), recursive=True)

        # Should have -r flag for directory
        assert cmd[0] == "/usr/bin/clamscan"
        assert "-r" in cmd
        assert "-i" in cmd
        assert str(tmp_path) in cmd

    def test_build_command_fallback_to_clamscan(self, tmp_path):
        """Test _build_command falls back to 'clamscan' when path not found."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        with mock.patch("src.core.scanner.get_clamav_path", return_value=None):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(test_file), recursive=False)

        # Should fall back to 'clamscan'
        assert cmd[0] == "clamscan"

    def test_build_command_wraps_with_flatpak_spawn(self, tmp_path):
        """Test _build_command wraps command with flatpak-spawn when in Flatpak."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        # Mock wrap_host_command to add flatpak-spawn prefix (simulating Flatpak environment)
        def mock_wrap(cmd):
            return ["flatpak-spawn", "--host"] + cmd

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=mock_wrap):
                cmd = scanner._build_command(str(test_file), recursive=False)

        # Should be prefixed with flatpak-spawn --host
        assert cmd[0] == "flatpak-spawn"
        assert cmd[1] == "--host"
        assert cmd[2] == "/usr/bin/clamscan"
        assert "-i" in cmd
        assert str(test_file) in cmd

    def test_build_command_no_wrap_outside_flatpak(self, tmp_path):
        """Test _build_command does NOT wrap when not in Flatpak."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        # Mock wrap_host_command to return command unchanged (not in Flatpak)
        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(test_file), recursive=False)

        # Should NOT be prefixed with flatpak-spawn
        assert cmd[0] == "/usr/bin/clamscan"
        assert "flatpak-spawn" not in cmd


class TestScannerFlatpakIntegration:
    """Tests for Flatpak integration in Scanner."""

    def test_scanner_uses_wrap_host_command(self, tmp_path):
        """Test that Scanner._build_command calls wrap_host_command."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command") as mock_wrap:
                mock_wrap.return_value = ["/usr/bin/clamscan", "-i", str(test_file)]
                scanner._build_command(str(test_file), recursive=False)

        # Verify wrap_host_command was called
        mock_wrap.assert_called_once()
        # Verify it was called with the expected base command
        call_args = mock_wrap.call_args[0][0]
        assert call_args[0] == "/usr/bin/clamscan"


class TestScanResult:
    """Tests for the ScanResult dataclass."""

    def test_scan_result_is_clean(self):
        """Test ScanResult.is_clean property."""
        result = ScanResult(
            status=ScanStatus.CLEAN,
            path="/test/path",
            stdout="",
            stderr="",
            exit_code=0,
            infected_files=[],
            scanned_files=10,
            scanned_dirs=1,
            infected_count=0,
            error_message=None,
        )
        assert result.is_clean is True
        assert result.has_threats is False

    def test_scan_result_has_threats(self):
        """Test ScanResult.has_threats property."""
        result = ScanResult(
            status=ScanStatus.INFECTED,
            path="/test/path",
            stdout="",
            stderr="",
            exit_code=1,
            infected_files=["/test/infected.txt"],
            scanned_files=10,
            scanned_dirs=1,
            infected_count=1,
            error_message=None,
        )
        assert result.is_clean is False
        assert result.has_threats is True

    def test_scan_result_error(self):
        """Test ScanResult with error status."""
        result = ScanResult(
            status=ScanStatus.ERROR,
            path="/test/path",
            stdout="",
            stderr="ClamAV error",
            exit_code=2,
            infected_files=[],
            scanned_files=0,
            scanned_dirs=0,
            infected_count=0,
            error_message="ClamAV error",
        )
        assert result.is_clean is False
        assert result.has_threats is False

    def test_scan_result_cancelled(self):
        """Test ScanResult with cancelled status."""
        result = ScanResult(
            status=ScanStatus.CANCELLED,
            path="/test/path",
            stdout="",
            stderr="",
            exit_code=-1,
            infected_files=[],
            scanned_files=0,
            scanned_dirs=0,
            infected_count=0,
            error_message="Scan cancelled by user",
        )
        assert result.is_clean is False
        assert result.has_threats is False


class TestScanStatus:
    """Tests for the ScanStatus enum."""

    def test_scan_status_values(self):
        """Test ScanStatus enum has expected values."""
        assert ScanStatus.CLEAN.value == "clean"
        assert ScanStatus.INFECTED.value == "infected"
        assert ScanStatus.ERROR.value == "error"
        assert ScanStatus.CANCELLED.value == "cancelled"


class TestScannerParseResults:
    """Tests for the Scanner._parse_results method."""

    def test_parse_results_clean(self):
        """Test _parse_results with clean scan output."""
        scanner = Scanner()

        stdout = """
/home/user/test.txt: OK

----------- SCAN SUMMARY -----------
Known viruses: 8000000
Engine version: 1.2.3
Scanned directories: 1
Scanned files: 10
Infected files: 0
Data scanned: 0.50 MB
Data read: 0.50 MB
Time: 0.500 sec (0 m 0 s)
"""
        result = scanner._parse_results("/home/user", stdout, "", 0)

        assert result.status == ScanStatus.CLEAN
        assert result.infected_count == 0
        assert result.scanned_files == 10
        assert result.scanned_dirs == 1
        assert len(result.infected_files) == 0

    def test_parse_results_infected(self):
        """Test _parse_results with infected scan output."""
        scanner = Scanner()

        stdout = """
/home/user/test/virus.txt: Eicar-Test-Signature FOUND

----------- SCAN SUMMARY -----------
Known viruses: 8000000
Engine version: 1.2.3
Scanned directories: 1
Scanned files: 5
Infected files: 1
Data scanned: 0.01 MB
Data read: 0.01 MB
Time: 0.100 sec (0 m 0 s)
"""
        result = scanner._parse_results("/home/user/test", stdout, "", 1)

        assert result.status == ScanStatus.INFECTED
        assert result.infected_count == 1
        assert result.scanned_files == 5
        assert len(result.infected_files) == 1
        assert "/home/user/test/virus.txt" in result.infected_files

    def test_parse_results_error(self):
        """Test _parse_results with error exit code."""
        scanner = Scanner()

        result = scanner._parse_results("/nonexistent", "", "Can't access path", 2)

        assert result.status == ScanStatus.ERROR
        assert result.error_message is not None

    def test_parse_results_multiple_infected(self):
        """Test _parse_results with multiple infected files."""
        scanner = Scanner()

        stdout = """
/home/user/virus1.txt: Eicar-Test-Signature FOUND
/home/user/virus2.txt: Trojan.Generic FOUND
/home/user/virus3.exe: Win.Trojan.Agent FOUND

----------- SCAN SUMMARY -----------
Scanned files: 100
Infected files: 3
"""
        result = scanner._parse_results("/home/user", stdout, "", 1)

        assert result.status == ScanStatus.INFECTED
        assert result.infected_count == 3
        assert len(result.infected_files) == 3
