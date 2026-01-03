# ClamUI StatisticsCalculator Tests
"""Unit tests for the StatisticsCalculator class and caching functionality."""

from datetime import datetime, timedelta
from unittest import mock

import pytest

from src.core.log_manager import LogEntry
from src.core.statistics_calculator import (
    ProtectionLevel,
    ProtectionStatus,
    ScanStatistics,
    StatisticsCalculator,
    Timeframe,
)


@pytest.fixture
def mock_log_manager():
    """
    Create a mock LogManager for testing.

    Returns a MagicMock configured with:
    - get_logs method that returns sample scan log entries
    - Tracking of call count to verify caching behavior
    """
    log_manager = mock.MagicMock()

    # Create sample log entries with different timestamps and statuses
    sample_logs = [
        LogEntry(
            id="log-1",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="clean",
            summary="Scanned 100 files - No threats found",
            details="Scan complete",
            path="/home/user/documents",
            duration=60.0,
            scheduled=False,
        ),
        LogEntry(
            id="log-2",
            timestamp="2024-01-14T14:30:00",
            type="scan",
            status="infected",
            summary="Found 2 threats in 50 files",
            details="Infected files detected",
            path="/home/user/downloads",
            duration=45.5,
            scheduled=True,
        ),
        LogEntry(
            id="log-3",
            timestamp="2024-01-13T09:15:00",
            type="scan",
            status="clean",
            summary="Scanned 200 files - No threats found",
            details="Scan complete",
            path="/home/user",
            duration=120.0,
            scheduled=False,
        ),
        LogEntry(
            id="log-4",
            timestamp="2024-01-12T16:45:00",
            type="scan",
            status="error",
            summary="Scan failed - Permission denied",
            details="Error during scan",
            path="/root",
            duration=5.0,
            scheduled=False,
        ),
    ]

    # Configure get_logs to return sample logs
    log_manager.get_logs.return_value = sample_logs

    return log_manager


@pytest.fixture
def statistics_calculator(mock_log_manager):
    """
    Create a StatisticsCalculator instance with a mock LogManager.

    Args:
        mock_log_manager: The mock LogManager fixture

    Returns:
        StatisticsCalculator instance configured for testing
    """
    return StatisticsCalculator(log_manager=mock_log_manager)


@pytest.fixture
def empty_log_manager():
    """
    Create a mock LogManager that returns no logs.

    Useful for testing edge cases with no scan history.
    """
    log_manager = mock.MagicMock()
    log_manager.get_logs.return_value = []
    return log_manager


@pytest.fixture
def large_log_dataset():
    """
    Create a large dataset of log entries for testing performance and caching.

    Returns a list of LogEntry objects spanning multiple days with varied statuses.
    """
    logs = []
    base_time = datetime(2024, 1, 1, 10, 0, 0)

    for i in range(100):
        timestamp = base_time + timedelta(hours=i)
        status = ["clean", "infected", "clean", "clean"][i % 4]  # 75% clean, 25% infected
        logs.append(
            LogEntry(
                id=f"log-{i}",
                timestamp=timestamp.isoformat(),
                type="scan",
                status=status,
                summary=f"Scanned {10 * (i + 1)} files",
                details=f"Details for scan {i}",
                path=f"/test/path/{i}",
                duration=float(30 + (i % 10)),
                scheduled=(i % 2 == 0),  # Alternating scheduled/manual
            )
        )

    return logs


class TestTimeframe:
    """Tests for the Timeframe enum."""

    def test_timeframe_values(self):
        """Test Timeframe enum has expected values."""
        assert Timeframe.DAILY.value == "daily"
        assert Timeframe.WEEKLY.value == "weekly"
        assert Timeframe.MONTHLY.value == "monthly"
        assert Timeframe.ALL.value == "all"


class TestProtectionLevel:
    """Tests for the ProtectionLevel enum."""

    def test_protection_level_values(self):
        """Test ProtectionLevel enum has expected values."""
        assert ProtectionLevel.PROTECTED.value == "protected"
        assert ProtectionLevel.AT_RISK.value == "at_risk"
        assert ProtectionLevel.UNPROTECTED.value == "unprotected"
        assert ProtectionLevel.UNKNOWN.value == "unknown"


