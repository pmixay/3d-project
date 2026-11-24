#!/usr/bin/env python3
"""Run the detector once over every frame of recorded sessions and cache the boxes.

Cache: <cache_dir>/<session>.jsonl, one line per frame:
  {"file": ..., "t": seconds, "boxes": [[x1,y1,x2,y2,conf], ...], "ms": latency, "w": W, "h": H}
Boxes are stored after NMS at a low floor (0.01). Greedy NMS never lets a
lower-confidence box suppress a higher one, so filtering this cache at a
higher threshold gives exactly the boxes a run at that threshold would give.
"""
import argparse
import json
import multiprocessing as mp
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402

from hercules.camera import list_frames  # noqa: E402
from hercules.config import Config  # noqa: E402
from hercules.detector import Detector, postprocess  # noqa: E402

FLOOR = 0.01
_det = None


def _init(threads, backend, model):
    global _det
    cfg = Config()
    cfg.detector.threads = threads
    cfg.detector.backend = backend
    if model:
        cfg.detector.model_path = model
        cfg.detector.model_sha256 = ""
    _det = Detector(cfg.detector)


def _score(args):
    path, t = args
    img = cv2.imread(path)
    import time
    t0 = time.perf_counter()
    b, c = _det.raw(img)
    ms = (time.perf_counter() - t0) * 1000
    boxes = postprocess(b, c, img.shape[1], img.shape[0], FLOOR, 0.45)
    return {"file": os.path.basename(path), "t": t, "w": img.shape[1], "h": img.shape[0], "ms": round(ms, 1),
            "boxes": [[round(x.x1, 1), round(x.y1, 1), round(x.x2, 1), round(x.y2, 1), round(x.conf, 4)] for x in boxes]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sessions", nargs="+")
    ap.add_argument("--cache", default="data/cache")
    ap.add_argument("--tag", default="", help="suffix for the cache file (e.g. model variant)")
    ap.add_argument("--model", default="", help="alternative ONNX file (e.g. quantised)")
    ap.add_argument("--backend", default="onnxruntime")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--threads", type=int, default=2)
    a = ap.parse_args()
    os.makedirs(a.cache, exist_ok=True)
    with mp.Pool(a.workers, _init, (a.threads, a.backend, a.model)) as pool:
        for s in a.sessions:
            name = os.path.basename(os.path.normpath(s))
            out = os.path.join(a.cache, name + (f".{a.tag}" if a.tag else "") + ".jsonl")
            files, times = list_frames(s)
            if os.path.exists(out) and sum(1 for _ in open(out)) == len(files):
                print("cached", out)
                continue
            rows = pool.map(_score, list(zip(files, times)), chunksize=8)
            with open(out + ".tmp", "w") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
            os.replace(out + ".tmp", out)
            ms = sorted(r["ms"] for r in rows)
            print(f"{name}: {len(rows)} frames, median {ms[len(ms)//2]:.0f} ms -> {out}", flush=True)


if __name__ == "__main__":
    main()
