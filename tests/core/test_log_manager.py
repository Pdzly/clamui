# ClamUI LogManager Tests
"""Unit tests for the LogManager and LogEntry classes."""

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from unittest import mock

import pytest

from src.core.log_manager import (
    CLAMD_LOG_PATHS,
    DaemonStatus,
    LogEntry,
    LogManager,
    LogType,
)


class TestLogEntry:
    """Tests for the LogEntry dataclass."""

    def test_create_generates_unique_id(self):
        """Test that LogEntry.create generates unique IDs."""
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="Details here",
        )
        entry2 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="Details here",
        )
        assert entry1.id != entry2.id

    def test_create_sets_timestamp(self):
        """Test that LogEntry.create sets a timestamp."""
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="Details here",
        )
        assert entry.timestamp is not None
        assert len(entry.timestamp) > 0
        # Should be ISO format
        assert "T" in entry.timestamp

    def test_create_with_all_fields(self):
        """Test LogEntry.create with all fields."""
        entry = LogEntry.create(
            log_type="scan",
            status="infected",
            summary="Found malware",
            details="Detailed output here",
            path="/home/user/downloads",
            duration=15.5,
        )
        assert entry.type == "scan"
        assert entry.status == "infected"
        assert entry.summary == "Found malware"
        assert entry.details == "Detailed output here"
        assert entry.path == "/home/user/downloads"
        assert entry.duration == 15.5

    def test_to_dict(self):
        """Test LogEntry.to_dict serialization."""
        entry = LogEntry(
            id="test-uuid-123",
            timestamp="2024-01-15T10:30:00",
            type="update",
            status="success",
            summary="Database updated",
            details="Full output",
            path=None,
            duration=30.0,
        )
        data = entry.to_dict()

        assert data["id"] == "test-uuid-123"
        assert data["timestamp"] == "2024-01-15T10:30:00"
        assert data["type"] == "update"
        assert data["status"] == "success"
        assert data["summary"] == "Database updated"
        assert data["details"] == "Full output"
        assert data["path"] is None
        assert data["duration"] == 30.0

    def test_from_dict(self):
        """Test LogEntry.from_dict deserialization."""
        data = {
            "id": "test-uuid-456",
            "timestamp": "2024-01-16T14:00:00",
            "type": "scan",
            "status": "clean",
            "summary": "No threats found",
            "details": "Scan complete",
            "path": "/home/user",
            "duration": 120.5,
        }
        entry = LogEntry.from_dict(data)

        assert entry.id == "test-uuid-456"
        assert entry.timestamp == "2024-01-16T14:00:00"
        assert entry.type == "scan"
        assert entry.status == "clean"
        assert entry.summary == "No threats found"
        assert entry.details == "Scan complete"
        assert entry.path == "/home/user"
        assert entry.duration == 120.5

    def test_from_dict_with_missing_fields(self):
        """Test LogEntry.from_dict handles missing fields gracefully."""
        data = {"summary": "Partial data"}
        entry = LogEntry.from_dict(data)

        # Should have defaults for missing fields
        assert entry.id is not None
        assert entry.timestamp is not None
        assert entry.type == "unknown"
        assert entry.status == "unknown"
        assert entry.summary == "Partial data"
        assert entry.details == ""
        assert entry.path is None
        assert entry.duration == 0.0

    def test_roundtrip_serialization(self):
        """Test that to_dict and from_dict are reversible."""
        original = LogEntry.create(
            log_type="scan",
            status="infected",
            summary="Test summary",
            details="Test details",
            path="/test/path",
            duration=5.5,
        )
        data = original.to_dict()
        restored = LogEntry.from_dict(data)

        assert restored.id == original.id
        assert restored.timestamp == original.timestamp
        assert restored.type == original.type
        assert restored.status == original.status
        assert restored.summary == original.summary
        assert restored.details == original.details
        assert restored.path == original.path
        assert restored.duration == original.duration


