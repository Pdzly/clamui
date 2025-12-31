# ClamUI Secure File Handler Module
"""
Secure file handler for quarantine operations with atomic operations and permission management.

Provides secure file movement to/from quarantine with:
- Atomic operations (move, not copy-delete)
- SHA256 hash calculation for integrity verification
- Restrictive file permissions (0o700 directory, 0o400 files)
- Cross-platform path handling via pathlib
"""

import hashlib
import os
import shutil
import stat
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple
import uuid


class FileOperationStatus(Enum):
    """Status of a file operation."""
    SUCCESS = "success"
    ERROR = "error"
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    ALREADY_EXISTS = "already_exists"
    DISK_FULL = "disk_full"


@dataclass
class FileOperationResult:
    """Result of a file operation."""
    status: FileOperationStatus
    source_path: str
    destination_path: Optional[str]
    file_size: int
    file_hash: str
    error_message: Optional[str]

    @property
    def is_success(self) -> bool:
        """Check if the operation was successful."""
        return self.status == FileOperationStatus.SUCCESS


class SecureFileHandler:
    """
    Handler for secure file operations with permission management.

    Provides methods for moving files to/from quarantine with:
    - Atomic file operations using shutil.move
    - SHA256 hash calculation before operations
    - Restrictive permissions on quarantine directory and files
    - Thread-safe operations with file locking

    Example:
        >>> handler = SecureFileHandler("/home/user/.local/share/clamui/quarantine")
        >>> result = handler.move_to_quarantine("/home/user/infected.exe")
        >>> if result.is_success:
        ...     print(f"File quarantined at {result.destination_path}")
    """

    # Directory permission: owner read/write/execute only
    QUARANTINE_DIR_PERMISSIONS = 0o700

    # File permission: owner read-only (prevents execution)
    QUARANTINE_FILE_PERMISSIONS = 0o400

    # Buffer size for hash calculation (64KB)
    HASH_BUFFER_SIZE = 65536

    def __init__(self, quarantine_directory: Optional[str] = None):
        """
        Initialize the SecureFileHandler.

        Args:
            quarantine_directory: Path to the quarantine directory.
                                  Defaults to XDG_DATA_HOME/clamui/quarantine
        """
        if quarantine_directory:
            self._quarantine_dir = Path(quarantine_directory).expanduser()
        else:
            xdg_data_home = os.environ.get("XDG_DATA_HOME", "~/.local/share")
            self._quarantine_dir = Path(xdg_data_home).expanduser() / "clamui" / "quarantine"

        # Thread lock for safe concurrent operations
        self._lock = threading.Lock()

        # Ensure quarantine directory exists with proper permissions
        self._ensure_quarantine_dir()

    @property
    def quarantine_directory(self) -> Path:
        """Get the quarantine directory path."""
        return self._quarantine_dir

    def _ensure_quarantine_dir(self) -> Tuple[bool, Optional[str]]:
        """
        Ensure the quarantine directory exists with proper permissions.

        Creates the directory if it doesn't exist and sets restrictive
        permissions (0o700 - owner read/write/execute only).

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Create directory with parents if it doesn't exist
            self._quarantine_dir.mkdir(parents=True, exist_ok=True)

            # Set restrictive permissions on the directory
            os.chmod(self._quarantine_dir, self.QUARANTINE_DIR_PERMISSIONS)

            return (True, None)

        except PermissionError as e:
            return (False, f"Permission denied creating quarantine directory: {e}")
        except OSError as e:
            return (False, f"Error creating quarantine directory: {e}")

    def calculate_hash(self, file_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """
        Calculate SHA256 hash of a file for integrity verification.

        Uses buffered reading to handle large files efficiently without
        loading the entire file into memory.

        Args:
            file_path: Path to the file to hash

        Returns:
            Tuple of (hash_string, error_message):
            - (hash, None) if successful
            - (None, error_message) if failed

        Example:
            >>> handler = SecureFileHandler()
            >>> hash_value, error = handler.calculate_hash(Path("/path/to/file"))
            >>> if hash_value:
            ...     print(f"SHA256: {hash_value}")
        """
        try:
            sha256_hash = hashlib.sha256()

            with open(file_path, "rb") as f:
                for block in iter(lambda: f.read(self.HASH_BUFFER_SIZE), b""):
                    sha256_hash.update(block)

            return (sha256_hash.hexdigest(), None)

        except FileNotFoundError:
            return (None, f"File not found: {file_path}")
        except PermissionError:
            return (None, f"Permission denied reading file: {file_path}")
        except OSError as e:
            return (None, f"Error reading file: {e}")

    def get_file_size(self, file_path: Path) -> Tuple[int, Optional[str]]:
        """
        Get the size of a file in bytes.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (size_in_bytes, error_message):
            - (size, None) if successful
            - (-1, error_message) if failed
        """
        try:
            return (file_path.stat().st_size, None)
        except FileNotFoundError:
            return (-1, f"File not found: {file_path}")
        except PermissionError:
            return (-1, f"Permission denied accessing file: {file_path}")
        except OSError as e:
            return (-1, f"Error accessing file: {e}")

    def _generate_quarantine_filename(self, original_path: Path) -> str:
        """
        Generate a unique filename for the quarantined file.

        Uses UUID to ensure uniqueness while preserving the original
        filename for identification.

        Args:
            original_path: Original file path

        Returns:
            Unique filename for quarantine storage

        Example:
            >>> handler._generate_quarantine_filename(Path("/home/user/malware.exe"))
            'a1b2c3d4-5678-90ab-cdef-1234567890ab_malware.exe'
        """
        unique_id = uuid.uuid4().hex[:16]
        original_name = original_path.name
        return f"{unique_id}_{original_name}"

    def _check_disk_space(self, file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Check if there's enough disk space for the quarantine operation.

        Args:
            file_size: Size of the file to be quarantined in bytes

        Returns:
            Tuple of (has_space, error_message)
        """
        try:
            usage = shutil.disk_usage(self._quarantine_dir)
            # Require at least file_size + 10MB buffer
            required_space = file_size + (10 * 1024 * 1024)

            if usage.free < required_space:
                free_mb = usage.free / (1024 * 1024)
                return (False, f"Insufficient disk space. Only {free_mb:.1f} MB available")

            return (True, None)

        except OSError as e:
            return (False, f"Error checking disk space: {e}")

    def move_to_quarantine(
        self,
        source_path: str,
        threat_name: Optional[str] = None
    ) -> FileOperationResult:
        """
        Move a file to the quarantine directory securely.

        Performs the following operations atomically:
        1. Validates the source file exists and is readable
        2. Calculates SHA256 hash for integrity verification
        3. Checks available disk space
        4. Moves the file to quarantine directory
        5. Sets restrictive permissions on the quarantined file

        Args:
            source_path: Path to the file to quarantine
            threat_name: Optional threat name for logging (not used in filename)

        Returns:
            FileOperationResult with operation status and details

        Example:
            >>> handler = SecureFileHandler()
            >>> result = handler.move_to_quarantine("/home/user/infected.exe")
            >>> if result.is_success:
            ...     print(f"Quarantined: {result.destination_path}")
            ...     print(f"Hash: {result.file_hash}")
        """
        source = Path(source_path).resolve()

        with self._lock:
            # Validate source file exists
            if not source.exists():
                return FileOperationResult(
                    status=FileOperationStatus.FILE_NOT_FOUND,
                    source_path=str(source),
                    destination_path=None,
                    file_size=0,
                    file_hash="",
                    error_message=f"Source file not found: {source}"
                )

            # Check if it's a file (not directory)
            if not source.is_file():
                return FileOperationResult(
                    status=FileOperationStatus.ERROR,
                    source_path=str(source),
                    destination_path=None,
                    file_size=0,
                    file_hash="",
                    error_message=f"Source is not a file: {source}"
                )

            # Get file size
            file_size, size_error = self.get_file_size(source)
            if size_error:
                return FileOperationResult(
                    status=FileOperationStatus.PERMISSION_DENIED,
                    source_path=str(source),
                    destination_path=None,
                    file_size=0,
                    file_hash="",
                    error_message=size_error
                )

            # Calculate hash before moving
            file_hash, hash_error = self.calculate_hash(source)
            if hash_error:
                return FileOperationResult(
                    status=FileOperationStatus.PERMISSION_DENIED,
                    source_path=str(source),
                    destination_path=None,
                    file_size=file_size,
                    file_hash="",
                    error_message=hash_error
                )

            # Ensure quarantine directory exists
            dir_ok, dir_error = self._ensure_quarantine_dir()
            if not dir_ok:
                return FileOperationResult(
                    status=FileOperationStatus.PERMISSION_DENIED,
                    source_path=str(source),
                    destination_path=None,
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=dir_error
                )

            # Check disk space
            has_space, space_error = self._check_disk_space(file_size)
            if not has_space:
                return FileOperationResult(
                    status=FileOperationStatus.DISK_FULL,
                    source_path=str(source),
                    destination_path=None,
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=space_error
                )

            # Generate unique quarantine filename
            quarantine_filename = self._generate_quarantine_filename(source)
            destination = self._quarantine_dir / quarantine_filename

            # Check if destination already exists (shouldn't happen with UUID)
            if destination.exists():
                return FileOperationResult(
                    status=FileOperationStatus.ALREADY_EXISTS,
                    source_path=str(source),
                    destination_path=str(destination),
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=f"Destination already exists: {destination}"
                )

            try:
                # Atomic move operation
                shutil.move(str(source), str(destination))

                # Set restrictive permissions on quarantined file
                os.chmod(destination, self.QUARANTINE_FILE_PERMISSIONS)

                return FileOperationResult(
                    status=FileOperationStatus.SUCCESS,
                    source_path=str(source),
                    destination_path=str(destination),
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=None
                )

            except PermissionError as e:
                return FileOperationResult(
                    status=FileOperationStatus.PERMISSION_DENIED,
                    source_path=str(source),
                    destination_path=None,
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=f"Permission denied during move: {e}"
                )
            except shutil.Error as e:
                return FileOperationResult(
                    status=FileOperationStatus.ERROR,
                    source_path=str(source),
                    destination_path=None,
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=f"Move operation failed: {e}"
                )
            except OSError as e:
                return FileOperationResult(
                    status=FileOperationStatus.ERROR,
                    source_path=str(source),
                    destination_path=None,
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=f"File operation error: {e}"
                )

    def restore_from_quarantine(
        self,
        quarantine_path: str,
        original_path: str
    ) -> FileOperationResult:
        """
        Restore a file from quarantine to its original location.

        Performs the following operations:
        1. Validates the quarantine file exists
        2. Ensures the original directory exists (creates if needed)
        3. Restores file permissions to default before moving
        4. Moves the file back to the original location

        Args:
            quarantine_path: Path to the quarantined file
            original_path: Original path to restore the file to

        Returns:
            FileOperationResult with operation status and details

        Example:
            >>> handler = SecureFileHandler()
            >>> result = handler.restore_from_quarantine(
            ...     "/home/user/.local/share/clamui/quarantine/abc123_file.exe",
            ...     "/home/user/file.exe"
            ... )
            >>> if result.is_success:
            ...     print(f"Restored to: {result.destination_path}")
        """
        source = Path(quarantine_path).resolve()
        destination = Path(original_path).resolve()

        with self._lock:
            # Validate quarantine file exists
            if not source.exists():
                return FileOperationResult(
                    status=FileOperationStatus.FILE_NOT_FOUND,
                    source_path=str(source),
                    destination_path=str(destination),
                    file_size=0,
                    file_hash="",
                    error_message=f"Quarantine file not found: {source}"
                )

            # Get file size
            file_size, size_error = self.get_file_size(source)
            if size_error:
                file_size = 0

            # Calculate hash for verification
            file_hash, _ = self.calculate_hash(source)

            # Ensure destination directory exists
            try:
                destination.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                return FileOperationResult(
                    status=FileOperationStatus.PERMISSION_DENIED,
                    source_path=str(source),
                    destination_path=str(destination),
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=f"Cannot create destination directory: {e}"
                )
            except OSError as e:
                return FileOperationResult(
                    status=FileOperationStatus.ERROR,
                    source_path=str(source),
                    destination_path=str(destination),
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=f"Error creating destination directory: {e}"
                )

            # Check if destination already exists
            if destination.exists():
                return FileOperationResult(
                    status=FileOperationStatus.ALREADY_EXISTS,
                    source_path=str(source),
                    destination_path=str(destination),
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=f"Destination file already exists: {destination}"
                )

            try:
                # Restore file permissions before moving (to allow move operation)
                # Set to owner read/write
                os.chmod(source, stat.S_IRUSR | stat.S_IWUSR)

                # Atomic move operation
                shutil.move(str(source), str(destination))

                # Set normal file permissions (owner read/write, group/others read)
                os.chmod(destination, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

                return FileOperationResult(
                    status=FileOperationStatus.SUCCESS,
                    source_path=str(source),
                    destination_path=str(destination),
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=None
                )

            except PermissionError as e:
                return FileOperationResult(
                    status=FileOperationStatus.PERMISSION_DENIED,
                    source_path=str(source),
                    destination_path=str(destination),
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=f"Permission denied during restore: {e}"
                )
            except shutil.Error as e:
                return FileOperationResult(
                    status=FileOperationStatus.ERROR,
                    source_path=str(source),
                    destination_path=str(destination),
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=f"Restore operation failed: {e}"
                )
            except OSError as e:
                return FileOperationResult(
                    status=FileOperationStatus.ERROR,
                    source_path=str(source),
                    destination_path=str(destination),
                    file_size=file_size,
                    file_hash=file_hash or "",
                    error_message=f"File operation error: {e}"
                )

    def delete_quarantined_file(self, quarantine_path: str) -> FileOperationResult:
        """
        Permanently delete a file from quarantine.

        Securely removes the file from the quarantine directory.
        This operation cannot be undone.

        Args:
            quarantine_path: Path to the quarantined file to delete

        Returns:
            FileOperationResult with operation status and details

        Example:
            >>> handler = SecureFileHandler()
            >>> result = handler.delete_quarantined_file(
            ...     "/home/user/.local/share/clamui/quarantine/abc123_file.exe"
            ... )
            >>> if result.is_success:
            ...     print("File permanently deleted")
        """
        target = Path(quarantine_path).resolve()

        with self._lock:
            # Validate file exists
            if not target.exists():
                return FileOperationResult(
                    status=FileOperationStatus.FILE_NOT_FOUND,
                    source_path=str(target),
                    destination_path=None,
                    file_size=0,
                    file_hash="",
                    error_message=f"File not found: {target}"
                )

            # Verify file is in quarantine directory (security check)
            try:
                target.relative_to(self._quarantine_dir)
            except ValueError:
                return FileOperationResult(
                    status=FileOperationStatus.PERMISSION_DENIED,
                    source_path=str(target),
                    destination_path=None,
                    file_size=0,
                    file_hash="",
                    error_message="File is not in quarantine directory"
                )

            # Get file info before deletion
            file_size, _ = self.get_file_size(target)
            file_hash, _ = self.calculate_hash(target)

            try:
                # Ensure we have write permission to delete
                os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)

                # Delete the file
                target.unlink()

                return FileOperationResult(
                    status=FileOperationStatus.SUCCESS,
                    source_path=str(target),
                    destination_path=None,
                    file_size=file_size if file_size > 0 else 0,
                    file_hash=file_hash or "",
                    error_message=None
                )

            except PermissionError as e:
                return FileOperationResult(
                    status=FileOperationStatus.PERMISSION_DENIED,
                    source_path=str(target),
                    destination_path=None,
                    file_size=file_size if file_size > 0 else 0,
                    file_hash=file_hash or "",
                    error_message=f"Permission denied deleting file: {e}"
                )
            except OSError as e:
                return FileOperationResult(
                    status=FileOperationStatus.ERROR,
                    source_path=str(target),
                    destination_path=None,
                    file_size=file_size if file_size > 0 else 0,
                    file_hash=file_hash or "",
                    error_message=f"Error deleting file: {e}"
                )

    def verify_file_integrity(
        self,
        file_path: str,
        expected_hash: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify the integrity of a file by comparing its hash.

        Calculates the SHA256 hash of the file and compares it to
        the expected hash to ensure the file hasn't been modified.

        Args:
            file_path: Path to the file to verify
            expected_hash: Expected SHA256 hash string

        Returns:
            Tuple of (is_valid, error_message):
            - (True, None) if hash matches
            - (False, error_message) if hash doesn't match or error occurred

        Example:
            >>> handler = SecureFileHandler()
            >>> is_valid, error = handler.verify_file_integrity(
            ...     "/path/to/file",
            ...     "a1b2c3d4..."
            ... )
        """
        target = Path(file_path)

        if not target.exists():
            return (False, f"File not found: {file_path}")

        actual_hash, hash_error = self.calculate_hash(target)

        if hash_error:
            return (False, hash_error)

        if actual_hash != expected_hash:
            return (False, f"Hash mismatch: expected {expected_hash}, got {actual_hash}")

        return (True, None)

    def get_quarantine_info(self) -> dict:
        """
        Get information about the quarantine directory.

        Returns:
            Dictionary with:
            - 'path': Quarantine directory path
            - 'exists': Whether the directory exists
            - 'file_count': Number of files in quarantine
            - 'total_size': Total size of quarantined files in bytes
            - 'permissions': Directory permissions as octal string
        """
        info = {
            'path': str(self._quarantine_dir),
            'exists': self._quarantine_dir.exists(),
            'file_count': 0,
            'total_size': 0,
            'permissions': None
        }

        if not info['exists']:
            return info

        try:
            # Get directory permissions
            stat_info = self._quarantine_dir.stat()
            info['permissions'] = oct(stat_info.st_mode)[-3:]

            # Count files and calculate total size
            for file_path in self._quarantine_dir.iterdir():
                if file_path.is_file():
                    info['file_count'] += 1
                    try:
                        info['total_size'] += file_path.stat().st_size
                    except OSError:
                        pass

        except OSError:
            pass

        return info
