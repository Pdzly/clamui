"""Tests for None handling in clamav_config validation functions."""

from src.core.clamav_config import validate_config, validate_config_file


class TestValidateConfigNoneHandling:
    """Test that validate_config handles None gracefully."""

    def test_validate_config_with_none(self):
        """validate_config should handle None gracefully."""
        is_valid, errors = validate_config(None)

        assert not is_valid
        assert len(errors) == 1
        assert "Configuration is not loaded" in errors[0]

    def test_validate_config_with_valid_config(self, tmp_path):
        """validate_config should work with valid config."""
        from src.core.clamav_config import parse_config

        config_file = tmp_path / "test.conf"
        config_file.write_text("DatabaseMirror database.clamav.net\n")
        config, error = parse_config(str(config_file))

        assert error is None
        assert config is not None

        is_valid, errors = validate_config(config)
        # Just ensure no crash
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_validate_config_file_with_nonexistent_file(self, tmp_path):
        """validate_config_file should handle missing files gracefully."""
        nonexistent = tmp_path / "nonexistent.conf"

        is_valid, errors = validate_config_file(str(nonexistent))

        assert not is_valid
        assert len(errors) >= 1
        # Should get an error message, not a crash
        assert any("not found" in err.lower() or "exist" in err.lower() for err in errors)

    def test_validate_config_file_with_empty_file(self, tmp_path):
        """validate_config_file should handle empty files gracefully."""
        empty_file = tmp_path / "empty.conf"
        empty_file.write_text("")

        is_valid, errors = validate_config_file(str(empty_file))

        # Empty config might be valid or invalid, but shouldn't crash
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
