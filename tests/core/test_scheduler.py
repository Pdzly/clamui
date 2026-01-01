# ClamUI Scheduler Tests
"""Unit tests for the Scheduler class."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from src.core.scheduler import (
    Scheduler,
    SchedulerBackend,
    ScheduleFrequency,
    ScheduleConfig,
    _check_systemd_available,
    _check_cron_available,
)


class TestScheduleConfig:
    """Tests for ScheduleConfig dataclass."""

    def test_schedule_config_defaults(self):
        """Test ScheduleConfig has correct default values."""
        config = ScheduleConfig()
        assert config.enabled is False
        assert config.frequency == ScheduleFrequency.DAILY
        assert config.time == "02:00"
        assert config.targets == []
        assert config.skip_on_battery is True
        assert config.auto_quarantine is False
        assert config.day_of_week == 0
        assert config.day_of_month == 1

    def test_schedule_config_custom_values(self):
        """Test ScheduleConfig accepts custom values."""
        config = ScheduleConfig(
            enabled=True,
            frequency=ScheduleFrequency.WEEKLY,
            time="14:30",
            targets=["/home/user/Documents"],
            skip_on_battery=False,
            auto_quarantine=True,
            day_of_week=3,
            day_of_month=15
        )
        assert config.enabled is True
        assert config.frequency == ScheduleFrequency.WEEKLY
        assert config.time == "14:30"
        assert config.targets == ["/home/user/Documents"]
        assert config.skip_on_battery is False
        assert config.auto_quarantine is True
        assert config.day_of_week == 3
        assert config.day_of_month == 15


class TestScheduleFrequency:
    """Tests for ScheduleFrequency enum."""

    def test_frequency_values(self):
        """Test ScheduleFrequency enum values."""
        assert ScheduleFrequency.HOURLY.value == "hourly"
        assert ScheduleFrequency.DAILY.value == "daily"
        assert ScheduleFrequency.WEEKLY.value == "weekly"
        assert ScheduleFrequency.MONTHLY.value == "monthly"

    def test_frequency_from_string(self):
        """Test ScheduleFrequency can be created from string."""
        assert ScheduleFrequency("hourly") == ScheduleFrequency.HOURLY
        assert ScheduleFrequency("daily") == ScheduleFrequency.DAILY
        assert ScheduleFrequency("weekly") == ScheduleFrequency.WEEKLY
        assert ScheduleFrequency("monthly") == ScheduleFrequency.MONTHLY


class TestSchedulerBackendDetection:
    """Tests for scheduler backend detection."""

    def test_check_systemd_available_returns_bool(self):
        """Test _check_systemd_available returns a boolean."""
        # Reset cache to test fresh
        import src.core.scheduler
        src.core.scheduler._systemd_available = None

        result = _check_systemd_available()
        assert isinstance(result, bool)

    def test_check_cron_available_returns_bool(self):
        """Test _check_cron_available returns a boolean."""
        # Reset cache to test fresh
        import src.core.scheduler
        src.core.scheduler._cron_available = None

        result = _check_cron_available()
        assert isinstance(result, bool)


class TestSchedulerInit:
    """Tests for Scheduler initialization."""

    def test_scheduler_init_default(self):
        """Test Scheduler initializes with default config directory."""
        scheduler = Scheduler()
        # Should have detected a backend (or NONE if neither available)
        assert scheduler.backend in [
            SchedulerBackend.SYSTEMD,
            SchedulerBackend.CRON,
            SchedulerBackend.NONE
        ]

    def test_scheduler_init_custom_config_dir(self):
        """Test Scheduler with custom config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(config_dir=Path(tmpdir))
            assert scheduler._config_dir == Path(tmpdir)


class TestSchedulerProperties:
    """Tests for Scheduler properties."""

    def test_backend_property(self):
        """Test backend property returns correct value."""
        scheduler = Scheduler()
        assert isinstance(scheduler.backend, SchedulerBackend)

    def test_is_available_property(self):
        """Test is_available property."""
        scheduler = Scheduler()
        # is_available should be True if backend is not NONE
        expected = scheduler.backend != SchedulerBackend.NONE
        assert scheduler.is_available == expected

    def test_get_backend_name(self):
        """Test get_backend_name returns human-readable name."""
        scheduler = Scheduler()

        if scheduler.backend == SchedulerBackend.SYSTEMD:
            assert scheduler.get_backend_name() == "systemd timers"
        elif scheduler.backend == SchedulerBackend.CRON:
            assert scheduler.get_backend_name() == "cron"
        else:
            assert scheduler.get_backend_name() == "none"


