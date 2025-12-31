# ClamUI QuarantineManager Tests
"""Unit tests for the QuarantineManager class."""

import os
import sys
import tempfile
import threading
from pathlib import Path
from unittest import mock

import pytest

# Mock gi module before importing src.core to avoid GTK dependencies in tests
_original_gi = sys.modules.get("gi")
_original_gi_repository = sys.modules.get("gi.repository")

sys.modules["gi"] = mock.MagicMock()
sys.modules["gi.repository"] = mock.MagicMock()

from src.core.quarantine.database import QuarantineDatabase, QuarantineEntry
from src.core.quarantine.file_handler import (
    FileOperationResult,
    FileOperationStatus,
    SecureFileHandler,
)
from src.core.quarantine.manager import (
    QuarantineManager,
    QuarantineResult,
    QuarantineStatus,
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


class TestQuarantineStatus:
    """Tests for the QuarantineStatus enum."""

    def test_quarantine_status_values(self):
        """Test QuarantineStatus enum has expected values."""
        assert QuarantineStatus.SUCCESS.value == "success"
        assert QuarantineStatus.FILE_NOT_FOUND.value == "file_not_found"
        assert QuarantineStatus.PERMISSION_DENIED.value == "permission_denied"
        assert QuarantineStatus.DISK_FULL.value == "disk_full"
        assert QuarantineStatus.DATABASE_ERROR.value == "database_error"
        assert QuarantineStatus.ALREADY_QUARANTINED.value == "already_quarantined"
        assert QuarantineStatus.ENTRY_NOT_FOUND.value == "entry_not_found"
        assert QuarantineStatus.RESTORE_DESTINATION_EXISTS.value == "restore_destination_exists"
        assert QuarantineStatus.ERROR.value == "error"


class TestQuarantineResult:
    """Tests for the QuarantineResult dataclass."""

    def test_quarantine_result_success(self):
        """Test QuarantineResult with successful status."""
        entry = QuarantineEntry(
            id=1,
            original_path="/test/file.exe",
            quarantine_path="/quarantine/file.quar",
            threat_name="TestThreat",
            detection_date="2024-01-01T10:00:00",
            file_size=1024,
            file_hash="abc123",
        )
        result = QuarantineResult(
            status=QuarantineStatus.SUCCESS,
            entry=entry,
            error_message=None,
        )

        assert result.is_success is True
        assert result.status == QuarantineStatus.SUCCESS
        assert result.entry == entry
        assert result.error_message is None

    def test_quarantine_result_failure(self):
        """Test QuarantineResult with failure status."""
        result = QuarantineResult(
            status=QuarantineStatus.FILE_NOT_FOUND,
            entry=None,
            error_message="File not found: /test/file.exe",
        )

        assert result.is_success is False
        assert result.status == QuarantineStatus.FILE_NOT_FOUND
        assert result.entry is None
        assert result.error_message == "File not found: /test/file.exe"

    def test_is_success_property_all_statuses(self):
        """Test is_success property returns correct values for all statuses."""
        # Only SUCCESS should return True
        for status in QuarantineStatus:
            result = QuarantineResult(
                status=status,
                entry=None,
                error_message=None,
            )
            if status == QuarantineStatus.SUCCESS:
                assert result.is_success is True
            else:
                assert result.is_success is False


class TestQuarantineManager:
    """Tests for the QuarantineManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for quarantine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a QuarantineManager with temporary directories."""
        quarantine_dir = os.path.join(temp_dir, "quarantine")
        db_path = os.path.join(temp_dir, "quarantine.db")
        return QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )

    @pytest.fixture
    def test_file(self, temp_dir):
        """Create a temporary test file."""
        file_path = os.path.join(temp_dir, "test_infected.exe")
        with open(file_path, "wb") as f:
            f.write(b"This is test malware content for testing purposes.")
        return file_path

    def test_init_creates_quarantine_directory(self, temp_dir):
        """Test that QuarantineManager creates the quarantine directory on init."""
        quarantine_dir = os.path.join(temp_dir, "subdir", "quarantine")
        db_path = os.path.join(temp_dir, "subdir", "db.db")
        manager = QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )
        assert Path(quarantine_dir).exists()

    def test_quarantine_directory_property(self, manager, temp_dir):
        """Test quarantine_directory property returns correct path."""
        expected = Path(temp_dir) / "quarantine"
        assert manager.quarantine_directory == expected

    def test_quarantine_file_success(self, manager, test_file):
        """Test successfully quarantining a file."""
        result = manager.quarantine_file(test_file, "Win.Trojan.Test")

        assert result.is_success is True
        assert result.status == QuarantineStatus.SUCCESS
        assert result.entry is not None
        assert result.entry.original_path == str(Path(test_file).resolve())
        assert result.entry.threat_name == "Win.Trojan.Test"
        assert result.entry.file_size > 0
        assert len(result.entry.file_hash) == 64  # SHA256 hex length
        assert result.error_message is None

        # Verify original file is moved
        assert not Path(test_file).exists()

        # Verify file is in quarantine
        assert Path(result.entry.quarantine_path).exists()

    def test_quarantine_file_sets_permissions(self, manager, test_file):
        """Test quarantined file has restrictive permissions."""
        result = manager.quarantine_file(test_file, "TestThreat")

        assert result.is_success is True

        # Check quarantined file permissions (should be 0o400 - read-only for owner)
        quarantine_path = Path(result.entry.quarantine_path)
        mode = quarantine_path.stat().st_mode & 0o777
        assert mode == 0o400

    def test_quarantine_file_directory_permissions(self, manager, test_file):
        """Test quarantine directory has restrictive permissions."""
        result = manager.quarantine_file(test_file, "TestThreat")

        assert result.is_success is True

        # Check quarantine directory permissions (should be 0o700 - owner only)
        mode = manager.quarantine_directory.stat().st_mode & 0o777
        assert mode == 0o700

    def test_quarantine_file_file_not_found(self, manager):
        """Test quarantining a file that doesn't exist."""
        result = manager.quarantine_file("/nonexistent/file.exe", "TestThreat")

        assert result.is_success is False
        assert result.status == QuarantineStatus.FILE_NOT_FOUND
        assert result.entry is None
        assert result.error_message is not None

    def test_quarantine_file_already_quarantined(self, manager, test_file):
        """Test quarantining a file that's already quarantined."""
        # First quarantine
        result1 = manager.quarantine_file(test_file, "TestThreat")
        assert result1.is_success is True

        # Create a new file at the same path
        with open(test_file, "wb") as f:
            f.write(b"New content")

        # Try to quarantine again (same original path)
        result2 = manager.quarantine_file(test_file, "TestThreat2")

        assert result2.is_success is False
        assert result2.status == QuarantineStatus.ALREADY_QUARANTINED
        assert result2.entry is None
        assert result2.error_message is not None

    def test_quarantine_file_hash_calculation(self, manager, temp_dir):
        """Test that file hash is correctly calculated before quarantine."""
        # Create file with known content
        test_file = os.path.join(temp_dir, "hash_test.exe")
        content = b"Known content for hash testing"
        with open(test_file, "wb") as f:
            f.write(content)

        # Calculate expected hash
        import hashlib
        expected_hash = hashlib.sha256(content).hexdigest()

        result = manager.quarantine_file(test_file, "TestThreat")

        assert result.is_success is True
        assert result.entry.file_hash == expected_hash

    def test_quarantine_file_database_entry_created(self, manager, test_file):
        """Test that database entry is created on quarantine."""
        result = manager.quarantine_file(test_file, "TestThreat")

        assert result.is_success is True
        assert result.entry.id is not None

        # Verify entry can be retrieved from database
        entry = manager.get_entry(result.entry.id)
        assert entry is not None
        assert entry.original_path == result.entry.original_path


