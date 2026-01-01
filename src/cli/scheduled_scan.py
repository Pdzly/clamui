#!/usr/bin/env python3
# ClamUI Scheduled Scan CLI Entry Point
"""
CLI entry point for headless scheduled scan execution.

This module provides the main() function used by the clamui-scheduled-scan
console script entry point defined in pyproject.toml.

It is invoked by systemd timers or cron jobs to execute scheduled antivirus
scans without requiring a GUI environment.

Usage:
    clamui-scheduled-scan [OPTIONS]

Options:
    --skip-on-battery     Skip scan if running on battery power
    --auto-quarantine     Automatically quarantine detected threats
    --target PATH         Path to scan (can be specified multiple times)
    --dry-run             Show what would be done without executing
    --verbose             Enable verbose output
    --help                Show this help message

Examples:
    # Run scheduled scan with settings from config
    clamui-scheduled-scan

    # Scan specific targets with battery skip
    clamui-scheduled-scan --skip-on-battery --target /home/user/Documents

    # Scan with auto-quarantine enabled
    clamui-scheduled-scan --auto-quarantine --target /home/user/Downloads
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from src.core.battery_manager import BatteryManager
from src.core.log_manager import LogEntry, LogManager
from src.core.quarantine import QuarantineManager
from src.core.scanner import Scanner, ScanResult, ScanStatus
from src.core.settings_manager import SettingsManager


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="ClamUI Scheduled Scan - Headless antivirus scanning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use settings from config
  %(prog)s --target /home/user/Documents      # Scan specific directory
  %(prog)s --skip-on-battery --auto-quarantine # Skip on battery, quarantine threats
        """
    )

    parser.add_argument(
        "--skip-on-battery",
        action="store_true",
        default=None,
        help="Skip scan if running on battery power"
    )

    parser.add_argument(
        "--auto-quarantine",
        action="store_true",
        default=None,
        help="Automatically quarantine detected threats"
    )

    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        metavar="PATH",
        help="Path to scan (can be specified multiple times)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    return parser.parse_args()


def log_message(message: str, verbose: bool = False, is_verbose: bool = False) -> None:
    """
    Log a message to stderr.

    Args:
        message: The message to log
        verbose: Whether verbose mode is enabled
        is_verbose: Whether this is a verbose-only message
    """
    if is_verbose and not verbose:
        return
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", file=sys.stderr)


