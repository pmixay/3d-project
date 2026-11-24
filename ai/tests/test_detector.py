import glob
import os

import numpy as np
import pytest

from conftest import MODEL, ROOT, textured
from hercules.config import Config, PipelineCfg
from hercules.detector import Box, Detector, nms, postprocess, score_boxes

needs_model = pytest.mark.skipif(not os.path.exists(MODEL), reason="model not downloaded")


def test_nms_keeps_best_of_overlapping():
    b = np.array([[0, 0, 10, 10], [1, 1, 10, 10], [20, 20, 30, 30]], float)
    s = np.array([0.5, 0.9, 0.3])
    assert sorted(nms(b, s, 0.45)) == [1, 2]


def test_postprocess_scales_to_pixels():
    b = np.array([[0.1, 0.2, 0.5, 0.6], [0.0, 0.0, 0.1, 0.1]], np.float32)
    c = np.array([0.7, 0.05], np.float32)
    out = postprocess(b, c, 1000, 500, 0.08, 0.45)
    assert len(out) == 1
    assert (round(out[0].x1), round(out[0].y1), round(out[0].x2), round(out[0].y2)) == (100, 100, 500, 300)


def test_roi_and_ignore_zones():
    pc = PipelineCfg(roi=[0.0, 0.0, 0.5, 1.0], ignore_zones=[[0.0, 0.0, 0.2, 0.2]])
    boxes = [Box(10, 10, 30, 30, 0.5),      # centre in ignore zone
             Box(200, 200, 260, 260, 0.4),  # inside ROI
             Box(800, 200, 900, 260, 0.9)]  # outside ROI
    d = score_boxes(boxes, 1000, 500, pc)
    assert [b.in_roi for b in boxes] == [False, True, False]
    assert d.p == pytest.approx(0.4) and d.max_conf == pytest.approx(0.4)


@needs_model
def test_model_runs_and_matches_obico_reference():
    """Our pre/post-processing must give the same boxes as Obico ml_api/lib/onnx.py."""
    import cv2
    cfg = Config()
    det = Detector(cfg.detector)
    frames = sorted(glob.glob(os.path.join(ROOT, "data/zenodo_fffqc/test_extrusion_error_print_camera1/frame_0018*.jpg")))
    img = cv2.imread(frames[0]) if frames else textured(0, 416, 416)
    # --- reference, transcribed from obico-server ml_api/lib/onnx.py (AGPL-3.0) ---
    x = cv2.resize(img, (416, 416), interpolation=cv2.INTER_LINEAR)
    x = np.transpose(cv2.cvtColor(x, cv2.COLOR_BGR2RGB), (2, 0, 1)).astype(np.float32)[None] / 255.0
    rb, rc = det.session.run(None, {det.session.get_inputs()[0].name: x})
    rc = rc[0, :, 0]
    ref = sorted(float(v) for v in rc[rc > 0.08])
    ours = det.detect(img, cfg.pipeline)
    # our list is after NMS, so it is a subset of the reference candidates
    for b in ours.boxes:
        assert any(abs(b.conf - r) < 1e-5 for r in ref)
    if ref:
        assert ours.max_conf == pytest.approx(max(ref), abs=1e-5)
    assert ours.latency_ms > 0


@needs_model
def test_opencv_backend_agrees_with_onnxruntime():
    pytest.importorskip("cv2")
    import cv2
    frames = sorted(glob.glob(os.path.join(ROOT, "data/zenodo_fffqc/test_extrusion_error_print_camera1/frame_0019*.jpg")))
    if not frames:
        pytest.skip("evaluation data not downloaded")
    img = cv2.imread(frames[0])
    cfg = Config()
    a = Detector(cfg.detector).detect(img, cfg.pipeline)
    cfg.detector.backend = "opencv"
    try:
        b = Detector(cfg.detector).detect(img, cfg.pipeline)
    except cv2.error as e:
        pytest.skip(f"OpenCV DNN cannot load this model: {e}")
    assert abs(a.p - b.p) < 0.02


@needs_model
def test_crop_mode_maps_boxes_back_to_full_frame():
    import cv2
    frames = sorted(glob.glob(os.path.join(ROOT, "data/zenodo_fffqc/test_extrusion_error_print_camera2/frame_0017*.jpg")))
    if not frames:
        pytest.skip("evaluation data not downloaded")
    img = cv2.imread(frames[0])
    H, W = img.shape[:2]
    cfg = Config()
    cfg.pipeline.roi, cfg.pipeline.roi_mode = [0.0, 0.3, 1.0, 1.0], "crop"
    det = Detector(cfg.detector).detect(img, cfg.pipeline)
    assert det.boxes and det.p > 0.38                # spaghetti in this frame
    for b in det.boxes:
        assert 0 <= b.x1 < b.x2 <= W and 0.3 * H - 1 <= b.y1 < b.y2 <= H
