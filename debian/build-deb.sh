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
    log_success "Package structure ready. Ready to copy files."
    log_info "(File copying and package building will be added in subsequent subtasks)"
}

main "$@"
