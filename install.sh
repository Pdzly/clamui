#!/bin/sh
# ClamUI Installation Script
# Installs ClamUI with context menu integration for file managers
#
# Usage: ./install.sh [OPTIONS]
#
# Options:
#   --system    Install system-wide (requires root privileges)
#   --help      Show this help message
#
# Dependencies: Python 3.10+, pip/uv, GTK4, libadwaita, ClamAV

set -e

# Colors for output (only if terminal supports it)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Logging functions
log_info() {
    printf "${BLUE}[INFO]${NC} %s\n" "$1"
}

log_success() {
    printf "${GREEN}[OK]${NC} %s\n" "$1"
}

log_warning() {
    printf "${YELLOW}[WARN]${NC} %s\n" "$1"
}

log_error() {
    printf "${RED}[ERROR]${NC} %s\n" "$1" >&2
}

# Show usage information
show_help() {
    cat << 'EOF'
ClamUI Installation Script

Usage: ./install.sh [OPTIONS]

Options:
    --system    Install system-wide to /usr/local/share (requires root)
    --help      Show this help message

By default, installs to user-local directories (~/.local/share/).
No root privileges required for user-local installation.

ClamUI is installed into an isolated virtual environment:
    - User install: ~/.local/share/clamui/venv
    - System install: /usr/local/share/clamui/venv

A wrapper script is created at ~/.local/bin/clamui (or /usr/local/bin/clamui).

Dependencies Required:
    - Python 3.10 or higher
    - pip or uv (Python package manager)
    - GTK4 with GObject Introspection
    - libadwaita
    - ClamAV (clamscan)
EOF
}

# Parse command line arguments
SYSTEM_INSTALL=0
for arg in "$@"; do
    case "$arg" in
        --system)
            SYSTEM_INSTALL=1
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $arg"
            show_help
            exit 1
            ;;
    esac
done

# Set installation directories based on mode
if [ "$SYSTEM_INSTALL" = "1" ]; then
    if [ "$(id -u)" != "0" ]; then
        log_error "System-wide installation requires root privileges."
        log_info "Please run with: sudo ./install.sh --system"
        exit 1
    fi
    SHARE_DIR="/usr/share"
    BIN_DIR="/usr/local/bin"
    log_info "Installing system-wide to $SHARE_DIR"
else
    XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
    SHARE_DIR="$XDG_DATA_HOME"
    BIN_DIR="$HOME/.local/bin"
    log_info "Installing to user directory: $SHARE_DIR"
fi

# XDG directory paths
DESKTOP_DIR="$SHARE_DIR/applications"
ICON_DIR="$SHARE_DIR/icons/hicolor/scalable/apps"
NEMO_ACTION_DIR="$SHARE_DIR/nemo/actions"
NAUTILUS_SCRIPTS_DIR="$HOME/.local/share/nautilus/scripts"
DOLPHIN_SERVICES_DIR="$SHARE_DIR/kservices5/ServiceMenus"

# Get script directory (where install.sh is located)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

#
# Dependency Checking Functions
#

# Check Python version (3.10+)
check_python() {
    log_info "Checking Python..."

    # Try python3 first, then python
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
    else
        log_error "Python not found. Please install Python 3.10 or higher."
        return 1
    fi

    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

    if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
        log_error "Python 3.10+ required. Found: $PYTHON_VERSION"
        return 1
    fi

    log_success "Python $PYTHON_VERSION found"
    return 0
}

# Check for pip or uv package manager
check_package_manager() {
    log_info "Checking package manager (pip/uv)..."

    # Prefer uv if available
    if command -v uv >/dev/null 2>&1; then
        PKG_MANAGER="uv"
        PKG_INSTALL_CMD="uv pip install"
        log_success "uv package manager found"
        return 0
    fi

    # Fall back to pip
    if command -v pip3 >/dev/null 2>&1; then
        PKG_MANAGER="pip3"
        PKG_INSTALL_CMD="pip3 install"
        log_success "pip3 found"
        return 0
    elif command -v pip >/dev/null 2>&1; then
        PKG_MANAGER="pip"
        PKG_INSTALL_CMD="pip install"
        log_success "pip found"
        return 0
    fi

    log_error "No Python package manager found. Please install pip or uv."
    log_info "Install pip: sudo apt install python3-pip"
    log_info "Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    return 1
}

