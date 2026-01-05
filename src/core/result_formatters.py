# ClamUI Result Formatters
"""
Scan result formatting utilities.

This module provides functions for:
- Formatting ScanResult objects as human-readable text reports
- Formatting ScanResult objects as CSV for spreadsheet export
- Generating exportable scan reports with timestamps and threat details
"""

import csv
import io
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scanner import ScanResult


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
