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
    - ClamUI Python package (pip)
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

#
# Uninstallation Functions
#

# Uninstall ClamUI Python package using pip or uv
uninstall_python_package() {
    log_info "=== Uninstalling ClamUI Python Package ==="
    echo

    # Determine which package manager to use
    PKG_UNINSTALL_CMD=""

    # Prefer uv if available
    if command -v uv >/dev/null 2>&1; then
        PKG_MANAGER="uv"
        if [ "$SYSTEM_INSTALL" = "1" ]; then
            PKG_UNINSTALL_CMD="uv pip uninstall --system"
        else
            PKG_UNINSTALL_CMD="uv pip uninstall"
        fi
        log_info "Using uv package manager"
    elif command -v pip3 >/dev/null 2>&1; then
        PKG_MANAGER="pip3"
        PKG_UNINSTALL_CMD="pip3 uninstall"
        log_info "Using pip3"
    elif command -v pip >/dev/null 2>&1; then
        PKG_MANAGER="pip"
        PKG_UNINSTALL_CMD="pip uninstall"
        log_info "Using pip"
    else
        log_warning "No Python package manager found. Skipping pip package removal."
        log_warning "You may need to manually remove the clamui package."
        return 0
    fi

    # Check if clamui is installed
    if $PKG_MANAGER show clamui >/dev/null 2>&1 || pip3 show clamui >/dev/null 2>&1 2>/dev/null; then
        log_info "Removing clamui package..."

        # Execute the uninstallation
        if $PKG_UNINSTALL_CMD -y clamui 2>/dev/null; then
            log_success "ClamUI Python package uninstalled successfully!"
        else
            log_warning "Could not uninstall pip package (may not be installed via pip)"
        fi
    else
        log_info "ClamUI pip package not found (may have been installed differently)"
    fi

    echo
    return 0
}

# Remove XDG files (desktop entry, icon, nemo action)
remove_xdg_files() {
    log_info "=== Removing XDG Files ==="
    echo

    FILES_REMOVED=0

    # Remove desktop entry
    DESKTOP_FILE="$DESKTOP_DIR/com.github.clamui.desktop"
    if [ -f "$DESKTOP_FILE" ]; then
        log_info "Removing desktop entry..."
        rm -f "$DESKTOP_FILE"
        log_success "Removed: $DESKTOP_FILE"
        FILES_REMOVED=$((FILES_REMOVED + 1))
    else
        log_info "Desktop entry not found: $DESKTOP_FILE"
    fi

    # Remove application icon
    ICON_FILE="$ICON_DIR/com.github.clamui.svg"
    if [ -f "$ICON_FILE" ]; then
        log_info "Removing application icon..."
        rm -f "$ICON_FILE"
        log_success "Removed: $ICON_FILE"
        FILES_REMOVED=$((FILES_REMOVED + 1))
    else
        log_info "Icon not found: $ICON_FILE"
    fi

    # Remove Nemo file manager action
    NEMO_FILE="$NEMO_ACTION_DIR/com.github.clamui.nemo_action"
    if [ -f "$NEMO_FILE" ]; then
        log_info "Removing Nemo action..."
        rm -f "$NEMO_FILE"
        log_success "Removed: $NEMO_FILE"
        FILES_REMOVED=$((FILES_REMOVED + 1))
    else
        log_info "Nemo action not found: $NEMO_FILE"
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
