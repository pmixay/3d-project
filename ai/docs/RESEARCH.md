# Research: models, datasets, camera, platform

Research date: November 2026. Sources are linked; anything we did not verify ourselves is marked as such.

## 1. Platform interfaces

- **Moonraker** HTTP API ([docs](https://moonraker.readthedocs.io/en/latest/external_api/introduction/)). We use `GET /server/info`, `GET /printer/objects/query` (`print_stats`, `virtual_sdcard`, `webhooks`, `display_status`), `POST /printer/print/pause` and `POST /printer/gcode/script`. `print_stats.state` is one of `standby | printing | paused | complete | cancelled | error`. An API key, if Moonraker requires one, goes in `X-Api-Key`.
- **Klipper** `M117` writes to `display_status.message`, which shows on the printer display and in Mainsail/Fluidd. `RESPOND` needs `[respond]` in `printer.cfg`, so it is configurable but not the default.
- **Crowsnest** ([mainsail-crew/crowsnest](https://github.com/mainsail-crew/crowsnest)) serves cameras through ustreamer / camera-streamer. The URLs `/webcam/?action=stream` (MJPEG) and `/webcam/?action=snapshot` (JPEG) are the ones Mainsail uses, and our camera module accepts both.
- **Obico** ([obico-server](https://github.com/TheSpaghettiDetective/obico-server), AGPL-3.0): `ml_api` serves a YOLOv2 network with one class, `failure`. Its backend turns the per-frame scores into a decision with an EWM / rolling-mean scheme (`backend/lib/prediction.py`).

## 2. Pretrained models

| Model | Source / licence | Task | Suitability | Used |
| :--- | :--- | :--- | :--- | :--- |
| **Obico failure detector** (YOLOv2, ONNX, 416², 192 MB) | obico-server `ml_api/model/model-weights.onnx.url`, AGPL-3.0 project; SHA-256 `0a6ebd8e…b9aa` | Boxes around spaghetti / filament mess | Trained on large amounts of user webcam footage, close to our camera position. Runs on a CPU. | **Yes** |
| Same, INT8 static (QDQ, ours) | made by `tools/quantize_model.py` | — | 4× smaller, ~2× faster on CPU, scores compressed (EVALUATION § 5) | Optional |
| PrintGuard (ShuffleNetV2 + prototypes) | GPL-2.0 | Whole-frame classification | 0/22 real spaghetti frames in an independent test ([3d-cli research](https://github.com/alex-mextner/3d-cli/blob/main/docs/research/printer-vision.md)); we did not re-test it | No |
| CLIP / DINOv2 zero-shot | MIT / Apache-2.0 | Generic image embeddings | Useful only as a second-stage verifier, and slow on a CPU (≈150 M parameters) | No (possible future verifier) |
| CAXTON multi-head network (Brion & Pattinson 2022) | Cambridge | Nozzle-camera extrusion parameters | Needs a camera on the nozzle, a different viewpoint from ours | No |

## 3. Datasets

| Dataset | Licence | Content | Annotations | Suitability, biases | Used for |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Zenodo 18628777** "Quality Control in AM: Image Dataset for Defect Detection in FFF" | CC-BY-4.0 | Complete prints from 3 fixed side cameras, ~1.4 s per frame. Test split: 3 normal, 3 extrusion-failure (spaghetti), 3 layer-shift prints, 20 141 frames, 7.6 h | Whole-print label only. **We added onset frames** by inspection (`datasets/labels/sessions.json`) | Real sequences, which is what a temporal engine needs. **Bias:** one printer (Prusa MK3-type), one red PLA, one simple block geometry, one lab, daylight. The failures were induced at ~29 min. | **Main evaluation** (session-level) |
| Alex-Ultra/3d-cli-print-failure-frames (HF) | CC-BY-4.0 | 421 healthy frames from 7 prints (Snapmaker U1), 7 spaghetti, 1 detached, 7 empty bed | Per frame + print group | Strongly imbalanced, and the failure classes are too small for metrics | Spot check / future |
| Javiai/failures-3D-print (HF) | **unknown** | 73 web images, boxes (error, extruder, part, spaghetti) | Boxes | Hand-held web photos, no licence | Not used |
| Masamsa/3d-print-failure-detection (HF) | **none stated** | 2 714 images merged from Roboflow + HF + "user-provided" | Binary | Random split across merged sources, so near-duplicates are likely shared between train and test (leakage); no licence | Not used |
| MLBenyamin/layerwatch | CC-BY-NC-4.0, gated | YOLO boxes: clogged nozzle, etc. | Boxes | Access needs approval | Not used |
| PARD 71-print (Zenodo 24182180) | CC-BY-4.0 | Process logs, no images | — | — | Not used |

**Leakage prevention.** Neighbouring frames of one print are almost identical, so a random frame split measures memorisation. Every split and metric here is **per print session**: a folder is one session. Session-level evaluation is the main result, and frame-level numbers are given only as model diagnostics. Any future fine-tuning must keep whole sessions on one side of the split.

**Fine-tuning: why not now.** We have no footage of our own printer yet. The public sets are small, imbalanced or unlicensed, and the one large clean set (Zenodo) has a single printer, filament and geometry, so a model fine-tuned on it would learn "red block on a Prusa". The tooling for when our own footage exists:
`python -m hercules record` (capture sessions) → `tools/contact_sheet.py` (find onset frames) → `datasets/labels/*.json` → `tools/score_sessions.py` + `tools/evaluate.py` (session-level evaluation). A fine-tune that does not beat the pretrained model on held-out *sessions* should not ship.

## 4a. Camera in use: CSI ribbon module on a Raspberry Pi

The team's camera is a small CSI board camera with an M12 lens and a flat ribbon cable (Raspberry Pi camera format). Consequences we checked:
- **The BTT Pi v1.2 has no CSI connector.** Its listed I/O is 4× USB 2.0, micro-HDMI, Ethernet, GPIO, SPI-screen and UART ([CNX Software](https://www.cnx-software.com/2023/05/01/bigtreetech-pi-v1-2-a-raspberry-pi-sized-allwinner-h616-sbc-for-3d-printers/), [Tom's Hardware](https://www.tomshardware.com/news/bigtreetech-pi-12-a-raspberry-pi-alternative-aimed-squarely-at-3d-printers), [LinuxGizmos](https://linuxgizmos.com/btt-pi-is-a-low-cost-allwinner-h616-based-sbc/)). PCs and laptops have no CSI port either. **The monitor therefore runs on a Raspberry Pi**, which also keeps the network off the Klipper host.
- On current Raspberry Pi OS, CSI cameras are driven by **libcamera**. OpenCV's V4L2 capture cannot use them directly, so Hercules reads them through `rpicam-vid` (`libcamera-vid` on Bullseye) as an MJPEG stream (`camera.source = "csi"`). The command line is built from fixed arguments only, because the source can be changed from the dashboard.
- **Sensor:** most cheap M12 modules use the OV5647 (Camera v1, 5 MP), which libcamera supports. Confirm with `rpicam-hello --list-cameras`. Setup and troubleshooting: [RASPBERRY_PI.md](RASPBERRY_PI.md).
- **Image quality:** these modules are noisy in dim light. The temporal averaging option and its measured effect are in EVALUATION § 5c.

## 4. Camera: Creality Nebula Camera — compatibility is **unverified**

Public reports conflict. The camera connects over USB-A and is marketed for Creality's Sonic Pad, Nebula Pad and K-series ([Creality store](https://store.creality.com/products/creality-nebula-camera)). Users report it enumerating as a camera, but one OctoPrint user found its advertised MJPEG mode did not work on a Raspberry Pi ([OctoPrint forum](https://community.octoprint.org/t/creality-camera-with-rasberry-pi-4/37775)). The documented Klipper route ([SimplyPrint](https://simplyprint.io/setup-guide/methods/nebula-smart-kit)) relies on Creality's own rooted firmware. We found no confirmation for a generic Linux host.

**Acceptance test on arrival** (5 minutes, on the BTT Pi or the inference PC):

```bash
v4l2-ctl --list-devices                         # must appear as a /dev/videoN device
v4l2-ctl -d /dev/video0 --list-formats-ext      # look for MJPG 1280x720 or 1920x1080
python -m hercules check-camera --source /dev/video0 --seconds 10 --save nebula.jpg
```

- MJPG listed and `check-camera` reports frames at ≥ 5 fps: **compatible**, use `fourcc = "MJPG"`.
- Only YUYV: works through OpenCV with `fourcc = ""`, at a lower resolution or frame rate. That is fine for an analysis every few seconds, but check the frame rate over the Pi's USB 2.0.
- No `/dev/video*` device: not UVC-compatible, so return it. The documented fallback is a Logitech C270 (UVC, 720p), and any ordinary UVC webcam works.

Our monitor needs about 1 frame every 3 s at ≥ 640×360. It does not need the camera's night vision. Constant lighting from the planned 24 V LED strip matters more.

## 5. Licences

- Our code: part of this repository.
- Obico weights: the Obico project is AGPL-3.0, and the weights carry no separate licence. We do not redistribute them: they are downloaded from Obico's URL and verified by hash. Running them locally for our own printer creates no obligations. If a modified version of the *service* were offered to other users over a network, AGPL source-availability obligations would apply to it, and publishing this repository satisfies them.
- Zenodo frames: CC-BY-4.0. Attribution is in `datasets/labels/sessions.json` and in EVALUATION.
