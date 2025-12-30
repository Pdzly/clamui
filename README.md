# ClamUI

A modern Linux desktop application that provides a graphical user interface for the ClamAV antivirus command-line tool. Built with PyGObject, GTK4, and Adwaita for a native GNOME appearance.

## Features

- **Folder/File Selection**: Select files or directories to scan using the native GTK4 file dialog
- **Async Scanning**: Scans run in the background, keeping the UI responsive
- **Results Display**: Clear, readable display of scan results
- **ClamAV Detection**: Graceful handling when ClamAV is not installed
- **Modern UI**: Native Adwaita styling with proper GNOME integration

## Installation

### Flatpak (Recommended)

Flatpak is the recommended installation method for most users. It works on any Linux distribution and provides automatic updates.

> **Important: ClamAV Host Requirement**
>
> ClamUI requires ClamAV to be installed on your **host system** (not inside the Flatpak sandbox). The Flatpak app uses your system's ClamAV installation for scanning. See [Installing ClamAV](#installing-clamav) below.

**Install from Flathub:**

```bash
# Install ClamUI from Flathub
flatpak install flathub com.github.rooki.ClamUI

# Run the application
flatpak run com.github.rooki.ClamUI
```

**Or build and install locally:**

```bash
# Clone the repository
git clone https://github.com/yourusername/clamui.git
cd clamui

# Build and install
flatpak-builder --user --install --force-clean build-dir com.github.rooki.ClamUI.yml

# Run the application
flatpak run com.github.rooki.ClamUI
```

### Installing ClamAV

ClamUI requires ClamAV to be installed on your system. Install it using your distribution's package manager:

**Ubuntu/Debian:**
```bash
sudo apt install clamav
sudo freshclam  # Update virus definitions
```

**Fedora:**
```bash
sudo dnf install clamav clamav-update
sudo freshclam  # Update virus definitions
```

**Arch Linux:**
```bash
sudo pacman -S clamav
sudo freshclam  # Update virus definitions
```

**openSUSE:**
```bash
sudo zypper install clamav
sudo freshclam  # Update virus definitions
```

Verify your ClamAV installation:
```bash
clamscan --version
```

### From Source (Development)

For development or if you prefer not to use Flatpak:

#### System Dependencies

ClamUI requires the following system packages (Ubuntu/Debian):

```bash
# GTK4 and Adwaita runtime libraries
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 libadwaita-1-dev

# Build dependencies (required for pip install)
sudo apt install libgirepository-2.0-dev libcairo2-dev pkg-config python3-dev
# On Ubuntu < 24.04, use: libgirepository1.0-dev instead of libgirepository-2.0-dev

# ClamAV antivirus
sudo apt install clamav
```

For other distributions:
- **Fedora**: `sudo dnf install python3-gobject python3-gobject-devel gtk4 libadwaita gobject-introspection-devel cairo-gobject-devel clamav`
- **Arch**: `sudo pacman -S python-gobject gtk4 libadwaita clamav`

#### Python Dependencies

- Python 3.x
- PyGObject >= 3.48.0
- pycairo >= 1.25.0

#### Installation Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/clamui.git
   cd clamui
   ```

2. **Install system dependencies** (see above)

3. **Install Python dependencies with uv**:
   ```bash
   uv sync
   ```

4. **Verify ClamAV installation**:
   ```bash
   which clamscan
   clamscan --version
   ```

#### Running from Source

```bash
uv run clamui
```

## Project Structure

```
clamui/
├── src/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── app.py               # Adw.Application class
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── window.py        # Main application window
│   │   └── scan_view.py     # Scan interface component
│   └── core/
│       ├── __init__.py
│       ├── scanner.py       # ClamAV subprocess integration
│       └── utils.py         # Utility functions
├── pyproject.toml
├── uv.lock
├── README.md
└── .gitignore
```

## Usage

1. Launch the application with `uv run clamui`
2. Click the folder selection button to choose a file or directory to scan
3. Click the "Scan" button to start the antivirus scan
4. View the results in the results display area

## ClamAV Exit Codes

The application interprets ClamAV exit codes as follows:
- **0**: No viruses found (clean)
- **1**: Virus(es) found
- **2**: Error occurred during scan

## Development

### Tech Stack

- **Language**: Python 3.x
- **Framework**: PyGObject (GTK4 bindings)
- **UI Toolkit**: GTK4 with libadwaita

### Key Patterns

- Uses `Adw.Application` for modern GNOME application structure
- Background scanning with `threading.Thread` and `GLib.idle_add()` for thread-safe UI updates
- Subprocess integration with `clamscan` for antivirus scanning
- Automatic Flatpak sandbox detection with `flatpak-spawn --host` for ClamAV execution

### Running Tests

```bash
python -m pytest tests/
```

### Building Flatpak Locally

For development and testing of the Flatpak package:

1. **Install Flatpak build tools:**
   ```bash
   # Ubuntu/Debian
   sudo apt install flatpak-builder flatpak

   # Fedora
   sudo dnf install flatpak-builder flatpak

   # Arch
   sudo pacman -S flatpak-builder flatpak
   ```

2. **Add Flathub repository and install GNOME SDK:**
   ```bash
   flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
   flatpak install flathub org.gnome.Platform//46 org.gnome.Sdk//46
   ```

3. **Build the Flatpak:**
   ```bash
   flatpak-builder --force-clean --repo=repo build-dir com.github.rooki.ClamUI.yml
   ```

4. **Install and run locally:**
   ```bash
   flatpak-builder --user --install --force-clean build-dir com.github.rooki.ClamUI.yml
   flatpak run com.github.rooki.ClamUI
   ```

5. **Validate packaging files:**
   ```bash
   # Validate AppStream metadata
   appstream-util validate-relax com.github.rooki.ClamUI.metainfo.xml

   # Validate desktop entry
   desktop-file-validate com.github.rooki.ClamUI.desktop
   ```

### Flatpak Architecture

ClamUI uses `flatpak-spawn --host` to execute ClamAV binaries on the host system from within the Flatpak sandbox. This approach:

- Requires ClamAV to be installed on the host (not bundled in Flatpak)
- Uses the `--talk-name=org.freedesktop.Flatpak` permission
- Automatically detects the Flatpak environment via `/.flatpak-info`
- Falls back to direct execution when running outside Flatpak

## License

This project is open source. See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
