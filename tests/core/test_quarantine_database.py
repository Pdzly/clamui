# ClamUI QuarantineDatabase Tests
"""Unit tests for the QuarantineDatabase and QuarantineEntry classes."""

import os
import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest

from src.core.quarantine.database import (
    QuarantineDatabase,
    QuarantineEntry,
)


class TestQuarantineEntry:
    """Tests for the QuarantineEntry dataclass."""

    def test_to_dict(self):
        """Test QuarantineEntry.to_dict serialization."""
        entry = QuarantineEntry(
            id=1,
            original_path="/home/user/malware.exe",
            quarantine_path="/var/clamui/quarantine/abc123.quar",
            threat_name="Win.Trojan.Generic",
            detection_date="2024-01-15T10:30:00",
            file_size=1024,
            file_hash="abc123def456",
        )
        data = entry.to_dict()

        assert data["id"] == 1
        assert data["original_path"] == "/home/user/malware.exe"
        assert data["quarantine_path"] == "/var/clamui/quarantine/abc123.quar"
        assert data["threat_name"] == "Win.Trojan.Generic"
        assert data["detection_date"] == "2024-01-15T10:30:00"
        assert data["file_size"] == 1024
        assert data["file_hash"] == "abc123def456"

    def test_from_row(self):
        """Test QuarantineEntry.from_row deserialization."""
        row = (
            42,
            "/original/path/file.exe",
            "/quarantine/path/uuid.quar",
            "Eicar-Test-Signature",
            "2024-02-20T14:00:00",
            2048,
            "sha256hashvalue",
        )
        entry = QuarantineEntry.from_row(row)

        assert entry.id == 42
        assert entry.original_path == "/original/path/file.exe"
        assert entry.quarantine_path == "/quarantine/path/uuid.quar"
        assert entry.threat_name == "Eicar-Test-Signature"
        assert entry.detection_date == "2024-02-20T14:00:00"
        assert entry.file_size == 2048
        assert entry.file_hash == "sha256hashvalue"

    def test_roundtrip_serialization(self):
        """Test that to_dict and from_row are consistent."""
        original = QuarantineEntry(
            id=99,
            original_path="/test/malware.bin",
            quarantine_path="/quarantine/test.quar",
            threat_name="TestThreat",
            detection_date="2024-03-10T08:15:30",
            file_size=4096,
            file_hash="roundtriphash123",
        )
        data = original.to_dict()

        # Simulate database row from dict values
        row = (
            data["id"],
            data["original_path"],
            data["quarantine_path"],
            data["threat_name"],
            data["detection_date"],
            data["file_size"],
            data["file_hash"],
        )
        restored = QuarantineEntry.from_row(row)

        assert restored.id == original.id
        assert restored.original_path == original.original_path
        assert restored.quarantine_path == original.quarantine_path
        assert restored.threat_name == original.threat_name
        assert restored.detection_date == original.detection_date
        assert restored.file_size == original.file_size
        assert restored.file_hash == original.file_hash


