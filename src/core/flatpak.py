# ClamUI Flatpak Integration
"""
Flatpak detection and portal path resolution utilities.

This module provides functions for:
- Detecting if ClamUI is running inside a Flatpak sandbox
- Wrapping host commands to bridge the sandbox boundary
- Resolving Flatpak document portal paths to user-friendly display paths
- Finding binaries on the host system when running in Flatpak
"""

import logging
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Default database directory for Flatpak (inside sandbox data directory)
_FLATPAK_DATABASE_DIR: Path | None = None

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


def get_clamav_database_dir() -> Path | None:
    """
    Get the ClamAV database directory for Flatpak installations.

    In Flatpak, the /app directory is read-only, so we use the app's
    data directory ($XDG_DATA_HOME/clamav) for virus databases.

    Returns:
        Path to database directory in Flatpak, None for native installations
    """
    global _FLATPAK_DATABASE_DIR

    if not is_flatpak():
        return None

    if _FLATPAK_DATABASE_DIR is not None:
        return _FLATPAK_DATABASE_DIR

    # Use XDG_DATA_HOME which maps to ~/.var/app/<app-id>/data/ in Flatpak
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        _FLATPAK_DATABASE_DIR = Path(data_home) / "clamav"
    else:
        # Fallback to standard location
        _FLATPAK_DATABASE_DIR = Path.home() / ".local" / "share" / "clamav"

    return _FLATPAK_DATABASE_DIR


def ensure_clamav_database_dir() -> Path | None:
    """
    Ensure the ClamAV database directory exists for Flatpak installations.

    Creates the directory if it doesn't exist. Only applicable in Flatpak.

    Returns:
        Path to the created/existing database directory, None for native installations
    """
    db_dir = get_clamav_database_dir()
    if db_dir is None:
        return None

    try:
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("ClamAV database directory ensured: %s", db_dir)
        return db_dir
    except Exception as e:
        logger.error("Failed to create ClamAV database directory: %s", e)
        return None


def get_freshclam_config_path() -> Path | None:
    """
    Get the path to freshclam.conf for Flatpak installations.

    In Flatpak, we generate a config file at runtime in the user's config
    directory because:
    1. /app is read-only, so we can't modify the bundled config
    2. We need to set DatabaseDirectory to a user-writable location
    3. Config files can't use environment variables

    Returns:
        Path to the config file in Flatpak, None for native installations
    """
    if not is_flatpak():
        return None

    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "clamav" / "freshclam.conf"
    else:
        return Path.home() / ".config" / "clamav" / "freshclam.conf"


def ensure_freshclam_config() -> Path | None:
    """
    Ensure freshclam.conf exists with correct DatabaseDirectory for Flatpak.

    Generates the config file at runtime with the correct database directory
    path since static config files can't use environment variables.

    Returns:
        Path to the config file, None for native installations or on error
    """
    if not is_flatpak():
        logger.debug("Not in Flatpak, skipping freshclam config generation")
        return None

    config_path = get_freshclam_config_path()
    if config_path is None:
        logger.error("Failed to get freshclam config path")
        return None

    # If config file already exists, don't regenerate it (preserve user settings)
    if config_path.exists():
        logger.debug("Freshclam config already exists at: %s, skipping generation", config_path)
        return config_path

    logger.info("Generating freshclam config at: %s", config_path)

    # Ensure database directory exists first
    db_dir = ensure_clamav_database_dir()
    if db_dir is None:
        logger.error("Failed to ensure database directory")
        return None

    logger.info("Using database directory: %s", db_dir)

    # Ensure config directory exists
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Config directory created: %s", config_path.parent)
    except Exception as e:
        logger.error("Failed to create ClamAV config directory %s: %s", config_path.parent, e)
        return None

    # Generate the config file with the correct database directory
    config_content = f"""# ClamUI Flatpak freshclam configuration
# Auto-generated - do not edit manually

# Database directory (user-writable location in Flatpak)
DatabaseDirectory {db_dir}

# Database mirror - official ClamAV database server
DatabaseMirror database.clamav.net

# Number of database checks per day
Checks 12

# Connect timeout in seconds
ConnectTimeout 30

# Receive timeout in seconds
ReceiveTimeout 60

# Disable test databases
TestDatabases no

# Log verbosely
LogVerbose yes

# Run in foreground (for Flatpak)
Foreground yes
"""

    try:
        config_path.write_text(config_content)
        logger.info("Successfully generated freshclam config at: %s", config_path)
        # Verify file exists
        if config_path.exists():
            logger.debug("Config file verified to exist")
            return config_path
        else:
            logger.error("Config file does not exist after write!")
            return None
    except Exception as e:
        logger.error("Failed to write freshclam config to %s: %s", config_path, e)
        return None


