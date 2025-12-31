# ClamUI Test Configuration
"""
Pytest configuration and shared fixtures for ClamUI tests.

This file provides common test configuration. GTK/GI mocking is handled
by individual test files as needed since different tests require different
mocking strategies.
"""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest


# EICAR standard test string - recognized by antivirus software as a test file
# This string MUST be exact (any modification breaks detection)
# See: https://www.eicar.org/download-anti-malware-testfile/
EICAR_STRING = r"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


@pytest.fixture
def eicar_file(tmp_path: Path) -> Path:
    """
    Create a temporary EICAR test file for antivirus testing.

    The EICAR test file is a standard test file used to verify antivirus
    detection without using real malware. ClamAV classifies EICAR as:
    - Category: "Test"
    - Severity: "low"

    The file is automatically cleaned up after the test completes.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Yields:
        Path: Path to the temporary EICAR test file
    """
    eicar_path = tmp_path / "eicar_test_file.txt"
    try:
        eicar_path.write_text(EICAR_STRING)
        yield eicar_path
    finally:
        # Ensure cleanup even if test fails
        if eicar_path.exists():
            eicar_path.unlink()


@pytest.fixture
def eicar_directory(tmp_path: Path) -> Path:
    """
    Create a temporary directory containing an EICAR test file.

    Useful for testing directory scanning with infected files.
    The directory structure is:
        tmp_path/
            eicar_dir/
                eicar_test_file.txt (EICAR content)
                clean_file.txt (clean content)

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Yields:
        Path: Path to the temporary directory containing test files
    """
    eicar_dir = tmp_path / "eicar_dir"
    eicar_dir.mkdir()
    eicar_file_path = eicar_dir / "eicar_test_file.txt"
    clean_file_path = eicar_dir / "clean_file.txt"

    try:
        eicar_file_path.write_text(EICAR_STRING)
        clean_file_path.write_text("This is a clean file with no threats.")
        yield eicar_dir
    finally:
        # Ensure cleanup even if test fails
        if eicar_file_path.exists():
            eicar_file_path.unlink()
        if clean_file_path.exists():
            clean_file_path.unlink()
        if eicar_dir.exists():
            eicar_dir.rmdir()


@pytest.fixture
def clean_test_file(tmp_path: Path) -> Path:
    """
    Create a temporary clean test file for scanning.

    Useful for testing clean scan results.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Yields:
        Path: Path to the temporary clean test file
    """
    clean_path = tmp_path / "clean_test_file.txt"
    try:
        clean_path.write_text("This is a clean file with no malicious content.")
        yield clean_path
    finally:
        if clean_path.exists():
            clean_path.unlink()


@pytest.fixture
def mock_scanner():
    """
    Create a mock Scanner object for testing.

    Provides a pre-configured MagicMock that mimics the Scanner interface.
    Commonly used methods are pre-configured with sensible defaults:
    - scan_sync: Returns a clean ScanResult mock by default
    - scan_async: Returns a clean ScanResult mock by default
    - cancel_scan: Does nothing by default
    - _build_command: Returns a basic clamscan command

    The mock can be easily customized in individual tests by modifying
    return_value or side_effect on specific methods.

    Example usage:
        def test_something(mock_scanner):
            # Use default behavior
            result = mock_scanner.scan_sync("/path")

            # Or customize for specific test
            mock_scanner.scan_sync.return_value.status = ScanStatus.INFECTED
            mock_scanner.scan_sync.return_value.infected_count = 1

    Yields:
        MagicMock: A mock Scanner object with pre-configured methods
    """
    scanner = mock.MagicMock()

    # Configure default scan result (clean scan)
    clean_result = mock.MagicMock()
    clean_result.status = "clean"
    clean_result.is_clean = True
    clean_result.has_threats = False
    clean_result.infected_count = 0
    clean_result.scanned_files = 0
    clean_result.scanned_dirs = 0
    clean_result.infected_files = []
    clean_result.threat_details = []
    clean_result.error_message = None
    clean_result.stdout = ""
    clean_result.stderr = ""
    clean_result.exit_code = 0

    # Configure default return values for scanner methods
    scanner.scan_sync.return_value = clean_result
    scanner.scan_async.return_value = clean_result
    scanner.cancel_scan.return_value = None
    scanner._build_command.return_value = ["clamscan", "-i"]
    scanner._scan_cancelled = False
    scanner._current_process = None

    yield scanner
