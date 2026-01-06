# ClamUI SecureFileHandler Tests
"""Unit tests for the SecureFileHandler path validation."""

import os
from pathlib import Path

from src.core.quarantine.file_handler import (
    FileOperationStatus,
    SecureFileHandler,
)


class TestValidateRestorePath:
    """Tests for SecureFileHandler.validate_restore_path() method."""

    def test_valid_user_home_path(self):
        """Test that paths in user home directory are accepted."""
        handler = SecureFileHandler()

        # Test path in user's home directory
        user_path = str(Path.home() / "Documents" / "file.txt")
        is_valid, error = handler.validate_restore_path(user_path)

        assert is_valid is True
        assert error is None

    def test_valid_tmp_path(self, tmp_path):
        """Test that paths in /tmp are accepted."""
        handler = SecureFileHandler()

        # Test path in /tmp directory
        temp_path = str(tmp_path / "test_file.txt")
        is_valid, error = handler.validate_restore_path(temp_path)

        assert is_valid is True
        assert error is None

    def test_empty_path_rejected(self):
        """Test that empty paths are rejected."""
        handler = SecureFileHandler()

        # Test empty string
        is_valid, error = handler.validate_restore_path("")
        assert is_valid is False
        assert "cannot be empty" in error

        # Test whitespace-only string
        is_valid, error = handler.validate_restore_path("   ")
        assert is_valid is False
        assert "cannot be empty" in error

    def test_newline_character_rejected(self):
        """Test that paths containing newline characters are rejected."""
        handler = SecureFileHandler()

        # Test Unix newline
        path_with_newline = "/home/user/file\nmalicious.txt"
        is_valid, error = handler.validate_restore_path(path_with_newline)

        assert is_valid is False
        assert "newline" in error.lower()

        # Test carriage return
        path_with_cr = "/home/user/file\rmalicious.txt"
        is_valid, error = handler.validate_restore_path(path_with_cr)

        assert is_valid is False
        assert "newline" in error.lower()

    def test_null_byte_rejected(self):
        """Test that paths containing null bytes are rejected."""
        handler = SecureFileHandler()

        path_with_null = "/home/user/file\x00malicious.txt"
        is_valid, error = handler.validate_restore_path(path_with_null)

        assert is_valid is False
        assert "null" in error.lower()

    def test_etc_directory_rejected(self):
        """Test that paths in /etc directory are rejected."""
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/etc/passwd")

        assert is_valid is False
        assert "/etc" in error
        assert "protected" in error.lower()

    def test_var_directory_rejected(self):
        """Test that paths in /var directory are rejected."""
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/var/lib/important.db")

        assert is_valid is False
        assert "/var" in error
        assert "protected" in error.lower()

    def test_usr_directory_rejected(self):
        """Test that paths in /usr directory are rejected."""
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/usr/bin/malicious")

        assert is_valid is False
        assert "/usr" in error
        assert "protected" in error.lower()

    def test_bin_directory_rejected(self):
        """Test that paths in /bin directory are rejected.

        Note: On modern Linux systems, /bin is a symlink to /usr/bin,
        so the error message may reference /usr instead of /bin.
        """
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/bin/bash")

        assert is_valid is False
        # Error message may reference /usr/bin (symlink target) or /bin
        assert "protected" in error.lower()

    def test_sbin_directory_rejected(self):
        """Test that paths in /sbin directory are rejected.

        Note: On modern Linux systems, /sbin is a symlink to /usr/sbin,
        so the error message may reference /usr instead of /sbin.
        """
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/sbin/init")

        assert is_valid is False
        # Error message may reference /usr/sbin (symlink target) or /sbin
        assert "protected" in error.lower()

    def test_lib_directory_rejected(self):
        """Test that paths in /lib directory are rejected.

        Note: On modern Linux systems, /lib is a symlink to /usr/lib,
        so the error message may reference /usr instead of /lib.
        """
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/lib/systemd/system/service.conf")

        assert is_valid is False
        # Error message may reference /usr/lib (symlink target) or /lib
        assert "protected" in error.lower()

    def test_lib64_directory_rejected(self):
        """Test that paths in /lib64 directory are rejected."""
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/lib64/ld-linux-x86-64.so.2")

        assert is_valid is False
        assert "protected" in error.lower()

    def test_boot_directory_rejected(self):
        """Test that paths in /boot directory are rejected."""
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/boot/vmlinuz")

        assert is_valid is False
        assert "/boot" in error
        assert "protected" in error.lower()

    def test_root_directory_rejected(self):
        """Test that paths in /root directory are rejected."""
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/root/.bashrc")

        assert is_valid is False
        assert "/root" in error
        assert "protected" in error.lower()

    def test_sys_directory_rejected(self):
        """Test that paths in /sys directory are rejected."""
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/sys/class/net/eth0/mtu")

        assert is_valid is False
        assert "/sys" in error
        assert "protected" in error.lower()

    def test_proc_directory_rejected(self):
        """Test that paths in /proc directory are rejected."""
        handler = SecureFileHandler()

        is_valid, error = handler.validate_restore_path("/proc/sys/kernel/hostname")

        assert is_valid is False
        assert "/proc" in error
        assert "protected" in error.lower()

    def test_parent_directory_traversal_to_protected(self):
        """Test that paths using .. to reach protected directories are rejected."""
        handler = SecureFileHandler()

        # Attempt to use .. to escape to /etc
        # The resolve() method should handle this
        path_with_traversal = "/home/user/../../etc/passwd"
        is_valid, error = handler.validate_restore_path(path_with_traversal)

        assert is_valid is False
        assert "protected" in error.lower()

    def test_symlink_to_protected_directory(self, tmp_path):
        """Test that symlinks pointing to protected directories are rejected."""
        handler = SecureFileHandler()

        # Create a symlink to /etc
        symlink_path = tmp_path / "link_to_etc"
        try:
            symlink_path.symlink_to("/etc")

            # Try to restore to a path that includes this symlink
            restore_path = str(symlink_path / "passwd")
            is_valid, error = handler.validate_restore_path(restore_path)

            assert is_valid is False
            assert "symlink" in error.lower() or "protected" in error.lower()
        finally:
            # Clean up symlink
            if symlink_path.exists():
                symlink_path.unlink()

    def test_symlink_to_safe_directory(self, tmp_path):
        """Test that symlinks pointing to safe directories are accepted."""
        handler = SecureFileHandler()

        # Create a safe target directory
        safe_target = tmp_path / "safe_target"
        safe_target.mkdir()

        # Create a symlink to the safe directory
        symlink_path = tmp_path / "link_to_safe"
        try:
            symlink_path.symlink_to(safe_target)

            # Try to restore to a path that includes this symlink
            restore_path = str(symlink_path / "file.txt")
            is_valid, error = handler.validate_restore_path(restore_path)

            assert is_valid is True
            assert error is None
        finally:
            # Clean up symlink
            if symlink_path.exists():
                symlink_path.unlink()

    def test_nonexistent_path_in_safe_location(self, tmp_path):
        """Test that nonexistent paths in safe locations are accepted."""
        handler = SecureFileHandler()

        # The validation should accept paths that don't exist yet
        # as long as they're in a safe location
        nonexistent_path = str(tmp_path / "doesnt_exist" / "yet" / "file.txt")
        is_valid, error = handler.validate_restore_path(nonexistent_path)

        assert is_valid is True
        assert error is None

    def test_relative_path_resolves_safely(self, tmp_path):
        """Test that relative paths that resolve to safe locations are accepted."""
        handler = SecureFileHandler()

        # Change to tmp directory and use relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Relative path that resolves to tmp_path
            relative_path = "./subdir/file.txt"
            is_valid, error = handler.validate_restore_path(relative_path)

            assert is_valid is True
            assert error is None
        finally:
            os.chdir(original_cwd)

    def test_invalid_path_format(self):
        """Test that invalid path formats are handled gracefully."""
        handler = SecureFileHandler()

        # Test with None - should be handled gracefully, not raise exception
        is_valid, error = handler.validate_restore_path(None)
        assert is_valid is False
        assert "Invalid path format" in error or "cannot be empty" in error


