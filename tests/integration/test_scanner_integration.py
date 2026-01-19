# ClamUI Scanner Integration Tests
"""
Integration tests for the scanner module covering complete scan workflows.

These tests verify the scanner's end-to-end behavior including:
- Sync scan workflow (file selection -> scan execution -> results display)
- Async scan workflow with callback verification
- EICAR test file detection and classification
- Scan cancellation handling

All tests mock ClamAV subprocess execution to run without requiring ClamAV installed.
"""

import subprocess
import sys
from unittest import mock

import pytest


def _clear_src_modules():
    """Clear all cached src.* modules to ensure clean imports."""
    modules_to_remove = [
        mod for mod in list(sys.modules.keys()) if mod.startswith("src.")
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]


# Global references for scanner classes - populated by fixture
Scanner = None
ScanResult = None
ScanStatus = None
ThreatDetail = None


@pytest.fixture(autouse=True)
def ensure_fresh_scanner_import():
    """Ensure scanner module is freshly imported for each integration test.

    This fixture clears cached src modules before each test to prevent
    stale module references when running alongside test_scanner.py which
    also clears modules.
    """
    global Scanner, ScanResult, ScanStatus, ThreatDetail

    # Clear any cached src modules before test
    _clear_src_modules()

    # Import fresh
    # Reset flatpak cache after imports
    import src.core.flatpak as flatpak_module
    from src.core.scanner import Scanner as _Scanner
    from src.core.scanner import ScanResult as _ScanResult
    from src.core.scanner import ScanStatus as _ScanStatus
    from src.core.scanner import ThreatDetail as _ThreatDetail

    flatpak_module._flatpak_detected = None

    Scanner = _Scanner
    ScanResult = _ScanResult
    ScanStatus = _ScanStatus
    ThreatDetail = _ThreatDetail

    yield


