# ClamUI Tray Manager
"""
Manager for the system tray indicator subprocess.

This module spawns and communicates with the tray_service subprocess,
which runs with GTK3 to avoid GTK4 version conflicts. Communication
is done via JSON messages over stdin/stdout.
"""

import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, List, Optional

from gi.repository import GLib

logger = logging.getLogger(__name__)


class TrayManager:
    """
    Manager for the system tray indicator subprocess.

    Spawns tray_service.py as a subprocess and communicates with it
    via JSON messages. This avoids GTK3/GTK4 version conflicts by
    isolating GTK3 in a separate process.
    """

    def __init__(self) -> None:
        """Initialize the TrayManager."""
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self._ready = False
        self._current_status = "protected"

        # Callbacks for menu actions
        self._on_quick_scan: Optional[Callable[[], None]] = None
        self._on_full_scan: Optional[Callable[[], None]] = None
        self._on_update: Optional[Callable[[], None]] = None
        self._on_quit: Optional[Callable[[], None]] = None
        self._on_window_toggle: Optional[Callable[[], None]] = None
        self._on_profile_select: Optional[Callable[[str], None]] = None

        # Profile state
        self._current_profile_id: Optional[str] = None

    def start(self) -> bool:
        """
        Start the tray service subprocess.

        Returns:
            True if subprocess started successfully, False otherwise.
        """
        if self._process is not None:
            logger.warning("Tray service already running")
            return True

        try:
            # Find the tray_service module path
            service_path = self._get_service_path()
            if not service_path:
                logger.error("Could not find tray_service.py")
                return False

            # Build command
            python_executable = sys.executable
            cmd = [python_executable, str(service_path)]

            # Set up environment
            env = os.environ.copy()
            if logger.isEnabledFor(logging.DEBUG):
                env["CLAMUI_DEBUG"] = "1"

            # Start subprocess
            logger.info(f"Starting tray service: {' '.join(cmd)}")
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                env=env,
            )

            self._running = True

            # Start reader thread for stdout
            self._reader_thread = threading.Thread(
                target=self._read_stdout,
                daemon=True,
                name="TrayManagerReader"
            )
            self._reader_thread.start()

            # Start stderr reader for logging
            stderr_thread = threading.Thread(
                target=self._read_stderr,
                daemon=True,
                name="TrayManagerStderr"
            )
            stderr_thread.start()

            # Wait a moment for ready signal
            # The actual ready check happens in _read_stdout
            logger.info("Tray service subprocess started")
            return True

        except Exception as e:
            logger.error(f"Failed to start tray service: {e}")
            self._process = None
            return False

    def _get_service_path(self) -> Optional[Path]:
        """Get the path to tray_service.py."""
        # Try relative to this file
        this_dir = Path(__file__).parent
        service_path = this_dir / "tray_service.py"
        if service_path.exists():
            return service_path

        # Try as module path
        # This handles the case when installed as a package
        import src.ui.tray_service as tray_service_module
        module_path = Path(tray_service_module.__file__)
        if module_path.exists():
            return module_path

        return None

    def _read_stdout(self) -> None:
        """Read messages from the subprocess stdout."""
        try:
            if self._process is None or self._process.stdout is None:
                return

            for line in self._process.stdout:
                if not self._running:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                    self._handle_message(message)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from tray service: {e}")

        except Exception as e:
            logger.error(f"Error reading tray service stdout: {e}")
        finally:
            logger.debug("Tray service stdout reader ended")

    def _read_stderr(self) -> None:
        """Read and log stderr from the subprocess."""
        try:
            if self._process is None or self._process.stderr is None:
                return

            for line in self._process.stderr:
                if not self._running:
                    break
                line = line.strip()
                if line:
                    logger.debug(f"[TrayService] {line}")

        except Exception as e:
            logger.error(f"Error reading tray service stderr: {e}")

    def _handle_message(self, message: dict) -> None:
        """Handle a message from the tray service."""
        event = message.get("event")

        if event == "ready":
            self._ready = True
            logger.info("Tray service is ready")

        elif event == "pong":
            logger.debug("Received pong from tray service")

        elif event == "error":
            error_msg = message.get("message", "Unknown error")
            logger.error(f"Tray service error: {error_msg}")

        elif event == "menu_action":
            action = message.get("action")
            self._handle_menu_action(action, message)

        else:
            logger.warning(f"Unknown event from tray service: {event}")

    def _handle_menu_action(self, action: str, message: dict) -> None:
        """Handle a menu action from the tray service."""
        logger.debug(f"Menu action: {action}")

        # Use GLib.idle_add to ensure callbacks run on GTK main thread
        if action == "quick_scan" and self._on_quick_scan:
            GLib.idle_add(self._on_quick_scan)
        elif action == "full_scan" and self._on_full_scan:
            GLib.idle_add(self._on_full_scan)
        elif action == "update" and self._on_update:
            GLib.idle_add(self._on_update)
        elif action == "quit" and self._on_quit:
            GLib.idle_add(self._on_quit)
        elif action == "toggle_window" and self._on_window_toggle:
            GLib.idle_add(self._on_window_toggle)
        elif action == "select_profile" and self._on_profile_select:
            profile_id = message.get("profile_id")
            if profile_id:
                self._current_profile_id = profile_id
                GLib.idle_add(self._on_profile_select, profile_id)
            else:
                logger.warning("select_profile action missing profile_id")
        else:
            logger.warning(f"No handler for action: {action}")

    def _send_command(self, command: dict) -> bool:
        """Send a command to the tray service."""
        if self._process is None or self._process.stdin is None:
            return False

        try:
            message = json.dumps(command) + "\n"
            self._process.stdin.write(message)
            self._process.stdin.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to send command to tray service: {e}")
            return False

    def set_action_callbacks(
        self,
        on_quick_scan: Optional[Callable[[], None]] = None,
        on_full_scan: Optional[Callable[[], None]] = None,
        on_update: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Set callbacks for menu actions.

        Args:
            on_quick_scan: Callback for Quick Scan action
            on_full_scan: Callback for Full Scan action
            on_update: Callback for Update Definitions action
            on_quit: Callback for Quit action
        """
        self._on_quick_scan = on_quick_scan
        self._on_full_scan = on_full_scan
        self._on_update = on_update
        self._on_quit = on_quit
        logger.debug("Action callbacks configured")

    def set_window_toggle_callback(
        self,
        on_toggle: Callable[[], None],
        get_visible: Optional[Callable[[], bool]] = None
    ) -> None:
        """
        Set the callback for window show/hide toggle.

        Args:
            on_toggle: Callback to invoke when toggling window visibility
            get_visible: Callback to query current window visibility (optional)
        """
        self._on_window_toggle = on_toggle
        logger.debug("Window toggle callback configured")

    def set_profile_select_callback(
        self,
        on_select: Callable[[str], None]
    ) -> None:
        """
        Set the callback for profile selection from tray menu.

        Args:
            on_select: Callback to invoke when a profile is selected.
                       Receives the profile_id as argument.
        """
        self._on_profile_select = on_select
        logger.debug("Profile select callback configured")

    def update_status(self, status: str) -> None:
        """
        Update the tray icon based on protection status.

        Args:
            status: One of 'protected', 'warning', 'scanning', 'threat'
        """
        self._current_status = status
        self._send_command({"action": "update_status", "status": status})

    def update_scan_progress(self, percentage: int) -> None:
        """
        Show scan progress percentage in the tray.

        Args:
            percentage: Progress percentage (0-100). Use 0 to clear.
        """
        self._send_command({"action": "update_progress", "percentage": percentage})

    def update_window_menu_label(self, visible: bool = True) -> None:
        """
        Update the Show/Hide Window menu item label.

        Args:
            visible: Whether the window is currently visible
        """
        self._send_command({"action": "update_window_visible", "visible": visible})

    def update_profiles(
        self,
        profiles: List[dict],
        current_profile_id: Optional[str] = None
    ) -> None:
        """
        Update the profiles list in the tray menu.

        Args:
            profiles: List of profile dictionaries with 'id', 'name', 'is_default' keys
            current_profile_id: ID of the currently selected profile (optional)
        """
        if current_profile_id is not None:
            self._current_profile_id = current_profile_id
        self._send_command({
            "action": "update_profiles",
            "profiles": profiles,
            "current_profile_id": self._current_profile_id
        })
        logger.debug(f"Updated tray profiles: {len(profiles)} profiles")

    def stop(self) -> None:
        """Stop the tray service subprocess."""
        self._running = False

        if self._process is not None:
            try:
                # Send quit command
                self._send_command({"action": "quit"})

                # Wait for graceful shutdown
                try:
                    self._process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    logger.warning("Tray service didn't stop gracefully, terminating")
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        logger.warning("Tray service didn't terminate, killing")
                        self._process.kill()

            except Exception as e:
                logger.error(f"Error stopping tray service: {e}")
            finally:
                self._process = None

        self._ready = False
        logger.info("Tray manager stopped")

    def cleanup(self) -> None:
        """
        Clean up resources.

        Alias for stop() for API compatibility.
        """
        self.stop()

        # Clear callbacks
        self._on_quick_scan = None
        self._on_full_scan = None
        self._on_update = None
        self._on_quit = None
        self._on_window_toggle = None
        self._on_profile_select = None

    @property
    def is_active(self) -> bool:
        """Check if the tray service is running and ready."""
        return self._running and self._ready and self._process is not None

    @property
    def is_library_available(self) -> bool:
        """
        Check if the tray indicator is available.

        Always returns True for TrayManager since availability
        is determined by subprocess startup success.
        """
        return self._running and self._process is not None

    @property
    def current_status(self) -> str:
        """Get the current protection status."""
        return self._current_status


def is_available() -> bool:
    """
    Check if the tray service can be started.

    Returns:
        True (we always try subprocess approach)
    """
    return True


def get_unavailable_reason() -> Optional[str]:
    """
    Get the reason why tray is unavailable.

    Returns:
        None (subprocess approach handles availability internally)
    """
    return None
