# Troubleshooting Guide

This guide covers common issues and solutions for ClamUI.

## Table of Contents

1. [Flatpak-Specific Issues](#flatpak-specific-issues)
2. [ClamAV Installation Issues](#clamav-installation-issues)
3. [File Manager Context Menu Issues](#file-manager-context-menu-issues)
4. [System Tray Icon Issues](#system-tray-icon-issues)
5. [Scan Issues](#scan-issues)
6. [Database Update Issues](#database-update-issues)

---

## Flatpak-Specific Issues

### ClamAV Not Working in Flatpak

**Symptom:** Scans fail or ClamAV commands don't work in the Flatpak version.

**Note:** The ClamUI Flatpak bundles ClamAV internally - you do NOT need to install ClamAV on your host system when
using the Flatpak version.

**Possible causes and solutions:**

1. **Virus definitions not downloaded**: Run a database update from within ClamUI
2. **Corrupted installation**: Try reinstalling the Flatpak:
   ```bash
   flatpak uninstall io.github.linx_systems.ClamUI
   flatpak install flathub io.github.linx_systems.ClamUI
   ```
3. **Check for errors**: Look at the ClamUI logs in `~/.var/app/io.github.linx_systems.ClamUI/data/clamui/logs/`

### Permission Denied Errors

**Symptom:** "Permission denied" when scanning certain directories.

**Cause:** Flatpak sandbox permissions may not cover all directories.

**Solution:**

Grant additional filesystem access:

```bash
# Grant access to a specific directory
flatpak override --user --filesystem=/path/to/directory io.github.linx_systems.ClamUI

# Or grant broader access (use with caution)
flatpak override --user --filesystem=host io.github.linx_systems.ClamUI
```

### Freshclam Database Updates Fail

**Symptom:** Database updates fail with permission or path errors in Flatpak.

**Cause:** Flatpak uses a separate database directory from the host system.

**Solution:**

ClamUI automatically manages a Flatpak-specific database directory at
`~/.var/app/io.github.linx_systems.ClamUI/data/clamav/`. If updates fail:

1. Check the directory exists and is writable
2. Verify internet connectivity
3. Check `~/.var/app/io.github.linx_systems.ClamUI/config/clamui/freshclam.conf` for correct paths

---

## ClamAV Installation Issues

> **Note:** This section applies to **native installations only** (deb package, from source).
> The Flatpak version bundles ClamAV internally and does not require host installation.

### clamscan Not Found

**Symptom:** ClamUI cannot find the `clamscan` binary.

**Solution:**

1. Install ClamAV:

   ```bash
   # Ubuntu/Debian
   sudo apt install clamav

   # Fedora
   sudo dnf install clamav

   # Arch Linux
   sudo pacman -S clamav
   ```

2. Verify installation:

   ```bash
   which clamscan
   clamscan --version
   ```

### Virus Definitions Outdated

**Symptom:** ClamUI warns that virus definitions are outdated.

**Solution:**

- **Flatpak**: Use ClamUI's built-in update feature (recommended)
- **Native installation**: Run `sudo freshclam` or use ClamUI's built-in update

### clamd Daemon Not Running (Native Only)

**Symptom:** Daemon scanner backend unavailable.

> **Note:** The Flatpak version uses its bundled ClamAV and does not require the host clamd daemon.

**Solution (for native installations):**

1. Check daemon status:

   ```bash
   sudo systemctl status clamav-daemon
   ```

2. Start the daemon:

   ```bash
   sudo systemctl start clamav-daemon
   sudo systemctl enable clamav-daemon
   ```

3. Verify socket exists:

   ```bash
   ls -la /var/run/clamav/clamd.ctl
   # or
   ls -la /run/clamav/clamd.sock
   ```

---

## File Manager Context Menu Issues

### "Scan with ClamUI" Not Appearing

**Symptom:** Right-click menu doesn't show the scan option.

**Cause:** Desktop entry or Nemo action file not installed.

**Solution for GNOME (Nautilus):**

1. Copy the desktop entry:

   ```bash
   cp /usr/share/applications/io.github.linx_systems.ClamUI.desktop ~/.local/share/applications/
   ```

2. Update desktop database:

   ```bash
   update-desktop-database ~/.local/share/applications
   ```

3. Restart Nautilus:

   ```bash
   nautilus -q
   ```

**Solution for Cinnamon (Nemo):**

1. Create actions directory:

   ```bash
   mkdir -p ~/.local/share/nemo/actions
   ```

2. Copy the Nemo action:

   ```bash
   cp /usr/share/nemo/actions/io.github.linx_systems.ClamUI.nemo_action ~/.local/share/nemo/actions/
   ```

3. Restart Nemo:

   ```bash
   nemo -q
   ```

### Context Menu Shows But Doesn't Work

**Symptom:** Clicking "Scan with ClamUI" does nothing.

**Solution:**

1. Check if ClamUI is installed and executable:

   ```bash
   which clamui
   clamui --version
   ```

2. Try running manually with a test file:

   ```bash
   clamui /path/to/test/file
   ```

---

## System Tray Icon Issues

### Tray Icon Not Appearing

**Symptom:** System tray icon doesn't show even when enabled in settings.

**Cause:** Missing tray indicator library or unsupported desktop environment.

**Solution:**

1. Install the required library:

   ```bash
   # Ubuntu/Debian
   sudo apt install gir1.2-ayatanaappindicator3-0.1

   # Fedora
   sudo dnf install libayatana-appindicator-gtk3

   # Arch Linux
   sudo pacman -S libayatana-appindicator
   ```

2. For GNOME, install a tray extension:
    - [AppIndicator Support](https://extensions.gnome.org/extension/615/appindicator-support/)

3. Restart ClamUI.

### Tray Menu Not Working

**Symptom:** Tray icon appears but right-click menu doesn't work.

**Cause:** Desktop environment may not fully support StatusNotifierItem protocol.

**Solution:**

1. Try clicking the icon (some desktops use left-click for menu)
2. Check your desktop environment's system tray settings
3. On GNOME, ensure the AppIndicator extension is enabled and up to date

---

## Scan Issues

### Scans Taking Too Long

**Symptom:** Scans are much slower than expected.

**Solution:**

1. **Use daemon backend**: Switch to `daemon` scan backend in settings for faster scanning
2. **Create exclusion patterns**: Add large directories (like `node_modules`, `.git`) to exclusions
3. **Use scan profiles**: Create focused profiles that target specific directories

### False Positives

**Symptom:** ClamAV reports threats in files you know are safe.

**Solution:**

1. **Verify with VirusTotal**: Use ClamUI's VirusTotal integration to check against multiple engines
2. **Check ClamAV signatures**: Some signatures are known to have false positives
3. **Add to exclusions**: If confirmed safe, add the file pattern to exclusions
4. **Report to ClamAV**: Submit false positives to the ClamAV community

### Scan Hangs or Crashes

**Symptom:** Scan stops responding or ClamUI crashes.

**Solution:**

1. **Check file permissions**: Ensure ClamUI can read the target files
2. **Avoid special files**: Exclude device files, sockets, and virtual filesystems
3. **Check system resources**: Ensure adequate memory and disk space
4. **Try clamscan backend**: Switch from daemon to clamscan backend

---

## Database Update Issues

### Freshclam Permission Denied

**Symptom:** Database updates fail with permission errors.

**Solution:**

1. For native installations, run with sudo or fix permissions:

   ```bash
   sudo freshclam
   # or fix directory ownership
   sudo chown -R clamav:clamav /var/lib/clamav
   ```

2. For Flatpak, check the sandbox database directory permissions.

### Network Errors During Update

**Symptom:** Updates fail with connection or timeout errors.

**Solution:**

1. Check internet connectivity
2. Try a different mirror in freshclam configuration
3. Check firewall settings for outbound connections to database.clamav.net

### Corrupt Database Files

**Symptom:** ClamAV reports database errors after update.

**Solution:**

1. Remove corrupt files and re-download:

   ```bash
   # Native installation
   sudo rm /var/lib/clamav/*.cvd /var/lib/clamav/*.cld
   sudo freshclam

   # Flatpak
   rm ~/.var/app/io.github.linx_systems.ClamUI/data/clamav/*.cvd
   # Then use ClamUI's update feature
   ```

---

## Getting Help

If you can't resolve your issue:

1. **Check existing issues**: [GitHub Issues](https://github.com/linx-systems/clamui/issues)
2. **Report a bug**: Create a new issue with:
    - ClamUI version
    - Operating system and version
    - Installation method (Flatpak, .deb, source)
    - Steps to reproduce
    - Error messages or logs

3. **Community support**: Join discussions on the GitHub repository
