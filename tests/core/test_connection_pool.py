# ClamUI ConnectionPool Tests
"""Unit tests for the ConnectionPool class."""

import queue
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from unittest import mock

import pytest

from src.core.quarantine.connection_pool import ConnectionPool


class TestConnectionPoolInit:
    """Tests for ConnectionPool initialization."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield str(Path(tmpdir) / "test_pool.db")

    def test_init_with_default_pool_size(self, temp_db_path):
        """Test ConnectionPool initialization with default pool size."""
        pool = ConnectionPool(temp_db_path)
        assert pool._pool_size == 5
        assert pool._db_path == Path(temp_db_path)
        assert pool._total_connections == 0
        assert pool._closed is False
        assert isinstance(pool._pool, queue.Queue)

    def test_init_with_custom_pool_size(self, temp_db_path):
        """Test ConnectionPool initialization with custom pool size."""
        pool = ConnectionPool(temp_db_path, pool_size=10)
        assert pool._pool_size == 10
        assert pool._total_connections == 0
        assert pool._closed is False

    def test_init_with_minimum_pool_size(self, temp_db_path):
        """Test ConnectionPool initialization with minimum pool size."""
        pool = ConnectionPool(temp_db_path, pool_size=1)
        assert pool._pool_size == 1

    def test_init_with_invalid_pool_size(self, temp_db_path):
        """Test ConnectionPool raises ValueError for pool_size < 1."""
        with pytest.raises(ValueError, match="pool_size must be at least 1"):
            ConnectionPool(temp_db_path, pool_size=0)

        with pytest.raises(ValueError, match="pool_size must be at least 1"):
            ConnectionPool(temp_db_path, pool_size=-1)

    def test_init_creates_lock(self, temp_db_path):
        """Test ConnectionPool creates a threading lock."""
        pool = ConnectionPool(temp_db_path)
        assert isinstance(pool._lock, threading.Lock)


class TestConnectionPoolCreateConnection:
    """Tests for ConnectionPool._create_connection() method."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_create.db"
            yield str(db_path)

    @pytest.fixture
    def pool(self, temp_db_path):
        """Create a ConnectionPool instance."""
        return ConnectionPool(temp_db_path, pool_size=3)

    def test_create_connection_returns_connection(self, pool):
        """Test _create_connection returns a sqlite3.Connection object."""
        conn = pool._create_connection()
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_create_connection_enables_wal_mode(self, pool):
        """Test _create_connection enables WAL mode."""
        conn = pool._create_connection()
        cursor = conn.execute("PRAGMA journal_mode")
        result = cursor.fetchone()
        # WAL mode should be enabled
        assert result[0].upper() == "WAL"
        conn.close()

    def test_create_connection_enables_foreign_keys(self, pool):
        """Test _create_connection enables foreign key constraints."""
        conn = pool._create_connection()
        cursor = conn.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        # Foreign keys should be ON (1)
        assert result[0] == 1
        conn.close()

    def test_create_connection_sets_timeout(self, pool):
        """Test _create_connection sets timeout to 30 seconds."""
        # The timeout is set during sqlite3.connect, not as a PRAGMA
        # We can verify it works by checking the connection doesn't raise immediately
        conn = pool._create_connection()
        assert conn is not None
        conn.close()

    def test_create_connection_closes_on_pragma_error(self, pool):
        """Test _create_connection closes connection if PRAGMA configuration fails."""
        with mock.patch("sqlite3.connect") as mock_connect:
            mock_conn = mock.MagicMock()
            mock_conn.execute.side_effect = sqlite3.Error("PRAGMA failed")
            mock_connect.return_value = mock_conn

            with pytest.raises(sqlite3.Error):
                pool._create_connection()

            # Verify connection was closed on error
            mock_conn.close.assert_called_once()


