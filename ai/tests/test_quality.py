import cv2
import numpy as np

from conftest import textured
from hercules.config import PipelineCfg
from hercules.quality import FrameValidator


def test_normal_frames_are_usable():
    v = FrameValidator(PipelineCfg())
    for i in range(6):
        q = v.check(textured(i))
        assert q.usable and not q.blurred and not q.duplicate


def test_dark_and_overexposed():
    v = FrameValidator(PipelineCfg())
    assert v.check(np.full((270, 480, 3), 5, np.uint8)).too_dark
    assert v.check(np.full((270, 480, 3), 252, np.uint8)).overexposed


def test_obstructed_lens():
    v = FrameValidator(PipelineCfg())
    img = textured(1)
    img[:, :] = (60, 60, 60)          # e.g. covered by a hand / tape: flat grey
    img[:20] = textured(2)[:20]
    q = v.check(img)
    assert q.obstructed and not q.usable


def test_identical_and_duplicate():
    v = FrameValidator(PipelineCfg())
    a = textured(3)
    v.check(a)
    q = v.check(a.copy())
    assert q.identical and q.duplicate
    noisy = np.clip(a.astype(int) + np.random.default_rng(0).integers(-1, 2, a.shape), 0, 255).astype(np.uint8)
    q = v.check(noisy)
    assert q.duplicate and not q.identical


def test_motion_blur_is_relative_to_history():
    v = FrameValidator(PipelineCfg())
    for i in range(8):
        v.check(textured(i))
    k = np.zeros((1, 25), np.float32)
    k[0, :] = 1 / 25
    blurred = cv2.filter2D(textured(20), -1, k)
    q = v.check(blurred)
    assert q.blurred and q.usable
