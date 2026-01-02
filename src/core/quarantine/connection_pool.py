# ClamUI SQLite Connection Pool Module
"""
SQLite connection pool for the quarantine database.

Manages a pool of SQLite connections to reduce connection overhead for
batch operations and UI updates that make multiple quick queries.
"""

import queue
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional


class ConnectionPool:
    """
    Thread-safe connection pool for SQLite database connections.

    Manages a pool of SQLite connections to reduce the overhead of creating
    and configuring new connections for each database operation. Connections
    are stored in a queue and reused across operations.

    Attributes:
        _db_path: Path to the SQLite database file
        _pool_size: Maximum number of connections in the pool
        _pool: Queue storing available connections
        _lock: Thread lock for thread-safe operations
        _total_connections: Total number of connections created
        _closed: Flag indicating if the pool has been closed
    """

    def __init__(self, db_path: str, pool_size: int = 5):
        """
        Initialize the connection pool.

        Args:
            db_path: Path to the SQLite database file
            pool_size: Maximum number of connections to maintain in the pool (default: 5)

        Raises:
            ValueError: If pool_size is less than 1
        """
        if pool_size < 1:
            raise ValueError("pool_size must be at least 1")

        self._db_path = Path(db_path)
        self._pool_size = pool_size
        self._pool: queue.Queue = queue.Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._total_connections = 0  # Track total connections created
        self._closed = False  # Track if pool has been closed

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new SQLite connection with WAL mode and foreign keys enabled.

        This method creates a connection with the same configuration as used
        in QuarantineDatabase._get_connection() to ensure consistency.

        Returns:
            Configured SQLite connection object

        Raises:
            sqlite3.Error: If connection creation or configuration fails
        """
        conn = sqlite3.connect(str(self._db_path), timeout=30.0)
        try:
            # Enable WAL mode for better concurrency and corruption prevention
            conn.execute("PRAGMA journal_mode=WAL")
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        except sqlite3.Error:
            # Close connection on configuration failure
            conn.close()
            raise

    def acquire(self, timeout: Optional[float] = None) -> sqlite3.Connection:
        """
        Acquire a connection from the pool.

        Returns a connection from the pool if available, or creates a new one
        if the pool is empty and the maximum pool size has not been reached.

        Args:
            timeout: Maximum time in seconds to wait for a connection.
                    None means wait indefinitely (default).

        Returns:
            A configured SQLite connection

        Raises:
            queue.Empty: If timeout expires while waiting for a connection
            RuntimeError: If the pool has been closed
        """
        # Check if pool is closed
        if self._closed:
            raise RuntimeError("Connection pool has been closed")

        # First, check if we can create a new connection (non-blocking check)
        with self._lock:
            if self._total_connections < self._pool_size:
                # We can create a new connection
                conn = self._create_connection()
                self._total_connections += 1
                return conn

        # Pool is at max capacity - wait for an available connection
        try:
            return self._pool.get(block=True, timeout=timeout)
        except queue.Empty:
            # Timeout while waiting for a connection - re-raise
            raise

    def release(self, conn: sqlite3.Connection) -> None:
        """
        Release a connection back to the pool.

        Validates the connection is still usable before returning it to the pool.
        Invalid connections are closed and discarded instead of being returned.

        Args:
            conn: The connection to release back to the pool

        Raises:
            RuntimeError: If the pool has been closed
        """
        # Check if pool is closed
        if self._closed:
            # Pool is closed - just close the connection
            conn.close()
            return

        # Validate connection health before returning to pool
        try:
            # Execute a simple query to verify connection is usable
            conn.execute("SELECT 1")
            # Connection is valid - return to pool
            self._pool.put(conn, block=False)
        except (sqlite3.Error, queue.Full):
            # Connection is invalid or pool is full - close and discard
            # This handles: database locked, connection closed, or pool overflow
            conn.close()
            # Decrement total connections count since we're discarding this one
            with self._lock:
                self._total_connections -= 1

    @contextmanager
    def get_connection(self, timeout: Optional[float] = None) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager that acquires and releases a connection automatically.

        Provides the same interface as QuarantineDatabase._get_connection() for
        easy integration. Acquires a connection on entry, commits transactions
        on normal exit, and ensures the connection is released even on exceptions.

        Args:
            timeout: Maximum time in seconds to wait for a connection.
                    None means wait indefinitely (default).

        Yields:
            A configured SQLite connection from the pool

        Raises:
            queue.Empty: If timeout expires while waiting for a connection
            RuntimeError: If the pool has been closed

        Example:
            >>> pool = ConnectionPool("path/to/db.sqlite")
            >>> with pool.get_connection() as conn:
            ...     conn.execute("INSERT INTO table VALUES (?)", (value,))
        """
        conn = self.acquire(timeout=timeout)
        try:
            yield conn
            # Commit transaction on normal exit
            conn.commit()
        except Exception:
            # Rollback transaction on exception
            try:
                conn.rollback()
            except sqlite3.Error:
                # Ignore rollback errors - connection may be invalid
                pass
            raise
        finally:
            # Always release connection back to pool
            self.release(conn)

    def get_stats(self) -> dict:
        """
        Get current pool statistics for debugging and monitoring.

        Returns a dictionary containing pool statistics including pool size,
        available connections, total connections created, and active connections.

        Returns:
            Dictionary with the following keys:
                - pool_size: Maximum number of connections in the pool
                - available_count: Number of connections currently available in the pool
                - total_created: Total number of connections created
                - active_count: Number of connections currently in use (total - available)
                - is_closed: Whether the pool has been closed

        Thread-safe operation using internal lock.

        Example:
            >>> pool = ConnectionPool("path/to/db.sqlite", pool_size=5)
            >>> stats = pool.get_stats()
            >>> print(f"Active: {stats['active_count']}/{stats['pool_size']}")
            Active: 0/5
        """
        with self._lock:
            available_count = self._pool.qsize()
            active_count = self._total_connections - available_count

            return {
                "pool_size": self._pool_size,
                "available_count": available_count,
                "total_created": self._total_connections,
                "active_count": active_count,
                "is_closed": self._closed,
            }

    def close_all(self) -> None:
        """
        Close all connections in the pool and prevent new connections.

        This method drains the connection pool, closes all connections, and sets
        a flag to prevent new connections from being created. Safe to call multiple
        times. Essential for proper resource cleanup.

        After calling this method:
        - All connections in the pool are closed
        - acquire() will raise RuntimeError
        - release() will close connections instead of returning them to pool

        Thread-safe operation using internal lock.
        """
        with self._lock:
            # Set closed flag to prevent new connections
            self._closed = True

            # Drain and close all connections from the pool
            while True:
                try:
                    # Get connection without blocking
                    conn = self._pool.get(block=False)
                    # Close the connection
                    try:
                        conn.close()
                    except sqlite3.Error:
                        # Ignore errors closing already-closed connections
                        pass
                    # Decrement total connections count
                    self._total_connections -= 1
                except queue.Empty:
                    # Pool is empty - we're done
                    break
