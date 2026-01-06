# ClamUI VirusTotal Client Tests
"""Unit tests for the VirusTotal API client."""

import hashlib
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

from src.core.virustotal import (
    VT_MAX_FILE_SIZE,
    VT_RATE_LIMIT_REQUESTS,
    VTDetection,
    VTScanResult,
    VTScanStatus,
    VirusTotalClient,
)


class TestVTScanResult:
    """Tests for VTScanResult dataclass."""

    def test_is_clean_for_clean_status(self):
        """Test is_clean property for clean status."""
        result = VTScanResult(status=VTScanStatus.CLEAN, file_path="/test")
        assert result.is_clean is True

    def test_is_clean_for_not_found(self):
        """Test is_clean property for not found status."""
        result = VTScanResult(status=VTScanStatus.NOT_FOUND, file_path="/test")
        assert result.is_clean is True

    def test_is_clean_for_detected(self):
        """Test is_clean property for detected status."""
        result = VTScanResult(status=VTScanStatus.DETECTED, file_path="/test")
        assert result.is_clean is False

    def test_has_threats_for_detected(self):
        """Test has_threats property for detected status."""
        result = VTScanResult(status=VTScanStatus.DETECTED, file_path="/test")
        assert result.has_threats is True

    def test_has_threats_for_clean(self):
        """Test has_threats property for clean status."""
        result = VTScanResult(status=VTScanStatus.CLEAN, file_path="/test")
        assert result.has_threats is False

    def test_is_error_for_error_status(self):
        """Test is_error property for various error statuses."""
        for status in [VTScanStatus.ERROR, VTScanStatus.RATE_LIMITED, VTScanStatus.FILE_TOO_LARGE]:
            result = VTScanResult(status=status, file_path="/test")
            assert result.is_error is True

    def test_is_error_for_non_error_status(self):
        """Test is_error property for non-error statuses."""
        for status in [VTScanStatus.CLEAN, VTScanStatus.DETECTED, VTScanStatus.NOT_FOUND]:
            result = VTScanResult(status=status, file_path="/test")
            assert result.is_error is False


class TestVirusTotalClientInit:
    """Tests for VirusTotalClient initialization."""

    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        client = VirusTotalClient(api_key="test_key")
        assert client._api_key == "test_key"

    def test_init_without_api_key(self):
        """Test client initialization without API key."""
        client = VirusTotalClient()
        assert client._api_key is None

    def test_set_api_key(self):
        """Test setting API key after initialization."""
        client = VirusTotalClient()
        client.set_api_key("new_key")
        assert client._api_key == "new_key"


