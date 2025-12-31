# ClamUI Quarantine Module
"""
Quarantine management module for ClamUI providing secure threat isolation.
Handles moving detected threats to quarantine, metadata persistence, and restoration.
"""

from .database import QuarantineDatabase, QuarantineEntry

__all__ = ["QuarantineDatabase", "QuarantineEntry"]
