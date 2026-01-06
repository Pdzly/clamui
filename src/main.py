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
from src.app import ClamUIApp


def parse_arguments(argv: list[str]) -> tuple[list[str], bool, list[str]]:
    """
    Parse command line arguments for file paths and VirusTotal flag.

    This function extracts file and folder paths from the command line
    arguments, typically passed from file manager context menu actions
    via the %F field code in desktop files. It also checks for the
    --virustotal flag to enable VirusTotal scanning.

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
        help="Files or directories to scan",
    )

    # Parse only known args to allow GTK to process its own arguments
    args, unknown_args = parser.parse_known_args(argv[1:])

    file_paths = args.files if args.files else []

    if file_paths:
        # Log received file paths for debugging context menu integration
        mode = "VirusTotal" if args.virustotal else "ClamAV"
        print(f"ClamUI: Received {len(file_paths)} path(s) for {mode} scanning:", file=sys.stderr)
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

    Parses CLI file arguments and creates a ClamUIApp instance.
    When file paths are provided (e.g., from file manager context menu),
    they will be queued for scanning when the application starts.

    Returns:
        int: Exit code from the application (0 for success).
    """
    # Parse file arguments and options from CLI (e.g., from context menu %F)
    file_paths, use_virustotal, gtk_args = parse_arguments(sys.argv)

    # Create application instance
    app = ClamUIApp()

    # Store file paths for processing after activation
    # The app's do_activate() will handle these paths
    if file_paths:
        # Pass file paths to the app if the method is available
        if hasattr(app, "set_initial_scan_paths"):
            app.set_initial_scan_paths(file_paths, use_virustotal=use_virustotal)

    # Pass only program name + unknown args (GTK-specific) to app.run()
    # Our custom args (--virustotal, file paths) have already been processed
    return app.run([sys.argv[0]] + gtk_args)


if __name__ == "__main__":
    sys.exit(main())