class TestQuarantineManagerRestore:
    """Tests for the QuarantineManager restore operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for quarantine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a QuarantineManager with temporary directories."""
        quarantine_dir = os.path.join(temp_dir, "quarantine")
        db_path = os.path.join(temp_dir, "quarantine.db")
        return QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )

    @pytest.fixture
    def quarantined_file(self, manager, temp_dir):
        """Create and quarantine a test file."""
        file_path = os.path.join(temp_dir, "files", "test.exe")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(b"Test content for restore testing")

        result = manager.quarantine_file(file_path, "TestThreat")
        assert result.is_success is True
        return result.entry

    def test_restore_file_success(self, manager, quarantined_file):
        """Test successfully restoring a quarantined file."""
        result = manager.restore_file(quarantined_file.id)

        assert result.is_success is True
        assert result.status == QuarantineStatus.SUCCESS
        assert result.entry is not None

        # Verify file is restored to original location
        assert Path(quarantined_file.original_path).exists()

        # Verify quarantine file is removed
        assert not Path(quarantined_file.quarantine_path).exists()

        # Verify database entry is removed
        assert manager.get_entry(quarantined_file.id) is None

    def test_restore_file_entry_not_found(self, manager):
        """Test restoring a file with non-existent entry ID."""
        result = manager.restore_file(999999)

        assert result.is_success is False
        assert result.status == QuarantineStatus.ENTRY_NOT_FOUND
        assert result.error_message is not None

    def test_restore_file_destination_exists(self, manager, quarantined_file):
        """Test restoring a file when destination already exists."""
        # Create a file at the original location
        Path(quarantined_file.original_path).parent.mkdir(parents=True, exist_ok=True)
        with open(quarantined_file.original_path, "wb") as f:
            f.write(b"Existing file content")

        result = manager.restore_file(quarantined_file.id)

        assert result.is_success is False
        assert result.status == QuarantineStatus.RESTORE_DESTINATION_EXISTS
        assert result.error_message is not None

    def test_restore_file_creates_parent_directory(self, manager, temp_dir):
        """Test restore creates parent directory if it doesn't exist."""
        # Create and quarantine a file in a nested directory
        nested_dir = os.path.join(temp_dir, "nested", "deep", "path")
        os.makedirs(nested_dir, exist_ok=True)
        file_path = os.path.join(nested_dir, "test.exe")
        with open(file_path, "wb") as f:
            f.write(b"Test content")

        qresult = manager.quarantine_file(file_path, "TestThreat")
        assert qresult.is_success is True

        # Remove the nested directory
        import shutil
        shutil.rmtree(os.path.join(temp_dir, "nested"))

        # Restore should recreate the directory structure
        result = manager.restore_file(qresult.entry.id)

        assert result.is_success is True
        assert Path(file_path).exists()


