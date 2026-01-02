# CLAUDE.md - ClamUI AI Assistant Guide

This document provides comprehensive guidance for AI assistants working with the ClamUI codebase.

## Project Overview

ClamUI is a modern Linux desktop application providing a graphical user interface for ClamAV antivirus. Built with **PyGObject**, **GTK4**, and **libadwaita** for native GNOME integration.

**Key Facts:**
- Python 3.10+ required
- GTK4/Adwaita UI framework
- ClamAV integration via subprocess (clamscan, clamdscan, freshclam)
- Supports both native and Flatpak installations
- MIT licensed

## Repository Structure

```
clamui/
├── src/
│   ├── main.py                 # Application entry point
│   ├── app.py                  # Adw.Application class (lifecycle, views, tray)
│   ├── __init__.py
│   ├── cli/
│   │   └── scheduled_scan.py   # CLI for scheduled scans (systemd/cron)
│   ├── core/                   # Business logic modules
│   │   ├── scanner.py          # ClamAV scanning (sync/async)
│   │   ├── daemon_scanner.py   # clamd daemon integration
│   │   ├── scheduler.py        # systemd/cron scheduled scans
│   │   ├── quarantine/         # Threat quarantine system
│   │   │   ├── manager.py      # High-level quarantine operations
│   │   │   ├── database.py     # SQLite metadata storage
│   │   │   └── file_handler.py # Secure file operations
│   │   ├── settings_manager.py # JSON settings persistence
│   │   ├── log_manager.py      # Scan history logging
│   │   ├── notification_manager.py
│   │   ├── battery_manager.py  # Battery status for scheduled scans
│   │   ├── updater.py          # freshclam database updates
│   │   ├── clamav_config.py    # ClamAV configuration parsing
│   │   ├── statistics_calculator.py
│   │   └── utils.py            # Utility functions (Flatpak detection, path validation)
│   ├── profiles/               # Scan profile management
│   │   ├── profile_manager.py  # CRUD operations, validation, import/export
│   │   ├── profile_storage.py  # JSON persistence
│   │   └── models.py           # ScanProfile dataclass
│   └── ui/                     # GTK4/Adwaita UI components
│       ├── window.py           # Main application window
│       ├── scan_view.py        # Scanning interface
│       ├── update_view.py      # Database update view
│       ├── logs_view.py        # Scan history
│       ├── quarantine_view.py  # Quarantine management
│       ├── statistics_view.py  # Statistics dashboard
│       ├── components_view.py  # ClamAV components status
│       ├── preferences_window.py / preferences_dialog.py
│       ├── profile_dialogs.py  # Profile create/edit dialogs
│       ├── tray_manager.py     # System tray subprocess manager
│       ├── tray_indicator.py   # GTK3 tray subprocess
│       └── fullscreen_dialog.py
├── tests/                      # Test suite (mirrors src structure)
│   ├── conftest.py             # Shared fixtures, GTK mocking
│   ├── core/                   # Core module tests
│   ├── ui/                     # UI component tests
│   ├── profiles/               # Profile tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── scripts/
│   └── clamui-scheduled-scan   # Scheduled scan CLI wrapper
├── debian/                     # Debian packaging
├── icons/                      # Application icons
├── .github/workflows/          # CI: test.yml, lint.yml, build-*.yml
├── pyproject.toml              # Project config, dependencies, tool settings
└── install.sh                  # Installation script
```

## Architecture Documentation

For detailed technical documentation on specific architectural patterns:

### System Tray Subprocess Architecture
**Location**: [`docs/architecture/tray-subprocess.md`](docs/architecture/tray-subprocess.md)

ClamUI uses a unique subprocess architecture for system tray integration:
- **Main process** (GTK4): `ClamUIApp` and `TrayManager`
- **Subprocess** (GTK3): `TrayService` running AppIndicator
- **IPC**: JSON messages over stdin/stdout pipes