@pytest.mark.integration
class TestScannerSyncWorkflow:
    """Integration tests for the synchronous scan workflow."""

    def test_scanner_sync_workflow(self, tmp_path):
        """
        Test complete sync scan workflow: file selection -> scan execution -> results.

        This test verifies the full scan_sync workflow:
        1. Create a test file to scan
        2. Execute scan_sync with mocked subprocess
        3. Verify ScanResult contains expected data
        4. Verify all ScanResult properties are correctly populated
        """
        # Step 1: Create test file (simulates file selection)
        test_file = tmp_path / "test_document.txt"
        test_file.write_text("This is a clean test document for scanning.")

        scanner = Scanner()

        # Step 2: Mock ClamAV subprocess execution
        mock_stdout = f"""
{test_file}: OK

----------- SCAN SUMMARY -----------
Known viruses: 8000000
Engine version: 1.2.3
Scanned directories: 0
Scanned files: 1
Infected files: 0
Data scanned: 0.01 MB
Data read: 0.01 MB
Time: 0.100 sec (0 m 0 s)
"""

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.return_value = (mock_stdout, "")
                            mock_process.returncode = 0
                            mock_popen.return_value = mock_process

                            # Step 3: Execute scan
                            result = scanner.scan_sync(str(test_file))

        # Step 4: Verify ScanResult structure
        assert isinstance(result, ScanResult)
        assert result.status == ScanStatus.CLEAN
        assert result.path == str(test_file)
        assert result.exit_code == 0

        # Verify properties
        assert result.is_clean is True
        assert result.has_threats is False

        # Verify counts
        assert result.infected_count == 0
        assert result.scanned_files == 1
        assert len(result.infected_files) == 0
        assert len(result.threat_details) == 0

        # Verify error handling
        assert result.error_message is None

    def test_scanner_sync_workflow_infected_file(self, tmp_path):
        """
        Test sync scan workflow with infected file detection.

        Verifies that when clamscan detects a threat:
        1. Status is set to INFECTED
        2. infected_files list is populated
        3. threat_details are extracted with proper classification
        4. has_threats property returns True
        """
        test_file = tmp_path / "infected_file.exe"
        test_file.write_text("simulated infected content")

        scanner = Scanner()

        # Mock ClamAV output with detected threat
        mock_stdout = f"""
{test_file}: Win.Trojan.Agent FOUND

----------- SCAN SUMMARY -----------
Scanned directories: 0
Scanned files: 1
Infected files: 1
Data scanned: 0.01 MB
Time: 0.100 sec (0 m 0 s)
"""

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.return_value = (mock_stdout, "")
                            mock_process.returncode = (
                                1  # ClamAV exit code 1 = virus found
                            )
                            mock_popen.return_value = mock_process

                            result = scanner.scan_sync(str(test_file))

        # Verify infected status
        assert result.status == ScanStatus.INFECTED
        assert result.is_clean is False
        assert result.has_threats is True

        # Verify infected files list
        assert result.infected_count == 1
        assert len(result.infected_files) == 1
        assert str(test_file) in result.infected_files

        # Verify threat details
        assert len(result.threat_details) == 1
        threat = result.threat_details[0]
        assert isinstance(threat, ThreatDetail)
        assert threat.file_path == str(test_file)
        assert threat.threat_name == "Win.Trojan.Agent"
        assert threat.category == "Trojan"
        assert threat.severity == "high"

    def test_scanner_sync_workflow_directory(self, tmp_path):
        """
        Test sync scan workflow with directory scanning.

        Verifies that directory scanning:
        1. Scans multiple files in directory
        2. Properly counts scanned files and directories
        3. Can detect multiple threats
        """
        # Create directory with multiple files
        scan_dir = tmp_path / "documents"
        scan_dir.mkdir()
        (scan_dir / "file1.txt").write_text("Clean file 1")
        (scan_dir / "file2.txt").write_text("Clean file 2")
        (scan_dir / "file3.txt").write_text("Clean file 3")

        scanner = Scanner()

        mock_stdout = f"""
{scan_dir}/file1.txt: OK
{scan_dir}/file2.txt: OK
{scan_dir}/file3.txt: OK

----------- SCAN SUMMARY -----------
Scanned directories: 1
Scanned files: 3
Infected files: 0
Data scanned: 0.01 MB
Time: 0.200 sec (0 m 0 s)
"""

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.return_value = (mock_stdout, "")
                            mock_process.returncode = 0
                            mock_popen.return_value = mock_process

                            result = scanner.scan_sync(str(scan_dir), recursive=True)

        # Verify clean scan
        assert result.status == ScanStatus.CLEAN
        assert result.is_clean is True

        # Verify counts
        assert result.scanned_files == 3
        assert result.scanned_dirs == 1
        assert result.infected_count == 0

    def test_scanner_sync_workflow_error_handling(self, tmp_path):
        """
        Test sync scan workflow error handling.

        Verifies that when ClamAV reports an error:
        1. Status is set to ERROR
        2. error_message is populated
        3. Exit code is captured
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        mock_stderr = "ERROR: Can't open database file"

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.return_value = ("", mock_stderr)
                            mock_process.returncode = 2  # ClamAV exit code 2 = error
                            mock_popen.return_value = mock_process

                            result = scanner.scan_sync(str(test_file))

        # Verify error status
        assert result.status == ScanStatus.ERROR
        assert result.is_clean is False
        assert result.has_threats is False
        assert result.exit_code == 2
        assert result.error_message is not None

    def test_scanner_sync_workflow_invalid_path(self):
        """
        Test sync scan workflow with invalid path.

        Verifies that scanning a non-existent path:
        1. Returns ERROR status
        2. Contains appropriate error message
        """
        scanner = Scanner()

        # Try to scan non-existent path
        result = scanner.scan_sync("/nonexistent/path/that/does/not/exist")

        # Verify error handling for invalid path
        assert result.status == ScanStatus.ERROR
        assert result.error_message is not None
        assert result.exit_code == -1

    def test_scanner_sync_workflow_subprocess_called_correctly(self, tmp_path):
        """
        Test that subprocess.Popen is called with correct arguments.

        Verifies the scanner correctly builds the clamscan command and
        passes it to subprocess.Popen.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    # Mock check_clamd_connection to force clamscan path (in "auto" mode,
                    # daemon is tried first if available)
                    with mock.patch(
                        "src.core.scanner.check_clamd_connection",
                        return_value=(False, "not running"),
                    ):
                        with mock.patch(
                            "src.core.scanner.check_clamav_installed",
                            return_value=(True, "1.2.3"),
                        ):
                            with mock.patch("subprocess.Popen") as mock_popen:
                                mock_process = mock.MagicMock()
                                mock_process.communicate.return_value = ("", "")
                                mock_process.returncode = 0
                                mock_popen.return_value = mock_process

                                scanner.scan_sync(str(test_file))

                                # Verify Popen was called
                                mock_popen.assert_called_once()

                                # Verify command arguments
                                call_args = mock_popen.call_args
                                cmd = call_args[0][0]

                                assert cmd[0] == "/usr/bin/clamscan"
                                assert "-i" in cmd
                                assert str(test_file) in cmd

    def test_scanner_sync_workflow_multiple_threats(self, tmp_path):
        """
        Test sync scan workflow with multiple threats of varying severity.

        Verifies that scanner correctly:
        1. Detects multiple infected files
        2. Classifies each threat appropriately
        3. Assigns correct severity levels
        """
        scan_dir = tmp_path / "infected_dir"
        scan_dir.mkdir()

        scanner = Scanner()

        # Mock output with multiple different threats
        mock_stdout = f"""
{scan_dir}/critical.exe: Ransomware.Locky FOUND
{scan_dir}/high.exe: Trojan.Banker FOUND
{scan_dir}/medium.exe: Adware.Toolbar FOUND
{scan_dir}/low.exe: Eicar-Test-Signature FOUND

----------- SCAN SUMMARY -----------
Scanned directories: 1
Scanned files: 4
Infected files: 4
"""

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.return_value = (mock_stdout, "")
                            mock_process.returncode = 1
                            mock_popen.return_value = mock_process

                            result = scanner.scan_sync(str(scan_dir), recursive=True)

        # Verify all threats detected
        assert result.status == ScanStatus.INFECTED
        assert result.infected_count == 4
        assert len(result.threat_details) == 4

        # Build a map for easy verification
        threat_map = {t.threat_name: t for t in result.threat_details}

        # Verify severity classification
        assert threat_map["Ransomware.Locky"].severity == "critical"
        assert threat_map["Ransomware.Locky"].category == "Ransomware"

        assert threat_map["Trojan.Banker"].severity == "high"
        assert threat_map["Trojan.Banker"].category == "Trojan"

        assert threat_map["Adware.Toolbar"].severity == "medium"
        assert threat_map["Adware.Toolbar"].category == "Adware"

        assert threat_map["Eicar-Test-Signature"].severity == "low"
        assert threat_map["Eicar-Test-Signature"].category == "Test"


