# ClamUI Utils Tests
"""Unit tests for the utils module functions."""

import sys
from unittest import mock

# Store original gi modules to restore later (if they exist)
_original_gi = sys.modules.get("gi")
_original_gi_repository = sys.modules.get("gi.repository")

# Mock gi module before importing src.core to avoid GTK dependencies in tests
sys.modules["gi"] = mock.MagicMock()
sys.modules["gi.repository"] = mock.MagicMock()

from src.core.scanner import ScanResult, ScanStatus, ThreatDetail
from src.core.threat_classifier import ThreatSeverity, categorize_threat, classify_threat_severity
from src.core.utils import (
    check_clamav_installed,
    check_clamdscan_installed,
    check_freshclam_installed,
    format_results_as_csv,
    format_results_as_text,
    format_scan_path,
    get_clamav_path,
    get_freshclam_path,
    get_path_info,
    validate_dropped_files,
    validate_path,
)

# Restore original gi modules after imports are done
if _original_gi is not None:
    sys.modules["gi"] = _original_gi
else:
    del sys.modules["gi"]
if _original_gi_repository is not None:
    sys.modules["gi.repository"] = _original_gi_repository
else:
    del sys.modules["gi.repository"]


class TestCheckClamdscanInstalled:
    """Tests for the check_clamdscan_installed function."""

    def test_check_clamdscan_installed(self):
        """Test clamdscan check returns (True, version) when installed."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0,
                    stdout="ClamAV 1.2.3/27421/Mon Dec 30 09:00:00 2024\n",
                    stderr="",
                )
                installed, version = check_clamdscan_installed()
                assert installed is True
                assert "ClamAV" in version

    def test_check_clamdscan_not_installed(self):
        """Test clamdscan check returns (False, message) when not installed."""
        with mock.patch("shutil.which", return_value=None):
            installed, message = check_clamdscan_installed()
            assert installed is False
            assert "not installed" in message.lower()

    def test_check_clamdscan_timeout(self):
        """Test clamdscan check handles timeout gracefully."""
        import subprocess

        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired(cmd="clamdscan", timeout=10)
                installed, message = check_clamdscan_installed()
                assert installed is False
                assert "timed out" in message.lower()

    def test_check_clamdscan_permission_denied(self):
        """Test clamdscan check handles permission errors gracefully."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = PermissionError("Permission denied")
                installed, message = check_clamdscan_installed()
                assert installed is False
                assert "permission denied" in message.lower()

    def test_check_clamdscan_file_not_found(self):
        """Test clamdscan check handles FileNotFoundError gracefully."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("File not found")
                installed, message = check_clamdscan_installed()
                assert installed is False
                assert "not found" in message.lower()

    def test_check_clamdscan_returns_error(self):
        """Test clamdscan check when command returns non-zero exit code."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=1,
                    stdout="",
                    stderr="Some error occurred",
                )
                installed, message = check_clamdscan_installed()
                assert installed is False
                assert "error" in message.lower()

    def test_check_clamdscan_generic_exception(self):
        """Test clamdscan check handles generic exceptions gracefully."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamdscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = Exception("Unexpected error")
                installed, message = check_clamdscan_installed()
                assert installed is False
                assert "error" in message.lower()


class TestCheckClamavInstalled:
    """Tests for the check_clamav_installed function."""

    def test_check_clamav_installed(self):
        """Test clamscan check returns (True, version) when installed."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamscan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0,
                    stdout="ClamAV 1.2.3/27421/Mon Dec 30 09:00:00 2024\n",
                    stderr="",
                )
                installed, version = check_clamav_installed()
                assert installed is True
                assert "ClamAV" in version

    def test_check_clamav_not_installed(self):
        """Test clamscan check returns (False, message) when not installed."""
        with mock.patch("shutil.which", return_value=None):
            installed, message = check_clamav_installed()
            assert installed is False
            assert "not installed" in message.lower()


class TestCheckFreshclamInstalled:
    """Tests for the check_freshclam_installed function."""

    def test_check_freshclam_installed(self):
        """Test freshclam check returns (True, version) when installed."""
        with mock.patch("shutil.which", return_value="/usr/bin/freshclam"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0,
                    stdout="ClamAV 1.2.3/27421/Mon Dec 30 09:00:00 2024\n",
                    stderr="",
                )
                installed, version = check_freshclam_installed()
                assert installed is True
                assert "ClamAV" in version

    def test_check_freshclam_not_installed(self):
        """Test freshclam check returns (False, message) when not installed."""
        with mock.patch("shutil.which", return_value=None):
            installed, message = check_freshclam_installed()
            assert installed is False
            assert "not installed" in message.lower()


