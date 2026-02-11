# ClamUI Updater Module
"""
Updater module for ClamUI providing freshclam subprocess execution and async database updates.
"""

import logging
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from gi.repository import GLib

from .flatpak import (
    ensure_clamav_database_dir,
    ensure_freshclam_config,
    get_clamav_database_dir,
    is_flatpak,
)
from .i18n import _
from .log_manager import LogEntry, LogManager
from .utils import (
    check_freshclam_installed,
    get_clean_env,
    get_freshclam_path,
    wrap_host_command,
)

logger = logging.getLogger(__name__)

# Timeout constants (seconds)
_TERMINATE_GRACE_TIMEOUT = 5  # Time to wait after SIGTERM before SIGKILL
_KILL_WAIT_TIMEOUT = 2  # Time to wait after SIGKILL
_UPDATE_COMMUNICATE_TIMEOUT = 600  # 10 minutes for freshclam (network operations)


def get_pkexec_path() -> str | None:
    """
    Get the full path to the pkexec executable for privilege elevation.

    Returns:
        The full path to pkexec if found, None otherwise
    """

    return shutil.which("pkexec")


class UpdateStatus(Enum):
    """Status of a database update operation."""

    SUCCESS = "success"  # Database updated successfully (exit code 0)
    UP_TO_DATE = "up_to_date"  # Database already current (exit code 0, no updates)
    ERROR = "error"  # Error occurred (exit code 1 or exception)
    CANCELLED = "cancelled"  # Update was cancelled


class UpdateMethod(Enum):
    """How the update was triggered."""

    SERVICE_SIGNAL = "service_signal"  # Via SIGUSR1 to freshclam service
    MANUAL = "manual"  # Via pkexec freshclam subprocess


class FreshclamServiceStatus(Enum):
    """Status of the freshclam systemd service."""

    RUNNING = "running"  # Service active, can trigger via signal
    STOPPED = "stopped"  # Service exists but not running
    NOT_FOUND = "not_found"  # No systemd service detected
    UNKNOWN = "unknown"  # Error checking status


@dataclass
class UpdateResult:
    """Result of a database update operation."""

    status: UpdateStatus
    stdout: str
    stderr: str
    exit_code: int
    databases_updated: int
    error_message: str | None
    update_method: UpdateMethod = UpdateMethod.MANUAL

    @property
    def is_success(self) -> bool:
        """Check if update completed successfully."""
        return self.status in (UpdateStatus.SUCCESS, UpdateStatus.UP_TO_DATE)

    @property
    def has_error(self) -> bool:
        """Check if update encountered an error."""
        return self.status == UpdateStatus.ERROR


