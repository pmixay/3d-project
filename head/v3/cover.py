"""Cover of the Hefest head with the printer name.

One shell that slides on from the front and closes the head in front of and above the X rail:
a nose over the 3010 hotend fan and the hotend mounts, and a taller box over the extruder,
the NEMA14 and the frame.  The back is open.  Left open on purpose:
  - a window in front of the extruder (lever and gears stay reachable and visible);
  - the EBB42 GEN2 side: the board with its connectors and wiring stands outside the shell;
  - a slot in the top over the whole board: the real board (board.py) ends 1.3 mm above the cover,
    its XT30 2.1 mm above; a hole for the filament;
  - everything below the lower edge: the MicroProbe, its arm and cable, the nozzle, the duct.
The -Z wall carries two pairs of slots for cable ties: the probe lead (and the hotend wires) go up
this wall to the board, in front of the belt and above it.
The side walls stop above the rail and the belts.  The part under the rail (triangle, 5015
blower) is not covered: a shell there cannot be one piece with this one, and the blower needs air.

Fixing: three M3 x 8 screws of its own into heat-set inserts (cover_points.py) - two through the
side walls into the lower blocks of hotend mount 2 (mount2_probe.py), one through the top into
a boss on the frame (frame_cover.py).

Printing: top face on the bed, no supports.  Every wall is vertical in that position, the nose
grows out of the front wall along a 45 degree slope, the extruder window ends in a 45 degree
point, and nothing hangs from the inside.  print_check.py verifies this on the STL.

Run:  python3 cover.py
"""
import os

import cadquery as cq

import board as B
import cover_points as CP

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FONT = os.path.join(HERE, "..", "..", "submission", "tools", "fonts", "Benzin-Semibold.ttf")

# what the cover goes over (head coordinates, from the assembly)
MOUNT_FRONT_X = -52.6                     # front face of hotend mount 2
FAN_FRONT_X = -62.6                       # front face of the 3010 fan
FAN_C = (-27.05, 1.15)                    # fan axis (y, z)
WING_Z = (-27.7, 28.5)                    # hotend mounts across the wings
MOUNT_TOP_Y = 1.4                         # top of hotend mount 2
EXTRUDER_FRONT_X = -45.4                  # front of the K3D Minifeeder
HEAD_TOP_Y = 62.4                         # the inner top face is GAP above this: 2.2 mm over the frame (61.0)
FRAME_REAR_X = 27.0
FILAMENT = (-38.9, 0.1)                   # filament axis (x, z)
GAP = 0.8                                 # to the wings and the top of mount 2
WALL, PLATE = 1.6, 2.4
X_IN = FAN_FRONT_X - 1.2                  # inner face of the nose front plate
X_OUT = X_IN - PLATE
X_UP_IN = EXTRUDER_FRONT_X - 1.0          # inner face of the upper front wall
X_UP_OUT = X_UP_IN - WALL
X_RAIL = -23.0                            # below RAIL_Y the side walls end here: 8 mm in front of the front belt run
X_BACK = FRAME_REAR_X + 2.0
Y_BOTTOM = -44.5                          # 1.3 mm below the probe seat, 1.9 mm above the probe connector
Y_SLOPE = 11.0                            # the 45 degree slope of the nose starts here on the upper front wall
Y_RAIL = 16.0                             # lower edge of the side walls behind X_RAIL: 1 mm above the belt cover
Y_TOP = HEAD_TOP_Y + GAP + WALL
Z0, Z1 = WING_Z[0] - GAP - WALL, WING_Z[1] + GAP + WALL
FAN_HOLE_D, FAN_RIM = 27.0, 2.0            # opening for the fan; rim left below it
PAD_D, SIDE_PAD = 9.0, 0.6                # pads under the screws: the side ones take up most of GAP
WINDOW_Y, WINDOW_Z = (14.0, 46.0), (-17.0, 20.0)         # extruder window in the upper front wall; its lower end is a 45 degree point
BOARD_X = B.X0 - 1.5                                     # -17.0: the -Z wall ends here: behind it is the board
PLUG_SLOT_X, PLUG_SLOT_Z = BOARD_X, -22.5                # slot in the top over the board and its XT30 plug, open to the back
TIE_POINTS = ((-44.0, -12.0), (-29.0, 18.0))             # cable ties on the -Z wall (x, y): at least 12 mm free behind the wall
TIE_SLOT, TIE_PITCH = (1.8, 4.0), 7.0                    # slot (along X, along Y); the two slots of a pair are TIE_PITCH apart
FILAMENT_HOLE_D = 10.0
TEXT, TEXT_W, TEXT_DEPTH, TEXT_Y = "HEFEST", 52.0, 0.8, 54.8