class TestValidatePath:
    """Tests for the validate_path function."""

    def test_validate_path_empty(self):
        """Test validate_path returns error for empty path."""
        is_valid, error = validate_path("")
        assert is_valid is False
        assert "no path" in error.lower()

    def test_validate_path_whitespace_only(self):
        """Test validate_path returns error for whitespace-only path."""
        is_valid, error = validate_path("   ")
        assert is_valid is False
        assert "no path" in error.lower()

    def test_validate_path_nonexistent(self):
        """Test validate_path returns error for non-existent path."""
        is_valid, error = validate_path("/nonexistent/path/that/does/not/exist")
        assert is_valid is False
        assert "does not exist" in error.lower()

    def test_validate_path_existing_file(self, tmp_path):
        """Test validate_path returns success for existing readable file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        is_valid, error = validate_path(str(test_file))
        assert is_valid is True
        assert error is None

    def test_validate_path_existing_directory(self, tmp_path):
        """Test validate_path returns success for existing readable directory."""
        is_valid, error = validate_path(str(tmp_path))
        assert is_valid is True
        assert error is None


class TestGetClamavPath:
    """Tests for the get_clamav_path function."""

    def test_get_clamav_path_found(self):
        """Test get_clamav_path returns path when clamscan is found."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamscan"):
            path = get_clamav_path()
            assert path == "/usr/bin/clamscan"

    def test_get_clamav_path_not_found(self):
        """Test get_clamav_path returns None when clamscan is not found."""
        with mock.patch("shutil.which", return_value=None):
            path = get_clamav_path()
            assert path is None


class TestGetFreshclamPath:
    """Tests for the get_freshclam_path function."""

    def test_get_freshclam_path_found(self):
        """Test get_freshclam_path returns path when freshclam is found."""
        with mock.patch("shutil.which", return_value="/usr/bin/freshclam"):
            path = get_freshclam_path()
            assert path == "/usr/bin/freshclam"

    def test_get_freshclam_path_not_found(self):
        """Test get_freshclam_path returns None when freshclam is not found."""
        with mock.patch("shutil.which", return_value=None):
            path = get_freshclam_path()
            assert path is None


class TestFormatScanPath:
    """Tests for the format_scan_path function."""

    def test_format_scan_path_empty(self):
        """Test format_scan_path handles empty path."""
        result = format_scan_path("")
        assert "no path" in result.lower()

    def test_format_scan_path_none(self):
        """Test format_scan_path handles None path."""
        result = format_scan_path(None)
        assert "no path" in result.lower()

    def test_format_scan_path_absolute(self, tmp_path):
        """Test format_scan_path handles absolute path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        result = format_scan_path(str(test_file))
        # Should return a valid path string
        assert str(tmp_path) in result or "~" in result


class TestGetPathInfo:
    """Tests for the get_path_info function."""

    def test_get_path_info_empty(self):
        """Test get_path_info handles empty path."""
        info = get_path_info("")
        assert info["type"] == "unknown"
        assert info["exists"] is False
        assert info["readable"] is False

    def test_get_path_info_nonexistent(self):
        """Test get_path_info handles non-existent path."""
        info = get_path_info("/nonexistent/path/that/does/not/exist")
        assert info["exists"] is False

    def test_get_path_info_existing_file(self, tmp_path):
        """Test get_path_info returns correct info for existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        info = get_path_info(str(test_file))
        assert info["type"] == "file"
        assert info["exists"] is True
        assert info["readable"] is True
        assert info["size"] == len("test content")

    def test_get_path_info_existing_directory(self, tmp_path):
        """Test get_path_info returns correct info for existing directory."""
        info = get_path_info(str(tmp_path))
        assert info["type"] == "directory"
        assert info["exists"] is True
        assert info["readable"] is True
        assert info["size"] is None


