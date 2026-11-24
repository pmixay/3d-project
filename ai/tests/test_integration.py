"""Monitor + mock Moonraker + dashboard API, end to end (fake detector, real everything else)."""
import time

import requests

from conftest import FakeDetector
from hercules.config import LiveConfig, load
from hercules.monitor import Monitor
from hercules.web import create_app


def make(tmp_path, session_dir, moon_url, **over):
    env = {"HERCULES_STATE_DIR": str(tmp_path / "state"), "HERCULES_CAMERA__SOURCE": session_dir,
           "HERCULES_CAMERA__REPLAY_SPEED": "10", "HERCULES_MOONRAKER__URL": moon_url,
           "HERCULES_MOONRAKER__POLL_INTERVAL_S": "0.2", "HERCULES_PIPELINE__INTERVAL_S": "0.1",
           "HERCULES_DECISION__WARMUP_S": "0", "HERCULES_DECISION__EWM_TAU_S": "2",
           "HERCULES_DECISION__EVIDENCE_WINDOW_S": "5", "HERCULES_DECISION__CLEAR_HOLD_S": "3"}
    env.update({f"HERCULES_{k.upper()}": v for k, v in over.items()})
    live = LiveConfig(load(None, env=env))
    mon = Monitor(live, detector=FakeDetector())
    return mon


