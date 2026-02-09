# ClamUI Development Guide

>New to ClamUI? Start with the **[Getting Started Guide](GETTING_STARTED.md)** to learn about installation and basic usage before diving into development.

This document provides instructions for setting up a development environment, running tests, and contributing to ClamUI.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Running from Source](#running-from-source)
3. [Testing](#testing)
4. [Code Quality](#code-quality)
5. [Contributing](#contributing)
6. [Architecture Overview](#architecture-overview)

---

## Development Environment Setup

### Prerequisites

ClamUI requires system packages for GTK4/PyGObject bindings before installing Python dependencies.

#### Ubuntu/Debian

```bash
# GTK4 and Adwaita runtime libraries
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 libadwaita-1-dev

# Build dependencies (required for pip install)
sudo apt install libgirepository-2.0-dev libcairo2-dev pkg-config python3-dev
# On Ubuntu < 24.04, use: libgirepository1.0-dev instead of libgirepository-2.0-dev

# ClamAV antivirus (for testing scan functionality)
sudo apt install clamav

# System tray support (optional)
sudo apt install gir1.2-ayatanaappindicator3-0.1
```

#### Fedora

```bash
sudo dnf install python3-gobject python3-gobject-devel gtk4 libadwaita \
    gobject-introspection-devel cairo-gobject-devel clamav libayatana-appindicator-gtk3
```

#### Arch Linux

```bash
sudo pacman -S python-gobject gtk4 libadwaita clamav libayatana-appindicator
```

### Clone the Repository

```bash
git clone https://github.com/linx-systems/clamui.git
cd clamui
```

### Install Python Dependencies

ClamUI uses [uv](https://github.com/astral-sh/uv) for dependency management (recommended):

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (including dev dependencies)
uv sync --dev
```

Alternatively, use pip:

```bash
pip install -e ".[dev]"
```

---

## Running from Source

### With uv (Recommended)

```bash
uv run clamui
```

### With pip installation

```bash
clamui
```

### With file arguments

```bash
# Open with files/folders pre-selected for scanning
uv run clamui /path/to/file1 /path/to/folder
```

### Scheduled Scan CLI

ClamUI includes a CLI tool for scheduled scans (used by systemd/cron):

```bash
uv run clamui-scheduled-scan --help
```

---

## Testing

ClamUI includes a comprehensive test suite with pytest. The project enforces a minimum of **50% code coverage** with a
target of **80%+** for comprehensive coverage.

### Test Dependencies

Test dependencies are included in the `[dev]` optional dependencies:

```bash
# With uv
uv sync --dev

# With pip
pip install -e ".[dev]"
```

### Running Tests

| Command                             | Description                 |
|-------------------------------------|-----------------------------|
| `pytest`                            | Run all tests               |
| `pytest -v`                         | Run with verbose output     |
| `pytest tests/core/`                | Run specific test directory |
| `pytest tests/core/test_scanner.py` | Run specific test file      |
| `pytest -k "test_scanner"`          | Run tests matching pattern  |

### Running Tests with Coverage

```bash
# Terminal coverage report
pytest --cov=src --cov-report=term-missing

# HTML coverage report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in your browser

# Both reports
pytest --cov=src --cov-report=term-missing --cov-report=html
```

### Coverage Targets

| Module          | Coverage Target | Description                            |
|-----------------|-----------------|----------------------------------------|
| `src/core/`     | 80%+            | Critical business logic                |
| `src/profiles/` | 80%+            | Profile management                     |
| `src/ui/`       | 70%+            | GTK components (some lines untestable) |
| Overall `src/`  | 50% minimum     | Enforced by CI                         |

### Test Organization

Tests are organized to mirror the source code structure:

```
tests/
├── conftest.py                 # Shared fixtures, GTK mocking
├── core/                       # Tests for src/core/ modules
│   ├── test_battery_manager.py
│   ├── test_clamav_config.py
│   ├── test_daemon_scanner.py
│   ├── test_log_manager.py
│   ├── test_notification_manager.py
│   ├── test_quarantine_database.py
│   ├── test_quarantine_manager.py
│   ├── test_scheduler.py
│   ├── test_settings_manager.py
│   └── test_utils.py
├── profiles/                   # Tests for src/profiles/ modules
│   ├── test_models.py
│   ├── test_profile_manager.py
│   └── test_profile_storage.py
├── ui/                         # Tests for src/ui/ components
│   ├── test_fullscreen_dialog.py
│   ├── test_logs_view.py
│   ├── test_preferences_window.py
│   ├── test_profile_dialogs.py
│   ├── test_quarantine_view.py
│   ├── test_scanner_ui.py
│   ├── test_statistics_view.py
│   ├── test_tray_indicator.py
│   └── test_tray_manager.py
├── integration/                # Integration tests
│   ├── test_scanner_integration.py
│   ├── test_scheduled_scan.py
│   └── test_tray_integration.py
└── e2e/                        # End-to-end tests
    ├── test_profile_lifecycle.py
    └── test_scheduled_scan_flow.py
```

### Test Markers

Tests are categorized using pytest markers:

| Marker                     | Description                                           |
|----------------------------|-------------------------------------------------------|
| `@pytest.mark.integration` | Integration tests (may require external dependencies) |
| `@pytest.mark.ui`          | UI tests (require GTK/display environment)            |
| `@pytest.mark.slow`        | Slow-running tests                                    |

Run specific categories:

```bash
# Skip integration tests
pytest -m "not integration"

# Run only UI tests
pytest -m ui
```

### Headless/CI Testing

All tests are designed to run in headless CI environments without requiring a display server. GTK-dependent tests skip
gracefully when no display is available:

```bash
# Run in headless mode (no DISPLAY set)
unset DISPLAY
pytest

# GTK tests will show as skipped with a clear message
```

### Performance Verification

```bash
# Show slowest tests
pytest --durations=10

# Full suite should complete in under 30 seconds
pytest --durations=0
```

---

## Code Quality

### Linting with Ruff

ClamUI uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Install Ruff
pip install ruff

# Run linting
ruff check src/ tests/

# Run linting with auto-fix
ruff check --fix src/ tests/

# Check formatting
ruff format --check src/ tests/

# Apply formatting
ruff format src/ tests/
```

### Configuration

Ruff is configured in `pyproject.toml` with the following rules:

| Category | Rules                           |
|----------|---------------------------------|
| `E`, `W` | pycodestyle errors and warnings |
| `F`      | Pyflakes                        |
| `I`      | isort (import sorting)          |
| `B`      | flake8-bugbear                  |
| `C4`     | flake8-comprehensions           |
| `UP`     | pyupgrade                       |
| `ARG`    | flake8-unused-arguments         |
| `SIM`    | flake8-simplify                 |

### Pre-commit Checks

Before committing, run:

```bash
# Lint and format
ruff check --fix src/ tests/
ruff format src/ tests/

# Run tests
pytest
```

---

## Contributing

Contributions are welcome! Please follow these guidelines.

### Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/clamui.git
   cd clamui
   ```
3. Set up the development environment (see above)
4. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Development Workflow

1. **Make your changes** following the existing code patterns
2. **Add tests** for new functionality
3. **Run the test suite** and ensure all tests pass:
   ```bash
   pytest
   ```
4. **Check code quality**:
   ```bash
   ruff check --fix src/ tests/
   ruff format src/ tests/
   ```
5. **Commit your changes** with a descriptive message:
   ```bash
   git commit -m "Add feature: description of what you added"
   ```

### Writing Tests

Follow these patterns when writing tests:

1. **Use fixtures** for common setup (`@pytest.fixture`)
2. **Mock external dependencies** (ClamAV, system paths, GTK)
3. **Use `tmp_path`** fixture for file I/O tests
4. **Add docstrings** to all test methods
5. **Test error paths** explicitly

Example test structure:

```python
import pytest
from unittest import mock

class TestMyFeature:
    """Tests for MyFeature class."""

    @pytest.fixture
    def my_instance(self, tmp_path):
        """Create instance for testing."""
        return MyFeature(data_dir=str(tmp_path))

    def test_basic_operation(self, my_instance):
        """Test basic operation succeeds."""
        result = my_instance.do_something()
        assert result is not None

    def test_error_handling(self, my_instance):
        """Test error case is handled gracefully."""
        with pytest.raises(ValueError):
            my_instance.do_something_invalid()
```

### Pull Request Guidelines

1. **Update documentation** if you change APIs or add features
2. **Keep changes focused** - one feature or fix per PR
3. **Describe your changes** in the PR description
4. **Link related issues** using `Fixes #123` or `Closes #123`
5. **Ensure CI passes** - all tests and linting must pass

### Code Style

- **Python**: Follow PEP 8 (enforced by Ruff)
- **Line length**: 100 characters maximum
- **Imports**: Sorted by isort (enforced by Ruff)
- **Type hints**: Use where practical (not required)
- **Docstrings**: Required for classes and public methods

---

## Architecture Overview

### Tech Stack

| Component    | Technology                |
|--------------|---------------------------|
| Language     | Python 3.10+              |
| UI Framework | GTK4 with PyGObject       |
| UI Styling   | libadwaita (GNOME design) |
| Testing      | pytest, pytest-cov        |
| Linting      | Ruff                      |
| Packaging    | Hatch, Flatpak, Debian    |

### Key Design Patterns

- **Adw.Application**: Modern GNOME application structure
- **Async Scanning**: Background threads with `GLib.idle_add()` for thread-safe UI updates
- **Subprocess Integration**: `clamscan` for antivirus scanning

### Project Structure

```
clamui/
├── src/
│   ├── main.py               # Application entry point
│   ├── app.py                # Adw.Application class
│   ├── cli/                  # CLI tools
│   ├── core/                 # Business logic modules
│   ├── profiles/             # Scan profile management
│   └── ui/                   # GTK4/Adwaita UI components
├── tests/                    # Test suite (mirrors src structure)
├── docs/                     # Documentation
├── debian/                   # Debian packaging
├── .github/workflows/        # CI workflows
└── pyproject.toml            # Project configuration
```

For a detailed breakdown of all modules, see the [Project Structure](../README.md#project-structure) section in the
README.

---

## Continuous Integration

ClamUI uses GitHub Actions for CI with the following workflows:

| Workflow            | Trigger         | Purpose                              |
|---------------------|-----------------|--------------------------------------|
| `test.yml`          | Push/PR to main | Run tests on Python 3.10, 3.11, 3.12 |
| `lint.yml`          | Push/PR to main | Run Ruff linting and format checks   |
| `build-deb.yml`     | Manual/Release  | Build Debian packages                |
| `build-flatpak.yml` | Manual/Release  | Build Flatpak packages               |

### CI Environment

- **Runner**: Ubuntu 22.04
- **Display**: xvfb for headless GTK testing
- **Coverage**: Uploaded as artifact on Python 3.12

---

## See Also

- [README.md](../README.md) - Project overview and quick start
- [CONFIGURATION.md](./CONFIGURATION.md) - Configuration reference and settings guide
- [docs/INSTALL.md](./INSTALL.md) - Installation guide
- [TRANSLATING.md](./TRANSLATING.md) - Translation contributing guide
- [DEBIAN_PACKAGING.md](../DEBIAN_PACKAGING.md) - Debian packaging details
- [FLATPAK_SUBMISSION.md](../FLATPAK_SUBMISSION.md) - Flathub submission documentation
