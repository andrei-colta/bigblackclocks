#!/bin/bash
# Helper invoked by the Apply button inside g510-backlight-control.sh.
# Args: <color name> <brightness 0-100>
LED=/sys/class/leds/g15::kbd_backlight

case "$1" in
    "Blue-Violet") RGB="110 0 255" ;;
    "Red")         RGB="255 0 0" ;;
    "Green")       RGB="0 255 0" ;;
    "Blue")        RGB="0 0 255" ;;
    "Purple")      RGB="128 0 128" ;;
    "Cyan")        RGB="0 255 255" ;;
    "Orange")      RGB="255 100 0" ;;
    "Pink")        RGB="255 0 150" ;;
    "White")       RGB="255 255 255" ;;
    *) RGB="" ;;
esac

[ -n "$RGB" ] && echo "$RGB" > "$LED/multi_intensity"

BRIGHT_VAL=$(( $2 * 255 / 100 ))
echo "$BRIGHT_VAL" > "$LED/brightness"

# Also make this the new permanent boot-time default (this file is
# owned by you, not root -- rewriting it needs no sudo). Without this,
# a reboot/replug would revert to whatever was set here previously.
if [ -n "$RGB" ]; then
    DEFAULTS_SCRIPT="$(dirname "$0")/set-backlight-color.sh"
    cat > "$DEFAULTS_SCRIPT" << EOF
#!/bin/bash
# Applies the chosen keyboard backlight color. Run automatically by
# 99-g510-lcd.rules whenever the LED device appears (boot or replug).
# Auto-updated by g510-backlight-apply.sh every time you click Apply.
echo $BRIGHT_VAL > /sys/class/leds/g15::kbd_backlight/brightness
echo "$RGB" > /sys/class/leds/g15::kbd_backlight/multi_intensity
EOF
    chmod +x "$DEFAULTS_SCRIPT"
fi
