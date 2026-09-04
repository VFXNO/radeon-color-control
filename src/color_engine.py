"""
Color Engine for Radeon Color Control.
Generates custom matrix-shaper ICC profiles with VCGT (Video Card Gamma Table) tags
using liblcms2 and applies them to KWin via atomic kscreen-doctor commands.
"""

import os
import sys
import math
import json
import ctypes
import threading
import subprocess
from typing import List, Dict, Tuple, Optional

# Load liblcms2
try:
    lcms = ctypes.CDLL('liblcms2.so.2')
except Exception as e:
    raise RuntimeError(f"Could not load liblcms2.so.2: {e}")

class cmsCIExyY(ctypes.Structure):
    _fields_ = [
        ('x', ctypes.c_double),
        ('y', ctypes.c_double),
        ('Y', ctypes.c_double)
    ]

class cmsCIExyYTRIPLE(ctypes.Structure):
    _fields_ = [
        ('Red', cmsCIExyY),
        ('Green', cmsCIExyY),
        ('Blue', cmsCIExyY)
    ]

# Setup LCMS function signatures
lcms.cmsCreateRGBProfile.restype = ctypes.c_void_p
lcms.cmsCreateRGBProfile.argtypes = [
    ctypes.POINTER(cmsCIExyY),
    ctypes.POINTER(cmsCIExyYTRIPLE),
    ctypes.POINTER(ctypes.c_void_p)
]

lcms.cmsBuildGamma.restype = ctypes.c_void_p
lcms.cmsBuildGamma.argtypes = [ctypes.c_void_p, ctypes.c_double]

lcms.cmsBuildTabulatedToneCurve16.restype = ctypes.c_void_p
lcms.cmsBuildTabulatedToneCurve16.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint16)
]

lcms.cmsWriteTag.restype = ctypes.c_int
lcms.cmsWriteTag.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]

lcms.cmsSaveProfileToFile.restype = ctypes.c_int
lcms.cmsSaveProfileToFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

lcms.cmsCloseProfile.restype = ctypes.c_int
lcms.cmsCloseProfile.argtypes = [ctypes.c_void_p]

lcms.cmsFreeToneCurve.restype = None
lcms.cmsFreeToneCurve.argtypes = [ctypes.c_void_p]


def kelvin_to_rgb_multipliers(kelvin: float) -> Tuple[float, float, float]:
    """
    Computes RGB multipliers for a given color temperature (Kelvin).
    """
    temp = max(3000.0, min(12000.0, float(kelvin))) / 100.0

    # Red
    if temp <= 66.0:
        r = 255.0
    else:
        r = temp - 60.0
        r = 329.698727446 * (r ** -0.1332047592)
        r = max(0.0, min(255.0, r))

    # Green
    if temp <= 66.0:
        g = temp
        g = 99.4708025861 * math.log(max(1.0, g)) - 161.1195681661
        g = max(0.0, min(255.0, g))
    else:
        g = temp - 60.0
        g = 288.1221695283 * (g ** -0.0755148492)
        g = max(0.0, min(255.0, g))

    # Blue
    if temp >= 66.0:
        b = 255.0
    else:
        if temp <= 19.0:
            b = 0.0
        else:
            b = temp - 10.0
            b = 138.5177312231 * math.log(max(1.0, b)) - 305.0447927307
            b = max(0.0, min(255.0, b))

    return (r / 255.0, g / 255.0, b / 255.0)


