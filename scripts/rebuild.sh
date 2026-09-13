#!/bin/bash
# Rebuilds both G510 LCD programs and restarts their services.
# Run this after editing g510_lcd_stats.c or g510_lcd_buttons.c.
set -e
cd "$(dirname "$0")/../src"

echo "Building g510_lcd_stats..."
# Needs the same FreeType/TTF flags libg15render.so was built with, or
# g15canvas's struct layout mismatches between this program and the
# library and corrupts stack memory (bit us once already -- see README).
gcc $(pkg-config --cflags freetype2) g510_lcd_stats.c -o g510_lcd_stats -lg15render $(pkg-config --libs freetype2)

echo "Building g510_lcd_buttons..."
gcc g510_lcd_buttons.c -o g510_lcd_buttons

echo "Restarting services..."
systemctl --user restart g510-lcd-stats.service
systemctl --user restart g510-lcd-buttons.service

echo ""
echo "Done. Status:"
systemctl --user status g510-lcd-stats.service --no-pager -l | head -5
systemctl --user status g510-lcd-buttons.service --no-pager -l | head -5

read -p "Press Enter to close..."
