"""Project head parts along the X rail and show where a straight belt run can pass.

Head coordinates (as exported from the Hefest KOMPAS assembly):
  origin = MGN12H carriage centre, +Z along the X rail, +Y up, -X towards the hotend.
Usage: python belt_corridor.py out.png part1.stl part2.stl ...   (binary STL, mm)
"""
import struct, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

RES = 8                                  # raster px per mm
X0, X1, Y0, Y1 = -56, 42, -72, 60        # window, mm
RAIL = (-6.5, -4.0, 12.0, 8.0)           # MGN12 rail: x, y, w, h (carriage holes centred on x = -0.5)
BLOCK = (-14.0, -1.0, 27.0, 10.0)        # MGN12H block, top face at y = 9 (underside of the frame plate)
BELT_REAR = (15.0, -2.0, 6.0, 6.0)       # clamped run: teardrop pockets x 15..21, belt y -2..4
BELT_FRONT = (-22.0, -2.0, 6.0, 6.0)     # second run IF it mirrors the rear one about the rail (to be measured)
COLORS = ["#1f5fbf", "#e67e22", "#27ae60", "#8e44ad", "#c0392b", "#b8860b", "#555555"]


def load_stl(path):
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[80:84])[0]
    dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(b, dtype=dt, count=n, offset=84)["v"].astype(float)


def main(out, paths):
    w, h = (X1 - X0) * RES, (Y1 - Y0) * RES
    img = Image.new("RGB", (w, h), "white")
    occ = Image.new("1", (w, h), 0)
    d, dm = ImageDraw.Draw(img), ImageDraw.Draw(occ)
    for path, col in zip(paths, COLORS * 9):
        for t in load_stl(path):
            pts = [((p[0] - X0) * RES, (Y1 - p[1]) * RES) for p in t]
            d.polygon(pts, fill=col)
            dm.polygon(pts, fill=1)
    occ = np.array(occ)
    fig, ax = plt.subplots(figsize=(9, 12))
    ax.imshow(img, extent=(X0, X1, Y0, Y1))
    for (x, y, bw, bh), ec, ls, lab in [(RAIL, "k", "-", "MGN12 rail"), (BLOCK, "k", "--", "MGN12H block"),
                                        (BELT_REAR, "lime", "-", "belt, clamped run"),
                                        (BELT_FRONT, "red", "-", "belt, second run if mirrored")]:
        ax.add_patch(plt.Rectangle((x, y), bw, bh, fill=False, ec=ec, ls=ls, lw=2, label=lab))
    ax.set_xlabel("x, mm  (− = hotend side, + = belt-clamp side)")
    ax.set_ylabel("y, mm (up)")
    ax.set_title("Head projected along the X rail: white = free straight-through corridor")
    ax.grid(True, lw=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out, dpi=80)
    x, y, bw, bh = BELT_FRONT
    sub = occ[int((Y1 - y - bh) * RES):int((Y1 - y) * RES), int((x - X0) * RES):int((x + bw - X0) * RES)]
    print(f"second-run zone x[{x},{x + bw}] y[{y},{y + bh}]: {100 * sub.mean():.0f}% blocked")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
