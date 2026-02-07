# ClamUI Scanner Base Module
"""
Shared utilities for ClamAV scanner implementations.

This module provides common functionality used by both Scanner (clamscan) and
DaemonScanner (clamdscan) to avoid code duplication:
- Process communication with cancellation support
- Streaming output with progress callbacks
- Process termination with graceful shutdown
- Scan log saving
- Error result creation
"""

import logging
import os
import select
import subprocess
from collections.abc import Callable

from .log_manager import LogEntry, LogManager
from .scanner_types import ScanResult, ScanStatus

logger = logging.getLogger(__name__)

# Timeout constants (seconds)
TERMINATE_GRACE_TIMEOUT = 5  # Time to wait after SIGTERM before SIGKILL
KILL_WAIT_TIMEOUT = 2  # Time to wait after SIGKILL
STREAM_POLL_TIMEOUT = 0.1  # select() timeout for checking cancellation between output reads


def communicate_with_cancel_check(
    process: subprocess.Popen,
    is_cancelled: Callable[[], bool],
) -> tuple[str, str, bool]:
    """
    Communicate with process while checking for cancellation.

    Polling Loop Strategy:
    - Uses process.communicate(timeout=0.5) instead of blocking wait
    - Checks is_cancelled() before each communicate() attempt
    - If timeout expires, loop continues to check cancellation again
    - If cancelled during wait, terminates process and drains remaining output
    - This provides ~500ms cancellation responsiveness (vs minutes for blocking wait)

    Why Not process.wait():
    - process.wait() blocks until completion with no timeout mechanism
    - Long scans would be uninterruptible without SIGTERM from another thread
    - communicate(timeout) gives us both output collection and cancellation points

    Uses a polling loop with timeout to allow periodic cancellation checks.
    This prevents the scan thread from blocking indefinitely on communicate().

    Args:
        process: The subprocess to communicate with.
        is_cancelled: Callable that returns True if operation was cancelled.

    Returns:
        Tuple of (stdout, stderr, was_cancelled).
    """
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []

    while True:
        if is_cancelled():
            # Terminate process and collect any remaining output
            try:
                process.terminate()
                stdout, stderr = process.communicate(timeout=2.0)
                stdout_parts.append(stdout or "")
                stderr_parts.append(stderr or "")
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            return "".join(stdout_parts), "".join(stderr_parts), True

        try:
            stdout, stderr = process.communicate(timeout=0.5)
            stdout_parts.append(stdout or "")
            stderr_parts.append(stderr or "")
            return "".join(stdout_parts), "".join(stderr_parts), False
        except subprocess.TimeoutExpired:
            continue  # Loop again, check cancel flag


