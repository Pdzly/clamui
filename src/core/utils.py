# ClamUI Utility Functions
"""
Backwards compatibility module for ClamUI utilities.

This module re-exports all utility functions from focused modules to maintain
backwards compatibility with existing imports like:
    from clamui.core.utils import check_clamav_installed

The original utils.py has been split into focused modules:
- flatpak.py: Flatpak detection and portal path resolution
- clamav_detection.py: ClamAV installation detection and daemon connectivity
- path_validation.py: Path validation and formatting
- result_formatters.py: Scan result formatting (text/CSV)
- clipboard.py: Clipboard operations

All functions are re-exported here to ensure existing code continues to work.
New code should import directly from the focused modules.
"""

# Re-export all public functions from focused modules
from .clamav_detection import (
    check_clamav_installed,
    check_clamd_connection,
    check_clamdscan_installed,
    check_freshclam_installed,
    get_clamav_path,
    get_clamd_socket_path,
    get_freshclam_path,
)
from .clipboard import copy_to_clipboard
from .flatpak import (
    _resolve_portal_path_via_dbus,
    _resolve_portal_path_via_gio,
    _resolve_portal_path_via_xattr,
    ensure_clamav_database_dir,
    ensure_freshclam_config,
    format_flatpak_portal_path,
    get_clamav_database_dir,
    get_clean_env,
    get_freshclam_config_path,
    is_flatpak,
    which_host_command,
    wrap_host_command,
)
from .path_validation import (
    check_symlink_safety,
    format_scan_path,
    get_path_info,
    validate_dropped_files,
    validate_path,
)
from .result_formatters import format_results_as_csv, format_results_as_text

# Define public API for backwards compatibility
__all__ = [
    # Flatpak/packaging functions
    "get_clean_env",
    "is_flatpak",
    "wrap_host_command",
    "which_host_command",
    "format_flatpak_portal_path",
    "get_clamav_database_dir",
    "ensure_clamav_database_dir",
    "get_freshclam_config_path",
    "ensure_freshclam_config",
    "_resolve_portal_path_via_xattr",
    "_resolve_portal_path_via_gio",
    "_resolve_portal_path_via_dbus",
    # ClamAV detection functions
    "check_clamav_installed",
    "check_freshclam_installed",
    "check_clamdscan_installed",
    "get_clamd_socket_path",
    "check_clamd_connection",
    "get_clamav_path",
    "get_freshclam_path",
    # Path validation functions
    "check_symlink_safety",
    "validate_path",
    "validate_dropped_files",
    "format_scan_path",
    "get_path_info",
    # Result formatting functions
    "format_results_as_text",
    "format_results_as_csv",
    # Clipboard functions
    "copy_to_clipboard",
]
