#!/bin/bash
# ClamUI Debian Package Build Script
# Builds a .deb package for ClamUI using dpkg-deb
#
# Usage: ./debian/build-deb.sh [OPTIONS]
#
# Options:
#   --help      Show this help message
#
# Prerequisites: dpkg-deb, fakeroot
# Output: clamui_VERSION_all.deb in the project root

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
ClamUI Debian Package Build Script

Usage: ./debian/build-deb.sh [OPTIONS]

Options:
    --help      Show this help message

This script builds a Debian .deb package for ClamUI.

Prerequisites:
    - dpkg-deb (from dpkg-dev package)
    - fakeroot

The script will:
    1. Extract version from pyproject.toml
    2. Create the Debian package directory structure
    3. Copy Python source files (excluding __pycache__)
    4. Create launcher script
    5. Copy desktop entry, icon, and metainfo files
    6. Generate DEBIAN control files
    7. Build the .deb package

Output: clamui_VERSION_all.deb in the project root directory.

Install the generated package with:
    sudo dpkg -i clamui_*.deb
    sudo apt install -f  # if there are missing dependencies
EOF
}

# Parse command line arguments
for arg in "$@"; do
    case "$arg" in
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

#
# Directory and Path Setup
#

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Package configuration
PACKAGE_NAME="clamui"
ARCHITECTURE="all"

#
# Version Extraction Function
#

# Extract version from pyproject.toml
extract_version() {
    log_info "Extracting version from pyproject.toml..."

    PYPROJECT_FILE="$PROJECT_ROOT/pyproject.toml"

    # Check if pyproject.toml exists
    if [ ! -f "$PYPROJECT_FILE" ]; then
        log_error "pyproject.toml not found at $PYPROJECT_FILE"
        log_info "Please run this script from the project repository."
        return 1
    fi

    # Extract version using grep and sed
    # Matches: version = "X.Y.Z" or version = 'X.Y.Z'
    VERSION=$(grep -E '^version\s*=' "$PYPROJECT_FILE" | head -n1 | sed -E 's/^version\s*=\s*["\x27]([^"\x27]+)["\x27].*/\1/')

    # Validate version was extracted
    if [ -z "$VERSION" ]; then
        log_error "Could not extract version from pyproject.toml"
        log_info "Ensure pyproject.toml contains: version = \"X.Y.Z\""
        return 1
    fi

    # Validate version format (should be X.Y.Z or similar)
    if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+'; then
        log_warning "Version '$VERSION' may not follow semantic versioning (X.Y.Z)"
    fi

    log_success "Version: $VERSION"

    # Export for use in package naming
    DEB_FILENAME="${PACKAGE_NAME}_${VERSION}_${ARCHITECTURE}.deb"
    log_info "Package will be: $DEB_FILENAME"

    return 0
}

#
# Prerequisites Checking Functions
#

# Check for dpkg-deb availability
check_dpkg_deb() {
    log_info "Checking for dpkg-deb..."

    if command -v dpkg-deb >/dev/null 2>&1; then
        DPKG_VERSION=$(dpkg-deb --version 2>/dev/null | head -n1)
        log_success "dpkg-deb found: $DPKG_VERSION"
        return 0
    fi

    log_error "dpkg-deb not found."
    log_info "Install on Ubuntu/Debian: sudo apt install dpkg-dev"
    return 1
}

# Check for fakeroot availability
check_fakeroot() {
    log_info "Checking for fakeroot..."

    if command -v fakeroot >/dev/null 2>&1; then
        FAKEROOT_VERSION=$(fakeroot --version 2>/dev/null | head -n1)
        log_success "fakeroot found: $FAKEROOT_VERSION"
        return 0
    fi

    log_error "fakeroot not found."
    log_info "Install on Ubuntu/Debian: sudo apt install fakeroot"
    return 1
}

# Check all prerequisites
check_prerequisites() {
    log_info "=== Checking Prerequisites ==="
    echo

    PREREQS_OK=1

    if ! check_dpkg_deb; then
        PREREQS_OK=0
    fi

    if ! check_fakeroot; then
        PREREQS_OK=0
    fi

    echo

    if [ "$PREREQS_OK" = "0" ]; then
        log_error "Missing prerequisites. Please install them and try again."
        log_info "Quick install: sudo apt install dpkg-dev fakeroot"
        exit 1
    fi

    log_success "All prerequisites satisfied!"
    echo
    return 0
}

