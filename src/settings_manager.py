"""
Settings Manager for Radeon Color Control.
Handles persistence, presets, and user configuration.
"""

import os
import json
from typing import Dict, Any

CONFIG_DIR = os.path.expanduser("~/.config/radeon-color-control")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_PRESETS = {
    "Default (sRGB)": {
        "enabled": False,
        "saturation": 100,      # percentage (100 = normal)
        "contrast": 100,        # percentage (100 = normal)
        "brightness": 0,        # -50 to +50
        "temperature": 6500,    # Kelvin
        "wcg": False,
        "sync_ddc": False,
        "r_gain": 100,
        "g_gain": 100,
        "b_gain": 100
    },
    "Esports Vibrance (CS2/FPS)": {
        "enabled": True,
        "saturation": 145,
        "contrast": 110,
        "brightness": 5,
        "temperature": 6800,
        "wcg": True,
        "sync_ddc": True,
        "r_gain": 100,
        "g_gain": 100,
        "b_gain": 100
    },
    "Ultra Saturated (200%+)": {
        "enabled": True,
        "saturation": 180,
        "contrast": 115,
        "brightness": 2,
        "temperature": 6500,
        "wcg": True,
        "sync_ddc": True,
        "r_gain": 100,
        "g_gain": 100,
        "b_gain": 100
    },
    "Vivid Cinema": {
        "enabled": True,
        "saturation": 120,
        "contrast": 105,
        "brightness": 0,
        "temperature": 6500,
        "wcg": True,
        "sync_ddc": True,
        "r_gain": 100,
        "g_gain": 98,
        "b_gain": 98
    },
    "Warm Night": {
        "enabled": True,
        "saturation": 95,
        "contrast": 95,
        "brightness": -5,
        "temperature": 4800,
        "wcg": False,
        "sync_ddc": False,
        "r_gain": 100,
        "g_gain": 95,
        "b_gain": 90
    }
}

DEFAULT_CONFIG = {
    "current_output": "DP-2",
    "autostart": False,
    "close_to_tray": True,
    "current_settings": {
        "enabled": True,
        "saturation": 140,
        "contrast": 105,
        "brightness": 0,
        "temperature": 6500,
        "wcg": True,
        "sync_ddc": True,
        "r_gain": 100,
        "g_gain": 100,
        "b_gain": 100
    },
    "presets": DEFAULT_PRESETS
}


def load_config() -> Dict[str, Any]:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            if "presets" not in data:
                data["presets"] = DEFAULT_PRESETS.copy()
            else:
                for pk, pv in DEFAULT_PRESETS.items():
                    if pk not in data["presets"]:
                        data["presets"][pk] = pv
            return data
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")
