# Competition demonstration (December 3, 2026)

Duration: about 8 minutes. The replay demo runs on the Raspberry Pi (the real inference computer) or, as a fallback, on any laptop. Show it in a browser; a phone on the same Wi-Fi makes a good second screen for the mobile dashboard. On the Pi, stop the service first (`sudo systemctl stop hercules`) so the demo can use port 8090. If the CSI camera is connected, its live view can be shown separately with `camera.source = "csi"` and `pipeline.monitor_when = "always"`.

## Preparation (the day before)

```bash
cd 3d-project/ai
./deploy/install.sh --no-service
.venv/bin/python datasets/fetch_zenodo_fffqc.py --kinds no_error_print extrusion_error_print --cams camera2
.venv/bin/python -m pytest -q          # show that all tests pass
```
Check that `state-demo/` gets created and that the dashboard opens at `http://localhost:8090`. Also have this ready:
- `docs/EVALUATION.md` open in a tab (the measured numbers)
- `docs/ARCHITECTURE.md` with the diagram open in a tab
- If the real printer is available and supervised: `config/hercules.local.toml` pointing at its Moonraker, with `pause_policy = "confirm"`

## Script

| # | Requirement | What to do / say |
| :--- | :--- | :--- |
| 1 | **Normal printing footage** | `./tools/demo.sh data/zenodo_fffqc/test_extrusion_error_print_camera2 10 auto`. Open the dashboard. The live view shows a real recorded print: a Prusa MK3 printing PLA, a CC-BY-4.0 dataset recording. The level is **OK**, the score line stays flat and the printer card shows `printing` from the simulated Moonraker. Point out the system card: inference latency, CPU, RAM, analyses per minute. |
| 2 | **Real-time analysis** | Explain that every 3 s of print time one frame passes validation (blur, darkness, duplicates), then the neural network, then the temporal engine. Draw an ROI on the settings image to show the region of interest. At 10× speed the analysis runs on the recording's clock, so the decisions are the same as in real time. |
| 3 | **Recognition of a real recorded defect** | At about 29 min of print time (about 3 min of wall time) the second part breaks into loose filament. Boxes appear on the live view, and the frame score p rises before the decision score. Explain why the system waits for evidence: a single frame is not enough (evidence gate, smoothing). |
| 4 | **Visualisation** | The level switches to WARNING and then CRITICAL. The incident banner appears, the chart crosses the dashed warning and critical lines, and the bounding boxes label the failure with confidence values. |
| 5 | **Incident report** | Click **Report**. The HTML report shows the times, peak score, printer state (file, progress, print time), the action taken, the score timeline and annotated evidence images. All of it is also in `state-demo/incidents/<id>/` (report.json, images). |
| 6 | **Verified pause** | With policy `auto`, the system has already sent `POST /printer/print/pause`. The incident action reads **paused — pause verified (print_stats.state == paused)**, and the printer card shows `paused`. Open `http://127.0.0.1:7125/mock/log`: exactly one `pause`, one `M117` message, and **no** resume. Monitoring has suspended itself because the printer is paused. *Variant:* run with `confirm` instead of `auto` and press **Pause print** in the banner yourself. |
| 7 | **Measured performance** | Show the system card live, then `docs/EVALUATION.md`: detection rate, false alarms per printing hour, latency, and the inference-interval and hardware tables. Point out what is **not** detected (layer shift) and why we say so. |

### Optional: a false alarm and recovery
Run `./tools/demo.sh data/zenodo_fffqc/test_extrusion_error_print_camera2 10 confirm`. When the warning appears, press **False alarm**. The incident is marked *dismissed*, the engine resets and stays quiet for 10 minutes. Explain that this is how an operator handles a wrong alert without disabling the monitor.

### Optional: robustness live
- Run `curl -X POST "127.0.0.1:7125/mock/fault?mode=down"`: the printer pill turns red, the analysis continues ("printer link lost (alerts only, cannot pause)"). Then run `mode=ok` and it recovers on its own.
- Point a real webcam at the table (`HERCULES_CAMERA__SOURCE=0`) and cover the lens with a hand: after 20 s a *camera view obstructed* incident appears.

### Optional: the real printer (only supervised, only `confirm`)
Set `moonraker.url` to the BTT Pi, `pause_policy = "confirm"`, and point the camera at the bed. Start a small print, and use the dashboard's **Pause** button to show that a real `PAUSE` reaches Klipper and is verified. Resume from Mainsail by hand, because the AI never resumes.

## Talking points: engineering, not plugin installation

1. **We measured instead of assuming:** session-level evaluation on complete recorded prints, false alarms per printing hour, detection latency from the first visible strand, and a sweep of the inference interval.
2. **What we built ourselves:** the decision engine (time-normalised, evidence gate, frozen baseline, hysteresis), camera health monitoring, verified pause, the mock printer, the dashboard, and the evaluation and benchmark tools. What we reused: the Obico pretrained network and its published thresholds (ARCHITECTURE § 4).
3. **Honesty about limits:** layer shift is not detected, there are no measurements on the BTT Pi yet, and the dataset has one printer and one filament. All of this is in the next-steps list.
4. **Safety:** the AI can only pause (default `auto`, verified), never resume; Klipper's protections are independent of it.