class TestSchedulerOnCalendar:
    """Tests for Scheduler._generate_oncalendar()."""

    @pytest.fixture
    def scheduler(self):
        """Create a Scheduler instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Scheduler(config_dir=Path(tmpdir))

    def test_generate_oncalendar_hourly(self, scheduler):
        """Test OnCalendar generation for hourly schedule."""
        result = scheduler._generate_oncalendar(ScheduleFrequency.HOURLY, "02:00")
        # Hourly ignores the time parameter and runs at minute 0 of every hour
        assert result == "*-*-* *:00:00"

    def test_generate_oncalendar_daily(self, scheduler):
        """Test OnCalendar generation for daily schedule."""
        result = scheduler._generate_oncalendar(ScheduleFrequency.DAILY, "02:00")
        assert result == "*-*-* 02:00:00"

    def test_generate_oncalendar_daily_different_time(self, scheduler):
        """Test OnCalendar generation for daily with different time."""
        result = scheduler._generate_oncalendar(ScheduleFrequency.DAILY, "14:30")
        assert result == "*-*-* 14:30:00"

    def test_generate_oncalendar_weekly_monday(self, scheduler):
        """Test OnCalendar generation for weekly on Monday."""
        result = scheduler._generate_oncalendar(
            ScheduleFrequency.WEEKLY, "02:00", day_of_week=0
        )
        assert result == "Mon *-*-* 02:00:00"

    def test_generate_oncalendar_weekly_friday(self, scheduler):
        """Test OnCalendar generation for weekly on Friday."""
        result = scheduler._generate_oncalendar(
            ScheduleFrequency.WEEKLY, "03:00", day_of_week=4
        )
        assert result == "Fri *-*-* 03:00:00"

    def test_generate_oncalendar_weekly_sunday(self, scheduler):
        """Test OnCalendar generation for weekly on Sunday."""
        result = scheduler._generate_oncalendar(
            ScheduleFrequency.WEEKLY, "08:00", day_of_week=6
        )
        assert result == "Sun *-*-* 08:00:00"

    def test_generate_oncalendar_monthly_first(self, scheduler):
        """Test OnCalendar generation for monthly on 1st."""
        result = scheduler._generate_oncalendar(
            ScheduleFrequency.MONTHLY, "02:00", day_of_month=1
        )
        assert result == "*-*-01 02:00:00"

    def test_generate_oncalendar_monthly_fifteenth(self, scheduler):
        """Test OnCalendar generation for monthly on 15th."""
        result = scheduler._generate_oncalendar(
            ScheduleFrequency.MONTHLY, "04:00", day_of_month=15
        )
        assert result == "*-*-15 04:00:00"

    def test_generate_oncalendar_monthly_clamps_day(self, scheduler):
        """Test OnCalendar clamps day_of_month to 1-28 range."""
        # Day 31 should be clamped to 28
        result = scheduler._generate_oncalendar(
            ScheduleFrequency.MONTHLY, "02:00", day_of_month=31
        )
        assert result == "*-*-28 02:00:00"

        # Day 0 should be clamped to 1
        result = scheduler._generate_oncalendar(
            ScheduleFrequency.MONTHLY, "02:00", day_of_month=0
        )
        assert result == "*-*-01 02:00:00"

    def test_generate_oncalendar_invalid_time(self, scheduler):
        """Test OnCalendar handles invalid time format."""
        result = scheduler._generate_oncalendar(ScheduleFrequency.DAILY, "invalid")
        # Should default to 02:00:00
        assert result == "*-*-* 02:00:00"


class TestSchedulerCrontabEntry:
    """Tests for Scheduler._generate_crontab_entry()."""

    @pytest.fixture
    def scheduler(self):
        """Create a Scheduler instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Scheduler(config_dir=Path(tmpdir))

    def test_generate_crontab_hourly(self, scheduler):
        """Test crontab entry for hourly schedule."""
        result = scheduler._generate_crontab_entry(ScheduleFrequency.HOURLY, "02:00")
        # Hourly runs at minute 0 of every hour
        assert result == "0 * * * *"

    def test_generate_crontab_daily(self, scheduler):
        """Test crontab entry for daily schedule."""
        result = scheduler._generate_crontab_entry(ScheduleFrequency.DAILY, "02:00")
        assert result == "0 2 * * *"

    def test_generate_crontab_daily_different_time(self, scheduler):
        """Test crontab entry for daily with different time."""
        result = scheduler._generate_crontab_entry(ScheduleFrequency.DAILY, "14:30")
        assert result == "30 14 * * *"

    def test_generate_crontab_weekly_monday(self, scheduler):
        """Test crontab entry for weekly on Monday."""
        # 0=Monday in our format, cron uses 1=Monday
        result = scheduler._generate_crontab_entry(
            ScheduleFrequency.WEEKLY, "02:00", day_of_week=0
        )
        assert result == "0 2 * * 1"

    def test_generate_crontab_weekly_friday(self, scheduler):
        """Test crontab entry for weekly on Friday."""
        # 4=Friday in our format, cron uses 5=Friday
        result = scheduler._generate_crontab_entry(
            ScheduleFrequency.WEEKLY, "03:00", day_of_week=4
        )
        assert result == "0 3 * * 5"

    def test_generate_crontab_weekly_sunday(self, scheduler):
        """Test crontab entry for weekly on Sunday."""
        # 6=Sunday in our format, cron uses 0=Sunday
        result = scheduler._generate_crontab_entry(
            ScheduleFrequency.WEEKLY, "08:00", day_of_week=6
        )
        assert result == "0 8 * * 0"

    def test_generate_crontab_monthly(self, scheduler):
        """Test crontab entry for monthly schedule."""
        result = scheduler._generate_crontab_entry(
            ScheduleFrequency.MONTHLY, "02:00", day_of_month=1
        )
        assert result == "0 2 1 * *"

    def test_generate_crontab_monthly_fifteenth(self, scheduler):
        """Test crontab entry for monthly on 15th."""
        result = scheduler._generate_crontab_entry(
            ScheduleFrequency.MONTHLY, "04:00", day_of_month=15
        )
        assert result == "0 4 15 * *"

    def test_generate_crontab_invalid_time(self, scheduler):
        """Test crontab entry handles invalid time format."""
        result = scheduler._generate_crontab_entry(ScheduleFrequency.DAILY, "invalid")
        # Should default to 02:00
        assert result == "0 2 * * *"


