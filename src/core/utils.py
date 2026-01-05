# ClamUI Utility Functions
"""
Utility functions for ClamUI including ClamAV detection and path validation.
"""

import contextlib
import csv
import io
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scanner import ScanResult

# Re-export threat classification utilities for backwards compatibility


# Flatpak detection cache (None = not checked, True/False = result)
_flatpak_detected: bool | None = None
_flatpak_lock = threading.Lock()


def is_flatpak() -> bool:
    """
    Detect if running inside a Flatpak sandbox.

    Uses the presence of /.flatpak-info file as the detection method,
    which is the standard way to detect Flatpak environment.

    The result is cached after the first check for performance.
    Thread-safe via lock.

    Returns:
        True if running inside Flatpak sandbox, False otherwise
    """
    global _flatpak_detected

    with _flatpak_lock:
        if _flatpak_detected is None:
            _flatpak_detected = os.path.exists("/.flatpak-info")
        return _flatpak_detected


def wrap_host_command(command: list[str]) -> list[str]:
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
        return ["flatpak-spawn", "--host"] + list(command)

    return list(command)


def which_host_command(binary: str) -> str | None:
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
                ["flatpak-spawn", "--host", "which", binary],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
    return shutil.which(binary)


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


def check_symlink_safety(path: Path) -> tuple[bool, str | None]:
    """
    Check if a path involves symlinks and if they are safe.

    Detects symlinks that could be used for path traversal attacks by
    checking if the resolved path escapes common protected directories.

    Args:
        path: Path object to check

    Returns:
        Tuple of (is_safe, warning_message):
        - (True, None) if path is safe
        - (True, warning_message) if path is a symlink but safe
        - (False, error_message) if path is potentially dangerous
    """
    try:
        # Check if the path itself is a symlink
        if not path.is_symlink():
            return (True, None)

        # Get the resolved target
        resolved = path.resolve()

        # Check if the symlink target exists
        if not resolved.exists():
            return (False, f"Symlink target does not exist: {path} -> {resolved}")

        # Define protected system directories that symlinks should not escape to
        # when the original path is in a user directory
        protected_dirs = [
            Path("/etc"),
            Path("/var"),
            Path("/usr"),
            Path("/bin"),
            Path("/sbin"),
            Path("/lib"),
            Path("/lib64"),
            Path("/boot"),
            Path("/root"),
        ]

        # Get the original path's parent directory
        original_parent = path.parent.resolve()

        # If the original path is in a user-writable location (like /home or /tmp),
        # check if the symlink escapes to a protected system directory
        user_dirs = [Path("/home"), Path("/tmp"), Path("/var/tmp")]
        is_in_user_dir = any(
            str(original_parent).startswith(str(user_dir)) for user_dir in user_dirs
        )

        if is_in_user_dir:
            for protected in protected_dirs:
                if str(resolved).startswith(str(protected)):
                    return (False, f"Symlink escapes to protected directory: {path} -> {resolved}")

        # Symlink is present but appears safe
        return (True, f"Path is a symlink: {path} -> {resolved}")

    except (OSError, RuntimeError) as e:
        return (False, f"Error checking symlink: {str(e)}")