# Check GTK4 availability via GObject Introspection
check_gtk4() {
    log_info "Checking GTK4..."

    if $PYTHON_CMD -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk" 2>/dev/null; then
        GTK_VERSION=$($PYTHON_CMD -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print(f'{Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}.{Gtk.MICRO_VERSION}')")
        log_success "GTK4 $GTK_VERSION found"
        return 0
    fi

    log_error "GTK4 with GObject Introspection not found."
    log_info "Install on Ubuntu/Debian: sudo apt install gir1.2-gtk-4.0"
    log_info "Install on Fedora: sudo dnf install gtk4"
    log_info "Install on Arch: sudo pacman -S gtk4"
    return 1
}

# Check libadwaita availability
check_libadwaita() {
    log_info "Checking libadwaita..."

    if $PYTHON_CMD -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw" 2>/dev/null; then
        ADW_VERSION=$($PYTHON_CMD -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw; print(f'{Adw.MAJOR_VERSION}.{Adw.MINOR_VERSION}.{Adw.MICRO_VERSION}')")
        log_success "libadwaita $ADW_VERSION found"
        return 0
    fi

    log_error "libadwaita with GObject Introspection not found."
    log_info "Install on Ubuntu/Debian: sudo apt install gir1.2-adw-1 libadwaita-1-dev"
    log_info "Install on Fedora: sudo dnf install libadwaita"
    log_info "Install on Arch: sudo pacman -S libadwaita"
    return 1
}

# Check ClamAV availability
check_clamav() {
    log_info "Checking ClamAV..."

    if command -v clamscan >/dev/null 2>&1; then
        CLAM_VERSION=$(clamscan --version 2>/dev/null | head -n1)
        log_success "$CLAM_VERSION found"
        return 0
    fi

    log_error "ClamAV (clamscan) not found."
    log_info "Install on Ubuntu/Debian: sudo apt install clamav"
    log_info "Install on Fedora: sudo dnf install clamav"
    log_info "Install on Arch: sudo pacman -S clamav"
    return 1
}

# Check all dependencies
check_all_dependencies() {
    log_info "=== Checking Dependencies ==="
    echo

    DEPS_OK=1

    if ! check_python; then
        DEPS_OK=0
    fi

    if ! check_package_manager; then
        DEPS_OK=0
    fi

    if ! check_gtk4; then
        DEPS_OK=0
    fi

    if ! check_libadwaita; then
        DEPS_OK=0
    fi

    if ! check_clamav; then
        DEPS_OK=0
    fi

    echo

    if [ "$DEPS_OK" = "0" ]; then
        log_error "Some dependencies are missing. Please install them and try again."
        exit 1
    fi

    log_success "All dependencies satisfied!"
    echo
    return 0
}

#
# Installation Functions
#

# Install ClamUI Python package into a dedicated virtual environment
install_python_package() {
    log_info "=== Installing ClamUI Python Package ==="
    echo

    # Verify we're in a directory with pyproject.toml
    if [ ! -f "$SCRIPT_DIR/pyproject.toml" ]; then
        log_error "pyproject.toml not found in $SCRIPT_DIR"
        log_error "Please run this script from the ClamUI source directory."
        return 1
    fi

    # Set up virtual environment location
    if [ "$SYSTEM_INSTALL" = "1" ]; then
        VENV_DIR="/usr/local/share/clamui/venv"
    else
        VENV_DIR="$SHARE_DIR/clamui/venv"
    fi

    log_info "Creating virtual environment at $VENV_DIR..."

    # Create the parent directory
    mkdir -p "$(dirname "$VENV_DIR")"

    # Create virtual environment using uv or python venv
    if [ "$PKG_MANAGER" = "uv" ]; then
        # Use uv to create venv (faster)
        if uv venv "$VENV_DIR" --python "$PYTHON_CMD" 2>/dev/null; then
            log_success "Virtual environment created with uv"
        else
            log_error "Failed to create virtual environment with uv"
            return 1
        fi
    else
        # Use python's built-in venv
        if $PYTHON_CMD -m venv "$VENV_DIR" 2>/dev/null; then
            log_success "Virtual environment created with python venv"
        else
            log_error "Failed to create virtual environment"
            log_info "You may need to install python3-venv: sudo apt install python3-venv"
            return 1
        fi
    fi

    # Install the package into the virtual environment
    log_info "Installing clamui package into virtual environment..."

    if [ "$PKG_MANAGER" = "uv" ]; then
        INSTALL_CMD="uv pip install --python \"$VENV_DIR/bin/python\" \"$SCRIPT_DIR\""
    else
        INSTALL_CMD="\"$VENV_DIR/bin/pip\" install \"$SCRIPT_DIR\""
    fi

    log_info "Running: $INSTALL_CMD"

    if eval "$INSTALL_CMD"; then
        log_success "ClamUI Python package installed successfully!"
    else
        log_error "Failed to install ClamUI Python package."
        log_info "You may need to install build dependencies first:"
        log_info "  Ubuntu/Debian: sudo apt install libgirepository-2.0-dev libcairo2-dev pkg-config python3-dev"
        log_info "  Fedora: sudo dnf install python3-gobject-devel gobject-introspection-devel cairo-gobject-devel"
        log_info "  Arch: sudo pacman -S python-gobject"
        return 1
    fi

    # Create wrapper script to run clamui from the venv
    log_info "Creating clamui wrapper script..."
    mkdir -p "$BIN_DIR"

    # Create wrapper script that activates the venv and runs clamui
    cat > "$BIN_DIR/clamui" << EOF
#!/bin/sh
# ClamUI launcher - runs clamui from its virtual environment
exec "$VENV_DIR/bin/clamui" "\$@"
EOF
    chmod +x "$BIN_DIR/clamui"
    log_success "Wrapper script created: $BIN_DIR/clamui"

    # Verify the installation
    echo
    if "$VENV_DIR/bin/python" -c "import src" 2>/dev/null; then
        log_success "Package import verification passed"
    else
        log_warning "Package installed but import verification skipped"
    fi

    # Check if bin directory is in PATH
    case ":$PATH:" in
        *":$BIN_DIR:"*)
            log_success "Binary directory is in PATH"
            ;;
        *)
            log_warning "$BIN_DIR is not in your PATH"
            log_info "Add it to your PATH by adding this to ~/.bashrc or ~/.profile:"
            log_info "  export PATH=\"$BIN_DIR:\$PATH\""
            ;;
    esac

    echo
    return 0
}