class TestQuarantineDatabase:
    """Tests for the QuarantineDatabase class."""

    @pytest.fixture
    def temp_db_dir(self):
        """Create a temporary directory for database storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def db(self, temp_db_dir):
        """Create a QuarantineDatabase with a temporary database."""
        db_path = os.path.join(temp_db_dir, "test_quarantine.db")
        return QuarantineDatabase(db_path=db_path)

    def test_init_creates_database_directory(self, temp_db_dir):
        """Test that QuarantineDatabase creates the database directory on init."""
        db_path = os.path.join(temp_db_dir, "subdir", "nested", "quarantine.db")
        _db = QuarantineDatabase(db_path=db_path)
        assert Path(db_path).parent.exists()

    def test_init_with_default_directory(self, monkeypatch):
        """Test QuarantineDatabase uses XDG_DATA_HOME by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("XDG_DATA_HOME", tmpdir)
            db = QuarantineDatabase()
            expected_path = Path(tmpdir) / "clamui" / "quarantine.db"
            assert db._db_path == expected_path

    def test_init_creates_schema(self, db, temp_db_dir):
        """Test that database schema is created on init."""
        # Verify the table exists by querying it
        db_path = os.path.join(temp_db_dir, "test_quarantine.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='quarantine'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None
        assert result[0] == "quarantine"

    def test_add_entry(self, db):
        """Test adding a quarantine entry."""
        entry_id = db.add_entry(
            original_path="/home/user/infected.exe",
            quarantine_path="/quarantine/uuid1.quar",
            threat_name="Win.Malware.Test",
            file_size=1024,
            file_hash="testhash123",
        )

        assert entry_id is not None
        assert entry_id > 0

    def test_add_entry_sets_detection_date(self, db):
        """Test that add_entry automatically sets detection_date."""
        before = datetime.now()
        entry_id = db.add_entry(
            original_path="/test/file.exe",
            quarantine_path="/quarantine/file.quar",
            threat_name="TestThreat",
            file_size=512,
            file_hash="hash1",
        )
        after = datetime.now()

        entry = db.get_entry(entry_id)
        detection_time = datetime.fromisoformat(entry.detection_date)
        assert before <= detection_time <= after

    def test_add_entry_duplicate_quarantine_path_fails(self, db):
        """Test that adding duplicate quarantine_path fails."""
        db.add_entry(
            original_path="/path1/file.exe",
            quarantine_path="/quarantine/unique.quar",
            threat_name="Threat1",
            file_size=100,
            file_hash="hash1",
        )
        # Same quarantine_path should fail (UNIQUE constraint)
        result = db.add_entry(
            original_path="/path2/file.exe",
            quarantine_path="/quarantine/unique.quar",
            threat_name="Threat2",
            file_size=200,
            file_hash="hash2",
        )
        assert result is None

    def test_get_entry(self, db):
        """Test retrieving a specific entry by ID."""
        entry_id = db.add_entry(
            original_path="/home/user/test.exe",
            quarantine_path="/quarantine/test.quar",
            threat_name="TestThreat",
            file_size=2048,
            file_hash="abc123",
        )

        entry = db.get_entry(entry_id)
        assert entry is not None
        assert entry.id == entry_id
        assert entry.original_path == "/home/user/test.exe"
        assert entry.quarantine_path == "/quarantine/test.quar"
        assert entry.threat_name == "TestThreat"
        assert entry.file_size == 2048
        assert entry.file_hash == "abc123"

    def test_get_entry_not_found(self, db):
        """Test get_entry returns None for non-existent ID."""
        result = db.get_entry(999999)
        assert result is None

    def test_get_entry_by_original_path(self, db):
        """Test retrieving an entry by original path."""
        db.add_entry(
            original_path="/specific/original/path.exe",
            quarantine_path="/quarantine/specific.quar",
            threat_name="SpecificThreat",
            file_size=3072,
            file_hash="specifichash",
        )

        entry = db.get_entry_by_original_path("/specific/original/path.exe")
        assert entry is not None
        assert entry.original_path == "/specific/original/path.exe"
        assert entry.threat_name == "SpecificThreat"

    def test_get_entry_by_original_path_not_found(self, db):
        """Test get_entry_by_original_path returns None for non-existent path."""
        result = db.get_entry_by_original_path("/nonexistent/path.exe")
        assert result is None

    def test_get_all_entries_empty(self, db):
        """Test get_all_entries returns empty list when no entries exist."""
        entries = db.get_all_entries()
        assert entries == []

    def test_get_all_entries_returns_saved_entries(self, db):
        """Test get_all_entries returns previously saved entries."""
        db.add_entry(
            original_path="/file1.exe",
            quarantine_path="/quarantine/file1.quar",
            threat_name="Threat1",
            file_size=100,
            file_hash="hash1",
        )
        time.sleep(0.01)  # Ensure different timestamps
        db.add_entry(
            original_path="/file2.exe",
            quarantine_path="/quarantine/file2.quar",
            threat_name="Threat2",
            file_size=200,
            file_hash="hash2",
        )

        entries = db.get_all_entries()
        assert len(entries) == 2

    def test_get_all_entries_sorted_by_date_descending(self, db, temp_db_dir):
        """Test that get_all_entries returns entries sorted by date (newest first)."""
        # Insert entries with explicit dates via direct SQL
        db_path = os.path.join(temp_db_dir, "test_quarantine.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO quarantine
            (original_path, quarantine_path, threat_name, detection_date, file_size, file_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/oldest.exe", "/quarantine/oldest.quar", "ThreatOld", "2024-01-01T10:00:00", 100, "hash1"),
        )
        conn.execute(
            """
            INSERT INTO quarantine
            (original_path, quarantine_path, threat_name, detection_date, file_size, file_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/newest.exe", "/quarantine/newest.quar", "ThreatNew", "2024-03-01T10:00:00", 300, "hash3"),
        )
        conn.execute(
            """
            INSERT INTO quarantine
            (original_path, quarantine_path, threat_name, detection_date, file_size, file_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/middle.exe", "/quarantine/middle.quar", "ThreatMid", "2024-02-01T10:00:00", 200, "hash2"),
        )
        conn.commit()
        conn.close()

        entries = db.get_all_entries()
        assert len(entries) == 3
        assert entries[0].original_path == "/newest.exe"
        assert entries[1].original_path == "/middle.exe"
        assert entries[2].original_path == "/oldest.exe"

    def test_remove_entry(self, db):
        """Test removing a specific entry."""
        entry_id = db.add_entry(
            original_path="/to/remove.exe",
            quarantine_path="/quarantine/remove.quar",
            threat_name="RemoveThreat",
            file_size=512,
            file_hash="removehash",
        )

        # Verify it exists
        assert db.get_entry(entry_id) is not None

        # Remove it
        result = db.remove_entry(entry_id)
        assert result is True

        # Should be gone
        assert db.get_entry(entry_id) is None

    def test_remove_entry_not_found(self, db):
        """Test remove_entry returns False for non-existent ID."""
        result = db.remove_entry(999999)
        assert result is False

    def test_get_total_size(self, db):
        """Test calculating total size of quarantined files."""
        db.add_entry(
            original_path="/file1.exe",
            quarantine_path="/quarantine/file1.quar",
            threat_name="Threat1",
            file_size=1000,
            file_hash="hash1",
        )
        db.add_entry(
            original_path="/file2.exe",
            quarantine_path="/quarantine/file2.quar",
            threat_name="Threat2",
            file_size=2000,
            file_hash="hash2",
        )
        db.add_entry(
            original_path="/file3.exe",
            quarantine_path="/quarantine/file3.quar",
            threat_name="Threat3",
            file_size=3000,
            file_hash="hash3",
        )

        total = db.get_total_size()
        assert total == 6000

    def test_get_total_size_empty(self, db):
        """Test get_total_size returns 0 when no entries exist."""
        total = db.get_total_size()
        assert total == 0

    def test_get_entry_count(self, db):
        """Test get_entry_count returns correct count."""
        assert db.get_entry_count() == 0

        for i in range(5):
            db.add_entry(
                original_path=f"/file{i}.exe",
                quarantine_path=f"/quarantine/file{i}.quar",
                threat_name=f"Threat{i}",
                file_size=100 * i,
                file_hash=f"hash{i}",
            )

        assert db.get_entry_count() == 5

    def test_get_old_entries(self, db, temp_db_dir):
        """Test getting entries older than specified days."""
        db_path = os.path.join(temp_db_dir, "test_quarantine.db")
        conn = sqlite3.connect(db_path)

        # Old entry (60 days ago)
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        conn.execute(
            """
            INSERT INTO quarantine
            (original_path, quarantine_path, threat_name, detection_date, file_size, file_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/old.exe", "/quarantine/old.quar", "OldThreat", old_date, 100, "oldhash"),
        )

        # Recent entry (5 days ago)
        recent_date = (datetime.now() - timedelta(days=5)).isoformat()
        conn.execute(
            """
            INSERT INTO quarantine
            (original_path, quarantine_path, threat_name, detection_date, file_size, file_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/recent.exe", "/quarantine/recent.quar", "RecentThreat", recent_date, 200, "recenthash"),
        )
        conn.commit()
        conn.close()

        # Get entries older than 30 days
        old_entries = db.get_old_entries(days=30)
        assert len(old_entries) == 1
        assert old_entries[0].original_path == "/old.exe"

    def test_get_old_entries_empty(self, db):
        """Test get_old_entries returns empty list when no old entries exist."""
        # Add only recent entry
        db.add_entry(
            original_path="/recent.exe",
            quarantine_path="/quarantine/recent.quar",
            threat_name="RecentThreat",
            file_size=100,
            file_hash="hash",
        )

        old_entries = db.get_old_entries(days=30)
        assert len(old_entries) == 0

    def test_cleanup_old_entries(self, db, temp_db_dir):
        """Test removing entries older than specified days."""
        db_path = os.path.join(temp_db_dir, "test_quarantine.db")
        conn = sqlite3.connect(db_path)

        # Old entries (60 days ago)
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        for i in range(3):
            conn.execute(
                """
                INSERT INTO quarantine
                (original_path, quarantine_path, threat_name, detection_date, file_size, file_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (f"/old{i}.exe", f"/quarantine/old{i}.quar", f"OldThreat{i}", old_date, 100, f"oldhash{i}"),
            )

        # Recent entry (5 days ago)
        recent_date = (datetime.now() - timedelta(days=5)).isoformat()
        conn.execute(
            """
            INSERT INTO quarantine
            (original_path, quarantine_path, threat_name, detection_date, file_size, file_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/recent.exe", "/quarantine/recent.quar", "RecentThreat", recent_date, 200, "recenthash"),
        )
        conn.commit()
        conn.close()

        # Initial count
        assert db.get_entry_count() == 4

        # Cleanup old entries
        removed_count = db.cleanup_old_entries(days=30)
        assert removed_count == 3

        # Verify only recent entry remains
        assert db.get_entry_count() == 1
        entries = db.get_all_entries()
        assert entries[0].original_path == "/recent.exe"

    def test_cleanup_old_entries_empty(self, db):
        """Test cleanup_old_entries returns 0 when no old entries exist."""
        # Add only recent entry
        db.add_entry(
            original_path="/recent.exe",
            quarantine_path="/quarantine/recent.quar",
            threat_name="RecentThreat",
            file_size=100,
            file_hash="hash",
        )

        removed_count = db.cleanup_old_entries(days=30)
        assert removed_count == 0

    def test_entry_exists(self, db):
        """Test checking if an entry exists for a path."""
        db.add_entry(
            original_path="/exists/file.exe",
            quarantine_path="/quarantine/exists.quar",
            threat_name="ExistsThreat",
            file_size=100,
            file_hash="existshash",
        )

        assert db.entry_exists("/exists/file.exe") is True
        assert db.entry_exists("/nonexistent/file.exe") is False

    def test_entry_exists_empty_database(self, db):
        """Test entry_exists returns False on empty database."""
        assert db.entry_exists("/any/path.exe") is False

    def test_close(self, db):
        """Test close method doesn't raise errors."""
        # The close method should be callable without errors
        db.close()
        # Database should still be usable after close (connections are per-operation)
        assert db.get_entry_count() == 0


class TestQuarantineDatabaseThreadSafety:
    """Tests for thread safety in QuarantineDatabase."""

    @pytest.fixture
    def db(self):
        """Create a QuarantineDatabase with a temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "thread_test.db")
            yield QuarantineDatabase(db_path=db_path)

    def test_concurrent_add_operations(self, db):
        """Test that concurrent add operations don't corrupt data."""
        errors = []
        entry_ids = []
        lock = threading.Lock()

        def add_entry(index):
            try:
                entry_id = db.add_entry(
                    original_path=f"/concurrent/file{index}.exe",
                    quarantine_path=f"/quarantine/concurrent{index}.quar",
                    threat_name=f"ConcurrentThreat{index}",
                    file_size=100 * index,
                    file_hash=f"hash{index}",
                )
                if entry_id is None:
                    errors.append(f"Failed to add entry {index}")
                else:
                    with lock:
                        entry_ids.append(entry_id)
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = []
        for i in range(20):
            t = threading.Thread(target=add_entry, args=(i,))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all entries were saved
        assert len(entry_ids) == 20
        assert db.get_entry_count() == 20

    def test_concurrent_read_operations(self, db):
        """Test that concurrent read operations work correctly."""
        # Add some entries first
        for i in range(10):
            db.add_entry(
                original_path=f"/read/file{i}.exe",
                quarantine_path=f"/quarantine/read{i}.quar",
                threat_name=f"ReadThreat{i}",
                file_size=100 * i,
                file_hash=f"readhash{i}",
            )

        errors = []
        results = []
        lock = threading.Lock()

        def read_entries(thread_id):
            try:
                entries = db.get_all_entries()
                count = db.get_entry_count()
                total_size = db.get_total_size()
                with lock:
                    results.append({
                        "thread": thread_id,
                        "entries": len(entries),
                        "count": count,
                        "total_size": total_size,
                    })
            except Exception as e:
                errors.append(str(e))

        # Create multiple read threads
        threads = []
        for i in range(20):
            t = threading.Thread(target=read_entries, args=(i,))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all reads returned consistent data
        assert len(results) == 20
        for result in results:
            assert result["entries"] == 10
            assert result["count"] == 10

    def test_concurrent_read_write_operations(self, db):
        """Test that concurrent read and write operations work correctly."""
        errors = []
        write_count = [0]
        read_count = [0]
        lock = threading.Lock()

        def write_entry(index):
            try:
                entry_id = db.add_entry(
                    original_path=f"/mixed/file{index}.exe",
                    quarantine_path=f"/quarantine/mixed{index}.quar",
                    threat_name=f"MixedThreat{index}",
                    file_size=100,
                    file_hash=f"mixedhash{index}",
                )
                if entry_id:
                    with lock:
                        write_count[0] += 1
            except Exception as e:
                errors.append(f"Write error: {e}")

        def read_entries():
            try:
                entries = db.get_all_entries()
                with lock:
                    read_count[0] += 1
            except Exception as e:
                errors.append(f"Read error: {e}")

        # Create mixed read/write threads
        threads = []
        for i in range(15):
            t = threading.Thread(target=write_entry, args=(i,))
            threads.append(t)
        for _ in range(15):
            t = threading.Thread(target=read_entries)
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify writes completed
        assert write_count[0] == 15
        assert read_count[0] == 15


class TestQuarantineDatabaseErrorHandling:
    """Tests for error handling in QuarantineDatabase."""

    @pytest.fixture
    def temp_db_dir(self):
        """Create a temporary directory for database storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_handles_invalid_db_path_gracefully(self, temp_db_dir):
        """Test that database handles invalid path gracefully."""
        # Try to create database in a path that doesn't exist
        # The class should handle this gracefully
        db = QuarantineDatabase(db_path="/nonexistent/path/that/cannot/be/created/db.db")
        # Operations should return failure rather than raising
        result = db.add_entry(
            original_path="/test.exe",
            quarantine_path="/quarantine/test.quar",
            threat_name="Test",
            file_size=100,
            file_hash="hash",
        )
        # Should return None on failure
        assert result is None

    def test_get_entry_handles_db_errors(self, temp_db_dir):
        """Test that get_entry handles database errors gracefully."""
        db_path = os.path.join(temp_db_dir, "test.db")
        db = QuarantineDatabase(db_path=db_path)

        # Add an entry
        entry_id = db.add_entry(
            original_path="/test.exe",
            quarantine_path="/quarantine/test.quar",
            threat_name="Test",
            file_size=100,
            file_hash="hash",
        )
        assert entry_id is not None

        # Mock _get_connection to raise an error
        with mock.patch.object(db, "_get_connection", side_effect=sqlite3.Error("Test error")):
            result = db.get_entry(entry_id)
            assert result is None

    def test_get_all_entries_handles_db_errors(self, temp_db_dir):
        """Test that get_all_entries handles database errors gracefully."""
        db_path = os.path.join(temp_db_dir, "test.db")
        db = QuarantineDatabase(db_path=db_path)

        with mock.patch.object(db, "_get_connection", side_effect=sqlite3.Error("Test error")):
            result = db.get_all_entries()
            assert result == []

    def test_remove_entry_handles_db_errors(self, temp_db_dir):
        """Test that remove_entry handles database errors gracefully."""
        db_path = os.path.join(temp_db_dir, "test.db")
        db = QuarantineDatabase(db_path=db_path)

        with mock.patch.object(db, "_get_connection", side_effect=sqlite3.Error("Test error")):
            result = db.remove_entry(1)
            assert result is False

    def test_get_total_size_handles_db_errors(self, temp_db_dir):
        """Test that get_total_size handles database errors gracefully."""
        db_path = os.path.join(temp_db_dir, "test.db")
        db = QuarantineDatabase(db_path=db_path)

        with mock.patch.object(db, "_get_connection", side_effect=sqlite3.Error("Test error")):
            result = db.get_total_size()
            assert result == 0

    def test_get_entry_count_handles_db_errors(self, temp_db_dir):
        """Test that get_entry_count handles database errors gracefully."""
        db_path = os.path.join(temp_db_dir, "test.db")
        db = QuarantineDatabase(db_path=db_path)

        with mock.patch.object(db, "_get_connection", side_effect=sqlite3.Error("Test error")):
            result = db.get_entry_count()
            assert result == 0

    def test_entry_exists_handles_db_errors(self, temp_db_dir):
        """Test that entry_exists handles database errors gracefully."""
        db_path = os.path.join(temp_db_dir, "test.db")
        db = QuarantineDatabase(db_path=db_path)

        with mock.patch.object(db, "_get_connection", side_effect=sqlite3.Error("Test error")):
            result = db.entry_exists("/test.exe")
            assert result is False