class TestValidateDroppedFiles:
    """Tests for the validate_dropped_files function."""

    def test_validate_dropped_files_empty_list(self):
        """Test validate_dropped_files returns error for empty list."""
        valid_paths, errors = validate_dropped_files([])
        assert valid_paths == []
        assert len(errors) == 1
        assert "no files" in errors[0].lower()

    def test_validate_dropped_files_valid_file(self, tmp_path):
        """Test validate_dropped_files returns valid path for existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        valid_paths, errors = validate_dropped_files([str(test_file)])
        assert len(valid_paths) == 1
        assert str(test_file.resolve()) in valid_paths[0]
        assert errors == []

    def test_validate_dropped_files_valid_directory(self, tmp_path):
        """Test validate_dropped_files returns valid path for existing directory."""
        valid_paths, errors = validate_dropped_files([str(tmp_path)])
        assert len(valid_paths) == 1
        assert str(tmp_path.resolve()) in valid_paths[0]
        assert errors == []

    def test_validate_dropped_files_multiple_valid(self, tmp_path):
        """Test validate_dropped_files handles multiple valid paths."""
        file1 = tmp_path / "test1.txt"
        file1.write_text("content 1")
        file2 = tmp_path / "test2.txt"
        file2.write_text("content 2")
        valid_paths, errors = validate_dropped_files([str(file1), str(file2)])
        assert len(valid_paths) == 2
        assert errors == []

    def test_validate_dropped_files_none_path_remote(self):
        """Test validate_dropped_files handles None paths (remote files)."""
        valid_paths, errors = validate_dropped_files([None])
        assert valid_paths == []
        assert len(errors) == 1
        assert "remote" in errors[0].lower()

    def test_validate_dropped_files_multiple_none_paths(self):
        """Test validate_dropped_files handles multiple None paths."""
        valid_paths, errors = validate_dropped_files([None, None])
        assert valid_paths == []
        assert len(errors) == 2
        assert all("remote" in error.lower() for error in errors)

    def test_validate_dropped_files_mixed_none_and_valid(self, tmp_path):
        """Test validate_dropped_files handles mixed None and valid paths."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        valid_paths, errors = validate_dropped_files([None, str(test_file)])
        assert len(valid_paths) == 1
        assert len(errors) == 1
        assert "remote" in errors[0].lower()

    def test_validate_dropped_files_nonexistent_path(self):
        """Test validate_dropped_files handles non-existent paths."""
        valid_paths, errors = validate_dropped_files(["/nonexistent/path/that/does/not/exist"])
        assert valid_paths == []
        assert len(errors) == 1
        assert "does not exist" in errors[0].lower()

    def test_validate_dropped_files_mixed_valid_and_invalid(self, tmp_path):
        """Test validate_dropped_files handles mix of valid and invalid paths."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        valid_paths, errors = validate_dropped_files([str(test_file), "/nonexistent/path", None])
        assert len(valid_paths) == 1
        assert len(errors) == 2

    def test_validate_dropped_files_permission_denied(self, tmp_path):
        """Test validate_dropped_files handles permission errors."""
        import stat

        # Create a file and remove read permissions
        test_file = tmp_path / "unreadable.txt"
        test_file.write_text("test content")

        # Remove read permissions
        original_mode = test_file.stat().st_mode
        test_file.chmod(stat.S_IWUSR)  # Write-only

        try:
            valid_paths, errors = validate_dropped_files([str(test_file)])
            assert valid_paths == []
            assert len(errors) == 1
            assert "permission" in errors[0].lower()
        finally:
            # Restore permissions for cleanup
            test_file.chmod(original_mode)

    def test_validate_dropped_files_unreadable_directory(self, tmp_path):
        """Test validate_dropped_files handles unreadable directories."""
        import stat

        # Create a directory and remove read permissions
        test_dir = tmp_path / "unreadable_dir"
        test_dir.mkdir()

        # Remove read permissions
        original_mode = test_dir.stat().st_mode
        test_dir.chmod(stat.S_IWUSR | stat.S_IXUSR)  # Write+Execute only

        try:
            valid_paths, errors = validate_dropped_files([str(test_dir)])
            assert valid_paths == []
            assert len(errors) == 1
            assert "permission" in errors[0].lower()
        finally:
            # Restore permissions for cleanup
            test_dir.chmod(original_mode)


class TestClassifyThreatSeverity:
    """Tests for the classify_threat_severity function."""

    def test_classify_threat_severity_critical_ransomware(self):
        """Test CRITICAL severity for ransomware threats."""
        assert classify_threat_severity("Win.Ransomware.Locky") == ThreatSeverity.CRITICAL
        assert classify_threat_severity("Ransom.WannaCry") == ThreatSeverity.CRITICAL
        assert classify_threat_severity("Win.Ransom.Cerber") == ThreatSeverity.CRITICAL

    def test_classify_threat_severity_critical_rootkit(self):
        """Test CRITICAL severity for rootkit threats."""
        assert classify_threat_severity("Win.Rootkit.Agent") == ThreatSeverity.CRITICAL
        assert classify_threat_severity("Unix.Rootkit.Kaiten") == ThreatSeverity.CRITICAL

    def test_classify_threat_severity_critical_bootkit(self):
        """Test CRITICAL severity for bootkit threats."""
        assert classify_threat_severity("Win.Bootkit.Rovnix") == ThreatSeverity.CRITICAL

    def test_classify_threat_severity_critical_cryptolocker(self):
        """Test CRITICAL severity for CryptoLocker variants."""
        assert classify_threat_severity("Win.Trojan.CryptoLocker") == ThreatSeverity.CRITICAL

    def test_classify_threat_severity_critical_wannacry(self):
        """Test CRITICAL severity for WannaCry."""
        assert classify_threat_severity("WannaCry.Ransomware") == ThreatSeverity.CRITICAL

    def test_classify_threat_severity_high_trojan(self):
        """Test HIGH severity for trojan threats."""
        assert classify_threat_severity("Win.Trojan.Agent") == ThreatSeverity.HIGH
        assert classify_threat_severity("Trojan.Generic") == ThreatSeverity.HIGH
        assert classify_threat_severity("Win.Trojan.Downloader") == ThreatSeverity.HIGH

    def test_classify_threat_severity_high_worm(self):
        """Test HIGH severity for worm threats."""
        assert classify_threat_severity("Win.Worm.Conficker") == ThreatSeverity.HIGH
        assert classify_threat_severity("Worm.Blaster") == ThreatSeverity.HIGH

    def test_classify_threat_severity_high_backdoor(self):
        """Test HIGH severity for backdoor threats."""
        assert classify_threat_severity("Win.Backdoor.Poison") == ThreatSeverity.HIGH
        assert classify_threat_severity("Backdoor.Trojan") == ThreatSeverity.HIGH

    def test_classify_threat_severity_high_exploit(self):
        """Test HIGH severity for exploit threats."""
        assert classify_threat_severity("Exploit.PDF.CVE-2023-1234") == ThreatSeverity.HIGH
        assert classify_threat_severity("Win.Exploit.Agent") == ThreatSeverity.HIGH

    def test_classify_threat_severity_high_downloader(self):
        """Test HIGH severity for downloader threats."""
        assert classify_threat_severity("Win.Downloader.Agent") == ThreatSeverity.HIGH

    def test_classify_threat_severity_high_dropper(self):
        """Test HIGH severity for dropper threats."""
        assert classify_threat_severity("Win.Dropper.Agent") == ThreatSeverity.HIGH

    def test_classify_threat_severity_high_keylogger(self):
        """Test HIGH severity for keylogger threats."""
        assert classify_threat_severity("Win.Keylogger.Agent") == ThreatSeverity.HIGH

    def test_classify_threat_severity_medium_adware(self):
        """Test MEDIUM severity for adware threats."""
        assert classify_threat_severity("PUA.Win.Adware.Agent") == ThreatSeverity.MEDIUM
        assert classify_threat_severity("Adware.Generic") == ThreatSeverity.MEDIUM

    def test_classify_threat_severity_medium_pua(self):
        """Test MEDIUM severity for PUA/PUP threats."""
        assert classify_threat_severity("PUA.Win.Tool.Agent") == ThreatSeverity.MEDIUM
        assert classify_threat_severity("PUP.Optional.Agent") == ThreatSeverity.MEDIUM

    def test_classify_threat_severity_medium_spyware(self):
        """Test MEDIUM severity for spyware threats."""
        assert classify_threat_severity("Win.Spyware.Agent") == ThreatSeverity.MEDIUM

    def test_classify_threat_severity_medium_miner(self):
        """Test MEDIUM severity for crypto miner threats."""
        assert classify_threat_severity("CoinMiner.Generic") == ThreatSeverity.MEDIUM
        assert classify_threat_severity("Win.Miner.Agent") == ThreatSeverity.MEDIUM

    def test_classify_threat_severity_low_eicar(self):
        """Test LOW severity for EICAR test file."""
        assert classify_threat_severity("Eicar-Test-Signature") == ThreatSeverity.LOW
        assert classify_threat_severity("EICAR_Test") == ThreatSeverity.LOW

    def test_classify_threat_severity_low_test_signature(self):
        """Test LOW severity for test signatures."""
        assert classify_threat_severity("Test-Signature") == ThreatSeverity.LOW
        assert classify_threat_severity("ClamAV-Test-Signature") == ThreatSeverity.LOW

    def test_classify_threat_severity_low_test_file(self):
        """Test LOW severity for test files."""
        assert classify_threat_severity("Test.File.Virus") == ThreatSeverity.LOW

    def test_classify_threat_severity_low_heuristic(self):
        """Test LOW severity for heuristic detections."""
        assert classify_threat_severity("Heuristic.Suspicious") == ThreatSeverity.LOW
        assert classify_threat_severity("Win.Heuristic.Agent") == ThreatSeverity.LOW

    def test_classify_threat_severity_low_generic(self):
        """Test LOW severity for generic detections."""
        assert classify_threat_severity("Generic.Malware") == ThreatSeverity.LOW
        assert classify_threat_severity("Win.Generic.Agent") == ThreatSeverity.LOW

    def test_classify_threat_severity_default_unknown(self):
        """Test default MEDIUM severity for unknown threats."""
        assert classify_threat_severity("Unknown.Malware.Type") == ThreatSeverity.MEDIUM
        assert classify_threat_severity("Win.Virus.Agent") == ThreatSeverity.MEDIUM
        assert classify_threat_severity("Some.Random.Threat") == ThreatSeverity.MEDIUM

    def test_classify_threat_severity_empty_string(self):
        """Test MEDIUM severity for empty string."""
        assert classify_threat_severity("") == ThreatSeverity.MEDIUM

    def test_classify_threat_severity_none(self):
        """Test MEDIUM severity for None input."""
        assert classify_threat_severity(None) == ThreatSeverity.MEDIUM

    def test_classify_threat_severity_case_insensitive(self):
        """Test case-insensitive matching."""
        assert classify_threat_severity("RANSOMWARE") == ThreatSeverity.CRITICAL
        assert classify_threat_severity("Trojan") == ThreatSeverity.HIGH
        assert classify_threat_severity("ADWARE") == ThreatSeverity.MEDIUM
        assert classify_threat_severity("EICAR") == ThreatSeverity.LOW

    def test_classify_threat_severity_priority_critical_over_high(self):
        """Test that CRITICAL patterns take priority over HIGH patterns."""
        # CryptoLocker contains "Trojan" which is HIGH, but CryptoLocker is CRITICAL
        # Since we check critical first, this should be CRITICAL
        assert classify_threat_severity("Win.Trojan.CryptoLocker") == ThreatSeverity.CRITICAL

    def test_classify_threat_severity_real_world_threats(self):
        """Test with real-world threat names from ClamAV."""
        # Critical
        assert (
            classify_threat_severity("Win.Ransomware.WannaCry-9952423-0") == ThreatSeverity.CRITICAL
        )

        # High
        assert classify_threat_severity("Win.Trojan.Emotet-9953123-0") == ThreatSeverity.HIGH
        assert classify_threat_severity("Unix.Worm.Mirai-123456") == ThreatSeverity.HIGH

        # Medium
        assert classify_threat_severity("PUA.Win.Adware.OpenCandy-1234") == ThreatSeverity.MEDIUM

        # Low
        assert classify_threat_severity("Eicar-Test-Signature") == ThreatSeverity.LOW


class TestCategorizeThreat:
    """Tests for the categorize_threat function."""

    def test_categorize_threat_ransomware(self):
        """Test Ransomware category extraction."""
        assert categorize_threat("Win.Ransomware.Locky") == "Ransomware"
        assert categorize_threat("Ransom.WannaCry") == "Ransomware"
        assert categorize_threat("Win.Ransom.Cerber") == "Ransomware"

    def test_categorize_threat_rootkit(self):
        """Test Rootkit category extraction."""
        assert categorize_threat("Win.Rootkit.Agent") == "Rootkit"
        assert categorize_threat("Unix.Rootkit.Kaiten") == "Rootkit"
        assert categorize_threat("Win.Bootkit.Rovnix") == "Rootkit"

    def test_categorize_threat_trojan(self):
        """Test Trojan category extraction."""
        assert categorize_threat("Win.Trojan.Agent") == "Trojan"
        assert categorize_threat("Trojan.Generic") == "Trojan"
        assert categorize_threat("Win.Trojan.Downloader") == "Trojan"

    def test_categorize_threat_worm(self):
        """Test Worm category extraction."""
        assert categorize_threat("Win.Worm.Conficker") == "Worm"
        assert categorize_threat("Worm.Mydoom") == "Worm"
        assert categorize_threat("Worm.Blaster") == "Worm"

    def test_categorize_threat_backdoor(self):
        """Test Backdoor category extraction."""
        assert categorize_threat("Win.Backdoor.Poison") == "Backdoor"
        assert categorize_threat("Backdoor.IRC") == "Backdoor"
        assert categorize_threat("Backdoor.Trojan") == "Backdoor"

    def test_categorize_threat_exploit(self):
        """Test Exploit category extraction."""
        assert categorize_threat("Exploit.PDF.CVE-2023-1234") == "Exploit"
        assert categorize_threat("Win.Exploit.Agent") == "Exploit"
        assert categorize_threat("Exploit.Java") == "Exploit"

    def test_categorize_threat_adware(self):
        """Test Adware category extraction."""
        assert categorize_threat("PUA.Win.Adware.Agent") == "Adware"
        assert categorize_threat("Adware.Generic") == "Adware"
        assert categorize_threat("Win.Adware.OpenCandy") == "Adware"

    def test_categorize_threat_spyware(self):
        """Test Spyware category extraction."""
        assert categorize_threat("Win.Spyware.Agent") == "Spyware"
        assert categorize_threat("Spyware.Generic") == "Spyware"
        assert categorize_threat("Win.Keylogger.Agent") == "Spyware"

    def test_categorize_threat_pua(self):
        """Test PUA category extraction."""
        assert categorize_threat("PUA.Win.Tool.Agent") == "PUA"
        assert categorize_threat("PUP.Optional.Agent") == "PUA"
        assert categorize_threat("Win.PUA.Generic") == "PUA"

    def test_categorize_threat_test(self):
        """Test Test category extraction for EICAR and test signatures."""
        assert categorize_threat("Eicar-Test-Signature") == "Test"
        assert categorize_threat("EICAR_Test") == "Test"
        assert categorize_threat("ClamAV-Test-Signature") == "Test"
        assert categorize_threat("Test.File.Virus") == "Test"

    def test_categorize_threat_virus(self):
        """Test Virus category extraction."""
        assert categorize_threat("Win.Virus.Agent") == "Virus"
        assert categorize_threat("Virus.Generic") == "Virus"

    def test_categorize_threat_macro(self):
        """Test Macro category extraction."""
        assert categorize_threat("Win.Macro.Agent") == "Macro"
        assert categorize_threat("Macro.Generic") == "Macro"
        assert categorize_threat("Doc.Macro.Dropper") == "Macro"

    def test_categorize_threat_phishing(self):
        """Test Phishing category extraction."""
        assert categorize_threat("Phishing.Email") == "Phishing"
        assert categorize_threat("Phish.Bank.Generic") == "Phishing"
        assert categorize_threat("Win.Phishing.PayPal") == "Phishing"

    def test_categorize_threat_heuristic(self):
        """Test Heuristic category extraction."""
        assert categorize_threat("Heuristic.Suspicious") == "Heuristic"
        assert categorize_threat("Win.Heuristic.Agent") == "Heuristic"

    def test_categorize_threat_empty_string(self):
        """Test Unknown category for empty string."""
        assert categorize_threat("") == "Unknown"

    def test_categorize_threat_none(self):
        """Test Unknown category for None input."""
        assert categorize_threat(None) == "Unknown"

    def test_categorize_threat_default_to_virus(self):
        """Test default Virus category for unrecognized threats."""
        assert categorize_threat("Unknown.Malware") == "Virus"
        assert categorize_threat("Some.Random.Threat") == "Virus"
        assert categorize_threat("Win.Agent.Generic") == "Virus"

    def test_categorize_threat_case_insensitive(self):
        """Test case-insensitive matching."""
        assert categorize_threat("RANSOMWARE") == "Ransomware"
        assert categorize_threat("TROJAN") == "Trojan"
        assert categorize_threat("worm") == "Worm"
        assert categorize_threat("EICAR") == "Test"

    def test_categorize_threat_priority_order(self):
        """Test that more specific patterns take priority."""
        # Ransomware should take priority over generic patterns
        assert categorize_threat("Win.Ransomware.Trojan") == "Ransomware"
        # Rootkit should take priority over trojan
        assert categorize_threat("Win.Rootkit.Trojan") == "Rootkit"
        # Backdoor in name takes priority when listed first
        assert categorize_threat("Win.Trojan.Backdoor") == "Trojan"

    def test_categorize_threat_real_world_threats(self):
        """Test with real-world threat names from ClamAV."""
        # Ransomware
        assert categorize_threat("Win.Ransomware.WannaCry-9952423-0") == "Ransomware"

        # Trojan
        assert categorize_threat("Win.Trojan.Emotet-9953123-0") == "Trojan"

        # Worm
        assert categorize_threat("Unix.Worm.Mirai-123456") == "Worm"

        # Adware
        assert categorize_threat("PUA.Win.Adware.OpenCandy-1234") == "Adware"

        # Test
        assert categorize_threat("Eicar-Test-Signature") == "Test"


class TestFormatResultsAsText:
    """Tests for the format_results_as_text function."""

    def _create_scan_result(
        self,
        status: ScanStatus = ScanStatus.CLEAN,
        path: str = "/home/user/test",
        scanned_files: int = 100,
        scanned_dirs: int = 10,
        infected_count: int = 0,
        threat_details: list = None,
        error_message: str = None,
    ) -> ScanResult:
        """Helper method to create a ScanResult for testing."""
        return ScanResult(
            status=status,
            path=path,
            stdout="",
            stderr="",
            exit_code=0 if status == ScanStatus.CLEAN else 1,
            infected_files=[t.file_path for t in (threat_details or [])],
            scanned_files=scanned_files,
            scanned_dirs=scanned_dirs,
            infected_count=infected_count,
            error_message=error_message,
            threat_details=threat_details or [],
        )

    def test_format_results_as_text_clean_scan(self):
        """Test formatting a clean scan result."""
        result = self._create_scan_result(
            status=ScanStatus.CLEAN,
            path="/home/user/Documents",
            scanned_files=150,
            scanned_dirs=25,
        )

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        assert "ClamUI Scan Report" in text
        assert "2024-01-15 14:30:45" in text
        assert "/home/user/Documents" in text
        assert "Status: CLEAN" in text
        assert "Files Scanned: 150" in text
        assert "Directories Scanned: 25" in text
        assert "Threats Found: 0" in text
        assert "No Threats Detected" in text
        assert "All scanned files are clean" in text

    def test_format_results_as_text_with_threats(self):
        """Test formatting a scan result with detected threats."""
        threat_details = [
            ThreatDetail(
                file_path="/home/user/Downloads/malware.exe",
                threat_name="Win.Ransomware.Locky",
                category="Ransomware",
                severity="critical",
            ),
            ThreatDetail(
                file_path="/home/user/Downloads/suspicious.doc",
                threat_name="Win.Trojan.Agent",
                category="Trojan",
                severity="high",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            path="/home/user/Downloads",
            scanned_files=200,
            scanned_dirs=30,
            infected_count=2,
            threat_details=threat_details,
        )

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        assert "ClamUI Scan Report" in text
        assert "Status: INFECTED" in text
        assert "Threats Found: 2" in text
        assert "Detected Threats" in text
        assert "[1] CRITICAL - Ransomware" in text
        assert "File: /home/user/Downloads/malware.exe" in text
        assert "Threat: Win.Ransomware.Locky" in text
        assert "[2] HIGH - Trojan" in text
        assert "File: /home/user/Downloads/suspicious.doc" in text
        assert "Threat: Win.Trojan.Agent" in text

    def test_format_results_as_text_error_status(self):
        """Test formatting an error scan result."""
        result = self._create_scan_result(
            status=ScanStatus.ERROR,
            path="/home/user/restricted",
            scanned_files=0,
            scanned_dirs=0,
            error_message="Permission denied: Cannot access directory",
        )

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        assert "ClamUI Scan Report" in text
        assert "Status: ERROR" in text
        assert "Scan Error" in text
        assert "Error: Permission denied: Cannot access directory" in text

    def test_format_results_as_text_cancelled_status(self):
        """Test formatting a cancelled scan result."""
        result = self._create_scan_result(
            status=ScanStatus.CANCELLED,
            path="/home/user/large_directory",
            scanned_files=50,
            scanned_dirs=5,
        )

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        assert "ClamUI Scan Report" in text
        assert "Status: CANCELLED" in text
        assert "Scan Cancelled" in text
        assert "scan was cancelled before completion" in text

    def test_format_results_as_text_auto_timestamp(self):
        """Test that timestamp is auto-generated when not provided."""
        result = self._create_scan_result()

        text = format_results_as_text(result)

        assert "ClamUI Scan Report" in text
        assert "Scan Date:" in text
        # Should contain a date-like string
        assert "20" in text  # Year starting with 20xx

    def test_format_results_as_text_header_and_footer(self):
        """Test that the output has proper header and footer lines."""
        result = self._create_scan_result()

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        lines = text.split("\n")
        # First line should be the header border
        assert lines[0].startswith("═")
        # Last line should be the footer border
        assert lines[-1].startswith("═")

    def test_format_results_as_text_multiple_threats_numbered(self):
        """Test that multiple threats are numbered correctly."""
        threat_details = [
            ThreatDetail(
                file_path=f"/path/to/file{i}.exe",
                threat_name=f"Win.Trojan.Agent{i}",
                category="Trojan",
                severity="high",
            )
            for i in range(1, 6)
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=5,
            threat_details=threat_details,
        )

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        assert "[1] HIGH - Trojan" in text
        assert "[2] HIGH - Trojan" in text
        assert "[3] HIGH - Trojan" in text
        assert "[4] HIGH - Trojan" in text
        assert "[5] HIGH - Trojan" in text

    def test_format_results_as_text_severity_levels(self):
        """Test that all severity levels are formatted correctly."""
        threat_details = [
            ThreatDetail(
                file_path="/path/critical.exe",
                threat_name="Win.Ransomware.Test",
                category="Ransomware",
                severity="critical",
            ),
            ThreatDetail(
                file_path="/path/high.exe",
                threat_name="Win.Trojan.Test",
                category="Trojan",
                severity="high",
            ),
            ThreatDetail(
                file_path="/path/medium.exe",
                threat_name="PUA.Adware.Test",
                category="Adware",
                severity="medium",
            ),
            ThreatDetail(
                file_path="/path/low.exe",
                threat_name="Eicar-Test",
                category="Test",
                severity="low",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=4,
            threat_details=threat_details,
        )

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        assert "CRITICAL - Ransomware" in text
        assert "HIGH - Trojan" in text
        assert "MEDIUM - Adware" in text
        assert "LOW - Test" in text

    def test_format_results_as_text_special_characters_in_path(self):
        """Test that special characters in paths are handled correctly."""
        result = self._create_scan_result(
            status=ScanStatus.CLEAN,
            path="/home/user/My Documents (2024)/test folder",
        )

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        assert "/home/user/My Documents (2024)/test folder" in text

    def test_format_results_as_text_empty_threat_details_infected(self):
        """Test infected status with empty threat_details (edge case)."""
        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=1,
            threat_details=[],  # Empty but infected_count > 0
        )

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        assert "Status: INFECTED" in text
        assert "Threats Found: 1" in text
        # Should not have "Detected Threats" section since threat_details is empty
        assert "Detected Threats" not in text

    def test_format_results_as_text_long_threat_name(self):
        """Test that long threat names are handled correctly."""
        long_threat_name = "Win.Trojan.VeryLongThreatNameThatExceedsNormalLength-123456789-0"
        threat_details = [
            ThreatDetail(
                file_path="/path/to/file.exe",
                threat_name=long_threat_name,
                category="Trojan",
                severity="high",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=1,
            threat_details=threat_details,
        )

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        assert long_threat_name in text

    def test_format_results_as_text_unicode_in_path(self):
        """Test that unicode characters in paths are handled correctly."""
        result = self._create_scan_result(
            status=ScanStatus.CLEAN,
            path="/home/user/文档/テスト/résumé.pdf",
        )

        text = format_results_as_text(result, timestamp="2024-01-15 14:30:45")

        assert "/home/user/文档/テスト/résumé.pdf" in text


class TestFormatResultsAsCsv:
    """Tests for the format_results_as_csv function."""

    def _create_scan_result(
        self,
        status: ScanStatus = ScanStatus.CLEAN,
        path: str = "/home/user/test",
        scanned_files: int = 100,
        scanned_dirs: int = 10,
        infected_count: int = 0,
        threat_details: list = None,
        error_message: str = None,
    ) -> ScanResult:
        """Helper method to create a ScanResult for testing."""
        return ScanResult(
            status=status,
            path=path,
            stdout="",
            stderr="",
            exit_code=0 if status == ScanStatus.CLEAN else 1,
            infected_files=[t.file_path for t in (threat_details or [])],
            scanned_files=scanned_files,
            scanned_dirs=scanned_dirs,
            infected_count=infected_count,
            error_message=error_message,
            threat_details=threat_details or [],
        )

    def test_format_results_as_csv_header_row(self):
        """Test that CSV output contains proper header row."""
        result = self._create_scan_result()

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")
        lines = csv_output.strip().split("\n")

        assert lines[0] == "File Path,Threat Name,Category,Severity,Timestamp"

    def test_format_results_as_csv_clean_scan(self):
        """Test formatting a clean scan result - only header row."""
        result = self._create_scan_result(
            status=ScanStatus.CLEAN,
            path="/home/user/Documents",
            scanned_files=150,
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")
        lines = csv_output.strip().split("\n")

        # Should only have header row for clean scan
        assert len(lines) == 1
        assert "File Path,Threat Name,Category,Severity,Timestamp" in lines[0]

    def test_format_results_as_csv_with_threats(self):
        """Test formatting a scan result with detected threats."""
        threat_details = [
            ThreatDetail(
                file_path="/home/user/Downloads/malware.exe",
                threat_name="Win.Ransomware.Locky",
                category="Ransomware",
                severity="critical",
            ),
            ThreatDetail(
                file_path="/home/user/Downloads/suspicious.doc",
                threat_name="Win.Trojan.Agent",
                category="Trojan",
                severity="high",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=2,
            threat_details=threat_details,
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")
        lines = csv_output.strip().split("\n")

        # Header + 2 threat rows
        assert len(lines) == 3
        assert "File Path,Threat Name,Category,Severity,Timestamp" in lines[0]
        assert "/home/user/Downloads/malware.exe" in lines[1]
        assert "Win.Ransomware.Locky" in lines[1]
        assert "Ransomware" in lines[1]
        assert "critical" in lines[1]
        assert "2024-01-15 14:30:45" in lines[1]
        assert "/home/user/Downloads/suspicious.doc" in lines[2]
        assert "Win.Trojan.Agent" in lines[2]

    def test_format_results_as_csv_auto_timestamp(self):
        """Test that timestamp is auto-generated when not provided."""
        threat_details = [
            ThreatDetail(
                file_path="/path/to/file.exe",
                threat_name="Test.Threat",
                category="Test",
                severity="low",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=1,
            threat_details=threat_details,
        )

        csv_output = format_results_as_csv(result)  # No timestamp provided
        lines = csv_output.strip().split("\n")

        # Should have a timestamp containing current year
        assert len(lines) == 2
        # Should contain a date-like string (20xx)
        assert "20" in lines[1]

    def test_format_results_as_csv_special_characters_in_path(self):
        """Test that special characters in paths are properly escaped."""
        threat_details = [
            ThreatDetail(
                file_path='/home/user/My Documents, Files/test "file".exe',
                threat_name="Win.Trojan.Agent",
                category="Trojan",
                severity="high",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=1,
            threat_details=threat_details,
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")

        # Parse using csv module to verify proper escaping
        import csv
        import io

        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 2
        # CSV module should properly handle commas and quotes
        assert rows[1][0] == '/home/user/My Documents, Files/test "file".exe'
        assert rows[1][1] == "Win.Trojan.Agent"

    def test_format_results_as_csv_unicode_in_path(self):
        """Test that unicode characters in paths are handled correctly."""
        threat_details = [
            ThreatDetail(
                file_path="/home/user/文档/テスト/résumé.exe",
                threat_name="Win.Virus.Unicode",
                category="Virus",
                severity="medium",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=1,
            threat_details=threat_details,
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")

        # Parse and verify unicode is preserved
        import csv
        import io

        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 2
        assert rows[1][0] == "/home/user/文档/テスト/résumé.exe"

    def test_format_results_as_csv_multiple_threats(self):
        """Test formatting with many threats."""
        threat_details = [
            ThreatDetail(
                file_path=f"/path/to/file{i}.exe",
                threat_name=f"Win.Trojan.Agent{i}",
                category="Trojan",
                severity="high",
            )
            for i in range(1, 6)
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=5,
            threat_details=threat_details,
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")
        lines = csv_output.strip().split("\n")

        # Header + 5 threat rows
        assert len(lines) == 6

    def test_format_results_as_csv_all_severity_levels(self):
        """Test that all severity levels are included correctly."""
        threat_details = [
            ThreatDetail(
                file_path="/path/critical.exe",
                threat_name="Win.Ransomware.Test",
                category="Ransomware",
                severity="critical",
            ),
            ThreatDetail(
                file_path="/path/high.exe",
                threat_name="Win.Trojan.Test",
                category="Trojan",
                severity="high",
            ),
            ThreatDetail(
                file_path="/path/medium.exe",
                threat_name="PUA.Adware.Test",
                category="Adware",
                severity="medium",
            ),
            ThreatDetail(
                file_path="/path/low.exe",
                threat_name="Eicar-Test",
                category="Test",
                severity="low",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=4,
            threat_details=threat_details,
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")

        assert "critical" in csv_output
        assert "high" in csv_output
        assert "medium" in csv_output
        assert "low" in csv_output

    def test_format_results_as_csv_valid_csv_format(self):
        """Test that output is valid CSV parseable by csv module."""
        threat_details = [
            ThreatDetail(
                file_path="/home/user/file.exe",
                threat_name="Win.Trojan.Agent",
                category="Trojan",
                severity="high",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=1,
            threat_details=threat_details,
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")

        # Verify it can be parsed back with csv module
        import csv
        import io

        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        # Should have header and one data row
        assert len(rows) == 2
        # Header should have 5 columns
        assert len(rows[0]) == 5
        assert rows[0] == ["File Path", "Threat Name", "Category", "Severity", "Timestamp"]
        # Data row should have 5 columns
        assert len(rows[1]) == 5

    def test_format_results_as_csv_error_status(self):
        """Test formatting an error scan result - only header row."""
        result = self._create_scan_result(
            status=ScanStatus.ERROR,
            path="/home/user/restricted",
            error_message="Permission denied",
            threat_details=[],
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")
        lines = csv_output.strip().split("\n")

        # Should only have header row for error scan (no threats)
        assert len(lines) == 1

    def test_format_results_as_csv_cancelled_status(self):
        """Test formatting a cancelled scan result - only header row."""
        result = self._create_scan_result(
            status=ScanStatus.CANCELLED,
            path="/home/user/large_directory",
            threat_details=[],
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")
        lines = csv_output.strip().split("\n")

        # Should only have header row for cancelled scan (no threats)
        assert len(lines) == 1

    def test_format_results_as_csv_long_threat_name(self):
        """Test that long threat names are handled correctly."""
        long_threat_name = "Win.Trojan.VeryLongThreatNameThatExceedsNormalLength-123456789-0"
        threat_details = [
            ThreatDetail(
                file_path="/path/to/file.exe",
                threat_name=long_threat_name,
                category="Trojan",
                severity="high",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=1,
            threat_details=threat_details,
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")

        # Parse to verify long name is preserved
        import csv
        import io

        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        assert rows[1][1] == long_threat_name

    def test_format_results_as_csv_newline_in_path(self):
        """Test that newline characters in paths are properly escaped."""
        threat_details = [
            ThreatDetail(
                file_path="/home/user/line1\nline2/file.exe",
                threat_name="Win.Trojan.Agent",
                category="Trojan",
                severity="high",
            ),
        ]

        result = self._create_scan_result(
            status=ScanStatus.INFECTED,
            infected_count=1,
            threat_details=threat_details,
        )

        csv_output = format_results_as_csv(result, timestamp="2024-01-15 14:30:45")

        # Parse to verify newline is properly escaped in CSV
        import csv
        import io

        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 2
        # The newline should be preserved in the parsed value
        assert "\n" in rows[1][0]
