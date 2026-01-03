# ClamUI ClamAV Configuration Module
"""
ClamAV configuration file parser and writer.
Supports reading and modifying freshclam.conf and clamd.conf files.
"""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ClamAVConfigValue:
    """
    Represents a single configuration value with metadata.

    ClamAV config files may have multiple lines with the same key
    (e.g., multiple DatabaseMirror entries), so each value tracks
    its position in the file for accurate reconstruction.

    Attributes:
        value: The configuration value as a string
        comment: Optional inline comment associated with this value
        line_number: The line number where this value appears (1-indexed)
    """
    value: str
    comment: Optional[str] = None
    line_number: int = 0


@dataclass
class ClamAVConfig:
    """
    Parsed ClamAV configuration file.

    Stores configuration values from ClamAV config files (freshclam.conf,
    clamd.conf) while preserving the original file structure for accurate
    reconstruction when writing changes.

    ClamAV config format:
    - Key-value pairs separated by space (not INI format, no sections)
    - Comments start with #
    - Multi-value options allowed (multiple lines with same key)
    - Boolean values are typically 'yes' or 'no'

    Attributes:
        file_path: Path to the configuration file
        values: Dictionary mapping option names to lists of ClamAVConfigValue.
                Lists are used because some options (like DatabaseMirror)
                can have multiple values.
        raw_lines: Original lines from the file for accurate reconstruction
    """
    file_path: Path
    values: Dict[str, List[ClamAVConfigValue]] = field(default_factory=dict)
    raw_lines: List[str] = field(default_factory=list)

    def get_value(self, key: str) -> Optional[str]:
        """
        Get the first value for a configuration key.

        Args:
            key: The configuration option name

        Returns:
            The first value if the key exists, None otherwise
        """
        if key in self.values and self.values[key]:
            return self.values[key][0].value
        return None

    def get_values(self, key: str) -> List[str]:
        """
        Get all values for a configuration key.

        Useful for multi-value options like DatabaseMirror.

        Args:
            key: The configuration option name

        Returns:
            List of all values for the key, empty list if key doesn't exist
        """
        if key in self.values:
            return [v.value for v in self.values[key]]
        return []

    def set_value(self, key: str, value: str, line_number: int = 0) -> None:
        """
        Set a single value for a configuration key.

        Replaces any existing values for the key.

        Args:
            key: The configuration option name
            value: The value to set
            line_number: Optional line number for this value
        """
        self.values[key] = [ClamAVConfigValue(value=value, line_number=line_number)]

    def add_value(self, key: str, value: str, line_number: int = 0) -> None:
        """
        Add a value to a configuration key (for multi-value options).

        Args:
            key: The configuration option name
            value: The value to add
            line_number: Optional line number for this value
        """
        if key not in self.values:
            self.values[key] = []
        self.values[key].append(ClamAVConfigValue(value=value, line_number=line_number))

    def has_key(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: The configuration option name

        Returns:
            True if the key exists with at least one value
        """
        return key in self.values and len(self.values[key]) > 0

    def get_bool(self, key: str) -> Optional[bool]:
        """
        Get a boolean configuration value.

        ClamAV uses 'yes'/'no' or 'true'/'false' for booleans.

        Args:
            key: The configuration option name

        Returns:
            True if value is 'yes'/'true', False if 'no'/'false', None if missing
        """
        value = self.get_value(key)
        if value is None:
            return None
        value_lower = value.lower()
        if value_lower in ('yes', 'true', '1'):
            return True
        if value_lower in ('no', 'false', '0'):
            return False
        return None

    def get_int(self, key: str) -> Optional[int]:
        """
        Get an integer configuration value.

        Args:
            key: The configuration option name

        Returns:
            The integer value if valid, None otherwise
        """
        value = self.get_value(key)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def to_string(self) -> str:
        """
        Serialize the configuration back to a string.

        Preserves the original file structure by using raw_lines as a base
        and updating only the modified values. Comments and empty lines
        are preserved in their original positions.

        Returns:
            The configuration as a string ready to write to a file
        """
        if not self.raw_lines:
            # No original content - generate from values only
            lines = []
            for key, value_list in self.values.items():
                for config_value in value_list:
                    if config_value.value:
                        lines.append(f"{key} {config_value.value}")
                    else:
                        # Boolean-style option with no value
                        lines.append(key)
            return '\n'.join(lines) + '\n' if lines else ''

        # Build a map of line numbers to new values
        # Track which values have been written by (key, value_index)
        line_updates: Dict[int, str] = {}
        value_indices: Dict[str, int] = {}

        for key, value_list in self.values.items():
            value_indices[key] = 0

        # First pass: identify which lines need updating based on parsed values
        for key, value_list in self.values.items():
            for idx, config_value in enumerate(value_list):
                if config_value.line_number > 0:
                    # This value has a known line number - update that line
                    if config_value.value:
                        new_line = f"{key} {config_value.value}"
                    else:
                        new_line = key
                    # Preserve inline comment if present
                    if config_value.comment:
                        new_line += f" # {config_value.comment}"
                    line_updates[config_value.line_number] = new_line

        # Build output lines
        output_lines = []
        for line_number, line in enumerate(self.raw_lines, start=1):
            if line_number in line_updates:
                # Replace this line with updated value
                output_lines.append(line_updates[line_number])
            else:
                # Keep original line (strip trailing newline for consistency)
                output_lines.append(line.rstrip('\n\r'))

        # Add any new values that don't have line numbers
        new_values = []
        for key, value_list in self.values.items():
            for config_value in value_list:
                if config_value.line_number == 0:
                    # New value without a line number
                    if config_value.value:
                        new_values.append(f"{key} {config_value.value}")
                    else:
                        new_values.append(key)

        if new_values:
            # Add blank line separator if content exists
            if output_lines and output_lines[-1].strip():
                output_lines.append('')
            output_lines.extend(new_values)

        # Join with newlines and ensure trailing newline
        result = '\n'.join(output_lines)
        if result and not result.endswith('\n'):
            result += '\n'
        return result


def parse_config(file_path: str) -> Tuple[Optional[ClamAVConfig], Optional[str]]:
    """
    Parse a ClamAV configuration file.

    Reads and parses ClamAV config files (freshclam.conf, clamd.conf) which use
    a simple key-value format (not INI format, no sections).

    Format:
    - Key Value (separated by space, value is everything after first space)
    - Lines starting with # are comments
    - Empty lines are preserved
    - Same key can appear multiple times (multi-value options)

    Args:
        file_path: Path to the configuration file

    Returns:
        Tuple of (config, error):
        - (ClamAVConfig, None) on success
        - (None, error_message) on failure
    """
    # Validate file path
    if not file_path or not file_path.strip():
        return (None, "No configuration file path specified")

    try:
        resolved_path = Path(file_path).resolve()
    except (OSError, RuntimeError) as e:
        return (None, f"Invalid file path: {str(e)}")

    # Check if file exists
    if not resolved_path.exists():
        return (None, f"Configuration file not found: {file_path}")

    # Check if it's a file (not a directory)
    if not resolved_path.is_file():
        return (None, f"Path is not a file: {file_path}")

    # Check if file is readable
    if not os.access(resolved_path, os.R_OK):
        return (None, f"Permission denied: Cannot read {file_path}")

    # Read and parse the file
    try:
        with open(resolved_path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()
    except UnicodeDecodeError:
        # Try with latin-1 encoding as fallback
        try:
            with open(resolved_path, 'r', encoding='latin-1') as f:
                raw_lines = f.readlines()
        except Exception as e:
            return (None, f"Error reading configuration file: {str(e)}")
    except PermissionError:
        return (None, f"Permission denied: Cannot read {file_path}")
    except IOError as e:
        return (None, f"Error reading configuration file: {str(e)}")

    # Create config object
    config = ClamAVConfig(file_path=resolved_path, raw_lines=raw_lines)

    # Parse each line
    for line_number, line in enumerate(raw_lines, start=1):
        # Strip trailing whitespace/newline but preserve leading whitespace for raw_lines
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Skip comment lines
        if stripped.startswith('#'):
            continue

        # Handle inline comments
        comment = None
        content = stripped
        comment_pos = stripped.find('#')
        if comment_pos > 0:
            # Check if # is not inside a quoted string (basic check)
            before_hash = stripped[:comment_pos]
            # Simple heuristic: if quotes are balanced before #, it's a comment
            if before_hash.count('"') % 2 == 0 and before_hash.count("'") % 2 == 0:
                content = stripped[:comment_pos].strip()
                comment = stripped[comment_pos + 1:].strip()

        # Parse key-value pair
        # ClamAV format: Key Value (separated by first space)
        parts = content.split(None, 1)  # Split on first whitespace

        if len(parts) == 0:
            # Empty after stripping (shouldn't happen, but handle it)
            continue

        key = parts[0]

        # Value is everything after the key (may be empty for boolean-style options)
        value = parts[1] if len(parts) > 1 else ""

        # Add value to config (supports multi-value options)
        config_value = ClamAVConfigValue(
            value=value,
            comment=comment,
            line_number=line_number
        )

        if key not in config.values:
            config.values[key] = []
        config.values[key].append(config_value)

    return (config, None)


# Configuration option type definitions
# Maps option names to their expected types and validation constraints
CONFIG_OPTION_TYPES = {
    # Path options (directory or file paths)
    'DatabaseDirectory': {'type': 'path', 'must_exist': False},
    'UpdateLogFile': {'type': 'path', 'must_exist': False},
    'LogFile': {'type': 'path', 'must_exist': False},
    'NotifyClamd': {'type': 'path', 'must_exist': False},
    'PidFile': {'type': 'path', 'must_exist': False},
    'LocalSocket': {'type': 'path', 'must_exist': False},
    'TemporaryDirectory': {'type': 'path', 'must_exist': False},

    # Boolean options
    'LogVerbose': {'type': 'boolean'},
    'LogSyslog': {'type': 'boolean'},
    'LogTime': {'type': 'boolean'},
    'LogRotate': {'type': 'boolean'},
    'Foreground': {'type': 'boolean'},
    'ScanArchive': {'type': 'boolean'},
    'ScanPDF': {'type': 'boolean'},
    'ScanHTML': {'type': 'boolean'},
    'ScanMail': {'type': 'boolean'},
    'ScanOLE2': {'type': 'boolean'},
    'ScanPE': {'type': 'boolean'},
    'ScanELF': {'type': 'boolean'},
    'ScanSWF': {'type': 'boolean'},
    'DetectPUA': {'type': 'boolean'},
    'AlertBrokenExecutables': {'type': 'boolean'},
    'FollowDirectorySymlinks': {'type': 'boolean'},
    'FollowFileSymlinks': {'type': 'boolean'},
    'CrossFilesystems': {'type': 'boolean'},

    # Integer options with ranges
    'Checks': {'type': 'integer', 'min': 0, 'max': 50},
    'HTTPProxyPort': {'type': 'integer', 'min': 1, 'max': 65535},
    'MaxRecursion': {'type': 'integer', 'min': 0, 'max': 100},
    'MaxFiles': {'type': 'integer', 'min': 0, 'max': 100000},
    'MaxThreads': {'type': 'integer', 'min': 1, 'max': 256},
    'MaxDirectoryRecursion': {'type': 'integer', 'min': 0, 'max': 100},
    # Size options that accept integer or size suffix like M, K
    'MaxEmbeddedPE': {'type': 'size'},
    'MaxHTMLNormalize': {'type': 'size'},
    'MaxHTMLNoTags': {'type': 'size'},
    'MaxScriptNormalize': {'type': 'size'},
    'MaxZipTypeRcg': {'type': 'size'},
    # Pure integer options
    'MaxPartitions': {'type': 'integer', 'min': 0},
    'MaxIconsPE': {'type': 'integer', 'min': 0},
    'TCPSocket': {'type': 'integer', 'min': 1, 'max': 65535},
    'IdleTimeout': {'type': 'integer', 'min': 0},
    'ReadTimeout': {'type': 'integer', 'min': 0},
    'CommandReadTimeout': {'type': 'integer', 'min': 0},
    'SendBufTimeout': {'type': 'integer', 'min': 0},

    # Size options (accept integer or size suffix like M, K)
    'MaxScanSize': {'type': 'size'},
    'MaxFileSize': {'type': 'size'},
    'StreamMaxLength': {'type': 'size'},
    'MaxScanTime': {'type': 'integer', 'min': 0},

    # String options (no special validation, just non-empty)
    'HTTPProxyServer': {'type': 'string'},
    'HTTPProxyUsername': {'type': 'string'},
    'HTTPProxyPassword': {'type': 'string'},
    'DatabaseMirror': {'type': 'string'},
    'DatabaseOwner': {'type': 'string'},
    'TCPAddr': {'type': 'string'},
    'User': {'type': 'string'},
    'LocalSocketGroup': {'type': 'string'},
    'LocalSocketMode': {'type': 'string'},

    # On-Access scanning options (clamonacc)
    # Path options
    'OnAccessIncludePath': {'type': 'path', 'must_exist': False},
    'OnAccessExcludePath': {'type': 'path', 'must_exist': False},
    'OnAccessMountPath': {'type': 'path', 'must_exist': False},

    # Boolean options
    'OnAccessPrevention': {'type': 'boolean'},
    'OnAccessExtraScanning': {'type': 'boolean'},
    'OnAccessDenyOnError': {'type': 'boolean'},
    'OnAccessDisableDDD': {'type': 'boolean'},
    'OnAccessExcludeRootUID': {'type': 'boolean'},

    # Integer options
    'OnAccessMaxThreads': {'type': 'integer', 'min': 1, 'max': 256},
    'OnAccessCurlTimeout': {'type': 'integer', 'min': 0, 'max': 60000},
    'OnAccessRetryAttempts': {'type': 'integer', 'min': 0, 'max': 10},
    'OnAccessExcludeUID': {'type': 'integer', 'min': 0},

    # Size options
    'OnAccessMaxFileSize': {'type': 'size'},

    # String options
    'OnAccessExcludeUname': {'type': 'string'},
}


def validate_path(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a path configuration value.

    Checks that the path is well-formed. Does not require the path to exist
    since config files may reference paths that will be created.

    Args:
        value: The path value to validate

    Returns:
        Tuple of (is_valid, error_message):
        - (True, None) if path is valid
        - (False, error_message) if path is invalid
    """
    if not value or not value.strip():
        return (False, "Path cannot be empty")

    try:
        # Check if it's a valid path format
        path = Path(value)

        # Check for obviously invalid paths
        if not path.parts:
            return (False, "Invalid path format")

        # Path should be absolute for system configs
        if not path.is_absolute():
            return (False, "Path must be absolute")

        return (True, None)
    except (OSError, RuntimeError, ValueError) as e:
        return (False, f"Invalid path format: {str(e)}")


def validate_integer(value: str, min_val: Optional[int] = None,
                     max_val: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate an integer configuration value.

    Args:
        value: The integer value to validate (as string)
        min_val: Optional minimum allowed value (inclusive)
        max_val: Optional maximum allowed value (inclusive)

    Returns:
        Tuple of (is_valid, error_message):
        - (True, None) if integer is valid
        - (False, error_message) if integer is invalid
    """
    if not value or not value.strip():
        return (False, "Integer value cannot be empty")

    try:
        int_val = int(value.strip())
    except ValueError:
        return (False, f"Invalid integer value: {value}")

    if min_val is not None and int_val < min_val:
        return (False, f"Value must be at least {min_val}")

    if max_val is not None and int_val > max_val:
        return (False, f"Value must be at most {max_val}")

    return (True, None)


def validate_boolean(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a boolean configuration value.

    ClamAV accepts 'yes', 'no', 'true', 'false', '1', '0' as boolean values.

    Args:
        value: The boolean value to validate (as string)

    Returns:
        Tuple of (is_valid, error_message):
        - (True, None) if boolean is valid
        - (False, error_message) if boolean is invalid
    """
    if not value or not value.strip():
        return (False, "Boolean value cannot be empty")

    value_lower = value.strip().lower()
    valid_values = ('yes', 'no', 'true', 'false', '1', '0')

    if value_lower not in valid_values:
        return (False, f"Invalid boolean value: {value}. Use 'yes' or 'no'")

    return (True, None)


def validate_size(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a size configuration value.

    ClamAV accepts sizes as integers with optional suffix (K, M, G).

    Args:
        value: The size value to validate (e.g., "25M", "1024K", "100")

    Returns:
        Tuple of (is_valid, error_message):
        - (True, None) if size is valid
        - (False, error_message) if size is invalid
    """
    if not value or not value.strip():
        return (False, "Size value cannot be empty")

    value = value.strip().upper()

    # Check for size suffix
    suffix = ''
    num_part = value

    if value.endswith(('K', 'M', 'G')):
        suffix = value[-1]
        num_part = value[:-1]

    try:
        num_val = int(num_part)
        if num_val < 0:
            return (False, "Size cannot be negative")
        return (True, None)
    except ValueError:
        return (False, f"Invalid size value: {value}. Use integer or integer with K/M/G suffix")


def validate_string(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a string configuration value.

    String values just need to be non-empty (after stripping whitespace).

    Args:
        value: The string value to validate

    Returns:
        Tuple of (is_valid, error_message):
        - (True, None) if string is valid
        - (False, error_message) if string is invalid
    """
    # Empty strings are allowed for some options, so we just do basic validation
    # Allow any non-null value
    if value is None:
        return (False, "Value cannot be None")

    return (True, None)


def validate_config_value(key: str, value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a configuration value based on its key.

    Looks up the expected type for the key and applies appropriate validation.
    Unknown keys are accepted without validation.

    Args:
        key: The configuration option name
        value: The value to validate

    Returns:
        Tuple of (is_valid, error_message):
        - (True, None) if value is valid for the key
        - (False, error_message) if value is invalid
    """
    # Get option definition
    option_def = CONFIG_OPTION_TYPES.get(key)

    if option_def is None:
        # Unknown option - accept any value
        return (True, None)

    opt_type = option_def.get('type', 'string')

    if opt_type == 'path':
        return validate_path(value)
    elif opt_type == 'integer':
        min_val = option_def.get('min')
        max_val = option_def.get('max')
        return validate_integer(value, min_val, max_val)
    elif opt_type == 'boolean':
        return validate_boolean(value)
    elif opt_type == 'size':
        return validate_size(value)
    elif opt_type == 'string':
        return validate_string(value)
    else:
        # Unknown type - accept any value
        return (True, None)


def validate_config(config: ClamAVConfig) -> Tuple[bool, List[str]]:
    """
    Validate all values in a ClamAV configuration.

    Args:
        config: The ClamAVConfig object to validate

    Returns:
        Tuple of (is_valid, errors):
        - (True, []) if all values are valid
        - (False, [error_messages]) if any values are invalid
    """
    errors = []

    for key, value_list in config.values.items():
        for config_value in value_list:
            is_valid, error = validate_config_value(key, config_value.value)
            if not is_valid:
                errors.append(f"{key}: {error}")

    return (len(errors) == 0, errors)


def write_config_with_elevation(config: ClamAVConfig) -> Tuple[bool, Optional[str]]:
    """
    Write configuration file with root permissions via pkexec.

    ClamAV configuration files are typically located in /etc/clamav/ and
    require root permissions to modify. This function writes the config
    to a temporary file first, then uses pkexec to copy it to the target
    location with elevated privileges.

    Args:
        config: The ClamAVConfig object to write

    Returns:
        Tuple of (success, error):
        - (True, None) on success
        - (False, error_message) on failure
    """
    if config.file_path is None:
        return (False, "No file path specified in configuration")

    # Validate the configuration before writing
    is_valid, errors = validate_config(config)
    if not is_valid:
        return (False, f"Configuration validation failed: {'; '.join(errors)}")

    # Generate the config content
    try:
        config_content = config.to_string()
    except Exception as e:
        return (False, f"Failed to serialize configuration: {str(e)}")

    # Write to a temporary file first
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.conf',
            encoding='utf-8'
        ) as f:
            f.write(config_content)
            temp_path = f.name

        # Use pkexec to copy the temp file to the target location
        try:
            result = subprocess.run(
                ['pkexec', 'cp', temp_path, str(config.file_path)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return (True, None)

            # Handle pkexec-specific errors
            stderr = result.stderr.strip() if result.stderr else ""
            if result.returncode == 126:
                # User dismissed the authentication dialog
                return (False, "Authentication cancelled")
            elif result.returncode == 127:
                return (False, "pkexec not found - cannot elevate privileges")
            else:
                return (False, stderr or "Permission denied")

        except subprocess.TimeoutExpired:
            return (False, "Operation timed out waiting for authentication")
        except FileNotFoundError:
            return (False, "pkexec not found - cannot elevate privileges")
        except PermissionError as e:
            return (False, f"Permission denied: {str(e)}")
        except Exception as e:
            return (False, f"Failed to write configuration: {str(e)}")

    except IOError as e:
        return (False, f"Failed to create temporary file: {str(e)}")
    except Exception as e:
        return (False, f"Unexpected error: {str(e)}")
    finally:
        # Clean up the temporary file
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except (OSError, PermissionError):
                pass  # Best effort cleanup


def backup_config(config_path: str) -> Tuple[bool, str]:
    """
    Create a timestamped backup of a configuration file.

    Creates a backup copy of the specified configuration file with a
    timestamp in the filename. The backup is created in the same directory
    as the original file.

    Backup filename format: {original_name}.backup.{YYYYMMDD_HHMMSS}
    Example: freshclam.conf.backup.20251230_143256

    Args:
        config_path: Path to the configuration file to back up

    Returns:
        Tuple of (success, result):
        - (True, backup_path) on success, where backup_path is the path
          to the created backup file
        - (False, error_message) on failure
    """
    # Validate input
    if not config_path or not config_path.strip():
        return (False, "No configuration file path specified")

    try:
        resolved_path = Path(config_path).resolve()
    except (OSError, RuntimeError) as e:
        return (False, f"Invalid file path: {str(e)}")

    # Check if source file exists
    if not resolved_path.exists():
        return (False, f"Configuration file not found: {config_path}")

    # Check if it's a file (not a directory)
    if not resolved_path.is_file():
        return (False, f"Path is not a file: {config_path}")

    # Check if source file is readable
    if not os.access(resolved_path, os.R_OK):
        return (False, f"Permission denied: Cannot read {config_path}")

    # Generate timestamped backup filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{config_path}.backup.{timestamp}"

    try:
        # Use shutil.copy2 to preserve metadata (permissions, timestamps)
        shutil.copy2(resolved_path, backup_path)
        return (True, backup_path)
    except PermissionError:
        return (False, f"Permission denied: Cannot create backup at {backup_path}")
    except OSError as e:
        return (False, f"Failed to create backup: {str(e)}")
    except Exception as e:
        return (False, f"Unexpected error creating backup: {str(e)}")
