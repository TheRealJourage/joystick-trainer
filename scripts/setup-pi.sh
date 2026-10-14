#!/usr/bin/env bash
# Run on the Raspberry Pi 5, from the repo root, as the normal user (uses sudo for apt only).
# Not yet run on a Pi.
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)

sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential cmake git gpiod evtest

python3 -m venv "$repo/.venv"
"$repo/.venv/bin/pip" install -e "$repo[pi,dev]"

if [ ! -f /usr/local/lib/libpio.a ] && [ ! -f /usr/local/lib/libpio.so ]; then
  build=$(mktemp -d)
  git clone --depth 1 https://github.com/raspberrypi/utils.git "$build/utils"
  cmake -S "$build/utils/piolib" -B "$build/piolib"
  cmake --build "$build/piolib"
  sudo cmake --install "$build/piolib"
  sudo ldconfig
fi
make -C "$repo/native" ppm_pio

sudo usermod -aG input "$USER"
loginctl enable-linger "$USER"

mkdir -p "$HOME/.config/systemd/user"
sed "s|%h/joystick-trainer|$repo|g" "$repo/systemd/joystick-trainer.service" \
  > "$HOME/.config/systemd/user/joystick-trainer.service"
systemctl --user daemon-reload

echo
echo "--- checks ---"
ls /dev/pio0 2>/dev/null && echo "/dev/pio0 present" || echo "WARNING: /dev/pio0 missing (update OS and firmware: sudo apt full-upgrade, reboot)"
gpiodetect
echo "Joystick devices:"
"$repo/.venv/bin/python" -m evdev.evtest </dev/null 2>&1 | head -10 || true
echo
echo "Next: log out and in (input group), copy config.example.yaml to config.yaml,"
echo "run it with sink: print first, then enable the service:"
echo "  systemctl --user enable --now joystick-trainer"