@pytest.mark.integration
def test_eicar_detection(eicar_file):
    """
    Test EICAR test file detection and classification.

    EICAR (European Institute for Computer Antivirus Research) test file is a
    standard test file used to verify antivirus detection without using real malware.

    This test verifies that when scanning an EICAR test file:
    1. The scanner detects it as infected (status=INFECTED)
    2. The threat is classified with category='Test'
    3. The threat severity is 'low' (as it's a test file, not real malware)
    4. The threat details are correctly populated

    Args:
        eicar_file: pytest fixture that creates a temp EICAR test file
    """
    scanner = Scanner()

    # Mock ClamAV output for EICAR detection
    # ClamAV identifies EICAR with the signature "Eicar-Test-Signature"
    mock_stdout = f"""
{eicar_file}: Eicar-Test-Signature FOUND

----------- SCAN SUMMARY -----------
Known viruses: 8000000
Engine version: 1.2.3
Scanned directories: 0
Scanned files: 1
Infected files: 1
Data scanned: 0.01 MB
Data read: 0.01 MB
Time: 0.100 sec (0 m 0 s)
"""

    with mock.patch("src.core.scanner.is_flatpak", return_value=False):
        with mock.patch(
            "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
        ):
            with mock.patch(
                "src.core.scanner.wrap_host_command", side_effect=lambda x: x
            ):
                with mock.patch(
                    "src.core.scanner.check_clamav_installed",
                    return_value=(True, "1.2.3"),
                ):
                    with mock.patch("subprocess.Popen") as mock_popen:
                        mock_process = mock.MagicMock()
                        mock_process.communicate.return_value = (mock_stdout, "")
                        mock_process.returncode = 1  # ClamAV exit code 1 = virus found
                        mock_popen.return_value = mock_process

                        # Execute scan on EICAR file
                        result = scanner.scan_sync(str(eicar_file))

    # Verify EICAR detection
    assert result.status == ScanStatus.INFECTED, "EICAR should be detected as infected"
    assert result.is_clean is False
    assert result.has_threats is True

    # Verify infected count
    assert result.infected_count == 1
    assert len(result.infected_files) == 1
    assert str(eicar_file) in result.infected_files

    # Verify threat details
    assert len(result.threat_details) == 1
    threat = result.threat_details[0]
    assert isinstance(threat, ThreatDetail)
    assert threat.file_path == str(eicar_file)
    assert threat.threat_name == "Eicar-Test-Signature"

    # CRITICAL: Verify EICAR-specific classification
    # EICAR test files must be classified as:
    # - category='Test' (not a real threat category)
    # - severity='low' (minimal risk since it's just a test file)
    assert (
        threat.category == "Test"
    ), f"EICAR category should be 'Test', got '{threat.category}'"
    assert (
        threat.severity == "low"
    ), f"EICAR severity should be 'low', got '{threat.severity}'"


