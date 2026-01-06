# ClamUI Daemon Scanner Module
"""
Daemon scanner module for ClamUI using clamdscan for clamd communication.
Provides faster scanning by leveraging the ClamAV daemon's in-memory database.
"""

import fnmatch
import logging
import os
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from gi.repository import GLib

from .log_manager import LogEntry, LogManager

logger = logging.getLogger(__name__)

# Timeout constants (seconds)
_TERMINATE_GRACE_TIMEOUT = 5  # Time to wait after SIGTERM before SIGKILL
_KILL_WAIT_TIMEOUT = 2  # Time to wait after SIGKILL

from .scanner import ScanResult, ScanStatus, ThreatDetail
from .settings_manager import SettingsManager
from .threat_classifier import (
    categorize_threat,
    classify_threat_severity_str,
)
from .utils import (
    check_clamd_connection,
    check_clamdscan_installed,
    is_flatpak,
    validate_path,
    which_host_command,
    wrap_host_command,
)


class DaemonScanner:
    """
    ClamAV daemon scanner using clamdscan.

    Provides faster scanning by communicating with the clamd daemon,
    which keeps the virus database loaded in memory.
    """

    def __init__(
        self, log_manager: LogManager | None = None, settings_manager: SettingsManager | None = None
    ):
        """
        Initialize the daemon scanner.

        Args:
            log_manager: Optional LogManager instance for saving scan logs.
            settings_manager: Optional SettingsManager instance for reading
                              exclusion patterns and daemon settings.
        """
        self._current_process: subprocess.Popen | None = None
        self._scan_cancelled = False
        self._log_manager = log_manager if log_manager else LogManager()
        self._settings_manager = settings_manager

    def check_available(self) -> tuple[bool, str | None]:
        """
        Check if daemon scanning is available.

        Verifies both clamdscan is installed and clamd is responding.

        Returns:
            Tuple of (is_available, version_or_error)
        """
        # Check clamdscan is installed
        is_installed, error = check_clamdscan_installed()
        if not is_installed:
            return (False, error)

        # Check clamd is running and responding
        is_connected, message = check_clamd_connection()
        if not is_connected:
            return (False, f"clamd not accessible: {message}")

        return (True, "clamd is available")

    def scan_sync(
        self, path: str, recursive: bool = True, profile_exclusions: dict | None = None
    ) -> ScanResult:
        """
        Execute a synchronous scan using clamdscan.

        WARNING: This will block the calling thread. For UI applications,
        use scan_async() instead.

        Args:
            path: Path to file or directory to scan
            recursive: Whether to scan directories recursively (always true for clamdscan)
            profile_exclusions: Optional exclusions from a scan profile.

        Returns:
            ScanResult with scan details
        """
        start_time = time.monotonic()

        # Validate the path first
        is_valid, error = validate_path(path)
        if not is_valid:
            result = ScanResult(
                status=ScanStatus.ERROR,
                path=path,
                stdout="",
                stderr=error or "Invalid path",
                exit_code=-1,
                infected_files=[],
                scanned_files=0,
                scanned_dirs=0,
                infected_count=0,
                error_message=error,
                threat_details=[],
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

        # Check daemon is available
        is_available, error_msg = self.check_available()
        if not is_available:
            result = ScanResult(
                status=ScanStatus.ERROR,
                path=path,
                stdout="",
                stderr=error_msg or "Daemon not available",
                exit_code=-1,
                infected_files=[],
                scanned_files=0,
                scanned_dirs=0,
                infected_count=0,
                error_message=error_msg,
                threat_details=[],
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

        # Count files/directories before scanning (clamdscan doesn't report these)
        file_count, dir_count = self._count_scan_targets(path, profile_exclusions)

        # Build clamdscan command
        cmd = self._build_command(path, recursive, profile_exclusions)

        try:
            self._scan_cancelled = False
            self._current_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            try:
                stdout, stderr = self._current_process.communicate()
                exit_code = self._current_process.returncode
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

            # Check if cancelled during execution
            if self._scan_cancelled:
                result = ScanResult(
                    status=ScanStatus.CANCELLED,
                    path=path,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    infected_files=[],
                    scanned_files=file_count,
                    scanned_dirs=dir_count,
                    infected_count=0,
                    error_message="Scan cancelled by user",
                    threat_details=[],
                )
                duration = time.monotonic() - start_time
                self._save_scan_log(result, duration)
                return result

            # Parse the results
            result = self._parse_results(path, stdout, stderr, exit_code, file_count, dir_count)

            # Apply exclusion filtering (clamdscan doesn't support --exclude)
            result = self._filter_excluded_threats(result, profile_exclusions)

            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

        except FileNotFoundError:
            result = ScanResult(
                status=ScanStatus.ERROR,
                path=path,
                stdout="",
                stderr="clamdscan executable not found",
                exit_code=-1,
                infected_files=[],
                scanned_files=0,
                scanned_dirs=0,
                infected_count=0,
                error_message="clamdscan executable not found",
                threat_details=[],
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result
        except PermissionError as e:
            result = ScanResult(
                status=ScanStatus.ERROR,
                path=path,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                infected_files=[],
                scanned_files=0,
                scanned_dirs=0,
                infected_count=0,
                error_message=f"Permission denied: {e}",
                threat_details=[],
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result
        except Exception as e:
            result = ScanResult(
                status=ScanStatus.ERROR,
                path=path,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                infected_files=[],
                scanned_files=0,
                scanned_dirs=0,
                infected_count=0,
                error_message=f"Scan failed: {e}",
                threat_details=[],
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

    def scan_async(
        self,
        path: str,
        callback: Callable[[ScanResult], None],
        recursive: bool = True,
        profile_exclusions: dict | None = None,
    ) -> None:
        """
        Execute an asynchronous scan using clamdscan.

        The scan runs in a background thread and the callback is invoked
        on the main GTK thread via GLib.idle_add when complete.

        Args:
            path: Path to file or directory to scan
            callback: Function to call with ScanResult when scan completes
            recursive: Whether to scan directories recursively
            profile_exclusions: Optional exclusions from a scan profile.
        """

        def scan_thread():
            result = self.scan_sync(path, recursive, profile_exclusions)
            GLib.idle_add(callback, result)

        thread = threading.Thread(target=scan_thread)
        thread.daemon = True
        thread.start()

    def cancel(self) -> None:
        """
        Cancel the current scan operation with graceful shutdown escalation.

        If a scan is in progress, it will be terminated with SIGTERM first,
        then escalated to SIGKILL if the process doesn't respond within
        the grace period.
        """
        self._scan_cancelled = True
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
            logger.warning("Daemon scan process didn't terminate gracefully, killing")
            try:
                process.kill()
                process.wait(timeout=_KILL_WAIT_TIMEOUT)
            except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
                pass  # Best effort

    def _build_command(
        self, path: str, recursive: bool, profile_exclusions: dict | None = None
    ) -> list[str]:
        """
        Build the clamdscan command arguments.

        Uses --multiscan for parallel scanning and --fdpass for
        file descriptor passing (faster than streaming).

        Args:
            path: Path to scan
            recursive: Whether to scan recursively (clamdscan is always recursive)
            profile_exclusions: Optional exclusions from a scan profile.

        Returns:
            List of command arguments (wrapped with flatpak-spawn if in Flatpak)
        """
        clamdscan = which_host_command("clamdscan") or "clamdscan"
        cmd = [clamdscan]

        # Use multiscan and fdpass for better performance
        # In Flatpak: use --stream instead (clamdscan reads file and streams to clamd)
        # This avoids permission issues where clamd can't access files created by Flatpak
        if is_flatpak():
            cmd.append("--stream")
        else:
            cmd.append("--multiscan")
            cmd.append("--fdpass")

        # Show infected files only
        cmd.append("-i")

        # NOTE: clamdscan does NOT support --exclude or --exclude-dir options
        # (it silently ignores them with a warning). Exclusion filtering is
        # performed post-scan in _filter_excluded_threats() instead.

        cmd.append(path)
        return wrap_host_command(cmd)

    def _count_scan_targets(
        self, path: str, profile_exclusions: dict | None = None
    ) -> tuple[int, int]:
        """
        Count files and directories that will be scanned.

        Since clamdscan doesn't report file/directory counts in its output,
        we count them ourselves before scanning.

        Args:
            path: Path to scan
            profile_exclusions: Optional exclusions from a scan profile.

        Returns:
            Tuple of (file_count, dir_count)
        """
        scan_path = Path(path)

        # Single file scan
        if scan_path.is_file():
            return (1, 0)

        # Not a valid path
        if not scan_path.is_dir():
            return (0, 0)

        # Collect exclusion patterns
        exclude_patterns: list[str] = []
        exclude_dirs: list[str] = []

        # Global exclusions from settings
        if self._settings_manager is not None:
            exclusions = self._settings_manager.get("exclusion_patterns", [])
            for exclusion in exclusions:
                if not exclusion.get("enabled", True):
                    continue
                pattern = exclusion.get("pattern", "")
                if not pattern:
                    continue
                exclusion_type = exclusion.get("type", "pattern")
                if exclusion_type == "directory":
                    exclude_dirs.append(pattern)
                else:
                    exclude_patterns.append(pattern)

        # Profile exclusions
        if profile_exclusions:
            for excl_path in profile_exclusions.get("paths", []):
                if excl_path:
                    # Expand ~ in paths
                    if excl_path.startswith("~"):
                        excl_path = str(Path(excl_path).expanduser())
                    exclude_dirs.append(excl_path)

            for pattern in profile_exclusions.get("patterns", []):
                if pattern:
                    exclude_patterns.append(pattern)

        file_count = 0
        dir_count = 0

        try:
            for root, dirs, files in os.walk(path):
                # Filter out excluded directories (modifies dirs in-place)
                dirs[:] = [
                    d
                    for d in dirs
                    if not self._is_excluded(os.path.join(root, d), d, exclude_dirs, is_dir=True)
                ]

                # Count directories (excluding the root)
                dir_count += len(dirs)

                # Count files that aren't excluded
                for f in files:
                    file_path = os.path.join(root, f)
                    if not self._is_excluded(file_path, f, exclude_patterns, is_dir=False):
                        file_count += 1
        except (PermissionError, OSError):
            # If we can't access the directory, return 0 counts
            pass

        # Count the root directory itself
        if dir_count > 0 or file_count > 0:
            dir_count += 1

        return (file_count, dir_count)

    def _is_excluded(self, full_path: str, name: str, patterns: list[str], is_dir: bool) -> bool:
        """
        Check if a path matches any exclusion pattern.

        Args:
            full_path: Full path to check
            name: Base name of the file/directory
            patterns: List of exclusion patterns (glob or path)
            is_dir: Whether this is a directory

        Returns:
            True if the path should be excluded
        """
        for pattern in patterns:
            # Check if pattern is an absolute path
            if pattern.startswith("/") or pattern.startswith("~"):
                expanded = str(Path(pattern).expanduser()) if pattern.startswith("~") else pattern
                if full_path.startswith(expanded):
                    return True
            # Check glob pattern against filename
            elif fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(full_path, pattern):
                return True
        return False

    def _parse_results(
        self,
        path: str,
        stdout: str,
        stderr: str,
        exit_code: int,
        file_count: int = 0,
        dir_count: int = 0,
    ) -> ScanResult:
        """
        Parse clamdscan output into a ScanResult.

        clamdscan output format is similar to clamscan but doesn't include
        file/directory counts in the summary. These are provided separately
        via the file_count and dir_count parameters.

        Exit codes: 0=clean, 1=infected, 2=error

        Args:
            path: The scanned path
            stdout: Standard output from clamdscan
            stderr: Standard error from clamdscan
            exit_code: Process exit code
            file_count: Pre-counted number of files scanned
            dir_count: Pre-counted number of directories scanned

        Returns:
            Parsed ScanResult
        """
        infected_files = []
        threat_details = []
        scanned_files = file_count
        scanned_dirs = dir_count
        infected_count = 0

        for line in stdout.splitlines():
            line = line.strip()

            if line.endswith("FOUND"):
                parts = line.rsplit(":", 1)
                if len(parts) == 2:
                    file_path = parts[0].strip()
                    threat_part = parts[1].strip()
                    threat_name = (
                        threat_part.rsplit(" ", 1)[0].strip()
                        if " FOUND" in threat_part
                        else threat_part
                    )

                    infected_files.append(file_path)

                    threat_detail = ThreatDetail(
                        file_path=file_path,
                        threat_name=threat_name,
                        category=categorize_threat(threat_name),
                        severity=classify_threat_severity_str(threat_name),
                    )
                    threat_details.append(threat_detail)
                    infected_count += 1

        if exit_code == 0:
            status = ScanStatus.CLEAN
        elif exit_code == 1:
            status = ScanStatus.INFECTED
        else:
            status = ScanStatus.ERROR

        return ScanResult(
            status=status,
            path=path,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            infected_files=infected_files,
            scanned_files=scanned_files,
            scanned_dirs=scanned_dirs,
            infected_count=infected_count,
            error_message=stderr if status == ScanStatus.ERROR else None,
            threat_details=threat_details,
        )

    def _filter_excluded_threats(
        self, result: ScanResult, profile_exclusions: dict | None = None
    ) -> ScanResult:
        """
        Filter out threats that match exclusion patterns.

        Since clamdscan doesn't support --exclude options, we filter the
        results post-scan to remove any threats matching exclusion patterns.

        Args:
            result: The parsed ScanResult
            profile_exclusions: Optional exclusions from a scan profile

        Returns:
            A new ScanResult with excluded threats filtered out
        """
        if result.status != ScanStatus.INFECTED or not result.threat_details:
            return result

        # Collect all exclusion patterns
        exclude_patterns: list[str] = []

        # Global exclusions from settings
        if self._settings_manager is not None:
            exclusions = self._settings_manager.get("exclusion_patterns", [])
            for exclusion in exclusions:
                if not exclusion.get("enabled", True):
                    continue
                pattern = exclusion.get("pattern", "")
                if pattern:
                    exclude_patterns.append(pattern)

        # Profile exclusions (patterns only, paths are for directories)
        if profile_exclusions:
            for pattern in profile_exclusions.get("patterns", []):
                if pattern:
                    exclude_patterns.append(pattern)

        if not exclude_patterns:
            return result

        # Filter threats
        filtered_threats = []
        filtered_files = []

        for threat in result.threat_details:
            file_path = threat.file_path
            is_excluded = False

            for pattern in exclude_patterns:
                # Expand ~ in patterns
                if pattern.startswith("~"):
                    pattern = str(Path(pattern).expanduser())

                # Check for exact path match or fnmatch pattern match
                if file_path == pattern or fnmatch.fnmatch(file_path, pattern):
                    is_excluded = True
                    break

            if not is_excluded:
                filtered_threats.append(threat)
                filtered_files.append(file_path)

        # If all threats were filtered, return CLEAN status
        if not filtered_threats:
            return ScanResult(
                status=ScanStatus.CLEAN,
                path=result.path,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_code,
                infected_files=[],
                scanned_files=result.scanned_files,
                scanned_dirs=result.scanned_dirs,
                infected_count=0,
                error_message=None,
                threat_details=[],
            )

        # Return result with filtered threats
        return ScanResult(
            status=ScanStatus.INFECTED,
            path=result.path,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            infected_files=filtered_files,
            scanned_files=result.scanned_files,
            scanned_dirs=result.scanned_dirs,
            infected_count=len(filtered_threats),
            error_message=None,
            threat_details=filtered_threats,
        )

    def _save_scan_log(self, result: ScanResult, duration: float) -> None:
        """Save scan result to log."""
        # Map ScanStatus to string
        status_map = {
            ScanStatus.CLEAN: "clean",
            ScanStatus.INFECTED: "infected",
            ScanStatus.CANCELLED: "cancelled",
            ScanStatus.ERROR: "error",
        }
        scan_status = status_map.get(result.status, "error")

        # Convert threat details to dicts for the factory method
        threat_dicts = [
            {"file_path": t.file_path, "threat_name": t.threat_name} for t in result.threat_details
        ]

        entry = LogEntry.from_scan_result_data(
            scan_status=scan_status,
            path=result.path,
            duration=duration,
            scanned_files=result.scanned_files,
            scanned_dirs=result.scanned_dirs,
            infected_count=result.infected_count,
            threat_details=threat_dicts,
            error_message=result.error_message,
            stdout=result.stdout,
            suffix="(daemon)",
            scheduled=False,
        )
        self._log_manager.save_log(entry)
