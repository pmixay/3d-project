#!/usr/bin/env python3
"""Mock Moonraker server for integration tests and the competition demo.

Implements the subset of the Moonraker HTTP API that Hercules uses, with the
same response envelopes ({"result": ...}), plus /mock/* control endpoints:

  POST /mock/start?filename=demo.gcode&duration_s=3600   start a simulated print
  POST /mock/fault?mode=ok|down|klippy_shutdown|slow     simulate failures
  GET  /mock/log                                         every command received
  POST /mock/reset

A real printer is never involved. Moonraker API reference:
https://moonraker.readthedocs.io/en/latest/external_api/printer/
"""
from __future__ import annotations

import argparse
import threading
import time

from flask import Flask, jsonify, request


class MockPrinter:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.state = "standby"
        self.filename = ""
        self.duration_s = 3600.0
        self.printed_s = 0.0
        self.resumed_at: float | None = None
        self.started_at: float | None = None
        self.fault = "ok"
        self.message = ""
        self.log: list[dict] = []

    def print_duration(self):
        extra = time.time() - self.resumed_at if self.state == "printing" and self.resumed_at else 0.0
        return self.printed_s + extra

    def tick(self):
        if self.state == "printing" and self.print_duration() >= self.duration_s:
            self.printed_s, self.resumed_at, self.state = self.duration_s, None, "complete"

    def set_state(self, new):
        if self.state == "printing" and new != "printing":
            self.printed_s = self.print_duration()
            self.resumed_at = None
        if new == "printing" and self.state != "printing":
            self.resumed_at = time.time()
        self.state = new


def create_app(printer: MockPrinter | None = None) -> Flask:
    app = Flask(__name__)
    pr = printer or MockPrinter()
    app.config["printer"] = pr

    def record(kind, **kw):
        pr.log.append({"t": time.time(), "kind": kind, "state": pr.state, **kw})

    @app.before_request
    def faults():
        if request.path.startswith("/mock/"):
            return None
        if pr.fault == "down":
            return jsonify({"error": {"code": 503, "message": "mock: service down"}}), 503
        if pr.fault == "slow":
            time.sleep(6)
        return None

    @app.get("/server/info")
    def server_info():
        ks = "shutdown" if pr.fault == "klippy_shutdown" else "ready"
        return jsonify({"result": {"klippy_connected": True, "klippy_state": ks,
                                   "components": ["mock"], "moonraker_version": "mock"}})

    @app.get("/printer/info")
    def printer_info():
        return jsonify({"result": {"state": "ready", "state_message": "Printer is ready",
                                   "hostname": "mock-hercules", "software_version": "mock"}})

    @app.get("/printer/objects/query")
    def query():
        if pr.fault == "klippy_shutdown":
            return jsonify({"error": {"code": 503, "message": "Klippy Host not connected"}}), 503
        with pr.lock:
            pr.tick()
            dur = pr.print_duration()
            prog = min(1.0, dur / pr.duration_s) if pr.state != "standby" else 0.0
            status = {
                "print_stats": {"state": pr.state, "filename": pr.filename, "print_duration": dur,
                                "total_duration": (time.time() - pr.started_at) if pr.started_at else 0.0,
                                "filament_used": 0.0, "message": pr.message,
                                "info": {"total_layer": 200, "current_layer": int(prog * 200)}},
                "virtual_sdcard": {"progress": prog, "is_active": pr.state == "printing"},
                "webhooks": {"state": "ready", "state_message": "Printer is ready"},
                "display_status": {"progress": prog, "message": pr.message},
            }
        wanted = set(request.args.keys())
        return jsonify({"result": {"eventtime": time.monotonic(),
                                   "status": {k: v for k, v in status.items() if not wanted or k in wanted}}})

    @app.post("/printer/print/pause")
    def pause():
        with pr.lock:
            record("pause")
            if pr.state != "printing":
                return jsonify({"error": {"code": 400, "message": "Print is not running"}}), 400
            pr.set_state("paused")
        return jsonify({"result": "ok"})

    @app.post("/printer/print/resume")
    def resume():
        with pr.lock:
            record("resume")
            if pr.state == "paused":
                pr.set_state("printing")
        return jsonify({"result": "ok"})

    @app.post("/printer/print/cancel")
    def cancel():
        with pr.lock:
            record("cancel")
            pr.set_state("cancelled")
        return jsonify({"result": "ok"})

    @app.post("/printer/gcode/script")
    def gcode():
        script = request.args.get("script") or (request.get_json(silent=True) or {}).get("script", "")
        with pr.lock:
            record("gcode", script=script)
            if script.upper().startswith("M117"):
                pr.message = script[4:].strip()
            if script.strip().upper() == "PAUSE" and pr.state == "printing":
                pr.set_state("paused")
        return jsonify({"result": "ok"})

    @app.post("/mock/start")
    def mock_start():
        with pr.lock:
            pr.filename = request.args.get("filename", "demo.gcode")
            pr.duration_s = float(request.args.get("duration_s", 3600))
            pr.printed_s, pr.started_at, pr.message = 0.0, time.time(), ""
            pr.state = "standby"
            pr.set_state("printing")
            record("mock_start", filename=pr.filename)
        return jsonify({"result": "ok"})

    @app.post("/mock/fault")
    def mock_fault():
        pr.fault = request.args.get("mode", "ok")
        record("mock_fault", mode=pr.fault)
        return jsonify({"result": pr.fault})

    @app.post("/mock/reset")
    def mock_reset():
        with pr.lock:
            pr.reset()
        return jsonify({"result": "ok"})

    @app.get("/mock/log")
    def mock_log():
        return jsonify({"result": pr.log, "state": pr.state})

    return app


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7125)
    ap.add_argument("--start-print", metavar="FILENAME", help="start a simulated print immediately")
    ap.add_argument("--duration-s", type=float, default=3600)
    a = ap.parse_args()
    pr = MockPrinter()
    if a.start_print:
        pr.filename, pr.duration_s, pr.started_at = a.start_print, a.duration_s, time.time()
        pr.set_state("printing")
    create_app(pr).run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
