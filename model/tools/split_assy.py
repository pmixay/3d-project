"""Split an assembly STEP into per-leaf .brep files (in assembly coordinates) + print a table."""
import sys, os, re, json
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.BRepTools import BRepTools
from OCP.TopLoc import TopLoc_Location
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
src, out = sys.argv[1:3]
doc = TDocStd_Document(TCollection_ExtendedString("x"))
r = STEPCAFControl_Reader(); r.SetNameMode(True); r.ReadFile(src); r.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
def name(l):
    n = TDataStd_Name()
    return l.FindAttribute(TDataStd_Name.GetID_s(), n) and n.Get().ToExtString() or "?"
rows = []
def walk(label, loc, path):
    ref = TDF_Label()
    nm = name(label)
    if st.IsReference_s(label):
        st.GetReferredShape_s(label, ref)
        loc = loc.Multiplied(st.GetLocation_s(label))
        nm = name(ref) if name(ref) != "?" else nm
        label = ref
    if st.IsAssembly_s(label):
        comps = TDF_LabelSequence(); st.GetComponents_s(label, comps)
        for i in range(1, comps.Length() + 1):
            walk(comps.Value(i), loc, path + [nm])
        return
    shape = st.GetShape_s(label).Moved(loc)
    b = Bnd_Box(); BRepBndLib.Add_s(shape, b)
    if b.IsVoid():
        return
    bb = [round(v, 1) for v in b.Get()]
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(shape, g)
    ns = 0; e = TopExp_Explorer(shape, TopAbs_SOLID)
    while e.More(): ns += 1; e.Next()
    i = len(rows)
    fn = f"{i:03d}.brep"
    BRepTools.Write_s(shape, os.path.join(out, fn))
    rows.append(dict(i=i, file=fn, path="/".join(path[1:]), name=nm, solids=ns, vol=round(g.Mass(), 1),
                     x=[bb[0], bb[3]], y=[bb[1], bb[4]], z=[bb[2], bb[5]]))
roots = TDF_LabelSequence(); st.GetFreeShapes(roots)
for i in range(1, roots.Length() + 1):
    walk(roots.Value(i), TopLoc_Location(), [])
json.dump(rows, open(os.path.join(out, "index.json"), "w"), ensure_ascii=False, indent=0)
for r_ in rows:
    print(r_["i"], r_["path"], "|", r_["name"], "| solids", r_["solids"], "vol", r_["vol"], "x", r_["x"], "y", r_["y"], "z", r_["z"])
