#!/usr/bin/env python3
"""Contact sheet of a recorded session with frame indices burnt in (for labelling event onsets)."""
import argparse
import os

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2  # noqa: E402
import numpy as np

from hercules.camera import list_frames

ap = argparse.ArgumentParser()
ap.add_argument("session")
ap.add_argument("--start", type=int, default=0)
ap.add_argument("--end", type=int, default=10**9)
ap.add_argument("--step", type=int, default=30)
ap.add_argument("--cols", type=int, default=6)
ap.add_argument("--width", type=int, default=320)
ap.add_argument("--out", required=True)
a = ap.parse_args()
files, times = list_frames(a.session)
tiles = []
for f, t in zip(files, times):
    idx = int(os.path.basename(f).split("_")[1].split(".")[0])
    if a.start <= idx <= a.end and (idx - a.start) % a.step == 0:
        im = cv2.imread(f)
        im = cv2.resize(im, (a.width, round(im.shape[0] * a.width / im.shape[1])))
        cv2.rectangle(im, (0, 0), (150, 22), (0, 0, 0), -1)
        cv2.putText(im, f"#{idx} {t/60:.1f}m", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        tiles.append(im)
while len(tiles) % a.cols:
    tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + a.cols]) for i in range(0, len(tiles), a.cols)]
cv2.imwrite(a.out, np.vstack(rows))
print(len(tiles), "tiles ->", a.out)
