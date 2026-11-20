#!/usr/bin/env bash
# Renders the README images from the HTML in this folder with headless Chrome (2x for sharp text).
set -euo pipefail
cd "$(dirname "$0")"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
shot() { "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --virtual-time-budget=4000 --window-size="$2" --screenshot="../assets/$1.png" "file://$PWD/$1.html" >/dev/null 2>&1; echo "assets/$1.png"; }
shot banner 1280,420
shot social-preview 1280,640
shot terminal 1200,760
shot report 1200,1230
shot avatar 512,512
