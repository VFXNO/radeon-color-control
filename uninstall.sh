#!/usr/bin/env bash
#
# Radeon Color Control Uninstaller
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${RED}==> Uninstalling Radeon Color Control...${NC}"

# Reset display before uninstalling if kscreen-doctor is available
if command -v kscreen-doctor >/dev/null 2>&1; then
    echo "Resetting active display color calibration..."
    kscreen-doctor output.DP-2.colorProfileSource.sRGB output.DP-2.wcg.disable output.DP-2.sdrGamut.0 output.DP-2.iccprofile. >/dev/null 2>&1 || true
fi

# Kill any running instances
pkill -f "radeon-color-control" 2>/dev/null || true

# Remove installed files
rm -rf "$HOME/.local/share/radeon-color-control"
rm -f "$HOME/.local/bin/radeon-color-control"
rm -f "$HOME/.local/share/applications/radeon-color-control.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/radeon-color-control.svg"
rm -f "$HOME/.config/autostart/radeon-color-control.desktop"

# Optional: ask to remove config
read -p "Do you want to delete user configuration (~/.config/radeon-color-control)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.config/radeon-color-control"
    echo "Removed user configuration."
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

echo -e "${GREEN}==> Radeon Color Control has been uninstalled.${NC}"
