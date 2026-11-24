#!/usr/bin/env bash
# Hercules AI print monitor - installer for Raspberry Pi OS 64-bit (main target),
# Debian/Ubuntu/Armbian on x86_64 or aarch64.
#
#   cd 3d-project/ai && ./deploy/install.sh            # install + systemd service
#   ./deploy/install.sh --no-service                   # install only (run by hand)
#
# What it does (idempotent, safe to re-run):
#   1. apt packages: python3-venv, OpenCV runtime libs, v4l-utils; on a Raspberry Pi
#      also rpicam-apps (CSI cameras), and it refuses a 32-bit OS with a clear message
#   2. Python virtualenv in ./.venv with pinned-minimum dependencies
#   3. downloads the detector weights and verifies the SHA-256
#   4. creates config/hercules.local.toml from the template (never overwrites);
#      on a Raspberry Pi from config/hercules.rpi.toml (CSI camera, Pi-sized load)
#   5. installs and starts the systemd unit "hercules" (auto-restart on crash)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE=1
for arg in "$@"; do
  case "$arg" in
    --no-service) SERVICE=0 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown option $arg"; exit 2 ;;
  esac
done

cd "$HERE"
echo "==> installing into $HERE"

IS_RPI=0
if grep -qi "raspberry pi" /proc/device-tree/model 2>/dev/null; then
  IS_RPI=1
  echo "==> Raspberry Pi detected: $(tr -d '\0' < /proc/device-tree/model)"
  if [ "$(uname -m)" != "aarch64" ]; then
    echo "ERROR: 32-bit OS ($(uname -m)). ONNX Runtime publishes Linux ARM wheels only for 64-bit."
    echo "       Flash 'Raspberry Pi OS (64-bit)' Lite with Raspberry Pi Imager and run this again."
    exit 1
  fi
  MEM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
  if [ "$MEM_MB" -lt 1800 ]; then
    echo "NOTE: ${MEM_MB} MB RAM. The Pi preset uses the INT8 model (~270 MB). Build it on a PC with"
    echo "      tools/build_int8.sh and copy it to models/ (docs/RASPBERRY_PI.md section 3.1);"
    echo "      until then the FP32 model (~450 MB) runs as a fallback."
  fi
fi

if command -v apt-get >/dev/null; then
  SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq python3 python3-venv python3-pip libglib2.0-0 v4l-utils curl >/dev/null
  $SUDO apt-get install -y -qq libgl1 >/dev/null 2>&1 || true
  if [ "$IS_RPI" = 1 ]; then
    # CSI ribbon cameras are read through rpicam-vid (Bookworm) / libcamera-vid (Bullseye)
    $SUDO apt-get install -y -qq rpicam-apps >/dev/null 2>&1 \
      || $SUDO apt-get install -y -qq libcamera-apps >/dev/null 2>&1 \
      || echo "WARNING: could not install rpicam-apps; CSI cameras will not work"
  fi
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
  if [ "$IS_RPI" = 1 ]; then
    cp config/hercules.rpi.toml config/hercules.local.toml
  else
    cp config/hercules.toml config/hercules.local.toml
  fi
  echo "==> created config/hercules.local.toml - edit moonraker.url (and camera.source if not a CSI camera)"
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
