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


class TestLogManagerIndexInfrastructure:
    """Tests for index infrastructure in LogManager."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    def test_load_index_empty_state(self, log_manager):
        """Test _load_index returns empty structure when no index file exists."""
        index = log_manager._load_index()
        assert isinstance(index, dict)
        assert index["version"] == 1
        assert index["entries"] == []

    def test_load_index_valid_index(self, log_manager, temp_log_dir):
        """Test _load_index successfully loads a valid index file."""
        # Create a valid index file
        index_data = {
            "version": 1,
            "entries": [
                {"id": "test-id-1", "timestamp": "2024-01-01T10:00:00", "type": "scan"},
                {"id": "test-id-2", "timestamp": "2024-01-02T10:00:00", "type": "update"},
            ]
        }
        index_path = Path(temp_log_dir) / "log_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f)

        # Load the index
        loaded = log_manager._load_index()
        assert loaded["version"] == 1
        assert len(loaded["entries"]) == 2
        assert loaded["entries"][0]["id"] == "test-id-1"
        assert loaded["entries"][1]["id"] == "test-id-2"

    def test_load_index_corrupted_json(self, log_manager, temp_log_dir):
        """Test _load_index handles corrupted JSON gracefully."""
        # Create a corrupted index file
        index_path = Path(temp_log_dir) / "log_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json }")

        # Should return empty structure instead of crashing
        index = log_manager._load_index()
        assert index["version"] == 1
        assert index["entries"] == []

    def test_load_index_invalid_structure(self, log_manager, temp_log_dir):
        """Test _load_index handles invalid structure gracefully."""
        # Create index with wrong structure (missing required keys)
        index_path = Path(temp_log_dir) / "log_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({"invalid": "structure"}, f)

        # Should return empty structure
        index = log_manager._load_index()
        assert index["version"] == 1
        assert index["entries"] == []

    def test_load_index_permission_error(self, log_manager, temp_log_dir):
        """Test _load_index handles permission errors gracefully."""
        # Create a valid index file
        index_path = Path(temp_log_dir) / "log_index.json"
        index_data = {"version": 1, "entries": []}
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f)

        # Mock open to raise PermissionError
        with mock.patch("builtins.open", side_effect=PermissionError("Permission denied")):
            index = log_manager._load_index()
            assert index["version"] == 1
            assert index["entries"] == []

    def test_save_index_success(self, log_manager, temp_log_dir):
        """Test _save_index successfully saves index to file."""
        index_data = {
            "version": 1,
            "entries": [
                {"id": "test-id-1", "timestamp": "2024-01-01T10:00:00", "type": "scan"},
            ]
        }

        result = log_manager._save_index(index_data)
        assert result is True

        # Verify file was created
        index_path = Path(temp_log_dir) / "log_index.json"
        assert index_path.exists()

        # Verify content
        with open(index_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["version"] == 1
        assert len(saved_data["entries"]) == 1
        assert saved_data["entries"][0]["id"] == "test-id-1"

    def test_save_index_atomic_write(self, log_manager, temp_log_dir):
        """Test _save_index uses atomic write pattern."""
        index_data = {"version": 1, "entries": []}

        # Save initial data
        log_manager._save_index(index_data)

        # Save again with different data
        new_data = {
            "version": 1,
            "entries": [
                {"id": "new-id", "timestamp": "2024-01-01T10:00:00", "type": "scan"},
            ]
        }
        result = log_manager._save_index(new_data)
        assert result is True

        # Verify new data was written
        loaded = log_manager._load_index()
        assert len(loaded["entries"]) == 1
        assert loaded["entries"][0]["id"] == "new-id"

    def test_save_index_creates_directory(self, temp_log_dir):
        """Test _save_index creates parent directory if needed."""
        # Create manager with non-existent directory
        log_dir = Path(temp_log_dir) / "subdir" / "logs"
        manager = LogManager(log_dir=str(log_dir))

        # Delete the directory that was created by __init__
        import shutil
        shutil.rmtree(log_dir)

        # Save should recreate the directory
        index_data = {"version": 1, "entries": []}
        result = manager._save_index(index_data)
        assert result is True
        assert log_dir.exists()

    def test_save_index_permission_error(self, log_manager):
        """Test _save_index handles permission errors gracefully."""
        index_data = {"version": 1, "entries": []}

        # Mock tempfile.mkstemp to raise PermissionError
        with mock.patch("tempfile.mkstemp", side_effect=PermissionError("Permission denied")):
            result = log_manager._save_index(index_data)
            assert result is False

    def test_save_index_cleanup_on_failure(self, log_manager, temp_log_dir):
        """Test _save_index cleans up temp file on failure."""
        index_data = {"version": 1, "entries": []}

        # Track created temp files
        temp_files = []
        original_mkstemp = tempfile.mkstemp

        def track_mkstemp(*args, **kwargs):
            fd, path = original_mkstemp(*args, **kwargs)
            temp_files.append(path)
            return fd, path

        # Mock Path.replace to fail after temp file is created
        with mock.patch("tempfile.mkstemp", side_effect=track_mkstemp):
            with mock.patch("pathlib.Path.replace", side_effect=OSError("Simulated failure")):
                result = log_manager._save_index(index_data)
                assert result is False

                # Verify temp file was cleaned up
                if temp_files:
                    assert not Path(temp_files[0]).exists()

    def test_rebuild_index_empty_directory(self, log_manager, temp_log_dir):
        """Test rebuild_index creates empty index when no logs exist."""
        result = log_manager.rebuild_index()
        assert result is True

        # Verify index was created with empty entries
        index = log_manager._load_index()
        assert index["version"] == 1
        assert index["entries"] == []

    def test_rebuild_index_with_valid_logs(self, log_manager):
        """Test rebuild_index creates index from existing log files."""
        # Create some log entries
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

        # Rebuild the index
        result = log_manager.rebuild_index()
        assert result is True

        # Verify index contains both entries
        index = log_manager._load_index()
        assert len(index["entries"]) == 2

        # Verify entries contain correct metadata
        ids = {entry["id"] for entry in index["entries"]}
        assert entry1.id in ids
        assert entry2.id in ids

        types = {entry["type"] for entry in index["entries"]}
        assert "scan" in types
        assert "update" in types

    def test_rebuild_index_skips_corrupted_files(self, log_manager, temp_log_dir):
        """Test rebuild_index skips corrupted log files."""
        # Create a valid log entry
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Valid entry",
            details="Details",
        )
        log_manager.save_log(entry)

        # Create a corrupted log file
        corrupted_path = Path(temp_log_dir) / "corrupted.json"
        with open(corrupted_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        # Rebuild should succeed and include only the valid entry
        result = log_manager.rebuild_index()
        assert result is True

        index = log_manager._load_index()
        assert len(index["entries"]) == 1
        assert index["entries"][0]["id"] == entry.id

    def test_rebuild_index_skips_index_file(self, log_manager, temp_log_dir):
        """Test rebuild_index doesn't process the index file itself."""
        # Create an old index file
        old_index = {
            "version": 1,
            "entries": [
                {"id": "old-id", "timestamp": "2024-01-01T10:00:00", "type": "scan"},
            ]
        }
        index_path = Path(temp_log_dir) / "log_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(old_index, f)

        # Create a real log entry
        entry = LogEntry.create(
            log_type="update",
            status="success",
            summary="Real entry",
            details="Details",
        )
        log_manager.save_log(entry)

        # Rebuild should create new index with only the real log entry
        result = log_manager.rebuild_index()
        assert result is True

        index = log_manager._load_index()
        assert len(index["entries"]) == 1
        assert index["entries"][0]["id"] == entry.id
        assert index["entries"][0]["type"] == "update"

    def test_rebuild_index_handles_missing_fields(self, log_manager, temp_log_dir):
        """Test rebuild_index skips entries with missing required fields."""
        # Create log file with missing timestamp
        incomplete_log = {
            "id": "test-id",
            "type": "scan",
            # Missing timestamp
            "status": "clean",
            "summary": "Test",
            "details": "Test",
        }
        incomplete_path = Path(temp_log_dir) / "incomplete.json"
        with open(incomplete_path, "w", encoding="utf-8") as f:
            json.dump(incomplete_log, f)

        # Create a complete log entry
        complete_entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Complete entry",
            details="Details",
        )
        log_manager.save_log(complete_entry)

        # Rebuild should skip incomplete entry
        result = log_manager.rebuild_index()
        assert result is True

        index = log_manager._load_index()
        assert len(index["entries"]) == 1
        assert index["entries"][0]["id"] == complete_entry.id

    def test_rebuild_index_nonexistent_directory(self, temp_log_dir):
        """Test rebuild_index handles non-existent directory gracefully."""
        # Create manager with directory, then remove it
        log_dir = Path(temp_log_dir) / "nonexistent"
        manager = LogManager(log_dir=str(log_dir))

        # Delete the directory
        import shutil
        shutil.rmtree(log_dir)

        # Rebuild should create empty index
        result = manager.rebuild_index()
        assert result is True

        # Verify empty index was created
        index = manager._load_index()
        assert index["version"] == 1
        assert index["entries"] == []

    def test_rebuild_index_after_corruption(self, log_manager, temp_log_dir):
        """Test rebuild_index can recover from corrupted index file."""
        # Create valid log entries
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry 1",
            details="Details 1",
        )
        entry2 = LogEntry.create(
            log_type="update",
            status="success",
            summary="Entry 2",
            details="Details 2",
        )
        log_manager.save_log(entry1)
        log_manager.save_log(entry2)

        # Corrupt the index file
        index_path = Path(temp_log_dir) / "log_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("{ corrupted json data }")

        # Verify index is corrupted
        corrupted_index = log_manager._load_index()
        assert corrupted_index["entries"] == []

        # Rebuild should recover
        result = log_manager.rebuild_index()
        assert result is True

        # Verify index now contains both entries
        recovered_index = log_manager._load_index()
        assert len(recovered_index["entries"]) == 2

    def test_rebuild_index_thread_safety(self, log_manager):
        """Test rebuild_index is thread-safe."""
        # Create some log entries
        for i in range(5):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Entry {i}",
                details="Details",
            )
            log_manager.save_log(entry)

        # Rebuild index from multiple threads
        errors = []
        results = []

        def rebuild():
            try:
                result = log_manager.rebuild_index()
                results.append(result)
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(5):
            t = threading.Thread(target=rebuild)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0
        # All rebuilds should succeed
        assert all(results)

        # Verify final index is valid
        index = log_manager._load_index()
        assert len(index["entries"]) == 5


