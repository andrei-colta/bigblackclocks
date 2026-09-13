#!/usr/bin/env python3
"""
G510 LCD Control App.

Architecture: one QTabWidget, one tab per feature. Adding a new feature
= adding a new tab class + one line in MainWindow.__init__. Nothing in
an existing tab needs to change when a new one is added.

Phase 1 (this file): Backlight tab (color/brightness + service control).
G-Keys tab (this file): record/assign macros to G1-G18 per M1/M2/M3 profile.
Phase 2 (later):     Custom Screen tab (text/image placement on screen 6).
"""
import sys
import json
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QGridLayout, QComboBox, QSlider, QPushButton, QLabel,
    QMessageBox, QDialog,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import evdev
from evdev import ecodes

PROJECT_DIR = Path(__file__).resolve().parent
LED_DIR = Path("/sys/class/leds/g15::kbd_backlight")
DEFAULTS_SCRIPT = PROJECT_DIR / "set-backlight-color.sh"
MACROS_FILE = PROJECT_DIR / "macros.json"
MAIN_KEYBOARD_DEVICE = "/dev/input/by-id/usb-Logitech_G510s_Gaming_Keyboard-event-kbd"

COLOR_RGB = {
    "Blue-Violet": (110, 0, 255),
    "Red": (255, 0, 0),
    "Green": (0, 255, 0),
    "Blue": (0, 0, 255),
    "Purple": (128, 0, 128),
    "Cyan": (0, 255, 255),
    "Orange": (255, 100, 0),
    "Pink": (255, 0, 150),
    "White": (255, 255, 255),
}
DEFAULT_COLOR = "Blue-Violet"
DEFAULT_BRIGHTNESS_PCT = 100


def read_current_rgb():
    try:
        r, g, b = (int(x) for x in (LED_DIR / "multi_intensity").read_text().split())
        return (r, g, b)
    except Exception:
        return None


def read_current_brightness_pct():
    try:
        val = int((LED_DIR / "brightness").read_text().strip())
        return round(val * 100 / 255)
    except Exception:
        return 100


def apply_backlight(color_name, brightness_pct):
    """Writes the LED sysfs files AND rewrites set-backlight-color.sh so
    this becomes the new permanent boot default (matches the behavior
    already established by g510-backlight-apply.sh -- same contract)."""
    rgb = COLOR_RGB.get(color_name)
    if rgb is None:
        return False, f"Unknown color: {color_name}"
    brightness_val = round(brightness_pct * 255 / 100)
    try:
        (LED_DIR / "multi_intensity").write_text(f"{rgb[0]} {rgb[1]} {rgb[2]}")
        (LED_DIR / "brightness").write_text(str(brightness_val))
    except PermissionError as e:
        return False, f"Permission denied writing to {LED_DIR} -- check the udev rule (99-g510-lcd.rules) is installed: {e}"

    script = f"""#!/bin/bash
# Applies the chosen keyboard backlight color. Run automatically by
# 99-g510-lcd.rules whenever the LED device appears (boot or replug).
# Auto-updated by g510_app.py every time you click Apply.
echo {brightness_val} > /sys/class/leds/g15::kbd_backlight/brightness
echo "{rgb[0]} {rgb[1]} {rgb[2]}" > /sys/class/leds/g15::kbd_backlight/multi_intensity
"""
    DEFAULTS_SCRIPT.write_text(script)
    DEFAULTS_SCRIPT.chmod(0o755)
    return True, None


def run_systemctl(action):
    try:
        subprocess.run(
            ["systemctl", "--user", action,
             "g510-lcd-stats.service", "g510-lcd-buttons.service"],
            check=True, capture_output=True, text=True,
        )
        return True, None
    except subprocess.CalledProcessError as e:
        return False, e.stderr or str(e)


class BacklightTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("<b>Keyboard Backlight</b>"))

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color:"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(COLOR_RGB.keys())
        current_rgb = read_current_rgb()
        for name, rgb in COLOR_RGB.items():
            if rgb == current_rgb:
                self.color_combo.setCurrentText(name)
                break
        color_row.addWidget(self.color_combo)
        layout.addLayout(color_row)

        bright_row = QHBoxLayout()
        bright_row.addWidget(QLabel("Brightness:"))
        self.bright_slider = QSlider(Qt.Horizontal)
        self.bright_slider.setRange(0, 100)
        self.bright_slider.setValue(read_current_brightness_pct())
        self.bright_label = QLabel(f"{self.bright_slider.value()}%")
        self.bright_slider.valueChanged.connect(
            lambda v: self.bright_label.setText(f"{v}%")
        )
        bright_row.addWidget(self.bright_slider)
        bright_row.addWidget(self.bright_label)
        layout.addLayout(bright_row)

        btn_row = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.on_apply)
        defaults_btn = QPushButton("Apply Defaults")
        defaults_btn.clicked.connect(self.on_apply_defaults)
        btn_row.addWidget(apply_btn)
        btn_row.addWidget(defaults_btn)
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("<b>Service Control</b>"))
        svc_row = QHBoxLayout()
        start_btn = QPushButton("Start")
        start_btn.clicked.connect(lambda: self.on_service_action("start"))
        restart_btn = QPushButton("Restart Service")
        restart_btn.clicked.connect(lambda: self.on_service_action("restart"))
        svc_row.addWidget(start_btn)
        svc_row.addWidget(restart_btn)
        layout.addLayout(svc_row)

        layout.addStretch()
        self.setLayout(layout)

    def on_apply(self):
        ok, err = apply_backlight(self.color_combo.currentText(), self.bright_slider.value())
        if not ok:
            QMessageBox.critical(self, "Error", err)

    def on_apply_defaults(self):
        self.color_combo.setCurrentText(DEFAULT_COLOR)
        self.bright_slider.setValue(DEFAULT_BRIGHTNESS_PCT)
        ok, err = apply_backlight(DEFAULT_COLOR, DEFAULT_BRIGHTNESS_PCT)
        if not ok:
            QMessageBox.critical(self, "Error", err)

    def on_service_action(self, action):
        ok, err = run_systemctl(action)
        if not ok:
            QMessageBox.critical(self, "Error", err)


def load_macros():
    if MACROS_FILE.exists():
        try:
            return json.loads(MACROS_FILE.read_text())
        except Exception:
            pass
    return {"M1": {}, "M2": {}, "M3": {}}


def save_macro(profile, gkey, sequence):
    macros = load_macros()
    macros.setdefault(profile, {})[gkey] = sequence
    MACROS_FILE.write_text(json.dumps(macros, indent=2))


def clear_macro(profile, gkey):
    macros = load_macros()
    macros.setdefault(profile, {}).pop(gkey, None)
    MACROS_FILE.write_text(json.dumps(macros, indent=2))


class RecorderThread(QThread):
    """Captures real keystrokes from the main keyboard while recording,
    grabbing the device so they don't also leak into whatever window has
    focus. Emits the final ydotool-ready 'code:value code:value ...'
    string when stopped."""
    finished_recording = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._stop = False
        self._events = []

    def stop(self):
        self._stop = True

    def run(self):
        import select
        dev = evdev.InputDevice(MAIN_KEYBOARD_DEVICE)
        dev.grab()
        try:
            while not self._stop:
                # Poll with a short timeout instead of a blocking read --
                # read_loop() only checks _stop between events, so it can
                # hang forever if the user stops without pressing another
                # key. This checks _stop every 0.1s regardless.
                r, _, _ = select.select([dev.fd], [], [], 0.1)
                if not r:
                    continue
                for event in dev.read():
                    if event.type == ecodes.EV_KEY:
                        self._events.append(f"{event.code}:{event.value}")
        finally:
            dev.ungrab()
            dev.close()
        self.finished_recording.emit(" ".join(self._events))


