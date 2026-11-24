# Hercules AI — print failure monitor

The camera subsystem of the Hefest / Hercules printer rebuild (owner: Голубев Павел). It runs on a **Raspberry Pi** next to the printer, watches the print through a CSI ribbon camera (or a USB/network camera) and runs a neural network on the frames. A temporal decision engine sits between the network and the alerts, so it only raises an incident when a failure is persistent. It shows everything on a local dashboard and can pause the print through Moonraker. Klipper keeps full control of the printer. This process can only **pause**: it never resumes, cancels, heats or moves anything.

Everything runs locally: no cloud service, account or subscription is needed.

| Document | Contents |
| :--- | :--- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline diagram, design decisions, Obico vs. own pipeline, what is ours and what is third-party |
| [docs/RESEARCH.md](docs/RESEARCH.md) | Models, datasets, licences, camera compatibility (Creality Nebula) |
| [docs/EVALUATION.md](docs/EVALUATION.md) | **Measured** detection quality, false alarms per hour, latency, inference interval and hardware benchmarks |
| [docs/RASPBERRY_PI.md](docs/RASPBERRY_PI.md) | **Target setup:** Raspberry Pi + CSI camera — hardware, camera check, install, Pi defaults, how to measure the Pi |
| [docs/DEMO.md](docs/DEMO.md) | Step-by-step competition demonstration (December 3, 2026) |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Camera, Moonraker, performance and service problems |

## What it detects (and what it does not)

| Category | Status | Evidence |
| :--- | :--- | :--- |
| Spaghetti / filament mess / extrusion into the air | **Supported** | 3/3 recorded spaghetti failures detected, 1–4 min after the first loose strand; 0 false alarms in 5.4 h of normal printing (one public dataset, another printer; 95 % upper bound 0.56 false alarms/h) ([EVALUATION](docs/EVALUATION.md)) |
| Camera offline / stream unavailable / stalled | **Supported** | automated tests (USB, MJPEG, snapshot, reconnect) |
| Frozen image, covered lens, unusable lighting, heavy sensor noise | **Supported** | automated tests; noise flag: 0/340 clean vs 87/87 noisy real frames flagged |
| Part detached from the bed | Partly: only once the loose part produces visible mess | not separately validated, no labelled data |
| Layer shift, warping, under-extrusion, first-layer defects | **Not supported** | 0/3 recorded layer shifts alerted (max. score 0.30 < warning 0.38); the network was not trained for these classes (see EVALUATION) |

We do not claim a defect class unless a measurement supports it.

## Quick start (offline, no printer needed)

```bash
cd ai
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,datasets]"
python -m hercules download-model                       # 192 MB, SHA-256 verified
python datasets/fetch_zenodo_fffqc.py --kinds extrusion_error_print --cams camera2   # one recorded failing print
python tools/mock_moonraker.py --start-print demo.gcode &                           # simulated printer on :7125
HERCULES_CAMERA__SOURCE=data/zenodo_fffqc/test_extrusion_error_print_camera2 \
HERCULES_CAMERA__REPLAY_SPEED=10 HERCULES_PIPELINE__INTERVAL_S=0.3 \
HERCULES_MOONRAKER__URL=http://127.0.0.1:7125 python -m hercules run
# open http://localhost:8090
```

For replays the decision engine runs on the **recording's clock**, so the 10× replay makes the same decisions at the same points of the print as real time would. 0.3 s of wall time at 10× is 3 s of print time, the default interval.

## Install

### Target setup — Raspberry Pi with a CSI camera (recommended)

```
CSI camera ──ribbon──► Raspberry Pi (Hercules AI + dashboard) ──LAN──► BTT Pi (Moonraker → Klipper)
```
The BTT Pi has no CSI connector, and running the network on the Klipper host would compete with Klipper. A separate Raspberry Pi takes the camera and the AI load. Step-by-step guide, Pi defaults and the (still missing) Pi measurements: **[docs/RASPBERRY_PI.md](docs/RASPBERRY_PI.md)**.

```bash
git clone https://github.com/pmixay/3d-project && cd 3d-project/ai
./deploy/install.sh               # 64-bit check, rpicam-apps, venv, model, Pi config preset, systemd service
nano config/hercules.local.toml   # moonraker.url = "http://<btt-pi-ip>:7125"
sudo systemctl restart hercules
journalctl -u hercules -f         # logs (also state/logs/hercules.log, rotated)
```