def wait(cond, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cond():
            return True
        time.sleep(0.05)
    return False


def test_auto_pause_flow(tmp_path, session_dir, mock_moonraker):
    srv, pr = mock_moonraker
    requests.post(srv.url + "/mock/start?filename=part.gcode&duration_s=3600")
    mon = make(tmp_path, session_dir, srv.url, actions__pause_policy="auto")
    mon.start()
    try:
        assert wait(lambda: pr.state == "paused")
        assert wait(lambda: any(i["action"] == "paused" for i in mon.incidents.list()))
        inc = mon.incidents.list()
        fail = [i for i in inc if i["category"] == "failure"]
        assert len(fail) == 1                                  # one incident, no repeats
        i = fail[0]
        assert i["severity"] == "critical" and i["action"] == "paused" and "verified" in i["action_detail"]
        assert i["printer"]["filename"] == "part.gcode"
        assert "start_annotated.jpg" in i["evidence"]
        assert wait(lambda: (tmp_path / "state" / "incidents" / str(i["id"]) / "report.html").exists())
        # notification reached the printer display, and nothing ever resumed the print
        kinds = [e["kind"] for e in pr.log]
        assert "gcode" in kinds and "resume" not in kinds and kinds.count("pause") == 1
        # monitoring suspends while paused
        assert wait(lambda: not mon.active and "paused" in mon.status_reason)
    finally:
        mon.stop()


def test_notify_policy_never_pauses(tmp_path, session_dir, mock_moonraker):
    srv, pr = mock_moonraker
    requests.post(srv.url + "/mock/start")
    mon = make(tmp_path, session_dir, srv.url, actions__pause_policy="notify")
    mon.start()
    try:
        assert wait(lambda: any(i["severity"] == "critical" for i in mon.incidents.list()))
        time.sleep(0.5)
        assert pr.state == "printing"
        assert "pause" not in [e["kind"] for e in pr.log]
    finally:
        mon.stop()


def test_confirm_policy_and_dashboard_api(tmp_path, session_dir, mock_moonraker):
    srv, pr = mock_moonraker
    requests.post(srv.url + "/mock/start")
    mon = make(tmp_path, session_dir, srv.url, actions__pause_policy="confirm")
    app = create_app(mon).test_client()
    mon.start()
    try:
        assert wait(lambda: any(i["action"] == "awaiting_confirmation" for i in mon.incidents.list()))
        assert pr.state == "printing"                       # waits for a person
        s = app.get("/api/status").get_json()
        assert s["monitoring"]["active"] and s["printer"]["state"] == "printing"
        assert s["open_failure_incident"] and s["analysis"]["boxes"]
        assert s["metrics"]["inferences_per_min"] > 0
        iid = s["open_failure_incident"]
        r = app.post(f"/api/incidents/{iid}/pause")
        assert r.status_code == 200 and r.get_json()["ok"]
        assert pr.state == "paused"
        assert app.get(f"/incidents/{iid}/report.html").status_code == 200
        assert app.get(f"/incidents/{iid}/start_annotated.jpg").status_code == 200
        assert app.get(f"/incidents/{iid}/..%2Fincidents.db").status_code == 404
        assert app.get("/api/history").get_json()["points"]
        assert app.get("/snapshot.jpg").status_code == 200
    finally:
        mon.stop()


def test_dismiss_false_alarm(tmp_path, session_dir, mock_moonraker):
    srv, pr = mock_moonraker
    requests.post(srv.url + "/mock/start")
    mon = make(tmp_path, session_dir, srv.url, actions__pause_policy="notify")
    app = create_app(mon).test_client()
    mon.start()
    try:
        assert wait(lambda: mon.failure_incident is not None)
        iid = mon.failure_incident
        assert app.post(f"/api/incidents/{iid}/dismiss").status_code == 200
        assert mon.incidents.get(iid)["status"] == "dismissed"
        assert mon.analyzer.tracker.suppress_until > time.time()
        time.sleep(1.0)
        assert mon.failure_incident is None                 # suppressed, no immediate re-alert
    finally:
        mon.stop()


def test_settings_api_and_auth(tmp_path, session_dir, mock_moonraker):
    srv, pr = mock_moonraker
    mon = make(tmp_path, session_dir, srv.url, web__auth_token="t0k")
    app = create_app(mon).test_client()
    assert app.post("/api/settings", json={"pipeline": {"interval_s": 5}}).status_code == 401
    h = {"X-Hercules-Token": "t0k"}
    r = app.post("/api/settings", json={"pipeline": {"interval_s": 5}, "actions": {"pause_policy": "confirm"}}, headers=h)
    assert r.status_code == 200 and r.get_json()["values"]["pipeline"]["interval_s"] == 5.0
    assert mon.live.cfg.pipeline.interval_s == 5.0 and mon.analyzer.cfg.pipeline.interval_s == 5.0
    r = app.post("/api/settings", json={"moonraker": {"url": "x"}}, headers=h)
    assert r.status_code == 400
    assert app.post("/api/monitoring", json={"enabled": False}, headers=h).get_json() == {"enabled": False}


def test_monitoring_suspended_when_not_printing(tmp_path, session_dir, mock_moonraker):
    srv, pr = mock_moonraker
    mon = make(tmp_path, session_dir, srv.url)
    mon.start()
    try:
        assert wait(lambda: mon.moon.connected)
        time.sleep(0.5)
        assert not mon.active and "standby" in mon.status_reason
        assert mon.metrics.counters.get("inferences", 0) == 0
    finally:
        mon.stop()


def test_printer_link_loss_keeps_monitoring(tmp_path, session_dir, mock_moonraker):
    srv, pr = mock_moonraker
    requests.post(srv.url + "/mock/start")
    mon = make(tmp_path, session_dir, srv.url)
    mon.start()
    try:
        assert wait(lambda: mon.active)
        pr.fault = "down"
        assert wait(lambda: not mon.moon.connected)
        assert wait(lambda: mon.active and "link lost" in mon.status_reason)
        pr.fault = "ok"
        assert wait(lambda: mon.moon.connected and mon.status_reason == "monitoring active print")
    finally:
        mon.stop()


def test_camera_offline_incident(tmp_path, mock_moonraker):
    srv, pr = mock_moonraker
    idle = make(tmp_path / "idle", "http://127.0.0.1:9/stream", srv.url, decision__camera_alert_after_s="0.5",
                camera__reconnect_max_s="0.5")
    idle.start()
    try:
        time.sleep(2.0)
        assert "camera_offline" not in idle.cam_incidents     # printer idle: no alert
    finally:
        idle.stop()
    requests.post(srv.url + "/mock/start")
    mon = make(tmp_path, "http://127.0.0.1:9/stream", srv.url, decision__camera_alert_after_s="0.5",
               camera__reconnect_max_s="0.5")
    mon.start()
    try:
        assert wait(lambda: "camera_offline" in mon.cam_incidents)
        inc = mon.incidents.get(mon.cam_incidents["camera_offline"])
        assert inc["category"] == "camera_offline" and inc["status"] == "open"
    finally:
        mon.stop()


def test_reconnect_keeps_evidence_but_new_print_resets(tmp_path, session_dir, mock_moonraker):
    srv, pr = mock_moonraker
    mon = make(tmp_path, session_dir, srv.url)
    tr = mon.analyzer.tracker
    mon._printer_changed("standby", "printing", {"filename": "a.gcode", "print_duration": 0})
    tr.ewm = 0.9
    mon._printer_changed("printing", "disconnected", {"state": "disconnected"})
    mon._printer_changed("disconnected", "printing", {"filename": "a.gcode", "print_duration": 120})
    assert mon.analyzer.tracker.ewm == 0.9          # network blip: same print, evidence kept
    mon._printer_changed("printing", "paused", {"filename": "a.gcode", "print_duration": 130})
    mon._printer_changed("paused", "printing", {"filename": "a.gcode", "print_duration": 130})
    assert mon.analyzer.tracker.ewm == 0.9          # resume: kept
    mon._printer_changed("printing", "complete", {"filename": "a.gcode"})
    mon.analyzer.tracker.ewm = 0.5
    mon._printer_changed("complete", "printing", {"filename": "b.gcode", "print_duration": 0})
    assert mon.analyzer.tracker.ewm == 0.0          # a new print starts clean
