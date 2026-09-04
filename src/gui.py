"""
Graphical User Interface for Radeon Color Control.
Built with PyQt6, providing an AMD Radeon Software style dark theme,
real-time sliders for Digital Vibrance, Color Temperature, Contrast,
Brightness, RGB Gains, and Wide Color Gamut (WCG).
"""

import os
import sys
import shutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QCheckBox, QPushButton, QComboBox, QFrame,
    QSystemTrayIcon, QMenu, QInputDialog, QScrollArea
)

from color_engine import (
    generate_color_profile, get_connected_outputs,
    apply_color_settings, reset_color_settings,
    set_hardware_saturation_async
)
from settings_manager import (
    load_config, save_config, DEFAULT_CONFIG, DEFAULT_PRESETS
)

STYLESHEET = """
QMainWindow {
    background-color: #121417;
}

QWidget#CentralWidget {
    background-color: #121417;
    color: #e0e4eb;
    font-family: 'Inter', 'Segoe UI', 'Noto Sans', sans-serif;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #181b20;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #363c47;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #e01122;
}

QFrame.Card {
    background-color: #1a1d23;
    border: 1px solid #282c35;
    border-radius: 10px;
    padding: 14px;
}

QLabel {
    color: #e0e4eb;
}

QLabel.HeaderTitle {
    font-size: 19px;
    font-weight: bold;
    color: #ffffff;
}

QLabel.HeaderSubtitle {
    font-size: 12px;
    color: #8f96a3;
}

QLabel.CardTitle {
    font-size: 14px;
    font-weight: 600;
    color: #ffffff;
}

QLabel.CardDesc {
    font-size: 11px;
    color: #7b8290;
}

QLabel.ValueBadge {
    font-size: 13px;
    font-weight: bold;
    color: #ff3344;
    background-color: #242932;
    border: 1px solid #333946;
    border-radius: 6px;
    padding: 2px 8px;
    min-width: 48px;
}

QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #272c36;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff3344, stop:1 #e01122);
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #e01122;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #ff4d5e;
    border-color: #ffffff;
}

QComboBox {
    background-color: #20242c;
    border: 1px solid #323845;
    border-radius: 6px;
    padding: 6px 12px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 500;
}
QComboBox:hover {
    border-color: #ff3344;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #1c2027;
    border: 1px solid #333946;
    color: #ffffff;
    selection-background-color: #e01122;
}

QPushButton {
    background-color: #242932;
    border: 1px solid #353b47;
    border-radius: 6px;
    padding: 7px 14px;
    color: #e0e4eb;
    font-size: 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #2d3340;
    border-color: #ff3344;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #191c22;
}

QPushButton#PrimaryBtn {
    background-color: #e01122;
    border: 1px solid #ff3344;
    color: #ffffff;
}
QPushButton#PrimaryBtn:hover {
    background-color: #ff2233;
}

QPushButton#ResetBtn {
    background-color: transparent;
    border: 1px solid #3a414f;
    color: #9ba3b2;
}
QPushButton#ResetBtn:hover {
    border-color: #ff5566;
    color: #ff5566;
}

QCheckBox {
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #3a414f;
    background-color: #20242c;
}
QCheckBox::indicator:checked {
    background-color: #e01122;
    border-color: #ff3344;
}
"""