class TestScanStatistics:
    """Tests for the ScanStatistics dataclass."""

    def test_scan_statistics_creation(self):
        """Test creating a ScanStatistics instance."""
        stats = ScanStatistics(
            timeframe="daily",
            total_scans=10,
            files_scanned=1000,
            threats_detected=2,
            clean_scans=8,
            infected_scans=1,
            error_scans=1,
            average_duration=60.5,
            total_duration=605.0,
            scheduled_scans=5,
            manual_scans=5,
            start_date="2024-01-01T00:00:00",
            end_date="2024-01-02T00:00:00",
        )

        assert stats.timeframe == "daily"
        assert stats.total_scans == 10
        assert stats.files_scanned == 1000
        assert stats.threats_detected == 2
        assert stats.clean_scans == 8
        assert stats.infected_scans == 1
        assert stats.error_scans == 1
        assert stats.average_duration == 60.5
        assert stats.total_duration == 605.0
        assert stats.scheduled_scans == 5
        assert stats.manual_scans == 5

    def test_scan_statistics_to_dict(self):
        """Test ScanStatistics.to_dict serialization."""
        stats = ScanStatistics(
            timeframe="weekly",
            total_scans=5,
            files_scanned=500,
            threats_detected=1,
            clean_scans=4,
            infected_scans=1,
            error_scans=0,
            average_duration=45.0,
            total_duration=225.0,
            scheduled_scans=3,
            manual_scans=2,
        )

        data = stats.to_dict()

        assert data["timeframe"] == "weekly"
        assert data["total_scans"] == 5
        assert data["files_scanned"] == 500
        assert data["threats_detected"] == 1
        assert data["clean_scans"] == 4
        assert data["infected_scans"] == 1
        assert data["error_scans"] == 0
        assert data["average_duration"] == 45.0
        assert data["total_duration"] == 225.0
        assert data["scheduled_scans"] == 3
        assert data["manual_scans"] == 2


class TestProtectionStatus:
    """Tests for the ProtectionStatus dataclass."""

    def test_protection_status_creation(self):
        """Test creating a ProtectionStatus instance."""
        status = ProtectionStatus(
            level="protected",
            last_scan_timestamp="2024-01-15T10:00:00",
            last_scan_age_hours=2.5,
            last_definition_update="2024-01-15T08:00:00",
            definition_age_hours=4.5,
            message="System is protected",
            is_protected=True,
        )

        assert status.level == "protected"
        assert status.last_scan_timestamp == "2024-01-15T10:00:00"
        assert status.last_scan_age_hours == 2.5
        assert status.last_definition_update == "2024-01-15T08:00:00"
        assert status.definition_age_hours == 4.5
        assert status.message == "System is protected"
        assert status.is_protected is True

    def test_protection_status_to_dict(self):
        """Test ProtectionStatus.to_dict serialization."""
        status = ProtectionStatus(
            level="at_risk",
            last_scan_timestamp="2024-01-10T10:00:00",
            last_scan_age_hours=120.0,
            last_definition_update=None,
            definition_age_hours=None,
            message="Last scan was over a week ago",
            is_protected=False,
        )

        data = status.to_dict()

        assert data["level"] == "at_risk"
        assert data["last_scan_timestamp"] == "2024-01-10T10:00:00"
        assert data["last_scan_age_hours"] == 120.0
        assert data["last_definition_update"] is None
        assert data["definition_age_hours"] is None
        assert data["message"] == "Last scan was over a week ago"
        assert data["is_protected"] is False


class TestStatisticsCalculator:
    """Tests for the StatisticsCalculator class."""

    def test_init_with_log_manager(self, mock_log_manager):
        """Test StatisticsCalculator initialization with provided LogManager."""
        calculator = StatisticsCalculator(log_manager=mock_log_manager)
        assert calculator._log_manager is mock_log_manager

    def test_init_without_log_manager(self):
        """Test StatisticsCalculator initialization creates default LogManager."""
        calculator = StatisticsCalculator()
        assert calculator._log_manager is not None

    def test_cache_initialized(self, statistics_calculator):
        """Test that cache data structures are initialized."""
        assert hasattr(statistics_calculator, "_cache")
        assert hasattr(statistics_calculator, "_cache_timestamp")
        assert hasattr(statistics_calculator, "_lock")
        assert isinstance(statistics_calculator._cache, dict)
        assert statistics_calculator._cache_timestamp is None

    def test_cache_ttl_constant(self):
        """Test that CACHE_TTL_SECONDS constant is defined."""
        assert hasattr(StatisticsCalculator, "CACHE_TTL_SECONDS")
        assert StatisticsCalculator.CACHE_TTL_SECONDS == 30


