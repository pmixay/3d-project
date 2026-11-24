"""Frame -> validation -> preprocessing/inference -> temporal decision.

`Analyzer` is the single code path used by the live service and by offline
replay/evaluation, so measured results describe the code that actually runs.
"""
from __future__ import annotations

import dataclasses as dc
import time

import numpy as np

from .config import Config
from .detector import Detection, Detector
from .quality import FrameValidator, Quality
from .temporal import Assessment, FailureTracker


@dc.dataclass
class StepResult:
    t: float
    quality: Quality
    detection: Detection | None
    assessment: Assessment | None
    skipped: str | None          # why inference was skipped: unusable | duplicate | blurred
    step_ms: float


class Analyzer:
    def __init__(self, cfg: Config, detector: Detector | None = None):
        self.cfg = cfg
        self.detector = detector or Detector(cfg.detector)
        self.validator = FrameValidator(cfg.pipeline)
        self.tracker = FailureTracker(cfg.decision)
        self.last_detection: Detection | None = None
        self.consecutive_skips = 0

    def reset(self, t: float | None = None) -> None:
        self.validator.reset()
        self.tracker.reset(t)
        self.last_detection = None
        self.consecutive_skips = 0

    def step(self, img: np.ndarray, t: float, detect_fn=None) -> StepResult:
        """Analyse one frame taken at time t (seconds, wall or media clock).

        detect_fn(img) may replace the network call (used by evaluation to
        reuse cached detections when sweeping parameters)."""
        t0 = time.perf_counter()
        pc = self.cfg.pipeline
        q = self.validator.check(img)
        skipped = None
        can_skip = self.consecutive_skips < pc.max_consecutive_skips
        if not q.usable:
            skipped = "unusable"
        elif pc.skip_duplicates and q.duplicate and self.last_detection is not None and can_skip:
            skipped = "duplicate"
        elif pc.skip_blurred and q.blurred and can_skip:
            skipped = "blurred"

        det, a = None, None
        if skipped is None:
            det = detect_fn(img) if detect_fn else self.detector.detect(img, pc)
            self.last_detection = det
            self.consecutive_skips = 0
            a = self.tracker.update(t, det.p)
        else:
            self.consecutive_skips += 1
            if skipped == "duplicate":
                # unchanged scene -> same evidence; keep the clock of the tracker moving
                a = self.tracker.update(t, self.last_detection.p)
        return StepResult(t, q, det, a, skipped, (time.perf_counter() - t0) * 1000)
