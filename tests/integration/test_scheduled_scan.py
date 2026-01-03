# ClamUI Scheduled Scan Integration Tests
"""Integration tests for the scheduled scan functionality."""

import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Store original gi modules to restore later (if they exist)
_original_gi = sys.modules.get("gi")
_original_gi_repository = sys.modules.get("gi.repository")

# Mock gi module before importing to avoid GTK dependencies in tests
sys.modules["gi"] = mock.MagicMock()
sys.modules["gi.repository"] = mock.MagicMock()

from src.core.battery_manager import BatteryManager
from src.core.log_manager import LogEntry, LogManager
from src.core.quarantine.manager import (
    QuarantineManager,
    QuarantineStatus,
)
from src.core.scheduler import Scheduler, SchedulerBackend
from src.core.settings_manager import SettingsManager

# Restore original gi modules after imports are done
if _original_gi is not None:
    sys.modules["gi"] = _original_gi
else:
    del sys.modules["gi"]
if _original_gi_repository is not None:
    sys.modules["gi.repository"] = _original_gi_repository
else:
    del sys.modules["gi.repository"]


class TestScheduleSettingsPersistence:
    """Tests for schedule settings persistence."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_schedule_settings_in_defaults(self, temp_config_dir):
        """Test that schedule settings are in DEFAULT_SETTINGS."""
        manager = SettingsManager(config_dir=temp_config_dir)

        assert "scheduled_scans_enabled" in manager.DEFAULT_SETTINGS
        assert "schedule_frequency" in manager.DEFAULT_SETTINGS
        assert "schedule_time" in manager.DEFAULT_SETTINGS
        assert "schedule_targets" in manager.DEFAULT_SETTINGS
        assert "schedule_skip_on_battery" in manager.DEFAULT_SETTINGS
        assert "schedule_auto_quarantine" in manager.DEFAULT_SETTINGS

    def test_schedule_settings_persist(self, temp_config_dir):
        """Test that schedule settings persist to file."""
        manager = SettingsManager(config_dir=temp_config_dir)

        # Set schedule settings
        manager.set("scheduled_scans_enabled", True)
        manager.set("schedule_frequency", "weekly")
        manager.set("schedule_time", "03:00")
        manager.set("schedule_targets", ["/home/user/Documents", "/home/user/Downloads"])
        manager.set("schedule_skip_on_battery", True)
        manager.set("schedule_auto_quarantine", True)

        # Create new manager to test persistence
        manager2 = SettingsManager(config_dir=temp_config_dir)

        assert manager2.get("scheduled_scans_enabled") is True
        assert manager2.get("schedule_frequency") == "weekly"
        assert manager2.get("schedule_time") == "03:00"
        assert manager2.get("schedule_targets") == ["/home/user/Documents", "/home/user/Downloads"]
        assert manager2.get("schedule_skip_on_battery") is True
        assert manager2.get("schedule_auto_quarantine") is True


class TestLogEntryScheduledField:
    """Tests for LogEntry scheduled field."""

    def test_log_entry_scheduled_field_default(self):
        """Test LogEntry defaults scheduled to False."""
        entry = LogEntry.create(
            log_type="scan", status="clean", summary="Test scan", details="Test details"
        )
        assert entry.scheduled is False

    def test_log_entry_scheduled_field_true(self):
        """Test LogEntry can be created with scheduled=True."""
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scheduled scan",
            details="Details",
            scheduled=True,
        )
        assert entry.scheduled is True

    def test_log_entry_to_dict_includes_scheduled(self):
        """Test LogEntry.to_dict() includes scheduled field."""
        entry = LogEntry.create(
            log_type="scan", status="clean", summary="Test", details="Details", scheduled=True
        )
        data = entry.to_dict()
        assert "scheduled" in data
        assert data["scheduled"] is True

    def test_log_entry_from_dict_reads_scheduled(self):
        """Test LogEntry.from_dict() reads scheduled field."""
        data = {
            "id": "test-id",
            "timestamp": "2024-01-01T00:00:00",
            "type": "scan",
            "status": "clean",
            "summary": "Test",
            "details": "Details",
            "scheduled": True,
        }
        entry = LogEntry.from_dict(data)
        assert entry.scheduled is True

    def test_log_entry_from_dict_defaults_scheduled(self):
        """Test LogEntry.from_dict() defaults scheduled to False for old entries."""
        data = {
            "id": "test-id",
            "timestamp": "2024-01-01T00:00:00",
            "type": "scan",
            "status": "clean",
            "summary": "Test",
            "details": "Details",
            # No scheduled field (old entry)
        }
        entry = LogEntry.from_dict(data)
        assert entry.scheduled is False


class TestScheduledScanLogPersistence:
    """Tests for scheduled scan log persistence."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_scheduled_scan_log_saved(self, temp_log_dir):
        """Test that scheduled scan log is saved with scheduled=True."""
        log_manager = LogManager(log_dir=temp_log_dir)

        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scheduled scan completed",
            details="No threats found",
            path="/home/user/Documents",
            duration=120.5,
            scheduled=True,
        )
        result = log_manager.save_log(entry)
        assert result is True

        # Retrieve and verify
        logs = log_manager.get_logs()
        assert len(logs) == 1
        assert logs[0].scheduled is True
        assert logs[0].type == "scan"
        assert logs[0].path == "/home/user/Documents"

    def test_scheduled_scan_log_filters(self, temp_log_dir):
        """Test that logs can be filtered by type."""
        log_manager = LogManager(log_dir=temp_log_dir)

        # Create mix of scheduled and manual scans
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scheduled scan {i}",
                details="Details",
                scheduled=True,
            )
            log_manager.save_log(entry)

        for i in range(2):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Manual scan {i}",
                details="Details",
                scheduled=False,
            )
            log_manager.save_log(entry)

        # Get all scan logs
        logs = log_manager.get_logs(log_type="scan")
        assert len(logs) == 5

        # Count scheduled vs manual
        scheduled_count = sum(1 for log in logs if log.scheduled)
        manual_count = sum(1 for log in logs if not log.scheduled)
        assert scheduled_count == 3
        assert manual_count == 2


