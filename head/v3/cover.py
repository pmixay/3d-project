"""Front cover of the Hefest head with the printer name.

A shell over the 3010 hotend fan and the front of hotend mount 2.  It is held by the two
M3 clamp screws in the wings of mount 2: the cover's posts drop into their counterbores,
the screws go through the posts (about 14 mm longer than without the cover).  The lower edge stops
above the MicroProbe flange, so the probe, its arm and its cable stay free.

Run:  python3 cover.py
"""
import os

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FONT = os.path.join(HERE, "..", "..", "submission", "tools", "fonts", "Benzin-Semibold.ttf")

# what the cover goes over (head coordinates, from the assembly)
MOUNT_FRONT_X = -52.6                     # front face of hotend mount 2
FAN_FRONT_X = -62.6                       # front face of the 3010 fan
FAN_C = (-27.05, 1.15)                    # fan axis (y, z)
WING_Z = (-27.7, 28.5)                    # mount 2 across the wings
MOUNT_TOP_Y = 1.4
CLAMP = ((-30.9, -21.8), (-30.9, 22.6))   # clamp screws in the wings (y, z); counterbore 7.2 x 3 mm

GAP = 0.8                                 # to the wings and the top of the mount
WALL, PLATE = 1.6, 2.4
X_IN = FAN_FRONT_X - 1.2                  # inner face of the front plate
X_OUT = X_IN - PLATE
X_BACK = -46.0                            # the side walls reach 6.6 mm over the wings
Y_BOTTOM = -44.5                          # 1.3 mm below the probe seat, 1.9 mm above the probe connector
Z0, Z1 = WING_Z[0] - GAP - WALL, WING_Z[1] + GAP + WALL
Y_TOP = MOUNT_TOP_Y + GAP + WALL
FAN_HOLE_D = 27.0
POST_D, POST_IN_CBORE = 6.8, 2.8
SCREW_D, HEAD_D, HEAD_DEPTH = 3.4, 6.0, 3.0
TEXT, TEXT_W, TEXT_DEPTH, TEXT_Y = "HEFEST", 46.0, 0.8, -5.6


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def xcyl(d, x0, x1, y, z):
    return cq.Workplane("YZ").circle(d / 2).extrude(x1 - x0).translate((x0, y, z))


def name_plate():
    """The letters of the printer name as solids to cut from the front face, reading left to right from the front."""
    plane = cq.Plane(origin=(X_OUT, 0, (Z0 + Z1) / 2), xDir=(0, 0, 1), normal=(-1, 0, 0))
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


def build():
    shell = box(X_OUT, X_BACK, Y_BOTTOM, Y_TOP, Z0, Z1).edges("|X").edges(">Y").fillet(4.0)
    shell = shell.faces("<X").edges().chamfer(0.8)
    inner = box(X_IN, X_BACK + 1, Y_BOTTOM - 1, Y_TOP - WALL, Z0 + WALL, Z1 - WALL).edges("|X").edges(">Y").fillet(2.4)
    cover = shell.cut(inner)
    cover = cover.cut(xcyl(FAN_HOLE_D, X_OUT - 1, X_IN + 1, *FAN_C))
    for y, z in CLAMP:
        cover = cover.union(xcyl(POST_D, X_IN - 0.1, MOUNT_FRONT_X + POST_IN_CBORE, y, z))
    for y, z in CLAMP:
        cover = cover.cut(xcyl(SCREW_D, X_OUT - 1, MOUNT_FRONT_X + 5, y, z)).cut(xcyl(HEAD_D, X_OUT - 1, X_OUT + HEAD_DEPTH, y, z))
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