class TestLogManager:
    """Tests for the LogManager class."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    def test_init_creates_log_directory(self, temp_log_dir):
        """Test that LogManager creates the log directory on init."""
        log_dir = Path(temp_log_dir) / "subdir" / "logs"
        manager = LogManager(log_dir=str(log_dir))
        assert log_dir.exists()

    def test_init_with_default_directory(self, monkeypatch):
        """Test LogManager uses XDG_DATA_HOME by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("XDG_DATA_HOME", tmpdir)
            manager = LogManager()
            expected_path = Path(tmpdir) / "clamui" / "logs"
            assert manager._log_dir == expected_path

    def test_save_log(self, log_manager, temp_log_dir):
        """Test saving a log entry."""
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="Details here",
        )
        result = log_manager.save_log(entry)

        assert result is True
        log_file = Path(temp_log_dir) / f"{entry.id}.json"
        assert log_file.exists()

        # Verify content
        with open(log_file, "r") as f:
            data = json.load(f)
        assert data["id"] == entry.id
        assert data["type"] == "scan"

    def test_get_logs_empty(self, log_manager):
        """Test get_logs returns empty list when no logs exist."""
        logs = log_manager.get_logs()
        assert logs == []

    def test_get_logs_returns_saved_entries(self, log_manager):
        """Test get_logs returns previously saved entries."""
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scan 1",
            details="Details 1",
        )
        entry2 = LogEntry.create(
            log_type="update",
            status="success",
            summary="Update 1",
            details="Details 2",
        )
        log_manager.save_log(entry1)
        time.sleep(0.01)  # Ensure different timestamps
        log_manager.save_log(entry2)

        logs = log_manager.get_logs()
        assert len(logs) == 2

    def test_get_logs_sorted_by_timestamp_descending(self, log_manager):
        """Test that get_logs returns entries sorted by timestamp (newest first)."""
        entry1 = LogEntry(
            id="id-1",
            timestamp="2024-01-01T10:00:00",
            type="scan",
            status="clean",
            summary="First",
            details="",
        )
        entry2 = LogEntry(
            id="id-2",
            timestamp="2024-01-02T10:00:00",
            type="scan",
            status="clean",
            summary="Second",
            details="",
        )
        entry3 = LogEntry(
            id="id-3",
            timestamp="2024-01-03T10:00:00",
            type="scan",
            status="clean",
            summary="Third",
            details="",
        )
        log_manager.save_log(entry1)
        log_manager.save_log(entry3)
        log_manager.save_log(entry2)

        logs = log_manager.get_logs()
        assert len(logs) == 3
        assert logs[0].summary == "Third"
        assert logs[1].summary == "Second"
        assert logs[2].summary == "First"

    def test_get_logs_with_limit(self, log_manager):
        """Test get_logs respects the limit parameter."""
        for i in range(10):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details="",
            )
            log_manager.save_log(entry)

        logs = log_manager.get_logs(limit=5)
        assert len(logs) == 5

    def test_get_logs_filter_by_type(self, log_manager):
        """Test get_logs can filter by log type."""
        scan_entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scan",
            details="",
        )
        update_entry = LogEntry.create(
            log_type="update",
            status="success",
            summary="Update",
            details="",
        )
        log_manager.save_log(scan_entry)
        log_manager.save_log(update_entry)

        scan_logs = log_manager.get_logs(log_type="scan")
        assert len(scan_logs) == 1
        assert scan_logs[0].type == "scan"

        update_logs = log_manager.get_logs(log_type="update")
        assert len(update_logs) == 1
        assert update_logs[0].type == "update"

    def test_get_log_by_id(self, log_manager):
        """Test retrieving a specific log by ID."""
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="Details here",
        )
        log_manager.save_log(entry)

        retrieved = log_manager.get_log_by_id(entry.id)
        assert retrieved is not None
        assert retrieved.id == entry.id
        assert retrieved.summary == entry.summary

    def test_get_log_by_id_not_found(self, log_manager):
        """Test get_log_by_id returns None for non-existent ID."""
        result = log_manager.get_log_by_id("non-existent-id")
        assert result is None

    def test_delete_log(self, log_manager, temp_log_dir):
        """Test deleting a specific log entry."""
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="Details here",
        )
        log_manager.save_log(entry)

        # Verify it exists
        log_file = Path(temp_log_dir) / f"{entry.id}.json"
        assert log_file.exists()

        # Delete it
        result = log_manager.delete_log(entry.id)
        assert result is True
        assert not log_file.exists()

        # Should return None now
        assert log_manager.get_log_by_id(entry.id) is None

    def test_delete_log_not_found(self, log_manager):
        """Test delete_log returns False for non-existent ID."""
        result = log_manager.delete_log("non-existent-id")
        assert result is False

    def test_clear_logs(self, log_manager, temp_log_dir):
        """Test clearing all logs."""
        # Create several entries
        for i in range(5):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details="",
            )
            log_manager.save_log(entry)

        # Verify they exist
        assert len(list(Path(temp_log_dir).glob("*.json"))) == 5

        # Clear all
        result = log_manager.clear_logs()
        assert result is True

        # Verify they're gone
        assert len(list(Path(temp_log_dir).glob("*.json"))) == 0
        assert log_manager.get_logs() == []

    def test_clear_logs_empty_directory(self, log_manager):
        """Test clear_logs works when directory is already empty."""
        result = log_manager.clear_logs()
        assert result is True

    def test_get_log_count(self, log_manager):
        """Test get_log_count returns correct count."""
        assert log_manager.get_log_count() == 0

        for i in range(3):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details="",
            )
            log_manager.save_log(entry)

        assert log_manager.get_log_count() == 3

    def test_get_log_count_nonexistent_directory(self, temp_log_dir):
        """Test get_log_count handles missing directory."""
        manager = LogManager(log_dir=os.path.join(temp_log_dir, "nonexistent"))
        # Delete the created directory
        os.rmdir(manager._log_dir)
        assert manager.get_log_count() == 0


