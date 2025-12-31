# ClamUI Quarantine Database Module
"""
Quarantine database module for ClamUI providing metadata persistence.
Stores information about quarantined files including original path, threat info, and file hash.
"""

import os
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class QuarantineEntry:
    """A single quarantine entry representing an isolated threat."""

    id: int
    original_path: str
    quarantine_path: str
    threat_name: str
    detection_date: str  # ISO format string for portability
    file_size: int
    file_hash: str  # SHA256 hash for integrity verification

    def to_dict(self) -> dict:
        """Convert QuarantineEntry to dictionary."""
        return asdict(self)

    @classmethod
    def from_row(cls, row: tuple) -> "QuarantineEntry":
        """
        Create QuarantineEntry from database row.

        Args:
            row: Database row tuple (id, original_path, quarantine_path,
                 threat_name, detection_date, file_size, file_hash)

        Returns:
            New QuarantineEntry instance
        """
        return cls(
            id=row[0],
            original_path=row[1],
            quarantine_path=row[2],
            threat_name=row[3],
            detection_date=row[4],
            file_size=row[5],
            file_hash=row[6],
        )


class QuarantineDatabase:
    """
    Manager for quarantine metadata persistence using SQLite.

    Provides methods for adding, retrieving, updating, and removing
    quarantine entries with thread-safe operations.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the QuarantineDatabase.

        Args:
            db_path: Optional custom database path. Defaults to XDG_DATA_HOME/clamui/quarantine.db
        """
        if db_path:
            self._db_path = Path(db_path)
        else:
            xdg_data_home = os.environ.get("XDG_DATA_HOME", "~/.local/share")
            self._db_path = Path(xdg_data_home).expanduser() / "clamui" / "quarantine.db"

        # Thread lock for safe concurrent access
        self._lock = threading.Lock()

        # Ensure parent directory exists
        self._ensure_db_dir()

        # Initialize database schema
        self._init_database()

    def _ensure_db_dir(self) -> None:
        """Ensure the database directory exists."""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Handle silently - will fail on database operations
            pass

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a new database connection with WAL mode enabled.

        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(str(self._db_path), timeout=30.0)
        # Enable WAL mode for better concurrency and corruption prevention
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_database(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS quarantine (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            original_path TEXT NOT NULL,
                            quarantine_path TEXT NOT NULL UNIQUE,
                            threat_name TEXT NOT NULL,
                            detection_date TEXT NOT NULL,
                            file_size INTEGER NOT NULL,
                            file_hash TEXT NOT NULL
                        )
                        """
                    )
                    # Create index for faster lookups
                    conn.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_quarantine_detection_date
                        ON quarantine(detection_date)
                        """
                    )
                    conn.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_quarantine_original_path
                        ON quarantine(original_path)
                        """
                    )
                    conn.commit()
            except sqlite3.Error:
                # Database initialization failed - will be handled on operations
                pass

    def add_entry(
        self,
        original_path: str,
        quarantine_path: str,
        threat_name: str,
        file_size: int,
        file_hash: str,
    ) -> Optional[int]:
        """
        Add a new quarantine entry to the database.

        Args:
            original_path: Original file path before quarantine
            quarantine_path: Path to the quarantined file
            threat_name: Name of the detected threat
            file_size: Size of the file in bytes
            file_hash: SHA256 hash of the file for integrity verification

        Returns:
            The ID of the newly created entry, or None if failed
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO quarantine
                        (original_path, quarantine_path, threat_name, detection_date, file_size, file_hash)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            original_path,
                            quarantine_path,
                            threat_name,
                            datetime.now().isoformat(),
                            file_size,
                            file_hash,
                        ),
                    )
                    conn.commit()
                    return cursor.lastrowid
            except sqlite3.Error:
                return None

    def get_entry(self, entry_id: int) -> Optional[QuarantineEntry]:
        """
        Retrieve a specific quarantine entry by ID.

        Args:
            entry_id: The ID of the quarantine entry

        Returns:
            QuarantineEntry if found, None otherwise
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        """
                        SELECT id, original_path, quarantine_path, threat_name,
                               detection_date, file_size, file_hash
                        FROM quarantine WHERE id = ?
                        """,
                        (entry_id,),
                    )
                    row = cursor.fetchone()
                    if row:
                        return QuarantineEntry.from_row(row)
            except sqlite3.Error:
                pass
        return None

    def get_entry_by_original_path(self, original_path: str) -> Optional[QuarantineEntry]:
        """
        Retrieve a quarantine entry by original file path.

        Args:
            original_path: The original path of the quarantined file

        Returns:
            QuarantineEntry if found, None otherwise
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        """
                        SELECT id, original_path, quarantine_path, threat_name,
                               detection_date, file_size, file_hash
                        FROM quarantine WHERE original_path = ?
                        """,
                        (original_path,),
                    )
                    row = cursor.fetchone()
                    if row:
                        return QuarantineEntry.from_row(row)
            except sqlite3.Error:
                pass
        return None

    def get_all_entries(self) -> list[QuarantineEntry]:
        """
        Retrieve all quarantine entries, sorted by detection date (newest first).

        Returns:
            List of QuarantineEntry objects
        """
        entries = []
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        """
                        SELECT id, original_path, quarantine_path, threat_name,
                               detection_date, file_size, file_hash
                        FROM quarantine
                        ORDER BY detection_date DESC
                        """
                    )
                    for row in cursor.fetchall():
                        entries.append(QuarantineEntry.from_row(row))
            except sqlite3.Error:
                pass
        return entries

    def remove_entry(self, entry_id: int) -> bool:
        """
        Remove a quarantine entry from the database.

        Args:
            entry_id: The ID of the entry to remove

        Returns:
            True if removed successfully, False otherwise
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "DELETE FROM quarantine WHERE id = ?",
                        (entry_id,),
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            except sqlite3.Error:
                return False

    def get_total_size(self) -> int:
        """
        Calculate the total size of all quarantined files.

        Returns:
            Total size in bytes
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT COALESCE(SUM(file_size), 0) FROM quarantine"
                    )
                    row = cursor.fetchone()
                    if row:
                        return row[0]
            except sqlite3.Error:
                pass
        return 0

    def get_entry_count(self) -> int:
        """
        Get the total number of quarantine entries.

        Returns:
            Number of entries
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM quarantine")
                    row = cursor.fetchone()
                    if row:
                        return row[0]
            except sqlite3.Error:
                pass
        return 0

    def get_old_entries(self, days: int = 30) -> list[QuarantineEntry]:
        """
        Get entries older than the specified number of days.

        Args:
            days: Number of days threshold (default 30)

        Returns:
            List of QuarantineEntry objects older than the threshold
        """
        entries = []
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        """
                        SELECT id, original_path, quarantine_path, threat_name,
                               detection_date, file_size, file_hash
                        FROM quarantine
                        WHERE detection_date < ?
                        ORDER BY detection_date ASC
                        """,
                        (cutoff_date,),
                    )
                    for row in cursor.fetchall():
                        entries.append(QuarantineEntry.from_row(row))
            except sqlite3.Error:
                pass
        return entries

    def cleanup_old_entries(self, days: int = 30) -> int:
        """
        Remove entries older than the specified number of days.

        Note: This only removes database entries. The caller is responsible
        for deleting the actual quarantined files before calling this.

        Args:
            days: Number of days threshold (default 30)

        Returns:
            Number of entries removed
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "DELETE FROM quarantine WHERE detection_date < ?",
                        (cutoff_date,),
                    )
                    conn.commit()
                    return cursor.rowcount
            except sqlite3.Error:
                return 0

    def entry_exists(self, original_path: str) -> bool:
        """
        Check if an entry already exists for the given original path.

        Args:
            original_path: The original file path to check

        Returns:
            True if an entry exists, False otherwise
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT 1 FROM quarantine WHERE original_path = ? LIMIT 1",
                        (original_path,),
                    )
                    return cursor.fetchone() is not None
            except sqlite3.Error:
                return False

    def close(self) -> None:
        """
        Close database connections and cleanup.

        Note: Since connections are created per-operation, this mainly
        serves as a cleanup hook for subclasses or future enhancements.
        """
        # Connections are created and closed per-operation for thread safety
        # This method exists for API consistency and future enhancements
        pass
