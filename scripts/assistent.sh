#!/usr/bin/env bash
# Starts the German setup assistant; installs the software first if that has not happened yet.
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
if [ ! -x "$repo/.venv/bin/joystick-trainer-assistent" ] || ! "$repo/.venv/bin/python" -c "import pygame, lgpio" 2>/dev/null; then
  echo
  echo "Installiere die Software. Das dauert 10-20 Minuten und fragt einmal nach deinem Passwort."
  echo "Warnungen wie \"/dev/pio0 missing\" kannst du ignorieren."
  echo
  "$repo/scripts/setup-pi.sh"
fi
exec "$repo/.venv/bin/joystick-trainer-assistent" "$@"
