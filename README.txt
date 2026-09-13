G510s LCD Stats Screen + Buttons + Backlight
=============================================
Repo: github.com/grumpybollocks/bigblackclocks (pushed via SSH -- key
already set up on this machine and on GitHub).
Fresh-install setup: run ./install.sh (installs every dependency,
places system files, compiles, enables services -- see that file for
the one thing it CAN'T automate: sourcing your own Eurostile Bold font).

STATUS FOR AI AGENTS -- read this block only, skip the rest unless you
need deep detail for actual debugging:
- PRIMARY UI is g510_app.py (PyQt5, one window, QTabWidget).
  - Backlight tab = DONE, confirmed working: color preset dropdown,
    brightness slider, Apply, Apply Defaults, Start, Restart Service.
  - G-Keys tab = DONE, mostly confirmed: 3-group physical-layout grid
    (2x3 per group), M1/M2/M3 profile buttons, record/save/clear per
    G-key via a QThread + python-evdev, playback via ydotool through
    g510_macro_daemon.py (separate systemd --user service, watches
    /dev/g510-keys, tracks live active profile). G1 record+replay
    under M1 CONFIRMED working by the user. Physical M1/M2/M3
    profile-switching is UNVERIFIED -- user reported pressing M2 didn't
    change behavior (G1 still played the M1 macro). Root cause not
    found yet -- PAUSED at the user's request, do not assume it works.
    Suspect: the KEY_MACRO_PRESET1/2/3 codes (691/692/693, from the
    upstream kernel driver source, never verified empirically on this
    exact keyboard) may not be what M1/M2/M3 actually send here --
    test_mkeys.py-style capture (see BUTTONS section pattern) is the
    next step, not a fix guess.
  - M1/M2/M3/MR hardware INDICATOR LEDS (separate from RGB backlight --
    g15::macro_preset1/2/3, g15::macro_record, on/off only) are wired
    in g510_macro_daemon.py's light_profile_led() but the udev
    permission rule for them hasn't taken effect yet (still root:root
    at last check, synthetic trigger didn't apply it, real replug
    wasn't tried). PAUSED at the user's request, low priority.
- g510-backlight-control.sh + g510-backlight-apply.sh (yad/bash) are the
  SUPERSEDED old UI, kept only as fallback reference -- do not present
  them as "the" interface anymore, g510_app.py is.
- PHASE 2, NOT STARTED: a "Custom Screen" tab in g510_app.py for
  placing text/PNG images on LCD screen 6 (reached by pressing L2,
  which currently just shows a placeholder "L2" test screen). The user
  EXPLICITLY wants this planned/confirmed with them BEFORE any code is
  written -- do not start building it unprompted. png-to-lcd.py (PNG ->
  raw XBM bitmap) and the g15r_drawXBM() render path are already
  built+verified working (rectangle test rendered correctly) and ready
  to reuse whenever Phase 2 actually starts.
- Everything else below (LCD stats screen, L1/L3-L5 buttons, media-key
  fixes, udev persistence, fonts) is DONE and confirmed working as of
  the last session -- only read further if something in one of those
  areas is actually broken.

(rest of this file: explains the WHY behind the non-obvious parts, for
whoever/whatever needs to actually debug something)

WHAT THIS IS
------------
Turns the Logitech G510s keyboard's built-in LCD into a live CPU/RAM/
VRAM/TEMP display, wires up the 5 buttons under the screen (L1-L5),
and adds RGB backlight control. Everything runs as your normal user
(no root needed at runtime), starts automatically at login, and
survives reboots/replugs/kernel updates.

FILES
-----
  g510_app.py               - PRIMARY UI (PyQt5). Phase 1 = Backlight
                              tab. Phase 2 (Custom Screen) goes here too,
                              add as a new tab, see STATUS block above.
  g510_lcd_stats.c          - draws the screen(s), the main program
  g510_lcd_buttons.c        - listens for L1-L5 presses
  png-to-lcd.py             - PNG -> raw XBM bitmap converter, verified
                              working, ready for Phase 2 to call
  g510-lcd-stats.service    - systemd --user unit for the above
  g510-lcd-buttons.service  - systemd --user unit for the above
  99-g510-lcd.rules         - udev rules (see PERSISTENCE below)
  fonts/lcd-label-8.fnt     - the label font, converted, actually used (see FONTS below)
  fonts/source-ttf/Eurostile_Bold.otf
                            - the original font lcd-label-8.fnt was converted
                              FROM (keep this -- you need it to reconvert at
                              a different size/gap; the .fnt alone can't be
                              edited, only regenerated from this source)
  set-backlight-color.sh    - applies the saved backlight color on boot
                              (auto-rewritten every time you click Apply
                              in the GUI -- don't hand-edit and expect it
                              to stick, the GUI owns this file now)
  g510-backlight-control.sh - SUPERSEDED by g510_app.py, kept as fallback
  g510-backlight-apply.sh   - SUPERSEDED by g510_app.py, kept as fallback
  rebuild.sh                - recompiles both programs, restarts services
  view-logs.sh              - tails both services' logs live
  start.sh                  - one-click start (used by the Desktop icon)

Desktop icons (in ~/Desktop, named "G510 LCD - ..."):
  App              - PRIMARY: launches g510_app.py
  Rebuild          - run after editing the .c files
  Start            - restarts both services (works whether stopped,
                     crashed, or just stuck/unresponsive)
  View Logs        - live log viewer
  Backlight Color  - SUPERSEDED by the App icon, kept as fallback
  Project Folder   - opens this folder in the file manager

HOW TO MAKE A CODE CHANGE
--------------------------
1. Edit g510_lcd_stats.c or g510_lcd_buttons.c
2. Double-click "G510 LCD - Rebuild" on the Desktop (or run ./rebuild.sh)
   -- this recompiles both and restarts the services for you.
3. If you touched pixel-drawing code, check the screen for garbage --
   see "THE PIXEL FORMAT" below before assuming it's a typo.

THE PIXEL FORMAT (the single most important thing to know)
------------------------------------------------------------
The LCD is 160x43, 1 bit per pixel. libg15render's canvas buffer stores
pixels ROW-MAJOR, MSB-first (pixel_offset = y*160+x). The physical LCD
hardware wants pixels in a different, VERTICAL "page" format (8 pixels
per byte, one byte per column, LSB = top pixel) -- this is the classic
SSD1306-style layout. dump_to_lcd_format() in g510_lcd_stats.c is a
byte-for-byte port of libg15's own dumpPixmapIntoLCDFormat() that does
this conversion. If you ever see garbled diagonal/streaky output
instead of clean text, you skipped this conversion somewhere -- do NOT
just memcpy canvas->buffer to the device, it will look like static.

The final wire format is a 992-byte HID report: byte 0 = 0x03 (the
report ID, discovered by reading libg15's source -- it's not documented
anywhere else), bytes 1-31 = padding/zero, bytes 32-991 = the converted
960 bytes of page-format pixel data.

WHY THIS DOESN'T USE g15daemon / libg15's own device code
-------------------------------------------------------------
g15daemon (the "standard" tool for this) grabs the keyboard's whole
extra-keys USB interface via libusb, detaching it from the kernel's
hid_lg_g15 driver, then re-emits key events through its OWN decoder --
which has the WRONG key table for a G510s specifically (a long-standing,
never-fixed bug in that 15+ year old project). This broke media/volume
keys HARD when tested live (confirmed: random garbage keystrokes).

Instead, this program writes directly to /dev/g510-lcd, a hidraw device
node -- hidraw lets you send/receive HID reports through a device the
kernel driver already owns, without detaching anything. The kernel's
normal key handling (hid_lg_g15) keeps working completely undisturbed.
This was verified repeatedly with the LCD screen running continuously
while actively using media keys -- zero interference either way.

MEDIA KEYS FIX (predates this project, but this is why it's safe to
touch this keyboard at all -- read before changing anything input-related)
-------------------------------------------------------------------------------
Three separate, unrelated problems were found and fixed on this exact
keyboard. None of them involve this LCD project's code, but breaking
any of them again is an easy mistake to make while experimenting:

1. Play/Pause is PHYSICALLY DEAD (corrosion/worn contact, confirmed via
   raw HID capture -- zero signal from that key even wet with contact
   cleaner, while every neighboring key on the same interface worked).
   Fixed with a udev hwdb remap: the Stop button's key sends the
   correct signal, so /etc/udev/hwdb.d/91-g510-stop-to-playpause.hwdb
   remaps its exact scan code (0x000c00b7, HID consumer-page "Stop")
   to KEY_PLAYPAUSE instead of KEY_STOPCD. You lose a hardware Stop
   button; you gain a working Play/Pause. If you ever want the real
   Stop function back, delete that hwdb file and re-run
   `sudo systemd-hwdb update`.

2. Brave's native media-key support and the "Plasma Integration" browser
   extension (id cimiefiiaegbelhefglklhhakcgmhkai) were BOTH registering
   as MPRIS players for the same tab, so KDE's media-key router got
   confused about which one to actually control. Fixed by disabling
   that extension's media-control feature (its `active_bit` should read
   `false` in Brave's Preferences JSON if you ever need to check).

3. The kernel driver, hid_lg_g15, is what actually reports all of this
   keyboard's keys correctly -- do NOT blacklist it (an earlier attempt
   to "fix" flaky media keys by forcing hid-generic instead turned out
   to be unnecessary once #1 and #2 above were found; hid_lg_g15 is
   also required for the Gaming Keys interface this LCD project's
   buttons depend on). Check `lsmod | grep hid_lg_g15` and
   `grep -rl lg_g15 /etc/modprobe.d/` (should be empty) if media keys
   or L1-L5 ever stop responding after a system change.