def validate_path(path: str) -> tuple[bool, str | None]:
    """
    Validate a path for scanning.

    Checks that the path:
    - Is not empty
    - Exists on the filesystem
    - Is readable by the current user
    - Is not a dangerous symlink

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

    # Convert to Path object for checks
    path_obj = Path(path)

    # Check for dangerous symlinks before resolving
    is_safe, symlink_msg = check_symlink_safety(path_obj)
    if not is_safe:
        return (False, symlink_msg)

    # Normalize and resolve the path
    try:
        resolved_path = path_obj.resolve()
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


def validate_dropped_files(paths: list[str | None]) -> tuple[list[str], list[str]]:
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
    valid_paths: list[str] = []
    errors: list[str] = []

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


def _resolve_portal_path_via_xattr(portal_path: str) -> str | None:
    """
    Try to resolve a Flatpak portal path using extended attributes.

    The document portal FUSE filesystem may expose the original path
    through extended attributes.

    Args:
        portal_path: A Flatpak document portal path

    Returns:
        The real filesystem path if resolution succeeds, None otherwise.
    """
    try:
        import xattr

        # The document portal might store the real path in an xattr
        attrs_to_try = [
            "user.document-portal.path",
            "user.xdg.origin.path",
            "trusted.overlay.origin",
        ]
        for attr_name in attrs_to_try:
            try:
                value = xattr.getxattr(portal_path, attr_name)
                if value:
                    return value.decode("utf-8").rstrip("\x00")
            except (OSError, KeyError):
                pass
    except ImportError:
        pass  # xattr module not available
    except Exception:
        pass

    return None


def _resolve_portal_path_via_gio(portal_path: str) -> str | None:
    """
    Try to resolve a Flatpak portal path using GIO file attributes.

    The document portal may expose the original path through GIO attributes.

    Args:
        portal_path: A Flatpak document portal path

    Returns:
        The real filesystem path if resolution succeeds, None otherwise.
    """
    try:
        from gi.repository import Gio

        gfile = Gio.File.new_for_path(portal_path)

        # Try to get the target URI which might point to the real location
        try:
            info = gfile.query_info(
                "standard::target-uri,standard::symlink-target,xattr::*",
                Gio.FileQueryInfoFlags.NONE,
                None,
            )
            target_uri = info.get_attribute_string("standard::target-uri")
            if target_uri and target_uri.startswith("file://"):
                return target_uri[7:]  # Strip file:// prefix

            symlink_target = info.get_attribute_string("standard::symlink-target")
            if symlink_target and not symlink_target.startswith("/run/"):
                return symlink_target

            # Try custom xattr via GIO
            xattr_path = info.get_attribute_string("xattr::document-portal-path")
            if xattr_path:
                return xattr_path
        except Exception:
            pass

    except Exception:
        pass

    return None


def _resolve_portal_path_via_dbus(portal_path: str) -> str | None:
    """
    Try to resolve a Flatpak portal path to its real location via D-Bus.

    Queries the document portal's Info() method to get the original host path.
    This is a best-effort resolution - it may not always succeed.

    Args:
        portal_path: A Flatpak document portal path like:
            - /run/user/1000/doc/<hash>/...
            - /run/flatpak/doc/<hash>/...

    Returns:
        The real filesystem path if resolution succeeds, None otherwise.
    """
    # Match both /run/user/<uid>/doc/ and /run/flatpak/doc/ patterns
    match = re.match(r"/run/(?:user/\d+|flatpak)/doc/([a-f0-9]+)/(.+)", portal_path)
    if not match:
        return None

    doc_id = match.group(1)

    try:
        from gi.repository import Gio, GLib

        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        # Info method returns: (path ay, apps a{sas})
        # path is a byte array containing the host filesystem path
        result = bus.call_sync(
            "org.freedesktop.portal.Documents",
            "/org/freedesktop/portal/documents",
            "org.freedesktop.portal.Documents",
            "Info",
            GLib.Variant("(s)", (doc_id,)),
            GLib.VariantType("(aya{sas})"),
            Gio.DBusCallFlags.NONE,
            1000,  # 1 second timeout
            None,
        )
        unpacked = result.unpack()
        # First element is the path as byte array
        path_bytes = unpacked[0]
        if path_bytes:
            # Convert byte array to string, strip null terminator
            if isinstance(path_bytes, bytes):
                host_path = path_bytes.rstrip(b"\x00").decode("utf-8")
            else:
                # It's a list of integers (byte values)
                host_path = bytes(path_bytes).rstrip(b"\x00").decode("utf-8")

            if host_path:
                return host_path
    except Exception:
        pass  # D-Bus query failed silently

    return None


def format_flatpak_portal_path(path: str) -> str:
    """
    Convert Flatpak document portal paths to user-friendly display paths.

    In Flatpak, files selected via the file picker are exposed through the
    document portal at paths like:
        - /run/user/1000/doc/<hash>/<path>
        - /run/flatpak/doc/<hash>/<path>
    This function converts them to readable paths.

    Examples:
        /run/user/1000/doc/bceb31dc/Downloads/file.txt -> ~/Downloads/file.txt
        /run/flatpak/doc/abc123/home/user/Docs/f.txt -> ~/Docs/f.txt
        /run/flatpak/doc/abc123/media/data/nextcloud -> /media/data/nextcloud

    Args:
        path: The filesystem path to check and potentially convert

    Returns:
        A user-friendly path if it's a portal path, otherwise the original path
    """
    # Match both /run/user/<uid>/doc/ and /run/flatpak/doc/ patterns
    match = re.match(r"/run/(?:user/\d+|flatpak)/doc/[a-f0-9]+/(.+)", path)
    if match:
        relative_path = match.group(1)

        # If it starts with home/username, strip that part and use ~/
        home_match = re.match(r"home/[^/]+/(.+)", relative_path)
        if home_match:
            return f"~/{home_match.group(1)}"

        # Get the first path component
        first_component = relative_path.split("/")[0]

        # Known home subdirectories - prefix with ~/
        home_subdirs = (
            "Downloads",
            "Documents",
            "Desktop",
            "Pictures",
            "Videos",
            "Music",
            ".config",
            ".local",
            ".cache",
        )
        if first_component in home_subdirs:
            return f"~/{relative_path}"

        # Absolute path indicators - prefix with /
        abs_indicators = ("media", "mnt", "run", "tmp", "opt", "var", "usr", "srv")
        if first_component in abs_indicators:
            return f"/{relative_path}"

        # Unknown location - try multiple resolution methods

        # Method 1: Try extended attributes (might work from inside sandbox)
        resolved = _resolve_portal_path_via_xattr(path)

        # Method 2: Try GIO file attributes
        if not resolved:
            resolved = _resolve_portal_path_via_gio(path)

        # Method 3: Try D-Bus resolution
        if not resolved:
            resolved = _resolve_portal_path_via_dbus(path)

        if resolved:
            # Format the resolved path with ~ for home directory
            try:
                home = str(Path.home())
                if resolved.startswith(home):
                    return "~" + resolved[len(home) :]
            except Exception:
                pass
            return resolved

        # All resolution methods failed - show just the name with indicator
        # This is friendlier than the raw portal path
        return f"[Portal] {relative_path}"

    return path


def format_scan_path(path: str) -> str:
    """
    Format a path for display in the UI.

    Shortens long paths for better readability while keeping them identifiable.
    Handles Flatpak document portal paths by converting them to user-friendly format.

    Args:
        path: The filesystem path to format

    Returns:
        A formatted string suitable for UI display
    """
    if not path:
        return "No path selected"

    # First, handle Flatpak document portal paths
    path = format_flatpak_portal_path(path)

    # If already formatted (~ notation or [Portal] indicator), return as-is
    if path.startswith("~/") or path.startswith("[Portal]"):
        return path

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
        "type": "unknown",
        "exists": False,
        "readable": False,
        "size": None,
        "display_path": format_scan_path(path),
    }

    if not path:
        return info

    try:
        resolved = Path(path).resolve()
        info["exists"] = resolved.exists()

        if not info["exists"]:
            return info

        if resolved.is_file():
            info["type"] = "file"
            with contextlib.suppress(OSError):
                info["size"] = resolved.stat().st_size
        elif resolved.is_dir():
            info["type"] = "directory"

        info["readable"] = os.access(resolved, os.R_OK)

    except (OSError, RuntimeError):
        pass

    return info


def format_results_as_text(result: "ScanResult", timestamp: str | None = None) -> str:
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


def copy_to_clipboard(text: str) -> bool:
    """
    Copy text to the system clipboard using GTK 4 clipboard API.

    Uses the default display's clipboard to copy text content.
    This works in both regular desktop and Flatpak environments.

    Args:
        text: The text content to copy to the clipboard

    Returns:
        True if the text was successfully copied, False otherwise

    Example:
        >>> copy_to_clipboard("Hello, World!")
        True

        >>> copy_to_clipboard("")
        False
    """
    if not text:
        return False

    try:
        # Import GTK/GDK for clipboard access
        import gi

        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk

        # Get the default display
        display = Gdk.Display.get_default()
        if display is None:
            return False

        # Get the clipboard
        clipboard = display.get_clipboard()
        if clipboard is None:
            return False

        # Set the text content
        clipboard.set(text)

        return True

    except Exception:
        return False


def format_results_as_csv(result: "ScanResult", timestamp: str | None = None) -> str:
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
            writer.writerow(
                [threat.file_path, threat.threat_name, threat.category, threat.severity, timestamp]
            )

    return output.getvalue()
