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

ClamUI uses `freshclam` to update the ClamAV virus definition database. The updater module (`src/core/updater.py`) handles automatic privilege escalation via `pkexec` and provides detailed error reporting.

### freshclam permission errors

**Symptoms:**
- Error message: "Authentication cancelled. Database update requires administrator privileges."
- Error message: "Authorization failed. You are not authorized to update the database."
- Error message: "Permission denied. You may need elevated privileges to update the database."
- Exit codes 126 (authentication cancelled) or 127 (not authorized) from pkexec
- Update button disabled or update fails immediately

**Diagnostic Steps:**

1. **Verify freshclam is installed:**
```bash
which freshclam
freshclam --version
```

Expected output:
```
ClamAV 1.0.0/26700/Thu Jan  2 08:30:02 2024
```

2. **Check database directory permissions:**
```bash
# Ubuntu/Debian/Fedora
ls -la /var/lib/clamav/

# Expected: owned by clamav:clamav or root:root
drwxr-xr-x 2 clamav clamav 4096 Jan  2 12:00 /var/lib/clamav/
-rw-r--r-- 1 clamav clamav  123M Jan  2 12:00 daily.cvd
-rw-r--r-- 1 clamav clamav   56M Jan  2 12:00 main.cvd
```

3. **Test pkexec authentication:**
```bash
pkexec freshclam --version
# Should prompt for password and display version
```

**Solutions:**

**Solution 1: Use polkit authentication (recommended)**

ClamUI automatically uses `pkexec` for privilege escalation. When prompted:
1. Enter your user password
2. Ensure your user is in the `sudo` or `wheel` group

Verify group membership:
```bash
groups
# Should include 'sudo' (Ubuntu/Debian) or 'wheel' (Fedora/Arch)
```

Add user to sudo group if needed:
```bash
# Ubuntu/Debian
sudo usermod -aG sudo $USER

# Fedora/Arch
sudo usermod -aG wheel $USER

# Log out and back in for changes to take effect
```

**Solution 2: Fix polkit configuration**

If authentication fails despite correct password:

```bash
# Check PolicyKit rules
pkaction --action-id org.freedesktop.policykit.exec --verbose

# For Flatpak installations, ensure host PolicyKit is accessible
flatpak override --user --talk-name=org.freedesktop.PolicyKit1 com.github.rooki.ClamUI
```

**Solution 3: Configure manual freshclam with sudo (fallback)**

If pkexec doesn't work, update manually:
```bash
sudo freshclam
```

