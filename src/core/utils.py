# ClamUI Utility Functions
"""
Utility functions for ClamUI including ClamAV detection and path validation.
"""

import csv
import io
import os
import shutil
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Tuple, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .scanner import ScanResult


class ThreatSeverity(Enum):
    """Severity level of a detected threat."""
    CRITICAL = "critical"     # Ransomware, Rootkit, Bootkit
    HIGH = "high"             # Trojan, Worm, Backdoor, Exploit
    MEDIUM = "medium"         # Adware, PUA, Spyware, Unknown
    LOW = "low"               # Test signatures (EICAR), Generic detections


# Flatpak detection cache (None = not checked, True/False = result)
_flatpak_detected: Optional[bool] = None


def is_flatpak() -> bool:
    """
    Detect if running inside a Flatpak sandbox.

    Uses the presence of /.flatpak-info file as the detection method,
    which is the standard way to detect Flatpak environment.

    The result is cached after the first check for performance.

    Returns:
        True if running inside Flatpak sandbox, False otherwise
    """
    global _flatpak_detected

    if _flatpak_detected is None:
        _flatpak_detected = os.path.exists('/.flatpak-info')

    return _flatpak_detected


def wrap_host_command(command: List[str]) -> List[str]:
    """
    Wrap a command with flatpak-spawn --host if running inside Flatpak.

    When running inside a Flatpak sandbox, commands that need to execute
    on the host system (like ClamAV binaries) must be prefixed with
    'flatpak-spawn --host' to bridge the sandbox boundary.

    Args:
        command: The command to wrap as a list of strings
                 (e.g., ['clamscan', '--version'])

    Returns:
        The original command if not in Flatpak, or the command prefixed
        with ['flatpak-spawn', '--host'] if running in Flatpak sandbox

    Example:
        >>> wrap_host_command(['clamscan', '--version'])
        ['clamscan', '--version']  # When not in Flatpak

        >>> wrap_host_command(['clamscan', '--version'])
        ['flatpak-spawn', '--host', 'clamscan', '--version']  # When in Flatpak
    """
    if not command:
        return command

    if is_flatpak():
        return ['flatpak-spawn', '--host'] + list(command)

    return list(command)