class TestRestoreFromQuarantineValidation:
    """Tests for path validation integration in restore_from_quarantine()."""

    def test_restore_rejects_invalid_path(self, tmp_path):
        """Test that restore_from_quarantine rejects invalid restore paths."""
        handler = SecureFileHandler(str(tmp_path / "quarantine"))

        # Create a fake quarantined file
        quarantine_file = tmp_path / "quarantine" / "test_file.quar"
        quarantine_file.parent.mkdir(parents=True, exist_ok=True)
        quarantine_file.write_text("fake quarantined content")

        # Try to restore to a protected directory
        result = handler.restore_from_quarantine(str(quarantine_file), "/etc/malicious.conf")

        assert result.status == FileOperationStatus.INVALID_RESTORE_PATH
        assert result.error_message is not None
        assert "protected" in result.error_message.lower()

    def test_restore_rejects_path_with_injection(self, tmp_path):
        """Test that restore_from_quarantine rejects paths with injection characters."""
        handler = SecureFileHandler(str(tmp_path / "quarantine"))

        # Create a fake quarantined file
        quarantine_file = tmp_path / "quarantine" / "test_file.quar"
        quarantine_file.parent.mkdir(parents=True, exist_ok=True)
        quarantine_file.write_text("fake quarantined content")

        # Try to restore to a path with newline injection
        result = handler.restore_from_quarantine(str(quarantine_file), "/tmp/file\nmalicious.txt")

        assert result.status == FileOperationStatus.INVALID_RESTORE_PATH
        assert result.error_message is not None
        assert "newline" in result.error_message.lower()

    def test_restore_accepts_valid_path(self, tmp_path):
        """Test that restore_from_quarantine accepts valid restore paths."""
        handler = SecureFileHandler(str(tmp_path / "quarantine"))

        # Create a fake quarantined file
        quarantine_file = tmp_path / "quarantine" / "test_file.quar"
        quarantine_file.parent.mkdir(parents=True, exist_ok=True)
        quarantine_file.write_text("fake quarantined content")

        # Try to restore to a safe location
        safe_restore_path = str(tmp_path / "restored" / "file.txt")
        result = handler.restore_from_quarantine(str(quarantine_file), safe_restore_path)

        # Should not fail due to path validation
        # (might fail for other reasons like missing hash, but not INVALID_RESTORE_PATH)
        assert result.status != FileOperationStatus.INVALID_RESTORE_PATH

    def test_restore_validation_before_file_operations(self, tmp_path):
        """Test that path validation occurs before any file operations."""
        handler = SecureFileHandler(str(tmp_path / "quarantine"))

        # Don't create the quarantined file - validation should happen first
        quarantine_file = tmp_path / "quarantine" / "nonexistent.quar"

        # Try to restore to protected directory
        result = handler.restore_from_quarantine(str(quarantine_file), "/etc/malicious.conf")

        # Should fail with INVALID_RESTORE_PATH, not FILE_NOT_FOUND
        # This proves validation happens before checking if source exists
        assert result.status == FileOperationStatus.INVALID_RESTORE_PATH
        assert "protected" in result.error_message.lower()