#
# Directory Structure Creation Functions
#

# Build directory (temporary, used during package creation)
BUILD_DIR=""

# Create the FHS-compliant directory structure for the package
create_package_structure() {
    log_info "=== Creating Package Directory Structure ==="
    echo

    # Set build directory path
    BUILD_DIR="$PROJECT_ROOT/build-deb-temp"

    # Clean up any existing build directory
    if [ -d "$BUILD_DIR" ]; then
        log_warning "Removing existing build directory..."
        rm -rf "$BUILD_DIR"
    fi

    log_info "Creating build directory: $BUILD_DIR"
    mkdir -p "$BUILD_DIR"

    # Create DEBIAN directory for control files
    log_info "Creating DEBIAN/ directory..."
    mkdir -p "$BUILD_DIR/DEBIAN"

    # Create /usr/bin/ for executable launcher script
    log_info "Creating usr/bin/ for launcher script..."
    mkdir -p "$BUILD_DIR/usr/bin"

    # Create /usr/lib/python3/dist-packages/clamui/ for Python modules
    log_info "Creating usr/lib/python3/dist-packages/clamui/ for Python modules..."
    mkdir -p "$BUILD_DIR/usr/lib/python3/dist-packages/clamui"

    # Create /usr/share/applications/ for desktop file
    log_info "Creating usr/share/applications/ for desktop entry..."
    mkdir -p "$BUILD_DIR/usr/share/applications"

    # Create /usr/share/icons/hicolor/scalable/apps/ for icon
    log_info "Creating usr/share/icons/hicolor/scalable/apps/ for icon..."
    mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"

    # Create /usr/share/metainfo/ for AppStream metadata
    log_info "Creating usr/share/metainfo/ for AppStream data..."
    mkdir -p "$BUILD_DIR/usr/share/metainfo"

    echo
    log_success "Package directory structure created successfully!"
    log_info "Build directory: $BUILD_DIR"

    # Display the created structure
    log_info "Created directories:"
    log_info "  - DEBIAN/"
    log_info "  - usr/bin/"
    log_info "  - usr/lib/python3/dist-packages/clamui/"
    log_info "  - usr/share/applications/"
    log_info "  - usr/share/icons/hicolor/scalable/apps/"
    log_info "  - usr/share/metainfo/"

    return 0
}

# Cleanup build directory
cleanup_build_dir() {
    if [ -n "$BUILD_DIR" ] && [ -d "$BUILD_DIR" ]; then
        log_info "Cleaning up build directory..."
        rm -rf "$BUILD_DIR"
        log_success "Build directory cleaned up."
    fi
}

#
# File Copying Functions
#

# Copy Python source files (excluding __pycache__)
copy_python_source() {
    log_info "=== Copying Python Source Files ==="
    echo

    SRC_DIR="$PROJECT_ROOT/src"
    DEST_DIR="$BUILD_DIR/usr/lib/python3/dist-packages/clamui"

    # Check if source directory exists
    if [ ! -d "$SRC_DIR" ]; then
        log_error "Source directory not found: $SRC_DIR"
        return 1
    fi

    log_info "Copying Python source from src/ to clamui module..."

    # Copy all Python files and subdirectories, excluding __pycache__
    # Use rsync if available for cleaner exclusion, otherwise use find
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --exclude='__pycache__' --exclude='*.pyc' "$SRC_DIR/" "$DEST_DIR/"
    else
        # Fallback: use cp then clean up __pycache__
        cp -r "$SRC_DIR/"* "$DEST_DIR/"
        # Remove __pycache__ directories
        find "$DEST_DIR" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
        # Remove .pyc files
        find "$DEST_DIR" -type f -name '*.pyc' -delete 2>/dev/null || true
    fi

    # Verify copy was successful
    if [ ! -f "$DEST_DIR/main.py" ]; then
        log_error "Failed to copy Python source files"
        return 1
    fi

    # Set proper permissions (644 for .py files)
    find "$DEST_DIR" -type f -name '*.py' -exec chmod 644 {} +

    log_success "Python source files copied successfully"
    log_info "Installed to: /usr/lib/python3/dist-packages/clamui/"

    return 0
}

