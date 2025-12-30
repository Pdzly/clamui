# ClamUI Debian Package Guide

This document provides comprehensive instructions for building, installing, and understanding the Debian packaging for ClamUI.

## Table of Contents

1. [Overview](#overview)
2. [Debian Package Structure](#debian-package-structure)
3. [Control File Reference](#control-file-reference)
4. [Maintainer Scripts](#maintainer-scripts)
5. [Prerequisites](#prerequisites)
6. [Building the Package](#building-the-package)
7. [Installing and Removing](#installing-and-removing)
8. [Verification Commands](#verification-commands)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)

---

## Overview

ClamUI is distributed as a Debian `.deb` package for easy installation on Debian, Ubuntu, and derivative Linux distributions. The package follows the Filesystem Hierarchy Standard (FHS) and Debian Policy for proper system integration.

### Package Information

| Field | Value |
|-------|-------|
| Package Name | `clamui` |
| Architecture | `all` (pure Python, platform-independent) |
| Section | `utils` |
| Priority | `optional` |

### What Gets Installed

When you install the ClamUI package, the following files are placed on your system:

| Path | Description |
|------|-------------|
| `/usr/bin/clamui` | Launcher script (executable) |
| `/usr/lib/python3/dist-packages/clamui/` | Python application modules |
| `/usr/share/applications/com.github.rooki.ClamUI.desktop` | Desktop entry file |
| `/usr/share/icons/hicolor/scalable/apps/com.github.rooki.ClamUI.svg` | Application icon |
| `/usr/share/metainfo/com.github.rooki.ClamUI.metainfo.xml` | AppStream metadata |

---

## Debian Package Structure

A `.deb` package is essentially an `ar` archive containing control information and file data. The ClamUI package follows this standard structure:

```
clamui_0.1.0_all.deb
└── (archive contents)
    ├── debian-binary          # Package format version ("2.0")
    ├── control.tar.xz         # Control files archive
    │   ├── control            # Package metadata
    │   ├── postinst           # Post-installation script
    │   ├── prerm              # Pre-removal script
    │   └── postrm             # Post-removal script
    └── data.tar.xz            # Installed files archive
        └── usr/
            ├── bin/
            │   └── clamui     # Launcher script
            ├── lib/
            │   └── python3/
            │       └── dist-packages/
            │           └── clamui/
            │               ├── __init__.py
            │               ├── main.py
            │               ├── app.py
            │               ├── core/
            │               └── ui/
            └── share/
                ├── applications/
                │   └── com.github.rooki.ClamUI.desktop
                ├── icons/
                │   └── hicolor/
                │       └── scalable/
                │           └── apps/
                │               └── com.github.rooki.ClamUI.svg
                └── metainfo/
                    └── com.github.rooki.ClamUI.metainfo.xml
```

### Directory Purposes

| Directory | Purpose |
|-----------|---------|
| `DEBIAN/` | Contains package control files and maintainer scripts |
| `usr/bin/` | User-executable programs |
| `usr/lib/python3/dist-packages/` | System-wide Python modules |
| `usr/share/applications/` | Desktop entry files for application menus |
| `usr/share/icons/hicolor/` | Theme-compatible icons (follows freedesktop.org spec) |
| `usr/share/metainfo/` | AppStream application metadata |

---

## Control File Reference

The control file (`debian/DEBIAN/control`) defines package metadata that `dpkg` uses for installation and dependency resolution.

### Control File Format

```
Package: clamui
Version: 0.1.0
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-gi, python3-cairo, gir1.2-gtk-4.0, gir1.2-adw-1, clamav
Maintainer: ClamUI Contributors <clamui@example.com>
Homepage: https://github.com/yourusername/clamui
Description: Modern graphical interface for ClamAV antivirus scanner
 ClamUI is a modern Linux desktop application that provides a graphical
 user interface for the ClamAV antivirus command-line tool.
 .
 Features:
  - Easy-to-use GTK4/libadwaita interface
  - Scan files and directories for malware
  - View and manage scan results
  - Desktop integration with notifications
 .
 This package requires ClamAV to be installed for scanning functionality.
```

### Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `Package` | Yes | Package name (lowercase, alphanumeric, hyphens allowed) |
| `Version` | Yes | Version number (typically `major.minor.patch`) |
| `Section` | No | Category in the archive (`utils`, `admin`, `net`, etc.) |
| `Priority` | No | Installation priority (`required`, `important`, `standard`, `optional`) |
| `Architecture` | Yes | Target architecture (`all` for platform-independent, `amd64`, `arm64`, etc.) |
| `Depends` | No | Packages required for this package to function |
| `Maintainer` | Yes | Name and email of package maintainer |
| `Homepage` | No | Project website URL |
| `Description` | Yes | Short description (first line) and long description (subsequent lines, indented with space) |

### Dependency Explanation

ClamUI depends on the following system packages:

| Dependency | Purpose |
|------------|---------|
| `python3 (>= 3.10)` | Python interpreter (version 3.10 or higher required) |
| `python3-gi` | PyGObject bindings for GLib/GTK |
| `python3-cairo` | Python bindings for Cairo graphics library |
| `gir1.2-gtk-4.0` | GTK 4 introspection data |
| `gir1.2-adw-1` | libadwaita introspection data |
| `clamav` | ClamAV antivirus engine |

---

## Maintainer Scripts

Maintainer scripts are shell scripts that run at various points during package installation and removal. ClamUI uses three maintainer scripts.

### Script Execution Order

**During Installation (`dpkg -i`):**
1. `preinst` (not used by ClamUI)
2. Files are unpacked
3. `postinst configure`

**During Removal (`dpkg -r`):**
1. `prerm remove`
2. Files are removed
3. `postrm remove`

**During Purge (`dpkg -P`):**
1. Same as removal
2. `postrm purge` (removes configuration files)

### postinst Script

The `postinst` script runs after package files are installed. ClamUI's postinst:

- Updates the desktop file database (`update-desktop-database`)
- Refreshes the GTK icon cache (`gtk-update-icon-cache`)

```bash
#!/bin/bash
set -e

case "$1" in
    configure)
        # Update desktop file database
        if command -v update-desktop-database > /dev/null 2>&1; then
            update-desktop-database -q /usr/share/applications || true
        fi

        # Update GTK icon cache
        if command -v gtk-update-icon-cache > /dev/null 2>&1; then
            gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
        fi
        ;;
esac

exit 0
```

### prerm Script

The `prerm` script runs before package files are removed. ClamUI's prerm is minimal since there are no background services to stop:

```bash
#!/bin/bash
set -e

case "$1" in
    remove|upgrade|deconfigure)
        # No services to stop for GUI application
        ;;
esac

exit 0
```

### postrm Script

The `postrm` script runs after package files are removed. ClamUI's postrm:

- Updates the desktop file database to remove the application entry
- Refreshes the icon cache to remove the application icon

```bash
#!/bin/bash
set -e

case "$1" in
    remove|purge)
        if command -v update-desktop-database > /dev/null 2>&1; then
            update-desktop-database -q /usr/share/applications || true
        fi
        if command -v gtk-update-icon-cache > /dev/null 2>&1; then
            gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
        fi
        ;;
esac

exit 0
```

### Script Best Practices

All ClamUI maintainer scripts follow Debian best practices:

1. **Idempotent**: Scripts can be run multiple times without side effects
2. **Error Tolerant**: Commands use `|| true` to prevent failures from aborting
3. **Command Checks**: `command -v` verifies tools exist before use
4. **Proper Exit**: Scripts exit with code 0 on success

---

## Prerequisites

Before building the ClamUI Debian package, install the required build tools:

```bash
# Install Debian packaging tools
sudo apt install dpkg-dev fakeroot

# Verify installation
dpkg-deb --version
fakeroot --version
```

### Tool Descriptions

| Tool | Package | Purpose |
|------|---------|---------|
| `dpkg-deb` | `dpkg-dev` | Creates and extracts `.deb` archives |
| `fakeroot` | `fakeroot` | Simulates root privileges for file ownership |

---

## Building the Package

### Quick Build

From the project root directory:

```bash
# Make the script executable (if needed)
chmod +x debian/build-deb.sh

# Build the package
./debian/build-deb.sh
```

This creates `clamui_VERSION_all.deb` in the project root (e.g., `clamui_0.1.0_all.deb`).

### What the Build Script Does

1. **Checks Prerequisites**: Verifies `dpkg-deb` and `fakeroot` are available
2. **Extracts Version**: Reads version from `pyproject.toml`
3. **Creates Build Directory**: Sets up FHS-compliant directory structure
4. **Copies Python Source**: Installs source to `dist-packages` (excluding `__pycache__`)
5. **Creates Launcher**: Generates `/usr/bin/clamui` executable script
6. **Copies Desktop Files**: Installs `.desktop`, icon, and metainfo files
7. **Processes Control Files**: Copies DEBIAN files with version substitution
8. **Builds Package**: Uses `fakeroot dpkg-deb --build`
9. **Cleans Up**: Removes temporary build directory

### Build Options

```bash
# Show help
./debian/build-deb.sh --help
```

---

## Installing and Removing

### Install the Package

```bash
# Install the package
sudo dpkg -i clamui_0.1.0_all.deb

# If there are missing dependencies, fix them with:
sudo apt install -f
```

### Run the Application

After installation:

```bash
# From command line
clamui

# Or find "ClamUI" in your application menu
```

### Remove the Package

```bash
# Remove (keeps configuration files)
sudo dpkg -r clamui

# Purge (removes everything including config)
sudo dpkg -P clamui
```

---

## Verification Commands

### Before Installation

```bash
# Show package information
dpkg -I clamui_0.1.0_all.deb

# List package contents
dpkg -c clamui_0.1.0_all.deb

# Extract package without installing (for inspection)
dpkg-deb -x clamui_0.1.0_all.deb ./extract-test/
dpkg-deb -e clamui_0.1.0_all.deb ./extract-test/DEBIAN/
```

### After Installation

```bash
# Check if package is installed
dpkg -l clamui

# Show installed package details
dpkg -s clamui

# List files installed by package
dpkg -L clamui

# Find which package owns a file
dpkg -S /usr/bin/clamui

# Verify clamui is in PATH
which clamui
```

---

## Troubleshooting

### Build Errors

#### "dpkg-deb not found"

```bash
# Install dpkg-dev
sudo apt install dpkg-dev
```

#### "fakeroot not found"

```bash
# Install fakeroot
sudo apt install fakeroot
```

#### "pyproject.toml not found"

Ensure you're running the build script from the project root:

```bash
cd /path/to/clamui
./debian/build-deb.sh
```

#### "Could not extract version"

Check that `pyproject.toml` contains a valid version:

```toml
[project]
version = "0.1.0"
```

### Installation Errors

#### "Dependency is not satisfiable"

Install missing dependencies:

```bash
sudo apt install -f

# Or manually install specific dependencies
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 clamav
```

#### "Package architecture does not match"

The ClamUI package is `Architecture: all` and should work on any system. If you see this error, verify the package wasn't corrupted during transfer.

### Runtime Errors

#### "ModuleNotFoundError: No module named 'clamui'"

The Python path may not include the system packages directory:

```bash
# Check if clamui is installed
ls /usr/lib/python3/dist-packages/clamui/

# Run with explicit Python path
PYTHONPATH=/usr/lib/python3/dist-packages python3 -m clamui.main
```

#### "No module named 'gi'"

GTK Python bindings are missing:

```bash
sudo apt install python3-gi python3-cairo
```

#### "Namespace Gtk not available"

GTK 4 introspection data is missing:

```bash
sudo apt install gir1.2-gtk-4.0
```

#### "Namespace Adw not available"

libadwaita introspection data is missing:

```bash
sudo apt install gir1.2-adw-1
```

#### Application icon not showing

Refresh the icon cache:

```bash
sudo gtk-update-icon-cache -f /usr/share/icons/hicolor
```

#### Application not in menu

Refresh the desktop database:

```bash
sudo update-desktop-database
```

---

## Advanced Topics

### Manual Package Building

If you need to build the package manually without the build script:

```bash
# Create build directory structure
mkdir -p build-deb/DEBIAN
mkdir -p build-deb/usr/bin
mkdir -p build-deb/usr/lib/python3/dist-packages/clamui
mkdir -p build-deb/usr/share/applications
mkdir -p build-deb/usr/share/icons/hicolor/scalable/apps
mkdir -p build-deb/usr/share/metainfo

# Copy Python source (excluding __pycache__)
rsync -a --exclude='__pycache__' src/ build-deb/usr/lib/python3/dist-packages/clamui/

# Create launcher script
cat > build-deb/usr/bin/clamui << 'EOF'
#!/usr/bin/env python3
import sys
from clamui.main import main
sys.exit(main())
EOF
chmod 755 build-deb/usr/bin/clamui

# Copy desktop files
cp com.github.rooki.ClamUI.desktop build-deb/usr/share/applications/
cp icons/com.github.rooki.ClamUI.svg build-deb/usr/share/icons/hicolor/scalable/apps/
cp com.github.rooki.ClamUI.metainfo.xml build-deb/usr/share/metainfo/

# Copy and modify control file
sed 's/^Version: VERSION$/Version: 0.1.0/' debian/DEBIAN/control > build-deb/DEBIAN/control
cp debian/DEBIAN/post* debian/DEBIAN/prerm build-deb/DEBIAN/
chmod 755 build-deb/DEBIAN/postinst build-deb/DEBIAN/prerm build-deb/DEBIAN/postrm

# Set proper permissions
chmod 644 build-deb/DEBIAN/control
find build-deb/usr -type f -name '*.py' -exec chmod 644 {} +
find build-deb/usr/share -type f -exec chmod 644 {} +

# Build package
fakeroot dpkg-deb --build build-deb clamui_0.1.0_all.deb

# Clean up
rm -rf build-deb
```

### Inspecting an Existing Package

```bash
# Extract control files
ar x clamui_0.1.0_all.deb
tar xf control.tar.xz
cat control

# View all metadata
dpkg -I clamui_0.1.0_all.deb

# View file listing
dpkg -c clamui_0.1.0_all.deb
```

### Version Numbering

ClamUI follows semantic versioning (`MAJOR.MINOR.PATCH`):

- **MAJOR**: Incompatible API changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

The version is sourced from `pyproject.toml` and automatically substituted into the control file during build.

### Testing Package Installation in a Clean Environment

Use Docker to test package installation:

```bash
# Build test image
docker run -it --rm -v $(pwd):/pkg ubuntu:22.04 bash

# Inside container
apt update
apt install /pkg/clamui_0.1.0_all.deb
apt install -f
clamui --version  # Verify installation
```

### Lintian (Package Quality Checker)

For thorough package validation, use lintian:

```bash
# Install lintian
sudo apt install lintian

# Check package
lintian clamui_0.1.0_all.deb

# Verbose output with explanations
lintian -i -I clamui_0.1.0_all.deb
```

---

## Additional Resources

- [Debian Policy Manual](https://www.debian.org/doc/debian-policy/)
- [Debian New Maintainers' Guide](https://www.debian.org/doc/manuals/maint-guide/)
- [dpkg Manual Page](https://man7.org/linux/man-pages/man1/dpkg.1.html)
- [Filesystem Hierarchy Standard](https://refspecs.linuxfoundation.org/fhs.shtml)
- [Desktop Entry Specification](https://specifications.freedesktop.org/desktop-entry-spec/latest/)
- [AppStream Specification](https://www.freedesktop.org/software/appstream/docs/)
