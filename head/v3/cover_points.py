"""Where the cover is screwed to the head: three M3 screws of its own, into M3 heat-set inserts.

  - two from the sides (along Z) into the lower blocks of hotend mount 2, one on each side;
  - one from above (along Y) into a boss on the inside of the frame's side wall.
Head coordinates, see probe.py.
"""
import cadquery as cq

INSERT_D, INSERT_DEPTH = 4.0, 5.5          # hole for an M3 heat-set insert (4.6 mm outside, 4-5 mm long)
SIDE_INSERT_DEPTH = 7.5                    # the side holes are deeper: an M3 x 8 through the 2.4 mm of the cover wall, pad
                                           # and gap reaches 5.6 mm into the block, 1.1 mm past the end of the insert
SCREW_D = 3.4                              # clearance hole in the cover
SCREW_LEN = 8.0                            # M3 x 8, button head

SIDE_XY = (-48.5, -39.6)                   # side screws: axis position (x, y), same on both sides
SIDE_Z = (-27.7, 28.5)                     # faces of mount 2 they go into
TOP_XZ = (8.5, -16.7)                      # top screw: axis position (x, z)
TOP_Y = 61.0                               # top of the frame boss


def xcyl(d, x0, x1, y, z):
    return cq.Workplane().add(cq.Solid.makeCylinder(d / 2, x1 - x0, cq.Vector(x0, y, z), cq.Vector(1, 0, 0)))


def ycyl(d, y0, y1, x, z):
    return cq.Workplane().add(cq.Solid.makeCylinder(d / 2, y1 - y0, cq.Vector(x, y0, z), cq.Vector(0, 1, 0)))


def zcyl(d, z0, z1, x, y):
    return cq.Workplane().add(cq.Solid.makeCylinder(d / 2, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1)))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def insert_holes_mount():
    x, y = SIDE_XY
    return [zcyl(INSERT_D, SIDE_Z[0], SIDE_Z[0] + SIDE_INSERT_DEPTH, x, y), zcyl(INSERT_D, SIDE_Z[1] - SIDE_INSERT_DEPTH, SIDE_Z[1], x, y)]


def inserts():
    """The three brass inserts, for the head model."""
    x, y = SIDE_XY
    out = []
    for body in (zcyl(4.6, SIDE_Z[0], SIDE_Z[0] + 4.5, x, y), zcyl(4.6, SIDE_Z[1] - 4.5, SIDE_Z[1], x, y),
                 ycyl(4.6, TOP_Y - 4.5, TOP_Y, *TOP_XZ)):
        out.append(body)
    out[0] = out[0].cut(zcyl(2.5, SIDE_Z[0] - 1, SIDE_Z[0] + 6, x, y))
    out[1] = out[1].cut(zcyl(2.5, SIDE_Z[1] - 6, SIDE_Z[1] + 1, x, y))
    out[2] = out[2].cut(ycyl(2.5, TOP_Y - 6, TOP_Y + 1, *TOP_XZ))
    return out


def screws(z_out, y_out):
    """The three screws in place: button heads on the outer faces of the cover (z_out = (Z0, Z1), y_out = top)."""
    x, y = SIDE_XY
    head_d, head_h = 5.7, 1.65
    return [
        zcyl(3.0, z_out[0], z_out[0] + SCREW_LEN, x, y).union(zcyl(head_d, z_out[0] - head_h, z_out[0], x, y)),
        zcyl(3.0, z_out[1] - SCREW_LEN, z_out[1], x, y).union(zcyl(head_d, z_out[1], z_out[1] + head_h, x, y)),
        ycyl(3.0, y_out - SCREW_LEN, y_out, *TOP_XZ).union(ycyl(head_d, y_out, y_out + head_h, *TOP_XZ)),
    ]
