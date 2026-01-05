# ClamUI Input Sanitization Tests
"""Unit tests for the sanitize module functions."""

from src.core.sanitize import sanitize_log_line, sanitize_log_text


class TestSanitizeLogLine:
    """Tests for the sanitize_log_line function (single-line fields)."""

    def test_sanitize_log_line_clean_text(self):
        """Test sanitize_log_line with clean text - no changes."""
        assert (
            sanitize_log_line("Clean text without special characters")
            == "Clean text without special characters"
        )

    def test_sanitize_log_line_none_input(self):
        """Test sanitize_log_line with None input returns empty string."""
        assert sanitize_log_line(None) == ""

    def test_sanitize_log_line_empty_string(self):
        """Test sanitize_log_line with empty string returns empty string."""
        assert sanitize_log_line("") == ""

    def test_sanitize_log_line_whitespace_only(self):
        """Test sanitize_log_line with whitespace-only string preserves spaces and tabs."""
        assert sanitize_log_line("   \t  ") == "   \t  "

    def test_sanitize_log_line_removes_newlines(self):
        """Test sanitize_log_line removes newline characters (LF)."""
        assert sanitize_log_line("Line 1\nLine 2") == "Line 1 Line 2"
        assert sanitize_log_line("Line 1\n\nLine 2") == "Line 1  Line 2"

    def test_sanitize_log_line_removes_carriage_returns(self):
        """Test sanitize_log_line removes carriage return characters (CR)."""
        assert sanitize_log_line("Line 1\rLine 2") == "Line 1 Line 2"
        assert sanitize_log_line("Line 1\r\nLine 2") == "Line 1  Line 2"

    def test_sanitize_log_line_preserves_tabs(self):
        """Test sanitize_log_line preserves tab characters."""
        assert sanitize_log_line("Column1\tColumn2\tColumn3") == "Column1\tColumn2\tColumn3"

    def test_sanitize_log_line_preserves_spaces(self):
        """Test sanitize_log_line preserves space characters."""
        assert sanitize_log_line("Word1 Word2  Word3   Word4") == "Word1 Word2  Word3   Word4"

    def test_sanitize_log_line_removes_null_bytes(self):
        """Test sanitize_log_line removes null bytes."""
        assert sanitize_log_line("Text\x00with\x00nulls") == "Textwithnulls"
        assert sanitize_log_line("\x00Start") == "Start"
        assert sanitize_log_line("End\x00") == "End"

    def test_sanitize_log_line_removes_ansi_escape_sequences(self):
        """Test sanitize_log_line removes ANSI escape sequences."""
        # Basic color codes
        assert sanitize_log_line("Normal\x1b[31mRED\x1b[0m") == "NormalRED"
        assert sanitize_log_line("\x1b[32mGREEN\x1b[0m") == "GREEN"
        assert sanitize_log_line("\x1b[1;33mYELLOW BOLD\x1b[0m") == "YELLOW BOLD"

        # Cursor movement
        assert sanitize_log_line("Text\x1b[2JClear") == "TextClear"
        assert sanitize_log_line("\x1b[HHome") == "Home"

        # Complex ANSI sequences
        assert sanitize_log_line("\x1b[1;31;40mComplex\x1b[0m") == "Complex"

    def test_sanitize_log_line_removes_unicode_bidi_overrides(self):
        """Test sanitize_log_line removes Unicode bidirectional override characters."""
        # U+202A - U+202E (deprecated but still supported)
        assert sanitize_log_line("Text\u202aOverride\u202c") == "TextOverride"
        assert sanitize_log_line("\u202bLRE\u202c") == "LRE"
        assert sanitize_log_line("Test\u202dTest\u202c") == "TestTest"

        # U+2066 - U+2069 (modern equivalents)
        assert sanitize_log_line("Text\u2066Override\u2069") == "TextOverride"
        assert sanitize_log_line("\u2067RLI\u2069") == "RLI"
        assert sanitize_log_line("Test\u2068FSI\u2069") == "TestFSI"

    def test_sanitize_log_line_removes_control_characters(self):
        """Test sanitize_log_line removes various control characters."""
        # Bell, backspace, form feed, etc.
        assert sanitize_log_line("Text\x07Bell") == "TextBell"
        assert sanitize_log_line("Text\x08Backspace") == "TextBackspace"
        assert sanitize_log_line("Text\x0cFormFeed") == "TextFormFeed"

        # DEL character (0x7F)
        assert sanitize_log_line("Text\x7fDEL") == "TextDEL"

        # Various control characters
        assert sanitize_log_line("\x01\x02\x03Text") == "Text"
        assert sanitize_log_line("Text\x1b\x1cTest") == "TextTest"

    def test_sanitize_log_line_combined_malicious_input(self):
        """Test sanitize_log_line with combined malicious characters."""
        # Combining newlines, ANSI, null bytes, and bidi overrides
        malicious = "Path\x00\nFile\x1b[31m\u202aEvil\u202c\x1b[0m"
        # Should remove: \x00, \n (becomes space), \x1b[31m, \u202A, \u202C, \x1b[0m
        assert sanitize_log_line(malicious) == "Path FileEvil"

    def test_sanitize_log_line_log_injection_attempt(self):
        """Test sanitize_log_line prevents log injection with fake entries."""
        # Attacker tries to inject a fake log entry using newlines
        injection = "legitimate.txt\n[CLEAN] Fake scan result for malware.exe"
        # Newlines should become spaces, preventing injection
        assert (
            sanitize_log_line(injection)
            == "legitimate.txt [CLEAN] Fake scan result for malware.exe"
        )

    def test_sanitize_log_line_ansi_obfuscation_attempt(self):
        """Test sanitize_log_line prevents ANSI-based obfuscation."""
        # Attacker tries to hide text with ANSI sequences
        obfuscated = "safe.txt\x1b[8mHIDDEN_MALWARE\x1b[0m"
        # Hidden text should be revealed (ANSI codes removed)
        assert sanitize_log_line(obfuscated) == "safe.txtHIDDEN_MALWARE"

    def test_sanitize_log_line_unicode_spoofing(self):
        """Test sanitize_log_line prevents Unicode direction spoofing."""
        # Right-to-left override to reverse displayed text
        # "file\u202Etxt.evil" displays as "file" + "live.txt" (reversed)
        spoofed = "file\u202etxt.evil"
        assert sanitize_log_line(spoofed) == "filetxt.evil"

    def test_sanitize_log_line_very_long_string(self):
        """Test sanitize_log_line handles very long strings."""
        # 10,000 character string
        long_text = "A" * 10000
        result = sanitize_log_line(long_text)
        assert len(result) == 10000
        assert result == long_text

        # Long string with malicious content spread throughout
        long_malicious = ("Clean" + "\x00" + "Text" + "\n") * 1000
        result = sanitize_log_line(long_malicious)
        # Each iteration: "CleanText " (10 chars)
        assert len(result) == 10000
        assert "\x00" not in result
        assert "\n" not in result

    def test_sanitize_log_line_preserves_unicode_text(self):
        """Test sanitize_log_line preserves legitimate Unicode characters."""
        # Various language scripts
        assert sanitize_log_line("文档/テスト/résumé.pdf") == "文档/テスト/résumé.pdf"
        assert sanitize_log_line("Привет мир") == "Привет мир"
        assert sanitize_log_line("🔒 secure_file.txt") == "🔒 secure_file.txt"

    def test_sanitize_log_line_special_characters(self):
        """Test sanitize_log_line preserves legitimate special characters."""
        # File path characters
        assert sanitize_log_line("/home/user/file.txt") == "/home/user/file.txt"
        assert sanitize_log_line("C:\\Users\\file.exe") == "C:\\Users\\file.exe"

        # Common punctuation
        assert sanitize_log_line("File (copy).txt") == "File (copy).txt"
        assert sanitize_log_line("project-v2.1_final!.zip") == "project-v2.1_final!.zip"

    def test_sanitize_log_line_mixed_safe_and_unsafe(self):
        """Test sanitize_log_line with mix of safe and unsafe characters."""
        # Legitimate path with injected control characters
        mixed = "/home/user\x00/Documents\nmalicious\x1b[31m/file.txt"
        assert sanitize_log_line(mixed) == "/home/user/Documents malicious/file.txt"

    def test_sanitize_log_line_multiple_spaces_preserved(self):
        """Test sanitize_log_line preserves multiple consecutive spaces."""
        assert sanitize_log_line("Text    with    spaces") == "Text    with    spaces"

    def test_sanitize_log_line_only_control_characters(self):
        """Test sanitize_log_line with only control characters."""
        # Should return mostly empty or spaces
        assert sanitize_log_line("\x00\x01\x02") == ""
        assert sanitize_log_line("\n\r\n") == "   "  # Newlines become spaces

    def test_sanitize_log_line_starts_with_control_chars(self):
        """Test sanitize_log_line with control characters at start."""
        assert sanitize_log_line("\x00\x01Clean") == "Clean"
        assert sanitize_log_line("\nClean") == " Clean"

    def test_sanitize_log_line_ends_with_control_chars(self):
        """Test sanitize_log_line with control characters at end."""
        assert sanitize_log_line("Clean\x00\x01") == "Clean"
        assert sanitize_log_line("Clean\n") == "Clean "