box, xcyl, ycyl, zcyl = CP.box, CP.xcyl, CP.ycyl, CP.zcyl


def name_plate():
    """The letters of the printer name as solids to cut from the front face, reading left to right from the front."""
    plane = cq.Plane(origin=(X_UP_OUT, 0, (Z0 + Z1) / 2), xDir=(0, 0, 1), normal=(-1, 0, 0))
    size = 8.0
    for _ in range(2):                    # scale the font so the word is TEXT_W wide
        t = cq.Workplane(plane).text(TEXT, size, -TEXT_DEPTH, fontPath=FONT, halign="center", valign="center", combine=False)
        b = t.val().BoundingBox()
        size *= TEXT_W / (b.zmax - b.zmin)
    dy = TEXT_Y - (b.ymin + b.ymax) / 2
    letters = []
    for glyph in t.val().Solids():
        # rebuild each letter from its outline alone: the font's "T" carries a stray contour that breaks the solid
        # (fine for this word, none of its letters has a hole)
        front = min((f for f in glyph.Faces() if abs(f.normalAt().x) > 0.99), key=lambda f: f.Center().x)
        face = cq.Face.makeFromWires(front.outerWire())
        letters.append(cq.Solid.extrudeLinear(face, cq.Vector(TEXT_DEPTH, 0, 0)).translate((0, dy, 0)))
    return letters


def profile(pts, z0, z1):
    """A side-view outline (x, y) extruded along Z."""
    return cq.Workplane("XY").polyline(pts).close().extrude(z1 - z0).translate((0, 0, z0))


def side_profile(x_nose, x_up, y_bottom, y_slope, y_top, x_back, closed_back):
    """Side-view outline (x, y): nose front, 45 degree slope, upper front wall, top, and the step over the rail."""
    pts = [(x_nose, y_bottom), (x_nose, y_slope - (x_up - x_nose)), (x_up, y_slope), (x_up, y_top), (x_back, y_top)]
    return pts + ([(x_back, Y_RAIL), (X_RAIL, Y_RAIL), (X_RAIL, y_bottom)] if closed_back else [(x_back, y_bottom)])


def front_cut(x_in, thickness, pts):
    """A (z, y) outline cut through a front wall whose inner face is at x_in."""
    plane = cq.Plane(origin=(x_in + 1, 0, 0), xDir=(0, 0, 1), normal=(-1, 0, 0))      # local x = +Z, local y = +Y
    return cq.Workplane(plane).polyline(pts).close().extrude(thickness + 2)


def window():
    """Extruder window: a rectangle whose lower end is a 45 degree point (so it prints without a bridge)."""
    (y0, y1), (z0, z1) = WINDOW_Y, WINDOW_Z
    half = (z1 - z0) / 2
    return front_cut(X_UP_IN, WALL, [(z0, y1), (z1, y1), (z1, y0 + half), ((z0 + z1) / 2, y0), (z0, y0 + half)])


