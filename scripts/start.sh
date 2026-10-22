#!/usr/bin/env bash
# Desktop icon "Joystick-Trainer starten": the channel display (if there is a desktop and a DSI screen)
# plus the trainer with the sending config. Closing the window or Ctrl+C stops both.
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo"
config=config.lgpio.yaml
if [ ! -f "$config" ]; then
  echo "Die Einrichtung ist noch nicht fertig (config.lgpio.yaml fehlt). Bitte \"Einrichtung fortsetzen\"."
  exit 1
fi
echo "Joystick-Trainer"
echo "  - An der Fernsteuerung: Testmodell mit Internal RF und External RF = Off?"
echo "  - Notschalter SD oben = die Fernsteuerung steuert selbst, unten = der Joystick."
echo "  - Stoppen: dieses Fenster schließen oder Strg + C."
read -r -p "Starten mit Enter. " _

display_pid=""
if [ -n "${WAYLAND_DISPLAY:-}${DISPLAY:-}" ] && grep -qs '^connected' /sys/class/drm/card*-DSI-*/status; then
  .venv/bin/joystick-trainer-display &
  display_pid=$!
fi
trap '[ -n "$display_pid" ] && kill "$display_pid" 2>/dev/null; true' EXIT
.venv/bin/joystick-trainer "$config"