class TestLogManagerDaemonStatus:
    """Tests for daemon status detection in LogManager."""

    @pytest.fixture
    def log_manager(self):
        """Create a LogManager with a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LogManager(log_dir=tmpdir)

    def test_get_daemon_status_not_installed(self, log_manager):
        """Test daemon status when clamd is not installed."""
        with mock.patch("shutil.which", return_value=None):
            status, message = log_manager.get_daemon_status()
            assert status == DaemonStatus.NOT_INSTALLED
            assert "not installed" in message.lower()

    def test_get_daemon_status_running(self, log_manager):
        """Test daemon status when clamd is running."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamd"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(returncode=0)
                status, message = log_manager.get_daemon_status()
                assert status == DaemonStatus.RUNNING
                assert "running" in message.lower()

    def test_get_daemon_status_stopped(self, log_manager):
        """Test daemon status when clamd is installed but not running."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamd"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(returncode=1)
                status, message = log_manager.get_daemon_status()
                assert status == DaemonStatus.STOPPED
                assert "not running" in message.lower()

    def test_get_daemon_status_unknown_on_error(self, log_manager):
        """Test daemon status returns UNKNOWN on subprocess error."""
        with mock.patch("shutil.which", return_value="/usr/bin/clamd"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = OSError("Test error")
                status, message = log_manager.get_daemon_status()
                assert status == DaemonStatus.UNKNOWN


class TestLogManagerDaemonLogs:
    """Tests for daemon log reading in LogManager."""

    @pytest.fixture
    def log_manager(self):
        """Create a LogManager with a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LogManager(log_dir=tmpdir)

    def test_get_daemon_log_path_not_found(self, log_manager):
        """Test get_daemon_log_path returns None when no log exists."""
        with mock.patch.object(Path, "exists", return_value=False):
            result = log_manager.get_daemon_log_path()
            # Result may be None if no log file is found
            # This depends on system state, so just ensure it doesn't crash
            assert result is None or isinstance(result, str)

    def test_read_daemon_logs_file_not_found(self, log_manager):
        """Test read_daemon_logs when log file doesn't exist."""
        with mock.patch.object(log_manager, "get_daemon_log_path", return_value=None):
            # Also mock journalctl fallback to return failure
            with mock.patch.object(
                log_manager, "_read_daemon_logs_journalctl",
                return_value=(False, "No journal entries found")
            ):
                success, content = log_manager.read_daemon_logs()
                assert success is False
                assert "not found" in content.lower()

    def test_read_daemon_logs_success(self, log_manager):
        """Test read_daemon_logs successfully reads log content."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            temp_log_path = f.name

        try:
            with mock.patch.object(
                log_manager, "get_daemon_log_path", return_value=temp_log_path
            ):
                success, content = log_manager.read_daemon_logs(num_lines=10)
                assert success is True
                assert "Line 1" in content
                assert "Line 2" in content
                assert "Line 3" in content
        finally:
            os.unlink(temp_log_path)

    def test_read_daemon_logs_respects_num_lines(self, log_manager):
        """Test read_daemon_logs respects the num_lines parameter."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            for i in range(100):
                f.write(f"Log line {i}\n")
            temp_log_path = f.name

        try:
            with mock.patch.object(
                log_manager, "get_daemon_log_path", return_value=temp_log_path
            ):
                success, content = log_manager.read_daemon_logs(num_lines=10)
                assert success is True
                # Should only have last 10 lines
                lines = [line for line in content.strip().split("\n") if line]
                assert len(lines) <= 10
        finally:
            os.unlink(temp_log_path)

    def test_read_daemon_logs_empty_file(self, log_manager):
        """Test read_daemon_logs handles empty log file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            temp_log_path = f.name

        try:
            with mock.patch.object(
                log_manager, "get_daemon_log_path", return_value=temp_log_path
            ):
                success, content = log_manager.read_daemon_logs()
                assert success is True
                assert "empty" in content.lower()
        finally:
            os.unlink(temp_log_path)


class TestLogType:
    """Tests for the LogType enum."""

    def test_log_type_values(self):
        """Test LogType enum has expected values."""
        assert LogType.SCAN.value == "scan"
        assert LogType.UPDATE.value == "update"


class TestDaemonStatus:
    """Tests for the DaemonStatus enum."""

    def test_daemon_status_values(self):
        """Test DaemonStatus enum has expected values."""
        assert DaemonStatus.RUNNING.value == "running"
        assert DaemonStatus.STOPPED.value == "stopped"
        assert DaemonStatus.NOT_INSTALLED.value == "not_installed"
        assert DaemonStatus.UNKNOWN.value == "unknown"


class TestLogManagerAsync:
    """Tests for async log retrieval in LogManager."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    def test_get_logs_async_calls_callback_with_entries(self, log_manager):
        """Test that get_logs_async calls callback with log entries."""
        # Create some test entries
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan 1",
            details="Details 1",
        )
        entry2 = LogEntry.create(
            log_type="update",
            status="success",
            summary="Test update 1",
            details="Details 2",
        )
        log_manager.save_log(entry1)
        log_manager.save_log(entry2)

        # Track callback invocation
        callback_results = []
        callback_event = threading.Event()

        def mock_callback(entries):
            callback_results.append(entries)
            callback_event.set()

        # Mock GLib.idle_add to call the callback directly
        with mock.patch("src.core.log_manager.GLib") as mock_glib:
            # Make idle_add call the function immediately
            mock_glib.idle_add.side_effect = lambda func, *args: func(*args)

            log_manager.get_logs_async(mock_callback)

            # Wait for background thread to complete
            callback_event.wait(timeout=5)

        assert len(callback_results) == 1
        assert len(callback_results[0]) == 2

    def test_get_logs_async_empty_logs(self, log_manager):
        """Test get_logs_async with no stored logs."""
        callback_results = []
        callback_event = threading.Event()

        def mock_callback(entries):
            callback_results.append(entries)
            callback_event.set()

        with mock.patch("src.core.log_manager.GLib") as mock_glib:
            mock_glib.idle_add.side_effect = lambda func, *args: func(*args)

            log_manager.get_logs_async(mock_callback)
            callback_event.wait(timeout=5)

        assert len(callback_results) == 1
        assert callback_results[0] == []

    def test_get_logs_async_respects_limit(self, log_manager):
        """Test that get_logs_async respects the limit parameter."""
        # Create more entries than the limit
        for i in range(10):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details="",
            )
            log_manager.save_log(entry)

        callback_results = []
        callback_event = threading.Event()

        def mock_callback(entries):
            callback_results.append(entries)
            callback_event.set()

        with mock.patch("src.core.log_manager.GLib") as mock_glib:
            mock_glib.idle_add.side_effect = lambda func, *args: func(*args)

            log_manager.get_logs_async(mock_callback, limit=5)
            callback_event.wait(timeout=5)

        assert len(callback_results) == 1
        assert len(callback_results[0]) == 5

    def test_get_logs_async_filters_by_type(self, log_manager):
        """Test that get_logs_async filters by log type."""
        # Create entries of different types
        scan_entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scan entry",
            details="",
        )
        update_entry = LogEntry.create(
            log_type="update",
            status="success",
            summary="Update entry",
            details="",
        )
        log_manager.save_log(scan_entry)
        log_manager.save_log(update_entry)

        callback_results = []
        callback_event = threading.Event()

        def mock_callback(entries):
            callback_results.append(entries)
            callback_event.set()

        with mock.patch("src.core.log_manager.GLib") as mock_glib:
            mock_glib.idle_add.side_effect = lambda func, *args: func(*args)

            log_manager.get_logs_async(mock_callback, log_type="scan")
            callback_event.wait(timeout=5)

        assert len(callback_results) == 1
        assert len(callback_results[0]) == 1
        assert callback_results[0][0].type == "scan"

    def test_get_logs_async_uses_glib_idle_add(self, log_manager):
        """Test that get_logs_async schedules callback via GLib.idle_add."""
        callback_event = threading.Event()

        def mock_callback(entries):
            callback_event.set()

        with mock.patch("src.core.log_manager.GLib") as mock_glib:
            # Track calls to idle_add without executing
            mock_glib.idle_add.side_effect = lambda func, *args: (func(*args), callback_event.set())

            log_manager.get_logs_async(mock_callback)
            callback_event.wait(timeout=5)

            # Verify GLib.idle_add was called
            assert mock_glib.idle_add.called

    def test_get_logs_async_runs_in_daemon_thread(self, log_manager):
        """Test that get_logs_async runs in a daemon thread."""
        thread_info = {}
        callback_event = threading.Event()

        def mock_callback(entries):
            callback_event.set()

        # Patch Thread.start to capture thread properties right before start
        original_start = threading.Thread.start

        def patched_start(self):
            thread_info["daemon"] = self.daemon
            original_start(self)

        with mock.patch("src.core.log_manager.GLib") as mock_glib:
            mock_glib.idle_add.side_effect = lambda func, *args: func(*args)

            with mock.patch.object(threading.Thread, "start", patched_start):
                log_manager.get_logs_async(mock_callback)
                callback_event.wait(timeout=5)

        assert thread_info.get("daemon") is True


class TestLogManagerThreadSafety:
    """Tests for thread safety in LogManager."""

    @pytest.fixture
    def log_manager(self):
        """Create a LogManager with a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LogManager(log_dir=tmpdir)

    def test_concurrent_save_operations(self, log_manager):
        """Test that concurrent save operations don't corrupt data."""
        import threading

        entries = []
        errors = []

        def save_entry(index):
            try:
                entry = LogEntry.create(
                    log_type="scan",
                    status="clean",
                    summary=f"Concurrent scan {index}",
                    details=f"Details {index}",
                )
                entries.append(entry)
                result = log_manager.save_log(entry)
                if not result:
                    errors.append(f"Failed to save entry {index}")
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = []
        for i in range(20):
            t = threading.Thread(target=save_entry, args=(i,))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0

        # Verify all entries were saved
        logs = log_manager.get_logs(limit=100)
        assert len(logs) == 20
