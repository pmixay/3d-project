#!/usr/bin/env python3
"""Fetch a subset of the Zenodo FFF quality-control dataset (record 18628777, CC-BY-4.0).

Dataset: "Quality Control in Additive Manufacturing: Image Dataset for Defect
Detection in Fused Filament Fabrication", https://zenodo.org/records/18628777
Licence: CC-BY-4.0 (attribution required; we do not redistribute the frames,
this script downloads them on demand).

The archive is 48 GB; we read only the files we need through HTTP range
requests (remotezip). Each `<split>/full_res/<kind>/<cameraN>/` folder is one
complete print recorded by one fixed camera (~50 min, ~1.4 s per frame), so a
folder is a *session*: train/eval splits are made per folder, never per frame.

Output layout (one directory per session):
    <out>/<split>_<kind>_<camera>/frame_000123.jpg
    <out>/<split>_<kind>_<camera>/frames.csv   index,file,t_s,zip_name
Frames are resized to --width (default 960) to save disk; t_s is the capture
time reconstructed from the zip entry mtimes (2 s resolution), linearly
interpolated over the frame index.
"""
import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import os
import re
import sys
import threading

import cv2
import numpy as np
from remotezip import RemoteZip

URL = "https://zenodo.org/api/records/18628777/files/{split}_data.zip/content"
KINDS = ["no_error_print", "extrusion_error_print", "layershift_error_print"]
CAMS = ["camera1", "camera2", "camera3"]
_local = threading.local()


def _zip(url):
    z = getattr(_local, "z", None)
    if z is None or _local.url != url:
        _local.z, _local.url = RemoteZip(url), url
    return _local.z


def fetch(url, name, dst, width):
    if os.path.exists(dst):
        return
    for attempt in range(4):
        try:
            data = _zip(url).read(name)
            break
        except Exception:  # network hiccup: new connection, retry
            _local.z = None
            if attempt == 3:
                raise
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if width and img.shape[1] > width:
        h = round(img.shape[0] * width / img.shape[1])
        img = cv2.resize(img, (width, h), interpolation=cv2.INTER_AREA)
    tmp = dst + ".tmp.jpg"
    cv2.imwrite(tmp, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    os.replace(tmp, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/zenodo_fffqc")
    ap.add_argument("--split", default="test", choices=["test", "base", "additional_defect"])
    ap.add_argument("--kinds", nargs="+", default=KINDS)
    ap.add_argument("--cams", nargs="+", default=CAMS)
    ap.add_argument("--step", type=int, default=1, help="keep every Nth frame")
    ap.add_argument("--width", type=int, default=960)
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()

    url = URL.format(split=a.split)
    infos = RemoteZip(url).infolist()
    jobs = []
    for kind in a.kinds:
        for cam in a.cams:
            prefix = f"{a.split}/full_res/{kind}/{cam}/"
            sel = [i for i in infos if i.filename.startswith(prefix) and i.filename.endswith(".jpg")]
            if not sel:
                print("missing", prefix, file=sys.stderr)
                continue
            sel.sort(key=lambda i: int(re.findall(r"_(\d+)\.jpg$", i.filename)[0]))
            times = [dt.datetime(*i.date_time).timestamp() for i in sel]
            t0, span = times[0], (max(times) - min(times))
            per = span / max(1, len(sel) - 1)
            d = os.path.join(a.out, f"{a.split}_{kind}_{cam}")
            os.makedirs(d, exist_ok=True)
            rows = []
            for k, info in enumerate(sel):
                if k % a.step:
                    continue
                fn = f"frame_{k:06d}.jpg"
                rows.append((k, fn, round(k * per, 2), info.filename))
                jobs.append((info.filename, os.path.join(d, fn)))
            with open(os.path.join(d, "frames.csv"), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["index", "file", "t_s", "zip_name"])
                w.writerows(rows)
            print(f"{d}: {len(rows)} frames, {span/60:.1f} min, {per:.2f} s/frame", flush=True)

    done = 0
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(fetch, url, n, p, a.width) for n, p in jobs]
        for f in cf.as_completed(futs):
            f.result()
            done += 1
            if done % 500 == 0:
                print(f"{done}/{len(jobs)}", flush=True)
    print("done", len(jobs))


if __name__ == "__main__":
    main()
