# ClamUI User Guide

Welcome to ClamUI! This guide will help you get the most out of your antivirus protection on Linux.

## What is ClamUI?

ClamUI is a user-friendly desktop application that brings the powerful ClamAV antivirus engine to your Linux desktop with an intuitive graphical interface. No command-line knowledge required!

Whether you're downloading files, managing USB drives, or just want peace of mind about your system's security, ClamUI makes virus scanning simple and accessible.

## Who is this guide for?

This guide is written for Linux desktop users who want straightforward antivirus protection without dealing with terminal commands. If you've installed ClamUI via Flatpak, a .deb package, or any other method, you're in the right place!

You don't need to be a Linux expert or understand how ClamAV works under the hood. This guide focuses on **what you can do** with ClamUI, not how the code works.

## What you'll learn

This guide covers everything you need to know to use ClamUI effectively:

- **Getting started** - Launch the app and understand the interface
- **Scanning for threats** - Check files and folders for viruses
- **Managing detected threats** - Handle quarantined files safely
- **Automating protection** - Set up scheduled scans
- **Customizing your experience** - Configure settings to match your needs

## Table of Contents

### Getting Started
- [Launching ClamUI](#launching-clamui)
- [First-Time Setup](#first-time-setup)
- [Understanding the Main Window](#understanding-the-main-window)
- [Navigating Between Views](#navigating-between-views)
- [Your First Scan](#your-first-scan)
  - [Selecting Files and Folders](#selecting-files-and-folders)
  - [Understanding Scan Progress](#understanding-scan-progress)
  - [Interpreting Scan Results](#interpreting-scan-results)

### Scanning for Viruses
- [File and Folder Scanning](#file-and-folder-scanning)
- [Drag-and-Drop Scanning](#drag-and-drop-scanning)
- [Testing with the EICAR Test File](#testing-with-the-eicar-test-file)
- [Understanding Scan Progress](#understanding-scan-progress-1)
- [Reading Scan Results](#reading-scan-results)
- [Threat Severity Levels](#threat-severity-levels)

### Scan Profiles
- [What are Scan Profiles?](#what-are-scan-profiles)
- [Using Default Profiles](#using-default-profiles)
  - [Quick Scan](#quick-scan)
  - [Full Scan](#full-scan)
  - [Home Folder Scan](#home-folder-scan)
- [Creating Custom Profiles](#creating-custom-profiles)
- [Editing Existing Profiles](#editing-existing-profiles)
- [Managing Exclusions](#managing-exclusions)
- [Importing and Exporting Profiles](#importing-and-exporting-profiles)

### Quarantine Management
- [What is Quarantine?](#what-is-quarantine)
- [Viewing Quarantined Files](#viewing-quarantined-files)
- [Restoring Files from Quarantine](#restoring-files-from-quarantine)
- [Permanently Deleting Threats](#permanently-deleting-threats)
- [Clearing Old Quarantine Items](#clearing-old-quarantine-items)
- [Understanding Quarantine Storage](#understanding-quarantine-storage)

### Scan History
- [Viewing Past Scan Results](#viewing-past-scan-results)
- [Filtering Scan History](#filtering-scan-history)
- [Understanding Log Entries](#understanding-log-entries)
- [Exporting Scan Logs](#exporting-scan-logs)

### Scheduled Scans
- [Why Use Scheduled Scans?](#why-use-scheduled-scans)
- [Enabling Automatic Scanning](#enabling-automatic-scanning)
- [Choosing Scan Frequency](#choosing-scan-frequency)
- [Setting Scan Times](#setting-scan-times)
- [Configuring Scan Targets](#configuring-scan-targets)
- [Battery-Aware Scanning](#battery-aware-scanning)
- [Auto-Quarantine Options](#auto-quarantine-options)
- [Managing Scheduled Scans](#managing-scheduled-scans)

### Statistics Dashboard
- [Understanding Protection Status](#understanding-protection-status)
- [Viewing Scan Statistics](#viewing-scan-statistics)
- [Filtering by Timeframe](#filtering-by-timeframe)
- [Understanding Scan Activity Charts](#understanding-scan-activity-charts)
- [Quick Actions](#quick-actions)

### Settings and Preferences
- [Accessing Preferences](#accessing-preferences)
- [Scan Backend Options](#scan-backend-options)
- [Database Update Settings](#database-update-settings)
- [Scanner Configuration](#scanner-configuration)
- [Managing Exclusion Patterns](#managing-exclusion-patterns)
- [Notification Settings](#notification-settings)

### System Tray and Background Features
- [Enabling System Tray Integration](#enabling-system-tray-integration)
- [Minimize to Tray](#minimize-to-tray)
- [Start Minimized](#start-minimized)
- [Tray Menu Quick Actions](#tray-menu-quick-actions)
- [Background Scanning](#background-scanning)

### Troubleshooting
- [ClamAV Not Found](#clamav-not-found)
- [Daemon Connection Issues](#daemon-connection-issues)
- [Scan Errors](#scan-errors)
- [Quarantine Problems](#quarantine-problems)
- [Scheduled Scan Not Running](#scheduled-scan-not-running)
- [Performance Issues](#performance-issues)

### Frequently Asked Questions
- [Is ClamUI the same as ClamAV?](#is-clamui-the-same-as-clamav)
- [How often should I scan my computer?](#how-often-should-i-scan-my-computer)
- [What should I do if a scan finds threats?](#what-should-i-do-if-a-scan-finds-threats)
- [Why did my file get flagged as a false positive?](#why-did-my-file-get-flagged-as-a-false-positive)
- [Does scanning slow down my computer?](#does-scanning-slow-down-my-computer)
- [Is my data safe when using quarantine?](#is-my-data-safe-when-using-quarantine)
- [How do I update virus definitions?](#how-do-i-update-virus-definitions)
- [Can I scan external drives and USB devices?](#can-i-scan-external-drives-and-usb-devices)

---

## Getting Started

### Launching ClamUI

After installing ClamUI using your preferred method, you can launch it in several ways:

**From your Application Menu:**
- Look for "ClamUI" in your desktop's application launcher
- On GNOME, press the Super key and type "ClamUI"
- The application appears with a shield icon

**From the Terminal:**

If you installed via Flatpak:
```bash
flatpak run com.github.rooki.ClamUI
```

If you installed via .deb package or from source:
```bash
clamui
```

**With Files to Scan:**

You can also launch ClamUI with files or folders to scan immediately:

```bash
# Flatpak
flatpak run com.github.rooki.ClamUI /path/to/file /path/to/folder

# Native installation
clamui /path/to/file /path/to/folder
```

When launched with file arguments, ClamUI will open with those paths pre-loaded in the scan view.

### First-Time Setup

When you first launch ClamUI, the application will:

1. **Check for ClamAV Installation**
   - ClamUI requires ClamAV (the antivirus engine) to be installed on your system
   - If ClamAV is not found, you'll see a warning message with installation instructions
   - See the [Troubleshooting](#clamav-not-found) section if you encounter this issue

2. **Create Default Scan Profiles**
   - ClamUI automatically creates three useful scan profiles:
     - **Quick Scan**: Scans common locations like Downloads, Desktop, and Documents
     - **Full Scan**: Comprehensive scan of your entire home directory
     - **Home Folder**: Scans your home directory with common exclusions
   - You can customize these or create your own profiles later

3. **Set Up Configuration Directories**
   - Settings are saved to `~/.config/clamui/`
   - Scan logs and quarantine data are stored in `~/.local/share/clamui/`
   - These directories are created automatically

**Updating Virus Definitions**

Before your first scan, it's important to ensure your virus definitions are up to date:

1. Click the **Update Database** button (cloud icon with arrow) in the header bar
2. Click the "Update Now" button in the Update view
3. Wait for the update to complete (this may take a few minutes on first run)
4. You'll see a success message when definitions are current

💡 **Tip**: ClamUI can check for database updates automatically. See [Database Update Settings](#database-update-settings) to enable auto-updates.

### Understanding the Main Window

ClamUI uses a clean, modern interface that follows GNOME design guidelines. Here's what you'll see when you open the application:

![Main Window](../screenshots/main_view.png)

**Header Bar (Top)**

The header bar contains your main navigation and controls:

- **ClamUI Title**: Shows the application name
- **Navigation Buttons** (left side): Six icon buttons to switch between views:
  - 📁 **Scan Files**: Main scanning interface (default view)
  - ☁️ **Update Database**: Update virus definitions
  - 📄 **View Logs**: Browse scan history
  - ⚙️ **ClamAV Components**: Check ClamAV installation status
  - 🛡️ **Quarantine**: Manage isolated threats
  - 📊 **Statistics**: View protection statistics and scan activity
- **Menu Button** (right side): Access Preferences, About, and Quit

**Content Area (Center)**

The main content area displays the currently selected view. Each view has its own purpose:

- **Scan View**: Select files/folders to scan, configure scan options, and view results
- **Update View**: Check database status and update virus definitions
- **Logs View**: Review past scan results and filter by date/status
- **Components View**: Verify ClamAV installation and component versions
- **Quarantine View**: Manage files that have been isolated due to threats
- **Statistics View**: See charts and metrics about your scanning activity

**Status Information**

At the bottom of most views, you'll find:
- ClamAV version information
- Database status (last updated date and number of signatures)
- Quick status indicators

### Navigating Between Views

Switching between different parts of ClamUI is simple and intuitive.

**Using the Navigation Buttons**

The six buttons in the header bar let you quickly jump to any view:

1. Click any navigation button to switch to that view
2. The active view's button will be highlighted (pressed in)
3. The content area updates immediately to show the selected view

**Keyboard Shortcuts**

ClamUI supports keyboard shortcuts for faster navigation:

| Shortcut | Action |
|----------|--------|
| `Ctrl+Q` | Quit ClamUI |
| `Ctrl+,` | Open Preferences |

💡 **Tip**: More keyboard shortcuts for specific actions are available in each view.

**View-Specific Navigation**

Some views have additional navigation within them:

- **Scan View**: Switch between "Quick Actions" using scan profiles
- **Logs View**: Filter and search through scan history
- **Statistics View**: Change timeframe filters (7 days, 30 days, all time)

**Returning to the Scan View**

Click the folder icon (📁) button in the header bar at any time to return to the main scanning interface.

### Your First Scan

Ready to scan for viruses? This walkthrough will guide you through running your very first scan with ClamUI. We'll show you how to select what to scan, understand what's happening during the scan, and interpret the results.

#### Selecting Files and Folders

ClamUI gives you several ways to choose what to scan. Pick the method that works best for you:

**Method 1: Using the Browse Button**

This is the most straightforward approach:

1. Look for the **Scan Target** section in the main view
2. Click the **Browse** button on the right side of the "Selected Path" row
3. A file picker dialog will appear
4. Navigate to the folder or file you want to scan
5. Click **Select** to confirm your choice
6. The selected path will appear in the "Selected Path" subtitle

💡 **What should I scan first?** Start with your Downloads folder - it's where files from the internet arrive and is most likely to contain threats.

**Method 2: Drag and Drop**

For quick scanning, you can simply drag files or folders into ClamUI:

1. Open your file manager (Files, Nautilus, etc.)
2. Locate the file or folder you want to scan
3. Drag it into the ClamUI window
4. Drop it anywhere in the scan view
5. The path will be automatically selected

**Visual Feedback**: When dragging over ClamUI, you'll see a highlighted border indicating it's ready to accept your files.

**Method 3: Using Scan Profiles** (Recommended for beginners)

Scan profiles are pre-configured scan targets that make scanning even easier:

1. Look for the **Scan Profile** section at the top
2. Click the dropdown menu (it says "No Profile (Manual)" by default)
3. Choose one of the default profiles:
   - **Quick Scan**: Scans common locations (Downloads, Desktop, Documents)
   - **Full Scan**: Comprehensive scan of your entire home directory
   - **Home Folder**: Scans your home directory with common exclusions
4. The scan target will be automatically set when you select a profile

💡 **Tip**: For your first scan, try "Quick Scan" - it's fast and covers the most important areas.

**Method 4: Command-Line Arguments** (Advanced)

If you're comfortable with the terminal, you can launch ClamUI with a path already selected:

```bash
# Flatpak
flatpak run com.github.rooki.ClamUI ~/Downloads

# Native installation
clamui ~/Downloads
```

This method is great for integrating ClamUI with other tools or file managers.

#### Understanding Scan Progress

Once you've selected what to scan, you're ready to start. Here's what to expect:

**Starting the Scan**

1. Click the **Scan** button (the big blue button in the middle)
2. You'll immediately see changes in the interface:
   - The Scan button becomes disabled (grayed out)
   - The Browse button and Profile dropdown are also disabled
   - A "Scanning..." message appears at the bottom
   - The entire interface becomes non-interactive to prevent conflicts

**During the Scan**

While ClamUI is scanning:

- **Be patient**: Scanning can take time, especially for large folders or if you have many files
- **Don't close the window**: Closing ClamUI will stop the scan in progress
- **Watch the status**: The status message at the bottom will show "Scanning..." until complete
- **System usage**: You may notice increased CPU usage - this is normal as ClamAV analyzes files

**How long will it take?**

Scan duration depends on:
- **Number of files**: More files = longer scan time
- **File sizes**: Large files take longer to analyze
- **Scan backend**: Daemon (clamd) is faster than standalone clamscan
- **System resources**: Faster CPU = faster scanning

Typical scan times:
- Downloads folder (100-500 files): 10-30 seconds
- Home directory (10,000+ files): 2-10 minutes
- Full system scan: 15-60+ minutes

💡 **Tip**: While your first scan runs, feel free to read ahead in this guide to learn about other features!

**Scan Completion**

When the scan finishes:
- All buttons become active again
- The status message updates with results
- If threats were found, they appear in the "Scan Results" section below
- If no threats were found, you'll see a success message

#### Interpreting Scan Results

After your scan completes, ClamUI displays clear, easy-to-understand results. Let's break down what you'll see:

![Scan Results Example](../screenshots/main_view_with_scan_result.png)

**Clean Scan (No Threats Found)**

If your files are clean, you'll see:

```
✓ Scan complete: No threats found (XXX files scanned)
```

This green success message means:
- All scanned files are safe
- No viruses, trojans, or malware were detected
- You can continue using your files normally

The number in parentheses shows how many files were examined.

**Threats Detected**

If ClamUI finds threats, you'll see:

```
⚠ Scan complete: X threat(s) found
```

This red warning message is followed by a detailed list of each threat found. Don't panic - ClamUI gives you all the information and tools you need to handle threats safely.

**Understanding Threat Details**

Each detected threat is displayed in a card showing:

1. **Threat Name** (large text at the top)
   - The technical name of the virus or malware
   - Example: "Eicar-Signature", "Win.Test.EICAR_HDB-1"
   - This name is used by antivirus databases worldwide

2. **Severity Badge** (colored label on the right)
   - **CRITICAL** (red): Dangerous malware, immediate action required
   - **HIGH** (orange): Serious threats, should be quarantined
   - **MEDIUM** (yellow): Moderate concern, investigate further
   - **LOW** (blue): Minor issues or test files

3. **File Path** (monospaced text, second line)
   - The exact location of the infected file
   - You can select and copy this text
   - Example: `/home/username/Downloads/suspicious_file.exe`

4. **Category** (if available)
   - The type of threat detected
   - Examples: "Trojan", "Test", "Malware", "PUA" (Potentially Unwanted Application)

5. **Action Buttons** (bottom of each card)
   - **Quarantine**: Safely isolates the threat file
   - **Copy Path**: Copies the file path to your clipboard

**What Should I Do With Detected Threats?**

Here's your action plan:

1. **Don't panic** - ClamUI has already identified the threat and prevented any harm
2. **Review the threat details** - Check the file path to understand what was flagged
3. **Click "Quarantine"** - This safely moves the file to isolation where it can't cause harm
4. **Verify it's not a false positive** - Sometimes legitimate files are mistakenly flagged (see FAQ)

**For most users**: Click "Quarantine" on any detected threats. You can always restore files later if needed.

**Testing With EICAR**

Not sure if ClamUI is working correctly? Use the built-in test feature:

1. Click the **Test (EICAR)** button next to the Scan button
2. ClamUI creates a harmless test file that all antivirus software recognizes
3. The scan runs automatically and should find the test "threat"
4. You'll see a detection for "Eicar-Signature" or similar
5. This confirms ClamUI is working properly

**Important**: EICAR is NOT real malware - it's an industry-standard test pattern that's completely safe. It exists only to test antivirus software.

**Understanding Large Result Sets**

If a scan finds many threats (50+), ClamUI uses smart pagination:

- Only the first 25 threats are shown initially
- A **"Show More"** button appears at the bottom
- Click it to load 25 more threats at a time
- This keeps the interface responsive even with hundreds of detections

**Next Steps After Your First Scan**

Congratulations on completing your first scan! Now you can:

- **Explore scan profiles** - Try the Quick Scan, Full Scan, or Home Folder profiles
- **Set up scheduled scans** - Automate scanning to run regularly
- **Check the quarantine** - Review what's been isolated
- **View scan history** - See all your past scans in the Logs view
- **Customize settings** - Configure ClamUI to match your preferences

Ready to learn more? Continue reading to discover all of ClamUI's powerful features!

---

## Scanning for Viruses

Now that you've completed your first scan, let's dive deeper into ClamUI's scanning capabilities. This section provides comprehensive reference information about all scanning features.

### File and Folder Scanning

ClamUI provides flexible options for selecting files and folders to scan. Understanding these options helps you scan exactly what you need, when you need it.

#### Understanding Scan Targets

A **scan target** is the file or folder you want ClamUI to check for viruses. You can scan:

- **Individual files**: Any single file on your system (useful for checking downloads)
- **Folders/directories**: Entire folders and all their contents (recursive scanning)
- **Multiple locations**: Using scan profiles, you can scan multiple folders at once
- **External drives**: USB sticks, external hard drives, network locations (if accessible)

**Important**: ClamUI scans recursively by default. When you select a folder, all files and subfolders inside it are scanned automatically.

#### Selecting Files to Scan

**Using the File Picker (Browse Button)**

The Browse button opens a standard GTK file picker dialog:

1. Click **Browse** in the "Scan Target" section
2. The dialog opens to your home directory by default
3. Navigate using:
   - **Folder list** (left sidebar): Jump to common locations
   - **Path bar** (top): Click any folder in the current path
   - **Search** (Ctrl+F): Find files/folders by name
4. To select a file:
   - Click on the file name
   - Click **Select** in the bottom-right corner
5. To select a folder:
   - Navigate into the folder you want to scan
   - Click **Select** in the bottom-right corner (folder itself is selected)
   - Or click the folder once and then click **Select** to scan it

**Tips for File Selection**:
- You can only select one path at a time using the Browse button
- To scan multiple locations, use scan profiles instead
- The file picker respects hidden files based on your file manager settings
- You can type a path directly in the location bar (Ctrl+L)

#### Path Display and Validation

Once you select a path, ClamUI displays it in the "Selected Path" row:

```
Selected Path: /home/username/Downloads
```

The path is validated automatically:
- ✅ **Valid paths** display normally in monospaced font
- ❌ **Invalid paths** show an error banner with details
- 🔒 **Permission issues** are detected before scanning starts

**Common path validation errors**:
- Path does not exist (file/folder was deleted or moved)
- Insufficient permissions to read the location
- Path is on a remote filesystem that's not mounted
- Special system paths that require root access

If you see a validation error, choose a different path or check the file permissions.

### Drag-and-Drop Scanning

Drag-and-drop provides the fastest way to scan files in ClamUI. Simply grab a file or folder from your file manager and drop it into the ClamUI window.

#### How Drag-and-Drop Works

**Visual Feedback**

When you drag files over the ClamUI window:

1. **Drag starts**: Pick up a file/folder in your file manager
2. **Drag over ClamUI**: The entire window highlights with a colored border
3. **Border style**: Dashed blue/accent color border appears
4. **Background tint**: Light transparent overlay shows the drop is accepted
5. **Drop the file**: Release your mouse button anywhere in the window
6. **Border disappears**: Visual feedback clears immediately
7. **Path updates**: The dropped path appears in "Selected Path"

This visual feedback confirms ClamUI is ready to accept your file.

#### Drag-and-Drop Behavior

**What you can drop**:
- ✅ Files from your local filesystem
- ✅ Folders/directories
- ✅ Multiple files (first valid file is used)
- ✅ Files from archive managers (if they provide local paths)

**What won't work**:
- ❌ Remote files (http://, ftp://, etc.) - must be downloaded first
- ❌ Files from cloud storage (unless locally synced)
- ❌ Dropping during an active scan (rejected with error message)
- ❌ Special URIs that don't resolve to local paths

**Multi-file drops**: If you drop multiple files, ClamUI uses the first valid file path and ignores the rest. To scan multiple locations, use scan profiles instead.

#### Drop Error Handling

If a drag-and-drop operation fails, ClamUI displays an error banner explaining why:

- **"Scan in progress"**: You can't change the scan target while scanning
- **"No files were dropped"**: The drag operation didn't contain valid file data
- **"Remote files not supported"**: The file is not on your local filesystem
- **"Path does not exist"**: The file was moved or deleted during the drag
- **"Permission denied"**: You don't have read access to the dropped file

These error banners can be dismissed by clicking the "×" button or automatically disappear after a few seconds.

### Testing with the EICAR Test File

The **EICAR test file** is a special tool for verifying that antivirus software is working correctly. ClamUI includes a convenient "Test (EICAR)" button for instant testing.

#### What is EICAR?

EICAR (European Institute for Computer Antivirus Research) created a standard test file that **all antivirus software recognizes as a threat**, but which is **completely harmless**.

**Important facts about EICAR**:
- ✅ It's NOT real malware - it cannot harm your computer
- ✅ It's just a specific text string that antivirus programs look for
- ✅ It's used worldwide to test antivirus installations
- ✅ It's safe to create, download, and delete
- ❌ It won't do anything malicious (it's not even executable code)

The EICAR string looks like this:
```
X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*
```

When ClamAV scans this string, it detects it as a threat with names like:
- `Eicar-Signature`
- `Eicar-Test-Signature`
- `Win.Test.EICAR_HDB-1`

#### Using the EICAR Test Button

ClamUI makes EICAR testing simple with a dedicated test button:

**Step-by-Step**:

1. **Find the Test button**: Located next to the main Scan button in the scan view
2. **Click "Test (EICAR)"**: The button is styled with a beaker icon (🧪)
3. **Automatic test file creation**: ClamUI creates a temporary EICAR file
4. **Scan starts immediately**: No need to select a path
5. **Wait for results**: Scanning completes in 1-2 seconds
6. **Review detection**: You should see the EICAR threat detected
7. **Automatic cleanup**: The test file is deleted after scanning

**Expected Results**:

✅ **Working correctly**: ClamUI shows a threat detection with:
- Threat name containing "EICAR" or "Eicar-Signature"
- Severity level: **LOW** (blue badge)
- Category: **Test**
- File path: Temporary directory path

❌ **Not working**: If no threat is detected:
- ClamAV may not be properly installed
- Virus definitions may be outdated
- Scan backend might have issues
- See [Troubleshooting](#troubleshooting) for solutions

#### When to Use EICAR Testing

**Use the EICAR test when**:
- You just installed ClamUI and want to verify it works
- You updated virus definitions and want to confirm they loaded
- You suspect ClamUI isn't detecting threats correctly
- You're demonstrating ClamUI to someone
- You changed scan backend settings and want to test

**How often to test**: Testing once after installation is usually sufficient. You don't need to test regularly unless you suspect problems.

### Understanding Scan Progress

When you click the Scan button, ClamUI performs several operations behind the scenes. Understanding what's happening helps you interpret scan behavior and diagnose issues.

#### The Scanning Lifecycle

**1. Scan Initialization (< 1 second)**

When you click Scan:
- UI elements become disabled (buttons grayed out)
- Visual indication shows scanning is in progress
- ClamUI validates your scan target path one final time
- Settings are read (exclusion patterns, scan backend choice)
- The scanner is configured with your chosen options

**2. Backend Selection**

ClamUI chooses which scanning method to use:

- **Auto mode** (default):
  - First, try to connect to clamd daemon
  - If daemon is running: Use daemon for faster scanning
  - If daemon is unavailable: Fall back to clamscan
- **Daemon mode**: Use clamd only (error if unavailable)
- **Clamscan mode**: Use standalone clamscan only

**Backend performance**:
- **clamd (daemon)**: Fast (10-50x faster), lower CPU usage, requires running daemon
- **clamscan (standalone)**: Slower, higher CPU usage, always available

💡 **Tip**: Check which backend is being used in Statistics → Components view

**3. Scanning Process**

ClamAV analyzes files looking for malware signatures:

- Files are read from disk sequentially
- Each file is checked against the virus definition database
- Suspicious patterns trigger detections
- Results are collected as scanning progresses
- Exclusion patterns (if configured) skip matched files

**What ClamAV checks**:
- File contents (signature matching)
- File headers and structure
- Embedded scripts and macros
- Archive contents (zip, tar, rar, etc.)
- Email attachments and formats
- Compressed and encoded data

**System impact during scanning**:
- **CPU usage**: 20-80% of one CPU core (varies by backend)
- **Disk I/O**: Reading files from disk (SSD is faster than HDD)
- **Memory**: Typically 50-200 MB (higher for large archives)
- **Other apps**: Should remain responsive during scanning

**4. Scan Completion**

When scanning finishes:
- Results are parsed from ClamAV output
- Threat details are extracted and classified
- Severity levels are assigned to detected threats
- Scan log is saved to history
- UI updates with results
- Buttons become active again

**Exit codes** (technical reference):
- `0` = Clean (no threats found)
- `1` = Infected (threats detected)
- `2` = Error (scanning failed)

#### Scan Duration Estimates

How long a scan takes depends on several factors:

**File count**: More files = longer scan time
- 100 files: ~10-30 seconds
- 1,000 files: ~1-3 minutes
- 10,000 files: ~5-15 minutes
- 100,000+ files: ~30-120 minutes

**File sizes**: Large files take longer to scan
- Small text files: Milliseconds per file
- Large documents (PDFs, Office files): 1-5 seconds each
- Videos and archives: 5-30 seconds each
- ISO images and disk images: Minutes per file

**File types**: Different formats have different scan complexity
- ⚡ Fast: Plain text, small binaries
- 🐌 Slow: Archives (zip, tar.gz), large PDFs, disk images

**Scan backend**:
- clamd (daemon): Up to 50x faster
- clamscan (standalone): Slower but always available

**Storage speed**:
- SSD: 2-5x faster than HDD
- Network drives: Much slower (depends on network speed)
- USB 2.0: Slower than internal drives
- USB 3.0/3.1: Similar to internal HDDs

**Example scan times** (typical modern system with SSD):

| Location | File Count | Backend | Duration |
|----------|------------|---------|----------|
| Downloads folder | 200 files | daemon | 10-20s |
| Downloads folder | 200 files | clamscan | 30-60s |
| Home directory | 15,000 files | daemon | 3-8 min |
| Home directory | 15,000 files | clamscan | 10-20 min |
| Full system | 500,000+ files | daemon | 30-90 min |

💡 **Tip**: For faster scans, enable the clamd daemon in Preferences → Scan Backend

#### Monitoring Scan Progress

**What you can see during scanning**:
- Status message: "Scanning..." appears at the bottom
- UI state: All controls disabled while scanning
- Window title: May show scanning indicator (depends on desktop environment)

**What you can't see** (current limitation):
- Real-time file count or progress percentage
- Current file being scanned
- Estimated time remaining

**Why there's no progress bar**: ClamAV doesn't report real-time progress when scanning. ClamUI only receives results when the scan completes.

**What you can do during scanning**:
- ✅ Leave the window open (don't minimize or close)
- ✅ Read other parts of this guide
- ✅ Use other applications
- ❌ Don't close ClamUI window (stops the scan)
- ❌ Don't put your computer to sleep
- ❌ Don't unmount the drive being scanned

### Reading Scan Results

After a scan completes, ClamUI presents results in a clear, structured format. This section explains how to read and understand every detail.

#### Result Status Messages

**Clean Scan (No Threats)**:
```
✓ Scan complete: No threats found (1,543 files scanned)
```

This green success message tells you:
- ✅ All scanned files are safe
- ✅ No viruses, trojans, or malware detected
- ✅ The number in parentheses shows files examined
- ✅ You can use your files normally

**Threats Detected**:
```
⚠ Scan complete: 3 threat(s) found
```

This orange/red warning message indicates:
- ⚠️ ClamAV found infected or suspicious files
- ⚠️ Number of distinct threats detected
- ⚠️ Detailed threat cards appear below
- ⚠️ Action is recommended (quarantine or review)

**Scan Error**:
```
✗ Scan failed: [error details]
```

This red error message means:
- ❌ The scan couldn't complete
- ❌ Error details explain what went wrong
- ❌ Common causes: missing ClamAV, permission denied, path not found
- ❌ See error message and [Troubleshooting](#troubleshooting) section

#### Threat Detail Cards

Each detected threat is displayed in its own card with complete information:

**Card Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ Win.Trojan.Generic-12345                         [HIGH] │
│ /home/user/Downloads/suspicious-file.exe                │
│ Category: Trojan                                        │
│                                                         │
│ [Quarantine]  [Copy Path]                              │
└─────────────────────────────────────────────────────────┘
```

**Card Components Explained**:

**1. Threat Name** (top, large bold text)
- The technical name from ClamAV's virus database
- Format varies: `Platform.Type.Variant-ID`
- Examples:
  - `Win.Trojan.Generic-12345` (Windows trojan)
  - `Eicar-Test-Signature` (EICAR test)
  - `PUA.Linux.Miner.Generic` (potentially unwanted app)
- This name is recognized globally across all antivirus software

**2. Severity Badge** (top-right, colored label)
- Visual indicator of threat danger level
- Four levels: CRITICAL, HIGH, MEDIUM, LOW
- Color-coded for quick recognition
- See [Threat Severity Levels](#threat-severity-levels) for details

**3. File Path** (second line, monospaced)
- Absolute path to the infected file
- You can select this text and copy it
- Format: `/full/path/to/infected/file.ext`
- Use this to locate the file in your file manager

**4. Category** (third line, if available)
- The type of malware or threat
- Common categories:
  - **Virus**: Traditional computer viruses
  - **Trojan**: Trojan horse malware
  - **Worm**: Self-replicating worms
  - **Ransomware**: File-encrypting ransomware
  - **Adware**: Advertising software
  - **PUA**: Potentially Unwanted Application
  - **Test**: Test signatures (like EICAR)
  - **Spyware**: Information-stealing software
  - **Rootkit**: System-hiding malware
  - **Backdoor**: Remote access tools
  - **Exploit**: Vulnerability exploits
  - **Macro**: Macro viruses (documents)
  - **Phishing**: Phishing attempts
  - **Heuristic**: Behavior-based detection

**5. Action Buttons** (bottom)
- **Quarantine**: Safely isolate the threat file
  - Moves file to secure quarantine storage
  - File can't execute or spread from quarantine
  - You can restore it later if it's a false positive
  - See [Quarantine Management](#quarantine-management) for details
- **Copy Path**: Copy file path to clipboard
  - Useful for reporting or manual investigation
  - You can paste the path into a terminal or file manager
  - Helps you locate the file without typing the full path

#### Understanding File Counts

At the end of a scan, ClamUI reports:

```
No threats found (1,543 files scanned)
```

**What "files scanned" means**:
- Individual files examined by ClamAV
- Includes files in subdirectories (recursive count)
- Does NOT include:
  - Directories themselves (only files within)
  - Excluded files (via exclusion patterns)
  - Files ClamAV couldn't read (permission denied)
  - Symbolic links (unless they point to files)

**Why the count might seem low**:
- Hidden files might not be counted
- Some files might be skipped due to exclusions
- Symlinks to outside the scan path are ignored
- Empty directories contain zero files

**Why the count might seem high**:
- Archives are unpacked and contents are counted individually
- Cache files and temp files are included
- Each file in nested folders is counted

### Threat Severity Levels

ClamUI automatically classifies detected threats into four severity levels. Understanding these levels helps you prioritize your response to detections.

#### How Severity is Determined

ClamUI analyzes the threat name from ClamAV and matches it against known patterns to determine severity. This classification is based on:

- **Threat type keywords**: Ransomware, Trojan, Adware, etc.
- **Malware capabilities**: What the threat can do
- **Potential damage**: How dangerous the threat is
- **Industry standards**: Common classification practices

**Classification is automatic**: You don't need to understand threat names yourself - ClamUI does the analysis for you.

#### The Four Severity Levels

**🔴 CRITICAL (Red Badge)**

The most dangerous threats requiring immediate action.

**Threat types**:
- **Ransomware**: Encrypts your files and demands payment
  - Examples: `Ransom.Locky`, `CryptoLocker`, `WannaCry`
- **Rootkits**: Hides malware presence and provides deep system access
  - Examples: `Rootkit.Win32`, `Bootkit.Generic`
- **Bootkits**: Infects boot process for persistence
  - Examples: `Bootkit.MBR`, `Rootkit.Boot`

**What they can do**:
- Encrypt all your personal files
- Hide themselves from antivirus software
- Survive system restarts
- Provide attackers with complete system control
- Steal credentials and sensitive data

**Recommended action**:
1. **Quarantine immediately** - Don't delay
2. **Scan other systems** - Check if it spread
3. **Change passwords** - If the system was compromised
4. **Consider professional help** - For business/critical systems

**🟠 HIGH (Orange Badge)**

Serious threats that should be quarantined promptly.

**Threat types**:
- **Trojans**: Disguised malware that performs malicious actions
  - Examples: `Win.Trojan.Agent`, `Trojan.Generic`
- **Worms**: Self-replicating malware that spreads automatically
  - Examples: `Worm.Win32`, `Worm.AutoRun`
- **Backdoors**: Provides remote access to attackers
  - Examples: `Backdoor.Linux.Generic`, `RAT.Win32`
- **Exploits**: Takes advantage of software vulnerabilities
  - Examples: `Exploit.CVE-2021-12345`, `Exploit.PDF`
- **Downloaders/Droppers**: Downloads additional malware
  - Examples: `Downloader.Generic`, `Dropper.Win32`
- **Keyloggers**: Records keyboard input to steal credentials
  - Examples: `Keylogger.Win32`, `Spyware.KeyLog`

**What they can do**:
- Steal passwords and personal information
- Download more malware to your system
- Give hackers remote control of your computer
- Spread to other computers on your network
- Monitor your activities and communications

**Recommended action**:
1. **Quarantine the file** - Isolate the threat
2. **Run a full system scan** - Check for related infections
3. **Review recent downloads** - Identify the source
4. **Update software** - Patch exploited vulnerabilities

**🟡 MEDIUM (Yellow Badge)**

Concerning threats that warrant investigation.

**Threat types**:
- **Adware**: Displays unwanted advertisements
  - Examples: `Adware.Generic`, `PUA.Adware.Win32`
- **PUA/PUP**: Potentially Unwanted Applications/Programs
  - Examples: `PUA.Win.Generic`, `PUP.Optional.Toolbar`
- **Spyware**: Monitors activities and collects information
  - Examples: `Spyware.Win32`, `Monitor.Generic`
- **Miners**: Uses your computer to mine cryptocurrency
  - Examples: `CoinMiner.Win32`, `Miner.Linux`
- **Unknown threats**: Threats not matching specific patterns
  - Examples: `Generic.Suspicious`, `Unknown.Malware`

**What they can do**:
- Slow down your computer (especially miners)
- Display annoying ads and pop-ups
- Track your browsing habits
- Modify browser settings and search engines
- Consume resources for cryptocurrency mining
- Collect data for marketing purposes

**Recommended action**:
1. **Review the file** - Is it something you intentionally installed?
2. **Check if it's a false positive** - See [FAQ](#faq)
3. **Quarantine if unsure** - Better safe than sorry
4. **Uninstall related software** - Remove the source application

**🔵 LOW (Blue Badge)**

Minor issues and test files that pose little to no real danger.

**Threat types**:
- **EICAR test signatures**: Industry-standard antivirus test files
  - Examples: `Eicar-Signature`, `Test.File.EICAR`
- **Heuristic detections**: Behavior-based suspicious patterns
  - Examples: `Heuristic.Generic`, `Suspicious.Behavior`
- **Generic detections**: Very broad pattern matches
  - Examples: `Generic.Low`, `Possible.Threat`
- **Test files**: Created intentionally for testing
  - Examples: `Test-Signature`, `Sample.Test`

**What they are**:
- Harmless test files (EICAR)
- Files that "look suspicious" but may be safe
- Overly broad matches that catch legitimate software
- Test malware samples (if you're a security researcher)

**Recommended action**:
1. **Don't panic** - These are usually safe
2. **Verify the file purpose** - Why do you have this file?
3. **For EICAR**: This confirms your antivirus works - you can delete it
4. **For heuristics**: Check if it's a known program
5. **Quarantine if unknown** - Or delete if it's just a test file

#### Severity Classification Examples

Here are real-world examples showing how ClamUI classifies different threat names:

| Threat Name | Severity | Category | Reasoning |
|-------------|----------|----------|-----------|
| `Ransom.WannaCry` | CRITICAL | Ransomware | Ransomware = critical |
| `Win.Rootkit.Generic` | CRITICAL | Rootkit | Rootkit = critical |
| `Trojan.Agent.Win32` | HIGH | Trojan | Trojan = high |
| `Worm.AutoRun.VBS` | HIGH | Worm | Worm = high |
| `Backdoor.Linux.Generic` | HIGH | Backdoor | Backdoor = high |
| `Exploit.CVE-2021-1234` | HIGH | Exploit | Exploit = high |
| `PUA.Win.Adware.Generic` | MEDIUM | Adware | Adware = medium |
| `Spyware.KeyLogger` | HIGH | Spyware | Keylogger = high |
| `CoinMiner.Linux.XMRig` | MEDIUM | Miner | Miner = medium |
| `Eicar-Test-Signature` | LOW | Test | EICAR = low |
| `Heuristic.Suspicious` | LOW | Heuristic | Heuristic = low |

#### Severity Limitations and False Positives

**Important notes about severity classification**:

- ⚠️ **Severity is based on the threat name only**: ClamUI can't analyze the actual malware behavior
- ⚠️ **New threats**: Very new malware might get generic names and lower severity ratings
- ⚠️ **False positives**: Legitimate software can be flagged incorrectly
- ⚠️ **Platform matters**: A Windows virus on Linux can't execute (but should still be removed)

**When severity might be misleading**:
- Generic detections: `Generic.Trojan` might be critical or might be benign
- Test files: Security researchers might have high-severity test samples that are safely contained
- Cross-platform threats: Windows malware on Linux isn't immediately dangerous but should be quarantined

**Always use your judgment**: Severity is a guide, not a definitive risk assessment. When in doubt, quarantine the file and research the threat name online.

---

---

## Scan Profiles

Scan profiles are pre-configured scan settings that save you time and make scanning more convenient. Instead of manually selecting folders and configuring options every time you scan, profiles let you save your preferred scanning setups and launch them with a single click.

### What are Scan Profiles?

A **scan profile** is a saved configuration that contains:

- **Target directories/files**: What to scan (e.g., Downloads, Home folder, entire system)
- **Exclusion rules**: What to skip (specific paths or file patterns)
- **Profile metadata**: Name, description, creation date

**Why use profiles?**

✅ **Save time**: Launch common scans instantly without browsing for folders
✅ **Consistency**: Ensure you scan the same locations every time
✅ **Convenience**: Create specialized profiles for different purposes
✅ **Efficiency**: Skip irrelevant files automatically with exclusions

**Common use cases**:
- Quick check of downloaded files
- Weekly scan of your home directory
- Full system scan with common exclusions (system folders, caches)
- Scan external USB drives with specific exclusion patterns

### Using Default Profiles

ClamUI includes three built-in profiles that cover the most common scanning needs. These profiles are created automatically when you first launch ClamUI.

#### Quick Scan

**Purpose**: Fast scan of commonly infected locations

**What it scans**:
- `~/Downloads` - Your Downloads folder

**Exclusions**: None

**When to use**:
- After downloading files from the internet
- Quick daily security check
- Testing suspicious downloads
- When you want fast results (typically 10-30 seconds)

**How to use**:
1. Click the **Scan Profile** dropdown in the scan view
2. Select **Quick Scan**
3. Click the **Scan** button
4. Wait for results

💡 **Tip**: Quick Scan is perfect for beginners or as a daily habit. It focuses on your Downloads folder where most threats enter your system.

#### Full Scan

**Purpose**: Comprehensive system-wide security check

**What it scans**:
- `/` - The entire root filesystem (all directories and files)

**Exclusions**:
The following system directories are excluded for performance and to avoid false positives:
- `/proc` - Kernel process information (virtual filesystem)
- `/sys` - Kernel system information (virtual filesystem)
- `/dev` - Device files (not regular files)
- `/run` - Runtime data (temporary)
- `/tmp` - Temporary files
- `/var/cache` - Application caches
- `/var/tmp` - More temporary files

**When to use**:
- Monthly or quarterly comprehensive scan
- After suspecting a system compromise
- Before important backups
- When you have time for a thorough check (30-90+ minutes)

**How to use**:
1. Ensure you have time available (this can take 30-90+ minutes)
2. Select **Full Scan** from the Scan Profile dropdown
3. Click **Scan**
4. Let it run in the background

⚠️ **Important**: Full Scan examines hundreds of thousands of files and can take a significant amount of time. It's best run when you don't need your computer for other tasks, or schedule it to run automatically (see [Scheduled Scans](#scheduled-scans)).

#### Home Folder Scan

**Purpose**: Balanced scan of your personal files

**What it scans**:
- `~` - Your entire home directory (includes Documents, Pictures, Videos, Downloads, Desktop, etc.)

**Exclusions**:
- `~/.cache` - Application cache files (typically safe)
- `~/.local/share/Trash` - Your trash folder (files you've deleted)

**When to use**:
- Weekly personal files security check
- Before backing up your home directory
- After installing new software
- When you want thorough coverage without scanning system files (10-30 minutes)

**How to use**:
1. Select **Home Folder** from the Scan Profile dropdown
2. Click **Scan**
3. Review results when complete

💡 **Tip**: Home Folder is a good middle ground between Quick Scan (fast but limited) and Full Scan (thorough but slow). It covers all your personal data while excluding common cache locations.

### Creating Custom Profiles

While the default profiles cover most needs, you can create custom profiles for specific purposes like scanning USB drives, project folders, or specialized directories.

#### How to Create a Profile

**Step-by-Step**:

1. **Open the Profile Manager**:
   - Click the **hamburger menu** (three horizontal lines) in the header bar
   - Select **Manage Profiles** from the menu

2. **Click "New Profile"**:
   - Look for the **+** button or **New Profile** button
   - A dialog window will appear

3. **Fill in Basic Information**:
   - **Name** (required): Give your profile a descriptive name
     - Maximum 50 characters
     - Must be unique (no duplicate names)
     - Examples: "USB Drives", "Project Files", "Work Documents"
   - **Description** (optional): Explain what this profile is for
     - Helpful reminder of the profile's purpose
     - Example: "Scans all USB drives connected to /media"

4. **Add Target Directories**:
   - Click the **Add Target** button
   - Browse to the folder you want to scan, or type the path
   - Repeat to add multiple locations
   - **Tips**:
     - Use `~` to represent your home directory (e.g., `~/Projects`)
     - You can add both files and folders
     - Each target is scanned recursively (includes all subfolders)

5. **Add Exclusions** (optional):
   - **By Path**: Exclude specific directories
     - Click **Add Exclusion Path**
     - Browse to or enter the path to exclude
     - Example: `~/Projects/node_modules` (skip npm packages)
   - **By Pattern**: Exclude files matching patterns
     - Click **Add Exclusion Pattern**
     - Enter a glob pattern (e.g., `*.tmp`, `*.log`)
     - Example: `*.iso` (skip large disk images)

6. **Save the Profile**:
   - Click the **Save** button
   - Your new profile appears in the Scan Profile dropdown immediately

**Example Custom Profiles**:

**USB Drive Scanner**:
- Name: "External Drives"
- Targets: `/media`, `/mnt`
- Exclusions: `*.mp4`, `*.mkv` (skip video files for speed)
- Purpose: Quickly scan USB sticks and external hard drives

**Development Projects**:
- Name: "Code Projects"
- Targets: `~/Projects`, `~/workspace`
- Exclusions: `*/node_modules`, `*/.git`, `*/build`, `*/dist`
- Purpose: Scan source code while skipping dependencies and build artifacts

**Important Documents**:
- Name: "Documents Only"
- Targets: `~/Documents`, `~/Desktop`
- Exclusions: None
- Purpose: Focused scan of your important work files

#### Profile Creation Tips

💡 **Best Practices**:

- **Descriptive names**: Use clear names that explain what the profile scans
- **Start simple**: Create basic profiles first, add complexity as needed
- **Test your profile**: Run it once to ensure it scans what you expect
- **Exclude wisely**: Skip large files/folders that are unlikely to contain threats
- **Use ~ for home paths**: Makes profiles portable across systems

⚠️ **Common Mistakes to Avoid**:

- **Don't exclude everything**: If your exclusions cover all targets, the scan will find nothing
- **Watch name length**: Profile names are limited to 50 characters
- **Verify paths exist**: While non-existent paths are allowed, they won't be scanned
- **Don't scan virtual filesystems**: Skip `/proc`, `/sys`, `/dev` (these aren't real files)

### Editing Existing Profiles

You can modify any profile you've created (default profiles cannot be edited, but you can duplicate them).

#### How to Edit a Profile

**Step-by-Step**:

1. **Open the Profile Manager**:
   - Click the **hamburger menu** in the header bar
   - Select **Manage Profiles**

2. **Select the Profile to Edit**:
   - Find the profile in the list
   - Click the **Edit** button (pencil icon) next to it

3. **Modify Settings**:
   - Change the name, description, targets, or exclusions
   - Add or remove target directories
   - Add or remove exclusion rules
   - All fields work the same as when creating a profile

4. **Save Changes**:
   - Click **Save** to apply your changes
   - Click **Cancel** to discard changes

**What you can edit**:
- ✅ Profile name (must remain unique)
- ✅ Description
- ✅ Target directories (add/remove)
- ✅ Exclusion paths and patterns (add/remove)

**What you cannot edit**:
- ❌ Profile ID (internal identifier)
- ❌ Creation date
- ❌ Default profile flag (default profiles cannot be edited)

**Editing Default Profiles**:

Default profiles (Quick Scan, Full Scan, Home Folder) are **protected from editing** to ensure they remain available with their standard configurations.

**To customize a default profile**:
1. **Export** the default profile (see [Importing and Exporting](#importing-and-exporting-profiles))
2. **Import** it (this creates a copy with a new name like "Quick Scan (2)")
3. **Edit** the imported copy with your customizations

This way, you keep the original default profile and have your customized version.

### Managing Exclusions

Exclusions let you skip files and folders during scanning, improving performance and reducing false positives.

#### Why Use Exclusions?

**Performance reasons**:
- Skip large files that are unlikely to contain threats (videos, disk images)
- Avoid scanning build artifacts and dependencies (node_modules, .git)
- Exclude temporary files and caches

**Reduce false positives**:
- Development tools sometimes flag legitimate software as "PUA" (Potentially Unwanted Application)
- Test files and security tools might trigger detections

**Privacy and system stability**:
- Skip trash folders (files you've already deleted)
- Avoid virtual filesystems that can cause errors (`/proc`, `/sys`)

#### Types of Exclusions

**1. Path Exclusions** (Skip specific directories or files)

Exclude by exact path:

```
~/.cache
~/Projects/node_modules
/tmp
```

**How they work**:
- Exact path matching
- Recursive: Excluding a directory skips everything inside it
- Supports `~` for home directory
- Case-sensitive on Linux

**Examples**:
- `~/Downloads/archives` - Skip your download archives subfolder
- `~/.local/share/Trash` - Skip trash (already in Home Folder default)
- `/var/cache` - Skip system cache (already in Full Scan default)

**2. Pattern Exclusions** (Skip files matching patterns)

Exclude by filename pattern using glob syntax:

```
*.tmp
*.log
*.iso
node_modules
```

**How they work**:
- Glob pattern matching (like shell wildcards)
- `*` matches any characters
- `?` matches a single character
- Applies to filenames, not full paths

**Common patterns**:
- `*.tmp` - Skip all temporary files
- `*.log` - Skip log files
- `*.iso` - Skip disk images (large and unlikely to be infected)
- `*.mp4` - Skip video files (for speed)
- `.DS_Store` - Skip macOS metadata files

#### Adding Exclusions to a Profile

**When creating or editing a profile**:

1. **In the Profile Dialog**:
   - Look for the **Exclusions** section

2. **Add Path Exclusion**:
   - Click **Add Exclusion Path**
   - A new row appears
   - Enter or browse to the path
   - Example: `~/Projects/node_modules`

3. **Add Pattern Exclusion**:
   - Click **Add Exclusion Pattern**
   - A new row appears
   - Enter the pattern
   - Example: `*.tmp`

4. **Remove an Exclusion**:
   - Click the **minus (-)** button next to the exclusion
   - The exclusion is removed immediately

**Exclusion Validation**:

ClamUI validates exclusions when you save:
- ✅ **Valid**: Accepted and saved
- ⚠️ **Warning**: Saved, but you'll see a warning (e.g., "This exclusion might exclude all targets")
- ❌ **Error**: Invalid format, must be corrected before saving

#### Global vs. Profile Exclusions

**Profile Exclusions** (Configured in each profile):
- Apply only when using that specific profile
- Different profiles can have different exclusions
- Stored with the profile

**Global Exclusions** (Configured in Preferences):
- Apply to ALL scans, regardless of profile
- Useful for system-wide exclusions you never want to scan
- Configured in Preferences → Exclusion Patterns
- See [Managing Exclusion Patterns](#managing-exclusion-patterns)

💡 **Tip**: Use global exclusions for system directories (`/proc`, `/sys`) and profile exclusions for profile-specific needs (skip videos in USB scanner profile, but not in Documents profile).

#### Exclusion Best Practices

**DO**:
- ✅ Exclude build artifacts and dependencies (`node_modules`, `vendor`, `build`)
- ✅ Skip virtual filesystems (`/proc`, `/sys`, `/dev`)
- ✅ Exclude large media files if scanning for speed (`.iso`, `.mp4`)
- ✅ Skip caches and temporary directories
- ✅ Test your profile after adding exclusions

**DON'T**:
- ❌ Exclude your entire scan target (this creates a circular exclusion)
- ❌ Exclude important data folders like Documents or Downloads
- ❌ Blindly exclude common file types (.exe, .zip) - these can contain threats
- ❌ Over-exclude just to make scans faster - you might miss threats

**Example Exclusions by Use Case**:

| Use Case | Recommended Exclusions |
|----------|------------------------|
| **Development** | `*/node_modules`, `*/.git`, `*/build`, `*/dist`, `*/__pycache__` |
| **Media Library** | `*.mp4`, `*.mkv`, `*.avi`, `*.mp3`, `*.flac` (if just scanning for documents) |
| **USB Drives** | `*/lost+found`, `*.iso`, `System Volume Information` |
| **Home Directory** | `~/.cache`, `~/.local/share/Trash`, `~/Downloads/archives` |
| **System Scan** | `/proc`, `/sys`, `/dev`, `/run`, `/tmp`, `/var/cache` |

### Importing and Exporting Profiles

Profiles can be exported to JSON files for backup, sharing, or transferring between computers.

#### Exporting a Profile

**Purpose**: Save a profile to a file

**Step-by-Step**:

1. **Open the Profile Manager**:
   - Hamburger menu → **Manage Profiles**

2. **Select the Profile**:
   - Find the profile you want to export
   - Click the **Export** button (download icon) next to it

3. **Choose Save Location**:
   - A file save dialog appears
   - Navigate to where you want to save the file
   - The filename defaults to `ProfileName.json`
   - Click **Save**

4. **Confirmation**:
   - The profile is exported to the JSON file
   - You'll see a success message

**What's in the export file?**

The JSON file contains:
- Profile name and description
- Target directories list
- Exclusion paths and patterns
- Metadata (creation date, update date)

**Example export file** (`Quick-Scan.json`):
```json
{
  "export_version": 1,
  "profile": {
    "name": "Quick Scan",
    "description": "Fast scan of the Downloads folder",
    "targets": ["~/Downloads"],
    "exclusions": {},
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Use cases for exporting**:
- **Backup**: Save your custom profiles before system reinstall
- **Sharing**: Send profiles to colleagues or friends
- **Version control**: Track changes to important scan configurations
- **Migration**: Move profiles to another computer

#### Importing a Profile

**Purpose**: Load a profile from a JSON file

**Step-by-Step**:

1. **Open the Profile Manager**:
   - Hamburger menu → **Manage Profiles**

2. **Click "Import Profile"**:
   - Look for the **Import** button (usually with an upload icon)
   - A file chooser dialog appears

3. **Select the JSON File**:
   - Navigate to your exported profile JSON file
   - Select the file (must have `.json` extension)
   - Click **Open**

4. **Handle Duplicate Names**:
   - If a profile with the same name already exists:
     - ClamUI automatically appends a number: `"Quick Scan (2)"`
     - The imported profile gets a new unique ID
     - Both profiles coexist independently

5. **Confirmation**:
   - You'll see a success message
   - The imported profile appears in your profile list immediately
   - It's available in the Scan Profile dropdown

**Import Validation**:

ClamUI validates imported profiles:
- ✅ Checks JSON syntax is valid
- ✅ Ensures required fields are present (name, targets)
- ✅ Validates paths and exclusions
- ❌ Rejects invalid files with error message

**Import Behavior**:

- **New ID**: Imported profiles always get a new unique ID
- **Never default**: Imported profiles are never marked as default (even if the export was from a default profile)
- **Name uniqueness**: Duplicate names get numeric suffix `(2)`, `(3)`, etc.
- **Editable**: Imported profiles can be edited or deleted

**Troubleshooting Import Errors**:

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid JSON format" | File is corrupted or not JSON | Re-export the profile or check file contents |
| "Missing required field 'name'" | Export file is incomplete | Ensure file was exported correctly |
| "Invalid path format" | Paths in the file are malformed | Edit the JSON file to fix paths, or create a new profile |
| "File not found" | JSON file path is incorrect | Verify file location and try again |

#### Sharing Profiles

**Best practices for sharing**:

1. **Export to a descriptive filename**:
   - Good: `USB-Scanner-Profile.json`
   - Bad: `profile.json`

2. **Include documentation**:
   - Add a README explaining what the profile does
   - Note any system-specific paths that might need adjustment

3. **Test on target system**:
   - Import the profile on the destination computer
   - Run a scan to verify it works as expected
   - Adjust paths if needed (e.g., `/media/usb` vs `/mnt/usb`)

4. **Version your profiles**:
   - Include version or date in filename: `Dev-Scan-v2-2024-01.json`
   - Keep older versions as backups

**Privacy note**: Exported profiles contain paths from your system, which might reveal usernames or directory structures. Review the JSON file before sharing publicly.

### Managing Profiles

#### Viewing All Profiles

**In the Profile Manager** (Hamburger menu → Manage Profiles):

You'll see a list of all profiles with:
- **Profile name** (e.g., "Quick Scan")
- **Description** (if provided)
- **Default badge** (for built-in profiles)
- **Action buttons**: Edit, Export, Delete

#### Deleting a Profile

**To remove a custom profile**:

1. Open the Profile Manager
2. Find the profile to delete
3. Click the **Delete** button (trash icon)
4. Confirm deletion in the dialog

**Important**:
- ❌ Default profiles cannot be deleted (Quick Scan, Full Scan, Home Folder)
- ✅ Custom profiles can be deleted freely
- ⚠️ Deletion is permanent (export first if you want to keep a backup)

#### Using Profiles in Scans

**From the Scan View**:

1. **Select a profile**:
   - Click the **Scan Profile** dropdown
   - Choose a profile from the list
   - The target path updates automatically

2. **Start scanning**:
   - Click the **Scan** button
   - The scan uses the profile's targets and exclusions

3. **Switch back to manual**:
   - Select **No Profile (Manual)** from the dropdown
   - You can now manually select paths with Browse button

**Profile indicator**:
- When a profile is selected, the dropdown shows the profile name
- The "Selected Path" row shows the first target (or "Multiple locations" if the profile has multiple targets)

#### Profile Tips and Tricks

💡 **Productivity Tips**:

1. **Create profiles for recurring tasks**:
   - Weekly home scan: "Weekly Home Check"
   - After downloads: "Post-Download Quick Scan"
   - Before backup: "Pre-Backup Full Scan"

2. **Name profiles by frequency or purpose**:
   - "Daily Downloads Check"
   - "Monthly System Scan"
   - "USB Drive Inspector"

3. **Use exclusions strategically**:
   - Development scans: Exclude `node_modules`, `.git`, build folders
   - Media scans: Exclude video files if you only care about documents
   - System scans: Exclude virtual filesystems and caches

4. **Combine with scheduled scans**:
   - Create a profile
   - Use it in scheduled scans for automated security
   - See [Scheduled Scans](#scheduled-scans)

5. **Keep profiles updated**:
   - As your directory structure changes, update profile targets
   - Add new exclusions as you discover slowdowns
   - Delete unused profiles to reduce clutter

---

## Quarantine Management

When ClamUI detects a threat, you can **quarantine** the file - a safe isolation process that prevents the threat from causing harm while giving you options to review, restore, or delete it permanently.

### What is Quarantine?

**Quarantine** is a secure storage area where detected threats are isolated from your system. Think of it as a digital "holding cell" for suspicious files.

#### How Quarantine Works

When you quarantine a file, ClamUI:

1. **Moves the file** from its original location to a secure quarantine directory
2. **Records metadata** in a database (original path, threat name, detection date, file size, hash)
3. **Calculates a hash** (SHA-256) to verify file integrity
4. **Stores it safely** where it cannot execute or spread

**Important facts about quarantine**:

- ✅ **Safe**: Quarantined files cannot run or infect your system
- ✅ **Reversible**: You can restore files if they're false positives
- ✅ **Verifiable**: File integrity is checked before restoration
- ✅ **Automatic cleanup**: Old items can be cleared after 30 days
- ✅ **Detailed records**: Full metadata preserved for each file

#### When to Use Quarantine

**Quarantine immediately for**:
- 🔴 **CRITICAL** threats (ransomware, rootkits)
- 🟠 **HIGH** threats (trojans, worms, backdoors)
- 🟡 **MEDIUM** threats (adware, PUA, spyware) - investigate first

**Consider before quarantining**:
- 🔵 **LOW** threats (EICAR tests, heuristic detections) - likely false positives
- **Known safe files**: Software tools, security utilities, test files
- **Development files**: Build tools, compilers that trigger PUA detections

💡 **Tip**: If you're unsure whether a detection is legitimate, research the threat name online or quarantine it temporarily while you investigate.

### Viewing Quarantined Files

Access your quarantined files through the **Quarantine view** to review isolated threats and manage them.

#### Opening the Quarantine View

**From the main window**:
1. Click the **Quarantine** button in the left navigation sidebar
2. The quarantine list loads automatically

**Keyboard shortcut**: No dedicated shortcut, but navigate using Tab or arrow keys.

#### Understanding the Quarantine List

The quarantine list shows all isolated files with key information:

**Main List View**:
```
┌─────────────────────────────────────────────────────┐
│ Storage Header                                      │
│ Total Size: 2.5 MB                        12 items │
├─────────────────────────────────────────────────────┤
│ ⚠ Win.Trojan.Generic-12345                         │
│   .../Downloads/suspicious.exe                      │
│   2024-01-15 14:30 • 1.2 MB                 [▼]    │
│                                                     │
│ ⚠ PUA.Linux.Miner.Generic                          │
│   .../Documents/crypto-miner                        │
│   2024-01-10 09:15 • 856 KB                 [▼]    │
└─────────────────────────────────────────────────────┘
```

**Storage Information Section** (at the top):
- **Total Size**: Combined size of all quarantined files
- **Item Count**: Number of files in quarantine
- **Purpose**: Quick overview of quarantine usage

**Each Entry Shows**:

**1. Threat Name** (title line):
- The virus/malware name from ClamAV's database
- Examples: `Win.Trojan.Generic-12345`, `Eicar-Test-Signature`
- This is the primary identifier

**2. Original Path** (subtitle line):
- Shows where the file was located before quarantine
- Long paths are truncated with `...` at the start
- Example: `.../Downloads/suspicious.exe` (full path in details)

**3. Metadata** (date and size):
- **Detection Date**: When the file was quarantined (YYYY-MM-DD HH:MM)
- **File Size**: Human-readable size (KB, MB, or GB)
- Separated by bullet point: `2024-01-15 14:30 • 1.2 MB`

**4. Expand Arrow** (`[▼]`):
- Click any entry to expand and see full details
- Expands to show complete information and action buttons

#### Viewing Detailed Information

Click any quarantined file entry to expand it and see complete details:

**Expanded View**:
```
┌─────────────────────────────────────────────────────┐
│ ⚠ Win.Trojan.Generic-12345                  [▲]    │
│   .../Downloads/suspicious.exe                      │
│   2024-01-15 14:30 • 1.2 MB                        │
│                                                     │
│   📁 Original Path                                  │
│      /home/user/Downloads/suspicious.exe            │
│                                                     │
│   📅 Detection Date                                 │
│      2024-01-15 14:30                               │
│                                                     │
│   💾 File Size                                      │
│      1.2 MB (1,258,291 bytes)                       │
│                                                     │
│   [Restore]  [Delete]                               │
└─────────────────────────────────────────────────────┘
```

**Detailed Fields**:

**Original Path**:
- Full absolute path to where the file was located
- Selectable text - you can copy it
- Useful for remembering where the file came from

**Detection Date**:
- Exact date and time when the file was quarantined
- Formatted as `YYYY-MM-DD HH:MM`
- Helps track when threats were detected

**File Size**:
- Human-readable size (e.g., "1.2 MB")
- Exact byte count in parentheses (e.g., "1,258,291 bytes")
- Useful for identifying large files taking up storage

**Action Buttons**:
- **Restore** (blue): Recover the file to its original location
- **Delete** (red): Permanently remove the file
- See sections below for details on each action

#### List Features

**Pagination** (for large lists):
- **Initial display**: First 25 entries shown automatically
- **Show More**: Click button to load 25 more entries
- **Show All**: Load all remaining entries at once (if many remain)
- **Progress indicator**: "Showing X of Y entries"

**Empty State**:
If no files are quarantined, you'll see:
```
        🛡️
  No Quarantined Files
  Detected threats will be isolated here for review
```

**Refresh Button**:
- Click the **refresh icon** (↻) in the header to reload the list
- Useful after quarantining files from scans
- The list auto-refreshes when you open the view

**Loading State**:
While loading, you'll see:
```
   ⏳  Loading quarantine entries...
```

### Restoring Files from Quarantine

If a quarantined file is actually safe (a **false positive**), you can restore it to its original location.

⚠️ **Important**: Only restore files you are **absolutely certain** are safe. If you're unsure, leave the file quarantined or delete it.

#### When to Restore Files

**Restore if**:
- ✅ You recognize the file as legitimate software
- ✅ The threat is flagged as **LOW** severity (often EICAR tests or heuristics)
- ✅ You verified the file source and it's from a trusted developer
- ✅ You researched the threat name and confirmed it's a known false positive
- ✅ You need the file for work and have verified its safety

**Do NOT restore if**:
- ❌ The threat is **CRITICAL** or **HIGH** severity
- ❌ You don't recognize the file or don't remember downloading it
- ❌ The file came from an untrusted source (unknown website, email attachment)
- ❌ You cannot verify the file is safe
- ❌ The detection is for ransomware, trojan, or malware

#### How to Restore a File

**Step-by-Step**:

1. **Open Quarantine View**:
   - Navigate to the **Quarantine** view

2. **Find the File**:
   - Locate the quarantined file in the list
   - Check the threat name and original path

3. **Expand the Entry**:
   - Click the file entry to expand it
   - Review the full details (path, date, size)

4. **Click Restore**:
   - Click the **Restore** button (blue button)
   - A confirmation dialog appears

5. **Review the Warning**:
   ```
   Restore File?

   This will restore the file to its original location:
   /home/user/Downloads/suspicious.exe

   Warning: This file was detected as a threat (Win.Trojan.Generic-12345).
   Only restore if you are certain it is a false positive.

   [Cancel]  [Restore]
   ```

6. **Confirm Restoration**:
   - Read the warning carefully
   - Verify the original path is correct
   - Click **Restore** to proceed, or **Cancel** to abort

7. **Wait for Completion**:
   - ClamUI verifies file integrity (checks SHA-256 hash)
   - Moves the file back to its original location
   - Removes the entry from quarantine
   - Shows success/failure message

**Success Message**:
```
✓ File restored successfully
```

**The file is now**:
- Back in its original location
- Removed from quarantine
- Can be used normally

#### Restore Errors

If restoration fails, you'll see an error message explaining why:

**Common Errors**:

| Error Message | Cause | Solution |
|--------------|-------|----------|
| **Cannot restore: A file already exists at the original location** | Another file now exists at the same path | Manually choose a different location for the file, or delete/move the existing file first |
| **File integrity verification failed** | The quarantined file was modified or corrupted | Do NOT restore - file may be damaged or tampered with. Delete it instead. |
| **Permission denied** | You don't have write access to the original directory | Run ClamUI with appropriate permissions, or manually move the file as root |
| **Quarantine entry not found** | The database entry is missing | The file may have been deleted. Refresh the quarantine list. |
| **File not found** | The quarantined file was manually deleted from storage | The file is gone. Remove the database entry by clicking Delete. |

💡 **Troubleshooting Tip**: If you need the file but restoration fails, you can find it manually in the quarantine storage directory (see [Understanding Quarantine Storage](#understanding-quarantine-storage)) and copy it yourself.

#### After Restoring

Once a file is restored:

1. **Rescan it**: Run a scan on the restored file to verify it's still detected
   - If ClamAV still flags it → likely a real threat, quarantine again
   - If ClamAV doesn't flag it → may have been a false positive

2. **Add an exclusion** (if it's a known false positive):
   - Go to **Preferences** → **Exclusion Patterns**
   - Add the file path or a pattern to prevent future detections
   - See [Managing Exclusion Patterns](#managing-exclusion-patterns)

3. **Report false positives** (optional):
   - Visit the ClamAV false positive reporting page
   - Help improve ClamAV's detection accuracy
   - [https://www.clamav.net/reports/fp](https://www.clamav.net/reports/fp)

### Permanently Deleting Threats

If a quarantined file is genuinely malicious, you should **permanently delete** it to free up storage and ensure it cannot be accidentally restored.

⚠️ **Warning**: Deletion is **permanent and irreversible**. Once deleted, the file cannot be recovered.

#### When to Delete Files

**Delete immediately for**:
- 🔴 **CRITICAL** threats (ransomware, rootkits, bootkits)
- 🟠 **HIGH** threats (trojans, worms, backdoors) - after you're sure they're not false positives
- Known malware that you've verified is not a false positive

**Consider keeping quarantined (don't delete yet) if**:
- You're not 100% certain the file is malicious
- You want to investigate further
- The threat is **LOW** severity and might be a false positive
- You need time to verify with antivirus vendors or security forums

💡 **Best Practice**: When in doubt, keep files quarantined for a few days/weeks while you research. You can delete them later using the "Clear Old Items" feature.

#### How to Delete a File

**Step-by-Step**:

1. **Open Quarantine View**:
   - Navigate to the **Quarantine** view

2. **Find the File**:
   - Locate the quarantined threat in the list
   - Verify the threat name and path

3. **Expand the Entry**:
   - Click the file entry to expand it
   - Double-check you're deleting the right file

4. **Click Delete**:
   - Click the **Delete** button (red button)
   - A confirmation dialog appears

5. **Review the Warning**:
   ```
   Permanently Delete File?

   This will permanently delete the quarantined file:

   Threat: Win.Trojan.Generic-12345
   Size: 1.2 MB

   This action cannot be undone.

   [Cancel]  [Delete]
   ```

6. **Confirm Deletion**:
   - Verify the threat name and size
   - Click **Delete** to proceed, or **Cancel** to abort
   - **There is no undo** - be certain before confirming

7. **Wait for Completion**:
   - ClamUI deletes the file from quarantine storage
   - Removes the database entry
   - Shows success/failure message

**Success Message**:
```
✓ File deleted permanently
```

**The file is now**:
- Permanently deleted from quarantine storage
- Removed from the quarantine database
- Cannot be recovered

#### Delete Errors

If deletion fails, you'll see an error message:

**Common Errors**:

| Error Message | Cause | Solution |
|--------------|-------|----------|
| **Permission denied** | ClamUI doesn't have permission to delete the file | Check quarantine directory permissions. May need to run as different user. |
| **File not found** | File was already deleted manually | Click Refresh to update the list. The entry will be cleaned up. |
| **Quarantine entry not found** | Database entry is missing | Refresh the list. The file may have already been removed. |

💡 **Tip**: If deletion fails, you can manually delete files from the quarantine storage directory. See [Understanding Quarantine Storage](#understanding-quarantine-storage).

### Clearing Old Quarantine Items

Over time, quarantined files accumulate and use disk space. ClamUI provides a **Clear Old Items** feature to automatically remove files older than 30 days.

#### Why Clear Old Items?

**Benefits**:
- 🗑️ **Free up disk space**: Remove old threats you've forgotten about
- 🧹 **Reduce clutter**: Keep the quarantine list focused on recent detections
- ⏰ **Automatic cleanup**: Don't manually review old files one by one
- 🔒 **Safe timeframe**: 30 days is enough time to verify false positives

**When to use it**:
- After several months of use when quarantine is filling up
- When you notice quarantine storage is taking significant space
- As part of regular system maintenance (monthly/quarterly)
- When you're confident old detections are genuine threats

#### How to Clear Old Items

**Step-by-Step**:

1. **Open Quarantine View**:
   - Navigate to the **Quarantine** view

2. **Click "Clear Old Items"**:
   - Look for the **Clear Old Items** button in the header
   - Located near the Refresh button (top right of quarantine list)

3. **Review the Confirmation Dialog**:
   ```
   Clear Old Items?

   This will permanently delete 8 quarantined file(s) that are older than 30 days.

   This action cannot be undone.

   [Cancel]  [Clear Old Items]
   ```

4. **Check the Count**:
   - The dialog shows how many files will be deleted
   - Make sure the number seems reasonable
   - If it's higher than expected, consider reviewing the list first

5. **Confirm Cleanup**:
   - Click **Clear Old Items** to proceed
   - Click **Cancel** if you want to review files individually first

6. **Wait for Completion**:
   - ClamUI deletes all files older than 30 days
   - Removes database entries
   - Shows success message with count

**Success Message**:
```
✓ Removed 8 old item(s)
```

**If no old items exist**:
```
ℹ No items older than 30 days
```

#### What Gets Cleared

**Files included**:
- ✅ Any file quarantined **more than 30 days ago** (based on detection date)
- ✅ All threat types (CRITICAL, HIGH, MEDIUM, LOW)
- ✅ All file sizes

**Files excluded**:
- ❌ Files quarantined **less than 30 days ago** (kept in quarantine)
- ❌ Files you've just added this month

**Age calculation**:
- Based on the **Detection Date** field
- Calculated from current date/time
- Exactly 30 days = 30 × 24 hours from detection timestamp

💡 **Example**: If today is February 15, 2024:
- File from January 15, 2024 → Cleared (30 days old)
- File from January 16, 2024 → Kept (29 days old)
- File from February 1, 2024 → Kept (14 days old)

#### Before Clearing: Review the List

**Recommended workflow**:

1. **Sort by age** (mentally):
   - Scroll through the quarantine list
   - Older entries appear with earlier detection dates
   - Identify files from >30 days ago

2. **Check for false positives**:
   - Look for **LOW** severity threats in old entries
   - Review any files you recognize as safe
   - Restore false positives before clearing

3. **Verify critical threats**:
   - Confirm CRITICAL/HIGH threats are genuine malware
   - Research any unfamiliar threat names
   - Decide if you want to keep them longer for reference

4. **Then clear**:
   - Once you're satisfied, run "Clear Old Items"
   - Old threats are removed automatically

⚠️ **Warning**: The 30-day threshold is **fixed** and cannot be customized in the current version. If you want to keep files longer, don't use this feature - delete files individually instead.

### Understanding Quarantine Storage

Quarantined files are stored securely on your system. Understanding where and how they're stored helps with troubleshooting and advanced management.

#### Storage Location

**Default Quarantine Directory**:
```
~/.local/share/clamui/quarantine/
```

**Full path example**:
```
/home/username/.local/share/clamui/quarantine/
```

**What this means**:
- `~` = Your home directory
- `.local/share/` = User-specific application data (XDG Base Directory standard)
- `clamui/` = ClamUI's data directory
- `quarantine/` = Isolated threat storage

**Database Location**:
```
~/.local/share/clamui/quarantine.db
```

This SQLite database stores metadata for each quarantined file:
- Original file path
- Quarantine storage path
- Threat name
- Detection date/time
- File size
- SHA-256 hash (for integrity verification)

#### How Files Are Stored

When you quarantine a file, ClamUI:

1. **Generates a unique filename**:
   - Uses timestamp + random identifier
   - Example: `quarantined_20240115_143022_a3f9d8e1`
   - Original filename is NOT preserved in storage

2. **Moves the file**:
   - From original location (e.g., `/home/user/Downloads/virus.exe`)
   - To quarantine directory (e.g., `~/.local/share/clamui/quarantine/quarantined_20240115_143022_a3f9d8e1`)

3. **Calculates SHA-256 hash**:
   - Creates a cryptographic fingerprint of the file
   - Stored in database for integrity verification
   - Used to detect tampering before restoration

4. **Records metadata**:
   - All information saved to `quarantine.db`
   - Links the quarantined file to its original path

**Example quarantine storage**:
```
~/.local/share/clamui/
├── quarantine/
│   ├── quarantined_20240115_143022_a3f9d8e1   (Win.Trojan.Generic)
│   ├── quarantined_20240110_091530_b7e4f2c9   (PUA.Linux.Miner)
│   └── quarantined_20240105_182045_c1d8a3f7   (Eicar-Test-Signature)
└── quarantine.db                               (Metadata database)
```

#### File Permissions

**Security measures**:
- Quarantine directory has restricted permissions (user-only access)
- Files cannot execute from quarantine (standard file permissions)
- No special attributes needed - isolation is through location and database tracking

**Default permissions**:
- Directory: `700` (rwx------, owner read/write/execute only)
- Files: Preserve original permissions but cannot execute from this location

#### Storage Considerations

**Disk Space Usage**:
- Quarantined files consume disk space equal to their original size
- Large files (ISOs, videos) take significant space
- Monitor with: **Total Size** in quarantine view header
- Example: 50 quarantined files = ~100 MB (varies widely)

**Quota Limits**:
- No built-in quota limit
- Quarantine can grow indefinitely if not cleared
- Use "Clear Old Items" regularly to manage space
- Consider manual cleanup if storage is constrained

**Best Practices for Storage Management**:

💡 **Tips**:

1. **Regular cleanup**:
   - Use "Clear Old Items" monthly or quarterly
   - Delete confirmed threats after a few days/weeks
   - Don't keep EICAR test files in quarantine

2. **Monitor storage**:
   - Check "Total Size" indicator in Quarantine view
   - If it exceeds 500 MB, review and delete old files
   - Large quarantine may slow down list loading

3. **Delete large false positives**:
   - If you restore a large file (e.g., 100+ MB ISO)
   - It's removed from quarantine automatically
   - But if you delete without restoring, it frees space immediately

4. **Backup considerations**:
   - Do NOT include `~/.local/share/clamui/quarantine/` in backups
   - These are isolated threats - you don't want to back them up
   - The database (`quarantine.db`) can be backed up safely (only metadata)

#### Manual File Management

**Advanced users** can manually manage quarantine files:

**Viewing files**:
```bash
ls -lh ~/.local/share/clamui/quarantine/
```

**Checking storage size**:
```bash
du -sh ~/.local/share/clamui/quarantine/
```

**Manually deleting all quarantined files** (⚠️ use with caution):
```bash
rm -rf ~/.local/share/clamui/quarantine/*
rm ~/.local/share/clamui/quarantine.db
```

**Restoring a file manually** (if ClamUI fails):
```bash
# Find the original path in the database first, then:
cp ~/.local/share/clamui/quarantine/quarantined_XXXXXX /original/path/filename
```

⚠️ **Warning**: Manual management bypasses integrity checks and database updates. Only use if ClamUI's built-in features aren't working.

#### Flatpak Considerations

If you installed ClamUI via **Flatpak**, the quarantine location is different:

**Flatpak Quarantine Directory**:
```
~/.var/app/io.github.dave-kennedy.ClamUI/data/clamui/quarantine/
```

**Flatpak Database**:
```
~/.var/app/io.github.dave-kennedy.ClamUI/data/clamui/quarantine.db
```

**Accessing Flatpak quarantine**:
- Same directory structure, just different base path
- All ClamUI features work identically
- Manual file operations require Flatpak-specific paths

💡 **Tip**: You can check if you're using Flatpak by running:
```bash
flatpak list | grep -i clamui
```

If output appears, you're using the Flatpak version.

#### Troubleshooting Storage Issues

**Problem: Quarantine list shows files but directory is empty**

**Cause**: Database entries exist but files were manually deleted

**Solution**:
1. Click each entry and click **Delete** to clean up database entries
2. Or manually delete the database file (⚠️ removes all quarantine records):
   ```bash
   rm ~/.local/share/clamui/quarantine.db
   ```

**Problem: File restoration fails with "File integrity verification failed"**

**Cause**: The quarantined file was modified or corrupted in storage

**Solution**:
- Do NOT restore this file - it may be damaged or tampered with
- Delete the entry permanently
- If you need the file, obtain it from the original source again

**Problem: Quarantine view loads slowly**

**Cause**: Too many entries in the database (hundreds or thousands)

**Solution**:
1. Use "Clear Old Items" to reduce count
2. Delete old entries manually
3. Consider clearing the entire quarantine if all files are confirmed threats

**Problem: Permission denied when quarantining/restoring/deleting**

**Cause**: Incorrect file permissions on quarantine directory

**Solution**:
```bash
# Fix quarantine directory permissions:
chmod 700 ~/.local/share/clamui/quarantine/
chmod 644 ~/.local/share/clamui/quarantine.db
```

---

## Scan History

ClamUI keeps a detailed history of all your scans and virus definition updates. This allows you to review past operations, check when you last scanned specific folders, and investigate previous threat detections.

### Viewing Past Scan Results

#### Opening the Scan History View

To access your scan history:

1. Click the **"Logs"** navigation button in the sidebar (document icon)
2. The view opens with two tabs:
   - **Historical Logs** - Past scan and update operations (default)
   - **ClamAV Daemon** - Live logs from the clamd daemon (advanced users)

Make sure you're on the **Historical Logs** tab to view past scans.

#### Understanding the Historical Logs List

The logs list shows all your past operations, with the newest entries at the top:

```
┌─────────────────────────────────────────────────────────────────┐
│ Historical Logs                    [spinner] [↻] [Clear All]   │
│ Previous scan and update operations                             │
├─────────────────────────────────────────────────────────────────┤
│  📁 Clean scan of /home/user/Downloads                      ✅  │
│     2024-01-15 14:30 • clean • .../Downloads                    │
├─────────────────────────────────────────────────────────────────┤
│  🔄 Virus database update completed                         ✅  │
│     2024-01-15 09:00 • success                                  │
├─────────────────────────────────────────────────────────────────┤
│  📁 Found 1 threat(s) in /home/user/Documents               ⚠️  │
│     2024-01-14 16:45 • infected • .../Documents                 │
├─────────────────────────────────────────────────────────────────┤
│  📁 Scan error: /mnt/external                               ⚠️  │
│     2024-01-14 12:00 • error • /mnt/external                    │
└─────────────────────────────────────────────────────────────────┘
```

**Entry Components:**

- **Icon**: 📁 for scans, 🔄 for updates
- **Summary**: Brief description of what happened
- **Timestamp**: Date and time of the operation (YYYY-MM-DD HH:MM format)
- **Status**: Operation outcome (clean, infected, success, error, etc.)
- **Path**: Location that was scanned (truncated if long, showing last 40 characters)
- **Status Indicator**: ✅ for successful operations, ⚠️ for warnings/errors

#### Viewing Detailed Log Information

To see the full details of a scan or update:

1. **Click on any log entry** in the list
2. The **Log Details** panel below shows complete information:

```
SCAN LOG
==================================================

ID: 7a3b9f12-4e56-7890-abcd-ef1234567890
Timestamp: 2024-01-15T14:30:45.123456
Type: scan
Status: clean
Path: /home/user/Downloads
Duration: 12.34 seconds

Summary:
  Clean scan of /home/user/Downloads

--------------------------------------------------
Full Output:
--------------------------------------------------
Scanned: 1,234 files, 45 directories
```

**Detail Fields Explained:**

- **ID**: Unique identifier for the log entry (useful for troubleshooting)
- **Timestamp**: Full ISO format timestamp with milliseconds
- **Type**: `scan` (antivirus scan) or `update` (virus definition update)
- **Status**: Operation result
  - `clean` - No threats found
  - `infected` - Threats detected
  - `success` - Update completed successfully
  - `up_to_date` - Virus definitions already current
  - `error` - Operation failed
  - `cancelled` - User cancelled the operation
- **Path**: Full path that was scanned (only for scan operations)
- **Duration**: How long the operation took, in seconds
- **Summary**: Human-readable description
- **Full Output**: Complete details including:
  - File and directory counts
  - List of detected threats (if infected)
  - Error messages (if operation failed)
  - Raw command output

#### List Features and Navigation

**Pagination:**

The logs list displays 25 entries initially to keep the interface responsive. If you have more logs:

1. **"Show More" button** appears at the bottom
   - Click to load the next 25 entries
   - Shows current count: "Showing 25 of 150 logs"
2. **"Show All" button** (appears if 50+ remaining logs)
   - Click to load all remaining logs at once
   - Useful for searching through history

**Empty State:**

If you haven't performed any scans or updates yet, you'll see:

```
     📄
  No logs yet

  Logs from scans and updates will appear here
```

**Refresh:**

Click the **Refresh button** (🔄 icon) in the top-right to reload the log list. Useful after:

- Completing a new scan in another window
- Running scheduled scans
- Clearing logs in another ClamUI instance

**Loading State:**

While logs are loading, you'll see:

```
  ⌛ Loading logs...
```

The refresh button and Clear All button are disabled during loading.

---

### Filtering Scan History

ClamUI automatically sorts your scan history by date, showing the **newest entries first**. This ensures you always see your most recent scans at the top of the list.

#### Current Filtering Behavior

**Automatic Date Sorting:**

- Logs are sorted by timestamp in descending order (newest to oldest)
- The most recent scan or update always appears at the top
- No manual date filtering is currently available

**Viewing Older Logs:**

Use the pagination buttons to navigate through your history:

1. **Initial view**: Shows your 25 most recent operations
2. **Show More**: Loads the next 25 older entries
3. **Show All**: Displays all historical logs

#### Identifying Log Types

While there's no filter dropdown, you can easily identify log types by their icons:

- **📁 Folder icon** = Scan operation
- **🔄 Update icon** = Virus definition update

#### Finding Specific Scans

To find a particular scan in your history:

1. Look for the **path** in the subtitle (e.g., ".../Downloads")
2. Check the **timestamp** to narrow down by date
3. Check the **status indicator**:
   - ✅ Green checkmark = Clean scan or successful update
   - ⚠️ Warning symbol = Infected scan or error

**Example search workflow:**

> "I want to find when I last scanned my Documents folder for threats..."

1. Scan the list for entries showing ".../Documents" in the subtitle
2. Look for entries with ⚠️ warning indicators (infections)
3. Click the entry to view full details including threat names

💡 **Tip**: If you have many logs, use **Show All** to load everything, then use your browser's find feature (Ctrl+F) to search through the visible entries.

---

### Understanding Log Entries

#### Log Entry Structure

Every log entry contains both **summary information** (visible in the list) and **detailed information** (shown when selected).

**Summary Information** (Always Visible):

| Field | Description | Example |
|-------|-------------|---------|
| **Icon** | Visual type indicator | 📁 = scan, 🔄 = update |
| **Title** | Operation summary | "Clean scan of /home/user/Downloads" |
| **Timestamp** | When it happened | "2024-01-15 14:30" |
| **Status** | Operation outcome | "clean", "infected", "success", "error" |
| **Path** | Target location | ".../Downloads" (truncated to 40 chars) |
| **Indicator** | Visual status | ✅ = success, ⚠️ = warning/error |

**Detailed Information** (Click to View):

| Field | Description | When Present |
|-------|-------------|--------------|
| **ID** | Unique UUID | Always |
| **Timestamp** | Full ISO timestamp | Always |
| **Type** | "scan" or "update" | Always |
| **Status** | Detailed status code | Always |
| **Path** | Complete file path | Scan operations only |
| **Duration** | Operation time (seconds) | Always (0.00 if unavailable) |
| **Summary** | Human-readable description | Always |
| **Full Output** | Complete details and raw output | Always |

#### Status Meanings

**Scan Statuses:**

- **`clean`** - ✅ No threats detected
  - All scanned files are safe
  - Example: "Clean scan of /home/user/Downloads"

- **`infected`** - ⚠️ Threats found and logged
  - One or more threats detected
  - View details to see threat list
  - Example: "Found 2 threat(s) in /home/user/Documents"

- **`error`** - ⚠️ Scan failed to complete
  - Could be permission denied, path not found, or ClamAV error
  - Check Full Output for error message
  - Example: "Scan error: /mnt/external"

- **`cancelled`** - ℹ️ User stopped the scan
  - You clicked "Cancel" during scanning
  - Partial results may be available

**Update Statuses:**

- **`success`** - ✅ Database update completed
  - New virus definitions downloaded and installed
  - Example: "Virus database update completed"

- **`up_to_date`** - ✅ Already have latest definitions
  - No update needed
  - Example: "Virus definitions are up to date"

- **`error`** - ⚠️ Update failed
  - Could be network issue, permission denied, or service unavailable
  - Check Full Output for error details

#### Interpreting Full Output

When you select a log entry, the **Full Output** section shows operation-specific details.

**For Clean Scans:**

```
Scanned: 1,234 files, 45 directories
```

- **Files**: Number of individual files checked
- **Directories**: Number of folders traversed
- No threat details (scan was clean)

**For Infected Scans:**

```
Scanned: 567 files, 12 directories
Threats found: 2
  - /home/user/Documents/suspicious.exe: Win.Trojan.Generic-1234
  - /home/user/Downloads/test.pdf: Pdf.Exploit.CVE-2023-12345
```

- Shows file and directory counts
- Lists threat count
- Provides detailed threat information:
  - **Full file path** where threat was found
  - **Threat name** as identified by ClamAV

**For Errors:**

```
Error: Permission denied scanning /root/private
```

or

```
Error: Path not found: /mnt/external/backup
```

- Shows the specific error message
- Helps diagnose why the scan failed

**For Updates:**

```
Database updated successfully
Updated from version 26523 to 26524
```

or simply:

```
Virus definitions are already up to date (version 26524)
```

#### Scheduled vs Manual Scans

Log entries include a hidden `scheduled` flag indicating whether the scan was automatic:

- **Manual scans**: You started them through the UI or command line
- **Scheduled scans**: Automatically run by systemd timer or cron

Currently, both types appear the same in the UI. You can infer scheduled scans by:
- Consistent timestamps (e.g., every day at 9:00 AM)
- Scanning common profile targets (Downloads, Home Folder, Full System)

---

### Exporting Scan Logs

ClamUI lets you export log entries for record-keeping, sharing with IT support, or archival purposes.

#### Export Options

When you select a log entry, three export actions become available:

1. **Copy to Clipboard** - Quick copy for pasting into emails or documents
2. **Export to Text File** - Save as human-readable `.txt` file
3. **Export to CSV File** - Save as spreadsheet-compatible `.csv` file

All export buttons are located in the **Log Details** section header.

#### Copying to Clipboard

To quickly copy log details:

1. **Select a log entry** from the list
2. Click the **Copy button** (📋 icon) in the Log Details header
3. A toast notification confirms: "Log details copied to clipboard"
4. **Paste** (Ctrl+V) into any application

**What gets copied:**

The complete text from the Log Details panel, including:
- Header (SCAN LOG or UPDATE LOG)
- All metadata fields (ID, timestamp, status, path, duration)
- Summary
- Full output with separator lines

**Example clipboard content:**

```
SCAN LOG
==================================================

ID: 7a3b9f12-4e56-7890-abcd-ef1234567890
Timestamp: 2024-01-15T14:30:45.123456
Type: scan
Status: infected
Path: /home/user/Downloads
Duration: 12.34 seconds

Summary:
  Found 1 threat(s) in /home/user/Downloads

--------------------------------------------------
Full Output:
--------------------------------------------------
Scanned: 1,234 files, 45 directories
Threats found: 1
  - /home/user/Downloads/test.exe: Win.Trojan.Eicar-Test
```

💡 **Tip**: Use this for quick sharing via email, chat, or support tickets.

#### Exporting to Text File

To save a log entry as a text file:

1. **Select a log entry** from the list
2. Click the **Export to Text** button (💾 icon)
3. A file save dialog appears
4. **Choose a location** and optionally rename the file
   - Default name: `clamui_log_YYYYMMDD_HHMMSS.txt`
   - Example: `clamui_log_20240115_143045.txt`
5. Click **Save**
6. A toast notification confirms: "Log exported to clamui_log_20240115_143045.txt"

**Text File Format:**

The exported `.txt` file contains exactly the same content as the clipboard export:
- Plain text format
- UTF-8 encoding
- Readable in any text editor
- Same structure as displayed in the UI

**Use Cases:**

- Archiving scan results for compliance
- Creating scan reports for documentation
- Sharing with users who need human-readable format

**Export Error Handling:**

| Error | Cause | Solution |
|-------|-------|----------|
| "Permission denied" | Cannot write to selected location | Choose a location you have write access to (e.g., Documents, Downloads) |
| "Invalid file path selected" | Selected a remote/network location | Select a local folder on your computer |
| File dialog closes with no message | Cancelled by clicking "Cancel" | Normal behavior, try again |

#### Exporting to CSV File

To save a log entry as a CSV file:

1. **Select a log entry** from the list
2. Click the **Export to CSV** button (📊 icon)
3. A file save dialog appears
4. **Choose a location** and optionally rename the file
   - Default name: `clamui_log_YYYYMMDD_HHMMSS.csv`
   - Example: `clamui_log_20240115_143045.csv`
5. Click **Save**
6. A toast notification confirms: "Log exported to clamui_log_20240115_143045.csv"

**CSV File Format:**

The exported CSV file contains a header row and one data row:

| timestamp | type | status | path | summary | duration |
|-----------|------|--------|------|---------|----------|
| 2024-01-15T14:30:45.123456 | scan | clean | /home/user/Downloads | Clean scan of /home/user/Downloads | 12.34 |

**CSV Characteristics:**

- Standard RFC 4180 CSV format
- UTF-8 encoding
- Proper quoting for fields containing commas
- Opens in Excel, LibreOffice Calc, Google Sheets
- Easy to import into databases or analysis tools

**Use Cases:**

- Importing into spreadsheet software for analysis
- Creating scan history reports with charts
- Bulk processing scan data with scripts
- Compliance reporting requiring structured data

💡 **Tip**: To create a comprehensive scan history CSV with all your logs, you'll need to export each entry individually and then combine them. The CSV format makes this easy - just copy the data rows (excluding headers) and paste into a master spreadsheet.

#### Exporting Multiple Logs

**Current Limitation:**

ClamUI currently exports one log entry at a time. There's no "Export All" button.

**Workaround for Bulk Export:**

If you need all your scan history:

1. Locate the log storage directory:
   - Default: `~/.local/share/clamui/logs/`
   - Flatpak: `~/.var/app/com.github.davesteele.ClamUI/data/clamui/logs/` (if applicable)
2. **Copy the entire directory** to your desired backup location
3. Each log is stored as `<UUID>.json` (e.g., `7a3b9f12-4e56-7890-abcd-ef1234567890.json`)
4. Use a script or JSON tools to process these files if needed

**Manual JSON Processing Example:**

```bash
# List all log files
ls ~/.local/share/clamui/logs/

# View a specific log
cat ~/.local/share/clamui/logs/7a3b9f12-4e56-7890-abcd-ef1234567890.json | jq

# Count total logs
ls ~/.local/share/clamui/logs/*.json | wc -l
```

---

### Viewing Daemon Logs (Advanced)

The **ClamAV Daemon** tab shows live logs from the clamd background service. This is useful for troubleshooting daemon-related issues or monitoring real-time activity.

#### Opening Daemon Logs

1. Navigate to **Logs** view
2. Click the **ClamAV Daemon** tab at the top
3. The daemon status and log viewer appear

#### Understanding Daemon Status

The status row shows clamd's current state:

**🟢 Running:**
- Daemon is active and ready to scan
- Live log updates available
- Example: "Daemon Status: Running"

**⚪ Stopped:**
- Daemon is installed but not running
- Start it with: `sudo systemctl start clamav-daemon`
- Live logs unavailable

**ℹ️ Not installed:**
- clamd package not detected
- ClamUI can still scan using `clamscan` command
- Helpful message explains daemon is optional

**❓ Unknown:**
- Unable to determine daemon status
- May indicate permission issues or system configuration

#### Using Live Log Updates

To view real-time daemon logs:

1. Ensure daemon status shows **"Running"**
2. Click the **Play button** (▶️) to start live updates
   - Button changes to ⏸️ (pause icon)
   - Tooltip changes to "Stop live log updates"
3. Logs refresh automatically every 3 seconds
4. Scroll automatically jumps to newest entries
5. Click **Pause** (⏸️) to stop auto-refresh

**What You'll See:**

```
Mon Jan 15 14:30:01 2024 -> +++ Started at Mon Jan 15 14:30:01 2024
Mon Jan 15 14:30:01 2024 -> clamd daemon 1.0.0 (OS: linux-gnu, ARCH: x86_64)
Mon Jan 15 14:30:01 2024 -> Log file size limit disabled.
Mon Jan 15 14:30:01 2024 -> Reading databases from /var/lib/clamav
Mon Jan 15 14:30:03 2024 -> Database correctly loaded (7654321 signatures)
Mon Jan 15 14:30:03 2024 -> TCP: Bound to address [::]:3310
Mon Jan 15 14:30:03 2024 -> Running as user clamav (UID 108, GID 113)
Mon Jan 15 14:35:12 2024 -> /home/user/Downloads/file.txt: OK
```

**Log Entry Types:**

- **Startup messages**: Daemon initialization, database loading
- **Scan results**: Files scanned via daemon (`OK`, `FOUND`)
- **Database updates**: When freshclam updates definitions
- **Connection events**: Client connections and disconnections
- **Errors**: Permission issues, configuration problems

#### Viewing in Fullscreen

For easier reading of long daemon logs:

1. Click the **Fullscreen button** (⛶ icon) in the Daemon Logs header
2. A fullscreen dialog opens with the complete log content
3. Read and scroll comfortably in the expanded view
4. **Close** or press **Escape** to return

💡 **Tip**: Use fullscreen mode when diagnosing daemon issues or copying large portions of logs for support tickets.

#### Troubleshooting Daemon Log Access

**"Permission denied" errors:**

If you see permission errors reading `/var/log/clamav/clamd.log`:

```
Permission denied reading /var/log/clamav/clamd.log

The daemon log file requires elevated permissions.
Options:
  • Add your user to the 'adm' or 'clamav' group:
    sudo usermod -aG adm $USER
  • Or check if clamd logs to systemd journal:
    journalctl -u clamav-daemon
```

**Solutions:**

1. **Add yourself to the log-reading group:**
   ```bash
   sudo usermod -aG adm $USER
   ```
   Then log out and back in for changes to take effect.

2. **Use journalctl instead** (if clamd uses systemd):
   ```bash
   journalctl -u clamav-daemon -n 100 --no-pager
   ```

3. **Check if clamd is actually running:**
   ```bash
   systemctl status clamav-daemon
   ```

**"Daemon log file not found" errors:**

ClamUI checks these locations automatically:
- `/var/log/clamav/clamd.log`
- `/var/log/clamd.log`
- Log path from `/etc/clamav/clamd.conf`

If none exist, clamd may not be installed or may log to journalctl instead.

---

### Managing Your Log History

#### Clearing Old Logs

Over time, your log history can grow large. Clear old logs to free up disk space:

1. Navigate to **Logs** view → **Historical Logs** tab
2. Click **Clear All** button in the top-right
3. A confirmation dialog appears:
   ```
   Clear All Logs?

   This will permanently delete all historical logs.
   This action cannot be undone.

   [Cancel]  [Clear All]
   ```
4. Click **Clear All** to confirm (button is red/destructive)
5. All log entries are deleted immediately
6. The empty state appears: "No logs yet"

⚠️ **Warning**: This action is permanent and cannot be undone. Export important logs before clearing.

💡 **Tip**: If you want to preserve certain logs, export them to text or CSV files before clearing.

#### Log Storage Location

Logs are stored as individual JSON files on your system:

**Default Installation:**
```
~/.local/share/clamui/logs/
├── 7a3b9f12-4e56-7890-abcd-ef1234567890.json
├── b2c4d5e6-f789-0123-4567-89abcdef0123.json
└── ... (one file per log entry)
```

**Flatpak Installation** (if applicable):
```
~/.var/app/com.github.davesteele.ClamUI/data/clamui/logs/
```

**Storage Considerations:**

- Each log entry is typically 500 bytes to 2 KB
- 1,000 logs ≈ 1-2 MB of disk space
- JSON format is human-readable if you open files directly
- Files are named by UUID (matches the ID field in log details)

**Manual Log Management:**

For advanced users, you can manage logs directly:

```bash
# View log count
ls ~/.local/share/clamui/logs/*.json | wc -l

# Check storage usage
du -sh ~/.local/share/clamui/logs/

# Backup all logs
cp -r ~/.local/share/clamui/logs/ ~/clamui-logs-backup/

# Delete logs older than 30 days
find ~/.local/share/clamui/logs/ -name "*.json" -mtime +30 -delete

# View a specific log file
cat ~/.local/share/clamui/logs/<UUID>.json | jq
```

⚠️ **Warning**: Manually deleting log files bypasses the UI's "Clear All" confirmation dialog. Be certain before running manual deletion commands.

---

### Log History Best Practices

**Regular Review:**

- Check logs weekly to ensure scans are running as expected
- Verify scheduled scans are completing successfully
- Investigate any recurring errors

**Export Important Findings:**

- Export logs showing threat detections for your records
- Save CSV exports for monthly/quarterly security reports
- Keep text exports when reporting false positives to ClamAV

**Periodic Cleanup:**

- Clear very old logs (6+ months) if you don't need historical data
- Or export to backup before clearing to free up space
- Consider disk space if you perform many scans daily

**Compliance and Auditing:**

- Use log exports to demonstrate regular antivirus scanning
- CSV format makes it easy to generate scan frequency reports
- Logs include precise timestamps for audit trails

**Troubleshooting:**

- Check logs when scans fail to understand what went wrong
- Compare clean vs infected scan outputs to identify patterns
- Use daemon logs to diagnose clamd connection issues

💡 **Tip**: Set a monthly reminder to review your scan history and export any logs you need to keep before clearing the rest.

---

## Scheduled Scans

Set up automatic virus scanning to protect your system without manual intervention. ClamUI's scheduled scans run in the background at your chosen times, keeping your computer safe while you work.

### Why Use Scheduled Scans?

Scheduled scans provide continuous protection by automatically scanning your system at regular intervals.

**Key Benefits**:

1. **Automatic Protection**: Scans run without manual intervention
2. **Consistent Coverage**: Regular scanning catches threats quickly
3. **Flexible Scheduling**: Choose when scans run to avoid interrupting work
4. **Battery-Aware**: Automatically skip scans on laptops when unplugged
5. **Auto-Quarantine**: Optionally isolate threats immediately when found

**Common Use Cases**:

- **Daily Downloads Scan**: Check your Downloads folder every evening for threats
- **Weekly Home Scan**: Scan your home directory every Sunday night
- **Monthly Full Scan**: Deep scan of your entire system once per month
- **USB Drive Scanning**: Regular scans of external drives when connected
- **After Hours Scanning**: Heavy scans during lunch breaks or overnight

💡 **Tip**: Schedule scans during low-activity periods (early morning, lunch, overnight) to minimize system impact.

---

### Enabling Automatic Scanning

Configure scheduled scans through the Preferences window.

#### Opening Scheduled Scans Settings

1. Click the **menu button** (☰) in the header bar
2. Select **Preferences**
3. Navigate to **Scheduled Scans** page (on the left sidebar)

The Scheduled Scans page contains all configuration options:

```
┌─────────────────────────────────────────────────┐
│ Scheduled Scans Configuration                   │
├─────────────────────────────────────────────────┤
│ ⚙ Enable Scheduled Scans              [Toggle] │
│   Run automatic scans at specified intervals    │
│                                                  │
│ 📅 Scan Frequency             [Daily ▼]         │
│ 🕐 Scan Time                  [02:00]           │
│ 📁 Scan Targets               [~/]              │
│ 🔋 Skip on Battery             [✓]              │
│ 🔒 Auto-Quarantine            [ ]               │
└─────────────────────────────────────────────────┘
```

#### Enabling Scheduled Scans

1. Open the **Scheduled Scans** page in Preferences
2. Toggle **Enable Scheduled Scans** to ON
3. Configure your preferences (frequency, time, targets - see sections below)
4. Click **Save & Apply** at the bottom of the Preferences window
5. Close Preferences

**What happens when you enable**:
- ClamUI creates a system-level scheduled task (systemd timer or cron job)
- The schedule persists across system restarts
- Scans run even when the ClamUI GUI is closed
- You receive desktop notifications when scans complete

#### Disabling Scheduled Scans

1. Open the **Scheduled Scans** page in Preferences
2. Toggle **Enable Scheduled Scans** to OFF
3. Click **Save & Apply**

**What happens when you disable**:
- The system-level scheduled task is removed
- No automatic scans will run
- Existing scan history is preserved
- You can still run manual scans anytime

⚠️ **Important**: You must click **Save & Apply** for changes to take effect. Simply toggling the switch is not enough.

---

### Choosing Scan Frequency

Select how often scheduled scans should run.

#### Available Frequencies

**Hourly** - Scans run every hour on the hour (e.g., 1:00, 2:00, 3:00)

- **Best for**: Critical systems requiring frequent checks
- **Use case**: Servers or public computers handling many downloads
- **System impact**: High - scans run 24 times per day
- **Duration**: Only suitable for small scan targets (Downloads folder)
- **Recommendation**: Use sparingly; usually too frequent for desktops

**Daily** - Scans run once per day at your specified time

- **Best for**: Most users and typical protection needs
- **Use case**: Daily Downloads folder scans, evening home directory scans
- **System impact**: Low - single scan per day
- **Duration**: 2-30 minutes depending on targets
- **Recommendation**: ✅ **Recommended for most users**

**Weekly** - Scans run once per week on your chosen day

- **Best for**: Larger scan jobs like full home directory scans
- **Use case**: Weekend full scans, weekly document folder checks
- **System impact**: Very low - single scan per week
- **Duration**: 10-60 minutes depending on targets
- **Recommendation**: Good for comprehensive scans without daily overhead

**Monthly** - Scans run once per month on your chosen day

- **Best for**: Full system scans and comprehensive checks
- **Use case**: Complete system scan on the 1st of each month
- **System impact**: Minimal - single scan per month
- **Duration**: 30-120+ minutes for full system scan
- **Recommendation**: Good for thorough monthly security audits

#### Selecting Frequency

1. Open **Preferences** → **Scheduled Scans**
2. Click the **Scan Frequency** dropdown
3. Select your desired frequency:
   - Hourly
   - Daily
   - Weekly
   - Monthly
4. Configure additional settings based on frequency (see next section)
5. Click **Save & Apply**

**Frequency-Specific Settings**:

| Frequency | Additional Settings | Notes |
|-----------|---------------------|-------|
| Hourly | None | Runs at :00 of every hour |
| Daily | Scan Time (HH:MM) | Choose what time to run |
| Weekly | Day of Week + Scan Time | Choose day (Mon-Sun) and time |
| Monthly | Day of Month (1-28) + Scan Time | Choose day (1-28) and time |

💡 **Tip**: Start with **Daily** scans of your Downloads folder, then add **Weekly** home scans if needed.

---

### Setting Scan Times

Configure when your scheduled scans run.

#### Understanding Scan Time

**Format**: 24-hour time (HH:MM)
- `02:00` = 2:00 AM
- `14:30` = 2:30 PM
- `23:45` = 11:45 PM

**Default**: `02:00` (2:00 AM)

**Applies to**: Daily, Weekly, and Monthly scans (Hourly scans always run at :00)

#### Choosing the Best Time

**Early Morning (2:00 - 6:00 AM)** ✅ Recommended

- **Pros**: Computer likely idle, scans complete before work starts
- **Cons**: Computer must be on (or wake-on-timer configured)
- **Best for**: Desktop computers left on overnight
- **Example**: `02:00` for minimal interference

**Evening (19:00 - 23:00)**

- **Pros**: Computer still on, scans during low-activity evening
- **Cons**: May slow down evening browsing/entertainment
- **Best for**: Laptops that aren't left on overnight
- **Example**: `20:00` after dinner

**Lunch/Break Times (12:00 - 14:00)**

- **Pros**: Minimal work disruption during lunch
- **Cons**: Computer must be on and awake
- **Best for**: Work computers with regular lunch breaks
- **Example**: `12:30` during lunch hour

**After Hours (18:00 - 22:00)**

- **Pros**: Work is done, computer still on
- **Cons**: May interfere with personal computer use
- **Best for**: Work-only computers
- **Example**: `18:15` just after work hours

#### Setting the Time

1. Open **Preferences** → **Scheduled Scans**
2. Find the **Scan Time** field
3. Enter time in 24-hour format (e.g., `02:00`, `14:30`, `20:00`)
4. Click **Save & Apply**

**Valid Time Formats**:
- ✅ `02:00` - Correct (2:00 AM)
- ✅ `14:30` - Correct (2:30 PM)
- ✅ `23:59` - Correct (11:59 PM)
- ❌ `2:00` - Missing leading zero
- ❌ `14:30:45` - Seconds not supported
- ❌ `2:00 PM` - 12-hour format not supported

⚠️ **Important**: Your computer must be powered on at the scheduled time for scans to run. Most laptops don't support wake-on-timer by default.

#### Day of Week (Weekly Scans)

For weekly scans, choose which day the scan runs:

1. Set **Scan Frequency** to **Weekly**
2. Click the **Day of Week** dropdown
3. Select your preferred day:
   - Monday
   - Tuesday
   - Wednesday
   - Thursday
   - Friday
   - Saturday ✅ Recommended for home users
   - Sunday ✅ Recommended for home users
4. Set your preferred **Scan Time**
5. Click **Save & Apply**

**Recommendation**: Weekend days (Saturday/Sunday) at early morning hours (e.g., Sunday 02:00).

#### Day of Month (Monthly Scans)

For monthly scans, choose which day of the month the scan runs:

1. Set **Scan Frequency** to **Monthly**
2. Use the **Day of Month** spinner to select a day (1-28)
3. Set your preferred **Scan Time**
4. Click **Save & Apply**

**Day Range**: 1-28 only (ensures scan runs every month, even February)

**Common Choices**:
- **1st of month**: Start each month with a clean scan
- **15th of month**: Mid-month comprehensive check
- **Last week**: Use day 28 for near-end-of-month scans

💡 **Tip**: Choose day 1 (first of month) for easy-to-remember monthly scans.

---

### Configuring Scan Targets

Specify which files and folders to scan automatically.

#### Understanding Scan Targets

**Scan targets** are the paths that ClamUI will scan during scheduled scans.

**Target Format**:
- Comma-separated list of paths
- Example: `/home/user/Downloads, /home/user/Documents`
- Example: `~/Downloads, ~/Documents` (tilde ~ = your home directory)

**Default Target**: Your home directory (`~` or `/home/username`)

**How Scanning Works**:
- Each target is scanned **recursively** (includes all subdirectories)
- Multiple targets are scanned sequentially (one after another)
- Scan duration depends on total size and file count across all targets

#### Recommended Scan Targets

**Downloads Folder Only** - ✅ Recommended for daily scans

```
~/Downloads
```

- **Scan time**: 10-30 seconds (typical)
- **File count**: 50-200 files
- **Best for**: Daily scans to catch threats quickly
- **Why**: Most threats arrive via downloads

**Home Directory** - Good for weekly scans

```
~
```

- **Scan time**: 10-30 minutes (typical)
- **File count**: 50,000-200,000 files
- **Best for**: Weekly comprehensive scans
- **Why**: Covers all user data without system files

**Multiple Specific Folders** - Customized protection

```
~/Downloads, ~/Documents, ~/Pictures
```

- **Scan time**: Varies by folder size
- **File count**: Varies
- **Best for**: Targeted scanning of important folders
- **Why**: Focus on data you care about

**Full System** - For monthly deep scans

```
/
```

- **Scan time**: 30-120+ minutes
- **File count**: 500,000+ files
- **Best for**: Monthly full system audits
- **Why**: Complete system coverage
- ⚠️ **Warning**: Very slow, only suitable for monthly scans

**External Drives** - Monitor USB drives and backups

```
/media/username/USB-Drive, ~/Backups
```

- **Scan time**: Varies by drive size
- **File count**: Varies
- **Best for**: Regular checks of external media
- **Why**: USB drives are common malware vectors
- ⚠️ **Note**: Drive must be connected at scan time

#### Setting Scan Targets

1. Open **Preferences** → **Scheduled Scans**
2. Find the **Scan Targets** field
3. Enter your target paths, separated by commas:
   - Use full paths: `/home/user/Downloads, /home/user/Documents`
   - Or use tilde shortcuts: `~/Downloads, ~/Documents`
   - Or mix both: `~/Downloads, /media/usb`
4. Click **Save & Apply**

**Path Tips**:
- ✅ Use `~` for home directory (portable across users)
- ✅ Separate multiple paths with commas
- ✅ Both absolute and relative paths work
- ❌ Don't include quotes around paths
- ❌ Don't use wildcards (* or ?)

**Example Configurations**:

| Use Case | Frequency | Targets | Rationale |
|----------|-----------|---------|-----------|
| Basic protection | Daily | `~/Downloads` | Catch threats as they arrive |
| Home user | Daily + Weekly | `~/Downloads` (daily)<br>`~` (weekly) | Daily quick scans + weekly full scans |
| Privacy-conscious | Weekly | `~/Downloads, ~/Documents, ~/Pictures` | Skip browser cache and config files |
| Developer | Daily | `~/Downloads, ~/projects` | Protect code and downloads |
| Server admin | Daily | `/var/www, /home` | Web files and user directories |

💡 **Recommendation**: Start with `~/Downloads` for daily scans. Add more targets only if needed.

---

### Battery-Aware Scanning

Automatically skip scans when your laptop is running on battery power.

#### What is Battery-Aware Scanning?

**Battery-aware scanning** checks your laptop's power status before running scheduled scans:

- **Plugged in (AC power)**: Scan runs normally
- **On battery (unplugged)**: Scan is skipped to save battery life

**Default**: Enabled (Skip on Battery = ON)

**Applies to**: Laptops and devices with batteries (desktops always run scans)

#### How It Works

When a scheduled scan is triggered:

1. **Check power status**: Is the laptop plugged in?
2. **If plugged in**: Run the scan normally
3. **If on battery**: Skip the scan and log the skip event
4. **Next schedule**: The scan will try again at the next scheduled time

**What happens when skipped**:
- A log entry is created: "Scheduled scan skipped (on battery power)"
- No notification is shown (to avoid interruptions)
- The scan is **not rescheduled** - it waits until the next normal schedule
- Battery percentage is recorded in the log

**Example scenario**:
- You schedule daily scans at 2:00 AM
- Your laptop is unplugged at night
- Scan is skipped on Monday night (on battery)
- Scan runs on Tuesday night (plugged in while charging)

#### When to Use Battery-Aware Scanning

**Enable "Skip on Battery" (✓)** - ✅ Recommended

Good for:
- Laptops used unplugged frequently
- Battery life is a priority
- You charge overnight regularly
- Casual home use

Benefits:
- Preserves battery life
- Reduces CPU load when unplugged
- Scans still run when plugged in
- No performance impact during mobile use

**Disable "Skip on Battery" ( )** - Force scans even on battery

Good for:
- Critical systems requiring guaranteed scans
- Laptops plugged in most of the time
- Security is more important than battery life
- Desktop computers (no battery to preserve)

Drawbacks:
- Drains battery faster
- May slow down laptop when unplugged
- Increases CPU usage on battery
- Reduces mobile battery life by 10-30 minutes (typical scan)

#### Enabling/Disabling Battery-Aware Scanning

1. Open **Preferences** → **Scheduled Scans**
2. Find the **Skip on Battery** switch
3. **Enable** (✓) to skip scans when on battery (recommended for laptops)
4. **Disable** ( ) to run scans regardless of power status
5. Click **Save & Apply**

**Desktop Computers**:
Desktop computers without batteries are always treated as "plugged in", so this setting has no effect.

#### Checking Battery Skip Events

To see when scans were skipped due to battery:

1. Open the **Logs** view (click Logs in the navigation)
2. Look for log entries with status: "Skipped"
3. Summary will say: "Scheduled scan skipped (on battery power)"
4. Details show battery percentage at skip time

Example log entry:
```
Date: 2026-01-03 02:00
Status: Skipped
Summary: Scheduled scan skipped (on battery power)
Details:
  Battery level: 67%
  Scan skipped due to battery-aware settings.
```

💡 **Tip**: If you notice scans being skipped frequently, consider:
- Scheduling scans during times when you're typically plugged in (evening while working)
- Plugging in your laptop overnight if you schedule early morning scans
- Disabling "Skip on Battery" if scans rarely run

---

### Auto-Quarantine Options

Automatically isolate detected threats without manual intervention.

#### What is Auto-Quarantine?

**Auto-quarantine** automatically moves infected files to quarantine when they're detected during scheduled scans.

**Manual Scans**: Always require manual action (you choose whether to quarantine)

**Scheduled Scans**: Can optionally quarantine automatically with this setting

**Default**: Disabled (Auto-Quarantine = OFF) for safety

#### How Auto-Quarantine Works

**When enabled** and a scheduled scan finds threats:

1. **Scan completes** and identifies infected files
2. **Automatic quarantine**: Each infected file is moved to quarantine storage
3. **Integrity hash**: SHA-256 hash is calculated for each file
4. **Metadata saved**: Original path, threat name, date are recorded
5. **Notification**: You receive a notification with quarantine count
6. **Log entry**: Detailed log shows "X threats found, Y quarantined"

**What gets quarantined**:
- All files detected as infected (regardless of severity)
- Both individual files and files within archives
- Files from all scan targets

**What happens to quarantined files**:
- ✅ Moved to secure quarantine storage (`~/.local/share/clamui/quarantine/`)
- ✅ Isolated from the rest of your system
- ✅ Can be reviewed in the Quarantine view
- ✅ Can be restored if false positive (with hash verification)
- ✅ Can be permanently deleted
- ✅ Auto-cleared after 30 days with "Clear Old Items"

#### Automatic vs Manual Quarantine

| Aspect | Manual (Default) | Auto-Quarantine (Enabled) |
|--------|------------------|---------------------------|
| **Action** | You review threats and choose whether to quarantine | Threats quarantined immediately |
| **Notification** | Shows threat count, requires your review | Shows threat + quarantine count |
| **Safety** | ✅ Safer - you control what's quarantined | ⚠️ Riskier - false positives quarantined too |
| **Convenience** | ❌ Requires manual action | ✅ Fully automatic |
| **Review** | Before quarantine | After quarantine (via Logs + Quarantine views) |
| **Best for** | Users who want control | Users who want hands-off protection |
| **False positives** | You can skip quarantine | Automatically quarantined, must restore later |

#### When to Enable Auto-Quarantine

**Enable Auto-Quarantine (✓)**

Good for:
- Fully automated protection ("set and forget")
- Systems handling untrusted files frequently
- Users who don't want to review every detection
- Downloads folders with high malware risk
- Servers and unattended systems

Benefits:
- Threats are isolated immediately
- No manual intervention required
- Full protection even when you're away
- Automated response to threats

Risks:
- ⚠️ False positives are automatically quarantined
- ⚠️ Important files might be removed without your knowledge
- ⚠️ You must check logs and quarantine view to know what happened

**Disable Auto-Quarantine ( )** - ✅ Recommended for most users

Good for:
- Users who want control over quarantine decisions
- Systems with important files that might trigger false positives
- Users who review scan results regularly
- Development environments (source code might trigger heuristics)
- Document folders with macros or scripts

Benefits:
- ✅ You choose what to quarantine
- ✅ Review each detection before taking action
- ✅ Avoid accidentally quarantining false positives
- ✅ Understand what was detected and why

Drawbacks:
- Requires manual review of scheduled scan results (check Logs view)
- Threats remain in place until you quarantine them manually

#### Enabling/Disabling Auto-Quarantine

1. Open **Preferences** → **Scheduled Scans**
2. Find the **Auto-Quarantine** switch
3. **Enable** (✓) to automatically quarantine all detected threats
4. **Disable** ( ) to require manual review (recommended)
5. Click **Save & Apply**

⚠️ **Important Recommendation**: Start with auto-quarantine **disabled**. Enable it only after:
- Running several scheduled scans to understand what gets detected
- Verifying your scan targets don't trigger frequent false positives
- Understanding how to review and restore files from quarantine

#### Reviewing Auto-Quarantined Files

If you enable auto-quarantine, regularly check what was quarantined:

**Via Logs View** (see what scans found):

1. Open **Logs** view
2. Look for scheduled scan entries (check timestamp matching your schedule)
3. Read the summary: "Scheduled scan found X threats, Y quarantined"
4. Expand the log to see detailed threat information
5. Note: Each threat's name, path, severity, and category

**Via Quarantine View** (see what was quarantined):

1. Open **Quarantine** view
2. Review quarantined files by threat name and original path
3. Check detection date to match scheduled scan times
4. **If false positive**: Restore the file (see Quarantine Management section)
5. **If legitimate threat**: Leave in quarantine or delete permanently

**Notifications** (immediate alerts):

When auto-quarantine runs, you'll receive a notification:
```
┌────────────────────────────────────┐
│ 🔴 Scheduled Scan: Threats Detected│
│                                    │
│ 3 infected files found,            │
│ 3 quarantined                      │
│                                    │
│ 2 minutes ago                      │
└────────────────────────────────────┘
```

Click the notification to open ClamUI and review the scan logs.

💡 **Best Practice**: Check the Logs view once a week to review what scheduled scans found, even with auto-quarantine enabled.

#### Quarantine Failures

If auto-quarantine is enabled but quarantine fails for some files:

**Possible causes**:
- File no longer exists (deleted between detection and quarantine)
- Insufficient permissions (file owned by root or another user)
- File in use (locked by another application)
- Disk space full (no room for quarantine storage)

**What happens**:
- Scan continues and logs the failure
- Successfully quarantined files are still quarantined
- Failed files remain in their original location ⚠️
- Log entry shows: "Found X threats, Y quarantined, Z failed"

**How to check**:
1. Open **Logs** view
2. Expand the scheduled scan entry
3. Look for "Quarantine Failed" section in details
4. Each failed file is listed with error reason

**How to handle**:
- Manual quarantine: Find the file and quarantine it via a manual scan
- Fix permissions: Change file ownership or permissions
- Delete manually: If it's confirmed malware, delete via terminal with sudo

---

### Managing Scheduled Scans

Monitor, test, and troubleshoot your scheduled scan configuration.

#### Checking Scheduled Scan Status

**Via Preferences** (current configuration):

1. Open **Preferences** → **Scheduled Scans**
2. Check the **Enable Scheduled Scans** switch:
   - ✅ ON = Scheduled scans are active
   - ⚪ OFF = Scheduled scans are disabled
3. Review your current configuration:
   - Frequency, time, targets, battery skip, auto-quarantine

**Via System Commands** (advanced - verify backend):

ClamUI uses your system's scheduler (systemd or cron). To check the backend:

**For systemd (most modern Linux)**:

```bash
# Check if timer is active
systemctl --user is-active clamui-scheduled-scan.timer

# View timer status
systemctl --user status clamui-scheduled-scan.timer

# List all timers to see when next scan runs
systemctl --user list-timers clamui-scheduled-scan.timer
```

**For cron (older systems)**:

```bash
# View your crontab (look for "ClamUI Scheduled Scan")
crontab -l
```

#### Testing Your Schedule

Before relying on scheduled scans, test that they work:

**Option 1: Trigger a Test Scan Manually**

Since scheduled scans use the same `clamui-scheduled-scan` command, you can test it manually:

```bash
# Test with dry-run (shows what would happen without scanning)
clamui-scheduled-scan --dry-run --verbose

# Run a real test scan
clamui-scheduled-scan --verbose
```

This runs the scan immediately with your configured settings and shows verbose output.

**Option 2: Temporarily Change Schedule Time**

1. Note your current schedule time
2. Change it to 2-3 minutes in the future
3. Click **Save & Apply**
4. Wait for the scheduled time
5. Check the **Logs** view for a new scan entry
6. Change time back to your desired schedule
7. Click **Save & Apply** again

**Option 3: Check Logs After First Scheduled Run**

1. Wait until after your first scheduled scan time
2. Open **Logs** view
3. Look for a scan entry matching your scheduled time
4. Verify the scan ran and completed successfully

**What successful scheduled scans look like**:

In the Logs view:
```
📁 Scheduled scan completed - 1,234 files scanned, no threats
   2026-01-03 02:00 • Clean • ~/Downloads

Click to expand:
  Scan Duration: 12.3 seconds
  Files Scanned: 1,234
  Threats Found: 0
  Targets: /home/user/Downloads
```

#### Modifying Your Schedule

To change scheduled scan settings:

1. Open **Preferences** → **Scheduled Scans**
2. Modify any setting:
   - Toggle **Enable Scheduled Scans** to disable entirely
   - Change **Scan Frequency** (hourly/daily/weekly/monthly)
   - Update **Scan Time** (HH:MM in 24-hour format)
   - Edit **Scan Targets** (comma-separated paths)
   - Toggle **Skip on Battery** or **Auto-Quarantine**
3. **Must click Save & Apply** for changes to take effect
4. Close Preferences

⚠️ **Important**: Simply changing values doesn't update the schedule. You **must** click **Save & Apply** for ClamUI to update the system scheduler.

#### Viewing Scheduled Scan History

All scheduled scans are logged separately from manual scans:

1. Open the **Logs** view
2. Look for scan entries matching your scheduled time
3. Scheduled scans show:
   - 📁 Folder icon
   - Timestamp matching your schedule (e.g., 02:00, 14:00)
   - "Scheduled scan" in the summary
4. Click an entry to see full details

**Identifying scheduled vs manual scans**:
- Scheduled scans have precise times matching your schedule (02:00, not 02:03)
- Summary explicitly says "Scheduled scan..."
- Internal metadata marks them as `scheduled=true` (not visible in UI)

#### Troubleshooting Scheduled Scans

**Problem: Scans aren't running at scheduled time**

Possible causes and solutions:

| Cause | How to Check | Solution |
|-------|--------------|----------|
| Schedule not enabled | Check Preferences → Scheduled Scans → Enable switch | Toggle ON and click Save & Apply |
| Forgot to click "Save & Apply" | Check system timer (see commands above) | Go to Preferences and click Save & Apply |
| Computer is off at scheduled time | Check if computer is on during schedule | Change schedule time or leave computer on |
| On battery (Skip on Battery enabled) | Check Logs for "skipped" entries | Disable Skip on Battery or plug in at scheduled time |
| Systemd/cron not available | Run test commands (see above) | Check system logs, may need systemd or cron installed |
| No scan targets configured | Check Preferences → Scan Targets field | Add at least one valid path |
| Invalid scan target paths | Check Logs for error entries | Fix paths in Preferences (use ~ or full paths) |

**Problem: No notification shown after scheduled scan**

Possible causes:
- Notifications disabled in ClamUI Preferences
- Notifications disabled at system level
- Desktop notification service not running
- Scan ran while you were logged out

Solutions:
- Check **Preferences** → ensure notifications are enabled
- Check **Logs** view - scan logs are always recorded even without notifications
- Test notification system: `notify-send "Test" "This is a test"`

**Problem: Scheduled scan found threats but didn't quarantine**

Possible causes:
- Auto-Quarantine is disabled (this is normal and expected)
- Quarantine failed due to permissions or disk space

Solutions:
- If auto-quarantine disabled: Review Logs, then manually scan and quarantine
- If auto-quarantine enabled: Check Logs for "Quarantine Failed" section
- Fix permissions or free disk space, then re-scan manually

**Problem: Can't save scheduled scan settings (permission error)**

This shouldn't happen for scheduled scans (they don't require root), but if you see errors:

Solutions:
- Check that ~/.config/systemd/user/ directory exists: `mkdir -p ~/.config/systemd/user`
- Verify you have write permissions: `ls -ld ~/.config/systemd/user`
- Check disk space: `df -h ~`
- Try creating the schedule via terminal (see command-line option below)

#### Command-Line Scheduled Scan (Advanced)

For advanced users, you can run scheduled scans manually or customize further:

**Basic manual execution**:
```bash
clamui-scheduled-scan
```

**With options**:
```bash
# Scan specific targets
clamui-scheduled-scan --target ~/Downloads --target ~/Documents

# Skip scan if on battery
clamui-scheduled-scan --skip-on-battery

# Auto-quarantine detected threats
clamui-scheduled-scan --auto-quarantine

# Combine options
clamui-scheduled-scan --skip-on-battery --auto-quarantine --target ~/Downloads

# Dry run (test without scanning)
clamui-scheduled-scan --dry-run --verbose

# Verbose output
clamui-scheduled-scan --verbose
```

**Use cases**:
- Testing scheduled scan configuration
- Running scans from custom scripts
- Triggering scans from other automation tools
- Debugging scheduling issues

**Help**:
```bash
clamui-scheduled-scan --help
```

#### Scheduler Backend Information

ClamUI automatically detects and uses the best available scheduler:

**systemd timers** (preferred - modern Linux):
- More reliable and flexible
- Better logging and status checking
- Shows next run time
- Handles missed scans (persistent timers)
- Used by: Ubuntu 16.04+, Fedora, Arch, most modern distros

**cron** (fallback - older systems):
- Traditional Unix scheduler
- Works on older systems
- Less flexible than systemd
- Used by: Systems without systemd, older distributions

**Detection**:
ClamUI automatically detects which is available and uses it transparently. You don't need to choose.

**Which backend am I using?**

Run this command to check:
```bash
# Check for systemd timer
systemctl --user is-active clamui-scheduled-scan.timer 2>/dev/null && echo "Using systemd"

# Check for cron
crontab -l 2>/dev/null | grep -q "ClamUI Scheduled Scan" && echo "Using cron"
```

💡 **Tip**: If neither systemd nor cron is available, you'll see an error when trying to enable scheduled scans. Install systemd (recommended) or cron to enable this feature.

---

**Scheduled Scans Summary**:

✅ **Do**:
- Start with daily Downloads folder scans
- Use early morning times (2:00-6:00 AM) when computer is idle
- Enable "Skip on Battery" on laptops to preserve battery
- Keep auto-quarantine disabled initially until you understand what gets detected
- Check Logs view weekly to review scheduled scan results
- Test your schedule after setting it up

❌ **Don't**:
- Schedule hourly scans unless absolutely necessary (too frequent)
- Scan entire filesystem (`/`) daily (too slow)
- Enable auto-quarantine without understanding it (risks false positives)
- Forget to click "Save & Apply" after changing settings
- Schedule scans when computer is typically off

💡 **Recommended Setup for Most Users**:
- **Frequency**: Daily
- **Time**: 02:00 (2:00 AM)
- **Targets**: ~/Downloads
- **Skip on Battery**: Enabled (✓)
- **Auto-Quarantine**: Disabled ( )

This provides daily protection of your most vulnerable folder (Downloads) with minimal system impact and maximum control

---

## Statistics Dashboard

Monitor your system's security status and scan activity with ClamUI's comprehensive Statistics Dashboard. Get an at-a-glance view of your protection level, scan history, and threat detection trends.

**What you'll find in the Statistics Dashboard:**

- **Protection Status**: Current security posture and last scan information
- **Scan Metrics**: Aggregated statistics for scans, files checked, and threats found
- **Timeframe Filtering**: View statistics by day, week, month, or all time
- **Activity Charts**: Visual trends showing scan and threat patterns
- **Quick Actions**: One-click access to common scanning operations

**When to use the Statistics Dashboard:**

- Check your current protection status at a glance
- Review your scanning activity over time
- Identify patterns in threat detection
- Verify that scheduled scans are running
- Monitor scanning coverage (how many files you're checking)
- Generate insights for security reports

### Understanding Protection Status

The Protection Status section at the top of the Statistics Dashboard tells you whether your system is currently protected based on your scanning activity and virus definition freshness.

#### Opening the Statistics Dashboard

1. Click the **Statistics** button in the navigation bar
2. The dashboard loads automatically with your current statistics
3. All data is calculated from your scan history

#### Protection Status Levels

ClamUI evaluates your protection status based on two factors:

1. **Last Scan Age**: How recently you scanned your system
2. **Definition Age**: How fresh your virus definitions are (if available)

**Protection Levels:**

| Status | Badge Color | Icon | What It Means | Criteria |
|--------|-------------|------|---------------|----------|
| 🟢 **Protected** | Green | ✅ Checkmark | System is actively protected | Last scan within 7 days AND definitions current (if available) |
| 🟡 **At Risk** | Yellow/Orange | ⚠️ Warning | Protection is degraded | Last scan 7-30 days ago OR definitions outdated (7+ days old) |
| 🔴 **Unprotected** | Red | ❌ Error | System lacks adequate protection | No scans performed OR last scan over 30 days ago |
| ⚪ **Unknown** | Gray | ❓ Question | Cannot determine status | Unable to access scan history or parse data |

#### Protection Status Display

```
┌─────────────────────────────────────────────────────┐
│ Protection Status                      [🔄 Refresh] │
│ Current system security posture                     │
├─────────────────────────────────────────────────────┤
│ ✅  System Status                      [Protected] │
│     System is protected                            │
│                                                     │
│ 🕐  Last Scan                                       │
│     2026-01-02 14:30 (2 hours ago)                 │
└─────────────────────────────────────────────────────┘
```

**What you see:**

- **System Status Row**: Shows your current protection level with icon and message
- **Protection Badge**: Color-coded label indicating your status (Protected/At Risk/Unprotected/Unknown)
- **Status Message**: Explanation of your current protection state
- **Last Scan Row**: Timestamp of your most recent scan with human-readable age
- **Refresh Button**: Manually reload statistics to get latest data

#### Protection Status Messages

**🟢 Protected Status Messages:**

- `"System is protected"` - Everything is current (scan within 7 days, definitions fresh)
- `"System protected, but definitions should be updated"` - Scan is recent but definitions are 1-7 days old
- `"System protected (definition status unknown)"` - Recent scan but definition age cannot be determined

**🟡 At Risk Status Messages:**

- `"Last scan was over a week ago"` - Last scan was 7-30 days ago (time to scan again)
- `"Virus definitions are outdated (over 7 days old)"` - Definitions haven't been updated in over a week

**🔴 Unprotected Status Messages:**

- `"No scans performed yet"` - You haven't run any scans (run your first scan!)
- `"Last scan was over 30 days ago"` - Your last scan is too old to provide meaningful protection

**⚪ Unknown Status Messages:**

- `"Unable to determine protection status"` - Cannot access scan history or parse timestamps

#### Improving Your Protection Status

If your status is not **Protected**, here's what to do:

**For "At Risk" or "Unprotected" (scan age issues):**

1. Click **Quick Scan** in the Quick Actions section (bottom of Statistics view)
2. Or navigate to the Scan view and perform a scan of your important folders
3. Consider setting up [Scheduled Scans](#scheduled-scans) for automatic protection
4. Refresh the Statistics view to see updated status

**For definition age issues:**

1. Navigate to the **Update** view
2. Click **Update Virus Definitions**
3. Wait for the update to complete
4. Return to Statistics view and refresh

**For "Unknown" status:**

1. Check that ClamAV is installed correctly (see [Troubleshooting](#troubleshooting))
2. Verify you have scan history in the Logs view
3. Try refreshing the statistics manually
4. If the issue persists, run a new scan to generate fresh data

💡 **Tip**: Set up a weekly scheduled scan to maintain "Protected" status automatically without manual intervention.

⚠️ **Important**: The Protection Status is based on *scan recency*, not real-time threat detection. ClamAV doesn't provide active real-time protection like some commercial antivirus products. Regular scans are essential.

#### Last Scan Information

The **Last Scan** row shows details about your most recent scan:

- **Timestamp**: Date and time in YYYY-MM-DD HH:MM format (24-hour clock)
- **Age**: Human-readable time since the scan (e.g., "2 hours ago", "3 days ago")
- **No Scans**: Shows "No scans recorded" if you haven't run any scans yet

**Age Display Formats:**

| Age | Display Format | Example |
|-----|----------------|---------|
| < 1 hour | "less than an hour ago" | 2026-01-02 14:30 (less than an hour ago) |
| 1-23 hours | "X hour(s) ago" | 2026-01-02 10:00 (4 hours ago) |
| 1-6 days | "X day(s) ago" | 2026-01-01 14:30 (1 day ago) |
| 7+ days | "X week(s) ago" | 2025-12-15 09:00 (3 weeks ago) |

### Viewing Scan Statistics

The **Scan Statistics** section displays aggregated metrics for all scans in your selected timeframe.

#### Statistics Cards

```
┌─────────────────────────────────────────────────────┐
│ Scan Statistics                                     │
│ Statistics for: Dec 26 - Jan 02, 2026              │
├─────────────────────────────────────────────────────┤
│ 🔍  Total Scans                               42   │
│     Number of scans performed                      │
│                                                     │
│ 📄  Files Scanned                         15,234   │
│     Total files checked                            │
│                                                     │
│ ⚠️  Threats Detected                            3   │
│     Malware and suspicious files found             │
│                                                     │
│ ✅  Clean Scans                                39   │
│     Scans with no threats found                    │
│                                                     │
│ ⏱️  Average Scan Duration                   2m 15s │
│     Mean time per scan                             │
└─────────────────────────────────────────────────────┘
```

#### Understanding Each Metric

**1. Total Scans**

- **What it is**: Number of scans you've performed in the selected timeframe
- **Includes**: Both manual and scheduled scans
- **Use case**: Monitor your scanning frequency
- **Example**: `42` means you ran 42 scans in the past week

**What counts as a scan:**
- Manual scans from the Scan view
- Scheduled scans (automatic)
- Scans run from the command line
- Scans triggered via drag-and-drop

**What doesn't count:**
- Cancelled scans (stopped before completion)
- Database updates (shown separately in Logs)
- Failed scans that never started

**2. Files Scanned**

- **What it is**: Total number of individual files checked across all scans
- **Format**: Formatted with thousand separators (e.g., `15,234` not `15234`)
- **Calculation**: Sum of all files checked in every scan in the timeframe
- **Use case**: Understand your scanning coverage

**Example interpretation:**
- `15,234 files scanned` with `42 total scans` = average of 363 files per scan
- High file count typically means full system scans or large folder scans
- Low file count might indicate targeted Quick Scans of specific folders

**What files are counted:**
- Every file ClamAV examines, including:
  - Regular files (documents, images, executables, etc.)
  - Archive contents (files inside .zip, .tar, .7z, etc.)
  - Email attachments (if scanning mail folders)
  - Nested archives (archives within archives)

**What's excluded from the count:**
- Directories (folders are traversed but not "scanned")
- Excluded files/patterns (see [Managing Exclusions](#managing-exclusions))
- Symbolic links (unless they point to real files)
- Files that couldn't be accessed (permission errors)

💡 **Tip**: If your Files Scanned count seems lower than expected, check your [exclusion patterns](#managing-exclusions) - you might be excluding more than intended.

**3. Threats Detected**

- **What it is**: Total number of threats (malware, viruses, suspicious files) found
- **Color coding**: Displays in red if threats were found, normal color if zero
- **Calculation**: Sum of all infected files across all scans in the timeframe
- **Use case**: Monitor threat activity on your system

**What counts as a threat:**
- Any file that ClamAV flags as infected
- All severity levels (CRITICAL, HIGH, MEDIUM, LOW)
- EICAR test files (if you tested with the EICAR button)
- False positives (files incorrectly identified as threats)

**Example scenarios:**

| Threats Detected | Interpretation | What To Do |
|-----------------|----------------|------------|
| `0` (in green) | No threats found - system is clean | Continue regular scanning schedule |
| `1-2` (in red) | Minimal threat activity | Review [Quarantine](#quarantine-management) to see what was found |
| `3-10` (in red) | Moderate threat detection | Check Quarantine, investigate sources, run additional scans |
| `10+` (in red) | Significant threat activity | Review all detected threats, check for infection patterns, consider full system scan |

**Understanding the count:**
- If the same infected file is scanned multiple times, it's counted each time
- Quarantining a file doesn't remove it from statistics (historical data is preserved)
- The count reflects *when threats were detected*, not when they appeared on your system

💡 **Tip**: A sudden spike in Threats Detected (visible in the [activity chart](#understanding-scan-activity-charts)) might indicate a new infection source like a USB drive or download.

⚠️ **Note**: Not all detections are real threats - see [Threat Severity Levels](#threat-severity-levels) to understand the difference between CRITICAL ransomware and LOW-severity test files.

**4. Clean Scans**

- **What it is**: Number of scans that completed with zero threats found
- **Formula**: Clean Scans + Infected Scans ≈ Total Scans (error scans excluded)
- **Use case**: Gauge your system's overall health

**Example analysis:**

```
Total Scans: 42
Clean Scans: 39
Threats Detected: 3

Analysis: 39 out of 42 scans were clean (93% success rate)
```

**What makes a scan "clean":**
- Scan completed successfully (no errors)
- Zero infected files found
- All scanned files passed ClamAV checks

**Why clean scans matter:**
- High clean scan percentage (90%+) = healthy system with minimal threats
- Low clean scan percentage (<80%) = may indicate recurring infections or problematic files
- Consistent clean scans = good evidence your protection is working

**5. Average Scan Duration**

- **What it is**: Mean time it took to complete scans in the timeframe
- **Format**: Human-readable (e.g., `2m 15s`, `45.3s`, `1h 5m`)
- **Calculation**: Total time spent scanning ÷ number of scans
- **Use case**: Understand scanning performance and plan scan schedules

**Duration Formats:**

| Duration | Display Format | Example |
|----------|----------------|---------|
| < 60 seconds | `X.Xs` | `45.3s` |
| 1-59 minutes | `Xm Ys` | `2m 15s` |
| 1+ hours | `Xh Ym` | `1h 5m` |

**Interpreting Average Duration:**

| Average Duration | Typical Scenario | What It Means |
|-----------------|------------------|---------------|
| < 30 seconds | Quick Scans of Downloads folder | Small, targeted scans of specific folders |
| 30s - 5 minutes | Home folder scans | Medium-sized scans with moderate file counts |
| 5-30 minutes | Partial system scans | Scanning multiple large folders or user directories |
| 30+ minutes | Full system scans | Complete filesystem scans with high file counts |

**Factors affecting scan duration:**
- **File count**: More files = longer scans
- **File sizes**: Larger files take longer to scan
- **File types**: Archives and compressed files are slower
- **Backend**: `daemon` backend is 10-50x faster than `clamscan` (see [Scan Backend Options](#scan-backend-options))
- **Storage speed**: SSDs scan faster than HDDs
- **System load**: CPU/disk usage from other programs slows scans

💡 **Tip**: If your average duration seems too long:
1. Switch to the `daemon` backend in [Settings](#scan-backend-options) for dramatically faster scans
2. Use scan profiles with targeted folders instead of full system scans
3. Add exclusions for cache directories and other non-critical folders

#### Date Range Display

The statistics group description shows the date range for your selected timeframe:

**Examples:**

- `"Statistics for: Dec 26 - Jan 02, 2026"` - Weekly view showing 7-day range
- `"Statistics for: Jan 01 - Jan 02, 2026"` - Daily view showing 24-hour range
- `"Aggregated metrics for all time"` - All Time view (no date filtering)

**Empty State:**

If you haven't run any scans yet, the statistics section displays:

```
┌─────────────────────────────────────────────────────┐
│ Scan Statistics                                     │
│ Run your first scan to see statistics here         │
├─────────────────────────────────────────────────────┤
│ 🔍  Total Scans                                0   │
│ 📄  Files Scanned                              0   │
│ ⚠️  Threats Detected                            0   │
│ ✅  Clean Scans                                 0   │
│ ⏱️  Average Scan Duration                      -- │
└─────────────────────────────────────────────────────┘
```

### Filtering by Timeframe

The **Timeframe** selector lets you filter statistics to specific time periods, helping you analyze recent activity or view your complete scanning history.

#### Timeframe Options

```
┌─────────────────────────────────────────────────────┐
│ Timeframe                                           │
│ Select the time period for statistics               │
├─────────────────────────────────────────────────────┤
│           [ Day ] [ Week ] [ Month ] [ All Time ]  │
└─────────────────────────────────────────────────────┘
```

**Available Timeframes:**

| Timeframe | Time Period | When to Use | Example Use Case |
|-----------|-------------|-------------|------------------|
| **Day** | Last 24 hours | Monitor today's activity, verify scheduled scans ran today | Check if your daily 3am scan completed |
| **Week** | Last 7 days | Review recent protection (default view), weekly summary | See this week's scanning coverage before weekend |
| **Month** | Last 30 days | Monthly reports, identify long-term trends | Generate monthly security report for team |
| **All Time** | Complete history | View cumulative statistics, assess overall protection | Review total threats found since installation |

#### Changing the Timeframe

1. **Click the desired timeframe button** (Day, Week, Month, or All Time)
2. The button becomes **highlighted/active** to show it's selected
3. Statistics **automatically reload** for the new timeframe
4. The **date range updates** in the statistics section (except for All Time)
5. The **activity chart updates** to show trends for the selected period

**Visual Feedback:**

- **Active button**: Highlighted with accent color, appears "pressed"
- **Inactive buttons**: Neutral appearance
- **Loading state**: Buttons disabled with spinner while data loads
- **Only one button active**: Selecting a new timeframe deactivates the previous one

💡 **Tip**: The timeframe selection is remembered during your session but resets to "Week" when you relaunch ClamUI.

#### Timeframe and Chart Data Points

The number of data points in the [activity chart](#understanding-scan-activity-charts) varies by timeframe:

| Timeframe | Data Points | Interval | Example |
|-----------|-------------|----------|---------|
| **Day** | 6 points | 4-hour blocks | 00:00-04:00, 04:00-08:00, ..., 20:00-24:00 |
| **Week** | 7 points | Daily intervals | Mon, Tue, Wed, Thu, Fri, Sat, Sun |
| **Month** | 10 points | 3-day intervals | Days 1-3, 4-6, 7-9, ..., 28-30 |
| **All Time** | 12 points | Monthly intervals | Jan, Feb, Mar, ..., Dec (or distributed across history) |

This ensures the chart remains readable regardless of how much data you have.

#### Examples: Comparing Timeframes

**Scenario 1: Daily Quick Scans**

You run Quick Scans of Downloads every day at 3am via scheduled scans.

- **Day view**: Shows 1 scan (today's 3am scan)
- **Week view**: Shows 7 scans (one per day)
- **Month view**: Shows ~30 scans (one per day for 30 days)
- **All Time view**: Shows total scans since you installed ClamUI

**Scenario 2: Weekly Full Scans**

You run a Full Scan every Sunday at 2am.

- **Day view**: Shows 1 scan if today is Sunday, 0 if another day
- **Week view**: Shows 1 scan (this week's Sunday scan)
- **Month view**: Shows 4-5 scans (4-5 Sundays in a month)
- **All Time view**: Shows total scans since installation

**Scenario 3: Mixed Manual and Scheduled**

You have daily scheduled scans plus manual scans when downloading files.

- **Day view**: Shows today's scheduled scan + any manual scans you ran today
- **Week view**: Shows 7 scheduled scans + manual scans from the week
- **Month view**: Shows all 30 scheduled scans + all manual scans
- **All Time view**: Complete combined history

#### Understanding Filtered Statistics

When you change timeframes, **all statistics recalculate** for the selected period:

**Example: Switching from Week to Month**

```
Week View (last 7 days):
- Total Scans: 7
- Files Scanned: 2,450
- Threats Detected: 0
- Average Duration: 1m 30s

Month View (last 30 days):
- Total Scans: 35
- Files Scanned: 10,283
- Threats Detected: 2
- Average Duration: 1m 42s
```

**What changed:**
- Scans increased 5x (7 → 35) because we're looking at 4x more time
- Files scanned increased ~4x (proportional to scan count)
- Threats appeared (2 were found 10 days ago, outside the weekly view)
- Average duration increased slightly (might have had longer scans 2-3 weeks ago)

💡 **Tip**: Use **Week view** as your default for monitoring recent activity, then switch to **Month** when you need a broader perspective or **Day** to troubleshoot today's scans.

⚠️ **Note**: Timeframe filtering affects statistics and charts but does NOT filter the Logs view - use the Logs view itself to see individual scan details.

### Understanding Scan Activity Charts

The **Scan Activity** chart provides a visual representation of your scanning patterns and threat detection trends over the selected timeframe.

#### Chart Overview

```
┌─────────────────────────────────────────────────────┐
│ Scan Activity                                       │
│ Scan trends over the selected timeframe            │
├─────────────────────────────────────────────────────┤
│                                                     │
│   8 ┤                                               │
│   7 ┤     ▅▅                  ▅▅                    │
│   6 ┤     ██        ▅▅        ██                    │
│   5 ┤ ▅▅  ██        ██    ▅▅  ██                    │
│   4 ┤ ██  ██    ▅▅  ██    ██  ██    ▅▅              │
│   3 ┤ ██  ██    ██  ██    ██  ██    ██              │
│   2 ┤ ██  ██    ██  ██    ██  ██    ██              │
│   1 ┤ ██  ██    ██  ██    ██  ██    ██  ▅▅          │
│   0 ┴─────────────────────────────────────────      │
│     Mon Tue Wed Thu Fri Sat Sun                     │
│                                                     │
│     Legend: █ Scans  ▅ Threats                      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Chart Components:**

- **Blue bars**: Number of scans performed in each time interval
- **Red bars**: Number of threats detected in each interval
- **X-axis**: Time intervals (dates or time periods)
- **Y-axis**: Count (number of scans or threats)
- **Legend**: Identifies what the blue and red bars represent
- **Grid**: Light background grid for easier reading

#### Reading the Chart

**Bar Chart Structure:**

For each time interval, you'll see two bars side-by-side:
- **Left bar (blue)**: How many scans ran in this interval
- **Right bar (red)**: How many threats were found in this interval

**Example interpretation (Weekly view):**

```
Monday:    7 scans, 0 threats  (tall blue bar, no red bar)
Tuesday:   8 scans, 1 threat   (tall blue bar, short red bar)
Wednesday: 5 scans, 0 threats  (medium blue bar, no red bar)
...
```

**What the chart tells you:**

✅ **Consistent blue bars**: Regular scanning schedule is working
✅ **Low/no red bars**: System is clean with minimal threat activity
⚠️ **Missing blue bars**: Gaps in your scanning coverage (consider scheduled scans)
⚠️ **Tall red bars**: Spike in threat detection (investigate the source)
⚠️ **Red bars without blue bars**: Impossible (indicates data issue)

#### Chart Time Intervals

The X-axis shows different time units depending on your selected timeframe:

**Daily View (6 data points - 4-hour blocks):**
```
X-axis labels: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
Example: "04:00" shows scans run between 4am-8am today
```

**Weekly View (7 data points - daily):**
```
X-axis labels: 12/26, 12/27, 12/28, 12/29, 12/30, 12/31, 01/01
Format: MM/DD (month/day)
Example: "12/26" shows all scans on December 26
```

**Monthly View (10 data points - 3-day intervals):**
```
X-axis labels: 12/03, 12/06, 12/09, ..., 12/30
Format: MM/DD (first day of each 3-day period)
Example: "12/06" shows scans from Dec 6-8
```

**All Time View (12 data points - monthly):**
```
X-axis labels: 01/01, 02/01, 03/01, ..., 12/01
Format: MM/DD (first day of each month)
Example: "03/01" shows all scans in March
```

💡 **Tip**: Hover over or click chart elements in some GTK themes to see tooltips with exact values (though this feature depends on your desktop environment).

#### Chart Patterns and What They Mean

**Pattern 1: Steady blue bars, no red bars (Ideal)**
```
All intervals have similar blue bar heights, red bars are absent
Interpretation: Consistent scanning schedule, no threats detected
Action: ✅ Keep up the good work! Your protection strategy is working.
```

**Pattern 2: Scattered blue bars (Irregular scanning)**
```
Some intervals have tall blue bars, others have no bars
Interpretation: Inconsistent scanning (manual scans only, no schedule)
Action: ⚠️ Consider setting up [scheduled scans](#scheduled-scans) for regular protection
```

**Pattern 3: Single tall red bar spike (Isolated threat)**
```
One interval has a red bar, others are clean
Interpretation: Threat detected once, possibly from external source (USB, download)
Action: ℹ️ Review [Quarantine](#quarantine-management) for that day's threats, investigate source
```

**Pattern 4: Multiple red bars (Persistent threats)**
```
Red bars appear in multiple consecutive intervals
Interpretation: Recurring threat detection, possible active infection
Action: ⚠️ Run full system scan, check if threats are being re-downloaded, review [quarantine](#quarantine-management)
```

**Pattern 5: All red bars same height as blue bars (Problematic)**
```
Every scan finds the same number of threats (e.g., blue=1, red=1 every day)
Interpretation: Same threat being detected repeatedly without removal
Action: ⚠️ Check if threat is in an excluded folder, verify quarantine is working, review scan targets
```

**Pattern 6: No data (Empty chart)**
```
Chart shows "No scan data available" message instead of bars
Interpretation: No scans in the selected timeframe (or no scans ever)
Action: ℹ️ Run your first scan or select a different timeframe (e.g., switch from Day to All Time)
```

#### Chart Color Coding

ClamUI uses GNOME/Adwaita color scheme for consistency:

| Element | Color | Meaning |
|---------|-------|---------|
| Blue bars | `#3584e4` (GNOME Blue) | Scans performed (neutral/positive) |
| Red bars | `#e01b24` (GNOME Red) | Threats detected (warning/attention needed) |
| Text/labels | Adapts to theme | Black in light mode, white in dark mode |
| Grid lines | Light gray | Background reference lines |
| Background | Transparent | Matches the application window background |

💡 **Dark Mode Support**: The chart automatically adapts its text and grid colors when you switch your system to dark mode, ensuring readability.

#### Chart Empty States

**No scan history at all:**
```
┌─────────────────────────────────────────────────────┐
│ Scan Activity                                       │
│ No scan activity recorded                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│         📊                                          │
│    No scan data available                           │
│  Run some scans to see activity trends here         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**No scans in selected timeframe:**

Same empty state appears if you select "Day" but haven't scanned today, or "Week" but have only older scans.

**Action**: Switch to a broader timeframe (e.g., All Time) to see your historical data.

#### Chart Limitations

⚠️ **What the chart doesn't show:**

- **Individual scan details**: Use [Logs view](#scan-history) to see specific scan information
- **Which files were infected**: Check [Quarantine](#quarantine-management) for infected file details
- **Scan targets**: Chart shows counts only, not what was scanned
- **Scan duration**: Average duration is in the statistics cards, not visualized
- **Real-time updates**: Chart loads once; click Refresh to update
- **Threat severity**: All threats are counted equally (no distinction between CRITICAL and LOW)

**Chart rendering issues:**

If the chart displays "Unable to render chart" instead of bars:
1. Check that matplotlib is installed correctly
2. Try refreshing the statistics (click the refresh button)
3. Restart ClamUI to reload the chart library
4. See [Troubleshooting](#troubleshooting) if the issue persists

#### Scrolling in the Statistics View

The chart area is embedded in the scrollable Statistics view. When you scroll:

- **On the chart area**: Scrolling moves the entire Statistics view up/down
- **Chart doesn't zoom**: The chart size is fixed (no pinch-to-zoom)
- **Mobile/touchpad scrolling**: Uses kinetic scrolling (smooth momentum)

💡 **Tip**: If the chart feels too small, consider maximizing the ClamUI window or viewing it in fullscreen.

### Quick Actions

The **Quick Actions** section at the bottom of the Statistics Dashboard provides one-click access to common scanning operations without navigating to other views.

#### Available Quick Actions

```
┌─────────────────────────────────────────────────────┐
│ Quick Actions                                       │
│ Common scanning operations                          │
├─────────────────────────────────────────────────────┤
│ ▶️  Quick Scan                                   ❯  │
│     Scan your home directory                        │
│                                                     │
│ 📋  View Scan Logs                               ❯  │
│     See detailed scan history                       │
└─────────────────────────────────────────────────────┘
```

**What you see:**

- **Icon**: Visual indicator of the action (▶️ for scan, 📋 for logs)
- **Action title**: What the action does
- **Description**: Brief explanation of the action
- **Chevron (❯)**: Indicates the row is clickable/activatable
- **Hover effect**: Row highlights when you hover over it

#### Quick Scan Action

**What it does:**
- Switches to the **Scan view** (navigates away from Statistics)
- Automatically starts scanning your **home directory** (equivalent to "Home Folder" profile)
- Uses your configured scan backend and settings

**When to use it:**
- You want to quickly verify your home folder is clean
- You've just downloaded files and want to scan them
- Your protection status shows "At Risk" or "Unprotected"
- You want to run a scan without manually selecting folders

**How to use it:**

1. Click the **Quick Scan** row (anywhere on the row is clickable)
2. ClamUI **navigates to the Scan view**
3. The scan **starts automatically** with your home directory as the target
4. **Monitor progress** in the Scan view
5. **Return to Statistics** when done to see updated metrics

⚠️ **Note**: Quick Scan uses the default scan settings. If you need custom targets or exclusions, use [Scan Profiles](#scan-profiles) instead.

💡 **Tip**: Quick Scan is equivalent to:
1. Clicking "Scan" in the navigation bar
2. Clicking "Browse" and selecting your home folder
3. Clicking "Start Scan"

It just saves you 3 steps!

#### View Scan Logs Action

**What it does:**
- Switches to the **Logs view** (navigates away from Statistics)
- Shows your complete scan history
- Allows you to review past scan results, export logs, etc.

**When to use it:**
- You see threats in the statistics and want to know when they were found
- You want to verify scheduled scans are running
- You need to export scan logs for reporting
- You want detailed information about specific scans

**How to use it:**

1. Click the **View Scan Logs** row
2. ClamUI **navigates to the Logs view** (Historical Logs tab)
3. Review your scan history (see [Scan History](#scan-history) for details)
4. Click **Statistics** in the navigation bar to return

💡 **Tip**: The Statistics Dashboard and Logs view complement each other:
- **Statistics**: High-level overview and trends (aggregated data)
- **Logs**: Detailed individual scan information (raw data)

#### Quick Actions Workflow Examples

**Example 1: Responding to "At Risk" status**

1. Check Statistics Dashboard
2. See status: **"At Risk - Last scan was over a week ago"**
3. Click **Quick Scan** to immediately scan home directory
4. Scan completes, switch back to Statistics (or it auto-refreshes)
5. Status updates to **"Protected - System is protected"**

**Example 2: Investigating a threat spike**

1. Check Statistics Dashboard
2. See chart shows **red bars** (threats detected)
3. Click **View Scan Logs**
4. Review logs to find when threats were detected
5. See details like file paths, threat names, timestamps
6. Navigate to **Quarantine** to see what was isolated

**Example 3: Verifying scheduled scans**

1. Check Statistics Dashboard daily view
2. See if scans ran today (blue bar in today's chart interval)
3. If no scans visible, click **View Scan Logs**
4. Check if scheduled scan failed or didn't run
5. Review [Managing Scheduled Scans](#managing-scheduled-scans) to troubleshoot

#### Quick Actions Notes

**What Quick Actions don't do:**

- **Don't perform actions in-place**: They navigate you to another view
- **Don't show confirmation dialogs**: Actions execute immediately
- **Don't interrupt ongoing scans**: If a scan is running, Quick Scan is disabled
- **Don't customize scan targets**: Use Scan view with profiles for custom targets

**Keyboard navigation:**

- Quick Actions rows are **keyboard accessible**
- Press **Tab** to focus on a Quick Action row
- Press **Enter** or **Space** to activate it
- Use **Shift+Tab** to navigate backwards

💡 **Tip**: If you frequently use Quick Actions, consider learning the keyboard shortcuts:
- **Ctrl+Q**: Quit ClamUI (not Quick Scan!)
- **Ctrl+,**: Open Preferences
- For view navigation, use the navigation buttons or click the view name in the header

#### Refreshing Statistics

While not in the Quick Actions section, the **Refresh button** (🔄) in the Protection Status header is another important quick action:

**How to refresh:**

1. Click the **refresh icon** (🔄) in the top-right of the Protection Status section
2. Statistics **reload automatically** from scan history
3. A **loading spinner** appears while refreshing
4. All sections update: Protection Status, Statistics, and Chart

**When to refresh:**

- After completing a scan
- After quarantining threats
- After updating virus definitions
- When you want to see latest protection status
- If statistics seem outdated

**Auto-refresh:**

- Statistics do **NOT auto-refresh** while the view is open
- You must manually refresh to see updates
- Statistics **reload automatically** when you change timeframes
- Statistics **load automatically** when you first open the Statistics view

💡 **Tip**: Get in the habit of clicking Refresh after important actions (scans, updates, quarantine operations) to ensure your statistics reflect the latest data.

---

**Summary: Making the Most of the Statistics Dashboard**

✅ **Do:**
- Check your Protection Status regularly (daily or weekly)
- Use timeframe filtering to analyze different periods
- Review the activity chart for patterns and trends
- Investigate red bars (threat spikes) in the chart
- Use Quick Scan for immediate home directory scanning
- Refresh after scans to see updated statistics

⚠️ **Don't:**
- Rely solely on Protection Status - run regular scans
- Ignore "At Risk" or "Unprotected" warnings
- Assume all threats are critical (check severity in Quarantine)
- Expect real-time updates (manual refresh required)
- Use statistics as a replacement for detailed Logs

💡 **Best Practices:**
- **Daily check**: Open Statistics view, verify Protection Status is "Protected"
- **Weekly review**: Switch to Week timeframe, check for consistent scan patterns
- **Monthly analysis**: Switch to Month timeframe, review threat trends
- **After major events**: Refresh statistics after scans, updates, or quarantine operations
- **Combine with Logs**: Use Statistics for overview, Logs for investigation

---

## Settings and Preferences

ClamUI provides comprehensive configuration options to customize how virus scanning works on your system. This section covers all available settings, from choosing the scan backend to configuring advanced ClamAV options.

💡 **Tip:** Most users only need to adjust a few basic settings. Advanced options like ClamAV configuration files are for experienced users who want fine-grained control.

---

### Accessing Preferences

ClamUI's preferences are organized into several pages covering different aspects of the application.

**How to Open Preferences:**

1. **Using Keyboard Shortcut:**
   - Press `Ctrl+,` (Comma) from anywhere in ClamUI

2. **Using Menu:**
   - Click the menu button (☰) in the header bar
   - Select "Preferences"

**Preferences Window Layout:**

The preferences window uses a sidebar navigation with these pages:

```
┌─────────────────────────────────────────┐
│ Sidebar          │ Settings Page        │
├──────────────────┼──────────────────────┤
│ ▶ Database      │                       │
│   Updates        │  [Configuration      │
│                  │   Settings Display]  │
│ ▶ Scanner        │                       │
│   Settings       │                       │
│                  │                       │
│ ▶ Scheduled      │                       │
│   Scans          │                       │
│                  │                       │
│ ▶ Exclusions     │                       │
│                  │                       │
│ ▶ Save & Apply   │                       │
└──────────────────┴──────────────────────┘
```

**Navigation:**
- Click any sidebar item to view that settings page
- Changes are **not** saved until you click "Save & Apply"
- Close the window to discard unsaved changes

⚠️ **Important:** Many settings require administrator (root) privileges to modify because they change system-wide ClamAV configuration files. You'll see a lock icon (🔒) next to settings groups that require elevated permissions.

---

### Scan Backend Options

The scan backend determines how ClamUI performs virus scanning. Choose the method that best fits your setup.

#### Understanding Scan Backends

ClamUI supports three scanning methods:

| Backend | Description | Speed | When to Use |
|---------|-------------|-------|-------------|
| **Auto (Recommended)** | Automatically prefer clamd daemon if available, fall back to clamscan | Fast (daemon) or Moderate (clamscan) | Default choice for most users. Gets best performance automatically. |
| **ClamAV Daemon (clamd)** | Use the ClamAV daemon exclusively | Very Fast (10-50x faster) | When daemon is always running and you want guaranteed fast scans. **Requires clamd to be active.** |
| **Standalone Scanner (clamscan)** | Use standalone clamscan command | Moderate | When clamd is not available, or for compatibility with specific scan profiles. |

**Performance Comparison:**

The ClamAV daemon (clamd) keeps virus signatures loaded in memory, making scans **10-50 times faster** than the standalone scanner (clamscan), which must load signatures from disk for every scan.

**Example scan time for 10,000 files:**
- Daemon (clamd): 10-30 seconds
- Standalone (clamscan): 2-5 minutes

#### Choosing Your Scan Backend

**To Select Scan Backend:**

1. Open Preferences (`Ctrl+,`)
2. Click "Scanner Settings" in the sidebar
3. Locate the "Scan Backend" section at the top
4. Click the "Scan Backend" dropdown
5. Select your preferred option:
   - "Auto (prefer daemon)" - Recommended
   - "ClamAV Daemon (clamd)" - Fast, requires daemon
   - "Standalone Scanner (clamscan)" - Compatible

**The selection is saved immediately** - no need to click Save & Apply for this setting.

#### Checking Daemon Status

Below the scan backend selector, you'll see the **Daemon Status** indicator:

**Status Messages:**

| Status | Icon | Meaning | What to Do |
|--------|------|---------|------------|
| "Connected to clamd" | ✅ Green checkmark | Daemon is running and accessible | No action needed. Fast scanning available. |
| "Not available: ..." | ⚠️ Warning | Daemon is not running or not installed | Install clamd or use Auto/Clamscan backend. Details shown in message. |

**To Refresh Daemon Status:**

1. Click the "Refresh Status" button next to the status indicator
2. Status updates immediately with current daemon state

**Common Daemon Status Issues:**

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "Socket not found" | clamd not installed or not running | Install clamav-daemon package and start the service: `sudo systemctl start clamav-daemon` |
| "Connection refused" | Socket permissions issue | Check socket permissions or run ClamUI with appropriate access |
| "Daemon not installed" | ClamAV daemon package missing | Install: `sudo apt install clamav-daemon` (Ubuntu/Debian) |

💡 **Tip:** If you're unsure whether clamd is installed, use the "Auto (prefer daemon)" backend. ClamUI will automatically use the daemon if available and fall back to clamscan otherwise.

⚠️ **Note:** On some distributions, the daemon is installed separately from the main ClamAV package. Check your distribution's package manager for "clamav-daemon" or "clamd".

---

### Database Update Settings

ClamUI allows you to configure how ClamAV updates its virus definition databases through the `freshclam.conf` configuration file.

🔒 **Requires Administrator Privileges:** These settings modify `/etc/clamav/freshclam.conf` and require root access.

#### Opening Database Update Settings

1. Open Preferences (`Ctrl+,`)
2. Click "Database Updates" in the sidebar

You'll see several configuration groups:

#### Configuration File Location

At the top of the page, you'll see the configuration file path:

**File Location:** `/etc/clamav/freshclam.conf`

**To Open the Configuration Folder:**
- Click "Open Folder" button to view the file in your file manager
- Useful for manual edits or viewing backup files

#### Paths Configuration

**DatabaseDirectory** - Where virus definition files are stored
- **Default:** `/var/lib/clamav`
- **Purpose:** Storage location for virus signature databases (main.cvd, daily.cld, etc.)
- **When to change:** If you want databases on a different partition or faster storage
- **Example:** `/mnt/ssd/clamav-db` (for SSD storage)

**Update Log File** - Log file for database update operations
- **Default:** `/var/log/clamav/freshclam.log`
- **Purpose:** Records all database update attempts, successes, and failures
- **When to check:** Troubleshooting update issues, verifying update schedule
- **Example:** `/var/log/freshclam-updates.log`

**Notify ClamD Config** - Path to clamd.conf for reload notification
- **Default:** `/etc/clamav/clamd.conf`
- **Purpose:** Tells freshclam to notify the daemon when databases are updated
- **When to change:** If clamd.conf is in a non-standard location
- **Why it matters:** Ensures the daemon reloads new signatures without restart

**Verbose Logging** - Enable detailed logging
- **Options:** On/Off (switch)
- **Default:** Usually Off
- **When to enable:** Troubleshooting update failures, monitoring update process
- **Impact:** Larger log files, more detailed information

**Syslog Logging** - Send log messages to system log
- **Options:** On/Off (switch)
- **Default:** Usually Off
- **When to enable:** Centralized logging, system monitoring integration
- **Location:** Messages appear in `/var/log/syslog` or journalctl

#### Update Behavior Configuration

**Checks Per Day** - How often to check for database updates
- **Range:** 0-50 checks per day
- **Default:** Usually 24 (once per hour)
- **Recommended:** 12-24 for most users
- **Special value:** 0 disables automatic updates (not recommended)
- **Impact:** More frequent checks catch new threats faster but use more bandwidth

**Update Frequency Recommendations:**

| Checks/Day | Update Interval | Best For | Bandwidth Impact |
|------------|-----------------|----------|------------------|
| 24 | Every hour | Security-conscious users, servers | Low (~10-20 MB/day) |
| 12 | Every 2 hours | Standard desktop users | Very Low (~5-10 MB/day) |
| 6 | Every 4 hours | Low-bandwidth connections | Minimal (~2-5 MB/day) |
| 2 | Every 12 hours | Infrequent usage | Negligible |
| 0 | Never (manual only) | Testing/offline systems | None |

**Database Mirror** - Mirror server URL for downloading databases
- **Default:** `database.clamav.net`
- **Purpose:** Server that provides virus definition database files
- **When to change:** Local mirror available, connection issues with default mirror
- **Format:** Hostname only (e.g., `db.local.clamav.net`) or full URL
- **Example:** `your-company-mirror.local`

⚠️ **Warning:** Only use trusted mirror servers. Malicious mirrors could provide compromised definitions.

#### Proxy Settings Configuration

If your network requires an HTTP proxy for internet access, configure these settings:

**Proxy Server** - Proxy server hostname or IP address
- **Example:** `proxy.company.com` or `192.168.1.1`
- **When needed:** Corporate networks, restricted internet access
- **Leave empty** if no proxy is required

**Proxy Port** - Proxy server port number
- **Range:** 0-65535
- **Common values:** 8080 (HTTP proxy), 3128 (Squid proxy)
- **Special value:** 0 disables proxy usage
- **Default:** 0

**Proxy Username** - Authentication username for proxy (optional)
- **When needed:** Proxy requires authentication
- **Leave empty** for anonymous proxies

**Proxy Password** - Authentication password for proxy (optional)
- **When needed:** Proxy requires authentication
- **Security:** Stored in plaintext in freshclam.conf
- **Leave empty** for anonymous proxies

**Example Proxy Configuration:**

| Scenario | Server | Port | Username | Password |
|----------|--------|------|----------|----------|
| Corporate proxy with auth | `proxy.company.com` | 8080 | `john.doe` | `password123` |
| Local Squid proxy | `192.168.1.1` | 3128 | *(empty)* | *(empty)* |
| No proxy | *(empty)* | 0 | *(empty)* | *(empty)* |

⚠️ **Security Note:** Proxy passwords are stored in plaintext in the configuration file. Use a dedicated proxy account with minimal privileges.

#### Applying Database Update Settings

After configuring database update settings:

1. Navigate to "Save & Apply" page in the sidebar
2. Click the "Save & Apply" button
3. Enter your administrator password when prompted
4. Wait for confirmation dialog: "Configuration Saved"

**What Happens When You Save:**
- Backups are created of existing config files (`.bak` extension)
- New settings are written to `/etc/clamav/freshclam.conf`
- freshclam service may need restart to apply changes

**To Apply Changes Immediately:**

```bash
# Restart freshclam service (systemd)
sudo systemctl restart clamav-freshclam

# Or run freshclam manually once
sudo freshclam
```

💡 **Tip:** Test your configuration by running `sudo freshclam` manually. This will attempt a database update and show any errors immediately.

---

### Scanner Configuration

ClamUI allows you to configure the ClamAV daemon scanner (clamd) behavior through the `clamd.conf` configuration file.

🔒 **Requires Administrator Privileges:** These settings modify `/etc/clamav/clamd.conf` and require root access.

⚠️ **Note:** Scanner settings are only available if `clamd.conf` exists. If you see "ClamD Configuration - clamd.conf not found", install the clamav-daemon package.

#### Opening Scanner Settings

1. Open Preferences (`Ctrl+,`)
2. Click "Scanner Settings" in the sidebar
3. Scroll past the "Scan Backend" section (covered earlier)

You'll see the configuration file location and scanner-specific settings.

#### Configuration File Location

**File Location:** `/etc/clamav/clamd.conf`

**To Open the Configuration Folder:**
- Click "Open Folder" button to view the file in your file manager

#### File Type Scanning

Control which file types ClamAV scans. Disabling unnecessary file types can improve scan performance.

**Available File Type Options:**

| Setting | What It Scans | Recommended | When to Disable |
|---------|---------------|-------------|-----------------|
| **Scan PE Files** | Windows/DOS executables (.exe, .dll, .sys) | ✅ Yes | Never - critical for Windows malware |
| **Scan ELF Files** | Unix/Linux executables | ✅ Yes | Never - critical for Linux malware |
| **Scan OLE2 Files** | Microsoft Office documents (.doc, .xls, .ppt) | ✅ Yes | If you never work with Office files |
| **Scan PDF Files** | PDF documents | ✅ Yes | If you never work with PDFs |
| **Scan HTML Files** | HTML documents and emails | ✅ Yes | Only if you trust all HTML sources |
| **Scan Archive Files** | Compressed archives (ZIP, RAR, 7z, etc.) | ✅ Yes | Never - archives often contain malware |

**Default Configuration:** All file types enabled (recommended)

**Performance Considerations:**

Disabling file types provides minimal performance improvement. Only disable if you have a specific reason:

- **Office documents:** Large OLE2 files (50+ MB) can slow scans
- **Archives:** Deeply nested archives can increase scan time significantly
- **HTML:** Scanning HTML is very fast, minimal impact

💡 **Tip:** Unless you have performance issues, leave all file types enabled for maximum protection.

⚠️ **Warning:** Disabling file type scanning creates security gaps. Malware often hides in "trusted" file types like PDFs and Office documents.

**To Enable/Disable File Type Scanning:**

1. Locate the "File Type Scanning" group
2. Toggle the switch for each file type
3. Navigate to "Save & Apply" page
4. Click "Save & Apply" and enter administrator password

#### Performance and Limits

These settings control resource usage and prevent excessive scan times.

**MaxFileSize** - Maximum individual file size to scan (MB)
- **Range:** 0-4000 MB
- **Default:** Usually 25-100 MB
- **Special value:** 0 = unlimited (not recommended)
- **Purpose:** Skip extremely large files to prevent timeouts
- **Recommendation:** 100-200 MB for desktop, 500+ MB for servers

**MaxScanSize** - Maximum total scan size (MB)
- **Range:** 0-4000 MB
- **Default:** Usually 100-400 MB
- **Special value:** 0 = unlimited (not recommended)
- **Purpose:** Limit total data scanned within archives
- **Recommendation:** 400-800 MB for most users

**MaxRecursion** - Maximum recursion depth for archives
- **Range:** 0-255 levels
- **Default:** Usually 16
- **Purpose:** Prevent infinite recursion in maliciously crafted archives
- **Recommendation:** 10-20 for most users
- **Example:** ZIP containing ZIP containing ZIP (3 levels deep)

**MaxFiles** - Maximum number of files in an archive
- **Range:** 0-1,000,000 files
- **Default:** Usually 10,000
- **Special value:** 0 = unlimited (dangerous)
- **Purpose:** Prevent "zip bomb" attacks with millions of tiny files
- **Recommendation:** 5,000-20,000 for most users

**Understanding Performance Settings:**

```
Example Scan Scenario:
───────────────────────────────────────────────
Archive: suspicious.zip (50 MB compressed)
  ├─ file1.bin (150 MB)         ← MaxFileSize applies
  ├─ nested.zip
  │   └─ level2.zip
  │       └─ level3.zip         ← MaxRecursion applies
  └─ [20,000 tiny files]        ← MaxFiles applies

Total extracted: 800 MB          ← MaxScanSize applies
```

**Performance Tuning Guide:**

| Use Case | MaxFileSize | MaxScanSize | MaxRecursion | MaxFiles |
|----------|-------------|-------------|--------------|----------|
| **Fast scans (less thorough)** | 50 MB | 200 MB | 10 | 5,000 |
| **Balanced (recommended)** | 100 MB | 400 MB | 16 | 10,000 |
| **Thorough scans (slower)** | 500 MB | 1000 MB | 20 | 50,000 |
| **Maximum protection** | 1000 MB | 2000 MB | 25 | 100,000 |

💡 **Tip:** If scans are too slow, reduce MaxScanSize and MaxFiles first. These have the biggest performance impact.

⚠️ **Warning:** Setting values to 0 (unlimited) can cause scans to hang on malicious archives designed to consume resources (zip bombs, recursive archives).

**To Configure Performance Limits:**

1. Locate the "Performance and Limits" group
2. Adjust the values using the number spinners
3. Navigate to "Save & Apply" page
4. Click "Save & Apply" and enter administrator password

#### Logging Configuration

Control how the ClamAV daemon logs scan operations.

**Log File Path** - Location of the scanner log file
- **Default:** `/var/log/clamav/clamav.log`
- **Purpose:** Records all daemon scan operations and errors
- **When to change:** Different partition, centralized logging
- **Example:** `/var/log/clamd-scans.log`

**Verbose Logging** - Enable detailed scan logging
- **Options:** On/Off (switch)
- **Default:** Usually Off
- **When to enable:** Troubleshooting scan issues, detailed audit trail
- **Impact:** **Much larger log files** - can grow quickly with frequent scans
- **What's logged:** Every file scanned, scan results, virus signatures matched

**Syslog Logging** - Send log messages to system log
- **Options:** On/Off (switch)
- **Default:** Usually Off
- **When to enable:** Centralized logging, system monitoring integration
- **Location:** Messages appear in `/var/log/syslog` or via journalctl
- **Integration:** Works with log aggregation tools (Splunk, ELK, etc.)

**Logging Recommendations:**

| Scenario | Verbose | Syslog | Log File |
|----------|---------|--------|----------|
| **Home desktop user** | Off | Off | Default |
| **Troubleshooting** | On | Off | Default |
| **Server with monitoring** | Off | On | Default |
| **Compliance/audit** | On | On | Custom path |

💡 **Tip:** Enable verbose logging temporarily when troubleshooting, then disable it to reduce log file size.

**To View Daemon Logs:**

ClamUI provides built-in log viewing:
1. Go to the "Scan History" view
2. Click the "ClamAV Daemon" tab
3. View live daemon logs with auto-refresh

Or use command line:
```bash
# View daemon log file
sudo tail -f /var/log/clamav/clamav.log

# View via systemd journal
journalctl -u clamav-daemon -f
```

**To Configure Logging:**

1. Locate the "Logging" group
2. Set the log file path if needed
3. Toggle verbose and syslog switches
4. Navigate to "Save & Apply" page
5. Click "Save & Apply" and enter administrator password

---

### Managing Exclusion Patterns

Exclusion patterns allow you to skip certain files or directories during scans, improving performance and reducing false positives.

💡 **Note:** Exclusions configured here are **global exclusions** that apply to all scans. For profile-specific exclusions, use the Scan Profiles feature (see [Managing Exclusions](#managing-exclusions) section).

#### Opening Exclusions Settings

1. Open Preferences (`Ctrl+,`)
2. Click "Exclusions" in the sidebar

You'll see two groups: Preset Exclusions and Custom Exclusions.

#### Understanding Exclusion Types

ClamUI supports two types of exclusions:

**Path Exclusions:**
- Exact file or directory paths
- Example: `/home/user/safe-folder` or `/opt/myapp/cache`
- Use for: Specific directories you trust completely

**Pattern Exclusions:**
- Glob patterns matching multiple files/directories
- Example: `*.tmp`, `node_modules`, `/home/*/.cache`
- Use for: Common file types or directory names anywhere on the system

**Global vs Profile Exclusions:**

| Type | Where Configured | Applies To | Use Case |
|------|------------------|------------|----------|
| **Global Exclusions** | Preferences → Exclusions | **All scans** (manual, scheduled, profile-based) | System-wide safe directories |
| **Profile Exclusions** | Scan Profiles → Edit Profile | **Only that profile** | Profile-specific needs |

💡 **Tip:** Use global exclusions for directories you **never** want to scan (system caches, temp directories). Use profile exclusions for context-specific needs.

#### Preset Exclusions

ClamUI provides common development directory patterns as presets. These are especially useful for developers and can significantly improve scan performance.

**Available Preset Exclusions:**

| Pattern | Description | Typical Size | Why Exclude |
|---------|-------------|--------------|-------------|
| `node_modules` | Node.js dependencies | 100-500 MB | Thousands of files, false positives, build artifacts |
| `.git` | Git repository data | 10-100 MB | Binary objects, not executable, no malware risk |
| `.venv` | Python virtual environment | 50-200 MB | Python packages, duplicates system packages |
| `build` | Build output directory | 50-500 MB | Compiled artifacts, temporary files |
| `dist` | Distribution output directory | 10-100 MB | Packaged builds, minified code |
| `__pycache__` | Python bytecode cache | 1-50 MB | Compiled Python, not executable |

**To Enable/Disable Preset Exclusions:**

1. Locate the "Preset Exclusions" group
2. Toggle the switch for each pattern
3. Enabled (On) = pattern will be excluded from scans
4. Disabled (Off) = pattern will be scanned normally

**Changes take effect immediately** - no need to Save & Apply for preset exclusions.

**When to Enable Presets:**

✅ **Enable if you:**
- Are a software developer
- Have projects in your home directory
- Want faster scans
- Experience false positives in build directories

❌ **Disable if you:**
- Don't use development tools
- Want maximum thorough scanning
- Work with untrusted downloaded projects

💡 **Tip:** Enabling all preset exclusions is safe for developers. These directories rarely contain executable malware and are rebuilt frequently.

#### Custom Exclusions

Add your own exclusion patterns for directories and files specific to your system.

**To Add a Custom Exclusion Pattern:**

1. Locate the "Custom Exclusions" group
2. Click in the entry field labeled "Add Pattern"
3. Type your exclusion pattern
4. Click the "Add" button

**Pattern Examples:**

| Pattern | What It Excludes | Use Case |
|---------|------------------|----------|
| `/home/user/Music` | Entire Music directory | Media library (no malware risk) |
| `/opt/safe-app` | Entire application folder | Trusted proprietary software |
| `*.iso` | All ISO disk images | Large files, CD/DVD images |
| `*.mp4` | All MP4 video files | Video library |
| `/mnt/*` | All mounted filesystems | External drives, network shares |
| `/var/log` | System log directory | Log files (no executable risk) |
| `Thumbs.db` | Windows thumbnail cache | Temporary system files |

**Pattern Syntax:**

- **Exact paths:** Start with `/` for absolute paths (e.g., `/home/user/safe`)
- **Wildcards:** Use `*` for any characters (e.g., `*.tmp` or `/home/*/Downloads/*.pdf`)
- **Recursive:** Patterns match at any depth (e.g., `node_modules` matches `/project/node_modules` and `/project/sub/node_modules`)

**Pattern Validation:**

When you add a pattern, ClamUI validates it:

| Indicator | Meaning | Action |
|-----------|---------|--------|
| ✅ Green checkmark | Valid pattern | Pattern will work correctly |
| ⚠️ Yellow warning | Pattern works but may be too broad | Review pattern for accuracy |
| ❌ Red X | Invalid pattern syntax | Correct the pattern before adding |

**To Remove a Custom Exclusion:**

1. Locate the exclusion in the custom exclusions list
2. Click the remove/delete button (🗑️) next to the pattern
3. Confirm removal if prompted

**Changes take effect immediately** - no need to Save & Apply for custom exclusions.

#### Best Practices for Exclusions

**DO:**
- ✅ Exclude large media libraries (Music, Videos, Photos)
- ✅ Exclude development directories with many files
- ✅ Exclude system cache directories
- ✅ Exclude known safe application data folders
- ✅ Test exclusions by running a scan and checking the file count

**DON'T:**
- ❌ Exclude your Downloads folder (common malware entry point)
- ❌ Exclude Documents folder (macros in Office files)
- ❌ Exclude your entire home directory (too broad)
- ❌ Exclude email attachment directories
- ❌ Exclude USB mount points (external media often contains threats)

**Performance Impact Example:**

```
Scan without exclusions:
├─ Files scanned: 250,000
├─ Scan time: 8 minutes
└─ False positives: 15 detections in build/

Scan with exclusions (node_modules, build, .git):
├─ Files scanned: 45,000
├─ Scan time: 90 seconds
└─ False positives: 0 detections
```

⚠️ **Warning:** Every exclusion reduces protection. Only exclude directories you completely trust.

💡 **Tip:** Use the Statistics Dashboard to see how many files are scanned. If the number drops unexpectedly after adding exclusions, review your patterns.

---

### Notification Settings

ClamUI can display desktop notifications when scans complete, threats are detected, or virus definitions are updated.

#### Enabling Desktop Notifications

**To Enable/Disable Notifications:**

1. Open Preferences (`Ctrl+,`)
2. Look for the "Notifications" group (usually at the top or in a General settings page)
3. Toggle the "Desktop Notifications" switch
   - **On:** Show notifications
   - **Off:** Silent mode (no notifications)

**When Notifications Appear:**

| Event | Notification | Priority |
|-------|--------------|----------|
| **Scan Complete (Clean)** | "No threats found (X files scanned)" | Normal |
| **Threats Detected** | "Threats Detected! X infected file(s) found" | **Urgent** (stays visible longer) |
| **Database Update Success** | "Virus definitions updated" | Normal |
| **Database Update Failed** | "Database update failed" with error | Normal |
| **Scheduled Scan Complete** | "Scheduled scan complete" with results | Normal |

**Notification Behavior:**

- Appear in the GNOME notification area (top-right on most systems)
- Click a notification to open ClamUI and view details
- Dismiss automatically after a few seconds (except urgent threats)
- Persist in notification center for review

**When to Enable Notifications:**

✅ **Enable if you:**
- Want immediate awareness of scan results
- Run scheduled scans while away from computer
- Need alerts for detected threats
- Multitask and may not watch scan progress

❌ **Disable if you:**
- Find notifications distracting
- Always monitor scans manually
- Run frequent scans that would spam notifications
- Use ClamUI in a server/headless environment

**Notification Examples:**

```
┌─────────────────────────────────────────┐
│ ClamUI                              [×] │
│ ─────────────────────────────────────── │
│ Scan Complete                           │
│ No threats found (1,234 files scanned)  │
│                                  2m ago │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ClamUI                              [×] │
│ ─────────────────────────────────────── │
│ ⚠️ Threats Detected!                    │
│ 3 infected file(s) found                │
│                                  now    │
└─────────────────────────────────────────┘
```

💡 **Tip:** Notifications are especially useful for scheduled scans. Enable them to get alerts even when you're not actively using ClamUI.

⚠️ **Note:** Notifications require a GNOME-compatible desktop environment. They may not work in all Linux desktop environments.

**To Test Notifications:**

1. Enable "Desktop Notifications"
2. Run a Quick Scan (Downloads folder)
3. Wait for scan to complete
4. You should see a "Scan Complete" notification

If notifications don't appear:
- Check your desktop environment notification settings
- Ensure ClamUI has notification permissions
- Try the "Test EICAR" button (should trigger threat notification)

---

### Saving and Applying Settings

After configuring any settings, you must explicitly save them.

#### Save & Apply Page

1. Open Preferences (`Ctrl+,`)
2. Navigate to "Save & Apply" in the sidebar
3. Review the "Current Status" indicator:
   - **"Ready"** ✅ - Settings can be saved
   - **"Saving..."** ⏳ - Save in progress
   - **"Error"** ❌ - Previous save failed

#### Applying Configuration Changes

**To Save All Settings:**

1. Click the **"Save & Apply"** button (blue/suggested-action style)
2. **For ClamAV configuration changes** (Database Updates, Scanner Settings):
   - Authentication dialog appears
   - Enter your administrator/sudo password
   - Click "Authenticate"
3. Wait for confirmation: "Configuration Saved" dialog
4. Click "OK" to dismiss confirmation

**What Gets Saved:**

| Settings Page | What Changes | Requires Admin Password |
|---------------|--------------|-------------------------|
| Database Updates | `/etc/clamav/freshclam.conf` | ✅ Yes |
| Scanner Settings | `/etc/clamav/clamd.conf` | ✅ Yes |
| Scan Backend | `~/.config/clamui/settings.json` | ❌ No |
| Scheduled Scans | `~/.config/clamui/settings.json` + system schedule | ✅ Yes (for schedule) |
| Exclusions | `~/.config/clamui/settings.json` | ❌ No |
| Notifications | `~/.config/clamui/settings.json` | ❌ No |

**Automatic Backups:**

Before saving ClamAV configuration files, ClamUI creates backups:

```
/etc/clamav/freshclam.conf.bak  ← Previous version
/etc/clamav/clamd.conf.bak      ← Previous version
```

💡 **Tip:** If changes cause problems, restore from backups:
```bash
sudo cp /etc/clamav/freshclam.conf.bak /etc/clamav/freshclam.conf
sudo systemctl restart clamav-freshclam
```

#### Applying Changes to Services

Some changes require service restarts to take effect:

**After Changing Database Update Settings:**
```bash
# Restart freshclam service
sudo systemctl restart clamav-freshclam

# Or run a manual update
sudo freshclam
```

**After Changing Scanner Settings:**
```bash
# Restart clamd service
sudo systemctl restart clamav-daemon

# Verify daemon is running
systemctl status clamav-daemon
```

**After Changing Scheduled Scans:**
No action needed - ClamUI automatically creates/updates systemd timers or crontab entries.

**To Verify Schedule Changes:**
```bash
# View systemd timer
systemctl --user list-timers clamui-scan

# View crontab entry
crontab -l | grep clamui
```

#### Troubleshooting Save Errors

**Common Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| "Authentication failed" | Wrong password | Re-enter correct sudo password |
| "Permission denied" | Not in sudoers | Add user to sudo group: `sudo usermod -aG sudo USERNAME` |
| "File not found" | Config file missing | Install ClamAV packages: `sudo apt install clamav clamav-daemon` |
| "Invalid configuration" | Syntax error in settings | Review settings, check error message details |
| "Failed to enable schedule" | Systemd/cron not available | Check system has systemd or cron installed |

**If Save Fails:**

1. Check the error message details in the dialog
2. Verify ClamAV is installed: `clamscan --version`
3. Check file permissions: `ls -l /etc/clamav/`
4. Try manual config edit: `sudo nano /etc/clamav/freshclam.conf`
5. Check ClamUI logs for detailed errors

💡 **Tip:** Always save and test settings one page at a time. This makes it easier to identify which change caused an issue.

---

### Settings Storage Locations

Understanding where settings are stored helps with backups and troubleshooting.

**ClamUI Application Settings:**
```
~/.config/clamui/settings.json
```
Contains:
- Scan backend preference
- Notification enabled/disabled
- Scheduled scan configuration
- Global exclusion patterns
- Minimize to tray settings

**ClamAV System Configuration:**
```
/etc/clamav/freshclam.conf  ← Database updates
/etc/clamav/clamd.conf      ← Scanner daemon
```

**Scan Profiles:**
```
~/.config/clamui/profiles.json
```

**Scheduled Scan Scripts:**
```
# Systemd user timer
~/.config/systemd/user/clamui-scan.timer
~/.config/systemd/user/clamui-scan.service

# Or crontab entry (alternative)
crontab -l
```

**Backup Recommendations:**

To backup all your ClamUI settings:
```bash
# Backup ClamUI application settings
cp -r ~/.config/clamui ~/clamui-settings-backup

# Backup ClamAV system configuration (requires sudo)
sudo cp /etc/clamav/freshclam.conf ~/freshclam.conf.backup
sudo cp /etc/clamav/clamd.conf ~/clamd.conf.backup
```

To restore settings:
```bash
# Restore ClamUI application settings
cp -r ~/clamui-settings-backup/* ~/.config/clamui/

# Restore ClamAV system configuration (requires sudo)
sudo cp ~/freshclam.conf.backup /etc/clamav/freshclam.conf
sudo cp ~/clamd.conf.backup /etc/clamav/clamd.conf
sudo systemctl restart clamav-freshclam clamav-daemon
```

---

### Settings Best Practices

**For Home Desktop Users:**
- ✅ Scan Backend: "Auto (prefer daemon)"
- ✅ Database Updates: 12-24 checks per day
- ✅ Scanner: All file types enabled, balanced limits
- ✅ Exclusions: Enable preset development directories if applicable
- ✅ Notifications: Enabled

**For Developers:**
- ✅ Scan Backend: "Auto (prefer daemon)" for speed
- ✅ Exclusions: Enable all preset patterns (node_modules, .git, etc.)
- ✅ Custom Exclusions: Add project-specific build directories
- ✅ Scanner Limits: Increase MaxFiles (20,000+) for large projects

**For Security-Conscious Users:**
- ✅ Scan Backend: "ClamAV Daemon (clamd)" if available
- ✅ Database Updates: 24 checks per day (hourly)
- ✅ Scanner: All file types enabled, high limits
- ✅ Exclusions: Minimal - only media libraries
- ✅ Logging: Verbose enabled for audit trail
- ✅ Notifications: Enabled for immediate threat alerts

**For Low-Bandwidth Connections:**
- ✅ Database Updates: 4-6 checks per day
- ✅ Scanner Limits: Lower MaxScanSize (200 MB) for faster scans
- ✅ Consider local mirror if available

💡 **Tip:** Start with default settings and adjust only when you have a specific need. ClamAV's defaults are chosen for good security and performance balance.

---

## System Tray and Background Features

*(This section will be completed in subtask 3.4)*

---

## Troubleshooting

*(This section will be completed in subtask 4.1)*

---

## Frequently Asked Questions

*(This section will be completed in subtask 4.2)*

---

## Need More Help?

If you're experiencing issues not covered in this guide:

- **Report bugs**: Visit the [GitHub Issues](https://github.com/rooki/clamui/issues) page
- **Technical documentation**: See [DEVELOPMENT.md](./DEVELOPMENT.md) for developer information
- **Installation help**: Check the [Installation Guide](./INSTALL.md)

---

*Last updated: January 2026*
