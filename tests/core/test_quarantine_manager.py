# ClamUI QuarantineManager Tests
"""Unit tests for the QuarantineManager class."""

import os
import tempfile
import threading
from pathlib import Path
from unittest import mock

import pytest

# Import directly - quarantine modules use GLib only for async callbacks,
# which are mocked in tests via GLib.idle_add patching
from src.core.quarantine.database import QuarantineEntry
from src.core.quarantine.file_handler import (
    FileOperationStatus,
)
from src.core.quarantine.manager import (
    QuarantineManager,
    QuarantineResult,
    QuarantineStatus,
)


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
        assert QuarantineStatus.INVALID_RESTORE_PATH.value == "invalid_restore_path"
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
        QuarantineManager(
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

    def test_restore_to_protected_directory_rejected(self, manager, temp_dir):
        """Test restore to protected system directory is rejected."""
        # Create and quarantine a file
        file_path = os.path.join(temp_dir, "test.exe")
        with open(file_path, "wb") as f:
            f.write(b"Test content")

        qresult = manager.quarantine_file(file_path, "TestThreat")
        assert qresult.is_success is True

        # Manually update the database to have a protected path
        # This simulates a corrupted/manipulated database
        import sqlite3

        db_path = manager._database._db_path
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE quarantine SET original_path = ? WHERE id = ?",
            ("/etc/malicious.conf", qresult.entry.id),
        )
        conn.commit()
        conn.close()

        # Attempt to restore should be rejected
        result = manager.restore_file(qresult.entry.id)

        assert result.is_success is False
        assert result.status == QuarantineStatus.INVALID_RESTORE_PATH
        assert result.error_message is not None
        assert "protected" in result.error_message.lower()

    def test_restore_to_etc_directory_rejected(self, manager, temp_dir):
        """Test restore to /etc directory is rejected."""
        # Create and quarantine a file
        file_path = os.path.join(temp_dir, "test.exe")
        with open(file_path, "wb") as f:
            f.write(b"Test content")

        qresult = manager.quarantine_file(file_path, "TestThreat")
        assert qresult.is_success is True

        # Update database to /etc path
        import sqlite3

        db_path = manager._database._db_path
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE quarantine SET original_path = ? WHERE id = ?",
            ("/etc/passwd", qresult.entry.id),
        )
        conn.commit()
        conn.close()

        result = manager.restore_file(qresult.entry.id)

        assert result.is_success is False
        assert result.status == QuarantineStatus.INVALID_RESTORE_PATH
        assert "/etc" in result.error_message

    def test_restore_to_var_directory_rejected(self, manager, temp_dir):
        """Test restore to /var directory is rejected."""
        # Create and quarantine a file
        file_path = os.path.join(temp_dir, "test.exe")
        with open(file_path, "wb") as f:
            f.write(b"Test content")

        qresult = manager.quarantine_file(file_path, "TestThreat")
        assert qresult.is_success is True

        # Update database to /var path
        import sqlite3

        db_path = manager._database._db_path
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE quarantine SET original_path = ? WHERE id = ?",
            ("/var/spool/malicious", qresult.entry.id),
        )
        conn.commit()
        conn.close()

        result = manager.restore_file(qresult.entry.id)

        assert result.is_success is False
        assert result.status == QuarantineStatus.INVALID_RESTORE_PATH
        assert "/var" in result.error_message


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

    def test_get_all_entries(self, manager, temp_dir):
        """Test retrieving all quarantined entries."""
        # Initially empty
        entries = manager.get_all_entries()
        assert entries == []

        # Add some entries
        for i in range(3):
            file_path = os.path.join(temp_dir, f"test_{i}.exe")
            with open(file_path, "wb") as f:
                f.write(b"Test content")
            manager.quarantine_file(file_path, f"Threat{i}")

        # Verify all entries are retrieved
        entries = manager.get_all_entries()
        assert len(entries) == 3

    def test_export_to_csv(self, manager, temp_dir):
        """Test exporting quarantine log to CSV format."""
        # Add some entries
        for i in range(2):
            file_path = os.path.join(temp_dir, f"test_{i}.exe")
            with open(file_path, "wb") as f:
                f.write(b"Test content")
            manager.quarantine_file(file_path, f"Threat{i}")

        # Export to CSV
        csv_path = os.path.join(temp_dir, "quarantine.csv")
        result = manager.export_to_csv(csv_path)

        assert result is True
        assert Path(csv_path).exists()

        # Verify CSV content
        with open(csv_path, "r") as f:
            content = f.read()
            assert "original_path" in content
            assert "threat_name" in content

    def test_export_to_json(self, manager, temp_dir):
        """Test exporting quarantine log to JSON format."""
        # Add some entries
        for i in range(2):
            file_path = os.path.join(temp_dir, f"test_{i}.exe")
            with open(file_path, "wb") as f:
                f.write(b"Test content")
            manager.quarantine_file(file_path, f"Threat{i}")

        # Export to JSON
        json_path = os.path.join(temp_dir, "quarantine.json")
        result = manager.export_to_json(json_path)

        assert result is True
        assert Path(json_path).exists()

        # Verify JSON content
        import json

        with open(json_path, "r") as f:
            data = json.load(f)
            assert isinstance(data, list)
            assert len(data) == 2