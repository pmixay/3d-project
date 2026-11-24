import os
import sys
import threading

import cv2
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from hercules.detector import Box, Detection  # noqa: E402

MODEL = os.path.join(ROOT, "models", "obico-failure-5a6b1be1fa.onnx")


def textured(seed=0, h=270, w=480, red=False):
    rng = np.random.default_rng(seed)
    img = (rng.random((h, w, 3)) * 180 + 40).astype(np.uint8)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    if red:
        img[h // 3: 2 * h // 3, w // 3: 2 * w // 3] = (0, 0, 255)
    return img


class FakeDetector:
    """Deterministic stand-in for the network: a big pure-red patch = failure."""
    backend, providers, load_s = "fake", ["fake"], 0.0

    def detect(self, img, pcfg, box_threshold=None):
        red = (img[..., 2] > 240) & (img[..., 1] < 20) & (img[..., 0] < 20)
        frac = float(red.mean())
        h, w = img.shape[:2]
        if frac > 0.05:
            b = Box(w / 3, h / 3, 2 * w / 3, 2 * h / 3, 0.9)
            return Detection([b], 0.9, 0.9, 1.0)
        return Detection([], 0.0, 0.0, 1.0)


@pytest.fixture
def session_dir(tmp_path):
    """40 normal frames then 80 failure frames, 1 s apart (frames.csv)."""
    d = tmp_path / "session"
    d.mkdir()
    rows = ["index,file,t_s"]
    for i in range(120):
        name = f"frame_{i:06d}.jpg"
        cv2.imwrite(str(d / name), textured(i, red=i >= 40))
        rows.append(f"{i},{name},{float(i)}")
    (d / "frames.csv").write_text("\n".join(rows) + "\n")
    return str(d)


class ServerThread:
    """Run a WSGI app (Flask) on a free localhost port in a thread."""

    def __init__(self, app):
        from werkzeug.serving import make_server
        self.srv = make_server("127.0.0.1", 0, app, threaded=True)
        self.port = self.srv.server_port
        self.url = f"http://127.0.0.1:{self.port}"
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()

    def stop(self):
        self.srv.shutdown()


@pytest.fixture
def mock_moonraker():
    from mock_moonraker import MockPrinter, create_app
    pr = MockPrinter()
    st = ServerThread(create_app(pr))
    yield st, pr
    st.stop()