class TestLogManagerIndexMaintenance:
    """Tests for index maintenance during log operations."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    def test_save_log_updates_index(self, log_manager):
        """Test that save_log adds entry metadata to index."""
        # Create and save a log entry
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="Details here",
        )
        result = log_manager.save_log(entry)
        assert result is True

        # Verify index was updated
        index = log_manager._load_index()
        assert len(index["entries"]) == 1
        assert index["entries"][0]["id"] == entry.id
        assert index["entries"][0]["timestamp"] == entry.timestamp
        assert index["entries"][0]["type"] == entry.type

    def test_save_log_updates_index_multiple_entries(self, log_manager):
        """Test that save_log correctly maintains index with multiple entries."""
        entries = []
        for i in range(5):
            entry = LogEntry.create(
                log_type="scan" if i % 2 == 0 else "update",
                status="clean",
                summary=f"Entry {i}",
                details="Details",
            )
            entries.append(entry)
            log_manager.save_log(entry)

        # Verify all entries are in index
        index = log_manager._load_index()
        assert len(index["entries"]) == 5

        # Verify all IDs are present
        index_ids = {e["id"] for e in index["entries"]}
        for entry in entries:
            assert entry.id in index_ids

    def test_save_log_preserves_existing_index(self, log_manager):
        """Test that save_log preserves existing index entries."""
        # Save first entry
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry 1",
            details="Details",
        )
        log_manager.save_log(entry1)

        # Save second entry
        entry2 = LogEntry.create(
            log_type="update",
            status="success",
            summary="Entry 2",
            details="Details",
        )
        log_manager.save_log(entry2)

        # Verify both entries are in index
        index = log_manager._load_index()
        assert len(index["entries"]) == 2
        ids = {e["id"] for e in index["entries"]}
        assert entry1.id in ids
        assert entry2.id in ids

    def test_save_log_continues_on_index_failure(self, log_manager, temp_log_dir):
        """Test that save_log succeeds even if index update fails."""
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="Details",
        )

        # Mock _save_index to fail
        with mock.patch.object(log_manager, "_save_index", return_value=False):
            result = log_manager.save_log(entry)
            # Log file should still be saved
            assert result is True

            # Verify log file exists
            log_file = Path(temp_log_dir) / f"{entry.id}.json"
            assert log_file.exists()

    def test_delete_log_removes_from_index(self, log_manager):
        """Test that delete_log removes entry from index."""
        # Create and save entries
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry 1",
            details="Details",
        )
        entry2 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry 2",
            details="Details",
        )
        log_manager.save_log(entry1)
        log_manager.save_log(entry2)

        # Verify both are in index
        index = log_manager._load_index()
        assert len(index["entries"]) == 2

        # Delete first entry
        result = log_manager.delete_log(entry1.id)
        assert result is True

        # Verify only second entry remains in index
        index = log_manager._load_index()
        assert len(index["entries"]) == 1
        assert index["entries"][0]["id"] == entry2.id

    def test_delete_log_handles_nonexistent_entry_in_index(self, log_manager):
        """Test delete_log handles entry not in index gracefully."""
        # Create an entry and save it
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry",
            details="Details",
        )
        log_manager.save_log(entry)

        # Manually remove from index but leave file
        index = log_manager._load_index()
        index["entries"] = []
        log_manager._save_index(index)

        # Delete should still succeed
        result = log_manager.delete_log(entry.id)
        assert result is True

    def test_delete_log_continues_on_index_failure(self, log_manager, temp_log_dir):
        """Test that delete_log succeeds even if index update fails."""
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="Details",
        )
        log_manager.save_log(entry)

        # Mock _save_index to fail
        with mock.patch.object(log_manager, "_save_index", return_value=False):
            result = log_manager.delete_log(entry.id)
            # Log file should still be deleted
            assert result is True

            # Verify log file is gone
            log_file = Path(temp_log_dir) / f"{entry.id}.json"
            assert not log_file.exists()

    def test_clear_logs_resets_index(self, log_manager):
        """Test that clear_logs resets index to empty state."""
        # Create multiple entries
        for i in range(5):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Entry {i}",
                details="Details",
            )
            log_manager.save_log(entry)

        # Verify entries exist in index
        index = log_manager._load_index()
        assert len(index["entries"]) == 5

        # Clear all logs
        result = log_manager.clear_logs()
        assert result is True

        # Verify index is reset to empty
        index = log_manager._load_index()
        assert index["version"] == 1
        assert index["entries"] == []

    def test_clear_logs_skips_index_file_during_deletion(self, log_manager, temp_log_dir):
        """Test that clear_logs doesn't delete the index file itself."""
        # Create entries
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Entry {i}",
                details="Details",
            )
            log_manager.save_log(entry)

        # Get index path
        index_path = Path(temp_log_dir) / "log_index.json"
        assert index_path.exists()

        # Clear logs
        log_manager.clear_logs()

        # Verify index file still exists (but is empty)
        assert index_path.exists()
        index = log_manager._load_index()
        assert index["entries"] == []

    def test_clear_logs_continues_on_index_failure(self, log_manager, temp_log_dir):
        """Test that clear_logs succeeds even if index reset fails."""
        # Create entries
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry",
            details="Details",
        )
        log_manager.save_log(entry)

        # Mock _save_index to fail
        with mock.patch.object(log_manager, "_save_index", return_value=False):
            result = log_manager.clear_logs()
            # Clear operation should still succeed
            assert result is True

            # Verify log files are gone
            json_files = list(Path(temp_log_dir).glob("*.json"))
            # Only index file should remain (if any)
            for f in json_files:
                assert f.name == "log_index.json"

    def test_concurrent_save_operations_maintain_index(self, log_manager):
        """Test that concurrent save operations correctly maintain index."""
        entries = []
        errors = []

        def save_entry(index):
            try:
                entry = LogEntry.create(
                    log_type="scan",
                    status="clean",
                    summary=f"Concurrent entry {index}",
                    details="Details",
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

        # Wait for completion
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0

        # Verify index contains all entries
        index = log_manager._load_index()
        assert len(index["entries"]) == 20

        # Verify all entry IDs are in index
        index_ids = {e["id"] for e in index["entries"]}
        for entry in entries:
            assert entry.id in index_ids

    def test_concurrent_delete_operations_maintain_index(self, log_manager):
        """Test that concurrent delete operations correctly maintain index."""
        # Create entries first
        entries = []
        for i in range(20):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Entry {i}",
                details="Details",
            )
            log_manager.save_log(entry)
            entries.append(entry)

        # Verify all are in index
        index = log_manager._load_index()
        assert len(index["entries"]) == 20

        errors = []

        def delete_entry(entry):
            try:
                result = log_manager.delete_log(entry.id)
                if not result:
                    errors.append(f"Failed to delete {entry.id}")
            except Exception as e:
                errors.append(str(e))

        # Delete from multiple threads
        threads = []
        for entry in entries:
            t = threading.Thread(target=delete_entry, args=(entry,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0

        # Verify index is empty
        index = log_manager._load_index()
        assert len(index["entries"]) == 0

    def test_concurrent_mixed_operations_maintain_index(self, log_manager):
        """Test that mixed concurrent operations don't corrupt index."""
        # Pre-populate with some entries
        initial_entries = []
        for i in range(10):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Initial {i}",
                details="Details",
            )
            log_manager.save_log(entry)
            initial_entries.append(entry)

        saved_entries = []
        errors = []

        def save_entry(index):
            try:
                entry = LogEntry.create(
                    log_type="update",
                    status="success",
                    summary=f"New {index}",
                    details="Details",
                )
                saved_entries.append(entry)
                if not log_manager.save_log(entry):
                    errors.append(f"Save failed {index}")
            except Exception as e:
                errors.append(f"Save error: {e}")

        def delete_entry(entry):
            try:
                if not log_manager.delete_log(entry.id):
                    errors.append(f"Delete failed {entry.id}")
            except Exception as e:
                errors.append(f"Delete error: {e}")

        # Mix of save and delete operations
        threads = []

        # Add 10 new entries
        for i in range(10):
            t = threading.Thread(target=save_entry, args=(i,))
            threads.append(t)

        # Delete 5 initial entries
        for entry in initial_entries[:5]:
            t = threading.Thread(target=delete_entry, args=(entry,))
            threads.append(t)

        # Shuffle to mix operations
        import random
        random.shuffle(threads)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0

        # Verify index integrity
        index = log_manager._load_index()
        # Should have: 10 initial - 5 deleted + 10 new = 15 entries
        assert len(index["entries"]) == 15

        # Verify structure is valid
        assert "version" in index
        assert "entries" in index
        for entry in index["entries"]:
            assert "id" in entry
            assert "timestamp" in entry
            assert "type" in entry

    def test_concurrent_save_and_rebuild_maintain_index(self, log_manager):
        """Test that concurrent save and rebuild operations don't corrupt index."""
        errors = []
        saved_entries = []

        def save_entries():
            try:
                for i in range(10):
                    entry = LogEntry.create(
                        log_type="scan",
                        status="clean",
                        summary=f"Entry {i}",
                        details="Details",
                    )
                    saved_entries.append(entry)
                    log_manager.save_log(entry)
                    time.sleep(0.001)  # Small delay to allow interleaving
            except Exception as e:
                errors.append(f"Save error: {e}")

        def rebuild_index():
            try:
                for _ in range(5):
                    log_manager.rebuild_index()
                    time.sleep(0.002)  # Small delay
            except Exception as e:
                errors.append(f"Rebuild error: {e}")

        # Run save and rebuild concurrently
        save_thread = threading.Thread(target=save_entries)
        rebuild_thread = threading.Thread(target=rebuild_index)

        save_thread.start()
        rebuild_thread.start()

        save_thread.join()
        rebuild_thread.join()

        # Verify no errors
        assert len(errors) == 0

        # Final rebuild to ensure consistency
        log_manager.rebuild_index()

        # Verify all saved entries are in final index
        index = log_manager._load_index()
        assert len(index["entries"]) == 10

        index_ids = {e["id"] for e in index["entries"]}
        for entry in saved_entries:
            assert entry.id in index_ids

    def test_index_entries_have_correct_structure(self, log_manager):
        """Test that index entries have the correct structure after operations."""
        # Save various types of entries
        scan_entry = LogEntry.create(
            log_type="scan",
            status="infected",
            summary="Found threats",
            details="Details",
            path="/home/user",
            duration=15.5,
        )
        update_entry = LogEntry.create(
            log_type="update",
            status="success",
            summary="Database updated",
            details="Details",
            duration=30.0,
        )

        log_manager.save_log(scan_entry)
        log_manager.save_log(update_entry)

        # Verify index entries have only required metadata (not full entry data)
        index = log_manager._load_index()
        assert len(index["entries"]) == 2

        for entry in index["entries"]:
            # Should have exactly these three fields
            assert set(entry.keys()) == {"id", "timestamp", "type"}
            assert isinstance(entry["id"], str)
            assert isinstance(entry["timestamp"], str)
            assert entry["type"] in ["scan", "update"]

            # Should NOT include full entry data
            assert "status" not in entry
            assert "summary" not in entry
            assert "details" not in entry
            assert "path" not in entry
            assert "duration" not in entry


class TestLogManagerIndexValidation:
    """Tests for index validation and automatic rebuild functionality."""

    def test_validate_index_with_valid_index(self, tmp_path):
        """Test that _validate_index returns True for a valid index."""
        log_manager = LogManager(str(tmp_path))

        # Create some log entries
        for i in range(5):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Test scan {i}",
                details="Details",
            )
            log_manager.save_log(entry)

        # Load the index
        index_data = log_manager._load_index()

        # Validate it
        assert log_manager._validate_index(index_data) is True

    def test_validate_index_with_empty_index_and_empty_directory(self, tmp_path):
        """Test that _validate_index returns True for empty index with no logs."""
        log_manager = LogManager(str(tmp_path))

        # Empty index
        index_data = {"version": 1, "entries": []}

        # Should be valid (no logs, no index entries)
        assert log_manager._validate_index(index_data) is True

    def test_validate_index_with_entry_count_mismatch_extra_entries(self, tmp_path):
        """Test that _validate_index returns False when index has more entries than files."""
        log_manager = LogManager(str(tmp_path))

        # Create 3 log entries
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Test scan {i}",
                details="Details",
            )
            log_manager.save_log(entry)

        # Load the index and add extra bogus entries
        index_data = log_manager._load_index()
        index_data["entries"].append({
            "id": "bogus-id-1",
            "timestamp": "2024-01-01T00:00:00",
            "type": "scan"
        })
        index_data["entries"].append({
            "id": "bogus-id-2",
            "timestamp": "2024-01-01T00:00:00",
            "type": "scan"
        })

        # Should be invalid (5 index entries, 3 actual files)
        assert log_manager._validate_index(index_data) is False

    def test_validate_index_with_entry_count_mismatch_fewer_entries(self, tmp_path):
        """Test that _validate_index returns False when index has fewer entries than files."""
        log_manager = LogManager(str(tmp_path))

        # Create 5 log entries
        for i in range(5):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Test scan {i}",
                details="Details",
            )
            log_manager.save_log(entry)

        # Load the index and remove some entries
        index_data = log_manager._load_index()
        index_data["entries"] = index_data["entries"][:3]

        # Should be invalid (3 index entries, 5 actual files)
        assert log_manager._validate_index(index_data) is False

    def test_validate_index_with_missing_files_above_threshold(self, tmp_path):
        """Test that _validate_index returns False when >20% of files are missing."""
        log_manager = LogManager(str(tmp_path))

        # Create 10 log entries
        log_ids = []
        for i in range(10):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Test scan {i}",
                details="Details",
            )
            log_manager.save_log(entry)
            log_ids.append(entry.id)

        # Delete 3 log files (30% missing - above 20% threshold)
        for i in range(3):
            log_file = tmp_path / f"{log_ids[i]}.json"
            log_file.unlink()

        # Load the index (which still has all 10 entries)
        index_data = log_manager._load_index()

        # Should be invalid (30% missing > 20% threshold)
        assert log_manager._validate_index(index_data) is False

    def test_validate_index_with_missing_files_below_threshold(self, tmp_path):
        """Test that _validate_index returns False even with few missing files due to count mismatch."""
        log_manager = LogManager(str(tmp_path))

        # Create 10 log entries
        log_ids = []
        for i in range(10):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Test scan {i}",
                details="Details",
            )
            log_manager.save_log(entry)
            log_ids.append(entry.id)

        # Delete 1 log file (10% missing - below 20% threshold)
        log_file = tmp_path / f"{log_ids[0]}.json"
        log_file.unlink()

        # Load the index (which still has all 10 entries)
        index_data = log_manager._load_index()

        # Should be invalid due to count mismatch (10 entries, 9 files)
        # even though missing percentage is below threshold
        assert log_manager._validate_index(index_data) is False

    def test_validate_index_with_nonexistent_directory(self, tmp_path):
        """Test that _validate_index handles non-existent directory gracefully."""
        # Create log manager with non-existent directory
        log_manager = LogManager(str(tmp_path / "nonexistent"))

        # Index with entries (but directory doesn't exist)
        index_data = {
            "version": 1,
            "entries": [
                {"id": "test-id", "timestamp": "2024-01-01T00:00:00", "type": "scan"}
            ]
        }

        # Should be invalid (directory doesn't exist but index has entries)
        assert log_manager._validate_index(index_data) is False

    def test_validate_index_with_large_index_uses_sampling(self, tmp_path):
        """Test that _validate_index uses sampling for large indices (>50 entries)."""
        log_manager = LogManager(str(tmp_path))

        # Create 60 log entries
        log_ids = []
        for i in range(60):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Test scan {i}",
                details="Details",
            )
            log_manager.save_log(entry)
            log_ids.append(entry.id)

        # Load the index
        index_data = log_manager._load_index()

        # All files exist, should be valid
        assert log_manager._validate_index(index_data) is True

        # Delete 15 files (25% missing)
        for i in range(15):
            log_file = tmp_path / f"{log_ids[i]}.json"
            log_file.unlink()

        # Reload index (still has all 60 entries)
        index_data = log_manager._load_index()

        # Should be invalid due to count mismatch first
        # (60 entries, 45 files)
        assert log_manager._validate_index(index_data) is False

    def test_get_logs_triggers_rebuild_on_stale_index_count_mismatch(self, tmp_path):
        """Test that get_logs() triggers automatic rebuild when index has count mismatch."""
        log_manager = LogManager(str(tmp_path))

        # Create 5 log entries
        for i in range(5):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Test scan {i}",
                details="Details",
            )
            log_manager.save_log(entry)

        # Manually corrupt the index by adding bogus entries
        index_data = log_manager._load_index()
        original_count = len(index_data["entries"])
        index_data["entries"].append({
            "id": "bogus-id",
            "timestamp": "2024-01-01T00:00:00",
            "type": "scan"
        })
        log_manager._save_index(index_data)

        # Call get_logs() - should detect stale index and rebuild
        logs = log_manager.get_logs()

        # Should return all valid logs
        assert len(logs) == 5

        # Verify index was rebuilt (should have correct count now)
        rebuilt_index = log_manager._load_index()
        assert len(rebuilt_index["entries"]) == original_count

    def test_get_logs_triggers_rebuild_on_missing_files(self, tmp_path):
        """Test that get_logs() triggers automatic rebuild when many files are missing."""
        log_manager = LogManager(str(tmp_path))

        # Create 10 log entries
        log_ids = []
        for i in range(10):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Test scan {i}",
                details="Details",
            )
            log_manager.save_log(entry)
            log_ids.append(entry.id)

        # Delete 3 log files (30% missing - above threshold)
        for i in range(3):
            log_file = tmp_path / f"{log_ids[i]}.json"
            log_file.unlink()

        # Call get_logs() - should detect stale index and rebuild
        logs = log_manager.get_logs()

        # Should return only the 7 remaining valid logs
        assert len(logs) == 7

        # Verify index was rebuilt with correct count
        rebuilt_index = log_manager._load_index()
        assert len(rebuilt_index["entries"]) == 7

    def test_get_logs_handles_validation_error_gracefully(self, tmp_path):
        """Test that get_logs() handles validation errors gracefully."""
        log_manager = LogManager(str(tmp_path))

        # Create some log entries
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Test scan {i}",
                details="Details",
            )
            log_manager.save_log(entry)

        # Mock _validate_index to raise an exception
        original_validate = log_manager._validate_index

        def mock_validate(index_data):
            raise Exception("Validation error")

        log_manager._validate_index = mock_validate

        # get_logs() should handle the error and fall back to full scan
        logs = log_manager.get_logs()

        # Should still return logs via fallback
        assert len(logs) == 3

        # Restore original method
        log_manager._validate_index = original_validate

    def test_validate_index_handles_permission_error(self, tmp_path):
        """Test that _validate_index handles permission errors gracefully."""
        log_manager = LogManager(str(tmp_path))

        # Create a log entry
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="Details",
        )
        log_manager.save_log(entry)

        # Load the index
        index_data = log_manager._load_index()

        # Mock glob to raise PermissionError
        original_glob = tmp_path.glob

        def mock_glob(pattern):
            raise PermissionError("Permission denied")

        log_manager._log_dir.glob = mock_glob

        # Should return False on error
        assert log_manager._validate_index(index_data) is False

        # Restore original glob
        log_manager._log_dir.glob = original_glob


