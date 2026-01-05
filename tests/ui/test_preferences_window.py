# ClamUI PreferencesWindow Tests (Backward Compatibility)
"""
Backward compatibility tests for PreferencesWindow.

IMPORTANT: This file provides basic smoke tests for backward compatibility.
For comprehensive test coverage of the preferences window and all its components,
see the modular test suite in tests/ui/preferences/:

- test_base.py - PreferencesPageMixin utility methods
- test_window.py - PreferencesWindow integration (33 tests)
- test_database_page.py - Database Updates page (31 tests)
- test_scanner_page.py - Scanner Settings page (56 tests)
- test_onaccess_page.py - On-Access Scanning page (43 tests)
- test_scheduled_page.py - Scheduled Scans page (62 tests)
- test_exclusions_page.py - Exclusions page (47 tests)
- test_save_page.py - Save & Apply page (68 tests)

Total: 361+ comprehensive tests covering all preference functionality.
"""

import sys
from unittest import mock

import pytest


def _clear_src_modules():
    """Clear all cached src.* modules to prevent test pollution."""
    modules_to_remove = [mod for mod in sys.modules if mod.startswith("src.")]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestPreferencesWindowBackwardCompatibility:
    """Backward compatibility smoke tests for PreferencesWindow."""

    def test_import_preferences_window_from_package(self, mock_gi_modules):
        """Test that PreferencesWindow can be imported from new package location."""
        with mock.patch.dict(
            sys.modules,
            {
                "src.core.clamav_config": mock.MagicMock(),
                "src.core.scheduler": mock.MagicMock(),
                "src.core.scanner": mock.MagicMock(),
            },
        ):
            from src.ui.preferences import PreferencesWindow

            assert PreferencesWindow is not None
            # Clean up to prevent test pollution
            _clear_src_modules()

    def test_import_preset_exclusions_from_package(self, mock_gi_modules):
        """Test that PRESET_EXCLUSIONS can be imported from new package location."""
        with mock.patch.dict(
            sys.modules,
            {
                "src.core.clamav_config": mock.MagicMock(),
                "src.core.scheduler": mock.MagicMock(),
                "src.core.scanner": mock.MagicMock(),
            },
        ):
            from src.ui.preferences import PRESET_EXCLUSIONS

            assert PRESET_EXCLUSIONS is not None
            assert isinstance(PRESET_EXCLUSIONS, list)
            assert len(PRESET_EXCLUSIONS) == 6
            # Clean up to prevent test pollution
            _clear_src_modules()

    def test_preset_exclusions_structure(self, mock_gi_modules):
        """Test that PRESET_EXCLUSIONS maintains expected structure."""
        with mock.patch.dict(
            sys.modules,
            {
                "src.core.clamav_config": mock.MagicMock(),
                "src.core.scheduler": mock.MagicMock(),
                "src.core.scanner": mock.MagicMock(),
            },
        ):
            from src.ui.preferences import PRESET_EXCLUSIONS

            # Verify structure of preset exclusions
            for exclusion in PRESET_EXCLUSIONS:
                assert "pattern" in exclusion
                assert "type" in exclusion
                assert "enabled" in exclusion
                assert "description" in exclusion

            # Verify common patterns exist
            patterns = [e["pattern"] for e in PRESET_EXCLUSIONS]
            assert "node_modules" in patterns
            assert ".git" in patterns
            assert "__pycache__" in patterns
            assert ".venv" in patterns
            assert "build" in patterns
            assert "dist" in patterns
            # Clean up to prevent test pollution
            _clear_src_modules()

    def test_package_all_exports(self, mock_gi_modules):
        """Test that package __all__ includes expected exports."""
        with mock.patch.dict(
            sys.modules,
            {
                "src.core.clamav_config": mock.MagicMock(),
                "src.core.scheduler": mock.MagicMock(),
                "src.core.scanner": mock.MagicMock(),
            },
        ):
            import src.ui.preferences as preferences_pkg

            assert hasattr(preferences_pkg, "__all__")
            assert "PreferencesWindow" in preferences_pkg.__all__
            assert "PRESET_EXCLUSIONS" in preferences_pkg.__all__
            # Clean up to prevent test pollution
            _clear_src_modules()