Then configure automatic updates (see [Outdated database warnings](#outdated-database-warnings)).

**Solution 4: Run ClamUI from terminal to see detailed errors**

```bash
# Native installation
clamui

# Flatpak installation
flatpak run com.github.rooki.ClamUI

# Watch for error messages in terminal output like:
# "pkexec error: [details]"
# "freshclam: ERROR: [specific error]"
```

**Flatpak-Specific Considerations:**

Flatpak uses `flatpak-spawn --host` to run freshclam on the host system:

```bash
# Verify host freshclam is accessible
flatpak-spawn --host freshclam --version

# If this fails, freshclam is not installed on the host
# Install ClamAV on the host system (not inside Flatpak)
```

---

### Running updates without root

**Symptoms:**
- Don't have administrator privileges
- Cannot use sudo or pkexec
- Need to update database for personal use only
- Error: "Permission denied" when updating to system location

**Solution: Use a local user database directory**

**Step 1: Create local database directory**

```bash
mkdir -p ~/.local/share/clamav
```

**Step 2: Update to local directory**

```bash
freshclam --datadir=$HOME/.local/share/clamav --config-file=/dev/null

# With verbose output to see progress
freshclam --datadir=$HOME/.local/share/clamav --config-file=/dev/null --verbose
```

Expected output:
```
ClamAV update process started at Thu Jan  2 12:00:00 2024
Downloading main.cvd [100%]
main.cvd updated (version: 62, sigs: 6647427)
Downloading daily.cvd [100%]
daily.cvd updated (version: 27154, sigs: 2044356)
Database updated (8691783 signatures) from database.clamav.net
```

**Step 3: Configure clamscan to use local database**

When scanning with clamscan directly, specify the database directory:
```bash
clamscan --database=$HOME/.local/share/clamav /path/to/scan
```

**Step 4: Verify local database**

```bash
ls -lh ~/.local/share/clamav/
# Should show main.cvd, daily.cvd, and bytecode.cvd
```

**ClamUI Automatic Detection:**

ClamUI automatically detects database locations in this order:
1. `/var/lib/clamav/` (system default)
2. `/var/db/clamav/` (alternative system location)
3. `~/.local/share/clamav/` (user location)

If you've created a local database, ClamUI should detect and use it automatically.

**Creating a local freshclam configuration:**

For regular updates without root, create a user freshclam configuration:

```bash
# Create config directory
mkdir -p ~/.config/clamav

# Create freshclam configuration
cat > ~/.config/clamav/freshclam.conf <<EOF
DatabaseDirectory $HOME/.local/share/clamav
UpdateLogFile $HOME/.local/share/clamav/freshclam.log
DatabaseMirror database.clamav.net
LogVerbose yes
EOF

# Update using your config
freshclam --config-file=$HOME/.config/clamav/freshclam.conf
```

**Automate local updates with cron:**

```bash
# Add to crontab (update daily at 3 AM)
crontab -e

# Add this line:
0 3 * * * /usr/bin/freshclam --config-file=$HOME/.config/clamav/freshclam.conf --quiet
```

**Limitations:**
- Local databases are per-user (not system-wide)
- Must manually update (ClamUI update button won't work without privileges)
- Clamd daemon typically requires system database location

---

### Database location issues

**Symptoms:**
- Error: "Can't open/parse the config file"
- Error: "Database initialization error"
- ClamAV can't find virus database
- Warning: "Virus database date/version is older than 7 days"
- Scans fail with "no database found" error

**Diagnostic Steps:**

1. **Check common database locations:**

```bash
# Ubuntu/Debian/Fedora (most common)
ls -lh /var/lib/clamav/

# Alternative location (some BSD systems, Arch Linux)
ls -lh /var/db/clamav/

# User local database
ls -lh ~/.local/share/clamav/

# Expected files:
# main.cvd (or main.cld)     - Main virus database (~100-200MB)
# daily.cvd (or daily.cld)   - Daily updates (~50-150MB)
# bytecode.cvd (or bytecode.cld) - Bytecode signatures (~1-10MB)
```

2. **Check ClamAV configuration:**

```bash
# Ubuntu/Debian
grep "^DatabaseDirectory" /etc/clamav/clamd.conf
grep "^DatabaseDirectory" /etc/clamav/freshclam.conf

# Fedora
grep "^DatabaseDirectory" /etc/clamd.d/scan.conf
grep "^DatabaseDirectory" /etc/freshclam.conf

# Expected output:
DatabaseDirectory /var/lib/clamav
```

3. **Verify database file integrity:**

```bash
# Check if database files are complete and not corrupted
cd /var/lib/clamav  # or your database directory
file *.cvd *.cld 2>/dev/null

# Expected output for .cvd files:
daily.cvd: ClamAV virus database
main.cvd: ClamAV virus database
```

4. **Test clamscan with explicit database path:**

```bash
# Test if clamscan can load the database
clamscan --database=/var/lib/clamav /tmp/testfile

# Should output:
# Loading:     3/3 signatures loaded.
```

**Solutions:**

**Solution 1: Update the database to correct location**

```bash
# Update to system location (requires root)
sudo freshclam

# Update to user location
mkdir -p ~/.local/share/clamav
freshclam --datadir=$HOME/.local/share/clamav --config-file=/dev/null

# Verify database files exist
ls -lh /var/lib/clamav/*.cvd /var/lib/clamav/*.cld 2>/dev/null
```

**Solution 2: Fix database directory permissions**

```bash
# Check current permissions
ls -la /var/lib/clamav/

# Fix ownership (Ubuntu/Debian)
sudo chown -R clamav:clamav /var/lib/clamav/
sudo chmod 755 /var/lib/clamav/
sudo chmod 644 /var/lib/clamav/*.cvd /var/lib/clamav/*.cld 2>/dev/null

# Fix ownership (Fedora - some versions use different user)
sudo chown -R clamscan:clamscan /var/lib/clamav/
sudo chmod 755 /var/lib/clamav/
```

**Solution 3: Recreate database directory**

If the directory is missing or severely corrupted:

```bash
# Backup any existing database
sudo mkdir -p /var/lib/clamav.backup
sudo mv /var/lib/clamav/* /var/lib/clamav.backup/ 2>/dev/null

# Recreate directory
sudo mkdir -p /var/lib/clamav
sudo chown clamav:clamav /var/lib/clamav
sudo chmod 755 /var/lib/clamav

# Download fresh database
sudo freshclam
```

**Solution 4: Configure ClamAV to use custom database location**

If you need to use a non-standard location:

```bash
# Edit clamd configuration
sudo nano /etc/clamav/clamd.conf  # Ubuntu/Debian
sudo nano /etc/clamd.d/scan.conf   # Fedora

# Set custom database directory
DatabaseDirectory /custom/path/to/database

# Also update freshclam configuration
sudo nano /etc/clamav/freshclam.conf  # Ubuntu/Debian
sudo nano /etc/freshclam.conf          # Fedora

# Set same database directory
DatabaseDirectory /custom/path/to/database

# Ensure directory exists and has correct permissions
sudo mkdir -p /custom/path/to/database
sudo chown clamav:clamav /custom/path/to/database
sudo chmod 755 /custom/path/to/database

# Update database
sudo freshclam

# Restart clamd daemon
sudo systemctl restart clamav-daemon  # Ubuntu/Debian
sudo systemctl restart clamd@scan     # Fedora
```

**Solution 5: Handle "Database is locked" error**

**Symptoms:** Error message "Database is locked. Another freshclam instance may be running."

This error appears when:
- Another freshclam process is already updating
- A stale lock file exists from a crashed update
- The automatic freshclam daemon is running

```bash
# Check for running freshclam processes
ps aux | grep freshclam

# If found, wait for it to complete or kill it
sudo killall freshclam

# Check for lock file
ls -la /var/lib/clamav/*.lck 2>/dev/null

# Remove stale lock file (only if no freshclam is running)
sudo rm /var/lib/clamav/freshclam.lck

# Try update again
sudo freshclam
```

**Verification:**

After fixing database location issues:

```bash
# Verify database is loaded
clamscan --version

# Should show:
ClamAV 1.0.0/26700/Thu Jan  2 08:30:02 2024

# Test scan with EICAR test file
curl -o /tmp/eicar.com https://secure.eicar.org/eicar.com.txt
clamscan /tmp/eicar.com

# Should detect:
/tmp/eicar.com: Win.Test.EICAR_HDB-1 FOUND
```

---

### Network connectivity problems

**Symptoms:**
- Error: "Connection error. Please check your network connection."
- Error: "DNS resolution failed. Please check your network settings."
- Error: "Can't connect to database.clamav.net"
- Error: "Timeout while downloading"
- Update hangs or takes extremely long
- Error messages containing "can't connect", "connection refused", "host not found"

**Diagnostic Steps:**

1. **Test basic network connectivity:**

```bash
# Ping ClamAV database server
ping -c 4 database.clamav.net

# Expected output:
64 bytes from database.clamav.net (104.16.218.84): icmp_seq=1 ttl=54 time=15.2 ms
```

2. **Test DNS resolution:**

```bash
# Resolve ClamAV mirror addresses
nslookup database.clamav.net
dig database.clamav.net

# Should return multiple IP addresses
```

3. **Test HTTP/HTTPS connectivity:**

```bash
# Test download from ClamAV CDN
curl -I https://database.clamav.net/daily.cvd

# Expected: HTTP 200 OK or 302 redirect
HTTP/2 200
content-type: application/octet-stream
```

4. **Check firewall and proxy settings:**

```bash
# Check if firewall is blocking outbound connections
sudo iptables -L -n | grep -i clamav
sudo ufw status

# Check proxy environment variables
echo $http_proxy
echo $https_proxy
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

**Solutions:**

**Solution 1: Verify network connection**

```bash
# Test general internet connectivity
ping -c 4 8.8.8.8  # Google DNS
ping -c 4 1.1.1.1  # Cloudflare DNS

# If general connectivity fails, troubleshoot network first
# Check NetworkManager or systemd-networkd status
systemctl status NetworkManager
nmcli device status
```

**Solution 2: Fix DNS resolution issues**

```bash
# Test DNS resolution
nslookup database.clamav.net

# If DNS fails, try different DNS servers
# Temporarily use Google DNS
sudo nano /etc/resolv.conf
# Add:
nameserver 8.8.8.8
nameserver 8.8.4.4

# Or use systemd-resolved
sudo systemctl restart systemd-resolved
resolvectl status

# Permanent DNS configuration (Ubuntu/Debian)
sudo nano /etc/systemd/resolved.conf
# Set:
[Resolve]
DNS=8.8.8.8 8.8.4.4
FallbackDNS=1.1.1.1

sudo systemctl restart systemd-resolved
```

**Solution 3: Configure proxy settings for freshclam**

If you're behind a corporate proxy or firewall:

```bash
# Edit freshclam configuration
sudo nano /etc/clamav/freshclam.conf  # Ubuntu/Debian
sudo nano /etc/freshclam.conf          # Fedora

# Add proxy settings (remove leading # to uncomment)
HTTPProxyServer proxy.example.com
HTTPProxyPort 8080

# If proxy requires authentication
HTTPProxyUsername your_username
HTTPProxyPassword your_password

# For HTTPS proxy
# HTTPSProxyServer proxy.example.com
# HTTPSProxyPort 8080

# Save and test
sudo freshclam --verbose
```

**Solution 4: Use alternative database mirrors**

If the default mirror is unreachable, configure alternative mirrors:

```bash
# Edit freshclam configuration
sudo nano /etc/clamav/freshclam.conf  # Ubuntu/Debian
sudo nano /etc/freshclam.conf          # Fedora

# Comment out default mirror and add alternatives
# DatabaseMirror database.clamav.net

# Add specific regional mirrors (choose closest to your location)
DatabaseMirror db.us.clamav.net        # United States
DatabaseMirror db.eu.clamav.net        # Europe
DatabaseMirror db.jp.clamav.net        # Japan
DatabaseMirror db.au.clamav.net        # Australia

# Or use CloudFlare mirror
DatabaseMirror database.clamav.net

# Save and update
sudo freshclam --verbose
```

**Solution 5: Bypass firewall restrictions**

If corporate firewall blocks ClamAV updates:

```bash
# Allow outbound HTTPS to ClamAV servers
sudo ufw allow out to database.clamav.net
sudo ufw allow out 443/tcp

# For iptables
sudo iptables -A OUTPUT -p tcp -d database.clamav.net --dport 443 -j ACCEPT

# Check if SELinux is blocking (Fedora/RHEL)
sudo ausearch -m avc -ts recent | grep freshclam

# If blocked by SELinux, allow HTTP/HTTPS for freshclam
sudo setsebool -P antivirus_can_scan_system 1
sudo setsebool -P antivirus_use_jit 1
```

**Solution 6: Download database manually**

If automated updates consistently fail, download manually:

```bash
# Create temporary directory
mkdir -p /tmp/clamav-db
cd /tmp/clamav-db

# Download database files manually
wget https://database.clamav.net/main.cvd
wget https://database.clamav.net/daily.cvd
wget https://database.clamav.net/bytecode.cvd

# Or use curl
curl -O https://database.clamav.net/main.cvd
curl -O https://database.clamav.net/daily.cvd
curl -O https://database.clamav.net/bytecode.cvd

# Verify downloads (should be 100-200MB for main, 50-150MB for daily)
ls -lh

# Move to ClamAV database directory
sudo mv *.cvd /var/lib/clamav/
sudo chown clamav:clamav /var/lib/clamav/*.cvd
sudo chmod 644 /var/lib/clamav/*.cvd

# Verify database loads
clamscan --version
```

**Solution 7: Increase timeout for slow connections**

For slow or unreliable networks:

```bash
# Edit freshclam configuration
sudo nano /etc/clamav/freshclam.conf  # Ubuntu/Debian
sudo nano /etc/freshclam.conf          # Fedora

# Increase timeout values (default is 30 seconds)
ConnectTimeout 120
ReceiveTimeout 120

# Set maximum download attempts
MaxAttempts 5

# Save and update
sudo freshclam --verbose
```

**Solution 8: Check system clock**

Incorrect system time can cause SSL certificate validation failures:

```bash
# Check current system time
date

# Sync with NTP servers
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd

# Or use ntpdate
sudo ntpdate pool.ntp.org

# Verify time is correct
timedatectl status
```

**Flatpak-Specific Network Issues:**

```bash
# Verify Flatpak has network access
flatpak info --show-permissions com.github.rooki.ClamUI | grep network

# Should show:
# network

# If missing, grant network permission
flatpak override --user --share=network com.github.rooki.ClamUI

# Test network from within Flatpak
flatpak run --command=sh com.github.rooki.ClamUI
# Inside Flatpak shell:
ping -c 4 database.clamav.net
```

**Verification:**

```bash
# Test update with verbose output
sudo freshclam --verbose

# Expected successful output:
ClamAV update process started at Thu Jan  2 12:00:00 2024
Downloading main.cvd [100%]
main.cvd updated (version: 62, sigs: 6647427)
Downloading daily.cvd [100%]
daily.cvd updated (version: 27154, sigs: 2044356)
Database updated (8691783 signatures) from database.clamav.net

# Check database age
clamscan --version
# Should show recent date (within 1-2 days)
ClamAV 1.0.0/26700/Thu Jan  2 08:30:02 2024
                    ^^^^^^^^ Recent date
```

---

### Outdated database warnings

**Symptoms:**
- Warning: "Your virus database is outdated"
- Warning: "Virus database date/version is older than 7 days"
- ClamUI displays "Last updated: X days ago" with warning icon
- Update view shows red/orange status indicator
- Scans may miss new malware variants

**Why database updates matter:**

New malware variants emerge daily. ClamAV releases database updates multiple times per day. An outdated database (>7 days old) significantly reduces detection effectiveness.

**Recommended update frequency:**
- **Minimum:** Weekly
- **Recommended:** Daily
- **Optimal:** Multiple times per day (automated)

**Solution 1: Enable automatic database updates (recommended)**

The best approach is to enable the ClamAV freshclam daemon for automatic updates.

**Ubuntu/Debian:**

```bash
# Enable and start freshclam daemon
sudo systemctl enable clamav-freshclam
sudo systemctl start clamav-freshclam

# Verify it's running
sudo systemctl status clamav-freshclam

# Expected output:
● clamav-freshclam.service - ClamAV virus database updater
     Loaded: loaded (/lib/systemd/system/clamav-freshclam.service; enabled)
     Active: active (running) since Thu 2024-01-02 12:00:00 UTC
```

**Fedora/RHEL/CentOS:**

```bash
# Enable and start freshclam daemon
sudo systemctl enable clamav-freshclam.service
sudo systemctl start clamav-freshclam.service

# Verify it's running
sudo systemctl status clamav-freshclam.service
```

**Arch Linux:**

```bash
# Enable and start freshclam timer (uses systemd timer, not daemon)
sudo systemctl enable clamav-freshclam.timer
sudo systemctl start clamav-freshclam.timer

# Verify timer is active
sudo systemctl list-timers | grep clamav

# Expected output:
Thu 2024-01-02 13:00:00 UTC  1h left  clamav-freshclam.timer
```

**Configuration for automatic updates:**

```bash
# Edit freshclam configuration
sudo nano /etc/clamav/freshclam.conf  # Ubuntu/Debian
sudo nano /etc/freshclam.conf          # Fedora

# Ensure these settings are configured:
Checks 24                    # Check for updates 24 times per day (hourly)
DatabaseMirror database.clamav.net
LogVerbose yes
UpdateLogFile /var/log/clamav/freshclam.log

# Comment out this line if present (prevents daemon mode)
# Example

# Save and restart service
sudo systemctl restart clamav-freshclam
```

**Solution 2: Manual update via ClamUI**

1. Open ClamUI
2. Navigate to "Database Update" view (database icon in sidebar)
3. Click "Update Database" button
4. Enter your password when prompted by pkexec
5. Wait for update to complete (typically 1-5 minutes)

**Solution 3: Manual update via command line**

```bash
# Update database immediately
sudo freshclam

# Update with verbose output (shows progress)
sudo freshclam --verbose

# Expected output:
ClamAV update process started at Thu Jan  2 12:00:00 2024
Downloading main.cvd [100%]
main.cvd updated (version: 62, sigs: 6647427)
Downloading daily.cvd [100%]
daily.cvd updated (version: 27154, sigs: 2044356)
Database updated (8691783 signatures) from database.clamav.net
```

**Solution 4: Schedule updates with cron (if systemd not available)**

If systemd is not available or you prefer cron:

```bash
# Edit system crontab
sudo crontab -e

# Add freshclam to run every 4 hours
0 */4 * * * /usr/bin/freshclam --quiet

# Or run once daily at 3 AM
0 3 * * * /usr/bin/freshclam --quiet

# Or run twice daily (3 AM and 3 PM)
0 3,15 * * * /usr/bin/freshclam --quiet

# Verify cron job
sudo crontab -l
```

**Solution 5: Force immediate update**

If update is stuck or database is very old:

```bash
# Stop freshclam daemon (if running)
sudo systemctl stop clamav-freshclam

# Remove lock file (if exists)
sudo rm -f /var/lib/clamav/freshclam.lck

# Force update
sudo freshclam --verbose

# Restart daemon
sudo systemctl start clamav-freshclam

# Verify database is current
clamscan --version
```

**Monitoring database freshness:**

```bash
# Check database version and date
clamscan --version

# Output shows database date:
ClamAV 1.0.0/26700/Thu Jan  2 08:30:02 2024
#                   ^^^^^^^^ Database version
#                           ^^^^^^^^^^^^^^^^^^^ Last update date

# Check when database was last modified
ls -lh /var/lib/clamav/*.cvd /var/lib/clamav/*.cld

# Check freshclam log for recent updates
sudo tail -n 50 /var/log/clamav/freshclam.log
```

**Troubleshooting automatic updates not running:**

```bash
# Check systemd timer/service status
sudo systemctl status clamav-freshclam

# If failed, check journalctl for errors
sudo journalctl -u clamav-freshclam -n 50

# Common issues and fixes:

# Issue: Service disabled
sudo systemctl enable clamav-freshclam

# Issue: Configuration error
sudo freshclam --verbose  # Will show config errors

# Issue: Lock file preventing updates
sudo rm -f /var/lib/clamav/freshclam.lck
sudo systemctl restart clamav-freshclam

# Issue: "Example" line not commented in config
sudo nano /etc/clamav/freshclam.conf
# Find and comment out (or remove):
# Example
# Should be:
# Example  (commented out)

sudo systemctl restart clamav-freshclam
```

**Verification:**

After setting up automatic updates:

```bash
# Wait 1-2 hours, then check database date
clamscan --version

# Check freshclam log for successful updates
sudo tail -n 20 /var/log/clamav/freshclam.log

# Expected in log:
Database updated (8691783 signatures) from database.clamav.net

# Verify daemon is running
sudo systemctl is-active clamav-freshclam
# Should output: active

# Check next scheduled update (for timer-based systems)
sudo systemctl list-timers | grep clamav
```

**Best practices:**
1. Enable automatic updates (systemd service or timer)
2. Monitor logs periodically to ensure updates succeed
3. Keep update logs for troubleshooting: `/var/log/clamav/freshclam.log`
4. Update manually before important scans if automated updates haven't run recently
5. Set up monitoring/alerts if running ClamAV in production environments

---

## Scheduled Scanning Issues

ClamUI supports scheduled scanning via systemd user timers (preferred) or cron (fallback). This section covers common issues with both scheduling systems.

### Systemd user timers not working

**Symptoms:**
- Scheduled scans don't run automatically at the configured time
- Timer appears in `systemctl --user list-timers` but never triggers
- Error: "Failed to enable timer: Unit file ... not found"
- Service file or timer file missing in `~/.config/systemd/user/`
- Scans only run when logged in (not when system is running but user logged out)

**Diagnostic Steps:**

1. **Check if systemd user session is running:**

```bash
# Verify systemd user session
systemctl --user status

# Expected output should show "Active: active (running)"
# If you see "Failed to connect to bus" or "No such file or directory",
# systemd user session is not available
```

2. **List all user timers:**

```bash
# Show all systemd user timers (including ClamUI)
systemctl --user list-timers --all

# Expected output should include:
# NEXT                          LEFT        LAST  PASSED  UNIT                         ACTIVATES
# Thu 2024-01-04 02:00:00 EST   12h left    -     -       clamui-scheduled-scan.timer  clamui-scheduled-scan.service
```

3. **Check timer status:**

```bash
# Check if timer is active
systemctl --user is-active clamui-scheduled-scan.timer

# Expected output: "active" (if running) or "inactive" (if not)

# Get detailed timer status
systemctl --user status clamui-scheduled-scan.timer

# Expected output shows:
#   Active: active (waiting)
#   Trigger: [next scheduled time]
```

4. **View timer and service files:**

```bash
# Check if files exist
ls -lh ~/.config/systemd/user/clamui-scheduled-scan.*

# Expected files:
# clamui-scheduled-scan.service
# clamui-scheduled-scan.timer

# View timer file contents
cat ~/.config/systemd/user/clamui-scheduled-scan.timer

# View service file contents
cat ~/.config/systemd/user/clamui-scheduled-scan.service
```

5. **Check timer logs for errors:**

```bash
# View timer unit logs
journalctl --user -u clamui-scheduled-scan.timer --since today

# View service unit logs (shows actual scan execution)
journalctl --user -u clamui-scheduled-scan.service --since "3 days ago"

# Look for errors like:
# - "Failed to execute command"
# - "Permission denied"
# - "No such file or directory"
```

**Solutions:**

**Solution 1: Enable user lingering (scans run when logged out)**

By default, systemd user services only run while you're logged in. To allow scheduled scans to run even when you're logged out:

```bash
# Enable lingering for your user
loginctl enable-linger $USER

# Verify linger is enabled
loginctl show-user $USER | grep Linger

# Expected output:
# Linger=yes
```

This allows your systemd user instance to continue running after logout, enabling scheduled scans to execute.

**Solution 2: Reload systemd daemon and restart timer**

If you've manually edited timer/service files or they seem out of sync:

```bash
# Reload systemd user daemon
systemctl --user daemon-reload

# Restart the timer
systemctl --user restart clamui-scheduled-scan.timer

# Verify timer is active
systemctl --user is-active clamui-scheduled-scan.timer

# Check next scheduled run time
systemctl --user list-timers clamui-scheduled-scan.timer
```

**Solution 3: Manually enable the timer**

If the timer exists but isn't enabled:

```bash
# Enable and start the timer
systemctl --user enable --now clamui-scheduled-scan.timer

# Verify it's running
systemctl --user status clamui-scheduled-scan.timer
```

**Solution 4: Recreate timer/service files via ClamUI**

If files are missing or corrupted:

1. Open ClamUI → Preferences → Scheduled Scans
2. Disable scheduled scanning (if enabled)
3. Wait a few seconds
4. Re-enable scheduled scanning with your desired settings
5. ClamUI will recreate the systemd files

Verify the files were created:
```bash
ls -lh ~/.config/systemd/user/clamui-scheduled-scan.*
systemctl --user daemon-reload
systemctl --user status clamui-scheduled-scan.timer
```

**Solution 5: Check clamui-scheduled-scan command is available**

The service file needs to find the `clamui-scheduled-scan` command:

```bash
# Check if command is in PATH
which clamui-scheduled-scan

# Expected output: /usr/bin/clamui-scheduled-scan or /usr/local/bin/clamui-scheduled-scan

# If not found, verify ClamUI installation
pip show clamui  # For pip installation

# For Flatpak, the command should be wrapped via flatpak-spawn
# (ClamUI handles this automatically)
```

If the command is not found, reinstall ClamUI or check your installation method.

**Solution 6: Fix service file permissions**

```bash
# Ensure service/timer files are readable
chmod 644 ~/.config/systemd/user/clamui-scheduled-scan.*

# Reload and restart
systemctl --user daemon-reload
systemctl --user restart clamui-scheduled-scan.timer
```

**Solution 7: Test timer manually**

```bash
# Manually trigger the service (doesn't wait for timer)
systemctl --user start clamui-scheduled-scan.service

# Watch the logs in real-time
journalctl --user -u clamui-scheduled-scan.service -f

# If this works but timer doesn't, check timer's OnCalendar specification:
systemctl --user cat clamui-scheduled-scan.timer | grep OnCalendar
```

**Flatpak-Specific Considerations:**

When using ClamUI as a Flatpak:
- The timer runs on the host system via `flatpak-spawn --host`
- Systemd files are created in the host user directory
- The service executes: `flatpak run --command=clamui-scheduled-scan com.github.rooki.clamui`

Check Flatpak-specific issues:
```bash
# Verify Flatpak can spawn host commands
flatpak-spawn --host systemctl --user status

# Check ClamUI Flatpak is installed
flatpak list | grep clamui
```

---

### Cron fallback configuration

**Symptoms:**
- ClamUI detects "cron" as scheduler backend instead of systemd
- Systemd is not available on your system (minimal installations, containers)
- Manual cron configuration needed
- Cron jobs not executing scheduled scans
- Error: "crontab: command not found"

**Diagnostic Steps:**

1. **Check which scheduler backend ClamUI is using:**

Open ClamUI and check the Preferences → Scheduled Scans section. It will indicate whether systemd or cron is being used.

2. **Verify cron is installed and running:**

```bash
# Check if crontab command exists
which crontab

# Expected output: /usr/bin/crontab

# Check if cron daemon is running
# Ubuntu/Debian:
systemctl status cron

# Fedora/RHEL:
systemctl status crond

# Expected output: Active: active (running)
```

3. **List current crontab entries:**

```bash
# View your crontab
crontab -l

# Look for ClamUI entries marked with:
# ClamUI Scheduled Scan

# If no crontab exists, you'll see:
# "no crontab for [username]"
```

4. **Check cron logs:**

```bash
# Ubuntu/Debian:
grep CRON /var/log/syslog | grep clamui | tail -20

# Fedora/RHEL/Arch:
journalctl -u crond | grep clamui

# Look for execution entries like:
# (username) CMD (/path/to/clamui-scheduled-scan ...)
```

**Solutions:**

**Solution 1: Install cron if missing**

```bash
# Ubuntu/Debian:
sudo apt update
sudo apt install cron

# Fedora/RHEL:
sudo dnf install cronie
sudo systemctl enable --now crond

# Arch Linux:
sudo pacman -S cronie
sudo systemctl enable --now cronie
```

Verify installation:
```bash
crontab -l
# Should show "no crontab" or existing entries (not "command not found")
```

**Solution 2: Configure scheduled scan via ClamUI**

1. Open ClamUI → Preferences → Scheduled Scans
2. Enable scheduled scanning
3. Configure frequency (daily/weekly/monthly) and time
4. Select scan targets
5. Apply settings

ClamUI will automatically create a crontab entry.

Verify the entry was created:
```bash
crontab -l | grep -A 1 "ClamUI Scheduled Scan"

# Expected output (example for daily at 2 AM):
# ClamUI Scheduled Scan
# 0 2 * * * /usr/bin/clamui-scheduled-scan --skip-on-battery --target /home/username
```

**Solution 3: Manually create cron entry**

If ClamUI's automatic cron creation fails, you can create it manually:

```bash
# Edit crontab
crontab -e

# Add entry for daily scan at 2 AM:
# ClamUI Scheduled Scan
0 2 * * * /usr/bin/clamui-scheduled-scan --skip-on-battery --target "$HOME" 2>&1 | logger -t clamui-scan

# Add entry for weekly scan (every Monday at 3 AM):
# ClamUI Scheduled Scan
0 3 * * 1 /usr/bin/clamui-scheduled-scan --target "$HOME/Documents" --auto-quarantine 2>&1 | logger -t clamui-scan

# Add entry for monthly scan (1st of month at 4 AM):
# ClamUI Scheduled Scan
0 4 1 * * /usr/bin/clamui-scheduled-scan --target "$HOME" 2>&1 | logger -t clamui-scan
```

Cron time format: `minute hour day month day_of_week command`
- `0 2 * * *` = Daily at 2:00 AM
- `0 3 * * 1` = Weekly on Monday at 3:00 AM (0=Sunday, 1=Monday, ..., 6=Saturday)
- `0 4 1 * *` = Monthly on the 1st at 4:00 AM
- `0 * * * *` = Hourly at minute 0

**Solution 4: Verify clamui-scheduled-scan command path**

Cron has a limited PATH, so use absolute paths:

```bash
# Find full path to command
which clamui-scheduled-scan

# Common locations:
# /usr/bin/clamui-scheduled-scan (system install)
# /usr/local/bin/clamui-scheduled-scan (local install)
# ~/.local/bin/clamui-scheduled-scan (pip user install)

# Update crontab with absolute path
crontab -e

# Use the full path found above
0 2 * * * /usr/bin/clamui-scheduled-scan --target "$HOME"
```

**Solution 5: Add environment variables to crontab**

Cron runs with minimal environment. Add necessary variables:

```bash
crontab -e

# Add at the top of the crontab:
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOME=/home/yourusername
SHELL=/bin/bash

# ClamUI Scheduled Scan
0 2 * * * /usr/bin/clamui-scheduled-scan --target "$HOME"
```

**Solution 6: Test cron command manually**

```bash
# Run the exact command from your crontab
/usr/bin/clamui-scheduled-scan --target "$HOME" --verbose

# Check for errors in output
# Common issues:
# - "Command not found" → Use absolute path
# - "Permission denied" → Check file permissions
# - "ClamAV not available" → ClamAV not in cron's PATH
```

**Solution 7: Enable cron logging for debugging**

```bash
# Create a crontab entry that logs output
crontab -e

# Redirect output to a log file:
# ClamUI Scheduled Scan
0 2 * * * /usr/bin/clamui-scheduled-scan --target "$HOME" --verbose >> /tmp/clamui-cron.log 2>&1

# Check the log file after scheduled time:
cat /tmp/clamui-cron.log
```

**Cron vs Systemd Trade-offs:**

**Systemd advantages:**
- Better logging via journalctl
- Service dependencies and ordering
- User lingering for logged-out execution
- Randomized delay to avoid resource spikes

**Cron advantages:**
- Available on all systems (including older/minimal installs)
- Simpler configuration (one-line entries)
- Works without systemd user session

**Flatpak with Cron:**

```bash
# Flatpak cron entry example
crontab -e

# Add:
# ClamUI Scheduled Scan
0 2 * * * flatpak run --command=clamui-scheduled-scan com.github.rooki.clamui --target "$HOME" 2>&1 | logger -t clamui-scan
```

---

### Battery detection issues

**Symptoms:**
- Scheduled scans run on battery power even with "Skip scans on battery" enabled
- Scans never run because battery is always detected as "on battery" (even when plugged in)
- Error in logs: "psutil not available" or "Failed to detect battery status"
- Desktop system incorrectly detected as having battery
- Battery status always shows "unknown" or incorrect percentage

**Diagnostic Steps:**

1. **Check if psutil is installed:**

ClamUI uses the `psutil` Python library for battery detection:

```bash
# Check if psutil is available
python3 -c "import psutil; print(f'psutil version: {psutil.__version__}')"

# Expected output:
# psutil version: 5.9.x

# If you see "ModuleNotFoundError: No module named 'psutil'",
# psutil is not installed
```

2. **Test battery detection directly:**

```bash
# Test battery status using Python
python3 -c "
import psutil
battery = psutil.sensors_battery()
if battery is None:
    print('No battery detected (desktop system)')
else:
    print(f'Battery detected:')
    print(f'  Percent: {battery.percent}%')
    print(f'  Plugged in: {battery.power_plugged}')
    print(f'  Time remaining: {battery.secsleft}s')
"

# Expected output for laptop on AC power:
# Battery detected:
#   Percent: 85.0%
#   Plugged in: True
#   Time remaining: -2

# Expected output for desktop:
# No battery detected (desktop system)
```

3. **Check system power supply information:**

```bash
# List power supply devices
ls /sys/class/power_supply/

# Expected output (laptop):
# AC  BAT0

# Expected output (desktop):
# (empty or only AC adapter)

# Check battery status (laptop only)
cat /sys/class/power_supply/BAT*/status 2>/dev/null

# Possible outputs:
# Charging    - Battery charging
# Discharging - Running on battery
# Full        - Battery full, on AC
# Unknown     - Status cannot be determined

# Check AC adapter status
cat /sys/class/power_supply/AC*/online 2>/dev/null

# Output:
# 1 = AC power connected
# 0 = AC power disconnected
```

4. **Check scheduled scan logs for battery skip events:**

```bash
# View recent scheduled scan logs
cat ~/.local/share/clamui/logs/scan_$(date +%Y%m%d).json 2>/dev/null | jq '.[] | select(.summary | contains("battery"))'

# Or check all recent logs:
grep -r "battery" ~/.local/share/clamui/logs/ | tail -10

# Look for entries like:
# "Scheduled scan skipped (on battery power)"
# "Battery level: 45%"
```

5. **Test clamui-scheduled-scan battery detection:**

```bash
# Run scheduled scan manually with battery skip enabled
clamui-scheduled-scan --skip-on-battery --target /tmp --verbose --dry-run

# Expected output if on battery:
# [timestamp] Checking battery status...
# [timestamp] Skipping scan: running on battery power (45%)

# Expected output if on AC:
# [timestamp] Checking battery status...
# [timestamp] Scanning 1 target(s)...
```

**Solutions:**

**Solution 1: Install psutil**

If psutil is not installed, battery detection won't work:

```bash
# Install via pip (if using native installation)
pip install psutil

# Or via distribution package manager
# Ubuntu/Debian:
sudo apt install python3-psutil

# Fedora:
sudo dnf install python3-psutil

# Arch Linux:
sudo pacman -S python-psutil

# Verify installation
python3 -c "import psutil; print(psutil.__version__)"
```

For Flatpak installations, psutil should be bundled. If it's missing:
```bash
# Reinstall ClamUI Flatpak
flatpak update com.github.rooki.clamui
```

**Solution 2: Verify battery detection is working**

After installing psutil, test battery detection:

```bash
# Test battery manager
python3 << 'EOF'
from src.core.battery_manager import BatteryManager

bm = BatteryManager()
status = bm.get_status()

print(f"Has battery: {status.has_battery}")
print(f"Is plugged: {status.is_plugged}")
print(f"Percent: {status.percent}")
print(f"On battery: {bm.is_on_battery()}")
print(f"Should skip scan: {bm.should_skip_scan(skip_on_battery=True)}")
EOF

# Expected output (desktop):
# Has battery: False
# Is plugged: True
# Percent: None
# On battery: False
# Should skip scan: False

# Expected output (laptop on AC):
# Has battery: True
# Is plugged: True
# Percent: 85.0
# On battery: False
# Should skip scan: False

# Expected output (laptop on battery):
# Has battery: True
# Is plugged: False
# Percent: 45.0
# On battery: True
# Should skip scan: True
```

**Solution 3: Disable battery skip if detection is unreliable**

If battery detection is incorrect or unavailable:

1. Open ClamUI → Preferences → Scheduled Scans
2. Disable "Skip scans on battery" option
3. Scans will always run regardless of power status

Or via command line:
```bash
# Run scheduled scan without battery check
clamui-scheduled-scan --target "$HOME"
# (omit --skip-on-battery flag)

# Update crontab/systemd to remove --skip-on-battery
```

**Solution 4: Fix battery status reporting (laptop)**

If battery exists but status is incorrect:

```bash
# Check for ACPI errors in kernel logs
dmesg | grep -i "acpi\|battery" | tail -20

# Look for errors like:
# "ACPI: battery: fail to get battery information"
# "ACPI: battery: [Firmware Bug]"

# Update ACPI/power management packages
# Ubuntu/Debian:
sudo apt update
sudo apt install acpi acpi-support

# Fedora:
sudo dnf install acpi

# Test ACPI battery detection
acpi -b

# Expected output:
# Battery 0: Discharging, 45%, 02:30:00 remaining
```

**Solution 5: Desktop systems (no battery)**

For desktop systems incorrectly detecting a battery:

```bash
# Verify no battery in /sys
ls -la /sys/class/power_supply/

# If phantom battery devices appear, check hardware/BIOS
# Some desktop motherboards report a phantom CMOS battery

# ClamUI should detect no battery and always assume AC power:
python3 -c "
from src.core.battery_manager import BatteryManager
bm = BatteryManager()
print(f'Has battery: {bm.has_battery}')  # Should be False
print(f'Is plugged: {bm.is_plugged}')    # Should be True
"
```

**Solution 6: Force battery check in scheduled scans**

Add explicit battery logging to diagnose issues:

```bash
# Create wrapper script for debugging
cat > ~/debug-clamui-scan.sh << 'EOF'
#!/bin/bash
echo "=== Battery Status Debug ===" >> /tmp/clamui-battery-debug.log
date >> /tmp/clamui-battery-debug.log

# Check /sys battery status
echo "Battery status:" >> /tmp/clamui-battery-debug.log
cat /sys/class/power_supply/BAT*/status 2>/dev/null >> /tmp/clamui-battery-debug.log

# Check AC status
echo "AC online:" >> /tmp/clamui-battery-debug.log
cat /sys/class/power_supply/AC*/online 2>/dev/null >> /tmp/clamui-battery-debug.log

# Run psutil check
python3 -c "
import psutil
battery = psutil.sensors_battery()
print(f'psutil battery: {battery}')
" >> /tmp/clamui-battery-debug.log 2>&1

# Run scheduled scan
/usr/bin/clamui-scheduled-scan --skip-on-battery --target /tmp --verbose >> /tmp/clamui-battery-debug.log 2>&1
EOF

chmod +x ~/debug-clamui-scan.sh

# Run manually
~/debug-clamui-scan.sh

# Check debug log
cat /tmp/clamui-battery-debug.log
```

**Behavior Summary:**

| System Type | has_battery | is_plugged | is_on_battery() | should_skip_scan() |
|-------------|-------------|------------|-----------------|-------------------|
| Desktop | False | True | False | False (never skip) |
| Laptop on AC | True | True | False | False (never skip) |
| Laptop on battery | True | False | True | True (skip if enabled) |
| psutil unavailable | False | True | False | False (assume AC) |

**Default Behavior When Detection Fails:**
- If psutil is not available: Assumes desktop (no battery, always on AC power)
- If battery detection fails: Assumes AC power (scan proceeds)
- **This is safe:** Scans will run unless battery is explicitly detected and user opted to skip

---

### Scheduled scans not running

**Symptoms:**
- Timer/cron is configured but scans never execute
- No log entries for scheduled scans in `~/.local/share/clamui/logs/`
- Systemd timer shows "active (waiting)" but service never runs
- Crontab entry exists but no execution in syslog/journal
- Manual execution of `clamui-scheduled-scan` works, but automated doesn't
- Error in logs: "Could not find clamui-scheduled-scan command"

**Diagnostic Steps:**

1. **Verify scheduler is configured:**

```bash
# For systemd:
systemctl --user list-timers | grep clamui

# Expected output:
# NEXT                         LEFT          LAST                         PASSED       UNIT                         ACTIVATES
# Thu 2024-01-04 02:00:00 EST  8h left       Wed 2024-01-03 02:00:05 EST  16h ago      clamui-scheduled-scan.timer  clamui-scheduled-scan.service

# For cron:
crontab -l | grep -A 1 "ClamUI"

# Expected output:
# # ClamUI Scheduled Scan
# 0 2 * * * /usr/bin/clamui-scheduled-scan --target /home/user
```

2. **Check when the scan last ran:**

```bash
# Systemd - check service last execution
systemctl --user status clamui-scheduled-scan.service

# Look for:
#   Active: inactive (dead) since [timestamp]
#   Main PID: [pid] (code=exited, status=0/SUCCESS)

# Systemd - check timer last trigger
systemctl --user list-timers --all clamui-scheduled-scan.timer

# Cron - check syslog/journal
# Ubuntu/Debian:
grep "clamui-scheduled-scan" /var/log/syslog | tail -10

# Systemd-based systems:
journalctl -t CRON | grep clamui | tail -10
```

3. **Check for execution errors in logs:**

```bash
# Systemd logs
journalctl --user -u clamui-scheduled-scan.service --since "3 days ago"

# Look for errors:
# - "Failed to execute command: No such file or directory"
# - "Permission denied"
# - "ClamAV not available"
# - "Error: No valid scan targets found"

# ClamUI scan logs
ls -lh ~/.local/share/clamui/logs/
# Check if recent scan_YYYYMMDD.json files exist

# View most recent log
ls -t ~/.local/share/clamui/logs/scan_*.json | head -1 | xargs cat | jq '.'
```

4. **Test manual execution:**

```bash
# Run the scheduled scan command manually
clamui-scheduled-scan --target "$HOME/Documents" --verbose

# Expected successful output:
# [timestamp] ClamUI scheduled scan starting...
# [timestamp] Scanning 1 target(s)...
# [timestamp]   - /home/user/Documents
# [timestamp] ClamAV version: 1.0.x
# [timestamp] Scanning: /home/user/Documents
# [timestamp]   Clean (XXX files scanned)
# [timestamp] Scan completed in X.X seconds
# [timestamp] No threats found (XXX files scanned, no threats)

# Common errors to watch for:
# - "ClamAV not available" → clamscan not found
# - "No valid scan targets found" → paths don't exist
# - "psutil not available" → battery detection disabled
```

5. **Verify target paths exist:**

```bash
# Extract target paths from systemd service
systemctl --user cat clamui-scheduled-scan.service | grep ExecStart

# Or from crontab
crontab -l | grep clamui-scheduled-scan

# Check if each target exists
ls -ld /home/user/Documents /home/user/Downloads  # example paths

# If path doesn't exist, scan will fail with:
# "Error: No valid scan targets found"
```

**Solutions:**

**Solution 1: Verify clamui-scheduled-scan is accessible**

```bash
# Check command exists
which clamui-scheduled-scan

# Expected: /usr/bin/clamui-scheduled-scan or /usr/local/bin/clamui-scheduled-scan

# If not found, check installation
pip show clamui

# Reinstall if necessary
pip install --upgrade --force-reinstall clamui
```

**Solution 2: Fix systemd timer/service configuration**

If timer exists but service doesn't run:

```bash
# Check timer file
systemctl --user cat clamui-scheduled-scan.timer

# Ensure it has:
# [Timer]
# OnCalendar=*-*-* 02:00:00  (or your configured time)
# Persistent=true

# Check service file
systemctl --user cat clamui-scheduled-scan.service

# Ensure ExecStart command is correct and uses full path

# Reload and restart
systemctl --user daemon-reload
systemctl --user restart clamui-scheduled-scan.timer
systemctl --user status clamui-scheduled-scan.timer
```

**Solution 3: Enable user lingering (systemd only)**

Scans won't run when logged out unless lingering is enabled:

```bash
# Enable lingering
loginctl enable-linger $USER

# Verify
loginctl show-user $USER | grep Linger
# Should show: Linger=yes

# This allows your systemd user instance to remain running after logout
```

**Solution 4: Fix cron PATH issues**

Cron runs with minimal PATH. Update crontab:

```bash
crontab -e

# Add PATH at the top:
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Use absolute paths in cron entries:
# ClamUI Scheduled Scan
0 2 * * * /usr/bin/clamui-scheduled-scan --target "$HOME/Documents" 2>&1 | logger -t clamui-scan

# Test cron command directly:
/usr/bin/clamui-scheduled-scan --target "$HOME/Documents" --verbose
```

**Solution 5: Check ClamAV is installed and accessible**

The scheduled scan requires ClamAV to be installed:

```bash
# Verify ClamAV installation
clamscan --version

# Expected output:
# ClamAV 1.0.x/...

# If not found:
# Ubuntu/Debian:
sudo apt install clamav

# Fedora:
sudo dnf install clamav clamav-update

# Arch:
sudo pacman -S clamav

# For Flatpak ClamUI, ClamAV must be on host:
flatpak-spawn --host clamscan --version
```

**Solution 6: Validate scan targets**

Ensure paths configured in scheduled scan exist:

```bash
# Open ClamUI → Preferences → Scheduled Scans
# Check "Scan Targets" section

# Verify paths exist:
ls -ld ~/Documents ~/Downloads  # or your configured paths

# If paths don't exist, remove them or create them:
mkdir -p ~/Documents ~/Downloads

# Recreate schedule via ClamUI UI to update paths
```

**Solution 7: Check for conflicting schedule**

Multiple schedules can interfere:

```bash
# Systemd - check for duplicate timers
systemctl --user list-timers --all | grep clamui

# If you see multiple timers, disable extras:
systemctl --user disable --now clamui-scan-old.timer

# Cron - check for duplicate entries
crontab -l | grep -n clamui

# Edit and remove duplicates:
crontab -e
```

**Solution 8: Test timer trigger manually**

```bash
# Manually start the service (bypasses timer)
systemctl --user start clamui-scheduled-scan.service

# Watch logs in real-time
journalctl --user -u clamui-scheduled-scan.service -f

# If manual start works but timer doesn't:
# Check timer's OnCalendar specification
systemctl --user cat clamui-scheduled-scan.timer | grep OnCalendar

# Verify time format is correct:
# Daily:   *-*-* 02:00:00
# Weekly:  Mon *-*-* 03:00:00
# Monthly: *-*-01 04:00:00
```

**Solution 9: Enable verbose logging**

Update service/cron to include `--verbose` flag:

```bash
# Systemd - edit service file manually
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/clamui-scheduled-scan.service

# Add --verbose to ExecStart:
ExecStart=/usr/bin/clamui-scheduled-scan --target /home/user --verbose

# Reload
systemctl --user daemon-reload
systemctl --user restart clamui-scheduled-scan.timer

# Cron - update crontab
crontab -e

# Add --verbose and redirect to log:
0 2 * * * /usr/bin/clamui-scheduled-scan --target "$HOME" --verbose >> /tmp/clamui-scan.log 2>&1
```

**Solution 10: Check notification issues**

If scans ARE running but you're not seeing notifications:

```bash
# Verify notify-send is installed
which notify-send

# Install if missing (Ubuntu/Debian):
sudo apt install libnotify-bin

# Fedora:
sudo dnf install libnotify

# Test notification manually
notify-send "Test" "ClamUI scheduled scan test"

# For Flatpak, notifications require D-Bus permissions (usually granted by default)
```

**Scheduled Scan Exit Codes:**

The `clamui-scheduled-scan` command returns:
- `0` = Success (clean scan, no threats found)
- `1` = Threats found (but scan completed)
- `2` = Error (ClamAV unavailable, target not found, etc.)

Check service/cron exit codes:
```bash
# Systemd - check last exit code
systemctl --user show clamui-scheduled-scan.service -p ExecMainStatus

# Cron logs show exit code in some configurations
journalctl -t CRON | grep clamui
```

**Common Failure Reasons Summary:**

| Issue | Systemd Symptom | Cron Symptom | Solution |
|-------|----------------|--------------|----------|
| Command not found | "No such file or directory" | No execution in logs | Use absolute path |
| User not lingering | Only runs when logged in | N/A | `loginctl enable-linger` |
| ClamAV missing | "ClamAV not available" | "ClamAV not available" | Install ClamAV |
| Invalid targets | "No valid targets found" | "No valid targets found" | Fix paths in config |
| Timer not enabled | Not in `list-timers` | N/A | `systemctl --user enable` |
| Cron daemon not running | N/A | No execution | Start cron daemon |

---

### Verifying scheduled scan logs

**Symptoms:**
- Want to confirm scheduled scans are running as expected
- Need to review scan results from automated scans
- Verify no threats were found during unattended scans
- Check performance/duration of scheduled scans
- Audit scan history for compliance purposes

**Log Locations and Formats:**

ClamUI stores scheduled scan logs in multiple locations:

1. **ClamUI application logs:** `~/.local/share/clamui/logs/`
2. **Systemd journal:** `journalctl --user -u clamui-scheduled-scan.*`
3. **Syslog/cron logs:** `/var/log/syslog` or `journalctl -t CRON`

**Diagnostic Steps:**

1. **Check ClamUI scan history logs:**

```bash
# List all scan log files
ls -lh ~/.local/share/clamui/logs/

# Expected output:
# scan_20240103.json
# scan_20240104.json
# scan_20240105.json

# Files are named scan_YYYYMMDD.json and contain all scans for that day
```

2. **View recent scan log:**

```bash
# View today's scan log
cat ~/.local/share/clamui/logs/scan_$(date +%Y%m%d).json

# Pretty-print with jq (if installed)
cat ~/.local/share/clamui/logs/scan_$(date +%Y%m%d).json | jq '.'

# Expected format:
# [
#   {
#     "timestamp": "2024-01-03T02:00:15",
#     "type": "scan",
#     "status": "clean",
#     "summary": "Scheduled scan completed - 15432 files scanned, no threats",
#     "details": "Scan Duration: 145.2 seconds\nFiles Scanned: 15432\nThreats Found: 0...",
#     "path": "/home/user/Documents",
#     "duration": 145.2,
#     "scheduled": true
#   }
# ]
```

3. **Check for scheduled scans specifically:**

```bash
# Filter for scheduled scans only (scheduled: true)
cat ~/.local/share/clamui/logs/scan_*.json | jq '.[] | select(.scheduled == true)'

# Or grep for "Scheduled scan"
grep -h "Scheduled scan" ~/.local/share/clamui/logs/scan_*.json

# Count scheduled scan executions in the last 7 days
find ~/.local/share/clamui/logs/ -name "scan_*.json" -mtime -7 -exec cat {} \; | jq -r '.[] | select(.scheduled == true) | .timestamp' | wc -l
```

4. **View systemd journal logs (systemd scheduler only):**

```bash
# View all scheduled scan service logs
journalctl --user -u clamui-scheduled-scan.service --since "7 days ago"

# View only today's scans
journalctl --user -u clamui-scheduled-scan.service --since today

# View timer activations (when timer triggered)
journalctl --user -u clamui-scheduled-scan.timer --since "7 days ago"

# Follow logs in real-time
journalctl --user -u clamui-scheduled-scan.service -f
```

5. **Check cron execution logs (cron scheduler only):**

```bash
# Ubuntu/Debian - check syslog for cron executions
grep "clamui-scheduled-scan" /var/log/syslog | tail -20

# Systemd-based systems - check cron via journalctl
journalctl -t CRON | grep clamui-scheduled-scan | tail -20

# Expected output:
# Jan  3 02:00:01 hostname CRON[12345]: (username) CMD (/usr/bin/clamui-scheduled-scan --target /home/user)
```

6. **Verify last scan time via ClamUI GUI:**

1. Open ClamUI application
2. Navigate to "Logs" or "History" view
3. Check for entries marked as "Scheduled Scan"
4. Verify timestamp matches your schedule

**Detailed Log Analysis:**

**Check scan status:**

```bash
# Count clean scans
cat ~/.local/share/clamui/logs/scan_*.json | jq -r '.[] | select(.scheduled == true and .status == "clean")' | wc -l

# Find scans with threats
cat ~/.local/share/clamui/logs/scan_*.json | jq '.[] | select(.scheduled == true and .status == "infected")'

# Find scans with errors
cat ~/.local/share/clamui/logs/scan_*.json | jq '.[] | select(.scheduled == true and .status == "error")'

# Find scans skipped due to battery
cat ~/.local/share/clamui/logs/scan_*.json | jq '.[] | select(.status == "skipped" and .summary | contains("battery"))'
```

**Check scan performance:**

```bash
# Get average scan duration
cat ~/.local/share/clamui/logs/scan_*.json | jq -r '.[] | select(.scheduled == true and .duration != null) | .duration' | awk '{sum+=$1; count++} END {print "Average duration:", sum/count, "seconds"}'

# Find longest scan
cat ~/.local/share/clamui/logs/scan_*.json | jq -r '.[] | select(.scheduled == true) | "\(.duration)s - \(.timestamp)"' | sort -n | tail -5

# Find scans that took longer than 5 minutes (300 seconds)
cat ~/.local/share/clamui/logs/scan_*.json | jq '.[] | select(.scheduled == true and .duration > 300)'
```

**Verify scan targets:**

```bash
# List all scanned paths
cat ~/.local/share/clamui/logs/scan_*.json | jq -r '.[] | select(.scheduled == true) | .path' | sort -u

# Check if specific path was scanned
cat ~/.local/share/clamui/logs/scan_*.json | jq '.[] | select(.scheduled == true and .path | contains("/home/user/Documents"))'
```

**Check threat details:**

```bash
# View all threats found in scheduled scans
cat ~/.local/share/clamui/logs/scan_*.json | jq '.[] | select(.scheduled == true and .status == "infected") | .details'

# Extract infected file paths
cat ~/.local/share/clamui/logs/scan_*.json | jq -r '.[] | select(.scheduled == true and .status == "infected") | .details' | grep -E "^\s+/"

# Count total threats found in last 30 days
find ~/.local/share/clamui/logs/ -name "scan_*.json" -mtime -30 -exec cat {} \; | jq '.[] | select(.scheduled == true and .status == "infected")' | grep -c '"status"'
```

**Solutions:**

**Solution 1: View comprehensive scan history via ClamUI**

1. Open ClamUI application
2. Navigate to **Logs** view (in navigation sidebar)
3. Filter by "Scheduled Scans" (if filter available)
4. Review entries sorted by date
5. Click on individual entries to see full details

This provides a user-friendly way to review scan history without command line.

**Solution 2: Generate scan summary report**

Create a script to summarize scheduled scan activity:

```bash
cat > ~/clamui-scan-report.sh << 'EOF'
#!/bin/bash
# ClamUI Scheduled Scan Summary Report

LOGS_DIR="$HOME/.local/share/clamui/logs"

echo "=== ClamUI Scheduled Scan Summary Report ==="
echo "Generated: $(date)"
echo ""

# Total scheduled scans
total=$(cat $LOGS_DIR/scan_*.json 2>/dev/null | jq -r '.[] | select(.scheduled == true)' | grep -c '"timestamp"')
echo "Total scheduled scans: $total"

# Scans by status
clean=$(cat $LOGS_DIR/scan_*.json 2>/dev/null | jq -r '.[] | select(.scheduled == true and .status == "clean")' | grep -c '"timestamp"')
infected=$(cat $LOGS_DIR/scan_*.json 2>/dev/null | jq -r '.[] | select(.scheduled == true and .status == "infected")' | grep -c '"timestamp"')
errors=$(cat $LOGS_DIR/scan_*.json 2>/dev/null | jq -r '.[] | select(.scheduled == true and .status == "error")' | grep -c '"timestamp"')
skipped=$(cat $LOGS_DIR/scan_*.json 2>/dev/null | jq -r '.[] | select(.status == "skipped")' | grep -c '"timestamp"')

echo "  Clean: $clean"
echo "  Threats found: $infected"
echo "  Errors: $errors"
echo "  Skipped (battery): $skipped"
echo ""

# Last scan
last_scan=$(cat $LOGS_DIR/scan_*.json 2>/dev/null | jq -r '.[] | select(.scheduled == true) | .timestamp' | sort | tail -1)
echo "Last scheduled scan: $last_scan"

# Average duration
avg_duration=$(cat $LOGS_DIR/scan_*.json 2>/dev/null | jq -r '.[] | select(.scheduled == true and .duration != null) | .duration' | awk '{sum+=$1; count++} END {if(count>0) print sum/count; else print "N/A"}')
echo "Average scan duration: ${avg_duration} seconds"
echo ""

# Recent threats
echo "=== Recent Threats (if any) ==="
cat $LOGS_DIR/scan_*.json 2>/dev/null | jq -r '.[] | select(.scheduled == true and .status == "infected") | "\(.timestamp): \(.summary)"' | tail -5
EOF

chmod +x ~/clamui-scan-report.sh

# Run report
~/clamui-scan-report.sh
```

**Solution 3: Set up log rotation**

Prevent log directory from growing too large:

```bash
# Create logrotate configuration
mkdir -p ~/.config/logrotate

cat > ~/.config/logrotate/clamui.conf << 'EOF'
~/.local/share/clamui/logs/*.json {
    rotate 90
    daily
    compress
    delaycompress
    missingok
    notifempty
}
EOF

# Run logrotate manually
logrotate -f ~/.config/logrotate/clamui.conf

# Add to crontab for automatic rotation (weekly)
crontab -e

# Add:
0 3 * * 0 logrotate -f ~/.config/logrotate/clamui.conf
```

**Solution 4: Export logs for external analysis**

```bash
# Export all scheduled scans to CSV
echo "Timestamp,Status,Summary,Duration,Path" > ~/clamui-scans.csv
cat ~/.local/share/clamui/logs/scan_*.json | jq -r '.[] | select(.scheduled == true) | [.timestamp, .status, .summary, .duration, .path] | @csv' >> ~/clamui-scans.csv

# View in spreadsheet application
libreoffice ~/clamui-scans.csv  # or your preferred spreadsheet app
```

**Solution 5: Monitor for threats in real-time**

Set up a notification for any threats found:

```bash
cat > ~/.config/systemd/user/clamui-threat-alert.service << 'EOF'
[Unit]
Description=ClamUI Threat Alert Monitor
After=clamui-scheduled-scan.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'if journalctl --user -u clamui-scheduled-scan.service -n 1 | grep -q "threat"; then notify-send -u critical "ClamUI Alert" "Threats detected in scheduled scan!"; fi'

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable clamui-threat-alert.service
```

**Solution 6: Verify scheduled scans are running on time**

Check if scans execute at the configured time:

```bash
# List timer next/last run times
systemctl --user list-timers clamui-scheduled-scan.timer

# Expected output shows:
# NEXT: [future time when next scan will run]
# LAST: [past time when last scan ran]
# PASSED: [time since last scan]

# Compare LAST time with your schedule
# If LAST is "n/a" or very old, timer isn't firing

# For cron, check execution times in logs
grep "clamui-scheduled-scan" /var/log/syslog | awk '{print $1, $2, $3}' | sort -u

# Should show execution dates/times matching your cron schedule
```

**Solution 7: Enable desktop notifications for scan completion**

Ensure you're notified when scheduled scans complete:

1. Open ClamUI → Preferences
2. Enable "Show notifications"
3. Scheduled scans will send desktop notifications showing:
   - Clean scans: "Scheduled Scan Complete - No threats found"
   - Threats found: "Scheduled Scan: Threats Detected!"
   - Errors: "Scheduled Scan Completed - Scan completed with some errors"

Verify notifications work:
```bash
# Send test notification
notify-send -u normal "ClamUI Test" "Notification test successful"

# If notifications don't appear, check notification daemon:
# GNOME:
systemctl --user status gnome-shell.service

# Other DEs may use different notification daemons
```

**Log Retention Recommendations:**

- **Keep logs for at least 30 days** for routine monitoring
- **Keep logs for 90+ days** for compliance/audit purposes
- **Archive old logs** by compressing or moving to backup storage
- **Monitor log directory size**: `du -sh ~/.local/share/clamui/logs/`

**Expected Log Size:**

- Typical scan log entry: 1-5 KB (clean scan)
- Scan with threats: 10-50 KB (includes threat details)
- Daily storage (1 scan/day): 30-150 KB/month
- Weekly storage: 10-20 KB/month

**Troubleshooting Missing Logs:**

If scheduled scans should have run but no logs appear:

```bash
# Verify log directory exists and is writable
ls -ld ~/.local/share/clamui/logs/
# Should show: drwxr-xr-x (755 permissions)

# Check disk space
df -h ~/.local/share/

# Recreate log directory if missing
mkdir -p ~/.local/share/clamui/logs/
chmod 755 ~/.local/share/clamui/logs/

# Run manual scan to verify logging works
clamui-scheduled-scan --target /tmp --verbose

# Check if log was created
ls -lh ~/.local/share/clamui/logs/scan_$(date +%Y%m%d).json
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
