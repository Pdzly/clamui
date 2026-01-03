# ClamUI Scanner Module
"""
Scanner module for ClamUI providing ClamAV subprocess execution and async scanning.
"""

import fnmatch
import re
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from gi.repository import GLib

if TYPE_CHECKING:
    from .daemon_scanner import DaemonScanner

import contextlib

from .log_manager import LogEntry, LogManager
from .settings_manager import SettingsManager
from .threat_classifier import (
    categorize_threat,
    classify_threat_severity_str,
)
from .utils import (
    check_clamav_installed,
    check_clamd_connection,
    get_clamav_path,
    validate_path,
    wrap_host_command,
)


def glob_to_regex(pattern: str) -> str:
    """
    Convert a user-friendly glob pattern to POSIX ERE for ClamAV.

    Uses fnmatch.translate() for conversion and strips Python-specific
    regex suffixes for ClamAV compatibility. Adds anchors (^ and $) to ensure
    the pattern matches the entire string, not just a substring.

    Note: fnmatch doesn't support '**' recursive wildcards - document as limitation.

    Args:
        pattern: Glob pattern (e.g., '*.log', 'node_modules', '/tmp/*')

    Returns:
        POSIX Extended Regular Expression string with anchors
    """
    regex = fnmatch.translate(pattern)
    # Strip fnmatch's \Z(?ms) suffix for ClamAV compatibility
    # fnmatch.translate() adds (?s:...) wrapper and \Z anchor
    # We need to remove these for ClamAV's regex engine
    if regex.endswith(r"\Z"):
        regex = regex[:-2]
    # Handle newer Python versions that use (?s:pattern)\Z format
    if regex.startswith("(?s:") and regex.endswith(")"):
        regex = regex[4:-1]
    # Add anchors to ensure full string match (prevents substring matching)
    if not regex.startswith("^"):
        regex = "^" + regex
    if not regex.endswith("$"):
        regex = regex + "$"
    return regex


def validate_pattern(pattern: str) -> bool:
    """
    Validate that a pattern can be converted and compiled as regex.

    Args:
        pattern: Glob pattern to validate

    Returns:
        True if pattern is valid, False otherwise
    """
    if not pattern or not pattern.strip():
        return False
    try:
        re.compile(glob_to_regex(pattern))
        return True
    except re.error:
        return False


class ScanStatus(Enum):
    """Status of a scan operation."""

    CLEAN = "clean"  # No threats found (exit code 0)
    INFECTED = "infected"  # Threats found (exit code 1)
    ERROR = "error"  # Error occurred (exit code 2 or exception)
    CANCELLED = "cancelled"  # Scan was cancelled


@dataclass
class ThreatDetail:
    """Detailed information about a detected threat."""

    file_path: str
    threat_name: str
    category: str
    severity: str


@dataclass
class ScanResult:
    """Result of a scan operation."""

    status: ScanStatus
    path: str
    stdout: str
    stderr: str
    exit_code: int
    infected_files: list[str]
    scanned_files: int
    scanned_dirs: int
    infected_count: int
    error_message: str | None
    threat_details: list[ThreatDetail]

    @property
    def is_clean(self) -> bool:
        """Check if scan found no threats."""
        return self.status == ScanStatus.CLEAN

    @property
    def has_threats(self) -> bool:
        """Check if scan found threats."""
        return self.status == ScanStatus.INFECTED