@pytest.mark.integration
class TestScannerAsyncWorkflow:
    """Integration tests for the asynchronous scan workflow with callback verification."""

    def test_scanner_async_workflow(self, tmp_path):
        """
        Test async scan workflow with callback verification.

        This test verifies the full scan_async workflow:
        1. Create a test file to scan
        2. Execute scan_async with mocked subprocess
        3. Verify callback is invoked with ScanResult
        4. Verify GLib.idle_add is used to schedule callback on main thread
        5. Verify all ScanResult properties are correctly populated
        """
        import threading

        # Step 1: Create test file (simulates file selection)
        test_file = tmp_path / "test_async_document.txt"
        test_file.write_text("This is a test document for async scanning.")

        scanner = Scanner()

        # Step 2: Mock ClamAV subprocess execution
        mock_stdout = f"""
{test_file}: OK

----------- SCAN SUMMARY -----------
Known viruses: 8000000
Engine version: 1.2.3
Scanned directories: 0
Scanned files: 1
Infected files: 0
Data scanned: 0.01 MB
Data read: 0.01 MB
Time: 0.100 sec (0 m 0 s)
"""

        # Track callback invocation
        callback_results = []
        callback_event = threading.Event()

        def test_callback(result: ScanResult):
            """Callback to capture scan result."""
            callback_results.append(result)
            callback_event.set()

        # Track GLib.idle_add calls to verify main thread scheduling
        glib_idle_add_calls = []

        def mock_glib_idle_add(callback_func, *args):
            """Mock GLib.idle_add to capture and immediately invoke callback."""
            glib_idle_add_calls.append((callback_func, args))
            # Immediately invoke the callback (simulates GTK main loop)
            return callback_func(*args)

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.return_value = (mock_stdout, "")
                            mock_process.returncode = 0
                            mock_popen.return_value = mock_process

                            # Mock GLib.idle_add in the scanner module
                            with mock.patch(
                                "src.core.scanner.GLib.idle_add",
                                side_effect=mock_glib_idle_add,
                            ):
                                # Step 3: Execute async scan
                                scanner.scan_async(str(test_file), test_callback)

                                # Wait for callback to be invoked (with timeout)
                                callback_received = callback_event.wait(timeout=5.0)

        # Step 4: Verify callback was invoked
        assert callback_received, "Callback was not invoked within timeout"
        assert len(callback_results) == 1, "Callback should be invoked exactly once"

        # Verify GLib.idle_add was used for main thread scheduling
        assert len(glib_idle_add_calls) == 1, "GLib.idle_add should be called once"
        idle_callback, idle_args = glib_idle_add_calls[0]
        assert (
            idle_callback == test_callback
        ), "GLib.idle_add should schedule our callback"

        # Step 5: Verify ScanResult structure
        result = callback_results[0]
        assert isinstance(result, ScanResult)
        assert result.status == ScanStatus.CLEAN
        assert result.path == str(test_file)
        assert result.exit_code == 0

        # Verify properties
        assert result.is_clean is True
        assert result.has_threats is False

        # Verify counts
        assert result.infected_count == 0
        assert result.scanned_files == 1
        assert len(result.infected_files) == 0
        assert len(result.threat_details) == 0

        # Verify error handling
        assert result.error_message is None

    def test_scanner_async_workflow_with_infected_file(self, tmp_path):
        """
        Test async scan workflow with infected file detection.

        Verifies that async scan correctly:
        1. Detects infected files
        2. Invokes callback with INFECTED status
        3. Populates threat_details with correct classification
        """
        import threading

        test_file = tmp_path / "infected_async.exe"
        test_file.write_text("simulated infected content")

        scanner = Scanner()

        mock_stdout = f"""
{test_file}: Win.Trojan.Agent FOUND

----------- SCAN SUMMARY -----------
Scanned directories: 0
Scanned files: 1
Infected files: 1
Data scanned: 0.01 MB
Time: 0.100 sec (0 m 0 s)
"""

        callback_results = []
        callback_event = threading.Event()

        def test_callback(result: ScanResult):
            callback_results.append(result)
            callback_event.set()

        def mock_glib_idle_add(callback_func, *args):
            return callback_func(*args)

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.return_value = (mock_stdout, "")
                            mock_process.returncode = (
                                1  # ClamAV exit code 1 = virus found
                            )
                            mock_popen.return_value = mock_process

                            with mock.patch(
                                "src.core.scanner.GLib.idle_add",
                                side_effect=mock_glib_idle_add,
                            ):
                                scanner.scan_async(str(test_file), test_callback)
                                callback_received = callback_event.wait(timeout=5.0)

        assert callback_received, "Callback was not invoked within timeout"

        result = callback_results[0]
        assert result.status == ScanStatus.INFECTED
        assert result.is_clean is False
        assert result.has_threats is True

        # Verify threat details
        assert len(result.threat_details) == 1
        threat = result.threat_details[0]
        assert isinstance(threat, ThreatDetail)
        assert threat.file_path == str(test_file)
        assert threat.threat_name == "Win.Trojan.Agent"
        assert threat.category == "Trojan"
        assert threat.severity == "high"

    def test_scanner_async_workflow_callback_receives_error(self, tmp_path):
        """
        Test async scan workflow error handling via callback.

        Verifies that errors are properly propagated to the callback.
        """
        import threading

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        mock_stderr = "ERROR: Can't open database file"

        callback_results = []
        callback_event = threading.Event()

        def test_callback(result: ScanResult):
            callback_results.append(result)
            callback_event.set()

        def mock_glib_idle_add(callback_func, *args):
            return callback_func(*args)

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.return_value = ("", mock_stderr)
                            mock_process.returncode = 2  # ClamAV exit code 2 = error
                            mock_popen.return_value = mock_process

                            with mock.patch(
                                "src.core.scanner.GLib.idle_add",
                                side_effect=mock_glib_idle_add,
                            ):
                                scanner.scan_async(str(test_file), test_callback)
                                callback_received = callback_event.wait(timeout=5.0)

        assert callback_received, "Callback was not invoked within timeout"

        result = callback_results[0]
        assert result.status == ScanStatus.ERROR
        assert result.exit_code == 2
        assert result.error_message is not None

    def test_scanner_async_workflow_runs_in_background_thread(self, tmp_path):
        """
        Test that async scan runs in a background thread (non-blocking).

        Verifies that scan_async returns immediately and scan executes in background.
        """
        import threading
        import time

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        scanner = Scanner()

        mock_stdout = f"{test_file}: OK\n"

        callback_results = []
        callback_event = threading.Event()
        scan_thread_ids = []
        main_thread_id = threading.current_thread().ident

        def test_callback(result: ScanResult):
            callback_results.append(result)
            callback_event.set()

        def mock_glib_idle_add(callback_func, *args):
            return callback_func(*args)

        def mock_communicate(timeout=None):
            # Record the thread ID where scan executes
            scan_thread_ids.append(threading.current_thread().ident)
            return (mock_stdout, "")

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.side_effect = mock_communicate
                            mock_process.returncode = 0
                            mock_popen.return_value = mock_process

                            with mock.patch(
                                "src.core.scanner.GLib.idle_add",
                                side_effect=mock_glib_idle_add,
                            ):
                                # Record time before calling scan_async
                                start_time = time.monotonic()

                                # Call scan_async - should return immediately
                                scanner.scan_async(str(test_file), test_callback)

                                # Should return immediately (non-blocking)
                                elapsed = time.monotonic() - start_time

                                # Wait for callback
                                callback_event.wait(timeout=5.0)

        # Verify scan_async returned quickly (non-blocking)
        assert elapsed < 0.5, f"scan_async took {elapsed}s, should be non-blocking"

        # Verify scan executed in a different thread than main
        assert len(scan_thread_ids) == 1
        assert (
            scan_thread_ids[0] != main_thread_id
        ), "Scan should run in background thread"

    def test_scanner_async_workflow_with_recursive_directory(self, tmp_path):
        """
        Test async scan workflow with recursive directory scanning.

        Verifies that async scan correctly handles directory scans.
        """
        import threading

        # Create directory with multiple files
        scan_dir = tmp_path / "async_documents"
        scan_dir.mkdir()
        (scan_dir / "file1.txt").write_text("Clean file 1")
        (scan_dir / "file2.txt").write_text("Clean file 2")
        (scan_dir / "file3.txt").write_text("Clean file 3")

        scanner = Scanner()

        mock_stdout = f"""
{scan_dir}/file1.txt: OK
{scan_dir}/file2.txt: OK
{scan_dir}/file3.txt: OK

----------- SCAN SUMMARY -----------
Scanned directories: 1
Scanned files: 3
Infected files: 0
Data scanned: 0.01 MB
Time: 0.200 sec (0 m 0 s)
"""

        callback_results = []
        callback_event = threading.Event()

        def test_callback(result: ScanResult):
            callback_results.append(result)
            callback_event.set()

        def mock_glib_idle_add(callback_func, *args):
            return callback_func(*args)

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.return_value = (mock_stdout, "")
                            mock_process.returncode = 0
                            mock_popen.return_value = mock_process

                            with mock.patch(
                                "src.core.scanner.GLib.idle_add",
                                side_effect=mock_glib_idle_add,
                            ):
                                # Scan directory with recursive=True
                                scanner.scan_async(
                                    str(scan_dir), test_callback, recursive=True
                                )
                                callback_received = callback_event.wait(timeout=5.0)

        assert callback_received, "Callback was not invoked within timeout"

        result = callback_results[0]
        assert result.status == ScanStatus.CLEAN
        assert result.is_clean is True
        assert result.scanned_files == 3
        assert result.scanned_dirs == 1

    def test_scanner_async_workflow_multiple_threats(self, tmp_path):
        """
        Test async scan workflow with multiple threat detection.

        Verifies that async scan correctly handles multiple threats
        with varying severity levels.
        """
        import threading

        scan_dir = tmp_path / "infected_dir"
        scan_dir.mkdir()

        scanner = Scanner()

        mock_stdout = f"""
{scan_dir}/critical.exe: Ransomware.Locky FOUND
{scan_dir}/high.exe: Trojan.Banker FOUND
{scan_dir}/medium.exe: Adware.Toolbar FOUND
{scan_dir}/low.exe: Eicar-Test-Signature FOUND

----------- SCAN SUMMARY -----------
Scanned directories: 1
Scanned files: 4
Infected files: 4
"""

        callback_results = []
        callback_event = threading.Event()

        def test_callback(result: ScanResult):
            callback_results.append(result)
            callback_event.set()

        def mock_glib_idle_add(callback_func, *args):
            return callback_func(*args)

        with mock.patch("src.core.scanner.is_flatpak", return_value=False):
            with mock.patch(
                "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
            ):
                with mock.patch(
                    "src.core.scanner.wrap_host_command", side_effect=lambda x: x
                ):
                    with mock.patch(
                        "src.core.scanner.check_clamav_installed",
                        return_value=(True, "1.2.3"),
                    ):
                        with mock.patch("subprocess.Popen") as mock_popen:
                            mock_process = mock.MagicMock()
                            mock_process.communicate.return_value = (mock_stdout, "")
                            mock_process.returncode = 1
                            mock_popen.return_value = mock_process

                            with mock.patch(
                                "src.core.scanner.GLib.idle_add",
                                side_effect=mock_glib_idle_add,
                            ):
                                scanner.scan_async(
                                    str(scan_dir), test_callback, recursive=True
                                )
                                callback_received = callback_event.wait(timeout=5.0)

        assert callback_received, "Callback was not invoked within timeout"

        result = callback_results[0]
        assert result.status == ScanStatus.INFECTED
        assert result.infected_count == 4
        assert len(result.threat_details) == 4

        # Build a map for easy verification
        threat_map = {t.threat_name: t for t in result.threat_details}

        # Verify severity classification
        assert threat_map["Ransomware.Locky"].severity == "critical"
        assert threat_map["Trojan.Banker"].severity == "high"
        assert threat_map["Adware.Toolbar"].severity == "medium"
        assert threat_map["Eicar-Test-Signature"].severity == "low"


