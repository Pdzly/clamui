# ClamUI Core Module
"""
Core functionality for ClamUI.
Contains ClamAV integration, scanning logic, and utilities.
"""

from .updater import FreshclamUpdater, UpdateResult, UpdateStatus

__all__ = ["FreshclamUpdater", "UpdateResult", "UpdateStatus"]
