"""Hercules AI print monitor - command line.

  python -m hercules run [--config config/hercules.toml]
  python -m hercules download-model
  python -m hercules check-camera --source 0
  python -m hercules record --source 0 --out data/own/session_001 --interval 2
"""
from __future__ import annotations

import argparse
import csv
import logging
import logging.handlers
import os
import signal
import sys
import time

from . import config as config_mod


def setup_logging(cfg) -> None:
    os.makedirs(os.path.join(cfg.state_dir, "logs"), exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(cfg.log_level.upper())
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    fh = logging.handlers.RotatingFileHandler(os.path.join(cfg.state_dir, "logs", "hercules.log"),
                                              maxBytes=5 * 2**20, backupCount=5)
    fh.setFormatter(fmt)
    root.handlers[:] = [sh, fh]
    logging.getLogger("waitress").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def cmd_run(a) -> int:
    cfg = config_mod.load(a.config)
    setup_logging(cfg)
    from .monitor import Monitor
    from .web import serve
    live = config_mod.LiveConfig(cfg)
    mon = Monitor(live)
    mon.start()
    logging.getLogger("hercules").info(
        "dashboard on http://%s:%d  camera=%s  printer=%s  pause_policy=%s",
        cfg.web.host, cfg.web.port, cfg.camera.source, cfg.moonraker.url or "-", cfg.actions.pause_policy)

    def bye(*_):
        mon.stop()
        sys.exit(0)
    signal.signal(signal.SIGTERM, bye)
    try:
        serve(mon)
    finally:
        mon.stop()
    return 0


def cmd_download(a) -> int:
    cfg = config_mod.load(a.config, use_overrides=False)
    from .config import DetectorCfg
    from .detector import ensure_model
    try:
        print(ensure_model(cfg.detector), "OK" + (" (sha256 verified)" if cfg.detector.model_sha256 else ""))
    except FileNotFoundError:
        if not cfg.detector.fallback_model_path:
            raise
        fb = DetectorCfg()
        if cfg.detector.fallback_model_path != fb.model_path:
            fb.model_url, fb.model_sha256 = "", ""
        fb.model_path = cfg.detector.fallback_model_path
        print(ensure_model(fb), "OK (fallback model)")
        print(f"NOTE: {cfg.detector.model_path} is not here yet. Build it on a PC with tools/build_int8.sh "
              "and copy it over (docs/RASPBERRY_PI.md); until then the fallback model is used.")
    return 0


def _open(source):
    cfg = config_mod.load(None, use_overrides=False)
    cfg.camera.source = source
    cfg.camera.replay_speed = 0
    from .camera import Camera
    cam = Camera(cfg.camera)
    cam.start()
    return cam


def cmd_check_camera(a) -> int:
    cam = _open(a.source)
    t0 = time.time()
    while time.time() - t0 < a.seconds:
        time.sleep(0.5)
    st = cam.status()
    f = cam.buffer.peek()
    cam.stop()
    print(st)
    if f is not None and a.save:
        import cv2
        cv2.imwrite(a.save, f.image)
        print("saved", a.save)
    return 0 if st["frames"] > 0 else 1


def cmd_record(a) -> int:
    """Record a session for the team's own dataset: JPEG frames + frames.csv."""
    import cv2
    cam = _open(a.source)
    os.makedirs(a.out, exist_ok=True)
    meta = open(os.path.join(a.out, "frames.csv"), "w", newline="")
    w = csv.writer(meta)
    w.writerow(["index", "file", "t_s", "wall_time"])
    t0, n, last = time.time(), 0, 0
    print("recording, Ctrl+C to stop")
    try:
        while a.duration <= 0 or time.time() - t0 < a.duration:
            f = cam.buffer.get(newer_than=last, timeout=5)
            if f is None:
                print("no frame:", cam.status()["state"], cam.error)
                continue
            last = f.seq
            name = f"frame_{n:06d}.jpg"
            cv2.imwrite(os.path.join(a.out, name), f.image, [cv2.IMWRITE_JPEG_QUALITY, 92])
            w.writerow([n, name, round(f.t_wall - t0, 2), round(f.t_wall, 3)])
            meta.flush()
            n += 1
            time.sleep(max(0.0, a.interval - (time.time() - f.t_wall)))
    except KeyboardInterrupt:
        pass
    finally:
        cam.stop()
        meta.close()
    print(f"{n} frames in {a.out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hercules", description="Hercules AI print failure monitor")
    ap.add_argument("--config", default=os.environ.get("HERCULES_CONFIG", "config/hercules.toml"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="run the monitor and dashboard")
    sub.add_parser("download-model", help="download and verify the detector weights")
    c = sub.add_parser("check-camera", help="open a source and report what it delivers")
    c.add_argument("--source", required=True)
    c.add_argument("--seconds", type=float, default=5)
    c.add_argument("--save", help="save the last frame to this JPEG")
    r = sub.add_parser("record", help="record frames for the team's own dataset")
    r.add_argument("--source", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--interval", type=float, default=2.0)
    r.add_argument("--duration", type=float, default=0, help="seconds, 0 = until Ctrl+C")
    a = ap.parse_args(argv)
    return {"run": cmd_run, "download-model": cmd_download, "check-camera": cmd_check_camera,
            "record": cmd_record}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
