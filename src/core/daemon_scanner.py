# ClamUI Daemon Scanner Module
"""
Daemon scanner module for ClamUI using clamdscan for clamd communication.
Provides faster scanning by leveraging the ClamAV daemon's in-memory database.
"""

import fnmatch
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from gi.repository import GLib

from .log_manager import LogEntry, LogManager
from .settings_manager import SettingsManager
from .scanner import ScanResult, ScanStatus, ThreatDetail, glob_to_regex
from .utils import (
    check_clamdscan_installed,
    check_clamd_connection,
    validate_path,
    wrap_host_command,
    which_host_command,
)


class DaemonScanner:
    """
    ClamAV daemon scanner using clamdscan.

    Provides faster scanning by communicating with the clamd daemon,
    which keeps the virus database loaded in memory.
    """

    def __init__(
        self,
        log_manager: Optional[LogManager] = None,
        settings_manager: Optional[SettingsManager] = None
    ):
        """
        Initialize the daemon scanner.

        Args:
            log_manager: Optional LogManager instance for saving scan logs.
            settings_manager: Optional SettingsManager instance for reading
                              exclusion patterns and daemon settings.
        """
        self._current_process: Optional[subprocess.Popen] = None
        self._scan_cancelled = False
        self._log_manager = log_manager if log_manager else LogManager()
        self._settings_manager = settings_manager

    def check_available(self) -> tuple[bool, Optional[str]]:
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
        self,
        path: str,
        recursive: bool = True,
        profile_exclusions: dict | None = None
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
                threat_details=[]
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
                threat_details=[]
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

        # Build clamdscan command
        cmd = self._build_command(path, recursive, profile_exclusions)

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
                    error_message="Scan cancelled by user",
                    threat_details=[]
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
                stderr="clamdscan executable not found",
                exit_code=-1,
                infected_files=[],
                scanned_files=0,
                scanned_dirs=0,
                infected_count=0,
                error_message="clamdscan executable not found",
                threat_details=[]
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
                threat_details=[]
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
                threat_details=[]
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

    def scan_async(
        self,
        path: str,
        callback: Callable[[ScanResult], None],
        recursive: bool = True,
        profile_exclusions: dict | None = None
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
        Cancel the current scan operation.

        If a scan is in progress, it will be terminated.
        """
        self._scan_cancelled = True
        if self._current_process is not None:
            try:
                self._current_process.terminate()
            except (OSError, ProcessLookupError):
                pass

    def _build_command(
        self,
        path: str,
        recursive: bool,
        profile_exclusions: dict | None = None
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

        # Use multiscan for parallel scanning (daemon handles threads)
        cmd.append("--multiscan")

        # Use file descriptor passing for better performance
        cmd.append("--fdpass")

        # Show infected files only
        cmd.append("-i")

        # Note: clamdscan exclusions work differently than clamscan
        # It uses --exclude and --exclude-dir with regex patterns
        if self._settings_manager is not None:
            exclusions = self._settings_manager.get('exclusion_patterns', [])
            for exclusion in exclusions:
                if not exclusion.get('enabled', True):
                    continue

                pattern = exclusion.get('pattern', '')
                if not pattern:
                    continue

                regex = glob_to_regex(pattern)
                exclusion_type = exclusion.get('type', 'pattern')

                if exclusion_type == 'directory':
                    cmd.extend(['--exclude-dir', regex])
                else:
                    cmd.extend(['--exclude', regex])

        # Apply profile exclusions
        if profile_exclusions:
            for excl_path in profile_exclusions.get('paths', []):
                if not excl_path:
                    continue
                if excl_path.startswith('~'):
                    excl_path = str(Path(excl_path).expanduser())
                cmd.extend(['--exclude-dir', excl_path])

            for pattern in profile_exclusions.get('patterns', []):
                if not pattern:
                    continue
                regex = glob_to_regex(pattern)
                cmd.extend(['--exclude', regex])

        cmd.append(path)
        return wrap_host_command(cmd)

    def _classify_threat_severity(self, threat_name: str) -> str:
        """Classify threat severity level."""
        if not threat_name:
            return "medium"

        name_lower = threat_name.lower()

        critical_patterns = ['ransom', 'rootkit', 'bootkit', 'cryptolocker', 'wannacry']
        for pattern in critical_patterns:
            if pattern in name_lower:
                return "critical"

        high_patterns = ['trojan', 'worm', 'backdoor', 'exploit', 'downloader', 'dropper', 'keylogger']
        for pattern in high_patterns:
            if pattern in name_lower:
                return "high"

        medium_patterns = ['adware', 'pua', 'pup', 'spyware', 'miner', 'coinminer']
        for pattern in medium_patterns:
            if pattern in name_lower:
                return "medium"

        low_patterns = ['eicar', 'test-signature', 'test.file', 'heuristic', 'generic']
        for pattern in low_patterns:
            if pattern in name_lower:
                return "low"

        return "medium"

    def _categorize_threat(self, threat_name: str) -> str:
        """Extract threat category from name."""
        if not threat_name:
            return "Unknown"

        name_lower = threat_name.lower()

        category_patterns = [
            ('ransomware', 'Ransomware'),
            ('ransom', 'Ransomware'),
            ('rootkit', 'Rootkit'),
            ('bootkit', 'Rootkit'),
            ('trojan', 'Trojan'),
            ('worm', 'Worm'),
            ('backdoor', 'Backdoor'),
            ('exploit', 'Exploit'),
            ('adware', 'Adware'),
            ('spyware', 'Spyware'),
            ('keylogger', 'Spyware'),
            ('pua', 'PUA'),
            ('pup', 'PUA'),
            ('eicar', 'Test'),
            ('test-signature', 'Test'),
            ('test.file', 'Test'),
            ('virus', 'Virus'),
            ('macro', 'Macro'),
            ('phish', 'Phishing'),
            ('heuristic', 'Heuristic'),
        ]

        for pattern, category in category_patterns:
            if pattern in name_lower:
                return category

        return "Virus"

    def _parse_results(
        self,
        path: str,
        stdout: str,
        stderr: str,
        exit_code: int
    ) -> ScanResult:
        """
        Parse clamdscan output into a ScanResult.

        clamdscan output format is similar to clamscan.
        Exit codes: 0=clean, 1=infected, 2=error

        Args:
            path: The scanned path
            stdout: Standard output from clamdscan
            stderr: Standard error from clamdscan
            exit_code: Process exit code

        Returns:
            Parsed ScanResult
        """
        infected_files = []
        threat_details = []
        scanned_files = 0
        scanned_dirs = 0
        infected_count = 0

        for line in stdout.splitlines():
            line = line.strip()

            if line.endswith("FOUND"):
                parts = line.rsplit(":", 1)
                if len(parts) == 2:
                    file_path = parts[0].strip()
                    threat_part = parts[1].strip()
                    threat_name = threat_part.rsplit(" ", 1)[0].strip() if " FOUND" in threat_part else threat_part

                    infected_files.append(file_path)

                    threat_detail = ThreatDetail(
                        file_path=file_path,
                        threat_name=threat_name,
                        category=self._categorize_threat(threat_name),
                        severity=self._classify_threat_severity(threat_name)
                    )
                    threat_details.append(threat_detail)
                    infected_count += 1

            elif line.startswith("Scanned files:"):
                match = re.search(r"Scanned files:\s*(\d+)", line)
                if match:
                    scanned_files = int(match.group(1))
            elif line.startswith("Scanned directories:"):
                match = re.search(r"Scanned directories:\s*(\d+)", line)
                if match:
                    scanned_dirs = int(match.group(1))

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
            threat_details=threat_details
        )

    def _save_scan_log(self, result: ScanResult, duration: float) -> None:
        """Save scan result to log."""
        if result.status == ScanStatus.CLEAN:
            summary = f"Clean scan of {result.path} (daemon)"
            status = "clean"
        elif result.status == ScanStatus.INFECTED:
            summary = f"Found {result.infected_count} threat(s) in {result.path} (daemon)"
            status = "infected"
        elif result.status == ScanStatus.CANCELLED:
            summary = f"Scan cancelled: {result.path}"
            status = "cancelled"
        else:
            summary = f"Scan error: {result.path}"
            status = "error"

        details_parts = []
        if result.scanned_files > 0:
            details_parts.append(f"Scanned: {result.scanned_files} files, {result.scanned_dirs} directories")
        if result.infected_count > 0:
            details_parts.append(f"Threats found: {result.infected_count}")
            for threat in result.threat_details:
                details_parts.append(f"  - {threat.file_path}: {threat.threat_name}")
        if result.error_message:
            details_parts.append(f"Error: {result.error_message}")
        details = "\n".join(details_parts) if details_parts else result.stdout or ""

        entry = LogEntry.create(
            log_type="scan",
            status=status,
            summary=summary,
            details=details,
            path=result.path,
            duration=duration,
            scheduled=False
        )
        self._log_manager.save_log(entry)