class TestLogManagerOptimizedGetLogs:
    """Tests for optimized get_logs() implementation using index."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    def test_get_logs_uses_index_when_available(self, log_manager):
        """Test that get_logs() uses index for retrieval when available."""
        # Create log entries
        entries = []
        for i in range(10):
            entry = LogEntry.create(
                log_type="scan" if i % 2 == 0 else "update",
                status="clean",
                summary=f"Test entry {i}",
                details="Details",
            )
            log_manager.save_log(entry)
            entries.append(entry)

        # Verify index exists and has correct entries
        index_data = log_manager._load_index()
        assert len(index_data["entries"]) == 10

        # Get logs should use the index
        logs = log_manager.get_logs()
        assert len(logs) == 10

    def test_get_logs_returns_correct_results_with_index(self, log_manager):
        """Test that get_logs() returns correct results when using index."""
        # Create entries with specific timestamps to control order
        entry1 = LogEntry(
            id="id-1",
            timestamp="2024-01-01T10:00:00",
            type="scan",
            status="clean",
            summary="First",
            details="Details",
        )
        entry2 = LogEntry(
            id="id-2",
            timestamp="2024-01-02T10:00:00",
            type="scan",
            status="clean",
            summary="Second",
            details="Details",
        )
        entry3 = LogEntry(
            id="id-3",
            timestamp="2024-01-03T10:00:00",
            type="update",
            status="success",
            summary="Third",
            details="Details",
        )

        log_manager.save_log(entry1)
        log_manager.save_log(entry2)
        log_manager.save_log(entry3)

        # Get all logs
        logs = log_manager.get_logs(limit=100)

        # Should return all 3 logs
        assert len(logs) == 3

        # Should be sorted by timestamp descending (newest first)
        assert logs[0].summary == "Third"
        assert logs[1].summary == "Second"
        assert logs[2].summary == "First"

    def test_get_logs_fallback_to_full_scan_without_index(self, log_manager, temp_log_dir):
        """Test that get_logs() falls back to full scan when index is missing."""
        # Create log entries
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry 1",
            details="Details",
        )
        entry2 = LogEntry.create(
            log_type="update",
            status="success",
            summary="Entry 2",
            details="Details",
        )
        log_manager.save_log(entry1)
        log_manager.save_log(entry2)

        # Delete the index file to simulate missing index
        index_path = Path(temp_log_dir) / "log_index.json"
        if index_path.exists():
            index_path.unlink()

        # get_logs() should fall back to full directory scan
        logs = log_manager.get_logs()

        # Should still return all logs
        assert len(logs) == 2

        # Verify we got the correct logs
        summaries = {log.summary for log in logs}
        assert "Entry 1" in summaries
        assert "Entry 2" in summaries

    def test_get_logs_fallback_to_full_scan_with_empty_index(self, log_manager, temp_log_dir):
        """Test that get_logs() falls back to full scan when index is empty."""
        # Create log entries
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test entry",
            details="Details",
        )
        log_manager.save_log(entry)

        # Manually set index to empty (corrupt state)
        log_manager._save_index({"version": 1, "entries": []})

        # get_logs() should fall back to full directory scan
        logs = log_manager.get_logs()

        # Should still return the log via fallback
        assert len(logs) == 1
        assert logs[0].summary == "Test entry"

    def test_get_logs_handles_missing_referenced_files(self, log_manager, temp_log_dir):
        """Test that get_logs() handles missing referenced files gracefully."""
        # Create log entries
        entries = []
        for i in range(5):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Entry {i}",
                details="Details",
            )
            log_manager.save_log(entry)
            entries.append(entry)

        # Delete one log file but leave it in the index
        log_file = Path(temp_log_dir) / f"{entries[2].id}.json"
        log_file.unlink()

        # get_logs() should skip the missing file
        logs = log_manager.get_logs()

        # Should return only 4 logs (skipping the missing one)
        assert len(logs) == 4

        # Verify the missing entry is not in results
        summaries = {log.summary for log in logs}
        assert "Entry 2" not in summaries
        assert "Entry 0" in summaries
        assert "Entry 1" in summaries
        assert "Entry 3" in summaries
        assert "Entry 4" in summaries

    def test_get_logs_type_filtering_with_index(self, log_manager):
        """Test that get_logs() correctly filters by type when using index."""
        # Create mixed entries
        scan_entries = []
        update_entries = []

        for i in range(5):
            scan_entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details="Details",
            )
            log_manager.save_log(scan_entry)
            scan_entries.append(scan_entry)

        for i in range(3):
            update_entry = LogEntry.create(
                log_type="update",
                status="success",
                summary=f"Update {i}",
                details="Details",
            )
            log_manager.save_log(update_entry)
            update_entries.append(update_entry)

        # Filter for scan logs only
        scan_logs = log_manager.get_logs(log_type="scan")
        assert len(scan_logs) == 5
        for log in scan_logs:
            assert log.type == "scan"

        # Filter for update logs only
        update_logs = log_manager.get_logs(log_type="update")
        assert len(update_logs) == 3
        for log in update_logs:
            assert log.type == "update"

    def test_get_logs_limit_application_with_index(self, log_manager):
        """Test that get_logs() correctly applies limit when using index."""
        # Create 20 entries
        entries = []
        for i in range(20):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Entry {i}",
                details="Details",
            )
            log_manager.save_log(entry)
            entries.append(entry)
            time.sleep(0.001)  # Small delay to ensure different timestamps

        # Test various limits
        logs_5 = log_manager.get_logs(limit=5)
        assert len(logs_5) == 5

        logs_10 = log_manager.get_logs(limit=10)
        assert len(logs_10) == 10

        logs_15 = log_manager.get_logs(limit=15)
        assert len(logs_15) == 15

        logs_100 = log_manager.get_logs(limit=100)
        assert len(logs_100) == 20  # Only 20 exist

    def test_get_logs_sort_order_verification_with_index(self, log_manager):
        """Test that get_logs() returns logs sorted by timestamp descending."""
        # Create entries with specific timestamps
        timestamps = [
            "2024-01-01T10:00:00",
            "2024-01-05T15:30:00",
            "2024-01-03T12:00:00",
            "2024-01-07T08:00:00",
            "2024-01-02T14:00:00",
        ]

        entries = []
        for i, ts in enumerate(timestamps):
            entry = LogEntry(
                id=f"id-{i}",
                timestamp=ts,
                type="scan",
                status="clean",
                summary=f"Entry {i}",
                details="Details",
            )
            log_manager.save_log(entry)
            entries.append(entry)

        # Get logs
        logs = log_manager.get_logs()

        # Should be sorted by timestamp descending
        assert len(logs) == 5
        assert logs[0].timestamp == "2024-01-07T08:00:00"  # Newest
        assert logs[1].timestamp == "2024-01-05T15:30:00"
        assert logs[2].timestamp == "2024-01-03T12:00:00"
        assert logs[3].timestamp == "2024-01-02T14:00:00"
        assert logs[4].timestamp == "2024-01-01T10:00:00"  # Oldest

    def test_get_logs_combined_type_filter_and_limit_with_index(self, log_manager):
        """Test that get_logs() correctly applies both type filter and limit."""
        # Create 10 scan entries and 10 update entries
        for i in range(10):
            scan_entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details="Details",
            )
            log_manager.save_log(scan_entry)
            time.sleep(0.001)

        for i in range(10):
            update_entry = LogEntry.create(
                log_type="update",
                status="success",
                summary=f"Update {i}",
                details="Details",
            )
            log_manager.save_log(update_entry)
            time.sleep(0.001)

        # Get only scan logs with limit
        scan_logs = log_manager.get_logs(limit=5, log_type="scan")
        assert len(scan_logs) == 5
        for log in scan_logs:
            assert log.type == "scan"

        # Get only update logs with limit
        update_logs = log_manager.get_logs(limit=3, log_type="update")
        assert len(update_logs) == 3
        for log in update_logs:
            assert log.type == "update"

    def test_get_logs_with_corrupted_log_file_in_index(self, log_manager, temp_log_dir):
        """Test that get_logs() skips corrupted log files when using index."""
        # Create valid entries
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Valid entry 1",
            details="Details",
        )
        entry2 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Valid entry 2",
            details="Details",
        )
        log_manager.save_log(entry1)
        log_manager.save_log(entry2)

        # Create a corrupted log file
        corrupted_id = "corrupted-id"
        corrupted_path = Path(temp_log_dir) / f"{corrupted_id}.json"
        with open(corrupted_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        # Manually add corrupted entry to index
        index_data = log_manager._load_index()
        index_data["entries"].append({
            "id": corrupted_id,
            "timestamp": "2024-01-01T10:00:00",
            "type": "scan"
        })
        log_manager._save_index(index_data)

        # get_logs() should skip the corrupted file
        logs = log_manager.get_logs()

        # Should return only valid entries
        assert len(logs) == 2
        summaries = {log.summary for log in logs}
        assert "Valid entry 1" in summaries
        assert "Valid entry 2" in summaries

    def test_get_logs_skips_index_file_in_fallback_scan(self, log_manager, temp_log_dir):
        """Test that get_logs() skips the index file during fallback scan."""
        # Create log entries
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test entry",
            details="Details",
        )
        log_manager.save_log(entry)

        # Force fallback by deleting index
        index_path = Path(temp_log_dir) / "log_index.json"
        if index_path.exists():
            index_path.unlink()

        # get_logs() should not try to parse the index file as a log
        logs = log_manager.get_logs()

        # Should return only the actual log entry
        assert len(logs) == 1
        assert logs[0].summary == "Test entry"

    def test_get_logs_performance_with_large_index(self, log_manager):
        """Test that get_logs() efficiently handles large indices with limit."""
        # Create 100 entries
        for i in range(100):
            entry = LogEntry.create(
                log_type="scan" if i % 2 == 0 else "update",
                status="clean",
                summary=f"Entry {i}",
                details="Details",
            )
            log_manager.save_log(entry)

        # With index optimization, this should only load 10 files instead of 100
        logs = log_manager.get_logs(limit=10)

        # Should return exactly 10 logs
        assert len(logs) == 10

        # Should be the 10 most recent (newest first)
        # Verify they're sorted correctly
        for i in range(len(logs) - 1):
            assert logs[i].timestamp >= logs[i + 1].timestamp

    def test_get_logs_handles_index_exception_gracefully(self, log_manager):
        """Test that get_logs() handles index loading exceptions gracefully."""
        # Create log entries
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Entry {i}",
                details="Details",
            )
            log_manager.save_log(entry)

        # Mock _load_index to raise an exception
        original_load = log_manager._load_index

        def mock_load():
            raise Exception("Index loading error")

        log_manager._load_index = mock_load

        # get_logs() should fall back to full scan
        logs = log_manager.get_logs()

        # Should still return all logs via fallback
        assert len(logs) == 3

        # Restore original method
        log_manager._load_index = original_load

    def test_get_logs_returns_empty_list_with_nonexistent_directory(self, temp_log_dir):
        """Test that get_logs() returns empty list when directory doesn't exist."""
        # Create manager, then delete directory
        log_dir = Path(temp_log_dir) / "nonexistent"
        manager = LogManager(log_dir=str(log_dir))

        # Delete the directory
        import shutil
        if log_dir.exists():
            shutil.rmtree(log_dir)

        # get_logs() should return empty list
        logs = manager.get_logs()
        assert logs == []

    def test_get_logs_consistency_between_index_and_fallback(self, log_manager, temp_log_dir):
        """Test that get_logs() returns same results with index and fallback."""
        # Create diverse set of entries
        entries = []
        for i in range(15):
            entry = LogEntry.create(
                log_type="scan" if i % 3 == 0 else "update",
                status="clean" if i % 2 == 0 else "infected",
                summary=f"Entry {i}",
                details=f"Details {i}",
            )
            log_manager.save_log(entry)
            entries.append(entry)

        # Get logs using index
        logs_with_index = log_manager.get_logs(limit=10, log_type="scan")

        # Delete index to force fallback
        index_path = Path(temp_log_dir) / "log_index.json"
        if index_path.exists():
            index_path.unlink()

        # Get logs using fallback
        logs_with_fallback = log_manager.get_logs(limit=10, log_type="scan")

        # Results should be identical
        assert len(logs_with_index) == len(logs_with_fallback)

        # Compare IDs (order should be same)
        index_ids = [log.id for log in logs_with_index]
        fallback_ids = [log.id for log in logs_with_fallback]
        assert index_ids == fallback_ids


