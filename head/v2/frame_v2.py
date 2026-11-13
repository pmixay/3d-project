"""Frame v2 for the Hefest head: toolhead board on the side wall instead of on top.

Starts from the Hefest frame as exported in commit 006a50f (src/hefest_frame_006a50f.step)
and applies four changes, all in the Hefest assembly coordinates
(origin = carriage centre, +Z along the X rail, +Y up, hotend on the -X side):

  1. removes the roof shelf that carried a board on top of the head;
  2. extends the -Z side wall so it carries the whole EBB42 GEN2 V1.0 hole pattern;
  3. adds four bosses for M3 heat-set inserts on a 31 x 31 mm pattern;
  4. opens the four MGN12H carriage holes from 2.7 mm to 3.4 mm (M3 clearance).

Run:  python frame_v2.py     (needs cadquery)
"""
import os
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "hefest_frame_006a50f.step")
OUT = os.path.join(HERE, "out")

# --- existing frame (measured from the STEP) ---------------------------------
WALL_Z_OUT, WALL_Z_IN = -24.7, -20.7     # -Z side wall, 4 mm thick
ROOF_Y0 = 52.0                           # underside of the roof shelf
FRONT_X = -19.5                          # front face of the front wall
CARRIAGE_HOLES = [(-10.5, -10.0), (-10.5, 10.0), (9.5, -10.0), (9.5, 10.0)]   # (x, z)
BELT_COVER_TOP_Y = 15.0                  # belt cover must lift 7 mm off its pins to come out

# --- EBB42 GEN2 V1.0 (BigTreeTech STEP model) --------------------------------
BOARD_W, BOARD_H, BOARD_T = 40.0, 45.0, 1.6
HOLE_PITCH = 31.0
HOLE_FROM_BOTTOM = 4.44                  # hole row to the bottom edge (9.56 to the XT30 edge)
COMP_H = 8.6                             # tallest part above the board
PINS_BELOW = 2.2                         # solder pins below the board

# --- placement ---------------------------------------------------------------
BOARD_BOTTOM_Y = 23.0                    # lower edge of the board
BOARD_CX = 0.75                          # board centre along X
BOSS_H = 3.5                             # stand-off height (pins need 2.2)
BOSS_D, INSERT_D, INSERT_DEPTH = 7.0, 4.0, 6.0
WALL_REAR_X = BOARD_CX + BOARD_W / 2 + 0.5       # 21.25
WALL_TOP_Y = BOARD_BOTTOM_Y + HOLE_FROM_BOTTOM + HOLE_PITCH + 4.5
WALL_REAR_BOTTOM_Y = BOARD_BOTTOM_Y - 0.5        # keeps the belt cover removable

HOLES = [(BOARD_CX + sx * HOLE_PITCH / 2, BOARD_BOTTOM_Y + HOLE_FROM_BOTTOM + dy)
         for sx in (-1, 1) for dy in (0.0, HOLE_PITCH)]          # (x, y) of the four bosses


def build():
    frame = cq.importers.importStep(SRC)
    # 1. roof off (the side wall slab itself is kept)
    roof = cq.Workplane("XY").box(80, 20, 80, centered=False).translate((-40, ROOF_Y0, WALL_Z_IN))
    frame = frame.cut(roof)
    # 2. side wall: one flat plate behind the whole board
    pts = [(FRONT_X, ROOF_Y0 - 6), (FRONT_X, WALL_TOP_Y), (WALL_REAR_X, WALL_TOP_Y),
           (WALL_REAR_X, WALL_REAR_BOTTOM_Y + 6), (WALL_REAR_X - 6, WALL_REAR_BOTTOM_Y),
           (9.0, WALL_REAR_BOTTOM_Y), (9.0, ROOF_Y0 - 6)]
    plate = (cq.Workplane("XY").polyline(pts).close().extrude(WALL_Z_IN - WALL_Z_OUT)
             .translate((0, 0, WALL_Z_OUT)))
    frame = frame.union(plate)
    # 3. bosses with blind holes for M3 heat-set inserts
    for x, y in HOLES:
        boss = (cq.Workplane("XY").circle(BOSS_D / 2).extrude(BOSS_H)
                .translate((x, y, WALL_Z_OUT - BOSS_H)))
        frame = frame.union(boss)
    for x, y in HOLES:
        hole = (cq.Workplane("XY").circle(INSERT_D / 2).extrude(INSERT_DEPTH)
                .translate((x, y, WALL_Z_OUT - BOSS_H)))
        frame = frame.cut(hole)
    # 4. carriage holes to M3 clearance
    for x, z in CARRIAGE_HOLES:
        drill = (cq.Workplane("XZ").circle(1.7).extrude(-4.0).translate((x, 8.0, z)))
        frame = frame.cut(drill)
    return frame


def board_proxy():
    """Simple envelope of the EBB42 GEN2 in its mounted position (for clearance checks)."""
    z_board = WALL_Z_OUT - BOSS_H                      # face of the board that sits on the bosses
    x0 = BOARD_CX - BOARD_W / 2
    pcb = cq.Workplane("XY").box(BOARD_W, BOARD_H, BOARD_T, centered=False).translate(
        (x0, BOARD_BOTTOM_Y, z_board - BOARD_T))
    comps = cq.Workplane("XY").box(BOARD_W, BOARD_H, COMP_H, centered=False).translate(
        (x0, BOARD_BOTTOM_Y, z_board - BOARD_T - COMP_H))
    pins = cq.Workplane("XY").box(BOARD_W - 9, BOARD_H - 2, PINS_BELOW, centered=False).translate(
        (x0 + 4.5, BOARD_BOTTOM_Y + 1, z_board))
    return pcb.union(comps).union(pins)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    f = build()
    b = board_proxy()
    cq.exporters.export(f, os.path.join(OUT, "frame_v2.step"))
    cq.exporters.export(f, os.path.join(OUT, "frame_v2.stl"), tolerance=0.03, angularTolerance=0.2)
    cq.exporters.export(b, os.path.join(OUT, "ebb42_gen2_envelope.step"))
    cq.exporters.export(b, os.path.join(OUT, "ebb42_gen2_envelope.stl"))
    s = f.val()
    bb = s.BoundingBox()
    print(f"frame v2: solids={len(s.Solids())} volume={s.Volume() / 1000:.1f} cm3 "
          f"x[{bb.xmin:.1f},{bb.xmax:.1f}] y[{bb.ymin:.1f},{bb.ymax:.1f}] z[{bb.zmin:.1f},{bb.zmax:.1f}]")
    print("boss centres (x, y):", [(round(x, 2), round(y, 2)) for x, y in HOLES])
    bb = b.val().BoundingBox()
    print(f"board envelope: x[{bb.xmin:.1f},{bb.xmax:.1f}] y[{bb.ymin:.1f},{bb.ymax:.1f}] z[{bb.zmin:.1f},{bb.zmax:.1f}]")
