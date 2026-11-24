"""BIQU MicroProbe V2 on the Hefest head: where it sits and the numbers the parts share.

Head coordinates: origin at the MGN12H carriage centre, +Z along the X rail, +Y up,
hotend on the -X side.  Nozzle tip at (-38.9, -69.8, 0.1).

Probe dimensions are from the MicroProbe V2 manual (v1.11, p.5) and the official mockup
(src/biqu_microprobe_mockup.step, github.com/bigtreetech/MicroProbe):
two 2.7 mm holes 17 mm apart in a 2.1 mm flange on top, M2.5 screws from below;
from the flange top down: body bottom 23.98, pin retracted 25.30, trigger 27.58, pin extended 28.10.
"""
import os

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
MOCKUP = os.path.join(HERE, "src", "biqu_microprobe_mockup.step")

NOZZLE = (-38.9, -69.8, 0.1)              # nozzle tip (x, y, z)

HOLE_PITCH = 16.92                         # between the two flange holes (mockup; 17.0 in the manual)
PIN_FROM_HOLES = 2.75                      # pin axis in front of the hole line
FLANGE_T = 2.1
BODY_BOTTOM, PIN_RETRACTED, PIN_TRIGGER, PIN_EXTENDED = 23.98, 25.30, 27.58, 28.10   # below the flange top

# the nozzle sits between "pin retracted" and "trigger": 1.3 mm above the retracted pin
# and 1.0 mm above the trigger point; the extended pin ends 1.5 mm below the nozzle
SEAT_Y = NOZZLE[1] - 1.5 + PIN_EXTENDED    # -43.2: flange top = underside of the mount
HOLE_Z = -20.5                             # the hole line runs along X at this z
HOLE_X = (-44.0, -44.0 - HOLE_PITCH)       # rear hole under mount 2, front hole under the new arm
PIN = ((HOLE_X[0] + HOLE_X[1]) / 2, HOLE_Z + PIN_FROM_HOLES)     # pin axis (x, z)

# mockup coordinates of the same features
_M_HOLE_X, _M_HOLE_ZC, _M_TOP_Y = -38.04, 9.66, 21.27


def probe_model():
    """The mockup in its mounted position, pin cut to the extended length."""
    m = cq.importers.importStep(MOCKUP)
    m = (m.translate((-_M_HOLE_X, -_M_TOP_Y, -_M_HOLE_ZC))
          .rotate((0, 0, 0), (0, 1, 0), -90)            # hole line -> X, pin towards +Z (the nozzle), connector towards -Z
          .translate((PIN[0], SEAT_Y, HOLE_Z)))
    keep = cq.Workplane("XY").box(60, PIN_EXTENDED, 60, centered=(True, False, True)).translate((PIN[0], SEAT_Y - PIN_EXTENDED, HOLE_Z))
    return m.intersect(keep)


if __name__ == "__main__":
    p = probe_model().val()
    b = p.BoundingBox()
    print(f"seat y={SEAT_Y:.2f}  holes x={HOLE_X[0]:.2f}, {HOLE_X[1]:.2f} z={HOLE_Z}  pin x={PIN[0]:.2f} z={PIN[1]:.2f}")
    print(f"pin offset from the nozzle: dx={PIN[0] - NOZZLE[0]:.2f} dz={PIN[1] - NOZZLE[2]:.2f}")
    print(f"probe bbox x[{b.xmin:.2f},{b.xmax:.2f}] y[{b.ymin:.2f},{b.ymax:.2f}] z[{b.zmin:.2f},{b.zmax:.2f}]")
