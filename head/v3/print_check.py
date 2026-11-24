"""Can the cover be printed without supports?  Checks out/head_cover.stl as it lies on the bed.

Print position: the top face (head +Y) on the bed, so the print grows towards head -Y.
Reports the footprint and height, and every downward-facing surface steeper than the limit:
  - faces on the bed are fine;
  - a lip that sticks out no more than LIP mm from a wall is fine (floors of the engraved letters, screw pads);
  - a strip no longer than BRIDGE mm is fine as a bridge between its two ends (tops of holes);
  - anything else is a failure.

Run:  python3 print_check.py
"""
import os

import numpy as np

import cover

HERE = os.path.dirname(os.path.abspath(__file__))
LIMIT_DEG = 46.0                           # overhang steeper than this from vertical needs support (45 is the design angle)
LIP, BRIDGE = 1.0, 10.0


def load(path):
    d = open(path, "rb").read()
    n = int.from_bytes(d[80:84], "little")
    rec = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(d, dtype=rec, count=n, offset=84)["v"].astype(float)


tri = load(os.path.join(HERE, "out", "head_cover.stl"))
up = np.array([0.0, -1.0, 0.0])            # print "up" in head coordinates
nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
area = np.linalg.norm(nrm, axis=1) / 2
nrm /= np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)[:, None]
h = (tri @ up)                              # height of each vertex above head y = 0, along print up
bed = h.min()
lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
print(f"on the bed: {hi[0] - lo[0]:.0f} x {hi[2] - lo[2]:.0f} mm, height {hi[1] - lo[1]:.0f} mm; "
      f"walls {cover.WALL} mm, front plate {cover.PLATE} mm")

down = nrm @ up < -np.cos(np.radians(90 - LIMIT_DEG))        # faces looking down, flatter than the limit
on_bed = h.max(axis=1) < bed + 0.05
bad = down & ~on_bed
print(f"faces on the bed: {area[down & on_bed].sum():.0f} mm2")

# group the remaining overhang triangles into patches that share vertices
idx = np.flatnonzero(bad)
key = {}
parent = list(range(len(idx)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for k, t in enumerate(idx):
    for v in tri[t]:
        q = tuple(np.round(v, 2))
        if q in key:
            parent[find(k)] = find(key[q])
        else:
            key[q] = k
groups = {}
for k, t in enumerate(idx):
    groups.setdefault(find(k), []).append(t)

fail = 0
rows = []
for g in groups.values():
    p = tri[g].reshape(-1, 3)
    size = p.max(0) - p.min(0)
    rows.append((max(size[0], size[2]), min(size[0], size[2]), area[g].sum(), p.min(0), p.max(0)))
rows.sort(key=lambda r: -r[0])
lips = 0
for long, narrow, a, p0, p1 in rows:
    kind = "lip" if narrow <= LIP else "bridge" if long <= BRIDGE else "FAIL"
    lips += kind == "lip"
    fail += kind == "FAIL"
    if kind != "lip":
        print(f"{kind:6s} {long:4.1f} x {narrow:3.1f} mm, {a:5.1f} mm2 at "
              f"x[{p0[0]:.1f},{p1[0]:.1f}] y[{p0[1]:.1f},{p1[1]:.1f}] z[{p0[2]:.1f},{p1[2]:.1f}]")
print(f"{len(rows)} overhang patches: {lips} lips up to {LIP} mm, {len(rows) - lips - fail} bridges up to {BRIDGE} mm, {fail} need support")
raise SystemExit(1 if fail else 0)