This split is necessary because GTK3 and GTK4 cannot coexist in the same process. The documentation includes:
- Runtime architecture diagrams showing process boundaries and threading models
- Complete IPC protocol specification (commands, events, message formats)
- Sequence diagrams for startup, status updates, and menu actions
- Component relationships between `app.py`, `tray_manager.py`, `tray_service.py`, and `tray_icons.py`
- Security considerations and troubleshooting guides

**When to reference this:**
- Implementing features that update the system tray (status, progress, icons)
- Debugging IPC communication issues between main app and tray
- Understanding why certain operations require thread-safe callbacks
- Contributing to tray-related code in `src/ui/tray_*.py`

## Development Commands

### Setup
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
    libgirepository-2.0-dev libcairo2-dev pkg-config python3-dev clamav

# Install Python dependencies with uv
uv sync --dev

# Run from source
uv run clamui
```

### Testing
```bash
# Run full test suite with coverage
pytest

# Run specific test file
pytest tests/core/test_scanner.py -v

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run only core tests (faster)
pytest tests/core -v

# Skip e2e tests (CI default)
pytest --ignore=tests/e2e
```

### Linting
```bash
# Check code style
ruff check src/ tests/

# Check formatting
ruff format --check src/ tests/

# Auto-fix issues
ruff check src/ tests/ --fix
ruff format src/ tests/
```

## Code Patterns & Conventions

### Async Operations (GTK Thread Safety)
All long-running operations use background threads with `GLib.idle_add()` for UI updates:

```python
def scan_async(self, path: str, callback: Callable[[ScanResult], None]) -> None:
    def scan_thread():
        result = self.scan_sync(path)
        GLib.idle_add(callback, result)  # Schedule callback on main thread

    thread = threading.Thread(target=scan_thread, daemon=True)
    thread.start()
```

### Dataclasses for Results
Use `@dataclass` for structured data with properties for computed values:

```python
@dataclass
class ScanResult:
    status: ScanStatus
    infected_files: list[str]
    infected_count: int

    @property
    def is_clean(self) -> bool:
        return self.status == ScanStatus.CLEAN
```

### Error Handling Pattern
Return tuples of `(success: bool, error_or_value: Optional[str])`:

```python
def check_clamav_installed() -> Tuple[bool, Optional[str]]:
    # Returns (True, version_string) or (False, error_message)
```

### Flatpak Support
Commands that execute on the host system must be wrapped:

```python
from .utils import wrap_host_command, is_flatpak

cmd = wrap_host_command(["clamscan", "--version"])
# In Flatpak: ['flatpak-spawn', '--host', 'clamscan', '--version']
# Native: ['clamscan', '--version']
```

### GTK4 Widget Patterns
- Inherit from appropriate base class (`Gtk.Box`, `Adw.PreferencesWindow`, etc.)
- Use `gi.require_version()` before importing
- Set CSS classes via `add_css_class()`

### Thread Locks
Use `threading.Lock()` for shared state in managers:

```python
class QuarantineManager:
    def __init__(self):
        self._lock = threading.Lock()

    def quarantine_file(self, path: str) -> QuarantineResult:
        with self._lock:
            # Thread-safe operations
```

## Testing Guidelines

### GTK Mocking (conftest.py)
Tests use centralized GTK mocking from `tests/conftest.py`:

```python
def test_something(mock_gi_modules):
    gtk = mock_gi_modules['gtk']
    from src.ui.some_view import SomeView
    # SomeView can be imported with mocked GTK
