#!/usr/bin/env bash
#
# Radeon Color Control Installer
# Installs application files to ~/.local/
#

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}==> Installing Radeon Color Control...${NC}"

# Directory setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/radeon-color-control"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

# 1. Dependency checks
echo "Checking system prerequisites..."
MISSING_DEPS=()

command -v python3 >/dev/null 2>&1 || MISSING_DEPS+=("python3")
command -v kscreen-doctor >/dev/null 2>&1 || MISSING_DEPS+=("kscreen-doctor (libkscreen)")

python3 -c "import PyQt6" >/dev/null 2>&1 || MISSING_DEPS+=("python3-pyqt6")
python3 -c "import ctypes; ctypes.CDLL('liblcms2.so.2')" >/dev/null 2>&1 || MISSING_DEPS+=("liblcms2-2")

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo -e "${RED}Error: The following required dependencies are missing:${NC}"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo "Install them using your package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pyqt6 liblcms2-2 libkscreen-bin"
    echo "  Arch Linux:    sudo pacman -S python python-pyqt6 lcms2 libkscreen"
    echo "  Fedora:        sudo dnf install python3 python3-pyqt6 lcms2 libkscreen"
    exit 1
fi

# Optional ddcutil check
if ! command -v ddcutil >/dev/null 2>&1; then
    echo -e "${YELLOW}Notice: 'ddcutil' not found. Digital vibrance will work, but hardware monitor sync will be disabled.${NC}"
    echo "  (Install with: sudo apt install ddcutil)"
fi

# 2. Create directories
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$APP_DIR" "$ICON_DIR"

# 3. Copy source files
echo "Installing application files to $INSTALL_DIR..."
cp -r "$SCRIPT_DIR"/src/* "$INSTALL_DIR/"
cp "$SCRIPT_DIR/assets/icon.svg" "$INSTALL_DIR/icon.svg"

# 4. Install icon to system icon theme
echo "Installing application icon..."
cp "$SCRIPT_DIR/assets/icon.svg" "$ICON_DIR/radeon-color-control.svg"

# 5. Install launcher script
echo "Installing launcher to $BIN_DIR/radeon-color-control..."
cat << 'EOF' > "$BIN_DIR/radeon-color-control"
#!/usr/bin/env bash
exec /usr/bin/python3 "$HOME/.local/share/radeon-color-control/main.py" "$@"
EOF
chmod +x "$BIN_DIR/radeon-color-control"
chmod +x "$INSTALL_DIR/main.py"

# 6. Install desktop file
echo "Installing desktop entry..."
cp "$SCRIPT_DIR/assets/radeon-color-control.desktop" "$APP_DIR/radeon-color-control.desktop"

# 7. Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

echo ""
echo -e "${GREEN}==> Installation Complete!${NC}"
echo "You can now launch the app:"
echo "  - From Application Menu: Search for 'Radeon Color Control'"
echo "  - From Terminal:         radeon-color-control"
echo ""

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "${YELLOW}Warning: $HOME/.local/bin is not in your PATH.${NC}"
    echo "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi
