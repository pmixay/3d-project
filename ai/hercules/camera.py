"""Camera acquisition.

Every source runs in its own thread and publishes into a single-slot
"latest frame" buffer. The consumer (the analyser) always takes the newest
frame; older ones are dropped and counted. This keeps memory bounded and
means slow inference can never build a backlog of stale frames.

Supported sources (CameraCfg.source):
  "0", "1", "/dev/video0"        USB / V4L2 camera
  "http://.../?action=stream"     MJPEG stream (Crowsnest / ustreamer / mjpg-streamer)
  "http://.../?action=snapshot"   single-JPEG URL, polled every snapshot_interval_s
  "/path/video.mp4"               video file replay (paced by the file's fps)
  "/path/dir/"                    directory of JPEG/PNG frames (paced by frames.csv t_s)
"""
from __future__ import annotations

import csv
import dataclasses as dc
import glob
import logging
import os
import threading
import time

import cv2
import numpy as np
import requests

from .config import CameraCfg

log = logging.getLogger("hercules.camera")


@dc.dataclass
class Frame:
    image: np.ndarray
    seq: int
    t_wall: float           # time.time() when the frame arrived
    t_media: float | None   # position in a replayed file (s), None for live sources
    label: str = ""         # e.g. replayed file name


class LatestFrame:
    def __init__(self):
        self._cond = threading.Condition()
        self._frame: Frame | None = None
        self._seq = 0
        self._taken_seq = 0
        self.dropped = 0

    def put(self, image: np.ndarray, t_media: float | None = None, label: str = "") -> None:
        with self._cond:
            self._seq += 1
            if self._frame is not None and self._frame.seq > self._taken_seq:
                self.dropped += 1
            self._frame = Frame(image, self._seq, time.time(), t_media, label)
            self._cond.notify_all()

    def get(self, newer_than: int = 0, timeout: float | None = None) -> Frame | None:
        with self._cond:
            if timeout:
                self._cond.wait_for(lambda: self._frame is not None and self._frame.seq > newer_than, timeout)
            f = self._frame
            if f is None or f.seq <= newer_than:
                return None
            self._taken_seq = max(self._taken_seq, f.seq)
            return f

    def peek(self) -> Frame | None:
        return self._frame


