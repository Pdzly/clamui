# ClamUI Statistics Calculator Tests
"""Unit tests for the StatisticsCalculator and related classes."""

import tempfile
from datetime import datetime, timedelta
from unittest import mock

import pytest

from src.core.log_manager import LogEntry, LogManager
from src.core.statistics_calculator import (
    FILES_SCANNED_PATTERNS,
    ProtectionLevel,
    ProtectionStatus,
    ScanStatistics,
    StatisticsCalculator,
    THREATS_FOUND_PATTERNS,
    Timeframe,
)


class TestTimeframeEnum:
    """Tests for the Timeframe enum."""

    def test_timeframe_values(self):
        """Test Timeframe enum has expected values."""
        assert Timeframe.DAILY.value == "daily"
        assert Timeframe.WEEKLY.value == "weekly"
        assert Timeframe.MONTHLY.value == "monthly"
        assert Timeframe.ALL.value == "all"


class TestProtectionLevelEnum:
    """Tests for the ProtectionLevel enum."""

    def test_protection_level_values(self):
        """Test ProtectionLevel enum has expected values."""
        assert ProtectionLevel.PROTECTED.value == "protected"
        assert ProtectionLevel.AT_RISK.value == "at_risk"
        assert ProtectionLevel.UNPROTECTED.value == "unprotected"
        assert ProtectionLevel.UNKNOWN.value == "unknown"


class TestScanStatistics:
    """Tests for the ScanStatistics dataclass."""

    def test_create_scan_statistics(self):
        """Test creating a ScanStatistics instance."""
        stats = ScanStatistics(
            timeframe="weekly",
            total_scans=10,
            files_scanned=5000,
            threats_detected=2,
            clean_scans=8,
            infected_scans=2,
            error_scans=0,
            average_duration=120.5,
            total_duration=1205.0,
            scheduled_scans=3,
            manual_scans=7,
            start_date="2024-01-01T00:00:00",
            end_date="2024-01-08T00:00:00",
        )
        assert stats.timeframe == "weekly"
        assert stats.total_scans == 10
        assert stats.files_scanned == 5000
        assert stats.threats_detected == 2
        assert stats.clean_scans == 8
        assert stats.infected_scans == 2
        assert stats.error_scans == 0
        assert stats.average_duration == 120.5
        assert stats.total_duration == 1205.0
        assert stats.scheduled_scans == 3
        assert stats.manual_scans == 7

    def test_scan_statistics_to_dict(self):
        """Test ScanStatistics.to_dict serialization."""
        stats = ScanStatistics(
            timeframe="daily",
            total_scans=5,
            files_scanned=1000,
            threats_detected=0,
            clean_scans=5,
            infected_scans=0,
            error_scans=0,
            average_duration=60.0,
            total_duration=300.0,
            scheduled_scans=1,
            manual_scans=4,
            start_date="2024-01-15T00:00:00",
            end_date="2024-01-16T00:00:00",
        )
        data = stats.to_dict()

        assert data["timeframe"] == "daily"
        assert data["total_scans"] == 5
        assert data["files_scanned"] == 1000
        assert data["threats_detected"] == 0
        assert data["clean_scans"] == 5
        assert data["infected_scans"] == 0
        assert data["error_scans"] == 0
        assert data["average_duration"] == 60.0
        assert data["total_duration"] == 300.0
        assert data["scheduled_scans"] == 1
        assert data["manual_scans"] == 4
        assert data["start_date"] == "2024-01-15T00:00:00"
        assert data["end_date"] == "2024-01-16T00:00:00"

    def test_scan_statistics_optional_dates(self):
        """Test ScanStatistics with None dates."""
        stats = ScanStatistics(
            timeframe="all",
            total_scans=100,
            files_scanned=50000,
            threats_detected=5,
            clean_scans=95,
            infected_scans=5,
            error_scans=0,
            average_duration=90.0,
            total_duration=9000.0,
            scheduled_scans=50,
            manual_scans=50,
            start_date=None,
            end_date=None,
        )
        data = stats.to_dict()
        assert data["start_date"] is None
        assert data["end_date"] is None