class TestQuarantineManagerDelete:
    """Tests for the QuarantineManager delete operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for quarantine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a QuarantineManager with temporary directories."""
        quarantine_dir = os.path.join(temp_dir, "quarantine")
        db_path = os.path.join(temp_dir, "quarantine.db")
        return QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )

    @pytest.fixture
    def quarantined_file(self, manager, temp_dir):
        """Create and quarantine a test file."""
        file_path = os.path.join(temp_dir, "test_delete.exe")
        with open(file_path, "wb") as f:
            f.write(b"Test content for delete testing")

        result = manager.quarantine_file(file_path, "TestThreat")
        assert result.is_success is True
        return result.entry

    def test_delete_file_success(self, manager, quarantined_file):
        """Test successfully deleting a quarantined file."""
        result = manager.delete_file(quarantined_file.id)

        assert result.is_success is True
        assert result.status == QuarantineStatus.SUCCESS
        assert result.entry is not None

        # Verify quarantine file is deleted
        assert not Path(quarantined_file.quarantine_path).exists()

        # Verify database entry is removed
        assert manager.get_entry(quarantined_file.id) is None

    def test_delete_file_entry_not_found(self, manager):
        """Test deleting a file with non-existent entry ID."""
        result = manager.delete_file(999999)

        assert result.is_success is False
        assert result.status == QuarantineStatus.ENTRY_NOT_FOUND
        assert result.error_message is not None

    def test_delete_file_permanently_removes(self, manager, quarantined_file):
        """Test that delete permanently removes the file."""
        quarantine_path = Path(quarantined_file.quarantine_path)
        assert quarantine_path.exists()

        result = manager.delete_file(quarantined_file.id)
        assert result.is_success is True

        # File should be completely gone
        assert not quarantine_path.exists()


