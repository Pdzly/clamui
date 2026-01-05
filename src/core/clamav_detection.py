# ClamUI ClamAV Detection
"""
ClamAV installation detection and daemon connectivity utilities.

This module provides functions for:
- Checking if ClamAV binaries (clamscan, freshclam, clamdscan) are installed
- Getting paths to ClamAV executables
- Detecting clamd socket locations
- Testing clamd daemon connectivity
"""

import os
import subprocess

from .flatpak import is_flatpak, which_host_command, wrap_host_command


def check_clamav_installed() -> tuple[bool, str | None]:
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
            wrap_host_command(["clamscan", "--version"]), capture_output=True, text=True, timeout=10
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


def check_freshclam_installed() -> tuple[bool, str | None]:
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
        return (
            False,
            "freshclam is not installed. Please install it with: sudo apt install clamav-freshclam",
        )

    # Try to get version to verify it's working
    try:
        result = subprocess.run(
            wrap_host_command(["freshclam", "--version"]),
            capture_output=True,
            text=True,
            timeout=10,
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


def check_clamdscan_installed() -> tuple[bool, str | None]:
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
        return (
            False,
            "clamdscan is not installed. Please install it with: sudo apt install clamav-daemon",
        )

    # Try to get version to verify it's working
    try:
        result = subprocess.run(
            wrap_host_command(["clamdscan", "--version"]),
            capture_output=True,
            text=True,
            timeout=10,
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


def get_clamd_socket_path() -> str | None:
    """
    Get the clamd socket path by checking common locations.

    Checks the following paths in order:
    - /var/run/clamav/clamd.ctl (Ubuntu/Debian default)
    - /run/clamav/clamd.ctl (alternative location)
    - /var/run/clamd.scan/clamd.sock (Fedora)

    Returns:
        Socket path if found, None otherwise
    """
    socket_paths = [
        "/var/run/clamav/clamd.ctl",
        "/run/clamav/clamd.ctl",
        "/var/run/clamd.scan/clamd.sock",
    ]

    for path in socket_paths:
        if os.path.exists(path):
            return path

    return None


def check_clamd_connection(socket_path: str | None = None) -> tuple[bool, str | None]:
    """
    Check if clamd is accessible and responding.

    Uses 'clamdscan --ping' to test the connection to the daemon.

    Args:
        socket_path: Optional socket path. If not provided, uses auto-detection.

    Returns:
        Tuple of (is_connected, message):
        - (True, "PONG") if daemon is responding
        - (False, error_message) if daemon is not accessible
    """
    # First check if clamdscan is installed
    is_installed, error = check_clamdscan_installed()
    if not is_installed:
        return (False, error)

    # Check socket exists (if not in Flatpak)
    if not is_flatpak():
        detected_socket = socket_path or get_clamd_socket_path()
        if detected_socket is None:
            return (False, "Could not find clamd socket. Is clamav-daemon installed?")

    # Try to ping the daemon (--ping requires a timeout argument in seconds)
    try:
        cmd = wrap_host_command(["clamdscan", "--ping", "3"])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and "PONG" in result.stdout:
            return (True, "PONG")
        else:
            # Check stderr and stdout for error messages
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            return (False, f"Daemon not responding: {error_msg}")

    except subprocess.TimeoutExpired:
        return (False, "Connection to clamd timed out")
    except FileNotFoundError:
        return (False, "clamdscan executable not found")
    except Exception as e:
        return (False, f"Error connecting to clamd: {str(e)}")


def get_clamav_path() -> str | None:
    """
    Get the full path to the clamscan executable.

    Returns:
        The full path to clamscan if found, None otherwise
    """
    return which_host_command("clamscan")


def get_freshclam_path() -> str | None:
    """
    Get the full path to the freshclam executable.

    Returns:
        The full path to freshclam if found, None otherwise
    """
    return which_host_command("freshclam")
