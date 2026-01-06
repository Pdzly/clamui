# Flathub Submission Checklist for ClamUI

This document provides a comprehensive guide for submitting ClamUI to Flathub, the centralized app store for Flatpak applications.

## Table of Contents

- [Pre-Submission Requirements](#pre-submission-requirements)
- [Screenshot Requirements](#screenshot-requirements)
- [Quality Guidelines Checklist](#quality-guidelines-checklist)
- [Submission Process](#submission-process)
- [Post-Submission Update Process](#post-submission-update-process)
- [Troubleshooting](#troubleshooting)

---

## Pre-Submission Requirements

### Application Requirements

- [ ] Application is Free and Open Source Software (FOSS)
  - ClamUI uses MIT license (FOSS-compliant)

- [ ] Source code is publicly available
  - Repository: https://github.com/Pdzly/clamui

- [ ] No bundled proprietary libraries or dependencies
  - All dependencies are open source (GTK4, libadwaita, Python)

- [ ] Application ID follows reverse-DNS format
  - Current: `com.github.rooki.ClamUI`

### File Validation

Before submission, validate all packaging files:

```bash
# Validate desktop entry
desktop-file-validate com.github.rooki.ClamUI.desktop

# Validate AppStream metadata
appstream-util validate-relax com.github.rooki.ClamUI.metainfo.xml

# Validate Flatpak manifest (builds successfully)
flatpak-builder --show-manifest com.github.rooki.ClamUI.yml

# Full test build
flatpak-builder --force-clean --repo=repo build-dir com.github.rooki.ClamUI.yml
```

### Required Files Checklist

- [ ] `com.github.rooki.ClamUI.yml` - Flatpak manifest
- [ ] `com.github.rooki.ClamUI.metainfo.xml` - AppStream metadata
- [ ] `com.github.rooki.ClamUI.desktop` - Desktop entry file
- [ ] Application icon (SVG preferred, min 128x128 PNG)

---

## Screenshot Requirements

### Technical Specifications

Flathub has strict screenshot requirements for software center visibility:

| Requirement | Specification |
|-------------|---------------|
| **Format** | PNG (preferred) or JPEG |
| **Minimum width** | 620 pixels |
| **Recommended size** | 1600x900 or 1920x1080 |
| **Aspect ratio** | 16:9 recommended |
| **Content** | English language, no placeholders |
| **Count** | Minimum 1, recommended 3-5 |

### URL Requirements

Screenshots must be hosted at **publicly accessible URLs**:

- [ ] URLs must be HTTPS
- [ ] URLs must be stable (not temporary/expiring)
- [ ] Images must load without authentication
- [ ] Recommended hosting: GitHub repository `/screenshots/` folder

**Current screenshot location in metainfo.xml:**
```xml
<image>https://raw.githubusercontent.com/Pdzly/clamui/main/screenshots/main-window.png</image>
```

### Screenshot Checklist

Create and host the following screenshots:

- [ ] **Main window** - Default view showing scan interface
  - Filename: `screenshots/main-window.png`
  - Caption: "Main application window showing scan interface"

- [ ] **Scan in progress** (optional but recommended)
  - Filename: `screenshots/scanning.png`
  - Caption: "Background scanning with progress indicator"

- [ ] **Scan results** (optional but recommended)
  - Filename: `screenshots/results.png`
  - Caption: "Clear display of scan results"

### Creating Screenshots

```bash
# Install GNOME Screenshot or use Flameshot
sudo dnf install gnome-screenshot  # Fedora
sudo apt install gnome-screenshot  # Ubuntu

# Take screenshot of running app
# Ensure window is using Adwaita theme
# Use a clean, representative state
gnome-screenshot -w -f main-window.png
```

### Uploading Screenshots

1. Create `screenshots/` directory in main repository
2. Add screenshots to the directory
3. Commit and push to main branch
4. Update `metainfo.xml` with correct URLs:

```xml
<screenshots>
  <screenshot type="default">
    <caption>Main application window showing scan interface</caption>
    <image>https://raw.githubusercontent.com/Pdzly/clamui/main/screenshots/main-window.png</image>
  </screenshot>
  <screenshot>
    <caption>Background scanning with progress indicator</caption>
    <image>https://raw.githubusercontent.com/Pdzly/clamui/main/screenshots/scanning.png</image>
  </screenshot>
</screenshots>
```

---

## Quality Guidelines Checklist

Based on [Flathub Quality Guidelines](https://docs.flathub.org/docs/for-app-authors/requirements/):

### Application Quality

- [ ] Application launches without errors
- [ ] Application launches within reasonable time (<5 seconds)
- [ ] Application window properly integrates with desktop environment
- [ ] No visible debug output or console errors in normal operation
- [ ] Graceful error handling for edge cases

### AppStream Metadata Quality

- [ ] **Name**: Clear, concise application name
  - Current: "ClamUI"

- [ ] **Summary**: One-line description (max 35 characters recommended)
  - Current: "Graphical interface for ClamAV antivirus scanner"

- [ ] **Description**: At least one paragraph describing functionality
  - Must include feature list
  - Must mention host ClamAV requirement

- [ ] **Categories**: Appropriate categories selected
  - Current: System, Security, Utility

- [ ] **Keywords**: Relevant search terms
  - Current: virus, antivirus, scanner, clamav, security, malware

- [ ] **Content Rating**: OARS 1.1 rating included
  - Current: Empty (appropriate for utility apps)

- [ ] **Release Notes**: At least one release entry
  - Current: v0.1.0 with feature list

### Permission Justification

Flathub reviewers scrutinize permissions. Document justifications:

| Permission | Justification |
|------------|---------------|
| `--filesystem=home` | Required for user file/directory scanning (core app function) |
| `--talk-name=org.freedesktop.Flatpak` | Required for `flatpak-spawn --host` to execute host ClamAV binaries |
| `--socket=session-bus` | Notifications for scan completion (optional but good UX) |
| `--socket=wayland` | Native Wayland display |
| `--socket=fallback-x11` | X11 compatibility |
| `--device=dri` | GPU acceleration for UI |
| `--share=ipc` | Required for X11 shared memory |

### ClamUI-Specific Considerations

- [ ] **Host ClamAV requirement** clearly documented in:
  - [ ] AppStream description
  - [ ] README.md
  - [ ] In-app error message when ClamAV not found

- [ ] **flatpak-spawn usage** justified:
  - Security scanner cannot bundle virus definitions
  - Host ClamAV allows shared virus database updates
  - Users expect system ClamAV integration

---

## Submission Process

### Step 1: Prepare Repository

1. Ensure all files are validated (see [Pre-Submission Requirements](#pre-submission-requirements))
2. Upload screenshots to public URLs
3. Update metainfo.xml with actual screenshot URLs
4. Tag a release version:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

### Step 2: Fork Flathub Repository

```bash
# Fork https://github.com/flathub/flathub via GitHub UI

# Clone your fork
git clone https://github.com/YOUR_USERNAME/flathub.git
cd flathub

# Create new branch
git checkout -b add-clamui
```

### Step 3: Create Submission Files

Create a new directory with your app manifest:

```bash
# Create app directory
mkdir com.github.rooki.ClamUI
cd com.github.rooki.ClamUI
```

Create `com.github.rooki.ClamUI.yml` (Flathub version):

```yaml
app-id: com.github.rooki.ClamUI
runtime: org.gnome.Platform
runtime-version: '47'
sdk: org.gnome.Sdk
command: clamui

finish-args:
  - --share=ipc
  - --socket=wayland
  - --socket=fallback-x11
  - --device=dri
  - --filesystem=home
  - --talk-name=org.freedesktop.Flatpak
  - --socket=session-bus

cleanup:
  - /include
  - /lib/pkgconfig
  - /share/man
  - '*.la'
  - '*.a'

modules:
  - name: clamui
    buildsystem: simple
    build-commands:
      - pip3 install --verbose --no-deps --no-build-isolation --prefix=/app .
      - install -Dm644 com.github.rooki.ClamUI.desktop -t /app/share/applications/
      - install -Dm644 com.github.rooki.ClamUI.metainfo.xml -t /app/share/metainfo/
    sources:
      - type: git
        url: https://github.com/Pdzly/clamui.git
        tag: v0.1.0
        commit: <COMMIT_HASH>  # Required: full commit hash for the tag
```

### Step 4: Submit Pull Request

```bash
# Add and commit
git add com.github.rooki.ClamUI/
git commit -m "Add ClamUI - Graphical interface for ClamAV"

# Push to your fork
git push origin add-clamui
```

Create PR via GitHub UI with:

**Title:** `Add com.github.rooki.ClamUI`

**Description:**
```markdown
## Application

ClamUI - Graphical interface for ClamAV antivirus scanner

## Repository

https://github.com/Pdzly/clamui

## License

MIT

## Notes

This application uses `flatpak-spawn --host` to execute ClamAV binaries
installed on the host system. This approach is required because:

1. ClamAV virus databases are shared system-wide
2. Regular database updates via `freshclam` are managed by the system
3. Bundling ClamAV would require independent database management

The `--filesystem=home` permission allows users to scan their personal files,
which is the core functionality of the application.

## Checklist

- [x] Manifest validated with flatpak-builder
- [x] AppStream metadata passes validation
- [x] Screenshots hosted at accessible URLs
- [x] Application follows quality guidelines
```

### Step 5: Respond to Review

Flathub maintainers will review the submission. Common feedback:

1. **Permission justification** - Explain why each permission is needed
2. **Screenshot issues** - Fix broken URLs or quality issues
3. **Metadata improvements** - Better descriptions, more keywords
4. **Build failures** - Debug and fix manifest issues

### Step 6: Post-Approval

Once approved:

1. Separate repository created: `github.com/flathub/com.github.rooki.ClamUI`
2. You receive maintainer access
3. Application published to Flathub within 24 hours
4. Users can install: `flatpak install flathub com.github.rooki.ClamUI`

---

## Post-Submission Update Process

### Releasing Updates

After initial Flathub acceptance, updates are managed via the dedicated Flathub repo:

```bash
# Clone the Flathub app repository
git clone https://github.com/flathub/com.github.rooki.ClamUI.git
cd com.github.rooki.ClamUI

# Update to new version
# 1. Tag new release in main repo
# 2. Update manifest with new tag and commit hash
```

### Update Workflow

1. **Tag new release** in main repository:
   ```bash
   cd /path/to/clamui
   git tag v0.2.0
   git push origin v0.2.0
   ```

2. **Update Flathub manifest**:
   ```bash
   cd /path/to/flathub-com.github.rooki.ClamUI

   # Edit manifest - update tag and commit
   # sources:
   #   - type: git
   #     url: https://github.com/Pdzly/clamui.git
   #     tag: v0.2.0
   #     commit: abc123...  # New commit hash
   ```

3. **Update AppStream metadata**:
   - Add new `<release>` entry to metainfo.xml
   - Include release notes

4. **Create PR**:
   ```bash
   git checkout -b v0.2.0
   git add .
   git commit -m "Update to v0.2.0"
   git push origin v0.2.0
   ```

5. **Merge PR** - Once CI passes, merge to main branch
6. **Automatic publication** - Flathub builds and publishes within hours

### Version Numbering

Follow semantic versioning for releases:

- **Major** (1.0.0): Breaking changes, major features
- **Minor** (0.2.0): New features, backward compatible
- **Patch** (0.1.1): Bug fixes, minor improvements

### Updating Screenshots

If UI changes significantly:

1. Take new screenshots
2. Upload to main repository `/screenshots/`
3. Update metainfo.xml URLs if filenames changed
4. Include in next release update

### Emergency Fixes

For security or critical bug fixes:

1. Create and tag hotfix release
2. Fast-track Flathub PR with explanation
3. Request expedited review if needed

---

## Troubleshooting

### Common Build Failures

**Python import errors:**
```
ModuleNotFoundError: No module named 'gi'
```
**Solution:** GNOME SDK provides PyGObject. Use `--no-deps` in pip install.

**Missing files:**
```
install: cannot stat 'com.github.rooki.ClamUI.desktop': No such file or directory
```
**Solution:** Ensure all files are in source tree and `type: dir` or `type: git` includes them.

**Permission denied:**
```
flatpak-spawn: error: Permission denied
```
**Solution:** Ensure `--talk-name=org.freedesktop.Flatpak` in finish-args.

### Validation Failures

**AppStream validation:**
```bash
# Check specific errors
appstream-util validate com.github.rooki.ClamUI.metainfo.xml

# Common fixes:
# - Add missing <release> entries
# - Fix screenshot URLs (must be HTTPS)
# - Add required elements (summary, description)
```

**Desktop entry validation:**
```bash
desktop-file-validate com.github.rooki.ClamUI.desktop

# Common fixes:
# - Ensure Categories ends with semicolon
# - Add required fields (Type, Name, Exec)
```

### Review Rejection Reasons

| Reason | Resolution |
|--------|------------|
| "Excessive permissions" | Justify each permission in PR description |
| "Screenshots not loading" | Verify URLs are publicly accessible HTTPS |
| "Missing content rating" | Add `<content_rating type="oars-1.1"/>` |
| "Non-free dependencies" | Remove or replace proprietary components |
| "Build failure on aarch64" | Test multi-arch build, ensure dependencies available |

### Getting Help

- **Flathub Matrix:** #flatpak:matrix.org
- **Flathub Discourse:** https://discourse.flathub.org/
- **Documentation:** https://docs.flathub.org/

---

## Quick Reference Commands

```bash
# Full local build test
flatpak-builder --force-clean --repo=repo build-dir com.github.rooki.ClamUI.yml

# Install locally for testing
flatpak-builder --user --install --force-clean build-dir com.github.rooki.ClamUI.yml

# Run installed Flatpak
flatpak run com.github.rooki.ClamUI

# Check permissions
flatpak info --show-permissions com.github.rooki.ClamUI

# Validate metadata
appstream-util validate-relax com.github.rooki.ClamUI.metainfo.xml
desktop-file-validate com.github.rooki.ClamUI.desktop

# View installed app info
flatpak info com.github.rooki.ClamUI
```

---

## Final Submission Checklist

Before creating the Flathub PR, verify:

- [ ] All packaging files validated without errors
- [ ] Screenshots uploaded to public URLs and loading correctly
- [ ] metainfo.xml URLs point to actual screenshots (not placeholders)
- [ ] At least one release tagged in main repository
- [ ] Manifest uses git source with tag and commit hash
- [ ] Permission justifications prepared for PR description
- [ ] Host ClamAV requirement documented in multiple places
- [ ] Local build and run test successful
- [ ] Multi-architecture build tested (if possible)

**Note:** Do NOT submit to Flathub until ALL items above are checked. Incomplete submissions may be rejected and require resubmission.
