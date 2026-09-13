# G510s Keyboard Backlight Control (yad script)

A standalone tool to change the Logitech G510s keyboard's RGB
backlight color and brightness, with no sudo prompts after initial
setup.

**This is the original, superseded UI.** The active project moved to a
proper PyQt5 app — see the `main` branch for that. This branch is kept
as a working, standalone reference for the simpler script-based
approach.

## Setup

```bash
./install-deps.sh
```

Installs `yad` and a udev rule granting your user account write access
to the keyboard's backlight LED files (so you never need sudo to
change the color afterward).

## Use

```bash
./g510-backlight-control.sh
```

Opens a small window: pick a color from the dropdown, set brightness
with the slider, click **Apply**. **Apply Defaults** resets to a
blue-violet default. Both buttons write immediately to the keyboard
*and* update `set-backlight-color.sh` so your choice survives reboots
and USB replugs (that script re-applies automatically via the udev
rule whenever the keyboard's LED device appears).

## Files

| File | What it does |
|---|---|
| `g510-backlight-control.sh` | The GUI (a `yad` form) |
| `g510-backlight-apply.sh` | Does the actual work when Apply is clicked: writes the LED sysfs files, rewrites `set-backlight-color.sh` |
| `set-backlight-color.sh` | Applies the saved default color on boot/replug — auto-rewritten by Apply, don't hand-edit and expect it to stick |
| `99-backlight-led.rules` | udev rule: grants your user group write access to the LED files, runs `set-backlight-color.sh` automatically when the keyboard's LED device appears |
| `install-deps.sh` | One-time setup: installs `yad`, installs the udev rule |

## Known limitation (why there's a color dropdown, not a live picker)

`yad`'s live color-picker widget (`CLR` field type) crashes when combined
with a brightness slider (`SCL` field type) in the same form — confirmed
GTK bug on this system. The dropdown of preset colors sidesteps it
entirely. If you want to add more colors, edit the `COLOR_RGB`
associative array at the top of both `.sh` files (keep them in sync).
