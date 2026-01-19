#!/usr/bin/env python3
# ClamUI Entry Point
"""
Main entry point for the ClamUI application.

This module provides the entry point for launching the ClamUI GTK4/Adwaita
desktop application. It handles path setup, CLI argument parsing for file
scanning, and initializes the GTK main loop.

Usage:
    python src/main.py
    python src/main.py /path/to/file.txt             # Scan a single file
    python src/main.py /path/to/folder               # Scan a folder
    python src/main.py file1.txt folder1 ...         # Scan multiple items
    python src/main.py --virustotal /path/to/file    # Scan with VirusTotal
"""

import os
import sys


def _setup_path():
    """
    Ensure the project root is in sys.path.

    This allows the application to be run directly as a script
    (python src/main.py) while still supporting proper package imports.
    """
    # Get the directory containing this file (src/)
    src_dir = os.path.dirname(os.path.abspath(__file__))
    # Get project root (parent of src/)
    project_root = os.path.dirname(src_dir)

    if project_root not in sys.path:
        sys.path.insert(0, project_root)


# Set up path before importing application modules
_setup_path()

# Import the application class
# Note: Tray indicator is handled by app.py with graceful degradation
# GTK3/GTK4 cannot coexist in the same process, so tray is disabled
# when running with GTK4 (which is required for the main UI)
from .app import ClamUIApp


def uri_to_path(uri: str) -> str:
    """
    Convert a file:// URI to a local filesystem path.

    Handles both file:// URIs (from Flatpak/portal) and regular paths.

    Args:
        uri: A file:// URI or regular filesystem path.

    Returns:
        The filesystem path.
    """
    from urllib.parse import unquote, urlparse

    if uri.startswith("file://"):
        parsed = urlparse(uri)
        # Decode percent-encoded characters (e.g., %20 -> space)
        return unquote(parsed.path)
    return uri


def parse_arguments(argv: list[str]) -> tuple[list[str], bool, list[str]]:
    """
    Parse command line arguments for file paths and VirusTotal flag.

    This function extracts file and folder paths from the command line
    arguments, typically passed from file manager context menu actions
    via the %U field code in desktop files. It handles both file:// URIs
    (used by Flatpak/portal) and regular filesystem paths.

    Args:
        argv: Command line arguments (sys.argv).

    Returns:
        Tuple of (file_paths, is_virustotal_scan, unknown_args):
        - file_paths: List of file/folder paths to scan. Empty list if none.
        - is_virustotal_scan: True if --virustotal flag was provided.
        - unknown_args: List of unrecognized args to pass to GTK.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="ClamUI - Graphical interface for ClamAV antivirus",
        prog="clamui",
    )
    parser.add_argument(
        "--virustotal",
        action="store_true",
        help="Scan files with VirusTotal instead of ClamAV",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files or directories to scan (paths or file:// URIs)",
    )

    # Parse only known args to allow GTK to process its own arguments
    args, unknown_args = parser.parse_known_args(argv[1:])

    # Convert URIs to paths (handles both file:// URIs and regular paths)
    file_paths = [uri_to_path(f) for f in args.files] if args.files else []

    if file_paths:
        # Log received file paths for debugging context menu integration
        mode = "VirusTotal" if args.virustotal else "ClamAV"
        print(
            f"ClamUI: Received {len(file_paths)} path(s) for {mode} scanning:",
            file=sys.stderr,
        )
        for path in file_paths:
            print(f"  - {path}", file=sys.stderr)

    return file_paths, args.virustotal, unknown_args


def parse_file_arguments(argv: list[str]) -> list[str]:
    """
    Parse file/folder paths from command line arguments.

    This function extracts file and folder paths from the command line
    arguments, typically passed from file manager context menu actions
    via the %F field code in desktop files.

    .. deprecated:: 0.2.0
        Use :func:`parse_arguments` instead, which also supports the
        --virustotal flag.

    Args:
        argv: Command line arguments (sys.argv).

    Returns:
        List of file/folder paths to scan. Empty list if no paths provided.
    """
    file_paths, _, _ = parse_arguments(argv)
    return file_paths


def main():
    """
    Application entry point.

    Creates a ClamUIApp instance and passes all arguments to it.
    The app's do_command_line() method handles argument parsing,
    enabling file manager integration to work even when ClamUI
    is already running (arguments are forwarded via D-Bus IPC).

    Returns:
        int: Exit code from the application (0 for success).
    """
    # Create application instance
    app = ClamUIApp()

    # Pass all arguments to app.run() - do_command_line() will process them
    # This enables single-instance behavior: when ClamUI is already running,
    # arguments from file manager context menu are forwarded to the running
    # instance via D-Bus, allowing it to start a new scan.
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
