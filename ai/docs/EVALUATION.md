# Evaluation — measured results only

All numbers here come from `tools/run_all_evaluations.sh`. The raw JSON files are in [`results/`](results/), and the tables are generated from them by `tools/results_tables.py`, not typed by hand. Measurements we could **not** make are listed as such in § 8.

## 1. Data and protocol

- **Recordings.** Zenodo record [18628777](https://zenodo.org/records/18628777) (CC-BY-4.0), test split, full resolution resized to 960×540. Nine complete prints from fixed side cameras, one print per camera folder, about 50 minutes and one frame every ~1.4 s each, **20 141 frames, 7.6 h**: 3 normal prints, 3 prints that turn into spaghetti (the dataset's "extrusion error"), and 3 prints with a layer shift.
- **Ground truth.** The dataset labels only whole prints. We marked the frame where the defect first becomes visible (`onset`: first loose strand or step) and where it becomes unmistakable (`obvious`), using contact sheets: [`datasets/labels/sessions.json`](../datasets/labels/sessions.json).
- **Replay.** Each print is replayed through the production `Analyzer`: frame validation, the decision engine, and the same thresholds as the live service. One frame is analysed every *N* seconds of recording time. Network outputs are cached once per frame (`tools/score_sessions.py`, results identical to a live run; see the script header).
- **Normal printing time** = the normal prints plus every failure print before its onset = **5.38 h**.
- **False alarm** = a failure incident opened during normal printing time. **Detection** = an incident opens or escalates at or after the onset. **Latency** is measured from the *first visible strand*, the strict choice, and also from the *obvious* point.
- **No tuning on this data.** All decision parameters were fixed beforehand: Obico's published thresholds, our window lengths. § 4 shows how the results move when they change, for transparency, not to pick values.

## 2. Main result (default settings, one analysis every 3 s)

| | Result |
| :--- | :--- |
| Spaghetti prints detected | **3 / 3** |
| False alarms in 5.38 h of normal printing | **0** (0.0 per printing hour) |
| Session precision / recall / F1 | 1.0 / 1.0 / 1.0 (3 positive and 6 negative sessions, a very small sample) |
| Warning latency after the first visible strand | 64 s, 114 s, 179 s |
| Warning latency after the defect becomes obvious | −6 s (before), 21 s, 87 s |
| Critical level (= pause under `auto`) after the first strand | 96 s, 147 s, 216 s |
| Layer-shift prints alerted | 0 / 3: **not detected** |

### Per session (3 s interval)

| Session | Kind | Length, min | Onset, min | Frames analysed | False alarms | Detected | Latency, s | Critical, s | Max score before onset | Max score after onset |
| :--- | :--- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: |
| no_error_camera1 | normal | 48.9 | — | 979 | 0 | no | — | — | 0.23 | — |
| no_error_camera2 | normal | 48.8 | — | 977 | 0 | no | — | — | 0.00 | — |
| no_error_camera3 | normal | 49.0 | — | 981 | 0 | no | — | — | 0.00 | — |
| extrusion_error_camera1 | spaghetti | 54.9 | 29.61 | 1098 | 0 | yes | 63.8 | 95.8 | 0.03 | 4.50 |
| extrusion_error_camera2 | spaghetti | 55.0 | 28.56 | 1101 | 0 | yes | 114.3 | 147.1 | 0.00 | 4.99 |
| extrusion_error_camera3 | spaghetti | 55.0 | 28.92 | 1100 | 0 | yes | 179.2 | 216.2 | 0.00 | 2.74 |
| layershift_error_camera1 | layer_shift | 51.1 | 29.67 | 1023 | 0 | no | — | — | 0.08 | 0.30 |
| layershift_error_camera2 | layer_shift | 51.1 | 29.57 | 1023 | 0 | no | — | — | 0.00 | 0.00 |
| layershift_error_camera3 | layer_shift | 51.0 | 29.66 | 1020 | 0 | no | — | — | 0.00 | 0.00 |

The decision score of the closest normal print (camera 1, a busy background) peaked at 0.23, against a warning level of 0.38. Spaghetti drove it to 2.7–5.0. The margin on this data is large, but it comes from one printer and one filament (§ 8).

## 3. Is low-frequency inference enough? — inference interval sweep

The same prints analysed every 1.4 s (every recorded frame) up to every 24 s:

#### Our engine (time-normalised)

| Interval, s | Detected | Latency from first strand, s | from 'obvious', s | Critical (pause) latency, s | False alarms | FA / print hour |
| ---: | :---: | :--- | :--- | :--- | ---: | ---: |
| 1.4 | 3/3 | 68, 114, 184 | -1, 21, 91 | 97, 143, 219 | 0 | 0.0 |
| 3.0 | 3/3 | 64, 114, 179 | -6, 21, 87 | 96, 147, 216 | 0 | 0.0 |
| 6.0 | 3/3 | 60, 111, 174 | -10, 19, 81 | 96, 147, 209 | 0 | 0.0 |
| 12.0 | 3/3 | 60, 111, 174 | -10, 19, 81 | 96, 147, 209 | 0 | 0.0 |
| 24.0 | 3/3 | 72, 134, 209 | 3, 41, 117 | 96, 158, 209 | 0 | 0.0 |

#### Obico's original frame-count scheme (baseline, same detections)

| Interval, s | Detected | Latency from first strand, s | from 'obvious', s | Critical (pause) latency, s | False alarms | FA / print hour |
| ---: | :---: | :--- | :--- | :--- | ---: | ---: |
| 1.4 | 3/3 | 18, 89, 95 | -51, -4, 3 | 56, 97, 168 | 0 | 0.0 |
| 3.0 | 3/3 | 42, 93, 101 | -28, 0, 8 | 60, 111, 174 | 0 | 0.0 |
| 6.0 | 3/3 | 54, 99, 168 | -15, 6, 75 | 85, 128, 192 | 0 | 0.0 |
| 12.0 | 3/3 | 72, 123, 186 | 3, 30, 94 | 96, 158, 233 | 0 | 0.0 |
| 24.0 | 3/3 | 96, 158, 209 | 26, 66, 117 | 144, 207, 282 | 0 | 0.0 |

**Findings.**
1. **Yes, low-frequency inference is enough for these failures.** With our engine, analysing every 12 s detects exactly as fast as analysing every recorded frame (1.4 s), at about one ninth of the compute (§ 6). Only at 24 s does the latency grow, by 12–35 s. Spaghetti develops over minutes, so per-frame analysis of the moving head adds nothing.
2. **Time normalisation does what it was designed to do.** Our latency stays roughly constant across a 17× change in frame rate. Obico's frame-count smoothing gets 5× slower on the first print (18 s → 96 s) as the interval grows, because 12 frames is a different length of time at each rate.
3. **The cost: at short intervals our default is slower than Obico's.** At 3 s Obico warns 21–78 s earlier, because its 12-frame window lasts about 34 s at that rate, against our 60 s time constant. With τ = 30 s (§ 4) we come within 6–67 s of it, still with no false alarms here. We keep 60 s as the default because this dataset contains only one printer and cannot show whether the shorter window stays quiet on noisier scenes. That decision should be revisited with recordings from our own printer.
4. A single analysis takes 60–210 ms (§ 6). Even the 1.4 s interval leaves the CPU idle most of the time.

## 4. What the temporal engine buys — comparison and sensitivity

| Engine / setting | Interval, s | Detected | Latency, s | Critical, s | False alarms (FA/h) | Non-target alerts |
| :--- | ---: | :---: | :--- | :--- | :--- | :---: |
| **Hercules (ours), τ=60 s, gate 3** | 3.0 | 3/3 | 64, 114, 179 | 96, 147, 216 | **0 (0.0)** | 0/3 |
| Hercules (ours), τ=60 s, gate 3 | 12.0 | 3/3 | 60, 111, 174 | 96, 147, 209 | 0 (0.0) | 0/3 |
| Hercules (ours), τ=60 s, gate 3 | 24.0 | 3/3 | 72, 134, 209 | 96, 158, 209 | 0 (0.0) | 0/3 |
| Obico original (frame-count EWM) | 3.0 | 3/3 | 42, 93, 101 | 60, 111, 174 | 0 (0.0) | 0/3 |
| Obico original (frame-count EWM) | 12.0 | 3/3 | 72, 123, 186 | 96, 158, 233 | 0 (0.0) | 0/3 |
| Obico original (frame-count EWM) | 24.0 | 3/3 | 96, 158, 209 | 144, 207, 282 | 0 (0.0) | 0/3 |
| Naive: alert on any frame p ≥ 0.38 | 3.0 | 3/3 | 10, 74, 78 | 10, 74, 92 | **5 (0.93)** | 1/3 |
| Naive: alert on any frame p ≥ 0.38 | 12.0 | 3/3 | 24, 74, 78 | 49, 74, 162 | 6 (1.115) | 1/3 |
| Ours, τ=30 s | 3.0 | 3/3 | 54, 99, 168 | 82, 123, 192 | 0 (0.0) | 0/3 |
| Ours, τ=120 s | 3.0 | 3/3 | 90, 141, 206 | 129, 180, 255 | 0 (0.0) | 0/3 |
| Ours, evidence gate off | 3.0 | 3/3 | 64, 114, 179 | 96, 147, 216 | 0 (0.0) | 0/3 |
| Ours, evidence gate off | 24.0 | 3/3 | 49, 111, 162 | 96, 158, 209 | 0 (0.0) | 0/3 |
| Ours, warning 0.25 instead of 0.38 | 3.0 | 3/3 | 49, 101, 165 | 72, 123, 189 | 1 (0.186) | 1/3 |

- **Without temporal analysis** (naive), the same network raises about one false alarm per printing hour. Four of them came from one normal print with a busy background and one from the normal phase of a layer-shift print; it also alerted once after a layer shift, on unrelated texture. That rate would make automatic pausing unusable. Temporal confirmation removes all of them, at the cost of 40–100 s more latency.
- **The evidence gate** made no difference on this data. Here the scores either stay low or rise for minutes, so the gate never decided an outcome. Its purpose is to stop a single isolated spike from alerting at long intervals; a unit test shows this (`tests/test_temporal.py::test_single_spike_at_long_interval_is_gated`), but these recordings contain no such spike. We keep it because it costs nothing on this data.
- **Lowering the warning threshold to 0.25** gains about 15 s and adds a false alarm, so the published value 0.38 is kept.

## 5. Model-level (per frame) diagnostics

These are per-frame numbers for the network alone, given for completeness. Adjacent frames are nearly identical, so they overstate the effective sample size; § 2 is the result that counts.

Frames: 17 326 (3 306 after a spaghetti onset; frames after a layer shift are excluded).

| Frame score threshold | Precision | Recall | F1 | False-positive rate |
| ---: | ---: | ---: | ---: | ---: |
| p ≥ 0.2 | 0.8 | 0.953 | 0.87 | 0.0561 |
| p ≥ 0.38 | 0.968 | 0.946 | 0.957 | 0.0073 |
| p ≥ 0.5 | 0.997 | 0.943 | 0.97 | 0.0006 |
| p ≥ 0.78 | 1.0 | 0.926 | 0.961 | 0.0 |

At the warning level of 0.38, 0.73 % of normal frames score as failure. This is what the naive baseline turns into false alarms and what the temporal engine absorbs.

## 5b. Robustness to camera problems

Synthetic degradations applied to the **real** recorded frames, followed by a full new network run (`tools/evaluate.py --perturb`). The window covers 10 min before to 15 min after each onset, and the first 25 min of the normal prints (2.25 h of normal printing in total). The interval is 6 s.

| Condition (applied to every frame) | Detected | Latency, s | False alarms | Frames not sent to the network | Max score after onset (per print) |
| :--- | :---: | :--- | ---: | ---: | :--- |
| none (reference for this window) | 3/3 | 61, 108, 193 | 0 | 0 | 3.32, 2.38, 1.63 |
| **dark**: gamma 1.8, gain 0.45 (lights off) | 2/3 | 97, 171 | 0 | 1833 of 2250 | 2.65, 0.00, 2.03 |
| **noise**: Gaussian σ = 18 (cheap sensor, dim light) | 2/3 | 108, 200 | **3** | 0 | 3.72, 2.25, 1.55 |
| **motion blur**: 21 px horizontal | 3/3 | 146, 253, 331 | 0 | 0 | 1.40, 0.95, 0.48 |
| **partial occlusion**: left third covered | 3/3 | 56, 294, 193 | 0 | 0 | 3.31, 0.61, 1.66 |

- **Darkness** is handled by refusing to guess. Darkened frames below the brightness floor are not analysed (1833 of 2250). In the live service this raises a *"Image quality poor"* incident after 20 s; the offline replay does not simulate camera incidents. The one "missed" print is a print whose every frame was refused. Where frames stayed just above the floor, spaghetti was still detected. No false alarms.
- **Sensor noise is the weak point.** The network starts to see "failure" in grain on the busy camera-1 view: 3 false alarms, and one failure counted as missed because a false-alarm incident was already open and critical before the onset. Denoising before inference was tested and made scores on normal prints *higher* (mean p on 20 normal frames: clean 0.19, noisy 0.45, noisy + Gaussian/median 5×5 denoise 0.79/0.57; a one-off check, not a scripted result), so it was rejected. The response instead: the validator measures noise (Immerkær σ; clean frames ≤ 2.9, noisy ≥ 5.8 on these recordings: 0/340 clean frames flagged, 87/87 noisy flagged, `tools/noise_check.py`). A noisy camera raises an image-quality incident that tells the operator to fix the lighting. **Practical rule: light the bed (the planned 24 V LED strip) and do not rely on night vision.**
- **Motion blur on every frame** lowers the scores 2–4×, but all failures are still detected, 1–2.5 minutes later than normal. In real use only some frames are blurred, and those are skipped relative to the camera's own sharpness history (§ 3: 0.0–0.2 % skipped on the real recordings).
- **Covering a third of the view** delays detection only when the spaghetti grows in the covered part (camera 2: 294 s). Choose the camera position so the bed and nozzle area is fully visible; the ROI editor helps check this.


## 5c. Cheap / low-quality cameras (CSI modules with M12 lenses)

The team's camera is a cheap CSI module. Its real images could not be tested yet (no Pi available), so its weaknesses were **simulated on the real recordings**: low resolution with heavy JPEG compression, sensor noise, and both together. Each condition was run without and with a region of interest drawn around the bed per camera view ([`datasets/labels/rois.json`](../datasets/labels/rois.json)). The setup matches § 5b: 10 min before to 15 min after each onset, 2.25 h of normal printing, a 6 s interval, and a fresh network run for every frame.

| Camera condition | ROI | Detected | Latency, s | False alarms (FA/h) |
| :--- | :--- | :---: | :--- | :--- |
| clean camera | none (full frame) | 3/3 | 61, 108, 193 | 0 (0.0) |
| clean camera | bed ROI, **crop** | 3/3 | 56, 97, 98 | 0 (0.0) |
| strong sensor noise (σ 18) | none (full frame) | 2/3 | 108, 200 | 3 (1.334) |
| strong sensor noise (σ 18) | bed ROI, filter | 3/3 | 110, 108, 200 | 0 (0.0) |
| strong noise + average_frames 4 | none (full frame) | 3/3 | 61, 103, 188 | 2 (0.889) |
| strong noise + average_frames 4 | bed ROI, filter | 3/3 | 92, 103, 188 | 0 (0.0) |
| 320×180 + heavy JPEG | none (full frame) | 1/3 | 43 | 0 (0.0) |
| 320×180 + heavy JPEG | bed ROI, **crop** | 2/3 | 265, 309 | 0 (0.0) |
| cheap module: 640×360, σ 14, JPEG q40 | none (full frame) | 3/3 | 97, 114, 218 | 2 (0.889) |
| cheap module: 640×360, σ 14, JPEG q40 | bed ROI, filter | 3/3 | 128, 114, 218 | 0 (0.0) |
| cheap module + average_frames 4 | none (full frame) | 3/3 | 92, 127, 200 | 2 (0.889) |
| cheap module + average_frames 4 | bed ROI, **crop** | 3/3 | 97, 151, 200 | 0 (0.0) |

**What this shows**
1. **The bed ROI matters most.** Every false alarm in every noisy or cheap condition came from the camera-1 view, where the network fires on the cluttered lab background (another printer, cables) once the image is grainy: all 58 boxes in a one-off 29-frame check sat in that background. With a rectangle around the bed, every condition here had **0 false alarms**.
2. **Resolution has a floor.** At 320×180 the distant views (cameras 2 and 3) fall from scores of 1.6–2.4 to 0.13–0.22, so only 1/3 failures is detected (2/3 with crop). At 640×360 all three are detected. **Run the camera at 1280×720 or at least 640×480**, and mount it so the bed fills most of the picture.
3. **Crop mode turns spare camera pixels into detection speed.** With a clean 960 px image, cropping to the bed nearly halves the latency on the distant view (193 → 98 s), because the print covers more of the network's 416×416 input. It cannot add detail a low-resolution camera never captured. Crop is therefore the default `roi_mode`; with the default full-frame ROI it is identical to the old behaviour.
4. **Averaging 4 frames** (`camera.average_frames = 4`) recovers detection under strong noise (2/3 → 3/3), but does not remove background false alarms by itself. Use it when the image is visibly grainy, together with the ROI.

**Limits of this test.** The degradations are synthetic and applied to another printer's footage. Averaging was simulated as 4 independent noise draws on one frame, i.e. a static scene. In a live stream the print head moves between those frames; the effect of that ghosting on scores is not measured. The camera-1 ROI was drawn after seeing where the noise boxes were. Lens distortion (wide M12 lenses), colour casts without an IR-cut filter and auto-exposure flicker were not simulated. **The real check is a recorded normal print from our own module** (RASPBERRY_PI.md).

**Setup rule for the CSI module:** light the bed, run the camera at 1280×720, draw the ROI around the bed in the dashboard (crop mode is the default), and enable `average_frames = 4` only if the picture is grainy.

## 6. Performance

Host: cloud VM, Intel(R) Xeon(R) Processor @ 2.10GHz, 4 logical cores, 16087 MB RAM, x86_64, ONNX Runtime 1.29.0, OpenCV 5.1.0

| Model | Backend | Threads | Median, ms | p95, ms | Load, s | Process RAM, MB |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| obico-failure-5a6b1be1fa.onnx | onnxruntime | 1 | 205.5 | 238.6 | 0.73 | 434 |
| obico-failure-5a6b1be1fa.onnx | onnxruntime | 2 | 111.2 | 147.8 | 0.8 | 418 |
| obico-failure-5a6b1be1fa.onnx | onnxruntime | 4 | 59.4 | 73.3 | 0.78 | 419 |
| obico-failure-int8-qdq.onnx | onnxruntime | 1 | 87.5 | 112.1 | 0.2 | 269 |
| obico-failure-int8-qdq.onnx | onnxruntime | 2 | 49.6 | 52.5 | 0.23 | 269 |
| obico-failure-int8-qdq.onnx | onnxruntime | 4 | 32.6 | 41.9 | 0.24 | 268 |
| obico-failure-int8-dynamic.onnx | onnxruntime | 1 | 247.8 | 253.7 | 0.11 | 275 |
| obico-failure-int8-dynamic.onnx | onnxruntime | 2 | 143.3 | 171.4 | 0.15 | 275 |
| obico-failure-int8-dynamic.onnx | onnxruntime | 4 | 93.5 | 120.1 | 0.16 | 275 |
| obico-failure-5a6b1be1fa.onnx | opencv | 4 | 119.4 | 151.4 | 0.41 | 343 |

| Camera frame | Full analysis step, ms | of which inference, ms | Validation + resize + decision, ms |
| :--- | ---: | ---: | ---: |
| 640x360 | 72.7 | 69.2 | 3.5 |
| 1280x720 | 65.5 | 62.2 | 3.3 |
| 1920x1080 | 71.4 | 67.3 | 4.1 |

| Interval, s | Analyses | Process CPU, % of one core | Process CPU, % of machine | System CPU, % | Peak RAM, MB |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1.0 | 60 | 42.1 | 10.5 | 10.8 | 447 |
| 3.0 | 20 | 13.3 | 3.3 | 3.7 | 447 |
| 10.0 | 6 | 4.4 | 1.1 | 1.3 | 447 |

**Reading the tables.**
- One analysis costs **60 ms (4 threads) to 206 ms (1 thread)** with the FP32 model in ONNX Runtime on this CPU. OpenCV DNN is 2× slower than ONNX Runtime on the same model, so ONNX Runtime is the default.
- The camera resolution barely matters: frame validation, resizing and the decision engine take 3–4 ms whether the frame is 640×360 or 1920×1080. The network always sees 416×416. Capture at 1280×720: it is good for the live view and the evidence images, and costs nothing in analysis time.
- At the default 3 s interval the monitor uses **13 % of one core** (3.3 % of this 4-core machine) and about **450 MB RAM**. The process size is dominated by the 192 MB FP32 weights.
- The dynamic INT8 model is *slower* on this x86 CPU (ConvInteger kernels) and is not recommended. See § 7 for the static INT8 model.

### Hardware requirements

Derived from the measurements above. Requirements for hosts we could not measure are **estimates**, marked as such.

| Host | Status | Recommendation |
| :--- | :--- | :--- |
| **Raspberry Pi 4 / Pi 5, 2 GB+ RAM, 64-bit Raspberry Pi OS, CSI camera** (the target setup) | **Not measured yet.** No Pi was available. A Cortex-A72/A76 core is slower than the measured Xeon core, so expect several times the latencies above. | Planned inference host. Use the `config/hercules.rpi.toml` preset: 3 threads, `interval_s = 6` (raise to 12 without latency loss per § 3). Measure with `tools/benchmark.py` as described in [RASPBERRY_PI.md § 5](RASPBERRY_PI.md#5-measure-the-pi-this-has-not-been-done-yet). |
| Raspberry Pi 3B/3B+ (1 GB) | **Not measured.** | Only with the INT8 model (268 MB vs 419 MB measured on x86) and `interval_s = 12`. |
| Any x86-64 PC from roughly the last 10 years, ≥ 2 cores, ≥ 2 GB RAM | Measured class: a 4-vCPU Xeon VM gives 60–206 ms per analysis | Works with default settings, e.g. a laptop with a USB camera. |
| Old dual-core laptop/PC (e.g. Core 2 / early i3) | Not measured. **Estimate**: 0.5–1.5 s per analysis | Usable: `threads = 2`, `interval_s = 6–12` (§ 3 shows no latency loss up to 12 s). |
| BTT Pi v1.2 (Allwinner H616, 4× Cortex-A53 1.5 GHz, 1 GB RAM), also the Klipper host | **Not measured** (no board access) | Not recommended. 450 MB RSS on a 1 GB board shared with Klipper is risky. If tried at all: INT8 model, `threads = 1`, `interval_s ≥ 12`, and run `tools/benchmark.py` first. Keep Klipper's `Timer too close` log under observation. |

## 7. INT8 model variant

Static INT8 quantisation (`tools/quantize_model.py --mode qdq`, per-tensor because the model is opset 11), re-run on all 20 141 frames and evaluated exactly like FP32:

| Model | Interval, s | Detected | Latency, s | Critical, s | False alarms | Frame P / R at p ≥ 0.38 | Inference (1 / 4 threads) | Process RAM |
| :--- | ---: | :---: | :--- | :--- | ---: | :--- | :--- | ---: |
| FP32 (default) | 3 | 3/3 | 64, 114, 179 | 96, 147, 216 | 0 | 0.968 / 0.946 | 206 / 59 ms | 419 MB |
| INT8 QDQ | 3 | 3/3 | 99, 129, 198 | 135, 171, 255 | 0 | 1.000 / 0.937 | 88 / 33 ms | 268 MB |
| INT8 QDQ | 12 | 3/3 | 96, 123, 198 | 144, 171, 257 | 0 | — | — | — |

INT8 compresses the scores: fewer false positives per frame, but warnings come 15–35 s later. It is **2.3× faster on one thread and uses 150 MB less RAM**, which makes it the candidate for weak hosts. It is not the default, because FP32 is faster to warn and has more margin.

*Caveat:* the activation ranges were calibrated on 64 frames of one of the normal test prints (`no_error_camera1`). Calibration uses no labels and only sets value ranges, but strictly that print is no longer unseen for the INT8 variant. A re-calibration on our own printer's footage is planned anyway.

## 8. What we could not measure, and limitations

- **Our own printer.** No recording of the Hefest/Hercules printer exists yet (the camera has not been bought; § RESEARCH 4). Every detection number above comes from one other printer, a Prusa MK3-type with red PLA, a simple block, three side cameras and lab lighting. Different filament colours (especially black or transparent), a top-down view, or a cluttered enclosure can change the false-alarm rate. **First action once the camera is installed:** record 5–10 normal prints with `python -m hercules record` and re-run § 2 on them. Automatic pausing is the default; if false alarms appear on our printer, use `pause_policy = "confirm"` until they are resolved.
- **Sample size.** 3 failing and 6 non-failing sessions. 0 false alarms in 5.4 h does **not** prove a rate of 0. The 95 % upper bound for a Poisson count of 0 over 5.38 h is about **0.56 false alarms per printing hour**. Recall 3/3 has a 95 % lower bound of 0.29 (Clopper–Pearson).
- **Failure types.** Validated: spaghetti. Not detected: layer shift (0/3, maximum score after the shift 0.30). Not measured, no labelled data: part detachment without mess, warping, under-extrusion, first-layer defects, gradual deterioration.
- **Detection latency** is 1–4 minutes after the first strand. Some filament is wasted before a pause, but the print is stopped long before a large spaghetti nest forms around the nozzle.
- **BTT Pi** performance: not measured (§ 6).
- **Camera:** the Creality Nebula has not been tested (RESEARCH § 4).
- **Live network faults** (Moonraker down, camera unplugged, stream stalls) are covered by automated tests with simulated faults, not by tests on the physical printer.
- **Long-term operation:** 40 minutes measured (§ 9), not days.

## 9. Extended operation (soak test)

`tools/soak.py` ran the complete live service (camera thread, analyser, mock Moonraker, dashboard API polled every minute) for **40 minutes** at an analysis interval of 1 s, three times the default load. It replayed a normal print in a loop at 4× speed, about 2.7 h of printing. Raw samples: [`results/soak_40min.json`](results/soak_40min.json).

| Metric | Start (after warm-up) | End |
| :--- | ---: | ---: |
| Analyses | — | 2 400 |
| Errors in the analysis loop | — | 0 |
| Process RAM (RSS) | 501.4 MB | 501.5 MB (+0.1 MB) |
| Threads | 19 | 19 |
| Open file descriptors | 7 | 7 |
| Camera reconnects | — | 0 |
| Slowest `/api/status` response | — | 41 ms |
| Incidents (false alarms) | — | 0 |

No memory, thread or file-descriptor growth was observed. A multi-day run on the real inference PC is still to be done (§ 8).
