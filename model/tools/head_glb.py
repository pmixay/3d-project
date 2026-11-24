"""Build model/parts/hefest_head.glb: the Hefest print head as a coloured mesh, in head coordinates.

Head coordinates (as in the team's KOMPAS assembly): origin at the MGN12H carriage centre,
+Z along the X rail, +Y up, hotend on the -X side.  The carriage top face is at y = 9.

Inputs
  parts_dir   the team's assembly export ("Сборка/Hefest extruder.stp", KAPACbik/Hefest, branch
              Side-PCB-test, 18697e8) split into .brep files by split_assy.py
  head/v3     frame v3 with the cover boss, hotend mount 2 with the MicroProbe seat, the probe, the cover

What goes in: everything in the assembly except the carriage block (the printer model has its
own), with the frame and hotend mount 2 replaced by their v3 versions, plus the BIQU MicroProbe
and the cover with its three screws (nodes "head_cover*", so that renders can hide them).
With --by-part the printed parts get one colour each, as in the CAD screenshots.

Run:  python model/tools/head_glb.py <parts_dir> model/parts/hefest_head.glb [--by-part] [--exploded]
"""
import json
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.join(HERE, "..", "..", "head", "v3")
sys.path.insert(0, V3)
import cover            # noqa: E402
import cover_points     # noqa: E402
import frame_cover      # noqa: E402
import mount2_probe     # noqa: E402
import probe            # noqa: E402

parts_dir, out = sys.argv[1:3]
by_part = "--by-part" in sys.argv

PRINTED = (0.14, 0.14, 0.15)
C = {
    "printed": PRINTED,
    "black": (0.07, 0.07, 0.08),
    "alu": (0.86, 0.87, 0.88),
    "steel": (0.78, 0.80, 0.82),
    "brass": (0.80, 0.62, 0.20),
    "ceramic": (0.93, 0.93, 0.90),
    "sock": (0.62, 0.12, 0.10),
    "pcb": (0.05, 0.05, 0.06),
    "white": (0.93, 0.93, 0.90),
    "xt30": (0.95, 0.75, 0.10),
    "terminal": (0.20, 0.60, 0.25),
    "probe": (0.90, 0.45, 0.08),
    "screw": (0.78, 0.80, 0.82),
    # one colour per printed part (--by-part)
    "frame": (0.16, 0.32, 0.62), "belt_cover": (0.80, 0.42, 0.12), "mount1": (0.25, 0.60, 0.33), "mount2": (0.20, 0.62, 0.62),
    "triangle": (0.66, 0.20, 0.16), "duct": (0.85, 0.68, 0.15), "minifeeder": (0.55, 0.75, 0.25), "cover": (0.88, 0.89, 0.90),
}
assy = cq.Assembly(name="hefest_head")


def add(name, shape, col, part=None):
    key = part if by_part and part else col
    assy.add(shape, name=name, color=cq.Color(*C[key], 1))


index = {r["i"]: r for r in json.load(open(os.path.join(parts_dir, "index.json")))}


def load(i):
    return cq.importers.importBrep(os.path.join(parts_dir, index[i]["file"])).val()


def wp(shapes):
    return cq.Workplane().add(shapes if isinstance(shapes, list) else [shapes])


# printed parts of the assembly: group 28 holds belt cover (2 pieces), hotend mount 1, hotend mount 2, triangle,
# and, as open shells, the duct and the frame
g = load(28)
s = g.Solids()
in_solids = {sh.hashCode() for sol in s for sh in sol.Shells()}
free = [sh for sh in g.Shells() if sh.hashCode() not in in_solids and len(sh.Faces()) > 10]
duct_shell = min(free, key=lambda sh: sh.BoundingBox().ymin)          # the other free shell is the original frame
add("head_frame_v3", frame_cover.build(), "printed", "frame")
add("head_belt_cover", wp([s[0], s[3]]), "printed", "belt_cover")
add("head_hotend_mount_1", wp(s[1]), "printed", "mount1")
add("head_hotend_mount_2_probe", mount2_probe.build(), "printed", "mount2")
add("head_triangle", wp(s[4]), "printed", "triangle")
add("head_duct", wp([duct_shell, load(21)] + load(25).Solids()), "printed", "duct")
add("head_minifeeder", wp([load(3), load(4), load(5)]), "printed", "minifeeder")

# CHC Pro hotend with the Volcano nozzle (items 10 and 11 are a second, overlapping nozzle model: left out)
add("head_chc_heatsink", wp(load(12)), "alu")
add("head_chc_heater", wp([load(6), load(14)]), "ceramic")
add("head_chc_sock", wp(load(8)), "sock")
add("head_chc_parts", wp([load(i) for i in (7, 9, 13, 16, 17)]), "steel")
add("head_nozzle_volcano", wp(load(15)), "brass")

add("head_nema14", wp(load(0)), "black")
fan5015 = load(20).Solids()
add("head_fans", wp([load(19)] + fan5015[:2]), "black")
add("head_screws", wp(fan5015[2:]), "steel")
add("head_inserts", wp([load(i) for i in (18, 22, 23)]), "brass")      # item 24 is a loose nut floating beside the belt cover

# EBB42 GEN2 on the side wall
board = load(27).Solids()
big = sorted(board, key=lambda b: -b.Volume())
pcb, xt30 = big[0], big[1]
terminal = min((b for b in board if b.Volume() > 200 and b is not pcb and b is not xt30), key=lambda b: b.BoundingBox().ymin)
rest = [b for b in board if b is not pcb and b is not xt30 and b is not terminal]
add("head_ebb42_gen2_pcb", wp(pcb), "pcb")
add("head_ebb42_gen2_xt30", wp(xt30), "xt30")
add("head_ebb42_gen2_heater_terminal", wp(terminal), "terminal")
add("head_ebb42_gen2_connectors", wp([b for b in rest if b.Volume() > 60]), "white")
add("head_ebb42_gen2_small", wp([b for b in rest if b.Volume() <= 60]), "steel")

# BIQU MicroProbe V2 and the front cover
add("head_microprobe", probe.probe_model(), "probe")
# with --exploded the cover is pulled off to the front and its screws are backed out (for the mounting picture)
EXPLODE_X, EXPLODE_SCREW = (-55.0, 14.0) if "--exploded" in sys.argv else (0.0, 0.0)
add("head_cover", cover.build().translate((EXPLODE_X, 0, 0)), "printed", "cover")
side_a, side_b, top = cover_points.screws((cover.Z0, cover.Z1), cover.Y_TOP)
add("head_cover_screws", wp([side_a.translate((EXPLODE_X, 0, -EXPLODE_SCREW)).val(), side_b.translate((EXPLODE_X, 0, EXPLODE_SCREW)).val(),
                             top.translate((EXPLODE_X, EXPLODE_SCREW, 0)).val()]), "steel")
add("head_inserts_cover", wp([s.val() for s in cover_points.inserts()]), "brass")

os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
assy.export(out, tolerance=0.08, angularTolerance=0.35)
print("saved", out, os.path.getsize(out) // 1024, "KB")