class TestQuarantineManagerQueries:
    """Tests for the QuarantineManager query operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for quarantine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a QuarantineManager with temporary directories."""
        quarantine_dir = os.path.join(temp_dir, "quarantine")
        db_path = os.path.join(temp_dir, "quarantine.db")
        return QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )

    @pytest.fixture
    def multiple_quarantined_files(self, manager, temp_dir):
        """Create and quarantine multiple test files."""
        entries = []
        for i in range(5):
            file_path = os.path.join(temp_dir, f"test_file_{i}.exe")
            with open(file_path, "wb") as f:
                f.write(f"Test content {i}".encode() * 100)

            result = manager.quarantine_file(file_path, f"Threat{i}")
            assert result.is_success is True
            entries.append(result.entry)
        return entries

    def test_get_entry(self, manager, temp_dir):
        """Test retrieving a specific entry by ID."""
        file_path = os.path.join(temp_dir, "test.exe")
        with open(file_path, "wb") as f:
            f.write(b"Test content")

        qresult = manager.quarantine_file(file_path, "TestThreat")
        assert qresult.is_success is True

        entry = manager.get_entry(qresult.entry.id)
        assert entry is not None
        assert entry.id == qresult.entry.id
        assert entry.threat_name == "TestThreat"

    def test_get_entry_not_found(self, manager):
        """Test get_entry returns None for non-existent ID."""
        entry = manager.get_entry(999999)
        assert entry is None

    def test_get_entry_by_original_path(self, manager, temp_dir):
        """Test retrieving an entry by original path."""
        file_path = os.path.join(temp_dir, "path_test.exe")
        with open(file_path, "wb") as f:
            f.write(b"Test content")

        qresult = manager.quarantine_file(file_path, "TestThreat")
        assert qresult.is_success is True

        resolved_path = str(Path(file_path).resolve())
        entry = manager.get_entry_by_original_path(resolved_path)
        assert entry is not None
        assert entry.original_path == resolved_path

    def test_get_entry_by_original_path_not_found(self, manager):
        """Test get_entry_by_original_path returns None for non-existent path."""
        entry = manager.get_entry_by_original_path("/nonexistent/path.exe")
        assert entry is None

    def test_get_all_entries_empty(self, manager):
        """Test get_all_entries returns empty list when no entries exist."""
        entries = manager.get_all_entries()
        assert entries == []

    def test_get_all_entries(self, manager, multiple_quarantined_files):
        """Test get_all_entries returns all quarantined files."""
        entries = manager.get_all_entries()
        assert len(entries) == 5

    def test_get_total_size(self, manager, multiple_quarantined_files):
        """Test get_total_size calculates correct total."""
        total = manager.get_total_size()
        # Each file has content like "Test content X" * 100
        assert total > 0

        # Verify against sum of individual entries
        entries = manager.get_all_entries()
        expected_total = sum(e.file_size for e in entries)
        assert total == expected_total

    def test_get_total_size_empty(self, manager):
        """Test get_total_size returns 0 when no entries exist."""
        total = manager.get_total_size()
        assert total == 0

    def test_get_entry_count(self, manager, multiple_quarantined_files):
        """Test get_entry_count returns correct count."""
        count = manager.get_entry_count()
        assert count == 5

    def test_get_entry_count_empty(self, manager):
        """Test get_entry_count returns 0 when no entries exist."""
        count = manager.get_entry_count()
        assert count == 0


