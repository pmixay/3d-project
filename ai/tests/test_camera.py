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