def send_notification(
    title: str,
    body: str,
    urgency: str = "normal"
) -> bool:
    """
    Send a desktop notification using notify-send.

    This is a headless alternative to Gio.Notification that works
    without requiring a running GTK application.

    Args:
        title: Notification title
        body: Notification body text
        urgency: Urgency level (low, normal, critical)

    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        # Use notify-send for headless notifications
        cmd = ["notify-send"]

        # Set urgency level
        if urgency in ("low", "normal", "critical"):
            cmd.extend(["--urgency", urgency])

        # Add app name for proper categorization
        cmd.extend(["--app-name", "ClamUI"])

        # Add icon if available
        icon_paths = [
            "/usr/share/icons/hicolor/scalable/apps/com.github.rooki.clamui.svg",
            "/usr/share/icons/hicolor/48x48/apps/com.github.clamui.ClamUI.png",
            "dialog-warning",  # Fallback system icon
        ]
        for icon in icon_paths:
            if icon.startswith("/") and os.path.exists(icon):
                cmd.extend(["--icon", icon])
                break
            elif not icon.startswith("/"):
                cmd.extend(["--icon", icon])
                break

        # Add title and body
        cmd.extend([title, body])

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0

    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        # notify-send not available or failed
        return False


def run_scheduled_scan(
    targets: List[str],
    skip_on_battery: bool,
    auto_quarantine: bool,
    dry_run: bool = False,
    verbose: bool = False
) -> int:
    """
    Execute a scheduled scan.

    Args:
        targets: List of paths to scan
        skip_on_battery: Whether to skip scan if on battery
        auto_quarantine: Whether to quarantine detected threats
        dry_run: If True, show what would be done without executing
        verbose: Enable verbose output

    Returns:
        Exit code (0 for success/clean, 1 for threats found, 2 for error)
    """
    # Initialize managers
    settings = SettingsManager()
    battery_manager = BatteryManager()
    log_manager = LogManager()
    scanner = Scanner(log_manager=log_manager)

    log_message("ClamUI scheduled scan starting...", verbose)

    # Check battery status if skip_on_battery is enabled
    if skip_on_battery:
        log_message("Checking battery status...", verbose, is_verbose=True)
        if battery_manager.should_skip_scan(skip_on_battery=True):
            battery_status = battery_manager.get_status()
            percent = battery_status.percent or 0
            log_message(
                f"Skipping scan: running on battery power ({percent:.0f}%)",
                verbose
            )

            # Log the skip event
            log_entry = LogEntry.create(
                log_type="scan",
                status="skipped",
                summary="Scheduled scan skipped (on battery power)",
                details=f"Battery level: {percent:.0f}%\nScan skipped due to battery-aware settings.",
                path=", ".join(targets) if targets else "N/A",
                scheduled=True
            )
            log_manager.save_log(log_entry)

            return 0

    # Validate targets
    if not targets:
        log_message("Error: No scan targets specified", verbose)
        return 2

    valid_targets = []
    for target in targets:
        target_path = Path(target).expanduser()
        if target_path.exists():
            valid_targets.append(str(target_path))
        else:
            log_message(f"Warning: Target does not exist: {target}", verbose)

    if not valid_targets:
        log_message("Error: No valid scan targets found", verbose)
        return 2

    log_message(f"Scanning {len(valid_targets)} target(s)...", verbose)
    for target in valid_targets:
        log_message(f"  - {target}", verbose, is_verbose=True)

    if dry_run:
        log_message("Dry run mode - scan not executed", verbose)
        log_message(f"  Skip on battery: {skip_on_battery}", verbose)
        log_message(f"  Auto quarantine: {auto_quarantine}", verbose)
        log_message(f"  Targets: {valid_targets}", verbose)
        return 0

    # Check ClamAV availability
    is_available, version_or_error = scanner.check_available()
    if not is_available:
        log_message(f"Error: ClamAV not available - {version_or_error}", verbose)

        log_entry = LogEntry.create(
            log_type="scan",
            status="error",
            summary="Scheduled scan failed: ClamAV not available",
            details=version_or_error or "ClamAV is not installed or not accessible",
            path=", ".join(valid_targets),
            scheduled=True
        )
        log_manager.save_log(log_entry)

        send_notification(
            "Scheduled Scan Failed",
            "ClamAV is not available. Please install ClamAV.",
            urgency="critical"
        )
        return 2

    log_message(f"ClamAV version: {version_or_error}", verbose, is_verbose=True)

    # Execute scans
    start_time = time.monotonic()
    total_scanned = 0
    total_infected = 0
    all_infected_files: List[str] = []
    all_results: List[ScanResult] = []
    has_errors = False

    for target in valid_targets:
        log_message(f"Scanning: {target}", verbose)
        result = scanner.scan_sync(target, recursive=True)
        all_results.append(result)

        total_scanned += result.scanned_files
        total_infected += result.infected_count
        all_infected_files.extend(result.infected_files)

        if result.status == ScanStatus.ERROR:
            has_errors = True
            log_message(f"  Error: {result.error_message}", verbose)
        elif result.status == ScanStatus.INFECTED:
            log_message(f"  Found {result.infected_count} threat(s)", verbose)
        else:
            log_message(f"  Clean ({result.scanned_files} files scanned)", verbose)

    duration = time.monotonic() - start_time

    # Handle quarantine if threats found and auto_quarantine enabled
    quarantined_count = 0
    quarantine_failed: List[Tuple[str, str]] = []

    if all_infected_files and auto_quarantine:
        log_message(f"Quarantining {len(all_infected_files)} infected file(s)...", verbose)

        # Initialize QuarantineManager and process each threat
        quarantine_manager = QuarantineManager()

        # Collect all threat details from scan results
        all_threat_details = []
        for result in all_results:
            all_threat_details.extend(result.threat_details)

        # Quarantine each infected file with its threat name
        for threat in all_threat_details:
            quarantine_result = quarantine_manager.quarantine_file(
                threat.file_path,
                threat.threat_name
            )
            if quarantine_result.is_success:
                quarantined_count += 1
            else:
                error_msg = quarantine_result.error_message or str(quarantine_result.status.value)
                quarantine_failed.append((threat.file_path, error_msg))

        if quarantined_count > 0:
            log_message(f"  Successfully quarantined: {quarantined_count} file(s)", verbose)
        if quarantine_failed:
            log_message(f"  Failed to quarantine: {len(quarantine_failed)} file(s)", verbose)
            for file_path, error in quarantine_failed:
                log_message(f"    - {file_path}: {error}", verbose, is_verbose=True)

    # Build summary and details for logging
    if total_infected > 0:
        if auto_quarantine and quarantined_count > 0:
            summary = (
                f"Scheduled scan found {total_infected} threat(s), "
                f"{quarantined_count} quarantined"
            )
        else:
            summary = f"Scheduled scan found {total_infected} threat(s)"
        status = "infected"
    elif has_errors:
        summary = "Scheduled scan completed with errors"
        status = "error"
    else:
        summary = f"Scheduled scan completed - {total_scanned} files scanned, no threats"
        status = "clean"

    # Build detailed log output
    details_parts = [
        f"Scan Duration: {duration:.1f} seconds",
        f"Files Scanned: {total_scanned}",
        f"Threats Found: {total_infected}",
        f"Targets: {', '.join(valid_targets)}",
    ]

    if auto_quarantine and all_infected_files:
        details_parts.append(f"Quarantined: {quarantined_count}")
        if quarantine_failed:
            details_parts.append(f"Quarantine Failed: {len(quarantine_failed)}")

    if all_infected_files:
        details_parts.append("\n--- Infected Files ---")
        for result in all_results:
            for threat in result.threat_details:
                details_parts.append(
                    f"  {threat.file_path}: {threat.threat_name} "
                    f"[{threat.category}/{threat.severity}]"
                )

    # Combine stdout from all scan results
    for i, result in enumerate(all_results):
        if result.stdout.strip():
            details_parts.append(f"\n--- Scan Output ({valid_targets[i]}) ---")
            details_parts.append(result.stdout)
        if result.stderr.strip():
            details_parts.append(f"\n--- Errors ({valid_targets[i]}) ---")
            details_parts.append(result.stderr)

    details = "\n".join(details_parts)

    # Create and save log entry with scheduled=True
    log_entry = LogEntry.create(
        log_type="scan",
        status=status,
        summary=summary,
        details=details,
        path=", ".join(valid_targets),
        duration=duration,
        scheduled=True
    )
    log_manager.save_log(log_entry)

    # Send notification
    if settings.get("notifications_enabled", True):
        if total_infected > 0:
            if quarantined_count > 0:
                body = (
                    f"{total_infected} infected file(s) found, "
                    f"{quarantined_count} quarantined"
                )
            else:
                body = f"{total_infected} infected file(s) found"
            send_notification(
                "Scheduled Scan: Threats Detected!",
                body,
                urgency="critical"
            )
        elif has_errors:
            send_notification(
                "Scheduled Scan Completed",
                "Scan completed with some errors. Check logs for details.",
                urgency="normal"
            )
        else:
            send_notification(
                "Scheduled Scan Complete",
                f"No threats found ({total_scanned} files scanned)",
                urgency="low"
            )

    log_message(f"Scan completed in {duration:.1f} seconds", verbose)
    log_message(summary, verbose)

    # Return appropriate exit code
    if total_infected > 0:
        return 1
    elif has_errors:
        return 2
    else:
        return 0


def main() -> int:
    """
    Main entry point for the scheduled scan CLI.

    Returns:
        Exit code (0 for success, 1 for threats, 2 for error)
    """
    args = parse_arguments()

    # Load settings
    settings = SettingsManager()

    # Determine effective settings (CLI args override config)
    if args.skip_on_battery is not None:
        skip_on_battery = args.skip_on_battery
    else:
        skip_on_battery = settings.get("schedule_skip_on_battery", True)

    if args.auto_quarantine is not None:
        auto_quarantine = args.auto_quarantine
    else:
        auto_quarantine = settings.get("schedule_auto_quarantine", False)

    # Determine targets (CLI args override config)
    if args.targets:
        targets = args.targets
    else:
        targets = settings.get("schedule_targets", [])
        # If no targets configured, default to home directory
        if not targets:
            home = os.path.expanduser("~")
            targets = [home]

    return run_scheduled_scan(
        targets=targets,
        skip_on_battery=skip_on_battery,
        auto_quarantine=auto_quarantine,
        dry_run=args.dry_run,
        verbose=args.verbose
    )


if __name__ == "__main__":
    sys.exit(main())
