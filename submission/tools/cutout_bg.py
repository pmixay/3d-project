"""Cut the flat gray CAD background out of a screenshot -> RGBA PNG.

The background is neutral gray with a vertical gradient. Pixels close to the row's
background value are flood-filled from the image border (the model has black outlines,
so the fill stops at the silhouette). Edge pixels that mix the gray with the black
outline get partial alpha so there is no gray halo.
usage: cutout_bg.py in.jpg out.png preview.png
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

src, out, prev = sys.argv[1:4]
im = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
h, w, _ = im.shape
lum = im.mean(axis=2)
sat = im.max(axis=2) - im.min(axis=2)

# background value per row from the left and right edge columns
edge = np.concatenate([lum[:, :6], lum[:, -6:]], axis=1)
bg_row = np.median(edge, axis=1)
bg_row = ndimage.uniform_filter1d(bg_row, 25)
bg = bg_row[:, None]

TOL = 9
cand = (np.abs(lum - bg) <= TOL) & (sat <= 8)
lab, n = ndimage.label(cand)
border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
border = border[border > 0]
bgmask = np.isin(lab, border)

alpha = np.where(bgmask, 0.0, 1.0)
# soften the silhouette: pixels next to the background that are neutral and darker than it
near = ndimage.binary_dilation(bgmask, iterations=2) & ~bgmask
mix = near & (sat <= 14) & (lum < bg)
a_mix = np.clip(1.0 - lum / bg, 0.0, 1.0)
a_mix = np.clip(a_mix * 1.6, 0.0, 1.0)  # outline pixels become opaque quickly
alpha = np.where(mix, a_mix, alpha)
# light neutral pixels next to background that are brighter than it: keep, they are model edges
rgb = im.copy()
# un-mix the gray from partially transparent pixels
a3 = alpha[..., None]
with np.errstate(divide="ignore", invalid="ignore"):
    unmixed = (im - (1 - a3) * bg[..., None]) / np.maximum(a3, 1e-3)
rgb = np.where((a3 > 0) & (a3 < 1), np.clip(unmixed, 0, 255), im)

# crop to content with a small margin
ys, xs = np.where(alpha > 0.05)
m = 12
y0, y1 = max(ys.min() - m, 0), min(ys.max() + m, h - 1)
x0, x1 = max(xs.min() - m, 0), min(xs.max() + m, w - 1)
rgba = np.dstack([rgb, alpha * 255]).astype(np.uint8)[y0:y1 + 1, x0:x1 + 1]
Image.fromarray(rgba, "RGBA").save(out, optimize=True)

# previews on magenta (leaks/holes) and on the slide colour
img = Image.fromarray(rgba, "RGBA")
canvas = Image.new("RGBA", (img.width * 2, img.height), (255, 0, 255, 255))
dark = Image.new("RGBA", img.size, (14, 24, 27, 255))
canvas.paste(Image.alpha_composite(dark, img), (img.width, 0))
canvas.alpha_composite(img, (0, 0))
canvas.convert("RGB").save(prev)
print(out, img.size, "bg rows", bg_row[0], bg_row[-1], "components", n)
