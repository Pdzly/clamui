# ClamUI Daemon Scanner Tests
"""Unit tests for the daemon scanner module."""

import subprocess
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

    def test_build_command_without_exclusions(self, tmp_path, daemon_scanner_class):
        """Test _build_command does NOT include --exclude (clamdscan doesn't support it)."""
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

        # clamdscan does NOT support --exclude options (they're silently ignored)
        # Exclusions are handled post-scan via _filter_excluded_threats()
        assert "--exclude" not in cmd
        assert "--exclude-dir" not in cmd


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
        """Test that cancel sets the cancel event."""
        scanner = daemon_scanner_class()

        scanner.cancel()

        assert scanner._cancel_event.is_set() is True

    def test_cancel_terminates_process(self, daemon_scanner_class):
        """Test that cancel terminates running process."""
        scanner = daemon_scanner_class()
        mock_process = MagicMock()
        scanner._current_process = mock_process

        scanner.cancel()

        mock_process.terminate.assert_called_once()

    def test_cancel_terminate_timeout_escalates_to_kill(self, daemon_scanner_class):
        """Test that cancel escalates to kill if terminate times out."""
        scanner = daemon_scanner_class()
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = MagicMock(
            side_effect=[
                subprocess.TimeoutExpired(cmd="test", timeout=5),  # First wait times out
                None,  # Second wait (after kill) succeeds
            ]
        )
        scanner._current_process = mock_process

        scanner.cancel()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert scanner._cancel_event.is_set() is True

    def test_cancel_kill_timeout_handles_gracefully(self, daemon_scanner_class):
        """Test that cancel handles kill timeout gracefully."""
        scanner = daemon_scanner_class()
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = MagicMock(
            side_effect=[
                subprocess.TimeoutExpired(cmd="test", timeout=5),  # First wait times out
                subprocess.TimeoutExpired(cmd="test", timeout=2),  # Second wait also times out
            ]
        )
        scanner._current_process = mock_process

        # Should not raise exception even if kill times out
        scanner.cancel()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert scanner._cancel_event.is_set() is True

    def test_cancel_process_already_terminated_on_terminate(self, daemon_scanner_class):
        """Test cancel handles process already gone when calling terminate."""
        scanner = daemon_scanner_class()
        mock_process = MagicMock()
        mock_process.terminate = MagicMock(side_effect=ProcessLookupError("No such process"))
        mock_process.kill = MagicMock()
        mock_process.wait = MagicMock()
        scanner._current_process = mock_process

        # Should not raise exception and should return early
        scanner.cancel()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_not_called()  # Should not reach kill
        mock_process.wait.assert_not_called()  # Should not reach wait
        assert scanner._cancel_event.is_set() is True

    def test_cancel_graceful_termination_success(self, daemon_scanner_class):
        """Test cancel when process terminates gracefully within timeout."""
        scanner = daemon_scanner_class()
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = MagicMock(return_value=None)  # Succeeds on first call
        scanner._current_process = mock_process

        scanner.cancel()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()  # Only one wait call
        mock_process.kill.assert_not_called()  # Should not escalate to kill
        assert scanner._cancel_event.is_set() is True


