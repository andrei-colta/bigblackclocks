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

WHAT'S EXPLICITLY *NOT* DONE YET
-----------------------------------
- No dependencies installed yet -- the install command above has been
  written and verified against real AUR data, but not yet run.
- No custom udev rule needs to be written (keyleds ships its own,
  uaccess-based -- confirmed above). Nothing to author here, just
  install the package.
- No hidraw capture of real G-key/M-key/MR byte sequences has been run
  yet on this actual keyboard. Whether keyleds itself reports these
  presses (and through which channel -- DBUS, keyledsctl, or the
  Cython binding) is UNCONFIRMED, see unknowns below.
- No g910_app.py file exists yet. No systemd service files for a G910
  macro daemon exist yet.
- Nothing has been installed, compiled, or run against the real
  keyboard beyond read-only USB/evdev/sysfs inspection.

REMAINING UNKNOWNS -- MUST be verified on the real keyboard, not
assumed (per this project's strict no-guessing rule):
------------------------------------------------------------------
1. Whether keyledsd actually detects and controls THIS exact G910
   unit's RGB with real per-key granularity (GitHub issues show mixed
   results from other G910 owners -- #17: zone names like "logo"/
   "light" don't work; #36: device not found for one user). Test with
   `keyledsctl list-devices` and real key-color commands once
   installed.
2. Whether keyleds reports G-key/M-key/MR presses at all, and through
   which channel (DBUS signal vs `keyledsctl` output vs the
   `python/keyleds.pyx` binding) -- especially notable since our own
   90-second live evdev capture on event2/event3 found ZERO G-key
   activity, so this needs direct confirmation, not assumption from
   the README.
3. Whether MR shows up as its own distinct event (vs. only M1-M3 being
   documented in most third-party tools) -- needed for the user's
   requested "literal macro-record toggle" behavior.
4. Whether the `python/keyleds.pyx` Cython binding builds automatically
   with the main cmake build, or needs a separate build step -- affects
   whether g910_app.py can `import keyleds` directly or must shell out
   to `keyledsctl` / use DBUS instead.
5. Session compatibility -- confirm this machine's Plasma session type
   (X11 vs Wayland) since ticpu's fork advertises added Wayland support
   as an improvement over the abandoned original; should confirm this
   isn't moot before assuming it matters either way.
If keyleds' G910 G-key support turns out incomplete on real hardware,
fall back to adapting JSubelj/g910-gkey-macro-support (interface-1-only
detach, confirmed low risk -- see DECISIONS above) rather than
abandoning the whole plan.

NEXT STEPS (in order)
------------------------
1. Present the finalized plan to the user, get explicit sign-off.
   (Research pass complete as of 2026-09-13 -- see DECISIONS above.)
2. Run the ONE-SHOT INSTALL COMMAND above (user pastes it once).
3. Verify unknowns 1-5 above against the real keyboard -- especially
   whether keyleds actually reports G-key presses, before writing any
   daemon logic against an assumed report format.
4. Write g910_app.py (Backlight tab, then G-Keys tab), reusing
   g510_app.py's RecorderThread/MacroRecordDialog pattern for macro
   recording.
5. Write the macro daemon + systemd --user service, mirroring
   g510_macro_daemon.py / g510-macro-daemon.service patterns from the
   sibling project (no udev rule needed this time, keyleds ships one).
6. Test on real hardware, iterate with the user before calling
   anything "done" (per this whole repo's established standard: don't
   claim something works without it being physically confirmed by the
   user on the actual device).
