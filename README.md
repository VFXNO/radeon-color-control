# Radeon Color Control 🎨

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Wayland-orange.svg)](#requirements)
[![Desktop](https://img.shields.io/badge/Desktop-KDE%20Plasma%206-blue.svg)](#requirements)
[![GUI](https://img.shields.io/badge/GUI-PyQt6-green.svg)](#requirements)

**AMD Radeon Software "Custom Color"** and **Digital Vibrance** control for Linux. 

Designed specifically for **KDE Plasma 6 on Wayland** with **AMD Radeon GPUs**, allowing you to push digital saturation up to **250%** across the whole screen—completely bypassing monitor hardware limits.

---

## 💡 The Problem & The Solution

* **The Problem:** On Windows, AMD Adrenalin allows players (especially CS2, Apex, Valorant, and FPS players) to digitally boost **Custom Color / Saturation** to 150%–200%. On Linux Wayland, traditional X11 tools (`vibrantLinux`, `xrandr`) do not work, and monitor hardware controls (DDC/CI) are physically capped at 100%.
* **The Solution:** **Radeon Color Control** synthesizes matrix-shaper color profiles with **VCGT (Video Card Gamma Table)** tags using `liblcms2` and controls KWin's DRM compositor directly via `kscreen-doctor`. It drives the GPU's hardware display engine and expands the desktop color space across all windows, browsers, video players, and games.

---

## ✨ Features

- **🎮 Digital Vibrance (Saturation) (0% – 250%):** Digitally multiplies saturation directly on the GPU pipeline (140%+ for competitive gaming).
- **🌈 Wide Color Gamut (WCG / DCI-P3):** Unlocks your monitor's native DCI-P3 wide color space without sRGB clamping.
- **🌡️ Color Temperature (4000K – 10000K):** Dial in your display white point from warm candle-light to crisp daylight (6500K neutral).
- **⚡ Contrast & Brightness:** Deepens shadows and intensifies highlights across the whole screen.
- **🎨 RGB Channel Tuning:** Independent Red, Green, and Blue gain sliders.
- **🖥️ Hardware DDC/CI Sync (Optional):** Simultaneously commands your monitor's internal scalar via `ddcutil` alongside digital GPU vibrance.
- **💾 Presets & Custom Profiles:** 
  - *Default (sRGB)*
  - *Esports Vibrance (CS2/FPS)* (145% Saturation, 110% Contrast, 6800K, WCG On)
  - *Ultra Saturated (200%+)* (180% Saturation, 115% Contrast, WCG On)
  - *Vivid Cinema* (120% Saturation, 105% Contrast)
  - *Warm Night* (95% Saturation, 4800K, soft contrast)
  - Save and name your own custom presets!
- **🛎️ System Tray & Autostart:** Close to system tray, right-click preset switcher, and one-click "Start minimized at login".
- **⌨️ CLI & Hotkey Support:** Apply any preset or setting directly from the command line or bind it to a KDE keyboard shortcut.

---

## 📦 Requirements

* **Desktop Environment:** KDE Plasma 6 (Wayland)
* **GPU:** AMD Radeon (Navi / RDNA / GCN) using the open-source `amdgpu` driver
* **Dependencies:**
  * Python 3
  * PyQt6
  * LittleCMS 2 (`liblcms2-2`)
  * `kscreen-doctor` (included with `libkscreen` / KDE Plasma)
  * *(Optional)* `ddcutil` (for monitor hardware saturation synchronization)

### Installing Dependencies

#### Ubuntu / Debian / Pop!_OS
```bash
sudo apt install python3 python3-pyqt6 liblcms2-2 libkscreen-bin ddcutil
```

#### Arch Linux / Manjaro
```bash
sudo pacman -S python python-pyqt6 lcms2 libkscreen ddcutil
```

#### Fedora
```bash
sudo dnf install python3 python3-pyqt6 lcms2 libkscreen ddcutil
```

---

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/vfxno/radeon-color-control.git
   cd radeon-color-control
   ```

2. **Run the installer:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

The application will be installed to `~/.local/share/radeon-color-control` and added to your application launcher.

---

## 🎯 Usage

### Graphical Interface (GUI)
* Launch **Radeon Color Control** from your application menu, or run:
  ```bash
  radeon-color-control
  ```

### Command-Line Interface (CLI)
You can apply settings instantly without launching the GUI. This is ideal for binding to keyboard shortcuts (e.g. in KDE *System Settings → Shortcuts*):

```bash
# Apply a preset
radeon-color-control --preset "Esports Vibrance (CS2/FPS)"
radeon-color-control --preset "Ultra Saturated (200%+)"

# Set custom digital vibrance and contrast
radeon-color-control --saturation 150 --contrast 110

# Adjust color temperature (in Kelvin)
radeon-color-control --temperature 7000

# Toggle Wide Color Gamut
radeon-color-control --wcg on

# Reset screen back to default sRGB
radeon-color-control --reset
```

---

## 🗑️ Uninstallation

To remove the application and clean up desktop files:
```bash
./uninstall.sh
```

---

## 📄 License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