class TestQuarantineManagerCleanup:
    """Tests for the QuarantineManager cleanup operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for quarantine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a QuarantineManager with temporary directories."""
        quarantine_dir = os.path.join(temp_dir, "quarantine")
        db_path = os.path.join(temp_dir, "quarantine.db")
        return QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )

    def test_get_old_entries(self, manager, temp_dir):
        """Test getting entries older than specified days."""
        import sqlite3
        from datetime import datetime, timedelta

        # Create a recent file
        file_path = os.path.join(temp_dir, "recent.exe")
        with open(file_path, "wb") as f:
            f.write(b"Recent content")
        manager.quarantine_file(file_path, "RecentThreat")

        # Manually insert an old entry into the database
        db_path = os.path.join(temp_dir, "quarantine.db")
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO quarantine
            (original_path, quarantine_path, threat_name, detection_date, file_size, file_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/old/file.exe", "/quarantine/old.quar", "OldThreat", old_date, 100, "oldhash"),
        )
        conn.commit()
        conn.close()

        old_entries = manager.get_old_entries(days=30)
        assert len(old_entries) == 1
        assert old_entries[0].threat_name == "OldThreat"

    def test_get_old_entries_empty(self, manager, temp_dir):
        """Test get_old_entries returns empty list when no old entries."""
        file_path = os.path.join(temp_dir, "recent.exe")
        with open(file_path, "wb") as f:
            f.write(b"Recent content")
        manager.quarantine_file(file_path, "RecentThreat")

        old_entries = manager.get_old_entries(days=30)
        assert len(old_entries) == 0

    def test_cleanup_old_entries(self, manager, temp_dir):
        """Test cleanup removes old entries and files."""
        import sqlite3
        from datetime import datetime, timedelta

        # Create a recent file
        recent_path = os.path.join(temp_dir, "recent.exe")
        with open(recent_path, "wb") as f:
            f.write(b"Recent content")
        recent_result = manager.quarantine_file(recent_path, "RecentThreat")
        assert recent_result.is_success is True

        # Create an old quarantine file manually
        old_quarantine_path = os.path.join(temp_dir, "quarantine", "old_file.quar")
        with open(old_quarantine_path, "wb") as f:
            f.write(b"Old content")
        os.chmod(old_quarantine_path, 0o400)

        # Insert old entry into database
        db_path = os.path.join(temp_dir, "quarantine.db")
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO quarantine
            (original_path, quarantine_path, threat_name, detection_date, file_size, file_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/old/file.exe", old_quarantine_path, "OldThreat", old_date, 100, "oldhash"),
        )
        conn.commit()
        conn.close()

        # Verify initial state
        assert manager.get_entry_count() == 2

        # Cleanup old entries
        removed = manager.cleanup_old_entries(days=30)
        assert removed == 1

        # Verify only recent entry remains
        assert manager.get_entry_count() == 1
        entries = manager.get_all_entries()
        assert entries[0].threat_name == "RecentThreat"


class TestQuarantineManagerIntegrity:
    """Tests for file integrity verification in QuarantineManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for quarantine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a QuarantineManager with temporary directories."""
        quarantine_dir = os.path.join(temp_dir, "quarantine")
        db_path = os.path.join(temp_dir, "quarantine.db")
        return QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )

    @pytest.fixture
    def quarantined_file(self, manager, temp_dir):
        """Create and quarantine a test file."""
        file_path = os.path.join(temp_dir, "integrity_test.exe")
        with open(file_path, "wb") as f:
            f.write(b"Test content for integrity verification")

        result = manager.quarantine_file(file_path, "TestThreat")
        assert result.is_success is True
        return result.entry

    def test_verify_entry_integrity_success(self, manager, quarantined_file):
        """Test integrity verification succeeds for unmodified file."""
        is_valid, error = manager.verify_entry_integrity(quarantined_file.id)

        assert is_valid is True
        assert error is None

    def test_verify_entry_integrity_not_found(self, manager):
        """Test integrity verification fails for non-existent entry."""
        is_valid, error = manager.verify_entry_integrity(999999)

        assert is_valid is False
        assert error is not None
        assert "not found" in error.lower()

    def test_verify_entry_integrity_modified_file(self, manager, quarantined_file):
        """Test integrity verification fails for modified file."""
        # Modify the quarantined file
        quarantine_path = Path(quarantined_file.quarantine_path)
        os.chmod(quarantine_path, 0o644)
        with open(quarantine_path, "wb") as f:
            f.write(b"Modified content - different from original")
        os.chmod(quarantine_path, 0o400)

        is_valid, error = manager.verify_entry_integrity(quarantined_file.id)

        assert is_valid is False
        assert error is not None
        assert "mismatch" in error.lower()


