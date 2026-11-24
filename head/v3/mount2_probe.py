"""Hotend mount 2 with a seat for the BIQU MicroProbe V2.

Starts from "Крепление хотенда 2" of the team's head assembly (KAPACbik/Hefest, Side-PCB-test,
18697e8; stored as src/hotend_mount_2_kapacbik.step, head coordinates) and adds, at the lower
corner on the board side (-Z):
  1. a block under the wing, flush with the mount's front and rear faces;
  2. an arm that runs forward beside the 3010 fan;
  3. two blind holes for the M2.5 screws of the probe, from below.
The mating faces, the fan seat and the clamp-screw holes are untouched.

Run:  python3 mount2_probe.py
"""
import os

import cadquery as cq

import probe as P

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "hotend_mount_2_kapacbik.step")
OUT = os.path.join(HERE, "out")

FRONT_X, REAR_X = -52.6, -40.6            # front and rear faces of the mount
SIDE_Z = -27.7                             # outer (-Z) face of the wing
BLOCK_Z1, BLOCK_TOP_Y = -12.5, -36.0       # the block stays 1.5 mm below the clamp-screw counterbore
ARM_FRONT_X = P.HOLE_X[1] - 2.5            # the arm ends flush with the end of the probe flange
ARM_Z1, ARM_TOP_Y = -14.7, -37.0           # 0.8 mm from the fan; below the clamp-screw head
SCREW_D, SCREW_DEPTH = 2.2, 5.5            # M2.5 x 6 straight into the plastic (2.1 mm flange + 3.9 mm thread)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def build():
    mount = cq.importers.importStep(SRC)
    block = box(FRONT_X, REAR_X, P.SEAT_Y, BLOCK_TOP_Y, SIDE_Z, BLOCK_Z1)
    arm = box(ARM_FRONT_X, FRONT_X, P.SEAT_Y, ARM_TOP_Y, SIDE_Z, ARM_Z1).edges("|Y").edges("<X").fillet(2.0)
    mount = mount.union(block, clean=True).union(arm, clean=True)
    for x in P.HOLE_X:
        hole = (cq.Workplane("XZ").circle(SCREW_D / 2).extrude(-SCREW_DEPTH)      # XZ extrudes towards -Y
                .translate((x, P.SEAT_Y, P.HOLE_Z)))
        mount = mount.cut(hole)
    return mount


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    src = cq.importers.importStep(SRC).val()
    m = build()
    cq.exporters.export(m, os.path.join(OUT, "hotend_mount_2_probe.step"))
    cq.exporters.export(m, os.path.join(OUT, "hotend_mount_2_probe.stl"), tolerance=0.03, angularTolerance=0.2)
    s = m.val()
    b = s.BoundingBox()
    assert s.isValid() and len(s.Solids()) == 1
    print(f"mount 2 with probe seat: solids={len(s.Solids())} volume={s.Volume() / 1000:.2f} cm3 (source {src.Volume() / 1000:.2f} cm3) "
          f"x[{b.xmin:.1f},{b.xmax:.1f}] y[{b.ymin:.1f},{b.ymax:.1f}] z[{b.zmin:.1f},{b.zmax:.1f}]")