def find_app_icon() -> Optional[str]:
    """Dynamically locates the application icon across local dev, user, and system paths."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "icon.svg"),
        os.path.expanduser("~/.local/share/radeon-color-control/icon.svg"),
        os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps/radeon-color-control.svg"),
        "/usr/share/icons/hicolor/scalable/apps/radeon-color-control.svg"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

class RadeonColorWindow(QMainWindow):
    def __init__(self, start_in_tray=False):
        super().__init__()
        self.config = load_config()
        self.profile_toggle = 0
        self.is_updating_ui = False

        # Paths
        self.profile_dir = os.path.expanduser("~/.local/share/radeon-color-control/profiles")
        os.makedirs(self.profile_dir, exist_ok=True)
        self.profile_a = os.path.join(self.profile_dir, "active_a.icc")
        self.profile_b = os.path.join(self.profile_dir, "active_b.icc")

        # Debounce timer for smooth slider adjustment
        self.apply_timer = QTimer(self)
        self.apply_timer.setSingleShot(True)
        self.apply_timer.setInterval(70)
        self.apply_timer.timeout.connect(self._perform_apply)

        self.init_ui()
        self.load_settings_into_ui()
        self.init_tray()

        if start_in_tray:
            self.hide()
        else:
            self.show()

        # Apply settings on start
        self.apply_timer.start(0)

    def init_ui(self):
        self.setWindowTitle("AMD Radeon Software - Custom Color")
        self.setMinimumSize(680, 800)
        self.resize(720, 860)
        self.setStyleSheet(STYLESHEET)

        icon_path = find_app_icon()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(14)

        # 1. Header Bar
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("RADEON™ CUSTOM COLOR")
        title_lbl.setProperty("class", "HeaderTitle")
        subtitle_lbl = QLabel("GPU Digital Vibrance & Hardware Color Calibration for Linux")
        subtitle_lbl.setProperty("class", "HeaderSubtitle")
        title_box.addWidget(title_lbl)
        title_box.addWidget(subtitle_lbl)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Status badge
        self.lbl_status = QLabel("● ACTIVE")
        self.lbl_status.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 12px; margin-right: 12px;")
        header_layout.addWidget(self.lbl_status)

        # Master Switch
        self.chk_master = QCheckBox("Custom Color Enabled")
        self.chk_master.setChecked(True)
        self.chk_master.toggled.connect(self.on_master_toggled)
        header_layout.addWidget(self.chk_master)

        root_layout.addWidget(header_frame)

        # 2. Display Selector & Preset Bar
        control_bar = QFrame()
        control_bar.setProperty("class", "Card")
        cb_layout = QHBoxLayout(control_bar)
        cb_layout.setContentsMargins(12, 10, 12, 10)
        cb_layout.setSpacing(12)

        cb_layout.addWidget(QLabel("Display:"))
        self.combo_displays = QComboBox()
        self.populate_displays()
        self.combo_displays.currentIndexChanged.connect(self.on_display_changed)
        cb_layout.addWidget(self.combo_displays, 1)

        btn_refresh = QPushButton("⟳")
        btn_refresh.setToolTip("Refresh connected displays")
        btn_refresh.setFixedWidth(36)
        btn_refresh.clicked.connect(self.populate_displays)
        cb_layout.addWidget(btn_refresh)

        cb_layout.addSpacing(15)

        cb_layout.addWidget(QLabel("Preset:"))
        self.combo_presets = QComboBox()
        self.populate_presets()
        self.combo_presets.currentTextChanged.connect(self.on_preset_selected)
        cb_layout.addWidget(self.combo_presets, 1)

        btn_save_preset = QPushButton("Save...")
        btn_save_preset.clicked.connect(self.on_save_preset)
        cb_layout.addWidget(btn_save_preset)

        root_layout.addWidget(control_bar)

        # 3. Scrollable Slider Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 4, 4, 4)
        scroll_layout.setSpacing(12)

        # Card: DIGITAL VIBRANCE (SATURATION)
        self.card_sat, self.slider_sat, self.lbl_sat_val = self.create_slider_card(
            title="Digital Vibrance (Saturation)",
            desc="Digitally multiplies saturation on GPU & monitor (100% is normal, 140%+ for FPS gaming)",
            min_val=0, max_val=250, default_val=140, unit="%"
        )
        scroll_layout.addWidget(self.card_sat)

        # Card: HARDWARE + GAMUT OPTIONS
        card_gamut = QFrame()
        card_gamut.setProperty("class", "Card")
        gamut_layout = QVBoxLayout(card_gamut)
        gamut_layout.setSpacing(8)

        row_wcg = QHBoxLayout()
        wcg_info = QVBoxLayout()
        wcg_title = QLabel("Wide Color Gamut (WCG / DCI-P3)")
        wcg_title.setProperty("class", "CardTitle")
        wcg_desc = QLabel("Unlocks native 96% DCI-P3 spectrum without sRGB clamping")
        wcg_desc.setProperty("class", "CardDesc")
        wcg_info.addWidget(wcg_title)
        wcg_info.addWidget(wcg_desc)
        row_wcg.addLayout(wcg_info)
        row_wcg.addStretch()

        self.chk_wcg = QCheckBox("Enable WCG")
        self.chk_wcg.setChecked(True)
        self.chk_wcg.toggled.connect(self.on_slider_changed)
        row_wcg.addWidget(self.chk_wcg)
        gamut_layout.addLayout(row_wcg)

        # DDC/CI Hardware Sync
        row_ddc = QHBoxLayout()
        ddc_info = QVBoxLayout()
        ddc_title = QLabel("Sync Monitor Hardware Saturation (DDC/CI)")
        ddc_title.setProperty("class", "CardTitle")
        ddc_desc = QLabel("Synchronizes the monitor's physical saturation scalar alongside digital vibrance")
        ddc_desc.setProperty("class", "CardDesc")
        ddc_info.addWidget(ddc_title)
        ddc_info.addWidget(ddc_desc)
        row_ddc.addLayout(ddc_info)
        row_ddc.addStretch()

        self.chk_ddc = QCheckBox("Sync Hardware")
        self.chk_ddc.setChecked(True)
        self.chk_ddc.toggled.connect(self.on_slider_changed)
        row_ddc.addWidget(self.chk_ddc)
        gamut_layout.addLayout(row_ddc)

        scroll_layout.addWidget(card_gamut)

        # Card: COLOR TEMPERATURE
        self.card_temp, self.slider_temp, self.lbl_temp_val = self.create_slider_card(
            title="Color Temperature",
            desc="Adjusts white point from warm candle-light to crisp daylight (6500K is neutral)",
            min_val=4000, max_val=10000, default_val=6500, unit="K"
        )
        scroll_layout.addWidget(self.card_temp)

        # Card: CONTRAST
        self.card_contrast, self.slider_contrast, self.lbl_contrast_val = self.create_slider_card(
            title="Contrast",
            desc="Deepens dark shadows and brightens highlights for punchier visuals",
            min_val=50, max_val=180, default_val=110, unit="%"
        )
        scroll_layout.addWidget(self.card_contrast)

        # Card: BRIGHTNESS
        self.card_bright, self.slider_bright, self.lbl_bright_val = self.create_slider_card(
            title="Digital Brightness Offset",
            desc="Fine-tunes luminance offset across the entire desktop",
            min_val=-50, max_val=50, default_val=0, unit=""
        )
        scroll_layout.addWidget(self.card_bright)

        # Card: COLOR BALANCE (RGB GAINS)
        card_rgb = QFrame()
        card_rgb.setProperty("class", "Card")
        rgb_layout = QVBoxLayout(card_rgb)
        rgb_title = QLabel("Color Balance (RGB Gains)")
        rgb_title.setProperty("class", "CardTitle")
        rgb_desc = QLabel("Individually calibrate Red, Green, and Blue channel intensities")
        rgb_desc.setProperty("class", "CardDesc")
        rgb_layout.addWidget(rgb_title)
        rgb_layout.addWidget(rgb_desc)
        rgb_layout.addSpacing(6)

        self.slider_r, self.lbl_r_val = self.create_sub_slider(rgb_layout, "Red Channel Gain", "#ff4444")
        self.slider_g, self.lbl_g_val = self.create_sub_slider(rgb_layout, "Green Channel Gain", "#44dd66")
        self.slider_b, self.lbl_b_val = self.create_sub_slider(rgb_layout, "Blue Channel Gain", "#44aaff")

        scroll_layout.addWidget(card_rgb)
        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area, 1)

        # 4. Footer Bar
        footer = QFrame()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        self.chk_autostart = QCheckBox("Start minimized at login")
        self.chk_autostart.setChecked(self.config.get("autostart", False))
        self.chk_autostart.toggled.connect(self.on_autostart_toggled)
        footer_layout.addWidget(self.chk_autostart)

        footer_layout.addStretch()

        btn_reset = QPushButton("Reset Defaults")
        btn_reset.setObjectName("ResetBtn")
        btn_reset.clicked.connect(self.reset_defaults)
        footer_layout.addWidget(btn_reset)

        btn_apply = QPushButton("Apply Settings")
        btn_apply.setObjectName("PrimaryBtn")
        btn_apply.clicked.connect(self.force_apply)
        footer_layout.addWidget(btn_apply)

        root_layout.addWidget(footer)

    def create_slider_card(self, title, desc, min_val, max_val, default_val, unit=""):
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        info_col = QVBoxLayout()
        info_col.setSpacing(1)

        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "CardTitle")
        lbl_desc = QLabel(desc)
        lbl_desc.setProperty("class", "CardDesc")
        info_col.addWidget(lbl_title)
        info_col.addWidget(lbl_desc)
        top_row.addLayout(info_col)

        top_row.addStretch()

        lbl_val = QLabel(f"{default_val}{unit}")
        lbl_val.setProperty("class", "ValueBadge")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(lbl_val)
        layout.addLayout(top_row)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        layout.addWidget(slider)

        def on_val_change(val):
            prefix = "+" if unit == "" and val > 0 else ""
            lbl_val.setText(f"{prefix}{val}{unit}")
            self.on_slider_changed()

        slider.valueChanged.connect(on_val_change)
        return card, slider, lbl_val

    def create_sub_slider(self, parent_layout, label_text, color_hex):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {color_hex}; font-weight: 500; font-size: 12px;")
        row.addWidget(lbl)
        row.addStretch()

        val_lbl = QLabel("100%")
        val_lbl.setProperty("class", "ValueBadge")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(val_lbl)
        parent_layout.addLayout(row)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(100)

        def on_change(val):
            val_lbl.setText(f"{val}%")
            self.on_slider_changed()

        slider.valueChanged.connect(on_change)
        parent_layout.addWidget(slider)
        return slider, val_lbl

    def populate_displays(self):
        self.combo_displays.blockSignals(True)
        self.combo_displays.clear()
        outputs = get_connected_outputs()
        current = self.config.get("current_output", "DP-2")
        selected_index = 0
        for i, op in enumerate(outputs):
            name = op.get("name", "Unknown")
            self.combo_displays.addItem(f"{name} (Connected)", name)
            if name == current:
                selected_index = i
        self.combo_displays.setCurrentIndex(selected_index)
        self.combo_displays.blockSignals(False)

    def populate_presets(self):
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()
        presets = self.config.get("presets", DEFAULT_PRESETS)
        for name in presets.keys():
            self.combo_presets.addItem(name)
        self.combo_presets.blockSignals(False)

    def on_display_changed(self, idx):
        output = self.combo_displays.currentData()
        if output:
            self.config["current_output"] = output
            save_config(self.config)
            self.apply_timer.start(50)

    def on_preset_selected(self, preset_name):
        if self.is_updating_ui:
            return
        presets = self.config.get("presets", DEFAULT_PRESETS)
        if preset_name in presets:
            self.apply_preset_data(presets[preset_name])

    def apply_preset_data(self, data):
        self.is_updating_ui = True
        self.chk_master.setChecked(True)
        self.slider_sat.setValue(int(data.get("saturation", 140)))
        self.slider_contrast.setValue(int(data.get("contrast", 110)))
        self.slider_bright.setValue(int(data.get("brightness", 0)))
        self.slider_temp.setValue(int(data.get("temperature", 6500)))
        self.chk_wcg.setChecked(data.get("wcg", True))
        self.slider_r.setValue(int(data.get("r_gain", 100)))
        self.slider_g.setValue(int(data.get("g_gain", 100)))
        self.slider_b.setValue(int(data.get("b_gain", 100)))
        self.is_updating_ui = False
        self.on_slider_changed()

    def on_save_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Enter a name for your custom preset:")
        if ok and name.strip():
            name = name.strip()
            settings = self.get_current_ui_settings()
            self.config.setdefault("presets", {})[name] = settings
            save_config(self.config)
            self.populate_presets()
            self.combo_presets.setCurrentText(name)

    def on_slider_changed(self):
        if self.is_updating_ui:
            return
        if not self.chk_master.isChecked():
            self.chk_master.blockSignals(True)
            self.chk_master.setChecked(True)
            self.chk_master.blockSignals(False)
            self.lbl_status.setText("● ACTIVE")
            self.lbl_status.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 12px; margin-right: 12px;")

        self.apply_timer.start()

    def on_master_toggled(self, checked):
        if checked:
            self.lbl_status.setText("● ACTIVE")
            self.lbl_status.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 12px; margin-right: 12px;")
            self.apply_timer.start(0)
        else:
            self.lbl_status.setText("○ DISABLED")
            self.lbl_status.setStyleSheet("color: #888888; font-weight: bold; font-size: 12px; margin-right: 12px;")
            output = self.combo_displays.currentData() or "DP-2"
            reset_color_settings(output)

    def force_apply(self):
        self.chk_master.setChecked(True)
        self._perform_apply()

    def get_current_ui_settings(self):
        return {
            "enabled": self.chk_master.isChecked(),
            "saturation": self.slider_sat.value(),
            "contrast": self.slider_contrast.value(),
            "brightness": self.slider_bright.value(),
            "temperature": self.slider_temp.value(),
            "wcg": self.chk_wcg.isChecked(),
            "sync_ddc": self.chk_ddc.isChecked(),
            "r_gain": self.slider_r.value(),
            "g_gain": self.slider_g.value(),
            "b_gain": self.slider_b.value()
        }

    def _perform_apply(self):
        settings = self.get_current_ui_settings()
        self.config["current_settings"] = settings
        save_config(self.config)

        output = self.combo_displays.currentData() or "DP-2"

        if not settings["enabled"]:
            reset_color_settings(output)
            return

        self.profile_toggle = 1 - self.profile_toggle
        target_profile = self.profile_a if self.profile_toggle == 0 else self.profile_b

        sat_val = settings["saturation"]
        sat_ratio = sat_val / 100.0
        contrast_ratio = settings["contrast"] / 100.0
        brightness_val = settings["brightness"] / 100.0
        temp_k = float(settings["temperature"])
        r_ratio = settings["r_gain"] / 100.0
        g_ratio = settings["g_gain"] / 100.0
        b_ratio = settings["b_gain"] / 100.0
        wcg = settings["wcg"]

        sdr_gamut_val = min(100, int(round((sat_val / 150.0) * 100)))

        ok = generate_color_profile(
            target_profile,
            saturation=sat_ratio,
            contrast=contrast_ratio,
            brightness=brightness_val,
            temp_k=temp_k,
            r_gain=r_ratio,
            g_gain=g_ratio,
            b_gain=b_ratio
        )

        if ok:
            apply_color_settings(output, target_profile, enable_wcg=wcg, sdr_gamut=sdr_gamut_val)

        if settings.get("sync_ddc", True):
            set_hardware_saturation_async(sat_val)

    def load_settings_into_ui(self):
        cur = self.config.get("current_settings", DEFAULT_CONFIG["current_settings"])
        cur["enabled"] = True
        self.apply_preset_data(cur)

    def reset_defaults(self):
        self.apply_preset_data(DEFAULT_PRESETS["Default (sRGB)"])

    def on_autostart_toggled(self, checked):
        self.config["autostart"] = checked
        save_config(self.config)
        autostart_path = os.path.expanduser("~/.config/autostart/radeon-color-control.desktop")
        if checked:
            os.makedirs(os.path.dirname(autostart_path), exist_ok=True)
            bin_path = shutil.which("radeon-color-control") or os.path.expanduser("~/.local/bin/radeon-color-control")
            icon_str = find_app_icon() or "radeon-color-control"
            content = f"""[Desktop Entry]
