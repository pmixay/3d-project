"""Numbered callouts on the exploded render of the head cover (hefest_head_cover_mount.png).

Run:  python3 head_cover_mount.py <render.png> <out.png>
The render is the view "hefest_head_cover_mount" of head_views.json made from a head GLB built
with --exploded; the callout positions are projected with the same camera.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "head", "v3"))
import cover               # noqa: E402
import cover_points as CP  # noqa: E402

src, out = sys.argv[1:3]
view = json.load(open(os.path.join(HERE, "head_views.json")))["hefest_head_cover_mount"]
img = Image.open(src).convert("RGBA")
scale = img.width / view["size"][0]
d = np.array(view["dir"], float); d /= np.linalg.norm(d)
right = np.cross([0, 1, 0], d); right /= np.linalg.norm(right)
up = np.cross(d, right)
k = view["size"][1] / view["span"] * scale


def px(p):
    v = np.array(p, float) - np.array(view["target"], float)
    return img.width / 2 + v @ right * k, img.height / 2 - v @ up * k


EX, ES = -55.0, 14.0                       # as in head_glb.py --exploded
sx, sy = CP.SIDE_XY
tx, tz = CP.TOP_XZ
# (number, point on the model, where the label goes relative to it in mm on the page: right, up)
marks = [
    ("1", (sx, sy, CP.SIDE_Z[0]), (-20, -16)),                       # insert in the mount block
    ("2", (tx, CP.TOP_Y, tz), (6, 22)),                              # insert in the frame boss
    ("3", (sx + EX, sy, cover.Z0 - ES - 1), (-14, -14)),             # side screw
    ("3", (tx + EX, cover.Y_TOP + ES + 2, tz), (16, 12)),            # top screw
    ("4", (cover.X_UP_OUT + EX + 30, cover.Y_TOP, 12), (14, 20)),    # the cover
]
draw = ImageDraw.Draw(img)
font = ImageFont.truetype(os.path.join(HERE, "fonts", "Montserrat-Bold.ttf"), int(15 * scale))
r = 11 * scale
for label, p, (dx, dy) in marks:
    x, y = px(p)
    lx, ly = x + dx * k, y - dy * k
    draw.line([(x, y), (lx, ly)], fill=(15, 90, 99, 255), width=max(2, int(1.5 * scale)))
    draw.ellipse([x - 3 * scale, y - 3 * scale, x + 3 * scale, y + 3 * scale], fill=(15, 90, 99, 255))
    draw.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(15, 90, 99, 255))
    draw.text((lx, ly), label, font=font, fill="white", anchor="mm")
box = img.getchannel("A").getbbox()
m = int(8 * scale)
img.crop((max(box[0] - m, 0), max(box[1] - m, 0), min(box[2] + m, img.width), min(box[3] + m, img.height))).save(out)
print("saved", out)
