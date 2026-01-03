# ClamUI NotificationManager Tests
"""Unit tests for the NotificationManager class."""

import tempfile
from unittest import mock

import pytest

from src.core.notification_manager import NotificationManager
from src.core.settings_manager import SettingsManager


class TestNotificationManagerInit:
    """Tests for NotificationManager initialization."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_init_without_settings_manager(self):
        """Test NotificationManager initializes with default SettingsManager."""
        manager = NotificationManager()
        assert manager._settings is not None
        assert isinstance(manager._settings, SettingsManager)

    def test_init_with_custom_settings_manager(self, temp_config_dir):
        """Test NotificationManager uses provided SettingsManager."""
        settings = SettingsManager(config_dir=temp_config_dir)
        manager = NotificationManager(settings_manager=settings)
        assert manager._settings is settings

    def test_init_sets_app_to_none(self):
        """Test NotificationManager initializes with no application reference."""
        manager = NotificationManager()
        assert manager._app is None
        assert manager.has_application is False

    def test_notification_ids_are_defined(self):
        """Test that notification ID constants are defined."""
        assert NotificationManager.NOTIFICATION_ID_SCAN == "scan-complete"
        assert NotificationManager.NOTIFICATION_ID_UPDATE == "update-complete"


class TestNotificationManagerSetApplication:
    """Tests for NotificationManager.set_application method."""

    def test_set_application_stores_reference(self):
        """Test that set_application stores the app reference."""
        manager = NotificationManager()
        mock_app = mock.Mock()

        manager.set_application(mock_app)

        assert manager._app is mock_app
        assert manager.has_application is True

    def test_set_application_can_be_updated(self):
        """Test that application reference can be updated."""
        manager = NotificationManager()
        mock_app1 = mock.Mock()
        mock_app2 = mock.Mock()

        manager.set_application(mock_app1)
        assert manager._app is mock_app1

        manager.set_application(mock_app2)
        assert manager._app is mock_app2


class TestNotificationManagerCanNotify:
    """Tests for NotificationManager._can_notify logic."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_can_notify_returns_false_without_app(self, temp_config_dir):
        """Test that notifications are blocked without app reference."""
        settings = SettingsManager(config_dir=temp_config_dir)
        manager = NotificationManager(settings_manager=settings)
        # No app set
        assert manager._can_notify() is False

    def test_can_notify_returns_false_when_disabled(self, temp_config_dir):
        """Test that notifications are blocked when disabled in settings."""
        settings = SettingsManager(config_dir=temp_config_dir)
        settings.set("notifications_enabled", False)

        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        manager.set_application(mock_app)

        assert manager._can_notify() is False

    def test_can_notify_returns_true_when_enabled(self, temp_config_dir):
        """Test that notifications are allowed when enabled and app set."""
        settings = SettingsManager(config_dir=temp_config_dir)
        settings.set("notifications_enabled", True)

        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        manager.set_application(mock_app)

        assert manager._can_notify() is True

    def test_can_notify_uses_default_enabled(self, temp_config_dir):
        """Test that notifications default to enabled."""
        settings = SettingsManager(config_dir=temp_config_dir)
        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        manager.set_application(mock_app)

        # Default should be True
        assert manager._can_notify() is True