def wrap_host_command(command: list[str]) -> list[str]:
    """
    Wrap a command with flatpak-spawn --host if needed in Flatpak.

    When running inside a Flatpak sandbox:
    - Commands using bundled binaries (/app/bin/*) run directly
    - Commands using host binaries are prefixed with 'flatpak-spawn --host'

    Args:
        command: The command to wrap as a list of strings
                 (e.g., ['clamscan', '--version'])

    Returns:
        The command, potentially wrapped for host execution if in Flatpak

    Example:
        >>> wrap_host_command(['clamscan', '--version'])
        ['clamscan', '--version']  # When not in Flatpak

        >>> wrap_host_command(['/app/bin/clamscan', '--version'])
        ['/app/bin/clamscan', '--version']  # Bundled binary in Flatpak

        >>> wrap_host_command(['clamscan', '--version'])
        ['flatpak-spawn', '--host', 'clamscan', '--version']  # Host binary in Flatpak
    """
    if not command:
        return command

    if is_flatpak():
        binary = command[0]
        # Check if it's a bundled Flatpak binary (absolute path in /app/)
        if binary.startswith("/app/"):
            return list(command)
        # Check if it's a binary name that exists in /app/bin/
        flatpak_bin = f"/app/bin/{binary}"
        if os.path.isfile(flatpak_bin) and os.access(flatpak_bin, os.X_OK):
            # Use the bundled binary directly
            return [flatpak_bin] + list(command[1:])
        # Fall back to host command
        return ["flatpak-spawn", "--host"] + list(command)

    return list(command)


def which_host_command(binary: str) -> str | None:
    """
    Find binary path, checking bundled Flatpak binaries first, then host system.

    When running inside a Flatpak sandbox:
    1. First checks if the binary exists in /app/bin/ (bundled with Flatpak)
    2. Falls back to host system via 'flatpak-spawn --host which'

    This ensures bundled ClamAV binaries are used when available.

    Args:
        binary: The name of the binary to find (e.g., 'clamscan')

    Returns:
        The full path to the binary if found, None otherwise
    """
    if is_flatpak():
        # First check for bundled binary in Flatpak
        flatpak_bin = f"/app/bin/{binary}"
        if os.path.isfile(flatpak_bin) and os.access(flatpak_bin, os.X_OK):
            logger.debug("Found bundled binary: %s", flatpak_bin)
            return flatpak_bin

        # Fall back to host system
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
        except Exception as e:
            logger.debug("Failed to find binary '%s' on host: %s", binary, e)
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
        logger.debug("xattr module not available for portal path resolution")
    except Exception as e:
        logger.debug("Failed to resolve portal path via xattr: %s", e)

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
        except Exception as e:
            logger.debug("GIO file info query failed: %s", e)

    except Exception as e:
        logger.debug("Failed to resolve portal path via GIO: %s", e)

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
    except Exception as e:
        logger.debug("D-Bus portal path resolution failed: %s", e)

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
            except Exception as e:
                logger.debug("Failed to get home directory for path formatting: %s", e)
            return resolved

        # All resolution methods failed - show just the name with indicator
        # This is friendlier than the raw portal path
        return f"[Portal] {relative_path}"

    return path