def fan_opening():
    """Round opening for the 3010 fan; its lower end runs out at 45 degrees to a short flat (a 7 mm bridge in print)."""
    yc, zc = FAN_C
    r, s = FAN_HOLE_D / 2, (FAN_HOLE_D / 2) * 2 ** -0.5
    flat_y = Y_BOTTOM + FAN_RIM
    half = s - ((yc - s) - flat_y)          # half-width left where the 45 degree sides reach the flat
    tail = front_cut(X_IN, PLATE, [(zc - s, yc - s), (zc + s, yc - s), (zc + half, flat_y), (zc - half, flat_y)])
    return xcyl(FAN_HOLE_D, X_OUT - 1, X_IN + 1, yc, zc).union(tail)


def build():
    outer = profile(side_profile(X_OUT, X_UP_OUT, Y_BOTTOM, Y_SLOPE, Y_TOP, X_BACK, True), Z0, Z1)
    outer = outer.edges("|Z").edges(">Y").chamfer(2.0).faces("|Z").edges().chamfer(0.8)
    slope_wall = WALL * 2 ** 0.5           # keeps the sloped wall as thick as the others
    inner = profile(side_profile(X_IN, X_UP_IN, Y_BOTTOM - 1, Y_SLOPE - slope_wall + (PLATE - WALL), Y_TOP - WALL, X_BACK + 1, False),
                    Z0 + WALL, Z1 - WALL)
    cover = outer.cut(inner)
    cover = cover.cut(fan_opening())
    cover = cover.cut(window())
    cover = cover.cut(box(BOARD_X, X_BACK + 1, Y_BOTTOM - 1, Y_TOP - WALL, Z0 - 1, Z0 + WALL + 1))
    cover = cover.cut(box(PLUG_SLOT_X, X_BACK + 1, Y_TOP - WALL - 1, Y_TOP + 1, Z0 - 1, PLUG_SLOT_Z))
    cover = cover.cut(ycyl(FILAMENT_HOLE_D, Y_TOP - WALL - 1, Y_TOP + 1, *FILAMENT))
    for x, y in TIE_POINTS:
        for dx in (-TIE_PITCH / 2, TIE_PITCH / 2):
            cover = cover.cut(box(x + dx - TIE_SLOT[0] / 2, x + dx + TIE_SLOT[0] / 2, y - TIE_SLOT[1] / 2, y + TIE_SLOT[1] / 2,
                                  Z0 - 1, Z0 + WALL + 1))
    # screw points: a pad inside the wall and a clearance hole through it
    x, y = CP.SIDE_XY
    cover = cover.union(zcyl(PAD_D, Z0 + WALL - 0.1, Z0 + WALL + SIDE_PAD, x, y)).union(zcyl(PAD_D, Z1 - WALL - SIDE_PAD, Z1 - WALL + 0.1, x, y))
    cover = cover.union(ycyl(PAD_D, CP.TOP_Y + 0.1, Y_TOP - WALL + 0.1, *CP.TOP_XZ))
    cover = cover.cut(zcyl(CP.SCREW_D, Z0 - 1, Z0 + WALL + 2, x, y)).cut(zcyl(CP.SCREW_D, Z1 - WALL - 2, Z1 + 1, x, y))
    cover = cover.cut(ycyl(CP.SCREW_D, CP.TOP_Y - 1, Y_TOP + 1, *CP.TOP_XZ))
    for letter in name_plate():
        assert letter.isValid() and letter.Volume() > 0
        cover = cover.cut(letter)
    return cover


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    c = build()
    cq.exporters.export(c, os.path.join(OUT, "head_cover.step"))
    cq.exporters.export(c, os.path.join(OUT, "head_cover.stl"), tolerance=0.02, angularTolerance=0.15)
    s = c.val()
    b = s.BoundingBox()
    assert s.isValid() and len(s.Solids()) == 1
    print(f"head cover: solids={len(s.Solids())} volume={s.Volume() / 1000:.2f} cm3 "
          f"x[{b.xmin:.1f},{b.xmax:.1f}] y[{b.ymin:.1f},{b.ymax:.1f}] z[{b.zmin:.1f},{b.zmax:.1f}]")
