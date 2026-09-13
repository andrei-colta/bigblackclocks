#!/bin/bash
# Restarts both services -- works whether they're stopped, crashed, or
# just stuck/unresponsive (a plain "start" does nothing if a service is
# already "running" but hung; "restart" fixes both cases the same way).
systemctl --user restart g510-lcd-stats.service g510-lcd-buttons.service
zenity --info --title="G510 LCD" --text="Screen and buttons restarted." --width=250 2>/dev/null