class TestStatisticsCalculatorBasicFunctionality:
    """Tests for basic StatisticsCalculator functionality without caching focus."""

    def test_get_statistics_returns_scan_statistics(self, statistics_calculator):
        """Test that get_statistics returns a ScanStatistics object."""
        stats = statistics_calculator.get_statistics(timeframe="all")
        assert isinstance(stats, ScanStatistics)

    def test_get_statistics_with_empty_logs(self, empty_log_manager):
        """Test get_statistics with no log entries."""
        calculator = StatisticsCalculator(log_manager=empty_log_manager)
        stats = calculator.get_statistics(timeframe="all")

        assert stats.total_scans == 0
        assert stats.files_scanned == 0
        assert stats.threats_detected == 0
        assert stats.clean_scans == 0
        assert stats.infected_scans == 0
        assert stats.error_scans == 0
        assert stats.average_duration == 0.0

    def test_has_scan_history_true(self, statistics_calculator):
        """Test has_scan_history returns True when logs exist."""
        result = statistics_calculator.has_scan_history()
        assert result is True

    def test_has_scan_history_false(self, empty_log_manager):
        """Test has_scan_history returns False when no logs exist."""
        calculator = StatisticsCalculator(log_manager=empty_log_manager)
        result = calculator.has_scan_history()
        assert result is False

    def test_invalidate_cache_method_exists(self, statistics_calculator):
        """Test that invalidate_cache method exists and is callable."""
        assert hasattr(statistics_calculator, "invalidate_cache")
        assert callable(statistics_calculator.invalidate_cache)

    def test_get_scan_trend_data_returns_list(self, statistics_calculator):
        """Test that get_scan_trend_data returns a list of data points."""
        trend_data = statistics_calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
        assert isinstance(trend_data, list)


