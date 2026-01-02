# ClamUI Troubleshooting Guide

This guide helps you diagnose and resolve common issues with ClamUI. If you encounter a problem not covered here, please [open an issue](https://github.com/rooki/clamui/issues) on GitHub.

## Table of Contents

1. [ClamAV Installation Issues](#clamav-installation-issues)
   - [ClamAV not found](#clamav-not-found)
   - [freshclam not installed](#freshclam-not-installed)
   - [clamdscan unavailable](#clamdscan-unavailable)
   - [clamd daemon not running](#clamd-daemon-not-running)
   - [Version compatibility](#version-compatibility)

2. [Flatpak-Specific Issues](#flatpak-specific-issues)
   - [Host ClamAV not accessible](#host-clamav-not-accessible)
   - [Permission denied when scanning files](#permission-denied-when-scanning-files)
   - [Granting additional filesystem access](#granting-additional-filesystem-access)
   - [D-Bus and portal permission issues](#d-bus-and-portal-permission-issues)

3. [System Tray Icon Issues](#system-tray-icon-issues)
   - [Tray icon not appearing](#tray-icon-not-appearing)
   - [AppIndicator library missing](#appindicator-library-missing)
   - [GNOME Shell tray support](#gnome-shell-tray-support)
   - [Desktop environment compatibility](#desktop-environment-compatibility)
   - [Flatpak tray icon issues](#flatpak-tray-icon-issues)
   - [Tray icon status not updating](#tray-icon-status-not-updating)
   - [Tray icon shows wrong icon or generic fallback](#tray-icon-shows-wrong-icon-or-generic-fallback)

4. [File Manager Context Menu Issues](#file-manager-context-menu-issues)
   - [Context menu not appearing](#context-menu-not-appearing)
   - [Desktop file permissions](#desktop-file-permissions)
   - [Manual context menu installation](#manual-context-menu-installation)
   - [File manager refresh requirements](#file-manager-refresh-requirements)

5. [Scanning Errors](#scanning-errors)
   - [Permission denied errors](#permission-denied-errors)
   - [Path validation failures](#path-validation-failures)
   - [Symlink security warnings](#symlink-security-warnings)
   - [Daemon connection failures](#daemon-connection-failures)
   - [Scan timeout issues](#scan-timeout-issues)

6. [Database Update Issues](#database-update-issues)
   - [freshclam permission errors](#freshclam-permission-errors)
   - [Running updates without root](#running-updates-without-root)
   - [Database location issues](#database-location-issues)
   - [Network connectivity problems](#network-connectivity-problems)
   - [Outdated database warnings](#outdated-database-warnings)

7. [Scheduled Scanning Issues](#scheduled-scanning-issues)
   - [Systemd user timers not working](#systemd-user-timers-not-working)
   - [Cron fallback configuration](#cron-fallback-configuration)
   - [Battery detection issues](#battery-detection-issues)
   - [Scheduled scans not running](#scheduled-scans-not-running)
   - [Verifying scheduled scan logs](#verifying-scheduled-scan-logs)

8. [General Issues](#general-issues)
   - [Application won't start](#application-wont-start)
   - [UI appears frozen](#ui-appears-frozen)
   - [High CPU or memory usage](#high-cpu-or-memory-usage)
   - [Quarantine operations failing](#quarantine-operations-failing)
   - [Settings not persisting](#settings-not-persisting)

9. [Frequently Asked Questions (FAQ)](#frequently-asked-questions-faq)
   - [What is ClamUI vs ClamAV?](#what-is-clamui-vs-clamav)
   - [Why is scanning slow?](#why-is-scanning-slow)
   - [How do I enable daemon mode?](#how-do-i-enable-daemon-mode)
   - [What does quarantine do?](#what-does-quarantine-do)
   - [How do I create custom scan profiles?](#how-do-i-create-custom-scan-profiles)
   - [What are the system requirements?](#what-are-the-system-requirements)

10. [Getting Help](#getting-help)

---

## ClamAV Installation Issues

### ClamAV not found

**Symptoms**: Error message "ClamAV is not installed" or "clamscan command not found"

**Solution**: Install ClamAV on your system

```bash
# Ubuntu/Debian
sudo apt install clamav

# Fedora
sudo dnf install clamav clamav-update

# Arch Linux
sudo pacman -S clamav
```

Verify the installation:

```bash
clamscan --version
```

### freshclam not installed

**Symptoms**: Database update fails with "freshclam not found"

**Solution**: Install the freshclam package (usually included with ClamAV)

```bash
# Ubuntu/Debian
sudo apt install clamav-freshclam

# Fedora (included in clamav-update)
sudo dnf install clamav-update

# Arch Linux (included in clamav)
sudo pacman -S clamav
```

### clamdscan unavailable

**Symptoms**: Warning about daemon scanner not available

**Solution**: Install and start the ClamAV daemon

```bash
# Ubuntu/Debian
sudo apt install clamav-daemon
sudo systemctl enable --now clamav-daemon

# Fedora
sudo dnf install clamd
sudo systemctl enable --now clamd@scan

# Arch Linux
sudo pacman -S clamav
sudo systemctl enable --now clamd
```

### clamd daemon not running

**Symptoms**: "Daemon connection failed" errors

**Solution**: Start the ClamAV daemon

```bash
# Check daemon status
sudo systemctl status clamav-daemon  # Ubuntu/Debian
sudo systemctl status clamd@scan     # Fedora
sudo systemctl status clamd          # Arch

# Start the daemon
sudo systemctl start clamav-daemon   # Ubuntu/Debian
sudo systemctl start clamd@scan      # Fedora
sudo systemctl start clamd           # Arch
```

### Version compatibility

**Symptoms**: Unexpected behavior or parsing errors

**Solution**: Ensure you're using a supported ClamAV version (0.103+)

```bash
clamscan --version
```

If your version is too old, update ClamAV:

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade clamav

# Fedora
sudo dnf upgrade clamav

# Arch Linux
sudo pacman -Syu clamav
```

---

## Flatpak-Specific Issues

### Host ClamAV not accessible

**Symptoms**:
- Error message "ClamAV is not installed"
- Error message "clamscan command not found"
- ClamUI can't detect ClamAV despite it being installed

**Cause**: ClamUI Flatpak runs in a sandbox and needs ClamAV installed on the **host system** (not inside Flatpak)

**Solution**: Install ClamAV on your host OS (outside Flatpak)

```bash
# Install on your host OS (outside Flatpak)
sudo apt install clamav  # Ubuntu/Debian
sudo dnf install clamav  # Fedora
sudo pacman -S clamav    # Arch
```

**How it works**: ClamUI uses `flatpak-spawn --host` to access host ClamAV binaries. This allows the sandboxed Flatpak app to use the ClamAV installation on your host system.

**Verify it works**:
```bash
# Test that ClamAV is accessible from the host
flatpak run --command=sh com.github.rooki.ClamUI -c "flatpak-spawn --host clamscan --version"
```

### Permission denied when scanning files

**Symptoms**:
- "Permission denied" when scanning directories
- "Cannot read" error messages
- Files/folders not appearing in scan results
- Quarantine operations fail

**Cause**: Flatpak sandbox restricts filesystem access by default

**Solution**: Grant Flatpak access to the directories you want to scan

```bash
# Grant read-only access to a specific directory
flatpak override --user --filesystem=/path/to/directory:ro com.github.rooki.ClamUI

# Grant full access (needed for quarantine operations)
flatpak override --user --filesystem=/path/to/directory com.github.rooki.ClamUI
```

**Common directories to grant access**:

```bash
# Home directory (usually already granted)
flatpak override --user --filesystem=home com.github.rooki.ClamUI

# External drives and USB devices
flatpak override --user --filesystem=/media com.github.rooki.ClamUI
flatpak override --user --filesystem=/mnt com.github.rooki.ClamUI
flatpak override --user --filesystem=/run/media com.github.rooki.ClamUI

# Additional common locations
flatpak override --user --filesystem=/var com.github.rooki.ClamUI  # For system scans
flatpak override --user --filesystem=/opt com.github.rooki.ClamUI  # For installed apps
```

**Note**: Read-only access (`:ro`) is sufficient for scanning, but quarantine operations require full write access.

### Granting additional filesystem access

**Symptoms**: Can't scan files outside of allowed directories

**Solution**: View and modify Flatpak permissions

**Command line method**:

```bash
# View current permissions
flatpak info --show-permissions com.github.rooki.ClamUI

# Grant access to a specific directory
flatpak override --user --filesystem=/path/to/directory com.github.rooki.ClamUI

# Grant access to all files (use with caution - reduces sandbox security)
flatpak override --user --filesystem=host com.github.rooki.ClamUI

# Remove a specific permission
flatpak override --user --nofilesystem=/path/to/directory com.github.rooki.ClamUI

# Reset permissions to default
flatpak override --user --reset com.github.rooki.ClamUI
```

**GUI method (Flatseal)**:

For easier permission management, install Flatseal:

```bash
flatpak install flathub com.github.tchx84.Flatseal
```

Then use Flatseal to:
1. Find "ClamUI" in the application list
2. Scroll to "Filesystem" section
3. Toggle access for specific directories
4. Click the "+" button to add custom paths

### D-Bus and portal permission issues

**Symptoms**:
- Notifications not appearing
- File picker dialogs not working
- "Open with file manager" button doesn't work
- Desktop integration features fail

**Cause**: Missing D-Bus or portal permissions

**Solution 1**: Ensure D-Bus permissions are set

```bash
# Verify D-Bus access
flatpak info --show-permissions com.github.rooki.ClamUI | grep -E 'talk-name|system-talk-name'

# Expected permissions should include:
# - org.freedesktop.Notifications (for notifications)
# - org.freedesktop.portal.* (for file picker and desktop integration)
```

**Solution 2**: Fix missing permissions

If D-Bus permissions are missing, reinstall the Flatpak:

```bash
flatpak uninstall com.github.rooki.ClamUI
flatpak install flathub com.github.rooki.ClamUI
```

**Solution 3**: Grant portal access manually (if needed)

```bash
# Grant portal access
flatpak override --user --talk-name=org.freedesktop.Notifications com.github.rooki.ClamUI
flatpak override --user --talk-name=org.freedesktop.portal.Desktop com.github.rooki.ClamUI
flatpak override --user --talk-name=org.freedesktop.portal.FileChooser com.github.rooki.ClamUI
```

**Troubleshooting notifications**:

If notifications still don't work:

1. Check that your desktop environment supports notifications
2. Verify notification daemon is running:
   ```bash
   ps aux | grep notification
   ```
3. Test notifications from the Flatpak:
   ```bash
   flatpak run --command=sh com.github.rooki.ClamUI -c \
     "notify-send 'Test' 'This is a test notification'"
   ```

---

## System Tray Icon Issues

### Tray icon not appearing

**Symptoms**: ClamUI runs but no tray icon is visible in the system tray

**Possible causes and solutions**:

1. **AppIndicator library missing** - See [AppIndicator library missing](#appindicator-library-missing)
2. **GNOME Shell missing extension** - See [GNOME Shell tray support](#gnome-shell-tray-support)
3. **Desktop environment doesn't support tray** - See [Desktop environment compatibility](#desktop-environment-compatibility)
4. **Tray disabled in settings** - Open ClamUI Preferences → General and enable "Show tray icon"
5. **Flatpak-specific issues** - See [Flatpak tray icon issues](#flatpak-tray-icon-issues)

**Quick diagnostic**:

```bash
# Check if AppIndicator library is installed
dpkg -l | grep ayatana  # Ubuntu/Debian
rpm -qa | grep ayatana  # Fedora

# Run ClamUI from terminal to see error messages
clamui  # or: flatpak run com.github.rooki.ClamUI
```

Look for error messages like:
- `"System tray indicator unavailable: Missing library"`
- `"AppIndicator library not found"`
- `"GTK version conflict"`

### AppIndicator library missing

**Symptoms**:
- Warning in logs: `"AppIndicator library not found"`
- Error message: `"Missing library: No module named 'gi.repository.AyatanaAppIndicator3'"`
- Tray icon doesn't appear on any desktop environment

**Cause**: The AyatanaAppIndicator3 library is not installed on your system

**Solution**: Install the AyatanaAppIndicator library

```bash
# Ubuntu/Debian
sudo apt install gir1.2-ayatanaappindicator3-0.1

# Fedora
sudo dnf install libayatana-appindicator-gtk3

# Arch Linux
sudo pacman -S libayatana-appindicator

# openSUSE
sudo zypper install typelib-1_0-AyatanaAppIndicator3-0_1
```

**Verify installation**:

```bash
# Check if library is available
python3 -c "from gi.repository import AyatanaAppIndicator3; print('AppIndicator available')"
```

**After installation**: Restart ClamUI for changes to take effect.

### GNOME Shell tray support

**Symptoms**:
- AppIndicator library installed but tray icon still not visible on GNOME
- Works on other desktop environments (KDE, XFCE) but not GNOME
- GNOME Shell version 3.38+ or GNOME 40+

**Cause**: GNOME Shell removed native tray icon support and requires an extension

**Solution**: Install the AppIndicator Support extension

**Method 1: Via GNOME Extensions website** (recommended)

1. Visit [GNOME Extensions: AppIndicator Support](https://extensions.gnome.org/extension/615/appindicator-support/)
2. Click the ON/OFF toggle to install
3. If prompted, install the browser extension first
4. Enable the extension in GNOME Extensions app
5. Restart ClamUI

**Method 2: Via package manager**

```bash
# Ubuntu/Debian
sudo apt install gnome-shell-extension-appindicator

# Fedora
sudo dnf install gnome-shell-extension-appindicator

# After installation, enable the extension
gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com
```

**Method 3: Via Extension Manager app**

1. Install Extension Manager: `flatpak install flathub com.mattjakeman.ExtensionManager`
2. Search for "AppIndicator and KStatusNotifierItem Support"
3. Install and enable
4. Restart GNOME Shell: Press `Alt+F2`, type `r`, press Enter

**Verify extension is active**:

```bash
gnome-extensions list --enabled | grep appindicator
```

### Desktop environment compatibility

**Symptoms**: Tray icon works on some desktop environments but not others

**Desktop-specific solutions**:

**KDE Plasma**:
- Tray icons should work natively with AppIndicator installed
- If icon doesn't appear, right-click the system tray area → Configure System Tray → Entries → Enable "ClamUI"

**XFCE**:
- Install the XFCE Panel Plugin: `sudo apt install xfce4-indicator-plugin`
- Add "Indicator Plugin" to your panel: Right-click panel → Panel → Add New Items → Indicator Plugin
- Restart ClamUI

**Cinnamon**:
- Tray icons should work natively with AppIndicator installed
- If icon doesn't appear, ensure "System Tray" applet is added to your panel
- Applets → System Tray → Enable

**MATE**:
- Install indicator support: `sudo apt install mate-indicator-applet`
- Add to panel: Right-click panel → Add to Panel → Indicator Applet
- Restart ClamUI

**LXQt**:
- Install StatusNotifier plugin: `sudo apt install lxqt-panel-plugin-statusnotifier`
- Add to panel: Right-click panel → Manage Widgets → StatusNotifier

**Budgie**:
- Tray icons should work natively with AppIndicator installed
- Check Budgie Settings → Raven → Show System Tray

### Flatpak tray icon issues

**Symptoms**:
- Tray icon doesn't appear when using Flatpak version
- Works with native installation but not Flatpak
- Error: `"Failed to start tray service subprocess"`

**Cause**: Flatpak sandbox restrictions or missing host libraries

**Solution 1: Install AppIndicator on host system**

The Flatpak version requires AppIndicator library on the **host system** (not inside Flatpak):

```bash
# Install on your host OS (outside Flatpak)
sudo apt install gir1.2-ayatanaappindicator3-0.1  # Ubuntu/Debian
sudo dnf install libayatana-appindicator-gtk3     # Fedora
sudo pacman -S libayatana-appindicator             # Arch
```

**Solution 2: Grant D-Bus permissions**

Ensure the Flatpak has tray icon permissions:

```bash
# View current permissions
flatpak info --show-permissions com.github.rooki.ClamUI

# Grant StatusNotifier permissions (if missing)
flatpak override --user --talk-name=org.kde.StatusNotifierWatcher com.github.rooki.ClamUI
```

**Solution 3: Enable XDG Desktop Portal**

Some desktop environments need the desktop portal for tray support:

```bash
# Install the portal for your desktop environment
sudo apt install xdg-desktop-portal-gtk   # GNOME/GTK-based
sudo apt install xdg-desktop-portal-kde   # KDE
```

**Verify tray service is running**:

```bash
# Check if tray subprocess starts
flatpak run com.github.rooki.ClamUI
# Look for messages like: "Starting tray service" or "Tray service is ready"
```

### Tray icon status not updating

**Symptoms**:
- Tray icon appears but doesn't change color/icon during scans
- Icon stuck on one status (protected, scanning, etc.)
- Progress percentage not showing during scans

**Possible causes and solutions**:

**Cause 1: Icon theme doesn't have required symbolic icons**

```bash
# Test if theme has required icons
gtk-update-icon-cache -f /usr/share/icons/YOUR_THEME_NAME/

# Switch to a standard icon theme temporarily
gsettings set org.gnome.desktop.interface icon-theme 'Adwaita'
```

**Cause 2: Tray service subprocess crashed**

```bash
# Check for errors in logs
journalctl --user -u clamui --since today | grep -i tray

# Look for:
# - "Tray service subprocess started"
# - "Tray service is ready"
# - Any error messages
```

**Cause 3: Communication issue between main app and tray subprocess**

```bash
# Run with debug logging
CLAMUI_DEBUG=1 clamui

# Or for Flatpak:
flatpak run --env=CLAMUI_DEBUG=1 com.github.rooki.ClamUI
```

**Solution**: Try these steps in order:

1. **Restart ClamUI** - Kills and restarts the tray subprocess
2. **Disable and re-enable tray icon**:
   - Open ClamUI Preferences → General
   - Uncheck "Show tray icon"
   - Click Apply
   - Check "Show tray icon" again
3. **Clear cached icon theme**:
   ```bash
   rm -rf ~/.cache/icon-cache
   gtk-update-icon-cache
   ```
4. **Check for multiple instances**:
   ```bash
   # Kill any existing ClamUI processes
   pkill -9 clamui
   # Start fresh
   clamui
   ```

### Tray icon shows wrong icon or generic fallback

**Symptoms**:
- Tray icon shows generic icons instead of ClamUI-specific icons
- All statuses show the same icon
- Icon doesn't match the application state

**Cause**: Icon theme missing symbolic icons or ClamUI icon not installed

**Solution**:

```bash
# Install complete icon theme
sudo apt install adwaita-icon-theme-full

# Update icon cache
sudo gtk-update-icon-cache -f /usr/share/icons/Adwaita/
sudo gtk-update-icon-cache -f /usr/share/icons/hicolor/

# For user-installed icons
gtk-update-icon-cache ~/.local/share/icons/hicolor/
```

**Verify ClamUI icon is installed**:

```bash
# Check for ClamUI icon
ls -la /usr/share/icons/hicolor/scalable/apps/com.github.rooki.clamui.*
ls -la ~/.local/share/icons/hicolor/scalable/apps/com.github.rooki.clamui.*
```

---

## File Manager Context Menu Issues

### Context menu not appearing

**Symptoms**:
- "Scan with ClamUI" option missing when right-clicking files/folders
- Context menu shows other applications but not ClamUI
- Desktop file exists but integration doesn't work

**Cause**: Missing desktop file, outdated desktop database, or file manager-specific configuration issues

**Diagnostic steps**:

```bash
# 1. Check if desktop file exists
ls -la ~/.local/share/applications/com.github.rooki.clamui.desktop

# 2. Verify desktop file content
cat ~/.local/share/applications/com.github.rooki.clamui.desktop | grep -E "Actions|ScanFile"

# 3. Check if clamui command is accessible
which clamui
clamui --version

# 4. Check your file manager
ps aux | grep -E "nautilus|dolphin|nemo|thunar|pcmanfm"
```

**File manager-specific solutions**:

**Nautilus (GNOME Files)**:

Context menu integration works via Desktop Actions in the `.desktop` file.

```bash
# Verify desktop file exists
ls ~/.local/share/applications/com.github.rooki.clamui.desktop

# Check if it has the Actions entry
grep "Actions=ScanFile" ~/.local/share/applications/com.github.rooki.clamui.desktop

# Update desktop database
update-desktop-database ~/.local/share/applications

# Clear cache and restart Nautilus
rm -rf ~/.cache/nautilus
nautilus -q
sleep 2
nautilus &
```

**Dolphin (KDE)**:

Dolphin uses the same Desktop Actions mechanism as Nautilus.

```bash
# Update desktop database
update-desktop-database ~/.local/share/applications

# Restart Dolphin completely
killall dolphin
kbuildsycoca5  # KDE 5
# or
kbuildsycoca6  # KDE 6

# Start Dolphin
dolphin &
```

**Nemo (Cinnamon)**:

Nemo supports both Desktop Actions and Nemo-specific action files.

```bash
# Check for Nemo action file (preferred method)
ls ~/.local/share/nemo/actions/com.github.rooki.clamui.nemo_action

# If missing, check desktop file fallback
ls ~/.local/share/applications/com.github.rooki.clamui.desktop

# Update desktop database
update-desktop-database ~/.local/share/applications

# Restart Nemo
nemo -q
sleep 2
nemo &
```

**Thunar (XFCE)**:

Thunar uses custom actions in its settings.

```bash
# Verify desktop file exists
ls ~/.local/share/applications/com.github.rooki.clamui.desktop

# Update desktop database
update-desktop-database ~/.local/share/applications

# Restart Thunar
thunar -q
sleep 1
thunar &
```

**PCManFM (LXDE/LXQt)**:

PCManFM uses Desktop Actions like Nautilus.

```bash
# Update desktop database
update-desktop-database ~/.local/share/applications

# Restart PCManFM
pkill pcmanfm
pcmanfm &
```

**Caja (MATE)**:

Caja uses Desktop Actions similar to Nautilus.

```bash
# Update desktop database
update-desktop-database ~/.local/share/applications

# Restart Caja
caja -q
sleep 1
caja &
```

### Desktop file permissions

**Symptoms**:
- Desktop file exists but context menu doesn't appear
- File manager shows errors when trying to use context menu
- ClamUI doesn't launch when clicked from context menu

**Cause**: Desktop file lacks executable permissions or has incorrect ownership

**Solution**: Fix permissions and ownership

```bash
# Check current permissions
ls -la ~/.local/share/applications/com.github.rooki.clamui.desktop

# The file should be readable (doesn't need to be executable for context menu)
# Set correct permissions
chmod 644 ~/.local/share/applications/com.github.rooki.clamui.desktop

# Verify ownership
stat ~/.local/share/applications/com.github.rooki.clamui.desktop

# Ensure it's owned by your user
sudo chown $USER:$USER ~/.local/share/applications/com.github.rooki.clamui.desktop
```

**Validate desktop file content**:

```bash
# Check for syntax errors
desktop-file-validate ~/.local/share/applications/com.github.rooki.clamui.desktop

# Verify it has required entries
grep -E "^Type=|^Name=|^Exec=|^Actions=|^\[Desktop Action" ~/.local/share/applications/com.github.rooki.clamui.desktop
```

**Expected output** should include:
```
Type=Application
Name=ClamUI
Exec=clamui
Actions=ScanFile
[Desktop Action ScanFile]
```

### Manual context menu installation

**Symptoms**:
- Fresh installation but context menu not working
- Flatpak installation missing context menu integration
- Desktop file not installed automatically

**Solution**: Manually install desktop file and related components

**For native installation**:

```bash
# Navigate to ClamUI source directory
cd /path/to/clamui

# Copy desktop file
mkdir -p ~/.local/share/applications
cp com.github.rooki.clamui.desktop ~/.local/share/applications/

# Copy Nemo action file (for Cinnamon users)
mkdir -p ~/.local/share/nemo/actions
cp com.github.rooki.clamui.nemo_action ~/.local/share/nemo/actions/

# Copy application icons
mkdir -p ~/.local/share/icons/hicolor/scalable/apps
cp icons/com.github.rooki.clamui.svg ~/.local/share/icons/hicolor/scalable/apps/

# Update desktop database
update-desktop-database ~/.local/share/applications

# Update icon cache
gtk-update-icon-cache -f ~/.local/share/icons/hicolor/

# Verify installation
ls -la ~/.local/share/applications/com.github.rooki.clamui.desktop
```

**For Flatpak installation**:

```bash
# Export desktop file from Flatpak
mkdir -p ~/.local/share/applications
flatpak run --command=sh com.github.rooki.ClamUI -c \
  "cat /app/share/applications/com.github.rooki.clamui.desktop" \
  > ~/.local/share/applications/com.github.rooki.clamui.desktop

# For Nemo users, export Nemo action
mkdir -p ~/.local/share/nemo/actions
flatpak run --command=sh com.github.rooki.ClamUI -c \
  "cat /app/share/nemo/actions/com.github.rooki.clamui.nemo_action" \
  > ~/.local/share/nemo/actions/com.github.rooki.clamui.nemo_action

# Update desktop file to use Flatpak command
sed -i 's|Exec=clamui|Exec=flatpak run com.github.rooki.ClamUI|g' \
  ~/.local/share/applications/com.github.rooki.clamui.desktop

# Also update the Desktop Action
sed -i 's|Exec=clamui %F|Exec=flatpak run com.github.rooki.ClamUI %F|g' \
  ~/.local/share/applications/com.github.rooki.clamui.desktop

# Update desktop database
update-desktop-database ~/.local/share/applications

# Verify the Exec line uses flatpak
grep "^Exec=" ~/.local/share/applications/com.github.rooki.clamui.desktop
```

**Verify integration works**:

```bash
# Test launching ClamUI from command line
clamui  # Native installation
# or
flatpak run com.github.rooki.ClamUI  # Flatpak

# Test with a file argument (simulates context menu click)
clamui ~/Documents  # Native
# or
flatpak run com.github.rooki.ClamUI ~/Documents  # Flatpak
```

### File manager refresh requirements

**Symptoms**:
- Desktop file installed correctly but context menu still not appearing
- Context menu appears but shows outdated information
- Changes to desktop file not reflected in file manager
- ClamUI launches with wrong arguments when clicked from context menu

**Cause**: File managers cache desktop file information and don't detect changes immediately

**Solution**: Force refresh of desktop integration

**Method 1: Update desktop database and restart file manager**

```bash
# Update desktop database
update-desktop-database ~/.local/share/applications

# Restart your file manager (choose one)
nautilus -q && nautilus &          # GNOME Files
killall dolphin && dolphin &       # KDE Dolphin
nemo -q && nemo &                  # Cinnamon Nemo
thunar -q && thunar &               # XFCE Thunar
caja -q && caja &                   # MATE Caja
pkill pcmanfm && pcmanfm &          # LXDE PCManFM
```

**Method 2: Restart desktop session** (most reliable)

```bash
# Log out and log back in
# or restart GNOME Shell (GNOME only)
# Press Alt+F2, type 'r', press Enter

# For GNOME on X11 (not Wayland)
killall -3 gnome-shell

# For KDE Plasma
kquitapp5 plasmashell && kstart5 plasmashell  # KDE 5
# or
kquitapp6 plasmashell && kstart plasmashell   # KDE 6
```

**Method 3: Clear file manager cache**

```bash
# Nautilus cache
rm -rf ~/.cache/nautilus
nautilus -q

# Dolphin cache
rm -rf ~/.cache/dolphin
rm -rf ~/.local/share/kservices5/ServiceMenus/*.desktop  # Old KDE cache
killall dolphin

# Nemo cache
rm -rf ~/.cache/nemo
nemo -q

# General desktop cache
rm -rf ~/.cache/desktop-file-*
```

**Method 4: Force desktop database rebuild**

```bash
# Remove and rebuild desktop database cache
rm ~/.local/share/applications/mimeinfo.cache
update-desktop-database ~/.local/share/applications

# Update MIME type associations
update-mime-database ~/.local/share/mime

# Update icon cache
gtk-update-icon-cache -f ~/.local/share/icons/hicolor/
```

**Verification checklist**:

After refreshing, verify the integration works:

```bash
# 1. Check desktop database was updated
ls -la ~/.local/share/applications/mimeinfo.cache

# 2. Verify desktop file is recognized
grep -r "clamui" ~/.local/share/applications/

# 3. Check if file manager process is running
ps aux | grep -E "nautilus|dolphin|nemo" | grep -v grep

# 4. Test context menu
# Right-click a file or folder in your file manager
# Look for "Scan with ClamUI" option
```

**Troubleshooting specific issues**:

**Issue**: Context menu appears on some files but not others

**Solution**: Check file type associations and Desktop Action configuration

```bash
# Verify the Desktop Action accepts all file types
grep -A 3 "\[Desktop Action ScanFile\]" ~/.local/share/applications/com.github.rooki.clamui.desktop

# Should show:
# [Desktop Action ScanFile]
# Name=Scan with ClamUI
# Exec=clamui %F
```

**Issue**: Context menu appears but clicking does nothing

**Solution**: Check ClamUI executable path and test manually

```bash
# Verify clamui is in PATH
which clamui

# Test execution with a file argument
clamui ~/Documents

# Check for errors in logs
journalctl --user -u clamui --since "1 minute ago"
```

**Issue**: Context menu works for native install but not Flatpak

**Solution**: Ensure desktop file uses correct Flatpak command

```bash
# Check Exec line in desktop file
grep "Exec=" ~/.local/share/applications/com.github.rooki.clamui.desktop

# Should contain:
# Exec=flatpak run com.github.rooki.ClamUI
# Exec=flatpak run com.github.rooki.ClamUI %F  (in Desktop Action section)

# If not, update it
sed -i 's|Exec=clamui|Exec=flatpak run com.github.rooki.ClamUI|g' \
  ~/.local/share/applications/com.github.rooki.clamui.desktop
update-desktop-database ~/.local/share/applications
```

---

## Scanning Errors

### Permission denied errors

**Symptoms**:
- Error message: `"Permission denied: Cannot read /path/to/file"`
- Error message: `"Permission denied: Cannot access directory contents of /path/to/directory"`
- Files or directories skipped during scan
- Scan completes but shows fewer files than expected
- Quarantine operations fail with permission errors

**Cause**: Insufficient permissions to access files, directories, or in Flatpak sandbox restrictions

**Diagnostic steps**:

```bash
# Check file/directory permissions
ls -la /path/to/file

# Check if you can read the file
cat /path/to/file > /dev/null
# If this fails with "Permission denied", you don't have read access

# For directories, check if you can list contents
ls /path/to/directory
# If this fails, you don't have execute permission on the directory

# Check ownership
stat /path/to/file
```

**Solution 1: Fix file permissions** (for native installation)

```bash
# Check current permissions
ls -la /path/to/file

# If the file is owned by another user, you may need to:
# Option A: Run scan with sudo (use with caution)
sudo -E clamui

# Option B: Change file ownership (if you own the parent directory)
sudo chown $USER:$USER /path/to/file

# Option C: Add read permissions for your user
sudo chmod +r /path/to/file  # For files
sudo chmod +rx /path/to/directory  # For directories
```

**Solution 2: Grant Flatpak filesystem access** (for Flatpak installation)

If you're using the Flatpak version, the sandbox restricts file access by default.

```bash
# Grant read-only access to a specific directory
flatpak override --user --filesystem=/path/to/directory:ro com.github.rooki.ClamUI

# Grant full access (needed for quarantine operations)
flatpak override --user --filesystem=/path/to/directory com.github.rooki.ClamUI

# Common directories that may need access
flatpak override --user --filesystem=/media com.github.rooki.ClamUI  # External drives
flatpak override --user --filesystem=/mnt com.github.rooki.ClamUI    # Mount points
flatpak override --user --filesystem=/var com.github.rooki.ClamUI    # System files

# Verify permissions were granted
flatpak info --show-permissions com.github.rooki.ClamUI | grep filesystem
```

**Solution 3: Check SELinux/AppArmor restrictions** (advanced)

```bash
# Check if SELinux is enforcing
getenforce

# View SELinux denials
sudo ausearch -m avc -ts recent | grep clamui

# Check AppArmor status
sudo aa-status | grep clamui

# Temporarily disable SELinux for testing (re-enable after!)
sudo setenforce 0
# Re-enable with: sudo setenforce 1
```

**Solution 4: Verify file isn't locked by another process**

```bash
# Check if file is open by another process
lsof /path/to/file

# Check for file locks
flock /path/to/file echo "Testing lock"
```

**Verification**:

```bash
# Test if ClamUI can now access the path
# For native installation:
clamscan /path/to/file

# For Flatpak:
flatpak run com.github.rooki.ClamUI /path/to/file

# Check ClamUI logs for permission errors
journalctl --user -u clamui --since "5 minutes ago" | grep -i "permission denied"
```

### Path validation failures

**Symptoms**:
- Error message: `"No path specified"`
- Error message: `"Path does not exist: /path/to/scan"`
- Error message: `"Invalid path format"`
- Error message: `"Error resolving path"`
- Scan button disabled or grayed out
- Path field shows red border or warning icon

**Cause**: Invalid, non-existent, or malformed filesystem paths

**Diagnostic steps**:

```bash
# Verify the path exists
ls -la /path/to/scan

# Check if path is valid
test -e /path/to/scan && echo "Path exists" || echo "Path does not exist"

# For files, verify it's readable
test -r /path/to/scan && echo "Path is readable" || echo "Path is not readable"

# Check for special characters or encoding issues
echo "/path/to/scan" | od -c  # Shows character encoding

# Verify path doesn't contain null bytes
echo "/path/to/scan" | grep -q $'\0' && echo "Contains null bytes!" || echo "No null bytes"
```

**Common causes and solutions**:

**Cause 1: Path doesn't exist**

```bash
# Verify path exists
ls -la /path/to/scan

# Check for typos in the path
# Correct: /home/user/Documents
# Wrong: /home/user/Documens (typo)
# Wrong: /Home/user/Documents (case mismatch on case-sensitive filesystems)

# If path should exist, check parent directory
ls -la /home/user/
```

**Cause 2: Relative path instead of absolute path**

ClamUI expects absolute paths starting with `/` or `~`.

```bash
# Wrong: Documents/file.txt (relative path)
# Correct: /home/user/Documents/file.txt (absolute path)
# Correct: ~/Documents/file.txt (home directory shorthand)

# Convert relative to absolute
realpath Documents/file.txt
# Output: /home/user/Documents/file.txt
```

**Cause 3: Special characters in path**

```bash
# Paths with spaces need to be valid
# Correct: /home/user/My Documents/file.txt
# The UI should handle this automatically

# Check for hidden characters
cat -A <<< "/path/to/scan"
# Look for: ^M (carriage return), ^@ (null), or other control characters
```

**Cause 4: Broken symbolic link**

```bash
# Check if path is a broken symlink
file /path/to/scan
# If output says "broken symbolic link", the target doesn't exist

# Find what the symlink points to
readlink -f /path/to/scan

# If the symlink is broken, either:
# 1. Fix the symlink target
# 2. Remove the broken symlink: rm /path/to/scan
# 3. Scan the intended target directly
```

**Cause 5: Network or remote paths**

```bash
# ClamUI cannot scan remote/network paths directly
# Wrong: smb://server/share/file.txt
# Wrong: ftp://server/path/file.txt

# Mount the network share first, then scan the mount point
# Example for SMB/CIFS:
sudo mount -t cifs //server/share /mnt/network -o username=user
clamui /mnt/network
```

**Verification**:

```bash
# Test path validation manually
test -e /path/to/scan && test -r /path/to/scan && echo "Path is valid for scanning" || echo "Path is invalid"

# Try scanning with clamscan directly
clamscan /path/to/scan

# Expected output if path is valid:
# -------  SCAN SUMMARY -------
# Known viruses: ...
# Engine version: ...
```

### Symlink security warnings

**Symptoms**:
- Warning message: `"Path is a symlink: /path/link -> /path/target"`
- Error message: `"Symlink target does not exist: /path/link -> /path/target"`
- Error message: `"Symlink escapes to protected directory: /path/link -> /system/path"`
- Scan proceeds but shows warning in logs
- Some symlinked directories skipped during scan

**Cause**: ClamUI validates symlinks for security to prevent directory traversal attacks and scanning system files unintentionally

**Understanding symlink security checks**:

ClamUI performs three levels of symlink validation:

1. **Target existence**: Verifies the symlink points to an existing file/directory
2. **Escape detection**: Prevents symlinks from escaping user directories to system directories
3. **Circular reference prevention**: Avoids infinite loops from circular symlinks

**Protected system directories** that symlinks cannot escape to from user directories:
- `/etc` - System configuration
- `/var` - Variable data
- `/usr` - System binaries
- `/bin`, `/sbin` - Essential commands
- `/lib`, `/lib64` - System libraries
- `/boot` - Boot files
- `/root` - Root user's home

**Diagnostic steps**:

```bash
# Check if path is a symlink
ls -la /path/to/check
# Look for: lrwxrwxrwx ... /path/to/check -> /path/to/target

# Find where the symlink points
readlink -f /path/to/check

# Check if target exists
test -e "$(readlink -f /path/to/check)" && echo "Target exists" || echo "Target missing"

# Find all symlinks in a directory
find /path/to/directory -type l

# Find broken symlinks
find /path/to/directory -type l ! -exec test -e {} \; -print
```

**Solution 1: Scan the actual target instead of the symlink**

```bash
# Instead of scanning the symlink:
# /home/user/link -> /home/user/Documents

# Scan the actual target:
clamui /home/user/Documents

# Or resolve the symlink first:
clamui "$(readlink -f /home/user/link)"
```

**Solution 2: Fix broken symlinks**

```bash
# Check what the symlink points to
ls -la /path/to/symlink

# If target doesn't exist, either:
# 1. Create the missing target
mkdir -p /path/to/target

# 2. Update the symlink to point to the correct location
ln -sf /correct/path /path/to/symlink

# 3. Remove the broken symlink
rm /path/to/symlink
```

**Solution 3: Understanding escape warnings**

If you see: `"Symlink escapes to protected directory"`

```bash
# Example scenario:
# /home/user/etc_link -> /etc
# This is flagged as potentially dangerous

# This is EXPECTED BEHAVIOR to protect you from:
# - Accidentally scanning system files
# - Potential privilege escalation attacks
# - Malware using symlinks for directory traversal

# If you genuinely need to scan system directories:
# 1. Use the actual path, not the symlink
sudo clamui /etc

# 2. Or grant explicit permission (Flatpak)
flatpak override --user --filesystem=/etc:ro com.github.rooki.ClamUI
```

**Solution 4: Scan with follow-symlinks disabled**

ClamAV follows symlinks by default. To disable:

```bash
# For command-line scanning:
clamscan --no-follow-symlinks /path/to/scan

# Note: ClamUI doesn't currently expose this option in the UI
# Follow symlinks is generally safe for user directories
```

**Common symlink scenarios**:

**Scenario 1: Symlink to another user directory** (✓ Safe)
```bash
/home/user/shared -> /home/user/Documents/Shared
# This is safe and will be scanned normally
```

**Scenario 2: Symlink to external drive** (✓ Safe)
```bash
/home/user/usb -> /media/user/USB_DRIVE
# Safe, but ensure Flatpak has access to /media
```

**Scenario 3: Symlink escaping to /etc** (⚠ Blocked)
```bash
/home/user/etc_link -> /etc
# Blocked for security - scan /etc directly with appropriate permissions
```

**Scenario 4: Circular symlink** (⚠ Detected)
```bash
/home/user/a -> /home/user/b
/home/user/b -> /home/user/a
# ClamAV detects circular references and skips
```

**Verification**:

```bash
# Test symlink validation
readlink -f /path/to/symlink && echo "Symlink is valid"

# Scan the symlink target directly
clamscan "$(readlink -f /path/to/symlink)"

# Check scan logs for symlink warnings
journalctl --user -u clamui --since "10 minutes ago" | grep -i symlink
```

### Daemon connection failures

**Symptoms**:
- Error message: `"Failed to connect to clamd"`
- Error message: `"Daemon not responding"`
- Error message: `"Could not find clamd socket"`
- Error message: `"Connection to clamd timed out"`
- Error message: `"clamdscan executable not found"`
- Scan falls back to slower clamscan mode
- Backend shows as "unavailable" in preferences

**Cause**: ClamAV daemon (clamd) not running, not installed, socket permission issues, or socket path misconfiguration

**Diagnostic steps**:

```bash
# Check if clamd daemon is installed
which clamdscan
dpkg -l | grep clamav-daemon  # Ubuntu/Debian
rpm -qa | grep clamd          # Fedora

# Check if daemon is running
sudo systemctl status clamav-daemon  # Ubuntu/Debian
sudo systemctl status clamd@scan     # Fedora
sudo systemctl status clamd          # Arch

# Test daemon connection with ping
clamdscan --ping 3
# Expected output: "PONG"

# Check socket file exists
ls -la /var/run/clamav/clamd.ctl      # Ubuntu/Debian
ls -la /run/clamav/clamd.ctl          # Alternative location
ls -la /var/run/clamd.scan/clamd.sock # Fedora

# Check socket permissions
stat /var/run/clamav/clamd.ctl

# View daemon logs for errors
sudo journalctl -u clamav-daemon --since "10 minutes ago"
sudo journalctl -u clamd@scan --since "10 minutes ago"

# Check clamd configuration
sudo cat /etc/clamav/clamd.conf | grep -E "LocalSocket|TCPSocket"
```

**Solution 1: Install and start the daemon**

**Ubuntu/Debian:**
```bash
# Install daemon package
sudo apt install clamav-daemon

# Enable and start the service
sudo systemctl enable clamav-daemon
sudo systemctl start clamav-daemon

# Verify it's running
sudo systemctl status clamav-daemon

# Test connection
clamdscan --ping 3
```

**Fedora:**
```bash
# Install clamd
sudo dnf install clamd

# Enable and start the service
sudo systemctl enable clamd@scan
sudo systemctl start clamd@scan

# Verify it's running
sudo systemctl status clamd@scan

# Test connection
clamdscan --ping 3
```

**Arch Linux:**
```bash
# Install ClamAV (includes daemon)
sudo pacman -S clamav

# Enable and start the service
sudo systemctl enable clamd
sudo systemctl start clamd

# Verify it's running
sudo systemctl status clamd

# Test connection
clamdscan --ping 3
```

**Solution 2: Fix daemon startup issues**

If daemon fails to start:

```bash
# View detailed error messages
sudo journalctl -u clamav-daemon -n 50 --no-pager

# Common issue: Database not found
# Error: "Database initialization error: Can't find file"
# Solution: Update virus database first
sudo freshclam
# Then restart daemon
sudo systemctl restart clamav-daemon

# Common issue: Port/socket already in use
# Check what's using the socket
sudo lsof /var/run/clamav/clamd.ctl
# Kill the conflicting process or change socket path in /etc/clamav/clamd.conf

# Common issue: Permission denied on database directory
sudo chown -R clamav:clamav /var/lib/clamav
sudo systemctl restart clamav-daemon
```

**Solution 3: Socket permission issues**

```bash
# Check socket permissions
ls -la /var/run/clamav/clamd.ctl

# Socket should be accessible by clamav group
# srwxrwxr-x 1 clamav clamav ... /var/run/clamav/clamd.ctl

# Add your user to clamav group (for native installation)
sudo usermod -aG clamav $USER

# Log out and log back in for group membership to take effect
# Verify group membership
groups | grep clamav

# If still having issues, check socket directory permissions
sudo chmod 755 /var/run/clamav
```

**Solution 4: Flatpak-specific daemon connection**

For Flatpak installations, the daemon must be running on the **host system**:

```bash
# Install daemon on host OS (not inside Flatpak)
sudo apt install clamav-daemon  # Ubuntu/Debian
sudo dnf install clamd          # Fedora

# Start daemon on host
sudo systemctl start clamav-daemon

# Test from Flatpak
flatpak run --command=sh com.github.rooki.ClamUI -c \
  "flatpak-spawn --host clamdscan --ping 3"

# Expected output: "PONG"
```

**Solution 5: Switch to clamscan backend**

If you can't get the daemon working, use direct scanning instead:

```bash
# Open ClamUI
# Go to: Preferences → General → Scan Backend
# Select: "Direct scan (clamscan)"
# Click: Apply

# Verify backend change
# The scan will now use clamscan instead of clamdscan
# Note: Scans will be slower but don't require the daemon
```

**Solution 6: Verify clamd configuration**

```bash
# Check daemon configuration file
sudo cat /etc/clamav/clamd.conf

# Important settings:
# LocalSocket /var/run/clamav/clamd.ctl  # Socket path
# TCPSocket 3310                          # Or TCP port if using network
# LocalSocketMode 666                     # Socket permissions

# If you changed the config, restart daemon
sudo systemctl restart clamav-daemon

# Test with verbose output
clamdscan --version
```

**Verification**:

```bash
# Test daemon is responding
clamdscan --ping 3
# Expected: "PONG"

# Test a simple scan via daemon
echo "test" > /tmp/test.txt
clamdscan /tmp/test.txt
# Expected: "Infected files: 0"

# Verify ClamUI can connect
# Open ClamUI → Preferences
# Check that "Daemon (clamdscan)" backend shows as available

# Check ClamUI logs
journalctl --user -u clamui --since "5 minutes ago" | grep -i daemon
```

### Scan timeout issues

**Symptoms**:
- Scan freezes or hangs on large files
- Error message: `"Scan timed out"`
- Progress bar stops moving for extended periods
- ClamUI becomes unresponsive during scan
- Scan aborts with timeout error on archives or large files
- System resource usage spikes during scan

**Cause**: Large files, slow I/O, insufficient timeout limits, or resource constraints

**Diagnostic steps**:

```bash
# Check file size that's timing out
ls -lh /path/to/large/file
# Files > 1GB can take several minutes

# Check system resources during scan
htop
# Look for high CPU or I/O wait

# Monitor scan in real-time
clamscan -v /path/to/large/file
# Watch for files taking excessive time

# Check disk I/O
iostat -x 1
# High %util indicates I/O bottleneck

# Test scan with time measurement
time clamscan /path/to/large/file
```

**Solution 1: Use daemon mode for faster scanning**

The daemon keeps the virus database in memory, significantly improving scan speed:

```bash
# Install and start daemon (if not already)
sudo apt install clamav-daemon
sudo systemctl enable --now clamav-daemon

# Configure ClamUI to use daemon
# Preferences → Scan Backend → "Daemon (clamdscan)" or "Auto"

# Verify daemon is being used
# The scan should be 3-10x faster for large files
```

**Solution 2: Increase clamd timeout limits**

If using daemon mode and still timing out:

```bash
# Edit clamd configuration
sudo nano /etc/clamav/clamd.conf

# Increase timeout values (in milliseconds):
ReadTimeout 300000        # Default: 120000 (2 minutes) → 300000 (5 minutes)
CommandReadTimeout 30000  # Default: 30000 (30 seconds)
SendBufTimeout 500        # Default: 200

# For very large archives:
MaxScanTime 600000        # Maximum time for scanning a file (10 minutes)
MaxScanSize 500M          # Maximum file size to scan

# Save and restart daemon
sudo systemctl restart clamav-daemon

# Verify settings took effect
sudo systemctl status clamav-daemon
```

**Solution 3: Optimize ClamAV scan settings**

```bash
# Edit clamd configuration for better performance
sudo nano /etc/clamav/clamd.conf

# Performance optimizations:
MaxThreads 4              # Use multiple CPU cores (adjust based on your CPU)
MaxQueue 200              # Increase queue size
MaxFileSize 100M          # Skip files larger than this (adjust as needed)
MaxScanSize 500M          # Maximum data to scan per file
StreamMaxLength 100M      # For network scanning

# For archives that timeout:
MaxRecursion 10           # Limit archive nesting depth (default: 16)
MaxFiles 5000             # Maximum files in archive (default: 10000)

# Restart daemon
sudo systemctl restart clamav-daemon
```

**Solution 4: Exclude problematic files/directories**

```bash
# If specific large files always timeout, exclude them

# In ClamUI:
# 1. Create or edit a scan profile
# 2. Add exclusion patterns for:
#    - Large video files: *.mkv, *.mp4, *.avi
#    - Large archives: *.tar.gz, *.zip > 1GB
#    - Virtual machine images: *.vdi, *.vmdk, *.qcow2
#    - Database files: *.db, *.sqlite

# For command-line scanning:
clamscan --exclude="*.mkv" --exclude="*.vdi" /path/to/scan
```

**Solution 5: Scan in smaller batches**

```bash
# Instead of scanning entire directory:
clamui /home/user  # May timeout

# Scan subdirectories separately:
clamui /home/user/Documents
clamui /home/user/Downloads
clamui /home/user/Pictures

# Or use find to scan in batches:
find /home/user -maxdepth 1 -type d -exec clamscan {} \;
```

**Solution 6: Adjust system resource limits**

```bash
# Check current limits
ulimit -a

# Increase file descriptor limit (if scanning many files)
ulimit -n 4096

# For systemd services, edit service file
sudo systemctl edit clamav-daemon

# Add:
[Service]
LimitNOFILE=4096
TimeoutStartSec=300

# Reload systemd and restart
sudo systemctl daemon-reload
sudo systemctl restart clamav-daemon
```

**Solution 7: Check for I/O bottlenecks**

```bash
# Monitor disk I/O during scan
sudo iotop -o
# Look for high disk read rates

# If scanning network drives or slow USB:
# - Copy files locally first
# - Use faster storage
# - Enable disk caching

# For network shares, mount with caching:
sudo mount -t cifs //server/share /mnt/network \
  -o cache=strict,username=user

# For USB drives, check connection:
lsusb -v
# Ensure USB 3.0 devices use USB 3.0 ports
```

**Solution 8: Skip archive scanning for speed**

Archives can take significantly longer to scan:

```bash
# Skip archive scanning (command-line)
clamscan --scan-archive=no /path/to/scan

# Note: This reduces security but improves speed
# Use only if archives are from trusted sources
```

**Workaround: Use scan profiles with conservative settings**

For known slow directories:

```bash
# Create a "Quick Scan" profile in ClamUI with:
# - Excluded patterns: *.mkv, *.avi, *.mp4, *.iso
# - Excluded paths: ~/.cache, ~/.local/share/Trash
# - Smaller target directories

# Create a separate "Deep Scan" profile for thorough scanning:
# - Run manually when time permits
# - Use during off-hours or scheduled overnight
```

**Verification**:

```bash
# Test that timeout limits are effective
time clamdscan /path/to/large/file
# Should complete within configured timeout

# Monitor daemon logs for timeout messages
sudo journalctl -u clamav-daemon -f
# Start a scan and watch for timeout-related entries

# Verify daemon settings
sudo clamconf | grep -E "ReadTimeout|MaxScanTime"

# Test scan performance improvement
# Before (clamscan): time clamscan /path/to/scan
# After (daemon): time clamdscan /path/to/scan
# Daemon should be significantly faster
```

**Performance expectations**:

- **Small files** (< 1MB): Instant to 1 second
- **Medium files** (1-100MB): 1-10 seconds
- **Large files** (100MB-1GB): 10-60 seconds
- **Very large files** (> 1GB): 1-10 minutes
- **Large archives**: Can take 10x longer than uncompressed

**When to expect timeouts** (these are normal):
- Files > 500MB without daemon mode
- Highly compressed archives with many nested files
- Encrypted or password-protected archives
- Scanning over slow network connections
- Virtual machine disk images (multi-GB)

---

## Database Update Issues

### freshclam permission errors

**Symptoms**: "Permission denied" when updating virus database

**Solution**: Run freshclam with appropriate permissions

```bash
# Option 1: Use sudo
sudo freshclam

# Option 2: Configure freshclam to run as your user (advanced)
# Edit /etc/clamav/freshclam.conf
sudo nano /etc/clamav/freshclam.conf
# Set: DatabaseOwner yourusername
```

### Running updates without root

**Symptoms**: Don't have root access but need to update database

**Solution**: Use local database directory

```bash
# Create local database directory
mkdir -p ~/.local/share/clamav

# Update to local directory
freshclam --datadir=$HOME/.local/share/clamav

# Configure ClamUI to use local database (if needed)
# This is usually automatic
```

### Database location issues

**Symptoms**: ClamAV can't find virus database

**Solution**: Verify database location and permissions

```bash
# Common database locations
ls -la /var/lib/clamav/  # Most distributions
ls -la /var/db/clamav/   # Some systems

# Update database
sudo freshclam
```

### Network connectivity problems

**Symptoms**: Database update fails with network errors

**Solution**: Check network and DNS

```bash
# Test connectivity to ClamAV mirrors
ping database.clamav.net

# Update with verbose output
sudo freshclam -v

# Try different mirror (in /etc/clamav/freshclam.conf)
sudo nano /etc/clamav/freshclam.conf
# Add: DatabaseMirror db.us.clamav.net
```

### Outdated database warnings

**Symptoms**: Warning that virus database is outdated

**Solution**: Update the database regularly

```bash
# Manual update
sudo freshclam

# Enable automatic updates (recommended)
sudo systemctl enable --now clamav-freshclam  # Ubuntu/Debian
sudo systemctl enable --now clamav-freshclam.service  # Fedora

# Verify automatic updates are running
sudo systemctl status clamav-freshclam
```

---

## Scheduled Scanning Issues

### Systemd user timers not working

**Symptoms**: Scheduled scans don't run automatically

**Solution**: Check systemd timer status

```bash
# List user timers
systemctl --user list-timers

# Check specific timer
systemctl --user status clamui-scan-*.timer

# View timer logs
journalctl --user -u clamui-scan-*.timer

# Enable linger for scans to run when logged out
loginctl enable-linger $USER
```

### Cron fallback configuration

**Symptoms**: Systemd not available, need cron-based scheduling

**Solution**: Manually configure cron

```bash
# Edit crontab
crontab -e

# Add scheduled scan (example: daily at 2 AM)
0 2 * * * /usr/bin/clamui-scheduled-scan --profile "Full Scan"

# Verify cron entry
crontab -l
```

### Battery detection issues

**Symptoms**: Scans run on battery when configured not to

**Solution**: Check battery detection

```bash
# Verify battery status detection
cat /sys/class/power_supply/BAT*/status

# Check ClamUI battery settings
# Preferences → Scheduled Scans → "Skip scans on battery"
```

### Scheduled scans not running

**Symptoms**: Timer/cron configured but scans don't execute

**Solution**: Debug scheduled scan execution

```bash
# Test manual execution
clamui-scheduled-scan --profile "Quick Scan"

# Check logs
journalctl --user -u clamui-scan-* --since today

# Verify scan profile exists
clamui  # Open app and check Profiles
```

### Verifying scheduled scan logs

**Symptoms**: Want to confirm scans are running

**Solution**: Check scan history

```bash
# View ClamUI scan logs
ls -lh ~/.local/share/clamui/logs/

# View recent log file
cat ~/.local/share/clamui/logs/scan_$(date +%Y%m%d).json

# Check systemd logs
journalctl --user -u clamui-scan-* --since "1 week ago"
```

---

## General Issues

### Application won't start

**Symptoms**: ClamUI fails to launch or crashes immediately

**Solution**: Check dependencies and logs

```bash
# Verify GTK4 and Adwaita are installed
dpkg -l | grep gtk-4  # Ubuntu/Debian
rpm -qa | grep gtk4   # Fedora

sudo apt install gir1.2-gtk-4.0 gir1.2-adw-1  # Ubuntu/Debian
sudo dnf install gtk4 libadwaita  # Fedora

# Run from terminal to see error messages
clamui

# For Flatpak
flatpak run com.github.rooki.ClamUI
```

### UI appears frozen

**Symptoms**: Interface becomes unresponsive

**Solution**: This usually indicates a background operation

1. **During scans**: Large directory scans can take time. Check the progress indicator.
2. **Force quit if necessary**:
   ```bash
   pkill -9 clamui
   ```
3. **Report the issue**: If reproducible, [open an issue](https://github.com/rooki/clamui/issues)

### High CPU or memory usage

**Symptoms**: ClamUI or ClamAV consuming excessive resources

**Solution**: Optimize scan settings

1. **Use daemon mode** for better performance:
   - Preferences → Scan Backend → "Daemon (clamdscan)"

2. **Reduce scan scope**:
   - Use scan profiles to exclude large directories
   - Skip already-scanned files

3. **Limit ClamAV resources**:
   ```bash
   # Edit /etc/clamav/clamd.conf
   sudo nano /etc/clamav/clamd.conf

   # Reduce thread count
   MaxThreads 2

   sudo systemctl restart clamav-daemon
   ```

### Quarantine operations failing

**Symptoms**: Can't quarantine or restore files

**Solution**: Check quarantine directory permissions

```bash
# Verify quarantine directory exists
ls -la ~/.local/share/clamui/quarantine/

# Create if missing
mkdir -p ~/.local/share/clamui/quarantine/

# Check permissions
chmod 700 ~/.local/share/clamui/quarantine/

# Check database
ls -la ~/.local/share/clamui/quarantine.db
```

### Settings not persisting

**Symptoms**: Preferences reset after restarting ClamUI

**Solution**: Check settings file permissions

```bash
# Verify settings directory
ls -la ~/.config/clamui/

# Create if missing
mkdir -p ~/.config/clamui/

# Check settings file
cat ~/.config/clamui/settings.json

# Reset to defaults if corrupted
rm ~/.config/clamui/settings.json
```

---

## Frequently Asked Questions (FAQ)

### What is ClamUI vs ClamAV?

**ClamAV** is the open-source antivirus engine that runs from the command line. **ClamUI** is a graphical user interface (GUI) that makes ClamAV easier to use by providing:

- Point-and-click file selection
- Visual scan results
- Quarantine management
- Scheduled scanning
- Integration with file managers

**ClamUI requires ClamAV to be installed** to function.

### Why is scanning slow?

Scanning speed depends on several factors:

1. **Scan backend**: Daemon mode (`clamdscan`) is faster than direct mode (`clamscan`)
   - Solution: Enable daemon in ClamUI preferences

2. **File size and count**: Large files or directories with many files take longer
   - Solution: Use scan profiles to limit scope

3. **System resources**: CPU, disk speed, and available RAM affect performance
   - Solution: Close other applications during scans

4. **Database loading**: `clamscan` loads the virus database for each scan
   - Solution: Use daemon mode which keeps the database in memory

### How do I enable daemon mode?

Daemon mode provides faster scanning by keeping ClamAV in memory:

1. **Install the daemon**:
   ```bash
   sudo apt install clamav-daemon  # Ubuntu/Debian
   sudo dnf install clamd  # Fedora
   ```

2. **Start the daemon**:
   ```bash
   sudo systemctl enable --now clamav-daemon  # Ubuntu/Debian
   sudo systemctl enable --now clamd@scan  # Fedora
   ```

3. **Configure ClamUI**:
   - Open Preferences
   - Set Scan Backend to "Daemon (clamdscan)" or "Auto"

### What does quarantine do?

Quarantine **isolates potentially harmful files** to prevent them from causing damage:

- **Secure storage**: Files are moved to `~/.local/share/clamui/quarantine/`
- **Metadata tracking**: Original location, hash, and detection info stored in database
- **Safe restoration**: Files can be restored to their original location if needed
- **Permanent deletion**: Quarantined files can be deleted permanently

**Important**: Quarantined files cannot execute or cause harm while in quarantine.

### How do I create custom scan profiles?

Scan profiles let you save scan configurations for different use cases:

1. **Open ClamUI**
2. **Navigate to Profiles** in the sidebar
3. **Click "New Profile"**
4. **Configure**:
   - Name your profile
   - Select target paths to scan
   - Add exclusion patterns (optional)
   - Set scan options
5. **Click "Save"**

**Example profiles**:
- **Quick Scan**: `~/Downloads`, `~/Desktop`
- **Full Scan**: `/home`
- **Custom**: Specific project directories

### What are the system requirements?

**Minimum requirements**:
- **OS**: Linux (any distribution)
- **Python**: 3.10 or higher
- **GTK**: GTK4
- **Adwaita**: libadwaita 1.0+
- **ClamAV**: 0.103 or higher
- **RAM**: 512 MB (2 GB recommended)
- **Disk**: 500 MB for ClamAV database

**Optional**:
- **Tray icon**: AyatanaAppIndicator3 library
- **GNOME**: AppIndicator Support extension
- **Daemon mode**: clamav-daemon package

---

## Getting Help

If you've tried the solutions in this guide and still need help:

### Community Support

1. **GitHub Issues**: [Report a bug or request a feature](https://github.com/rooki/clamui/issues)
2. **Discussions**: [Ask questions and share tips](https://github.com/rooki/clamui/discussions)

### Before Reporting an Issue

Please include:

1. **ClamUI version**: `clamui --version` or check About dialog
2. **Installation method**: Flatpak, .deb, or source
3. **Linux distribution and version**: `lsb_release -a`
4. **ClamAV version**: `clamscan --version`
5. **Error messages**: Copy exact error text or screenshots
6. **Steps to reproduce**: What you did before the error occurred

### Useful Debug Commands

```bash
# Check ClamUI version
clamui --version

# Check ClamAV version
clamscan --version

# Test ClamAV directly
clamscan --version && echo "ClamAV is working"

# Check GTK version
pkg-config --modversion gtk4

# View application logs
journalctl --user -u clamui --since today

# For Flatpak
flatpak run com.github.rooki.ClamUI --verbose
```

---

## See Also

- [README.md](../README.md) - Project overview and features
- [INSTALL.md](./INSTALL.md) - Installation instructions for all platforms
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development setup and contributing guidelines
- [ClamAV Documentation](https://docs.clamav.net/) - Official ClamAV documentation
- [GTK4 Documentation](https://docs.gtk.org/gtk4/) - GTK4 API reference