MULTI-SCREEN SYSTEM
--------------------
A single file, $XDG_RUNTIME_DIR/g510lcd_screen, holds one number:
  0 = the stats screen (CPU/TEMP/VRAM/RAM, in that vertical order)
  1 = a clock
  2-5 = "L2".."L5" test screens (see BUTTONS below)
g510_lcd_stats.c re-reads this file every loop iteration (~1-2s) and
draws whichever screen it says. g510_lcd_buttons.c is the only thing
that ever WRITES to this file. To add a new screen: write a new
draw_XXX_screen() function, add a branch for its number in main()'s
loop, and make some button set that number in g510_lcd_buttons.c.

BUTTONS (L1-L5)
----------------
Real, standard Linux keycodes -- no HID remapping was needed, unlike
the media keys (see MEDIA KEYS FIX above for that story). Confirmed by
testing each button individually:
  L1 = 696 (KEY_KBD_LCD_MENU1) -- cycles: stats -> clock -> stats...
       (if currently on an L2-L5 test screen, L1 returns to stats)
  L2 = 697 (KEY_KBD_LCD_MENU2) -- shows "L2" on screen (test/placeholder)
  L3 = 698, L4 = 699, L5 = 700 -- same pattern
These switches BOUNCE (one physical press can fire 2-4 raw events) --
g510_lcd_buttons.c has a 400ms debounce per key, don't remove it.
L2-L5 currently do nothing but confirm the press -- to actually program
them, edit the `else` branch in g510_lcd_buttons.c's main loop (the one
that currently just calls write_screen()+log_button()).