def generate_color_profile(
    filepath: str,
    saturation: float = 1.0,     # 0.5 to 2.5 (1.0 = normal 100%)
    contrast: float = 1.0,       # 0.5 to 1.8 (1.0 = normal 100%)
    brightness: float = 0.0,     # -0.5 to 0.5 (0.0 = normal)
    temp_k: float = 6500.0,      # 4000 to 10000 K
    r_gain: float = 1.0,         # 0.0 to 1.0
    g_gain: float = 1.0,         # 0.0 to 1.0
    b_gain: float = 1.0          # 0.0 to 1.0
) -> bool:
    """
    Generates a matrix-shaper ICC profile with a VCGT (Video Card Gamma Table) tag
    so KWin offloads color calibration directly to AMD GPU hardware.
    """
    # 1. White point D65
    wp = cmsCIExyY(0.3127, 0.3290, 1.0)

    # 2. Base primaries
    s_rx, s_ry = 0.6400, 0.3300
    s_gx, s_gy = 0.3000, 0.6000
    s_bx, s_by = 0.1500, 0.0600

    # Digital saturation scaling
    sat = max(0.1, min(saturation, 3.0))
    scale = 1.0 / sat

    rx = 0.3127 + scale * (s_rx - 0.3127)
    ry = 0.3290 + scale * (s_ry - 0.3290)
    gx = 0.3127 + scale * (s_gx - 0.3127)
    gy = 0.3290 + scale * (s_gy - 0.3290)
    bx = 0.3127 + scale * (s_bx - 0.3127)
    by = 0.3290 + scale * (s_by - 0.3290)

    prim = cmsCIExyYTRIPLE(
        cmsCIExyY(rx, ry, 1.0),
        cmsCIExyY(gx, gy, 1.0),
        cmsCIExyY(bx, by, 1.0)
    )

    # Linear TRC for base matrix
    c_lin = lcms.cmsBuildGamma(None, 1.0)
    curves_lin = (ctypes.c_void_p * 3)(c_lin, c_lin, c_lin)

    h_profile = lcms.cmsCreateRGBProfile(ctypes.byref(wp), ctypes.byref(prim), curves_lin)
    if not h_profile:
        return False

    # 3. Build VCGT curves (Video Card Gamma Table)
    temp_r, temp_g, temp_b = kelvin_to_rgb_multipliers(temp_k)
    final_r_mult = temp_r * r_gain
    final_g_mult = temp_g * g_gain
    final_b_mult = temp_b * b_gain

    n = 256
    r_vals = (ctypes.c_uint16 * n)()
    g_vals = (ctypes.c_uint16 * n)()
    b_vals = (ctypes.c_uint16 * n)()

    c_val = max(0.2, min(2.0, contrast))
    b_val = max(-0.5, min(0.5, brightness * 0.4))

    for i in range(n):
        x = i / (n - 1)
        v = 0.5 + (x - 0.5) * c_val + b_val
        v = max(0.0, min(1.0, v))

        vr = max(0.0, min(1.0, v * final_r_mult))
        vg = max(0.0, min(1.0, v * final_g_mult))
        vb = max(0.0, min(1.0, v * final_b_mult))

        r_vals[i] = int(round(vr * 65535))
        g_vals[i] = int(round(vg * 65535))
        b_vals[i] = int(round(vb * 65535))

    vcgt_r = lcms.cmsBuildTabulatedToneCurve16(None, n, r_vals)
    vcgt_g = lcms.cmsBuildTabulatedToneCurve16(None, n, g_vals)
    vcgt_b = lcms.cmsBuildTabulatedToneCurve16(None, n, b_vals)
    vcgt_curves = (ctypes.c_void_p * 3)(vcgt_r, vcgt_g, vcgt_b)

    # Tag signature: cmsSigVideoCardGammaTag = 0x76636774 ('vcgt')
    lcms.cmsWriteTag(h_profile, 0x76636774, vcgt_curves)

    lcms.cmsFreeToneCurve(c_lin)
    lcms.cmsFreeToneCurve(vcgt_r)
    lcms.cmsFreeToneCurve(vcgt_g)
    lcms.cmsFreeToneCurve(vcgt_b)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    saved = lcms.cmsSaveProfileToFile(h_profile, filepath.encode('utf-8'))
    lcms.cmsCloseProfile(h_profile)
    return saved != 0


def get_connected_outputs() -> List[Dict]:
    """
    Returns a list of connected display outputs via kscreen-doctor.
    """
    try:
        res = subprocess.check_output(['kscreen-doctor', '-j'], stderr=subprocess.DEVNULL)
        data = json.loads(res.decode('utf-8'))
        outputs = []
        for op in data.get('outputs', []):
            if op.get('connected'):
                outputs.append({
                    'name': op.get('name'),
                    'id': op.get('id'),
                    'wcg': op.get('wcg', False),
                    'hdr': op.get('hdr', False),
                    'icc': op.get('iccProfilePath', '')
                })
        return outputs
    except Exception:
        return [{'name': 'DP-2', 'id': 1, 'wcg': False, 'hdr': False, 'icc': ''}]


def apply_color_settings(
    output_name: str,
    profile_path: str,
    enable_wcg: bool = True,
    sdr_gamut: int = 100
) -> bool:
    """
    Applies the specified ICC profile, WCG state, and SDR gamut expansion to the output.
    """
    try:
        wcg_cmd = f"output.{output_name}.wcg.enable" if enable_wcg else f"output.{output_name}.wcg.disable"
        gamut_val = max(0, min(100, int(sdr_gamut)))
        gamut_cmd = f"output.{output_name}.sdrGamut.{gamut_val}"
        src_cmd = f"output.{output_name}.colorProfileSource.ICC"
        icc_cmd = f"output.{output_name}.iccprofile.{profile_path}" if profile_path else f"output.{output_name}.iccprofile."

        cmd = ['kscreen-doctor', src_cmd, wcg_cmd, gamut_cmd, icc_cmd]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Error applying color settings: {e}", file=sys.stderr)
        return False


def reset_color_settings(output_name: str) -> bool:
    """
    Clears the ICC profile and resets WCG and SDR Gamut to sRGB default.
    """
    try:
        cmd = [
            'kscreen-doctor',
            f'output.{output_name}.colorProfileSource.sRGB',
            f'output.{output_name}.wcg.disable',
            f'output.{output_name}.sdrGamut.0',
            f'output.{output_name}.iccprofile.'
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Error resetting color settings: {e}", file=sys.stderr)
        return False


def set_hardware_saturation_async(saturation_percent: int):
    """
    Optionally syncs monitor hardware saturation via ddcutil in a background thread
    so the UI never stutters.
    """
    def worker():
        try:
            hw_val = int(round(saturation_percent * 0.5))
            hw_val = max(0, min(100, hw_val))
            subprocess.run(
                ['ddcutil', 'setvcp', '8a', str(hw_val)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1.5
            )
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()
