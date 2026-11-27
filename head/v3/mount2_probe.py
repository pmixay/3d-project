"""Hotend mount 2 with a seat for the BIQU MicroProbe V2.

Starts from "Крепление хотенда 2" of the team's head assembly (KAPACbik/Hefest, Side-PCB-test,
18697e8; stored as src/hotend_mount_2_kapacbik.step, head coordinates) and adds, at the lower
corner on the board side (-Z):
  1. a block under the wing, flush with the mount's front and rear faces;
  2. an arm that runs forward beside the 3010 fan;
  3. two blind holes for the M2.5 screws of the probe, from below;
and, for the cover (cover.py), a matching block on the other side (+Z) and one hole for an M3
heat-set insert in the side face of each block.
The mating faces, the fan seat and the clamp-screw holes are untouched.

Printing: the arm reaches 10.8 mm past the front face, so the part cannot lie on that face.  Print it
with the rear mating face (x = -40.6) on the bed, arm up; the hotend bore then faces the bed and wants
supports from the build plate.

Run:  python3 mount2_probe.py
"""
import os

import cadquery as cq

import cover_points as CP
import probe as P

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "hotend_mount_2_kapacbik.step")
OUT = os.path.join(HERE, "out")

FRONT_X, REAR_X = -52.6, -40.6            # front and rear faces of the mount
SIDE_Z = -27.7                             # outer (-Z) face of the wing
SIDE_Z_PLUS, BLOCK_PLUS_Z0 = 28.5, 17.5    # the +Z block: outer face of that wing, inner face clear of the fan screw
BLOCK_Z1, BLOCK_TOP_Y = -12.5, -36.0       # the block stays 1.5 mm below the clamp-screw counterbore
ARM_FRONT_X = P.HOLE_X[1] - 2.5            # the arm ends flush with the end of the probe flange
ARM_Z1, ARM_TOP_Y = -14.7, -37.0           # 0.8 mm from the fan; below the clamp-screw head
SCREW_D, SCREW_DEPTH = 2.2, 5.5            # M2.5 straight into the plastic: x 6 (2.1 mm flange + 3.9 mm thread) or the
                                           # M2.5 x 5 from the probe's box (2.9 mm thread)


box = CP.box


def build():
    mount = cq.importers.importStep(SRC)
    block = box(FRONT_X, REAR_X, P.SEAT_Y, BLOCK_TOP_Y, SIDE_Z, BLOCK_Z1)
    arm = box(ARM_FRONT_X, FRONT_X, P.SEAT_Y, ARM_TOP_Y, SIDE_Z, ARM_Z1).edges("|Y").edges("<X").fillet(2.0)
    block_plus = box(FRONT_X, REAR_X, P.SEAT_Y, BLOCK_TOP_Y, BLOCK_PLUS_Z0, SIDE_Z_PLUS)
    mount = mount.union(block, clean=True).union(arm, clean=True).union(block_plus, clean=True)
    for x in P.HOLE_X:                     # probe screws, from the seat upwards
        mount = mount.cut(CP.ycyl(SCREW_D, P.SEAT_Y, P.SEAT_Y + SCREW_DEPTH, x, P.HOLE_Z))
    for hole in CP.insert_holes_mount():   # cover screws, from the sides
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
