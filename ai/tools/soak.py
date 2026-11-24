#!/usr/bin/env python3
"""Extended-operation (soak) test: the full live service, replaying a recording in
a loop against the mock printer, sampled every --sample seconds.

Checks: memory growth (leak), thread count growth, analysis errors, camera
reconnects, that analyses keep happening, and that the dashboard API stays responsive.

  python tools/soak.py --source data/zenodo_fffqc/test_no_error_print_camera2 --minutes 60
"""
import argparse
import json
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psutil  # noqa: E402
import requests  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--minutes", type=float, default=60)
    ap.add_argument("--interval", type=float, default=1.0, help="analysis interval (s)")
    ap.add_argument("--speed", type=float, default=4.0, help="replay speed")
    ap.add_argument("--sample", type=float, default=30)
    ap.add_argument("--out")
    a = ap.parse_args()

    from mock_moonraker import MockPrinter, create_app as mock_app
    from werkzeug.serving import make_server
    from hercules.config import LiveConfig, load
    from hercules.monitor import Monitor
    from hercules.web import create_app

    pr = MockPrinter()
    pr.filename, pr.duration_s, pr.started_at = "soak.gcode", 10 ** 7, time.time()
    pr.set_state("printing")
    msrv = make_server("127.0.0.1", 0, mock_app(pr), threaded=True)
    threading.Thread(target=msrv.serve_forever, daemon=True).start()

    state = tempfile.mkdtemp(prefix="hercules-soak-")
    env = {"HERCULES_STATE_DIR": state, "HERCULES_CAMERA__SOURCE": a.source, "HERCULES_CAMERA__LOOP": "true",
           "HERCULES_CAMERA__REPLAY_SPEED": str(a.speed), "HERCULES_PIPELINE__INTERVAL_S": str(a.interval),
           "HERCULES_MOONRAKER__URL": f"http://127.0.0.1:{msrv.server_port}"}
    mon = Monitor(LiveConfig(load(None, env=env)))
    wsrv = make_server("127.0.0.1", 0, create_app(mon), threaded=True)
    threading.Thread(target=wsrv.serve_forever, daemon=True).start()
    api = f"http://127.0.0.1:{wsrv.server_port}"
    mon.start()

    proc = psutil.Process()
    proc.cpu_percent(None)
    samples = []
    t0 = time.time()
    while time.time() - t0 < a.minutes * 60:
        time.sleep(a.sample)
        t_api = time.perf_counter()
        st = requests.get(api + "/api/status", timeout=10).json()
        api_ms = (time.perf_counter() - t_api) * 1000
        c = st["metrics"]["counters"]
        s = {"t_min": round((time.time() - t0) / 60, 2), "rss_mb": round(proc.memory_info().rss / 2**20, 1),
             "threads": proc.num_threads(), "cpu_pct": proc.cpu_percent(None),
             "inferences": c.get("inferences", 0), "errors": c.get("errors", 0),
             "camera": st["camera"]["state"], "reconnects": st["camera"]["reconnects"],
             "printer": st["printer"]["state"], "latency_ms_mean": st["metrics"]["latency_ms_mean"],
             "api_ms": round(api_ms, 1), "open_fds": proc.num_fds()}
        samples.append(s)
        print(json.dumps(s), flush=True)
    mon.stop()
    first = samples[min(2, len(samples) - 1)]     # after warm-up (model + caches loaded)
    last = samples[-1]
    summary = {
        "minutes": a.minutes, "interval_s": a.interval, "source": a.source,
        "inferences": last["inferences"], "errors": last["errors"],
        "rss_start_mb": first["rss_mb"], "rss_end_mb": last["rss_mb"], "rss_max_mb": max(x["rss_mb"] for x in samples),
        "rss_growth_mb": round(last["rss_mb"] - first["rss_mb"], 1),
        "threads_start": first["threads"], "threads_end": last["threads"],
        "fds_start": first["open_fds"], "fds_end": last["open_fds"],
        "camera_reconnects": last["reconnects"], "api_ms_max": max(x["api_ms"] for x in samples),
        "incidents": len(mon.incidents.list(1000)),
    }
    print("SUMMARY", json.dumps(summary))
    if a.out:
        with open(a.out, "w") as f:
            json.dump({"summary": summary, "samples": samples}, f, indent=1)


if __name__ == "__main__":
    main()