class Camera:
    """Owns the acquisition thread for one source; restart() swaps sources."""

    def __init__(self, cfg: CameraCfg):
        self.cfg = cfg
        self.buffer = LatestFrame()
        self.state = "stopped"          # connecting | online | stalled | offline | ended | stopped
        self.error = ""
        self.kind = ""
        self.resolution = (0, 0)
        self.fps = 0.0
        self.frames = 0
        self.reconnects = 0
        self.last_frame_wall = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ---- lifecycle -------------------------------------------------------
    def start(self) -> None:
        with self._lock:
            self._stop.clear()
            self.kind = source_kind(self.cfg.source)
            self.state = "connecting"
            self._thread = threading.Thread(target=self._run, name="camera", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._stop.set()
            t = self._thread
        if t:
            t.join(timeout=5)
        self.state = "stopped"

    def restart(self) -> None:
        self.stop()
        self.buffer = LatestFrame()
        self.frames = 0
        self.fps = 0.0
        self.start()

    def status(self) -> dict:
        age = time.time() - self.last_frame_wall if self.last_frame_wall else None
        state = self.state
        if state == "online" and age is not None and age > self.cfg.stale_after_s:
            state = "stalled"
        return {
            "state": state, "kind": self.kind, "source": self.cfg.source,
            "error": self.error, "resolution": list(self.resolution),
            "fps": round(self.fps, 2), "frames": self.frames,
            "dropped": self.buffer.dropped, "reconnects": self.reconnects,
            "frame_age_s": None if age is None else round(age, 2),
        }

    # ---- internals -------------------------------------------------------
    def _publish(self, img: np.ndarray, t_media=None, label="") -> None:
        if img is None or img.size == 0:
            return
        now = time.time()
        if self.last_frame_wall:
            dt = now - self.last_frame_wall
            if dt > 0:
                inst = 1.0 / dt
                self.fps = inst if self.fps == 0 else 0.9 * self.fps + 0.1 * inst
        self.last_frame_wall = now
        self.frames += 1
        self.resolution = (img.shape[1], img.shape[0])
        if self.state != "online":
            log.info("camera online: %s %dx%d", self.cfg.source, img.shape[1], img.shape[0])
        self.state = "online"
        self.error = ""
        self.buffer.put(img, t_media, label)

    def _run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                runner = {"usb": self._run_usb, "mjpeg": self._run_http, "http": self._run_http,
                          "video": self._run_video, "dir": self._run_dir}[self.kind]
                finished = runner()
                if finished:          # replay reached the end and loop is off
                    self.state = "ended"
                    return
                backoff = 1.0
            except Exception as e:  # noqa: BLE001 - any source error -> reconnect
                self.error = f"{type(e).__name__}: {e}"
                log.warning("camera error (%s): %s", self.cfg.source, self.error)
            if self._stop.is_set():
                break
            self.state = "offline"
            self.reconnects += 1
            self._stop.wait(backoff)
            backoff = min(backoff * 2, self.cfg.reconnect_max_s)

    def _run_usb(self) -> bool:
        src = self.cfg.source
        dev = int(src) if src.isdigit() else src
        cap = cv2.VideoCapture(dev, cv2.CAP_V4L2) if os.name == "posix" else cv2.VideoCapture(dev)
        try:
            if not cap.isOpened():
                raise IOError(f"cannot open USB camera {src}")
            if self.cfg.fourcc:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.cfg.fourcc))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg.height)
            cap.set(cv2.CAP_PROP_FPS, self.cfg.fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            fails = 0
            while not self._stop.is_set():
                ok, img = cap.read()
                if not ok:
                    fails += 1
                    if fails > 10:
                        raise IOError("USB camera stopped delivering frames (unplugged?)")
                    time.sleep(0.1)
                    continue
                fails = 0
                self._publish(img)
        finally:
            cap.release()
        return False

    def _run_http(self) -> bool:
        url = self.cfg.source
        with requests.get(url, stream=True, timeout=(5, 10)) as r:
            r.raise_for_status()
            ctype = r.headers.get("Content-Type", "")
            if "multipart" in ctype:
                self.kind = "mjpeg"
                self._read_mjpeg(r)
                return False
            self.kind = "http"
            img = _decode(r.content)
        if img is None:
            raise IOError(f"URL did not return an image or MJPEG stream (Content-Type {ctype!r})")
        self._publish(img)
        sess = requests.Session()
        while not self._stop.wait(self.cfg.snapshot_interval_s):
            r = sess.get(url, timeout=(5, 10))
            r.raise_for_status()
            img = _decode(r.content)
            if img is None:
                raise IOError("snapshot URL returned undecodable data")
            self._publish(img)
        return False

    def _read_mjpeg(self, r: requests.Response) -> None:
        # Robust to boundary formats: find JPEG SOI/EOI markers in the byte stream.
        buf = b""
        for chunk in r.iter_content(chunk_size=32768):
            if self._stop.is_set():
                return
            buf += chunk
            while True:
                a = buf.find(b"\xff\xd8")
                if a < 0:
                    buf = buf[-1:]
                    break
                b = buf.find(b"\xff\xd9", a + 2)
                if b < 0:
                    buf = buf[a:]
                    if len(buf) > 20_000_000:
                        raise IOError("MJPEG frame larger than 20 MB, stream corrupt")
                    break
                img = _decode(buf[a:b + 2])
                buf = buf[b + 2:]
                if img is not None:
                    self._publish(img)
        raise IOError("MJPEG stream closed by server")

    def _run_video(self) -> bool:
        cap = cv2.VideoCapture(self.cfg.source)
        if not cap.isOpened():
            raise IOError(f"cannot open video {self.cfg.source}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        try:
            while not self._stop.is_set():
                t0 = time.time()
                n = 0
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                while not self._stop.is_set():
                    ok, img = cap.read()
                    if not ok:
                        break
                    t_media = n / fps
                    self._publish(img, t_media, f"{os.path.basename(self.cfg.source)}#{n}")
                    n += 1
                    _pace(self._stop, t0, t_media, self.cfg.replay_speed)
                if not self.cfg.loop:
                    return True
        finally:
            cap.release()
        return False

    def _run_dir(self) -> bool:
        files, times = list_frames(self.cfg.source, self.cfg.replay_frame_interval_s)
        if not files:
            raise IOError(f"no images in {self.cfg.source}")
        while not self._stop.is_set():
            t0 = time.time()
            for f, t_media in zip(files, times):
                if self._stop.is_set():
                    return False
                img = cv2.imread(f)
                self._publish(img, t_media, os.path.basename(f))
                _pace(self._stop, t0, t_media, self.cfg.replay_speed)
            if not self.cfg.loop:
                return True
        return False


def _pace(stop: threading.Event, t0: float, t_media: float, speed: float) -> None:
    if speed and speed > 0:
        delay = t0 + t_media / speed - time.time()
        if delay > 0:
            stop.wait(delay)


def _decode(data: bytes):
    if not data:
        return None
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def source_kind(src: str) -> str:
    s = src.strip()
    if s.isdigit() or s.startswith("/dev/video"):
        return "usb"
    if s.startswith(("http://", "https://")):
        return "http"
    if os.path.isdir(s):
        return "dir"
    return "video"


def list_frames(directory: str, default_interval: float = 0.0):
    """Frames of a recorded session in order, with media timestamps (s).

    Uses frames.csv (file,t_s) written by our dataset/record tools when present,
    otherwise sorted file names spaced default_interval (or 1 s) apart.
    """
    meta = os.path.join(directory, "frames.csv")
    if os.path.exists(meta) and not default_interval:
        with open(meta) as f:
            rows = list(csv.DictReader(f))
        files = [os.path.join(directory, r["file"]) for r in rows]
        times = [float(r["t_s"]) for r in rows]
        keep = [i for i, p in enumerate(files) if os.path.exists(p)]
        return [files[i] for i in keep], [times[i] for i in keep]
    files = sorted(p for ext in ("jpg", "jpeg", "png")
                   for p in glob.glob(os.path.join(directory, f"*.{ext}")))
    step = default_interval or 1.0
    return files, [i * step for i in range(len(files))]