class TestQuarantineManagerInfo:
    """Tests for the QuarantineManager info operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for quarantine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a QuarantineManager with temporary directories."""
        quarantine_dir = os.path.join(temp_dir, "quarantine")
        db_path = os.path.join(temp_dir, "quarantine.db")
        return QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )

    def test_get_quarantine_info_empty(self, manager):
        """Test get_quarantine_info with empty quarantine."""
        info = manager.get_quarantine_info()

        assert "directory_path" in info
        assert "directory_exists" in info
        assert "entry_count" in info
        assert "total_size" in info
        assert "file_count" in info
        assert "permissions" in info

        assert info["directory_exists"] is True
        assert info["entry_count"] == 0
        assert info["total_size"] == 0
        assert info["permissions"] == "700"

    def test_get_quarantine_info_with_files(self, manager, temp_dir):
        """Test get_quarantine_info with quarantined files."""
        # Quarantine some files
        for i in range(3):
            file_path = os.path.join(temp_dir, f"file_{i}.exe")
            with open(file_path, "wb") as f:
                f.write(f"Content {i}".encode() * 100)
            result = manager.quarantine_file(file_path, f"Threat{i}")
            assert result.is_success is True

        info = manager.get_quarantine_info()

        assert info["directory_exists"] is True
        assert info["entry_count"] == 3
        assert info["total_size"] > 0
        assert info["file_count"] == 3