def stream_process_output(
    process: subprocess.Popen,
    is_cancelled: Callable[[], bool],
    on_line: Callable[[str], None],
    poll_interval: float = STREAM_POLL_TIMEOUT,
) -> tuple[str, str, bool]:
    """
    Stream stdout line-by-line with cancellation support.

    Why select() + os.read() Instead of readline():
    - readline() blocks until it finds a newline character (could be seconds/minutes)
    - select() with timeout allows checking cancellation every poll_interval (0.1s default)
    - os.read() is truly non-blocking after select() returns readable
    - process.stdout.read() uses TextIOWrapper which loops internally, blocking on pipe
    - This combination provides real-time progress AND fast cancellation response

    Why os.read() Over process.stdout.read():
    - process.stdout is a TextIOWrapper (BufferedReader + encoding)
    - TextIOWrapper.read(n) tries to accumulate exactly n characters
    - It internally loops on the underlying pipe, blocking until it has n chars
    - os.read() is a raw syscall that returns immediately with available data
    - This gives us true non-blocking behavior after select() indicates readability

    Uses select/poll for non-blocking reads to maintain cancellation responsiveness.
    Each line from stdout is passed to the on_line callback in real-time.

    Args:
        process: The subprocess to communicate with (must have stdout=PIPE, stderr=PIPE).
        is_cancelled: Callable that returns True if operation was cancelled.
        on_line: Callback function called with each line from stdout.
        poll_interval: Time to wait for output before checking cancellation (seconds).

    Returns:
        Tuple of (stdout, stderr, was_cancelled).
        Note: stdout contains all accumulated output for final parsing.
    """
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []

    if process.stdout is None or process.stderr is None:
        # Fallback to blocking communicate if pipes not available
        logger.warning("stream_process_output called without stdout/stderr pipes")
        return communicate_with_cancel_check(process, is_cancelled)

    # Get file descriptor for stdout
    stdout_fd = process.stdout.fileno()
    incomplete_line = ""

    try:
        while True:
            # Check for cancellation first
            if is_cancelled():
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                # Drain remaining output via os.read() to avoid mixing
                # with the TextIOWrapper used by process.communicate()
                for fd, parts in [
                    (stdout_fd, stdout_parts),
                    (process.stderr.fileno(), stderr_parts),
                ]:
                    while True:
                        try:
                            raw = os.read(fd, 4096)
                            if not raw:
                                break
                            parts.append(raw.decode("utf-8", errors="replace"))
                        except OSError:
                            break
                return "".join(stdout_parts), "".join(stderr_parts), True

            # Check if process has finished
            if process.poll() is not None:
                # Process finished - drain remaining output via os.read()
                remaining_chunks = []
                while True:
                    try:
                        raw = os.read(stdout_fd, 4096)
                        if not raw:
                            break
                        remaining_chunks.append(raw.decode("utf-8", errors="replace"))
                    except OSError:
                        break
                remaining_stdout = "".join(remaining_chunks)

                stderr_fd = process.stderr.fileno()
                remaining_stderr_chunks = []
                while True:
                    try:
                        raw = os.read(stderr_fd, 4096)
                        if not raw:
                            break
                        remaining_stderr_chunks.append(raw.decode("utf-8", errors="replace"))
                    except OSError:
                        break
                remaining_stderr = "".join(remaining_stderr_chunks)

                if remaining_stdout:
                    # Process remaining data including incomplete line
                    data = incomplete_line + remaining_stdout
                    lines = data.split("\n")
                    for line in lines:
                        if line:  # Skip empty lines from split
                            on_line(line)
                    stdout_parts.append(data)
                elif incomplete_line:
                    # Process the final incomplete line
                    on_line(incomplete_line)
                    stdout_parts.append(incomplete_line)
                if remaining_stderr:
                    stderr_parts.append(remaining_stderr)
                break

            # Use select to wait for data with timeout
            readable, _, _ = select.select([stdout_fd], [], [], poll_interval)

            if readable:
                # Use os.read() for truly non-blocking reads.
                # process.stdout.read(n) uses TextIOWrapper which internally
                # loops to accumulate n chars, blocking on the pipe even after
                # select() returns readable.
                raw_bytes = os.read(stdout_fd, 4096)
                if not raw_bytes:
                    # EOF reached
                    continue

                chunk = raw_bytes.decode("utf-8", errors="replace")

                # Accumulate for final parsing
                stdout_parts.append(chunk)

                # Incomplete line handling: Buffer partial lines until newline arrives
                # - incomplete_line holds text from previous read that didn't end with \n
                # - Prepend it to current chunk to reassemble the full line
                # - lines[-1] becomes the new incomplete_line (empty string if chunk ended with \n)
                # - This ensures callbacks always receive complete lines
                # Process lines for callback
                data = incomplete_line + chunk
                lines = data.split("\n")

                # The last element might be incomplete (no newline yet)
                incomplete_line = lines[-1]

                # Process complete lines
                for line in lines[:-1]:
                    if line:  # Skip empty lines
                        on_line(line)

    except OSError as e:
        logger.warning(f"Error streaming process output: {e}")
        # Try to get any remaining output
        try:
            remaining_stdout, remaining_stderr = process.communicate(timeout=2.0)
            if remaining_stdout:
                stdout_parts.append(remaining_stdout)
            if remaining_stderr:
                stderr_parts.append(remaining_stderr)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    return "".join(stdout_parts), "".join(stderr_parts), False


def cleanup_process(process: subprocess.Popen | None) -> None:
    """
    Ensure a subprocess is properly terminated and cleaned up.

    Args:
        process: The subprocess to clean up, or None.
    """
    if process is None:
        return

    try:
        if process.poll() is None:  # Only kill if still running
            process.kill()
        process.wait(timeout=KILL_WAIT_TIMEOUT)
    except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
        pass