class TestNotificationManagerNotifyScanComplete:
    """Tests for NotificationManager.notify_scan_complete method."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def notification_manager(self, temp_config_dir):
        """Create a NotificationManager with mock app and enabled notifications."""
        settings = SettingsManager(config_dir=temp_config_dir)
        settings.set("notifications_enabled", True)
        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        manager.set_application(mock_app)
        return manager

    def test_notify_scan_complete_clean_returns_true(self, notification_manager):
        """Test notify_scan_complete returns True when notification sent."""
        with mock.patch("src.core.notification_manager.Gio"):
            result = notification_manager.notify_scan_complete(is_clean=True, scanned_count=100)
            assert result is True

    def test_notify_scan_complete_clean_creates_notification(self, notification_manager):
        """Test notify_scan_complete creates notification for clean scan."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_scan_complete(is_clean=True, scanned_count=100)

            mock_gio.Notification.new.assert_called_once_with("Scan Complete")
            mock_notification.set_body.assert_called_once()
            body_arg = mock_notification.set_body.call_args[0][0]
            assert "No threats found" in body_arg
            assert "100" in body_arg

    def test_notify_scan_complete_clean_without_count(self, notification_manager):
        """Test notify_scan_complete with clean scan and no file count."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_scan_complete(is_clean=True)

            mock_notification.set_body.assert_called_once_with("No threats found")

    def test_notify_scan_complete_infected_creates_urgent_notification(self, notification_manager):
        """Test notify_scan_complete creates urgent notification for threats."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_scan_complete(is_clean=False, infected_count=3)

            mock_gio.Notification.new.assert_called_once_with("Threats Detected!")
            mock_notification.set_body.assert_called_once()
            body_arg = mock_notification.set_body.call_args[0][0]
            assert "3" in body_arg
            assert "infected" in body_arg

            # Verify URGENT priority
            mock_notification.set_priority.assert_called_once()
            priority_arg = mock_notification.set_priority.call_args[0][0]
            assert priority_arg == mock_gio.NotificationPriority.URGENT

    def test_notify_scan_complete_clean_uses_normal_priority(self, notification_manager):
        """Test clean scan notification uses NORMAL priority."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_scan_complete(is_clean=True)

            mock_notification.set_priority.assert_called_once()
            priority_arg = mock_notification.set_priority.call_args[0][0]
            assert priority_arg == mock_gio.NotificationPriority.NORMAL

    def test_notify_scan_complete_sets_default_action(self, notification_manager):
        """Test scan notification sets click action to show scan view."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_scan_complete(is_clean=True)

            mock_notification.set_default_action.assert_called_once_with("app.show-scan")

    def test_notify_scan_complete_sends_via_app(self, notification_manager):
        """Test scan notification is sent via the application."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_scan_complete(is_clean=True)

            notification_manager._app.send_notification.assert_called_once_with(
                "scan-complete", mock_notification
            )

    def test_notify_scan_complete_returns_false_when_disabled(self, temp_config_dir):
        """Test notify_scan_complete returns False when notifications disabled."""
        settings = SettingsManager(config_dir=temp_config_dir)
        settings.set("notifications_enabled", False)
        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        manager.set_application(mock_app)

        result = manager.notify_scan_complete(is_clean=True)
        assert result is False
        mock_app.send_notification.assert_not_called()

    def test_notify_scan_complete_returns_false_without_app(self, temp_config_dir):
        """Test notify_scan_complete returns False without app reference."""
        settings = SettingsManager(config_dir=temp_config_dir)
        manager = NotificationManager(settings_manager=settings)

        result = manager.notify_scan_complete(is_clean=True)
        assert result is False


class TestNotificationManagerNotifyUpdateComplete:
    """Tests for NotificationManager.notify_update_complete method."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def notification_manager(self, temp_config_dir):
        """Create a NotificationManager with mock app and enabled notifications."""
        settings = SettingsManager(config_dir=temp_config_dir)
        settings.set("notifications_enabled", True)
        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        manager.set_application(mock_app)
        return manager

    def test_notify_update_complete_success_returns_true(self, notification_manager):
        """Test notify_update_complete returns True when notification sent."""
        with mock.patch("src.core.notification_manager.Gio"):
            result = notification_manager.notify_update_complete(success=True, databases_updated=3)
            assert result is True

    def test_notify_update_complete_success_creates_notification(self, notification_manager):
        """Test notify_update_complete creates notification for successful update."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_update_complete(success=True, databases_updated=3)

            mock_gio.Notification.new.assert_called_once_with("Database Updated")
            mock_notification.set_body.assert_called_once()
            body_arg = mock_notification.set_body.call_args[0][0]
            assert "3" in body_arg
            assert "updated successfully" in body_arg

    def test_notify_update_complete_success_no_count(self, notification_manager):
        """Test notify_update_complete with success but no database count."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_update_complete(success=True)

            mock_notification.set_body.assert_called_once_with("Virus definitions are up to date")

    def test_notify_update_complete_failure_creates_notification(self, notification_manager):
        """Test notify_update_complete creates notification for failed update."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_update_complete(success=False)

            mock_gio.Notification.new.assert_called_once_with("Database Update Failed")
            mock_notification.set_body.assert_called_once()
            body_arg = mock_notification.set_body.call_args[0][0]
            assert "Check the update view" in body_arg

    def test_notify_update_complete_uses_normal_priority(self, notification_manager):
        """Test update notification uses NORMAL priority."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_update_complete(success=True)

            mock_notification.set_priority.assert_called_once()
            priority_arg = mock_notification.set_priority.call_args[0][0]
            assert priority_arg == mock_gio.NotificationPriority.NORMAL

    def test_notify_update_complete_sets_default_action(self, notification_manager):
        """Test update notification sets click action to show update view."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_update_complete(success=True)

            mock_notification.set_default_action.assert_called_once_with("app.show-update")

    def test_notify_update_complete_sends_via_app(self, notification_manager):
        """Test update notification is sent via the application."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_update_complete(success=True)

            notification_manager._app.send_notification.assert_called_once_with(
                "update-complete", mock_notification
            )

    def test_notify_update_complete_returns_false_when_disabled(self, temp_config_dir):
        """Test notify_update_complete returns False when notifications disabled."""
        settings = SettingsManager(config_dir=temp_config_dir)
        settings.set("notifications_enabled", False)
        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        manager.set_application(mock_app)

        result = manager.notify_update_complete(success=True)
        assert result is False
        mock_app.send_notification.assert_not_called()


