# ClamUI Threat Classification Module
"""
Threat classification utilities for ClamAV scan results.

This module provides functions to classify and categorize threats detected
by ClamAV based on their names. It consolidates threat classification logic
used by both the Scanner and DaemonScanner classes.
"""

from enum import Enum


class ThreatSeverity(Enum):
    """Severity level of a detected threat."""

    CRITICAL = "critical"  # Ransomware, Rootkit, Bootkit
    HIGH = "high"  # Trojan, Worm, Backdoor, Exploit
    MEDIUM = "medium"  # Adware, PUA, Spyware, Unknown
    LOW = "low"  # Test signatures (EICAR), Generic detections


# Pattern definitions for threat classification
# Each tuple is (pattern_to_match, result_value)

CRITICAL_PATTERNS: list[str] = ["ransom", "rootkit", "bootkit", "cryptolocker", "wannacry"]

HIGH_PATTERNS: list[str] = [
    "trojan",
    "worm",
    "backdoor",
    "exploit",
    "downloader",
    "dropper",
    "keylogger",
]

MEDIUM_PATTERNS: list[str] = ["adware", "pua", "pup", "spyware", "miner", "coinminer"]

LOW_PATTERNS: list[str] = ["eicar", "test-signature", "test.file", "heuristic", "generic"]

# High-priority category patterns (specific threat types)
# These take precedence over low-priority patterns
HIGH_PRIORITY_CATEGORY_PATTERNS: list[tuple[str, str]] = [
    ("ransomware", "Ransomware"),
    ("ransom", "Ransomware"),
    ("rootkit", "Rootkit"),
    ("bootkit", "Rootkit"),
    ("trojan", "Trojan"),
    ("worm", "Worm"),
    ("backdoor", "Backdoor"),
    ("exploit", "Exploit"),
    ("adware", "Adware"),
    ("spyware", "Spyware"),
    ("keylogger", "Spyware"),
    ("eicar", "Test"),
    ("test-signature", "Test"),
    ("test.file", "Test"),
    ("macro", "Macro"),
    ("phish", "Phishing"),
    ("heuristic", "Heuristic"),
]

# Low-priority category patterns (generic categories)
# Only used if no high-priority pattern matches
LOW_PRIORITY_CATEGORY_PATTERNS: list[tuple[str, str]] = [
    ("pua", "PUA"),
    ("pup", "PUA"),
    ("virus", "Virus"),
]


def classify_threat_severity(threat_name: str) -> ThreatSeverity:
    """
    Classify the severity level of a threat based on its name.

    ClamAV threat names typically follow patterns that indicate the threat type.
    This function analyzes the threat name to determine the severity level.

    Severity levels:
    - CRITICAL: Ransomware, Rootkit, Bootkit (most dangerous)
    - HIGH: Trojan, Worm, Backdoor, Exploit (serious threats)
    - MEDIUM: Adware, PUA, Spyware (less severe but concerning)
    - LOW: Test signatures (EICAR), Generic/Heuristic detections

    Args:
        threat_name: The threat name from ClamAV output (e.g., "Win.Trojan.Agent")

    Returns:
        ThreatSeverity enum value

    Example:
        >>> classify_threat_severity("Win.Ransomware.Locky")
        ThreatSeverity.CRITICAL

        >>> classify_threat_severity("Eicar-Test-Signature")
        ThreatSeverity.LOW
    """
    if not threat_name:
        return ThreatSeverity.MEDIUM

    name_lower = threat_name.lower()

    # Critical: Most dangerous threats
    for pattern in CRITICAL_PATTERNS:
        if pattern in name_lower:
            return ThreatSeverity.CRITICAL

    # High: Serious threats
    for pattern in HIGH_PATTERNS:
        if pattern in name_lower:
            return ThreatSeverity.HIGH

    # Medium: Less severe but concerning
    for pattern in MEDIUM_PATTERNS:
        if pattern in name_lower:
            return ThreatSeverity.MEDIUM

    # Low: Test files and generic detections
    for pattern in LOW_PATTERNS:
        if pattern in name_lower:
            return ThreatSeverity.LOW

    # Default to medium for unknown threats
    return ThreatSeverity.MEDIUM


def classify_threat_severity_str(threat_name: str) -> str:
    """
    Classify the severity level of a threat, returning a string.

    This is a convenience wrapper around classify_threat_severity() that
    returns the severity as a string instead of an enum. Useful for
    serialization or when string values are preferred.

    Args:
        threat_name: The threat name from ClamAV output

    Returns:
        Severity level as string: 'critical', 'high', 'medium', or 'low'
    """
    return classify_threat_severity(threat_name).value


def categorize_threat(threat_name: str) -> str:
    """
    Extract the category of a threat from its name.

    ClamAV threat names typically follow patterns like:
    - "Win.Trojan.Agent" -> "Trojan"
    - "Eicar-Test-Signature" -> "Test"
    - "PUA.Win.Adware.Generic" -> "Adware"

    The function uses two-tier matching:
    1. First, check high-priority patterns (specific threat types like Adware)
    2. Only if no high-priority match, check low-priority patterns (generic like PUA)
    Within each tier, position-based matching is used: when multiple category
    keywords are present, the one appearing earliest in the threat name wins.

    Categories returned:
    - Ransomware: Ransomware, CryptoLocker variants
    - Rootkit: Rootkits and bootkits
    - Trojan: Trojan horse malware
    - Worm: Self-replicating worms
    - Backdoor: Backdoor access tools
    - Exploit: Vulnerability exploits
    - Adware: Advertising software
    - Spyware: Spyware and keyloggers
    - PUA: Potentially Unwanted Applications
    - Test: Test signatures (EICAR)
    - Virus: Generic viruses
    - Macro: Macro viruses
    - Phishing: Phishing attempts
    - Heuristic: Heuristic detections

    Args:
        threat_name: The threat name from ClamAV output

    Returns:
        Category as string (e.g., 'Virus', 'Trojan', 'Worm', etc.)

    Example:
        >>> categorize_threat("Win.Trojan.Agent")
        'Trojan'

        >>> categorize_threat("Eicar-Test-Signature")
        'Test'
    """
    if not threat_name:
        return "Unknown"

    name_lower = threat_name.lower()

    # First, check high-priority patterns by position
    matches = []
    for pattern, category in HIGH_PRIORITY_CATEGORY_PATTERNS:
        pos = name_lower.find(pattern)
        if pos != -1:
            matches.append((pos, category))

    if matches:
        matches.sort(key=lambda x: x[0])
        return matches[0][1]

    # If no high-priority match, check low-priority patterns
    for pattern, category in LOW_PRIORITY_CATEGORY_PATTERNS:
        pos = name_lower.find(pattern)
        if pos != -1:
            matches.append((pos, category))

    if matches:
        matches.sort(key=lambda x: x[0])
        return matches[0][1]

    # Default to "Virus" for unrecognized threats (conservative assumption)
    return "Virus"