@pytest.mark.integration
def test_scan_cancellation(tmp_path):
    """
    Test scan cancellation handling.

    This test verifies that when a scan is cancelled:
    1. The cancel() method sets the internal cancelled flag
    2. The subprocess is terminated
    3. The result status is ScanStatus.CANCELLED
    4. The error_message indicates user cancellation
    5. The result contains expected default values for cancelled scans

    The test simulates a running scan and triggers cancellation mid-execution
    to verify the scanner properly handles the cancellation request.
    """
    import threading

    # Create test file to scan
    test_file = tmp_path / "test_cancel.txt"
    test_file.write_text("This is a test file for cancellation testing.")

    scanner = Scanner()

    # Track callback invocation
    callback_results = []
    callback_event = threading.Event()

    def test_callback(result: ScanResult):
        """Callback to capture scan result."""
        callback_results.append(result)
        callback_event.set()

    def mock_glib_idle_add(callback_func, *args):
        """Mock GLib.idle_add to capture and immediately invoke callback."""
        return callback_func(*args)

    # Track communicate call count for proper cancellation simulation
    call_count = [0]

    def mock_communicate(timeout=None):
        """
        Mock communicate that simulates a long-running scan with cancellation.

        The _communicate_with_cancel_check method polls with timeout=0.5:
        1. First call: Set cancel event and raise TimeoutExpired to force loop iteration
        2. Second call: Return empty output for cleanup after termination
        """
        call_count[0] += 1
        if call_count[0] == 1:
            # First call: simulate process still running, set cancel event
            scanner._cancel_event.set()
            raise subprocess.TimeoutExpired(cmd="clamscan", timeout=0.5)
        # Second call: return output after termination
        return ("", "")

    with mock.patch("src.core.scanner.is_flatpak", return_value=False):
        with mock.patch(
            "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
        ):
            with mock.patch(
                "src.core.scanner.wrap_host_command", side_effect=lambda x: x
            ):
                with mock.patch(
                    "src.core.scanner.check_clamav_installed",
                    return_value=(True, "1.2.3"),
                ):
                    with mock.patch("subprocess.Popen") as mock_popen:
                        mock_process = mock.MagicMock()
                        mock_process.communicate.side_effect = mock_communicate
                        mock_process.returncode = -15  # SIGTERM exit code
                        mock_popen.return_value = mock_process

                        with mock.patch(
                            "src.core.scanner.GLib.idle_add",
                            side_effect=mock_glib_idle_add,
                        ):
                            # Execute async scan
                            scanner.scan_async(str(test_file), test_callback)

                            # Wait for callback to be invoked
                            callback_received = callback_event.wait(timeout=5.0)

    # Verify callback was invoked
    assert callback_received, "Callback was not invoked within timeout"
    assert len(callback_results) == 1, "Callback should be invoked exactly once"

    # Verify cancellation result
    result = callback_results[0]
    assert isinstance(result, ScanResult)

    # CRITICAL: Verify ScanStatus.CANCELLED
    assert (
        result.status == ScanStatus.CANCELLED
    ), f"Expected ScanStatus.CANCELLED, got {result.status}"

    # Verify cancellation properties
    assert result.path == str(test_file)
    assert result.is_clean is False  # Cancelled is not clean
    assert result.has_threats is False  # Cancelled has no threats

    # Verify error message indicates cancellation
    assert result.error_message is not None
    assert "cancel" in result.error_message.lower()

    # Verify default values for cancelled scan
    assert result.infected_count == 0
    assert result.scanned_files == 0
    assert result.scanned_dirs == 0
    assert len(result.infected_files) == 0
    assert len(result.threat_details) == 0


