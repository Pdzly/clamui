#!/bin/sh
# ClamUI Uninstallation Script
# Removes ClamUI and all installed files from the system
#
# Usage: ./uninstall.sh [OPTIONS]
#
# Options:
#   --system    Uninstall system-wide installation (requires root privileges)
#   --help      Show this help message

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
ClamUI Uninstallation Script

Usage: ./uninstall.sh [OPTIONS]

Options:
    --system    Uninstall system-wide installation (requires root)
    --help      Show this help message

By default, uninstalls from user-local directories (~/.local/share/).
No root privileges required for user-local uninstallation.

This script will remove:
    - Desktop entry (application menu)
    - Application icon
    - Nemo file manager action (context menu)
    - ClamUI virtual environment and wrapper script
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
        log_error "System-wide uninstallation requires root privileges."
        log_info "Please run with: sudo ./uninstall.sh --system"
        exit 1
    fi
    SHARE_DIR="/usr/share"
    BIN_DIR="/usr/local/bin"
    log_info "Uninstalling system-wide from $SHARE_DIR"
else
    XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
    SHARE_DIR="$XDG_DATA_HOME"
    BIN_DIR="$HOME/.local/bin"
    log_info "Uninstalling from user directory: $SHARE_DIR"
fi

# XDG directory paths
DESKTOP_DIR="$SHARE_DIR/applications"
ICON_DIR="$SHARE_DIR/icons/hicolor/scalable/apps"
NEMO_ACTION_DIR="$SHARE_DIR/nemo/actions"
NAUTILUS_SCRIPTS_DIR="$HOME/.local/share/nautilus/scripts"
DOLPHIN_SERVICES_DIR="$SHARE_DIR/kservices5/ServiceMenus"

#
# Uninstallation Functions
#

# Uninstall ClamUI Python package and virtual environment
uninstall_python_package() {
    log_info "=== Uninstalling ClamUI Python Package ==="
    echo

    # Set up virtual environment location (same as install.sh)
    if [ "$SYSTEM_INSTALL" = "1" ]; then
        VENV_DIR="/usr/local/share/clamui/venv"
        CLAMUI_DIR="/usr/local/share/clamui"
    else
        VENV_DIR="$SHARE_DIR/clamui/venv"
        CLAMUI_DIR="$SHARE_DIR/clamui"
    fi

    # Remove the wrapper script
    WRAPPER_SCRIPT="$BIN_DIR/clamui"
    if [ -f "$WRAPPER_SCRIPT" ]; then
        log_info "Removing wrapper script..."
        rm -f "$WRAPPER_SCRIPT"
        log_success "Removed: $WRAPPER_SCRIPT"
    else
        log_info "Wrapper script not found: $WRAPPER_SCRIPT"
    fi

    # Remove the virtual environment
    if [ -d "$VENV_DIR" ]; then
        log_info "Removing virtual environment..."
        rm -rf "$VENV_DIR"
        log_success "Removed: $VENV_DIR"
    else
        log_info "Virtual environment not found: $VENV_DIR"
    fi

    # Remove the clamui directory if empty
    if [ -d "$CLAMUI_DIR" ]; then
        # Check if directory is empty
        if [ -z "$(ls -A "$CLAMUI_DIR" 2>/dev/null)" ]; then
            log_info "Removing empty clamui directory..."
            rmdir "$CLAMUI_DIR" 2>/dev/null || true
            log_success "Removed: $CLAMUI_DIR"
        else
            log_info "Clamui directory not empty, keeping: $CLAMUI_DIR"
        fi
    fi

    echo
    log_success "ClamUI Python package uninstalled!"
    return 0
}

