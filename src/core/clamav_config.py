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
    comment: str | None = None
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
    values: dict[str, list[ClamAVConfigValue]] = field(default_factory=dict)
    raw_lines: list[str] = field(default_factory=list)

    def get_value(self, key: str) -> str | None:
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

    def get_values(self, key: str) -> list[str]:
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

    def get_bool(self, key: str) -> bool | None:
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
        if value_lower in ("yes", "true", "1"):
            return True
        if value_lower in ("no", "false", "0"):
            return False
        return None

    def get_int(self, key: str) -> int | None:
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
            return "\n".join(lines) + "\n" if lines else ""

        # Build a map of line numbers to new values
        # Track which values have been written by (key, value_index)
        line_updates: dict[int, str] = {}
        value_indices: dict[str, int] = {}

        for key, _value_list in self.values.items():
            value_indices[key] = 0

        # First pass: identify which lines need updating based on parsed values
        for key, value_list in self.values.items():
            for _idx, config_value in enumerate(value_list):
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
                output_lines.append(line.rstrip("\n\r"))

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
                output_lines.append("")
            output_lines.extend(new_values)

        # Join with newlines and ensure trailing newline
        result = "\n".join(output_lines)
        if result and not result.endswith("\n"):
            result += "\n"
        return result


def parse_config(file_path: str) -> tuple[ClamAVConfig | None, str | None]:
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
        with open(resolved_path, encoding="utf-8") as f:
            raw_lines = f.readlines()
    except UnicodeDecodeError:
        # Try with latin-1 encoding as fallback
        try:
            with open(resolved_path, encoding="latin-1") as f:
                raw_lines = f.readlines()
        except Exception as e:
            return (None, f"Error reading configuration file: {str(e)}")
    except PermissionError:
        return (None, f"Permission denied: Cannot read {file_path}")
    except OSError as e:
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
        if stripped.startswith("#"):
            continue

        # Handle inline comments
        comment = None
        content = stripped
        comment_pos = stripped.find("#")
        if comment_pos > 0:
            # Check if # is not inside a quoted string (basic check)
            before_hash = stripped[:comment_pos]
            # Simple heuristic: if quotes are balanced before #, it's a comment
            if before_hash.count('"') % 2 == 0 and before_hash.count("'") % 2 == 0:
                content = stripped[:comment_pos].strip()
                comment = stripped[comment_pos + 1 :].strip()

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
        config_value = ClamAVConfigValue(value=value, comment=comment, line_number=line_number)

        if key not in config.values:
            config.values[key] = []
        config.values[key].append(config_value)

    return (config, None)


# Configuration option type definitions
# Maps option names to their expected types and validation constraints
CONFIG_OPTION_TYPES = {
    # Path options (directory or file paths)
    "DatabaseDirectory": {"type": "path", "must_exist": False},
    "UpdateLogFile": {"type": "path", "must_exist": False},
    "LogFile": {"type": "path", "must_exist": False},
    "NotifyClamd": {"type": "path", "must_exist": False},
    "PidFile": {"type": "path", "must_exist": False},
    "LocalSocket": {"type": "path", "must_exist": False},
    "TemporaryDirectory": {"type": "path", "must_exist": False},
    # Boolean options
    "LogVerbose": {"type": "boolean"},
    "LogSyslog": {"type": "boolean"},
    "LogTime": {"type": "boolean"},
    "LogRotate": {"type": "boolean"},
    "Foreground": {"type": "boolean"},
    "ScanArchive": {"type": "boolean"},
    "ScanPDF": {"type": "boolean"},
    "ScanHTML": {"type": "boolean"},
    "ScanMail": {"type": "boolean"},
    "ScanOLE2": {"type": "boolean"},
    "ScanPE": {"type": "boolean"},
    "ScanELF": {"type": "boolean"},
    "ScanSWF": {"type": "boolean"},
    "DetectPUA": {"type": "boolean"},
    "AlertBrokenExecutables": {"type": "boolean"},
    "FollowDirectorySymlinks": {"type": "boolean"},
    "FollowFileSymlinks": {"type": "boolean"},
    "CrossFilesystems": {"type": "boolean"},
    # Integer options with ranges
    "Checks": {"type": "integer", "min": 0, "max": 50},
    "HTTPProxyPort": {"type": "integer", "min": 1, "max": 65535},
    "MaxRecursion": {"type": "integer", "min": 0, "max": 100},
    "MaxFiles": {"type": "integer", "min": 0, "max": 100000},
    "MaxThreads": {"type": "integer", "min": 1, "max": 256},
    "MaxDirectoryRecursion": {"type": "integer", "min": 0, "max": 100},
    # Size options that accept integer or size suffix like M, K
    "MaxEmbeddedPE": {"type": "size"},
    "MaxHTMLNormalize": {"type": "size"},
    "MaxHTMLNoTags": {"type": "size"},
    "MaxScriptNormalize": {"type": "size"},
    "MaxZipTypeRcg": {"type": "size"},
    # Pure integer options
    "MaxPartitions": {"type": "integer", "min": 0},
    "MaxIconsPE": {"type": "integer", "min": 0},
    "TCPSocket": {"type": "integer", "min": 1, "max": 65535},
    "IdleTimeout": {"type": "integer", "min": 0},
    "ReadTimeout": {"type": "integer", "min": 0},
    "CommandReadTimeout": {"type": "integer", "min": 0},
    "SendBufTimeout": {"type": "integer", "min": 0},
    # Size options (accept integer or size suffix like M, K)
    "MaxScanSize": {"type": "size"},
    "MaxFileSize": {"type": "size"},
    "StreamMaxLength": {"type": "size"},
    "MaxScanTime": {"type": "integer", "min": 0},
    # String options (no special validation, just non-empty)
    "HTTPProxyServer": {"type": "string"},
    "HTTPProxyUsername": {"type": "string"},
    "HTTPProxyPassword": {"type": "string"},
    "DatabaseMirror": {"type": "string"},
    "DatabaseOwner": {"type": "string"},
    "User": {"type": "string"},
}