The service restarts automatically after a crash (`Restart=always`). It runs at low CPU priority (`Nice=10`, `CPUWeight=20`) with a memory cap. Hardware requirements are in [EVALUATION § hardware](docs/EVALUATION.md#hardware-requirements).

### Other camera sources

| `camera.source` | Camera |
| :--- | :--- |
| `csi`, `csi:1` | Raspberry Pi CSI ribbon camera (OV5647, IMX219, IMX708, …) through `rpicam-vid` |
| `/dev/video0` or `0` | USB webcam (UVC) on the computer running Hercules |
| `http://<host>/webcam/?action=snapshot` | Crowsnest/ustreamer on another machine, one JPEG per analysis |
| `http://<host>/webcam/?action=stream` | the same as an MJPEG stream (smoother live view, more bandwidth) |
| a video file or a folder of frames | offline replay for tests and the demo |

Any other Linux computer (x86 PC, laptop) works the same way with a USB or network camera; the installer then uses `config/hercules.toml`.

### Cheap / low-quality cameras

Small CSI modules with M12 lenses are noisy in dim light, and noise caused false alarms in testing. In order of measured effect (EVALUATION § 5c):
1. **Draw the region of interest around the bed** (dashboard → Settings → Region of interest). In every simulated noisy or cheap-camera condition, this removed all false alarms, which came from background clutter. In the default crop mode it also speeds up detection on distant views, because the print fills more of the network's input.
2. **Resolution: 1280×720, at least 640×480.** At 320×180, detection dropped to 1 of 3 failures.
3. **Light the bed** (the 24 V LED strip).
4. If the picture is still grainy, set `camera.average_frames = 4`. It averages the last 4 frames before each analysis, which recovered detection under strong noise (2/3 → 3/3).

These results come from simulated degradations of another printer's footage. Record a normal print with our own module to confirm them.

### Running on the BTT Pi itself

Not recommended and **not measured**. The BTT Pi runs Klipper, has no CSI port, and its 1 GB RAM is shared with Klipper.

## Configuration

`config/hercules.toml` documents every key. The order of precedence is: the file, then environment variables `HERCULES_<SECTION>__<KEY>` (for example `HERCULES_MOONRAKER__URL`), then dashboard edits, which are saved to `state/settings.json`. The keys that matter most:

| Key | Default | Meaning |
| :--- | :--- | :--- |
| `pipeline.interval_s` | 3.0 | seconds between analyses (measured trade-off in EVALUATION) |
| `pipeline.monitor_when` | printing | analyse only while Moonraker reports `printing`; `always` for demos |
| `pipeline.roi` | full frame | `[x0,y0,x1,y1]` 0..1: boxes outside are ignored (set it in the dashboard by dragging) |
| `decision.warn_threshold` | 0.38 | warning level of the decision score (critical = × `critical_factor` 1.75) |
| `decision.min_positive_frames` | 3 | evidence gate: frames with p ≥ 0.2 within 120 s needed to alert |
| `actions.pause_policy` | **auto** | `auto` (pause, verified) / `confirm` (dashboard button) / `notify` (alert only) |

**Automatic pausing is on by default.** On a confirmed failure the print is paused through Moonraker and the pause is verified. The detection numbers come from another printer, so watch the first prints on yours: a false alarm only pauses the print, and you resume it from Mainsail. If false alarms occur, switch to `confirm` or `notify` in the dashboard and record the session for evaluation. The AI never resumes a print. If this service stops, the printer simply carries on under Klipper's own protections: thermal runaway, heater limits and emergency stop do not depend on it.

**Network security.** The dashboard is meant for the workshop LAN. Anyone who can reach port 8090 can see the camera and, unless `web.auth_token` is set, change settings or press Pause. On a shared network, set `auth_token` (state-changing requests then need the `X-Hercules-Token` header; the dashboard asks for it once). Never expose the port to the internet. The service needs only *outgoing* access to Moonraker and the camera.

## Repository layout

```
ai/
  hercules/            the application (Python package)
    camera.py          CSI (rpicam-vid) / USB / MJPEG / snapshot / video / frame-folder sources, reconnect,
                       bounded buffer, temporal frame averaging
    quality.py         frame validation: dark, overexposed, noise, blur, duplicate, frozen, obstructed
    detector.py        ONNX Runtime / OpenCV DNN wrapper for the Obico model, ROI, ignore zones
    temporal.py        time-normalised decision engine, evidence gate, hysteresis
    pipeline.py        Analyzer: the single code path for live and offline runs
    monitor.py         orchestration, incidents, actions, camera-health incidents
    moonraker.py       printer state, verified pause, on-printer notification
    incidents.py       SQLite log, evidence images, HTML/JSON reports
    web.py, static/    dashboard
  tools/               mock_moonraker, evaluate, score_sessions, benchmark, quantize_model, contact_sheet
  datasets/            dataset fetcher + our onset labels (labels/sessions.json)
  tests/               pytest suite (44 tests, offline)
  deploy/              install.sh, systemd unit
  docs/                architecture, research, evaluation, demo, troubleshooting
```

## Tests

```bash
pip install -e ".[dev]" && python -m pytest -q
```
The suite covers camera sources (including disconnect and reconnect), frame validation, the decision engine, detector post-processing (parity with Obico's reference code), Moonraker outages and recovery, the verified pause, the configuration, and end-to-end runs: monitor + mock printer + dashboard API under all three pause policies.

## Licences

Our code in `ai/` is published as part of this repository. The detector weights belong to the **Obico** project (AGPL-3.0). They are downloaded at install time and not stored in this repository. If you distribute a modified network service built on them, the AGPL obligations apply; see [RESEARCH § licences](docs/RESEARCH.md#licences). The evaluation frames are CC-BY-4.0 (Zenodo record 18628777) and are also downloaded on demand, not redistributed.