# Install XDG files (desktop entry, icon, nemo action)
install_xdg_files() {
    log_info "=== Installing XDG Files ==="
    echo

    # Create directories if they don't exist
    log_info "Creating XDG directories..."
    mkdir -p "$DESKTOP_DIR"
    mkdir -p "$ICON_DIR"
    mkdir -p "$NEMO_ACTION_DIR"

    # Install desktop entry
    log_info "Installing desktop entry to $DESKTOP_DIR..."
    if [ -f "$SCRIPT_DIR/com.github.rooki.clamui.desktop" ]; then
        cp "$SCRIPT_DIR/com.github.rooki.clamui.desktop" "$DESKTOP_DIR/"
        log_success "Desktop entry installed: $DESKTOP_DIR/com.github.rooki.clamui.desktop"
    else
        log_error "Desktop entry file not found: $SCRIPT_DIR/com.github.rooki.clamui.desktop"
        return 1
    fi

    # Install application icons (both SVG and PNG for tray icon support)
    log_info "Installing application icons to $ICON_DIR..."
    if [ -f "$SCRIPT_DIR/icons/com.github.rooki.clamui.svg" ]; then
        cp "$SCRIPT_DIR/icons/com.github.rooki.clamui.svg" "$ICON_DIR/"
        log_success "SVG icon installed: $ICON_DIR/com.github.rooki.clamui.svg"
    else
        log_warning "SVG icon file not found: $SCRIPT_DIR/icons/com.github.rooki.clamui.svg"
    fi
    if [ -f "$SCRIPT_DIR/icons/com.github.rooki.clamui.png" ]; then
        cp "$SCRIPT_DIR/icons/com.github.rooki.clamui.png" "$ICON_DIR/"
        log_success "PNG icon installed: $ICON_DIR/com.github.rooki.clamui.png"
    else
        log_warning "PNG icon file not found: $SCRIPT_DIR/icons/com.github.rooki.clamui.png"
        log_warning "Tray icon may use default theme icon"
    fi

    # Install Nemo file manager actions
    log_info "Installing Nemo actions to $NEMO_ACTION_DIR..."
    if [ -f "$SCRIPT_DIR/com.github.rooki.clamui.nemo_action" ]; then
        cp "$SCRIPT_DIR/com.github.rooki.clamui.nemo_action" "$NEMO_ACTION_DIR/"
        log_success "Nemo action installed: $NEMO_ACTION_DIR/com.github.rooki.clamui.nemo_action"
    else
        log_warning "Nemo action file not found: $SCRIPT_DIR/com.github.rooki.clamui.nemo_action"
        log_warning "Nemo context menu integration will not be available"
    fi
    # Install VirusTotal Nemo action
    if [ -f "$SCRIPT_DIR/com.github.rooki.clamui-virustotal.nemo_action" ]; then
        cp "$SCRIPT_DIR/com.github.rooki.clamui-virustotal.nemo_action" "$NEMO_ACTION_DIR/"
        log_success "VirusTotal Nemo action installed"
    fi

    # Install Nautilus scripts (if Nautilus is detected)
    if [ -d "$HOME/.local/share/nautilus" ] || command -v nautilus >/dev/null 2>&1; then
        log_info "Installing Nautilus scripts..."
        mkdir -p "$NAUTILUS_SCRIPTS_DIR"
        if [ -f "$SCRIPT_DIR/scripts/clamui-virustotal-nautilus.sh" ]; then
            cp "$SCRIPT_DIR/scripts/clamui-virustotal-nautilus.sh" "$NAUTILUS_SCRIPTS_DIR/Scan with VirusTotal"
            chmod +x "$NAUTILUS_SCRIPTS_DIR/Scan with VirusTotal"
            log_success "Nautilus VirusTotal script installed"
        fi
    fi

    # Install Dolphin service menus (if Dolphin/KDE is detected)
    if command -v dolphin >/dev/null 2>&1 || [ -d "$SHARE_DIR/kservices5" ]; then
        log_info "Installing Dolphin service menus..."
        mkdir -p "$DOLPHIN_SERVICES_DIR"
        if [ -f "$SCRIPT_DIR/com.github.rooki.clamui-virustotal.desktop" ]; then
            cp "$SCRIPT_DIR/com.github.rooki.clamui-virustotal.desktop" "$DOLPHIN_SERVICES_DIR/"
            log_success "Dolphin VirusTotal service menu installed"
        fi
    fi

    # Update desktop database if available
    if command -v update-desktop-database >/dev/null 2>&1; then
        log_info "Updating desktop database..."
        if update-desktop-database "$DESKTOP_DIR" 2>/dev/null; then
            log_success "Desktop database updated"
        else
            log_warning "Could not update desktop database (non-fatal)"
        fi
    fi

    # Update icon cache if available
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        log_info "Updating icon cache..."
        if gtk-update-icon-cache -f -t "$SHARE_DIR/icons/hicolor" 2>/dev/null; then
            log_success "Icon cache updated"
        else
            log_warning "Could not update icon cache (non-fatal)"
        fi
    fi

    # Refresh file manager caches
    log_info "Refreshing file manager caches..."

    # Nemo: Restart to pick up new actions
    if command -v nemo >/dev/null 2>&1; then
        if pgrep -x nemo >/dev/null 2>&1; then
            log_info "Restarting Nemo to load new actions..."
            nemo -q 2>/dev/null || true
            sleep 1
            # Nemo will restart automatically when needed
            log_success "Nemo cache refreshed"
        else
            log_info "Nemo not running, actions will be available on next start"
        fi
    fi

    # Dolphin: Rebuild service menu cache
    if command -v kbuildsycoca5 >/dev/null 2>&1; then
        log_info "Rebuilding KDE service cache..."
        kbuildsycoca5 --noincremental 2>/dev/null || true
        log_success "KDE service cache rebuilt"
    elif command -v kbuildsycoca6 >/dev/null 2>&1; then
        log_info "Rebuilding KDE6 service cache..."
        kbuildsycoca6 --noincremental 2>/dev/null || true
        log_success "KDE6 service cache rebuilt"
    fi

    # Nautilus scripts don't need cache refresh - they're read on demand

    echo
    log_success "XDG files installed successfully!"
    return 0
}

#
# Main Execution
#

main() {
    echo
    log_info "=== ClamUI Installer ==="
    echo

    # Check all dependencies
    check_all_dependencies

    # Install the Python package
    if ! install_python_package; then
        log_error "Installation failed."
        exit 1
    fi

    # Install XDG files (desktop entry, icon, nemo action)
    if ! install_xdg_files; then
        log_error "XDG file installation failed."
        exit 1
    fi

    log_success "=== ClamUI Installation Complete ==="
    echo
    log_info "You may need to log out and back in, or run:"
    log_info "  update-desktop-database $DESKTOP_DIR"
    log_info "  gtk-update-icon-cache -f -t $SHARE_DIR/icons/hicolor"
}

main "$@"
