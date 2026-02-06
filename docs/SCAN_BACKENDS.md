# ClamUI Scan Backend Options

This document explains the three scan backend options available in ClamUI and helps you choose the right one for your
use case.

## Table of Contents

1. [Overview](#overview)
2. [Scan Backend Options](#scan-backend-options)
    - [Auto Mode (Recommended)](#auto-mode-recommended)
    - [Daemon Backend](#daemon-backend)
    - [Clamscan Backend](#clamscan-backend)
3. [Performance Comparison](#performance-comparison)
4. [How to Choose](#how-to-choose)
5. [Setup & Configuration](#setup--configuration)
6. [Troubleshooting](#troubleshooting)
7. [Technical Details](#technical-details)

---

## Overview

ClamUI supports three different scan backends for running ClamAV virus scans. Each backend has different performance
characteristics and requirements:

- **Auto Mode**: Intelligently chooses the best available backend (recommended for most users)
- **Daemon Backend**: Uses the ClamAV daemon (clamd) for fast scanning with in-memory database
- **Clamscan Backend**: Uses the standalone clamscan command-line tool

### What is a Scan Backend?

A scan backend determines how ClamUI communicates with ClamAV to perform virus scans. The choice of backend affects:

- **Scan Speed**: How quickly scans complete, especially scan startup time
- **Memory Usage**: How much RAM is consumed during scanning
- **Setup Requirements**: Whether you need to configure additional services
- **Availability**: Whether the backend works in all situations

### Default Configuration

By default, ClamUI uses **Auto Mode**, which automatically selects the daemon backend if available and falls back to
clamscan otherwise. This provides the best experience for most users without requiring manual configuration.

You can change the scan backend in **Preferences → General Settings → Scan Backend**.

---

## Scan Backend Options

### Auto Mode (Recommended)

**Description**: Intelligently selects the best available backend at scan time, prioritizing the daemon for performance
while providing automatic fallback to clamscan for reliability.

**How It Works**:

Auto mode implements a two-stage detection process that runs **at the start of each scan**:

1. **Daemon Availability Check**:
    - First checks if `clamdscan` command is installed on the system
    - Tests daemon connectivity by pinging the clamd socket using `clamdscan --ping`
    - Verifies that clamd service is running and responding to requests
    - Auto-detects socket location (supports both `/var/run/clamav/clamd.ctl` and `/run/clamav/clamd.ctl`)

2. **Backend Selection**:
    - If daemon responds with `PONG` → **Uses daemon backend** for this scan
    - If daemon is unavailable/not responding → **Falls back to clamscan backend**
    - Selection happens independently for each scan, adapting to real-time system state
    - No caching - always checks current daemon availability to ensure accuracy

3. **Transparent Operation**:
    - Backend selection is completely transparent to the user
    - UI and scan results are identical regardless of which backend is used
    - Scan logs indicate which backend was actually used for each operation
    - Preferences show current daemon status in real-time

**Advantages**:

- ✅ **Zero configuration required**: Works out-of-the-box with any ClamAV installation
- ✅ **Best performance when possible**: Automatically uses daemon if available for instant startup
- ✅ **Guaranteed reliability**: Always falls back to clamscan, ensuring scans never fail due to daemon issues
- ✅ **Adapts to system changes**: Automatically benefits from daemon when it's started, degrades gracefully when it
  stops
- ✅ **Perfect for mixed environments**: Works seamlessly whether daemon is installed or not
- ✅ **Recommended default**: Provides optimal experience for 95% of users without requiring expertise
- ✅ **No maintenance burden**: Users don't need to understand or configure backend selection
- ✅ **Development-friendly**: Automatically uses faster daemon during development if available

**Disadvantages**:

- ⚠️ **Variable performance**: Scan startup time may vary (instant vs 3-10 sec) if daemon availability changes
- ⚠️ **Detection overhead**: Adds approximately 50-100ms overhead per scan for daemon availability check (negligible for
  typical scans)
- ⚠️ **Potential confusion**: Users may wonder why scan speed varies between runs if daemon starts/stops
- ⚠️ **Not optimal for guaranteed performance**: If you need consistent predictable scan times, choose explicit backend

**When to Use**:

- **Desktop installations**: Default choice for all personal desktop/laptop installations
- **New users**: Users who are unfamiliar with ClamAV internals or don't want to configure backends
- **Mixed environments**: Systems where daemon may or may not be available (development machines, shared workstations)
- **Convenience over control**: When you want the system to make smart choices automatically
- **General-purpose scanning**: Most home users, small office setups, personal computers
- **Systems in flux**: Environments where daemon installation status may change over time
- **When daemon setup is uncertain**: If you're not sure whether clamd will be available, auto mode handles both cases
- **Default recommendation**: Unless you have specific requirements for daemon-only or clamscan-only behavior

**Technical Details**:

The auto mode implementation in `scanner.py` works as follows:

```python
# Simplified pseudo-code showing auto mode logic
if backend == "auto":
    is_daemon_available, message = check_clamd_connection()
    if is_daemon_available:
        # Use daemon backend
        return daemon_scanner.scan_sync(path, recursive, exclusions)
    else:
        # Fall back to clamscan backend
        return clamscan_scan(path, recursive, exclusions)
```

**Daemon Detection Process**:

1. Check if `clamdscan` command exists in PATH
2. Execute `clamdscan --ping` to test daemon connectivity
3. Look for socket at common locations (`/var/run/clamav/clamd.ctl`, `/run/clamav/clamd.ctl`)
4. Verify daemon responds with `PONG` (indicates healthy, responsive daemon)
5. On success → Use daemon backend; On failure → Use clamscan backend

**Performance Characteristics**:

- **When daemon available**: Matches daemon backend performance (instant startup + scan time)
- **When daemon unavailable**: Matches clamscan backend performance (3-10 sec startup + scan time)
- **Detection overhead**: Typically 50-100ms for daemon connectivity check (negligible compared to scan time)
- **No caching**: Detection runs fresh for each scan to ensure accuracy

---

### Daemon Backend

**Description**: Uses the ClamAV daemon (clamd) exclusively for all scanning operations.

**How It Works**:

- Communicates with the clamd background service via `clamdscan` command
- The daemon runs continuously as a system service (systemd or init.d)
- Keeps the entire virus database loaded in memory at all times for instant access
- Each scan reuses the pre-loaded database without any reload time
- Supports advanced features like parallel scanning (`--multiscan`) and file descriptor passing (`--fdpass`)
- Daemon automatically reloads database when freshclam updates signatures

**Advantages**:

- ✅ **Instant scan startup**: Database is already loaded in memory, eliminating 3-10 second load time
- ✅ **Superior performance for frequent scans**: No database reload between consecutive scans
- ✅ **Parallel scanning support**: Can scan multiple files simultaneously with `--multiscan` flag, utilizing all CPU
  cores
- ✅ **Lower per-scan overhead**: Daemon process stays resident, avoiding process creation/teardown costs
- ✅ **Advanced optimizations**: Supports `--fdpass` for improved performance on large files by passing file descriptors
- ✅ **Consistent performance**: Predictable scan times without database loading variability
- ✅ **Ideal for automation**: Perfect for scheduled scans, real-time monitoring, and server deployments
- ✅ **Efficient for batch operations**: Scanning multiple locations in sequence is much faster

**Disadvantages**:

- ❌ **Requires clamd to be running**: Scans fail completely if daemon is not available or crashes
- ❌ **Additional setup required**: Must install `clamav-daemon` package and configure systemd service
- ❌ **Higher baseline memory usage**: Daemon keeps database in RAM constantly (typically 500MB-1GB idle)
- ❌ **Service management overhead**: Must ensure daemon starts on boot, stays running, and restarts after crashes
- ❌ **Dependency on system service**: Requires root/sudo access for initial setup and configuration
- ❌ **Socket permission issues**: Can encounter permission problems with daemon socket access
- ❌ **Distribution-specific configuration**: Socket paths and service names vary across Linux distributions

**When to Use**:

- **Frequent or scheduled scans**: Running daily, hourly, or on-demand scans multiple times per day
- **Performance-critical environments**: When scan speed and responsiveness are paramount
- **Server deployments**: Mail servers, file servers, web servers with always-on scanning requirements
- **Real-time monitoring**: Systems that need continuous or near-continuous scanning capability
- **Maximum scan throughput**: When you need to scan large volumes of files as quickly as possible
- **Systems with clamd already configured**: Mail servers (Postfix/Exim), file sharing servers, or any system already
  using clamd
- **Development/testing environments**: Where repeated scanning of the same codebase is common
- **Dedicated security appliances**: Systems whose primary purpose is malware scanning

**Setup Requirements**:
See [Daemon Setup Instructions](#daemon-setup) below.

---

### Clamscan Backend

**Description**: Uses the standalone `clamscan` command-line tool directly without requiring any background services.

**How It Works**:

- Executes the `clamscan` command as a separate process for each scan operation
- Loads the entire virus database from disk at the start of every scan
- Scans files using the loaded database, then reports results
- Process terminates after completing the scan, freeing all resources
- No background services or daemons required - completely self-contained

**Advantages**:

- ✅ **No daemon required**: Works out-of-the-box with basic ClamAV installation
- ✅ **Simpler setup**: Just requires `clamscan` command to be installed (part of standard ClamAV package)
- ✅ **Lower baseline memory usage**: No resident daemon consuming RAM (~50MB idle vs 500MB-1GB for daemon)
- ✅ **Guaranteed to work**: Most reliable fallback option - works on any system with ClamAV installed
- ✅ **Easier troubleshooting**: Simpler architecture with fewer moving parts and dependencies
- ✅ **Maximum compatibility**: Works in restricted environments where daemon services cannot run
- ✅ **Clean resource usage**: Memory is freed immediately after each scan completes
- ✅ **No service management**: No need to worry about daemon crashes, restarts, or startup configuration

**Disadvantages**:

- ❌ **Slower startup time**: Must load database from disk for every scan (typically 3-10 seconds depending on disk
  speed)
- ❌ **Higher disk I/O**: Reads entire virus database (200-400MB) from disk each scan, increasing wear on storage
- ❌ **No parallel scanning**: Scans files sequentially, cannot take advantage of multi-core processors for scanning
- ❌ **Repeated overhead**: Database loading time is repeated for each scan operation, even consecutive scans
- ❌ **Higher total memory during scan**: Loads fresh database copy each time (500MB-1GB during scan)
- ❌ **Cache unfriendly**: Cannot benefit from filesystem cache as effectively as daemon for frequent scans

**When to Use**:

- **Infrequent, one-off scans**: When you only scan occasionally (weekly or less)
- **Systems where daemon setup is not feasible**: Embedded systems, minimal containers, or restricted environments
- **Testing or troubleshooting**: When debugging ClamAV issues or verifying scan behavior without daemon complexity
- **Minimal installations**: When memory is constrained and you can't afford 500MB-1GB for a resident daemon
- **Fallback scenario**: When daemon becomes unavailable or has configuration issues
- **Portable installations**: USB-based or portable ClamAV installations without system service access
- **Shared/multi-user systems**: Where you don't have permissions to configure system services
- **Battery-conscious mobile setups**: Laptops where you want to minimize background processes when not actively
  scanning

---

## Performance Comparison

### Detailed Metrics Comparison

| Aspect                         | Auto Mode  | Daemon Backend | Clamscan Backend |
|--------------------------------|------------|----------------|------------------|
| **First Scan Startup**         | 3-10 sec*  | <1 sec         | 3-10 sec         |
| **Subsequent Scans**           | 3-10 sec*  | <1 sec         | 3-10 sec         |
| **Scan Speed (Actual)**        | Fast*      | Fast           | Fast             |
| **CPU Usage**                  | Medium*    | Low-Medium     | Medium           |
| **Memory Usage (Baseline)**    | ~50MB*     | 500MB-1GB      | ~50MB            |
| **Memory Usage (During Scan)** | 500MB-1GB* | 500MB-1GB      | 500MB-1GB        |
| **Disk I/O Per Scan**          | High*      | Low            | High             |
| **Parallel Scanning**          | Yes/No*    | Yes            | No               |
| **Setup Complexity**           | None       | Moderate       | None             |
| **Reliability**                | High       | Medium**       | High             |
| **Best For**                   | Most users | Power users    | Occasional scans |

*Auto mode characteristics depend on whether daemon is available
**Daemon reliability depends on clamd service being properly configured and running

### Performance Metrics Explained

- **Startup Time**: Time from initiating scan to first file being scanned
    - Daemon: Instant (<100ms) - database already in memory
    - Clamscan: 3-10 seconds - must load 200-400MB database from disk
    - Auto: Depends on daemon availability

- **CPU Usage**: Processing overhead during scanning
    - Daemon: Lower due to optimized resident process and parallel scanning
    - Clamscan: Medium due to sequential scanning
    - Auto: Matches selected backend

- **Disk I/O**: Amount of disk reading required
    - Daemon: Minimal - only reads files being scanned, database already cached
    - Clamscan: High - reads entire database (200-400MB) plus scanned files
    - Auto: Low if daemon available, high if using clamscan

- **Parallel Scanning**: Ability to scan multiple files simultaneously
    - Daemon: Yes - supports `--multiscan` for parallel processing across CPU cores
    - Clamscan: No - always sequential file-by-file scanning
    - Auto: Available only when daemon is used

### Real-World Performance Examples

**Scanning a 1GB directory with 1000 files**:

- **Daemon**: 30 seconds total (instant startup + 30 sec scan)
- **Clamscan**: 40 seconds total (10 sec database load + 30 sec scan)
- **Auto (daemon available)**: 30 seconds total
- **Auto (daemon unavailable)**: 40 seconds total
- **Improvement**: Daemon is ~25% faster, more noticeable with multiple scans

**Running 5 consecutive scans**:

- **Daemon**: 150 seconds total (5× 30 sec scans)
- **Clamscan**: 200 seconds total (5× 40 sec scans including startup)
- **Auto (daemon available)**: 150 seconds total
- **Auto (daemon unavailable)**: 200 seconds total
- **Improvement**: Daemon saves 50 seconds over 5 scans

**Scanning a small directory (100 files, 50MB)**:

- **Daemon**: 2 seconds total (instant startup + 2 sec scan)
- **Clamscan**: 8 seconds total (6 sec database load + 2 sec scan)
- **Auto (daemon available)**: 2 seconds total
- **Auto (daemon unavailable)**: 8 seconds total
- **Improvement**: Daemon is 4× faster - startup overhead dominates small scans

**Daily scheduled scan of /home (10GB, 50,000 files)**:

- **Daemon**: ~5 minutes (instant startup + scan time)
- **Clamscan**: ~5.5 minutes (database load + scan time)
- **Auto**: Varies by daemon availability
- **Improvement**: Smaller relative improvement for large scans, but adds up over time

---

## How to Choose

Use this decision tree to select the best backend:

```
Do you run scans frequently (multiple times per day)?
  ├─ YES → Use Daemon Backend (after setup)
  └─ NO → Continue...

Is clamd already installed and running on your system?
  ├─ YES → Use Auto Mode (will use daemon automatically)
  └─ NO → Continue...

Are you willing to set up and maintain clamd daemon?
  ├─ YES → Use Daemon Backend (see setup instructions)
  └─ NO → Continue...

Do you only scan occasionally?
  ├─ YES → Use Auto Mode or Clamscan Backend
  └─ NO → Use Auto Mode (recommended default)
```

### Quick Recommendations

| Use Case                            | Recommended Backend | Rationale                               |
|-------------------------------------|---------------------|-----------------------------------------|
| Desktop user, occasional scans      | Auto Mode           | Best default, adapts automatically      |
| Desktop user, daily scheduled scans | Daemon Backend      | Worth the setup for better performance  |
| Server with mail scanning           | Daemon Backend      | Likely already has clamd configured     |
| Minimal installation / embedded     | Clamscan Backend    | Lower resource footprint                |
| Testing / troubleshooting           | Clamscan Backend    | Simpler, fewer dependencies             |
| Not sure                            | Auto Mode           | Safe default that adapts to your system |

---

## Setup & Configuration

### Changing the Scan Backend

1. Open ClamUI
2. Click the menu button (≡) and select **Preferences**
3. Navigate to **General Settings**
4. Find **Scan Backend** dropdown
5. Select your preferred backend: Auto, Daemon, or Clamscan
6. Close preferences - changes take effect immediately

### Daemon Setup

To use the daemon backend, you need to install and configure clamd:

#### Ubuntu/Debian

```bash
# Install ClamAV daemon
sudo apt install clamav-daemon

# Enable and start the daemon service
sudo systemctl enable clamav-daemon
sudo systemctl start clamav-daemon

# Verify daemon is running
sudo systemctl status clamav-daemon

# Test daemon connection
clamdscan --version
```

#### Fedora

```bash
# Install ClamAV daemon
sudo dnf install clamd

# Enable and start the daemon service (note: service name may be clamd@scan)
sudo systemctl enable clamd@scan
sudo systemctl start clamd@scan

# Verify daemon is running
sudo systemctl status clamd@scan

# Test daemon connection
clamdscan --version
```

#### Arch Linux

```bash
# Install ClamAV (includes daemon)
sudo pacman -S clamav

# Enable and start the daemon service
sudo systemctl enable clamav-daemon
sudo systemctl start clamav-daemon

# Verify daemon is running
sudo systemctl status clamav-daemon

# Test daemon connection
clamdscan --version
```

#### Flatpak Users

If you're running ClamUI as a Flatpak, the daemon must be installed on the **host system** (not inside Flatpak). Follow
the instructions above for your distribution, then ClamUI will automatically detect and use the host system's clamd
daemon.

---

## Troubleshooting

### Quick Troubleshooting Checklist

Before diving into specific issues, run through this quick checklist:

- [ ] **Verify ClamAV is installed**: Run `clamscan --version` in terminal
- [ ] **Check virus database is updated**: Ensure freshclam has run successfully
- [ ] **Confirm backend setting**: Check **Preferences → General Settings → Scan Backend**
- [ ] **Review recent logs**: Check **Logs View** in ClamUI for error messages
- [ ] **Test basic scan**: Try scanning a single file to isolate the issue
- [ ] **Check system resources**: Ensure sufficient disk space and memory available
- [ ] **Verify file permissions**: Confirm you have read access to files being scanned

### Checking Which Backend is Active

To see which backend ClamUI is currently using:

1. Run a scan with any file/folder
2. Check the scan results or logs - backend information is displayed
3. Alternatively, check Components View for daemon status
4. Look for "Using backend: daemon" or "Using backend: clamscan" in scan output

### Common Issues

#### "Daemon not available" error when using daemon backend

**Symptoms**: Scans fail with "clamd not accessible" message.

**Solutions**:

1. Verify clamd is installed: `which clamdscan`
2. Check daemon is running: `sudo systemctl status clamav-daemon`
3. Check daemon socket exists: `ls -l /var/run/clamav/clamd.ctl` (location may vary)
4. Review daemon logs: `sudo journalctl -u clamav-daemon`
5. Try manual connection: `clamdscan --version`
6. Switch to Auto or Clamscan mode as temporary workaround

#### Slow scan startup with auto/clamscan mode

**Symptoms**: 5-10 second delay before scan begins showing progress.

**Explanation**: This is normal - clamscan must load the virus database from disk (typically 200-400MB). This is not a
bug.

**Solutions**:

- Switch to daemon backend for instant startup
- Use auto mode and set up clamd to get automatic fast scanning
- Accept the delay as normal for clamscan backend

#### Daemon uses too much memory

**Symptoms**: clamd process consuming 500MB-1GB RAM constantly.

**Explanation**: This is normal - the daemon keeps the entire virus database loaded in memory for fast scanning. This is
the trade-off for performance.

**Solutions**:

- Switch to clamscan backend if memory is more important than speed
- Use auto mode and only run clamd when needed
- Configure clamd to use on-access scanning limits if available

#### Auto mode not using daemon

**Symptoms**: Auto mode always falls back to clamscan even though clamd is installed.

**Solutions**:

1. Verify daemon is actually running: `sudo systemctl status clamav-daemon`
2. Test manual connection: `clamdscan --version`
3. Check socket permissions (clamd socket must be readable)
4. Review ClamUI logs for connection errors
5. Try explicitly selecting daemon backend to see specific error

#### "Database load error" or "Database initialization failed"

**Symptoms**: Scan fails immediately with database-related error messages.

**Possible Causes**:

- Virus database is corrupt or incomplete
- Database update in progress (freshclam running)
- Insufficient disk space for database files
- Permission issues accessing database files

**Solutions**:

1. Update virus database: Run `sudo freshclam` manually
2. Check disk space: `df -h /var/lib/clamav`
3. Verify database files exist: `ls -lh /var/lib/clamav/*.cvd /var/lib/clamav/*.cld`
4. Check database ownership: `ls -l /var/lib/clamav/` (should be owned by clamav user)
5. Wait if freshclam is running: Check `ps aux | grep freshclam`
6. Reinstall database if corrupt: `sudo freshclam --verbose`

#### Scans are extremely slow or hang

**Symptoms**: Scans take much longer than expected, or appear to freeze without progress.

**Possible Causes**:

- Scanning very large files (archives, disk images)
- Scanning network/remote filesystems with high latency
- Insufficient system resources (low RAM, high CPU load)
- Nested or recursive archives
- Corrupted files causing scanner to hang

**Solutions**:

1. Check what's currently being scanned in scan progress window
2. Add problematic paths to exclusion list if they're known safe
3. Reduce scan scope to specific directories rather than entire filesystem
4. Increase available RAM (close other applications)
5. Use daemon backend for better performance
6. Configure archive scan limits in ClamAV configuration
7. Check system load: `top` or `htop` to see resource usage

#### "Permission denied" errors during scan

**Symptoms**: Some files show as "Permission denied" in scan results.

**Explanation**: This is usually normal - you cannot scan files you don't have permission to read.

**Solutions**:

1. **Expected behavior**: System files owned by root cannot be scanned by regular user
2. Run ClamUI with elevated permissions: `pkexec clamui` (use with caution)
3. Add frequently-denied paths to exclusion list
4. For system-wide scans, use scheduled scans with appropriate permissions
5. Check file permissions: `ls -l /path/to/file`

#### Flatpak-specific issues

**Symptoms**: Issues specific to ClamUI running as Flatpak.

**Common Issues**:

- Daemon not detected even when installed
- Cannot access certain directories
- Permission errors on non-standard mount points

**Solutions**:

1. **Daemon not detected**:
    - Install clamd on host system (not inside Flatpak)
    - Verify with: `flatpak-spawn --host clamdscan --version`
    - Check that ClamUI has host-spawn permission

2. **Directory access issues**:
    - Grant filesystem permissions: `flatpak override --user --filesystem=/path io.github.linx_systems.ClamUI`
    - Or use Flatseal GUI application to manage permissions
    - Check current permissions: `flatpak info --show-permissions io.github.linx_systems.ClamUI`

3. **Network shares**:
    - Flatpak may not have access to network mounts by default
    - Grant network access if needed: `flatpak override --user --share=network io.github.linx_systems.ClamUI`

#### Scan results show false positives

**Symptoms**: Known-safe files are reported as infected.

**Explanation**: False positives can occur, especially with development tools, packed executables, or test files.

**Solutions**:

1. Verify it's actually a false positive (not a real threat)
2. Submit false positive report to ClamAV: https://www.clamav.net/reports/fp
3. Add specific file or directory to exclusion patterns
4. Update virus database (false positives are often fixed in updates)
5. Check ClamAV forums/mailing list for known issues with specific signatures

#### Backend switching doesn't take effect

**Symptoms**: Changing backend in preferences doesn't seem to change scan behavior.

**Solutions**:

1. Close preferences window completely (changes apply on close)
2. Restart ClamUI if behavior persists
3. Check that the new backend is actually available (e.g., daemon is running)
4. Verify setting is saved: Check `~/.config/clamui/settings.json`
5. Review scan logs to confirm which backend is actually being used

#### Out of memory errors during scan

**Symptoms**: Scan crashes or fails with out-of-memory errors.

**Possible Causes**:

- Very large files being scanned
- Scanning many large archive files
- Insufficient system RAM
- Memory leak (rare)

**Solutions**:

1. Close other memory-intensive applications
2. Exclude very large files/archives from scan
3. Use clamscan backend instead of daemon (can use less memory in some cases)
4. Increase system swap space if needed
5. Scan smaller directories at a time rather than entire filesystem
6. Configure ClamAV limits: Check `/etc/clamav/clamd.conf` for MaxFileSize and MaxScanSize settings

### Getting Help

If you encounter issues not covered here:

1. Check ClamUI logs in **Preferences → Logs View**
2. Check system logs: `sudo journalctl -u clamav-daemon`
3. Verify ClamAV installation: `clamscan --version` and `clamdscan --version`
4. File an issue on GitHub: https://github.com/linx-systems/clamui/issues

---

## Technical Details

### Backend Selection Algorithm (Auto Mode)

When using auto mode, ClamUI determines the backend at scan time:

1. Check if `clamdscan` command is available on the system
2. Attempt to connect to clamd socket (typically `/var/run/clamav/clamd.ctl`)
3. If connection succeeds: Use daemon backend
4. If connection fails: Fall back to clamscan backend

This check happens before each scan, so auto mode adapts if daemon becomes available or unavailable.

### Exit Codes

Both backends return the same ClamAV exit codes:

- **0**: No virus found (clean)
- **1**: Virus found (infected)
- **2**: Error occurred during scanning

ClamUI interprets these codes consistently across all backends.

### Command-Line Examples

**Clamscan Backend** executes commands like:

```bash
clamscan --recursive --infected /path/to/scan
```

**Daemon Backend** executes commands like:

```bash
clamdscan --multiscan --fdpass --infected /path/to/scan
```

Note the different command names and options available. The daemon backend uses `--multiscan` for parallel scanning and
`--fdpass` for file descriptor passing to improve performance.

### Exclusion Patterns

Both backends support exclusion patterns configured in ClamUI preferences. ClamUI filters excluded files before passing
paths to ClamAV, ensuring consistent behavior across backends.

### Daemon Socket Locations

Clamd socket location varies by distribution. ClamUI automatically detects the socket by checking these locations in
order:

- `/var/run/clamav/clamd.ctl` (Ubuntu/Debian default)
- `/run/clamav/clamd.ctl` (Alternative Ubuntu/Debian location)
- `/var/run/clamd.scan/clamd.sock` (Fedora default)
- Custom: Check `/etc/clamav/clamd.conf` for `LocalSocket` setting if none of the above work

---

## Additional Resources

- [ClamAV Official Documentation](https://docs.clamav.net/)
- [ClamAV Daemon Configuration](https://docs.clamav.net/manual/Usage/Configuration.html)
- [ClamUI Installation Guide](./INSTALL.md)
- [ClamUI Development Guide](./DEVELOPMENT.md)
- [ClamUI GitHub Repository](https://github.com/linx-systems/clamui)

---

*Last updated: January 2026*
