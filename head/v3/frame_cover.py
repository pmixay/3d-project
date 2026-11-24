"""Frame v3 with a boss for the cover's top screw.

Frame v3 (frame_v3.py) plus one boss on the inside of the side wall, at its top edge, with a hole
for an M3 heat-set insert from above.  The underside of the boss slopes at 45 degrees, so it
prints without support whichever way the frame lies.

Run:  python3 frame_cover.py
"""
import os

import cadquery as cq

import cover_points as CP
import frame_v3

OUT = frame_v3.OUT
WALL_IN_Z = -20.7                          # inner face of the side wall (the wall is 4 mm thick)
BOSS = 8.0                                 # boss width along X and reach from the wall


def build():
    frame, _ = frame_v3.build()
    x, z = CP.TOP_XZ
    y, z1 = CP.TOP_Y, WALL_IN_Z + BOSS
    side = [(y, WALL_IN_Z - 1), (y, z1), (y - BOSS, z1), (y - BOSS - (z1 - WALL_IN_Z + 1), WALL_IN_Z - 1)]     # (y, z) outline
    boss = cq.Workplane("YZ").polyline(side).close().extrude(BOSS).translate((x - BOSS / 2, 0, 0))
    frame = frame.union(boss, clean=True)
    return frame.cut(CP.ycyl(CP.INSERT_D, y - CP.INSERT_DEPTH, y + 1, x, z))


if __name__ == "__main__":
    f = build()
    cq.exporters.export(f, os.path.join(OUT, "frame_v3_cover.step"))
    cq.exporters.export(f, os.path.join(OUT, "frame_v3_cover.stl"), tolerance=0.03, angularTolerance=0.2)
    s = f.val()
    b = s.BoundingBox()
    assert s.isValid() and len(s.Solids()) == 1
    print(f"frame v3 with cover boss: solids={len(s.Solids())} volume={s.Volume() / 1000:.3f} cm3 "
          f"x[{b.xmin:.1f},{b.xmax:.1f}] y[{b.ymin:.1f},{b.ymax:.1f}] z[{b.zmin:.1f},{b.zmax:.1f}]")