class TestProtectionStatus:
    """Tests for the ProtectionStatus dataclass."""

    def test_create_protection_status(self):
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
            last_definition_update="2024-01-14T08:00:00",
            definition_age_hours=26.0,
            message="Last scan was over a week ago",
            is_protected=False,
        )
        data = status.to_dict()

        assert data["level"] == "at_risk"
        assert data["last_scan_timestamp"] == "2024-01-10T10:00:00"
        assert data["last_scan_age_hours"] == 120.0
        assert data["last_definition_update"] == "2024-01-14T08:00:00"
        assert data["definition_age_hours"] == 26.0
        assert data["message"] == "Last scan was over a week ago"
        assert data["is_protected"] is False

    def test_protection_status_with_none_values(self):
        """Test ProtectionStatus with None optional values."""
        status = ProtectionStatus(
            level="unprotected",
            last_scan_timestamp=None,
            last_scan_age_hours=None,
            last_definition_update=None,
            definition_age_hours=None,
            message="No scans performed yet",
            is_protected=False,
        )
        data = status.to_dict()
        assert data["last_scan_timestamp"] is None
        assert data["last_scan_age_hours"] is None
        assert data["last_definition_update"] is None
        assert data["definition_age_hours"] is None


class TestPrecompiledPatterns:
    """Tests for pre-compiled regex patterns at module level."""

    def test_files_scanned_patterns_defined(self):
        """Test FILES_SCANNED_PATTERNS is defined at module level."""
        assert FILES_SCANNED_PATTERNS is not None

    def test_files_scanned_patterns_is_list(self):
        """Test FILES_SCANNED_PATTERNS is a list."""
        assert isinstance(FILES_SCANNED_PATTERNS, list)

    def test_files_scanned_patterns_count(self):
        """Test FILES_SCANNED_PATTERNS has expected number of patterns."""
        assert len(FILES_SCANNED_PATTERNS) == 4

    def test_files_scanned_patterns_are_compiled_regex(self):
        """Test FILES_SCANNED_PATTERNS contains compiled regex objects."""
        import re
        for pattern in FILES_SCANNED_PATTERNS:
            assert isinstance(pattern, type(re.compile("")))

    def test_threats_found_patterns_defined(self):
        """Test THREATS_FOUND_PATTERNS is defined at module level."""
        assert THREATS_FOUND_PATTERNS is not None

    def test_threats_found_patterns_is_list(self):
        """Test THREATS_FOUND_PATTERNS is a list."""
        assert isinstance(THREATS_FOUND_PATTERNS, list)

    def test_threats_found_patterns_count(self):
        """Test THREATS_FOUND_PATTERNS has expected number of patterns."""
        assert len(THREATS_FOUND_PATTERNS) == 3

    def test_threats_found_patterns_are_compiled_regex(self):
        """Test THREATS_FOUND_PATTERNS contains compiled regex objects."""
        import re
        for pattern in THREATS_FOUND_PATTERNS:
            assert isinstance(pattern, type(re.compile("")))


class TestStatisticsCalculator:
    """Tests for the StatisticsCalculator class."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    @pytest.fixture
    def calculator(self, log_manager):
        """Create a StatisticsCalculator with the test LogManager."""
        return StatisticsCalculator(log_manager=log_manager)

    def test_init_with_log_manager(self, log_manager):
        """Test StatisticsCalculator initialization with LogManager."""
        calc = StatisticsCalculator(log_manager=log_manager)
        assert calc._log_manager is log_manager

    def test_init_without_log_manager(self, monkeypatch):
        """Test StatisticsCalculator creates its own LogManager if not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("XDG_DATA_HOME", tmpdir)
            calc = StatisticsCalculator()
            assert calc._log_manager is not None
            assert isinstance(calc._log_manager, LogManager)


class TestStatisticsCalculatorTimeframeRange:
    """Tests for timeframe range calculation."""

    @pytest.fixture
    def calculator(self):
        """Create a StatisticsCalculator with mocked LogManager."""
        mock_log_manager = mock.Mock(spec=LogManager)
        mock_log_manager.get_logs.return_value = []
        return StatisticsCalculator(log_manager=mock_log_manager)

    def test_get_timeframe_range_daily(self, calculator):
        """Test daily timeframe range calculation."""
        start, end = calculator._get_timeframe_range("daily")
        delta = end - start
        # Should be approximately 1 day
        assert delta.days == 1 or (delta.days == 0 and delta.seconds > 0)

    def test_get_timeframe_range_weekly(self, calculator):
        """Test weekly timeframe range calculation."""
        start, end = calculator._get_timeframe_range("weekly")
        delta = end - start
        # Should be approximately 7 days
        assert 6 <= delta.days <= 7

    def test_get_timeframe_range_monthly(self, calculator):
        """Test monthly timeframe range calculation."""
        start, end = calculator._get_timeframe_range("monthly")
        delta = end - start
        # Should be approximately 30 days
        assert 29 <= delta.days <= 30

    def test_get_timeframe_range_all(self, calculator):
        """Test 'all' timeframe range calculation."""
        start, end = calculator._get_timeframe_range("all")
        # Start should be epoch (1970)
        assert start.year == 1970