class TestSchedulerIntegration:
    """Integration tests for Scheduler with system."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_scheduler_detects_backend(self, temp_config_dir):
        """Test that scheduler detects available backend."""
        scheduler = Scheduler(config_dir=Path(temp_config_dir))

        # Should detect at least one backend on most systems
        # (This test may fail on minimal systems without systemd or cron)
        assert scheduler.backend in [
            SchedulerBackend.SYSTEMD,
            SchedulerBackend.CRON,
            SchedulerBackend.NONE,
        ]

    def test_scheduler_status_check(self, temp_config_dir):
        """Test scheduler status check doesn't crash."""
        scheduler = Scheduler(config_dir=Path(temp_config_dir))

        # Should not raise any exceptions
        is_active, message = scheduler.get_status()
        assert isinstance(is_active, bool)

    def test_scheduler_get_backend_name(self, temp_config_dir):
        """Test scheduler returns backend name."""
        scheduler = Scheduler(config_dir=Path(temp_config_dir))

        name = scheduler.get_backend_name()
        assert name in ["systemd timers", "cron", "none"]


class TestBatteryAwareScanning:
    """Integration tests for battery-aware scanning."""

    def test_battery_manager_integration(self):
        """Test BatteryManager provides consistent status."""
        manager = BatteryManager()

        # Should not crash
        status = manager.get_status()

        # Basic sanity checks
        assert isinstance(status.has_battery, bool)
        assert isinstance(status.is_plugged, bool)

        # If no battery, should always be "plugged"
        if not status.has_battery:
            assert status.is_plugged is True

    def test_should_skip_scan_logic(self):
        """Test should_skip_scan logic is consistent."""
        manager = BatteryManager()

        # When skip_on_battery is False, should never skip
        assert manager.should_skip_scan(skip_on_battery=False) is False

        # When skip_on_battery is True, result depends on battery state
        # (we can't control the hardware, so just check it doesn't crash)
        result = manager.should_skip_scan(skip_on_battery=True)
        assert isinstance(result, bool)