class TestSchedulerServiceFiles:
    """Tests for Scheduler service/timer file generation."""

    @pytest.fixture
    def scheduler(self):
        """Create a Scheduler instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Scheduler(config_dir=Path(tmpdir))

    def test_generate_service_file(self, scheduler):
        """Test service file generation."""
        service = scheduler._generate_service_file(
            cli_path="/usr/bin/clamui-scheduled-scan",
            targets=["/home/user/Documents"],
            skip_on_battery=True,
            auto_quarantine=False
        )

        assert "[Unit]" in service
        assert "[Service]" in service
        assert "[Install]" in service
        assert "Type=oneshot" in service
        assert "ExecStart=/usr/bin/clamui-scheduled-scan" in service
        assert "--skip-on-battery" in service
        assert "--target \"/home/user/Documents\"" in service
        assert "--auto-quarantine" not in service

    def test_generate_service_file_with_quarantine(self, scheduler):
        """Test service file generation with quarantine enabled."""
        service = scheduler._generate_service_file(
            cli_path="/usr/bin/clamui-scheduled-scan",
            targets=["/home/user/Downloads"],
            skip_on_battery=False,
            auto_quarantine=True
        )

        assert "--auto-quarantine" in service
        assert "--skip-on-battery" not in service

    def test_generate_service_file_multiple_targets(self, scheduler):
        """Test service file generation with multiple targets."""
        service = scheduler._generate_service_file(
            cli_path="/usr/bin/clamui-scheduled-scan",
            targets=["/home/user/Documents", "/home/user/Downloads"],
            skip_on_battery=True,
            auto_quarantine=True
        )

        assert "--target \"/home/user/Documents\"" in service
        assert "--target \"/home/user/Downloads\"" in service

    def test_generate_timer_file(self, scheduler):
        """Test timer file generation."""
        timer = scheduler._generate_timer_file("*-*-* 02:00:00")

        assert "[Unit]" in timer
        assert "[Timer]" in timer
        assert "[Install]" in timer
        assert "OnCalendar=*-*-* 02:00:00" in timer
        assert "Persistent=true" in timer
        assert "WantedBy=timers.target" in timer


class TestSchedulerEnableDisable:
    """Tests for Scheduler enable/disable functionality."""

    @pytest.fixture
    def scheduler(self):
        """Create a Scheduler instance with temp config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Scheduler(config_dir=Path(tmpdir))

    def test_enable_schedule_no_backend(self):
        """Test enable_schedule fails when no backend available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(config_dir=Path(tmpdir))
            scheduler._backend = SchedulerBackend.NONE

            success, error = scheduler.enable_schedule(
                frequency="daily",
                time="02:00",
                targets=["/home/user"]
            )

            assert success is False
            assert "No scheduler backend available" in error

    def test_enable_schedule_invalid_frequency(self, scheduler):
        """Test enable_schedule fails with invalid frequency."""
        success, error = scheduler.enable_schedule(
            frequency="biweekly",  # Invalid - not a valid frequency option
            time="02:00",
            targets=["/home/user"]
        )

        if scheduler.is_available:
            assert success is False
            assert "Invalid frequency" in error

    def test_disable_schedule_no_backend(self):
        """Test disable_schedule succeeds when no backend available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(config_dir=Path(tmpdir))
            scheduler._backend = SchedulerBackend.NONE

            success, error = scheduler.disable_schedule()

            # Should succeed (nothing to disable)
            assert success is True