# Remove XDG files (desktop entry, icon, nemo action)
remove_xdg_files() {
    log_info "=== Removing XDG Files ==="
    echo

    FILES_REMOVED=0

    # Remove desktop entry
    DESKTOP_FILE="$DESKTOP_DIR/io.github.Pdzly.ClamUI.desktop"
    if [ -f "$DESKTOP_FILE" ]; then
        log_info "Removing desktop entry..."
        rm -f "$DESKTOP_FILE"
        log_success "Removed: $DESKTOP_FILE"
        FILES_REMOVED=$((FILES_REMOVED + 1))
    else
        log_info "Desktop entry not found: $DESKTOP_FILE"
    fi

    # Remove application icons (SVG and PNG)
    SVG_ICON_FILE="$ICON_DIR/io.github.Pdzly.ClamUI.svg"
    if [ -f "$SVG_ICON_FILE" ]; then
        log_info "Removing SVG icon..."
        rm -f "$SVG_ICON_FILE"
        log_success "Removed: $SVG_ICON_FILE"
        FILES_REMOVED=$((FILES_REMOVED + 1))
    else
        log_info "SVG icon not found: $SVG_ICON_FILE"
    fi

    PNG_ICON_FILE="$ICON_DIR/io.github.Pdzly.ClamUI.png"
    if [ -f "$PNG_ICON_FILE" ]; then
        log_info "Removing PNG icon..."
        rm -f "$PNG_ICON_FILE"
        log_success "Removed: $PNG_ICON_FILE"
        FILES_REMOVED=$((FILES_REMOVED + 1))
    else
        log_info "PNG icon not found: $PNG_ICON_FILE"
    fi

    # Remove Nemo file manager actions
    NEMO_FILE="$NEMO_ACTION_DIR/io.github.Pdzly.ClamUI.nemo_action"
    if [ -f "$NEMO_FILE" ]; then
        log_info "Removing Nemo action..."
        rm -f "$NEMO_FILE"
        log_success "Removed: $NEMO_FILE"
        FILES_REMOVED=$((FILES_REMOVED + 1))
    else
        log_info "Nemo action not found: $NEMO_FILE"
    fi

    # Remove VirusTotal Nemo action
    NEMO_VT_FILE="$NEMO_ACTION_DIR/io.github.Pdzly.ClamUI-virustotal.nemo_action"
    if [ -f "$NEMO_VT_FILE" ]; then
        log_info "Removing VirusTotal Nemo action..."
        rm -f "$NEMO_VT_FILE"
        log_success "Removed: $NEMO_VT_FILE"
        FILES_REMOVED=$((FILES_REMOVED + 1))
    else
        log_info "VirusTotal Nemo action not found: $NEMO_VT_FILE"
    fi

    # Remove Nautilus scripts
    NAUTILUS_VT_SCRIPT="$NAUTILUS_SCRIPTS_DIR/Scan with VirusTotal"
    if [ -f "$NAUTILUS_VT_SCRIPT" ]; then
        log_info "Removing Nautilus VirusTotal script..."
        rm -f "$NAUTILUS_VT_SCRIPT"
        log_success "Removed: $NAUTILUS_VT_SCRIPT"
        FILES_REMOVED=$((FILES_REMOVED + 1))
    else
        log_info "Nautilus script not found: $NAUTILUS_VT_SCRIPT"
    fi

    # Remove Dolphin service menus
    DOLPHIN_VT_FILE="$DOLPHIN_SERVICES_DIR/io.github.Pdzly.ClamUI-virustotal.desktop"
    if [ -f "$DOLPHIN_VT_FILE" ]; then
        log_info "Removing Dolphin VirusTotal service menu..."
        rm -f "$DOLPHIN_VT_FILE"
        log_success "Removed: $DOLPHIN_VT_FILE"
        FILES_REMOVED=$((FILES_REMOVED + 1))
    else
        log_info "Dolphin service menu not found: $DOLPHIN_VT_FILE"
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

    # Rebuild KDE service cache if available
    if command -v kbuildsycoca5 >/dev/null 2>&1; then
        log_info "Rebuilding KDE service cache..."
        kbuildsycoca5 --noincremental 2>/dev/null || true
        log_success "KDE service cache rebuilt"
    elif command -v kbuildsycoca6 >/dev/null 2>&1; then
        log_info "Rebuilding KDE6 service cache..."
        kbuildsycoca6 --noincremental 2>/dev/null || true
        log_success "KDE6 service cache rebuilt"
    fi

    echo
    if [ "$FILES_REMOVED" -gt 0 ]; then
        log_success "XDG files removed successfully! ($FILES_REMOVED files)"
    else
        log_info "No XDG files found to remove"
    fi
    return 0
}

#
# Main Execution
#

main() {
    echo
    log_info "=== ClamUI Uninstaller ==="
    echo

    # Remove XDG files (desktop entry, icon, nemo action)
    remove_xdg_files

    # Uninstall the Python package
    uninstall_python_package

    log_success "=== ClamUI Uninstallation Complete ==="
    echo
    log_info "ClamUI has been removed from your system."
    log_info "You may need to log out and back in for changes to take effect."
}

main "$@"
