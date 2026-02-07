# ClamUI Getting Started Guide

Welcome to ClamUI! This guide will help you get up and running quickly with ClamUI on Linux.

<div class="toc" data-toc="true">

## Table of Contents

- [What is ClamUI?](#what-is-clamui)
- [Installation](#installation)
  - [Quick Install (Recommended)](#quick-install-recommended)
  - [Alternative Methods](#alternative-methods)
  - [Verification](#verification)
- [Your First Use](#your-first-use)
  - [Launching the App](#launching-the-app)
  - [Understanding the Interface](#understanding-the-interface)
  - [Your First Scan](#your-first-scan)
  - [Understanding Results](#understanding-results)
- [Key Features](#key-features)
  - [Scan Profiles](#scan-profiles)
  - [Quarantine Management](#quarantine-management)
  - [Scheduled Scans](#scheduled-scans)
  - [System Tray](#system-tray)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)
- [Frequently Asked Questions](#frequently-asked-questions)

</div>

## What is ClamUI?

ClamUI is a user-friendly desktop application that brings the powerful ClamAV antivirus engine to your Linux desktop with an intuitive graphical interface.

|  |  |
|---|---|
| **Shield Icon** | ![Shield Icon](../icons/scalable/apps/io.github.linx_systems.ClamUI.svg) |
| **License** | MIT License |
| **Platforms** | Linux (GNOME, KDE, Xfce, and more) |
| **Installation** | Flatpak, .deb, or source |

**Key Features:**
- **Easy scanning** of files and folders
- **Virus quarantine** with restore capability
- **Scheduled scans** for automatic protection
- **System tray integration** for quick access
- **VirusTotal integration** for enhanced threat analysis
- **Scan history** with export options

---

## Installation

### Quick Install (Recommended)

The recommended installation method depends on your distribution:

| Distribution | Recommended Method |
|--------------|-------------------|
| **Any distribution** | [Flatpak](#flatpak-installation) (universal) |
| Debian, Ubuntu, Linux Mint | [.deb package](#debian-package-installation) |
| Fedora, Arch, others | [Flatpak](#flatpak-installation) |

#### Flatpak Installation

Flatpak works on any Linux distribution and includes automatic updates.

**1. Install Flatpak (if needed):**
```bash
# Ubuntu/Debian
sudo apt install flatpak

# Fedora (pre-installed)
# Fedora includes Flatpak by default

# Arch Linux
sudo pacman -S flatpak
```

**2. Add Flathub repository:**
```bash
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

**3. Install ClamUI:**
```bash
flatpak install flathub io.github.linx_systems.ClamUI
```

> **Note:** The Flatpak version bundles ClamAV internally — no separate ClamAV installation is required.

**4. Launch ClamUI:**
```bash
flatpak run io.github.linx_systems.ClamUI
```
Or find "ClamUI" in your application menu.

---

### Alternative Methods

#### Debian Package Installation

For Debian, Ubuntu, and derivative distributions:

**1. Install dependencies:**
```bash
# GTK4, Adwaita, and Python bindings
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1

# ClamAV antivirus
sudo apt install clamav
```

**2. Download and install the .deb package:**
Download from the [releases page](https://github.com/linx-systems/clamui/releases), then:
```bash
sudo dpkg -i clamui_*.deb
sudo apt install -f  # Fix any missing dependencies
```

#### Running from Source

For development or the latest changes:

```bash
git clone https://github.com/linx-systems/clamui.git
cd clamui

# Install system dependencies
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 clamav

# Install Python dependencies
uv sync --dev

# Run ClamUI
uv run clamui
```

---

### Verification

After installation, verify ClamUI is working correctly:

```bash
# For native installation
which clamui
clamui --version

# For Flatpak
flatpak info io.github.linx_systems.ClamUI
```

Check ClamAV is installed:
```bash
clamscan --version
freshclam --version
```

---

## Your First Use

### Launching the App

After installation, launch ClamUI in one of these ways:

1. **From your Application Menu:** Search for "ClamUI" in your desktop's application launcher
2. **From the Terminal:**
   ```bash
   # Flatpak
   flatpak run io.github.linx_systems.ClamUI

   # Native installation
   clamui
   ```

When you first launch, ClamUI will:
- Check for ClamAV installation
- Create default scan profiles (Quick Scan, Full Scan, Home Folder)

### Understanding the Interface

ClamUI has 6 main views, accessible via the sidebar:

| View | Icon | Purpose |
|------|------|---------|
| **Scan** | `document-open` | File/folder scanning interface |
| **Updates** | `system-software-update` | Virus database updates |
| **Logs** | `document-history` | Past scan history |
| **Quarantine** | `security-medium-symbolic` | Manage quarantined files |
| **Statistics** | `chart-symbolic` | Scan statistics dashboard |
| **Preferences** | `preferences-system-symbolic` | Application settings |

### Your First Scan

1. **Click the Scan view** (first icon in the sidebar)
2. **Click "Select Files or Folders"** or drag files onto the window
3. **Click "Scan"** to begin

> **Tip:** You can also right-click files in your file manager and select "Scan with ClamUI" (requires context menu setup).

### Understanding Results

After a scan completes, you'll see:

| Status | Color | Meaning |
|--------|-------|---------|
| **Clean** | Green | No threats detected |
| **Infected** | Red | Threats found - see Quarantine |
| **Error** | Orange | Scan failed (see details) |

**If threats are found:**
- Click "View Details" to see infected files
- Click "Quarantine" to isolate threats
- Click "Restore" to return files from quarantine

---

## Key Features

### Scan Profiles

Scan profiles save your scan settings for easy reuse.

**Default profiles created automatically:**

| Profile | Targets | Description |
|---------|---------|-------------|
| **Quick Scan** | Downloads folder | Fast scan of Downloads folder |
| **Full Scan** | Root filesystem (/) with exclusions | System-wide scan (excludes /proc, /sys, /dev, etc.) |
| **Custom** | User-defined | Create your own profiles |

**Creating a custom profile:**
1. Go to Scan view
2. Click "Save as Profile"
3. Enter a name and configure targets
4. Click "Save"

### Quarantine Management

The quarantine holds potentially harmful files for review.

**Common actions:**
- **View quarantined files** - Quarantine view shows all isolated files
- **Restore files** - Click "Restore" to return a file to its original location
- **Delete permanently** - Click "Delete" to remove from quarantine

### Scheduled Scans

Automate your antivirus protection with scheduled scans.

**Setting up scheduled scans:**
1. Open Preferences
2. Go to "Scheduled Scans"
3. Enable automatic scanning
4. Choose frequency (daily/weekly)
5. Select scan profile and time

**Features:**
- Systemd timers (modern Linux) or cron (older systems)
- Battery-aware scanning (waits for AC power)
- Email notifications on completion

### System Tray

Quick access to ClamUI from your system tray.

**Requirements:**
```bash
# Ubuntu/Debian
sudo apt install gir1.2-ayatanaappindicator3-0.1
```

**Features:**
- Status indicator (protected/warning/scanning/threat)
- Quick actions (Quick Scan, Full Scan, Update)
- Scan progress display
- Window toggle

---

## Troubleshooting

### Common Issues

**ClamAV Not Found**
```
Symptom: ClamUI cannot find ClamAV
Solution: Install ClamAV: sudo apt install clamav
```

**Permissions Denied**
```
Symptom: Cannot scan certain directories
Solution: Grant additional filesystem permissions
  flatpak override --user --filesystem=/path/to/directory io.github.linx_systems.ClamUI
```

**System Tray Not Working**
```
Symptom: No tray icon appears
Solution: Install AppIndicator library (see System Tray section)
```

### When to Check the Full Troubleshooting Guide

For more detailed solutions, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) which covers:
- Flatpak-specific issues
- Daemon connection problems
- Database update failures
- Performance tuning

---

## Next Steps

### For End Users

| Document | Description |
|----------|-------------|
| [USER_GUIDE.md](./USER_GUIDE.md) | Comprehensive user guide covering all features |
| [CONFIGURATION.md](./CONFIGURATION.md) | Settings and configuration reference |

### For Contributors

| Document | Description |
|----------|-------------|
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Development setup and contribution guide |
| [docs/architecture/](./architecture/) | Technical architecture documentation |

### Additional Resources

- [Official Website](https://github.com/linx-systems/clamui) - Project overview
- [GitHub Issues](https://github.com/linx-systems/clamui/issues) - Report bugs and request features

---

## Frequently Asked Questions

**Q: Is ClamUI the same as ClamAV?**
A: ClamAV is the command-line antivirus engine. ClamUI is a graphical interface for ClamAV.

**Q: How often should I scan my computer?**
A: Weekly scans are recommended. Set up scheduled scans for automatic protection.

**Q: What should I do if a scan finds threats?**
A: Review the threats in the Quarantine view. You can delete them or restore them if false positives.

**Q: Does scanning slow down my computer?**
A: Scans use minimal resources. Use "Quick Scan" for faster scans or schedule them when idle.

**Q: Can I scan external drives and USB devices?**
A: Yes! Drag and drop any file or folder onto the Scan view.

**Q: Where are my scan logs stored?**
A: In `~/.local/share/clamui/logs/` for native installs, or `~/.var/app/io.github.linx_systems.ClamUI/data/clamui/logs/` for Flatpak.

**Q: How do I update virus definitions?**
A: Click "Check for Updates" in the Updates view, or run `freshclam` from the terminal.

---
