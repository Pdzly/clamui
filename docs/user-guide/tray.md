# System Tray and Background Features

[← Back to User Guide](../USER_GUIDE.md)

---

## System Tray and Background Features

ClamUI can integrate with your system tray (notification area) to provide convenient access to antivirus protection
without keeping a window open. This allows you to run scans in the background, minimize the window to the tray, and
access quick actions with a simple right-click.

---

### Enabling System Tray Integration

ClamUI automatically enables system tray integration when the required libraries are available on your system.

#### Automatic Detection

When you launch ClamUI, it automatically checks for system tray support:

**✅ System Tray Available:**

- Tray icon appears in your notification area/system tray
- Shows current protection status with color-coded icon
- Right-click menu provides quick access to common actions
- Window can be minimized to tray (if enabled in settings)

**❌ System Tray Unavailable:**

- ClamUI runs normally without tray integration
- Window must remain open or minimized to taskbar
- All features still work, just without tray convenience

#### Checking Tray Availability

**Ubuntu/GNOME Users:**

- Install GNOME Shell extension: "AppIndicator and KStatusNotifierItem Support"
- Available through GNOME Extensions website or Extensions app
- Required for tray icons to display in GNOME Shell

**Other Desktop Environments:**

- KDE Plasma, XFCE, MATE, Cinnamon: Usually works out of the box
- System tray is typically enabled by default

**Flatpak Installation:**

- May require additional permissions for tray access
- Usually works automatically if system supports AppIndicator

#### Required System Libraries

ClamUI uses the AppIndicator library for tray integration:

**Library Name:** `libayatana-appindicator3` (or `libappindicator3`)

**To Install (if missing):**

```bash
# Ubuntu/Debian
sudo apt install libayatana-appindicator3-1

# Fedora
sudo dnf install libayatana-appindicator-gtk3

# Arch Linux
sudo pacman -S libayatana-appindicator
```

After installing the library, restart ClamUI to enable tray integration.

#### Tray Icon Status Indicators

The tray icon changes to reflect your protection status:

| Icon                    | Status    | Meaning                                  |
|-------------------------|-----------|------------------------------------------|
| 🛡️ **Shield (Green)**  | Protected | System is protected, definitions current |
| ⚠️ **Warning (Yellow)** | Warning   | Definitions outdated or scan overdue     |
| 🔄 **Spinning (Blue)**  | Scanning  | Scan currently in progress               |
| ⛔ **Error (Red)**       | Threat    | Threats detected in recent scan          |

**Hover Tooltip:** Hover your mouse over the tray icon to see a tooltip with the current status.

💡 **Tip:** The tray icon provides at-a-glance status without opening the main window.

---

### Minimize to Tray

When minimize-to-tray is enabled, clicking the minimize button hides the window to the system tray instead of minimizing
it to your taskbar.

#### What is Minimize to Tray?

**Normal Minimize (Default):**

- Click minimize button → window minimizes to taskbar
- Window appears as a taskbar button
- Click taskbar button to restore window

**Minimize to Tray (Optional):**

- Click minimize button → window hides to tray
- No taskbar button appears
- Click tray icon or use tray menu to restore window

**Benefits:**

- Cleaner taskbar with fewer window buttons
- ClamUI runs "invisibly" in the background
- Quick access via tray menu
- Reduces desktop clutter

**When to Use:**

- You want ClamUI always available but out of the way
- You have many windows open and want to reduce taskbar clutter
- You prefer tray-based workflow for background applications

#### Enabling Minimize to Tray

