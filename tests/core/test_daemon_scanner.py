# ClamUI Daemon Scanner Tests
"""Unit tests for the daemon scanner module."""

from unittest.mock import MagicMock, patch

import pytest

# Import directly - daemon_scanner uses GLib only for idle_add in async methods,
# and those methods are not tested here (unit tests mock the async behavior)
from src.core.daemon_scanner import DaemonScanner
from src.core.scanner import ScanStatus
from src.core.threat_classifier import categorize_threat, classify_threat_severity_str


@pytest.fixture
def daemon_scanner_class():
    """Get DaemonScanner class."""
    return DaemonScanner


@pytest.fixture
def scan_status_class():
    """Get ScanStatus enum."""
    return ScanStatus


@pytest.fixture
def daemon_scanner():
    """Create a DaemonScanner instance for testing."""
    return DaemonScanner()


class TestDaemonScannerCheckAvailable:
    """Tests for DaemonScanner.check_available method."""

    def test_check_available_when_daemon_running(self, daemon_scanner_class):
        """Test availability check when clamd is running."""
        scanner = daemon_scanner_class()

        with patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed:
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            with patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection:
                mock_connection.return_value = (True, "PONG")

                available, msg = scanner.check_available()

        assert available is True
        assert "available" in msg.lower()

    def test_check_available_clamdscan_not_installed(self, daemon_scanner_class):
        """Test availability check when clamdscan is not installed."""
        scanner = daemon_scanner_class()

        with patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed:
            mock_installed.return_value = (False, "clamdscan not found")

            available, msg = scanner.check_available()

        assert available is False
        assert "not found" in msg.lower() or "clamdscan" in msg.lower()

    def test_check_available_daemon_not_running(self, daemon_scanner_class):
        """Test availability check when clamd is not running."""
        scanner = daemon_scanner_class()

        with patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed:
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            with patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection:
                mock_connection.return_value = (False, "Connection refused")

                available, msg = scanner.check_available()

        assert available is False
        assert "not accessible" in msg.lower() or "connection" in msg.lower()


class TestDaemonScannerBuildCommand:
    """Tests for DaemonScanner._build_command method."""

    def test_build_command_basic(self, tmp_path, daemon_scanner_class):
        """Test _build_command builds correct clamdscan command."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = daemon_scanner_class()

        with patch("src.core.daemon_scanner.which_host_command", return_value="/usr/bin/clamdscan"):
            with patch("src.core.daemon_scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(test_file), recursive=True)

        assert cmd[0] == "/usr/bin/clamdscan"
        assert "--multiscan" in cmd
        assert "--fdpass" in cmd
        assert "-i" in cmd
        assert str(test_file) in cmd

    def test_build_command_fallback_to_clamdscan(self, tmp_path, daemon_scanner_class):
        """Test _build_command falls back to 'clamdscan' when path not found."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = daemon_scanner_class()

        with patch("src.core.daemon_scanner.which_host_command", return_value=None):
            with patch("src.core.daemon_scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(test_file), recursive=True)

        assert cmd[0] == "clamdscan"

    def test_build_command_with_exclusions(self, tmp_path, daemon_scanner_class):
        """Test _build_command includes exclusion patterns from settings."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_settings = MagicMock()
        mock_settings.get.return_value = [
            {"pattern": "*.log", "type": "file", "enabled": True},
            {"pattern": "node_modules", "type": "directory", "enabled": True},
        ]

        scanner = daemon_scanner_class(settings_manager=mock_settings)

        with patch("src.core.daemon_scanner.which_host_command", return_value="/usr/bin/clamdscan"):
            with patch("src.core.daemon_scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(test_file), recursive=True)

        # Check exclusions are added
        assert "--exclude" in cmd
        assert "--exclude-dir" in cmd


class TestDaemonScannerParseResults:
    """Tests for DaemonScanner._parse_results method."""

    def test_parse_results_clean_scan(self, daemon_scanner_class, scan_status_class):
        """Test parsing clean scan results."""
        scanner = daemon_scanner_class()

        # clamdscan output doesn't include file/directory counts,
        # so they are passed as parameters from pre-counting
        stdout = """
/home/user/test.txt: OK

----------- SCAN SUMMARY -----------
Infected files: 0
"""
        result = scanner._parse_results("/home/user", stdout, "", 0, file_count=1, dir_count=0)

        assert result.status == scan_status_class.CLEAN
        assert result.infected_count == 0
        assert result.scanned_files == 1

    def test_parse_results_infected_scan(self, daemon_scanner_class, scan_status_class):
        """Test parsing infected scan results."""
        scanner = daemon_scanner_class()

        # clamdscan output with -i flag only shows infected files
        stdout = """
/home/user/malware.exe: Win.Trojan.Agent FOUND

----------- SCAN SUMMARY -----------
Infected files: 1
"""
        result = scanner._parse_results("/home/user", stdout, "", 1, file_count=1, dir_count=0)

        assert result.status == scan_status_class.INFECTED
        assert result.infected_count == 1
        assert len(result.threat_details) == 1
        assert result.threat_details[0].threat_name == "Win.Trojan.Agent"
        assert result.threat_details[0].file_path == "/home/user/malware.exe"

    def test_parse_results_error(self, daemon_scanner_class, scan_status_class):
        """Test parsing error scan results."""
        scanner = daemon_scanner_class()

        result = scanner._parse_results("/home/user", "", "Connection refused", 2)

        assert result.status == scan_status_class.ERROR
        assert result.error_message is not None


class TestDaemonScannerThreatClassification:
    """Tests for threat classification functions."""

    def test_classify_threat_severity_critical(self):
        """Test classifying ransomware as critical."""
        severity = classify_threat_severity_str("Win.Ransomware.Locky")
        assert severity == "critical"

    def test_classify_threat_severity_high(self):
        """Test classifying trojan as high severity."""
        severity = classify_threat_severity_str("Win.Trojan.Agent")
        assert severity == "high"

    def test_classify_threat_severity_low(self):
        """Test classifying EICAR test as low severity."""
        severity = classify_threat_severity_str("Eicar-Test-Signature")
        assert severity == "low"

    def test_categorize_threat_trojan(self):
        """Test categorizing a trojan threat."""
        category = categorize_threat("Win.Trojan.Agent")
        assert category == "Trojan"

    def test_categorize_threat_ransomware(self):
        """Test categorizing a ransomware threat."""
        category = categorize_threat("Win.Ransomware.Locky")
        assert category == "Ransomware"


class TestDaemonScannerCancel:
    """Tests for DaemonScanner.cancel method."""

    def test_cancel_sets_flag(self, daemon_scanner_class):
        """Test that cancel sets the cancelled flag."""
        scanner = daemon_scanner_class()

        scanner.cancel()

        assert scanner._scan_cancelled is True

    def test_cancel_terminates_process(self, daemon_scanner_class):
        """Test that cancel terminates running process."""
        scanner = daemon_scanner_class()
        mock_process = MagicMock()
        scanner._current_process = mock_process

        scanner.cancel()

        mock_process.terminate.assert_called_once()