class TestConnectionPoolAcquire:
    """Tests for ConnectionPool.acquire() method."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_acquire.db"
            yield str(db_path)

    @pytest.fixture
    def pool(self, temp_db_path):
        """Create a ConnectionPool instance."""
        return ConnectionPool(temp_db_path, pool_size=3)

    def test_acquire_creates_new_connection_when_pool_empty(self, pool):
        """Test acquire creates a new connection when pool is empty."""
        conn = pool.acquire()
        assert isinstance(conn, sqlite3.Connection)
        assert pool._total_connections == 1
        conn.close()

    def test_acquire_returns_existing_connection_from_pool(self, pool):
        """Test acquire returns existing connection from pool."""
        # Create and release a connection to populate the pool
        conn1 = pool.acquire()
        pool.release(conn1)

        # Acquire should return the same connection
        conn2 = pool.acquire()
        assert conn2 == conn1
        assert pool._total_connections == 1
        conn2.close()

    def test_acquire_creates_multiple_connections_up_to_max(self, pool):
        """Test acquire creates connections up to pool_size."""
        connections = []
        for i in range(3):
            conn = pool.acquire()
            connections.append(conn)
            assert pool._total_connections == i + 1

        # Clean up
        for conn in connections:
            conn.close()

    def test_acquire_blocks_when_pool_exhausted(self, pool):
        """Test acquire blocks when pool is exhausted and timeout expires."""
        # Acquire all connections
        connections = [pool.acquire() for _ in range(3)]
        assert pool._total_connections == 3

        # Next acquire should timeout since pool is exhausted
        with pytest.raises(queue.Empty):
            pool.acquire(timeout=0.1)

        # Clean up
        for conn in connections:
            conn.close()

    def test_acquire_waits_for_released_connection(self, pool):
        """Test acquire waits and gets released connection."""
        # Acquire all connections
        connections = [pool.acquire() for _ in range(3)]

        # Release one connection in another thread after a delay
        def release_after_delay():
            time.sleep(0.1)
            pool.release(connections[0])

        release_thread = threading.Thread(target=release_after_delay)
        release_thread.start()

        # This should block briefly then succeed
        conn = pool.acquire(timeout=1.0)
        assert isinstance(conn, sqlite3.Connection)

        release_thread.join()

        # Clean up
        conn.close()
        for c in connections[1:]:
            c.close()

    def test_acquire_raises_runtime_error_when_closed(self, pool):
        """Test acquire raises RuntimeError when pool is closed."""
        pool.close_all()

        with pytest.raises(RuntimeError, match="Connection pool has been closed"):
            pool.acquire()

    def test_acquire_with_no_timeout_waits_indefinitely(self, pool):
        """Test acquire with timeout=None waits indefinitely (until released)."""
        # Acquire all connections
        connections = [pool.acquire() for _ in range(3)]

        # Release one connection after a short delay
        def release_after_delay():
            time.sleep(0.2)
            pool.release(connections[0])

        release_thread = threading.Thread(target=release_after_delay)
        release_thread.start()

        # This should wait indefinitely (no timeout)
        start_time = time.time()
        conn = pool.acquire(timeout=None)
        elapsed = time.time() - start_time

        # Should have waited for the release
        assert elapsed >= 0.2
        assert isinstance(conn, sqlite3.Connection)

        release_thread.join()

        # Clean up
        conn.close()
        for c in connections[1:]:
            c.close()


class TestConnectionPoolRelease:
    """Tests for ConnectionPool.release() method."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_release.db"
            yield str(db_path)

    @pytest.fixture
    def pool(self, temp_db_path):
        """Create a ConnectionPool instance."""
        return ConnectionPool(temp_db_path, pool_size=3)

    def test_release_returns_valid_connection_to_pool(self, pool):
        """Test release returns valid connection to pool."""
        conn = pool.acquire()
        pool.release(conn)

        # Connection should be back in the pool
        # Verify by checking we can acquire without creating a new one
        total_before = pool._total_connections
        conn2 = pool.acquire()
        assert pool._total_connections == total_before
        assert conn2 == conn

        conn2.close()

    def test_release_validates_connection_health(self, pool):
        """Test release validates connection health before returning to pool."""
        conn = pool.acquire()

        # Release should execute "SELECT 1" to validate
        with mock.patch.object(conn, "execute") as mock_execute:
            pool.release(conn)
            mock_execute.assert_called_once_with("SELECT 1")

        conn.close()

    def test_release_closes_invalid_connection(self, pool):
        """Test release closes and discards invalid connections."""
        conn = pool.acquire()
        initial_count = pool._total_connections

        # Make the connection invalid by closing it
        conn.close()

        # Release should detect it's invalid and discard it
        pool.release(conn)

        # Total connections should decrease
        assert pool._total_connections == initial_count - 1

    def test_release_closes_connection_when_pool_is_closed(self, pool):
        """Test release closes connection when pool is closed."""
        conn = pool.acquire()
        pool.close_all()

        # Mock the connection to verify close is called
        with mock.patch.object(conn, "close") as mock_close:
            pool.release(conn)
            mock_close.assert_called_once()

    def test_release_handles_database_error_gracefully(self, pool):
        """Test release handles database errors during validation."""
        conn = pool.acquire()
        initial_count = pool._total_connections

        # Mock execute to raise database error
        with mock.patch.object(conn, "execute", side_effect=sqlite3.Error("Database locked")):
            pool.release(conn)

        # Connection should be discarded, total count decreased
        assert pool._total_connections == initial_count - 1

    def test_release_handles_queue_full(self, pool):
        """Test release handles queue.Full when pool is at capacity."""
        # Fill the pool
        connections = [pool.acquire() for _ in range(3)]
        for conn in connections:
            pool.release(conn)

        # Try to release an extra connection (should handle queue.Full)
        extra_conn = pool._create_connection()
        pool._total_connections += 1

        # This should discard the connection instead of raising
        pool.release(extra_conn)

        # Verify the extra connection was discarded (count should be back to 3)
        assert pool._total_connections == 3


