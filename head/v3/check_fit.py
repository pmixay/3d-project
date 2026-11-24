"""Interference check of the new parts against the rest of the head assembly.

Run:  python3 check_fit.py <parts_dir>
parts_dir: the team's assembly export ("Сборка/Hefest extruder.stp" from KAPACbik/Hefest)
split into .brep files by model/tools/split_assy.py.
"""
import json
import os
import sys

import cadquery as cq

import cover
import mount2_probe
import probe as P

parts_dir = sys.argv[1]
index = json.load(open(os.path.join(parts_dir, "index.json")))
REPLACED = {(28, "solid", 2)}             # the original hotend mount 2

new = {"mount 2 with probe seat": mount2_probe.build().val(), "MicroProbe": P.probe_model().val(), "cover": cover.build().val()}
# room the probe needs besides its own body: the pin moving, and the cable plug behind the connector
b = new["MicroProbe"].BoundingBox()
new["probe cable plug (8 mm behind the connector)"] = cq.Workplane("XY").box(11.5, 3.5, 8.0, centered=(True, True, False)).translate(
    (P.PIN[0], P.SEAT_Y - 4.95, b.zmin - 8.0)).val()

others = []
for row in index:
    shape = cq.importers.importBrep(os.path.join(parts_dir, row["file"])).val()
    solids = shape.Solids()
    for j, s in enumerate(solids):
        if (row["i"], "solid", j) not in REPLACED:
            others.append((f'{row["i"]:02d}/{j} {row["name"]}', s))
    in_solids = {sh.hashCode() for s in solids for sh in s.Shells()}
    for j, sh in enumerate(shape.Shells()):          # parts exported as open shells: close them
        if sh.hashCode() in in_solids or len(sh.Faces()) < 10:
            continue
        try:
            s = cq.Solid.makeSolid(sh)
            if s.Volume() < 0:
                s = cq.Solid(s.wrapped.Reversed())
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
print(f"checked {len(pairs)} pairs, worst overlap {worst:.2f} mm3")
