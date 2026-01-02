#!/usr/bin/env python3
"""Manual verification script for pre-compiled regex patterns."""

import sys
import re

# Import the module to verify patterns are correctly defined
try:
    from src.core.statistics_calculator import (
        FILES_SCANNED_PATTERNS,
        THREATS_FOUND_PATTERNS,
        StatisticsCalculator,
    )
    from src.core.log_manager import LogEntry

    print("✓ Successfully imported statistics_calculator module")

    # Verify FILES_SCANNED_PATTERNS
    print("\n=== FILES_SCANNED_PATTERNS ===")
    print(f"Type: {type(FILES_SCANNED_PATTERNS)}")
    print(f"Length: {len(FILES_SCANNED_PATTERNS)}")
    assert isinstance(FILES_SCANNED_PATTERNS, list), "Should be a list"
    assert len(FILES_SCANNED_PATTERNS) == 4, "Should have 4 patterns"

    for i, pattern in enumerate(FILES_SCANNED_PATTERNS, 1):
        assert isinstance(pattern, type(re.compile(""))), f"Pattern {i} should be compiled regex"
        print(f"  Pattern {i}: {type(pattern).__name__} ✓")

    # Verify THREATS_FOUND_PATTERNS
    print("\n=== THREATS_FOUND_PATTERNS ===")
    print(f"Type: {type(THREATS_FOUND_PATTERNS)}")
    print(f"Length: {len(THREATS_FOUND_PATTERNS)}")
    assert isinstance(THREATS_FOUND_PATTERNS, list), "Should be a list"
    assert len(THREATS_FOUND_PATTERNS) == 3, "Should have 3 patterns"

    for i, pattern in enumerate(THREATS_FOUND_PATTERNS, 1):
        assert isinstance(pattern, type(re.compile(""))), f"Pattern {i} should be compiled regex"
        print(f"  Pattern {i}: {type(pattern).__name__} ✓")

    # Test pattern functionality with sample data
    print("\n=== FUNCTIONAL TESTS ===")

    # Create a mock log manager
    class MockLogManager:
        def get_logs(self):
            return []

    calc = StatisticsCalculator(log_manager=MockLogManager())

    # Test FILES_SCANNED_PATTERNS
    test_cases_files = [
        ("500 files scanned", 500),
        ("Scanned 1234 files", 1234),
        ("Files: 2500", 2500),
        ("100 files", 100),
        ("No match here", 0),
    ]

    for summary, expected in test_cases_files:
        entry = LogEntry(
            id="test",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status="clean",
            summary=summary,
            details="",
        )
        result = calc._extract_files_scanned(entry)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{summary}' -> {result} (expected {expected})")
        assert result == expected, f"Failed for '{summary}'"

    # Test THREATS_FOUND_PATTERNS
    test_cases_threats = [
        ("3 threats detected", "infected", 3),
        ("Found 5 items", "infected", 5),
        ("Detected 2", "infected", 2),
        ("Malware found", "infected", 1),  # Default to 1
        ("Clean scan", "clean", 0),
    ]

    for summary, status, expected in test_cases_threats:
        entry = LogEntry(
            id="test",
            timestamp="2024-01-15T10:00:00",
            type="scan",
            status=status,
            summary=summary,
            details="",
        )
        result = calc._extract_threats_found(entry)
        check = "✓" if result == expected else "✗"
        print(f"  {check} '{summary}' ({status}) -> {result} (expected {expected})")
        assert result == expected, f"Failed for '{summary}'"

    print("\n" + "="*50)
    print("✓ ALL VERIFICATION TESTS PASSED!")
    print("="*50)
    sys.exit(0)

except Exception as e:
    print(f"\n✗ VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