FONTS
------
The library ships default-00 through default-39.fnt, but they're all
the SAME typeface at different sizes -- not actually different fonts.
For anything else, use `g15fontconvert -i font.ttf -o out.fnt -s N -g 1`
(the AUR `libg15render` package; -s is NOT literal pixel height, it's
closer to a point size -- check the ACTUAL resulting height with:
  python3 -c "import struct; print(struct.unpack('<H', open('FILE.fnt','rb').read()[4:6])[0])"
and adjust -s up/down until it matches what you want (our 10px row
spacing needs a font around 8-9px tall).

IMPORTANT: thin/regular-weight fonts render GARBLED at this tiny size
(confirmed multiple times) -- there simply aren't enough pixels for
fine strokes. Use Bold or Black weights only. Current setup: labels
use Eurostile Bold (fonts/source-ttf has the .otf, matches the G510's
original stock LCD font style), numbers use the library's own built-in
G15_TEXT_SMALL font (also tried several converted fonts for numbers --
all looked worse than the built-in one, which was purpose-built for
this exact resolution).

.otb/.pcf bitmap fonts (like Terminus) do NOT work with g15fontconvert
-- it silently produces an empty/broken .fnt (font_height stuck at one
value regardless of -s, near-zero file size). Only scalable TTF/OTF
outline fonts convert correctly.

BACKLIGHT (RGB keyboard glow)
-------------------------------
This is a REAL Linux kernel LED device, nothing hidraw/USB-custom about
it: /sys/class/leds/g15::kbd_backlight/ -- `brightness` (0-255) and
`multi_intensity` ("R G B" space-separated, 0-255 each). KDE's own
"Keyboard Colour: Follow accent colour" toggle fights over this same
file -- turn that OFF in System Settings > Brightness & Color if you
want manual control to actually stick.
Applied automatically on boot/replug by set-backlight-color.sh via the
udev rule. Use the "Backlight Color" Desktop icon to change it -- a
proper combined GUI (yad form: color preset dropdown + brightness
slider + Apply + Apply Defaults, all in one window, no sudo prompt).
Whenever you click Apply, g510-backlight-apply.sh REWRITES
set-backlight-color.sh with your new choice -- so whatever you pick
becomes the new permanent boot default automatically, not just a
one-time live change. "Apply Defaults" resets to Blue-Violet/full
brightness (110 0 255) without touching the dropdown/slider state, and
also persists that choice.
Note: combining yad's live CLR color-picker widget with an SCL slider
in one form CRASHES on this system (confirmed GTK bug) -- that's why
this uses a preset-color dropdown (CB) instead of a free-form picker.
Add more presets by editing the COLOR_RGB array at the top of both
g510-backlight-control.sh and g510-backlight-apply.sh (keep them in
sync -- yes, this is duplicated, a shared config file would be cleaner
if you ever want to refactor it).

PERSISTENCE (why this survives reboots/updates)
--------------------------------------------------
99-g510-lcd.rules (installed at /etc/udev/rules.d/) does three things:
1. Creates /dev/g510-lcd, a stable symlink to whatever hidraw number
   the LCD's USB interface gets THIS boot (it changes across
   reboots/replugs, don't hardcode a hidrawN number anywhere).
2. Creates /dev/g510-keys the same way, for the Gaming Keys input device.
3. On the backlight LED appearing, chmod/chgrp's it to group "input"
   (so no sudo is needed at runtime) and runs set-backlight-color.sh.
The two systemd --user services are `enable`d, so they autostart at
every login. hid_lg_g15 (the kernel driver all of this depends on) is
a mainline upstream driver, ships in every Manjaro kernel package --
nothing here is tied to today's specific kernel version.

GOTCHA WE ACTUALLY HIT (keep this in mind if things break weirdly)
-----------------------------------------------------------------------
A test script once ran fopen("/dev/hidrawN", "wb") at the exact moment
the real device briefly didn't exist during re-enumeration -- this
silently created a REGULAR FILE named hidrawN in /dev instead of
erroring, which then permanently blocked the kernel from recreating the
real character device at that path. Symptom: permissions look right
but writes still fail, or udev rules seem to apply then "un-apply".
Fix: `stat /dev/hidrawN` -- if it says "regular file" instead of
"character special file", `sudo rm` it and replug the keyboard.

UDEV RULE GOTCHA (if you ever add another rule)
--------------------------------------------------
Don't mix ATTRS{} from two different ancestor devices in one rule line
(e.g. ATTRS{idVendor} lives on the USB device, ATTRS{bInterfaceNumber}
lives on the USB interface, a different level) -- once udev matches one
ATTRS{} against a device, it locks onto that SAME device for the rest
of the rule's ATTRS{} checks, silently failing to match. Use ENV{} for
properties instead where possible (ENV{ID_VENDOR_ID}, ENV{ID_MODEL_ID},
ENV{ID_USB_INTERFACE_NUM} are all already resolved onto the device you
actually want to match, no ancestor-walking involved) -- this is what
the hidraw rule does and it's reliable.
