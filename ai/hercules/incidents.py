"""Incident log: SQLite table + evidence images + HTML/JSON report per incident."""
from __future__ import annotations

import html
import json
import os
import sqlite3
import threading
import time

import cv2

from . import overlay

CATEGORY_LABELS = {
    "failure": "Print failure (spaghetti / filament mess)",
    "camera_offline": "Camera offline / stream unavailable",
    "camera_frozen": "Camera image frozen",
    "camera_obstructed": "Camera view obstructed",
    "bad_lighting": "Image quality poor (too dark / overexposed / noisy)",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL,            -- open | closed | dismissed
  started_at REAL NOT NULL,
  escalated_at REAL,
  closed_at REAL,
  peak_score REAL DEFAULT 0,
  peak_p REAL DEFAULT 0,
  max_conf REAL DEFAULT 0,
  action TEXT DEFAULT 'none',      -- none | notified | awaiting_confirmation | paused | pause_failed
  action_detail TEXT DEFAULT '',
  printer_json TEXT DEFAULT '{}',
  message TEXT DEFAULT '',
  timeline_json TEXT DEFAULT '[]',
  source TEXT DEFAULT ''
);
"""


class IncidentStore:
    def __init__(self, state_dir: str):
        self.dir = os.path.join(state_dir, "incidents")
        os.makedirs(self.dir, exist_ok=True)
        self._lock = threading.Lock()
        self.db = sqlite3.connect(os.path.join(state_dir, "incidents.db"), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        # Incidents left "open" by a crash are closed on start-up.
        self.db.execute("UPDATE incidents SET status='closed', closed_at=? WHERE status='open'", (time.time(),))
        self.db.commit()

    def evidence_dir(self, iid: int) -> str:
        return os.path.join(self.dir, str(iid))

    def open(self, category, severity, frame=None, boxes=(), roi=None, ignore_zones=(), score=0.0,
             p=0.0, max_conf=0.0, printer=None, message="", source="") -> int:
        with self._lock:
            cur = self.db.execute(
                "INSERT INTO incidents(category,severity,status,started_at,peak_score,peak_p,max_conf,"
                "printer_json,message,source) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (category, severity, "open", time.time(), score, p, max_conf,
                 json.dumps(printer or {}), message, source))
            self.db.commit()
            iid = cur.lastrowid
        if frame is not None:
            self.save_evidence(iid, "start", frame, boxes, roi, ignore_zones, severity, score)
        return iid

    def save_evidence(self, iid, tag, frame, boxes, roi, ignore_zones, level, score):
        d = self.evidence_dir(iid)
        os.makedirs(d, exist_ok=True)
        cv2.imwrite(os.path.join(d, f"{tag}_raw.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        ann = overlay.draw(frame, boxes, roi, ignore_zones, level, score, f"incident #{iid}")
        cv2.imwrite(os.path.join(d, f"{tag}_annotated.jpg"), ann, [cv2.IMWRITE_JPEG_QUALITY, 90])

    def update(self, iid: int, **fields) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        with self._lock:
            self.db.execute(f"UPDATE incidents SET {cols} WHERE id=?", (*fields.values(), iid))
            self.db.commit()

    def bump_peak(self, iid: int, score: float, p: float, max_conf: float) -> None:
        with self._lock:
            self.db.execute(
                "UPDATE incidents SET peak_score=MAX(peak_score,?), peak_p=MAX(peak_p,?), "
                "max_conf=MAX(max_conf,?) WHERE id=?", (score, p, max_conf, iid))
            self.db.commit()

    def get(self, iid: int) -> dict | None:
        with self._lock:
            r = self.db.execute("SELECT * FROM incidents WHERE id=?", (iid,)).fetchone()
        return self._row(r) if r else None

    def list(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self.db.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    def _row(self, r) -> dict:
        d = dict(r)
        d["printer"] = json.loads(d.pop("printer_json") or "{}")
        d["timeline"] = json.loads(d.pop("timeline_json") or "[]")
        d["label"] = CATEGORY_LABELS.get(d["category"], d["category"])
        ed = self.evidence_dir(d["id"])
        d["evidence"] = sorted(f for f in os.listdir(ed) if f.endswith(".jpg")) if os.path.isdir(ed) else []
        return d

    def write_report(self, iid: int) -> str:
        inc = self.get(iid)
        if inc is None:
            raise KeyError(iid)
        d = self.evidence_dir(iid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "report.json"), "w") as f:
            json.dump(inc, f, indent=2, default=str)
        path = os.path.join(d, "report.html")
        with open(path, "w") as f:
            f.write(render_report(inc))
        return path


def _ts(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) if t else "-"


def _sparkline(points, w=640, h=120, warn=None, crit=None):
    if len(points) < 2:
        return "<p>not enough data points</p>"
    t0, t1 = points[0][0], points[-1][0]
    vmax = max(max(p[1] for p in points), (crit or 0) * 1.1, 0.5)
    sx = lambda t: 4 + (w - 8) * (t - t0) / max(t1 - t0, 1e-6)  # noqa: E731
    sy = lambda v: h - 4 - (h - 8) * v / vmax  # noqa: E731
    path = " ".join(f"{'M' if i == 0 else 'L'}{sx(t):.1f},{sy(v):.1f}" for i, (t, v, *_) in enumerate(points))
    lines = ""
    for val, col in ((warn, "#e0a030"), (crit, "#e05050")):
        if val:
            lines += f'<line x1="0" x2="{w}" y1="{sy(val):.1f}" y2="{sy(val):.1f}" stroke="{col}" stroke-dasharray="4 4"/>'
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="background:#15181c;border:1px solid #2a2f36">'
            f'{lines}<path d="{path}" fill="none" stroke="#5ab0ff" stroke-width="2"/></svg>'
            f'<div class="muted">{_ts(t0)} → {_ts(t1)} · max score {max(p[1] for p in points):.2f}</div>')


def render_report(inc: dict) -> str:
    e = html.escape
    pr = inc["printer"] or {}
    tl = inc["timeline"] or []
    warn = pr.get("_warn_threshold")
    crit = pr.get("_critical_threshold")
    imgs = "".join(f'<figure><img src="{e(f)}"><figcaption>{e(f)}</figcaption></figure>'
                   for f in inc["evidence"] if "annotated" in f)
    rows = [
        ("Incident", f"#{inc['id']}"), ("Category", inc["label"]), ("Severity", inc["severity"]),
        ("Status", inc["status"]), ("Started", _ts(inc["started_at"])),
        ("Escalated", _ts(inc["escalated_at"])), ("Closed", _ts(inc["closed_at"])),
        ("Peak decision score", f"{inc['peak_score']:.3f}"), ("Peak frame score p", f"{inc['peak_p']:.3f}"),
        ("Max box confidence", f"{inc['max_conf']:.3f}"),
        ("Action", f"{inc['action']} {inc['action_detail']}"),
        ("Printer state", str(pr.get("state", "unknown"))), ("File", str(pr.get("filename", "-"))),
        ("Progress", f"{100 * pr['progress']:.1f} %" if isinstance(pr.get("progress"), (int, float)) else "-"),
        ("Print time", f"{pr['print_duration'] / 60:.1f} min" if pr.get("print_duration") else "-"),
        ("Camera source", inc.get("source", "")), ("Message", inc["message"]),
    ]
    table = "".join(f"<tr><th>{e(k)}</th><td>{e(str(v))}</td></tr>" for k, v in rows)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hercules incident #{inc['id']}</title>
<style>body{{background:#0f1114;color:#d8dde3;font:14px/1.45 system-ui,sans-serif;margin:0;padding:16px;max-width:1000px}}
h1{{font-size:18px}} table{{border-collapse:collapse;width:100%;margin:12px 0}}
th,td{{text-align:left;padding:5px 8px;border-bottom:1px solid #262b31}} th{{color:#8b949e;width:220px;font-weight:500}}
figure{{margin:12px 0}} img{{max-width:100%;border:1px solid #2a2f36}} .muted{{color:#8b949e;font-size:12px}}</style></head>
<body><h1>HERCULES — incident report #{inc['id']}: {e(inc['label'])}</h1>
<table>{table}</table><h2 style="font-size:15px">Decision score timeline</h2>{_sparkline(tl, warn=warn, crit=crit)}
<h2 style="font-size:15px">Evidence</h2>{imgs or '<p>no images</p>'}
<p class="muted">Detector: Obico pretrained failure model (third-party, AGPL-3.0 project). Decision engine, camera checks
and report: Hercules AI subsystem. Generated {_ts(time.time())}.</p></body></html>"""