class TestStatisticsCalculatorTimestampParsing:
    """Tests for timestamp parsing functionality."""

    @pytest.fixture
    def calculator(self):
        """Create a StatisticsCalculator with mocked LogManager."""
        mock_log_manager = mock.Mock(spec=LogManager)
        mock_log_manager.get_logs.return_value = []
        return StatisticsCalculator(log_manager=mock_log_manager)

    def test_parse_timestamp_valid_iso(self, calculator):
        """Test parsing valid ISO format timestamp."""
        result = calculator._parse_timestamp("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_timestamp_with_microseconds(self, calculator):
        """Test parsing timestamp with microseconds."""
        result = calculator._parse_timestamp("2024-01-15T10:30:00.123456")
        assert result is not None
        assert result.year == 2024

    def test_parse_timestamp_with_z_suffix(self, calculator):
        """Test parsing timestamp with Z suffix (UTC)."""
        result = calculator._parse_timestamp("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024

    def test_parse_timestamp_invalid(self, calculator):
        """Test parsing invalid timestamp returns None."""
        result = calculator._parse_timestamp("invalid-timestamp")
        assert result is None

    def test_parse_timestamp_empty(self, calculator):
        """Test parsing empty timestamp returns None."""
        result = calculator._parse_timestamp("")
        assert result is None


class TestStatisticsCalculatorFilesScannedExtraction:
    """Tests for extracting files scanned count from log entries."""

    @pytest.fixture
    def calculator(self):
        """Create a StatisticsCalculator with mocked LogManager."""
        mock_log_manager = mock.Mock(spec=LogManager)
        return StatisticsCalculator(log_manager=mock_log_manager)

    def test_extract_files_scanned_pattern_1(self, calculator):
        """Test extracting file count from 'X files scanned' pattern."""
        entry = LogEntry(
            id="test-1",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="clean",
            summary="500 files scanned",
            details="",
        )
        result = calculator._extract_files_scanned(entry)
        assert result == 500

    def test_extract_files_scanned_pattern_2(self, calculator):
        """Test extracting file count from 'Scanned X files' pattern."""
        entry = LogEntry(
            id="test-2",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="clean",
            summary="Scanned 1234 files",
            details="",
        )
        result = calculator._extract_files_scanned(entry)
        assert result == 1234

    def test_extract_files_scanned_from_details(self, calculator):
        """Test extracting file count from details field."""
        entry = LogEntry(
            id="test-3",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="clean",
            summary="Scan complete",
            details="Files: 2500",
        )
        result = calculator._extract_files_scanned(entry)
        assert result == 2500

    def test_extract_files_scanned_no_match(self, calculator):
        """Test extracting file count returns 0 when no pattern matches."""
        entry = LogEntry(
            id="test-4",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="clean",
            summary="Scan complete",
            details="No threats found",
        )
        result = calculator._extract_files_scanned(entry)
        assert result == 0


class TestStatisticsCalculatorThreatsExtraction:
    """Tests for extracting threats count from log entries."""

    @pytest.fixture
    def calculator(self):
        """Create a StatisticsCalculator with mocked LogManager."""
        mock_log_manager = mock.Mock(spec=LogManager)
        return StatisticsCalculator(log_manager=mock_log_manager)

    def test_extract_threats_found_clean_scan(self, calculator):
        """Test threats count is 0 for clean scans."""
        entry = LogEntry(
            id="test-1",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="clean",
            summary="No threats found",
            details="",
        )
        result = calculator._extract_threats_found(entry)
        assert result == 0

    def test_extract_threats_found_infected_with_count(self, calculator):
        """Test extracting threat count from infected scan with count."""
        entry = LogEntry(
            id="test-2",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="infected",
            summary="3 threats detected",
            details="",
        )
        result = calculator._extract_threats_found(entry)
        assert result == 3

    def test_extract_threats_found_infected_default(self, calculator):
        """Test infected scan defaults to 1 threat when count not found."""
        entry = LogEntry(
            id="test-3",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="infected",
            summary="Malware found",
            details="",
        )
        result = calculator._extract_threats_found(entry)
        assert result == 1

    def test_extract_threats_found_pattern_found(self, calculator):
        """Test extracting threat count from 'Found X' pattern."""
        entry = LogEntry(
            id="test-4",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="infected",
            summary="Found 5 items",
            details="",
        )
        result = calculator._extract_threats_found(entry)
        assert result == 5


class TestStatisticsCalculatorGetStatistics:
    """Tests for the get_statistics method."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    @pytest.fixture
    def calculator(self, log_manager):
        """Create a StatisticsCalculator with the test LogManager."""
        return StatisticsCalculator(log_manager=log_manager)

    def test_get_statistics_empty_logs(self, calculator):
        """Test get_statistics with no scan logs."""
        stats = calculator.get_statistics()
        assert stats.total_scans == 0
        assert stats.files_scanned == 0
        assert stats.threats_detected == 0
        assert stats.clean_scans == 0
        assert stats.infected_scans == 0
        assert stats.error_scans == 0
        assert stats.average_duration == 0.0
        assert stats.total_duration == 0.0

    def test_get_statistics_all_timeframe(self, calculator, log_manager):
        """Test get_statistics with 'all' timeframe."""
        # Create test entries
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="100 files scanned",
            details="",
            duration=60.0,
        )
        entry2 = LogEntry.create(
            log_type="scan",
            status="infected",
            summary="2 threats detected",
            details="",
            duration=120.0,
        )
        log_manager.save_log(entry1)
        log_manager.save_log(entry2)

        stats = calculator.get_statistics(timeframe="all")
        assert stats.timeframe == "all"
        assert stats.total_scans == 2
        assert stats.clean_scans == 1
        assert stats.infected_scans == 1
        assert stats.total_duration == 180.0
        assert stats.average_duration == 90.0

    def test_get_statistics_counts_scan_types(self, calculator, log_manager):
        """Test get_statistics correctly counts scan types."""
        # Create entries with different statuses
        clean_entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Clean scan",
            details="",
        )
        infected_entry = LogEntry.create(
            log_type="scan",
            status="infected",
            summary="Infected",
            details="",
        )
        error_entry = LogEntry.create(
            log_type="scan",
            status="error",
            summary="Error occurred",
            details="",
        )
        log_manager.save_log(clean_entry)
        log_manager.save_log(infected_entry)
        log_manager.save_log(error_entry)

        stats = calculator.get_statistics(timeframe="all")
        assert stats.total_scans == 3
        assert stats.clean_scans == 1
        assert stats.infected_scans == 1
        assert stats.error_scans == 1

    def test_get_statistics_counts_scheduled_vs_manual(self, calculator, log_manager):
        """Test get_statistics correctly counts scheduled vs manual scans."""
        scheduled_entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scheduled scan",
            details="",
            scheduled=True,
        )
        manual_entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Manual scan 1",
            details="",
            scheduled=False,
        )
        manual_entry2 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Manual scan 2",
            details="",
            scheduled=False,
        )
        log_manager.save_log(scheduled_entry)
        log_manager.save_log(manual_entry1)
        log_manager.save_log(manual_entry2)

        stats = calculator.get_statistics(timeframe="all")
        assert stats.scheduled_scans == 1
        assert stats.manual_scans == 2

    def test_get_statistics_ignores_update_logs(self, calculator, log_manager):
        """Test get_statistics only counts scan logs, not update logs."""
        scan_entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scan",
            details="",
        )
        update_entry = LogEntry.create(
            log_type="update",
            status="success",
            summary="Database updated",
            details="",
        )
        log_manager.save_log(scan_entry)
        log_manager.save_log(update_entry)

        stats = calculator.get_statistics(timeframe="all")
        assert stats.total_scans == 1

    def test_get_statistics_calculates_average_duration(self, calculator, log_manager):
        """Test get_statistics correctly calculates average duration."""
        entry1 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scan 1",
            details="",
            duration=100.0,
        )
        entry2 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scan 2",
            details="",
            duration=200.0,
        )
        entry3 = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Scan 3",
            details="",
            duration=300.0,
        )
        log_manager.save_log(entry1)
        log_manager.save_log(entry2)
        log_manager.save_log(entry3)

        stats = calculator.get_statistics(timeframe="all")
        assert stats.total_duration == 600.0
        assert stats.average_duration == 200.0


class TestStatisticsCalculatorTimeframeFiltering:
    """Tests for timeframe filtering functionality."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    @pytest.fixture
    def calculator(self, log_manager):
        """Create a StatisticsCalculator with the test LogManager."""
        return StatisticsCalculator(log_manager=log_manager)

    def test_filter_entries_by_timeframe_all(self, calculator):
        """Test that 'all' timeframe returns all entries."""
        now = datetime.now()
        entries = [
            LogEntry(
                id="1",
                timestamp=(now - timedelta(days=365)).isoformat(),
                type="scan",
                status="clean",
                summary="Old scan",
                details="",
            ),
            LogEntry(
                id="2",
                timestamp=now.isoformat(),
                type="scan",
                status="clean",
                summary="Recent scan",
                details="",
            ),
        ]
        filtered = calculator._filter_entries_by_timeframe(entries, "all")
        assert len(filtered) == 2

    def test_filter_entries_by_timeframe_daily(self, calculator):
        """Test that 'daily' timeframe filters correctly."""
        now = datetime.now()
        entries = [
            LogEntry(
                id="1",
                timestamp=(now - timedelta(hours=2)).isoformat(),
                type="scan",
                status="clean",
                summary="Recent scan",
                details="",
            ),
            LogEntry(
                id="2",
                timestamp=(now - timedelta(days=5)).isoformat(),
                type="scan",
                status="clean",
                summary="Old scan",
                details="",
            ),
        ]
        filtered = calculator._filter_entries_by_timeframe(entries, "daily")
        assert len(filtered) == 1
        assert filtered[0].id == "1"

    def test_filter_entries_by_timeframe_weekly(self, calculator):
        """Test that 'weekly' timeframe filters correctly."""
        now = datetime.now()
        entries = [
            LogEntry(
                id="1",
                timestamp=(now - timedelta(days=3)).isoformat(),
                type="scan",
                status="clean",
                summary="This week scan",
                details="",
            ),
            LogEntry(
                id="2",
                timestamp=(now - timedelta(days=14)).isoformat(),
                type="scan",
                status="clean",
                summary="Two weeks ago scan",
                details="",
            ),
        ]
        filtered = calculator._filter_entries_by_timeframe(entries, "weekly")
        assert len(filtered) == 1
        assert filtered[0].id == "1"

    def test_filter_entries_by_timeframe_monthly(self, calculator):
        """Test that 'monthly' timeframe filters correctly."""
        now = datetime.now()
        entries = [
            LogEntry(
                id="1",
                timestamp=(now - timedelta(days=15)).isoformat(),
                type="scan",
                status="clean",
                summary="This month scan",
                details="",
            ),
            LogEntry(
                id="2",
                timestamp=(now - timedelta(days=60)).isoformat(),
                type="scan",
                status="clean",
                summary="Two months ago scan",
                details="",
            ),
        ]
        filtered = calculator._filter_entries_by_timeframe(entries, "monthly")
        assert len(filtered) == 1
        assert filtered[0].id == "1"


class TestStatisticsCalculatorAverageDuration:
    """Tests for the calculate_average_duration method."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    @pytest.fixture
    def calculator(self, log_manager):
        """Create a StatisticsCalculator with the test LogManager."""
        return StatisticsCalculator(log_manager=log_manager)

    def test_calculate_average_duration_empty(self, calculator):
        """Test average duration is 0 when no scans exist."""
        result = calculator.calculate_average_duration()
        assert result == 0.0

    def test_calculate_average_duration_single_scan(self, calculator, log_manager):
        """Test average duration with single scan."""
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="",
            duration=150.0,
        )
        log_manager.save_log(entry)

        result = calculator.calculate_average_duration()
        assert result == 150.0

    def test_calculate_average_duration_multiple_scans(self, calculator, log_manager):
        """Test average duration with multiple scans."""
        for duration in [100.0, 200.0, 300.0, 400.0]:
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary="Test scan",
                details="",
                duration=duration,
            )
            log_manager.save_log(entry)

        result = calculator.calculate_average_duration()
        assert result == 250.0  # (100+200+300+400) / 4


class TestStatisticsCalculatorProtectionStatus:
    """Tests for the get_protection_status method."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    @pytest.fixture
    def calculator(self, log_manager):
        """Create a StatisticsCalculator with the test LogManager."""
        return StatisticsCalculator(log_manager=log_manager)

    def test_protection_status_no_scans(self, calculator):
        """Test protection status when no scans have been performed."""
        status = calculator.get_protection_status()
        assert status.level == ProtectionLevel.UNPROTECTED.value
        assert status.is_protected is False
        assert "no scans" in status.message.lower()
        assert status.last_scan_timestamp is None

    def test_protection_status_recent_scan_protected(self, calculator, log_manager):
        """Test protection status with recent scan is protected."""
        # Create a recent scan
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Recent scan",
            details="",
        )
        log_manager.save_log(entry)

        status = calculator.get_protection_status()
        assert status.level == ProtectionLevel.PROTECTED.value
        assert status.is_protected is True
        assert status.last_scan_timestamp is not None
        assert status.last_scan_age_hours is not None
        assert status.last_scan_age_hours < 1  # Less than 1 hour ago

    def test_protection_status_old_scan_at_risk(self, calculator, log_manager):
        """Test protection status with scan over a week old is at_risk."""
        # Create an old scan (8 days ago)
        old_timestamp = (datetime.now() - timedelta(days=8)).isoformat()
        entry = LogEntry(
            id="old-scan",
            timestamp=old_timestamp,
            type="scan",
            status="clean",
            summary="Old scan",
            details="",
        )
        log_manager.save_log(entry)

        status = calculator.get_protection_status()
        assert status.level == ProtectionLevel.AT_RISK.value
        assert status.is_protected is False
        assert "week" in status.message.lower()

    def test_protection_status_very_old_scan_unprotected(self, calculator, log_manager):
        """Test protection status with scan over 30 days old is unprotected."""
        # Create a very old scan (35 days ago)
        old_timestamp = (datetime.now() - timedelta(days=35)).isoformat()
        entry = LogEntry(
            id="very-old-scan",
            timestamp=old_timestamp,
            type="scan",
            status="clean",
            summary="Very old scan",
            details="",
        )
        log_manager.save_log(entry)

        status = calculator.get_protection_status()
        assert status.level == ProtectionLevel.UNPROTECTED.value
        assert status.is_protected is False
        assert "30 days" in status.message.lower()

    def test_protection_status_with_stale_definitions(self, calculator, log_manager):
        """Test protection status with outdated definitions."""
        # Create a recent scan
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Recent scan",
            details="",
        )
        log_manager.save_log(entry)

        # Definitions are 8 days old
        old_def_timestamp = (datetime.now() - timedelta(days=8)).isoformat()
        status = calculator.get_protection_status(last_definition_update=old_def_timestamp)
        assert status.level == ProtectionLevel.AT_RISK.value
        assert "definitions" in status.message.lower() or "outdated" in status.message.lower()

    def test_protection_status_with_fresh_definitions(self, calculator, log_manager):
        """Test protection status with fresh definitions."""
        # Create a recent scan
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Recent scan",
            details="",
        )
        log_manager.save_log(entry)

        # Definitions are fresh (1 hour old)
        fresh_def_timestamp = (datetime.now() - timedelta(hours=1)).isoformat()
        status = calculator.get_protection_status(last_definition_update=fresh_def_timestamp)
        assert status.level == ProtectionLevel.PROTECTED.value
        assert status.is_protected is True

    def test_protection_status_includes_definition_age(self, calculator, log_manager):
        """Test protection status includes definition age when provided."""
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Recent scan",
            details="",
        )
        log_manager.save_log(entry)

        def_timestamp = (datetime.now() - timedelta(hours=12)).isoformat()
        status = calculator.get_protection_status(last_definition_update=def_timestamp)
        assert status.definition_age_hours is not None
        assert 11 <= status.definition_age_hours <= 13