class TestValidateQuarantinePath:
    """Tests for SecureFileHandler._validate_quarantine_path() method."""

    def test_valid_quarantine_path(self, tmp_path):
        """Test that paths inside quarantine directory are accepted."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a file inside quarantine
        quarantine_file = quarantine_dir / "abc123_malware.exe"
        quarantine_file.write_text("fake quarantined content")

        is_valid, error = handler._validate_quarantine_path(str(quarantine_file))

        assert is_valid is True
        assert error is None

    def test_path_outside_quarantine_rejected(self, tmp_path):
        """Test that absolute paths outside quarantine directory are rejected."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a file outside quarantine
        outside_file = tmp_path / "outside" / "secret.txt"
        outside_file.parent.mkdir()
        outside_file.write_text("secret content")

        is_valid, error = handler._validate_quarantine_path(str(outside_file))

        assert is_valid is False
        assert "not inside quarantine directory" in error

    def test_path_traversal_outside_quarantine_rejected(self, tmp_path):
        """Test that .. traversal to escape quarantine directory is rejected."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a file outside quarantine that we'll try to access via traversal
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("secret content")

        # Try to access via .. traversal
        traversal_path = str(quarantine_dir / ".." / "secret.txt")
        is_valid, error = handler._validate_quarantine_path(traversal_path)

        assert is_valid is False
        assert "not inside quarantine directory" in error

    def test_symlink_quarantine_path_rejected(self, tmp_path):
        """Test that symlinks inside quarantine directory are rejected."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a real file outside quarantine
        outside_file = tmp_path / "outside" / "secret.txt"
        outside_file.parent.mkdir()
        outside_file.write_text("secret content")

        # Create a symlink inside quarantine pointing outside
        symlink_path = quarantine_dir / "symlink_to_secret"
        try:
            symlink_path.symlink_to(outside_file)

            is_valid, error = handler._validate_quarantine_path(str(symlink_path))

            assert is_valid is False
            assert "symlink" in error.lower()
        finally:
            if symlink_path.is_symlink():
                symlink_path.unlink()

    def test_empty_quarantine_path_rejected(self, tmp_path):
        """Test that empty paths are rejected."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Test empty string
        is_valid, error = handler._validate_quarantine_path("")
        assert is_valid is False
        assert "cannot be empty" in error

        # Test whitespace-only string
        is_valid, error = handler._validate_quarantine_path("   ")
        assert is_valid is False
        assert "cannot be empty" in error

    def test_nonexistent_path_inside_quarantine_accepted(self, tmp_path):
        """Test that nonexistent paths inside quarantine are accepted.

        This allows validation before file existence check in restore/delete.
        """
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Path that doesn't exist but is inside quarantine
        nonexistent_path = str(quarantine_dir / "nonexistent_file.quar")
        is_valid, error = handler._validate_quarantine_path(nonexistent_path)

        assert is_valid is True
        assert error is None


class TestRestoreFromQuarantinePathValidation:
    """Tests for quarantine path validation in restore_from_quarantine()."""

    def test_restore_rejects_quarantine_path_outside_dir(self, tmp_path):
        """Test that restore_from_quarantine rejects source paths outside quarantine."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a file outside quarantine
        outside_file = tmp_path / "outside" / "secret.txt"
        outside_file.parent.mkdir()
        outside_file.write_text("secret content")

        # Try to restore from outside quarantine
        result = handler.restore_from_quarantine(
            str(outside_file), str(tmp_path / "restored" / "file.txt")
        )

        assert result.status == FileOperationStatus.INVALID_QUARANTINE_PATH
        assert result.error_message is not None
        assert "not inside quarantine directory" in result.error_message

    def test_restore_rejects_symlink_quarantine_path(self, tmp_path):
        """Test that restore_from_quarantine rejects symlink source paths."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a real file outside quarantine
        outside_file = tmp_path / "outside" / "secret.txt"
        outside_file.parent.mkdir()
        outside_file.write_text("secret content")

        # Create a symlink inside quarantine pointing outside
        symlink_path = quarantine_dir / "symlink_to_secret"
        try:
            symlink_path.symlink_to(outside_file)

            result = handler.restore_from_quarantine(
                str(symlink_path), str(tmp_path / "restored" / "file.txt")
            )

            assert result.status == FileOperationStatus.INVALID_QUARANTINE_PATH
            assert "symlink" in result.error_message.lower()
        finally:
            if symlink_path.is_symlink():
                symlink_path.unlink()

    def test_restore_quarantine_path_validation_before_restore_path_validation(self, tmp_path):
        """Test that quarantine path validation happens before restore path validation."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a file outside quarantine
        outside_file = tmp_path / "outside" / "secret.txt"
        outside_file.parent.mkdir()
        outside_file.write_text("secret content")

        # Try to restore from outside quarantine to a protected directory
        # Should fail with INVALID_QUARANTINE_PATH, not INVALID_RESTORE_PATH
        result = handler.restore_from_quarantine(str(outside_file), "/etc/malicious.conf")

        assert result.status == FileOperationStatus.INVALID_QUARANTINE_PATH


