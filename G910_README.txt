G910 Orion Spectrum Control App -- Planning Notes
==================================================
Branch: g910-macros (started as an untouched copy of `main`, the G510s
LCD app -- diverging from here). This file documents the G910 project
specifically; README.txt in this same repo is the G510s LCD project's
docs and describes different hardware -- don't conflate the two.

STATUS FOR AI AGENTS -- read this block first:

PLANNING PHASE. NO APP CODE WRITTEN YET. Do not start implementation
until the user explicitly signs off on the finalized plan below --
they have said this multiple times and it matters to them. A deep
research pass (covering backend package health, alternative all-in-one
tools, and a hidraw-vs-exclusive-USB-claim question) was dispatched as
a background agent and had not yet reported back as of this writing --
check with the user/session for its results before treating anything
marked "TENTATIVE" below as final.

WHAT THIS IS SUPPOSED TO BECOME
--------------------------------
Same kind of app as g510_app.py (PyQt5, one window, QTabWidget,
tab-per-feature) but for a Logitech G910 Orion Spectrum keyboard
instead of a G510s. Two tabs only, no LCD tab (G910 has no screen):
  - Backlight/RGB tab: per-key color, brightness, effects (breathing/
    wave/cycle).
  - G-Keys tab: G1-G9 macro record/playback (keystroke combo or shell
    command), switchable via M1/M2/M3 profiles, reusing g510_app.py's
    RecorderThread/MacroRecordDialog pattern. MR key = a literal
    macro-record toggle (the user explicitly chose this over treating
    MR as a 4th M-profile, which is what one of the reference projects
    below does by default).

HARDWARE FACTS -- CONFIRMED EMPIRICALLY on ac130arch (2026-09-13)
--------------------------------------------------------------------
Do NOT re-derive these, they were checked directly on the real device,
not assumed:
- USB ID 046d:c335, lsusb identifies it as "G910 Orion Spectrum
  Mechanical Gaming Keyboard".
- Kernel driver bound: plain `usbhid` / `hid-generic` -- NOT
  `hid_lg_g15` like the G510s. This machine has no special in-kernel
  driver for this device at all.