class TestSchedulerStatus:
    """Tests for Scheduler status checking."""

    def test_get_status_no_backend(self):
        """Test get_status when no backend available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(config_dir=Path(tmpdir))
            scheduler._backend = SchedulerBackend.NONE

            is_active, message = scheduler.get_status()

            assert is_active is False
            assert "No scheduler backend available" in message

    def test_is_schedule_active_returns_bool(self):
        """Test is_schedule_active returns boolean."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(config_dir=Path(tmpdir))

            result = scheduler.is_schedule_active()

            assert isinstance(result, bool)


class TestSchedulerSystemdIntegration:
    """Tests for systemd-specific functionality (requires systemd)."""

    @pytest.fixture
    def scheduler_with_systemd(self):
        """Create a Scheduler that forces systemd backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(config_dir=Path(tmpdir))
            if scheduler.systemd_available:
                yield scheduler
            else:
                pytest.skip("systemd not available")

    def test_systemd_files_created(self, scheduler_with_systemd):
        """Test that systemd files are created on enable."""
        scheduler = scheduler_with_systemd

        # Mock the CLI path and systemctl commands
        with mock.patch.object(scheduler, "_get_cli_command_path", return_value="/usr/bin/clamui-scheduled-scan"):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.MagicMock(returncode=0, stdout="", stderr="")

                success, error = scheduler.enable_schedule(
                    frequency="daily",
                    time="02:00",
                    targets=["/tmp/test"]
                )

                if success:
                    # Check that service file was created
                    service_path = scheduler._systemd_dir / f"{scheduler.SERVICE_NAME}.service"
                    assert service_path.exists()

                    # Check that timer file was created
                    timer_path = scheduler._systemd_dir / f"{scheduler.TIMER_NAME}.timer"
                    assert timer_path.exists()


class TestSchedulerCronIntegration:
    """Tests for cron-specific functionality."""

    @pytest.fixture
    def scheduler_with_cron(self):
        """Create a Scheduler that forces cron backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(config_dir=Path(tmpdir))
            if scheduler.cron_available:
                # Force cron backend even if systemd available
                scheduler._backend = SchedulerBackend.CRON
                yield scheduler
            else:
                pytest.skip("cron not available")

    def test_cron_entry_format(self, scheduler_with_cron):
        """Test cron entry is formatted correctly."""
        scheduler = scheduler_with_cron

        # Test entry generation
        entry = scheduler._generate_crontab_entry(ScheduleFrequency.DAILY, "02:00")
        assert entry == "0 2 * * *"

        entry = scheduler._generate_crontab_entry(ScheduleFrequency.WEEKLY, "14:30", day_of_week=2)
        # Wednesday is 2 in our format, 3 in cron format
        assert entry == "30 14 * * 3"