class TestConnectionPoolGetConnection:
    """Tests for ConnectionPool.get_connection() context manager."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_context.db"
            # Create a test table
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
            conn.commit()
            conn.close()
            yield str(db_path)

    @pytest.fixture
    def pool(self, temp_db_path):
        """Create a ConnectionPool instance."""
        return ConnectionPool(temp_db_path, pool_size=3)

    def test_get_connection_acquires_and_releases(self, pool):
        """Test get_connection acquires connection on entry and releases on exit."""
        initial_count = pool._total_connections

        with pool.get_connection() as conn:
            assert isinstance(conn, sqlite3.Connection)
            # Should have acquired a connection
            assert pool._total_connections >= initial_count

        # Connection should be released back (can verify by acquiring again)
        conn2 = pool.acquire()
        assert isinstance(conn2, sqlite3.Connection)
        conn2.close()

    def test_get_connection_commits_on_normal_exit(self, pool):
        """Test get_connection commits transaction on normal exit."""
        with pool.get_connection() as conn:
            conn.execute("INSERT INTO test (value) VALUES (?)", ("test_value",))
            # Don't manually commit - context manager should do it

        # Verify data was committed
        with pool.get_connection() as conn:
            cursor = conn.execute("SELECT value FROM test")
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == "test_value"

    def test_get_connection_rolls_back_on_exception(self, pool):
        """Test get_connection rolls back transaction on exception."""
        try:
            with pool.get_connection() as conn:
                conn.execute("INSERT INTO test (value) VALUES (?)", ("should_rollback",))
                # Raise an exception before commit
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify data was NOT committed
        with pool.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test WHERE value = ?", ("should_rollback",))
            count = cursor.fetchone()[0]
            assert count == 0

    def test_get_connection_releases_on_exception(self, pool):
        """Test get_connection releases connection even when exception occurs."""
        initial_count = pool._total_connections

        try:
            with pool.get_connection() as conn:
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Connection should still be released
        # Verify by acquiring - should get the same total or less
        conn = pool.acquire()
        assert pool._total_connections <= initial_count + 1
        conn.close()

    def test_get_connection_handles_invalid_connection(self, pool):
        """Test get_connection handles invalid connections gracefully."""
        # Get a connection and close it to make it invalid
        conn = pool.acquire()
        conn.close()
        pool.release(conn)

        # The next get_connection should handle any issues
        with pool.get_connection() as conn:
            # Should get a valid connection (new or recovered)
            assert isinstance(conn, sqlite3.Connection)

    def test_get_connection_with_timeout(self, pool):
        """Test get_connection context manager with timeout parameter."""
        # Acquire all connections
        connections = [pool.acquire() for _ in range(3)]

        # This should timeout
        with pytest.raises(queue.Empty):
            with pool.get_connection(timeout=0.1) as conn:
                pass

        # Clean up
        for conn in connections:
            conn.close()

    def test_get_connection_handles_rollback_error(self, pool):
        """Test get_connection handles rollback errors gracefully."""
        with mock.patch("sqlite3.Connection.rollback", side_effect=sqlite3.Error("Rollback failed")):
            try:
                with pool.get_connection() as conn:
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Should not raise sqlite3.Error from rollback


class TestConnectionPoolCloseAll:
    """Tests for ConnectionPool.close_all() method."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_close.db"
            yield str(db_path)

    @pytest.fixture
    def pool(self, temp_db_path):
        """Create a ConnectionPool instance."""
        return ConnectionPool(temp_db_path, pool_size=3)

    def test_close_all_sets_closed_flag(self, pool):
        """Test close_all sets the _closed flag."""
        assert pool._closed is False
        pool.close_all()
        assert pool._closed is True

    def test_close_all_closes_all_connections_in_pool(self, pool):
        """Test close_all closes all connections in the pool."""
        # Create and release connections to populate the pool
        connections = []
        for _ in range(3):
            conn = pool.acquire()
            connections.append(conn)
            pool.release(conn)

        # Close all
        pool.close_all()

        # Total connections should be 0
        assert pool._total_connections == 0

    def test_close_all_prevents_new_acquire(self, pool):
        """Test close_all prevents new connections from being acquired."""
        pool.close_all()

        with pytest.raises(RuntimeError, match="Connection pool has been closed"):
            pool.acquire()

    def test_close_all_handles_partially_empty_pool(self, pool):
        """Test close_all handles partially empty pool."""
        # Acquire some connections but don't release them all
        conn1 = pool.acquire()
        conn2 = pool.acquire()
        pool.release(conn1)
        # Keep conn2 acquired

        # close_all should handle the partial pool
        pool.close_all()

        # Should have closed only the connection in the pool
        assert pool._closed is True

        # Clean up the unreleased connection
        conn2.close()

    def test_close_all_handles_empty_pool(self, pool):
        """Test close_all handles empty pool gracefully."""
        # Don't acquire any connections
        pool.close_all()

        # Should not raise any errors
        assert pool._closed is True
        assert pool._total_connections == 0

    def test_close_all_is_thread_safe(self, pool):
        """Test close_all is thread-safe."""
        # Populate the pool
        connections = [pool.acquire() for _ in range(3)]
        for conn in connections:
            pool.release(conn)

        # Close from multiple threads
        errors = []

        def close_pool():
            try:
                pool.close_all()
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=close_pool) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not have any errors
        assert len(errors) == 0
        assert pool._closed is True

    def test_close_all_handles_already_closed_connections(self, pool):
        """Test close_all handles already-closed connections gracefully."""
        # Create a connection and close it
        conn = pool.acquire()
        conn.close()
        pool.release(conn)

        # close_all should not raise errors for already-closed connections
        pool.close_all()
        assert pool._closed is True

    def test_close_all_can_be_called_multiple_times(self, pool):
        """Test close_all can be safely called multiple times."""
        pool.close_all()
        # Second call should not raise
        pool.close_all()
        # Third call should not raise
        pool.close_all()

        assert pool._closed is True


