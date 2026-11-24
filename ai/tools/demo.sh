#!/usr/bin/env bash
# Competition demo: replay a real recorded print that fails, against a simulated printer.
#
#   ./tools/demo.sh [session_dir] [speed] [pause_policy]
#   ./tools/demo.sh data/zenodo_fffqc/test_extrusion_error_print_camera2 10 auto
#
# Opens: dashboard http://<this-pc>:8090  ·  mock printer log http://127.0.0.1:7125/mock/log
# Ctrl+C stops both. State (incidents, reports) goes to state-demo/.
set -euo pipefail
cd "$(dirname "$0")/.."
SESSION="${1:-data/zenodo_fffqc/test_extrusion_error_print_camera2}"
SPEED="${2:-10}"
POLICY="${3:-auto}"
PY="${PYTHON:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}"

[ -d "$SESSION" ] || { echo "missing $SESSION - run: $PY datasets/fetch_zenodo_fffqc.py"; exit 1; }
DURATION=$($PY -c "import csv,sys; r=list(csv.DictReader(open('$SESSION/frames.csv'))); print(float(r[-1]['t_s']) / float('$SPEED'))")
# interval: 3 s of print time per analysis, whatever the replay speed
INTERVAL=$($PY -c "print(round(3.0/$SPEED, 3))")

rm -rf state-demo
$PY tools/mock_moonraker.py --port 7125 --start-print hercules_demo_part.gcode --duration-s "$DURATION" &
MOCK=$!
trap 'kill $MOCK 2>/dev/null' EXIT
sleep 1
echo "replaying $SESSION at ${SPEED}x, analysis every ${INTERVAL}s wall = 3 s print time, pause policy $POLICY"
HERCULES_STATE_DIR=state-demo \
HERCULES_CAMERA__SOURCE="$SESSION" \
HERCULES_CAMERA__REPLAY_SPEED="$SPEED" \
HERCULES_PIPELINE__INTERVAL_S="$INTERVAL" \
HERCULES_MOONRAKER__URL=http://127.0.0.1:7125 \
HERCULES_ACTIONS__PAUSE_POLICY="$POLICY" \
  $PY -m hercules --config config/hercules.toml run