⚠️ **Requirement:** System tray integration must be available (
see [Enabling System Tray Integration](#enabling-system-tray-integration)).

**Currently Not Configurable in UI:**

The minimize-to-tray feature is controlled by the `minimize_to_tray` setting in your configuration file. Currently,
there is no UI toggle for this setting.

**To Enable Manually:**

1. Close ClamUI if it's running
2. Open your configuration file in a text editor:
   ```bash
   # Native installation
   nano ~/.config/clamui/settings.json

   # Flatpak installation
   nano ~/.var/app/io.github.linx_systems.ClamUI/config/clamui/settings.json
   ```
3. Find the line with `"minimize_to_tray": false`
4. Change it to `"minimize_to_tray": true`
5. Save the file and restart ClamUI

**Configuration Example:**

```json
{
  "scan_backend": "auto",
  "minimize_to_tray": true,
  "start_minimized": false,
  "show_notifications": true
}
```

#### Using Minimize to Tray

Once enabled, the feature works automatically:

**To Minimize to Tray:**

1. Click the minimize button (usually top-right of window)
2. Window disappears from taskbar and hides to tray
3. Tray icon remains visible in notification area

**To Restore from Tray:**

- **Method 1:** Click the tray icon
- **Method 2:** Right-click tray icon → "Show Window"

**What Happens When Minimized to Tray:**

- Window is completely hidden (not visible anywhere)
- Application continues running in background
- Scans can still run while minimized
- Notifications still appear for important events
- Scheduled scans execute normally

💡 **Tip:** You can start a scan, minimize to tray, and continue working. ClamUI will notify you when the scan completes.

⚠️ **Note:** If you close ClamUI from the tray menu while a scan is running, the scan will be cancelled.

#### Troubleshooting Minimize to Tray

**Window minimizes to taskbar instead of tray:**

- System tray integration is not available
- Check if AppIndicator library is installed (see [Enabling System Tray Integration](#enabling-system-tray-integration))
- Verify `minimize_to_tray` is set to `true` in settings.json

**Can't find the tray icon after minimizing:**

- Check your notification area/system tray
- Some desktop environments hide tray icons in overflow menu
- GNOME users: Ensure AppIndicator extension is enabled
- Try clicking in the notification area to reveal hidden icons

**Window won't restore from tray:**

- Right-click tray icon and select "Show Window"
- If still not working, quit from tray and relaunch ClamUI

---

### Start Minimized

Start-minimized allows ClamUI to launch directly to the system tray without showing the main window, perfect for
autostart configurations.

#### What is Start Minimized?

**Normal Startup (Default):**

- Launch ClamUI → main window appears
- Window is visible and ready to use
- Must manually minimize if you don't need it

**Start Minimized (Optional):**

- Launch ClamUI → no window appears
- Tray icon appears in notification area
- Access ClamUI through tray menu when needed
- Window can be shown later via tray icon

**Use Cases:**

- Automatically start ClamUI at login without showing window
- Keep antivirus protection running invisibly
- Reduce startup distraction (no window popping up)
- Perfect for "set it and forget it" scheduled scanning

#### Enabling Start Minimized

⚠️ **Requirement:** System tray integration must be available. If tray is not available, ClamUI will start normally with
window visible (it won't start invisible).

**Currently Not Configurable in UI:**

The start-minimized feature is controlled by the `start_minimized` setting in your configuration file. Currently, there
is no UI toggle for this setting.

**To Enable Manually:**

1. Close ClamUI if it's running
2. Open your configuration file in a text editor:
   ```bash
   # Native installation
   nano ~/.config/clamui/settings.json

   # Flatpak installation
   nano ~/.var/app/io.github.linx_systems.ClamUI/config/clamui/settings.json
   ```
3. Find the line with `"start_minimized": false`
4. Change it to `"start_minimized": true`
5. Save the file

**Configuration Example:**

```json
{
  "scan_backend": "auto",
  "minimize_to_tray": true,
  "start_minimized": true,
  "show_notifications": true
}
```

💡 **Tip:** Combine `start_minimized` with `minimize_to_tray` for the best background experience.

#### Using Start Minimized

**When Enabled:**

1. Launch ClamUI (from menu, terminal, or autostart)
2. No window appears
3. Tray icon appears in notification area
4. Application is running and ready

**To Show the Window:**

- Click the tray icon, or
- Right-click tray icon → "Show Window"

**What Happens on Startup:**

- Application launches silently to tray
- Scheduled scans remain active
- Background tasks continue normally
- Virus definitions update automatically (if configured)
- Notifications appear for important events

#### Setting Up Autostart with Start Minimized

Automatically start ClamUI at login with the window hidden:

**Step 1: Enable Start Minimized**

- Set `start_minimized` to `true` in settings.json (see above)

**Step 2: Create Autostart Entry**

```bash
# Native installation
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/clamui.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=ClamUI
Comment=ClamUI Antivirus
Exec=clamui
Icon=io.github.linx_systems.ClamUI
Terminal=false
Categories=Utility;Security;
X-GNOME-Autostart-enabled=true
EOF

# Flatpak installation
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/clamui.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=ClamUI
Comment=ClamUI Antivirus
Exec=flatpak run io.github.linx_systems.ClamUI
Icon=io.github.linx_systems.ClamUI
Terminal=false
Categories=Utility;Security;
X-GNOME-Autostart-enabled=true
EOF
```

**Step 3: Test Autostart**

1. Log out and log back in
2. Look for ClamUI tray icon (no window should appear)
3. Click tray icon to verify it's running

**To Disable Autostart:**

```bash
rm ~/.config/autostart/clamui.desktop
```

💡 **Tip:** With autostart + start minimized + scheduled scans, you get "set and forget" antivirus protection that runs
automatically in the background.

#### Temporarily Showing Window on Startup

If you need to show the window despite having `start_minimized` enabled:

**Launch from terminal with window visible:**

```bash
# This always shows window regardless of start_minimized setting
clamui /path/to/scan
```

When you provide a path argument, ClamUI always shows the window so you can see the scan results.

---

### Tray Menu Quick Actions

The tray menu provides quick access to common ClamUI operations without opening the main window.

#### Accessing the Tray Menu

Right-click the ClamUI tray icon to open the context menu.

**Tray Menu Layout:**

```
┌─────────────────────────────┐
│ Show Window                 │  ← Toggle window visibility
├─────────────────────────────┤
│ Quick Scan                  │  ← Run Quick Scan profile
│ Full Scan                   │  ← Run Full Scan profile
├─────────────────────────────┤
│ Update Definitions          │  ← Update virus database
├─────────────────────────────┤
│ Quit                        │  ← Exit ClamUI
└─────────────────────────────┘
```

#### Available Quick Actions

**Show Window / Hide Window**

- **Purpose:** Toggle main window visibility
- **Behavior:**
    - If window is hidden → shows and presents window
    - If window is visible → hides window to tray
- **Label changes:** Menu item updates to reflect current state
- **Keyboard shortcut:** Click the tray icon (left-click)

**Quick Scan**

- **Purpose:** Run the default "Quick Scan" profile
- **What it scans:** Your Downloads folder (fast, 10-30 seconds)
- **Behavior:**
    - Shows main window if hidden
    - Switches to Scan view
    - Automatically starts Quick Scan
    - Displays results when complete
- **Use case:** Quick daily check of downloaded files

**Full Scan**

- **Purpose:** Run the default "Full Scan" profile
- **What it scans:** Entire system excluding system directories
- **Duration:** 30-90+ minutes depending on system size
- **Behavior:**
    - Shows main window if hidden
    - Switches to Scan view
    - Automatically starts Full Scan
    - Displays results when complete
- **Use case:** Thorough weekly or monthly system scan

**Update Definitions**

- **Purpose:** Update ClamAV virus definitions
- **Behavior:**
    - Shows main window if hidden
    - Switches to Update view
    - Automatically starts database update
    - Shows update progress and results
- **Use case:** Manually update definitions before a scan

**Quit**

- **Purpose:** Exit ClamUI completely
- **Behavior:**
    - Stops any running scan
    - Closes main window
    - Removes tray icon
    - Application exits
- **⚠️ Warning:** If a scan is in progress, it will be cancelled

#### Using Quick Actions Effectively

**Workflow Example 1: Quick Daily Check**

1. Right-click tray icon
2. Click "Quick Scan"
3. Window appears and scan starts automatically
4. Review results when scan completes
5. Close or minimize window back to tray

**Workflow Example 2: Background Scan**

1. Right-click tray icon
2. Click "Full Scan"
3. Window appears and scan starts
4. Minimize to tray (scan continues in background)
5. Wait for completion notification
6. Click tray icon to view results

**Workflow Example 3: Update Before Scanning**

1. Right-click tray icon
2. Click "Update Definitions"
3. Wait for update to complete
4. Right-click tray icon again
5. Click "Quick Scan" or "Full Scan"

💡 **Tip:** You don't need to open the window manually before scanning. Quick Actions handle everything automatically.

#### Quick Action Limitations

**What Quick Actions Cannot Do:**

- ❌ Scan custom paths (only predefined profiles)
- ❌ Use custom scan profiles (only Quick Scan / Full Scan)
- ❌ Configure scan settings
- ❌ Manage quarantine
- ❌ View scan history
- ❌ Change preferences

**For these tasks, you need to open the main window.**

**Why Only Quick Scan and Full Scan?**

- These are the most common use cases
- Keeps tray menu simple and uncluttered
- Custom profiles require showing window for proper UI
- Tray menu is designed for quick, common actions only

**To Use Custom Profiles:**

1. Click tray icon to show window
2. Navigate to Scan view
3. Select your custom profile from dropdown
4. Click "Run Scan"

---

### Background Scanning

ClamUI allows scans to run in the background while the window is hidden, so you can continue working without
interruption.

#### What is Background Scanning?

Background scanning means running antivirus scans while:

- Main window is hidden to system tray
- Main window is minimized to taskbar
- You're working in other applications
- Your system is otherwise idle

**Benefits:**

- Continue working while scanning
- No window taking up screen space
- Less distraction during long scans
- Notifications alert you when scan completes
- Perfect for scheduled scans

#### How Background Scanning Works

**Normal Scanning Workflow:**

1. Open ClamUI window
2. Select files/folder to scan
3. Click "Start Scan"
4. Window must remain open while scanning
5. View results when complete

**Background Scanning Workflow:**

1. Open ClamUI window (or use tray menu)
2. Start a scan (manually or via quick action)
3. Hide or minimize the window
4. Scan continues running in background
5. Notification appears when scan completes
6. Restore window to view results

#### Starting a Background Scan

**Method 1: Via Tray Menu (Easiest)**

1. Right-click tray icon
2. Select "Quick Scan" or "Full Scan"
3. Window appears and scan starts
4. Minimize window to tray (scan continues)

**Method 2: Via Main Window**

1. Open ClamUI window
2. Navigate to Scan view
3. Select files/folder or profile
4. Click "Start Scan"
5. Minimize or hide window to tray
6. Scan continues in background

**Method 3: Via Scheduled Scans**

- Configure scheduled scans (see [Scheduled Scans](scheduling.md))
- Scans run automatically at scheduled time
- No window required (fully background)
- Notifications inform you of results

#### Monitoring Background Scans

**While Scan is Running:**

**Tray Icon Changes:**

- Icon changes to "scanning" indicator (🔄 spinning/sync icon)
- Tooltip shows "ClamUI - Scanning"
- Visual feedback without opening window

**Opening Window During Scan:**

1. Click tray icon to restore window
2. Scan view shows active scan progress
3. You can see current status and files scanned (if available)
4. Scan continues running normally

**Can't Cancel from Tray:**

- Tray menu does not provide "Cancel Scan" option
- Must open window and use "Cancel" button in Scan view
- Or quit ClamUI entirely (cancels scan)

#### Scan Completion Notifications

When a background scan completes, ClamUI notifies you:

**Desktop Notification:**

- Notification appears in your notification area
- Shows scan result summary:
    - ✅ "Scan Complete - No threats found"
    - ⚠️ "Scan Complete - X threats detected"
    - ❌ "Scan Failed - Error occurred"

**Click Notification:**

- Clicking notification opens ClamUI window
- Automatically switches to Scan view
- Shows complete scan results

**If Notifications Disabled:**

- No popup appears
- Tray icon returns to normal status
- Check Scan History to view results

💡 **Tip:** Enable notifications (Settings > Notification Settings) to be alerted when background scans complete.

#### Background Scan Behavior

**What Happens During Background Scan:**

**✅ Scan continues normally:**

- Files are scanned at normal speed
- ClamAV engine runs with full priority
- Threats are detected and can be quarantined
- Scan log is created normally

**✅ You can continue working:**

- Other applications work normally
- System remains responsive
- You can restore window anytime to check progress

**❌ Limitations:**

- Cannot see real-time progress (ClamAV limitation)
- Cannot pause scan (must cancel and restart)
- Scan cancels if you quit ClamUI
- Some system resources used (CPU, disk I/O)

**System Impact:**

- **CPU usage:** 20-80% (depending on scan backend and file types)
- **Memory:** 50-200 MB typically
- **Disk I/O:** Moderate to high (reading files to scan)
- **Impact on other apps:** Usually minimal on modern systems

**Battery Considerations:**

- Background scans consume power
- May drain battery faster on laptops
- Consider using battery-aware scheduled scans (see [Battery-Aware Scanning](scheduling.md#battery-aware-scanning))

#### Best Practices for Background Scanning

**DO:**

- ✅ Use Quick Scan for frequent background checks (fast, low impact)
- ✅ Run Full Scans during lunch break or when away from computer
- ✅ Enable notifications to know when scan completes
- ✅ Use scheduled scans for fully automated background protection
- ✅ Check scan history later if you miss notification

**DON'T:**

- ❌ Close/quit ClamUI while scan is running (cancels scan)
- ❌ Run multiple large scans simultaneously (system slowdown)
- ❌ Expect real-time progress updates (not available from ClamAV)
- ❌ Scan while on battery without battery-aware scheduling

**Recommended Workflow:**

**Daily Background Protection:**

1. Enable autostart with start-minimized
2. Configure scheduled daily Quick Scan (morning, Downloads folder)
3. Configure scheduled weekly Full Scan (Sunday evening)
4. Enable battery-aware scanning
5. Let ClamUI run invisibly in tray
6. Check notifications or scan history periodically

**Manual Background Scans:**

1. Right-click tray → "Quick Scan" before leaving for lunch
2. Minimize to tray
3. Return later and check results
4. No need to watch scan progress

💡 **Tip:** Background scanning + scheduled scans + notifications = "set and forget" antivirus protection that works
invisibly.

---

**System Tray and Background Features Summary:**

| Feature                 | Purpose                                | Requirement                   |
|-------------------------|----------------------------------------|-------------------------------|
| **System Tray Icon**    | At-a-glance protection status          | AppIndicator library          |
| **Tray Menu**           | Quick access to common actions         | System tray enabled           |
| **Minimize to Tray**    | Hide window to tray instead of taskbar | System tray + setting enabled |
| **Start Minimized**     | Launch to tray without window          | System tray + setting enabled |
| **Quick Actions**       | Run scans/updates from tray            | System tray enabled           |
| **Background Scanning** | Run scans while window hidden          | None (always available)       |

**Key Takeaways:**

- System tray provides convenient access without opening window
- Tray icon shows protection status at a glance
- Quick actions enable one-click scanning from tray menu
- Background scanning allows scans to run while you work
- Combine with scheduled scans for fully automated protection
- Notifications keep you informed of scan results
- Perfect for "set and forget" antivirus workflow

---