```

### Fixtures
- `tmp_path`: Pytest's temporary directory (use for file I/O tests)
- `eicar_file`: EICAR test file for antivirus testing
- `eicar_directory`: Directory with EICAR + clean files
- `mock_scanner`: Pre-configured Scanner mock

### Test File Naming
- Tests mirror source structure: `src/core/scanner.py` → `tests/core/test_scanner.py`
- Prefix test methods with `test_`
- Use descriptive docstrings

### Coverage Requirements
- **Overall minimum**: 50% (fail_under in pyproject.toml)
- **Target coverage**: 80%+ for src/core, 70%+ for src/ui

## Key Modules Reference

### Scanner (`src/core/scanner.py`)
- Supports three backends: `"auto"`, `"daemon"`, `"clamscan"`
- Parses ClamAV exit codes: 0=clean, 1=infected, 2=error
- Classifies threats by category and severity
- Saves scan logs via `LogManager`

### Scheduler (`src/core/scheduler.py`)
- Detects systemd vs cron availability
- Creates systemd user timers or crontab entries
- Validates paths for injection attacks
- Uses `shlex.quote()` for safe command building

### QuarantineManager (`src/core/quarantine/manager.py`)
- Orchestrates `QuarantineDatabase` + `SecureFileHandler`
- Verifies file integrity via SHA-256 hashing
- Supports async operations with callbacks

### ProfileManager (`src/profiles/profile_manager.py`)
- Creates default profiles on first run (Quick Scan, Full Scan, Home Folder)
- Validates names, paths, and exclusion patterns
- Supports import/export with duplicate name handling

### ClamUIApp (`src/app.py`)
- Main `Adw.Application` class
- Manages view lifecycle and navigation
- Handles tray integration via subprocess (GTK3/GTK4 cannot coexist)
- Implements start-minimized functionality

## Configuration & Settings

### Settings Location
- XDG compliant: `~/.config/clamui/settings.json`
- Profiles: `~/.config/clamui/profiles.json`
- Quarantine DB: `~/.local/share/clamui/quarantine.db`
- Quarantine files: `~/.local/share/clamui/quarantine/`
- Logs: `~/.local/share/clamui/logs/`

### Key Settings
```json
{
  "scan_backend": "auto",       // "auto", "daemon", "clamscan"
  "start_minimized": false,
  "minimize_to_tray": false,
  "show_notifications": true,
  "exclusion_patterns": []      // Global exclusions
}
```

## CI/CD Workflows

### test.yml
- Runs on Python 3.10, 3.11, 3.12
- Uses xvfb for headless GTK testing
- Uploads coverage report on Python 3.12

### lint.yml
- Runs Ruff linting and format checking
- Configured rules in pyproject.toml

## Security Considerations

1. **Path Validation**: Always validate paths with `validate_path()` before operations
2. **Command Injection**: Use `shlex.quote()` for user-provided paths in shell commands
3. **Scheduler Security**: `_validate_target_paths()` checks for newlines/null bytes
4. **Quarantine Integrity**: SHA-256 hash verification before restore
5. **Secrets**: Never commit `.env` files or credentials

## Common Tasks

### Adding a New View
1. Create `src/ui/new_view.py` inheriting from `Gtk.Box` or similar
2. Add view instance in `app.py:do_activate()`
3. Add action in `app.py:_setup_actions()`
4. Add navigation button in `window.py:_create_navigation_buttons()`
5. Write tests in `tests/ui/test_new_view.py`

### Adding a Core Feature
1. Create module in `src/core/`
2. Use dataclasses for results, enums for statuses
3. Implement both sync and async methods
4. Add thread locks for shared state
5. Write comprehensive tests

### Modifying Scan Profiles
1. Default profiles defined in `ProfileManager.DEFAULT_PROFILES`
2. Validation in `_validate_profile()`, `_validate_targets()`, `_validate_exclusions()`
3. Storage in `ProfileStorage` using atomic file writes

## Debugging Tips

1. **GTK Issues**: Check `GLib.idle_add()` usage for thread safety
2. **Flatpak**: Test with `is_flatpak()` detection
3. **ClamAV Not Found**: Check `check_clamav_installed()` and PATH
4. **Daemon Issues**: Verify clamd socket with `get_clamd_socket_path()`
5. **Test Failures**: Ensure `mock_gi_modules` fixture is used for UI tests

## Entry Points (pyproject.toml)

```toml
[project.scripts]
clamui = "src.main:main"
clamui-scheduled-scan = "src.cli.scheduled_scan:main"
```
