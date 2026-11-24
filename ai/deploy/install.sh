#!/usr/bin/env bash
# Hercules AI print monitor - installer for Debian/Ubuntu/Armbian (x86_64 or aarch64).
#
#   cd 3d-project/ai && ./deploy/install.sh            # install + systemd service
#   ./deploy/install.sh --no-service                   # install only (run by hand)
#
# What it does (idempotent, safe to re-run):
#   1. apt packages: python3-venv, libgl/libglib (OpenCV runtime), v4l-utils
#   2. Python virtualenv in ./.venv with pinned-minimum dependencies
#   3. downloads the detector weights and verifies the SHA-256
#   4. creates config/hercules.local.toml from the template (never overwrites)
#   5. installs and starts the systemd unit "hercules" (auto-restart on crash)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE=1
for arg in "$@"; do
  case "$arg" in
    --no-service) SERVICE=0 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown option $arg"; exit 2 ;;
  esac
done

cd "$HERE"
echo "==> installing into $HERE"

if command -v apt-get >/dev/null; then
  SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq python3 python3-venv python3-pip libglib2.0-0 libgl1 v4l-utils curl >/dev/null
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    sys.exit("Python 3.9+ required, found " + sys.version)
PY

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .
echo "==> python packages installed"

if [ ! -f config/hercules.local.toml ]; then
  cp config/hercules.toml config/hercules.local.toml
  echo "==> created config/hercules.local.toml - edit camera.source and moonraker.url"
fi

.venv/bin/python -m hercules --config config/hercules.local.toml download-model

if [ "$SERVICE" = 1 ]; then
  SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  RUN_USER="${SUDO_USER:-$(id -un)}"
  # camera access for USB webcams
  $SUDO usermod -aG video "$RUN_USER" || true
  sed -e "s#@DIR@#$HERE#g" -e "s#@USER@#$RUN_USER#g" deploy/hercules.service \
    | $SUDO tee /etc/systemd/system/hercules.service >/dev/null
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable --now hercules
  sleep 3
  systemctl --no-pager --lines=5 status hercules || true
  IP=$(hostname -I 2>/dev/null | awk '{print $1}')
  echo "==> dashboard: http://${IP:-localhost}:8090   logs: journalctl -u hercules -f"
else
  echo "==> run: .venv/bin/python -m hercules --config config/hercules.local.toml run"
fi