class TestSanitizeLogText:
    """Tests for the sanitize_log_text function (multi-line fields)."""

    def test_sanitize_log_text_clean_text(self):
        """Test sanitize_log_text with clean text - no changes."""
        assert (
            sanitize_log_text("Clean text without special characters")
            == "Clean text without special characters"
        )

    def test_sanitize_log_text_none_input(self):
        """Test sanitize_log_text with None input returns empty string."""
        assert sanitize_log_text(None) == ""

    def test_sanitize_log_text_empty_string(self):
        """Test sanitize_log_text with empty string returns empty string."""
        assert sanitize_log_text("") == ""

    def test_sanitize_log_text_preserves_newlines(self):
        """Test sanitize_log_text preserves newline characters (LF)."""
        assert sanitize_log_text("Line 1\nLine 2") == "Line 1\nLine 2"
        assert sanitize_log_text("Line 1\n\nLine 2") == "Line 1\n\nLine 2"
        assert sanitize_log_text("Line 1\nLine 2\nLine 3") == "Line 1\nLine 2\nLine 3"

    def test_sanitize_log_text_preserves_carriage_returns(self):
        """Test sanitize_log_text preserves carriage return characters (CR)."""
        assert sanitize_log_text("Line 1\rLine 2") == "Line 1\rLine 2"
        assert sanitize_log_text("Line 1\r\nLine 2") == "Line 1\r\nLine 2"

    def test_sanitize_log_text_preserves_tabs(self):
        """Test sanitize_log_text preserves tab characters."""
        assert sanitize_log_text("Column1\tColumn2\tColumn3") == "Column1\tColumn2\tColumn3"

    def test_sanitize_log_text_preserves_spaces(self):
        """Test sanitize_log_text preserves space characters."""
        assert sanitize_log_text("Word1 Word2  Word3   Word4") == "Word1 Word2  Word3   Word4"

    def test_sanitize_log_text_removes_null_bytes(self):
        """Test sanitize_log_text removes null bytes."""
        assert sanitize_log_text("Text\x00with\x00nulls") == "Textwithnulls"
        assert sanitize_log_text("\x00Start") == "Start"
        assert sanitize_log_text("End\x00") == "End"

    def test_sanitize_log_text_removes_ansi_escape_sequences(self):
        """Test sanitize_log_text removes ANSI escape sequences."""
        # Basic color codes
        assert sanitize_log_text("Normal\x1b[31mRED\x1b[0m") == "NormalRED"
        assert sanitize_log_text("\x1b[32mGREEN\x1b[0m") == "GREEN"
        assert sanitize_log_text("\x1b[1;33mYELLOW BOLD\x1b[0m") == "YELLOW BOLD"

        # With newlines preserved
        assert sanitize_log_text("Line1\x1b[31m\nLine2\x1b[0m") == "Line1\nLine2"

    def test_sanitize_log_text_removes_unicode_bidi_overrides(self):
        """Test sanitize_log_text removes Unicode bidirectional override characters."""
        # U+202A - U+202E
        assert sanitize_log_text("Text\u202aOverride\u202c") == "TextOverride"
        assert sanitize_log_text("\u202bLRE\u202c") == "LRE"

        # U+2066 - U+2069
        assert sanitize_log_text("Text\u2066Override\u2069") == "TextOverride"
        assert sanitize_log_text("\u2067RLI\u2069") == "RLI"

        # With newlines preserved
        assert sanitize_log_text("Line1\u202a\nLine2\u202c") == "Line1\nLine2"

    def test_sanitize_log_text_removes_control_characters(self):
        """Test sanitize_log_text removes control characters except safe whitespace."""
        # Bell, backspace, form feed should be removed
        assert sanitize_log_text("Text\x07Bell") == "TextBell"
        assert sanitize_log_text("Text\x08Backspace") == "TextBackspace"
        assert sanitize_log_text("Text\x0cFormFeed") == "TextFormFeed"

        # DEL character (0x7F)
        assert sanitize_log_text("Text\x7fDEL") == "TextDEL"

        # But newlines, CR, tabs should be preserved
        assert sanitize_log_text("Text\nNew\rLine\tTab") == "Text\nNew\rLine\tTab"

    def test_sanitize_log_text_multiline_output(self):
        """Test sanitize_log_text with typical multi-line ClamAV output."""
        clamav_output = """----------- SCAN SUMMARY -----------
Known viruses: 8647632
Engine version: 1.0.0
Scanned directories: 1
Scanned files: 2
Infected files: 1
Data scanned: 0.00 MB
Time: 10.123 sec (0 m 10 s)"""

        result = sanitize_log_text(clamav_output)
        # Should preserve all newlines
        assert result == clamav_output
        assert result.count("\n") == 7

    def test_sanitize_log_text_multiline_with_malicious_content(self):
        """Test sanitize_log_text removes malicious content but preserves structure."""
        malicious = "Line 1\x00\nLine 2\x1b[31mRED\x1b[0m\nLine 3\u202aOverride"
        expected = "Line 1\nLine 2RED\nLine 3Override"
        assert sanitize_log_text(malicious) == expected

    def test_sanitize_log_text_combined_malicious_input(self):
        """Test sanitize_log_text with combined malicious characters."""
        # Combining null bytes, ANSI, bidi overrides (but preserving newlines)
        malicious = "Path\x00\nFile\x1b[31m\u202aEvil\u202c\x1b[0m\nEnd"
        # Should remove: \x00, ANSI codes, bidi overrides; keep: \n
        assert sanitize_log_text(malicious) == "Path\nFileEvil\nEnd"

    def test_sanitize_log_text_very_long_string(self):
        """Test sanitize_log_text handles very long multi-line strings."""
        # 1000 lines of text
        long_text = "\n".join([f"Line {i}" for i in range(1000)])
        result = sanitize_log_text(long_text)
        assert result.count("\n") == 999
        assert "Line 0" in result
        assert "Line 999" in result

        # Long string with malicious content
        long_malicious = ("Clean\x00Text\n") * 1000
        result = sanitize_log_text(long_malicious)
        assert result.count("\n") == 1000
        assert "\x00" not in result

    def test_sanitize_log_text_preserves_unicode_text(self):
        """Test sanitize_log_text preserves legitimate Unicode characters."""
        # Multi-line with Unicode
        unicode_text = "文档\nテスト\nrésumé"
        assert sanitize_log_text(unicode_text) == unicode_text

        # Emoji and symbols
        assert sanitize_log_text("🔒 Line 1\n🔑 Line 2") == "🔒 Line 1\n🔑 Line 2"

    def test_sanitize_log_text_windows_line_endings(self):
        """Test sanitize_log_text preserves Windows-style line endings."""
        windows_text = "Line 1\r\nLine 2\r\nLine 3"
        assert sanitize_log_text(windows_text) == windows_text

    def test_sanitize_log_text_mixed_line_endings(self):
        """Test sanitize_log_text preserves mixed line endings."""
        mixed = "Line 1\nLine 2\r\nLine 3\rLine 4"
        assert sanitize_log_text(mixed) == mixed

    def test_sanitize_log_text_only_whitespace(self):
        """Test sanitize_log_text with only whitespace characters."""
        assert sanitize_log_text("   \n\t\r\n   ") == "   \n\t\r\n   "

    def test_sanitize_log_text_only_control_characters(self):
        """Test sanitize_log_text with only non-whitespace control characters."""
        # Should remove all except newlines/CR/tabs
        assert sanitize_log_text("\x00\x01\x02") == ""
        assert sanitize_log_text("\x00\n\x01") == "\n"

    def test_sanitize_log_text_empty_lines(self):
        """Test sanitize_log_text preserves empty lines."""
        text = "Line 1\n\nLine 3\n\n\nLine 6"
        assert sanitize_log_text(text) == text

    def test_sanitize_log_text_indented_content(self):
        """Test sanitize_log_text preserves indentation."""
        indented = "Main\n\tIndent 1\n\t\tIndent 2\n\tIndent 1"
        assert sanitize_log_text(indented) == indented

    def test_sanitize_log_text_clamav_error_output(self):
        """Test sanitize_log_text with typical error messages."""
        error = "ERROR: Can't access file /path/to/file\nERROR: Permission denied"
        assert sanitize_log_text(error) == error

    def test_sanitize_log_text_starts_with_control_chars(self):
        """Test sanitize_log_text with control characters at start."""
        assert sanitize_log_text("\x00\x01Clean") == "Clean"
        # Newline at start should be preserved
        assert sanitize_log_text("\nClean") == "\nClean"

    def test_sanitize_log_text_ends_with_control_chars(self):
        """Test sanitize_log_text with control characters at end."""
        assert sanitize_log_text("Clean\x00\x01") == "Clean"
        # Newline at end should be preserved
        assert sanitize_log_text("Clean\n") == "Clean\n"

    def test_sanitize_log_text_real_world_scan_output(self):
        """Test sanitize_log_text with realistic ClamAV scan output."""
        scan_output = """/home/user/Downloads/file1.txt: OK
/home/user/Downloads/malware.exe: Win.Trojan.Agent FOUND
/home/user/Downloads/file2.doc: OK

----------- SCAN SUMMARY -----------
Infected files: 1
Time: 5.234 sec"""

        # Should preserve all structure
        result = sanitize_log_text(scan_output)
        assert result == scan_output
        assert "Win.Trojan.Agent FOUND" in result
        assert result.count("\n") == 6


class TestSanitizationEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_sanitize_functions_idempotent(self):
        """Test that sanitizing twice produces the same result (idempotent)."""
        malicious = "Path\x00\nFile\x1b[31m\u202aEvil\u202c"

        # sanitize_log_line
        result1 = sanitize_log_line(malicious)
        result2 = sanitize_log_line(result1)
        assert result1 == result2

        # sanitize_log_text
        result3 = sanitize_log_text(malicious)
        result4 = sanitize_log_text(result3)
        assert result3 == result4

    def test_sanitize_functions_with_only_malicious_chars(self):
        """Test sanitization when input is only malicious characters."""
        only_malicious = "\x00\x01\x1b[31m\u202a\u202c"

        assert sanitize_log_line(only_malicious) == ""
        assert sanitize_log_text(only_malicious) == ""

    def test_sanitize_functions_performance_with_large_input(self):
        """Test sanitization performance doesn't degrade with large input."""
        # 100KB of text
        large_text = "Clean text. " * 8000  # ~96KB

        result_line = sanitize_log_line(large_text)
        assert len(result_line) > 0

        result_text = sanitize_log_text(large_text)
        assert len(result_text) > 0

    def test_sanitize_log_line_vs_log_text_difference(self):
        """Test the key difference between sanitize_log_line and sanitize_log_text."""
        text_with_newlines = "Line 1\nLine 2\nLine 3"

        # sanitize_log_line should replace newlines with spaces
        line_result = sanitize_log_line(text_with_newlines)
        assert line_result == "Line 1 Line 2 Line 3"
        assert "\n" not in line_result

        # sanitize_log_text should preserve newlines
        text_result = sanitize_log_text(text_with_newlines)
        assert text_result == "Line 1\nLine 2\nLine 3"
        assert "\n" in text_result

    def test_all_unicode_bidi_characters_removed(self):
        """Test that all Unicode bidirectional override characters are removed."""
        # U+202A through U+202E
        bidi_old = "\u202a\u202b\u202c\u202d\u202e"
        assert sanitize_log_line("Text" + bidi_old + "End") == "TextEnd"
        assert sanitize_log_text("Text" + bidi_old + "End") == "TextEnd"

        # U+2066 through U+2069
        bidi_new = "\u2066\u2067\u2068\u2069"
        assert sanitize_log_line("Text" + bidi_new + "End") == "TextEnd"
        assert sanitize_log_text("Text" + bidi_new + "End") == "TextEnd"

    def test_ansi_escape_patterns(self):
        """Test various ANSI escape sequence patterns are removed."""
        # CSI sequences with different parameters
        patterns = [
            "\x1b[0m",  # Reset
            "\x1b[31m",  # Red foreground
            "\x1b[1;31m",  # Bold red
            "\x1b[1;31;40m",  # Bold red on black background
            "\x1b[2J",  # Clear screen
            "\x1b[H",  # Move cursor to home
            "\x1b[10;20H",  # Move cursor to row 10, col 20
            "\x1b[?25h",  # Show cursor
        ]

        for pattern in patterns:
            result = sanitize_log_line(f"Before{pattern}After")
            assert result == "BeforeAfter", f"Failed to remove pattern: {repr(pattern)}"

    def test_boundary_ascii_values(self):
        """Test handling of boundary ASCII values."""
        # 0x00 - null (should be removed)
        assert sanitize_log_line("\x00") == ""

        # 0x09 - tab (should be preserved)
        assert sanitize_log_line("\x09") == "\x09"

        # 0x0A - newline (should become space in log_line, preserved in log_text)
        assert sanitize_log_line("\x0a") == " "
        assert sanitize_log_text("\x0a") == "\x0a"

        # 0x0D - carriage return (should become space in log_line, preserved in log_text)
        assert sanitize_log_line("\x0d") == " "
        assert sanitize_log_text("\x0d") == "\x0d"

        # 0x1F - last control character (should be removed)
        assert sanitize_log_line("\x1f") == ""

        # 0x20 - space (should be preserved)
        assert sanitize_log_line("\x20") == "\x20"

        # 0x7E - tilde (should be preserved)
        assert sanitize_log_line("\x7e") == "\x7e"

        # 0x7F - DEL (should be removed)
        assert sanitize_log_line("\x7f") == ""

    def test_real_world_malicious_filename(self):
        """Test with realistic malicious filename examples."""
        # Filename that tries to hide .exe extension
        filename1 = "document.pdf\u202e\u202dexe.evil"
        assert "document.pdfexe.evil" in sanitize_log_line(filename1)

        # Filename with ANSI codes to hide part of it
        filename2 = "safe.txt\x1b[8mmalware.exe\x1b[0m"
        assert "safe.txtmalware.exe" in sanitize_log_line(filename2)

        # Filename with newline injection
        filename3 = "file.txt\nFake log entry: CLEAN"
        assert "\n" not in sanitize_log_line(filename3)
