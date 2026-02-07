# Frequently Asked Questions

[← Back to User Guide](../USER_GUIDE.md)

---

## Frequently Asked Questions

This section answers common questions about using ClamUI, understanding scan results, managing performance, and keeping
your data safe.

---

### Is ClamUI the same as ClamAV?

**No, but they work together.**

**ClamUI** is a graphical user interface (GUI) application that makes ClamAV easier to use. It provides:

- Point-and-click scanning without terminal commands
- Visual scan results with threat details
- Quarantine management for detected threats
- Scheduled scans that run automatically
- Statistics and scan history tracking

**ClamAV** is the underlying antivirus engine that does the actual virus scanning. It's a powerful command-line tool
created by Cisco.

**How they work together:**

```
┌─────────────────────────────────────┐
│  You click "Scan" in ClamUI         │
│  (Easy-to-use graphical interface)  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  ClamUI sends command to ClamAV     │
│  (Behind the scenes)                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  ClamAV scans files for viruses     │
│  (Powerful antivirus engine)        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  ClamUI shows you the results       │
│  (Clean, threat cards, actions)     │
└─────────────────────────────────────┘
```

**Key point:** You need **both** installed for ClamUI to work. ClamUI won't scan anything without ClamAV.

💡 **Tip:** When ClamUI first launches, it checks if ClamAV is installed. If not found, you'll see an error message with
installation instructions.

**See also:**