class TestQuarantineFunctionality:
    """Integration tests for quarantine functionality using QuarantineManager."""

    @pytest.fixture
    def temp_environment(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            quarantine_dir = Path(tmpdir) / "quarantine"
            db_path = Path(tmpdir) / "quarantine.db"

            yield {
                "tmpdir": tmpdir,
                "source_dir": source_dir,
                "quarantine_dir": quarantine_dir,
                "db_path": db_path,
            }

    @pytest.fixture
    def manager(self, temp_environment):
        """Create a QuarantineManager for testing."""
        mgr = QuarantineManager(
            quarantine_directory=str(temp_environment["quarantine_dir"]),
            database_path=str(temp_environment["db_path"]),
        )
        yield mgr
        mgr._database.close()

    def create_test_file(
        self, source_dir: Path, name: str = "test_threat.exe", content: bytes = b"malware content"
    ):
        """Helper to create a test file for quarantine testing."""
        file_path = source_dir / name
        file_path.write_bytes(content)
        return file_path

    def test_quarantine_moves_files(self, temp_environment, manager):
        """Test QuarantineManager.quarantine_file moves files correctly."""
        # Create test files
        test_file1 = self.create_test_file(
            temp_environment["source_dir"], "infected1.txt", b"test content 1"
        )
        test_file2 = self.create_test_file(
            temp_environment["source_dir"], "infected2.txt", b"test content 2"
        )

        # Quarantine files using QuarantineManager
        result1 = manager.quarantine_file(str(test_file1), "Threat.Test1")
        result2 = manager.quarantine_file(str(test_file2), "Threat.Test2")

        # Check results
        assert result1.is_success is True
        assert result1.status == QuarantineStatus.SUCCESS
        assert result1.entry is not None

        assert result2.is_success is True
        assert result2.status == QuarantineStatus.SUCCESS
        assert result2.entry is not None

        # Original files should not exist
        assert not test_file1.exists()
        assert not test_file2.exists()

        # Verify files are in quarantine directory
        assert Path(result1.entry.quarantine_path).exists()
        assert Path(result2.entry.quarantine_path).exists()
        assert Path(result1.entry.quarantine_path).parent == temp_environment["quarantine_dir"]
        assert Path(result2.entry.quarantine_path).parent == temp_environment["quarantine_dir"]

        # Verify database entries were created
        assert manager.get_entry_count() == 2

    def test_quarantine_handles_missing_file(self, temp_environment, manager):
        """Test quarantine handles missing files gracefully."""
        # Try to quarantine non-existent file
        nonexistent_path = str(temp_environment["source_dir"] / "nonexistent.txt")
        result = manager.quarantine_file(nonexistent_path, "Threat.Missing")

        assert result.is_success is False
        assert result.status == QuarantineStatus.FILE_NOT_FOUND
        assert result.entry is None
        assert result.error_message is not None

    def test_quarantine_creates_directory(self, temp_environment):
        """Test quarantine creates directory if it doesn't exist."""
        # Use non-existent quarantine directory
        new_quarantine = temp_environment["source_dir"] / "new_quarantine"
        db_path = Path(temp_environment["tmpdir"]) / "new_quarantine.db"

        # Create manager with new directory (should be created automatically)
        manager = QuarantineManager(
            quarantine_directory=str(new_quarantine),
            database_path=str(db_path),
        )

        # Create test file
        test_file = self.create_test_file(temp_environment["source_dir"], "test.txt", b"content")

        result = manager.quarantine_file(str(test_file), "Threat.Test")

        assert result.is_success is True
        assert new_quarantine.exists()

        # Cleanup
        manager._database.close()

    def test_quarantine_directory_permissions(self, temp_environment):
        """Test quarantine directory has restricted permissions."""
        # Use non-existent quarantine directory
        new_quarantine = temp_environment["source_dir"] / "secure_quarantine"
        db_path = Path(temp_environment["tmpdir"]) / "secure_quarantine.db"

        # Create manager with new directory
        manager = QuarantineManager(
            quarantine_directory=str(new_quarantine),
            database_path=str(db_path),
        )

        # Create test file
        test_file = self.create_test_file(temp_environment["source_dir"], "test.txt", b"content")

        result = manager.quarantine_file(str(test_file), "Threat.Test")
        assert result.is_success is True

        # Check directory permissions (0700)
        mode = new_quarantine.stat().st_mode & 0o777
        assert mode == 0o700

        # Cleanup
        manager._database.close()

    def test_quarantine_file_permissions(self, temp_environment, manager):
        """Test quarantined files have restricted permissions."""
        test_file = self.create_test_file(
            temp_environment["source_dir"], "test.exe", b"malware content"
        )

        result = manager.quarantine_file(str(test_file), "Win.Trojan.Test")
        assert result.is_success is True

        # Check quarantined file permissions (0400 - read-only for owner)
        quarantine_path = Path(result.entry.quarantine_path)
        mode = quarantine_path.stat().st_mode & 0o777
        assert mode == 0o400

    def test_quarantine_records_metadata(self, temp_environment, manager):
        """Test quarantine records correct metadata in database."""
        test_file = self.create_test_file(
            temp_environment["source_dir"], "infected.exe", b"test malware content"
        )
        original_path = str(test_file.resolve())
        original_size = test_file.stat().st_size

        result = manager.quarantine_file(str(test_file), "Win.Trojan.Test")

        assert result.is_success is True
        assert result.entry is not None
        assert result.entry.original_path == original_path
        assert result.entry.threat_name == "Win.Trojan.Test"
        assert result.entry.file_size == original_size
        assert len(result.entry.file_hash) == 64  # SHA256

    def test_quarantine_prevents_duplicates(self, temp_environment, manager):
        """Test that quarantining already quarantined file path is handled."""
        # Create and quarantine a file
        test_file = self.create_test_file(
            temp_environment["source_dir"], "duplicate.exe", b"content"
        )
        result1 = manager.quarantine_file(str(test_file), "FirstThreat")
        assert result1.is_success

        # Restore the file to original location
        result2 = manager.restore_file(result1.entry.id)
        assert result2.is_success

        # Re-quarantine should work since entry was removed
        result3 = manager.quarantine_file(str(test_file), "SecondThreat")
        assert result3.is_success
        assert manager.get_entry_count() == 1


class TestCLIWrapperIntegration:
    """Integration tests for the CLI wrapper."""

    def test_cli_module_importable(self):
        """Test CLI module can be imported."""
        from src.cli import scheduled_scan

        assert hasattr(scheduled_scan, "main")
        assert hasattr(scheduled_scan, "run_scheduled_scan")
        assert hasattr(scheduled_scan, "parse_arguments")

    def test_cli_parse_arguments(self):
        """Test CLI argument parsing."""
        from src.cli.scheduled_scan import parse_arguments

        # Test with no arguments
        with mock.patch("sys.argv", ["clamui-scheduled-scan"]):
            args = parse_arguments()
            assert args.skip_on_battery is None
            assert args.auto_quarantine is None
            assert args.targets is None
            assert args.dry_run is False
            assert args.verbose is False

    def test_cli_parse_arguments_with_options(self):
        """Test CLI argument parsing with options."""
        from src.cli.scheduled_scan import parse_arguments

        with mock.patch(
            "sys.argv",
            [
                "clamui-scheduled-scan",
                "--skip-on-battery",
                "--auto-quarantine",
                "--target",
                "/home/user/Documents",
                "--target",
                "/home/user/Downloads",
                "--verbose",
            ],
        ):
            args = parse_arguments()
            assert args.skip_on_battery is True
            assert args.auto_quarantine is True
            assert args.targets == ["/home/user/Documents", "/home/user/Downloads"]
            assert args.verbose is True

    def test_cli_dry_run(self):
        """Test CLI dry run mode."""
        from src.cli.scheduled_scan import run_scheduled_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file to scan
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            # Run in dry-run mode
            result = run_scheduled_scan(
                targets=[tmpdir],
                skip_on_battery=False,
                auto_quarantine=False,
                dry_run=True,
                verbose=False,
            )

            # Dry run should return success
            assert result == 0


class TestEndToEndScheduledScan:
    """End-to-end tests for scheduled scan workflow."""

    @pytest.fixture
    def test_environment(self):
        """Set up a complete test environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            log_dir = Path(tmpdir) / "logs"
            scan_dir = Path(tmpdir) / "scan_target"

            config_dir.mkdir()
            log_dir.mkdir()
            scan_dir.mkdir()

            # Create some test files
            for i in range(5):
                (scan_dir / f"file{i}.txt").write_text(f"content {i}")

            yield {"config_dir": config_dir, "log_dir": log_dir, "scan_dir": scan_dir}

    def test_full_workflow_configuration(self, test_environment):
        """Test complete workflow: configure -> save -> verify."""
        config_dir = test_environment["config_dir"]
        scan_dir = test_environment["scan_dir"]

        # 1. Configure settings
        settings = SettingsManager(config_dir=config_dir)
        settings.set("scheduled_scans_enabled", True)
        settings.set("schedule_frequency", "weekly")
        settings.set("schedule_time", "02:00")
        settings.set("schedule_targets", [str(scan_dir)])
        settings.set("schedule_skip_on_battery", True)
        settings.set("schedule_auto_quarantine", False)
        settings.set("schedule_day_of_week", 0)

        # 2. Verify settings persisted
        settings2 = SettingsManager(config_dir=config_dir)
        assert settings2.get("scheduled_scans_enabled") is True
        assert settings2.get("schedule_frequency") == "weekly"
        assert settings2.get("schedule_targets") == [str(scan_dir)]

        # 3. Create scheduler and verify config
        scheduler = Scheduler(config_dir=config_dir)
        # Should have detected a backend
        assert scheduler.backend in [
            SchedulerBackend.SYSTEMD,
            SchedulerBackend.CRON,
            SchedulerBackend.NONE,
        ]

    def test_scheduled_scan_creates_log(self, test_environment):
        """Test that scheduled scan creates log entry with scheduled=True."""
        log_dir = test_environment["log_dir"]

        # Create log entry as if scheduled scan ran
        log_manager = LogManager(log_dir=log_dir)
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scheduled scan completed - 5 files scanned",
            details="Scan Duration: 2.5 seconds\nFiles Scanned: 5\nThreats Found: 0",
            path=str(test_environment["scan_dir"]),
            duration=2.5,
            scheduled=True,
        )
        log_manager.save_log(entry)

        # Verify log was saved
        logs = log_manager.get_logs()
        assert len(logs) == 1
        assert logs[0].scheduled is True
        assert logs[0].status == "clean"
        assert "5 files scanned" in logs[0].summary
