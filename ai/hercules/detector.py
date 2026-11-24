"""Failure detector: the Obico (The Spaghetti Detective) pretrained YOLOv2 network.

Third-party component. The weights are published by the Obico project
(github.com/TheSpaghettiDetective/obico-server, AGPL-3.0) and are downloaded at
install time, verified by SHA-256 and never modified. The network has a single
class, "failure", trained on webcam images of spaghetti / filament mess.

Our code here: model loading with execution-provider selection and fallback,
a second backend (OpenCV DNN) for comparison, ROI crop/filter, ignore zones and
the frame score p (sum of box confidences inside the ROI, as Obico defines it).
Pre/post-processing reproduces Obico's ml_api/lib/onnx.py exactly (plain resize
to 416x416, RGB, /255; boxes are x1,y1,x2,y2 normalised) so scores match the
reference implementation.
"""
from __future__ import annotations

import dataclasses as dc
import hashlib
import logging
import os
import time
import urllib.request

import cv2
import numpy as np

from .config import DetectorCfg, PipelineCfg

log = logging.getLogger("hercules.detector")


@dc.dataclass
class Box:
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float
    in_roi: bool = True

    def as_list(self):
        return [round(self.x1, 1), round(self.y1, 1), round(self.x2, 1), round(self.y2, 1),
                round(self.conf, 4), self.in_roi]


