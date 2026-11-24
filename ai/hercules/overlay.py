"""Drawing detection overlays on frames (dashboard stream and evidence images)."""
from __future__ import annotations

import time

import cv2
import numpy as np

LEVEL_BGR = {"ok": (90, 200, 90), "warning": (0, 190, 255), "critical": (60, 60, 255)}


def draw(img: np.ndarray, boxes: list, roi=None, ignore_zones=(), level: str = "ok",
         score: float | None = None, caption: str = "", stamp: bool = True) -> np.ndarray:
    out = img.copy()
    H, W = out.shape[:2]
    lw = max(1, round(W / 640))
    if roi and list(roi) != [0.0, 0.0, 1.0, 1.0]:
        x0, y0, x1, y1 = roi
        cv2.rectangle(out, (int(x0 * W), int(y0 * H)), (int(x1 * W), int(y1 * H)), (230, 200, 60), lw)
    for z in ignore_zones or ():
        x0, y0, x1, y1 = z
        p0, p1 = (int(x0 * W), int(y0 * H)), (int(x1 * W), int(y1 * H))
        cv2.rectangle(out, p0, p1, (120, 120, 120), lw)
        cv2.line(out, p0, p1, (120, 120, 120), lw)
    for b in boxes:
        x1, y1, x2, y2, conf, in_roi = b if isinstance(b, (list, tuple)) else b.as_list()
        col = (60, 60, 255) if in_roi else (140, 140, 140)
        cv2.rectangle(out, (int(x1), int(y1)), (int(x2), int(y2)), col, 2 * lw)
        txt = f"failure {conf:.2f}"
        fs = 0.45 * lw
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, fs, lw)
        ty = max(int(y1), th + 4)
        cv2.rectangle(out, (int(x1), ty - th - 4), (int(x1) + tw + 4, ty), col, -1)
        cv2.putText(out, txt, (int(x1) + 2, ty - 3), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), lw, cv2.LINE_AA)
    if stamp:
        bar = f"HERCULES  {level.upper()}"
        if score is not None:
            bar += f"  score {score:.2f}"
        if caption:
            bar += f"  {caption}"
        bar += "  " + time.strftime("%Y-%m-%d %H:%M:%S")
        fs = 0.5 * lw
        (tw, th), _ = cv2.getTextSize(bar, cv2.FONT_HERSHEY_SIMPLEX, fs, lw)
        cv2.rectangle(out, (0, 0), (tw + 12, th + 12), (20, 20, 20), -1)
        cv2.rectangle(out, (0, 0), (6, th + 12), LEVEL_BGR.get(level, (200, 200, 200)), -1)
        cv2.putText(out, bar, (10, th + 5), cv2.FONT_HERSHEY_SIMPLEX, fs, (235, 235, 235), lw, cv2.LINE_AA)
    return out


def jpeg(img: np.ndarray, quality: int = 85) -> bytes:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else b""


def resize_w(img: np.ndarray, width: int) -> np.ndarray:
    h, w = img.shape[:2]
    if w <= width:
        return img
    return cv2.resize(img, (width, round(h * width / w)), interpolation=cv2.INTER_AREA)
