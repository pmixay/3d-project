#!/usr/bin/env python3
"""Build INT8 variants of the detector for weak CPUs (optional optimisation).

  dynamic : weights INT8, activations quantised on the fly. 4x smaller file
            and RAM, no calibration data needed.
  qdq     : static QDQ quantisation, per-channel weights, activation ranges
            calibrated on frames of *normal* printing (--calib). Usually the
            fastest INT8 path on ARM and recent x86.

The FP32 model stays the reference. Accept a variant only after
tools/evaluate.py shows the same decisions (docs/EVALUATION.md).
Requires: pip install onnx sympy
"""
import argparse
import glob
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def prep(path):
    x = cv2.resize(cv2.imread(path), (416, 416), interpolation=cv2.INTER_LINEAR)
    return cv2.cvtColor(x, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)[None].astype(np.float32) / 255.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="models/obico-failure-5a6b1be1fa.onnx")
    ap.add_argument("--mode", choices=["dynamic", "qdq"], default="qdq")
    ap.add_argument("--calib", nargs="+", default=[], help="directories of normal-print frames")
    ap.add_argument("--calib-frames", type=int, default=64)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    from onnxruntime.quantization import (CalibrationDataReader, QuantFormat, QuantType,
                                          quantize_dynamic, quantize_static)
    out = a.out or f"models/obico-failure-int8-{a.mode}.onnx"
    if a.mode == "dynamic":
        quantize_dynamic(a.src, out, weight_type=QuantType.QUInt8)
    else:
        from onnxruntime.quantization.shape_inference import quant_pre_process
        files = sorted(f for d in a.calib for f in glob.glob(os.path.join(d, "*.jpg")))
        if not files:
            sys.exit("--calib directories with JPEG frames are required for qdq")
        step = max(1, len(files) // a.calib_frames)
        files = files[::step][:a.calib_frames]

        class Reader(CalibrationDataReader):
            def __init__(self):
                self.it = iter(files)

            def get_next(self):
                f = next(self.it, None)
                return None if f is None else {"input": prep(f)}
        pre = out + ".pre.onnx"
        quant_pre_process(a.src, pre)
        import onnx
        opset = max(o.version for o in onnx.load(a.src, load_external_data=False).opset_import
                    if o.domain in ("", "ai.onnx"))
        per_channel = opset >= 13     # DequantizeLinear "axis" needs opset 13
        print(f"model opset {opset}, per-channel weights: {per_channel}")
        quantize_static(pre, out, Reader(), quant_format=QuantFormat.QDQ, per_channel=per_channel,
                        activation_type=QuantType.QUInt8, weight_type=QuantType.QInt8)
        os.remove(pre)
        print(f"calibrated on {len(files)} frames")
    print(out, os.path.getsize(out) // 2**20, "MB")


if __name__ == "__main__":
    main()