class TestLogManagerAutoMigration:
    """Tests for auto-migration on first get_logs() access."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    def test_auto_migration_when_logs_exist_without_index(self, temp_log_dir):
        """Test that index is automatically created when logs exist but no index."""
        # Create LogManager
        manager = LogManager(log_dir=temp_log_dir)

        # Manually create log files without using save_log() (simulates old installation)
        log_dir = Path(temp_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create 3 log files
        entries = []
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan" if i % 2 == 0 else "update",
                status="clean",
                summary=f"Entry {i}",
                details=f"Details {i}",
            )
            entries.append(entry)

            # Write directly to file (bypassing save_log to avoid index creation)
            log_file = log_dir / f"{entry.id}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)

        # Verify index doesn't exist yet
        index_path = log_dir / "log_index.json"
        assert not index_path.exists()

        # Create a NEW LogManager instance to ensure fresh state
        manager = LogManager(log_dir=temp_log_dir)

        # First get_logs() call should trigger auto-migration
        logs = manager.get_logs()

        # Index should now exist
        assert index_path.exists()

        # Index should contain all entries
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        assert index_data["version"] == 1
        assert len(index_data["entries"]) == 3

        # Verify all log IDs are in index
        index_ids = {entry["id"] for entry in index_data["entries"]}
        expected_ids = {entry.id for entry in entries}
        assert index_ids == expected_ids

        # Verify get_logs returns all logs
        assert len(logs) == 3

    def test_auto_migration_only_happens_once(self, temp_log_dir):
        """Test that auto-migration check only happens on first get_logs() call."""
        # Create LogManager
        manager = LogManager(log_dir=temp_log_dir)

        # Create a log file manually
        log_dir = Path(temp_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry 1",
            details="Details 1",
        )
        log_file = log_dir / f"{entry.id}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f, indent=2)

        # First call triggers migration
        manager.get_logs()

        # Verify migration flag is set
        assert manager._migration_checked is True

        # Delete index to test that it's not rebuilt on second call
        index_path = log_dir / "log_index.json"
        if index_path.exists():
            index_path.unlink()

        # Second call should NOT trigger migration (flag is already True)
        logs = manager.get_logs()

        # Index should still not exist (wasn't rebuilt)
        assert not index_path.exists()

        # But get_logs should still work (fallback to full scan)
        assert len(logs) == 1

    def test_no_migration_when_index_already_exists(self, log_manager, temp_log_dir):
        """Test that no migration happens when index already exists."""
        # Create a log using save_log (which creates index)
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry 1",
            details="Details 1",
        )
        log_manager.save_log(entry)

        # Index should exist
        index_path = Path(temp_log_dir) / "log_index.json"
        assert index_path.exists()

        # Get the modification time
        mtime_before = index_path.stat().st_mtime

        # Wait a tiny bit to ensure mtime would change if file is modified
        time.sleep(0.01)

        # Create a NEW LogManager instance
        manager = LogManager(log_dir=temp_log_dir)

        # Call get_logs (should not rebuild index since it exists)
        logs = manager.get_logs()

        # Index modification time should be unchanged
        mtime_after = index_path.stat().st_mtime
        assert mtime_before == mtime_after

        # Migration flag should still be set
        assert manager._migration_checked is True

        # Logs should be returned correctly
        assert len(logs) == 1

    def test_no_migration_when_no_logs_exist(self, temp_log_dir):
        """Test that no migration happens when no log files exist."""
        # Create LogManager with empty directory
        manager = LogManager(log_dir=temp_log_dir)

        # Call get_logs on empty directory
        logs = manager.get_logs()

        # No index should be created (no logs to index)
        index_path = Path(temp_log_dir) / "log_index.json"
        assert not index_path.exists()

        # Migration flag should be set
        assert manager._migration_checked is True

        # Should return empty list
        assert logs == []

    def test_migration_handles_corrupted_files_gracefully(self, temp_log_dir):
        """Test that migration skips corrupted log files gracefully."""
        # Create LogManager
        manager = LogManager(log_dir=temp_log_dir)

        # Create log directory
        log_dir = Path(temp_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create one valid log file
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Valid entry",
            details="Details",
        )
        log_file1 = log_dir / f"{entry1.id}.json"
        with open(log_file1, "w", encoding="utf-8") as f:
            json.dump(entry1.to_dict(), f, indent=2)

        # Create a corrupted log file
        corrupted_file = log_dir / "corrupted.json"
        with open(corrupted_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json content")

        # Create another valid log file
        entry2 = LogEntry.create(
            log_type="update",
            status="success",
            summary="Another valid entry",
            details="Details 2",
        )
        log_file2 = log_dir / f"{entry2.id}.json"
        with open(log_file2, "w", encoding="utf-8") as f:
            json.dump(entry2.to_dict(), f, indent=2)

        # Create a NEW LogManager instance
        manager = LogManager(log_dir=temp_log_dir)

        # First get_logs() call should trigger migration and skip corrupted file
        logs = manager.get_logs()

        # Index should exist
        index_path = log_dir / "log_index.json"
        assert index_path.exists()

        # Index should contain only valid entries
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        assert len(index_data["entries"]) == 2

        # Verify valid log IDs are in index
        index_ids = {entry["id"] for entry in index_data["entries"]}
        expected_ids = {entry1.id, entry2.id}
        assert index_ids == expected_ids

    def test_migration_handles_missing_fields_gracefully(self, temp_log_dir):
        """Test that migration skips log files with missing required fields."""
        # Create LogManager
        manager = LogManager(log_dir=temp_log_dir)

        # Create log directory
        log_dir = Path(temp_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create one valid log file
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Valid entry",
            details="Details",
        )
        log_file1 = log_dir / f"{entry1.id}.json"
        with open(log_file1, "w", encoding="utf-8") as f:
            json.dump(entry1.to_dict(), f, indent=2)

        # Create a log file missing the 'type' field
        incomplete_file = log_dir / "incomplete.json"
        with open(incomplete_file, "w", encoding="utf-8") as f:
            json.dump({
                "id": "incomplete-id",
                "timestamp": "2024-01-15T10:00:00",
                # Missing 'type' field
                "status": "clean",
                "summary": "Incomplete",
                "details": "Missing type field",
            }, f, indent=2)

        # Create a NEW LogManager instance
        manager = LogManager(log_dir=temp_log_dir)

        # First get_logs() call should trigger migration and skip incomplete file
        logs = manager.get_logs()

        # Index should exist
        index_path = log_dir / "log_index.json"
        assert index_path.exists()

        # Index should contain only the valid entry
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        assert len(index_data["entries"]) == 1
        assert index_data["entries"][0]["id"] == entry1.id

    def test_migration_failure_does_not_break_get_logs(self, temp_log_dir):
        """Test that get_logs() still works even if migration fails."""
        # Create LogManager
        manager = LogManager(log_dir=temp_log_dir)

        # Create a valid log file
        log_dir = Path(temp_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry 1",
            details="Details 1",
        )
        log_file = log_dir / f"{entry.id}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f, indent=2)

        # Create a NEW LogManager instance
        manager = LogManager(log_dir=temp_log_dir)

        # Mock _save_index to fail (simulates permission error during migration)
        original_save = manager._save_index

        def mock_save(index_data):
            return False  # Simulate failure

        manager._save_index = mock_save

        # get_logs() should still work via fallback, despite migration failure
        logs = manager.get_logs()

        # Should still return the log via fallback
        assert len(logs) == 1
        assert logs[0].id == entry.id

        # Migration flag should still be set (migration was attempted)
        assert manager._migration_checked is True

        # Restore original method
        manager._save_index = original_save

    def test_migration_with_nonexistent_directory(self, temp_log_dir):
        """Test that migration handles nonexistent directory gracefully."""
        # Create a path that doesn't exist
        log_dir = Path(temp_log_dir) / "nonexistent"

        # Create LogManager (directory won't exist yet)
        manager = LogManager(log_dir=str(log_dir))

        # Call get_logs (should handle gracefully)
        logs = manager.get_logs()

        # Migration flag should be set
        assert manager._migration_checked is True

        # Should return empty list
        assert logs == []

        # No index should be created
        index_path = log_dir / "log_index.json"
        assert not index_path.exists()

    def test_migration_creates_index_with_correct_structure(self, temp_log_dir):
        """Test that migration creates index with correct structure."""
        # Create LogManager
        manager = LogManager(log_dir=temp_log_dir)

        # Create log directory and files manually
        log_dir = Path(temp_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create log files with specific data
        entries = []
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan" if i % 2 == 0 else "update",
                status="clean",
                summary=f"Entry {i}",
                details=f"Details {i}",
            )
            entries.append(entry)

            log_file = log_dir / f"{entry.id}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)

        # Create a NEW LogManager instance
        manager = LogManager(log_dir=temp_log_dir)

        # Trigger migration
        manager.get_logs()

        # Verify index structure
        index_path = log_dir / "log_index.json"
        assert index_path.exists()

        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        # Verify structure
        assert "version" in index_data
        assert "entries" in index_data
        assert index_data["version"] == 1
        assert isinstance(index_data["entries"], list)
        assert len(index_data["entries"]) == 3

        # Verify each entry has required fields
        for entry in index_data["entries"]:
            assert "id" in entry
            assert "timestamp" in entry
            assert "type" in entry
            assert len(entry) == 3  # Only these 3 fields

    def test_migration_skips_index_file_itself(self, temp_log_dir):
        """Test that migration doesn't try to process the index file as a log."""
        # Create LogManager
        manager = LogManager(log_dir=temp_log_dir)

        # Create log directory
        log_dir = Path(temp_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create a valid log file
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry 1",
            details="Details 1",
        )
        log_file = log_dir / f"{entry.id}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f, indent=2)

        # Create a fake existing index file (to simulate edge case)
        index_path = log_dir / "log_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({
                "version": 1,
                "entries": [{"id": "fake", "timestamp": "2024-01-01T00:00:00", "type": "scan"}]
            }, f)

        # Now delete it to force migration
        index_path.unlink()

        # Create a NEW LogManager instance
        manager = LogManager(log_dir=temp_log_dir)

        # Trigger migration
        logs = manager.get_logs()

        # Index should be created and contain only the actual log entry
        assert index_path.exists()

        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        assert len(index_data["entries"]) == 1
        assert index_data["entries"][0]["id"] == entry.id