class TestNotificationManagerWithdrawNotification:
    """Tests for NotificationManager.withdraw_notification method."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_withdraw_notification_returns_false_without_app(self, temp_config_dir):
        """Test withdraw_notification returns False without app reference."""
        settings = SettingsManager(config_dir=temp_config_dir)
        manager = NotificationManager(settings_manager=settings)

        result = manager.withdraw_notification("scan-complete")
        assert result is False

    def test_withdraw_notification_calls_app_method(self, temp_config_dir):
        """Test withdraw_notification calls app.withdraw_notification."""
        settings = SettingsManager(config_dir=temp_config_dir)
        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        manager.set_application(mock_app)

        result = manager.withdraw_notification("scan-complete")

        assert result is True
        mock_app.withdraw_notification.assert_called_once_with("scan-complete")

    def test_withdraw_notification_handles_exception(self, temp_config_dir):
        """Test withdraw_notification returns False on exception."""
        settings = SettingsManager(config_dir=temp_config_dir)
        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        mock_app.withdraw_notification.side_effect = Exception("Test error")
        manager.set_application(mock_app)

        result = manager.withdraw_notification("scan-complete")
        assert result is False


class TestNotificationManagerProperties:
    """Tests for NotificationManager properties."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_has_application_false_initially(self):
        """Test has_application returns False when no app is set."""
        manager = NotificationManager()
        assert manager.has_application is False

    def test_has_application_true_after_set(self):
        """Test has_application returns True after app is set."""
        manager = NotificationManager()
        mock_app = mock.Mock()
        manager.set_application(mock_app)
        assert manager.has_application is True

    def test_notifications_enabled_default(self, temp_config_dir):
        """Test notifications_enabled returns True by default."""
        settings = SettingsManager(config_dir=temp_config_dir)
        manager = NotificationManager(settings_manager=settings)
        assert manager.notifications_enabled is True

    def test_notifications_enabled_reflects_settings(self, temp_config_dir):
        """Test notifications_enabled reflects settings value."""
        settings = SettingsManager(config_dir=temp_config_dir)
        settings.set("notifications_enabled", False)
        manager = NotificationManager(settings_manager=settings)
        assert manager.notifications_enabled is False


class TestNotificationManagerErrorHandling:
    """Tests for NotificationManager error handling."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def notification_manager(self, temp_config_dir):
        """Create a NotificationManager with mock app and enabled notifications."""
        settings = SettingsManager(config_dir=temp_config_dir)
        settings.set("notifications_enabled", True)
        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        manager.set_application(mock_app)
        return manager

    def test_send_notification_handles_gio_exception(self, notification_manager):
        """Test that _send handles Gio.Notification exceptions gracefully."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_gio.Notification.new.side_effect = Exception("D-Bus unavailable")

            result = notification_manager.notify_scan_complete(is_clean=True)

            # Should return False but not crash
            assert result is False

    def test_send_notification_handles_app_send_exception(self, notification_manager):
        """Test that _send handles app.send_notification exceptions gracefully."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification
            notification_manager._app.send_notification.side_effect = Exception("Send failed")

            result = notification_manager.notify_scan_complete(is_clean=True)

            # Should return False but not crash
            assert result is False


class TestNotificationManagerNotificationIds:
    """Tests for notification ID usage and deduplication."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for settings storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def notification_manager(self, temp_config_dir):
        """Create a NotificationManager with mock app and enabled notifications."""
        settings = SettingsManager(config_dir=temp_config_dir)
        settings.set("notifications_enabled", True)
        manager = NotificationManager(settings_manager=settings)
        mock_app = mock.Mock()
        manager.set_application(mock_app)
        return manager

    def test_scan_notifications_use_consistent_id(self, notification_manager):
        """Test that scan notifications use the same ID for deduplication."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            # Send multiple scan notifications
            notification_manager.notify_scan_complete(is_clean=True)
            notification_manager.notify_scan_complete(is_clean=False, infected_count=1)

            # Both should use the same notification ID
            calls = notification_manager._app.send_notification.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == "scan-complete"
            assert calls[1][0][0] == "scan-complete"

    def test_update_notifications_use_consistent_id(self, notification_manager):
        """Test that update notifications use the same ID for deduplication."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            # Send multiple update notifications
            notification_manager.notify_update_complete(success=True)
            notification_manager.notify_update_complete(success=False)

            # Both should use the same notification ID
            calls = notification_manager._app.send_notification.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == "update-complete"
            assert calls[1][0][0] == "update-complete"

    def test_scan_and_update_use_different_ids(self, notification_manager):
        """Test that scan and update notifications use different IDs."""
        with mock.patch("src.core.notification_manager.Gio") as mock_gio:
            mock_notification = mock.Mock()
            mock_gio.Notification.new.return_value = mock_notification

            notification_manager.notify_scan_complete(is_clean=True)
            notification_manager.notify_update_complete(success=True)

            calls = notification_manager._app.send_notification.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] != calls[1][0][0]