Type=Application
Name=Radeon Color Control
Comment=AMD Custom Color Management
Exec={bin_path} --tray
Icon={icon_str}
Terminal=false
Categories=Utility;Settings;
X-KDE-autostart-phase=2
"""
            with open(autostart_path, "w") as f:
                f.write(content)
        else:
            if os.path.exists(autostart_path):
                os.remove(autostart_path)

    def init_tray(self):
        self.tray = QSystemTrayIcon(self)
        icon_path = find_app_icon()
        if icon_path:
            self.tray.setIcon(QIcon(icon_path))
        else:
            self.tray.setIcon(self.windowIcon())

        menu = QMenu()

        act_show = menu.addAction("Open Color Control")
        act_show.triggered.connect(self.show_and_raise)

        menu.addSeparator()

        presets_menu = menu.addMenu("Presets")
        for preset_name in self.config.get("presets", DEFAULT_PRESETS).keys():
            act = presets_menu.addAction(preset_name)
            act.triggered.connect(lambda checked, name=preset_name: self.combo_presets.setCurrentText(name))

        menu.addSeparator()

        act_toggle = menu.addAction("Toggle Color On/Off")
        act_toggle.triggered.connect(lambda: self.chk_master.setChecked(not self.chk_master.isChecked()))

        act_reset = menu.addAction("Reset to Default")
        act_reset.triggered.connect(self.reset_defaults)

        menu.addSeparator()

        act_quit = menu.addAction("Exit")
        act_quit.triggered.connect(self.quit_app)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_and_raise()

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self.config.get("close_to_tray", True):
            event.ignore()
            self.hide()
        else:
            event.accept()

    def quit_app(self):
        QApplication.quit()