class FreshclamUpdater:
    """
    ClamAV database updater with async execution support.

    Provides methods for running freshclam in a background thread
    while safely updating the UI via GLib.idle_add.
    """

    def __init__(self, log_manager: LogManager | None = None):
        """
        Initialize the updater.

        Args:
            log_manager: Optional LogManager instance for saving update logs.
                         If not provided, a default instance is created.
        """
        self._current_process: subprocess.Popen | None = None
        self._update_cancelled = False
        self._log_manager = log_manager if log_manager else LogManager()

    def check_available(self) -> tuple[bool, str | None]:
        """
        Check if freshclam is available for database updates.

        Returns:
            Tuple of (is_available, version_or_error)
        """
        return check_freshclam_installed()

    def check_freshclam_service(self) -> tuple[FreshclamServiceStatus, str | None]:
        """
        Check if freshclam is running as a systemd service.

        Checks for both 'clamav-freshclam.service' (Debian/Ubuntu/Fedora/Arch)
        and 'freshclam.service' (openSUSE).

        Returns:
            Tuple of (status, pid_or_error_message)
            - RUNNING: (RUNNING, pid_string)
            - STOPPED: (STOPPED, None)
            - NOT_FOUND: (NOT_FOUND, None)
            - UNKNOWN: (UNKNOWN, error_message)
        """
        # Flatpak cannot reliably detect host systemd services
        if is_flatpak():
            return FreshclamServiceStatus.NOT_FOUND, None

        # Service names to check (in order of preference)
        service_names = ["clamav-freshclam.service", "freshclam.service"]

        for service_name in service_names:
            try:
                # Check if service is active
                result = subprocess.run(
                    wrap_host_command(["systemctl", "is-active", service_name]),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0 and result.stdout.strip() == "active":
                    # Service is active, get the PID
                    try:
                        pid_result = subprocess.run(
                            wrap_host_command(["pidof", "freshclam"]),
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if pid_result.returncode == 0:
                            pid = pid_result.stdout.strip().split()[0]  # Take first PID
                            logger.debug(
                                "Found running freshclam service: %s (PID %s)",
                                service_name,
                                pid,
                            )
                            return FreshclamServiceStatus.RUNNING, pid
                    except (subprocess.TimeoutExpired, OSError) as e:
                        logger.warning("Failed to get freshclam PID: %s", e)
                        # Service is active but couldn't get PID
                        return FreshclamServiceStatus.RUNNING, None

                elif result.returncode == 0 or "inactive" in result.stdout.strip().lower():
                    # Service exists but is stopped
                    logger.debug("Service %s exists but is not running", service_name)
                    return FreshclamServiceStatus.STOPPED, None

            except subprocess.TimeoutExpired:
                logger.warning("Timeout checking service %s", service_name)
                continue
            except OSError as e:
                logger.warning("Error checking service %s: %s", service_name, e)
                continue

        # No service found
        return FreshclamServiceStatus.NOT_FOUND, None

    def trigger_service_update(self) -> tuple[bool, str]:
        """
        Trigger a database update via the freshclam service using SIGUSR1.

        This is a non-blocking operation - the service handles the update
        in the background. Check service logs (journalctl -u clamav-freshclam)
        for results.

        Returns:
            Tuple of (success, message)
        """
        # Check service status first
        status, pid = self.check_freshclam_service()

        if status != FreshclamServiceStatus.RUNNING:
            return False, _("Freshclam service not running (status: {status})").format(
                status=status.value
            )

        if not pid:
            # Try to get PID again
            try:
                pid_result = subprocess.run(
                    wrap_host_command(["pidof", "freshclam"]),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if pid_result.returncode == 0:
                    pid = pid_result.stdout.strip().split()[0]
                else:
                    return False, _("Could not determine freshclam PID")
            except (subprocess.TimeoutExpired, OSError) as e:
                return False, _("Failed to get freshclam PID: {error}").format(error=e)

        # Send SIGUSR1 to trigger update
        try:
            # Use kill command to send signal (works without root for processes owned by same user)
            result = subprocess.run(
                wrap_host_command(["kill", "-s", "SIGUSR1", pid]),
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                logger.info("Sent SIGUSR1 to freshclam service (PID %s)", pid)
                return True, _("Update signal sent to freshclam service (PID {pid})").format(
                    pid=pid
                )

            # Regular signal failed (likely permission denied for clamav-owned process)
            # Try with pkexec elevation
            error = result.stderr.strip() or "Unknown error"
            logger.info("Regular kill failed (%s), trying elevated signal via pkexec", error)
            pkexec = get_pkexec_path()
            if pkexec:
                try:
                    elevated_result = subprocess.run(
                        wrap_host_command([pkexec, "kill", "-s", "SIGUSR1", pid]),
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if elevated_result.returncode == 0:
                        logger.info("Sent SIGUSR1 to freshclam via pkexec (PID %s)", pid)
                        return True, _(
                            "Update signal sent to freshclam service (PID {pid})"
                        ).format(pid=pid)
                    else:
                        elevated_error = elevated_result.stderr.strip() or error
                        logger.warning("Elevated signal also failed: %s", elevated_error)
                        return False, _("Failed to send signal: {error}").format(
                            error=elevated_error
                        )
                except subprocess.TimeoutExpired:
                    return False, _("Timeout sending elevated signal to freshclam")
                except OSError as e:
                    logger.warning("pkexec signal failed: %s", e)

            # Both attempts failed (or pkexec not available)
            logger.warning("Failed to send signal to freshclam: %s", error)
            return False, _("Failed to send signal: {error}").format(error=error)

        except subprocess.TimeoutExpired:
            return False, _("Timeout sending signal to freshclam")
        except OSError as e:
            return False, _("Error sending signal: {error}").format(error=e)

    def _check_freshclam_running(self) -> tuple[bool, str | None]:
        """
        Check if a freshclam process is currently running.

        Uses pidof to detect running freshclam instances. Skipped in Flatpak
        (where freshclam runs on the host and pidof may not work).

        Returns:
            Tuple of (is_running, pid_string_or_none)
        """
        if is_flatpak():
            return False, None
        try:
            pid_result = subprocess.run(
                wrap_host_command(["pidof", "freshclam"]),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if pid_result.returncode == 0 and pid_result.stdout.strip():
                pid = pid_result.stdout.strip().split()[0]
                return True, pid
        except Exception:
            pass  # Best-effort check; proceed with update if anything goes wrong
        return False, None

    def update_sync(self, force: bool = False, prefer_service: bool = True) -> UpdateResult:
        """
        Execute a synchronous database update.

        WARNING: This will block the calling thread. For UI applications,
        use update_async() instead.

        Args:
            force: If True, backup existing databases, delete them, then download
                   fresh copies from mirrors. Previous databases are restored if
                   the update fails.
            prefer_service: If True (default), attempt to trigger update via
                           freshclam systemd service using SIGUSR1 when available.
                           Falls back to manual method if service not running.
                           Force updates always use manual method.

        Returns:
            UpdateResult with update details
        """
        start_time = time.monotonic()

        # Check freshclam is available first (needed for both service and manual methods)
        is_installed, version_or_error = check_freshclam_installed()
        if not is_installed:
            result = UpdateResult(
                status=UpdateStatus.ERROR,
                stdout="",
                stderr=version_or_error or "freshclam not installed",
                exit_code=-1,
                databases_updated=0,
                error_message=version_or_error,
            )
            duration = time.monotonic() - start_time
            self._save_update_log(result, duration)
            return result

        # Try service-based update if preferred and not force mode
        # Force mode requires deleting databases which needs root privileges
        if prefer_service and not force:
            service_status, pid = self.check_freshclam_service()
            if service_status == FreshclamServiceStatus.RUNNING:
                success, message = self.trigger_service_update()
                if success:
                    # Service update triggered successfully
                    # Note: The actual update happens in the background
                    result = UpdateResult(
                        status=UpdateStatus.SUCCESS,
                        stdout=message,
                        stderr="",
                        exit_code=0,
                        databases_updated=0,  # Unknown - happens in background
                        error_message=None,
                        update_method=UpdateMethod.SERVICE_SIGNAL,
                    )
                    duration = time.monotonic() - start_time
                    self._save_update_log(result, duration)
                    return result
                else:
                    # Service is running but signal failed - do NOT fall back to manual.
                    # Manual freshclam will fail because the service holds all locks.
                    logger.warning(
                        "Service update trigger failed (%s), "
                        "not falling back to manual method (service holds locks)",
                        message,
                    )
                    result = UpdateResult(
                        status=UpdateStatus.ERROR,
                        stdout="",
                        stderr=message,
                        exit_code=-1,
                        databases_updated=0,
                        error_message=_(
                            "Could not trigger freshclam service update. "
                            "Try restarting the service: "
                            "sudo systemctl restart clamav-freshclam"
                        ),
                    )
                    duration = time.monotonic() - start_time
                    self._save_update_log(result, duration)
                    return result
        # Continue with manual update method

        # If force update, backup existing databases (for potential restore)
        # Note: In native mode, deletion happens via pkexec in _build_command
        # In Flatpak mode, deletion happens here with user permissions
        if force:
            if not is_flatpak():
                # Native: best-effort backup (may fail due to root-owned directory)
                # We continue even if backup fails since deletion is done via pkexec
                success, error, backed_files = self._backup_local_databases()
                if not success:
                    logger.warning(
                        "Could not backup databases in native mode (expected for root-owned directory): %s",
                        error,
                    )
                    # Clear any partial backup
                    self._cleanup_backup()
            else:
                # Flatpak: backup and delete here (user-writable directory)
                success, error, backed_files = self._backup_local_databases()
                if not success:
                    result = UpdateResult(
                        status=UpdateStatus.ERROR,
                        stdout="",
                        stderr=error or "",
                        exit_code=-1,
                        databases_updated=0,
                        error_message=error or _("Backup failed"),
                    )
                    duration = time.monotonic() - start_time
                    self._save_update_log(result, duration)
                    return result

                # Delete local databases to force fresh download
                success, error, deleted_count = self._delete_local_databases()
                if not success:
                    # Restore from backup and return error
                    self._restore_databases_from_backup()
                    self._cleanup_backup()
                    result = UpdateResult(
                        status=UpdateStatus.ERROR,
                        stdout="",
                        stderr=error or "",
                        exit_code=-1,
                        databases_updated=0,
                        error_message=error or _("Delete failed"),
                    )
                    duration = time.monotonic() - start_time
                    self._save_update_log(result, duration)
                    return result

                logger.info("Deleted %d database file(s) before force update", deleted_count)

        # Before building manual command, check for running freshclam processes.
        # Service check may have been skipped (force mode), but a running process
        # will hold locks and cause the manual method to fail.
        is_running, running_pid = self._check_freshclam_running()
        if is_running and running_pid:
            logger.warning(
                "Another freshclam instance running (PID %s), aborting manual update",
                running_pid,
            )
            result = UpdateResult(
                status=UpdateStatus.ERROR,
                stdout="",
                stderr="",
                exit_code=-1,
                databases_updated=0,
                error_message=_(
                    "Another freshclam instance is running (PID {pid}). "
                    "Stop it first: sudo systemctl stop clamav-freshclam"
                ).format(pid=running_pid),
            )
            duration = time.monotonic() - start_time
            self._save_update_log(result, duration)
            return result

        # Build freshclam command
        cmd = self._build_command(force=force)

        try:
            self._update_cancelled = False
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=get_clean_env(),
            )

            timed_out = False
            try:
                stdout, stderr = self._current_process.communicate(
                    timeout=_UPDATE_COMMUNICATE_TIMEOUT
                )
                exit_code = self._current_process.returncode
            except subprocess.TimeoutExpired as e:
                # Process timed out - capture partial output and kill
                logger.warning("Update process timed out, killing")
                timed_out = True
                self._current_process.kill()
                # Capture partial output from exception
                # Note: TimeoutExpired.stdout/stderr are always bytes even with text=True
                # Must decode before concatenating with string output from communicate()
                # Handle both bytes (real) and str (test mocks) for robustness
                if e.stdout:
                    partial_stdout = (
                        e.stdout
                        if isinstance(e.stdout, str)
                        else e.stdout.decode("utf-8", errors="replace")
                    )
                else:
                    partial_stdout = ""
                if e.stderr:
                    partial_stderr = (
                        e.stderr
                        if isinstance(e.stderr, str)
                        else e.stderr.decode("utf-8", errors="replace")
                    )
                else:
                    partial_stderr = ""
                try:
                    remaining_stdout, remaining_stderr = self._current_process.communicate(
                        timeout=_KILL_WAIT_TIMEOUT
                    )
                    stdout = partial_stdout + (remaining_stdout or "")
                    stderr = partial_stderr + (remaining_stderr or "")
                except subprocess.TimeoutExpired:
                    stdout = partial_stdout
                    stderr = partial_stderr
                exit_code = -1  # Indicate timeout
            finally:
                # Ensure process is cleaned up even if communicate() raises
                process = self._current_process
                if process is not None:
                    self._current_process = None  # Clear first to avoid race
                    try:
                        if process.poll() is None:  # Only kill if still running
                            process.kill()
                        process.wait(timeout=_KILL_WAIT_TIMEOUT)
                    except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
                        pass

            # Check if timed out (and not cancelled) - treat as error
            if timed_out and not self._update_cancelled:
                if force:
                    self._restore_databases_from_backup()
                result = UpdateResult(
                    status=UpdateStatus.ERROR,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    databases_updated=0,
                    error_message=_("Update timed out after 10 minutes"),
                )
                duration = time.monotonic() - start_time
                self._save_update_log(result, duration)
                self._cleanup_backup()
                return result

            # Check if cancelled during execution
            if self._update_cancelled:
                if force and is_flatpak():
                    self._restore_databases_from_backup()
                result = UpdateResult(
                    status=UpdateStatus.CANCELLED,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    databases_updated=0,
                    error_message=_("Update cancelled by user"),
                )
                duration = time.monotonic() - start_time
                self._save_update_log(result, duration)
                self._cleanup_backup()
                return result

            # Parse the results
            result = self._parse_results(stdout, stderr, exit_code)

            # On error in Flatpak mode, restore databases from backup
            # In native mode, restore is skipped (backup was likely not possible)
            if force and result.status == UpdateStatus.ERROR and is_flatpak():
                self._restore_databases_from_backup()

            duration = time.monotonic() - start_time
            self._save_update_log(result, duration)
            self._cleanup_backup()
            return result

        except FileNotFoundError:
            if force and is_flatpak():
                self._restore_databases_from_backup()
            result = UpdateResult(
                status=UpdateStatus.ERROR,
                stdout="",
                stderr="freshclam executable not found",
                exit_code=-1,
                databases_updated=0,
                error_message=_("freshclam executable not found"),
            )
            duration = time.monotonic() - start_time
            self._save_update_log(result, duration)
            self._cleanup_backup()
            return result
        except PermissionError as e:
            if force and is_flatpak():
                self._restore_databases_from_backup()
            result = UpdateResult(
                status=UpdateStatus.ERROR,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                databases_updated=0,
                error_message=_("Permission denied: {error}").format(error=e),
            )
            duration = time.monotonic() - start_time
            self._save_update_log(result, duration)
            self._cleanup_backup()
            return result
        except Exception as e:
            if force and is_flatpak():
                self._restore_databases_from_backup()
            result = UpdateResult(
                status=UpdateStatus.ERROR,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                databases_updated=0,
                error_message=_("Update failed: {error}").format(error=e),
            )
            duration = time.monotonic() - start_time
            self._save_update_log(result, duration)
            self._cleanup_backup()
            return result

    def update_async(
        self,
        callback: Callable[[UpdateResult], None],
        force: bool = False,
        prefer_service: bool = True,
    ) -> None:
        """
        Execute an asynchronous database update.

        The update runs in a background thread and the callback is invoked
        on the main GTK thread via GLib.idle_add when complete.

        Args:
            callback: Function to call with UpdateResult when update completes
            force: If True, backup existing databases, delete them, then download
                   fresh copies from mirrors. Previous databases are restored if
                   the update fails.
            prefer_service: If True (default), attempt to trigger update via
                           freshclam systemd service using SIGUSR1 when available.
        """

        def update_thread():
            result = self.update_sync(force=force, prefer_service=prefer_service)
            # Schedule callback on main thread
            GLib.idle_add(callback, result)

        thread = threading.Thread(target=update_thread)
        thread.daemon = True
        thread.start()

    def cancel(self) -> None:
        """
        Cancel the current update operation with graceful shutdown escalation.

        If an update is in progress, it will be terminated with SIGTERM first,
        then escalated to SIGKILL if the process doesn't respond within
        the grace period.
        """
        self._update_cancelled = True
        process = self._current_process
        if process is None:
            return

        # Step 1: SIGTERM (graceful)
        try:
            process.terminate()
        except (OSError, ProcessLookupError):
            # Process already gone
            return

        # Step 2: Wait for graceful termination
        try:
            process.wait(timeout=_TERMINATE_GRACE_TIMEOUT)
        except subprocess.TimeoutExpired:
            # Step 3: SIGKILL (forceful)
            logger.warning("Update process didn't terminate gracefully, killing")
            try:
                process.kill()
                process.wait(timeout=_KILL_WAIT_TIMEOUT)
            except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
                pass  # Best effort

    def _build_command(self, force: bool = False) -> list[str]:
        """
        Build the freshclam command arguments with privilege elevation.

        Uses pkexec for privilege elevation since freshclam requires
        root access to update the ClamAV database in /var/lib/clamav/.

        In Flatpak, databases are stored in user-writable directory so
        no privilege elevation is needed.

        When running inside a Flatpak sandbox, the command is automatically
        wrapped with 'flatpak-spawn --host' to execute freshclam on the host system.

        Args:
            force: If True and in native mode, delete databases before running
                   freshclam (via pkexec shell script). In Flatpak, databases
                   are deleted before this method is called.

        Returns:
            List of command arguments (wrapped with flatpak-spawn if in Flatpak)
        """
        freshclam = get_freshclam_path() or "freshclam"

        # In Flatpak, use user-writable database directory (no root needed)
        if is_flatpak():
            # Ensure the database directory exists
            db_dir = ensure_clamav_database_dir()
            logger.debug("Flatpak database directory: %s", db_dir)

            # Generate config file with correct DatabaseDirectory
            config_path = ensure_freshclam_config()
            logger.debug("Flatpak config path: %s", config_path)

            cmd = [freshclam]
            if config_path is not None and config_path.exists():
                cmd.extend(["--config-file", str(config_path)])
            else:
                # Config generation failed - log error but continue
                # freshclam will fail with its own error message
                logger.error(
                    "Failed to generate freshclam config. Config path: %s, exists: %s",
                    config_path,
                    config_path.exists() if config_path else False,
                )
        else:
            # Native: Use pkexec for privilege elevation
            pkexec = get_pkexec_path()
            if pkexec:
                if force:
                    # Force update: Delete databases first, then run freshclam
                    # This all happens via pkexec with root privileges
                    cmd = [
                        pkexec,
                        "sh",
                        "-c",
                        # Delete all ClamAV database files, then run freshclam
                        f"rm -f /var/lib/clamav/*.cvd /var/lib/clamav/*.cld /var/lib/clamav/*.cud 2>/dev/null; {freshclam} --verbose",
                    ]
                    return wrap_host_command(cmd)
                else:
                    cmd = [pkexec, freshclam]
            else:
                # Fallback to running without elevation (may fail with permission error)
                cmd = [freshclam]

        # Add verbose flag for more detailed output
        cmd.append("--verbose")

        # Wrap with flatpak-spawn if running inside Flatpak sandbox
        return wrap_host_command(cmd)

    def _parse_results(self, stdout: str, stderr: str, exit_code: int) -> UpdateResult:
        """
        Parse freshclam output into an UpdateResult.

        freshclam exit codes:
        - 0: Success (updates downloaded or already current)
        - 1: Error occurred

        Args:
            stdout: Standard output from freshclam
            stderr: Standard error from freshclam
            exit_code: Process exit code

        Returns:
            Parsed UpdateResult
        """
        databases_updated = 0

        # Combine stdout and stderr for parsing (freshclam uses both)
        output = stdout + stderr

        # Parse output line by line
        for line in output.splitlines():
            line = line.strip()

            # Check for database update messages
            # Format: "daily.cvd updated (version: XXXXX, ..."
            # or "main.cvd updated (version: XXXXX, ..."
            if "updated (version:" in line.lower():
                databases_updated += 1

            # Check if already up to date
            # Format: "daily.cvd database is up-to-date"
            if "is up-to-date" in line.lower() or "is up to date" in line.lower():
                pass

        # Determine status from exit code and parsed info
        if exit_code == 0:
            if databases_updated > 0:
                status = UpdateStatus.SUCCESS
            else:
                status = UpdateStatus.UP_TO_DATE
            error_message = None
        else:
            status = UpdateStatus.ERROR
            # Try to extract a meaningful error message
            error_message = self._extract_error_message(stdout, stderr, exit_code)

        return UpdateResult(
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            databases_updated=databases_updated,
            error_message=error_message,
        )

    def _extract_error_message(self, stdout: str, stderr: str, exit_code: int = 1) -> str:
        """
        Extract a meaningful error message from freshclam output.

        Args:
            stdout: Standard output from freshclam
            stderr: Standard error from freshclam
            exit_code: Process exit code

        Returns:
            Extracted error message
        """
        # Check for common error patterns
        output = stdout + stderr
        output_lower = output.lower()

        # Check for pkexec authentication errors
        # Exit code 126 = pkexec: user dismissed auth dialog
        # Exit code 127 = pkexec: not authorized
        if exit_code == 126:
            return _("Authentication cancelled. Database update requires administrator privileges.")
        if exit_code == 127 and "pkexec" in output_lower:
            return _("Authorization failed. You are not authorized to update the database.")

        # Rate limiting errors
        rate_limit_patterns = [
            "rate limit",
            "rate-limit",
            "rate limited",
            "429",
            "too many requests",
            "temporarily blocked",
            "blocked temporarily",
        ]
        if any(pattern in output_lower for pattern in rate_limit_patterns):
            return _("Update rate limited by mirror. Please wait a few minutes and try again.")

        # CDN/Proxy errors (often indicate rate limiting)
        if "cloudfront" in output_lower or "cloudflare" in output_lower:
            return _(
                "Update blocked by CDN. This may be due to rate limiting."
                " Please wait and try again later."
            )

        # Mirror unavailable
        if "mirror" in output_lower and ("down" in output_lower or "unavailable" in output_lower):
            return _("ClamAV mirror is currently unavailable. Please try again later.")

        # Certificate/SSL errors
        if any(
            p in output_lower for p in ["certificate", "ssl error", "tls error", "verify failed"]
        ):
            return _("SSL/TLS certificate error. The mirror may have configuration issues.")

        # Timeout errors
        if "timeout" in output_lower or "timed out" in output_lower:
            return _("Connection timed out. Please check your network connection.")

        # Check for polkit/pkexec related errors
        if "not authorized" in output_lower or "authorization" in output_lower:
            return _("Authorization failed. Please try again and enter your password.")

        # Check for lock file error (another freshclam running)
        if "locked" in output_lower or "lock" in output_lower:
            return _("Database is locked. Another freshclam instance may be running.")

        # Check for permission errors
        if "permission denied" in output_lower:
            return _("Permission denied. You may need elevated privileges to update the database.")

        # Check for network errors
        if "can't connect" in output_lower or "connection" in output_lower:
            return _("Connection error. Please check your network connection.")

        # Check for DNS errors
        if "can't resolve" in output_lower or "host not found" in output_lower:
            return _("DNS resolution failed. Please check your network settings.")

        # Default to stderr content if available
        if stderr.strip():
            return stderr.strip()

        return _("Update failed with an unknown error. Check the logs for details.")

    def _save_update_log(self, result: UpdateResult, duration: float) -> None:
        """
        Save an update result to the log manager.

        Args:
            result: The UpdateResult to log
            duration: Duration of the update in seconds
        """
        # Build summary based on update result
        if result.status == UpdateStatus.SUCCESS:
            summary = _("Database update completed - {count} database(s) updated").format(
                count=result.databases_updated
            )
        elif result.status == UpdateStatus.UP_TO_DATE:
            summary = _("Database update completed - Already up to date")
        elif result.status == UpdateStatus.CANCELLED:
            summary = _("Database update cancelled")
        else:
            summary = _("Database update failed: {error}").format(
                error=result.error_message or _("Unknown error")
            )

        # Build details combining stdout and stderr
        details_parts = []
        if result.stdout:
            details_parts.append(result.stdout)
        if result.stderr:
            details_parts.append(f"--- Errors ---\n{result.stderr}")
        details = "\n".join(details_parts) if details_parts else "(No output)"

        # Create and save log entry
        log_entry = LogEntry.create(
            log_type="update",
            status=result.status.value,
            summary=summary,
            details=details,
            path=None,  # Updates don't have a path
            duration=duration,
        )

        self._log_manager.save_log(log_entry)

    def _backup_local_databases(self) -> tuple[bool, str | None, list[Path]]:
        """
        Backup local ClamAV database files to a temporary directory.

        Returns:
            Tuple of (success, error_message, list_of_backed_files)
        """
        # Determine database directory
        if is_flatpak():
            db_dir = get_clamav_database_dir()
            if db_dir is None:
                return False, "Database directory not configured", []
        else:
            db_dir = Path("/var/lib/clamav")

        if not db_dir.exists():
            return False, "Database directory not found", []

        # Create backup directory with timestamp
        backup_dir = Path(tempfile.mkdtemp(prefix="clamav_backup_"))
        self._force_update_backup_dir = backup_dir

        # Common ClamAV database files
        db_patterns = ["*.cvd", "*.cld", "*.cud"]
        backed_up = []

        for pattern in db_patterns:
            for db_file in db_dir.glob(pattern):
                try:
                    backup_path = backup_dir / db_file.name
                    shutil.copy2(db_file, backup_path)
                    backed_up.append(backup_path)
                    logger.debug("Backed up database file: %s", db_file.name)
                except OSError as e:
                    # Cleanup on failure
                    shutil.rmtree(backup_dir, ignore_errors=True)
                    return False, f"Failed to backup {db_file.name}: {e}", []

        if not backed_up:
            shutil.rmtree(backup_dir, ignore_errors=True)
            return False, "No database files found to backup", []

        logger.info("Backed up %d database file(s) to %s", len(backed_up), backup_dir)
        return True, None, backed_up

    def _restore_databases_from_backup(self) -> tuple[bool, str | None]:
        """
        Restore database files from backup.

        Returns:
            Tuple of (success, error_message)
        """
        backup_dir = getattr(self, "_force_update_backup_dir", None)
        if not backup_dir or not backup_dir.exists():
            return False, "No backup available"

        # Determine database directory
        if is_flatpak():
            db_dir = get_clamav_database_dir()
            if db_dir is None:
                return False, "Database directory not configured"
        else:
            db_dir = Path("/var/lib/clamav")

        if not db_dir.exists():
            return False, "Database directory not found"

        restored_count = 0
        for backup_file in backup_dir.glob("*"):
            try:
                target_path = db_dir / backup_file.name
                shutil.copy2(backup_file, target_path)
                restored_count += 1
                logger.debug("Restored database file: %s", backup_file.name)
            except OSError as e:
                return False, f"Failed to restore {backup_file.name}: {e}"

        logger.info("Restored %d database file(s) from backup", restored_count)
        return True, f"Restored {restored_count} database file(s)"

    def _cleanup_backup(self) -> None:
        """Clean up backup directory."""
        backup_dir = getattr(self, "_force_update_backup_dir", None)
        if backup_dir and backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
            self._force_update_backup_dir = None
            logger.debug("Cleaned up backup directory: %s", backup_dir)

    def _delete_local_databases(self) -> tuple[bool, str | None, int]:
        """
        Delete local ClamAV database files to force fresh download.

        Returns:
            Tuple of (success, error_message, deleted_count)
        """
        # Determine database directory
        if is_flatpak():
            db_dir = get_clamav_database_dir()
            if db_dir is None:
                return False, "Database directory not configured", 0
        else:
            db_dir = Path("/var/lib/clamav")

        if not db_dir.exists():
            return False, "Database directory not found", 0

        # Common ClamAV database files
        db_patterns = ["*.cvd", "*.cld", "*.cud"]
        deleted_count = 0
        errors = []

        for pattern in db_patterns:
            for db_file in db_dir.glob(pattern):
                try:
                    db_file.unlink()
                    deleted_count += 1
                    logger.debug("Deleted database file: %s", db_file.name)
                except OSError as e:
                    errors.append(f"{db_file.name}: {e}")

        if errors:
            error_msg = f"Some files could not be deleted: {'; '.join(errors)}"
            if deleted_count == 0:
                return False, error_msg, 0
            # Partial success - log warning but continue
            logger.warning(error_msg)

        logger.info("Deleted %d database file(s)", deleted_count)
        return True, None, deleted_count
