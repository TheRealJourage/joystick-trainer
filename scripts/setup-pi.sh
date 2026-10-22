#!/usr/bin/env bash
# Run on the Raspberry Pi 5, from the repo root, as the normal user (uses sudo for apt only).
# Everything this script changes outside the repo is recorded in .install-state, so
# scripts/uninstall-pi.sh can undo exactly that and nothing else. piolib is installed into
# the repo (.piolib/), not /usr/local. Safe to re-run.
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
state="$repo/.install-state"
piolib="$repo/.piolib"
unit="$HOME/.config/systemd/user/joystick-trainer.service"

record() { grep -qxF "$1" "$state" 2>/dev/null || echo "$1" >> "$state"; }
installed() { dpkg-query -W -f='${Package} ${Status}\n' | sed -n 's/ install ok installed$//p' | sort; }

missing=()
# swig + liblgpio-dev: pip builds rpi-lgpio's lgpio dependency from source on Trixie/Python 3.13
for p in python3-venv python3-dev build-essential cmake git gpiod evtest swig liblgpio-dev; do
  dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "install ok installed" || missing+=("$p")
done
if [ ${#missing[@]} -gt 0 ]; then
  before=$(installed)
  sudo apt-get update
  sudo apt-get install -y "${missing[@]}"
  # Record pulled-in dependencies too, so uninstall leaves dpkg exactly as it was.
  comm -13 <(echo "$before") <(installed) | while read -r p; do record "apt=$p"; done
fi

python3 -m venv "$repo/.venv"
"$repo/.venv/bin/pip" install -e "$repo[pi,dev,pygame]"

if [ ! -d "$piolib/lib" ]; then
  build=$(mktemp -d)
  trap 'rm -rf "$build"' EXIT
  git clone --depth 1 https://github.com/raspberrypi/utils.git "$build/utils"
  cmake -S "$build/utils/piolib" -B "$build/piolib" -DCMAKE_INSTALL_PREFIX="$piolib"
  # Library only: piolib's examples also link against gpiolib, which is not installed.
  cmake --build "$build/piolib" --target pio
  cmake --install "$build/piolib" --component piolib
fi
make -C "$repo/native" ppm_pio PIOLIB="$piolib"

if ! id -nG "$USER" | tr ' ' '\n' | grep -qx input; then
  sudo usermod -aG input "$USER"
  record "group=input"
fi

if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" != "yes" ]; then
  loginctl enable-linger "$USER"
  record "linger=1"
fi

top=$(dirname "$unit")
while [ ! -d "$(dirname "$top")" ]; do top=$(dirname "$top"); done
[ -d "$top" ] || record "dir=$top"
mkdir -p "$(dirname "$unit")"
sed "s|%h/joystick-trainer|$repo|g" "$repo/systemd/joystick-trainer.service" > "$unit"
record "unit=$unit"
systemctl --user daemon-reload

echo
echo "--- recorded in $state ---"
cat "$state" 2>/dev/null || echo "(nothing outside the repo)"
echo
echo "--- checks ---"
ls /dev/pio0 2>/dev/null && echo "/dev/pio0 present" || echo "WARNING: /dev/pio0 missing (update OS and firmware: sudo apt full-upgrade, reboot)"
gpiodetect
echo "Joystick devices:"
"$repo/.venv/bin/python" -m evdev.evtest </dev/null 2>&1 | head -10 || true
echo
echo "Next: log out and in if the input group was added, copy config.example.yaml to config.yaml,"
echo "run it with sink: print first, then enable the service:"
echo "  systemctl --user enable --now joystick-trainer"
echo "Undo everything: scripts/uninstall-pi.sh"
