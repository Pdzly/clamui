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

from src.core.scanner import Scanner, ScanResult, ScanStatus, ThreatDetail, glob_to_regex, validate_pattern

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

    def test_build_command_with_exclusions(self, tmp_path):
        """Test _build_command includes exclusion patterns from settings."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Create a mock settings manager with exclusion patterns
        mock_settings = mock.MagicMock()
        mock_settings.get.return_value = [
            {"pattern": "*.log", "type": "file", "enabled": True},
            {"pattern": "node_modules", "type": "directory", "enabled": True},
            {"pattern": "*.tmp", "type": "pattern", "enabled": True},
            {"pattern": "*.disabled", "type": "file", "enabled": False},  # Should be skipped
            {"pattern": "", "type": "file", "enabled": True},  # Empty pattern, should be skipped
        ]

        scanner = Scanner(settings_manager=mock_settings)

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(test_dir), recursive=True)

        # Verify the command structure
        assert cmd[0] == "/usr/bin/clamscan"
        assert "-r" in cmd
        assert "-i" in cmd
        assert str(test_dir) in cmd

        # Verify file exclusions (--exclude) for *.log and *.tmp
        exclude_indices = [i for i, arg in enumerate(cmd) if arg == "--exclude"]
        assert len(exclude_indices) == 2  # *.log and *.tmp (not *.disabled which is disabled)

        # Verify directory exclusion (--exclude-dir) for node_modules
        exclude_dir_indices = [i for i, arg in enumerate(cmd) if arg == "--exclude-dir"]
        assert len(exclude_dir_indices) == 1

        # Verify the exclusion patterns are converted to regex
        # Get the argument following each --exclude flag
        exclude_patterns = [cmd[i + 1] for i in exclude_indices]
        exclude_dir_patterns = [cmd[i + 1] for i in exclude_dir_indices]

        # Verify regex patterns are present (glob_to_regex converts *.log to .*\.log etc.)
        # The exact regex format depends on fnmatch.translate, but should contain backslash-escaped dot
        assert any("log" in p for p in exclude_patterns)
        assert any("tmp" in p for p in exclude_patterns)
        assert any("node_modules" in p for p in exclude_dir_patterns)

        # Verify disabled patterns are NOT included
        all_args = " ".join(cmd)
        assert "disabled" not in all_args

    def test_build_command_without_settings_manager(self, tmp_path):
        """Test _build_command works without settings manager (no exclusions)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Scanner without settings manager
        scanner = Scanner()

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(test_file), recursive=False)

        # Should not have any exclusion flags
        assert "--exclude" not in cmd
        assert "--exclude-dir" not in cmd
        assert cmd[0] == "/usr/bin/clamscan"
        assert "-i" in cmd
        assert str(test_file) in cmd

    def test_build_command_with_empty_exclusions(self, tmp_path):
        """Test _build_command handles empty exclusions list."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Create a mock settings manager with empty exclusions
        mock_settings = mock.MagicMock()
        mock_settings.get.return_value = []

        scanner = Scanner(settings_manager=mock_settings)

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(test_file), recursive=False)

        # Should not have any exclusion flags
        assert "--exclude" not in cmd
        assert "--exclude-dir" not in cmd

    def test_disabled_exclusions_ignored(self, tmp_path):
        """Test _build_command ignores all disabled exclusions regardless of type."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Create a mock settings manager with ONLY disabled exclusions
        mock_settings = mock.MagicMock()
        mock_settings.get.return_value = [
            {"pattern": "*.log", "type": "file", "enabled": False},
            {"pattern": "node_modules", "type": "directory", "enabled": False},
            {"pattern": "*.tmp", "type": "pattern", "enabled": False},
            {"pattern": "__pycache__", "type": "directory", "enabled": False},
            {"pattern": ".git", "type": "directory", "enabled": False},
        ]

        scanner = Scanner(settings_manager=mock_settings)

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                cmd = scanner._build_command(str(test_dir), recursive=True)

        # Verify the command structure is correct
        assert cmd[0] == "/usr/bin/clamscan"
        assert "-r" in cmd
        assert "-i" in cmd
        assert str(test_dir) in cmd

        # Verify NO exclusion flags are present (all exclusions were disabled)
        assert "--exclude" not in cmd
        assert "--exclude-dir" not in cmd

        # Double-check none of the disabled patterns appear in the command
        all_args = " ".join(cmd)
        assert "log" not in all_args.lower()
        assert "node_modules" not in all_args
        assert "tmp" not in all_args.lower()
        assert "pycache" not in all_args
        assert ".git" not in all_args


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
            threat_details=[],
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
            threat_details=[],
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
            threat_details=[],
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
            threat_details=[],
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

    def test_parse_results_clean_has_empty_threat_details(self):
        """Test _parse_results returns empty threat_details for clean scans."""
        scanner = Scanner()

        stdout = """
/home/user/test.txt: OK

----------- SCAN SUMMARY -----------
Scanned files: 10
Infected files: 0
"""
        result = scanner._parse_results("/home/user", stdout, "", 0)

        assert result.status == ScanStatus.CLEAN
        assert len(result.threat_details) == 0

    def test_parse_results_extracts_threat_details(self):
        """Test _parse_results extracts ThreatDetail objects with correct data."""
        scanner = Scanner()

        stdout = """
/home/user/test/virus.txt: Eicar-Test-Signature FOUND

----------- SCAN SUMMARY -----------
Scanned files: 5
Infected files: 1
"""
        result = scanner._parse_results("/home/user/test", stdout, "", 1)

        assert len(result.threat_details) == 1
        threat = result.threat_details[0]
        assert threat.file_path == "/home/user/test/virus.txt"
        assert threat.threat_name == "Eicar-Test-Signature"
        assert threat.category == "Test"
        assert threat.severity == "low"

    def test_parse_results_multiple_threats_with_classification(self):
        """Test _parse_results correctly classifies multiple threats."""
        scanner = Scanner()

        stdout = """
/home/user/eicar.txt: Eicar-Test-Signature FOUND
/home/user/trojan.exe: Win.Trojan.Agent FOUND
/home/user/ransom.exe: Ransomware.Locky FOUND

----------- SCAN SUMMARY -----------
Scanned files: 100
Infected files: 3
"""
        result = scanner._parse_results("/home/user", stdout, "", 1)

        assert len(result.threat_details) == 3

        # EICAR - Test category, low severity
        assert result.threat_details[0].threat_name == "Eicar-Test-Signature"
        assert result.threat_details[0].category == "Test"
        assert result.threat_details[0].severity == "low"

        # Trojan - Trojan category, high severity
        assert result.threat_details[1].threat_name == "Win.Trojan.Agent"
        assert result.threat_details[1].category == "Trojan"
        assert result.threat_details[1].severity == "high"

        # Ransomware - Ransomware category, critical severity
        assert result.threat_details[2].threat_name == "Ransomware.Locky"
        assert result.threat_details[2].category == "Ransomware"
        assert result.threat_details[2].severity == "critical"

    def test_classify_threat_severity(self):
        """Test _classify_threat_severity returns correct severity levels."""
        scanner = Scanner()

        # Critical threats
        assert scanner._classify_threat_severity("Ransomware.Locky") == "critical"
        assert scanner._classify_threat_severity("Win.Rootkit.Agent") == "critical"
        assert scanner._classify_threat_severity("Bootkit.MBR") == "critical"
        assert scanner._classify_threat_severity("CryptoLocker.A") == "critical"

        # High threats
        assert scanner._classify_threat_severity("Trojan.Banker") == "high"
        assert scanner._classify_threat_severity("Worm.Mydoom") == "high"
        assert scanner._classify_threat_severity("Backdoor.IRC") == "high"
        assert scanner._classify_threat_severity("Exploit.CVE2021") == "high"
        assert scanner._classify_threat_severity("Downloader.Agent") == "high"

        # Medium threats
        assert scanner._classify_threat_severity("PUA.Adware.Generic") == "medium"
        assert scanner._classify_threat_severity("Spyware.Keylogger") == "high"  # keylogger = high
        assert scanner._classify_threat_severity("Coinminer.Generic") == "medium"
        assert scanner._classify_threat_severity("Unknown.Malware") == "medium"

        # Low threats
        assert scanner._classify_threat_severity("Eicar-Test-Signature") == "low"
        assert scanner._classify_threat_severity("Heuristic.Generic") == "low"

        # Edge cases
        assert scanner._classify_threat_severity("") == "medium"

    def test_categorize_threat(self):
        """Test _categorize_threat extracts correct category from threat name."""
        scanner = Scanner()

        # Specific categories
        assert scanner._categorize_threat("Win.Trojan.Agent") == "Trojan"
        assert scanner._categorize_threat("Worm.Mydoom") == "Worm"
        assert scanner._categorize_threat("Ransomware.Locky") == "Ransomware"
        assert scanner._categorize_threat("Win.Rootkit.Agent") == "Rootkit"
        assert scanner._categorize_threat("Backdoor.IRC") == "Backdoor"
        assert scanner._categorize_threat("Exploit.PDF") == "Exploit"
        assert scanner._categorize_threat("PUA.Adware.Generic") == "Adware"
        assert scanner._categorize_threat("Eicar-Test-Signature") == "Test"
        assert scanner._categorize_threat("Phishing.Email") == "Phishing"

        # Default category for unknown
        assert scanner._categorize_threat("Unknown.Malware") == "Virus"
        assert scanner._categorize_threat("") == "Unknown"