# Create the launcher script in /usr/bin/
create_launcher_script() {
    log_info "=== Creating Launcher Script ==="
    echo

    LAUNCHER_PATH="$BUILD_DIR/usr/bin/$PACKAGE_NAME"

    log_info "Creating launcher script: $LAUNCHER_PATH"

    # Create the launcher script
    # Note: Using 'clamui.main' since we install source as /usr/lib/python3/dist-packages/clamui/
    cat > "$LAUNCHER_PATH" << 'LAUNCHER'
#!/usr/bin/env python3
"""ClamUI launcher script for Debian package installation."""
import sys

from clamui.main import main
sys.exit(main())
LAUNCHER

    # Make executable (755)
    chmod 755 "$LAUNCHER_PATH"

    # Verify launcher was created
    if [ ! -x "$LAUNCHER_PATH" ]; then
        log_error "Failed to create launcher script"
        return 1
    fi

    log_success "Launcher script created successfully"
    log_info "Installed to: /usr/bin/$PACKAGE_NAME"

    return 0
}

# Copy desktop entry, icon, and metainfo files
copy_desktop_files() {
    log_info "=== Copying Desktop Integration Files ==="
    echo

    # Copy desktop entry
    DESKTOP_FILE="$PROJECT_ROOT/com.github.rooki.ClamUI.desktop"
    if [ -f "$DESKTOP_FILE" ]; then
        log_info "Copying desktop entry..."
        cp "$DESKTOP_FILE" "$BUILD_DIR/usr/share/applications/"
        chmod 644 "$BUILD_DIR/usr/share/applications/com.github.rooki.ClamUI.desktop"
        log_success "Desktop entry installed"
    else
        log_warning "Desktop file not found: $DESKTOP_FILE"
        log_warning "Application may not appear in desktop menus"
    fi

    # Copy icon (gracefully handle if not present)
    ICON_FILE="$PROJECT_ROOT/icons/com.github.rooki.ClamUI.svg"
    if [ -f "$ICON_FILE" ]; then
        log_info "Copying application icon..."
        cp "$ICON_FILE" "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/"
        chmod 644 "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/com.github.rooki.ClamUI.svg"
        log_success "Icon installed"
    else
        log_warning "Icon file not found: $ICON_FILE"
        log_warning "Application will use a fallback icon"
    fi

    # Copy AppStream metainfo
    METAINFO_FILE="$PROJECT_ROOT/com.github.rooki.ClamUI.metainfo.xml"
    if [ -f "$METAINFO_FILE" ]; then
        log_info "Copying AppStream metainfo..."
        cp "$METAINFO_FILE" "$BUILD_DIR/usr/share/metainfo/"
        chmod 644 "$BUILD_DIR/usr/share/metainfo/com.github.rooki.ClamUI.metainfo.xml"
        log_success "AppStream metainfo installed"
    else
        log_warning "Metainfo file not found: $METAINFO_FILE"
        log_warning "Package may not appear in software centers"
    fi

    echo
    log_success "Desktop integration files copied successfully"

    return 0
}

# Copy and process DEBIAN control files
copy_control_files() {
    log_info "=== Copying DEBIAN Control Files ==="
    echo

    DEBIAN_SRC_DIR="$SCRIPT_DIR/DEBIAN"
    DEBIAN_DEST_DIR="$BUILD_DIR/DEBIAN"

    # Check if source DEBIAN directory exists
    if [ ! -d "$DEBIAN_SRC_DIR" ]; then
        log_error "DEBIAN template directory not found: $DEBIAN_SRC_DIR"
        return 1
    fi

    # Copy control file with version substitution
    if [ -f "$DEBIAN_SRC_DIR/control" ]; then
        log_info "Processing control file (substituting version)..."
        sed "s/^Version: VERSION$/Version: $VERSION/" "$DEBIAN_SRC_DIR/control" > "$DEBIAN_DEST_DIR/control"
        chmod 644 "$DEBIAN_DEST_DIR/control"
        log_success "Control file installed (version: $VERSION)"
    else
        log_error "Control file template not found: $DEBIAN_SRC_DIR/control"
        return 1
    fi

    # Copy maintainer scripts with executable permissions (755)
    for script in postinst prerm postrm; do
        if [ -f "$DEBIAN_SRC_DIR/$script" ]; then
            log_info "Copying $script script..."
            cp "$DEBIAN_SRC_DIR/$script" "$DEBIAN_DEST_DIR/"
            chmod 755 "$DEBIAN_DEST_DIR/$script"
        else
            log_warning "Maintainer script not found: $script (optional)"
        fi
    done

    echo
    log_success "DEBIAN control files copied successfully"

    return 0
}

