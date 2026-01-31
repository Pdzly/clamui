#!/bin/bash
# local-run.sh - Install dependencies and run ClamUI from source
#
# Usage:
#   ./local-run.sh          # Install deps + run
#   ./local-run.sh --deps   # Only install dependencies
#   ./local-run.sh --run    # Only run (skip dep check)

set -e

DEPS_ONLY=false
SKIP_DEPS=false

for arg in "$@"; do
    case $arg in
        --deps)
            DEPS_ONLY=true
            ;;
        --run)
            SKIP_DEPS=true
            ;;
    esac
done

install_deps_debian() {
    echo "Installing dependencies for Debian/Ubuntu..."

    # GTK4, Adwaita, and Python bindings
    sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1

    # Build dependencies for pycairo/PyGObject
    # Ubuntu 24.04+ uses libgirepository-2.0-dev
    # Ubuntu 22.04 uses libgirepository1.0-dev
    if apt-cache show libgirepository-2.0-dev &>/dev/null; then
        sudo apt install -y python3-dev libcairo2-dev libgirepository-2.0-dev pkg-config
    else
        sudo apt install -y python3-dev libcairo2-dev libgirepository1.0-dev pkg-config
    fi

    # Build dependencies for Pillow (tray icon support)
    sudo apt install -y libjpeg-dev zlib1g-dev

    # ClamAV (optional for development, required for scanning)
    if ! command -v clamscan &>/dev/null; then
        read -p "Install ClamAV? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt install -y clamav
        fi
    fi
}

install_deps_fedora() {
    echo "Installing dependencies for Fedora..."
    sudo dnf install -y gtk4-devel libadwaita-devel python3-gobject python3-devel \
        cairo-devel gobject-introspection-devel pkg-config clamav
}

install_deps_arch() {
    echo "Installing dependencies for Arch Linux..."
    sudo pacman -S --needed python-gobject gtk4 libadwaita cairo pkgconf clamav
}

install_dependencies() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case $ID in
            ubuntu|debian|linuxmint|pop)
                install_deps_debian
                ;;
            fedora)
                install_deps_fedora
                ;;
            arch|manjaro)
                install_deps_arch
                ;;
            *)
                echo "Unsupported distribution: $ID"
                echo "Please install dependencies manually. See docs/INSTALL.md"
                exit 1
                ;;
        esac
    else
        echo "Cannot detect distribution. Please install dependencies manually."
        exit 1
    fi
}

# Check for uv
if ! command -v uv &>/dev/null; then
    echo "Error: 'uv' is not installed."
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
if [ "$SKIP_DEPS" = false ]; then
    install_dependencies
    echo "Dependencies installed successfully."
fi

if [ "$DEPS_ONLY" = true ]; then
    exit 0
fi

# Sync Python dependencies and run
echo "Syncing Python dependencies..."
uv sync

echo "Starting ClamUI..."
uv run clamui "$@"