- Two USB interfaces, each with its own hidraw node (confirmed via
  /dev/input/by-id symlinks and each hidraw's uevent HID_PHYS field):
    hidraw0 = interface 0 (paired with evdev event2, has EV_LED bits --
      the caps/num/scroll-lock-style interface)
    hidraw1 = interface 1 (paired with evdev event3)
- evdev capture confirmed EMPTY for G-keys: ran a live 90-second
  python-evdev listener on both event2 and event3 while attempting to
  press G-keys/M-keys/MR -- zero relevant events. Unlike the G510s's
  L1-L5 buttons (which ARE plain Linux keycodes, KEY_KBD_LCD_MENU1..5),
  this keyboard's G-keys/M-keys/MR do NOT show up as normal Linux
  keycodes at all. They must be read as raw vendor-specific HID++ 2.0
  reports via hidraw (or libusb) -- confirmed necessary, not assumed.
- No /sys/class/leds/ entry for this device beyond the standard
  input209/input211/... capslock/numlock/scrolllock LEDs every keyboard
  gets. Confirmed there is NO simple LED-class sysfs backlight
  mechanism like the G510s's /sys/class/leds/g15::kbd_backlight/ --
  RGB control needs a real HID++ 2.0-speaking tool, not a sysfs write.
- python-evdev already installed and importable on this machine.
  PyQt5 usage is already proven via the sibling g510_app.py.
- `yay` is available as the AUR helper.

GITHUB ACCESS -- SET UP 2026-09-13
------------------------------------
This machine (ac130arch) did NOT have GitHub SSH access before this
project -- the only existing key (~/.ssh/id_ed25519, comment
"ac130arch-to-tria") is for the separate Arch-to-Arch cross-machine
bridge to AC130Tria, not GitHub, and was never registered on GitHub.
Fixed by generating a SEPARATE dedicated key:
  ~/.ssh/id_ed25519_github (public half added to the user's GitHub
  account by the user themselves)
  ~/.ssh/config now has:
    Host github.com
        IdentityFile ~/.ssh/id_ed25519_github
Verified working: `ssh -T git@github.com` returns "Hi grumpybollocks!
You've successfully authenticated". Don't recreate this key or config
-- it's done.

DECISIONS -- FINALIZED after a deep research pass (2026-09-13)
-------------------------------------------------------------------
- MR key = literal macro-record toggle. CONFIRMED user decision.
- SUPERSEDED: the earlier lean toward `g810-led` for the Backlight tab
  is WRONG and must not be used -- confirmed via the AUR RPC API that
  both `g810-led` and `g810-led-git` have been REMOVED from AUR
  (resultcount:0 for both names as of 2026-09-13). `yay -S
  g810-led-git` would fail on a fresh install. Do not resurrect this
  plan without re-checking AUR first.
- FINAL BACKEND for BOTH tabs: `keyleds` (plain AUR package name, NOT
  `keyleds-git` -- that's the original upstream, abandoned since 2021).
  The correct package is maintained by `ticpu` (co-maintained by the
  original author `spectras` + `jtyr`), points at
  github.com/ticpu/keyleds, confirmed NOT archived and last pushed
  2026-09-08 (5 days before this was checked) -- a live, actively
  maintained project. One tool covers both the Backlight tab (per-key
  RGB) and the G-Keys tab (G-key/M-key event source) instead of
  stitching together two separate dependencies.
  - Explicitly lists G410/G513/G610/G810/G910/GPro support, ships a
    `keyledsctl` CLI, a DBUS interface, and a `python/keyleds.pyx`
    Cython binding directory (a real Python API MAY be usable directly
    -- unconfirmed whether it builds automatically with the main
    package, see unknowns below).
  - Its shipped `logitech.rules` udev file uses `uaccess` tagging
    (systemd-logind seat-based access) on hidraw nodes restricted to
    `bInterfaceProtocol=="00"` and on `ID_INPUT_KEY`-tagged event
    nodes -- confirmed it does NOT use libusb's
    detach_kernel_driver() anywhere. Same non-exclusive-claim
    philosophy this repo's G510s project already validated. No custom
    udev rule needs to be hand-written -- the AUR package installs its
    own, and no runtime root/sudo is needed once installed.
  - REAL, NOT HYPOTHETICAL CAVEAT: keyleds' own GitHub issues (#17,
    #36, #57) show mixed real-world results from other G910 owners --
    one report of the device not being detected at all, another of
    individual zone names ("logo", "light") not working even though
    broader effects do. These may predate ticpu's fork improvements,
    but this is NOT confirmed clean -- treat as a real risk to verify
    on this actual keyboard, not swept under the rug.
- RULED OUT, with reasons (don't re-litigate without new evidence):
  - OpenRGB: confirmed zone-only control for G910 per its own wiki
    (established before this research pass).
  - logiops/logid (AUR `logiops`, otherwise a healthy 29-vote
    package): its own TESTED.md lists 17 devices, all MX-series
    mice/keyboards -- zero G-series, zero "Orion", zero G910.
    Definitively does not support this keyboard.
  - LogiGSK: Java-based, LED-only (no G-key support at all), unusual
    heavier toolchain (Apache Ant + `alien` .deb/.rpm conversion), no
    evidence of recent activity. Not worth it next to keyleds.
  - gkeybind: built on top of keyleds itself, plus needs the Crystal
    language toolchain just to build. Unnecessary extra layer since
    keyleds already exposes G-key events and we're building our own
    PyQt5 macro UI, not reusing gkeybind's separate keybinding engine.
  - aquova/g910-macros (Rust, uinput-remap-only): superseded by
    keyleds' more complete feature set -- would still need something
    else bolted on for actual macro/profile logic.
- KEPT AS FALLBACK REFERENCE ONLY (not the primary plan): JSubelj's
  g910-gkey-macro-support. Its actual usb_device.py source was
  directly verified: detach_kernel_driver() targets INTERFACE 1 ONLY
  (never interface 0, normal typing stays untouched) -- so the
  "hogging" risk is smaller than first assumed. Real, working,
  forum-confirmed option to fall back to if keyleds' G910 G-key
  support turns out incomplete on real hardware.

FINAL DEPENDENCY LIST (from real AUR RPC data, not guessed)
----------------------------------------------------------------
`keyleds` AUR package Depends: libevdev, libuv, libx11, libxi,
libyaml, luajit, systemd-libs. MakeDepends: cmake. License GPL-3.0.
All ordinary Arch extra/core packages, no exotic transitive AUR chain.

ONE-SHOT INSTALL COMMAND (paste once, nothing else needed)
----------------------------------------------------------------
sudo pacman -S --needed base-devel git cmake libevdev libuv libx11 libxi libyaml luajit systemd-libs python-pyqt5 python-evdev python-dbus && \
yay -S --needed keyleds

(base-devel/git/cmake = AUR build tooling; the rest are keyleds's own
Depends, pre-installed via pacman so yay won't prompt mid-build.
python-pyqt5/python-evdev already proven via the G510s app. python-dbus
included in case the G910 app ends up talking to keyledsd over DBUS
rather than its Cython bindings. yay -S keyleds compiles from source
via cmake -- expect a short wait, not instant. No reboot needed; the
udev rule takes effect on replug, or `sudo udevadm control --reload`
+ replug if it doesn't pick up live.)

INSTALL CONFIRMED (2026-09-13)
----------------------------------
User ran the one-shot install command. Verified via `pacman -Qi
keyleds`: version 1.2.0-1, all Depends satisfied, installed cleanly.
Binaries present: /usr/bin/keyledsctl, /usr/bin/keyledsd. Confirmed
`keyledsctl list` detects the real hardware:
  /dev/hidraw1 046d:c335 [096239583837]   <- the G910
  /dev/hidraw4 046d:c332 [1062376D3633]   <- the G502 mouse, also HID++
`keyledsctl info -d /dev/hidraw1` output (real, not summarized):
  Name: G910 Orion Spectrum, Model: c33500000000, Serial: 33394709
  Known features: ... gamemode name layout2 gkeys mkeys mrkeys
    reportrate dfu-control leds led-effects
  G-keys: 9
  LED block[01]: 105 keys, max_rgb(255,255,255)  <- main keys, TRUE
    per-key RGB, all 105 keys individually addressable (NOT zone-only
    -- this is real confirmation the earlier OpenRGB-vs-keyleds
    reasoning was correct)
  LED block[02]:   5 keys, max_rgb(1,0,0)        <- red-only indicator
    LEDs, almost certainly M1/M2/M3/MR/gamemode
  LED block[04]:   9 keys, max_rgb(255,255,255)  <- G-keys' own
    individual backlighting, full RGB
  LED block[10]:   2 keys, max_rgb(255,255,255)  <- logo/media, guess
    not yet confirmed

G-KEY/M-KEY/MR PROTOCOL -- FULLY CONFIRMED VIA REAL RAW CAPTURE
--------------------------------------------------------------------
This was the single biggest open unknown and it is now COMPLETELY
resolved, not guessed. Method: a small non-exclusive hidraw reader
(os.open/os.read, no libusb, no detach_kernel_driver -- same low-risk
approach as the G510s project) was run against /dev/hidraw1 while the
user physically pressed G1 through G9, then M1-M3, then MR, in that
exact order, one at a time. Every single press/release produced a
clean, unambiguous 20-byte report. Full results:

  G1: 11 ff 08 00 01 00 00...   (press) / 11 ff 08 00 00 00... (release)
  G2: 11 ff 08 00 02 00 00...
  G3: 11 ff 08 00 04 00 00...
  G4: 11 ff 08 00 08 00 00...
  G5: 11 ff 08 00 10 00 00...
  G6: 11 ff 08 00 20 00 00...
  G7: 11 ff 08 00 40 00 00...
  G8: 11 ff 08 00 80 00 00...
  G9: 11 ff 08 00 00 01 00...   <- spills into byte 5, bit 0 (9th key,
                                    can't fit in the byte4 bitmask with
                                    G1-G8)
  M1: 11 ff 09 00 01 00 00...
  M2: 11 ff 09 00 02 00 00...
  M3: 11 ff 09 00 04 00 00...
  MR: 11 ff 0a 00 01 00 00...   <- CONFIRMED a genuinely distinct event
                                    (report type 0x0a), not just a 4th
                                    M-profile -- directly supports the
                                    user's requested "literal
                                    macro-record toggle" design, no
                                    workaround needed.

Report structure: byte0=0x11, byte1=0xff (standard HID++ 2.0 "long
report" prefix), byte2=event type (0x08=gkeys, 0x09=mkeys,
0x0a=mrkeys), byte3=always 0x00 (reserved, confirmed constant across
every single capture), byte4(+byte5 for G9 only)=bitmask, one bit per
key in that group, set on press. Release = the exact same report shape
with the bitmask zeroed (confirmed on every single key, no exceptions).
20 bytes total per report.

CRITICAL SETUP STEP, don't skip: by default the G910's G-keys act as
plain F13-F21 passthrough (per aquova/g910-macros' and JSubelj's
projects, matches what we saw too) and DO NOT emit these HID++ reports
at all -- confirmed empirically: an earlier capture attempt with zero
setup produced ZERO bytes on hidraw1 despite real key presses. The fix:
  keyledsctl gkeys -d /dev/hidraw1 on
run once, after which every press produced clean reports immediately
and repeatably across multiple separate test runs. This command must
run at daemon startup (systemd service ExecStartPre, or first line of
the daemon itself) every time, since it's a live device-mode toggle,
not a persisted setting.

ARCHITECTURE REVISION based on this confirmed data
-------------------------------------------------------
Since the exact report format is now fully known and verified, the
G-Keys tab does NOT need keyledsd (the background daemon) running at
all -- and there's good reason to avoid it: keyledsd has its own real,
observed bug on this exact machine (see BUGS FOUND below) and its
Lua-plugin/effect discovery mechanism was fought with for a while
without success (custom .lua effects placed via -m and in an effects/
subdirectory were never found -- "no module <keytest> in search
paths" -- root cause not resolved, not worth chasing further since we
don't need it).
Revised plan:
  - G-Keys tab: our own small Python daemon reads /dev/hidraw1 directly
    (hidraw_sniff.py in this session's scratchpad is a working proof of
    concept for the read loop -- same pattern, not literally reused
    verbatim, will become g910_macro_daemon.py mirroring
    g510_macro_daemon.py's structure), sends `keyledsctl gkeys -d
    /dev/hidraw1 on` once at startup, decodes the confirmed byte
    format above, and drives macro playback/M-profile switching/MR
    record-toggle directly -- no keyleds daemon in the loop for this
    part at all.
  - Backlight tab: still uses `keyledsctl` (the CLI, shelled out to,
    not the Python binding -- see BUGS FOUND below for why) for
    `set-leds`/`get-leds` per-key color commands against LED block 01
    (confirmed 105 keys, true per-key RGB) and possibly block 04 (the
    G-keys' own backlighting) as a secondary control.
  - `keyleds` package stays installed for its `keyledsctl` binary and
    udev rule (uaccess tagging -- confirmed this is what allows
    non-root reads of hidraw1 at all). The `keyledsd` background
    service itself is NOT needed and should not be enabled/autostarted
    for this project.

BUGS FOUND while testing keyledsd directly (real, observed, not
hypothetical -- keep in mind if keyledsd is ever reconsidered):
1. `could not load layout <c33500000000_0037.yaml>: No such file or
   directory` -- logged on every single keyledsd startup against this
   exact keyboard. The package only ships layout files for this model
   suffixed 0001-0005,0007,0008,000a,000b -- 0037 (this unit's actual
   firmware/region variant) isn't among them. keyledsd silently falls
   back to loading a DIFFERENT KEYBOARD MODEL's layout entirely
   (c32b00000000_0002.yaml, model c32b -- not c335) rather than erroring
   out. If keyledsd's own key-name resolution is ever relied upon, key
   names could be silently wrong. Not a blocker for the revised
   architecture above since we bypass keyledsd's layout system
   entirely, but worth knowing if this project ever revisits it.
2. Custom Lua effects (the `-m <path>` / effects/ subdirectory
   mechanism documented in the sample config) could not be gotten
   working in this session -- consistently "no module <name> in search
   paths" regardless of directory placement. Not investigated further
   since the revised architecture doesn't need it, but don't assume
   custom Lua effects "just work" per the docs without re-verifying.

RESOLVED UNKNOWNS from the previous research pass:
  1. RGB granularity: CONFIRMED true per-key (105 keys, full RGB) --
     see LED block 01 above.
  2. G-key/M-key/MR event delivery: CONFIRMED via direct hidraw read,
     full byte-level mapping captured -- see protocol table above.
  3. MR as distinct event: CONFIRMED (report type 0x0a, separate from
     M1-M3's 0x09) -- supports the literal record-toggle design as-is.
  4. python/keyleds.pyx Cython binding: NOT NEEDED given the
     architecture revision above (we shell out to keyledsctl and read
     hidraw directly instead) -- no longer a blocking unknown.
  5. Session compatibility (X11/Wayland): moot given the architecture
     revision -- we're not using keyledsd's X-focus-based profile
     switching, so this doesn't affect the plan either way.

NEXT STEPS (in order)
------------------------
1. Write g910_app.py (Backlight tab using `keyledsctl set-leds`/
   `get-leds`, then G-Keys tab), reusing g510_app.py's
   RecorderThread/MacroRecordDialog pattern for macro recording.
2. Write g910_macro_daemon.py: reads /dev/hidraw1 directly using the
   now-fully-confirmed report format above, runs `keyledsctl gkeys -d
   /dev/hidraw1 on` at startup, dispatches G1-G9 macros (filtered by
   active M1/M2/M3 profile), and treats MR as a literal record-toggle
   event per the user's decision.
3. Write the systemd --user service mirroring
   g510-macro-daemon.service's pattern (no udev rule needed, keyleds
   already installed one that grants non-root hidraw1 access).
4. Test on real hardware, iterate with the user before calling
   anything "done" (per this whole repo's established standard: don't
   claim something works without it being physically confirmed by the
   user on the actual device).
