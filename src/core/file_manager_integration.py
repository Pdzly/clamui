# ClamUI File Manager Integration
"""
File manager integration installer for Flatpak.

This module provides functions to install context menu integration
for various file managers (Nemo, Nautilus, Dolphin) when running
as a Flatpak application.

The integration files are bundled in the Flatpak at /app/share/clamui/integrations/
and are copied to the user's local share directories on first run.
"""

import logging
import os
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .flatpak import is_flatpak

logger = logging.getLogger(__name__)


class FileManager(Enum):
    """Supported file managers for integration."""

    NEMO = "nemo"
    NAUTILUS = "nautilus"
    DOLPHIN = "dolphin"


@dataclass
class IntegrationInfo:
    """Information about a file manager integration."""

    file_manager: FileManager
    display_name: str
    description: str
    source_files: list[tuple[str, str]]  # List of (source_filename, dest_path) tuples
    is_installed: bool = False
    is_available: bool = False


# Bundled integration files location in Flatpak
INTEGRATIONS_SOURCE_DIR = Path("/app/share/clamui/integrations")

# Integration file mappings: source filename -> destination relative path
NEMO_INTEGRATIONS = [
    (
        "io.github.linx_systems.ClamUI.nemo_action",
        "nemo/actions/io.github.linx_systems.ClamUI.nemo_action",
    ),
    (
        "io.github.linx_systems.ClamUI-virustotal.nemo_action",
        "nemo/actions/io.github.linx_systems.ClamUI-virustotal.nemo_action",
    ),
]

NAUTILUS_INTEGRATIONS = [
    (
        "clamui-virustotal-nautilus.sh",
        "nautilus/scripts/Scan with VirusTotal",
    ),
]

DOLPHIN_INTEGRATIONS = [
    (
        "io.github.linx_systems.ClamUI-virustotal.desktop",
        "kservices5/ServiceMenus/io.github.linx_systems.ClamUI-virustotal.desktop",
    ),
]


def _get_local_share_dir() -> Path:
    """
    Get the user's local share directory for file manager integrations.

    In Flatpak, we explicitly use ~/.local/share (not XDG_DATA_HOME) because:
    1. XDG_DATA_HOME points to the sandboxed ~/.var/app/<app-id>/data/
    2. File managers (Nemo, Nautilus, Dolphin) look in the real ~/.local/share
    3. The Flatpak manifest grants filesystem permissions to those directories

    Returns:
        Path to ~/.local/share (always the real user directory)
    """
    if is_flatpak():
        # In Flatpak, always use the real ~/.local/share, not the sandbox
        return Path.home() / ".local" / "share"

    # Outside Flatpak, respect XDG_DATA_HOME if set
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        return Path(data_home)
    return Path.home() / ".local" / "share"


def _check_file_manager_available(file_manager: FileManager) -> bool:
    """
    Check if a file manager is available on the system.

    Uses directory existence as the primary check since it's more reliable
    and doesn't require executing host commands.

    Args:
        file_manager: The file manager to check.

    Returns:
        True if the file manager appears to be installed/used.
    """
    local_share = _get_local_share_dir()

    if file_manager == FileManager.NEMO:
        # Check if Nemo actions directory exists or can be created
        nemo_dir = local_share / "nemo"
        return nemo_dir.exists() or _can_create_directory(nemo_dir)

    elif file_manager == FileManager.NAUTILUS:
        # Check if Nautilus scripts directory exists or can be created
        nautilus_dir = local_share / "nautilus"
        return nautilus_dir.exists() or _can_create_directory(nautilus_dir)

    elif file_manager == FileManager.DOLPHIN:
        # Check if KDE service menus directory exists or can be created
        kde_dir = local_share / "kservices5"
        return kde_dir.exists() or _can_create_directory(kde_dir)

    return False


def _can_create_directory(path: Path) -> bool:
    """
    Check if a directory can be created (parent exists and is writable).

    Args:
        path: The directory path to check.

    Returns:
        True if the directory can be created.
    """
    try:
        parent = path.parent
        return parent.exists() and os.access(parent, os.W_OK)
    except Exception:
        return False


def _check_integration_installed(file_manager: FileManager) -> bool:
    """
    Check if integration files are already installed for a file manager.

    Args:
        file_manager: The file manager to check.

    Returns:
        True if all integration files are installed.
    """
    local_share = _get_local_share_dir()

    if file_manager == FileManager.NEMO:
        files = NEMO_INTEGRATIONS
    elif file_manager == FileManager.NAUTILUS:
        files = NAUTILUS_INTEGRATIONS
    elif file_manager == FileManager.DOLPHIN:
        files = DOLPHIN_INTEGRATIONS
    else:
        return False

    # Check if at least the primary integration file exists
    if files:
        _, dest_rel = files[0]
        dest_path = local_share / dest_rel
        return dest_path.exists()

    return False


