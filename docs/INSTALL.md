# ClamUI Installation Guide

This document provides comprehensive installation instructions for ClamUI on Linux systems.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Flatpak Installation](#flatpak-installation)
3. [Debian Package Installation](#debian-package-installation)
4. [File Manager Context Menu](#file-manager-context-menu)
5. [System Tray Integration](#system-tray-integration)
6. [Verification](#verification)
7. [Uninstallation](#uninstallation)

---

## Quick Start

The recommended installation method depends on your Linux distribution:

| Distribution | Recommended Method |
|-------------|-------------------|
| Any (universal) | [Flatpak](#flatpak-installation) |
| Debian, Ubuntu, Linux Mint | [.deb package](#debian-package-installation) |
| Fedora, Arch, others | [Flatpak](#flatpak-installation) |

---

## Flatpak Installation

Flatpak is the recommended installation method as it works on any Linux distribution and includes automatic updates.

### Prerequisites

Ensure Flatpak is installed on your system:

```bash
# Ubuntu/Debian
sudo apt install flatpak

# Fedora (pre-installed)
# flatpak is included by default

# Arch Linux
sudo pacman -S flatpak
```

Add the Flathub repository if not already configured:

```bash
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

### Install ClamUI

```bash
flatpak install flathub com.github.rooki.ClamUI
```

### Install Host ClamAV (Required)

ClamUI requires ClamAV to be installed on your host system for scanning functionality:

```bash
# Ubuntu/Debian
sudo apt install clamav

# Fedora
sudo dnf install clamav clamav-update

# Arch Linux
sudo pacman -S clamav
```

Update the virus definitions:

```bash
sudo freshclam
```

### Run ClamUI

```bash
flatpak run com.github.rooki.ClamUI
```

Or find "ClamUI" in your application menu.

> **Troubleshooting**: If you encounter issues with Flatpak installation or ClamAV not being detected, see [Flatpak-Specific Issues](./TROUBLESHOOTING.md#flatpak-specific-issues) and [ClamAV Installation Issues](./TROUBLESHOOTING.md#clamav-installation-issues) in the troubleshooting guide.

### Flatpak Permissions

ClamUI requests the following permissions:

| Permission | Purpose |
|------------|---------|
| `--filesystem=host:ro` | Read-only access to scan files and directories |
| `--talk-name=org.freedesktop.Flatpak` | Execute host ClamAV binaries via `flatpak-spawn` |
| `--socket=session-bus` | Desktop notifications for scan completion |
| `--socket=wayland` | Native Wayland display support |
| `--socket=fallback-x11` | X11 compatibility |

### Managing Permissions

View current permissions:

```bash
flatpak info --show-permissions com.github.rooki.ClamUI
```

Override permissions if needed:

```bash
# Grant access to additional directories
flatpak override --user --filesystem=/path/to/directory com.github.rooki.ClamUI
```

---

## Debian Package Installation

For Debian, Ubuntu, and derivative distributions, ClamUI is available as a `.deb` package.

### Prerequisites

Install the required system dependencies:

```bash
# GTK4 and Adwaita runtime libraries
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1

# ClamAV antivirus
sudo apt install clamav
```

### Download and Install

Download the latest `.deb` package from the [releases page](https://github.com/Pdzly/clamui/releases), then install:

```bash
# Install the package
sudo dpkg -i clamui_*.deb

# Resolve any missing dependencies
sudo apt install -f
```

Or install directly with apt:

```bash
sudo apt install ./clamui_*.deb
```

### What Gets Installed

| Path | Description |
|------|-------------|
| `/usr/bin/clamui` | Launcher script |
| `/usr/lib/python3/dist-packages/clamui/` | Python application modules |
| `/usr/share/applications/com.github.rooki.ClamUI.desktop` | Desktop entry file |
| `/usr/share/icons/hicolor/scalable/apps/com.github.rooki.ClamUI.svg` | Application icon |

### Run ClamUI

```bash
clamui
```

Or find "ClamUI" in your application menu.

> **Troubleshooting**: If you encounter issues with missing dependencies or ClamAV installation, see [ClamAV Installation Issues](./TROUBLESHOOTING.md#clamav-installation-issues) in the troubleshooting guide.

### Further Information

For detailed information about building and troubleshooting the Debian package, see [DEBIAN_PACKAGING.md](../DEBIAN_PACKAGING.md).

---

## File Manager Context Menu

ClamUI integrates with file managers to provide a "Scan with ClamUI" right-click option.

### Supported File Managers

| File Manager | Desktop | Integration Type |
|--------------|---------|-----------------|
| Nautilus | GNOME | Desktop entry action |
| Dolphin | KDE | Desktop entry action |
| Nemo | Cinnamon | Native Nemo action |

### Flatpak Users

If you installed ClamUI via Flatpak, context menu integration is **included automatically**. The Flatpak manifest includes the necessary filesystem permissions to access files for scanning.

### Native Installation

For native (non-Flatpak) installations, set up context menu integration manually:

#### GNOME (Nautilus) and KDE (Dolphin)

1. **Copy the desktop file**:
   ```bash
   cp com.github.clamui.desktop ~/.local/share/applications/
   ```

2. **Update the desktop database**:
   ```bash
   update-desktop-database ~/.local/share/applications
   ```

3. **Restart your file manager**:
   ```bash
   # For GNOME (Nautilus):
   nautilus -q

   # For KDE (Dolphin):
   killall dolphin
   ```

#### Cinnamon (Nemo)

Nemo uses its own action format for context menu extensions:

1. **Create the Nemo actions directory**:
   ```bash
   mkdir -p ~/.local/share/nemo/actions
   ```

2. **Copy the Nemo action file**:
   ```bash
   cp com.github.clamui.nemo_action ~/.local/share/nemo/actions/
   ```

3. **Restart Nemo**:
   ```bash
   nemo -q
   ```

### Using the Context Menu

| Action | Description |
|--------|-------------|
| **Single file** | Right-click a file and select "Scan with ClamUI" |
| **Folder** | Right-click a folder to recursively scan all contents |
| **Multiple selection** | Select multiple files/folders, right-click, and scan all at once |

### Verifying Context Menu Installation

Check that the integration files are installed:

```bash
# Desktop entry
ls ~/.local/share/applications/com.github.clamui.desktop

# Nemo action (if using Nemo)
ls ~/.local/share/nemo/actions/com.github.clamui.nemo_action
```

If the context menu doesn't appear:

1. Log out and log back in
2. Manually refresh the desktop database:
   ```bash
   update-desktop-database ~/.local/share/applications
   gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor
   ```

> **Troubleshooting**: For more detailed troubleshooting of context menu issues, see [File Manager Context Menu Issues](./TROUBLESHOOTING.md#file-manager-context-menu-issues) in the troubleshooting guide.

---

## System Tray Integration

ClamUI provides an optional system tray icon for quick access to scanning functions.

### Features

| Feature | Description |
|---------|-------------|
| **Status Indicator** | Tray icon shows protection status (protected, warning, scanning, threat) |
| **Quick Actions** | Right-click menu for Quick Scan, Full Scan, and Update Definitions |
| **Scan Progress** | Shows scan progress percentage during active scans |
| **Window Toggle** | Click the tray icon to show/hide the main window |
| **Minimize to Tray** | Option to hide to tray instead of taskbar when minimizing |

### Requirements

The system tray feature requires the AyatanaAppIndicator3 library:

```bash
# Ubuntu/Debian
sudo apt install gir1.2-ayatanaappindicator3-0.1

# Fedora
sudo dnf install libayatana-appindicator-gtk3

# Arch Linux
sudo pacman -S libayatana-appindicator
```

### GNOME Shell Users

GNOME Shell requires an additional extension for tray icon support:

1. Install the [AppIndicator Support](https://extensions.gnome.org/extension/615/appindicator-support/) extension
2. Enable the extension in GNOME Extensions app

### Graceful Degradation

If the AppIndicator library is not installed, ClamUI runs normally without the tray icon feature. The application logs a warning but continues to function with all other features.

> **Troubleshooting**: If the system tray icon is not appearing or not working correctly, see [System Tray Icon Issues](./TROUBLESHOOTING.md#system-tray-icon-issues) in the troubleshooting guide.

---

## Verification

After installation, verify that ClamUI is working correctly.

### Check Installation

```bash
# For native installation
which clamui
clamui --version

# For Flatpak
flatpak info com.github.rooki.ClamUI
```

### Check ClamAV

```bash
# Verify ClamAV is installed
clamscan --version

# Check virus database is up to date
freshclam --version
```

### Test a Scan

Launch ClamUI and perform a test scan on a small directory to verify everything is working.

> **Troubleshooting**: If ClamAV is not detected or scanning fails, see [ClamAV Installation Issues](./TROUBLESHOOTING.md#clamav-installation-issues) in the troubleshooting guide.

---

## Uninstallation

### Flatpak

```bash
flatpak uninstall com.github.rooki.ClamUI
```

### Debian Package

```bash
# Remove (keeps configuration files)
sudo dpkg -r clamui

# Purge (removes everything including config)
sudo dpkg -P clamui
```

### Context Menu Cleanup

If you manually installed context menu integration:

```bash
# Remove desktop entry
rm ~/.local/share/applications/com.github.clamui.desktop

# Remove Nemo action
rm ~/.local/share/nemo/actions/com.github.clamui.nemo_action

# Refresh desktop database
update-desktop-database ~/.local/share/applications
```

---

## See Also

- [README.md](../README.md) - Project overview and quick start
- [CONFIGURATION.md](./CONFIGURATION.md) - Configuration reference and settings guide
- [DEBIAN_PACKAGING.md](../DEBIAN_PACKAGING.md) - Detailed Debian packaging guide
- [FLATPAK_SUBMISSION.md](../FLATPAK_SUBMISSION.md) - Flathub submission documentation
- [docs/DEVELOPMENT.md](./DEVELOPMENT.md) - Development setup and contributing