def validate_option(key: str, value: str) -> tuple[bool, str | None]:
    """
    Validate a configuration option value.

    Args:
        key: The configuration option name
        value: The value to validate

    Returns:
        Tuple of (is_valid, error_message):
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    if key not in CONFIG_OPTION_TYPES:
        # Unknown option - allow it (ClamAV may support options we don't know about)
        return (True, None)

    option_spec = CONFIG_OPTION_TYPES[key]
    option_type = option_spec.get("type", "string")

    if option_type == "path":
        if not value:
            return (False, f"{key}: path cannot be empty")
        must_exist = option_spec.get("must_exist", False)
        path = Path(value).expanduser()
        if must_exist and not path.exists():
            return (False, f"{key}: path does not exist: {value}")
        return (True, None)

    elif option_type == "boolean":
        if value.lower() not in ("yes", "no", "true", "false", "1", "0"):
            return (False, f"{key}: invalid boolean value: {value}")
        return (True, None)

    elif option_type == "integer":
        try:
            int_val = int(value)
        except ValueError:
            return (False, f"{key}: not a valid integer: {value}")
        # Check range constraints
        if "min" in option_spec and int_val < option_spec["min"]:
            return (
                False,
                f"{key}: value {int_val} is below minimum {option_spec['min']}",
            )
        if "max" in option_spec and int_val > option_spec["max"]:
            return (
                False,
                f"{key}: value {int_val} exceeds maximum {option_spec['max']}",
            )
        return (True, None)

    elif option_type == "size":
        # Parse size with optional suffix (M, K, G, etc.)
        if not value:
            return (False, f"{key}: size cannot be empty")
        # Basic validation - just check it starts with a number
        if not value[0].isdigit():
            return (False, f"{key}: size must start with a number: {value}")
        return (True, None)

    elif option_type == "string":
        if not value:
            return (False, f"{key}: string value cannot be empty")
        return (True, None)

    return (True, None)


def write_config(config: ClamAVConfig) -> tuple[bool, str | None]:
    """
    Write a configuration object back to its file.

    Args:
        config: The ClamAVConfig object to write

    Returns:
        Tuple of (success, error_message):
        - (True, None) on success
        - (False, error_message) on failure
    """
    if not config.file_path:
        return (False, "No file path specified in config object")

    try:
        # Create a backup of the original file
        backup_path = Path(str(config.file_path) + ".bak")
        if config.file_path.exists():
            shutil.copy2(config.file_path, backup_path)

        # Write the updated config
        content = config.to_string()
        with open(config.file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return (True, None)
    except PermissionError:
        return (False, f"Permission denied: Cannot write to {config.file_path}")
    except OSError as e:
        return (False, f"Error writing configuration file: {str(e)}")
    except Exception as e:
        return (False, f"Unexpected error writing configuration: {str(e)}")


def validate_config_file(file_path: str) -> tuple[bool, list[str]]:
    """
    Validate all options in a configuration file.

    Checks that all configuration values are valid according to their type
    and constraints.

    Args:
        file_path: Path to the configuration file

    Returns:
        Tuple of (is_valid, list_of_errors):
        - (True, []) if all options are valid
        - (False, [error1, error2, ...]) if there are validation errors
    """
    config, error = parse_config(file_path)
    if error:
        return (False, [error])

    if config is None:
        return (False, ["Configuration file could not be parsed"])

    errors = []
    for key, value_list in config.values.items():
        for config_value in value_list:
            is_valid, error_msg = validate_option(key, config_value.value)
            if not is_valid:
                errors.append(error_msg)

    return (len(errors) == 0, errors)


def get_config_summary(config: ClamAVConfig) -> str:
    """
    Get a human-readable summary of the configuration.

    Args:
        config: The ClamAVConfig object

    Returns:
        A formatted string summary of the configuration
    """
    if not config.values:
        return "No configuration options defined"

    lines = []
    lines.append(f"Configuration file: {config.file_path}")
    lines.append(f"Total options: {len(config.values)}")
    lines.append("")

    # Group by type
    by_type: dict[str, list[tuple[str, list[str]]]] = {}
    for key, value_list in sorted(config.values.items()):
        option_type = CONFIG_OPTION_TYPES.get(key, {}).get("type", "unknown")
        if option_type not in by_type:
            by_type[option_type] = []
        values = [v.value for v in value_list]
        by_type[option_type].append((key, values))

    for option_type in sorted(by_type.keys()):
        lines.append(f"{option_type.upper()} Options:")
        for key, values in by_type[option_type]:
            if len(values) == 1:
                lines.append(f"  {key}: {values[0]}")
            else:
                lines.append(f"  {key}:")
                for value in values:
                    lines.append(f"    - {value}")
        lines.append("")

    return "\n".join(lines)


def validate_config(config: ClamAVConfig | None) -> tuple[bool, list[str]]:
    """
    Validate all options in a ClamAVConfig object.

    Args:
        config: The ClamAVConfig object to validate (can be None if parse failed)

    Returns:
        Tuple of (is_valid, list_of_errors):
        - (True, []) if all options are valid
        - (False, [error1, error2, ...]) if there are validation errors or config is None
    """
    if config is None:
        return (False, ["Configuration is not loaded. Cannot validate."])

    errors = []
    for key, value_list in config.values.items():
        for config_value in value_list:
            is_valid, error_msg = validate_option(key, config_value.value)
            if not is_valid:
                errors.append(error_msg)

    return (len(errors) == 0, errors)


def backup_config(file_path: str) -> None:
    """
    Create a backup of a configuration file.

    Creates a timestamped backup in the same directory as the original file.

    Args:
        file_path: Path to the configuration file to backup
    """
    path = Path(file_path)
    if not path.exists():
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".bak.{timestamp}")

    try:
        shutil.copy2(path, backup_path)
    except (OSError, PermissionError):
        # Silently fail - backup is best effort
        pass


def write_config_with_elevation(config: ClamAVConfig) -> tuple[bool, str | None]:
    """
    Write a configuration file with elevated privileges using pkexec.

    This is needed for system config files like /etc/clamav/*.conf
    that require root privileges to modify.

    Args:
        config: The ClamAVConfig object to write

    Returns:
        Tuple of (success, error_message):
        - (True, None) on success
        - (False, error_message) on failure
    """
    if not config.file_path:
        return (False, "No file path specified in config object")

    try:
        # Write config to a temporary file first
        content = config.to_string()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Use pkexec to copy the temp file to the target location
            result = subprocess.run(
                ["pkexec", "cp", tmp_path, str(config.file_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                return (False, f"Failed to write config: {error_msg}")

            # Set proper permissions
            subprocess.run(
                ["pkexec", "chmod", "644", str(config.file_path)],
                capture_output=True,
            )

            return (True, None)

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    except FileNotFoundError:
        return (False, "pkexec not found - cannot elevate privileges")
    except Exception as e:
        return (False, f"Unexpected error: {str(e)}")
