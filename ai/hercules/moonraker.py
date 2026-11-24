"""Moonraker (Klipper API server) client.

Uses only documented HTTP endpoints (https://moonraker.readthedocs.io/en/latest/external_api/):
  GET  /server/info                         klippy connection state
  GET  /printer/objects/query?print_stats&virtual_sdcard&webhooks&display_status
  POST /printer/print/pause                 pause (PAUSE macro)
  POST /printer/gcode/script?script=...     on-printer notification (M117 / RESPOND)

Polling every couple of seconds is used instead of the websocket subscription:
it is stateless, recovers from Moonraker/Klipper restarts without
resubscribe logic, and the print state changes on a timescale of seconds.

Deliberately NOT implemented: resume, cancel, heater or motion commands. The AI
subsystem can only *pause* a print; firmware safety (thermal runaway, endstops,
emergency stop) stays entirely in Klipper and does not depend on this process.
"""
from __future__ import annotations

import logging
import threading
import time

import requests

from .config import MoonrakerCfg

log = logging.getLogger("hercules.moonraker")

QUERY = "/printer/objects/query?print_stats&virtual_sdcard&webhooks&display_status"


class Moonraker:
    def __init__(self, cfg: MoonrakerCfg, on_change=None):
        self.cfg = cfg
        self.on_change = on_change      # callback(old_state, new_state, status_dict)
        self.session = requests.Session()
        self.connected = False
        self.error = ""
        self.status: dict = {"state": "unknown"}
        self.last_ok = 0.0
        self.failures = 0
        self.commands: list[dict] = []  # audit log of commands we sent
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.url)

    def _headers(self):
        return {"X-Api-Key": self.cfg.api_key} if self.cfg.api_key else {}

    def _url(self, path):
        return self.cfg.url.rstrip("/") + path

    def start(self):
        if not self.enabled:
            return
        self._stop.clear()
        self.poll()                     # know the printer state before the analyser's first tick
        self._thread = threading.Thread(target=self._loop, name="moonraker", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        while not self._stop.is_set():
            self.poll()
            delay = self.cfg.poll_interval_s if self.connected else min(30.0, self.cfg.poll_interval_s * 2 ** min(self.failures, 4))
            self._stop.wait(delay)

    def poll(self) -> dict:
        old = self.status.get("state")
        try:
            r = self.session.get(self._url(QUERY), headers=self._headers(), timeout=self.cfg.timeout_s)
            if r.status_code != 200:
                # Moonraker answers but Klippy is not ready (startup / shutdown / disconnected)
                ri = self.session.get(self._url("/server/info"), headers=self._headers(),
                                      timeout=self.cfg.timeout_s)
                if ri.status_code != 200:
                    raise IOError(f"Moonraker HTTP {r.status_code}/{ri.status_code}")
                info = ri.json().get("result", {})
                new = {"state": f"klippy_{info.get('klippy_state', 'unavailable')}",
                       "klippy_state": info.get("klippy_state", "unavailable")}
            else:
                s = r.json()["result"]["status"]
                ps, vs = s.get("print_stats", {}), s.get("virtual_sdcard", {})
                wh, ds = s.get("webhooks", {}), s.get("display_status", {})
                info = ps.get("info") or {}
                new = {
                    "state": ps.get("state", "unknown"),
                    "klippy_state": wh.get("state", "unknown"),
                    "filename": ps.get("filename", ""),
                    "print_duration": ps.get("print_duration", 0.0),
                    "total_duration": ps.get("total_duration", 0.0),
                    "progress": vs.get("progress", ds.get("progress", 0.0)),
                    "message": ds.get("message") or ps.get("message", ""),
                    "current_layer": info.get("current_layer"),
                    "total_layer": info.get("total_layer"),
                }
            if not self.connected:
                log.info("moonraker connected: %s", self.cfg.url)
            self.connected, self.error, self.failures, self.last_ok = True, "", 0, time.time()
        except Exception as e:  # noqa: BLE001
            if self.connected or not self.error:
                log.warning("moonraker unreachable: %s", e)
            self.connected = False
            self.failures += 1
            self.error = f"{type(e).__name__}: {e}"[:200]
            new = {"state": "disconnected"}
        self.status = new
        if new.get("state") != old and self.on_change:
            try:
                self.on_change(old, new.get("state"), new)
            except Exception:  # noqa: BLE001
                log.exception("state change handler failed")
        return new

    def snapshot(self) -> dict:
        return {"enabled": self.enabled, "url": self.cfg.url, "connected": self.connected,
                "error": self.error, "last_ok": self.last_ok, **self.status}

    def _post(self, path, params=None) -> tuple[bool, str]:
        entry = {"t": time.time(), "path": path, "params": params or {}}
        try:
            r = self.session.post(self._url(path), params=params, headers=self._headers(),
                                  timeout=max(self.cfg.timeout_s, 10))
            ok = r.status_code == 200
            entry.update(ok=ok, http=r.status_code, body=r.text[:200])
        except Exception as e:  # noqa: BLE001
            ok = False
            entry.update(ok=False, error=str(e)[:200])
        self.commands.append(entry)
        del self.commands[:-100]
        return ok, entry.get("body") or entry.get("error", "")

    def pause(self, verify_timeout_s: float = 15.0) -> tuple[bool, str]:
        """Pause the print and confirm through print_stats that it actually paused."""
        if not self.enabled:
            return False, "no Moonraker URL configured"
        ok, detail = self._post("/printer/print/pause")
        if not ok:
            return False, f"pause request failed: {detail}"
        deadline = time.time() + verify_timeout_s
        while time.time() < deadline:
            if self.poll().get("state") == "paused":
                return True, "pause verified (print_stats.state == paused)"
            time.sleep(0.5)
        return False, f"pause sent but printer state is {self.status.get('state')!r}"

    def notify(self, text: str, gcode_template: str = "M117 {text}") -> bool:
        if not self.enabled or not self.connected:
            return False
        safe = "".join(ch for ch in text if ch.isprintable() and ch not in '"\n;')[:80]
        ok, _ = self._post("/printer/gcode/script", {"script": gcode_template.replace("{text}", safe)})
        return ok
