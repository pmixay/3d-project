#!/usr/bin/env bash
# Reproduce every number in docs/EVALUATION.md.
#   1. download the evaluation recordings  (~1.8 GB, ~30 min)
#   2. run the network once per frame       (cache, ~30-60 min on 4 cores)
#   3. replay through the decision engine   (fast, many configurations)
# Results: docs/results/*.json
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}"
R=docs/results
mkdir -p "$R"

$PY datasets/fetch_zenodo_fffqc.py --out data/zenodo_fffqc --split test
$PY tools/score_sessions.py data/zenodo_fffqc/test_* --workers 2 --threads 2

# main result + inference-interval sweep (frame period of the recordings is ~1.4 s)
$PY tools/evaluate.py --intervals 1.4 3 6 12 24 --out $R/eval_hercules.json
# baselines on the same data
$PY tools/evaluate.py --engine obico --intervals 1.4 3 6 12 24 --out $R/eval_obico.json
$PY tools/evaluate.py --engine naive --intervals 3 12 --out $R/eval_naive.json
# sensitivity of our engine to its own parameters (not tuned on this data; shown for transparency)
$PY tools/evaluate.py --intervals 3 --set decision.ewm_tau_s=30 --out $R/eval_tau30.json
$PY tools/evaluate.py --intervals 3 --set decision.ewm_tau_s=120 --out $R/eval_tau120.json
$PY tools/evaluate.py --intervals 3 --set decision.min_positive_frames=1 --out $R/eval_gate1.json
$PY tools/evaluate.py --intervals 12 --set decision.min_positive_frames=1 --out $R/eval_gate1_12s.json
# robustness: synthetic camera problems on real frames, 10 min before to 15 min after the onset
for k in dark blur occlusion noise; do
  $PY tools/evaluate.py --perturb $k --intervals 6 --window 600 900 --out $R/eval_perturb_$k.json
done
$PY tools/evaluate.py --intervals 6 --window 600 900 --out $R/eval_perturb_none.json
# INT8 model variant
if [ -f models/obico-failure-int8-qdq.onnx ]; then
  $PY tools/score_sessions.py data/zenodo_fffqc/test_* --model models/obico-failure-int8-qdq.onnx --cache data/cache_int8
  $PY tools/evaluate.py --cache data/cache_int8 --intervals 3 12 --out $R/eval_int8.json
fi
# performance on this host
$PY tools/benchmark.py --frames data/zenodo_fffqc/test_extrusion_error_print_camera1 --out "$R/benchmark_$(hostname).json"
$PY tools/noise_check.py
# 40-minute soak test of the live service
$PY tools/soak.py --source data/zenodo_fffqc/test_no_error_print_camera2 --minutes 40 --interval 1 --speed 4 --sample 60 --out $R/soak_40min.json
