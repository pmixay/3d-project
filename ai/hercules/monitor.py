"""Runtime orchestration: camera thread, analysis loop, printer link, incidents, actions."""
from __future__ import annotations

import collections
import json
import logging
import threading
import time

import requests

from . import overlay
from .camera import Camera
from .config import LiveConfig
from .detector import Detector
from .incidents import CATEGORY_LABELS, IncidentStore
from .metrics import Metrics
from .moonraker import Moonraker
from .pipeline import Analyzer, StepResult
from .temporal import Persistent

log = logging.getLogger("hercules.monitor")

CAMERA_CATEGORIES = ("camera_offline", "camera_frozen", "camera_obstructed", "bad_lighting")


class Monitor:
    def __init__(self, live: LiveConfig, detector: Detector | None = None):
        self.live = live
        cfg = live.cfg
        self.metrics = Metrics()
        self.camera = Camera(cfg.camera)
        self.analyzer = Analyzer(cfg, detector)
        self.incidents = IncidentStore(cfg.state_dir)
        self.moon = Moonraker(cfg.moonraker, on_change=self._printer_changed)
        self.enabled = True                      # master switch in the dashboard
        self.history = collections.deque(maxlen=2400)
        self.last: StepResult | None = None
        self.last_frame = None                   # Frame analysed last
        self.status_reason = "starting"
        self.active = False
        self.failure_incident: int | None = None
        self.cam_incidents: dict[str, int] = {}
        self.cam_conds = {c: Persistent(cfg.decision.camera_alert_after_s) for c in CAMERA_CATEGORIES}
        self.cam_conds["camera_frozen"] = Persistent(cfg.pipeline.frozen_after_s)
        self._last_seq = 0
        self._print_file: str | None = None
        self._print_duration = 0.0
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stream_cache = (None, b"")

    # ---------------------------------------------------------------- lifecycle
    def start(self):
        self.camera.start()
        self.moon.start()
        self._thread = threading.Thread(target=self._loop, name="analyzer", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self.camera.stop()
        self.moon.stop()
        if self._thread:
            self._thread.join(timeout=10)

    def restart_camera(self):
        self.camera.cfg = self.live.cfg.camera
        self.camera.restart()
        self._last_seq = 0
        self._media_origin = None
        self._last_td = 0.0
        with self._lock:
            self.analyzer.reset()

    # ---------------------------------------------------------------- gating
    def _should_monitor(self) -> tuple[bool, str]:
        cfg = self.live.cfg
        if not self.enabled:
            return False, "monitoring disabled in dashboard"
        if cfg.pipeline.monitor_when == "always":
            return True, "monitoring (always-on mode)"
        if not self.moon.enabled:
            return True, "monitoring (no printer link configured)"
        if not self.moon.connected:
            return True, "monitoring; printer link lost (alerts only, cannot pause)"
        st = self.moon.status.get("state")
        if st == "printing":
            return True, "monitoring active print"
        return False, f"suspended: printer {st}"

    def _printer_changed(self, old, new, status):
        log.info("printer state %s -> %s", old, new)
        ended = ("complete", "cancelled", "standby", "error")
        if new == "printing":
            same_print = (status.get("filename") == self._print_file
                          and (status.get("print_duration") or 0) >= self._print_duration - 1)
            # resume after pause, or the printer link came back during the same print:
            # keep the evidence collected so far
            if old == "paused" or (old in ("disconnected", "unknown", None) and same_print and self._print_file):
                log.info("print continues (%s): decision state kept", status.get("filename"))
            else:
                with self._lock:
                    self.analyzer.reset()
                log.info("new print detected (%s): decision state reset", status.get("filename"))
        if new == "printing" or new == "paused":
            self._print_file = status.get("filename")
            self._print_duration = status.get("print_duration") or 0.0
        if new in ended:
            if self.failure_incident:
                self._close_failure("print ended")
            self._print_file, self._print_duration = None, 0.0
            with self._lock:
                self.analyzer.reset()

    # ---------------------------------------------------------------- loop
    def _loop(self):
        next_t = time.time()
        while not self._stop.is_set():
            interval = self.live.cfg.pipeline.interval_s
            now = time.time()
            if next_t > now:
                self._stop.wait(next_t - now)
                continue
            next_t = max(next_t + interval, time.time())
            try:
                self._tick()
            except Exception:  # noqa: BLE001 - never let the analysis thread die
                log.exception("analysis step failed")
                self.metrics.count("errors")

    def _tick(self):
        t = time.time()
        if self.moon.connected and self.moon.status.get("state") == "printing":
            self._print_duration = self.moon.status.get("print_duration") or self._print_duration
        active, reason = self._should_monitor()
        self.active, self.status_reason = active, reason
        cs = self.camera.status()
        # a missing camera matters while a print is being watched, not overnight
        self._camera_condition("camera_offline", t, active and cs["state"] in ("offline", "stalled", "connecting")
                               and self.camera.kind not in ("dir", "video"),
                               message=cs.get("error") or cs["state"])
        if not active:
            return
        frame = self.camera.buffer.get(newer_than=self._last_seq)
        if frame is None:
            self.metrics.count("no_new_frame")
            return
        self._last_seq = frame.seq
        td = self._decision_time(t, frame)
        with self._lock:
            res = self.analyzer.step(frame.image, td)
        self.last, self.last_frame = res, frame
        q = res.quality
        self._camera_condition("camera_frozen", td, q.identical, "image identical for "
                               f"{self.live.cfg.pipeline.frozen_after_s:.0f} s", frame)
        self._camera_condition("camera_obstructed", td, q.obstructed,
                               f"{100 * q.flat_fraction:.0f}% of the image has no texture", frame)
        self._camera_condition("bad_lighting", td, q.too_dark or q.overexposed,
                               f"mean brightness {q.brightness:.0f}/255", frame)
        self.metrics.record(res.detection.latency_ms if res.detection else None, res.step_ms)
        self.metrics.count(f"skipped_{res.skipped}" if res.skipped else "inferences")
        a = res.assessment
        if a is not None:
            self.history.append((round(t, 2), round(a.score, 4), round(a.p, 4),
                                 res.detection.latency_ms if res.detection else None, a.level))
            if a.event:
                self._failure_event(a, res, frame)
            elif self.failure_incident and res.detection:
                self.incidents.bump_peak(self.failure_incident, a.score, a.p, res.detection.max_conf)

    def _decision_time(self, t_wall, frame) -> float:
        """Clock for the decision engine. Live sources: wall time. Replayed
        recordings: the recording's own clock, so a replay at 8x speed makes the
        same decisions, at the same points of the print, as real time would."""
        if frame.t_media is None:
            self._media_origin = None
            return t_wall
        origin = getattr(self, "_media_origin", None)
        if origin is None or frame.t_media + origin < getattr(self, "_last_td", 0.0) - 1e-6:
            origin = t_wall - frame.t_media          # replay started or looped
            self._media_origin = origin
            with self._lock:
                self.analyzer.reset(origin + frame.t_media)
        self._last_td = origin + frame.t_media
        return self._last_td

    # ---------------------------------------------------------------- incidents & actions
    def _enabled(self, category):
        return category in self.live.cfg.decision.enabled_categories

    def _printer_info(self):
        d = self.live.cfg.decision
        info = dict(self.moon.snapshot())
        info["_warn_threshold"] = d.warn_threshold
        info["_critical_threshold"] = d.warn_threshold * d.critical_factor
        return info

    def _camera_condition(self, cat, t, cond, message="", frame=None):
        ev = self.cam_conds[cat].update(t, bool(cond))
        if ev == "open" and self._enabled(cat):
            iid = self.incidents.open(cat, "warning", frame.image if frame else None,
                                      printer=self._printer_info(), message=message,
                                      source=self.live.cfg.camera.source)
            self.cam_incidents[cat] = iid
            log.warning("incident #%d %s: %s", iid, cat, message)
            self._notify(iid, cat, 0.0)
            if self.live.cfg.actions.pause_on_camera_loss and cat == "camera_offline":
                self._pause(iid)
            self.incidents.write_report(iid)
        elif ev == "close" and cat in self.cam_incidents:
            iid = self.cam_incidents.pop(cat)
            self.incidents.update(iid, status="closed", closed_at=time.time())
            self.incidents.write_report(iid)

    def refresh_timeline(self, iid):
        self.incidents.update(iid, timeline_json=json.dumps(self._timeline()))

    def _timeline(self, seconds=1800):
        cut = time.time() - seconds
        return [(t, s, p) for t, s, p, *_ in self.history if t >= cut]

    def _failure_event(self, a, res: StepResult, frame):
        cfg = self.live.cfg
        if not self._enabled("failure"):
            return
        det = res.detection
        boxes = det.boxes if det else (self.analyzer.last_detection.boxes if self.analyzer.last_detection else [])
        pc = cfg.pipeline
        if a.event == "open":
            iid = self.incidents.open("failure", a.level, frame.image, boxes, pc.roi, pc.ignore_zones,
                                      a.score, a.p, det.max_conf if det else 0.0, self._printer_info(),
                                      f"decision score {a.score:.2f} with {a.evidence} positive frames",
                                      cfg.camera.source)
            self.failure_incident = iid
            log.warning("incident #%d failure %s score=%.2f", iid, a.level, a.score)
            self._notify(iid, "failure", a.score)
            if a.level == "critical":
                self._critical(iid)
            self.incidents.update(iid, timeline_json=json.dumps(self._timeline()))
            self.incidents.write_report(iid)
        elif a.event == "escalate" and self.failure_incident:
            iid = self.failure_incident
            self.incidents.update(iid, severity="critical", escalated_at=time.time())
            self.incidents.bump_peak(iid, a.score, a.p, det.max_conf if det else 0.0)
            self.incidents.save_evidence(iid, "critical", frame.image, boxes, pc.roi, pc.ignore_zones,
                                         "critical", a.score)
            log.warning("incident #%d escalated to critical score=%.2f", iid, a.score)
            self._critical(iid)
            self.incidents.update(iid, timeline_json=json.dumps(self._timeline()))
            self.incidents.write_report(iid)
        elif a.event == "close":
            self._close_failure("score back below clear threshold")

    def _close_failure(self, why):
        iid = self.failure_incident
        if not iid:
            return
        self.failure_incident = None
        inc = self.incidents.get(iid)
        if inc and inc["status"] == "open":
            self.incidents.update(iid, status="closed", closed_at=time.time(),
                                  timeline_json=json.dumps(self._timeline()),
                                  action_detail=(inc["action_detail"] + f" | closed: {why}").strip(" |"))
            self.incidents.write_report(iid)

    def _critical(self, iid):
        policy = self.live.cfg.actions.pause_policy
        if policy == "auto":
            self._pause(iid)
        elif policy == "confirm":
            self.incidents.update(iid, action="awaiting_confirmation",
                                  action_detail="critical: press Pause in the dashboard to stop the print")
        # notify: nothing beyond the notification already sent

    def _pause(self, iid, by="auto"):
        if not self.moon.enabled:
            self.incidents.update(iid, action="pause_failed", action_detail="no printer link configured")
            return False
        if self.moon.status.get("state") != "printing":
            self.incidents.update(iid, action="pause_skipped",
                                  action_detail=f"printer state {self.moon.status.get('state')!r}")
            return False
        ok, detail = self.moon.pause()
        self.incidents.update(iid, action="paused" if ok else "pause_failed", action_detail=f"{by}: {detail}")
        log.warning("incident #%d pause (%s): %s %s", iid, by, ok, detail)
        self.incidents.write_report(iid)
        return ok

    def _notify(self, iid, category, score):
        acts = self.live.cfg.actions
        label = CATEGORY_LABELS.get(category, category)
        text = f"HERCULES #{iid}: {label.split(' (')[0]}"
        notified = []
        if acts.gcode_notify and self.moon.notify(text, acts.notify_gcode):
            notified.append("printer display")
        if acts.webhook_url:
            payload = {"incident": iid, "category": category, "label": label, "score": round(score, 3),
                       "printer": self.moon.snapshot(), "time": time.time()}
            threading.Thread(target=_post_webhook, args=(acts.webhook_url, payload), daemon=True).start()
            notified.append("webhook")
        notified.append("dashboard")
        self.incidents.update(iid, action="notified", action_detail="notified: " + ", ".join(notified))

    # ---------------------------------------------------------------- operator actions
    def operator_pause(self, iid: int | None = None) -> tuple[bool, str]:
        if iid is None:
            ok, detail = self.moon.pause() if self.moon.enabled else (False, "no printer link")
            return ok, detail
        ok = self._pause(iid, by="operator")
        inc = self.incidents.get(iid)
        return ok, inc["action_detail"] if inc else ""

    def dismiss(self, iid: int) -> None:
        inc = self.incidents.get(iid)
        if inc is None:
            raise KeyError(iid)
        self.incidents.update(iid, status="dismissed", closed_at=time.time(),
                              action_detail=(inc["action_detail"] + " | dismissed as false alarm").strip(" |"))
        for cat, cid in list(self.cam_incidents.items()):
            if cid == iid:
                del self.cam_incidents[cat]      # stays quiet until the condition clears and returns
        if iid == self.failure_incident:
            self.failure_incident = None
            with self._lock:
                self.analyzer.tracker.dismiss(time.time())
        self.incidents.write_report(iid)

    # ---------------------------------------------------------------- views
    def status(self) -> dict:
        cfg = self.live.cfg
        res = self.last
        a = res.assessment if res else None
        det = res.detection if res else (None)
        last_det = self.analyzer.last_detection
        d = cfg.decision
        return {
            "time": time.time(),
            "monitoring": {"enabled": self.enabled, "active": self.active, "reason": self.status_reason,
                           "interval_s": cfg.pipeline.interval_s, "pause_policy": cfg.actions.pause_policy},
            "camera": self.camera.status(),
            "printer": self.moon.snapshot(),
            "detector": {"backend": self.analyzer.detector.backend,
                         "providers": self.analyzer.detector.providers,
                         "load_s": round(self.analyzer.detector.load_s, 2),
                         "model": cfg.detector.model_path},
            "analysis": None if res is None else {
                "t": res.t, "skipped": res.skipped, "quality": {
                    "brightness": round(res.quality.brightness, 1),
                    "sharpness_ratio": round(res.quality.sharpness_ratio, 2),
                    "change": None if res.quality.change is None else round(res.quality.change, 2),
                    "flags": res.quality.flags()},
                "assessment": a.to_dict() if a else None,
                "boxes": [b.as_list() for b in (det or last_det).boxes] if (det or last_det) else [],
                "max_conf": round((det or last_det).max_conf, 3) if (det or last_det) else 0.0,
                "frame_label": self.last_frame.label if self.last_frame else "",
            },
            "thresholds": {"warn": d.warn_threshold, "critical": d.warn_threshold * d.critical_factor},
            "open_failure_incident": self.failure_incident,
            "open_camera_incidents": dict(self.cam_incidents),
            "metrics": self.metrics.snapshot(),
        }

    def stream_jpeg(self, width: int) -> bytes | None:
        """Latest camera frame with the most recent detection overlay."""
        f = self.camera.buffer.peek()
        if f is None:
            return None
        key = (f.seq, id(self.last), width)
        if self._stream_cache[0] == key:
            return self._stream_cache[1]
        cfg = self.live.cfg
        det = self.analyzer.last_detection
        a = self.last.assessment if self.last else None
        boxes = det.boxes if det and self.last_frame and abs(self.last_frame.seq - f.seq) < 10_000 else []
        img = overlay.draw(f.image, boxes if self.active else [], cfg.pipeline.roi, cfg.pipeline.ignore_zones,
                           a.level if a and self.active else "ok", a.score if a and self.active else None,
                           "" if self.active else "idle")
        data = overlay.jpeg(overlay.resize_w(img, width), 80)
        self._stream_cache = (key, data)
        return data


def _post_webhook(url, payload):
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:  # noqa: BLE001
        log.warning("webhook failed: %s", e)