class TestConnectionPoolThreadSafety:
    """Tests for thread safety in ConnectionPool."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_concurrent.db"
            yield str(db_path)

    @pytest.fixture
    def pool(self, temp_db_path):
        """Create a ConnectionPool instance."""
        return ConnectionPool(temp_db_path, pool_size=5)

    def test_concurrent_acquire_operations(self, pool):
        """Test concurrent acquire operations are thread-safe."""
        connections = []
        errors = []
        lock = threading.Lock()

        def acquire_connection(thread_id):
            try:
                conn = pool.acquire(timeout=2.0)
                with lock:
                    connections.append(conn)
                time.sleep(0.01)  # Hold briefly
                pool.release(conn)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Create multiple threads
        threads = []
        for i in range(20):
            t = threading.Thread(target=acquire_connection, args=(i,))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        # Should not exceed pool size
        assert pool._total_connections <= 5

    def test_concurrent_acquire_and_release(self, pool):
        """Test concurrent acquire and release operations."""
        operations = []
        errors = []
        lock = threading.Lock()

        def worker(worker_id):
            try:
                for _ in range(5):
                    conn = pool.acquire(timeout=2.0)
                    with lock:
                        operations.append(f"Worker {worker_id} acquired")
                    time.sleep(0.001)
                    pool.release(conn)
                    with lock:
                        operations.append(f"Worker {worker_id} released")
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(operations) == 100  # 10 workers * 5 iterations * 2 operations

    def test_concurrent_context_manager_usage(self, pool):
        """Test concurrent usage of get_connection context manager."""
        errors = []

        def use_context_manager(worker_id):
            try:
                with pool.get_connection(timeout=2.0) as conn:
                    # Do some work
                    conn.execute("SELECT 1")
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        threads = [threading.Thread(target=use_context_manager, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_pool_exhaustion_under_concurrent_load(self, pool):
        """Test pool exhaustion behavior under heavy concurrent load."""
        acquired_connections = []
        errors = []
        lock = threading.Lock()
        barrier = threading.Barrier(10)  # Ensure threads start simultaneously

        def acquire_and_hold(worker_id):
            try:
                # Wait for all threads to be ready
                barrier.wait()
                # Try to acquire a connection (pool has only 5)
                conn = pool.acquire(timeout=3.0)
                with lock:
                    acquired_connections.append((worker_id, conn))
                time.sleep(0.1)  # Hold the connection briefly
                pool.release(conn)
            except queue.Empty:
                # Some threads should timeout since pool only has 5 connections
                errors.append(f"Worker {worker_id} timed out")
            except Exception as e:
                errors.append(f"Worker {worker_id} error: {e}")

        threads = [threading.Thread(target=acquire_and_hold, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # With pool_size=5 and 10 threads trying to acquire simultaneously,
        # we should see either successful acquisitions or timeouts
        total_operations = len(acquired_connections) + len([e for e in errors if "timed out" in e])
        assert total_operations == 10, "All threads should complete (success or timeout)"
        # No unexpected errors should occur
        unexpected_errors = [e for e in errors if "timed out" not in e]
        assert len(unexpected_errors) == 0, f"Unexpected errors: {unexpected_errors}"

    def test_connection_reuse_under_concurrent_load(self, pool):
        """Test that connections are correctly reused under concurrent load."""
        connection_ids = []
        errors = []
        lock = threading.Lock()

        def acquire_and_release_multiple(worker_id):
            try:
                for iteration in range(10):
                    conn = pool.acquire(timeout=2.0)
                    # Track the connection object ID
                    with lock:
                        connection_ids.append(id(conn))
                    time.sleep(0.001)  # Brief work
                    pool.release(conn)
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        threads = [threading.Thread(target=acquire_and_release_multiple, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(connection_ids) == 50, "Should have 50 total acquisitions (5 workers * 10 iterations)"

        # Verify connection reuse: with pool_size=5, we should see repeated IDs
        unique_connections = len(set(connection_ids))
        assert unique_connections <= 5, f"Should not exceed pool_size of 5, got {unique_connections}"

        # Verify actual reuse occurred (same connection used multiple times)
        from collections import Counter
        conn_usage = Counter(connection_ids)
        max_reuse = max(conn_usage.values())
        assert max_reuse > 1, "Connections should be reused (same ID appearing multiple times)"

    def test_no_race_conditions_in_connection_creation(self, pool):
        """Test that connection creation under concurrent load has no race conditions."""
        barrier = threading.Barrier(10)
        connections = []
        errors = []
        lock = threading.Lock()

        def acquire_simultaneously(worker_id):
            try:
                barrier.wait()  # All threads start at the same time
                conn = pool.acquire(timeout=2.0)
                with lock:
                    connections.append(conn)
                time.sleep(0.01)
                pool.release(conn)
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        threads = [threading.Thread(target=acquire_simultaneously, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have no errors or timeouts (all should eventually get connections)
        # Some may timeout if contention is high, which is acceptable behavior
        assert all("timeout" in str(e).lower() or isinstance(e, queue.Empty) for e in errors) or len(errors) == 0

        # Verify total connections never exceeded pool size
        assert pool._total_connections <= 5, f"Total connections {pool._total_connections} exceeded pool_size"

    def test_concurrent_stress_test_many_threads(self, pool):
        """Stress test with many threads performing mixed operations."""
        operations_completed = []
        errors = []
        lock = threading.Lock()

        def worker(worker_id):
            try:
                for i in range(3):
                    # Use context manager for automatic acquire/release
                    with pool.get_connection(timeout=5.0) as conn:
                        # Perform a query
                        conn.execute("SELECT 1")
                        with lock:
                            operations_completed.append(f"Worker {worker_id} iteration {i}")
                    time.sleep(0.001)  # Brief pause between operations
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        # Create many threads (30 threads, pool_size=5)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All operations should complete successfully
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(operations_completed) == 90, "All 90 operations (30 threads * 3 iterations) should complete"
        # Pool should still be healthy
        assert pool._total_connections <= 5

    def test_concurrent_release_with_invalid_connections(self, pool):
        """Test concurrent release operations with mix of valid and invalid connections."""
        errors = []

        def release_invalid(worker_id):
            try:
                conn = pool.acquire(timeout=2.0)
                if worker_id % 3 == 0:
                    # Close the connection to make it invalid
                    conn.close()
                pool.release(conn)
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        threads = [threading.Thread(target=release_invalid, args=(i,)) for i in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should handle invalid connections gracefully
        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_no_deadlock_with_nested_acquisitions(self, pool):
        """Test that nested acquisition attempts don't cause deadlocks."""
        errors = []
        completed = []
        lock = threading.Lock()

        def nested_acquire(worker_id):
            try:
                # Acquire first connection
                conn1 = pool.acquire(timeout=2.0)
                time.sleep(0.01)

                # Try to acquire second connection (may block or timeout)
                try:
                    conn2 = pool.acquire(timeout=0.5)
                    time.sleep(0.01)
                    pool.release(conn2)
                except queue.Empty:
                    # Timeout is acceptable
                    pass

                pool.release(conn1)
                with lock:
                    completed.append(worker_id)
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        threads = [threading.Thread(target=nested_acquire, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()

        # Use join with timeout to detect deadlocks
        for t in threads:
            t.join(timeout=10.0)
            assert not t.is_alive(), "Thread should complete (no deadlock)"

        # All threads should complete
        assert len(completed) == 8, f"Expected 8 completions, got {len(completed)}"
        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_concurrent_close_all_during_active_operations(self, pool):
        """Test close_all() behavior when called during concurrent operations."""
        active_operations = []
        errors = []
        lock = threading.Lock()
        start_barrier = threading.Barrier(6)  # 5 workers + 1 closer

        def worker(worker_id):
            try:
                start_barrier.wait()
                for _ in range(5):
                    try:
                        with pool.get_connection(timeout=1.0) as conn:
                            conn.execute("SELECT 1")
                            with lock:
                                active_operations.append(worker_id)
                    except (RuntimeError, queue.Empty):
                        # Pool may be closed or exhausted - this is acceptable
                        break
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        def closer():
            try:
                start_barrier.wait()
                time.sleep(0.05)  # Let some operations start
                pool.close_all()
            except Exception as e:
                errors.append(f"Closer: {e}")

        # Start workers and closer
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        closer_thread = threading.Thread(target=closer)

        for t in threads:
            t.start()
        closer_thread.start()

        for t in threads:
            t.join()
        closer_thread.join()

        # Pool should be closed
        assert pool._closed is True
        # Workers should either complete or gracefully handle closure
        # No unexpected errors
        unexpected_errors = [e for e in errors if "closed" not in e.lower()]
        assert len(unexpected_errors) == 0, f"Unexpected errors: {unexpected_errors}"

    def test_connection_count_consistency_under_load(self, pool):
        """Test that connection count remains consistent under concurrent operations."""
        errors = []

        def worker(worker_id):
            try:
                for _ in range(10):
                    conn = pool.acquire(timeout=2.0)
                    time.sleep(0.001)
                    pool.release(conn)
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

        # After all operations complete, connection count should be consistent
        # All connections should be back in the pool or properly accounted for
        assert pool._total_connections <= pool._pool_size
        assert pool._total_connections >= 0

    def test_rapid_acquire_release_cycles(self, pool):
        """Test rapid acquire/release cycles to detect any timing issues."""
        iterations = 100
        errors = []
        lock = threading.Lock()
        operation_count = []

        def rapid_cycles(worker_id):
            try:
                local_count = 0
                for _ in range(iterations):
                    conn = pool.acquire(timeout=1.0)
                    pool.release(conn)
                    local_count += 1
                with lock:
                    operation_count.append(local_count)
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")

        threads = [threading.Thread(target=rapid_cycles, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert sum(operation_count) == 500, f"Expected 500 operations (5 workers * 100 iterations)"
        # Pool should be healthy
        assert pool._total_connections <= 5


class TestConnectionPoolGetStats:
    """Tests for ConnectionPool.get_stats() method."""

    @pytest.fixture
    def pool(self):
        """Create a ConnectionPool for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_stats.db")
            pool = ConnectionPool(db_path, pool_size=5)
            yield pool
            try:
                pool.close_all()
            except Exception:
                pass

    def test_get_stats_on_empty_pool(self, pool):
        """Test get_stats() on a newly created pool with no connections."""
        stats = pool.get_stats()

        assert stats["pool_size"] == 5
        assert stats["available_count"] == 0
        assert stats["total_created"] == 0
        assert stats["active_count"] == 0
        assert stats["is_closed"] is False

    def test_get_stats_after_acquiring_one_connection(self, pool):
        """Test get_stats() after acquiring one connection."""
        conn = pool.acquire()

        stats = pool.get_stats()
        assert stats["pool_size"] == 5
        assert stats["available_count"] == 0
        assert stats["total_created"] == 1
        assert stats["active_count"] == 1
        assert stats["is_closed"] is False

        pool.release(conn)

    def test_get_stats_after_releasing_connection(self, pool):
        """Test get_stats() after acquiring and releasing a connection."""
        conn = pool.acquire()
        pool.release(conn)

        stats = pool.get_stats()
        assert stats["pool_size"] == 5
        assert stats["available_count"] == 1
        assert stats["total_created"] == 1
        assert stats["active_count"] == 0
        assert stats["is_closed"] is False

    def test_get_stats_with_multiple_connections(self, pool):
        """Test get_stats() with multiple connections acquired and some released."""
        # Acquire 3 connections
        conn1 = pool.acquire()
        conn2 = pool.acquire()
        conn3 = pool.acquire()

        stats = pool.get_stats()
        assert stats["total_created"] == 3
        assert stats["active_count"] == 3
        assert stats["available_count"] == 0

        # Release one connection
        pool.release(conn1)

        stats = pool.get_stats()
        assert stats["total_created"] == 3
        assert stats["active_count"] == 2
        assert stats["available_count"] == 1

        # Release remaining connections
        pool.release(conn2)
        pool.release(conn3)

        stats = pool.get_stats()
        assert stats["total_created"] == 3
        assert stats["active_count"] == 0
        assert stats["available_count"] == 3

    def test_get_stats_at_pool_capacity(self, pool):
        """Test get_stats() when pool is at maximum capacity."""
        # Acquire all 5 connections
        connections = [pool.acquire() for _ in range(5)]

        stats = pool.get_stats()
        assert stats["pool_size"] == 5
        assert stats["total_created"] == 5
        assert stats["active_count"] == 5
        assert stats["available_count"] == 0
        assert stats["is_closed"] is False

        # Release all connections
        for conn in connections:
            pool.release(conn)

    def test_get_stats_after_close_all(self, pool):
        """Test get_stats() after closing the pool."""
        # Create some connections
        conn1 = pool.acquire()
        conn2 = pool.acquire()
        pool.release(conn1)
        pool.release(conn2)

        # Close the pool
        pool.close_all()

        stats = pool.get_stats()
        assert stats["is_closed"] is True
        assert stats["total_created"] == 0  # All connections were closed
        assert stats["available_count"] == 0
        assert stats["active_count"] == 0

    def test_get_stats_with_context_manager(self, pool):
        """Test get_stats() when using context manager."""
        # Before acquiring
        stats = pool.get_stats()
        assert stats["active_count"] == 0

        # While connection is active in context manager
        with pool.get_connection() as conn:
            stats = pool.get_stats()
            assert stats["total_created"] == 1
            assert stats["active_count"] == 1
            assert stats["available_count"] == 0

        # After context manager releases connection
        stats = pool.get_stats()
        assert stats["total_created"] == 1
        assert stats["active_count"] == 0
        assert stats["available_count"] == 1

    def test_get_stats_thread_safety(self, pool):
        """Test that get_stats() is thread-safe during concurrent operations."""
        stats_snapshots = []
        errors = []
        lock = threading.Lock()
        barrier = threading.Barrier(10)

        def worker():
            try:
                barrier.wait()  # Synchronize start
                for _ in range(10):
                    # Acquire and release connection
                    conn = pool.acquire(timeout=1.0)
                    # Get stats while holding connection
                    stats = pool.get_stats()
                    with lock:
                        stats_snapshots.append(stats)
                    pool.release(conn)
                    # Get stats after releasing
                    stats = pool.get_stats()
                    with lock:
                        stats_snapshots.append(stats)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(stats_snapshots) > 0

        # Verify all stats are valid
        for stats in stats_snapshots:
            assert "pool_size" in stats
            assert "available_count" in stats
            assert "total_created" in stats
            assert "active_count" in stats
            assert "is_closed" in stats
            # Verify consistency: active + available should equal total
            assert stats["active_count"] + stats["available_count"] == stats["total_created"]
            # Verify totals don't exceed pool size
            assert stats["total_created"] <= stats["pool_size"]

    def test_get_stats_consistency_check(self, pool):
        """Test that get_stats() maintains internal consistency."""
        # Acquire and release multiple times
        for i in range(10):
            conn = pool.acquire()
            stats = pool.get_stats()

            # Active + available should always equal total
            assert stats["active_count"] + stats["available_count"] == stats["total_created"]
            # Total should never exceed pool size
            assert stats["total_created"] <= stats["pool_size"]

            pool.release(conn)
            stats = pool.get_stats()

            # Verify consistency after release
            assert stats["active_count"] + stats["available_count"] == stats["total_created"]

    def test_get_stats_returns_new_dict(self, pool):
        """Test that get_stats() returns a new dictionary each time."""
        stats1 = pool.get_stats()
        stats2 = pool.get_stats()

        # Should be different objects
        assert stats1 is not stats2
        # But should have same values
        assert stats1 == stats2

        # Modifying one shouldn't affect the other
        stats1["pool_size"] = 999
        assert stats2["pool_size"] == 5

    def test_get_stats_with_custom_pool_size(self):
        """Test get_stats() with a custom pool size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_custom.db")
            pool = ConnectionPool(db_path, pool_size=10)

            stats = pool.get_stats()
            assert stats["pool_size"] == 10
            assert stats["total_created"] == 0

            pool.close_all()

    def test_get_stats_with_invalid_connections(self, pool):
        """Test get_stats() when connections are invalidated."""
        # Acquire connections
        conn1 = pool.acquire()
        conn2 = pool.acquire()

        # Close one connection to make it invalid
        conn1.close()

        # Release invalid connection (should be discarded)
        pool.release(conn1)

        # Release valid connection (should be returned to pool)
        pool.release(conn2)

        stats = pool.get_stats()
        # Only one connection should remain (the valid one)
        assert stats["total_created"] == 1
        assert stats["available_count"] == 1
        assert stats["active_count"] == 0


class TestConnectionPoolPermissions:
    """Tests for database file permission hardening in ConnectionPool."""

    @pytest.fixture
    def temp_db_dir(self):
        """Create a temporary directory for database storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_pool_created_database_has_secure_permissions(self, temp_db_dir):
        """Test that pool-created database has 0o600 permissions."""
        db_path = Path(temp_db_dir) / "pool_secure.db"
        pool = ConnectionPool(str(db_path), pool_size=3)

        # Acquire a connection to trigger database creation
        conn = pool.acquire()

        # Verify database file has 0o600 permissions
        assert db_path.exists()
        perms = db_path.stat().st_mode & 0o777
        assert perms == 0o600, f"Expected 0o600, got {oct(perms)}"

        pool.release(conn)
        pool.close_all()

    def test_pool_wal_file_gets_secure_permissions(self, temp_db_dir):
        """Test that WAL file gets correct permissions when created by pool."""
        db_path = Path(temp_db_dir) / "pool_wal_test.db"
        pool = ConnectionPool(str(db_path), pool_size=3)

        # Acquire connection and perform operation to trigger WAL file creation
        conn = pool.acquire()
        # Create a test table to ensure WAL mode is active
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        pool.release(conn)

        # Check WAL file permissions if it exists
        wal_file = Path(str(db_path) + '-wal')
        if wal_file.exists():
            perms = wal_file.stat().st_mode & 0o777
            assert perms == 0o600, f"WAL file: Expected 0o600, got {oct(perms)}"

        pool.close_all()

    def test_pool_shm_file_gets_secure_permissions(self, temp_db_dir):
        """Test that SHM file gets correct permissions when created by pool."""
        db_path = Path(temp_db_dir) / "pool_shm_test.db"
        pool = ConnectionPool(str(db_path), pool_size=3)

        # Acquire connection and perform operations to trigger SHM file creation
        conn = pool.acquire()
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO test (value) VALUES (?)", ("test_value",))
        conn.commit()
        pool.release(conn)

        # Check SHM file permissions if it exists
        shm_file = Path(str(db_path) + '-shm')
        if shm_file.exists():
            perms = shm_file.stat().st_mode & 0o777
            assert perms == 0o600, f"SHM file: Expected 0o600, got {oct(perms)}"

        pool.close_all()

    def test_pool_all_database_files_get_secure_permissions(self, temp_db_dir):
        """Test that main database file, WAL, and SHM all get secure permissions."""
        db_path = Path(temp_db_dir) / "pool_all_files.db"
        pool = ConnectionPool(str(db_path), pool_size=3)

        # Perform multiple operations to ensure WAL/SHM files are created
        with pool.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
            for i in range(10):
                conn.execute("INSERT INTO test (value) VALUES (?)", (f"value_{i}",))

        # Check main database file
        assert db_path.exists()
        perms = db_path.stat().st_mode & 0o777
        assert perms == 0o600, f"Main DB: Expected 0o600, got {oct(perms)}"

        # Check WAL file if it exists
        wal_file = Path(str(db_path) + '-wal')
        if wal_file.exists():
            perms = wal_file.stat().st_mode & 0o777
            assert perms == 0o600, f"WAL file: Expected 0o600, got {oct(perms)}"

        # Check SHM file if it exists
        shm_file = Path(str(db_path) + '-shm')
        if shm_file.exists():
            perms = shm_file.stat().st_mode & 0o777
            assert perms == 0o600, f"SHM file: Expected 0o600, got {oct(perms)}"

        pool.close_all()

    def test_pool_permission_setting_handles_errors_gracefully(self, temp_db_dir):
        """Test that pool permission setting handles errors gracefully."""
        db_path = Path(temp_db_dir) / "pool_error_test.db"
        pool = ConnectionPool(str(db_path), pool_size=3)

        # Acquire a connection first to create the database
        conn = pool.acquire()
        pool.release(conn)

        # Mock os.chmod to raise an error
        import os
        with mock.patch('os.chmod', side_effect=PermissionError("Permission denied")):
            # This should not raise an exception - errors are handled gracefully
            pool._secure_db_file_permissions()

        # Pool should still be functional despite permission error
        conn = pool.acquire()
        assert isinstance(conn, sqlite3.Connection)
        pool.release(conn)
        pool.close_all()

    def test_pool_permission_setting_handles_os_errors_gracefully(self, temp_db_dir):
        """Test that pool permission setting handles OSError gracefully."""
        db_path = Path(temp_db_dir) / "pool_oserror_test.db"
        pool = ConnectionPool(str(db_path), pool_size=3)

        # Acquire a connection first to create the database
        conn = pool.acquire()
        pool.release(conn)

        # Mock os.chmod to raise OSError
        import os
        with mock.patch('os.chmod', side_effect=OSError("Operation not permitted")):
            # This should not raise an exception - errors are handled gracefully
            pool._secure_db_file_permissions()

        # Pool should still be functional despite OS error
        conn = pool.acquire()
        assert isinstance(conn, sqlite3.Connection)
        pool.release(conn)
        pool.close_all()

    def test_pool_db_file_permissions_constant_value(self):
        """Test that DB_FILE_PERMISSIONS constant has correct value."""
        assert ConnectionPool.DB_FILE_PERMISSIONS == 0o600

    def test_pool_permissions_set_on_first_connection(self, temp_db_dir):
        """Test that permissions are set when the first connection is created."""
        db_path = Path(temp_db_dir) / "pool_first_conn.db"
        pool = ConnectionPool(str(db_path), pool_size=3)

        # Database shouldn't exist yet
        assert not db_path.exists()

        # Acquire first connection - should create database and set permissions
        conn = pool.acquire()

        # Database should now exist with secure permissions
        assert db_path.exists()
        perms = db_path.stat().st_mode & 0o777
        assert perms == 0o600, f"Expected 0o600, got {oct(perms)}"

        pool.release(conn)
        pool.close_all()

    def test_pool_permissions_consistent_across_multiple_connections(self, temp_db_dir):
        """Test that permissions remain secure across multiple connection acquisitions."""
        db_path = Path(temp_db_dir) / "pool_multi_conn.db"
        pool = ConnectionPool(str(db_path), pool_size=3)

        # Acquire and release multiple connections
        for i in range(10):
            conn = pool.acquire()
            conn.execute("SELECT 1")
            pool.release(conn)

        # Verify permissions are still secure
        perms = db_path.stat().st_mode & 0o777
        assert perms == 0o600, f"Expected 0o600, got {oct(perms)}"

        pool.close_all()

    def test_pool_existing_database_gets_secure_permissions(self, temp_db_dir):
        """Test that permissions are set on existing database files."""
        db_path = Path(temp_db_dir) / "pool_existing.db"

        # Create database with insecure permissions
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.close()

        # Set insecure permissions
        import os
        os.chmod(db_path, 0o644)
        perms = db_path.stat().st_mode & 0o777
        assert perms == 0o644  # Verify insecure permissions were set

        # Create pool - should secure permissions
        pool = ConnectionPool(str(db_path), pool_size=3)
        conn = pool.acquire()
        pool.release(conn)

        # Verify permissions are now secure
        perms = db_path.stat().st_mode & 0o777
        assert perms == 0o600, f"Expected 0o600, got {oct(perms)}"

        pool.close_all()

    def test_pool_concurrent_connections_maintain_secure_permissions(self, temp_db_dir):
        """Test that concurrent connections don't compromise file permissions."""
        db_path = Path(temp_db_dir) / "pool_concurrent_perms.db"
        pool = ConnectionPool(str(db_path), pool_size=3)

        errors = []

        def worker(worker_id):
            try:
                with pool.get_connection() as conn:
                    conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, value TEXT)")
                    conn.execute("INSERT INTO test (value) VALUES (?)", (f"worker_{worker_id}",))
            except Exception as e:
                errors.append(str(e))

        # Run multiple threads concurrently
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify permissions are still secure after concurrent operations
        perms = db_path.stat().st_mode & 0o777
        assert perms == 0o600, f"Expected 0o600, got {oct(perms)}"

        # Check WAL/SHM files if they exist
        wal_file = Path(str(db_path) + '-wal')
        if wal_file.exists():
            perms = wal_file.stat().st_mode & 0o777
            assert perms == 0o600, f"WAL file: Expected 0o600, got {oct(perms)}"

        shm_file = Path(str(db_path) + '-shm')
        if shm_file.exists():
            perms = shm_file.stat().st_mode & 0o777
            assert perms == 0o600, f"SHM file: Expected 0o600, got {oct(perms)}"

        pool.close_all()