class TestDeleteFromQuarantinePathValidation:
    """Tests for quarantine path validation in delete_from_quarantine()."""

    def test_delete_rejects_quarantine_path_outside_dir(self, tmp_path):
        """Test that delete_from_quarantine rejects paths outside quarantine."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a file outside quarantine
        outside_file = tmp_path / "outside" / "important.txt"
        outside_file.parent.mkdir()
        outside_file.write_text("important content")

        # Try to delete file outside quarantine
        result = handler.delete_from_quarantine(str(outside_file))

        assert result.status == FileOperationStatus.INVALID_QUARANTINE_PATH
        assert result.error_message is not None
        assert "not inside quarantine directory" in result.error_message
        # Verify file still exists
        assert outside_file.exists()

    def test_delete_rejects_symlink_quarantine_path(self, tmp_path):
        """Test that delete_from_quarantine rejects symlink paths."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a real file outside quarantine
        outside_file = tmp_path / "outside" / "important.txt"
        outside_file.parent.mkdir()
        outside_file.write_text("important content")

        # Create a symlink inside quarantine pointing outside
        symlink_path = quarantine_dir / "symlink_to_important"
        try:
            symlink_path.symlink_to(outside_file)

            result = handler.delete_from_quarantine(str(symlink_path))

            assert result.status == FileOperationStatus.INVALID_QUARANTINE_PATH
            assert "symlink" in result.error_message.lower()
            # Verify the target file still exists
            assert outside_file.exists()
        finally:
            if symlink_path.is_symlink():
                symlink_path.unlink()

    def test_delete_rejects_path_traversal(self, tmp_path):
        """Test that delete_from_quarantine rejects .. traversal paths."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a file outside quarantine
        outside_file = tmp_path / "important.txt"
        outside_file.write_text("important content")

        # Try to delete via .. traversal
        traversal_path = str(quarantine_dir / ".." / "important.txt")
        result = handler.delete_from_quarantine(traversal_path)

        assert result.status == FileOperationStatus.INVALID_QUARANTINE_PATH
        assert "not inside quarantine directory" in result.error_message
        # Verify file still exists
        assert outside_file.exists()

    def test_delete_accepts_valid_quarantine_path(self, tmp_path):
        """Test that delete_from_quarantine accepts valid paths inside quarantine."""
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        handler = SecureFileHandler(str(quarantine_dir))

        # Create a file inside quarantine
        quarantine_file = quarantine_dir / "abc123_malware.exe"
        quarantine_file.write_text("fake quarantined content")

        result = handler.delete_from_quarantine(str(quarantine_file))

        assert result.status == FileOperationStatus.SUCCESS
        assert not quarantine_file.exists()