class TestScannerThreatDetailsIntegration:
    """Integration tests for enhanced scanner with threat details."""

    def test_scan_sync_threat_details_integration(self, tmp_path):
        """Integration test: scan_sync produces structured threat details."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        # Mock clamscan output with infected result
        mock_stdout = """
/home/user/virus.exe: Win.Trojan.Agent FOUND

----------- SCAN SUMMARY -----------
Scanned files: 5
Infected files: 1
"""

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                with mock.patch("src.core.scanner.check_clamav_installed", return_value=(True, "1.0.0")):
                    with mock.patch("subprocess.Popen") as mock_popen:
                        mock_process = mock.MagicMock()
                        mock_process.communicate.return_value = (mock_stdout, "")
                        mock_process.returncode = 1
                        mock_popen.return_value = mock_process

                        result = scanner.scan_sync(str(test_file))

        # Verify threat details are properly populated
        assert result.status == ScanStatus.INFECTED
        assert len(result.threat_details) == 1
        assert result.threat_details[0].file_path == "/home/user/virus.exe"
        assert result.threat_details[0].threat_name == "Win.Trojan.Agent"
        assert result.threat_details[0].category == "Trojan"
        assert result.threat_details[0].severity == "high"

    def test_scan_sync_multiple_threat_details_integration(self, tmp_path):
        """Integration test: scan_sync handles multiple threats with different severities."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        scanner = Scanner()

        # Mock clamscan output with multiple infected files
        mock_stdout = """
/home/user/critical.exe: Ransomware.Locky FOUND
/home/user/high.exe: Win.Trojan.Agent FOUND
/home/user/medium.exe: PUA.Adware.Generic FOUND
/home/user/low.exe: Eicar-Test-Signature FOUND

----------- SCAN SUMMARY -----------
Scanned directories: 1
Scanned files: 100
Infected files: 4
"""

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                with mock.patch("src.core.scanner.check_clamav_installed", return_value=(True, "1.0.0")):
                    with mock.patch("subprocess.Popen") as mock_popen:
                        mock_process = mock.MagicMock()
                        mock_process.communicate.return_value = (mock_stdout, "")
                        mock_process.returncode = 1
                        mock_popen.return_value = mock_process

                        result = scanner.scan_sync(str(test_dir), recursive=True)

        # Verify all threat details are captured with correct classification
        assert result.status == ScanStatus.INFECTED
        assert result.infected_count == 4
        assert len(result.threat_details) == 4

        # Verify each threat has correct severity
        severities = {t.threat_name: t.severity for t in result.threat_details}
        assert severities["Ransomware.Locky"] == "critical"
        assert severities["Win.Trojan.Agent"] == "high"
        assert severities["PUA.Adware.Generic"] == "medium"
        assert severities["Eicar-Test-Signature"] == "low"

        # Verify categories
        categories = {t.threat_name: t.category for t in result.threat_details}
        assert categories["Ransomware.Locky"] == "Ransomware"
        assert categories["Win.Trojan.Agent"] == "Trojan"
        assert categories["PUA.Adware.Generic"] == "Adware"
        assert categories["Eicar-Test-Signature"] == "Test"

    def test_scan_sync_clean_threat_details_empty(self, tmp_path):
        """Integration test: clean scan produces empty threat_details list."""
        test_file = tmp_path / "clean.txt"
        test_file.write_text("clean content")

        scanner = Scanner()

        # Mock clamscan output with clean result
        mock_stdout = """
/home/user/clean.txt: OK

----------- SCAN SUMMARY -----------
Scanned files: 1
Infected files: 0
"""

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                with mock.patch("src.core.scanner.check_clamav_installed", return_value=(True, "1.0.0")):
                    with mock.patch("subprocess.Popen") as mock_popen:
                        mock_process = mock.MagicMock()
                        mock_process.communicate.return_value = (mock_stdout, "")
                        mock_process.returncode = 0
                        mock_popen.return_value = mock_process

                        result = scanner.scan_sync(str(test_file))

        # Verify clean result has empty threat_details
        assert result.status == ScanStatus.CLEAN
        assert result.is_clean is True
        assert result.has_threats is False
        assert len(result.threat_details) == 0
        assert result.infected_count == 0

    def test_threat_details_file_path_preserved(self, tmp_path):
        """Integration test: threat details preserve full file paths."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        # Mock output with complex path
        mock_stdout = """