class TestStatisticsCalculatorScanTrendData:
    """Tests for the get_scan_trend_data method."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    @pytest.fixture
    def calculator(self, log_manager):
        """Create a StatisticsCalculator with the test LogManager."""
        return StatisticsCalculator(log_manager=log_manager)

    def test_get_scan_trend_data_empty(self, calculator):
        """Test trend data with no scans returns empty data points."""
        trend = calculator.get_scan_trend_data(timeframe="weekly", data_points=7)
        assert len(trend) == 7
        for point in trend:
            assert point["scans"] == 0
            assert point["threats"] == 0
            assert "date" in point

    def test_get_scan_trend_data_returns_correct_points(self, calculator):
        """Test trend data returns requested number of data points."""
        trend = calculator.get_scan_trend_data(timeframe="weekly", data_points=5)
        assert len(trend) == 5

    def test_get_scan_trend_data_has_dates(self, calculator):
        """Test trend data includes ISO date strings."""
        trend = calculator.get_scan_trend_data(timeframe="daily", data_points=4)
        for point in trend:
            assert "date" in point
            # Should be parseable as ISO format
            datetime.fromisoformat(point["date"])

    def test_get_scan_trend_data_aggregates_scans(self, calculator, log_manager):
        """Test trend data correctly aggregates scan counts."""
        # Create several scans within the timeframe
        for _ in range(5):
            entry = LogEntry.create(
                log_type="scan",
                status="clean",
                summary="Test scan",
                details="",
            )
            log_manager.save_log(entry)

        trend = calculator.get_scan_trend_data(timeframe="daily", data_points=4)
        total_scans = sum(point["scans"] for point in trend)
        # All 5 scans should be counted somewhere in the trend data
        assert total_scans == 5


class TestStatisticsCalculatorHasScanHistory:
    """Tests for the has_scan_history method."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def log_manager(self, temp_log_dir):
        """Create a LogManager with a temporary directory."""
        return LogManager(log_dir=temp_log_dir)

    @pytest.fixture
    def calculator(self, log_manager):
        """Create a StatisticsCalculator with the test LogManager."""
        return StatisticsCalculator(log_manager=log_manager)

    def test_has_scan_history_no_logs(self, calculator):
        """Test has_scan_history returns False when no scans exist."""
        assert calculator.has_scan_history() is False

    def test_has_scan_history_with_scan_logs(self, calculator, log_manager):
        """Test has_scan_history returns True when scans exist."""
        entry = LogEntry.create(
            log_type="scan",
            status="clean",
            summary="Test scan",
            details="",
        )
        log_manager.save_log(entry)
        assert calculator.has_scan_history() is True

    def test_has_scan_history_only_update_logs(self, calculator, log_manager):
        """Test has_scan_history returns False when only update logs exist."""
        entry = LogEntry.create(
            log_type="update",
            status="success",
            summary="Database updated",
            details="",
        )
        log_manager.save_log(entry)
        assert calculator.has_scan_history() is False


class TestStatisticsCalculatorEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def calculator(self):
        """Create a StatisticsCalculator with mocked LogManager."""
        mock_log_manager = mock.Mock(spec=LogManager)
        mock_log_manager.get_logs.return_value = []
        return StatisticsCalculator(log_manager=mock_log_manager)

    def test_get_statistics_with_invalid_timeframe(self, calculator):
        """Test get_statistics handles invalid timeframe gracefully."""
        # Should default to 'all' behavior
        stats = calculator.get_statistics(timeframe="invalid")
        assert stats.timeframe == "invalid"
        assert stats.total_scans == 0

    def test_parse_timestamp_with_none(self, calculator):
        """Test _parse_timestamp handles None input."""
        # Should not crash
        result = calculator._parse_timestamp(None)
        assert result is None

    def test_extract_files_scanned_with_large_numbers(self, calculator):
        """Test extracting large file counts."""
        entry = LogEntry(
            id="test",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="clean",
            summary="1000000 files scanned",
            details="",
        )
        result = calculator._extract_files_scanned(entry)
        assert result == 1000000

    def test_statistics_with_zero_duration_entries(self, calculator):
        """Test statistics calculation with zero duration entries."""
        mock_log_manager = calculator._log_manager
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now().isoformat(),
                type="scan",
                status="clean",
                summary="Scan 1",
                details="",
                duration=0.0,
            ),
            LogEntry(
                id="2",
                timestamp=datetime.now().isoformat(),
                type="scan",
                status="clean",
                summary="Scan 2",
                details="",
                duration=0.0,
            ),
        ]
        mock_log_manager.get_logs.return_value = entries

        stats = calculator.get_statistics()
        assert stats.average_duration == 0.0
        assert stats.total_duration == 0.0
