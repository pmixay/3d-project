#!/usr/bin/env python3
"""Validate the sensor-noise flag: every 60th frame of each recorded session, clean
and with synthetic sigma-18 noise (tools/evaluate.py perturb 'noise')."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2  # noqa: E402

from evaluate import perturb  # noqa: E402
from hercules.config import PipelineCfg  # noqa: E402
from hercules.quality import FrameValidator  # noqa: E402

cfg = PipelineCfg()
v = FrameValidator(cfg)
res = {"threshold": cfg.noise_sigma_max, "sessions": {}}
clean_all, noisy_all = [], []
for s in sorted(glob.glob(os.path.join(sys.argv[1] if len(sys.argv) > 1 else "data/zenodo_fffqc", "test_*"))):
    fs = sorted(glob.glob(s + "/*.jpg"))[::60]
    c = [v.check(cv2.imread(f)).noise_sigma for f in fs]
    n = [v.check(perturb(cv2.imread(f), "noise")).noise_sigma for f in fs[::4]]
    clean_all += c
    noisy_all += n
    res["sessions"][os.path.basename(s)] = {"clean_max": round(max(c), 2), "noisy_min": round(min(n), 2)}
res["clean_flagged"] = f"{sum(x > cfg.noise_sigma_max for x in clean_all)}/{len(clean_all)}"
res["noisy_flagged"] = f"{sum(x > cfg.noise_sigma_max for x in noisy_all)}/{len(noisy_all)}"
print(json.dumps(res, indent=1))
os.makedirs("docs/results", exist_ok=True)
json.dump(res, open("docs/results/noise_flag.json", "w"), indent=1)