class TestStatisticsCalculatorCacheHit:
    """Tests for cache hit behavior - verifying log_manager.get_logs() is only called once."""

    def test_get_statistics_caches_log_data(self, statistics_calculator, mock_log_manager):
        """Test that get_statistics caches log data for subsequent calls."""
        # First call should fetch from log_manager
        stats1 = statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 1

        # Second call should use cached data (no additional fetch)
        stats2 = statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 1  # Still 1, not 2

        # Both results should be the same (using same data)
        assert stats1.total_scans == stats2.total_scans
        assert stats1.threats_detected == stats2.threats_detected

    def test_get_scan_trend_data_caches_log_data(self, statistics_calculator, mock_log_manager):
        """Test that get_scan_trend_data caches log data for subsequent calls."""
        # First call should fetch from log_manager
        trend1 = statistics_calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
        assert mock_log_manager.get_logs.call_count == 1

        # Second call should use cached data (no additional fetch)
        trend2 = statistics_calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
        assert mock_log_manager.get_logs.call_count == 1  # Still 1, not 2

        # Both results should be the same
        assert len(trend1) == len(trend2)

    def test_get_statistics_then_get_scan_trend_data_shares_cache(
        self, statistics_calculator, mock_log_manager
    ):
        """
        Test that get_statistics() and get_scan_trend_data() share the same cache.

        This is the key test: when called in succession, log_manager.get_logs()
        should only be called once because both methods use the same cache key
        (limit=10000, log_type='scan').
        """
        # Reset call count to ensure clean state
        mock_log_manager.get_logs.reset_mock()

        # First call to get_statistics should fetch from log_manager
        stats = statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 1
        assert isinstance(stats, ScanStatistics)

        # Second call to get_scan_trend_data should use cached data (cache hit!)
        trend_data = statistics_calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
        assert mock_log_manager.get_logs.call_count == 1  # Still 1 - cache hit!
        assert isinstance(trend_data, list)

    def test_get_scan_trend_data_then_get_statistics_shares_cache(
        self, statistics_calculator, mock_log_manager
    ):
        """
        Test cache sharing in reverse order (trend data first, then statistics).

        Verifies that the cache works bidirectionally - either method can
        populate the cache for the other.
        """
        # Reset call count to ensure clean state
        mock_log_manager.get_logs.reset_mock()

        # First call to get_scan_trend_data should fetch from log_manager
        trend_data = statistics_calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
        assert mock_log_manager.get_logs.call_count == 1
        assert isinstance(trend_data, list)

        # Second call to get_statistics should use cached data (cache hit!)
        stats = statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 1  # Still 1 - cache hit!
        assert isinstance(stats, ScanStatistics)

    def test_multiple_successive_calls_all_use_cache(self, statistics_calculator, mock_log_manager):
        """Test that multiple successive calls all benefit from caching."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        # Call both methods multiple times in succession
        statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 1

        statistics_calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
        assert mock_log_manager.get_logs.call_count == 1  # Cache hit

        statistics_calculator.get_statistics(timeframe="weekly")
        assert mock_log_manager.get_logs.call_count == 1  # Cache hit

        statistics_calculator.get_scan_trend_data(timeframe="monthly", data_points=30)
        assert mock_log_manager.get_logs.call_count == 1  # Cache hit

        # All calls should use the same cached data
        assert mock_log_manager.get_logs.call_count == 1

    def test_cache_key_uses_limit_and_log_type(self, mock_log_manager):
        """Test that cache key is based on limit and log_type parameters."""
        calculator = StatisticsCalculator(log_manager=mock_log_manager)

        # Both get_statistics and get_scan_trend_data use limit=10000, log_type='scan'
        calculator.get_statistics()
        assert mock_log_manager.get_logs.call_count == 1

        # Verify the call was made with correct parameters
        mock_log_manager.get_logs.assert_called_with(limit=10000, log_type="scan")

        # Second call should use cache
        calculator.get_scan_trend_data()
        assert mock_log_manager.get_logs.call_count == 1

        # Verify no additional calls were made
        assert mock_log_manager.get_logs.call_count == 1


class TestStatisticsCalculatorCacheExpiration:
    """Tests for cache expiration behavior - verifying cache expires after TTL."""

    def test_cache_expires_after_ttl(self, statistics_calculator, mock_log_manager):
        """Test that cache expires after 30 seconds and fetches fresh data."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        # Mock time.time() to control the passage of time
        with mock.patch("src.core.statistics_calculator.time.time") as mock_time:
            # Initial time: T=0
            mock_time.return_value = 0.0

            # First call should fetch from log_manager and cache the result
            stats1 = statistics_calculator.get_statistics(timeframe="all")
            assert mock_log_manager.get_logs.call_count == 1
            assert isinstance(stats1, ScanStatistics)

            # Advance time by 15 seconds (still within TTL)
            mock_time.return_value = 15.0

            # Second call should use cached data (cache still fresh)
            statistics_calculator.get_statistics(timeframe="all")
            assert mock_log_manager.get_logs.call_count == 1  # Still 1 - cache hit

            # Advance time by another 20 seconds (total 35 seconds - past TTL)
            mock_time.return_value = 35.0

            # Third call should fetch fresh data (cache expired)
            statistics_calculator.get_statistics(timeframe="all")
            assert mock_log_manager.get_logs.call_count == 2  # Now 2 - cache miss, fresh fetch

    def test_cache_expires_exactly_at_ttl(self, statistics_calculator, mock_log_manager):
        """Test cache expiration behavior exactly at the TTL boundary (30 seconds)."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        with mock.patch("src.core.statistics_calculator.time.time") as mock_time:
            # Initial time: T=0
            mock_time.return_value = 0.0

            # First call caches data
            statistics_calculator.get_statistics()
            assert mock_log_manager.get_logs.call_count == 1

            # At exactly 29.9 seconds - should still be cached
            mock_time.return_value = 29.9

            statistics_calculator.get_statistics()
            assert mock_log_manager.get_logs.call_count == 1  # Cache hit

            # At exactly 30.0 seconds - should expire (>= TTL)
            mock_time.return_value = 30.0

            statistics_calculator.get_statistics()
            assert mock_log_manager.get_logs.call_count == 2  # Cache miss - expired

    def test_cache_expiration_applies_to_all_methods(self, statistics_calculator, mock_log_manager):
        """Test that cache expiration applies to both get_statistics and get_scan_trend_data."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        with mock.patch("src.core.statistics_calculator.time.time") as mock_time:
            # Initial time: T=0
            mock_time.return_value = 0.0

            # First call to get_statistics caches data
            statistics_calculator.get_statistics(timeframe="all")
            assert mock_log_manager.get_logs.call_count == 1

            # Immediately call get_scan_trend_data - should use cache
            statistics_calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
            assert mock_log_manager.get_logs.call_count == 1  # Cache hit

            # Advance time past TTL (31 seconds)
            mock_time.return_value = 31.0

            # Call get_scan_trend_data again - should fetch fresh data
            statistics_calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
            assert mock_log_manager.get_logs.call_count == 2  # Cache expired

            # Call get_statistics - should use the newly cached data from previous call
            statistics_calculator.get_statistics(timeframe="all")
            assert mock_log_manager.get_logs.call_count == 2  # Cache hit with fresh cache

    def test_multiple_cache_cycles(self, statistics_calculator, mock_log_manager):
        """Test multiple cache expiration and refresh cycles."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        with mock.patch("src.core.statistics_calculator.time.time") as mock_time:
            # Cycle 1: T=0
            mock_time.return_value = 0.0
            statistics_calculator.get_statistics()
            assert mock_log_manager.get_logs.call_count == 1

            # Within TTL - cache hit
            mock_time.return_value = 10.0
            statistics_calculator.get_statistics()
            assert mock_log_manager.get_logs.call_count == 1

            # Cycle 2: After TTL expiration (35 seconds)
            mock_time.return_value = 35.0
            statistics_calculator.get_statistics()
            assert mock_log_manager.get_logs.call_count == 2

            # Within TTL - cache hit
            mock_time.return_value = 50.0
            statistics_calculator.get_statistics()
            assert mock_log_manager.get_logs.call_count == 2

            # Cycle 3: After TTL expiration (70 seconds)
            mock_time.return_value = 70.0
            statistics_calculator.get_statistics()
            assert mock_log_manager.get_logs.call_count == 3

    def test_cache_timestamp_updates_on_expiration(self, statistics_calculator, mock_log_manager):
        """Test that cache timestamp is updated when cache expires and fresh data is fetched."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        with mock.patch("src.core.statistics_calculator.time.time") as mock_time:
            # Initial fetch at T=0
            mock_time.return_value = 0.0
            statistics_calculator.get_statistics()

            # Check that cache timestamp was set to 0.0
            assert statistics_calculator._cache_timestamp == 0.0

            # Advance time past TTL
            mock_time.return_value = 40.0
            statistics_calculator.get_statistics()

            # Check that cache timestamp was updated to 40.0
            assert statistics_calculator._cache_timestamp == 40.0
            assert mock_log_manager.get_logs.call_count == 2


