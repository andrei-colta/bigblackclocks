#!/bin/bash
# Standalone keyboard backlight color/brightness control for the G510s.
# No sudo needed -- the udev rule grants the 'input' group write access
# to these two sysfs files.
#
# Uses a color PRESET dropdown instead of yad's live color-picker (CLR)
# widget: combining CLR+SCL in one yad form crashes on this system
# (confirmed - GTK bug in this yad/GTK combo). CB (combo-box) + SCL
# together is stable.
#
# Apply/Apply Defaults are FORM FIELDS (BTN type), not bottom --buttons --
# clicking them runs a command via %N field substitution WITHOUT closing
# the dialog. Only "Close" (a real --button) exits.
LED=/sys/class/leds/g15::kbd_backlight
DIR="$(dirname "$0")"
APPLY="$DIR/g510-backlight-apply.sh"

declare -A COLOR_RGB=(
    ["Blue-Violet"]="110 0 255"
    ["Red"]="255 0 0"
    ["Green"]="0 255 0"
    ["Blue"]="0 0 255"
    ["Purple"]="128 0 128"
    ["Cyan"]="0 255 255"
    ["Orange"]="255 100 0"
    ["Pink"]="255 0 150"
    ["White"]="255 255 255"
)
ORDER=("Blue-Violet" "Red" "Green" "Blue" "Purple" "Cyan" "Orange" "Pink" "White")

CUR_RGB=$(cat "$LED/multi_intensity")
CUR_BRIGHT=$(cat "$LED/brightness")
CUR_SCALE=$(( CUR_BRIGHT * 100 / 255 ))

# Build the dropdown list with whatever color is CURRENTLY active marked
# as the default selection (not always Blue-Violet).
LIST=""
for name in "${ORDER[@]}"; do
    if [ "${COLOR_RGB[$name]}" = "$CUR_RGB" ]; then
        LIST="${LIST}^${name}!"
    else
        LIST="${LIST}${name}!"
    fi
done
LIST="${LIST%!}"

yad --form --title="G510 Keyboard Backlight" \
    --text="<b>Keyboard Backlight</b>\nPick a color and brightness, then Apply." \
    --window-icon=preferences-desktop-color \
    --width=420 --height=220 \
    --field="Color:CB" "$LIST" \
    --field="Brightness (0-100):SCL" "$CUR_SCALE" \
    --field="Apply:BTN" "bash -c '\"$APPLY\" \"%1\" \"%2\"'" \
    --field="Apply Defaults:BTN" "bash -c '\"$APPLY\" \"Blue-Violet\" \"100\"'" \
    --field="Restart Service:BTN" "systemctl --user restart g510-lcd-stats.service g510-lcd-buttons.service" \
    --button="Close:1"
