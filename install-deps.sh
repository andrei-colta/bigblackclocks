#!/bin/bash
# Dependencies for the yad backlight control tool. Run from inside this
# folder: ./install-deps.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=== Installing yad ==="
sudo pacman -S --needed --noconfirm yad

echo "=== Installing udev rule (grants your user write access to the"
echo "    keyboard's backlight LED, no sudo needed at runtime) ==="
sudo cp 99-backlight-led.rules /etc/udev/rules.d/99-backlight-led.rules
sudo udevadm control --reload-rules
echo "NOTE: unplug and replug the keyboard now so this fully applies."
read -p "Press Enter once you've replugged the keyboard..."

chmod +x g510-backlight-control.sh g510-backlight-apply.sh set-backlight-color.sh

echo ""
echo "Done. Run ./g510-backlight-control.sh to open the tool."
