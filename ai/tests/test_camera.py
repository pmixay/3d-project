import time

import cv2
from flask import Flask, Response

from conftest import ServerThread, textured
from hercules.camera import Camera, source_kind
from hercules.config import CameraCfg


def wait(cond, timeout=10):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cond():
            return True
        time.sleep(0.05)
    return False


def test_source_kind(tmp_path):
    assert source_kind("0") == "usb"
    assert source_kind("/dev/video2") == "usb"
    assert source_kind("http://pi/webcam/?action=stream") == "http"
    assert source_kind(str(tmp_path)) == "dir"
    assert source_kind("clip.mp4") == "video"


def test_directory_replay_ends(session_dir):
    cam = Camera(CameraCfg(source=session_dir, replay_speed=0))
    cam.start()
    assert wait(lambda: cam.state == "ended")
    assert cam.frames == 120
    assert cam.buffer.peek().label == "frame_000119.jpg"
    assert cam.buffer.peek().t_media == 119.0


def test_video_file_replay(tmp_path):
    path = str(tmp_path / "clip.avi")
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 10, (320, 240))
    for i in range(15):
        vw.write(textured(i, 240, 320))
    vw.release()
    cam = Camera(CameraCfg(source=path, replay_speed=0))
    cam.start()
    assert wait(lambda: cam.state == "ended")
    assert cam.frames == 15 and cam.resolution == (320, 240)


def test_latest_frame_slot_is_bounded():
    from hercules.camera import LatestFrame
    lf = LatestFrame()
    for i in range(100):
        lf.put(textured(0, 10, 10))
    f = lf.get()
    assert f.seq == 100 and lf.dropped == 99
    assert lf.get(newer_than=f.seq) is None


def _jpeg(i):
    return cv2.imencode(".jpg", textured(i, 120, 160))[1].tobytes()


def test_mjpeg_stream_and_reconnect():
    app = Flask("mjpeg")
    state = {"fail": False}

    @app.get("/stream")
    def stream():
        if state["fail"]:
            return "camera gone", 503

        def gen():
            for i in range(40):
                yield b"--b\r\nContent-Type: image/jpeg\r\n\r\n" + _jpeg(i) + b"\r\n"
                time.sleep(0.02)
        return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=b")

    srv = ServerThread(app)
    cam = Camera(CameraCfg(source=srv.url + "/stream", reconnect_max_s=1))
    cam.start()
    try:
        assert wait(lambda: cam.frames >= 10)
        assert cam.kind == "mjpeg" and cam.resolution == (160, 120)
        state["fail"] = True                  # stream ends, server now answers 503
        assert wait(lambda: cam.state == "offline" and cam.error)
        state["fail"] = False                 # camera comes back
        n = cam.frames
        assert wait(lambda: cam.frames > n + 5, timeout=15)
        assert cam.reconnects >= 1
    finally:
        cam.stop()
        srv.stop()


def test_snapshot_url():
    app = Flask("snap")
    n = {"i": 0}

    @app.get("/snap")
    def snap():
        n["i"] += 1
        return Response(_jpeg(n["i"]), mimetype="image/jpeg")

    srv = ServerThread(app)
    cam = Camera(CameraCfg(source=srv.url + "/snap", snapshot_interval_s=0.05))
    cam.start()
    try:
        assert wait(lambda: cam.frames >= 5)
        assert cam.kind == "http"
    finally:
        cam.stop()
        srv.stop()


def test_unreachable_source_goes_offline():
    cam = Camera(CameraCfg(source="http://127.0.0.1:9/none", reconnect_max_s=1))
    cam.start()
    try:
        assert wait(lambda: cam.state == "offline")
        assert cam.status()["state"] == "offline" and cam.error
    finally:
        cam.stop()


# ---------------------------------------------------------------- Raspberry Pi CSI camera
FAKE_RPICAM = r'''#!{python}
import sys, time, cv2, numpy as np
args = sys.argv[1:]
w = int(args[args.index("--width") + 1]); h = int(args[args.index("--height") + 1])
if "{mode}" == "fail":
    sys.stderr.write("ERROR: *** no cameras available ***\n"); sys.exit(1)
sys.stderr.write("fake rpicam-vid started\n"); sys.stderr.flush()
out = sys.stdout.buffer
for i in range(10**6):
    img = (np.random.default_rng(i).random((h, w, 3)) * 255).astype("uint8")
    out.write(cv2.imencode(".jpg", img)[1].tobytes()); out.flush()
    time.sleep(0.02)
'''


def _fake_tool(tmp_path, monkeypatch, mode="ok"):
    import sys
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "rpicam-vid"
    exe.write_text(FAKE_RPICAM.replace("{python}", sys.executable).replace("{mode}", mode))
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}:" + __import__("os").environ["PATH"])


def test_csi_camera_stream(tmp_path, monkeypatch):
    _fake_tool(tmp_path, monkeypatch)
    cam = Camera(CameraCfg(source="csi", width=320, height=240, fps=5))
    cam.start()
    try:
        assert wait(lambda: cam.frames >= 5)
        assert cam.kind == "csi" and cam.resolution == (320, 240)
    finally:
        cam.stop()
    assert cam._proc is None                       # child process cleaned up


def test_csi_camera_failure_is_reported(tmp_path, monkeypatch):
    _fake_tool(tmp_path, monkeypatch, mode="fail")
    cam = Camera(CameraCfg(source="csi:0", reconnect_max_s=1))
    cam.start()
    try:
        assert wait(lambda: "no cameras available" in cam.error)
        assert cam.status()["state"] == "offline"
    finally:
        cam.stop()


def test_csi_command_is_fixed_and_validated(monkeypatch):
    import pytest
    from hercules.camera import csi_command
    from hercules.config import Config, validate
    monkeypatch.setattr("shutil.which", lambda t: "/usr/bin/" + t if t == "rpicam-vid" else None)
    cmd = csi_command(CameraCfg(source="csi:1", width=640, height=480, fps=5))
    assert cmd[0] == "/usr/bin/rpicam-vid" and cmd[cmd.index("--camera") + 1] == "1"
    for bad in ("csi:0; rm -rf ~", "csi:$(reboot)", "csi:../x"):
        with pytest.raises(IOError):
            csi_command(CameraCfg(source=bad))
        cfg = Config()
        cfg.camera.source = bad
        with pytest.raises(ValueError):
            validate(cfg)
    monkeypatch.setattr("shutil.which", lambda t: None)
    with pytest.raises(IOError, match="rpicam-apps"):
        csi_command(CameraCfg(source="csi"))


def test_frame_averaging_reduces_noise():
    import numpy as np
    from hercules.camera import Frame
    base = textured(3, 120, 160).astype(np.float32)
    cam = Camera(CameraCfg(source="0", average_frames=4))
    rng = np.random.default_rng(0)
    for i in range(4):
        cam._publish(np.clip(base + rng.normal(0, 18, base.shape), 0, 255).astype(np.uint8))
    f = cam.buffer.peek()
    single = np.abs(f.image.astype(np.float32) - base).mean()
    avg = np.abs(cam.averaged(f).astype(np.float32) - base).mean()
    assert avg < 0.65 * single                     # ~1/sqrt(4) of the noise
    assert cam.averaged(Frame(f.image, 1, 0.0, 5.0)) is f.image   # replays are not averaged
