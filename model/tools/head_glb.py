"""Build model/parts/hefest_head.glb: the Hefest print head as a coloured mesh, in head coordinates.

Head coordinates (as in the team's KOMPAS assembly): origin at the MGN12H carriage centre,
+Z along the X rail, +Y up, hotend on the -X side.  The carriage top face is at y = 9.

Inputs
  parts_dir   folder with the solids of the team's assembly export ("Hefest extruder.stp"),
              split into .brep files by assembly node (printed_00 ... printed_05, ANY*, accel ...)
  frame_v2    head/v2/out/frame_v2.step (replaces the original frame, printed_05)

What goes in: frame v2, the other printed parts, CHC Pro hotend with the Volcano nozzle,
K3D Minifeeder, NEMA14, both fans, screws, and a simplified EBB42 GEN2 on the side wall.
What is left out: the original frame with the roof shelf, the board that sat on that shelf,
the S2DW accelerometer and its plate (the EBB42 GEN2 has its own), and the carriage block
(the printer model has its own).

Run:  python model/tools/head_glb.py <parts_dir> head/v2/out/frame_v2.step model/parts/hefest_head.glb
"""
import os
import sys

import cadquery as cq

parts_dir, frame_v2, out = sys.argv[1:4]

PRINTED = (0.14, 0.14, 0.15)
C = {
    "printed": PRINTED,
    "black": (0.07, 0.07, 0.08),
    "alu": (0.86, 0.87, 0.88),
    "steel": (0.78, 0.80, 0.82),
    "brass": (0.80, 0.62, 0.20),
    "ceramic": (0.93, 0.93, 0.90),
    "pcb": (0.05, 0.05, 0.06),
    "white": (0.93, 0.93, 0.90),
    "xt30": (0.95, 0.75, 0.10),
    "terminal": (0.20, 0.60, 0.25),
}
assy = cq.Assembly(name="hefest_head")


def add(name, shape, col):
    assy.add(shape, name=name, color=cq.Color(*C[col], 1))


def load(name):
    return cq.importers.importBrep(os.path.join(parts_dir, name + ".brep"))


def solids(name):
    return load(name).solids().vals()


# printed parts (frame v2 instead of printed_05)
add("head_frame_v2", cq.importers.importStep(frame_v2), "printed")
for name, label in (("printed_00", "head_belt_cover_pin"), ("printed_04", "head_belt_cover"),
                    ("printed_01", "head_hotend_mount_1"), ("printed_02", "head_hotend_mount_2"),
                    ("printed_03", "head_triangle"), ("ANY_0_1_1_122", "head_duct"), ("ANY_0_1_1_123", "head_duct_tubes")):
    add(label, load(name), "printed")

# K3D Minifeeder (printed body and lever)
add("head_minifeeder", load("ANY_Minifeeder_MF3_Minifeeder_3"), "printed")

# CHC Pro hotend: heatsink, heater, small parts; Volcano nozzle
chc = solids("ANY_ANY")
add("head_chc_heatsink", cq.Workplane().add(chc[4]), "alu")
add("head_chc_heater", cq.Workplane().add([chc[i] for i in (0, 2, 6)]), "ceramic")
add("head_chc_parts", cq.Workplane().add([chc[i] for i in (1, 3, 5, 7, 8, 9)]), "steel")
add("head_nozzle_volcano", load("ANY_ANY_Volcano_HOTEND_v1"), "brass")

# loose components: keep everything below the old roof shelf (y < 55)
motor, fans, screws = [], [], []
for s in solids("ANY"):
    b = s.BoundingBox()
    if b.ymin > 55:          # the board on the old roof shelf and its connectors
        continue
    v = s.Volume() / 1000
    if v > 15:
        motor.append(s)
    elif v > 1:
        fans.append(s)
    else:
        screws.append(s)
add("head_nema14", cq.Workplane().add(motor), "black")
add("head_fans", cq.Workplane().add(fans), "black")
add("head_screws", cq.Workplane().add(screws), "steel")

# simplified EBB42 GEN2 V1.0 on the -Z side wall of frame v2 (placement as in frame_v2.py)
BOARD_W, BOARD_H, BOARD_T = 40.0, 45.0, 1.6
BOARD_BOTTOM_Y, BOARD_CX = 23.0, 0.75
Z_BOARD = -24.7 - 3.5                      # board face that sits on the bosses
x0, x1 = BOARD_CX - BOARD_W / 2, BOARD_CX + BOARD_W / 2
y0, y1 = BOARD_BOTTOM_Y, BOARD_BOTTOM_Y + BOARD_H
zb = Z_BOARD - BOARD_T                      # component side faces -Z


def box(xa, xb, ya, yb, za, zc):
    return cq.Workplane("XY").box(xb - xa, yb - ya, zc - za, centered=False).translate((xa, ya, za))


pcb = box(x0, x1, y0, y1, zb, Z_BOARD)
for hx in (x0 + 4.5, x1 - 4.5):
    for hy in (y0 + 4.44, y0 + 4.44 + 31):
        pcb = pcb.cut(cq.Workplane("XY").circle(1.55).extrude(4).translate((hx, hy, zb - 1)))
add("head_ebb42_gen2_pcb", pcb, "pcb")
add("head_ebb42_gen2_xt30", box(-8.95, 4.45, y1 - 11.9, y1 + 0.8, zb - 5.4, zb), "xt30")
conn = [box(x0 + 1.0, x0 + 7.0, y0 + 9, y0 + 21, zb - 6.0, zb),      # motor
        box(x0 + 1.0, x0 + 7.0, y0 + 24, y0 + 31, zb - 6.0, zb),     # fans
        box(x0 + 9.0, x0 + 21.0, y0 + 1.0, y0 + 7.0, zb - 6.0, zb),  # probe
        box(x0 + 23.0, x0 + 30.0, y0 + 1.0, y0 + 7.0, zb - 6.0, zb)]  # thermistor
add("head_ebb42_gen2_connectors", cq.Workplane().add([c.val() for c in conn]), "white")
add("head_ebb42_gen2_heater_terminal", box(x1 - 8.0, x1 - 0.5, y0 + 14, y0 + 26, zb - 8.6, zb), "terminal")
add("head_ebb42_gen2_chips", box(-6, 2, y0 + 16, y0 + 24, zb - 1.2, zb).union(box(4, 10, y0 + 18, y0 + 24, zb - 1.2, zb)), "black")
add("head_ebb42_gen2_screws", cq.Workplane().add(
    [cq.Workplane("XY").circle(2.75).extrude(2.5).translate((hx, hy, zb - 2.5)).val()
     for hx in (x0 + 4.5, x1 - 4.5) for hy in (y0 + 4.44, y0 + 35.44)]), "steel")

os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
assy.export(out, tolerance=0.08, angularTolerance=0.35)
print("saved", out, os.path.getsize(out) // 1024, "KB")
