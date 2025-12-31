# ClamUI Scanner Module
"""
Scanner module for ClamUI providing ClamAV subprocess execution and async scanning.
"""

import fnmatch
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from gi.repository import GLib

from .log_manager import LogEntry, LogManager
from .settings_manager import SettingsManager
from .utils import check_clamav_installed, validate_path, get_clamav_path, wrap_host_command


def glob_to_regex(pattern: str) -> str:
    """
    Convert a user-friendly glob pattern to POSIX ERE for ClamAV.

    Uses fnmatch.translate() for conversion and strips Python-specific
    regex suffixes for ClamAV compatibility.

    Note: fnmatch doesn't support '**' recursive wildcards - document as limitation.

    Args:
        pattern: Glob pattern (e.g., '*.log', 'node_modules', '/tmp/*')

    Returns:
        POSIX Extended Regular Expression string
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
    CLEAN = "clean"           # No threats found (exit code 0)
    INFECTED = "infected"     # Threats found (exit code 1)
    ERROR = "error"           # Error occurred (exit code 2 or exception)
    CANCELLED = "cancelled"   # Scan was cancelled


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
    error_message: Optional[str]
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

    Provides methods for running clamscan in a background thread
    while safely updating the UI via GLib.idle_add.
    """

    def __init__(
        self,
        log_manager: Optional[LogManager] = None,
        settings_manager: Optional[SettingsManager] = None
    ):
        """
        Initialize the scanner.

        Args:
            log_manager: Optional LogManager instance for saving scan logs.
                         If not provided, a default instance is created.
            settings_manager: Optional SettingsManager instance for reading
                              exclusion patterns. If not provided, exclusions
                              will not be applied to scans.
        """
        self._current_process: Optional[subprocess.Popen] = None
        self._scan_cancelled = False
        self._log_manager = log_manager if log_manager else LogManager()
        self._settings_manager = settings_manager

    def check_available(self) -> tuple[bool, Optional[str]]:
        """
        Check if ClamAV is available for scanning.

        Returns:
            Tuple of (is_available, version_or_error)
        """
        return check_clamav_installed()

    def scan_sync(
        self,
        path: str,
        recursive: bool = True,
        profile_exclusions: dict | None = None
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
                threat_details=[]
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
                error_message=version_or_error,
                threat_details=[]
            )
            duration = time.monotonic() - start_time
            self._save_scan_log(result, duration)
            return result

        # Build clamscan command
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
                stderr="ClamAV executable not found",
                exit_code=-1,
                infected_files=[],
                scanned_files=0,
                scanned_dirs=0,
                infected_count=0,
                error_message="ClamAV executable not found",
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
                else:  # file or pattern
                    cmd.extend(['--exclude', regex])

        # Apply profile exclusions (paths and patterns)
        if profile_exclusions:
            # Handle path exclusions (directories)
            for excl_path in profile_exclusions.get('paths', []):
                if not excl_path:
                    continue
                # Expand ~ in exclusion paths
                if excl_path.startswith('~'):
                    excl_path = str(Path(excl_path).expanduser())
                # Use the path directly for --exclude-dir (ClamAV accepts paths)
                cmd.extend(['--exclude-dir', excl_path])

            # Handle pattern exclusions (file patterns like *.tmp)
            for pattern in profile_exclusions.get('patterns', []):
                if not pattern:
                    continue
                # Convert glob pattern to regex for ClamAV
                regex = glob_to_regex(pattern)
                cmd.extend(['--exclude', regex])

        # Add the path to scan
        cmd.append(path)

        # Wrap with flatpak-spawn if running inside Flatpak sandbox
        return wrap_host_command(cmd)

    def _classify_threat_severity(self, threat_name: str) -> str:
        """
        Classify the severity level of a threat based on its name.

        Severity levels:
        - critical: Ransomware, Rootkit, Bootkit
        - high: Trojan, Worm, Backdoor, Exploit
        - medium: Adware, PUA (Potentially Unwanted Application), Spyware, Unknown
        - low: Test signatures (EICAR), Generic/Heuristic detections (when standalone)

        Args:
            threat_name: The threat name from ClamAV output

        Returns:
            Severity level as string: 'critical', 'high', 'medium', or 'low'
        """
        if not threat_name:
            return "medium"

        name_lower = threat_name.lower()

        # Critical: Most dangerous threats
        critical_patterns = ['ransom', 'rootkit', 'bootkit', 'cryptolocker', 'wannacry']
        for pattern in critical_patterns:
            if pattern in name_lower:
                return "critical"

        # High: Serious threats
        high_patterns = ['trojan', 'worm', 'backdoor', 'exploit', 'downloader', 'dropper', 'keylogger']
        for pattern in high_patterns:
            if pattern in name_lower:
                return "high"

        # Medium: Less severe but still concerning
        medium_patterns = ['adware', 'pua', 'pup', 'spyware', 'miner', 'coinminer']
        for pattern in medium_patterns:
            if pattern in name_lower:
                return "medium"

        # Low: Test files and generic/heuristic detections
        low_patterns = ['eicar', 'test-signature', 'test.file', 'heuristic', 'generic']
        for pattern in low_patterns:
            if pattern in name_lower:
                return "low"

        # Default to medium for unknown threats
        return "medium"

    def _categorize_threat(self, threat_name: str) -> str:
        """
        Extract the category of a threat from its name.

        ClamAV threat names typically follow patterns like:
        - "Win.Trojan.Agent" -> "Trojan"
        - "Eicar-Test-Signature" -> "Test"
        - "PUA.Win.Adware.Generic" -> "Adware"

        Args:
            threat_name: The threat name from ClamAV output

        Returns:
            Category as string (e.g., 'Virus', 'Trojan', 'Worm', etc.)
        """
        if not threat_name:
            return "Unknown"

        name_lower = threat_name.lower()

        # Check for specific categories in order of specificity
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

        # Default to "Virus" for unrecognized threats (conservative assumption)
        return "Virus"

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
                    threat_name = threat_part.rsplit(" ", 1)[0].strip() if " FOUND" in threat_part else threat_part

                    infected_files.append(file_path)

                    # Create ThreatDetail with classification
                    threat_detail = ThreatDetail(
                        file_path=file_path,
                        threat_name=threat_name,
                        category=self._categorize_threat(threat_name),
                        severity=self._classify_threat_severity(threat_name)
                    )
                    threat_details.append(threat_detail)
                    infected_count += 1

            # Look for summary line (format: "Scanned: X files, Y directories, Z infected files")
            elif line.startswith("Scanned:"):
                # Parse: "Scanned: 1234 files, 56 directories, 2 infected files"
                # Use regex to extract numbers
                match = re.search(r"Scanned:\s+(\d+)\s+files,\s+(\d+)\s+directories,\s+(\d+)\s+infected", line)
                if match:
                    scanned_files = int(match.group(1))
                    scanned_dirs = int(match.group(2))
                    # The infected count from summary should match what we counted
                    # but we use our manual count to be consistent

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
            threat_details=threat_details
        )

    def _save_scan_log(self, result: ScanResult, duration: float) -> None:
        """
        Save scan result to log.

        Args:
            result: The scan result
            duration: Scan duration in seconds
        """
        entry = LogEntry(
            scan_path=result.path,
            scan_status=result.status.value,
            threats_detected=result.infected_count,
            scan_duration=duration,
            timestamp=None
        )
        self._log_manager.add_entry(entry)