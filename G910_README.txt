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

DECISIONS MADE SO FAR (some TENTATIVE, pending the research pass above)
--------------------------------------------------------------------------
- MR key = literal macro-record toggle. CONFIRMED user decision, not
  tentative -- don't revisit without the user raising it again.
- Backlight tab backend: TENTATIVE lean toward `g810-led` (AUR
  g810-led-git, the MatMoul fork) over OpenRGB. Reasoning so far: the
  official OpenRGB wiki documents only ZONE-level control for the
  G910, not true per-key, while g810-led's own CLI (`g810-led -k <key>
  <color>`) demonstrates real per-key control, and an Arch Linux forum
  thread from someone with this exact keyboard recommends g810-led
  specifically for LEDs. NOT yet verified: whether g810-led-git's
  actual source device table lists PID c335 (Orion Spectrum) explicitly
  vs. only sibling models, whether the AUR package is actively
  maintained / builds cleanly, and whether a simpler single-tool
  alternative (keyleds -- claims to do BOTH per-key RGB AND G-key
  events in one daemon) should replace this entirely. The dispatched
  research pass is checking all of this.
- G-Keys tab backend: TENTATIVE lean toward adapting
  github.com/JSubelj/g910-gkey-macro-support's HID-report-reading
  logic (the same forum thread's recommended dedicated G-key driver
  for this exact keyboard -- built because nothing else existed).
  CONCERN, not yet resolved: that project uses pyusb's
  detach_kernel_driver() to EXCLUSIVELY claim a USB interface -- the
  exact antipattern that broke media keys on the G510s sibling project
  (g15daemon exclusively detaching the keyboard's extra-keys
  interface). The research pass is checking whether a non-exclusive
  hidraw read (matching this repo's established G510s philosophy: use
  hidraw, never detach the kernel driver) can see the same G-key
  reports, and whether JSubelj's exclusive claim is actually scoped
  narrowly enough (interface 1 only, leaving normal typing on
  interface 0 undisturbed) to be low-risk even if hidraw doesn't work.
- Other candidates surfaced but not yet fully evaluated: logiops/logid
  (G910 support status still unconfirmed), gkeybind, aquova/g910-macros
  (Rust, lighter-weight uinput remap approach, no built-in macro/
  profile logic of its own), "LogiGSK" (mentioned once in a forum
  thread, not yet investigated at all).

WHAT'S EXPLICITLY *NOT* DONE YET
-----------------------------------
- No dependencies installed (not even g810-led -- only searched for,
  never `yay -S`'d).
- No udev rules written for the G910 (the G510s's 99-g510-lcd.rules
  pattern -- ENV{} matching + chgrp/chmod to group "input" -- is the
  template to reuse once the final tool choice is locked in, so no
  sudo is needed at runtime, matching this repo's whole philosophy).
- No hidraw capture of real G-key/M-key/MR byte sequences has been run
  yet on this actual keyboard. JSubelj's project hints at report
  shapes like [0x11, 0xff, 0x08, ...] for G-keys, but per this
  project's strict no-guessing rule, those are a hypothesis to verify
  empirically on THIS unit, not a fact to code against directly.
- No g910_app.py file exists yet. No systemd service files for a G910
  macro daemon exist yet.
- Nothing has been installed, compiled, or run against the real
  keyboard beyond read-only USB/evdev/sysfs inspection.

NEXT STEPS (in order)
------------------------
1. Finish the in-flight research pass (backend package health check,
   keyleds-as-single-tool evaluation, hidraw-vs-exclusive-claim
   answer, exact dependency list, one consolidated install command).
2. Present the finalized plan to the user, get explicit sign-off.
3. Install dependencies (single install command, so the user -- who
   does not code and wants minimal manual sudo steps -- can paste it
   once).
4. Empirically capture real hidraw G-key/M-key/MR byte sequences on
   this actual keyboard (the user pressing each key on request) --
   confirm or correct the hypothesized report structure before writing
   any daemon logic against it.
5. Write g910_app.py (Backlight tab, then G-Keys tab), reusing
   g510_app.py's RecorderThread/MacroRecordDialog pattern for macro
   recording.
6. Write the macro daemon + systemd --user service + udev rule,
   mirroring g510_macro_daemon.py / g510-macro-daemon.service /
   99-g510-lcd.rules patterns from the sibling project.
7. Test on real hardware, iterate with the user before calling
   anything "done" (per this whole repo's established standard: don't
   claim something works without it being physically confirmed by the
   user on the actual device).