class TestQuarantineManagerAsync:
    """Tests for async operations in QuarantineManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for quarantine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a QuarantineManager with temporary directories."""
        quarantine_dir = os.path.join(temp_dir, "quarantine")
        db_path = os.path.join(temp_dir, "quarantine.db")
        return QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )

    def test_quarantine_file_async_calls_callback(self, manager, temp_dir):
        """Test quarantine_file_async calls callback with result."""
        file_path = os.path.join(temp_dir, "async_test.exe")
        with open(file_path, "wb") as f:
            f.write(b"Async test content")

        callback_results = []
        callback_event = threading.Event()

        def mock_callback(result):
            callback_results.append(result)
            callback_event.set()

        with mock.patch("src.core.quarantine.manager.GLib") as mock_glib:
            mock_glib.idle_add.side_effect = lambda func, *args: func(*args)

            manager.quarantine_file_async(file_path, "TestThreat", mock_callback)
            callback_event.wait(timeout=5)

        assert len(callback_results) == 1
        assert callback_results[0].is_success is True

    def test_restore_file_async_calls_callback(self, manager, temp_dir):
        """Test restore_file_async calls callback with result."""
        # First quarantine a file
        file_path = os.path.join(temp_dir, "restore_async.exe")
        with open(file_path, "wb") as f:
            f.write(b"Restore async test content")

        qresult = manager.quarantine_file(file_path, "TestThreat")
        assert qresult.is_success is True

        callback_results = []
        callback_event = threading.Event()

        def mock_callback(result):
            callback_results.append(result)
            callback_event.set()

        with mock.patch("src.core.quarantine.manager.GLib") as mock_glib:
            mock_glib.idle_add.side_effect = lambda func, *args: func(*args)

            manager.restore_file_async(qresult.entry.id, mock_callback)
            callback_event.wait(timeout=5)

        assert len(callback_results) == 1
        assert callback_results[0].is_success is True

    def test_delete_file_async_calls_callback(self, manager, temp_dir):
        """Test delete_file_async calls callback with result."""
        # First quarantine a file
        file_path = os.path.join(temp_dir, "delete_async.exe")
        with open(file_path, "wb") as f:
            f.write(b"Delete async test content")

        qresult = manager.quarantine_file(file_path, "TestThreat")
        assert qresult.is_success is True

        callback_results = []
        callback_event = threading.Event()

        def mock_callback(result):
            callback_results.append(result)
            callback_event.set()

        with mock.patch("src.core.quarantine.manager.GLib") as mock_glib:
            mock_glib.idle_add.side_effect = lambda func, *args: func(*args)

            manager.delete_file_async(qresult.entry.id, mock_callback)
            callback_event.wait(timeout=5)

        assert len(callback_results) == 1
        assert callback_results[0].is_success is True

    def test_get_all_entries_async_calls_callback(self, manager, temp_dir):
        """Test get_all_entries_async calls callback with entries."""
        # Quarantine some files
        for i in range(3):
            file_path = os.path.join(temp_dir, f"async_entry_{i}.exe")
            with open(file_path, "wb") as f:
                f.write(f"Content {i}".encode())
            manager.quarantine_file(file_path, f"Threat{i}")

        callback_results = []
        callback_event = threading.Event()

        def mock_callback(entries):
            callback_results.append(entries)
            callback_event.set()

        with mock.patch("src.core.quarantine.manager.GLib") as mock_glib:
            mock_glib.idle_add.side_effect = lambda func, *args: func(*args)

            manager.get_all_entries_async(mock_callback)
            callback_event.wait(timeout=5)

        assert len(callback_results) == 1
        assert len(callback_results[0]) == 3

    def test_cleanup_old_entries_async_calls_callback(self, manager, temp_dir):
        """Test cleanup_old_entries_async calls callback with count."""
        callback_results = []
        callback_event = threading.Event()

        def mock_callback(count):
            callback_results.append(count)
            callback_event.set()

        with mock.patch("src.core.quarantine.manager.GLib") as mock_glib:
            mock_glib.idle_add.side_effect = lambda func, *args: func(*args)

            manager.cleanup_old_entries_async(30, mock_callback)
            callback_event.wait(timeout=5)

        assert len(callback_results) == 1
        assert callback_results[0] == 0  # No old entries to clean up


class TestQuarantineManagerThreadSafety:
    """Tests for thread safety in QuarantineManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for quarantine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a QuarantineManager with temporary directories."""
        quarantine_dir = os.path.join(temp_dir, "quarantine")
        db_path = os.path.join(temp_dir, "quarantine.db")
        return QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )

    def test_concurrent_quarantine_operations(self, manager, temp_dir):
        """Test that concurrent quarantine operations don't corrupt data."""
        errors = []
        results = []
        lock = threading.Lock()

        def quarantine_file(index):
            try:
                file_path = os.path.join(temp_dir, f"concurrent_{index}.exe")
                with open(file_path, "wb") as f:
                    f.write(f"Content {index}".encode())

                result = manager.quarantine_file(file_path, f"Threat{index}")
                with lock:
                    if result.is_success:
                        results.append(result.entry.id)
                    else:
                        errors.append(f"Failed to quarantine file {index}: {result.error_message}")
            except Exception as e:
                with lock:
                    errors.append(str(e))

        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=quarantine_file, args=(i,))
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
        assert len(results) == 10
        assert manager.get_entry_count() == 10

    def test_concurrent_read_operations(self, manager, temp_dir):
        """Test that concurrent read operations work correctly."""
        # First add some entries
        for i in range(5):
            file_path = os.path.join(temp_dir, f"read_test_{i}.exe")
            with open(file_path, "wb") as f:
                f.write(f"Content {i}".encode())
            manager.quarantine_file(file_path, f"Threat{i}")

        errors = []
        results = []
        lock = threading.Lock()

        def read_entries(thread_id):
            try:
                entries = manager.get_all_entries()
                count = manager.get_entry_count()
                total_size = manager.get_total_size()
                with lock:
                    results.append({
                        "thread": thread_id,
                        "entries": len(entries),
                        "count": count,
                        "total_size": total_size,
                    })
            except Exception as e:
                with lock:
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
            assert result["entries"] == 5
            assert result["count"] == 5