@pytest.mark.integration
def test_scan_cancellation_via_cancel_method(tmp_path):
    """
    Test scan cancellation via the cancel() method.

    This test verifies that calling scanner.cancel() during an active scan:
    1. Sets the internal _cancel_event
    2. Calls terminate() on the subprocess
    3. The scan result reflects the cancellation

    This tests the explicit cancel() API rather than internal flag setting.
    """
    import threading
    import time

    # Create test file to scan
    test_file = tmp_path / "test_cancel_method.txt"
    test_file.write_text("Test content for cancel method testing.")

    scanner = Scanner()

    # Track callback invocation
    callback_results = []
    callback_event = threading.Event()
    process_started_event = threading.Event()

    def test_callback(result: ScanResult):
        """Callback to capture scan result."""
        callback_results.append(result)
        callback_event.set()

    def mock_glib_idle_add(callback_func, *args):
        """Mock GLib.idle_add to capture and immediately invoke callback."""
        return callback_func(*args)

    # Track communicate call count for proper cancellation simulation
    call_count = [0]

    def mock_communicate(timeout=None):
        """
        Mock communicate that signals when process starts and allows cancel().

        The _communicate_with_cancel_check method polls with timeout=0.5:
        1. First call: Signal process started, raise TimeoutExpired to keep loop running
        2. Main test calls scanner.cancel() which sets _cancel_event
        3. Loop detects cancellation, calls terminate() then communicate(timeout=2.0)
        4. Second call: Return empty output for cleanup
        """
        call_count[0] += 1
        if call_count[0] == 1:
            # First call: signal process started
            process_started_event.set()
            # Wait a bit to allow cancel() to be called
            time.sleep(0.2)
            # Raise TimeoutExpired to force loop to check cancel flag
            raise subprocess.TimeoutExpired(cmd="clamscan", timeout=0.5)
        # Second call: return output after termination
        return ("", "")

    with mock.patch("src.core.scanner.is_flatpak", return_value=False):
        with mock.patch(
            "src.core.scanner.get_clamav_path", return_value="/usr/bin/clamscan"
        ):
            with mock.patch(
                "src.core.scanner.wrap_host_command", side_effect=lambda x: x
            ):
                with mock.patch(
                    "src.core.scanner.check_clamav_installed",
                    return_value=(True, "1.2.3"),
                ):
                    with mock.patch("subprocess.Popen") as mock_popen:
                        mock_process = mock.MagicMock()
                        mock_process.communicate.side_effect = mock_communicate
                        mock_process.returncode = -15  # SIGTERM exit code
                        mock_popen.return_value = mock_process

                        with mock.patch(
                            "src.core.scanner.GLib.idle_add",
                            side_effect=mock_glib_idle_add,
                        ):
                            # Start async scan
                            scanner.scan_async(str(test_file), test_callback)

                            # Wait for process to start
                            process_started = process_started_event.wait(timeout=2.0)
                            assert process_started, "Process did not start"

                            # Call cancel() method - this should:
                            # 1. Set _cancel_event
                            # 2. Call terminate() on the subprocess
                            scanner.cancel()

                            # Wait for callback to be invoked
                            callback_received = callback_event.wait(timeout=5.0)

    # Verify callback was invoked
    assert callback_received, "Callback was not invoked within timeout"

    # Verify cancellation result
    result = callback_results[0]
    assert (
        result.status == ScanStatus.CANCELLED
    ), f"Expected ScanStatus.CANCELLED, got {result.status}"

    # Verify cancel() was effective
    assert scanner._cancel_event.is_set() is True

    # Verify terminate was called on the process
    # Note: terminate() may be called twice - once by cancel() and once by
    # _communicate_with_cancel_check() when it detects the cancellation flag
    mock_process.terminate.assert_called()

    # Verify result properties
    assert result.error_message is not None
    assert "cancel" in result.error_message.lower()
