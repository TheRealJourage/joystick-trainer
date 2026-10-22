#!/usr/bin/env bash
# One command on a fresh Raspberry Pi 5, for people without Linux knowledge:
#   bash <(curl -fsSL https://raw.githubusercontent.com/TheRealJourage/joystick-trainer/main/scripts/install.sh)
# Downloads (or updates) the project into ~/joystick-trainer and starts the German setup assistant.
set -euo pipefail

repo="$HOME/joystick-trainer"
url="https://github.com/TheRealJourage/joystick-trainer.git"

echo "Joystick-Trainer: Download nach $repo"
added=""
if ! command -v git >/dev/null; then
  echo "Installiere git (fragt nach deinem Passwort; beim Tippen erscheinen keine Zeichen)."
  before=$(dpkg-query -W -f='${Package} ${Status}\n' | sed -n 's/ install ok installed$//p' | sort)
  sudo apt-get update
  sudo apt-get install -y git
  after=$(dpkg-query -W -f='${Package} ${Status}\n' | sed -n 's/ install ok installed$//p' | sort)
  added=$(comm -13 <(echo "$before") <(echo "$after"))
fi
if [ -d "$repo/.git" ]; then
  git -C "$repo" pull --ff-only
else
  git clone "$url" "$repo"
fi
# Recorded like setup-pi.sh does, so uninstall-pi.sh removes git again if this script installed it.
for p in $added; do
  grep -qxF "apt=$p" "$repo/.install-state" 2>/dev/null || echo "apt=$p" >> "$repo/.install-state"
done
exec "$repo/scripts/assistent.sh"
