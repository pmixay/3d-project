import requests

from hercules.config import MoonrakerCfg
from hercules.moonraker import Moonraker


def client(url, **kw):
    return Moonraker(MoonrakerCfg(url=url, poll_interval_s=0.1, timeout_s=1, **kw))


def test_status_and_verified_pause(mock_moonraker):
    srv, pr = mock_moonraker
    requests.post(srv.url + "/mock/start?filename=cube.gcode&duration_s=600")
    m = client(srv.url)
    st = m.poll()
    assert m.connected and st["state"] == "printing" and st["filename"] == "cube.gcode"
    assert 0.0 <= st["progress"] < 0.1 and st["total_layer"] == 200
    ok, detail = m.pause(verify_timeout_s=3)
    assert ok and "verified" in detail
    assert pr.state == "paused"
    assert [e["kind"] for e in pr.log].count("pause") == 1
    # there is no resume method at all: the AI never resumes a print
    assert not hasattr(m, "resume")


def test_pause_when_not_printing_fails(mock_moonraker):
    srv, pr = mock_moonraker
    m = client(srv.url)
    m.poll()
    ok, detail = m.pause(verify_timeout_s=1)
    assert not ok and "failed" in detail


def test_notification_gcode(mock_moonraker):
    srv, pr = mock_moonraker
    m = client(srv.url)
    m.poll()
    assert m.notify('HERCULES #3: failure; "quoted"\nnewline')
    script = [e for e in pr.log if e["kind"] == "gcode"][0]["script"]
    assert script.startswith("M117 HERCULES #3") and ";" not in script and '"' not in script


def test_outage_and_recovery(mock_moonraker):
    srv, pr = mock_moonraker
    changes = []
    m = Moonraker(MoonrakerCfg(url=srv.url, timeout_s=1), on_change=lambda o, n, s: changes.append(n))
    m.poll()
    pr.fault = "down"
    assert m.poll()["state"] == "disconnected" and not m.connected and m.error
    pr.fault = "klippy_shutdown"
    st = m.poll()
    assert m.connected and st["state"] == "klippy_shutdown"
    pr.fault = "ok"
    assert m.poll()["state"] == "standby"
    assert changes == ["standby", "disconnected", "klippy_shutdown", "standby"]


def test_unreachable_host():
    m = client("http://127.0.0.1:9")
    assert m.poll()["state"] == "disconnected"
    ok, _ = m.pause(verify_timeout_s=0.5)
    assert not ok


def test_api_key_header(mock_moonraker):
    srv, pr = mock_moonraker
    m = client(srv.url, api_key="secret")
    assert m._headers() == {"X-Api-Key": "secret"}
