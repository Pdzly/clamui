# ClamUI Notification Manager Module
"""
Notification manager module for ClamUI providing GNOME desktop notifications.
Uses Gio.Notification API for native GNOME integration.
"""

from gi.repository import Gio

from .settings_manager import SettingsManager


class NotificationManager:
    """
    Manager for GNOME desktop notifications.

    Provides methods for sending notifications when scans complete,
    threats are detected, or virus definitions are updated.
    Notifications can be disabled via user settings.
    """

    # Notification IDs for deduplication
    NOTIFICATION_ID_SCAN = "scan-complete"
    NOTIFICATION_ID_UPDATE = "update-complete"
    NOTIFICATION_ID_SCHEDULED_SCAN = "scheduled-scan-complete"
    NOTIFICATION_ID_VT_SCAN = "virustotal-scan-complete"
    NOTIFICATION_ID_VT_RATE_LIMIT = "virustotal-rate-limit"
    NOTIFICATION_ID_VT_NO_KEY = "virustotal-no-key"

    def __init__(self, settings_manager: SettingsManager | None = None):
        """
        Initialize the NotificationManager.

        Args:
            settings_manager: Optional SettingsManager instance for checking
                              notification preferences. If not provided, a
                              default instance is created.
        """
        self._app: Gio.Application | None = None
        self._settings = settings_manager if settings_manager else SettingsManager()

    def set_application(self, app: Gio.Application) -> None:
        """
        Set the application reference for sending notifications.

        This must be called after the application is initialized,
        typically in do_startup().

        Args:
            app: The Gio.Application instance
        """
        self._app = app

    def notify_scan_complete(
        self, is_clean: bool, infected_count: int = 0, scanned_count: int = 0
    ) -> bool:
        """
        Send notification for scan completion.

        Args:
            is_clean: True if no threats were found
            infected_count: Number of infected files found
            scanned_count: Number of files scanned

        Returns:
            True if notification was sent, False otherwise
        """
        if not self._can_notify():
            return False

        if is_clean:
            title = "Scan Complete"
            if scanned_count > 0:
                body = f"No threats found ({scanned_count} files scanned)"
            else:
                body = "No threats found"
            priority = Gio.NotificationPriority.NORMAL
        else:
            title = "Threats Detected!"
            body = f"{infected_count} infected file(s) found"
            priority = Gio.NotificationPriority.URGENT

        return self._send(
            notification_id=self.NOTIFICATION_ID_SCAN,
            title=title,
            body=body,
            priority=priority,
            default_action="app.show-scan",
        )

    def notify_update_complete(self, success: bool, databases_updated: int = 0) -> bool:
        """
        Send notification for database update completion.

        Args:
            success: True if update completed successfully
            databases_updated: Number of databases updated

        Returns:
            True if notification was sent, False otherwise
        """
        if not self._can_notify():
            return False

        if success:
            title = "Database Updated"
            if databases_updated > 0:
                body = f"{databases_updated} database(s) updated successfully"
            else:
                body = "Virus definitions are up to date"
        else:
            title = "Database Update Failed"
            body = "Check the update view for details"

        return self._send(
            notification_id=self.NOTIFICATION_ID_UPDATE,
            title=title,
            body=body,
            priority=Gio.NotificationPriority.NORMAL,
            default_action="app.show-update",
        )

    def notify_scheduled_scan_complete(
        self,
        is_clean: bool,
        infected_count: int = 0,
        scanned_count: int = 0,
        quarantined_count: int = 0,
        target_path: str | None = None,
    ) -> bool:
        """
        Send notification for scheduled scan completion.

        Args:
            is_clean: True if no threats were found
            infected_count: Number of infected files found
            scanned_count: Number of files scanned
            quarantined_count: Number of files quarantined
            target_path: Optional path that was scanned

        Returns:
            True if notification was sent, False otherwise
        """
        if not self._can_notify():
            return False

        if is_clean:
            title = "Scheduled Scan Complete"
            if scanned_count > 0:
                body = f"No threats found ({scanned_count} files scanned)"
            else:
                body = "No threats found"
            priority = Gio.NotificationPriority.NORMAL
        else:
            title = "Scheduled Scan: Threats Detected!"
            if quarantined_count > 0:
                body = f"{infected_count} infected file(s) found, {quarantined_count} quarantined"
            else:
                body = f"{infected_count} infected file(s) found"
            priority = Gio.NotificationPriority.URGENT

        return self._send(
            notification_id=self.NOTIFICATION_ID_SCHEDULED_SCAN,
            title=title,
            body=body,
            priority=priority,
            default_action="app.show-scan",
        )

    def notify_virustotal_scan_complete(
        self,
        is_clean: bool,
        detections: int = 0,
        total_engines: int = 0,
        file_name: str | None = None,
        permalink: str | None = None,
    ) -> bool:
        """
        Send notification for VirusTotal scan completion.

        Args:
            is_clean: True if no threats were detected
            detections: Number of engines that detected threats
            total_engines: Total number of engines that scanned the file
            file_name: Optional name of the scanned file
            permalink: Optional VirusTotal permalink

        Returns:
            True if notification was sent, False otherwise
        """
        if not self._can_notify():
            return False

        if is_clean:
            title = "VirusTotal: No Threats"
            if file_name:
                body = f"'{file_name}' appears safe (0/{total_engines} detections)"
            else:
                body = f"File appears safe (0/{total_engines} detections)"
            priority = Gio.NotificationPriority.NORMAL
        else:
            title = "VirusTotal: Threats Detected!"
            if file_name:
                body = f"'{file_name}' flagged by {detections}/{total_engines} engines"
            else:
                body = f"File flagged by {detections}/{total_engines} engines"
            priority = Gio.NotificationPriority.URGENT

        return self._send(
            notification_id=self.NOTIFICATION_ID_VT_SCAN,
            title=title,
            body=body,
            priority=priority,
            default_action="app.show-logs",
        )

    def notify_virustotal_rate_limit(self) -> bool:
        """
        Send notification when VirusTotal rate limit is exceeded.

        Returns:
            True if notification was sent, False otherwise
        """
        if not self._can_notify():
            return False

        return self._send(
            notification_id=self.NOTIFICATION_ID_VT_RATE_LIMIT,
            title="VirusTotal Rate Limit",
            body="Too many requests. Try again in a minute or use the website.",
            priority=Gio.NotificationPriority.NORMAL,
            default_action="app.show-preferences",
        )

    def notify_virustotal_no_key(self) -> bool:
        """
        Send notification when VirusTotal API key is not configured.

        Returns:
            True if notification was sent, False otherwise
        """
        if not self._can_notify():
            return False

        return self._send(
            notification_id=self.NOTIFICATION_ID_VT_NO_KEY,
            title="VirusTotal Not Configured",
            body="Add your API key in Preferences to scan with VirusTotal.",
            priority=Gio.NotificationPriority.NORMAL,
            default_action="app.show-preferences",
        )

    def _can_notify(self) -> bool:
        """
        Check if notifications are enabled and possible.

        Returns:
            True if notifications can be sent, False otherwise
        """
        if self._app is None:
            return False

        return self._settings.get("notifications_enabled", True)

    def _send(
        self,
        notification_id: str,
        title: str,
        body: str,
        priority: Gio.NotificationPriority,
        default_action: str,
    ) -> bool:
        """
        Send a notification.

        Args:
            notification_id: Unique ID for this notification (for deduplication)
            title: Notification title
            body: Notification body text
            priority: Notification priority (NORMAL or URGENT)
            default_action: Action to trigger when notification is clicked

        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            notification = Gio.Notification.new(title)
            notification.set_body(body)
            notification.set_priority(priority)
            notification.set_default_action(default_action)

            # Send the notification
            self._app.send_notification(notification_id, notification)
            return True
        except Exception:
            # Silent failure if notifications unavailable
            # This handles cases where D-Bus notification service isn't running
            return False

    def withdraw_notification(self, notification_id: str) -> bool:
        """
        Withdraw a previously sent notification.

        Args:
            notification_id: The ID of the notification to withdraw

        Returns:
            True if withdrawal was attempted, False if no app reference
        """
        if self._app is None:
            return False

        try:
            self._app.withdraw_notification(notification_id)
            return True
        except Exception:
            return False

    @property
    def notifications_enabled(self) -> bool:
        """
        Check if notifications are enabled in settings.

        Returns:
            True if notifications are enabled, False otherwise
        """
        return self._settings.get("notifications_enabled", True)

    @property
    def has_application(self) -> bool:
        """
        Check if application reference has been set.

        Returns:
            True if application is set, False otherwise
        """
        return self._app is not None
