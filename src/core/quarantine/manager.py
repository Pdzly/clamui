# ClamUI Quarantine Manager Module
"""
Quarantine manager module for ClamUI providing high-level quarantine operations.

Orchestrates the QuarantineDatabase and SecureFileHandler to provide:
- Moving detected threats to quarantine
- Restoring quarantined files to original locations
- Permanently deleting quarantined files
- Listing and managing quarantine entries
- Async operations for UI integration
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from gi.repository import GLib

from .database import QuarantineDatabase, QuarantineEntry
from .file_handler import (
    FileOperationStatus,
    SecureFileHandler,
)

logger = logging.getLogger(__name__)


class QuarantineStatus(Enum):
    """Status of a quarantine operation."""

    SUCCESS = "success"
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    DISK_FULL = "disk_full"
    DATABASE_ERROR = "database_error"
    ALREADY_QUARANTINED = "already_quarantined"
    ENTRY_NOT_FOUND = "entry_not_found"
    RESTORE_DESTINATION_EXISTS = "restore_destination_exists"
    INVALID_RESTORE_PATH = "invalid_restore_path"
    ERROR = "error"


@dataclass
class QuarantineResult:
    """Result of a quarantine operation."""

    status: QuarantineStatus
    entry: QuarantineEntry | None
    error_message: str | None

    @property
    def is_success(self) -> bool:
        """Check if the operation was successful."""
        return self.status == QuarantineStatus.SUCCESS


class QuarantineManager:
    """
    Manager for quarantine operations orchestrating database and file handling.

    Provides methods for moving files to quarantine, restoring them to
    original locations, permanently deleting them, and managing the
    quarantine list. Supports both synchronous and asynchronous operations
    for UI integration.

    Example:
        >>> manager = QuarantineManager()
        >>> result = manager.quarantine_file("/home/user/malware.exe", "Win.Trojan.Generic")
        >>> if result.is_success:
        ...     print(f"File quarantined: {result.entry.quarantine_path}")
    """

    def __init__(
        self,
        quarantine_directory: str | None = None,
        database_path: str | None = None,
    ):
        """
        Initialize the QuarantineManager.

        Args:
            quarantine_directory: Optional custom quarantine directory path.
                                  Defaults to XDG_DATA_HOME/clamui/quarantine
            database_path: Optional custom database path.
                           Defaults to XDG_DATA_HOME/clamui/quarantine.db
        """
        self._file_handler = SecureFileHandler(quarantine_directory)
        self._database = QuarantineDatabase(database_path)

        # Thread lock for safe concurrent access
        self._lock = threading.Lock()

    @property
    def quarantine_directory(self) -> Path:
        """Get the quarantine directory path."""
        return self._file_handler.quarantine_directory

    def close(self) -> None:
        """Close database connections and cleanup resources."""
        if self._database is not None:
            self._database.close()

    def quarantine_file(
        self,
        file_path: str,
        threat_name: str,
    ) -> QuarantineResult:
        """
        Move a file to quarantine and record metadata.

        Performs the following operations:
        1. Checks if file is already quarantined
        2. Moves file to quarantine directory securely
        3. Records metadata in database

        Args:
            file_path: Path to the file to quarantine
            threat_name: Name of the detected threat

        Returns:
            QuarantineResult with operation status and entry details

        Example:
            >>> manager = QuarantineManager()
            >>> result = manager.quarantine_file("/path/to/infected.exe", "Win.Trojan.Agent")
            >>> if result.is_success:
            ...     print(f"Quarantined at: {result.entry.quarantine_path}")
        """
        with self._lock:
            source = Path(file_path).resolve()
            source_str = str(source)

            # Move file to quarantine (duplicate paths allowed - each gets unique ID)
            file_result = self._file_handler.move_to_quarantine(source_str, threat_name)

            if not file_result.is_success:
                # Map file operation status to quarantine status
                status = self._map_file_status(file_result.status)
                return QuarantineResult(
                    status=status,
                    entry=None,
                    error_message=file_result.error_message,
                )

            # Add entry to database
            entry_id = self._database.add_entry(
                original_path=source_str,
                quarantine_path=file_result.destination_path or "",
                threat_name=threat_name,
                file_size=file_result.file_size,
                file_hash=file_result.file_hash,
                original_permissions=file_result.original_permissions,
            )

            if entry_id is None:
                # Database error - try to restore the file
                # This is a critical error, but file is already moved
                return QuarantineResult(
                    status=QuarantineStatus.DATABASE_ERROR,
                    entry=None,
                    error_message="Failed to record quarantine entry in database",
                )

            # Retrieve the created entry
            entry = self._database.get_entry(entry_id)

            return QuarantineResult(
                status=QuarantineStatus.SUCCESS,
                entry=entry,
                error_message=None,
            )

    def quarantine_file_async(
        self,
        file_path: str,
        threat_name: str,
        callback: Callable[[QuarantineResult], None],
    ) -> None:
        """
        Move a file to quarantine asynchronously.

        The operation runs in a background thread and the callback is invoked
        on the main GTK thread via GLib.idle_add when complete.

        Args:
            file_path: Path to the file to quarantine
            threat_name: Name of the detected threat
            callback: Function to call with QuarantineResult when complete
        """

        def _quarantine_thread():
            result = self.quarantine_file(file_path, threat_name)
            GLib.idle_add(callback, result)

        thread = threading.Thread(target=_quarantine_thread)
        thread.daemon = True
        thread.start()

    def restore_file(self, entry_id: int) -> QuarantineResult:
        """
        Restore a quarantined file to its original location.

        Performs the following operations:
        1. Retrieves entry from database
        2. Verifies file integrity via hash
        3. Moves file back to original location
        4. Removes entry from database

        Args:
            entry_id: The ID of the quarantine entry to restore

        Returns:
            QuarantineResult with operation status

        Example:
            >>> manager = QuarantineManager()
            >>> result = manager.restore_file(1)
            >>> if result.is_success:
            ...     print("File restored successfully")
        """
        with self._lock:
            # Get entry from database
            entry = self._database.get_entry(entry_id)
            if entry is None:
                return QuarantineResult(
                    status=QuarantineStatus.ENTRY_NOT_FOUND,
                    entry=None,
                    error_message=f"Quarantine entry not found: {entry_id}",
                )

            # Verify file integrity before restore
            is_valid, verify_error = self._file_handler.verify_file_integrity(
                entry.quarantine_path, entry.file_hash
            )

            if not is_valid:
                return QuarantineResult(
                    status=QuarantineStatus.ERROR,
                    entry=entry,
                    error_message=f"File integrity verification failed: {verify_error}",
                )

            # Restore file to original location with original permissions
            file_result = self._file_handler.restore_from_quarantine(
                entry.quarantine_path,
                entry.original_path,
                entry.original_permissions,
            )

            if not file_result.is_success:
                status = self._map_file_status(file_result.status)
                # Special handling for destination exists
                if file_result.status == FileOperationStatus.ALREADY_EXISTS:
                    status = QuarantineStatus.RESTORE_DESTINATION_EXISTS
                return QuarantineResult(
                    status=status,
                    entry=entry,
                    error_message=file_result.error_message,
                )

            # Remove entry from database
            if not self._database.remove_entry(entry_id):
                # File restored but database entry remains
                # This is not critical - entry can be cleaned up later
                pass

            return QuarantineResult(
                status=QuarantineStatus.SUCCESS,
                entry=entry,
                error_message=None,
            )

    def restore_file_async(
        self,
        entry_id: int,
        callback: Callable[[QuarantineResult], None],
    ) -> None:
        """
        Restore a quarantined file asynchronously.

        The operation runs in a background thread and the callback is invoked
        on the main GTK thread via GLib.idle_add when complete.

        Args:
            entry_id: The ID of the quarantine entry to restore
            callback: Function to call with QuarantineResult when complete
        """

        def _restore_thread():
            result = self.restore_file(entry_id)
            GLib.idle_add(callback, result)

        thread = threading.Thread(target=_restore_thread)
        thread.daemon = True
        thread.start()

    def delete_file(self, entry_id: int) -> QuarantineResult:
        """
        Permanently delete a quarantined file.

        Performs the following operations:
        1. Retrieves entry from database
        2. Deletes the file from quarantine
        3. Removes entry from database

        Args:
            entry_id: The ID of the quarantine entry to delete

        Returns:
            QuarantineResult with operation status

        Example:
            >>> manager = QuarantineManager()
            >>> result = manager.delete_file(1)
            >>> if result.is_success:
            ...     print("File permanently deleted")
        """
        with self._lock:
            # Get entry from database
            entry = self._database.get_entry(entry_id)
            if entry is None:
                return QuarantineResult(
                    status=QuarantineStatus.ENTRY_NOT_FOUND,
                    entry=None,
                    error_message=f"Quarantine entry not found: {entry_id}",
                )

            # Delete the file
            file_result = self._file_handler.delete_from_quarantine(entry.quarantine_path)

            if not file_result.is_success:
                status = self._map_file_status(file_result.status)
                return QuarantineResult(
                    status=status,
                    entry=entry,
                    error_message=file_result.error_message,
                )

            # Remove entry from database
            if not self._database.remove_entry(entry_id):
                # File deleted but database entry remains
                # This is not critical - entry can be cleaned up later
                pass

            return QuarantineResult(
                status=QuarantineStatus.SUCCESS,
                entry=entry,
                error_message=None,
            )

    def delete_file_async(
        self,
        entry_id: int,
        callback: Callable[[QuarantineResult], None],
    ) -> None:
        """
        Permanently delete a quarantined file asynchronously.

        The operation runs in a background thread and the callback is invoked
        on the main GTK thread via GLib.idle_add when complete.

        Args:
            entry_id: The ID of the quarantine entry to delete
            callback: Function to call with QuarantineResult when complete
        """

        def _delete_thread():
            result = self.delete_file(entry_id)
            GLib.idle_add(callback, result)

        thread = threading.Thread(target=_delete_thread)
        thread.daemon = True
        thread.start()

    def get_entry(self, entry_id: int) -> QuarantineEntry | None:
        """
        Retrieve a specific quarantine entry by ID.

        Args:
            entry_id: The ID of the quarantine entry

        Returns:
            QuarantineEntry if found, None otherwise
        """
        return self._database.get_entry(entry_id)

    def get_entry_by_original_path(self, original_path: str) -> QuarantineEntry | None:
        """
        Retrieve a quarantine entry by original file path.

        Args:
            original_path: The original path of the quarantined file

        Returns:
            QuarantineEntry if found, None otherwise
        """
        return self._database.get_entry_by_original_path(original_path)

    def get_all_entries(self) -> list[QuarantineEntry]:
        """
        Retrieve all quarantine entries, sorted by detection date (newest first).

        Returns:
            List of QuarantineEntry objects
        """
        return self._database.get_all_entries()

    def get_all_entries_async(
        self,
        callback: Callable[[list[QuarantineEntry]], None],
    ) -> None:
        """
        Retrieve all quarantine entries asynchronously.

        The operation runs in a background thread and the callback is invoked
        on the main GTK thread via GLib.idle_add when complete.

        Args:
            callback: Function to call with list of QuarantineEntry objects when complete
        """

        def _get_entries_thread():
            try:
                entries = self.get_all_entries()
            except Exception as e:
                logger.debug("Failed to get quarantine entries async: %s", e)
                entries = []
            GLib.idle_add(callback, entries)

        thread = threading.Thread(target=_get_entries_thread)
        thread.daemon = True
        thread.start()

    def get_total_size(self) -> int:
        """
        Calculate the total size of all quarantined files.

        Returns:
            Total size in bytes
        """
        return self._database.get_total_size()

    def get_entry_count(self) -> int:
        """
        Get the total number of quarantine entries.

        Returns:
            Number of entries
        """
        return self._database.get_entry_count()

    def get_old_entries(self, days: int = 30) -> list[QuarantineEntry]:
        """
        Get entries older than the specified number of days.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            List of QuarantineEntry objects older than the specified days
        """
        return self._database.get_old_entries(days)

    def cleanup_old_entries(self, days: int = 30) -> int:
        """
        Delete old quarantine entries and their files.

        Args:
            days: Delete entries older than this many days (default: 30)

        Returns:
            Number of entries removed
        """
        with self._lock:
            # Get old entries
            old_entries = self.get_old_entries(days)

            # Delete each file
            for entry in old_entries:
                try:
                    self._file_handler.delete_from_quarantine(entry.quarantine_path)
                except Exception as e:
                    # Continue even if file deletion fails
                    logger.warning(
                        "Failed to delete quarantined file %s: %s", entry.quarantine_path, e
                    )

            # Remove from database
            return self._database.cleanup_old_entries(days)

    def cleanup_old_entries_async(
        self,
        callback: Callable[[int], None],
        days: int = 30,
    ) -> None:
        """
        Delete old quarantine entries asynchronously.

        Args:
            callback: Function to call with removed count when complete
            days: Delete entries older than this many days (default: 30)
        """

        def _cleanup_thread():
            removed_count = self.cleanup_old_entries(days)
            GLib.idle_add(callback, removed_count)

        thread = threading.Thread(target=_cleanup_thread)
        thread.daemon = True
        thread.start()

    def _map_file_status(self, file_status: FileOperationStatus) -> QuarantineStatus:
        """Map FileOperationStatus to QuarantineStatus."""
        status_map = {
            FileOperationStatus.SUCCESS: QuarantineStatus.SUCCESS,
            FileOperationStatus.FILE_NOT_FOUND: QuarantineStatus.FILE_NOT_FOUND,
            FileOperationStatus.PERMISSION_DENIED: QuarantineStatus.PERMISSION_DENIED,
            FileOperationStatus.DISK_FULL: QuarantineStatus.DISK_FULL,
            FileOperationStatus.INVALID_RESTORE_PATH: QuarantineStatus.INVALID_RESTORE_PATH,
            FileOperationStatus.ERROR: QuarantineStatus.ERROR,
        }
        return status_map.get(file_status, QuarantineStatus.ERROR)
