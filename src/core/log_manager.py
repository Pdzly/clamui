# ClamUI Log Manager Module
"""
Log manager module for ClamUI providing log persistence and retrieval.
Stores scan/update operation logs and provides daemon log access.
"""

import json
import os
import random
import subprocess
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from gi.repository import GLib

from .utils import is_flatpak, which_host_command, wrap_host_command


class LogType(Enum):
    """Type of log entry."""
    SCAN = "scan"
    UPDATE = "update"


class DaemonStatus(Enum):
    """Status of the clamd daemon."""
    RUNNING = "running"
    STOPPED = "stopped"
    NOT_INSTALLED = "not_installed"
    UNKNOWN = "unknown"


@dataclass
class LogEntry:
    """A single log entry for a scan or update operation."""
    id: str
    timestamp: str  # ISO format string for JSON serialization
    type: str  # "scan" or "update"
    status: str  # e.g., "clean", "infected", "success", "error"
    summary: str
    details: str
    path: Optional[str] = None  # Scanned path (for scans)
    duration: float = 0.0  # Operation duration in seconds
    scheduled: bool = False  # Whether this was a scheduled automatic scan

    @classmethod
    def create(
        cls,
        log_type: str,
        status: str,
        summary: str,
        details: str,
        path: Optional[str] = None,
        duration: float = 0.0,
        scheduled: bool = False
    ) -> "LogEntry":
        """
        Create a new LogEntry with auto-generated id and timestamp.

        Args:
            log_type: Type of operation ("scan" or "update")
            status: Status of the operation
            summary: Brief description of the operation
            details: Full output/details
            path: Scanned path (for scan operations)
            duration: Operation duration in seconds
            scheduled: Whether this was a scheduled automatic scan

        Returns:
            New LogEntry instance
        """
        return cls(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            type=log_type,
            status=status,
            summary=summary,
            details=details,
            path=path,
            duration=duration,
            scheduled=scheduled
        )

    def to_dict(self) -> dict:
        """Convert LogEntry to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        """Create LogEntry from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            type=data.get("type", "unknown"),
            status=data.get("status", "unknown"),
            summary=data.get("summary", ""),
            details=data.get("details", ""),
            path=data.get("path"),
            duration=data.get("duration", 0.0),
            scheduled=data.get("scheduled", False)
        )

    @classmethod
    def from_scan_result_data(
        cls,
        scan_status: str,
        path: str,
        duration: float,
        scanned_files: int = 0,
        scanned_dirs: int = 0,
        infected_count: int = 0,
        threat_details: Optional[list] = None,
        error_message: Optional[str] = None,
        stdout: str = "",
        suffix: str = "",
        scheduled: bool = False
    ) -> "LogEntry":
        """
        Create a LogEntry from scan result data.

        This factory method handles the common logic for creating log entries
        from scan results, used by both Scanner and DaemonScanner.

        Args:
            scan_status: Status of the scan ("clean", "infected", "cancelled", "error")
            path: The path that was scanned
            duration: Scan duration in seconds
            scanned_files: Number of files scanned
            scanned_dirs: Number of directories scanned
            infected_count: Number of infections found
            threat_details: List of threat details (dicts with file_path, threat_name)
            error_message: Error message if status is error
            stdout: Raw stdout from scan command
            suffix: Optional suffix for summary (e.g., "(daemon)")
            scheduled: Whether this was a scheduled scan

        Returns:
            New LogEntry instance
        """
        threat_details = threat_details or []

        # Build summary based on status
        suffix_str = f" {suffix}" if suffix else ""
        if scan_status == "clean":
            summary = f"Clean scan of {path}{suffix_str}"
            status = "clean"
        elif scan_status == "infected":
            summary = f"Found {infected_count} threat(s) in {path}{suffix_str}"
            status = "infected"
        elif scan_status == "cancelled":
            summary = f"Scan cancelled: {path}"
            status = "cancelled"
        else:
            summary = f"Scan error: {path}"
            status = "error"

        # Build details string
        details_parts = []
        if scanned_files > 0:
            details_parts.append(f"Scanned: {scanned_files} files, {scanned_dirs} directories")
        if infected_count > 0:
            details_parts.append(f"Threats found: {infected_count}")
            for threat in threat_details:
                file_path = threat.get("file_path", threat.get("path", "unknown"))
                threat_name = threat.get("threat_name", threat.get("name", "unknown"))
                details_parts.append(f"  - {file_path}: {threat_name}")
        if error_message:
            details_parts.append(f"Error: {error_message}")
        details = "\n".join(details_parts) if details_parts else stdout or ""

        return cls.create(
            log_type="scan",
            status=status,
            summary=summary,
            details=details,
            path=path,
            duration=duration,
            scheduled=scheduled
        )


