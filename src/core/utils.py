# ClamUI Utility Functions
"""
Utility functions for ClamUI including ClamAV detection and path validation.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Optional, List


def check_clamav_installed() -> Tuple[bool, Optional[str]]:
    """
    Check if ClamAV (clamscan) is installed and accessible.

    Returns:
        Tuple of (is_installed, version_or_error):
        - (True, version_string) if ClamAV is installed
        - (False, error_message) if ClamAV is not found or inaccessible
    """
    # First check if clamscan exists in PATH
    clamscan_path = shutil.which("clamscan")

    if clamscan_path is None:
        return (False, "ClamAV is not installed. Please install it with: sudo apt install clamav")

    # Try to get version to verify it's working
    try:
        result = subprocess.run(
            ["clamscan", "--version"],
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
    # First check if freshclam exists in PATH
    freshclam_path = shutil.which("freshclam")

    if freshclam_path is None:
        return (False, "freshclam is not installed. Please install it with: sudo apt install clamav-freshclam")

    # Try to get version to verify it's working
    try:
        result = subprocess.run(
            ["freshclam", "--version"],
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
    # First check if clamdscan exists in PATH
    clamdscan_path = shutil.which("clamdscan")

    if clamdscan_path is None:
        return (False, "clamdscan is not installed. Please install it with: sudo apt install clamav-daemon")

    # Try to get version to verify it's working
    try:
        result = subprocess.run(
            ["clamdscan", "--version"],
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
    return shutil.which("clamscan")


def get_freshclam_path() -> Optional[str]:
    """
    Get the full path to the freshclam executable.

    Returns:
        The full path to freshclam if found, None otherwise
    """
    return shutil.which("freshclam")


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