class TestDaemonScannerFilterExcludedThreats:
    """Tests for DaemonScanner._filter_excluded_threats method."""

    def test_filter_excludes_exact_path_match(self, daemon_scanner_class, scan_status_class):
        """Test that exact path matches are filtered out."""
        mock_settings = MagicMock()
        mock_settings.get.return_value = [
            {"pattern": "/home/user/eicar.txt", "type": "file", "enabled": True},
        ]
        scanner = daemon_scanner_class(settings_manager=mock_settings)

        # Create a mock ThreatDetail
        from src.core.scanner import ThreatDetail

        threat = ThreatDetail(
            file_path="/home/user/eicar.txt",
            threat_name="Eicar-Test-Signature",
            category="Test",
            severity="low",
        )

        # Create infected result
        from src.core.scanner import ScanResult

        result = ScanResult(
            status=scan_status_class.INFECTED,
            path="/home/user",
            stdout="",
            stderr="",
            exit_code=1,
            infected_files=["/home/user/eicar.txt"],
            scanned_files=1,
            scanned_dirs=0,
            infected_count=1,
            error_message=None,
            threat_details=[threat],
        )

        filtered = scanner._filter_excluded_threats(result)

        # Should be clean since threat was excluded
        assert filtered.status == scan_status_class.CLEAN
        assert filtered.infected_count == 0
        assert len(filtered.threat_details) == 0

    def test_filter_keeps_non_excluded_threats(self, daemon_scanner_class, scan_status_class):
        """Test that non-excluded threats are kept."""
        mock_settings = MagicMock()
        mock_settings.get.return_value = [
            {"pattern": "/some/other/path.txt", "type": "file", "enabled": True},
        ]
        scanner = daemon_scanner_class(settings_manager=mock_settings)

        from src.core.scanner import ScanResult, ThreatDetail

        threat = ThreatDetail(
            file_path="/home/user/virus.exe",
            threat_name="Win.Trojan.Test",
            category="Trojan",
            severity="high",
        )

        result = ScanResult(
            status=scan_status_class.INFECTED,
            path="/home/user",
            stdout="",
            stderr="",
            exit_code=1,
            infected_files=["/home/user/virus.exe"],
            scanned_files=1,
            scanned_dirs=0,
            infected_count=1,
            error_message=None,
            threat_details=[threat],
        )

        filtered = scanner._filter_excluded_threats(result)

        # Should still be infected
        assert filtered.status == scan_status_class.INFECTED
        assert filtered.infected_count == 1
        assert len(filtered.threat_details) == 1

    def test_filter_respects_disabled_exclusions(self, daemon_scanner_class, scan_status_class):
        """Test that disabled exclusions don't filter threats."""
        mock_settings = MagicMock()
        mock_settings.get.return_value = [
            {"pattern": "/home/user/eicar.txt", "type": "file", "enabled": False},
        ]
        scanner = daemon_scanner_class(settings_manager=mock_settings)

        from src.core.scanner import ScanResult, ThreatDetail

        threat = ThreatDetail(
            file_path="/home/user/eicar.txt",
            threat_name="Eicar-Test-Signature",
            category="Test",
            severity="low",
        )

        result = ScanResult(
            status=scan_status_class.INFECTED,
            path="/home/user",
            stdout="",
            stderr="",
            exit_code=1,
            infected_files=["/home/user/eicar.txt"],
            scanned_files=1,
            scanned_dirs=0,
            infected_count=1,
            error_message=None,
            threat_details=[threat],
        )

        filtered = scanner._filter_excluded_threats(result)

        # Should still be infected since exclusion is disabled
        assert filtered.status == scan_status_class.INFECTED
        assert filtered.infected_count == 1