def terminate_process_gracefully(process: subprocess.Popen | None) -> None:
    """
    Terminate a process with graceful shutdown escalation.

    First sends SIGTERM, then escalates to SIGKILL if the process
    doesn't respond within the grace period.

    Args:
        process: The subprocess to terminate, or None.
    """
    if process is None:
        return

    # Step 1: SIGTERM (graceful)
    try:
        process.terminate()
    except (OSError, ProcessLookupError):
        # Process already gone
        return

    # Step 2: Wait for graceful termination
    try:
        process.wait(timeout=TERMINATE_GRACE_TIMEOUT)
    except subprocess.TimeoutExpired:
        # Step 3: SIGKILL (forceful)
        logger.warning("Process didn't terminate gracefully, killing")
        try:
            process.kill()
            process.wait(timeout=KILL_WAIT_TIMEOUT)
        except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
            pass  # Best effort


def save_scan_log(
    log_manager: LogManager,
    result: ScanResult,
    duration: float,
    suffix: str = "",
    scheduled: bool = False,
) -> None:
    """
    Save scan result to log.

    Args:
        log_manager: The LogManager instance to save to.
        result: The scan result.
        duration: Scan duration in seconds.
        suffix: Optional suffix for summary (e.g., "(daemon)").
        scheduled: Whether this was a scheduled scan.
    """
    # Map ScanStatus to string
    status_map = {
        ScanStatus.CLEAN: "clean",
        ScanStatus.INFECTED: "infected",
        ScanStatus.CANCELLED: "cancelled",
        ScanStatus.ERROR: "error",
    }
    scan_status = status_map.get(result.status, "error")

    # Convert threat details to dicts for the factory method
    threat_dicts = [
        {"file_path": t.file_path, "threat_name": t.threat_name} for t in result.threat_details
    ]

    entry = LogEntry.from_scan_result_data(
        scan_status=scan_status,
        path=result.path,
        duration=duration,
        scanned_files=result.scanned_files,
        scanned_dirs=result.scanned_dirs,
        infected_count=result.infected_count,
        threat_details=threat_dicts,
        error_message=result.error_message,
        stdout=result.stdout,
        suffix=suffix,
        scheduled=scheduled,
    )
    log_manager.save_log(entry)


def create_error_result(
    path: str,
    error_message: str,
    stderr: str = "",
) -> ScanResult:
    """
    Create a ScanResult for an error condition.

    Args:
        path: The path that was being scanned.
        error_message: The error message.
        stderr: Optional stderr content.

    Returns:
        A ScanResult with ERROR status.
    """
    return ScanResult(
        status=ScanStatus.ERROR,
        path=path,
        stdout="",
        stderr=stderr or error_message,
        exit_code=-1,
        infected_files=[],
        scanned_files=0,
        scanned_dirs=0,
        infected_count=0,
        error_message=error_message,
        threat_details=[],
    )


def create_cancelled_result(
    path: str,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = -1,
    scanned_files: int = 0,
    scanned_dirs: int = 0,
    infected_files: list[str] | None = None,
    infected_count: int = 0,
    threat_details: list | None = None,
) -> ScanResult:
    """
    Create a ScanResult for a cancelled operation.

    Args:
        path: The path that was being scanned.
        stdout: Captured stdout.
        stderr: Captured stderr.
        exit_code: The process exit code.
        scanned_files: Number of files scanned before cancellation.
        scanned_dirs: Number of directories scanned before cancellation.
        infected_files: List of infected file paths found before cancellation.
        infected_count: Number of infected files found before cancellation.
        threat_details: List of ThreatDetail objects found before cancellation.

    Returns:
        A ScanResult with CANCELLED status.
    """
    return ScanResult(
        status=ScanStatus.CANCELLED,
        path=path,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        infected_files=infected_files or [],
        scanned_files=scanned_files,
        scanned_dirs=scanned_dirs,
        infected_count=infected_count,
        error_message="Scan cancelled by user",
        threat_details=threat_details or [],
    )
