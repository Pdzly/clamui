# ClamUI UI Components
"""
UI components for the ClamUI application.
Contains GTK4/Adwaita widgets and views.
"""

from .update_view import UpdateView
from .logs_view import LogsView
from .fullscreen_dialog import FullscreenLogDialog
from .components_view import ComponentsView
from .preferences_dialog import PreferencesDialog
from .quarantine_view import QuarantineView

__all__ = [
    "UpdateView",
    "LogsView",
    "FullscreenLogDialog",
    "ComponentsView",
    "PreferencesDialog",
    "QuarantineView",
]