def which_host_command(binary: str) -> Optional[str]:
    """
    Find binary path, checking host system if running in Flatpak.

    When running inside a Flatpak sandbox, shutil.which() only searches
    the sandbox's PATH. This function uses 'flatpak-spawn --host which'
    to check the host system's PATH instead.

    Args:
        binary: The name of the binary to find (e.g., 'clamscan')

    Returns:
        The full path to the binary if found, None otherwise
    """
    if is_flatpak():
        try:
            result = subprocess.run(
                ['flatpak-spawn', '--host', 'which', binary],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
    return shutil.which(binary)


def check_clamav_installed() -> Tuple[bool, Optional[str]]:
    """
    Check if ClamAV (clamscan) is installed and accessible.

    Returns:
        Tuple of (is_installed, version_or_error):
        - (True, version_string) if ClamAV is installed
        - (False, error_message) if ClamAV is not found or inaccessible
    """
    # First check if clamscan exists in PATH (checking host if in Flatpak)
    clamscan_path = which_host_command("clamscan")

    if clamscan_path is None:
        return (False, "ClamAV is not installed. Please install it with: sudo apt install clamav")

    # Try to get version to verify it's working
    try:
        result = subprocess.run(
            wrap_host_command(["clamscan", "--version"]),
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            return (True, version)
        else:
            return (False, f"ClamAV found but returned error: {result.stderr.strip()}")

    except subprocess.TimeoutExpired:
        return (False, "ClamAV check timed out")
    except FileNotFoundError:
        return (False, "ClamAV executable not found")
    except PermissionError:
        return (False, "Permission denied when accessing ClamAV")
    except Exception as e:
        return (False, f"Error checking ClamAV: {str(e)}")


def check_freshclam_installed() -> Tuple[bool, Optional[str]]:
    """
    Check if freshclam (ClamAV database updater) is installed and accessible.

    Returns:
        Tuple of (is_installed, version_or_error):
        - (True, version_string) if freshclam is installed
        - (False, error_message) if freshclam is not found or inaccessible
    """
    # First check if freshclam exists in PATH (checking host if in Flatpak)
    freshclam_path = which_host_command("freshclam")

    if freshclam_path is None:
        return (False, "freshclam is not installed. Please install it with: sudo apt install clamav-freshclam")

    # Try to get version to verify it's working
    try:
        result = subprocess.run(
            wrap_host_command(["freshclam", "--version"]),
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            return (True, version)
        else:
            return (False, f"freshclam found but returned error: {result.stderr.strip()}")

    except subprocess.TimeoutExpired:
        return (False, "freshclam check timed out")
    except FileNotFoundError:
        return (False, "freshclam executable not found")
    except PermissionError:
        return (False, "Permission denied when accessing freshclam")
    except Exception as e:
        return (False, f"Error checking freshclam: {str(e)}")


def check_clamdscan_installed() -> Tuple[bool, Optional[str]]:
    """
    Check if clamdscan (ClamAV daemon scanner) is installed and accessible.

    Returns:
        Tuple of (is_installed, version_or_error):
        - (True, version_string) if clamdscan is installed
        - (False, error_message) if clamdscan is not found or inaccessible
    """
    # First check if clamdscan exists in PATH (checking host if in Flatpak)
    clamdscan_path = which_host_command("clamdscan")

    if clamdscan_path is None:
        return (False, "clamdscan is not installed. Please install it with: sudo apt install clamav-daemon")

    # Try to get version to verify it's working
    try:
        result = subprocess.run(
            wrap_host_command(["clamdscan", "--version"]),
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            return (True, version)
        else:
            return (False, f"clamdscan found but returned error: {result.stderr.strip()}")

    except subprocess.TimeoutExpired:
        return (False, "clamdscan check timed out")
    except FileNotFoundError:
        return (False, "clamdscan executable not found")
    except PermissionError:
        return (False, "Permission denied when accessing clamdscan")
    except Exception as e:
        return (False, f"Error checking clamdscan: {str(e)}")


def validate_path(path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a path for scanning.

    Checks that the path:
    - Is not empty
    - Exists on the filesystem
    - Is readable by the current user

    Args:
        path: The filesystem path to validate

    Returns:
        Tuple of (is_valid, error_message):
        - (True, None) if path is valid for scanning
        - (False, error_message) if path is invalid
    """
    # Check for empty path
    if not path or not path.strip():
        return (False, "No path specified")

    # Normalize and resolve the path
    try:
        resolved_path = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        return (False, f"Invalid path format: {str(e)}")

    # Check if path exists
    if not resolved_path.exists():
        return (False, f"Path does not exist: {path}")

    # Check if path is readable
    if not os.access(resolved_path, os.R_OK):
        return (False, f"Permission denied: Cannot read {path}")

    # For directories, check if we can list contents
    if resolved_path.is_dir():
        try:
            # Try to list directory contents to verify access
            next(resolved_path.iterdir(), None)
        except PermissionError:
            return (False, f"Permission denied: Cannot access directory contents of {path}")
        except OSError as e:
            return (False, f"Error accessing directory: {str(e)}")

    return (True, None)


def validate_dropped_files(paths: List[Optional[str]]) -> Tuple[List[str], List[str]]:
    """
    Validate a batch of paths from dropped files (typically from Gio.File.get_path()).

    Handles:
    - None paths (remote files where Gio.File.get_path() returns None)
    - Non-existent paths
    - Permission errors
    - Empty path lists

    Args:
        paths: List of filesystem paths to validate. May contain None values
               for remote files that cannot be accessed locally.

    Returns:
        Tuple of (valid_paths, errors):
        - valid_paths: List of validated, resolved path strings ready for scanning
        - errors: List of error messages for invalid paths
    """
    valid_paths: List[str] = []
    errors: List[str] = []

    if not paths:
        errors.append("No files were dropped")
        return (valid_paths, errors)

    for path in paths:
        # Handle None paths (remote files)
        if path is None:
            errors.append("Remote files cannot be scanned locally")
            continue

        # Use existing validate_path for individual validation
        is_valid, error = validate_path(path)

        if is_valid:
            # Resolve path for consistent handling
            try:
                resolved = str(Path(path).resolve())
                valid_paths.append(resolved)
            except (OSError, RuntimeError) as e:
                errors.append(f"Error resolving path: {str(e)}")
        else:
            if error:
                errors.append(error)

    return (valid_paths, errors)


def get_clamav_path() -> Optional[str]:
    """
    Get the full path to the clamscan executable.

    Returns:
        The full path to clamscan if found, None otherwise
    """
    return which_host_command("clamscan")


def get_freshclam_path() -> Optional[str]:
    """
    Get the full path to the freshclam executable.

    Returns:
        The full path to freshclam if found, None otherwise
    """
    return which_host_command("freshclam")


def format_scan_path(path: str) -> str:
    """
    Format a path for display in the UI.

    Shortens long paths for better readability while keeping them identifiable.

    Args:
        path: The filesystem path to format

    Returns:
        A formatted string suitable for UI display
    """
    if not path:
        return "No path selected"

    try:
        resolved = Path(path).resolve()

        # For home directory paths, use ~ notation
        try:
            home = Path.home()
            if resolved.is_relative_to(home):
                return "~/" + str(resolved.relative_to(home))
        except (ValueError, RuntimeError):
            pass

        return str(resolved)
    except (OSError, RuntimeError):
        return path


def categorize_threat(threat_name: str) -> str:
    """
    Extract the category of a threat from its name.

    ClamAV threat names typically follow patterns that indicate the threat type.
    This function analyzes the threat name to extract a human-readable category.

    Categories returned:
    - Ransomware: Ransomware, CryptoLocker variants
    - Rootkit: Rootkits and bootkits
    - Trojan: Trojan horse malware
    - Worm: Self-replicating worms
    - Backdoor: Backdoor access tools
    - Exploit: Vulnerability exploits
    - Adware: Advertising software
    - Spyware: Spyware and keyloggers
    - PUA: Potentially Unwanted Applications
    - Test: Test signatures (EICAR)
    - Virus: Generic viruses
    - Macro: Macro viruses
    - Phishing: Phishing attempts
    - Heuristic: Heuristic detections
    - Unknown: Cannot determine category

    Args:
        threat_name: The threat name from ClamAV output (e.g., "Win.Trojan.Agent")

    Returns:
        Category as string (e.g., 'Virus', 'Trojan', 'Worm', etc.)

    Example:
        >>> categorize_threat("Win.Trojan.Agent")
        'Trojan'

        >>> categorize_threat("Eicar-Test-Signature")
        'Test'
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


def classify_threat_severity(threat_name: str) -> ThreatSeverity:
    """
    Classify the severity level of a threat based on its name.

    ClamAV threat names typically follow patterns that indicate the threat type.
    This function analyzes the threat name to determine the severity level.

    Severity levels:
    - CRITICAL: Ransomware, Rootkit, Bootkit (most dangerous, can cause data loss or system compromise)
    - HIGH: Trojan, Worm, Backdoor, Exploit (serious threats requiring immediate attention)
    - MEDIUM: Adware, PUA, Spyware (less severe but still concerning)
    - LOW: Test signatures (EICAR), Generic/Heuristic detections

    Args:
        threat_name: The threat name from ClamAV output (e.g., "Win.Trojan.Agent")

    Returns:
        ThreatSeverity enum value

    Example:
        >>> classify_threat_severity("Win.Ransomware.Locky")
        ThreatSeverity.CRITICAL

        >>> classify_threat_severity("Eicar-Test-Signature")
        ThreatSeverity.LOW
    """
    if not threat_name:
        return ThreatSeverity.MEDIUM

    name_lower = threat_name.lower()

    # Critical: Most dangerous threats - ransomware, rootkits, bootkits
    critical_patterns = ['ransom', 'rootkit', 'bootkit', 'cryptolocker', 'wannacry']
    for pattern in critical_patterns:
        if pattern in name_lower:
            return ThreatSeverity.CRITICAL

    # High: Serious threats requiring immediate attention
    high_patterns = ['trojan', 'worm', 'backdoor', 'exploit', 'downloader', 'dropper', 'keylogger']
    for pattern in high_patterns:
        if pattern in name_lower:
            return ThreatSeverity.HIGH

    # Medium: Less severe but still concerning threats
    medium_patterns = ['adware', 'pua', 'pup', 'spyware', 'miner', 'coinminer']
    for pattern in medium_patterns:
        if pattern in name_lower:
            return ThreatSeverity.MEDIUM

    # Low: Test files and generic/heuristic detections
    low_patterns = ['eicar', 'test-signature', 'test.file', 'heuristic', 'generic']
    for pattern in low_patterns:
        if pattern in name_lower:
            return ThreatSeverity.LOW

    # Default to medium for unknown threats
    return ThreatSeverity.MEDIUM


def get_path_info(path: str) -> dict:
    """
    Get information about a path for scanning.

    Args:
        path: The filesystem path to analyze

    Returns:
        Dictionary with path information:
        - 'type': 'file', 'directory', or 'unknown'
        - 'exists': boolean
        - 'readable': boolean
        - 'size': size in bytes (for files) or None
        - 'display_path': formatted path for display
    """
    info = {
        'type': 'unknown',
        'exists': False,
        'readable': False,
        'size': None,
        'display_path': format_scan_path(path)
    }

    if not path:
        return info

    try:
        resolved = Path(path).resolve()
        info['exists'] = resolved.exists()

        if not info['exists']:
            return info

        if resolved.is_file():
            info['type'] = 'file'
            try:
                info['size'] = resolved.stat().st_size
            except OSError:
                pass
        elif resolved.is_dir():
            info['type'] = 'directory'

        info['readable'] = os.access(resolved, os.R_OK)

    except (OSError, RuntimeError):
        pass

    return info


def format_results_as_text(result: 'ScanResult', timestamp: Optional[str] = None) -> str:
    """
    Format scan results as human-readable text for export or clipboard.

    Creates a formatted text report including:
    - Header with scan timestamp and path
    - Summary statistics (files scanned, threats found)
    - Detailed threat list with file path, threat name, category, and severity
    - Status indicator

    Args:
        result: The ScanResult object to format
        timestamp: Optional timestamp string. If not provided, uses current time.

    Returns:
        Formatted text string suitable for export to file or clipboard

    Example output:
        ═══════════════════════════════════════════════════════════════
        ClamUI Scan Report
        ═══════════════════════════════════════════════════════════════
        Scan Date: 2024-01-15 14:30:45
        Scanned Path: /home/user/Downloads
        Status: INFECTED

        ───────────────────────────────────────────────────────────────
        Summary
        ───────────────────────────────────────────────────────────────
        Files Scanned: 150
        Directories Scanned: 25
        Threats Found: 2

        ───────────────────────────────────────────────────────────────
        Detected Threats
        ───────────────────────────────────────────────────────────────

        [1] CRITICAL - Ransomware
            File: /home/user/Downloads/malware.exe
            Threat: Win.Ransomware.Locky

        [2] HIGH - Trojan
            File: /home/user/Downloads/suspicious.doc
            Threat: Win.Trojan.Agent

        ═══════════════════════════════════════════════════════════════
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []

    # Header
    header_line = "═" * 65
    sub_header_line = "─" * 65

    lines.append(header_line)
    lines.append("ClamUI Scan Report")
    lines.append(header_line)
    lines.append(f"Scan Date: {timestamp}")
    lines.append(f"Scanned Path: {result.path}")
    lines.append(f"Status: {result.status.value.upper()}")
    lines.append("")

    # Summary section
    lines.append(sub_header_line)
    lines.append("Summary")
    lines.append(sub_header_line)
    lines.append(f"Files Scanned: {result.scanned_files}")
    lines.append(f"Directories Scanned: {result.scanned_dirs}")
    lines.append(f"Threats Found: {result.infected_count}")
    lines.append("")

    # Threat details section
    if result.threat_details:
        lines.append(sub_header_line)
        lines.append("Detected Threats")
        lines.append(sub_header_line)
        lines.append("")

        for i, threat in enumerate(result.threat_details, 1):
            severity_upper = threat.severity.upper()
            lines.append(f"[{i}] {severity_upper} - {threat.category}")
            lines.append(f"    File: {threat.file_path}")
            lines.append(f"    Threat: {threat.threat_name}")
            lines.append("")
    elif result.status.value == "clean":
        lines.append(sub_header_line)
        lines.append("No Threats Detected")
        lines.append(sub_header_line)
        lines.append("")
        lines.append("✓ All scanned files are clean.")
        lines.append("")
    elif result.status.value == "error":
        lines.append(sub_header_line)
        lines.append("Scan Error")
        lines.append(sub_header_line)
        lines.append("")
        if result.error_message:
            lines.append(f"Error: {result.error_message}")
        lines.append("")
    elif result.status.value == "cancelled":
        lines.append(sub_header_line)
        lines.append("Scan Cancelled")
        lines.append(sub_header_line)
        lines.append("")
        lines.append("The scan was cancelled before completion.")
        lines.append("")

    # Footer
    lines.append(header_line)

    return "\n".join(lines)


def format_results_as_csv(result: 'ScanResult', timestamp: Optional[str] = None) -> str:
    """
    Format scan results as CSV for export to spreadsheet applications.

    Creates a CSV formatted string with the following columns:
    - File Path: The path to the infected file
    - Threat Name: The name of the detected threat from ClamAV
    - Category: The threat category (Ransomware, Trojan, etc.)
    - Severity: The severity level (critical, high, medium, low)
    - Timestamp: When the scan was performed

    Uses Python's csv module for proper escaping of special characters
    (commas, quotes, newlines) in file paths and threat names.

    Args:
        result: The ScanResult object to format
        timestamp: Optional timestamp string. If not provided, uses current time.

    Returns:
        CSV formatted string suitable for export to .csv file

    Example output:
        File Path,Threat Name,Category,Severity,Timestamp
        /home/user/malware.exe,Win.Ransomware.Locky,Ransomware,critical,2024-01-15 14:30:45
        /home/user/suspicious.doc,Win.Trojan.Agent,Trojan,high,2024-01-15 14:30:45
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Use StringIO to write CSV to a string
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Write header row
    writer.writerow(["File Path", "Threat Name", "Category", "Severity", "Timestamp"])

    # Write threat details
    if result.threat_details:
        for threat in result.threat_details:
            writer.writerow([
                threat.file_path,
                threat.threat_name,
                threat.category,
                threat.severity,
                timestamp
            ])

    return output.getvalue()