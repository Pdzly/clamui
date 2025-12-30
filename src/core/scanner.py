# ClamUI Scanner Module
"""
Scanner module for ClamUI providing ClamAV subprocess execution and async scanning.
"""

import subprocess
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from gi.repository import GLib

from .log_manager import LogEntry, LogManager
from .utils import check_clamav_installed, validate_path, get_clamav_path, wrap_host_command


class ScanStatus(Enum):
    """Status of a scan operation."""
    CLEAN = "clean"           # No threats found (exit code 0)
    INFECTED = "infected"     # Threats found (exit code 1)
    ERROR = "error"           # Error occurred (exit code 2 or exception)
    CANCELLED = "cancelled"   # Scan was cancelled


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
    error_message: Optional[str]

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

    Provides methods for running clamscan in a background thread
    while safely updating the UI via GLib.idle_add.
    """

    def __init__(self, log_manager: Optional[LogManager] = None):
        """
        Initialize the scanner.

        Args:
            log_manager: Optional LogManager instance for saving scan logs.
                         If not provided, a default instance is created.
        """
        self._current_process: Optional[subprocess.Popen] = None
        self._scan_cancelled = False
        self._log_manager = log_manager if log_manager else LogManager()

    def check_available(self) -> tuple[bool, Optional[str]]:
        """
        Check if ClamAV is available for scanning.

        Returns:
            Tuple of (is_available, version_or_error)
        """
        return check_clamav_installed()

    def scan_sync(self, path: str, recursive: bool = True) -> ScanResult:
        """
        Execute a synchronous scan on the given path.

        WARNING: This will block the calling thread. For UI applications,
        use scan_async() instead.

        Args:
            path: Path to file or directory to scan
            recursive: Whether to scan directories recursively

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
                error_message=error
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

        # Check ClamAV is available
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
                error_message=version_or_error
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

        # Build clamscan command
        cmd = self._build_command(path, recursive)

        try:
            self._scan_cancelled = False
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = self._current_process.communicate()
            exit_code = self._current_process.returncode
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
                    error_message="Scan cancelled by user"
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
                error_message="ClamAV executable not found"
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
                error_message=f"Permission denied: {e}"
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
                error_message=f"Scan failed: {e}"
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

    def scan_async(
        self,
        path: str,
        callback: Callable[[ScanResult], None],
        recursive: bool = True
    ) -> None:
        """
        Execute an asynchronous scan on the given path.

        The scan runs in a background thread and the callback is invoked
        on the main GTK thread via GLib.idle_add when complete.

        Args:
            path: Path to file or directory to scan
            callback: Function to call with ScanResult when scan completes
            recursive: Whether to scan directories recursively
        """
        def scan_thread():
            result = self.scan_sync(path, recursive)
            # Schedule callback on main thread
            GLib.idle_add(callback, result)

        thread = threading.Thread(target=scan_thread)
        thread.daemon = True
        thread.start()

    def cancel(self) -> None:
        """
        Cancel the current scan operation.

        If a scan is in progress, it will be terminated.
        """
        self._scan_cancelled = True
        if self._current_process is not None:
            try:
                self._current_process.terminate()
            except (OSError, ProcessLookupError):
                pass

    def _build_command(self, path: str, recursive: bool) -> list[str]:
        """
        Build the clamscan command arguments.

        When running inside a Flatpak sandbox, the command is automatically
        wrapped with 'flatpak-spawn --host' to execute ClamAV on the host system.

        Args:
            path: Path to scan
            recursive: Whether to scan recursively

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

        # Add the path to scan
        cmd.append(path)

        # Wrap with flatpak-spawn if running inside Flatpak sandbox
        return wrap_host_command(cmd)

    def _parse_results(
        self,
        path: str,
        stdout: str,
        stderr: str,
        exit_code: int
    ) -> ScanResult:
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
        scanned_files = 0
        scanned_dirs = 0
        infected_count = 0

        # Parse stdout line by line
        for line in stdout.splitlines():
            line = line.strip()

            # Look for infected file lines (format: "/path/to/file: Virus.Name FOUND")
            if line.endswith("FOUND"):
                # Extract the file path (everything before the colon)
                parts = line.rsplit(":", 1)
                if len(parts) >= 1:
                    infected_files.append(parts[0].strip())

            # Parse summary statistics
            if line.startswith("Scanned files:"):
                try:
                    scanned_files = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass
            elif line.startswith("Scanned directories:"):
                try:
                    scanned_dirs = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass
            elif line.startswith("Infected files:"):
                try:
                    infected_count = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass

        # Determine status from exit code
        if exit_code == 0:
            status = ScanStatus.CLEAN
            error_message = None
        elif exit_code == 1:
            status = ScanStatus.INFECTED
            error_message = None
        else:
            status = ScanStatus.ERROR
            error_message = stderr.strip() if stderr else "Scan error occurred"

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
            error_message=error_message
        )

    def _save_scan_log(self, result: ScanResult, duration: float) -> None:
        """
        Save a scan result to the log manager.

        Args:
            result: The ScanResult to log
            duration: Duration of the scan in seconds
        """
        # Build summary based on scan result
        if result.status == ScanStatus.CLEAN:
            summary = f"Scan completed - No threats found in {result.path}"
        elif result.status == ScanStatus.INFECTED:
            summary = f"Scan completed - {result.infected_count} threat(s) found in {result.path}"
        elif result.status == ScanStatus.CANCELLED:
            summary = f"Scan cancelled for {result.path}"
        else:
            summary = f"Scan failed for {result.path}: {result.error_message or 'Unknown error'}"

        # Build details combining stdout and stderr
        details_parts = []
        if result.stdout:
            details_parts.append(result.stdout)
        if result.stderr:
            details_parts.append(f"--- Errors ---\n{result.stderr}")
        details = "\n".join(details_parts) if details_parts else "(No output)"

        # Create and save log entry
        log_entry = LogEntry.create(
            log_type="scan",
            status=result.status.value,
            summary=summary,
            details=details,
            path=result.path,
            duration=duration
        )

        self._log_manager.save_log(log_entry)