/home/user/Documents/My Files/virus (copy).exe: Win.Trojan.Agent FOUND

----------- SCAN SUMMARY -----------
Scanned files: 1
Infected files: 1
"""

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                with mock.patch("src.core.scanner.check_clamav_installed", return_value=(True, "1.0.0")):
                    with mock.patch("subprocess.Popen") as mock_popen:
                        mock_process = mock.MagicMock()
                        mock_process.communicate.return_value = (mock_stdout, "")
                        mock_process.returncode = 1
                        mock_popen.return_value = mock_process

                        result = scanner.scan_sync(str(test_file))

        # Verify file path is preserved including spaces and special characters
        assert len(result.threat_details) == 1
        assert result.threat_details[0].file_path == "/home/user/Documents/My Files/virus (copy).exe"

    def test_threat_details_with_cancelled_scan(self, tmp_path):
        """Integration test: cancelled scan produces empty threat_details."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        # Set up mock to simulate cancellation during communicate()
        def simulate_cancel(*args, **kwargs):
            scanner._scan_cancelled = True
            return ("", "")

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                with mock.patch("src.core.scanner.check_clamav_installed", return_value=(True, "1.0.0")):
                    with mock.patch("subprocess.Popen") as mock_popen:
                        mock_process = mock.MagicMock()
                        mock_process.communicate.side_effect = simulate_cancel
                        mock_process.returncode = 0
                        mock_popen.return_value = mock_process

                        result = scanner.scan_sync(str(test_file))

        # Verify cancelled scan has empty threat_details
        assert result.status == ScanStatus.CANCELLED
        assert len(result.threat_details) == 0

    def test_threat_details_with_error_scan(self, tmp_path):
        """Integration test: error scan produces empty threat_details."""
        scanner = Scanner()

        # Mock ClamAV not installed
        with mock.patch("src.core.scanner.check_clamav_installed", return_value=(False, "ClamAV not found")):
            with mock.patch("src.core.scanner.validate_path", return_value=(True, None)):
                result = scanner.scan_sync("/nonexistent/path")

        # Verify error result has empty threat_details
        assert result.status == ScanStatus.ERROR
        assert len(result.threat_details) == 0

    def test_threat_details_dataclass_attributes(self):
        """Test ThreatDetail dataclass has correct attributes."""
        threat = ThreatDetail(
            file_path="/test/virus.exe",
            threat_name="Win.Trojan.Agent",
            category="Trojan",
            severity="high"
        )

        assert threat.file_path == "/test/virus.exe"
        assert threat.threat_name == "Win.Trojan.Agent"
        assert threat.category == "Trojan"
        assert threat.severity == "high"

    def test_threat_details_all_severity_levels(self):
        """Integration test: verify all severity levels are correctly assigned."""
        scanner = Scanner()

        # Create output with threats of each severity level
        mock_stdout = """
/path/ransomware.exe: Ransomware.WannaCry FOUND
/path/rootkit.exe: Linux.Rootkit.Agent FOUND
/path/trojan.exe: Trojan.Banker FOUND
/path/worm.exe: Worm.Slammer FOUND
/path/backdoor.exe: Backdoor.Cobalt FOUND
/path/adware.exe: Adware.Toolbar FOUND
/path/eicar.txt: Eicar-Test-Signature FOUND
/path/generic.exe: Heuristic.Generic FOUND

----------- SCAN SUMMARY -----------
Scanned files: 8
Infected files: 8
"""

        result = scanner._parse_results("/path", mock_stdout, "", 1)

        assert len(result.threat_details) == 8

        # Build a map for easy verification
        threat_map = {t.threat_name: t for t in result.threat_details}

        # Critical severity
        assert threat_map["Ransomware.WannaCry"].severity == "critical"
        assert threat_map["Linux.Rootkit.Agent"].severity == "critical"

        # High severity
        assert threat_map["Trojan.Banker"].severity == "high"
        assert threat_map["Worm.Slammer"].severity == "high"
        assert threat_map["Backdoor.Cobalt"].severity == "high"

        # Medium severity
        assert threat_map["Adware.Toolbar"].severity == "medium"

        # Low severity
        assert threat_map["Eicar-Test-Signature"].severity == "low"
        assert threat_map["Heuristic.Generic"].severity == "low"

    def test_threat_details_integration_with_scan_result_properties(self, tmp_path):
        """Integration test: threat_details integrates with ScanResult properties."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        mock_stdout = """
