#!/usr/bin/env python3
"""Download calibration frames for building the INT8 model.

Source: Hugging Face dataset Alex-Ultra/3d-cli-print-failure-frames (CC-BY-4.0),
frames of *healthy* prints from a Snapmaker U1 printer. It is a different printer,
lab and filament from the evaluation recordings (Zenodo 18628777), so the INT8
model's evaluation is not influenced by its calibration data.

Calibration only measures the value ranges inside the network (no labels, no
training); it needs normal-looking frames from a printer camera.

  python datasets/fetch_calibration.py --out data/calibration
"""
import argparse
import hashlib
import json
import os
import urllib.request

REPO = "https://huggingface.co/datasets/Alex-Ultra/3d-cli-print-failure-frames/resolve/{rev}/{path}"
REVISION = "3ac6790305246b7282ccd10a0f6a69f1761cdbcd"   # pinned dataset revision


def get(path, rev):
    with urllib.request.urlopen(REPO.format(rev=rev, path=path), timeout=60) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/calibration")
    ap.add_argument("--n", type=int, default=64, help="number of frames (spread over all healthy prints)")
    ap.add_argument("--revision", default=REVISION)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = [json.loads(line) for line in get("labels.jsonl", a.revision).decode().splitlines() if line.strip()]
    healthy = sorted((r for r in rows if r["label"] == "healthy"), key=lambda r: (r["group"], r["file"]))
    step = max(1, len(healthy) // a.n)
    chosen = healthy[::step][: a.n]
    for r in chosen:
        dst = os.path.join(a.out, os.path.basename(r["file"]))
        if not os.path.exists(dst):
            data = get(r["file"], a.revision)
            if hashlib.sha256(data).hexdigest() != r["sha256"]:
                raise SystemExit(f"checksum mismatch for {r['file']}")
            with open(dst, "wb") as f:
                f.write(data)
    groups = sorted({r["group"] for r in chosen})
    print(f"{len(chosen)} healthy frames from {len(groups)} prints ({', '.join(groups)}) -> {a.out}")
    print("Licence: CC-BY-4.0, Alex-Ultra/3d-cli-print-failure-frames (Hugging Face)")


if __name__ == "__main__":
    main()