class TestStatisticsCalculatorCacheInvalidation:
    """Tests for cache invalidation behavior - verifying invalidate_cache() clears cache."""

    def test_invalidate_cache_clears_cache_and_forces_fresh_fetch(
        self, statistics_calculator, mock_log_manager
    ):
        """Test that invalidate_cache() clears the cache and forces fresh fetch on next access."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        # First call should fetch from log_manager and cache the result
        stats1 = statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 1
        assert isinstance(stats1, ScanStatistics)

        # Second call should use cached data (cache hit)
        statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 1  # Still 1 - cache hit

        # Invalidate the cache
        statistics_calculator.invalidate_cache()

        # Third call should fetch fresh data (cache was invalidated)
        statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 2  # Now 2 - cache invalidated, fresh fetch

    def test_invalidate_cache_clears_cache_dict(self, statistics_calculator):
        """Test that invalidate_cache() clears the internal _cache dictionary."""
        # Populate the cache by making a call
        statistics_calculator.get_statistics(timeframe="all")

        # Verify cache has data
        assert len(statistics_calculator._cache) > 0

        # Invalidate the cache
        statistics_calculator.invalidate_cache()

        # Verify cache is now empty
        assert len(statistics_calculator._cache) == 0
        assert statistics_calculator._cache == {}

    def test_invalidate_cache_resets_timestamp(self, statistics_calculator):
        """Test that invalidate_cache() resets the cache timestamp to None."""
        # Populate the cache by making a call (this sets the timestamp)
        statistics_calculator.get_statistics(timeframe="all")

        # Verify cache timestamp is set
        assert statistics_calculator._cache_timestamp is not None

        # Invalidate the cache
        statistics_calculator.invalidate_cache()

        # Verify cache timestamp is reset to None
        assert statistics_calculator._cache_timestamp is None

    def test_invalidate_cache_on_empty_cache(self, statistics_calculator):
        """Test that calling invalidate_cache() on an empty cache doesn't cause errors."""
        # Verify cache is initially empty
        assert len(statistics_calculator._cache) == 0
        assert statistics_calculator._cache_timestamp is None

        # Calling invalidate_cache() on empty cache should not raise an error
        statistics_calculator.invalidate_cache()

        # Cache should still be empty
        assert len(statistics_calculator._cache) == 0
        assert statistics_calculator._cache_timestamp is None

    def test_invalidate_cache_multiple_times(self, statistics_calculator, mock_log_manager):
        """Test that invalidate_cache() can be called multiple times safely."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        # First call to populate cache
        statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 1

        # Invalidate multiple times
        statistics_calculator.invalidate_cache()
        statistics_calculator.invalidate_cache()
        statistics_calculator.invalidate_cache()

        # Verify cache is still empty after multiple invalidations
        assert len(statistics_calculator._cache) == 0
        assert statistics_calculator._cache_timestamp is None

        # Next call should fetch fresh data
        statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 2

    def test_invalidate_cache_affects_all_methods(self, statistics_calculator, mock_log_manager):
        """Test that invalidate_cache() affects both get_statistics and get_scan_trend_data."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        # Populate cache with get_statistics
        statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 1

        # get_scan_trend_data should use cached data
        statistics_calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
        assert mock_log_manager.get_logs.call_count == 1  # Cache hit

        # Invalidate the cache
        statistics_calculator.invalidate_cache()

        # Both methods should now fetch fresh data
        statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 2  # Fresh fetch

        statistics_calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
        assert mock_log_manager.get_logs.call_count == 2  # Cache hit with new cache

    def test_invalidate_cache_with_time_progression(self, statistics_calculator, mock_log_manager):
        """Test that invalidate_cache() works independently of time-based expiration."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        with mock.patch("src.core.statistics_calculator.time.time") as mock_time:
            # Initial time: T=0
            mock_time.return_value = 0.0

            # First call caches data
            statistics_calculator.get_statistics(timeframe="all")
            assert mock_log_manager.get_logs.call_count == 1

            # Advance time by only 5 seconds (well within TTL)
            mock_time.return_value = 5.0

            # Cache should still be valid
            statistics_calculator.get_statistics(timeframe="all")
            assert mock_log_manager.get_logs.call_count == 1  # Cache hit

            # Invalidate cache (even though TTL hasn't expired)
            statistics_calculator.invalidate_cache()

            # Next call should fetch fresh data despite being within TTL
            statistics_calculator.get_statistics(timeframe="all")
            assert mock_log_manager.get_logs.call_count == 2  # Fresh fetch due to invalidation

    def test_cache_repopulates_after_invalidation(self, statistics_calculator, mock_log_manager):
        """Test that cache properly repopulates after being invalidated."""
        # Reset call count
        mock_log_manager.get_logs.reset_mock()

        # Populate cache
        statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 1
        assert len(statistics_calculator._cache) > 0
        assert statistics_calculator._cache_timestamp is not None

        # Invalidate cache
        statistics_calculator.invalidate_cache()
        assert len(statistics_calculator._cache) == 0
        assert statistics_calculator._cache_timestamp is None

        # Fetch data again - should populate cache
        statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 2
        assert len(statistics_calculator._cache) > 0  # Cache repopulated
        assert statistics_calculator._cache_timestamp is not None  # Timestamp reset

        # Verify cache works again
        statistics_calculator.get_statistics(timeframe="all")
        assert mock_log_manager.get_logs.call_count == 2  # Cache hit - no additional fetch