class TestQuarantineManagerEdgeCases:
    """Tests for edge cases in QuarantineManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for quarantine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a QuarantineManager with temporary directories."""
        quarantine_dir = os.path.join(temp_dir, "quarantine")
        db_path = os.path.join(temp_dir, "quarantine.db")
        return QuarantineManager(
            quarantine_directory=quarantine_dir,
            database_path=db_path,
        )

    def test_quarantine_empty_file(self, manager, temp_dir):
        """Test quarantining an empty file."""
        file_path = os.path.join(temp_dir, "empty.exe")
        Path(file_path).touch()

        result = manager.quarantine_file(file_path, "TestThreat")

        assert result.is_success is True
        assert result.entry.file_size == 0

    def test_quarantine_file_with_spaces_in_path(self, manager, temp_dir):
        """Test quarantining a file with spaces in the path."""
        dir_with_spaces = os.path.join(temp_dir, "path with spaces")
        os.makedirs(dir_with_spaces, exist_ok=True)
        file_path = os.path.join(dir_with_spaces, "file with spaces.exe")
        with open(file_path, "wb") as f:
            f.write(b"Content with spaces")

        result = manager.quarantine_file(file_path, "TestThreat")

        assert result.is_success is True
        assert "spaces" in result.entry.original_path

    def test_quarantine_file_with_unicode_name(self, manager, temp_dir):
        """Test quarantining a file with unicode characters in name."""
        file_path = os.path.join(temp_dir, "tëst_fîlé_名前.exe")
        with open(file_path, "wb") as f:
            f.write(b"Unicode content")

        result = manager.quarantine_file(file_path, "TestThreat")

        assert result.is_success is True
        assert result.entry is not None

    def test_quarantine_large_threat_name(self, manager, temp_dir):
        """Test quarantining with a very long threat name."""
        file_path = os.path.join(temp_dir, "threat_test.exe")
        with open(file_path, "wb") as f:
            f.write(b"Content")

        long_threat = "A" * 1000  # Very long threat name
        result = manager.quarantine_file(file_path, long_threat)

        assert result.is_success is True
        assert result.entry.threat_name == long_threat

    def test_restore_to_nonexistent_directory(self, manager, temp_dir):
        """Test restoring a file to a directory that doesn't exist."""
        # Create a file in a nested directory
        nested_dir = os.path.join(temp_dir, "will", "be", "deleted")
        os.makedirs(nested_dir, exist_ok=True)
        file_path = os.path.join(nested_dir, "test.exe")
        with open(file_path, "wb") as f:
            f.write(b"Content")

        qresult = manager.quarantine_file(file_path, "TestThreat")
        assert qresult.is_success is True

        # Delete the directory
        import shutil
        shutil.rmtree(os.path.join(temp_dir, "will"))

        # Restore should recreate the directory
        result = manager.restore_file(qresult.entry.id)

        assert result.is_success is True
        assert Path(file_path).exists()

    def test_status_mapping_all_file_statuses(self, manager):
        """Test that all FileOperationStatus values are mapped correctly."""
        from src.core.quarantine.file_handler import FileOperationStatus

        # Test the internal status mapping method
        mappings = {
            FileOperationStatus.SUCCESS: QuarantineStatus.SUCCESS,
            FileOperationStatus.FILE_NOT_FOUND: QuarantineStatus.FILE_NOT_FOUND,
            FileOperationStatus.PERMISSION_DENIED: QuarantineStatus.PERMISSION_DENIED,
            FileOperationStatus.DISK_FULL: QuarantineStatus.DISK_FULL,
            FileOperationStatus.ALREADY_EXISTS: QuarantineStatus.ALREADY_QUARANTINED,
            FileOperationStatus.ERROR: QuarantineStatus.ERROR,
        }

        for file_status, expected_quarantine_status in mappings.items():
            result = manager._map_file_status(file_status)
            assert result == expected_quarantine_status
