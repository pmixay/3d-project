#!/usr/bin/env python3
"""Reproducible performance benchmark. Run it on every candidate host
(the inference PC, the BTT Pi) and commit the JSON it writes.

  python tools/benchmark.py --frames data/zenodo_fffqc/test_extrusion_error_print_camera1 \
         --out docs/results/benchmark_<host>.json

Sections
  1. model   latency (median / p95), load time and process RAM per backend,
             model variant and thread count; each in a fresh process
  2. resolution  full analysis step (validation + resize + inference + decision)
             for camera frames of 640x360, 1280x720, 1920x1080
  3. sustained   process / system CPU and RAM while analysing one frame every
             N seconds for --duration seconds (the cost of the inference interval)
"""
from __future__ import annotations

import argparse
import glob
import json
import multiprocessing as mp
import os
import platform
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def host_info():
    import psutil
    cpu = platform.processor() or platform.machine()
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.lower().startswith(("model name", "hardware")):
                    cpu = line.split(":", 1)[1].strip()
                    break
    except OSError:
        pass
    import onnxruntime
    import cv2
    return {"cpu": cpu, "machine": platform.machine(), "cores": psutil.cpu_count(),
            "ram_mb": psutil.virtual_memory().total // 2**20, "os": platform.platform(),
            "python": platform.python_version(), "onnxruntime": onnxruntime.__version__,
            "opencv": cv2.__version__, "ort_providers": onnxruntime.get_available_providers()}


def _model_job(q, model, backend, threads, files, n):
    import cv2
    import psutil
    from hercules.config import Config
    from hercules.detector import Detector
    proc = psutil.Process()
    rss0 = proc.memory_info().rss
    cfg = Config()
    cfg.detector.model_path, cfg.detector.model_sha256 = model, ""
    cfg.detector.backend, cfg.detector.threads = backend, threads
    try:
        det = Detector(cfg.detector)
    except Exception as e:  # noqa: BLE001
        q.put({"error": str(e)[:200]})
        return
    imgs = [cv2.imread(f) for f in files[:n]]
    det.raw(imgs[0])
    lat = []
    for img in imgs:
        t0 = time.perf_counter()
        det.raw(img)
        lat.append((time.perf_counter() - t0) * 1000)
    lat.sort()
    q.put({"load_s": round(det.load_s, 2), "median_ms": round(statistics.median(lat), 1),
           "p95_ms": round(lat[int(0.95 * (len(lat) - 1))], 1), "rss_mb": round(proc.memory_info().rss / 2**20),
           "rss_model_mb": round((proc.memory_info().rss - rss0) / 2**20), "providers": det.providers})


def bench_models(files, variants, threads_list, n):
    ctx = mp.get_context("spawn")
    rows = []
    for model, backend in variants:
        if not os.path.exists(model):
            continue
        for th in threads_list:
            if backend == "opencv" and th not in (0, threads_list[-1]):
                continue
            q = ctx.Queue()
            p = ctx.Process(target=_model_job, args=(q, model, backend, th, files, n))
            p.start()
            r = q.get(timeout=1800)
            p.join()
            r.update(model=os.path.basename(model), backend=backend, threads=th or "default")
            rows.append(r)
            print("  model", r, flush=True)
    return rows


def bench_resolution(files, n):
    import cv2
    from hercules.config import Config
    from hercules.pipeline import Analyzer
    cfg = Config()
    cfg.pipeline.skip_duplicates = cfg.pipeline.skip_blurred = False
    an = Analyzer(cfg)
    rows = []
    for w, h in ((640, 360), (1280, 720), (1920, 1080)):
        imgs = [cv2.resize(cv2.imread(f), (w, h)) for f in files[:n]]
        an.reset()
        ts, infer = [], []
        for i, img in enumerate(imgs):
            r = an.step(img, float(i))
            ts.append(r.step_ms)
            infer.append(r.detection.latency_ms)
        rows.append({"resolution": f"{w}x{h}", "step_median_ms": round(statistics.median(ts), 1),
                     "inference_median_ms": round(statistics.median(infer), 1),
                     "overhead_median_ms": round(statistics.median(ts) - statistics.median(infer), 1)})
        print("  resolution", rows[-1], flush=True)
    return rows


def bench_sustained(files, intervals, duration):
    import cv2
    import psutil
    from hercules.config import Config
    from hercules.pipeline import Analyzer
    cfg = Config()
    an = Analyzer(cfg)
    imgs = [cv2.imread(f) for f in files]
    proc = psutil.Process()
    rows = []
    for iv in intervals:
        an.reset()
        proc.cpu_percent(None)
        psutil.cpu_percent(None)
        t0 = time.time()
        k, nxt, rss = 0, t0, 0
        while time.time() - t0 < duration:
            if time.time() < nxt:
                time.sleep(min(0.05, nxt - time.time()))
                continue
            nxt += iv
            an.step(imgs[k % len(imgs)], time.time())
            k += 1
            rss = max(rss, proc.memory_info().rss)
        pcpu = proc.cpu_percent(None)
        rows.append({"interval_s": iv, "analyses": k, "process_cpu_pct_of_one_core": round(pcpu, 1),
                     "system_cpu_pct": round(psutil.cpu_percent(None), 1),
                     "process_cpu_pct_of_machine": round(pcpu / psutil.cpu_count(), 1),
                     "peak_rss_mb": round(rss / 2**20)})
        print("  sustained", rows[-1], flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames", required=True, help="directory of JPEG frames")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--threads", type=int, nargs="+", default=[1, 2, 4])
    ap.add_argument("--intervals", type=float, nargs="+", default=[1.0, 3.0, 10.0])
    ap.add_argument("--duration", type=float, default=60.0)
    ap.add_argument("--skip", nargs="*", default=[], choices=["model", "resolution", "sustained"])
    ap.add_argument("--out")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.frames, "*.jpg")))
    files = files[:: max(1, len(files) // max(a.n, 1))][: max(a.n, 10)]
    res = {"host": host_info(), "time": time.strftime("%Y-%m-%d %H:%M:%S"), "frames_dir": a.frames}
    print(res["host"], flush=True)
    variants = [("models/obico-failure-5a6b1be1fa.onnx", "onnxruntime"),
                ("models/obico-failure-int8-qdq.onnx", "onnxruntime"),
                ("models/obico-failure-int8-dynamic.onnx", "onnxruntime"),
                ("models/obico-failure-5a6b1be1fa.onnx", "opencv")]
    if "model" not in a.skip:
        res["model"] = bench_models(files, variants, a.threads, a.n)
    if "resolution" not in a.skip:
        res["resolution"] = bench_resolution(files, a.n)
    if "sustained" not in a.skip:
        res["sustained"] = bench_sustained(files, a.intervals, a.duration)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
        print("wrote", a.out)


if __name__ == "__main__":
    main()
