"""Interference check of the new parts against the rest of the head assembly.

Run:  python3 check_fit.py <parts_dir>
parts_dir: the team's assembly export ("Сборка/Hefest extruder.stp" from KAPACbik/Hefest)
split into .brep files by model/tools/split_assy.py.
"""
import json
import os
import sys

import cadquery as cq
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing

import cover
import frame_cover
import frame_v3
import mount2_probe
import probe as P

parts_dir = sys.argv[1]
index = json.load(open(os.path.join(parts_dir, "index.json")))
REPLACED = {(28, "solid", 2), (28, "shell", 7)}       # the original hotend mount 2 and the original frame

# of the frame only the added boss is checked: the assembly has the board's inserts drawn inside the frame wall
frame_boss = frame_cover.build().cut(frame_v3.build()[0]).val()
new = {"cover boss on the frame": frame_boss, "mount 2 with probe seat": mount2_probe.build().val(), "MicroProbe": P.probe_model().val(), "cover": cover.build().val()}
# room the probe needs besides its own body: the pin moving, and the cable plug behind the connector
b = new["MicroProbe"].BoundingBox()
new["probe cable plug (8 mm behind the connector)"] = cq.Workplane("XY").box(11.5, 3.5, 8.0, centered=(True, True, False)).translate(
    (P.PIN[0], P.SEAT_Y - 4.95, b.zmin - 8.0)).val()

others = []
surfaces = []          # parts that cannot be closed into a solid: checked by distance to their surface
for row in index:
    shape = cq.importers.importBrep(os.path.join(parts_dir, row["file"])).val()
    solids = shape.Solids()
    for j, s in enumerate(solids):
        if (row["i"], "solid", j) not in REPLACED:
            others.append((f'{row["i"]:02d}/{j} {row["name"]}', s))
    in_solids = {sh.hashCode() for s in solids for sh in s.Shells()}
    for j, sh in enumerate(shape.Shells()):          # parts exported as open shells: close them
        if sh.hashCode() in in_solids or len(sh.Faces()) < 10 or (row["i"], "shell", j) in REPLACED:
            continue
        try:
            sew = BRepBuilderAPI_Sewing(1e-3)          # the export leaves these shells unsewn
            sew.Add(sh.wrapped)
            sew.Perform()
            s = cq.Solid.makeSolid(cq.Shape.cast(sew.SewedShape()).Shells()[0])
            if s.Volume() < 0:
                s = cq.Solid(s.wrapped.Reversed())
            bb = s.BoundingBox()
            if not s.isValid() or s.Volume() > bb.xlen * bb.ylen * bb.zlen:      # a loose surface, not a closed part
                if row["i"] != 2:                    # item 2 is the carriage drawn a second time as surfaces
                    surfaces.append((f'{row["i"]:02d}/shell{j} {row["name"]}', sh))
                continue
            others.append((f'{row["i"]:02d}/shell{j} {row["name"]}', s))
        except Exception as e:
            print("skipped", row["i"], j, e)

worst = 0.0
names = list(new)
pairs = [(a, new[a], bname, bs) for a in names for bname, bs in others]
pairs += [(names[i], new[names[i]], names[j], new[names[j]]) for i in range(len(names)) for j in range(i + 1, len(names))]
for an, a, bn, bshape in pairs:
    ba, bb = a.BoundingBox(), bshape.BoundingBox()
    if (ba.xmin > bb.xmax or bb.xmin > ba.xmax or ba.ymin > bb.ymax or bb.ymin > ba.ymax or ba.zmin > bb.zmax or bb.zmin > ba.zmax):
        continue
    try:
        v = a.intersect(bshape).Volume()
    except Exception as e:
        print(f"?  {an} x {bn}: {e}")
        continue
    if v > 0.01:
        c = a.intersect(bshape).BoundingBox()
        print(f"CLASH {v:8.2f} mm3  {an}  x  {bn}   x[{c.xmin:.1f},{c.xmax:.1f}] y[{c.ymin:.1f},{c.ymax:.1f}] z[{c.zmin:.1f},{c.zmax:.1f}]")
        worst = max(worst, v)
for sn, sh in surfaces:
    for an, a in new.items():
        d = a.distance(sh)
        print(f"{'CLASH' if d < 0.05 else 'clear'}  {an}  to surface of  {sn}: {d:.2f} mm")
print(f"checked {len(pairs)} pairs, worst overlap {worst:.2f} mm3")
