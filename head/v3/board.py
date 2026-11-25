"""EBB42 GEN2 V1.0 on the side wall of the frame: the real outline of the board.

The board in the team's head assembly is a 40 x 40 mm placeholder.  The real board is
40 x 45 mm and its four holes are not centred: the edge with the XT30 is 9.56 mm above the upper
holes, the opposite edge 4.44 mm below the lower ones.  With the XT30 up, the board therefore
ends 5 mm higher than the placeholder.  Dimensions are from the official CAD
(github.com/bigtreetech/EBB, EBB_GEN2/EBB42_GEN2/CAD/EBB 42 GEN2 V1.0.step).

Head coordinates, see probe.py.  Components face outwards (-Z).
"""
import cadquery as cq

HOLES_X, HOLES_Y = (-11.0, 20.0), (25.5, 56.5)     # the four board holes in the frame wall (frame_v3.py)
WALL_OUT_Z = -24.7                                  # outer face of the frame's side wall
STANDOFF = 3.0
PCB_T = 1.6
BACK_Z = WALL_OUT_Z - STANDOFF                      # -27.7: back face of the board
FRONT_Z = BACK_Z - PCB_T                            # -29.3: component face

EDGE_X = 4.5                                        # board edge beyond the holes, both sides
EDGE_TOP, EDGE_BOTTOM = 9.56, 4.44                  # above the upper holes (XT30 edge), below the lower ones
CHAMFER = 4.0                                       # the four corners are cut at 45 degrees
X0, X1 = HOLES_X[0] - EDGE_X, HOLES_X[1] + EDGE_X                   # -15.5 .. 24.5
Y0, Y1 = HOLES_Y[0] - EDGE_BOTTOM, HOLES_Y[1] + EDGE_TOP            # 21.06 .. 66.06

# parts on the component face: (x0, x1, y0, y1, height)
XT30 = (-5.15, 8.25, 54.19, 66.87, 5.4)             # power and CAN/USB input, on the top edge
PROBE_PORT = (-1.51, 10.49, 21.32, 26.02, 6.0)      # 5-pin PH2.0 header on the bottom edge, plugged from the -Z side
HEATER_TERMINAL = (-15.5, -8.1, 28.5, 35.8, 8.6)    # the tallest part; its pins stick 2.2 mm out of the back
TOP_Y = XT30[3]                                     # 66.87: the highest point of the board

PROBE_PORT_C = ((PROBE_PORT[0] + PROBE_PORT[1]) / 2, (PROBE_PORT[2] + PROBE_PORT[3]) / 2, FRONT_Z - PROBE_PORT[4])


def _block(x0, x1, y0, y1, h):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, h, centered=False).translate((x0, y0, FRONT_Z - h))


def build():
    """The board plate with its three largest parts, in place on the frame."""
    c = CHAMFER
    outline = [(X0, Y0 + c), (X0, Y1 - c), (X0 + c, Y1), (X1 - c, Y1), (X1, Y1 - c), (X1, Y0 + c), (X1 - c, Y0), (X0 + c, Y0)]
    board = cq.Workplane("XY").polyline(outline).close().extrude(PCB_T).translate((0, 0, FRONT_Z))
    for part in (XT30, PROBE_PORT, HEATER_TERMINAL):
        board = board.union(_block(*part))
    return board


if __name__ == "__main__":
    b = build().val().BoundingBox()
    print(f"EBB42 GEN2 on the frame: x[{b.xmin:.2f},{b.xmax:.2f}] y[{b.ymin:.2f},{b.ymax:.2f}] z[{b.zmin:.2f},{b.zmax:.2f}]")
    print(f"PROBE port (x, y, z of its open end): {PROBE_PORT_C[0]:.1f}, {PROBE_PORT_C[1]:.1f}, {PROBE_PORT_C[2]:.1f}")