# Common locations for clamd log files
CLAMD_LOG_PATHS = [
    "/var/log/clamav/clamd.log",
    "/var/log/clamd.log",
]

# Index file for optimized log retrieval
INDEX_FILENAME = "log_index.json"


class LogManager:
    """
    Manager for log persistence and retrieval.

    Provides methods for saving scan/update logs, retrieving historical logs,
    and accessing clamd daemon logs.

    Index Schema:
        The log index file (log_index.json) contains metadata for fast log retrieval:
        {
            "version": 1,
            "entries": [
                {"id": "uuid-string", "timestamp": "ISO-8601-string", "type": "scan|update"},
                ...
            ]
        }
    """

    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize the LogManager.

        Args:
            log_dir: Optional custom log directory. Defaults to XDG_DATA_HOME/clamui/logs
        """
        if log_dir:
            self._log_dir = Path(log_dir)
        else:
            xdg_data_home = os.environ.get("XDG_DATA_HOME", "~/.local/share")
            self._log_dir = Path(xdg_data_home).expanduser() / "clamui" / "logs"

        # Thread lock for safe concurrent access
        self._lock = threading.Lock()

        # Ensure log directory exists
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        """Ensure the log directory exists."""
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Handle silently - will fail on write operations
            pass

    @property
    def _index_path(self) -> Path:
        """
        Get the path to the log index file.

        Returns:
            Path object pointing to log_index.json in the log directory
        """
        return self._log_dir / INDEX_FILENAME

    def _load_index(self) -> dict:
        """
        Load the log index from file.

        Returns a dictionary with 'version' and 'entries' keys. If the file doesn't
        exist or is corrupted, returns an empty structure with version 1 and empty entries list.

        Returns:
            Dictionary with structure: {"version": 1, "entries": [...]}
        """
        try:
            if self._index_path.exists():
                with open(self._index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Validate structure has required keys
                    if isinstance(data, dict) and "version" in data and "entries" in data:
                        return data
            # File doesn't exist or invalid structure - return empty index
            return {"version": 1, "entries": []}
        except (OSError, json.JSONDecodeError, PermissionError):
            # Handle file read errors and JSON parsing errors gracefully
            return {"version": 1, "entries": []}

    def _save_index(self, index_data: dict) -> bool:
        """
        Atomically save the log index to file.

        Uses a temporary file and rename pattern to prevent corruption
        during write operations (crash safety).

        Args:
            index_data: Dictionary with structure {"version": 1, "entries": [...]}

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure parent directory exists
            self._log_dir.mkdir(parents=True, exist_ok=True)

            # Atomic write using temp file + rename
            fd, temp_path = tempfile.mkstemp(
                suffix=".json",
                prefix="log_index_",
                dir=self._log_dir,
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(index_data, f, indent=2)

                # Atomic rename
                temp_path_obj = Path(temp_path)
                temp_path_obj.replace(self._index_path)
                return True
            except Exception:
                # Clean up temp file on failure
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except OSError:
                    pass
                raise

        except Exception:
            # Catch all exceptions (including OSError, PermissionError)
            return False

    def _validate_index(self, index_data: dict) -> bool:
        """
        Validate that the index is not stale or invalid.

        Checks for:
        - Entry count mismatch (index entries vs actual log files)
        - Missing referenced files (>20% of indexed files don't exist)

        Args:
            index_data: The loaded index data

        Returns:
            True if index is valid, False if it needs to be rebuilt
        """
        try:
            if not self._log_dir.exists():
                # No log directory means index should be empty
                return len(index_data.get("entries", [])) == 0

            # Get actual log file count (excluding index file)
            actual_log_files = [
                f for f in self._log_dir.glob("*.json")
                if f.name != INDEX_FILENAME
            ]
            actual_count = len(actual_log_files)

            # Get index entry count
            index_entries = index_data.get("entries", [])
            index_count = len(index_entries)

            # If counts don't match, index is stale
            if index_count != actual_count:
                return False

            # Check for missing referenced files (sample check to avoid excessive I/O)
            # If we have many entries, check a sample; otherwise check all
            entries_to_check = index_entries
            if len(index_entries) > 50:
                # Sample 50 entries for large indices
                entries_to_check = random.sample(index_entries, 50)

            missing_count = 0
            for entry in entries_to_check:
                log_id = entry.get("id")
                if log_id:
                    log_file = self._log_dir / f"{log_id}.json"
                    if not log_file.exists():
                        missing_count += 1

            # Calculate missing percentage
            checked_count = len(entries_to_check)
            if checked_count > 0:
                missing_percentage = (missing_count / checked_count) * 100
                # If >20% of files are missing, index is stale
                if missing_percentage > 20:
                    return False

            return True

        except Exception:
            # On any error during validation, consider index invalid
            return False

    def rebuild_index(self) -> bool:
        """
        Rebuild the log index from scratch by scanning all log files.

        Used for migration from non-indexed state and recovery from index corruption.
        Reads only id, timestamp, and type from each log file (minimal parsing).

        Returns:
            True if rebuilt successfully, False otherwise
        """
        with self._lock:
            try:
                # Ensure log directory exists
                if not self._log_dir.exists():
                    # No logs to index - create empty index
                    return self._save_index({"version": 1, "entries": []})

                entries = []

                # Scan all JSON log files (exclude the index file itself)
                for log_file in self._log_dir.glob("*.json"):
                    # Skip the index file
                    if log_file.name == INDEX_FILENAME:
                        continue

                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            data = json.load(f)

                            # Extract only the required fields
                            log_id = data.get("id")
                            timestamp = data.get("timestamp")
                            log_type = data.get("type")

                            # Only add if all required fields are present
                            if log_id and timestamp and log_type:
                                entries.append({
                                    "id": log_id,
                                    "timestamp": timestamp,
                                    "type": log_type
                                })
                    except (OSError, json.JSONDecodeError):
                        # Skip corrupted or unreadable files
                        continue

                # Build index structure and save
                index_data = {
                    "version": 1,
                    "entries": entries
                }

                return self._save_index(index_data)

            except Exception:
                # Catch any unexpected errors
                return False

    def save_log(self, entry: LogEntry) -> bool:
        """
        Save a log entry to storage and update the index.

        Args:
            entry: The LogEntry to save

        Returns:
            True if saved successfully, False otherwise
        """
        with self._lock:
            try:
                self._ensure_log_dir()
                log_file = self._log_dir / f"{entry.id}.json"
                with open(log_file, "w", encoding="utf-8") as f:
                    json.dump(entry.to_dict(), f, indent=2)

                # Update index with new entry metadata (best-effort)
                try:
                    index_data = self._load_index()
                    index_data["entries"].append({
                        "id": entry.id,
                        "timestamp": entry.timestamp,
                        "type": entry.type
                    })
                    self._save_index(index_data)
                except Exception:
                    # Index update failed, but log file was saved successfully
                    # Index can be rebuilt later if needed
                    pass

                return True
            except (OSError, PermissionError, json.JSONDecodeError):
                return False

    def get_logs(self, limit: int = 100, log_type: Optional[str] = None) -> list[LogEntry]:
        """
        Retrieve stored log entries, sorted by timestamp (newest first).

        Uses an index file for optimized retrieval. Validates the index and
        triggers automatic rebuild if stale/invalid. Falls back to full directory
        scan if the index is missing or corrupted.

        Args:
            limit: Maximum number of entries to return
            log_type: Optional filter by type ("scan" or "update")

        Returns:
            List of LogEntry objects
        """
        with self._lock:
            # Try optimized index-based approach first
            index_data = self._load_index()

            # Check if index has entries (not empty/corrupted)
            if index_data.get("entries"):
                # Validate index before using it
                if not self._validate_index(index_data):
                    # Index is stale/invalid - trigger automatic rebuild
                    # Note: rebuild_index() already holds the lock, but we're already inside _lock
                    # so we need to release and reacquire, or call the underlying logic
                    # Actually, rebuild_index() tries to acquire _lock, but we already have it
                    # We need to restructure this

                    # For now, fall back to full scan and rebuild will happen later
                    # A better approach would be to have an internal _rebuild_index_unsafe
                    # that doesn't acquire the lock
                    index_data = {"version": 1, "entries": []}
                    # Attempt rebuild in best-effort mode (without re-locking)
                    try:
                        if self._log_dir.exists():
                            entries_list = []
                            for log_file in self._log_dir.glob("*.json"):
                                if log_file.name == INDEX_FILENAME:
                                    continue
                                try:
                                    with open(log_file, "r", encoding="utf-8") as f:
                                        data = json.load(f)
                                        log_id = data.get("id")
                                        timestamp = data.get("timestamp")
                                        log_type_val = data.get("type")
                                        if log_id and timestamp and log_type_val:
                                            entries_list.append({
                                                "id": log_id,
                                                "timestamp": timestamp,
                                                "type": log_type_val
                                            })
                                except (OSError, json.JSONDecodeError):
                                    continue
                            index_data = {"version": 1, "entries": entries_list}
                            # Save the rebuilt index (best-effort)
                            self._save_index(index_data)
                    except Exception:
                        # If rebuild fails, continue with empty index (will fall back to full scan)
                        pass

                # Now proceed with index-based retrieval if we have entries
                if index_data.get("entries"):
                    try:
                        # Start with all index entries
                        filtered_entries = index_data["entries"]

                        # Filter by type if specified
                        if log_type is not None:
                            filtered_entries = [
                                entry for entry in filtered_entries
                                if entry.get("type") == log_type
                            ]

                        # Sort by timestamp descending (newest first)
                        filtered_entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

                        # Apply limit
                        filtered_entries = filtered_entries[:limit]

                        # Load only the needed log files by id
                        entries = []
                        for index_entry in filtered_entries:
                            log_id = index_entry.get("id")
                            if log_id:
                                try:
                                    log_file = self._log_dir / f"{log_id}.json"
                                    if log_file.exists():
                                        with open(log_file, "r", encoding="utf-8") as f:
                                            data = json.load(f)
                                            entries.append(LogEntry.from_dict(data))
                                except (OSError, json.JSONDecodeError):
                                    # Skip corrupted or missing files
                                    continue

                        return entries

                    except Exception:
                        # Index-based approach failed, fall back to full scan
                        pass

            # Fallback: full directory scan (original implementation)
            entries = []
            try:
                if not self._log_dir.exists():
                    return entries

                for log_file in self._log_dir.glob("*.json"):
                    # Skip the index file
                    if log_file.name == INDEX_FILENAME:
                        continue

                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            entry = LogEntry.from_dict(data)

                            # Apply type filter if specified
                            if log_type is None or entry.type == log_type:
                                entries.append(entry)
                    except (OSError, json.JSONDecodeError):
                        # Skip corrupted files
                        continue

            except OSError:
                return entries

            # Sort by timestamp (newest first) and apply limit
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            return entries[:limit]

    def get_logs_async(
        self,
        callback: Callable[[list["LogEntry"]], None],
        limit: int = 100,
        log_type: Optional[str] = None
    ) -> None:
        """
        Retrieve stored log entries asynchronously.

        The log retrieval runs in a background thread and the callback is invoked
        on the main GTK thread via GLib.idle_add when complete.

        Args:
            callback: Function to call with list of LogEntry objects when loading completes
            limit: Maximum number of entries to return
            log_type: Optional filter by type ("scan" or "update")
        """
        def _load_logs_thread():
            try:
                entries = self.get_logs(limit=limit, log_type=log_type)
            except Exception:
                # On any error, return empty list to ensure callback is always called
                # This prevents loading state from getting stuck forever
                entries = []
            # Schedule callback on main thread - always called to reset loading state
            GLib.idle_add(callback, entries)

        thread = threading.Thread(target=_load_logs_thread)
        thread.daemon = True
        thread.start()

    def get_log_by_id(self, log_id: str) -> Optional[LogEntry]:
        """
        Retrieve a specific log entry by ID.

        Args:
            log_id: The UUID of the log entry

        Returns:
            LogEntry if found, None otherwise
        """
        with self._lock:
            try:
                log_file = self._log_dir / f"{log_id}.json"
                if log_file.exists():
                    with open(log_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return LogEntry.from_dict(data)
            except (OSError, json.JSONDecodeError):
                pass
        return None

    def delete_log(self, log_id: str) -> bool:
        """
        Delete a specific log entry and remove it from the index.

        Args:
            log_id: The UUID of the log entry to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        with self._lock:
            try:
                log_file = self._log_dir / f"{log_id}.json"
                if log_file.exists():
                    log_file.unlink()

                    # Update index by removing the deleted entry (best-effort)
                    try:
                        index_data = self._load_index()
                        index_data["entries"] = [
                            entry for entry in index_data["entries"]
                            if entry.get("id") != log_id
                        ]
                        self._save_index(index_data)
                    except Exception:
                        # Index update failed, but log file was deleted successfully
                        # Index can be rebuilt later if needed
                        pass

                    return True
            except OSError:
                pass
        return False

    def clear_logs(self) -> bool:
        """
        Clear all stored log entries and reset the index.

        Returns:
            True if cleared successfully, False otherwise
        """
        with self._lock:
            try:
                if self._log_dir.exists():
                    for log_file in self._log_dir.glob("*.json"):
                        # Skip the index file - we'll reset it separately
                        if log_file.name == INDEX_FILENAME:
                            continue
                        try:
                            log_file.unlink()
                        except OSError:
                            pass

                # Reset index to empty state (best-effort)
                try:
                    self._save_index({"version": 1, "entries": []})
                except Exception:
                    # Index reset failed, but log files were cleared successfully
                    # Index can be rebuilt later if needed
                    pass

                return True
            except OSError:
                return False

    def get_log_count(self) -> int:
        """
        Get the total number of stored logs.

        Returns:
            Number of log entries
        """
        with self._lock:
            try:
                if not self._log_dir.exists():
                    return 0
                return len(list(self._log_dir.glob("*.json")))
            except OSError:
                return 0

    def get_daemon_status(self) -> tuple[DaemonStatus, Optional[str]]:
        """
        Check the status of the clamd daemon.

        Returns:
            Tuple of (DaemonStatus, optional_message)
        """
        # Check if clamd is installed (checking host if in Flatpak)
        clamd_path = which_host_command("clamd")
        if clamd_path is None:
            return (DaemonStatus.NOT_INSTALLED, "clamd is not installed")

        # Check if clamd process is running (on host if in Flatpak)
        try:
            result = subprocess.run(
                wrap_host_command(["pgrep", "-x", "clamd"]),
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return (DaemonStatus.RUNNING, "clamd daemon is running")
            else:
                return (DaemonStatus.STOPPED, "clamd daemon is not running")
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return (DaemonStatus.UNKNOWN, "Unable to determine daemon status")

    def _file_exists_on_host(self, path: str) -> bool:
        """
        Check if a file exists, using host filesystem if in Flatpak.

        Args:
            path: Path to check

        Returns:
            True if file exists, False otherwise
        """
        if is_flatpak():
            try:
                result = subprocess.run(
                    ["flatpak-spawn", "--host", "test", "-f", path],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            except Exception:
                return False
        return Path(path).exists()

    def get_daemon_log_path(self) -> Optional[str]:
        """
        Find the clamd log file path.

        Checks common locations for the clamd log file.

        Returns:
            Path to the log file if found, None otherwise
        """
        for log_path in CLAMD_LOG_PATHS:
            if self._file_exists_on_host(log_path):
                return log_path

        # Also try to get from clamd.conf if it exists
        clamd_conf_paths = [
            "/etc/clamav/clamd.conf",
            "/etc/clamd.conf",
            "/etc/clamd.d/scan.conf",
        ]

        for conf_path in clamd_conf_paths:
            if self._file_exists_on_host(conf_path):
                try:
                    # Read config file (use host command in Flatpak)
                    if is_flatpak():
                        result = subprocess.run(
                            ["flatpak-spawn", "--host", "cat", conf_path],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode != 0:
                            continue
                        config_content = result.stdout
                    else:
                        with open(conf_path, "r", encoding="utf-8") as f:
                            config_content = f.read()

                    for line in config_content.splitlines():
                        line = line.strip()
                        if line.startswith("LogFile"):
                            parts = line.split(None, 1)
                            if len(parts) == 2:
                                log_file = parts[1].strip()
                                if self._file_exists_on_host(log_file):
                                    return log_file
                except (OSError, PermissionError, subprocess.SubprocessError):
                    continue

        return None

    def read_daemon_logs(self, num_lines: int = 100) -> tuple[bool, str]:
        """
        Read the last N lines from the clamd daemon log.

        Uses tail-like behavior to read only the end of the file,
        avoiding loading large log files into memory.

        Tries multiple methods in order:
        1. tail command (wrapped for Flatpak)
        2. journalctl for systemd-based systems
        3. Direct file read (non-Flatpak only)

        Args:
            num_lines: Number of lines to read from the end of the log

        Returns:
            Tuple of (success, log_content_or_error_message)
        """
        log_path = self.get_daemon_log_path()

        # Try reading log file with tail
        if log_path is not None:
            try:
                # Use tail command - wrapped for Flatpak host access
                tail_cmd = wrap_host_command(
                    ["tail", "-n", str(num_lines), log_path]
                )
                result = subprocess.run(
                    tail_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    content = result.stdout
                    if not content.strip():
                        return (True, "(Log file is empty)")
                    return (True, content)
                # If tail failed (permission denied), fall through to journalctl

            except subprocess.TimeoutExpired:
                return (False, "Timeout reading log file")
            except FileNotFoundError:
                pass  # Fall through to journalctl
            except OSError:
                pass  # Fall through to journalctl

        # Try journalctl as fallback (works on systemd systems, no root needed)
        journalctl_result = self._read_daemon_logs_journalctl(num_lines)
        if journalctl_result[0]:
            return journalctl_result

        # If we found a log path but couldn't read it, give helpful error
        if log_path is not None:
            return (
                False,
                f"Permission denied reading {log_path}\n\n"
                "The daemon log file requires elevated permissions.\n"
                "Options:\n"
                "  • Add your user to the 'adm' or 'clamav' group:\n"
                "    sudo usermod -aG adm $USER\n"
                "  • Or check if clamd logs to systemd journal:\n"
                "    journalctl -u clamav-daemon"
            )

        return (
            False,
            "Daemon log file not found.\n\n"
            "ClamAV daemon (clamd) may not be installed or configured.\n"
            "Common log locations checked:\n"
            "  • /var/log/clamav/clamd.log\n"
            "  • /var/log/clamd.log"
        )

    def _read_daemon_logs_journalctl(
        self, num_lines: int
    ) -> tuple[bool, str]:
        """
        Read daemon logs from systemd journal.

        Args:
            num_lines: Number of lines to read

        Returns:
            Tuple of (success, content_or_error)
        """
        # Try different unit names used by various distros
        unit_names = [
            "clamav-daemon",
            "clamav-daemon.service",
            "clamd",
            "clamd.service",
            "clamd@scan",
            "clamd@scan.service",
        ]

        for unit in unit_names:
            try:
                cmd = wrap_host_command([
                    "journalctl",
                    "-u", unit,
                    "-n", str(num_lines),
                    "--no-pager",
                    "-q"  # Quiet - suppress info messages
                ])
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0 and result.stdout.strip():
                    return (True, result.stdout)

            except (subprocess.SubprocessError, FileNotFoundError, OSError):
                continue

        return (False, "No journal entries found for clamd")

    def _read_file_tail(self, file_path: str, num_lines: int) -> tuple[bool, str]:
        """
        Read the last N lines from a file directly (fallback method).

        Args:
            file_path: Path to the file
            num_lines: Number of lines to read

        Returns:
            Tuple of (success, content_or_error)
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                # For small files, read all and return last N lines
                lines = f.readlines()
                tail_lines = lines[-num_lines:] if len(lines) > num_lines else lines
                content = "".join(tail_lines)
                if not content.strip():
                    return (True, "(Log file is empty)")
                return (True, content)
        except PermissionError:
            return (False, "Permission denied reading log file")
        except OSError as e:
            return (False, f"Error reading log file: {e}")