/home/user/virus.exe: Win.Trojan.Agent FOUND

----------- SCAN SUMMARY -----------
Scanned files: 10
Scanned directories: 2
Infected files: 1
"""

        with mock.patch("src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"):
            with mock.patch("src.core.scanner.wrap_host_command", side_effect=lambda x: x):
                with mock.patch("src.core.scanner.check_clamav_installed", return_value=(True, "1.0.0")):
                    with mock.patch("subprocess.Popen") as mock_popen:
                        mock_process = mock.MagicMock()
                        mock_process.communicate.return_value = (mock_stdout, "")
                        mock_process.returncode = 1
                        mock_popen.return_value = mock_process

                        result = scanner.scan_sync(str(test_file))

        # Verify ScanResult properties work with threat_details
        assert result.is_clean is False
        assert result.has_threats is True
        assert result.infected_count == 1
        assert len(result.infected_files) == 1
        assert len(result.threat_details) == 1

        # Verify threat_details and infected_files are consistent
        assert result.threat_details[0].file_path == result.infected_files[0]


class TestPatternUtilities:
    """Tests for the glob_to_regex and validate_pattern utility functions."""

    # Tests for glob_to_regex function

    def test_glob_to_regex_simple_wildcard(self):
        """Test glob_to_regex converts simple wildcard patterns."""
        regex = glob_to_regex("*.log")
        # Should match any string ending with .log
        assert regex  # Not empty
        # Verify it's a valid regex by compiling
        import re
        compiled = re.compile(regex)
        assert compiled.match("test.log")
        assert compiled.match("error.log")
        assert not compiled.match("test.txt")

    def test_glob_to_regex_directory_pattern(self):
        """Test glob_to_regex converts directory name patterns."""
        regex = glob_to_regex("node_modules")
        import re
        compiled = re.compile(regex)
        assert compiled.match("node_modules")
        assert not compiled.match("node_modules_backup")

    def test_glob_to_regex_path_wildcard(self):
        """Test glob_to_regex converts path wildcard patterns."""
        regex = glob_to_regex("/tmp/*")
        import re
        compiled = re.compile(regex)
        assert compiled.match("/tmp/file.txt")
        assert compiled.match("/tmp/subdir")
        assert not compiled.match("/var/tmp/file")

    def test_glob_to_regex_multiple_wildcards(self):
        """Test glob_to_regex handles multiple wildcards."""
        regex = glob_to_regex("*.test.*")
        import re
        compiled = re.compile(regex)
        assert compiled.match("file.test.js")
        assert compiled.match("module.test.py")
        assert not compiled.match("file.spec.js")

    def test_glob_to_regex_question_mark_wildcard(self):
        """Test glob_to_regex converts ? wildcard (single character)."""
        regex = glob_to_regex("file?.txt")
        import re
        compiled = re.compile(regex)
        assert compiled.match("file1.txt")
        assert compiled.match("fileA.txt")
        assert not compiled.match("file12.txt")
        assert not compiled.match("file.txt")

    def test_glob_to_regex_character_class(self):
        """Test glob_to_regex converts character class patterns."""
        regex = glob_to_regex("file[0-9].txt")
        import re
        compiled = re.compile(regex)
        assert compiled.match("file0.txt")
        assert compiled.match("file9.txt")
        assert not compiled.match("fileA.txt")
        assert not compiled.match("file10.txt")

    def test_glob_to_regex_no_python_suffix(self):
        """Test glob_to_regex strips Python-specific regex suffixes."""
        regex = glob_to_regex("*.log")
        # Should not contain \Z (Python anchor)
        assert "\\Z" not in regex
        # Should not contain (?s: wrapper (newer Python)
        assert not regex.startswith("(?s:")

    def test_glob_to_regex_common_exclusion_patterns(self):
        """Test glob_to_regex handles common exclusion patterns."""
        import re

        # .git directory
        regex = glob_to_regex(".git")
        assert re.compile(regex).match(".git")

        # __pycache__ directory
        regex = glob_to_regex("__pycache__")
        assert re.compile(regex).match("__pycache__")

        # .venv directory
        regex = glob_to_regex(".venv")
        assert re.compile(regex).match(".venv")

        # build directory
        regex = glob_to_regex("build")
        assert re.compile(regex).match("build")

        # *.pyc files
        regex = glob_to_regex("*.pyc")
        compiled = re.compile(regex)
        assert compiled.match("module.pyc")
        assert not compiled.match("module.py")

    def test_glob_to_regex_special_characters_escaped(self):
        """Test glob_to_regex properly escapes special regex characters."""
        import re

        # Dots are escaped (not treated as regex wildcard)
        regex = glob_to_regex("file.txt")
        compiled = re.compile(regex)
        assert compiled.match("file.txt")
        assert not compiled.match("filextxt")  # Would match if . wasn't escaped

    def test_glob_to_regex_empty_pattern(self):
        """Test glob_to_regex handles empty pattern."""
        regex = glob_to_regex("")
        # Should return something (empty string becomes regex that matches empty)
        assert regex is not None

    # Tests for validate_pattern function

    def test_validate_pattern_valid_simple_wildcard(self):
        """Test validate_pattern accepts valid simple wildcard patterns."""
        assert validate_pattern("*.log") is True
        assert validate_pattern("*.txt") is True
        assert validate_pattern("*.py") is True

    def test_validate_pattern_valid_directory_names(self):
        """Test validate_pattern accepts valid directory name patterns."""
        assert validate_pattern("node_modules") is True
        assert validate_pattern(".git") is True
        assert validate_pattern("__pycache__") is True
        assert validate_pattern(".venv") is True
        assert validate_pattern("build") is True
        assert validate_pattern("dist") is True

    def test_validate_pattern_valid_path_patterns(self):
        """Test validate_pattern accepts valid path patterns."""
        assert validate_pattern("/tmp/*") is True
        assert validate_pattern("/var/log/*.log") is True
        assert validate_pattern("src/**") is True

    def test_validate_pattern_valid_complex_patterns(self):
        """Test validate_pattern accepts valid complex patterns."""
        assert validate_pattern("*.test.js") is True
        assert validate_pattern("file[0-9].txt") is True
        assert validate_pattern("file?.txt") is True

    def test_validate_pattern_empty_string(self):
        """Test validate_pattern rejects empty string."""
        assert validate_pattern("") is False

    def test_validate_pattern_whitespace_only(self):
        """Test validate_pattern rejects whitespace-only patterns."""
        assert validate_pattern("   ") is False
        assert validate_pattern("\t") is False
        assert validate_pattern("\n") is False
        assert validate_pattern("  \t\n  ") is False

    def test_validate_pattern_valid_with_spaces(self):
        """Test validate_pattern accepts patterns with internal spaces."""
        # Patterns with spaces are valid (e.g., matching files with spaces)
        assert validate_pattern("My Documents") is True
        assert validate_pattern("*.log file") is True

    def test_validate_pattern_common_development_exclusions(self):
        """Test validate_pattern accepts all common development exclusion patterns."""
        common_patterns = [
            "node_modules",
            ".git",
            ".venv",
            "build",
            "dist",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".env",
            ".DS_Store",
            "*.log",
            "*.tmp",
            "coverage",
            ".coverage",
            ".pytest_cache",
            ".mypy_cache",
            "*.egg-info",
        ]
        for pattern in common_patterns:
            assert validate_pattern(pattern) is True, f"Pattern '{pattern}' should be valid"

    def test_validate_pattern_preserves_none_handling(self):
        """Test validate_pattern handles None gracefully (if passed)."""
        # The function expects a string, but should handle edge cases
        # This test verifies that empty/falsy values are rejected
        assert validate_pattern("") is False