def get_available_integrations() -> list[IntegrationInfo]:
    """
    Get list of available file manager integrations.

    Detects which file managers are available and whether integrations
    are already installed.

    Returns:
        List of IntegrationInfo objects for each supported file manager.
    """
    integrations = []

    # Check if we're in Flatpak and have integration files
    if not is_flatpak():
        logger.debug("Not in Flatpak, file manager integrations not applicable")
        return integrations

    if not INTEGRATIONS_SOURCE_DIR.exists():
        logger.warning(
            f"Integration source directory not found: {INTEGRATIONS_SOURCE_DIR}"
        )
        return integrations

    # Nemo (Linux Mint, Cinnamon)
    nemo_available = _check_file_manager_available(FileManager.NEMO)
    nemo_installed = _check_integration_installed(FileManager.NEMO)
    integrations.append(
        IntegrationInfo(
            file_manager=FileManager.NEMO,
            display_name="Nemo",
            description="Linux Mint / Cinnamon file manager",
            source_files=NEMO_INTEGRATIONS,
            is_installed=nemo_installed,
            is_available=nemo_available,
        )
    )

    # Nautilus (GNOME Files)
    nautilus_available = _check_file_manager_available(FileManager.NAUTILUS)
    nautilus_installed = _check_integration_installed(FileManager.NAUTILUS)
    integrations.append(
        IntegrationInfo(
            file_manager=FileManager.NAUTILUS,
            display_name="Nautilus",
            description="GNOME Files",
            source_files=NAUTILUS_INTEGRATIONS,
            is_installed=nautilus_installed,
            is_available=nautilus_available,
        )
    )

    # Dolphin (KDE)
    dolphin_available = _check_file_manager_available(FileManager.DOLPHIN)
    dolphin_installed = _check_integration_installed(FileManager.DOLPHIN)
    integrations.append(
        IntegrationInfo(
            file_manager=FileManager.DOLPHIN,
            display_name="Dolphin",
            description="KDE file manager",
            source_files=DOLPHIN_INTEGRATIONS,
            is_installed=dolphin_installed,
            is_available=dolphin_available,
        )
    )

    return integrations


def install_integration(file_manager: FileManager) -> tuple[bool, str | None]:
    """
    Install file manager integration.

    Copies integration files from the Flatpak bundle to the user's
    local share directory.

    Args:
        file_manager: The file manager to install integration for.

    Returns:
        Tuple of (success, error_message).
    """
    if not is_flatpak():
        return False, "Not running as Flatpak"

    if not INTEGRATIONS_SOURCE_DIR.exists():
        return False, "Integration files not found"

    local_share = _get_local_share_dir()

    if file_manager == FileManager.NEMO:
        files = NEMO_INTEGRATIONS
    elif file_manager == FileManager.NAUTILUS:
        files = NAUTILUS_INTEGRATIONS
    elif file_manager == FileManager.DOLPHIN:
        files = DOLPHIN_INTEGRATIONS
    else:
        return False, f"Unknown file manager: {file_manager}"

    try:
        for source_name, dest_rel in files:
            source_path = INTEGRATIONS_SOURCE_DIR / source_name
            dest_path = local_share / dest_rel

            if not source_path.exists():
                logger.warning(f"Source file not found: {source_path}")
                continue

            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file
            shutil.copy2(source_path, dest_path)

            # Make scripts executable
            if source_name.endswith(".sh"):
                dest_path.chmod(0o755)

            logger.info(f"Installed: {dest_path}")

        return True, None

    except PermissionError as e:
        error_msg = f"Permission denied: {e}"
        logger.error(error_msg)
        return False, error_msg

    except Exception as e:
        error_msg = f"Failed to install integration: {e}"
        logger.error(error_msg)
        return False, error_msg


def remove_integration(file_manager: FileManager) -> tuple[bool, str | None]:
    """
    Remove file manager integration.

    Removes integration files from the user's local share directory.

    Args:
        file_manager: The file manager to remove integration for.

    Returns:
        Tuple of (success, error_message).
    """
    local_share = _get_local_share_dir()

    if file_manager == FileManager.NEMO:
        files = NEMO_INTEGRATIONS
    elif file_manager == FileManager.NAUTILUS:
        files = NAUTILUS_INTEGRATIONS
    elif file_manager == FileManager.DOLPHIN:
        files = DOLPHIN_INTEGRATIONS
    else:
        return False, f"Unknown file manager: {file_manager}"

    try:
        for _, dest_rel in files:
            dest_path = local_share / dest_rel

            if dest_path.exists():
                dest_path.unlink()
                logger.info(f"Removed: {dest_path}")

        return True, None

    except PermissionError as e:
        error_msg = f"Permission denied: {e}"
        logger.error(error_msg)
        return False, error_msg

    except Exception as e:
        error_msg = f"Failed to remove integration: {e}"
        logger.error(error_msg)
        return False, error_msg


def install_all_available() -> dict[FileManager, tuple[bool, str | None]]:
    """
    Install integrations for all available file managers.

    Returns:
        Dictionary mapping file manager to (success, error_message) tuple.
    """
    results = {}

    for integration in get_available_integrations():
        if integration.is_available and not integration.is_installed:
            success, error = install_integration(integration.file_manager)
            results[integration.file_manager] = (success, error)

    return results


def check_any_available() -> bool:
    """
    Check if any file manager integrations are available.

    Returns:
        True if at least one file manager integration can be installed.
    """
    if not is_flatpak():
        return False

    return any(integration.is_available for integration in get_available_integrations())


def check_any_not_installed() -> bool:
    """
    Check if any available integrations are not yet installed.

    Returns:
        True if at least one available integration is not installed.
    """
    if not is_flatpak():
        return False

    return any(
        integration.is_available and not integration.is_installed
        for integration in get_available_integrations()
    )
