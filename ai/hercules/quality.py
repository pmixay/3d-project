"""Frame validation before inference.

Cheap checks (~1-2 ms on a 960 px frame) that decide whether a frame is worth
sending to the neural network and whether the camera itself is healthy:

* brightness   mean grey level -> too_dark / overexposed
* sharpness    variance of the Laplacian, compared with the running median of
               this camera, so it adapts to the scene instead of using an
               absolute number -> blurred (motion blur from the moving head)
* change       mean absolute difference to the previous analysed frame
               -> duplicate (skip inference), and "frozen" if the image is
               bit-identical for frozen_after_s (stream hung, driver stuck)
* obstruction  share of 16x16 blocks with almost no texture -> lens covered,
               camera knocked to face a wall, or a uniform black/white frame
"""
from __future__ import annotations

import collections
import dataclasses as dc

import cv2
import numpy as np

from .config import PipelineCfg


@dc.dataclass
class Quality:
    brightness: float
    sharpness: float
    sharpness_ratio: float
    change: float | None
    flat_fraction: float
    too_dark: bool
    overexposed: bool
    blurred: bool
    duplicate: bool
    identical: bool
    obstructed: bool

    @property
    def usable(self) -> bool:
        return not (self.too_dark or self.overexposed or self.obstructed)

    def flags(self) -> list[str]:
        return [n for n in ("too_dark", "overexposed", "blurred", "duplicate", "obstructed")
                if getattr(self, n)]


class FrameValidator:
    def __init__(self, cfg: PipelineCfg):
        self.cfg = cfg
        self._prev_small: np.ndarray | None = None
        self._sharp_hist: collections.deque = collections.deque(maxlen=50)

    def reset(self) -> None:
        self._prev_small = None
        self._sharp_hist.clear()

    def check(self, img: np.ndarray) -> Quality:
        c = self.cfg
        h, w = img.shape[:2]
        scale = 480.0 / max(w, 1)
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        g = cv2.resize(g, (480, max(1, int(round(h * scale)))), interpolation=cv2.INTER_AREA)

        brightness = float(g.mean())
        sharp = float(cv2.Laplacian(g, cv2.CV_32F).var())
        med = float(np.median(self._sharp_hist)) if len(self._sharp_hist) >= 5 else sharp
        ratio = sharp / med if med > 1e-6 else 1.0
        self._sharp_hist.append(sharp)

        small = cv2.resize(g, (96, max(1, int(round(96 * g.shape[0] / g.shape[1])))),
                           interpolation=cv2.INTER_AREA)
        change = None
        identical = False
        if self._prev_small is not None and self._prev_small.shape == small.shape:
            change = float(np.abs(small.astype(np.int16) - self._prev_small).mean())
            identical = change < 0.01
        self._prev_small = small.astype(np.int16)

        # texture per 16x16 block
        bh, bw = g.shape[0] // 16, g.shape[1] // 16
        blocks = g[:bh * 16, :bw * 16].reshape(bh, 16, bw, 16).astype(np.float32)
        flat = float((blocks.std(axis=(1, 3)) < 2.5).mean()) if bh and bw else 1.0

        return Quality(
            brightness=brightness, sharpness=sharp, sharpness_ratio=ratio, change=change,
            flat_fraction=flat,
            too_dark=brightness < c.dark_level,
            overexposed=brightness > c.bright_level,
            blurred=len(self._sharp_hist) >= 5 and ratio < c.blur_ratio,
            duplicate=change is not None and change < c.duplicate_diff,
            identical=identical,
            obstructed=flat > c.obstructed_fraction,
        )