@dc.dataclass
class Detection:
    boxes: list
    p: float            # sum of confidences of boxes inside the ROI
    max_conf: float
    latency_ms: float


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_model(cfg: DetectorCfg) -> str:
    path = cfg.model_path
    if not os.path.exists(path):
        if not cfg.model_url:
            raise FileNotFoundError(path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        log.info("downloading model %s -> %s", cfg.model_url, path)
        tmp = path + ".part"
        urllib.request.urlretrieve(cfg.model_url, tmp)
        os.replace(tmp, path)
    if cfg.model_sha256:
        digest = sha256_file(path)
        if digest != cfg.model_sha256:
            raise ValueError(f"model checksum mismatch for {path}: {digest}")
    return path


def nms(boxes: np.ndarray, scores: np.ndarray, thr: float) -> list[int]:
    x1, y1, x2, y2 = boxes.T
    areas = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        order = order[1:][iou <= thr]
    return keep


class Detector:
    def __init__(self, cfg: DetectorCfg):
        self.cfg = cfg
        self.fallback_used = False
        try:
            path = ensure_model(cfg)
        except FileNotFoundError:
            if not cfg.fallback_model_path:
                raise FileNotFoundError(
                    f"model {cfg.model_path} not found. For the INT8 model run tools/build_int8.sh "
                    "on a PC with 2 GB+ RAM and copy the file (docs/RASPBERRY_PI.md)") from None
            fb = DetectorCfg()                     # the official FP32 model: URL + SHA-256
            if cfg.fallback_model_path != fb.model_path:
                fb.model_url, fb.model_sha256 = "", ""
            fb.model_path = cfg.fallback_model_path
            log.warning("model %s not found, using fallback %s", cfg.model_path, fb.model_path)
            path = ensure_model(fb)
            self.fallback_used = True
        self.model_path = path
        t0 = time.time()
        self.backend = cfg.backend
        if self.backend == "opencv":
            self.net = cv2.dnn.readNetFromONNX(path)
            if cfg.threads:
                cv2.setNumThreads(cfg.threads)
            self.input_hw = (416, 416)
            self.providers = ["opencv-dnn-cpu"]
        else:
            import onnxruntime as ort
            so = ort.SessionOptions()
            if cfg.threads:
                so.intra_op_num_threads = cfg.threads
            so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.session = None
            for providers in self._provider_candidates(ort):
                try:
                    self.session = ort.InferenceSession(path, so, providers=providers)
                    break
                except Exception as e:  # noqa: BLE001 - try next provider set
                    log.warning("providers %s failed: %s", providers, e)
            if self.session is None:
                raise RuntimeError("could not create an ONNX Runtime session")
            self.providers = self.session.get_providers()
            inp = self.session.get_inputs()[0]
            self.input_name = inp.name
            self.input_hw = (int(inp.shape[2]), int(inp.shape[3]))
        self.load_s = time.time() - t0
        log.info("model loaded in %.2fs, backend=%s providers=%s", self.load_s, self.backend, self.providers)

    def _provider_candidates(self, ort):
        avail = ort.get_available_providers()
        p = self.cfg.providers.strip().lower()
        if p == "cpu":
            return [["CPUExecutionProvider"]]
        if p == "auto":
            pref = ["CUDAExecutionProvider", "OpenVINOExecutionProvider",
                    "CoreMLExecutionProvider", "DmlExecutionProvider"]
            accel = [x for x in pref if x in avail]
            return [[a, "CPUExecutionProvider"] for a in accel] + [["CPUExecutionProvider"]]
        wanted = [x.strip() for x in self.cfg.providers.split(",") if x.strip()]
        return [wanted, ["CPUExecutionProvider"]]

    def raw(self, img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Network output for a BGR image: boxes (N,4) normalised x1y1x2y2, conf (N,)."""
        h, w = self.input_hw
        x = cv2.resize(img, (w, h), interpolation=cv2.INTER_LINEAR)
        x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        if self.backend == "opencv":
            self.net.setInput(x)
            names = self.net.getUnconnectedOutLayersNames()
            outs = self.net.forward(names)
            boxes, confs = (outs[0], outs[1]) if outs[0].shape[-1] == 4 else (outs[1], outs[0])
        else:
            boxes, confs = self.session.run(None, {self.input_name: x})
        return boxes.reshape(-1, 4), confs.reshape(confs.shape[1], -1).max(axis=1)

    def detect(self, img: np.ndarray, pcfg: PipelineCfg, box_threshold: float | None = None) -> Detection:
        thr = self.cfg.box_threshold if box_threshold is None else box_threshold
        H, W = img.shape[:2]
        ox, oy = 0, 0
        view = img
        if pcfg.roi_mode == "crop":
            x0, y0, x1, y1 = pcfg.roi
            ox, oy = int(x0 * W), int(y0 * H)
            view = img[oy:int(y1 * H), ox:int(x1 * W)]
        vh, vw = view.shape[:2]
        t0 = time.perf_counter()
        b, c = self.raw(view)
        latency = (time.perf_counter() - t0) * 1000
        boxes = postprocess(b, c, vw, vh, thr, self.cfg.nms_threshold, ox, oy)
        return score_boxes(boxes, W, H, pcfg, latency)


def postprocess(b, c, vw, vh, thr, nms_thr, ox=0, oy=0) -> list[Box]:
    sel = c > thr
    b, c = b[sel], c[sel]
    if not len(c):
        return []
    keep = nms(b, c, nms_thr)
    out = []
    for i in keep:
        x1, y1, x2, y2 = b[i]
        out.append(Box(float(np.clip(x1, 0, 1) * vw + ox), float(np.clip(y1, 0, 1) * vh + oy),
                       float(np.clip(x2, 0, 1) * vw + ox), float(np.clip(y2, 0, 1) * vh + oy),
                       float(c[i])))
    return out


def score_boxes(boxes: list[Box], W: int, H: int, pcfg: PipelineCfg, latency_ms: float = 0.0) -> Detection:
    """Mark boxes outside the ROI / inside ignore zones and compute p."""
    rx0, ry0, rx1, ry1 = pcfg.roi
    p, mx = 0.0, 0.0
    for bx in boxes:
        cx, cy = (bx.x1 + bx.x2) / 2 / W, (bx.y1 + bx.y2) / 2 / H
        inside = rx0 <= cx <= rx1 and ry0 <= cy <= ry1
        for z in pcfg.ignore_zones:
            if z[0] <= cx <= z[2] and z[1] <= cy <= z[3]:
                inside = False
        bx.in_roi = inside
        if inside:
            p += bx.conf
            mx = max(mx, bx.conf)
    return Detection(boxes, p, mx, latency_ms)