#
# Package Building Functions
#

# Build the .deb package using fakeroot and dpkg-deb
build_package() {
    log_info "=== Building Debian Package ==="
    echo

    DEB_OUTPUT="$PROJECT_ROOT/$DEB_FILENAME"

    # Remove any existing package with the same name
    if [ -f "$DEB_OUTPUT" ]; then
        log_warning "Removing existing package: $DEB_FILENAME"
        rm -f "$DEB_OUTPUT"
    fi

    log_info "Building package: $DEB_FILENAME"
    log_info "Build directory: $BUILD_DIR"
    log_info "Output: $DEB_OUTPUT"
    echo

    # Build the package using fakeroot and dpkg-deb
    # fakeroot simulates root privileges for file ownership
    # dpkg-deb --build creates the .deb package
    log_info "Running: fakeroot dpkg-deb --build $BUILD_DIR $DEB_OUTPUT"
    echo

    if ! fakeroot dpkg-deb --build "$BUILD_DIR" "$DEB_OUTPUT"; then
        log_error "Failed to build package with dpkg-deb"
        return 1
    fi

    echo
    log_success "Package built successfully!"

    # Verify the package was created
    if [ ! -f "$DEB_OUTPUT" ]; then
        log_error "Package file not found after build: $DEB_OUTPUT"
        return 1
    fi

    # Display package info
    DEB_SIZE=$(du -h "$DEB_OUTPUT" | cut -f1)
    log_success "Package: $DEB_FILENAME ($DEB_SIZE)"

    return 0
}

# Display final summary and instructions
print_summary() {
    echo
    log_info "========================================"
    log_success "   Build Complete!"
    log_info "========================================"
    echo
    log_info "Package created: $DEB_FILENAME"
    log_info "Location: $PROJECT_ROOT/$DEB_FILENAME"
    echo
    log_info "To install the package:"
    log_info "  sudo dpkg -i $DEB_FILENAME"
    log_info "  sudo apt install -f  # if there are missing dependencies"
    echo
    log_info "To verify the package:"
    log_info "  dpkg -I $DEB_FILENAME  # show package info"
    log_info "  dpkg -c $DEB_FILENAME  # list package contents"
    echo
}

#
# Main Execution
#

main() {
    echo
    log_info "=== ClamUI Debian Package Builder ==="
    echo

    # Check all prerequisites first
    check_prerequisites

    # Extract version from pyproject.toml
    log_info "=== Extracting Package Version ==="
    echo

    if ! extract_version; then
        log_error "Version extraction failed."
        exit 1
    fi

    echo

    # Create the package directory structure
    if ! create_package_structure; then
        log_error "Failed to create package directory structure."
        cleanup_build_dir
        exit 1
    fi

    echo

    # Copy Python source files
    if ! copy_python_source; then
        log_error "Failed to copy Python source files."
        cleanup_build_dir
        exit 1
    fi

    echo

    # Create the launcher script
    if ! create_launcher_script; then
        log_error "Failed to create launcher script."
        cleanup_build_dir
        exit 1
    fi

    echo

    # Copy desktop integration files
    if ! copy_desktop_files; then
        log_error "Failed to copy desktop integration files."
        cleanup_build_dir
        exit 1
    fi

    echo

    # Copy DEBIAN control files
    if ! copy_control_files; then
        log_error "Failed to copy DEBIAN control files."
        cleanup_build_dir
        exit 1
    fi

    echo

    # Build the .deb package
    if ! build_package; then
        log_error "Failed to build .deb package."
        cleanup_build_dir
        exit 1
    fi

    # Clean up the build directory (success case)
    echo
    cleanup_build_dir

    # Print final summary
    print_summary

    log_success "Done!"
}

main "$@"