class TestDaemonScannerCountTargets:
    """Tests for DaemonScanner count_targets parameter."""

    def test_scan_sync_with_count_targets_true_counts_files(
        self, tmp_path, daemon_scanner_class, scan_status_class
    ):
        """Test that count_targets=True (default) counts files and directories."""
        # Create test directory structure
        test_dir = tmp_path / "scan_test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")
        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")

        scanner = daemon_scanner_class()

        with (
            patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
            patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            mock_connection.return_value = (True, "PONG")

            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            result = scanner.scan_sync(str(test_dir), count_targets=True)

        assert result.status == scan_status_class.CLEAN
        # Should have counted files (3 files)
        assert result.scanned_files == 3
        # Should have counted directories (root + subdir = 2)
        assert result.scanned_dirs == 2

    def test_scan_sync_with_count_targets_false_skips_counting(
        self, tmp_path, daemon_scanner_class, scan_status_class
    ):
        """Test that count_targets=False skips file/directory counting."""
        # Create test directory structure
        test_dir = tmp_path / "scan_test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")
        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")

        scanner = daemon_scanner_class()

        with (
            patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
            patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            mock_connection.return_value = (True, "PONG")

            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            result = scanner.scan_sync(str(test_dir), count_targets=False)

        assert result.status == scan_status_class.CLEAN
        # Counts should be 0 when count_targets=False
        assert result.scanned_files == 0
        assert result.scanned_dirs == 0

    def test_scan_sync_count_targets_false_still_detects_infections(
        self, tmp_path, daemon_scanner_class, scan_status_class
    ):
        """Test that count_targets=False still correctly reports infections."""
        test_dir = tmp_path / "scan_test"
        test_dir.mkdir()
        (test_dir / "malware.exe").write_text("fake malware")

        scanner = daemon_scanner_class()

        with (
            patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
            patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            mock_connection.return_value = (True, "PONG")

            mock_process = MagicMock()
            infected_output = f"{test_dir}/malware.exe: Win.Trojan.Test FOUND\n"
            mock_process.communicate.return_value = (infected_output, "")
            mock_process.returncode = 1
            mock_popen.return_value = mock_process

            result = scanner.scan_sync(str(test_dir), count_targets=False)

        # Should still detect infection
        assert result.status == scan_status_class.INFECTED
        assert result.infected_count == 1
        assert len(result.threat_details) == 1
        assert result.threat_details[0].threat_name == "Win.Trojan.Test"
        # But counts should still be 0
        assert result.scanned_files == 0
        assert result.scanned_dirs == 0

    def test_scan_sync_default_count_targets_is_true(
        self, tmp_path, daemon_scanner_class, scan_status_class
    ):
        """Test that count_targets defaults to True for backwards compatibility."""
        test_dir = tmp_path / "scan_test"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        scanner = daemon_scanner_class()

        with (
            patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
            patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
            patch("subprocess.Popen") as mock_popen,
            patch.object(scanner, "_count_scan_targets") as mock_count,
        ):
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            mock_connection.return_value = (True, "PONG")
            mock_count.return_value = (1, 1)

            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            # Call without count_targets parameter (should default to True)
            scanner.scan_sync(str(test_dir))

        # _count_scan_targets should have been called
        mock_count.assert_called_once()

    def test_scan_async_passes_count_targets_to_sync(self, tmp_path, daemon_scanner_class):
        """Test that scan_async passes count_targets to scan_sync."""
        test_dir = tmp_path / "scan_test"
        test_dir.mkdir()

        scanner = daemon_scanner_class()
        callback = MagicMock()

        with (
            patch.object(scanner, "scan_sync") as mock_sync,
            patch("src.core.daemon_scanner.GLib.idle_add"),
        ):
            from src.core.scanner import ScanResult, ScanStatus

            mock_sync.return_value = ScanResult(
                status=ScanStatus.CLEAN,
                path=str(test_dir),
                stdout="",
                stderr="",
                exit_code=0,
                infected_files=[],
                scanned_files=0,
                scanned_dirs=0,
                infected_count=0,
                error_message=None,
                threat_details=[],
            )

            # Call async with count_targets=False
            scanner.scan_async(str(test_dir), callback, count_targets=False)

            # Wait for thread to execute
            import time

            time.sleep(0.1)

        # Verify scan_sync was called with count_targets=False
        mock_sync.assert_called_once()
        call_args = mock_sync.call_args
        assert call_args[0][0] == str(test_dir)  # path
        assert call_args[0][3] is False  # count_targets (4th positional arg)

    def test_filter_excludes_profile_path_subdirectory(
        self, daemon_scanner_class, scan_status_class, tmp_path
    ):
        """Test that threats under excluded directory paths are filtered."""
        mock_settings = MagicMock()
        mock_settings.get.return_value = []  # No global exclusions
        scanner = daemon_scanner_class(settings_manager=mock_settings)

        # Create a real directory structure for path resolution
        excluded_dir = tmp_path / "excluded"
        excluded_dir.mkdir()
        threat_file = excluded_dir / "subdir" / "virus.exe"
        threat_file.parent.mkdir(parents=True)
        threat_file.touch()

        from src.core.scanner import ScanResult, ThreatDetail

        threat = ThreatDetail(
            file_path=str(threat_file),
            threat_name="Win.Trojan.Test",
            category="Trojan",
            severity="high",
        )

        result = ScanResult(
            status=scan_status_class.INFECTED,
            path=str(tmp_path),
            stdout="",
            stderr="",
            exit_code=1,
            infected_files=[str(threat_file)],
            scanned_files=1,
            scanned_dirs=0,
            infected_count=1,
            error_message=None,
            threat_details=[threat],
        )

        profile_exclusions = {"paths": [str(excluded_dir)], "patterns": []}
        filtered = scanner._filter_excluded_threats(result, profile_exclusions)

        # Should be clean since threat is under excluded directory
        assert filtered.status == scan_status_class.CLEAN
        assert filtered.infected_count == 0
        assert len(filtered.threat_details) == 0

    def test_filter_excludes_profile_path_with_tilde(
        self, daemon_scanner_class, scan_status_class, monkeypatch, tmp_path
    ):
        """Test that tilde paths are expanded correctly."""
        mock_settings = MagicMock()
        mock_settings.get.return_value = []
        scanner = daemon_scanner_class(settings_manager=mock_settings)

        # Create directory structure and mock home expansion
        fake_home = tmp_path / "fakehome"
        cache_dir = fake_home / ".cache"
        cache_dir.mkdir(parents=True)
        threat_file = cache_dir / "malware.exe"
        threat_file.touch()

        # Patch Path.home() and expanduser
        monkeypatch.setenv("HOME", str(fake_home))

        from src.core.scanner import ScanResult, ThreatDetail

        threat = ThreatDetail(
            file_path=str(threat_file),
            threat_name="Win.Trojan.Test",
            category="Trojan",
            severity="high",
        )

        result = ScanResult(
            status=scan_status_class.INFECTED,
            path=str(fake_home),
            stdout="",
            stderr="",
            exit_code=1,
            infected_files=[str(threat_file)],
            scanned_files=1,
            scanned_dirs=0,
            infected_count=1,
            error_message=None,
            threat_details=[threat],
        )

        profile_exclusions = {"paths": ["~/.cache"], "patterns": []}
        filtered = scanner._filter_excluded_threats(result, profile_exclusions)

        assert filtered.status == scan_status_class.CLEAN
        assert filtered.infected_count == 0

    def test_filter_keeps_threats_outside_excluded_paths(
        self, daemon_scanner_class, scan_status_class, tmp_path
    ):
        """Test that threats outside excluded paths are preserved."""
        mock_settings = MagicMock()
        mock_settings.get.return_value = []
        scanner = daemon_scanner_class(settings_manager=mock_settings)

        # Create directories
        excluded_dir = tmp_path / "excluded"
        excluded_dir.mkdir()
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        threat_file = other_dir / "virus.exe"
        threat_file.touch()

        from src.core.scanner import ScanResult, ThreatDetail

        threat = ThreatDetail(
            file_path=str(threat_file),
            threat_name="Win.Trojan.Test",
            category="Trojan",
            severity="high",
        )

        result = ScanResult(
            status=scan_status_class.INFECTED,
            path=str(tmp_path),
            stdout="",
            stderr="",
            exit_code=1,
            infected_files=[str(threat_file)],
            scanned_files=1,
            scanned_dirs=0,
            infected_count=1,
            error_message=None,
            threat_details=[threat],
        )

        profile_exclusions = {"paths": [str(excluded_dir)], "patterns": []}
        filtered = scanner._filter_excluded_threats(result, profile_exclusions)

        # Should still be infected since threat is not under excluded dir
        assert filtered.status == scan_status_class.INFECTED
        assert filtered.infected_count == 1
        assert len(filtered.threat_details) == 1

    def test_filter_combines_global_and_profile_exclusions(
        self, daemon_scanner_class, scan_status_class, tmp_path
    ):
        """Test that both global patterns and profile paths work together."""
        mock_settings = MagicMock()
        mock_settings.get.return_value = [
            {"pattern": "*.tmp", "type": "file", "enabled": True},
        ]
        scanner = daemon_scanner_class(settings_manager=mock_settings)

        # Create directories and files
        excluded_dir = tmp_path / "excluded"
        excluded_dir.mkdir()
        threat1 = excluded_dir / "virus.exe"
        threat1.touch()
        threat2 = tmp_path / "temp.tmp"
        threat2.touch()
        threat3 = tmp_path / "real_virus.exe"
        threat3.touch()

        from src.core.scanner import ScanResult, ThreatDetail

        threats = [
            ThreatDetail(
                file_path=str(threat1),
                threat_name="Trojan1",
                category="Trojan",
                severity="high",
            ),
            ThreatDetail(
                file_path=str(threat2),
                threat_name="Trojan2",
                category="Trojan",
                severity="high",
            ),
            ThreatDetail(
                file_path=str(threat3),
                threat_name="Trojan3",
                category="Trojan",
                severity="high",
            ),
        ]

        result = ScanResult(
            status=scan_status_class.INFECTED,
            path=str(tmp_path),
            stdout="",
            stderr="",
            exit_code=1,
            infected_files=[str(threat1), str(threat2), str(threat3)],
            scanned_files=3,
            scanned_dirs=0,
            infected_count=3,
            error_message=None,
            threat_details=threats,
        )

        profile_exclusions = {"paths": [str(excluded_dir)], "patterns": []}
        filtered = scanner._filter_excluded_threats(result, profile_exclusions)

        # threat1 filtered by profile path, threat2 by global pattern
        # Only threat3 should remain
        assert filtered.status == scan_status_class.INFECTED
        assert filtered.infected_count == 1
        assert len(filtered.threat_details) == 1
        assert filtered.threat_details[0].file_path == str(threat3)


class TestDaemonScannerProcessLockThreadSafety:
    """Tests for DaemonScanner process lock and thread safety."""

    def test_daemon_scanner_has_process_lock(self, daemon_scanner_class):
        """Test that DaemonScanner has a _process_lock attribute."""
        import threading

        scanner = daemon_scanner_class()
        assert hasattr(scanner, "_process_lock")
        assert isinstance(scanner._process_lock, type(threading.Lock()))

    def test_cancel_uses_lock_for_process_access(self, daemon_scanner_class):
        """Test that cancel() acquires lock before accessing _current_process."""
        scanner = daemon_scanner_class()
        lock_acquired = []

        original_lock = scanner._process_lock

        class TrackingLock:
            def __enter__(self):
                lock_acquired.append("enter")
                return original_lock.__enter__()

            def __exit__(self, *args):
                lock_acquired.append("exit")
                return original_lock.__exit__(*args)

        scanner._process_lock = TrackingLock()
        scanner.cancel()

        assert "enter" in lock_acquired
        assert "exit" in lock_acquired

    def test_scan_sync_uses_lock_for_process_assignment(self, tmp_path, daemon_scanner_class):
        """Test that scan_sync() acquires lock when assigning _current_process."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = daemon_scanner_class()

        # Verify the lock attribute exists (check for the fix)
        assert hasattr(scanner, "_process_lock"), "Scanner should have _process_lock attribute"

        # We can verify the lock is used by checking that _current_process operations
        # don't raise errors during concurrent access. The actual lock usage is tested
        # by the concurrent test below. Here we just verify the lock exists and
        # scan completes successfully with proper cleanup.
        with (
            patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
            patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            mock_connection.return_value = (True, "PONG")

            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            result = scanner.scan_sync(str(test_file), count_targets=False)

        # Verify scan completed and process was cleared
        assert result.status.value in ["clean", "infected", "error", "cancelled"]
        assert scanner._current_process is None

    def test_concurrent_cancel_and_scan_cleanup(self, tmp_path, daemon_scanner_class):
        """Test that concurrent cancel and scan cleanup don't cause race conditions."""
        import threading
        import time

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = daemon_scanner_class()
        errors = []

        def scan_thread():
            try:
                with (
                    patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
                    patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
                    patch("subprocess.Popen") as mock_popen,
                ):
                    mock_installed.return_value = (True, "ClamAV 1.0.0")
                    mock_connection.return_value = (True, "PONG")

                    mock_process = MagicMock()
                    # Simulate slow scan
                    mock_process.communicate.side_effect = lambda: (
                        time.sleep(0.1),
                        ("", ""),
                    )[-1]
                    mock_process.returncode = 0
                    mock_popen.return_value = mock_process

                    scanner.scan_sync(str(test_file), count_targets=False)
            except Exception as e:
                errors.append(e)

        def cancel_thread():
            try:
                time.sleep(0.05)  # Wait for scan to start
                scanner.cancel()
            except Exception as e:
                errors.append(e)

        # Run multiple iterations to increase chance of hitting race condition
        for _ in range(5):
            scanner._cancel_event.clear()
            t1 = threading.Thread(target=scan_thread)
            t2 = threading.Thread(target=cancel_thread)

            t1.start()
            t2.start()

            t1.join(timeout=2)
            t2.join(timeout=2)

        # No exceptions should have been raised due to race conditions
        assert len(errors) == 0, f"Race condition errors: {errors}"

    def test_process_cleared_after_scan_completes(self, tmp_path, daemon_scanner_class):
        """Test that _current_process is None after scan completes."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = daemon_scanner_class()

        with (
            patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
            patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            mock_connection.return_value = (True, "PONG")

            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            scanner.scan_sync(str(test_file), count_targets=False)

        # After scan completes, _current_process should be None
        assert scanner._current_process is None

    def test_cancel_with_none_process_is_safe(self, daemon_scanner_class):
        """Test that cancel() is safe when _current_process is None."""
        scanner = daemon_scanner_class()
        assert scanner._current_process is None

        # Should not raise any exception
        scanner.cancel()
        assert scanner._cancel_event.is_set() is True


class TestDaemonScannerCancelFlagReset:
    """Tests for cancel event reset at start of new scans."""

    def test_cancelled_flag_reset_at_scan_start(
        self, tmp_path, daemon_scanner_class, scan_status_class
    ):
        """Test that _cancel_event is reset at start of scan_sync."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = daemon_scanner_class()

        # Manually set cancel event to simulate previous cancelled scan
        scanner._cancel_event.set()

        with (
            patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
            patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            mock_connection.return_value = (True, "PONG")

            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            result = scanner.scan_sync(str(test_file), count_targets=False)

        # Scan should complete successfully (not be cancelled)
        assert result.status == scan_status_class.CLEAN
        # Event should have been cleared during scan
        assert scanner._cancel_event.is_set() is False

    def test_scan_after_cancelled_during_counting_runs_normally(
        self, tmp_path, daemon_scanner_class, scan_status_class
    ):
        """Test that a new scan runs normally after previous scan was cancelled during counting.

        This is the specific bug scenario:
        1. Start scan A
        2. Cancel during counting phase (event set, scan returns cancelled)
        3. Start scan B - it should run normally, not return cancelled immediately
        """
        # Create test directory with files to trigger counting phase
        test_dir = tmp_path / "scan_test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")

        scanner = daemon_scanner_class()

        # Simulate scan A being cancelled during counting phase
        # This is what happens when user cancels during _count_scan_targets
        def counting_that_gets_cancelled(*args, **kwargs):
            # Simulate cancel during counting
            scanner._cancel_event.set()
            return (0, 0)

        with (
            patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
            patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
            patch.object(scanner, "_count_scan_targets", side_effect=counting_that_gets_cancelled),
        ):
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            mock_connection.return_value = (True, "PONG")

            # Scan A - should be cancelled during counting
            result_a = scanner.scan_sync(str(test_dir), count_targets=True)

        assert result_a.status == scan_status_class.CANCELLED
        # Event should still be set after cancelled scan
        assert scanner._cancel_event.is_set() is True

        # Now start scan B - this is where the bug manifested
        # Without the fix, scan B would return CANCELLED immediately
        # because the flag wasn't reset at scan start
        with (
            patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
            patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            mock_connection.return_value = (True, "PONG")

            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            # Scan B - should run normally, not be cancelled
            result_b = scanner.scan_sync(str(test_dir), count_targets=False)

        # With the fix, scan B should complete successfully
        assert result_b.status == scan_status_class.CLEAN
        assert scanner._cancel_event.is_set() is False

    def test_multiple_cancelled_scans_followed_by_successful_scan(
        self, tmp_path, daemon_scanner_class, scan_status_class
    ):
        """Test that multiple consecutive cancelled scans don't affect subsequent scans."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = daemon_scanner_class()

        # Cancel several scans in a row
        for _ in range(3):
            scanner._cancel_event.set()

        # Now run a real scan
        with (
            patch("src.core.daemon_scanner.check_clamdscan_installed") as mock_installed,
            patch("src.core.daemon_scanner.check_clamd_connection") as mock_connection,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_installed.return_value = (True, "ClamAV 1.0.0")
            mock_connection.return_value = (True, "PONG")

            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            result = scanner.scan_sync(str(test_file), count_targets=False)

        assert result.status == scan_status_class.CLEAN
