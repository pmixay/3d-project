#!/usr/bin/env bash
# Build the INT8 model for a small Raspberry Pi (1 GB RAM).
#
# Run this on a PC/laptop with >= 2 GB free RAM (the build peaks at ~1.2 GB, so it
# does not fit on a 1 GB Pi), then copy the result to the Pi:
#
#   cd 3d-project/ai && ./tools/build_int8.sh
#   scp models/obico-failure-int8-qdq.onnx pi@<raspberry-pi-ip>:3d-project/ai/models/
#   ssh pi@<raspberry-pi-ip> sudo systemctl restart hercules
#
# What it does: downloads the official FP32 model (SHA-256 checked) and 64 calibration
# frames of healthy prints from another printer (CC-BY-4.0, checksummed), and builds
# a static INT8 (QDQ) model. On the same software versions the output is bit-identical
# (verified: two builds gave the same SHA-256). Measured effect: docs/EVALUATION.md section 7.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}"

$PY -c "import onnx, sympy" 2>/dev/null || $PY -m pip install -q onnx sympy
$PY -m hercules --config config/hercules.toml download-model
$PY datasets/fetch_calibration.py --out data/calibration
$PY tools/quantize_model.py --mode qdq --calib data/calibration --out models/obico-failure-int8-qdq.onnx
sha256sum models/obico-failure-int8-qdq.onnx
echo
echo "Copy to the Raspberry Pi:"
echo "  scp models/obico-failure-int8-qdq.onnx <user>@<raspberry-pi-ip>:3d-project/ai/models/"
echo "  ssh <user>@<raspberry-pi-ip> sudo systemctl restart hercules"