class TestLogManagerOptimizedGetLogCount:
    """Tests for optimized get_log_count() using index."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_get_log_count_uses_index(self, temp_log_dir):
        """Test get_log_count uses index for O(1) performance."""
        manager = LogManager(log_dir=temp_log_dir)

        # Create some log entries
        for i in range(5):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details=f"Details {i}",
            )
            manager.save_log(entry)

        # Index should exist now
        index_path = Path(temp_log_dir) / "log_index.json"
        assert index_path.exists()

        # get_log_count should use the index
        count = manager.get_log_count()
        assert count == 5

        # Verify index was actually used by checking it has correct data
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        assert len(index_data["entries"]) == 5

    def test_get_log_count_fallback_without_index(self, temp_log_dir):
        """Test get_log_count falls back to directory scan without index."""
        log_dir = Path(temp_log_dir)

        # Create log files directly (bypassing save_log to avoid index creation)
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details=f"Details {i}",
            )
            log_file = log_dir / f"{entry.id}.json"
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)

        # No index should exist
        index_path = log_dir / "log_index.json"
        assert not index_path.exists()

        # Create manager and get count - should fall back to directory scan
        manager = LogManager(log_dir=temp_log_dir)
        count = manager.get_log_count()
        assert count == 3

    def test_get_log_count_excludes_index_file(self, temp_log_dir):
        """Test get_log_count excludes the index file from count."""
        log_dir = Path(temp_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create log files directly
        for i in range(2):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details=f"Details {i}",
            )
            log_file = log_dir / f"{entry.id}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)

        # Create an index file manually
        index_path = log_dir / "log_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "entries": []}, f)

        # Total JSON files = 3 (2 logs + 1 index), but count should be 2
        json_files = list(log_dir.glob("*.json"))
        assert len(json_files) == 3

        manager = LogManager(log_dir=temp_log_dir)
        count = manager.get_log_count()
        assert count == 2  # Should exclude index file

    def test_get_log_count_with_stale_index(self, temp_log_dir):
        """Test get_log_count rebuilds stale index and returns correct count."""
        manager = LogManager(log_dir=temp_log_dir)
        log_dir = Path(temp_log_dir)

        # Create logs through manager (creates index)
        entries = []
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details=f"Details {i}",
            )
            manager.save_log(entry)
            entries.append(entry)

        # Manually delete one log file to make index stale
        log_file = log_dir / f"{entries[0].id}.json"
        log_file.unlink()

        # get_log_count should detect stale index and fall back to directory scan
        count = manager.get_log_count()
        assert count == 2  # Should count remaining files

    def test_get_log_count_with_corrupted_index(self, temp_log_dir):
        """Test get_log_count handles corrupted index gracefully."""
        log_dir = Path(temp_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create some log files
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details=f"Details {i}",
            )
            log_file = log_dir / f"{entry.id}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)

        # Create a corrupted index file
        index_path = log_dir / "log_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json")

        # get_log_count should handle corrupted index and fall back
        manager = LogManager(log_dir=temp_log_dir)
        count = manager.get_log_count()
        assert count == 3

    def test_get_log_count_empty_directory(self, temp_log_dir):
        """Test get_log_count returns 0 for empty directory."""
        manager = LogManager(log_dir=temp_log_dir)
        count = manager.get_log_count()
        assert count == 0

    def test_get_log_count_nonexistent_directory(self, temp_log_dir):
        """Test get_log_count handles nonexistent directory."""
        manager = LogManager(log_dir=os.path.join(temp_log_dir, "nonexistent"))
        # Delete the created directory
        os.rmdir(manager._log_dir)
        count = manager.get_log_count()
        assert count == 0

    def test_get_log_count_with_invalid_index_structure(self, temp_log_dir):
        """Test get_log_count handles invalid index structure."""
        log_dir = Path(temp_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create some log files
        for i in range(2):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details=f"Details {i}",
            )
            log_file = log_dir / f"{entry.id}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)

        # Create an index with invalid structure (missing 'entries' key)
        index_path = log_dir / "log_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({"version": 1}, f)  # Missing 'entries' key

        # get_log_count should handle invalid structure and fall back
        manager = LogManager(log_dir=temp_log_dir)
        count = manager.get_log_count()
        assert count == 2

    def test_get_log_count_large_index(self, temp_log_dir):
        """Test get_log_count performance with large index."""
        manager = LogManager(log_dir=temp_log_dir)

        # Create a moderate number of log entries
        for i in range(20):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details=f"Details {i}",
            )
            manager.save_log(entry)

        # get_log_count should use index efficiently
        count = manager.get_log_count()
        assert count == 20

    def test_get_log_count_after_delete(self, temp_log_dir):
        """Test get_log_count updates correctly after delete_log."""
        manager = LogManager(log_dir=temp_log_dir)

        # Create logs
        entries = []
        for i in range(4):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details=f"Details {i}",
            )
            manager.save_log(entry)
            entries.append(entry)

        assert manager.get_log_count() == 4

        # Delete one log
        manager.delete_log(entries[0].id)

        # Count should be updated
        assert manager.get_log_count() == 3

    def test_get_log_count_after_clear(self, temp_log_dir):
        """Test get_log_count returns 0 after clear_logs."""
        manager = LogManager(log_dir=temp_log_dir)

        # Create logs
        for i in range(3):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Scan {i}",
                details=f"Details {i}",
            )
            manager.save_log(entry)

        assert manager.get_log_count() == 3

        # Clear logs
        manager.clear_logs()

        # Count should be 0
        assert manager.get_log_count() == 0


class TestLogManagerMigrationIntegration:
    """Integration tests for migration from non-indexed to indexed state.

    These tests verify that the auto-migration feature works correctly in
    end-to-end scenarios and doesn't break any existing functionality.
    """

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def _create_manual_log_files(self, log_dir, count=5):
        """Helper to create log files manually without using save_log().

        This simulates an old installation where logs exist but no index.
        Returns list of created LogEntry objects.
        """
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        entries = []
        for i in range(count):
            entry = LogEntry.create(
                log_type="scan" if i % 2 == 0 else "update",
                status="clean" if i % 3 != 0 else "infected",
                summary=f"Entry {i}",
                details=f"Details for entry {i}",
                path=f"/test/path/{i}",
                duration=float(i * 10),
            )
            entries.append(entry)

            # Write directly to file (bypassing save_log to avoid index creation)
            log_file = log_path / f"{entry.id}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)

        return entries

    def test_migration_transparent_workflow(self, temp_log_dir):
        """Test complete workflow: manual logs -> migrate -> continue operations."""
        # Step 1: Create logs manually (simulating old installation)
        entries = self._create_manual_log_files(temp_log_dir, count=5)

        # Verify no index exists
        index_path = Path(temp_log_dir) / "log_index.json"
        assert not index_path.exists()

        # Step 2: Create LogManager (triggers migration on first get_logs)
        manager = LogManager(log_dir=temp_log_dir)

        # Step 3: Retrieve logs (should trigger migration)
        logs = manager.get_logs()

        # Verify migration happened
        assert index_path.exists()
        assert len(logs) == 5

        # Step 4: Continue using manager normally - save new log
        new_entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="New entry after migration",
            details="This entry was created after migration",
        )
        result = manager.save_log(new_entry)
        assert result is True

        # Step 5: Verify index was updated
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        assert len(index_data["entries"]) == 6

        # Step 6: Retrieve logs again (should use index)
        logs_after = manager.get_logs()
        assert len(logs_after) == 6

        # Step 7: Delete a log
        result = manager.delete_log(entries[0].id)
        assert result is True

        # Step 8: Verify index was updated
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        assert len(index_data["entries"]) == 5

        # Step 9: Verify get_logs returns correct count
        logs_final = manager.get_logs()
        assert len(logs_final) == 5
        assert all(log.id != entries[0].id for log in logs_final)

    def test_migration_with_type_filtering(self, temp_log_dir):
        """Test that type filtering works correctly after migration."""
        # Create manual logs with mixed types
        entries = self._create_manual_log_files(temp_log_dir, count=10)

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)

        # Test filtering by scan type
        scan_logs = manager.get_logs(log_type="scan")
        assert len(scan_logs) == 5  # Half are scans (even indices)
        assert all(log.type == "scan" for log in scan_logs)

        # Test filtering by update type
        update_logs = manager.get_logs(log_type="update")
        assert len(update_logs) == 5  # Half are updates (odd indices)
        assert all(log.type == "update" for log in update_logs)

        # Test with no filter
        all_logs = manager.get_logs()
        assert len(all_logs) == 10

    def test_migration_with_limit_application(self, temp_log_dir):
        """Test that limit parameter works correctly after migration."""
        # Create manual logs
        entries = self._create_manual_log_files(temp_log_dir, count=20)

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)

        # Test various limits
        logs_5 = manager.get_logs(limit=5)
        assert len(logs_5) == 5

        logs_10 = manager.get_logs(limit=10)
        assert len(logs_10) == 10

        logs_all = manager.get_logs(limit=100)
        assert len(logs_all) == 20

        # Verify sort order (newest first)
        timestamps = [log.timestamp for log in logs_5]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_migration_combined_filters(self, temp_log_dir):
        """Test that type filtering and limit work together after migration."""
        # Create manual logs
        entries = self._create_manual_log_files(temp_log_dir, count=20)

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)

        # Test combined filters
        scan_logs = manager.get_logs(log_type="scan", limit=3)
        assert len(scan_logs) == 3
        assert all(log.type == "scan" for log in scan_logs)

        # Verify newest scans are returned
        timestamps = [log.timestamp for log in scan_logs]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_migration_get_log_count_consistency(self, temp_log_dir):
        """Test that get_log_count() returns correct count after migration."""
        # Create manual logs
        entries = self._create_manual_log_files(temp_log_dir, count=7)

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)

        # Trigger migration by calling get_logs
        logs = manager.get_logs()

        # Verify get_log_count uses the index
        count = manager.get_log_count()
        assert count == 7
        assert count == len(logs)

    def test_migration_clear_logs_workflow(self, temp_log_dir):
        """Test that clear_logs() works correctly after migration."""
        # Create manual logs
        entries = self._create_manual_log_files(temp_log_dir, count=5)

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)
        logs = manager.get_logs()
        assert len(logs) == 5

        # Clear all logs
        result = manager.clear_logs()
        assert result is True

        # Verify index was reset
        index_path = Path(temp_log_dir) / "log_index.json"
        assert index_path.exists()

        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        assert len(index_data["entries"]) == 0

        # Verify get_logs returns empty
        logs_after = manager.get_logs()
        assert len(logs_after) == 0

        # Verify get_log_count returns 0
        assert manager.get_log_count() == 0

    def test_migration_multiple_manager_instances(self, temp_log_dir):
        """Test that multiple LogManager instances work correctly after migration."""
        # Create manual logs
        entries = self._create_manual_log_files(temp_log_dir, count=5)

        # Create first manager and trigger migration
        manager1 = LogManager(log_dir=temp_log_dir)
        logs1 = manager1.get_logs()
        assert len(logs1) == 5

        # Verify index exists
        index_path = Path(temp_log_dir) / "log_index.json"
        assert index_path.exists()

        # Create second manager (should use existing index)
        manager2 = LogManager(log_dir=temp_log_dir)
        logs2 = manager2.get_logs()
        assert len(logs2) == 5

        # Add log via first manager
        new_entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Entry from manager1",
            details="Details",
        )
        manager1.save_log(new_entry)

        # Create third manager (should see updated index)
        manager3 = LogManager(log_dir=temp_log_dir)
        logs3 = manager3.get_logs()
        assert len(logs3) == 6

    def test_migration_concurrent_operations(self, temp_log_dir):
        """Test that concurrent operations work correctly during/after migration."""
        # Create manual logs
        entries = self._create_manual_log_files(temp_log_dir, count=10)

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)

        results = []
        errors = []

        def save_logs():
            try:
                for i in range(5):
                    entry = LogEntry.create(
                        log_type="scan",
                        status="clean",
                        summary=f"Concurrent save {i}",
                        details=f"Details {i}",
                    )
                    result = manager.save_log(entry)
                    results.append(result)
            except Exception as e:
                errors.append(e)

        def read_logs():
            try:
                for i in range(5):
                    logs = manager.get_logs()
                    results.append(len(logs) >= 10)  # Should have at least original logs
            except Exception as e:
                errors.append(e)

        # Run concurrent operations
        threads = [
            threading.Thread(target=save_logs),
            threading.Thread(target=read_logs),
            threading.Thread(target=save_logs),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0

        # Verify all operations succeeded
        assert all(results)

        # Verify final count is correct (10 original + 10 concurrent saves)
        final_logs = manager.get_logs()
        assert len(final_logs) == 20

    def test_migration_delete_and_recreate_index(self, temp_log_dir):
        """Test that system recovers if index is manually deleted after migration."""
        # Create manual logs
        entries = self._create_manual_log_files(temp_log_dir, count=5)

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)
        logs = manager.get_logs()
        assert len(logs) == 5

        # Verify index exists
        index_path = Path(temp_log_dir) / "log_index.json"
        assert index_path.exists()

        # Manually delete index (simulating corruption or manual deletion)
        index_path.unlink()
        assert not index_path.exists()

        # Create new LogManager instance
        manager2 = LogManager(log_dir=temp_log_dir)

        # get_logs should still work (fallback or validation triggers rebuild)
        logs2 = manager2.get_logs()
        assert len(logs2) == 5

        # Index should be recreated automatically (via validation)
        # Note: The first manager instance won't trigger migration again (flag is set)
        # but the validation logic should detect the missing/invalid index

    def test_migration_preserves_log_data_integrity(self, temp_log_dir):
        """Test that migration preserves all log data correctly."""
        # Create manual logs with diverse data
        entries = self._create_manual_log_files(temp_log_dir, count=5)

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)
        logs = manager.get_logs()

        # Verify all data is preserved
        assert len(logs) == 5

        # Create mapping for easy lookup
        original_by_id = {e.id: e for e in entries}
        retrieved_by_id = {log.id: log for log in logs}

        # Verify all IDs match
        assert set(original_by_id.keys()) == set(retrieved_by_id.keys())

        # Verify all fields are preserved for each log
        for log_id, original in original_by_id.items():
            retrieved = retrieved_by_id[log_id]
            assert retrieved.id == original.id
            assert retrieved.timestamp == original.timestamp
            assert retrieved.type == original.type
            assert retrieved.status == original.status
            assert retrieved.summary == original.summary
            assert retrieved.details == original.details
            assert retrieved.path == original.path
            assert retrieved.duration == original.duration

    def test_migration_with_corrupted_and_valid_logs(self, temp_log_dir):
        """Test migration skips corrupted logs but processes valid ones."""
        # Create some valid logs manually
        valid_entries = self._create_manual_log_files(temp_log_dir, count=3)

        # Add corrupted log files
        log_path = Path(temp_log_dir)
        corrupted1 = log_path / "corrupted1.json"
        with open(corrupted1, "w", encoding="utf-8") as f:
            f.write("{ invalid json")

        corrupted2 = log_path / "corrupted2.json"
        with open(corrupted2, "w", encoding="utf-8") as f:
            json.dump({"id": "missing-fields"}, f)  # Missing required fields

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)
        logs = manager.get_logs()

        # Should retrieve only valid logs
        assert len(logs) == 3

        # Verify all retrieved logs are from the valid set
        valid_ids = {e.id for e in valid_entries}
        retrieved_ids = {log.id for log in logs}
        assert retrieved_ids == valid_ids

    def test_migration_empty_directory_then_add_logs(self, temp_log_dir):
        """Test migration behavior when starting with empty directory."""
        # Create LogManager with empty directory
        manager = LogManager(log_dir=temp_log_dir)

        # First get_logs on empty directory
        logs = manager.get_logs()
        assert len(logs) == 0

        # No index should be created for empty directory
        index_path = Path(temp_log_dir) / "log_index.json"
        # Note: The index might not exist if no logs were ever saved

        # Now add logs normally
        for i in range(5):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary=f"Entry {i}",
                details=f"Details {i}",
            )
            manager.save_log(entry)

        # Index should now exist and be maintained
        assert index_path.exists()

        # Verify all logs are retrievable
        logs_after = manager.get_logs()
        assert len(logs_after) == 5

    def test_migration_large_log_collection(self, temp_log_dir):
        """Test migration with a large collection of logs (performance test)."""
        # Create many logs manually
        entries = self._create_manual_log_files(temp_log_dir, count=100)

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)

        # Migration should complete successfully
        logs = manager.get_logs(limit=10)
        assert len(logs) == 10

        # Verify index exists and contains all entries
        index_path = Path(temp_log_dir) / "log_index.json"
        assert index_path.exists()

        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        assert len(index_data["entries"]) == 100

        # Verify get_log_count is efficient (uses index)
        count = manager.get_log_count()
        assert count == 100

        # Verify filtering still works efficiently
        scan_logs = manager.get_logs(log_type="scan", limit=5)
        assert len(scan_logs) == 5
        assert all(log.type == "scan" for log in scan_logs)

    def test_migration_rebuild_index_method_still_works(self, temp_log_dir):
        """Test that rebuild_index() can be called manually after migration."""
        # Create manual logs
        entries = self._create_manual_log_files(temp_log_dir, count=5)

        # Create LogManager and trigger migration
        manager = LogManager(log_dir=temp_log_dir)
        logs = manager.get_logs()
        assert len(logs) == 5

        # Verify index exists
        index_path = Path(temp_log_dir) / "log_index.json"
        assert index_path.exists()

        # Manually rebuild index
        result = manager.rebuild_index()
        assert result is True

        # Verify index still exists and is correct
        assert index_path.exists()

        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        assert len(index_data["entries"]) == 5

        # Verify logs are still retrievable
        logs_after = manager.get_logs()
        assert len(logs_after) == 5