class TestCalculateSha256:
    """Tests for SHA256 calculation."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file with known content."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_calculate_sha256(self, temp_file):
        """Test SHA256 calculation for a file."""
        expected_hash = hashlib.sha256(b"test content").hexdigest().lower()
        result = VirusTotalClient.calculate_sha256(temp_file)
        assert result == expected_hash

    def test_calculate_sha256_file_not_found(self):
        """Test SHA256 calculation for non-existent file."""
        with pytest.raises(FileNotFoundError):
            VirusTotalClient.calculate_sha256("/nonexistent/file")


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_check_rate_limit_allows_initial_requests(self):
        """Test that initial requests are allowed."""
        client = VirusTotalClient(api_key="test")
        for _ in range(VT_RATE_LIMIT_REQUESTS):
            assert client._check_rate_limit() is True

    def test_check_rate_limit_blocks_excess_requests(self):
        """Test that excess requests are blocked."""
        client = VirusTotalClient(api_key="test")
        # Fill up the rate limit
        for _ in range(VT_RATE_LIMIT_REQUESTS):
            client._check_rate_limit()

        # Next request should be blocked
        assert client._check_rate_limit() is False


class TestScanFileSyncValidation:
    """Tests for scan_file_sync input validation."""

    @pytest.fixture
    def client(self):
        """Create a client with API key."""
        return VirusTotalClient(api_key="test_api_key_" + "a" * 50)

    def test_scan_without_api_key(self):
        """Test that scanning without API key returns error."""
        client = VirusTotalClient()
        result = client.scan_file_sync("/some/file")
        assert result.status == VTScanStatus.ERROR
        assert "API key" in result.error_message

    def test_scan_nonexistent_file(self, client):
        """Test scanning a non-existent file."""
        result = client.scan_file_sync("/nonexistent/file/path")
        assert result.status == VTScanStatus.ERROR
        assert "not found" in result.error_message.lower()

    def test_scan_directory(self, client, tmp_path):
        """Test that scanning a directory returns error."""
        result = client.scan_file_sync(str(tmp_path))
        assert result.status == VTScanStatus.ERROR
        assert "not a file" in result.error_message.lower()

    def test_scan_empty_file(self, client, tmp_path):
        """Test that scanning an empty file returns error."""
        empty_file = tmp_path / "empty.txt"
        empty_file.touch()

        result = client.scan_file_sync(str(empty_file))
        assert result.status == VTScanStatus.ERROR
        assert "empty" in result.error_message.lower()

    def test_scan_file_too_large(self, client, tmp_path):
        """Test that files exceeding size limit return error."""
        # Mock os.path.getsize to return a large size
        large_file = tmp_path / "large.bin"
        large_file.write_bytes(b"x")

        with mock.patch("os.path.getsize", return_value=VT_MAX_FILE_SIZE + 1):
            result = client.scan_file_sync(str(large_file))

        assert result.status == VTScanStatus.FILE_TOO_LARGE


class TestCheckFileHash:
    """Tests for hash checking functionality."""

    @pytest.fixture
    def client(self):
        """Create a client with API key."""
        return VirusTotalClient(api_key="test_api_key_" + "a" * 50)

    def test_check_hash_clean_file(self, client):
        """Test checking a clean file hash."""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 0,
                        "suspicious": 0,
                        "undetected": 70,
                        "harmless": 0,
                    },
                    "last_analysis_results": {},
                    "last_analysis_date": 1704067200,
                }
            }
        }

        with mock.patch.object(client, "_make_request", return_value=(mock_response, None)):
            # Bypass rate limiting
            client._request_times = []

            result = client.check_file_hash("a" * 64)

        assert result.status == VTScanStatus.CLEAN
        assert result.total_engines == 70

    def test_check_hash_detected_file(self, client):
        """Test checking a detected file hash."""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 5,
                        "suspicious": 2,
                        "undetected": 63,
                        "harmless": 0,
                    },
                    "last_analysis_results": {
                        "EngineA": {"category": "malicious", "result": "Trojan.Gen"},
                        "EngineB": {"category": "suspicious", "result": "PUP.Generic"},
                    },
                    "last_analysis_date": 1704067200,
                }
            }
        }

        with mock.patch.object(client, "_make_request", return_value=(mock_response, None)):
            client._request_times = []

            result = client.check_file_hash("b" * 64)

        assert result.status == VTScanStatus.DETECTED
        assert result.detections == 7
        assert len(result.detection_details) == 2

    def test_check_hash_not_found(self, client):
        """Test checking an unknown file hash."""
        mock_response = mock.Mock()
        mock_response.status_code = 404

        with mock.patch.object(client, "_make_request", return_value=(mock_response, None)):
            client._request_times = []

            result = client.check_file_hash("c" * 64)

        assert result.status == VTScanStatus.NOT_FOUND

    def test_check_hash_rate_limited(self, client):
        """Test handling rate limit response."""
        mock_response = mock.Mock()
        mock_response.status_code = 429

        with mock.patch.object(
            client, "_make_request", return_value=(mock_response, "API rate limit exceeded")
        ):
            client._request_times = []

            result = client.check_file_hash("d" * 64)

        assert result.status == VTScanStatus.RATE_LIMITED


class TestParseFileReport:
    """Tests for parsing VirusTotal API responses."""

    @pytest.fixture
    def client(self):
        """Create a client instance."""
        return VirusTotalClient(api_key="test")

    def test_parse_clean_report(self, client):
        """Test parsing a clean file report."""
        data = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 0,
                        "suspicious": 0,
                        "undetected": 72,
                        "harmless": 0,
                    },
                    "last_analysis_results": {},
                    "last_analysis_date": 1704067200,
                }
            }
        }

        result = client._parse_file_report(data, "test_hash")

        assert result.status == VTScanStatus.CLEAN
        assert result.detections == 0
        assert result.total_engines == 72
        assert result.permalink == "https://www.virustotal.com/gui/file/test_hash"

    def test_parse_detected_report(self, client):
        """Test parsing a report with detections."""
        data = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 10,
                        "suspicious": 5,
                        "undetected": 55,
                        "harmless": 0,
                    },
                    "last_analysis_results": {
                        "Avast": {"category": "malicious", "result": "Win32:Malware-gen"},
                        "Kaspersky": {"category": "malicious", "result": "Trojan.Win32.Generic"},
                        "Clean": {"category": "undetected", "result": None},
                    },
                }
            }
        }

        result = client._parse_file_report(data, "test_hash")

        assert result.status == VTScanStatus.DETECTED
        assert result.detections == 15
        assert len(result.detection_details) == 2  # Only malicious/suspicious

    def test_parse_malformed_report(self, client):
        """Test parsing a malformed report handles missing data gracefully."""
        data = {"invalid": "data"}

        result = client._parse_file_report(data, "test_hash")

        # The function handles missing keys gracefully with defaults
        # It will return CLEAN since there are no detections
        assert result.status == VTScanStatus.CLEAN
        assert result.detections == 0


class TestVTDetection:
    """Tests for VTDetection dataclass."""

    def test_detection_creation(self):
        """Test creating a VTDetection instance."""
        detection = VTDetection(
            engine_name="TestEngine", category="malicious", result="Trojan.Generic"
        )

        assert detection.engine_name == "TestEngine"
        assert detection.category == "malicious"
        assert detection.result == "Trojan.Generic"

    def test_detection_with_none_result(self):
        """Test creating a VTDetection with None result."""
        detection = VTDetection(engine_name="TestEngine", category="undetected", result=None)

        assert detection.result is None


class TestCancel:
    """Tests for scan cancellation."""

    def test_cancel_sets_flag(self):
        """Test that cancel sets the cancelled flag."""
        client = VirusTotalClient(api_key="test")
        assert client._cancelled is False

        client.cancel()

        assert client._cancelled is True

    def test_scan_file_sync_resets_cancel_flag(self):
        """Test that scan_file_sync resets the cancel flag."""
        client = VirusTotalClient()  # No API key to trigger early return
        client._cancelled = True

        client.scan_file_sync("/test")

        assert client._cancelled is False


class TestClose:
    """Tests for client cleanup."""

    def test_close_releases_session(self):
        """Test that close releases the session."""
        client = VirusTotalClient(api_key="test")
        # Force session creation
        session = client._get_session()
        assert client._session is not None

        client.close()

        assert client._session is None
