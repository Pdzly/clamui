# ClamUI Flatpak Integration
"""
Flatpak detection and portal path resolution utilities.

This module provides functions for:
- Detecting if ClamUI is running inside a Flatpak sandbox
- Wrapping host commands to bridge the sandbox boundary
- Resolving Flatpak document portal paths to user-friendly display paths
- Finding binaries on the host system when running in Flatpak
"""

import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

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
