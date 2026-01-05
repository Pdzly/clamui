# ClamUI Preferences Package
"""
Preferences package for ClamUI providing preference pages and window.

This package contains modular preference pages organized by domain:
- DatabasePage: Database update settings (freshclam.conf)
- ScannerPage: Scanner settings (clamd.conf + backend selection)
- OnAccessPage: On-Access scanning settings (clamonacc)
- ScheduledPage: Scheduled scans configuration
- ExclusionsPage: Scan exclusion patterns (preset + custom)
- SavePage: Save & Apply with config persistence
- PreferencesWindow: Main window orchestrating all pages
"""

from .exclusions_page import PRESET_EXCLUSIONS
from .window import PreferencesWindow

__all__ = ["PreferencesWindow", "PRESET_EXCLUSIONS"]