class MacroRecordDialog(QDialog):
    def __init__(self, profile, gkey, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.gkey = gkey
        self.recorder = None
        self.recorded_sequence = None

        self.setWindowTitle(f"{profile} / {gkey}")
        layout = QVBoxLayout()

        macros = load_macros()
        existing = macros.get(profile, {}).get(gkey)
        self.status_label = QLabel(
            "Currently assigned." if existing else "Nothing assigned yet."
        )
        layout.addWidget(self.status_label)

        self.record_btn = QPushButton("Record")
        self.record_btn.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_btn)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.on_save)
        self.save_btn.setEnabled(False)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.on_clear)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def toggle_recording(self):
        if self.recorder is None:
            self.status_label.setText("Recording... press your key combo, then click Stop.")
            self.record_btn.setText("Stop")
            self.recorder = RecorderThread()
            self.recorder.finished_recording.connect(self.on_recorded)
            self.recorder.start()
        else:
            self.record_btn.setEnabled(False)  # ignore clicks until the thread actually finishes
            self.status_label.setText("Stopping...")
            self.recorder.stop()

    def reject(self):
        if self.recorder is not None:
            self.recorder.stop()
            self.recorder.wait(2000)  # let it clean up (ungrab) before the dialog closes
        super().reject()

    def on_recorded(self, sequence):
        self.recorded_sequence = sequence
        if self.recorder is not None:
            # The signal can arrive just before Qt finishes tearing down
            # the OS thread -- wait() blocks until that's truly done
            # before we drop the last Python reference. Skipping this
            # causes "QThread: Destroyed while thread is still running"
            # and a hard process abort (confirmed -- this crashed twice).
            self.recorder.wait()
        self.recorder = None
        self.record_btn.setText("Record")
        self.record_btn.setEnabled(True)
        self.status_label.setText(f"Captured {len(sequence.split())} events. Click Save to keep it.")
        self.save_btn.setEnabled(bool(sequence))

    def on_save(self):
        if self.recorded_sequence:
            save_macro(self.profile, self.gkey, self.recorded_sequence)
        self.accept()

    def on_clear(self):
        clear_macro(self.profile, self.gkey)
        self.accept()


class GKeysTab(QWidget):
    """3 groups of 6 keys (2 rows x 3 columns each), stacked with spacing
    -- mirrors the G510s's actual physical G-key layout. M1/M2/M3 buttons
    above select which profile you're viewing/editing here (the DAEMON
    separately tracks which profile is live based on physical M-key
    presses on the keyboard itself)."""
    def __init__(self):
        super().__init__()
        self.current_profile = "M1"
        layout = QVBoxLayout()

        layout.addWidget(QLabel("<b>G-Key Macros</b> (click a key to record/assign)"))

        layout.addSpacing(10)
        profile_row = QHBoxLayout()
        profile_row.setSpacing(24)  # spaced out like a title, not crammed together
        profile_row.addStretch()
        self.profile_buttons = {}
        for name in ("M1", "M2", "M3"):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet("font-weight: bold; font-size: 14px; padding: 6px 14px;")
            btn.clicked.connect(lambda _, n=name: self.select_profile(n))
            profile_row.addWidget(btn)
            self.profile_buttons[name] = btn
        profile_row.addStretch()
        self.profile_buttons["M1"].setChecked(True)
        layout.addLayout(profile_row)
        layout.addSpacing(16)

        grid_container = QVBoxLayout()
        grid_container.setSpacing(20)  # visible gap between the 3 groups
        self.key_buttons = {}
        key_num = 1
        for group in range(3):
            grid = QGridLayout()
            grid.setVerticalSpacing(8)  # gap between the 2 rows within a group
            grid.setHorizontalSpacing(6)
            for row in range(2):
                for col in range(3):
                    name = f"G{key_num}"
                    btn = QPushButton(name)
                    btn.clicked.connect(lambda _, n=name: self.open_key_dialog(n))
                    grid.addWidget(btn, row, col)
                    self.key_buttons[name] = btn
                    key_num += 1
            grid_container.addLayout(grid)
        layout.addLayout(grid_container)

        layout.addStretch()
        self.setLayout(layout)

    def select_profile(self, name):
        self.current_profile = name
        for n, btn in self.profile_buttons.items():
            btn.setChecked(n == name)

    def open_key_dialog(self, gkey):
        dlg = MacroRecordDialog(self.current_profile, gkey, self)
        dlg.exec_()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G510 LCD Control")
        self.resize(420, 420)

        tabs = QTabWidget()
        tabs.addTab(BacklightTab(), "Backlight")
        tabs.addTab(GKeysTab(), "G-Keys")
        # Phase 2: tabs.addTab(CustomScreenTab(), "Custom Screen")
        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
