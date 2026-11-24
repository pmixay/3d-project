#!/usr/bin/env python3
"""Offline evaluation on recorded print sessions (no printer needed).

Replays every session through the production `Analyzer` (frame validation,
temporal decision engine) using cached network outputs from score_sessions.py,
analysing one frame every --interval seconds of *recording* time, exactly like
the live service would.

Ground truth: datasets/labels/sessions.json (session kind + failure onset frame,
labelled by us by visual inspection; see that file).

Metrics
  normal printing time  = whole "normal" sessions + failure sessions before onset
  false alarm           = a failure incident opened during normal printing time
  FA / printing hour    = false alarms / normal printing hours
  detection             = a failure incident opened at or after the onset
  latency               = alert time - onset time (first visible defect)
  session P / R / F1    = sessions with an alert vs. sessions with a target failure
  frame P / R / F1      = per analysed frame: raw model score p >= threshold vs label
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402

from hercules.config import Config, load  # noqa: E402
from hercules.detector import Box, score_boxes  # noqa: E402
from hercules.pipeline import Analyzer  # noqa: E402

TARGET = {"spaghetti"}       # failure kinds the system claims to detect


class CachedDetector:
    backend, providers, load_s = "cache", ["cache"], 0.0


class ObicoTracker:
    """Baseline: Obico's original decision scheme, transcribed from
    obico-server backend/lib/prediction.py + settings.py (frame-count based).
    Used only for comparison; returns objects with the fields simulate() reads."""
    P = dict(EWM_SPAN=12, ROLLING_WIN_SHORT=310, ROLLING_WIN_LONG=7200, THRESHOLD_LOW=0.38,
             THRESHOLD_HIGH=0.78, INIT_SAFE_FRAME_NUM=30, ROLLING_MEAN_SHORT_MULTIPLE=3.8, ESCALATING_FACTOR=1.75)

    def __init__(self):
        self.ewm = self.short = self.long = 0.0
        self.n = 0
        self.state = "ok"

    def _failing(self, factor):
        P = self.P
        if self.n < P["INIT_SAFE_FRAME_NUM"]:
            return False
        adj = (self.ewm - self.long) / factor
        if adj < P["THRESHOLD_LOW"]:
            return False
        if adj > P["THRESHOLD_HIGH"]:
            return True
        return adj > (self.short - self.long) * P["ROLLING_MEAN_SHORT_MULTIPLE"]

    def update(self, t, p):
        P = self.P
        a = 2 / (P["EWM_SPAN"] + 1)
        self.n += 1
        self.ewm = p * a + self.ewm * (1 - a)
        self.short += (p - self.short) / (P["ROLLING_WIN_SHORT"] if P["ROLLING_WIN_SHORT"] <= self.n else self.n + 1)
        self.long += (p - self.long) / (P["ROLLING_WIN_LONG"] if P["ROLLING_WIN_LONG"] <= self.n else self.n + 1)
        lvl = "critical" if self._failing(P["ESCALATING_FACTOR"]) else "warning" if self._failing(1) else "ok"
        return _transition(self, t, p, self.ewm - self.long, lvl)


class NaiveTracker:
    """Baseline: alert whenever a single frame has p >= thr (what a simple script would do).
    An alert 'episode' ends after 120 s without a positive frame."""
    def __init__(self, thr=0.38, crit=0.665):
        self.thr, self.crit, self.state, self.last_pos = thr, crit, "ok", -1e9

    def update(self, t, p):
        lvl = "critical" if p >= self.crit else "warning" if p >= self.thr else "ok"
        if lvl != "ok":
            self.last_pos = t
        elif t - self.last_pos < 120:
            lvl = self.state if self.state != "ok" else "ok"
        return _transition(self, t, p, p, lvl, sticky=t - self.last_pos < 120)


def _transition(tr, t, p, score, lvl, sticky=None):
    import types
    order = ("ok", "warning", "critical")
    ev = None
    if lvl != "ok" and order.index(lvl) > order.index(tr.state):
        ev = "open" if tr.state == "ok" else "escalate"
        tr.state = lvl
    elif tr.state != "ok" and lvl == "ok" and not sticky:
        tr.state = "ok"
        ev = "close"
    return types.SimpleNamespace(t=t, p=p, score=score, level=lvl, event=ev)


def perturb(img, kind):
    """Synthetic camera problems applied to real frames (robustness tests)."""
    import numpy as np
    if kind == "dark":            # lights off / evening: gamma + gain down
        return np.clip(((img / 255.0) ** 1.8) * 255 * 0.45, 0, 255).astype("uint8")
    if kind == "blur":            # horizontal motion blur, 21 px at 960 px width
        k = np.zeros((1, 21), np.float32)
        k[0, :] = 1 / 21
        return cv2.filter2D(img, -1, k)
    if kind == "occlusion":       # a third of the frame covered from the left (cable, hand, tape)
        out = img.copy()
        out[:, : img.shape[1] // 3] = (40, 40, 40)
        return out
    if kind == "noise":           # cheap sensor in low light
        rng = np.random.default_rng(0)
        return np.clip(img.astype(np.int16) + rng.normal(0, 18, img.shape), 0, 255).astype("uint8")
    raise ValueError(kind)


def load_cache(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def simulate(cfg: Config, session_dir: str, rows: list, interval: float, read_images=True,
             engine: str = "hercules", perturbation: str | None = None, detector=None):
    an = Analyzer(cfg, detector=detector or CachedDetector())
    if engine == "obico":
        an.tracker = ObicoTracker()
    elif engine == "naive":
        an.tracker = NaiveTracker(cfg.decision.warn_threshold, cfg.decision.warn_threshold * cfg.decision.critical_factor)
    pc = cfg.pipeline
    thr = cfg.detector.box_threshold
    alerts, trace = [], []
    next_t = None
    blank = None
    for r in rows:
        if next_t is not None and r["t"] < next_t:
            continue
        next_t = (r["t"] if next_t is None else next_t) + interval
        while next_t <= r["t"]:
            next_t += interval
        if read_images:
            img = cv2.imread(os.path.join(session_dir, r["file"]))
        else:
            if blank is None:
                import numpy as np
                rng = np.random.default_rng(0)
                blank = (rng.random((r["h"], r["w"], 3)) * 255).astype("uint8")
            img = blank.copy()
            img[0, 0, 0] = len(trace) % 255  # make consecutive frames differ
        if perturbation:
            img = perturb(img, perturbation)
            det_fn = None                      # perturbed frames need a real network run
        else:
            boxes = [Box(*b) for b in r["boxes"] if b[4] > thr]

            def det_fn(_img, boxes=boxes, r=r):
                return score_boxes(boxes, r["w"], r["h"], pc, r["ms"])
        res = an.step(img, r["t"], det_fn)
        a = res.assessment
        trace.append((r["t"], None if a is None else round(a.score, 4), None if res.detection is None
                      else round(res.detection.p, 4), res.skipped))
        if a is not None and a.event in ("open", "escalate"):
            alerts.append({"t": r["t"], "event": a.event, "level": a.level, "score": round(a.score, 3),
                           "file": r["file"]})
    return alerts, trace


def onset_time(rows, index):
    for r in rows:
        if int(r["file"].split("_")[1].split(".")[0]) >= index:
            return r["t"]
    return None


def evaluate(cfg, labels, data_dir, cache_dir, interval, read_images=True, sessions=None,
             engine="hercules", perturbation=None, detector=None, window=None):
    per = {}
    normal_s, fa = 0.0, 0
    for name, lab in labels["sessions"].items():
        if sessions and name not in sessions:
            continue
        cpath = os.path.join(cache_dir, name + ".jsonl")
        if not os.path.exists(cpath):
            print("missing cache", cpath, file=sys.stderr)
            continue
        rows = load_cache(cpath)
        if window is not None:
            # robustness runs: only the frames from `window[0]` s before the onset (or the
            # same span from the start of a normal print) up to `window[1]` s after it
            on = onset_time(rows, lab["onset_index"]) if lab.get("onset_index") is not None else None
            anchor = on if on is not None else rows[0]["t"] + window[0]
            rows = [r for r in rows if anchor - window[0] <= r["t"] <= anchor + window[1]]
        alerts, trace = simulate(cfg, os.path.join(data_dir, name), rows, interval, read_images,
                                 engine, perturbation, detector)
        t_end = rows[-1]["t"]
        onset = onset_time(rows, lab["onset_index"]) if lab.get("onset_index") is not None else None
        normal_end = onset if onset is not None else t_end
        normal_s += normal_end - rows[0]["t"]
        opens = [x for x in alerts if x["event"] == "open"]
        false = [x for x in opens if x["t"] < normal_end]
        fa += len(false)
        hit = next((x for x in opens if onset is not None and x["t"] >= onset), None)
        # an incident already open at onset (opened as a false alarm) still covers the failure
        crit = next((x for x in alerts if x["level"] == "critical" and onset is not None and x["t"] >= onset), None)
        per[name] = {
            "kind": lab["kind"], "frames_analysed": len(trace),
            "inferences": sum(1 for x in trace if x[3] is None),
            "duration_min": round(t_end / 60, 1),
            "onset_min": None if onset is None else round(onset / 60, 2),
            "false_alarms": len(false), "false_alarm_times_min": [round(x["t"] / 60, 1) for x in false],
            "detected": hit is not None,
            "latency_s": None if hit is None else round(hit["t"] - onset, 1),
            "critical_latency_s": None if crit is None else round(crit["t"] - onset, 1),
            "max_score_normal": max([s for t, s, p, k in trace if s is not None and t < normal_end] or [0]),
            "max_score_after_onset": None if onset is None else max(
                [s for t, s, p, k in trace if s is not None and t >= onset] or [0]),
        }

    tgt = [v for v in per.values() if v["kind"] in TARGET]
    nontarget_fail = [v for v in per.values() if v["kind"] not in TARGET and v["kind"] != "normal"]
    tp = sum(v["detected"] for v in tgt)
    fn = len(tgt) - tp
    fp_sessions = sum(1 for v in per.values() if v["false_alarms"] > 0)
    prec = tp / (tp + fp_sessions) if tp + fp_sessions else None
    rec = tp / len(tgt) if tgt else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if prec is not None and rec is not None else None)
    lats = [v["latency_s"] for v in tgt if v["latency_s"] is not None]
    return {
        "interval_s": interval, "engine": engine, "perturbation": perturbation,
        "sessions": per,
        "summary": {
            "target_sessions": len(tgt), "detected": tp, "missed": fn,
            "sessions_with_false_alarm": fp_sessions, "false_alarms": fa,
            "normal_print_hours": round(normal_s / 3600, 2),
            "false_alarms_per_print_hour": round(fa / (normal_s / 3600), 3) if normal_s else None,
            "session_precision": None if prec is None else round(prec, 3),
            "session_recall": None if rec is None else round(rec, 3),
            "session_f1": None if f1 is None else round(f1, 3),
            "latency_s": lats, "latency_s_mean": round(sum(lats) / len(lats), 1) if lats else None,
            "non_target_failures_alerted": sum(v["detected"] for v in nontarget_fail),
            "non_target_failure_sessions": len(nontarget_fail),
        },
    }


def frame_metrics(labels, cache_dir, thresholds=(0.2, 0.38, 0.5, 0.78), box_threshold=0.08, roi=(0, 0, 1, 1)):
    """Model-only, per frame: p >= thr predicts failure. Positives: frames at/after
    the onset of target failures. Negatives: normal sessions + pre-onset frames.
    Non-target failure sessions are excluded after their onset."""
    out = {}
    pts = []
    for name, lab in labels["sessions"].items():
        cpath = os.path.join(cache_dir, name + ".jsonl")
        if not os.path.exists(cpath):
            continue
        rows = load_cache(cpath)
        onset = onset_time(rows, lab["onset_index"]) if lab.get("onset_index") is not None else None
        for r in rows:
            after = onset is not None and r["t"] >= onset
            if after and lab["kind"] not in TARGET:
                continue
            p = 0.0
            for b in r["boxes"]:
                cx, cy = (b[0] + b[2]) / 2 / r["w"], (b[1] + b[3]) / 2 / r["h"]
                if b[4] > box_threshold and roi[0] <= cx <= roi[2] and roi[1] <= cy <= roi[3]:
                    p += b[4]
            pts.append((p, after))
    npos = sum(1 for _, y in pts if y)
    for thr in thresholds:
        tp = sum(1 for p, y in pts if y and p >= thr)
        fp = sum(1 for p, y in pts if not y and p >= thr)
        fn = npos - tp
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / npos if npos else 0.0
        out[str(thr)] = {"precision": round(pr, 3), "recall": round(rc, 3),
                         "f1": round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0,
                         "fp_rate": round(fp / max(1, len(pts) - npos), 4), "tp": tp, "fp": fp, "fn": fn}
    return {"frames": len(pts), "positives": npos, "by_threshold": out}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", default="datasets/labels/sessions.json")
    ap.add_argument("--data", default="data/zenodo_fffqc")
    ap.add_argument("--cache", default="data/cache")
    ap.add_argument("--config", default=None, help="TOML config (defaults if omitted)")
    ap.add_argument("--intervals", type=float, nargs="+", default=[3.0])
    ap.add_argument("--set", action="append", default=[], help="override, e.g. decision.warn_threshold=0.5")
    ap.add_argument("--no-images", action="store_true", help="skip frame validation (faster sweeps)")
    ap.add_argument("--engine", choices=["hercules", "obico", "naive"], default="hercules",
                    help="decision engine: ours, Obico's original frame-count scheme, or a per-frame threshold")
    ap.add_argument("--perturb", choices=["dark", "blur", "occlusion", "noise"],
                    help="apply a synthetic camera problem and re-run the network (slow)")
    ap.add_argument("--window", type=float, nargs=2, metavar=("BEFORE_S", "AFTER_S"),
                    help="evaluate only this span around the onset (for --perturb runs)")
    ap.add_argument("--sessions", nargs="*", help="only these session names")
    ap.add_argument("--out", help="write JSON results here")
    a = ap.parse_args()
    labels = json.load(open(a.labels))
    cfg = load(a.config, env={}, use_overrides=False) if a.config else Config()
    for s in a.set:
        k, v = s.split("=", 1)
        sec, key = k.split(".")
        sub = getattr(cfg, sec)
        cur = getattr(sub, key)
        setattr(sub, key, json.loads(v) if isinstance(cur, list) else type(cur)(v) if not isinstance(cur, bool) else v.lower() == "true")
    results = {"config": cfg.to_dict(), "engine": a.engine, "perturbation": a.perturb, "window": a.window,
               "runs": [], "frame_level": frame_metrics(
        labels, a.cache, box_threshold=cfg.detector.box_threshold, roi=cfg.pipeline.roi)}
    det = None
    if a.perturb:
        from hercules.detector import Detector
        det = Detector(cfg.detector)
    for iv in a.intervals:
        r = evaluate(copy.deepcopy(cfg), labels, a.data, a.cache, iv, not a.no_images, a.sessions,
                     a.engine, a.perturb, det, a.window)
        results["runs"].append(r)
        s = r["summary"]
        print(f"interval {iv:>5.1f}s  detected {s['detected']}/{s['target_sessions']}  "
              f"latency {s['latency_s']}  FA {s['false_alarms']} ({s['false_alarms_per_print_hour']}/h over "
              f"{s['normal_print_hours']} h)  P/R/F1 {s['session_precision']}/{s['session_recall']}/{s['session_f1']}  "
              f"non-target alerted {s['non_target_failures_alerted']}/{s['non_target_failure_sessions']}", flush=True)
        for n, v in r["sessions"].items():
            print(f"    {n:42s} {v['kind']:12s} FA={v['false_alarms']} det={v['detected']} lat={v['latency_s']} "
                  f"crit_lat={v['critical_latency_s']} maxN={v['max_score_normal']:.2f} maxF={v['max_score_after_onset']}")
    fl = results["frame_level"]
    print("frame-level (model only):", fl["frames"], "frames,", fl["positives"], "positive")
    for thr, m in fl["by_threshold"].items():
        print(f"    p>={thr}: P={m['precision']} R={m['recall']} F1={m['f1']} FPR={m['fp_rate']}")
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w") as f:
            json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
