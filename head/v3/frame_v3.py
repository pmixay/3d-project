"""Hefest print-head frame v3.

Starts from the current frame in KAPACbik/Hefest (branch Side-PCB-test, commit 18697e8,
"Сборка/Рама.stp", stored here as src/frame_kapacbik.step) and narrows the four
EBB42 GEN2 board mounting holes in the -Z side wall from 3.8 mm to 3.5 mm.
Nothing else is changed.

Run:  python3 frame_v3.py
"""
import os

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCP.GeomAbs import GeomAbs_Cylinder

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "frame_kapacbik.step")
OUT = os.path.join(HERE, "out")

OLD_D = 3.8          # board mounting hole diameter in the source model
NEW_D = 3.5          # corrected diameter


def board_holes(shape, dia):
    """(x, y, z_min, z_max) of every Z-axis cylindrical hole of the given diameter."""
    found = []
    for face in shape.faces().vals():
        surf = BRepAdaptor_Surface(face.wrapped)
        if surf.GetType() != GeomAbs_Cylinder:
            continue
        cyl = surf.Cylinder()
        if abs(cyl.Radius() - dia / 2) > 1e-6 or abs(abs(cyl.Axis().Direction().Z()) - 1) > 1e-6:
            continue
        loc, bb = cyl.Axis().Location(), face.BoundingBox()
        found.append((loc.X(), loc.Y(), bb.zmin, bb.zmax))
    return sorted(found)


def load_source():
    """The source STEP reads in as an unsewn shell; sew it and close it into a solid."""
    shape = cq.importers.importStep(SRC).val()
    if not shape.Solids():
        sew = BRepBuilderAPI_Sewing(1e-4)
        sew.Add(shape.wrapped)
        sew.Perform()
        shape = cq.Solid.makeSolid(cq.Shape.cast(sew.SewedShape()).Shells()[0])
    assert shape.isValid() and len(shape.Solids()) == 1, "source frame is not a single valid solid"
    return cq.Workplane("XY").newObject([shape])


def build():
    frame = load_source()
    holes = board_holes(frame, OLD_D)
    assert len(holes) == 4, f"expected 4 board holes of {OLD_D} mm, found {len(holes)}"
    for x, y, z0, z1 in holes:
        # fill the wall of the old hole with a ring, leaving a NEW_D bore on the same axis
        ring = (cq.Workplane("XY").circle(OLD_D / 2).circle(NEW_D / 2)
                .extrude(z1 - z0).translate((x, y, z0)))
        frame = frame.union(ring, clean=True)
    return frame, holes


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    src = load_source().val()
    f, holes = build()
    cq.exporters.export(f, os.path.join(OUT, "frame_v3.step"))
    cq.exporters.export(f, os.path.join(OUT, "frame_v3.stl"), tolerance=0.03, angularTolerance=0.2)
    s = f.val()
    bb = s.BoundingBox()
    print(f"frame v3: solids={len(s.Solids())} volume={s.Volume() / 1000:.3f} cm3 "
          f"(source {src.Volume() / 1000:.3f} cm3) "
          f"x[{bb.xmin:.1f},{bb.xmax:.1f}] y[{bb.ymin:.1f},{bb.ymax:.1f}] z[{bb.zmin:.1f},{bb.zmax:.1f}]")
    print(f"board holes {OLD_D} -> {NEW_D} mm at (x, y):", [(round(x, 2), round(y, 2)) for x, y, _, _ in holes])
    assert s.isValid() and len(s.Solids()) == 1
    print(f"holes of {OLD_D} mm left: {len(board_holes(f, OLD_D))}, holes of {NEW_D} mm: {len(board_holes(f, NEW_D))}")
