# ClamUI Input Sanitization Module
"""
Input sanitization functions for log entries to prevent log injection attacks.

This module provides functions to sanitize user-controlled input (file paths,
threat names, ClamAV output) before storing in log entries. It protects against:
- Control characters that could manipulate terminal output
- ANSI escape sequences that could hide or modify displayed content
- Unicode bidirectional overrides that could obscure malicious filenames
- Null bytes that could truncate or confuse log parsing
- Newline injection in single-line fields that could forge log entries
"""

import re
from typing import Optional


# ANSI escape sequence pattern (CSI sequences and other escape codes)
# Matches ESC followed by [ and optional parameters, or other ESC sequences
ANSI_ESCAPE_PATTERN = re.compile(
    r"""
    \x1b     # ESC character
    (?:      # Non-capturing group for alternatives
        \[   # CSI sequence: ESC [
        [0-9;]*  # Optional numeric parameters separated by semicolons
        [a-zA-Z] # Final character (command)
    |
        [^[]   # Other ESC sequences (not CSI)
    )
    """,
    re.VERBOSE,
)

# Unicode bidirectional override characters that can be used to obscure text
# U+202A - U+202E: LRE, RLE, PDF, LRO, RLO (deprecated but still supported)
# U+2066 - U+2069: LRI, RLI, FSI, PDI (modern equivalents)
UNICODE_BIDI_PATTERN = re.compile(r"[\u202A-\u202E\u2066-\u2069]")


def sanitize_log_line(text: Optional[str]) -> str:
    """
    Sanitize a string for use in single-line log fields.

    Removes control characters (including newlines), ANSI escape sequences,
    Unicode bidirectional overrides, and null bytes. This function is used
    for single-line fields like summary, path, and threat names where
    newlines could be used to inject fake log entries.

    Safe whitespace characters (space and tab) are preserved.

    Args:
        text: The input string to sanitize. If None, returns empty string.

    Returns:
        Sanitized string safe for single-line log fields

    Example:
        >>> sanitize_log_line("Clean\\npath")
        "Clean path"
        >>> sanitize_log_line("File\\x1b[31mRED\\x1b[0m")
        "FileRED"
        >>> sanitize_log_line("\\x00null\\x00bytes")
        "nullbytes"
    """
    if text is None:
        return ""

    # Remove null bytes first (they can truncate strings in some contexts)
    sanitized = text.replace("\x00", "")

    # Remove ANSI escape sequences
    sanitized = ANSI_ESCAPE_PATTERN.sub("", sanitized)

    # Remove Unicode bidirectional override characters
    sanitized = UNICODE_BIDI_PATTERN.sub("", sanitized)

    # Remove control characters except safe whitespace (space, tab)
    # Control characters are 0x00-0x1F and 0x7F (DEL)
    # We keep: 0x20 (space), 0x09 (tab)
    # We remove: 0x0A (LF), 0x0D (CR), and all other control characters
    result = []
    for char in sanitized:
        code = ord(char)
        # Keep printable characters (>= 0x20) and tab (0x09)
        # Skip all other control characters (0x00-0x1F except 0x09) and DEL (0x7F)
        if code >= 0x20 or code == 0x09:
            if code != 0x7F:  # Skip DEL character
                result.append(char)
        # Control characters (including newlines) are replaced with space
        elif code in (0x0A, 0x0D):  # Newlines specifically become spaces
            result.append(" ")

    return "".join(result)


def sanitize_log_text(text: Optional[str]) -> str:
    """
    Sanitize a string for use in multi-line log fields.

    Removes control characters (except newlines and tabs), ANSI escape sequences,
    Unicode bidirectional overrides, and null bytes. This function is used for
    multi-line fields like details and stdout where legitimate newlines should
    be preserved for readability.

    Safe whitespace characters (space, tab, newline, carriage return) are preserved.

    Args:
        text: The input string to sanitize. If None, returns empty string.

    Returns:
        Sanitized string safe for multi-line log fields

    Example:
        >>> sanitize_log_text("Line 1\\nLine 2")
        "Line 1\\nLine 2"
        >>> sanitize_log_text("Text\\x1b[32mGREEN\\x1b[0m")
        "TextGREEN"
        >>> sanitize_log_text("Data\\x00with\\x00nulls")
        "Datawithnulls"
    """
    if text is None:
        return ""

    # Remove null bytes first
    sanitized = text.replace("\x00", "")

    # Remove ANSI escape sequences
    sanitized = ANSI_ESCAPE_PATTERN.sub("", sanitized)

    # Remove Unicode bidirectional override characters
    sanitized = UNICODE_BIDI_PATTERN.sub("", sanitized)

    # Remove control characters except safe whitespace (space, tab, newline, CR)
    # Control characters are 0x00-0x1F and 0x7F (DEL)
    # We keep: 0x20 (space), 0x09 (tab), 0x0A (LF), 0x0D (CR)
    result = []
    for char in sanitized:
        code = ord(char)
        # Keep printable characters (>= 0x20) and safe whitespace
        if code >= 0x20:
            if code != 0x7F:  # Skip DEL character
                result.append(char)
        elif code in (0x09, 0x0A, 0x0D):  # Keep tab, LF, CR
            result.append(char)
        # All other control characters are silently removed

    return "".join(result)
