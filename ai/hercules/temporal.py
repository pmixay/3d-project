"""Temporal decision engine.

Per-frame model output is noisy: a single frame can show a blob of purge
filament, a reflection or the print head in a strange pose. Persistent
failures, on the other hand, stay in view for minutes. The engine turns the
per-frame score p into a decision with these steps:

1. Time-normalised exponential average (ewm). Obico smooths p with an EWM of
   span 12 *frames*, which only makes sense at its fixed frame rate. We use a
   time constant instead: alpha = 1 - exp(-dt / tau). With tau = 60 s the
   smoothing is the same whether we analyse a frame every 1 s or every 20 s.
2. Slow baseline subtraction. Some camera views always produce small scores
   (textured filament, cables). A long time-constant average of p is
   subtracted; it is frozen while an incident is open so a real failure
   cannot "teach" the baseline that spaghetti is normal.
3. Evidence gate. At long intervals one frame moves the ewm a lot (alpha
   grows with dt). An alert additionally needs at least N frames with
   p >= positive_p inside the evidence window.
4. Warm-up. No failure alerts during the first warmup_s of monitoring.
5. Hysteresis. Warning at score >= warn, critical at warn * critical_factor.
   An incident stays open until the score has stayed below warn * clear_ratio
   for clear_hold_s, so one failure produces one incident, not a flood.
6. False-alarm recovery. When a person dismisses an incident the engine is
   reset and alerts are suppressed for dismiss_suppress_s.
"""
from __future__ import annotations

import collections
import dataclasses as dc
import math

from .config import DecisionCfg

LEVELS = ("ok", "warning", "critical")


@dc.dataclass
class Assessment:
    t: float
    p: float
    ewm: float
    baseline: float
    score: float
    evidence: int
    level: str              # ok | warning | critical  (gated, what an alert would use)
    raw_level: str          # level from the score alone (before warm-up/evidence gates)
    warmup: bool
    suppressed: bool
    incident_open: bool
    event: str | None = None  # "open" | "escalate" | "close"

    def to_dict(self):
        d = dc.asdict(self)
        for k in ("p", "ewm", "baseline", "score"):
            d[k] = round(d[k], 4)
        return d


class FailureTracker:
    def __init__(self, cfg: DecisionCfg):
        self.cfg = cfg
        self.reset()

    def reset(self, t: float | None = None) -> None:
        self.ewm = 0.0
        self.baseline = 0.0
        self.last_t: float | None = None
        self.start_t: float | None = t
        self.hits: collections.deque = collections.deque()
        self.incident_level = "ok"     # level of the open incident, "ok" = none open
        self.below_since: float | None = None
        self.suppress_until = -math.inf

    def dismiss(self, t: float) -> None:
        """Operator says this was a false alarm."""
        self.reset(t)
        self.start_t = t - self.cfg.warmup_s   # no new warm-up, just suppression
        self.suppress_until = t + self.cfg.dismiss_suppress_s

    def update(self, t: float, p: float) -> Assessment:
        c = self.cfg
        if self.start_t is None:
            self.start_t = t
        dt = 0.0 if self.last_t is None else max(0.0, t - self.last_t)
        if self.last_t is None:
            # first frame: treat as one nominal step so a failure already in view counts
            dt = min(c.ewm_tau_s, 3.0)
        self.last_t = t
        a = 1.0 - math.exp(-dt / c.ewm_tau_s) if c.ewm_tau_s > 0 else 1.0
        self.ewm += a * (p - self.ewm)
        score = self.ewm - self.baseline

        warn = c.warn_threshold
        crit = warn * c.critical_factor
        if self.incident_level == "ok" and score < warn * c.clear_ratio:
            b = 1.0 - math.exp(-dt / c.baseline_tau_s) if c.baseline_tau_s > 0 else 0.0
            self.baseline += b * (p - self.baseline)

        if p >= c.positive_p:
            self.hits.append(t)
        while self.hits and self.hits[0] < t - c.evidence_window_s:
            self.hits.popleft()
        evidence = len(self.hits)

        raw = "critical" if score >= crit else "warning" if score >= warn else "ok"
        warmup = (t - self.start_t) < c.warmup_s
        suppressed = t < self.suppress_until
        level = raw
        if warmup or suppressed or evidence < c.min_positive_frames:
            level = "ok"

        event = None
        if level != "ok" and LEVELS.index(level) > LEVELS.index(self.incident_level):
            event = "open" if self.incident_level == "ok" else "escalate"
            self.incident_level = level
            self.below_since = None
        elif self.incident_level != "ok":
            if score < warn * c.clear_ratio:
                if self.below_since is None:
                    self.below_since = t
                elif t - self.below_since >= c.clear_hold_s:
                    event = "close"
                    self.incident_level = "ok"
                    self.below_since = None
            else:
                self.below_since = None

        return Assessment(t, p, self.ewm, self.baseline, score, evidence, level, raw,
                          warmup, suppressed, self.incident_level != "ok", event)


class Persistent:
    """A boolean condition that must hold for `after_s` to open and be absent for
    `clear_s` to close. Used for camera-health incidents."""

    def __init__(self, after_s: float, clear_s: float = 10.0):
        self.after_s, self.clear_s = after_s, clear_s
        self.since: float | None = None
        self.clear_since: float | None = None
        self.active = False

    def update(self, t: float, cond: bool) -> str | None:
        if cond:
            self.clear_since = None
            if self.since is None:
                self.since = t
            if not self.active and t - self.since >= self.after_s:
                self.active = True
                return "open"
        else:
            self.since = None
            if self.active:
                if self.clear_since is None:
                    self.clear_since = t
                if t - self.clear_since >= self.clear_s:
                    self.active = False
                    self.clear_since = None
                    return "close"
        return None