class Scanner:
    """
    ClamAV scanner with async execution support.

    Supports multiple scan backends:
    - "auto": Prefer daemon if available, fallback to clamscan
    - "daemon": Use clamd daemon only (error if unavailable)
    - "clamscan": Use standalone clamscan only

    Provides methods for running scans in a background thread
    while safely updating the UI via GLib.idle_add.
    """

    def __init__(
        self, log_manager: LogManager | None = None, settings_manager: SettingsManager | None = None
    ):
        """
        Initialize the scanner.

        Args:
            log_manager: Optional LogManager instance for saving scan logs.
                         If not provided, a default instance is created.
            settings_manager: Optional SettingsManager instance for reading
                              exclusion patterns and scan backend settings.
        """
        self._current_process: subprocess.Popen | None = None
        self._scan_cancelled = False
        self._log_manager = log_manager if log_manager else LogManager()
        self._settings_manager = settings_manager
        self._daemon_scanner: DaemonScanner | None = None

    def _get_backend(self) -> str:
        """Get the configured scan backend."""
        if self._settings_manager:
            return self._settings_manager.get("scan_backend", "auto")
        return "auto"

    def _get_daemon_scanner(self) -> "DaemonScanner":
        """Get or create the daemon scanner instance."""
        if self._daemon_scanner is None:
            from .daemon_scanner import DaemonScanner

            self._daemon_scanner = DaemonScanner(
                log_manager=self._log_manager, settings_manager=self._settings_manager
            )
        return self._daemon_scanner

    def get_active_backend(self) -> str:
        """
        Get the backend that will actually be used for scanning.

        Returns:
            "daemon" if daemon will be used, "clamscan" otherwise
        """
        backend = self._get_backend()
        if backend == "clamscan":
            return "clamscan"
        elif backend == "daemon":
            is_available, _ = self._get_daemon_scanner().check_available()
            return "daemon" if is_available else "unavailable"
        else:  # auto
            is_available, _ = check_clamd_connection()
            return "daemon" if is_available else "clamscan"

    def check_available(self) -> tuple[bool, str | None]:
        """
        Check if the configured scan backend is available.

        Returns:
            Tuple of (is_available, version_or_error)
        """
        backend = self._get_backend()

        if backend == "clamscan":
            return check_clamav_installed()
        elif backend == "daemon":
            return self._get_daemon_scanner().check_available()
        else:  # auto
            # For auto, check if daemon is available, otherwise fallback to clamscan
            is_daemon_available, _ = check_clamd_connection()
            if is_daemon_available:
                return (True, "Using clamd daemon")
            return check_clamav_installed()

    def scan_sync(
        self, path: str, recursive: bool = True, profile_exclusions: dict | None = None
    ) -> ScanResult:
        """
        Execute a synchronous scan on the given path.

        WARNING: This will block the calling thread. For UI applications,
        use scan_async() instead.

        Args:
            path: Path to file or directory to scan
            recursive: Whether to scan directories recursively
            profile_exclusions: Optional exclusions from a scan profile.
                               Format: {"paths": ["/path1", ...], "patterns": ["*.ext", ...]}

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

        # Determine which backend to use
        backend = self._get_backend()

        # For daemon-only mode, delegate entirely to daemon scanner
        if backend == "daemon":
            daemon_scanner = self._get_daemon_scanner()
            return daemon_scanner.scan_sync(path, recursive, profile_exclusions)

        # For auto mode, try daemon first if available
        if backend == "auto":
            is_daemon_available, _ = check_clamd_connection()
            if is_daemon_available:
                daemon_scanner = self._get_daemon_scanner()
                return daemon_scanner.scan_sync(path, recursive, profile_exclusions)

        # Fall through to clamscan for "clamscan" mode or auto fallback
        is_installed, version_or_error = check_clamav_installed()
        if not is_installed:
            result = ScanResult(
                status=ScanStatus.ERROR,
                path=path,
                stdout="",
                stderr=version_or_error or "ClamAV not installed",
                exit_code=-1,
                infected_files=[],
                scanned_files=0,
                scanned_dirs=0,
                infected_count=0,
                error_message=version_or_error,
                threat_details=[],
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

        # Build clamscan command
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
                if self._current_process is not None:
                    try:
                        self._current_process.kill()
                        self._current_process.wait(timeout=5)
                    except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
                        pass
                    self._current_process = None

            # Check if cancelled during execution
            if self._scan_cancelled:
                result = ScanResult(
                    status=ScanStatus.CANCELLED,
                    path=path,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    infected_files=[],
                    scanned_files=0,
                    scanned_dirs=0,
                    infected_count=0,
                    error_message="Scan cancelled by user",
                    threat_details=[],
                )
                duration = time.monotonic() - start_time
                self._save_scan_log(result, duration)
                return result

            # Parse the results
            result = self._parse_results(path, stdout, stderr, exit_code)
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

        except FileNotFoundError:
            result = ScanResult(
                status=ScanStatus.ERROR,
                path=path,
                stdout="",
                stderr="ClamAV executable not found",
                exit_code=-1,
                infected_files=[],
                scanned_files=0,
                scanned_dirs=0,
                infected_count=0,
                error_message="ClamAV executable not found",
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
        Execute an asynchronous scan on the given path.

        The scan runs in a background thread and the callback is invoked
        on the main GTK thread via GLib.idle_add when complete.

        Args:
            path: Path to file or directory to scan
            callback: Function to call with ScanResult when scan completes
            recursive: Whether to scan directories recursively
            profile_exclusions: Optional exclusions from a scan profile.
                               Format: {"paths": ["/path1", ...], "patterns": ["*.ext", ...]}
        """

        def scan_thread():
            result = self.scan_sync(path, recursive, profile_exclusions)
            # Schedule callback on main thread
            GLib.idle_add(callback, result)

        thread = threading.Thread(target=scan_thread)
        thread.daemon = True
        thread.start()

    def cancel(self) -> None:
        """
        Cancel the current scan operation.

        If a scan is in progress, it will be terminated.
        Cancels both clamscan and daemon scanner if active.
        """
        self._scan_cancelled = True
        if self._current_process is not None:
            with contextlib.suppress(OSError, ProcessLookupError):
                self._current_process.terminate()
        # Also cancel daemon scanner if it exists
        if self._daemon_scanner is not None:
            self._daemon_scanner.cancel()

    def _build_command(
        self, path: str, recursive: bool, profile_exclusions: dict | None = None
    ) -> list[str]:
        """
        Build the clamscan command arguments.

        When running inside a Flatpak sandbox, the command is automatically
        wrapped with 'flatpak-spawn --host' to execute ClamAV on the host system.

        Args:
            path: Path to scan
            recursive: Whether to scan recursively
            profile_exclusions: Optional exclusions from a scan profile.
                               Format: {"paths": ["/path1", ...], "patterns": ["*.ext", ...]}

        Returns:
            List of command arguments (wrapped with flatpak-spawn if in Flatpak)
        """
        clamscan = get_clamav_path() or "clamscan"
        cmd = [clamscan]

        # Add recursive flag for directories
        if recursive and Path(path).is_dir():
            cmd.append("-r")

        # Show infected files only (reduces output noise)
        cmd.append("-i")

        # Inject exclusion patterns from settings
        if self._settings_manager is not None:
            exclusions = self._settings_manager.get("exclusion_patterns", [])
            for exclusion in exclusions:
                if not exclusion.get("enabled", True):
                    continue

                pattern = exclusion.get("pattern", "")
                if not pattern:
                    continue

                regex = glob_to_regex(pattern)
                exclusion_type = exclusion.get("type", "pattern")

                if exclusion_type == "directory":
                    cmd.extend(["--exclude-dir", regex])
                else:  # file or pattern
                    cmd.extend(["--exclude", regex])

        # Apply profile exclusions (paths and patterns)
        if profile_exclusions:
            # Handle path exclusions (directories)
            for excl_path in profile_exclusions.get("paths", []):
                if not excl_path:
                    continue
                # Expand ~ in exclusion paths
                if excl_path.startswith("~"):
                    excl_path = str(Path(excl_path).expanduser())
                # Use the path directly for --exclude-dir (ClamAV accepts paths)
                cmd.extend(["--exclude-dir", excl_path])

            # Handle pattern exclusions (file patterns like *.tmp)
            for pattern in profile_exclusions.get("patterns", []):
                if not pattern:
                    continue
                # Convert glob pattern to regex for ClamAV
                regex = glob_to_regex(pattern)
                cmd.extend(["--exclude", regex])

        # Add the path to scan
        cmd.append(path)

        # Wrap with flatpak-spawn if running inside Flatpak sandbox
        return wrap_host_command(cmd)

    def _parse_results(self, path: str, stdout: str, stderr: str, exit_code: int) -> ScanResult:
        """
        Parse clamscan output into a ScanResult.

        ClamAV exit codes:
        - 0: No virus found
        - 1: Virus(es) found
        - 2: Some error(s) occurred

        Args:
            path: The scanned path
            stdout: Standard output from clamscan
            stderr: Standard error from clamscan
            exit_code: Process exit code

        Returns:
            Parsed ScanResult
        """
        infected_files = []
        threat_details = []
        scanned_files = 0
        scanned_dirs = 0
        infected_count = 0

        # Parse stdout line by line
        for line in stdout.splitlines():
            line = line.strip()

            # Look for infected file lines (format: "/path/to/file: Virus.Name FOUND")
            if line.endswith("FOUND"):
                # Extract file path and threat name
                # Format: "/path/to/file: ThreatName FOUND"
                parts = line.rsplit(":", 1)
                if len(parts) == 2:
                    file_path = parts[0].strip()
                    # Extract threat name (remove " FOUND" suffix)
                    threat_part = parts[1].strip()
                    threat_name = (
                        threat_part.rsplit(" ", 1)[0].strip()
                        if " FOUND" in threat_part
                        else threat_part
                    )

                    infected_files.append(file_path)

                    # Create ThreatDetail with classification
                    threat_detail = ThreatDetail(
                        file_path=file_path,
                        threat_name=threat_name,
                        category=categorize_threat(threat_name),
                        severity=classify_threat_severity_str(threat_name),
                    )
                    threat_details.append(threat_detail)
                    infected_count += 1

            # Look for individual summary lines from ClamAV output
            # Format: "Scanned files: 10" or "Scanned directories: 1" or "Infected files: 0"
            elif line.startswith("Scanned files:"):
                match = re.search(r"Scanned files:\s*(\d+)", line)
                if match:
                    scanned_files = int(match.group(1))
            elif line.startswith("Scanned directories:"):
                match = re.search(r"Scanned directories:\s*(\d+)", line)
                if match:
                    scanned_dirs = int(match.group(1))

        # Determine overall status based on exit code
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

    def _save_scan_log(self, result: ScanResult, duration: float) -> None:
        """
        Save scan result to log.

        Args:
            result: The scan result
            duration: Scan duration in seconds
        """
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
            scheduled=False,
        )
        self._log_manager.save_log(entry)
