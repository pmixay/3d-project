"""Dashboard HTTP server: JSON API, MJPEG stream, incident evidence and reports."""
from __future__ import annotations

import dataclasses as dc
import functools
import os
import re
import time

from flask import Flask, Response, abort, jsonify, request, send_from_directory

from .config import RUNTIME_EDITABLE
from .monitor import Monitor

STATIC = os.path.join(os.path.dirname(__file__), "static")


def create_app(mon: Monitor) -> Flask:
    app = Flask(__name__, static_folder=None)
    live = mon.live

    def guarded(fn):
        @functools.wraps(fn)
        def wrap(*a, **kw):
            tok = live.cfg.web.auth_token
            if tok and request.headers.get("X-Hercules-Token") != tok:
                return jsonify({"error": "missing or wrong X-Hercules-Token"}), 401
            return fn(*a, **kw)
        return wrap

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "index.html")

    @app.get("/static/<path:name>")
    def static_files(name):
        return send_from_directory(STATIC, name)

    @app.get("/api/status")
    def status():
        return jsonify(mon.status())

    @app.get("/api/history")
    def history():
        since = float(request.args.get("since", 0))
        pts = [h for h in list(mon.history) if h[0] > since]
        return jsonify({"points": pts, "fields": ["t", "score", "p", "latency_ms", "level"]})

    @app.get("/stream.mjpg")
    def stream():
        width = int(request.args.get("w", live.cfg.web.stream_width))

        def gen():
            last = None
            while True:
                data = mon.stream_jpeg(width)
                if data is not None and data is not last:
                    last = data
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                           + str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n")
                time.sleep(1.0 / max(0.5, live.cfg.web.stream_fps))
        return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame",
                        headers={"Cache-Control": "no-store"})

    @app.get("/snapshot.jpg")
    def snapshot():
        raw = request.args.get("raw") == "1"
        f = mon.camera.buffer.peek()
        if f is None:
            abort(503)
        from . import overlay
        data = overlay.jpeg(f.image, 90) if raw else mon.stream_jpeg(live.cfg.web.stream_width)
        return Response(data, mimetype="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/api/incidents")
    def incidents():
        return jsonify(mon.incidents.list(int(request.args.get("limit", 50))))

    @app.get("/api/incidents/<int:iid>")
    def incident(iid):
        inc = mon.incidents.get(iid)
        return jsonify(inc) if inc else (jsonify({"error": "not found"}), 404)

    @app.get("/incidents/<int:iid>/<name>")
    def incident_file(iid, name):
        if not re.fullmatch(r"[\w\-]+\.(jpg|html|json)", name):
            abort(404)
        d = mon.incidents.evidence_dir(iid)
        if name in ("report.html", "report.json"):
            inc = mon.incidents.get(iid)
            if inc is None:
                abort(404)
            if inc["status"] == "open" and iid == mon.failure_incident:
                mon.refresh_timeline(iid)      # an open incident's report shows the latest data
            mon.incidents.write_report(iid)
        return send_from_directory(os.path.abspath(d), name)

    @app.post("/api/incidents/<int:iid>/dismiss")
    @guarded
    def dismiss(iid):
        try:
            mon.dismiss(iid)
        except KeyError:
            return jsonify({"error": "not found"}), 404
        return jsonify({"ok": True})

    @app.post("/api/incidents/<int:iid>/pause")
    @guarded
    def pause_incident(iid):
        ok, detail = mon.operator_pause(iid)
        return jsonify({"ok": ok, "detail": detail}), (200 if ok else 409)

    @app.post("/api/printer/pause")
    @guarded
    def pause():
        ok, detail = mon.operator_pause(None)
        return jsonify({"ok": ok, "detail": detail}), (200 if ok else 409)

    @app.post("/api/monitoring")
    @guarded
    def monitoring():
        body = request.get_json(force=True, silent=True) or {}
        mon.enabled = bool(body.get("enabled", True))
        return jsonify({"enabled": mon.enabled})

    @app.get("/api/settings")
    def get_settings():
        cfg = live.cfg
        return jsonify({"values": {s: {k: getattr(getattr(cfg, s), k) for k in keys}
                                   for s, keys in RUNTIME_EDITABLE.items()},
                        "editable": {s: sorted(k) for s, k in RUNTIME_EDITABLE.items()},
                        "categories": ["failure", "camera_offline", "camera_frozen",
                                       "camera_obstructed", "bad_lighting"]})

    @app.post("/api/settings")
    @guarded
    def set_settings():
        body = request.get_json(force=True, silent=True) or {}
        old_cam = dc.asdict(live.cfg.camera)
        try:
            live.update(body)
        except (ValueError, TypeError) as e:
            return jsonify({"error": str(e)}), 400
        if dc.asdict(live.cfg.camera) != old_cam:
            mon.restart_camera()
        return get_settings()

    @app.get("/api/commands")
    def commands():
        return jsonify(mon.moon.commands[-50:])

    return app


def serve(mon: Monitor) -> None:
    app = create_app(mon)
    w = mon.live.cfg.web
    try:
        from waitress import serve as wserve
        wserve(app, host=w.host, port=w.port, threads=16, channel_timeout=30)
    except ImportError:
        app.run(host=w.host, port=w.port, threaded=True)
