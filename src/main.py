#!/usr/bin/env python3
"""
Radeon Color Control - Main Entrypoint
Supports both GUI and CLI operation.
"""

import os
import sys
import argparse

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from color_engine import (
    generate_color_profile, apply_color_settings,
    reset_color_settings, get_connected_outputs,
    set_hardware_saturation_async
)
from settings_manager import (
    load_config, save_config, DEFAULT_CONFIG, DEFAULT_PRESETS
)

def run_cli(args):
    config = load_config()
    output = args.display or config.get("current_output", "DP-2")

    if args.reset:
        print(f"Resetting color calibration on {output} to sRGB default...")
        reset_color_settings(output)
        set_hardware_saturation_async(100)
        config["current_settings"]["enabled"] = False
        save_config(config)
        print("Done.")
        return

    if args.preset:
        presets = config.get("presets", DEFAULT_PRESETS)
        if args.preset not in presets:
            print(f"Error: Unknown preset '{args.preset}'. Available presets: {', '.join(presets.keys())}")
            sys.exit(1)
        data = presets[args.preset]
        print(f"Applying preset '{args.preset}' to {output}...")
        sat_val = data.get("saturation", 100)
        sat_ratio = sat_val / 100.0
        contrast_ratio = data.get("contrast", 100) / 100.0
        brightness_val = data.get("brightness", 0) / 100.0
        temp_k = float(data.get("temperature", 6500))
        r_gain = data.get("r_gain", 100) / 100.0
        g_gain = data.get("g_gain", 100) / 100.0
        b_gain = data.get("b_gain", 100) / 100.0
        wcg = data.get("wcg", True)
        sync_ddc = data.get("sync_ddc", True)

        profile_dir = os.path.expanduser("~/.local/share/radeon-color-control/profiles")
        os.makedirs(profile_dir, exist_ok=True)
        prof_path = os.path.join(profile_dir, "cli_profile.icc")

        generate_color_profile(
            prof_path,
            saturation=sat_ratio,
            contrast=contrast_ratio,
            brightness=brightness_val,
            temp_k=temp_k,
            r_gain=r_gain,
            g_gain=g_gain,
            b_gain=b_gain
        )
        sdr_gamut_val = min(100, int(round((sat_val / 150.0) * 100)))
        apply_color_settings(output, prof_path, enable_wcg=wcg, sdr_gamut=sdr_gamut_val)
        if sync_ddc:
            set_hardware_saturation_async(sat_val)

        config["current_settings"] = data
        save_config(config)
        print("Done.")
        return

    if (args.saturation is not None or args.contrast is not None or
        args.brightness is not None or args.temperature is not None or args.wcg is not None):
        cur = config.get("current_settings", DEFAULT_CONFIG["current_settings"])
        if args.saturation is not None: cur["saturation"] = args.saturation
        if args.contrast is not None: cur["contrast"] = args.contrast
        if args.brightness is not None: cur["brightness"] = args.brightness
        if args.temperature is not None: cur["temperature"] = args.temperature
        if args.wcg is not None: cur["wcg"] = (args.wcg.lower() in ("1", "true", "yes", "on"))
        cur["enabled"] = True

        profile_dir = os.path.expanduser("~/.local/share/radeon-color-control/profiles")
        os.makedirs(profile_dir, exist_ok=True)
        prof_path = os.path.join(profile_dir, "cli_profile.icc")

        sat_val = cur["saturation"]
        generate_color_profile(
            prof_path,
            saturation=sat_val / 100.0,
            contrast=cur["contrast"] / 100.0,
            brightness=cur["brightness"] / 100.0,
            temp_k=float(cur["temperature"]),
            r_gain=cur.get("r_gain", 100) / 100.0,
            g_gain=cur.get("g_gain", 100) / 100.0,
            b_gain=cur.get("b_gain", 100) / 100.0
        )
        sdr_gamut_val = min(100, int(round((sat_val / 150.0) * 100)))
        apply_color_settings(output, prof_path, enable_wcg=cur["wcg"], sdr_gamut=sdr_gamut_val)
        if cur.get("sync_ddc", True):
            set_hardware_saturation_async(sat_val)

        save_config(config)
        print(f"Applied settings to {output}: Saturation={cur['saturation']}%, Contrast={cur['contrast']}%, Temp={cur['temperature']}K, WCG={cur['wcg']}")
        return

    run_gui(args.tray)

def run_gui(start_in_tray=False):
    from PyQt6.QtWidgets import QApplication
    from gui import RadeonColorWindow

    app = QApplication(sys.argv)
    app.setApplicationName("RadeonColorControl")
    app.setDesktopFileName("radeon-color-control")
    window = RadeonColorWindow(start_in_tray=start_in_tray)
    sys.exit(app.exec())

def main():
    parser = argparse.ArgumentParser(
        description="AMD Radeon Custom Color & Digital Vibrance Control for Linux"
    )
    parser.add_argument("--display", type=str, help="Target display connector (e.g. DP-2)")
    parser.add_argument("--saturation", type=int, help="Digital Vibrance / Saturation (0 - 250%%)")
    parser.add_argument("--contrast", type=int, help="Contrast (50 - 180%%)")
    parser.add_argument("--brightness", type=int, help="Brightness offset (-50 to 50)")
    parser.add_argument("--temperature", type=int, help="Color temperature (4000 to 10000 K)")
    parser.add_argument("--wcg", type=str, help="Wide Color Gamut (on/off)")
    parser.add_argument("--preset", type=str, help="Apply preset by name")
    parser.add_argument("--reset", action="store_true", help="Reset display to sRGB default")
    parser.add_argument("--tray", action="store_true", help="Start minimized to system tray")
    parser.add_argument("--gui", action="store_true", help="Launch Graphical Interface")

    args = parser.parse_args()

    cli_flags = [args.saturation, args.contrast, args.brightness, args.temperature, args.wcg, args.preset, args.reset]
    if any(f is not None and f is not False for f in cli_flags):
        run_cli(args)
    else:
        run_gui(start_in_tray=args.tray)

if __name__ == "__main__":
    main()