- [First-Time Setup](getting-started.md#first-time-setup) - Installing ClamAV if missing
- [ClamAV Not Found](troubleshooting.md#clamav-not-found) - Troubleshooting installation issues

---

### How often should I scan my computer?

**It depends on your usage, but here's practical guidance:**

#### Recommended Scanning Schedules

**For most home users:**

- ✅ **Daily Quick Scan** - Downloads folder (10-30 seconds)
- ✅ **Weekly Home Folder Scan** - Your entire home directory (10-30 minutes)
- ✅ **Monthly Full System Scan** - Everything on your computer (30-90+ minutes)

**For security-conscious users:**

- ✅ **Every 6 hours Quick Scan** - Downloads folder
- ✅ **Daily Home Folder Scan** - Your home directory
- ✅ **Weekly Full System Scan** - Entire system

**For casual users (minimal downloads):**

- ✅ **Weekly Quick Scan** - Downloads folder
- ✅ **Monthly Home Folder Scan** - Your home directory
- ✅ **Quarterly Full System Scan** - Every 3 months

**For developers/power users:**

- ✅ **Daily Quick Scan** - Downloads folder
- ✅ **Weekly Custom Scans** - Projects, Documents (with dev exclusions)
- ✅ **Monthly Full System Scan** - Entire system

#### What Affects How Often to Scan?

| Your Usage                  | Risk Level | Recommended Frequency                  |
|-----------------------------|------------|----------------------------------------|
| Frequent file downloads     | Higher     | Daily Quick Scan, Weekly Home Scan     |
| Regular USB drive use       | Higher     | Scan each USB when connected           |
| Opening email attachments   | Higher     | Daily Quick Scan, Weekly Home Scan     |
| Browsing untrusted websites | Higher     | Daily Quick Scan, 2x weekly Home Scan  |
| Mostly offline usage        | Lower      | Weekly Quick Scan, Monthly Home Scan   |
| No downloads, only browsing | Lower      | Weekly Quick Scan, Quarterly Full Scan |
| Software development        | Medium     | Daily Quick Scan, Weekly Custom Scan   |
| Running a server            | Higher     | Daily Full Scan (with exclusions)      |

#### Best Practices

**DO:**

- ✅ Scan immediately after downloading files from unknown sources
- ✅ Scan USB drives and external storage before opening files
- ✅ Set up scheduled scans so you don't have to remember
- ✅ Scan more often during periods of heavy downloading
- ✅ Update virus definitions daily (automatic by default)

**DON'T:**

- ❌ Wait until you suspect an infection - scan regularly
- ❌ Only scan when you see suspicious behavior
- ❌ Ignore scheduled scans because they're "inconvenient"
- ❌ Scan less often because "Linux doesn't get viruses" (it can!)

#### Setting Up Scheduled Scans

**The easiest way to maintain regular scanning:**

1. Open **Preferences** (Ctrl+,)
2. Go to **Scheduled Scans** tab
3. Enable **"Enable scheduled scans"**
4. Set frequency (Daily recommended)
5. Choose scan time (early morning works well)
6. Set targets (Downloads or Home)
7. Click **Save & Apply**

**Example configuration for balanced protection:**

```
Frequency: Daily
Time: 02:00 (2 AM)
Targets: ~/Downloads,~/Documents
Battery-aware: Yes (skip on battery)
Auto-quarantine: No (review threats first)
```

💡 **Tip:** Morning scans (2 AM - 6 AM) run while you sleep, won't interrupt your work, and complete before you start
your day.

⚠️ **Important:** Virus definitions matter more than scan frequency! Even with daily scans, outdated definitions (30+
days old) won't detect new threats. ClamUI auto-updates definitions, but verify they're current in the Statistics view.

**See also:**

- [Scheduled Scans](scheduling.md) - Complete scheduling guide
- [Scan Profiles](profiles.md) - Creating custom scan targets
- [Understanding Protection Status](statistics.md#understanding-protection-status) - Checking when you last scanned

---

### What should I do if a scan finds threats?

**Don't panic! Follow this step-by-step plan:**

#### Step 1: Review the Threat Details

**Look at each detected threat carefully:**

```
Example threat card:
┌────────────────────────────────────────────┐
│ 🔴 Win.Trojan.Generic-12345                │  ← Threat name
│ Severity: CRITICAL                         │  ← How serious
│ /home/user/Downloads/suspicious.exe        │  ← File location
│ Category: Trojan                           │  ← Threat type
│ [Quarantine] [Copy Path]                   │  ← Your actions
└────────────────────────────────────────────┘
```

**Check:**

- ✅ **File path** - Do you recognize this file? Did you download it?
- ✅ **Severity level** - CRITICAL/HIGH = act immediately, MEDIUM/LOW = investigate
- ✅ **Threat category** - Virus, Trojan, Adware, or Test (EICAR)?
- ✅ **File type** - Is it an executable (.exe, .sh, .app, .jar)?

#### Step 2: Determine if It's Real or False Positive

**Real threats typically:**

- 🔴 Come from unknown/untrusted sources
- 🔴 Have suspicious names (crack.exe, keygen.sh, patch.bin)
- 🔴 Were downloaded from file-sharing or piracy sites
- 🔴 Appeared unexpectedly in system directories
- 🔴 Are executable files you didn't intentionally download
- 🔴 Have CRITICAL or HIGH severity

**False positives typically:**

- 🟡 Are legitimate development tools (compilers, debuggers)
- 🟡 Come from trusted sources (official websites, package managers)
- 🟡 Are files you created yourself (scripts, compiled programs)
- 🟡 Have generic detection names (Heuristics.*, PUA.*)
- 🟡 Are from reputable software vendors
- 🟡 Have LOW or MEDIUM severity

#### Step 3: Choose Your Action

**For REAL threats (or when uncertain):**

1. **Quarantine immediately:**
    - Click the **[Quarantine]** button on the threat card
    - The file is moved to secure storage (can't harm your system)
    - You can restore it later if it was a mistake

2. **Verify it's quarantined:**
    - Go to **Quarantine** view
    - Confirm the file appears in the list
    - Note the detection date

3. **Delete permanently (optional):**
    - After 30 days, use "Clear Old Items" to auto-delete
    - Or manually delete from Quarantine view if you're certain
    - ⚠️ **Warning:** Deletion is permanent - can't be undone

4. **Check for more infections:**
    - Run a **Full Scan** to check entire system
    - Check recent scan history for similar threats
    - Consider re-scanning after updating definitions

**For likely FALSE POSITIVES:**

1. **Research the detection:**
    - Copy the threat name (e.g., "Win.Tool.Mimikatz")
    - Search online: "[threat name] false positive ClamAV"
    - Check ClamAV forums, security websites, vendor documentation

2. **Verify the file source:**
    - Did you download it from the official website?
    - Can you re-download from a trusted source?
    - Is it a known legitimate tool?

3. **If confirmed false positive:**
    - **DON'T** quarantine (unless you want to be extra safe)
    - Add exclusion to prevent future detections:
        - Preferences → Exclusion Patterns → Add: `/path/to/false/positive/file`
    - Or add to scan profile exclusions for targeted scanning

4. **Report to ClamAV:**
    - Visit [ClamAV False Positive Reporting](https://www.clamav.net/reports/fp)
    - Submit the file hash (don't upload the file if it's proprietary)
    - Helps improve ClamAV's detection accuracy

#### Step 4: Prevent Future Infections

**Best practices:**

- ✅ Only download files from trusted sources
- ✅ Verify file checksums (SHA-256) for important downloads
- ✅ Enable scheduled scans for automatic protection
- ✅ Keep virus definitions updated (daily automatic updates)
- ✅ Use USB scanning before opening files from drives
- ✅ Enable auto-quarantine for scheduled scans (optional)

#### Step 5: Review and Monitor

**After dealing with threats:**

1. **Check Scan History:**
    - Go to **Logs** view
    - Review recent scans for patterns
    - Look for repeated detections in same location

2. **Monitor quarantine:**
    - Go to **Quarantine** view
    - Review what's been isolated
    - Delete old threats after verification

3. **Verify system health:**
    - Run another scan after 24 hours
    - Check that threats haven't returned
    - Monitor system performance

#### Threat Severity Action Guide

| Severity        | Immediate Action                                        | Follow-Up                                                     |
|-----------------|---------------------------------------------------------|---------------------------------------------------------------|
| 🔴 **CRITICAL** | Quarantine immediately, disconnect network if spreading | Full system scan, check for more infections, change passwords |
| 🟠 **HIGH**     | Quarantine promptly, investigate source                 | Full system scan, review recent downloads                     |
| 🟡 **MEDIUM**   | Research online, quarantine if uncertain                | Scan related directories, monitor system                      |
| 🔵 **LOW**      | Check if false positive, investigate                    | Add exclusion if legitimate, report false positive            |

#### Example Scenarios

**Scenario 1: Downloaded executable flagged as Trojan**

```
Detection: Win.Trojan.Agent-12345 (HIGH severity)
File: ~/Downloads/game_crack.exe
Source: Unknown website
Action: 🔴 QUARANTINE IMMEDIATELY
Reason: Likely real threat - cracks often contain malware
Next: Run Full Scan, delete permanently, avoid piracy sites
```

**Scenario 2: Development tool flagged as PUA**

```
Detection: PUA.Tool.Mimikatz (MEDIUM severity)
File: ~/projects/security-tools/mimikatz.exe
Source: Official GitHub repository
Action: 🟡 RESEARCH FIRST
Reason: Legitimate pentesting tool, common false positive
Next: Verify download, add exclusion if authentic
```

**Scenario 3: EICAR test detection**

```
Detection: Eicar-Signature (LOW severity)
File: /tmp/eicar.txt
Source: EICAR test button
Action: ✅ EXPECTED BEHAVIOR
Reason: Test file, automatically cleaned up
Next: Nothing - this confirms antivirus is working
```

**Scenario 4: Multiple threats in Downloads**

```
Detection: 5 files with various threats (CRITICAL/HIGH)
Location: ~/Downloads/
Source: Unknown
Action: 🔴 QUARANTINE ALL IMMEDIATELY
Reason: Possible infection or malicious download
Next: Full system scan, review download history, clear browser cache
```

💡 **Tip:** When uncertain, **quarantine first, research later**. Quarantined files can't harm your system, and you can
always restore them if they're false positives.

⚠️ **Important:** Never manually delete detected files before quarantining - you'll lose the record and won't be able to
restore if needed.

**See also:**

- [Threat Severity Levels](scanning.md#threat-severity-levels) - Understanding severity classifications
- [Quarantine Management](quarantine.md) - How quarantine works
- [False Positives](#why-did-my-file-get-flagged-as-a-false-positive) - Understanding false detections

---

### Why did my file get flagged as a false positive?

**False positives happen when legitimate files are incorrectly identified as threats. Here's why and what to do:**

#### Common Causes of False Positives

**1. Generic or Heuristic Detection**

- ClamAV uses pattern matching and behavioral analysis
- Generic signatures match broad patterns (e.g., "Win.Trojan.Generic")
- Legitimate software may share patterns with malware

**Example:**

```
Detection: Heuristics.Win32.Generic.Suspicious
Reason: Compiler optimization created code pattern similar to malware
Common in: Custom-built executables, development tools, games
```

**2. Potentially Unwanted Applications (PUA)**

- Software that's not malware but may be unwanted
- Includes: adware, bundled software, browser toolbars, crypto miners
- Detection name often starts with "PUA."

**Example:**

```
Detection: PUA.Win.Adware.OpenCandy
Reason: Software includes bundled ads (annoying but not harmful)
Common in: Free software installers, download managers
```

**3. Legitimate Security/Admin Tools**

- Pentesting tools, debuggers, password recovery utilities
- These tools CAN be used maliciously, so ClamAV flags them
- If you're using them legitimately, they're false positives

**Example:**

```
Detection: PUA.Win.Tool.Mimikatz
Reason: Password extraction tool (legit for pentesters, malicious for attackers)
Common in: Security research, penetration testing, forensics
```

**4. Compressed or Packed Executables**

- Software compressed with packers (UPX, ASPack, etc.)
- Malware often uses packing to hide, so it triggers detection
- Legitimate software also uses packing to reduce file size

**Example:**

```
Detection: Heuristics.Packed.UPX
Reason: Executable compressed with UPX packer
Common in: Game executables, portable apps, installers
```

**5. Custom or Self-Compiled Software**

- Programs you compiled yourself
- Open-source software built from source
- Lacks digital signatures that verify legitimacy

**Example:**

```
Detection: Heuristics.ELF.Generic
Reason: Your compiled program matches a generic pattern
Common in: Development work, hobbyist programming, custom scripts
```

**6. Outdated Virus Definitions**

- Old signatures sometimes flag current software
- Software updates change file structure, triggering old signatures
- Fixed in newer ClamAV database versions

**Example:**

```
Detection: Win.Trojan.OldSignature-12345
Reason: Software version mismatch with database
Common in: Recently updated apps, beta software
```

#### How to Confirm a False Positive

**Method 1: Check the Source**

✅ **Likely FALSE POSITIVE if:**

- Downloaded from official vendor website
- Installed via package manager (apt, dnf, flatpak)
- Open-source project from reputable repository (GitHub, GitLab)
- Software you compiled yourself from trusted source code
- Common development tools (GCC, Python, Node.js modules)

🔴 **Likely REAL THREAT if:**

- Downloaded from file-sharing sites, torrents, or warez sites
- Source is unknown or untrusted
- File appeared without you downloading it
- Came from email attachment from unknown sender
- Downloaded from sketchy "free download" sites with ads

**Method 2: Research the Detection Name**

**Search online:**

```
"[detection name] false positive"
"[detection name] ClamAV"
"[software name] [detection name]"
```

**Check these sources:**

- ClamAV forums and mailing lists
- Software vendor's website or forums
- Security forums (Stack Exchange, Reddit /r/antivirus)
- VirusTotal (upload file hash, check other engines)

**Example search:**

```
Search: "PUA.Win.Tool.Mimikatz false positive"
Results: Confirms it's a legitimate pentesting tool flagged by design
```

**Method 3: Check File Properties**

**Examine the file:**

```bash
# Check file type:
file /path/to/suspected/file

# Check if it's executable:
ls -lh /path/to/suspected/file

# Check digital signature (if available):
# Windows: Right-click → Properties → Digital Signatures
# Linux: Check with codesign or similar tools
```

**Legitimate files often have:**

- ✅ Readable file type (ELF binary, Python script, etc.)
- ✅ Reasonable file size for its type
- ✅ Modification date matching when you created/downloaded it
- ✅ Digital signatures from known vendors (Windows executables)

**Method 4: Scan with Multiple Engines**

**Use VirusTotal:**

1. Go to [virustotal.com](https://www.virustotal.com/)
2. Upload the file OR upload just its SHA-256 hash (safer for proprietary files)
3. Check how many engines detect it

**Interpretation:**

- **1-3 detections out of 60+** → Likely false positive
- **20+ detections** → Likely real threat
- **Mix of generic names** → Possibly false positive
- **Specific threat names** → Likely real threat

**Example:**

```
VirusTotal Results:
- ClamAV: PUA.Win.Tool.Mimikatz
- Windows Defender: No threat
- Kaspersky: No threat
- Bitdefender: No threat
- Other 55 engines: No threat

Conclusion: False positive specific to ClamAV's signature
```

#### What to Do with False Positives

**Option 1: Add Exclusion (Recommended)**

**For a specific file:**

```
1. Open Preferences (Ctrl+,)
2. Go to Exclusion Patterns
3. Add the full file path:
   /home/user/projects/my-tool/compiled-binary
4. Save settings
```

**For a directory pattern:**

```
Add pattern: */build/*
Excludes: All "build" directories (common for compiled code)
```

**For a file type:**

```
Add pattern: *.pyc
Excludes: All Python compiled bytecode files
```

**When to use:**

- ✅ You're certain it's a false positive
- ✅ File is from a trusted source
- ✅ You need the file and want to keep scanning everything else
- ✅ Detection keeps recurring

**Option 2: Use Scan Profile Exclusions**

**For targeted exclusions:**

```
1. Open Scan Profiles
2. Edit or create profile
3. Add exclusions specific to that profile
4. Scan with that profile

Example: Development Projects profile
- Targets: ~/projects
- Exclusions: */node_modules/*, */build/*, */.git/*
```

**When to use:**

- ✅ False positives only affect specific directories
- ✅ You want different rules for different scans
- ✅ Development work with many false positives

**Option 3: Quarantine and Monitor**

**For uncertain cases:**

```
1. Click [Quarantine] to isolate the file
2. Research the detection thoroughly
3. If confirmed false positive:
   - Restore from quarantine
   - Add exclusion to prevent recurrence
4. If still unsure:
   - Keep it quarantined
   - Monitor for 30 days
   - Delete with "Clear Old Items" if truly unwanted
```

**When to use:**

- ⚠️ You're unsure if it's a false positive
- ⚠️ File might be unwanted even if not malicious
- ⚠️ Better safe than sorry approach

**Option 4: Report False Positive to ClamAV**

**Help improve detection accuracy:**

1. **Visit:** [https://www.clamav.net/reports/fp](https://www.clamav.net/reports/fp)

2. **Provide:**
    - Detection name (e.g., "PUA.Win.Tool.Mimikatz")
    - File description (what software it's from)
    - File hash (SHA-256) - safer than uploading file
    - Explanation why it's a false positive

3. **Wait for review:**
    - ClamAV team investigates
    - Signature updated in future database release
    - Your file won't be flagged in next update

**When to use:**

- ✅ You've confirmed it's definitely a false positive
- ✅ It's a common piece of software (affects many users)
- ✅ You want to help improve ClamAV
- ✅ File is publicly available (not proprietary)

💡 **Tip:** For proprietary or sensitive files, submit only the SHA-256 hash, not the actual file.

#### Reducing False Positives

**Best practices:**

**DO:**

- ✅ Keep ClamAV and virus definitions updated (reduces obsolete signatures)
- ✅ Use exclusions for development directories (node_modules, .git, build, __pycache__)
- ✅ Use scan profiles with targeted exclusions for different use cases
- ✅ Research detections before assuming they're false positives
- ✅ Verify file sources (official websites, package managers)

**DON'T:**

- ❌ Disable all scanning because of false positives
- ❌ Automatically exclude everything flagged
- ❌ Ignore HIGH/CRITICAL severity detections without research
- ❌ Download software from untrusted sources and call it a "false positive"

#### Common False Positive Examples

| File Type          | Common Detection          | Why It Happens          | Solution                           |
|--------------------|---------------------------|-------------------------|------------------------------------|
| Python scripts     | Heuristics.Python.Generic | Generic script pattern  | Exclude *.py or specific script    |
| Compiled binaries  | Heuristics.ELF.Generic    | Self-compiled code      | Exclude build directories          |
| Node.js modules    | Various PUA detections    | Minified code patterns  | Exclude node_modules               |
| Development tools  | PUA.Tool.*                | Can be used maliciously | Exclude dev tools directory        |
| Game files         | Packed.UPX                | Compressed executables  | Exclude game install directory     |
| Crack/keygen tools | Win.Trojan.*              | Often actual malware!   | DON'T exclude - likely real threat |

#### Understanding Detection Names

**Pattern analysis:**

```
PUA.Win.Tool.Mimikatz
│   │   │    └─ Specific variant
│   │   └─ Threat category (Tool)
│   └─ Platform (Windows)
└─ Type (Potentially Unwanted Application)

Heuristics.ELF.Generic.Suspicious
│          │   │       └─ Confidence level
│          │   └─ Generic signature
│          └─ Platform (Linux)
└─ Detection method (pattern matching)

Win.Trojan.Agent-12345
│   │       │     └─ Variant ID
│   │       └─ Family name
│   └─ Threat type
└─ Platform
```

**Key indicators of false positives:**

- 🟡 "Heuristics" - Pattern-based detection (less certain)
- 🟡 "Generic" - Broad signature (higher false positive rate)
- 🟡 "PUA" - Potentially unwanted (debatable)
- 🟡 Low severity rating

**Key indicators of real threats:**

- 🔴 Specific variant names (e.g., "WannaCry", "Emotet")
- 🔴 "Trojan", "Virus", "Worm", "Ransomware" categories
- 🔴 High/Critical severity
- 🔴 Multiple detection engines agree

💡 **Tip:** The more generic the detection name, the higher the chance of a false positive. Specific named threats (
e.g., "Trojan.Emotet.A") are usually accurate.

**See also:**

- [Threat Severity Levels](scanning.md#threat-severity-levels) - Understanding severity classifications
- [Managing Exclusion Patterns](settings.md#managing-exclusion-patterns) - Adding exclusions
- [Scan Profiles](profiles.md) - Profile-specific exclusions

---

### Does scanning slow down my computer?

**Yes, scanning uses system resources, but impact varies greatly depending on your setup:**

#### What Scanning Uses

**During a scan, ClamAV uses:**

| Resource         | Usage Level              | Impact                             |
|------------------|--------------------------|------------------------------------|
| **CPU**          | 20-80% of 1 core         | Moderate - may slow other tasks    |
| **Disk I/O**     | High (reading all files) | High - can slow file operations    |
| **Memory (RAM)** | 50-200 MB                | Low - negligible on modern systems |
| **Network**      | None during scan         | None - only for definition updates |

#### Performance Impact Comparison

**Daemon Backend (clamd) - FAST:**

```
System impact: Low to Moderate
Duration: 10-50x FASTER than clamscan
CPU: 20-40% of one core
Responsiveness: System remains usable
Best for: Regular scanning, large directories
```

**Clamscan Backend - SLOW:**

```
System impact: Moderate to High
Duration: 10-50x SLOWER than daemon
CPU: 60-80% of one core
Responsiveness: Noticeable slowdown
Best for: One-off scans, daemon unavailable
```

**Real-world examples:**

| Scan Target                | Files  | Daemon Backend | Clamscan Backend |
|----------------------------|--------|----------------|------------------|
| Downloads (100 files)      | ~50 MB | 5 seconds ⚡    | 30-60 seconds 🐌 |
| Home directory (10K files) | ~2 GB  | 4 minutes ⚡    | 30-60 minutes 🐌 |
| Full system (100K files)   | ~20 GB | 30 minutes ⚡   | 8-12 hours 🐌    |

💡 **Tip:** Always use the daemon backend (Auto mode) for best performance. It's 10-50x faster!

#### What Affects Performance?

**1. Scan Backend Choice**

- **Auto/Daemon:** Fast, recommended, minimal impact
- **Clamscan:** Very slow, high impact, avoid if possible

**2. Scan Scope**

- **Small targets** (Downloads folder): Minimal impact, completes quickly
- **Large targets** (Full system): High impact, takes time

**3. File Characteristics**

- **Many small files:** Longer (overhead per file)
- **Few large files:** Faster (efficient reading)
- **Compressed archives:** Slower (needs decompression)
- **Encrypted files:** Slower (can't scan, but tries)

**4. Storage Speed**

- **SSD:** 2-5x faster than HDD
- **NVMe SSD:** Fastest possible
- **External HDD:** Slowest (USB 2.0 very slow)
- **Network drives:** Very slow (network latency)

**5. System Resources**

- **Modern CPU** (4+ cores, 3+ GHz): Minimal slowdown
- **Older CPU** (2 cores, <2 GHz): Noticeable slowdown
- **Available RAM:** 4+ GB = no impact, <2 GB = possible slowdown
- **Other running apps:** Heavy apps compete for resources

**6. ClamAV Configuration**

- **Higher limits** (MaxFileSize, MaxScanSize): Slower but thorough
- **Lower limits:** Faster but may skip large files
- **More enabled scanners** (PDF, HTML, Archives): Slower but comprehensive

#### Minimizing Performance Impact

**Strategy 1: Use Daemon Backend**

**Enable in Preferences:**

```
Preferences → Scan Backend → Auto (recommended)
```

**Verify daemon is running:**

```bash
systemctl --user status clamav-daemon
# Should show: Active: active (running)
```

**Performance gain:** 10-50x faster than clamscan

**Strategy 2: Scan During Idle Time**

**Use scheduled scans overnight:**

```
Scheduled Scans → Daily → 02:00 (2 AM)
```

**Benefits:**

- ✅ Won't interrupt your work
- ✅ System is idle (no competing apps)
- ✅ Completes before you wake up
- ✅ Can run thorough full system scans

**Strategy 3: Scan Smaller Targets More Often**

**Instead of:**

```
❌ Weekly full system scan (90 minutes, high impact)
```

**Do this:**

```
✅ Daily Downloads scan (30 seconds, minimal impact)
✅ Weekly Home directory scan (10 minutes, moderate impact)
✅ Monthly full system scan (scheduled overnight)
```

**Strategy 4: Use Exclusions Wisely**

**Add exclusions for:**

- Development directories: `*/node_modules/*, */.git/*, */build/*`
- System directories: `/proc/*, /sys/*, /dev/*` (already excluded in Full Scan profile)
- Cache directories: `*/.cache/*, */tmp/*`
- Media libraries: `~/Videos/*, ~/Music/*` (if trusted)

**Performance gain:** Can reduce scan time by 50-80% for developer workflows

**Example:**

```
Without exclusions: 100,000 files, 45 minutes
With exclusions: 20,000 files, 8 minutes
```

**Strategy 5: Adjust ClamAV Limits**

**For faster scans (lower thoroughness):**

```
MaxFileSize 100M      # Skip files >100 MB
MaxScanSize 100M      # Scan first 100 MB of archives
MaxRecursion 10       # Limit archive depth
```

**For thorough scans (slower):**

```
MaxFileSize 500M      # Scan files up to 500 MB
MaxScanSize 500M      # Scan deeper into archives
MaxRecursion 17       # Default recursion depth
```

**Edit in Preferences:**

```
Preferences → Scanner Configuration → Performance and Limits
```

**Strategy 6: Use Battery-Aware Scanning**

**For laptops:**

```
Scheduled Scans → Battery-aware scanning: Yes
```

**What it does:**

- ⚡ Scans normally when plugged in (AC power)
- 🔋 Skips scans when on battery (preserves power)
- ✅ Won't drain battery during travel

**Strategy 7: Close Heavy Applications**

**Before large scans:**

```
❌ Close: Web browsers (Chrome, Firefox), IDEs, video editors, games
✅ System is more responsive during scan
✅ Scan completes faster (more resources available)
```

#### When Scanning WILL Slow You Down

**Expect noticeable impact when:**

**1. Using clamscan backend**

- Can take 10-50x longer
- Uses 60-80% CPU
- Makes system sluggish
- **Solution:** Enable daemon

**2. Scanning during active work**

- Competes for disk I/O
- Slows file operations (opening, saving)
- **Solution:** Use scheduled scans overnight

**3. Scanning entire system on HDD**

- Disk thrashing (constant seeking)
- Everything becomes slow
- **Solution:** Scan smaller targets, upgrade to SSD

**4. Scanning from USB 2.0 drive**

- Very slow transfer speeds (60 MB/s max)
- Can take hours for large drives
- **Solution:** Use USB 3.0, or scan overnight

**5. Running other heavy tasks**

- Video encoding, compiling, gaming
- All compete for CPU/disk
- **Solution:** Pause scan, schedule for later

**6. Low-end hardware**

- Old CPU (<2 cores, <2 GHz)
- Limited RAM (<2 GB)
- System struggles with any workload
- **Solution:** Scan very small targets, schedule overnight, add exclusions

#### When Scanning WON'T Slow You Down

**Minimal impact scenarios:**

**1. Quick Scan with daemon**

- ✅ Downloads folder (100-500 files)
- ✅ Completes in 5-30 seconds
- ✅ Barely noticeable

**2. Scheduled scans overnight**

- ✅ Runs while you sleep
- ✅ No competition for resources
- ✅ Zero perceived impact

**3. Modern hardware**

- ✅ SSD (fast disk access)
- ✅ 4+ core CPU (plenty of cores)
- ✅ 8+ GB RAM (no memory pressure)
- ✅ Background scan barely noticeable

**4. Small targeted scans**

- ✅ Single file or small folder
- ✅ Sub-second to few seconds
- ✅ No noticeable impact

#### Background Scanning

**ClamUI supports background scanning:**

**How it works:**

1. Start a scan (Quick/Full, or scheduled)
2. Minimize ClamUI or work in other apps
3. Scan continues in background
4. Notification shows when complete

**Impact:**

- Moderate disk/CPU usage continues
- System remains usable for most tasks
- Heavy tasks (video editing, gaming) may be affected
- Light tasks (browsing, documents) usually fine

**Best for:**

- Overnight scheduled scans
- Scanning while doing light work
- Downloads folder scans during browsing

**Not ideal for:**

- Gaming (CPU competition)
- Video editing (disk I/O competition)
- Compiling code (CPU + disk competition)

💡 **Tip:** Use the system tray icon to monitor background scans without opening the main window.

#### Performance Optimization Summary

**For BEST performance:**

1. ✅ Enable daemon backend (10-50x speedup)
2. ✅ Use scheduled scans overnight (zero perceived impact)
3. ✅ Scan smaller targets more frequently (quick, minimal impact)
4. ✅ Add exclusions for dev/cache directories (50-80% fewer files)
5. ✅ Use SSD if possible (2-5x faster than HDD)
6. ✅ Close heavy apps before manual scans
7. ✅ Adjust limits for balance (MaxFileSize, MaxRecursion)
8. ✅ Enable battery-aware mode on laptops

**Expected performance with optimizations:**

```
Quick Scan (Downloads): 5-10 seconds, imperceptible impact
Home Scan (with exclusions): 5-10 minutes, light background activity
Full Scan (scheduled overnight): 20-40 minutes, zero perceived impact
```

⚠️ **Important:** Never sacrifice security for speed! It's better to schedule thorough scans overnight than to skip them
because they're "too slow."

**See also:**

- [Scan Backend Options](settings.md#scan-backend-options) - Enabling daemon
- [Scheduled Scans](scheduling.md) - Automating overnight scans
- [Performance Issues](troubleshooting.md#performance-issues) - Troubleshooting slow scans
- [Managing Exclusion Patterns](settings.md#managing-exclusion-patterns) - Adding exclusions

---

### Is my data safe when using quarantine?

**Yes, quarantine is designed to be safe and secure. Here's how ClamUI protects your data:**

#### How Quarantine Protects Your Data

**1. Files Are Moved, Not Deleted**

```
Original: /home/user/Downloads/suspected.exe
Quarantined: /home/user/.local/share/clamui/quarantine/abc123.dat

✅ Original location preserved in database
✅ Can be restored to exact original path
✅ Not deleted until you explicitly confirm
```

**2. Secure Storage Location**

```
Directory: ~/.local/share/clamui/quarantine/
Permissions: 700 (only you can access)
Files: Renamed to prevent accidental execution
Database: Tracks all metadata (path, date, hash)

✅ Files can't accidentally run
✅ No other users can access them
✅ Complete audit trail
```

**3. Integrity Verification**

```
On quarantine: SHA-256 hash calculated and stored
On restore: Hash verified before restoring
Mismatch: Restore fails with error

✅ Ensures file wasn't corrupted
✅ Prevents partial/damaged restores
✅ Detects tampering
```

**4. Metadata Preservation**

```
Database stores:
- Original full path
- Detection date and time
- File size (bytes)
- SHA-256 hash
- Threat name

✅ Complete history of what was quarantined
✅ Can review before deleting
✅ Audit trail for security review
```

**5. Reversible Process**

```
Quarantine → Review → Restore or Delete

✅ Not permanent until you delete
✅ Can undo false positive detections
✅ 30-day buffer before auto-cleanup
```

#### What Could Go Wrong? (And How ClamUI Handles It)

**Scenario 1: Disk Full During Quarantine**

```
Problem: Not enough space to move file
ClamUI response:
  - Quarantine fails with clear error
  - Original file stays in place (not deleted)
  - Error message suggests freeing space
  - You can manually delete or free space first

Your data: ✅ SAFE - not deleted, still accessible
```

**Scenario 2: File Corruption**

```
Problem: File corrupted during move
ClamUI response:
  - SHA-256 hash mismatch detected
  - Restore operation fails
  - Error message shown
  - Original corrupted file remains in quarantine

Your data: ⚠️ Corrupted, but not made worse
Note: Corruption during filesystem operations is extremely rare
```

**Scenario 3: Accidental Deletion**

```
Problem: You click "Delete" instead of "Restore"
ClamUI response:
  - Confirmation dialog appears (destructive action)
  - Must explicitly confirm deletion
  - Deletion is immediate and permanent

Your data: ❌ DELETED - cannot be recovered
Prevention: Pay attention to confirmation dialogs
```

**Scenario 4: Database Corruption**

```
Problem: quarantine.db database file corrupted
ClamUI response:
  - Database error shown in UI
  - Files still exist in quarantine directory
  - Can manually restore files (see manual commands)
  - Can rebuild database or delete/recreate

Your data: ✅ SAFE - files exist, can be manually restored
```

**Scenario 5: Permission Issues**

```
Problem: Can't write to quarantine directory
ClamUI response:
  - Permission denied error
  - Quarantine fails
  - Original file stays in place

Your data: ✅ SAFE - not deleted, still accessible
```

**Scenario 6: System Crash During Quarantine**

```
Problem: Power loss or crash while quarantining
Possible outcomes:
  - File partially moved: may exist in both locations
  - Database not updated: file moved but not tracked
  - File deleted without record: rare, filesystem dependent

Your data: ⚠️ Potentially in inconsistent state
Recovery:
  - Check original location
  - Check quarantine directory
  - Worst case: file may be lost (very rare)
Prevention: Don't force shutdown during operations
```

#### Quarantine Safety Features

| Safety Feature       | Purpose                     | Benefit                          |
|----------------------|-----------------------------|----------------------------------|
| SHA-256 hashing      | Verify file integrity       | Detect corruption before restore |
| Move operation       | Don't copy then delete      | Atomic operation, safer          |
| Metadata database    | Track all details           | Complete audit trail             |
| Confirmation dialogs | Prevent accidents           | Require explicit confirmation    |
| 700 permissions      | Prevent unauthorized access | Only you can access quarantine   |
| Restore preview      | Show destination path       | Verify before restoring          |
| 30-day retention     | Keep old items              | Buffer against accidents         |
| Manual file access   | Direct filesystem access    | Can recover without UI           |

#### When Is Quarantine NOT Safe?

**These scenarios are YOUR responsibility:**

**1. Intentionally deleting quarantined files**

- ⚠️ Deletion is permanent - can't be undone
- ⚠️ Make sure you've verified the file is a real threat
- ⚠️ Use "Clear Old Items" to auto-delete after 30 days (safer)

**2. Quarantining important files you need**

- ⚠️ If you quarantine a file you're actively using, apps may fail
- ⚠️ Example: Quarantining a database file breaks the app
- ⚠️ Solution: Restore immediately if it's a false positive

**3. Manually deleting quarantine directory**

```bash
# ❌ DON'T DO THIS:
rm -rf ~/.local/share/clamui/quarantine/
```

- ⚠️ Bypasses all safety checks
- ⚠️ Deletes files AND database
- ⚠️ Permanent, no recovery

**4. Modifying quarantine files manually**

```bash
# ❌ DON'T DO THIS:
echo "corrupted" > ~/.local/share/clamui/quarantine/abc123.dat
```

- ⚠️ Hash verification will fail
- ⚠️ Restore won't work
- ⚠️ File is ruined

**5. Running out of disk space**

- ⚠️ Quarantine will fail
- ⚠️ Files stay in original location (still a threat if real)
- ⚠️ Monitor disk space if quarantining many/large files

#### Best Practices for Safe Quarantine Use

**DO:**

- ✅ Review quarantined files before deleting
- ✅ Use "Clear Old Items" for automatic cleanup (30 days)
- ✅ Restore false positives promptly
- ✅ Add exclusions for restored false positives
- ✅ Monitor disk space if quarantining large files
- ✅ Keep quarantine for audit trail (see what was detected)
- ✅ Verify file paths before restoring
- ✅ Use restore function, not manual file copying

**DON'T:**

- ❌ Manually delete quarantine directory
- ❌ Edit files in quarantine directory
- ❌ Bypass confirmation dialogs (they're there for a reason)
- ❌ Quarantine system files you need
- ❌ Restore files without researching the detection
- ❌ Delete files immediately - keep them for review
- ❌ Ignore "disk full" errors

#### Quarantine vs. Other Options

**Comparison:**

| Action                 | Reversible? | Data Safety              | When to Use                         |
|------------------------|-------------|--------------------------|-------------------------------------|
| **Quarantine**         | ✅ Yes       | Very Safe                | Uncertain threats, want to review   |
| **Delete immediately** | ❌ No        | Permanent                | NEVER - too risky                   |
| **Leave in place**     | ✅ Yes       | Risky if real threat     | Only if certain it's false positive |
| **Add exclusion**      | ✅ Yes       | Safe for false positives | Confirmed false positives only      |

**Recommendation:** **Always quarantine first, research later.** It's the safest approach.

#### How to Verify Quarantine Is Working

**Test quarantine with EICAR:**

1. **Create EICAR test:**
    - Click "Test with EICAR" button
    - Or manually create: `echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar.txt`

2. **Scan the file:**
    - Scan `/tmp/eicar.txt`
    - Should detect: `Eicar-Signature`

3. **Quarantine it:**
    - Click [Quarantine] button
    - Success message appears

4. **Verify in quarantine:**
    - Go to Quarantine view
    - See `Eicar-Signature` entry
    - Check details (path, date, size, hash)

5. **Restore it:**
    - Click [Restore] button
    - Confirm restoration
    - File back in original location

6. **Delete it:**
    - Quarantine again
    - Click [Delete] button
    - Confirm deletion
    - File permanently removed

✅ If all steps work, quarantine is functioning correctly!

#### Manual Quarantine Access (Advanced)

**If you need to manually manage quarantine:**

**View quarantined files:**

```bash
ls -lh ~/.local/share/clamui/quarantine/
```

**Check database:**

```bash
sqlite3 ~/.local/share/clamui/quarantine.db "SELECT threat_name, original_path, detection_date FROM quarantine;"
```

**Manually restore a file:**

```bash
# ⚠️ Warning: This bypasses hash verification!
# Get file ID from database first
cp ~/.local/share/clamui/quarantine/abc123.dat /original/path/filename
```

**Check quarantine size:**

```bash
du -sh ~/.local/share/clamui/quarantine/
```

**For Flatpak installation:**

```bash
ls -lh ~/.var/app/io.github.linx_systems.ClamUI/data/clamui/quarantine/
```

⚠️ **Warning:** Manual operations bypass safety checks. Use the UI whenever possible.

#### Quarantine Storage Limits

**Plan for disk space:**

**Typical quarantine sizes:**

```
Small threats (scripts, text): 1-50 KB each
Medium threats (executables): 100 KB - 5 MB each
Large threats (installers, archives): 10-100 MB each

Total storage depends on detection frequency:
- Home user, rare detections: <100 MB
- Developer, frequent false positives: 500 MB - 2 GB
- Security researcher, intentional samples: 5-50 GB
```

**Best practices:**

- Review and delete or restore files within 30 days
- Use "Clear Old Items" monthly
- Monitor disk space if quarantining many files
- Don't use quarantine for long-term malware storage (use dedicated analysis VM)

#### Privacy Considerations

**What's private:**

- ✅ Quarantine directory is user-specific (`~/.local/share/clamui/`)
- ✅ Only you (and root) can access quarantined files
- ✅ File permissions: 700 (user-only access)
- ✅ Files renamed to prevent identification

**What's NOT private:**

- ⚠️ Root user can access all files
- ⚠️ System backups may include quarantine directory
- ⚠️ If you share the database or file hashes, threats can be identified

**Recommendations:**

- Don't share quarantine directory or database
- Exclude quarantine from system backups if concerned about privacy
- If sharing system logs, redact file paths from quarantine

#### The Bottom Line

**Is my data safe? YES, if you:**

- ✅ Use the quarantine feature as designed (via UI)
- ✅ Don't manually delete quarantine directory
- ✅ Review files before deleting permanently
- ✅ Keep adequate disk space available
- ✅ Use restore function for false positives
- ✅ Pay attention to confirmation dialogs

**Quarantine is designed to be safe AND reversible.** It's the recommended way to handle detected threats because:

- You can research the threat without risk
- You can restore false positives easily
- You have an audit trail of what was detected
- Files can't harm your system while quarantined

💡 **Tip:** Think of quarantine as "isolation" rather than "deletion" - it's a holding area where threats can't harm you,
but you can still access them if needed.

**See also:**

- [Quarantine Management](quarantine.md) - Complete quarantine guide
- [Understanding Quarantine Storage](quarantine.md#understanding-quarantine-storage) - Storage details
- [Restoring Files](quarantine.md#restoring-files-from-quarantine) - Recovery process

---

### How do I update virus definitions?

**ClamUI automatically updates virus definitions, but you can also update manually:**

#### Automatic Updates (Recommended)

**ClamUI updates definitions automatically by default:**

**What happens:**

1. **Daily updates:** ClamAV's `freshclam` service runs automatically
2. **Checks for new definitions:** Connects to ClamAV database mirrors
3. **Downloads if available:** New signatures downloaded and installed
4. **Logs the update:** Visible in Logs view (Update History tab)
5. **No action needed:** Completely automatic

**How often:**

- Default: **24 times per day** (checks every hour)
- Configurable in Preferences → Database Update Settings

**To verify automatic updates are working:**

1. **Check Statistics view:**
   ```
   Statistics → Protection Status
   Look for: "Definitions: Up to date (Updated X hours ago)"
   ```

2. **Check Logs view:**
   ```
   Logs → Historical Logs
   Look for: 🔄 update entries with "success" or "up_to_date" status
   ```

3. **Check update service:**
   ```bash
   systemctl status clamav-freshclam
   # Should show: Active: active (running)
   ```

💡 **Tip:** If definitions are updated within the last 24 hours, you're protected! ClamAV releases new definitions
multiple times daily.

#### Manual Updates

**When to update manually:**

- 🔄 Before important scans
- 🔄 After system startup (if computer was off for days)
- 🔄 When troubleshooting detection issues
- 🔄 If automatic updates failed
- 🔄 When you see "Definitions outdated" warning

**Method 1: Update View (GUI)**

**Step-by-step:**

1. Click **Update** navigation button (in header bar)
2. Click **Check for Updates** button
3. Watch progress:
    - "Checking for updates..."
    - "Downloading database updates..." (if available)
    - "Database update completed successfully!"
4. View details:
    - Current version number
    - Last update date/time
    - Update status

**What you'll see:**

```
Status messages:
✅ "Your virus definitions are up to date"
   → No update needed, definitions are current

✅ "Database update completed successfully!"
   → New definitions downloaded and installed

ℹ️ "Database is up to date (already current)"
   → Checked for updates, but already have latest

⚠️ "Update failed: [error message]"
   → See troubleshooting below
```

**Method 2: Terminal Command**

**For immediate updates:**

```bash
# Native installation:
sudo freshclam

# Flatpak installation (bundled ClamAV):
flatpak run --command=freshclam io.github.linx_systems.ClamUI

# Flatpak with daemon backend (host clamd):
flatpak-spawn --host sudo freshclam
```

**Expected output:**

```
ClamAV update process started at [date]
daily.cvd database is up-to-date
main.cvd database is up-to-date
bytecode.cvd database is up-to-date
```

**If updates available:**

```
Downloading daily-12345.cdiff [100%]
daily.cvd updated (version: 12345, sigs: 123456)
Database updated (123456 signatures) from database.clamav.net
```

#### Understanding Update Status

**In Statistics view, you'll see:**

**"Definitions: Up to date"**

- ✅ Updated within last 24 hours
- ✅ System is protected with latest signatures
- ✅ No action needed

**"Definitions: Updated X hours ago"**

- ⚠️ Last update was X hours ago
- ⚠️ If X > 24 hours, may want to update
- ⚠️ If X > 7 days, should update immediately

**"Definitions: Outdated (Updated X days ago)"**

- 🔴 Definitions are old
- 🔴 New threats won't be detected
- 🔴 Update immediately

**"Definitions: Unknown"**

- ❓ Can't determine definition age
- ❓ ClamAV may not be installed correctly
- ❓ Check ClamAV installation

#### Configuring Update Settings

**To change update frequency:**

1. Open **Preferences** (Ctrl+,)
2. Go to **Database Update Settings** tab
3. Find **"Checks per day"** setting
4. Adjust value:
   ```
   1 = Once daily (every 24 hours)
   2 = Every 12 hours
   4 = Every 6 hours
   24 = Every hour (default, recommended)
   ```
5. Click **Save & Apply**

**Recommended settings:**

| Internet Connection | Checks per Day     | Bandwidth Impact         |
|---------------------|--------------------|--------------------------|
| Unlimited broadband | 24 (every hour)    | Negligible (~1-5 MB/day) |
| Limited bandwidth   | 4 (every 6 hours)  | Minimal (~1-5 MB/day)    |
| Mobile hotspot      | 2 (every 12 hours) | Low (~1-5 MB/day)        |
| Metered connection  | 1 (once daily)     | Very low (~1-5 MB/day)   |

💡 **Tip:** Even 24 checks per day uses minimal bandwidth - only downloads if new definitions exist.

#### Update Database Locations

**Where definitions are stored:**

**Native installation:**

```
Default: /var/lib/clamav/
Files:
  - daily.cvd (or daily.cld) - Daily updates
  - main.cvd - Main signature database
  - bytecode.cvd - Bytecode signatures
```

**Flatpak installation:**

```
Location: Host system (/var/lib/clamav/)
Note: Uses host ClamAV installation
```

**To check database versions:**

```bash
sigtool --info /var/lib/clamav/daily.cvd
sigtool --info /var/lib/clamav/main.cvd
```

**Output shows:**

```
Build time: 02 Jan 2026 10:45 +0000
Version: 12345
Signatures: 123456
```

#### Troubleshooting Update Issues

**Problem: "Update failed: Connection error"**

**Causes:**

- No internet connection
- ClamAV mirrors are down
- Firewall blocking updates
- Proxy configuration needed

**Solutions:**

1. **Check internet connection:**
   ```bash
   ping -c 3 google.com
   ```

2. **Try different mirror:**
   ```
   Preferences → Database Update Settings → Database Mirror
   Change from default to specific mirror
   ```

3. **Check firewall:**
   ```bash
   # Allow freshclam through firewall:
   sudo ufw allow out 53/tcp
   sudo ufw allow out 80/tcp
   ```

4. **Configure proxy** (if behind corporate proxy):
   ```
   Preferences → Database Update Settings → Proxy Settings
   HTTPProxyServer: proxy.company.com
   HTTPProxyPort: 8080
   ```

**Problem: "Update failed: Permission denied"**

**Cause:** Don't have permission to write to `/var/lib/clamav/`

**Solution:**

```bash
# Fix permissions:
sudo chown -R clamav:clamav /var/lib/clamav/
sudo chmod 755 /var/lib/clamav/

# Or run update with sudo:
sudo freshclam
```

**Problem: "Database initialization error"**

**Cause:** Corrupted database files

**Solution:**

```bash
# Remove old databases and re-download:
sudo systemctl stop clamav-daemon
sudo systemctl stop clamav-freshclam
sudo rm /var/lib/clamav/*.cvd
sudo rm /var/lib/clamav/*.cld
sudo freshclam
sudo systemctl start clamav-freshclam
sudo systemctl start clamav-daemon
```

**Problem: Updates succeed but scans fail**

**Cause:** Daemon not reloaded after update

**Solution:**

```bash
# Restart daemon to load new definitions:
sudo systemctl restart clamav-daemon

# Or configure auto-reload in Preferences:
Preferences → Database Update Settings → NotifyClamd
Set to: /var/run/clamav/clamd.ctl
```

#### How Often Are New Definitions Released?

**ClamAV updates frequently:**

- **Daily updates:** Multiple times per day (hence "daily.cvd")
- **Main database:** Updated less frequently (monthly)
- **Urgent updates:** Critical threats may trigger immediate updates

**What gets updated:**

- New virus signatures
- Updated detection patterns
- Heuristic improvements
- False positive fixes

**Why frequent updates matter:**

```
New malware is created constantly:
- 350,000+ new malware samples DAILY (globally)
- 0-day exploits appear regularly
- Ransomware variants evolve quickly

Outdated definitions = blind to new threats
```

💡 **Tip:** The "daily" database updates multiple times per day during active threat periods.

#### Bandwidth Considerations

**How much data does updating use?**

**Typical update sizes:**

```
Daily update (differential):
  - If current: 0 bytes (no download)
  - If 1 day old: ~1-2 MB
  - If 7 days old: ~5-10 MB
  - If 30+ days old: ~50-100 MB (full database)

Main database (rare updates):
  - ~100-150 MB (only when released)

Bytecode database:
  - ~1-5 MB (rare updates)
```

**Daily bandwidth usage:**

```
24 checks/day × 1-2 MB (when updates exist) = ~1-5 MB/day
Most checks = 0 bytes (already current)

Monthly estimate: ~50-150 MB
Yearly estimate: ~500 MB - 2 GB
```

**This is negligible compared to:**

- Streaming music: ~50 MB/hour
- Watching videos: ~500 MB/hour
- Web browsing: ~100 MB/hour

⚠️ **Important:** Don't disable updates to save bandwidth - the security benefit far outweighs the minimal data usage.

#### Verifying Definitions Are Current

**Check definition age:**

**Method 1: Statistics view**

```
Statistics → Protection Status
Look for: "Definitions: Up to date (Updated X hours ago)"

✅ <24 hours ago: Current
⚠️ 1-7 days ago: Slightly outdated, update recommended
🔴 >7 days ago: Outdated, update immediately
```

**Method 2: Terminal**

```bash
sigtool --info /var/lib/clamav/daily.cvd | grep "Build time"
# Shows when database was built

# Example output:
Build time: 02 Jan 2026 10:45 +0000
# Compare to current date/time
```

**Method 3: ClamAV version check**

```bash
clamscan --version
# Shows ClamAV version and database version

# Example output:
ClamAV 1.0.0/27000/Mon Jan  2 10:45:32 2026
           └─ Database version (should be recent date)
```

#### Best Practices

**DO:**

- ✅ Keep automatic updates enabled (default)
- ✅ Check update status weekly (Statistics view)
- ✅ Update manually before important scans
- ✅ Verify definitions are <24 hours old
- ✅ Check Logs view for update failures
- ✅ Keep freshclam service running

**DON'T:**

- ❌ Disable automatic updates
- ❌ Ignore update failures
- ❌ Scan with outdated definitions (>7 days)
- ❌ Stop freshclam service
- ❌ Manually delete database files (unless troubleshooting)

#### Update Frequency Recommendation

**For best protection:**

```
Automatic updates: Enabled ✅
Checks per day: 24 (every hour) ✅
Manual updates: Before important scans ✅
Verification: Check Statistics view weekly ✅
```

💡 **Remember:** Antivirus protection is only as good as your virus definitions. Keep them updated!

**See also:**

- [Database Update Settings](settings.md#database-update-settings) - Configuring updates
- [Understanding Protection Status](statistics.md#understanding-protection-status) - Checking definition age
- [Daemon Connection Issues](troubleshooting.md#daemon-connection-issues) - Update troubleshooting

---

### Can I scan external drives and USB devices?

**Yes! ClamUI can scan any mounted storage device:**

#### Scanning External Drives

**Step-by-step:**

1. **Connect the drive:**
    - Plug in USB drive, external HDD, SD card, etc.
    - Wait for system to mount it
    - Most Linux desktops auto-mount to `/media/username/` or `/run/media/username/`

2. **Open ClamUI:**
    - Launch ClamUI
    - Go to main Scan view

3. **Select the drive:**

   **Method A: File picker**
    - Click **Browse** button
    - Navigate to drive location (e.g., `/media/user/USB_DRIVE/`)
    - Click **Select** (scans entire drive)

   **Method B: Drag and drop**
    - Open file manager
    - Drag the drive icon to ClamUI window
    - Drop it on the scan path area

   **Method C: Type path**
    - Manually type the mount path:
      ```
      /media/user/USB_DRIVE
      /run/media/user/EXTERNAL_HDD
      ```

4. **Start the scan:**
    - Click **Scan** button
    - Scan progress appears
    - Results show threats (if any)

5. **Review results:**
    - Check for detected threats
    - Quarantine any threats found
    - Safe to use drive if clean

💡 **Tip:** Always scan external drives BEFORE opening files - this prevents malware from executing on your system.

#### Finding Your Drive's Path

**Common mount locations:**

**Ubuntu/Debian/GNOME:**

```
/media/username/DRIVE_NAME/
Example: /media/john/USB_DRIVE/
```

**Fedora/RHEL:**

```
/run/media/username/DRIVE_NAME/
Example: /run/media/john/BACKUP_HDD/
```

**How to find exact path:**

**Method 1: File manager**

```
1. Open Files (file manager)
2. Click on external drive in sidebar
3. Press Ctrl+L (show path bar)
4. Copy the path shown
5. Paste into ClamUI scan path
```

**Method 2: Terminal**

```bash
# List all mounted drives:
lsblk

# Example output:
NAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT
sda      8:0    0 238.5G  0 disk
└─sda1   8:1    0 238.5G  0 part /
sdb      8:16   1  14.9G  0 disk
└─sdb1   8:17   1  14.9G  0 part /media/user/USB_DRIVE
                                  └─ This is your path!

# Or use df:
df -h | grep media
# Shows mounted drives under /media/
```

**Method 3: Check recent mounts**

```bash
mount | grep media
# Shows all devices mounted in /media/
```

#### Creating a USB Scanning Profile

**For frequent USB scanning:**

1. **Open Scan Profiles:**
    - Click **Profiles** button
    - Click **New Profile**

2. **Configure profile:**
   ```
   Name: USB Drive Scanner
   Description: Scan USB drives and external storage
   Targets: /media/user/  (scans all drives in /media/)
   Exclusions: (leave empty for thorough scan)
   ```

3. **Save the profile**

4. **Use it:**
    - Select "USB Drive Scanner" from profile dropdown
    - Click **Scan**
    - Scans all currently mounted external drives

**Alternative for specific drive:**

```
Name: Specific USB Scanner
Targets: /media/user/MY_USB_NAME/
(Replace MY_USB_NAME with actual drive label)
```

💡 **Tip:** If your USB drive always has the same name, create a profile with the exact path for one-click scanning.

#### Scanning Before Opening Files

**Best practice workflow:**

**When you connect a new drive:**

```
1. Plug in drive → System mounts it
2. DON'T open any files yet!
3. Open ClamUI
4. Scan entire drive
5. Review results
6. If clean: Safe to use
7. If threats found: Quarantine, then decide
```

**Why this matters:**

- 🔴 Malware can auto-execute when files are opened
- 🔴 Infected documents can exploit vulnerabilities
- 🔴 Scanning first prevents execution on your system

**Autorun is mostly disabled on Linux, but:**

- Files you open can still be malicious
- Scripts can be executed if you run them
- Exploits in PDF/document readers exist

#### Scanning Speed for External Drives

**Performance varies by connection:**

| Connection Type | Speed     | Scan Time (10 GB drive) |
|-----------------|-----------|-------------------------|
| USB 3.0+        | Fast      | ~5-15 minutes           |
| USB 2.0         | Slow      | ~30-60 minutes          |
| USB-C           | Very fast | ~3-10 minutes           |
| External SSD    | Very fast | ~3-10 minutes           |
| External HDD    | Moderate  | ~10-30 minutes          |
| SD Card reader  | Varies    | ~10-40 minutes          |
| Network drive   | Very slow | ~1-4+ hours             |

💡 **Tip:** Use USB 3.0 ports (blue) for faster scanning. USB 2.0 ports (black) are much slower.

**Factors affecting speed:**

- Connection type (USB 2.0 vs 3.0 vs 3.1)
- Drive type (SSD vs HDD)
- File count (many small files = slower)
- File types (archives and large files = slower)

#### Scanning Network Drives

**Yes, but slower:**

**For mounted network drives:**

```
Mount point examples:
/mnt/nas/
/media/network_drive/
~/smb_share/

Process:
1. Ensure drive is mounted
2. Scan like any other directory
3. Expect much slower speeds (network latency)
```

**Performance tips:**

- Expect 5-10x slower than local drives
- Use gigabit ethernet (not WiFi) for better speed
- Consider scanning on the NAS/server itself if possible
- Schedule overnight for large network shares

#### Safely Ejecting After Scanning

**After scanning:**

1. **Review results:**
    - Check scan results
    - Quarantine any threats
    - Note any errors

2. **Eject safely:**
   ```
   File manager → Right-click drive → Eject/Unmount

   Or terminal:
   umount /media/user/USB_DRIVE
   ```

3. **Wait for confirmation:**
    - "Safe to remove" notification
    - Drive icon disappears from file manager
    - Don't unplug until confirmed!

⚠️ **Warning:** Don't unplug drive during scan - can corrupt files!

#### What to Do If Threats Are Found

**Scenario: Malware detected on USB drive**

**Option 1: Quarantine on your system**

```
1. Quarantine the infected files
2. Files are moved from USB to your quarantine
3. USB drive is now clean
4. Safe to use USB drive

Pros: ✅ Simple, one-click
Cons: ⚠️ Malware now on your system (in quarantine)
```

**Option 2: Delete from USB directly**

```
1. Note the infected file paths
2. Open file manager
3. Navigate to USB drive
4. Delete infected files manually
5. Empty trash

Pros: ✅ Malware not on your system
Cons: ⚠️ No record in quarantine, can't restore
```

**Option 3: Format the drive (severe infections)**

```
If heavily infected or you don't need the files:

1. Backup clean files (if any)
2. Format the drive:
   - File manager → Right-click drive → Format
   - Or: sudo mkfs.ext4 /dev/sdb1
3. Restore backed-up clean files

Pros: ✅ Guaranteed clean
Cons: ⚠️ Deletes everything
```

**Recommendation:** Quarantine first (reversible), delete later if confirmed threats.

#### Scheduled Scanning for External Drives

**Can I auto-scan USB drives?**

**Short answer:** Not automatically when plugged in.

**Workaround for regularly connected drives:**

**If drive is always connected:**

```
Scheduled Scans:
  Frequency: Daily
  Targets: /media/user/PERMANENT_DRIVE/

Works if: Drive is connected at scan time
Skipped if: Drive is disconnected
```

**If drive is occasionally connected:**

```
Manual scanning required - no auto-scan on plug-in feature currently.

Workflow:
1. Plug in drive
2. Open ClamUI
3. Use "USB Drive Scanner" profile
4. Click Scan
```

💡 **Feature idea:** Auto-scan on USB plug-in could be added in future versions.

#### Common External Drive Scenarios

**Scenario 1: Borrowed USB drive**

```
Risk: HIGH (unknown source)
Action: MUST scan before opening any files
Workflow:
  1. Plug in → Scan immediately
  2. Don't open files until scan completes
  3. If threats found → Quarantine all
  4. If clean → Safe to use
```

**Scenario 2: Your own backup drive**

```
Risk: LOW (trusted source)
Action: Optional periodic scanning
Workflow:
  1. Scan monthly or before important backups
  2. Ensures backups aren't infected
  3. Prevents spreading malware via backups
```

**Scenario 3: Public computer to home transfer**

```
Risk: HIGH (public computers often infected)
Action: MUST scan before opening
Workflow:
  1. Files from public computer → USB
  2. Bring USB home
  3. Scan USB BEFORE opening files
  4. Quarantine threats
  5. Only open clean files
```

**Scenario 4: Camera SD card**

```
Risk: LOW (photos/videos less likely infected)
Action: Optional quick scan
Workflow:
  1. Quick scan recommended
  2. Mainly for peace of mind
  3. Rare to find threats in raw photo/video files
```

**Scenario 5: Software installation USB**

```
Risk: MEDIUM (depends on software source)
Action: Scan before running installers
Workflow:
  1. Scan entire USB
  2. Check installers for PUA/adware
  3. Verify source is legitimate
  4. Run installer only if clean
```

#### Tips for Safe External Drive Use

**DO:**

- ✅ Scan external drives before opening files
- ✅ Scan borrowed/unknown drives immediately
- ✅ Create a USB scanning profile for quick access
- ✅ Quarantine threats found on external drives
- ✅ Keep external drives for specific purposes (backups, transfers)
- ✅ Eject safely after scanning
- ✅ Format heavily infected drives

**DON'T:**

- ❌ Open files before scanning
- ❌ Trust borrowed drives without scanning
- ❌ Unplug during scan (corrupts files)
- ❌ Ignore threats found on external drives
- ❌ Share infected drives with others
- ❌ Use infected drives for backups

#### Performance Optimization for External Drives

**For faster scans:**

1. **Use USB 3.0+ ports:**
    - Blue USB ports (USB 3.0)
    - USB-C ports (USB 3.1/3.2)
    - Avoid black USB 2.0 ports

2. **Enable daemon backend:**
   ```
   Preferences → Scan Backend → Auto
   10-50x faster than clamscan
   ```

3. **Add exclusions for known-safe large directories:**
   ```
   If scanning backup drive with videos:
   Exclusions: *.mp4, *.mkv, *.avi
   (Reduces files scanned)
   ```

4. **Scan overnight for large drives:**
   ```
   Scheduled Scans:
     Frequency: Weekly
     Time: 02:00 (2 AM)
     Targets: /media/user/BACKUP_DRIVE/
   ```

**See also:**

- [File and Folder Scanning](scanning.md#file-and-folder-scanning) - Scanning basics
- [Creating Custom Profiles](profiles.md#creating-custom-profiles) - USB scanning profiles
- [Scan Profiles](profiles.md) - Profile management

---

