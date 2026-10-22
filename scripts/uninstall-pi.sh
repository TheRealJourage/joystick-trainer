#!/usr/bin/env bash
# Undo scripts/setup-pi.sh: reverts exactly what .install-state records (apt packages the
# setup installed, input group, linger, user unit, desktop icons). With --delete-repo it also removes the
# repo directory itself, including .venv, .piolib and config.yaml.
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
state="$repo/.install-state"
delete_repo=0
[ "${1:-}" = "--delete-repo" ] && delete_repo=1

systemctl --user disable --now joystick-trainer.service 2>/dev/null || true

if [ -f "$state" ]; then
  while IFS='=' read -r key value; do
    case "$key" in
      unit)
        rm -f "$value"
        systemctl --user daemon-reload
        echo "removed unit $value" ;;
      file)
        rm -f "$value"
        echo "removed $value" ;;
      linger)
        loginctl disable-linger "$USER"
        echo "linger disabled" ;;
      group)
        sudo gpasswd -d "$USER" "$value"
        echo "removed $USER from group $value" ;;
    esac
  done < "$state"

  # Directories the setup created; only empty ones are removed, anything added since stays.
  while IFS='=' read -r key value; do
    [ "$key" = dir ] && find "$value" -depth -type d -empty -delete 2>/dev/null && echo "removed empty $value"
  done < "$state"

  pkgs=$(sed -n 's/^apt=//p' "$state" | tr '\n' ' ')
  if [ -n "$pkgs" ]; then
    # shellcheck disable=SC2086
    sudo apt-get remove -y $pkgs
    echo "removed apt packages: $pkgs"
  fi
  rm -f "$state"
else
  echo "no $state: nothing recorded outside the repo"
fi

if [ "$delete_repo" = 1 ]; then
  cd /
  rm -rf "$repo"
  echo "deleted $repo"
else
  echo "repo kept: $repo (re-run with --delete-repo to remove it too)"
fi
