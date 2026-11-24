# Troubleshooting

First look at the dashboard pills (monitor / camera / printer / model), then the logs:

```bash
journalctl -u hercules -f            # service log
tail -f state/logs/hercules.log      # same, rotated file (5 x 5 MB)
curl -s localhost:8090/api/status | python3 -m json.tool
```

## Camera

| Symptom | Cause / fix |
| :--- | :--- |
| `camera offline`, error `cannot open USB camera 0` | Wrong index or no permission. Run `v4l2-ctl --list-devices`, then use `/dev/videoN`. Add the service user to the `video` group (the installer does this) and log in again. |
| USB camera opens but gives 5 fps or less at 1080p | The camera is sending uncompressed YUYV. Keep `fourcc = "MJPG"`, or lower `width`/`height`. One frame every few seconds is enough for detection. |
| Camera only supports YUYV (some Nebula reports) | Set `fourcc = ""` and 1280×720 or lower. |
| `camera stalled` | The device is open but frames stopped (USB power, hub). Use a powered hub or a shorter cable. The source reconnects with back-off by itself. |
| Crowsnest URL gives `URL did not return an image or MJPEG stream` | Open the URL in a browser. Use `/webcam/?action=snapshot` or `?action=stream`, with the camera name if there are several (`/webcam2/...`). |
| `camera frozen` incident | Frames are bit-identical: the streamer hangs while the device still answers. Restart Crowsnest (`sudo systemctl restart crowsnest`). |
| `camera obstructed` / `bad lighting` | Lens covered, camera knocked out of position, or lights off. Detection is suspended for those frames rather than guessing. |
| Live view works, but no analyses | Monitoring runs only while the printer is `printing` (`pipeline.monitor_when`). Use `always` for tests without a printer. |

## Printer link (Moonraker)

| Symptom | Cause / fix |
| :--- | :--- |
| `printer offline` | Check `curl http://<pi>:7125/server/info` from the inference PC. Firewall? Wrong IP? Monitoring and alerts keep working; only pausing is impossible. |
| HTTP 401 / 403 | Moonraker needs authorisation: add the inference PC to `[authorization] trusted_clients` in `moonraker.conf`, or set `moonraker.api_key`. |
| `printer klippy_shutdown` | Klipper is in shutdown (an MCU error, for example). This is not an AI problem: fix it in Mainsail. |
| Pause shows `pause_failed` | Read the incident's action detail. "not printing" means the print had already stopped. "sent but state ..." means the `PAUSE` macro did not pause within 15 s: check `[pause_resume]` / the PAUSE macro in `printer.cfg`. |
| No message on the printer display | `M117` needs `display_status`, which is always loaded. For console messages use `notify_gcode = 'RESPOND TYPE=error MSG="{text}"'` with `[respond]` enabled. |

## Detection

| Symptom | What to do |
| :--- | :--- |
| False alarms on a busy background (cables, a textured wall, other printers) | Drag an ROI around the bed in the dashboard. Boxes outside it are ignored. Add `ignore_zones` for fixed objects. |
| False alarm during a valid print | Press **False alarm** on the incident. The engine resets and stays quiet for 10 minutes. Record the session (`python -m hercules record`) so it can be added to the evaluation set. |
| Detection is too slow | Lower `interval_s` (EVALUATION § 3 gives the measured effect), or lower `warn_threshold` slightly. Every change is a trade against false alarms, so re-run `tools/evaluate.py` afterwards. |
| Nothing detected in the first minute | Intentional: `decision.warmup_s` = 60 s. |

## Performance

| Symptom | What to do |
| :--- | :--- |
| High CPU on a shared machine | Set `detector.threads = 1` or `2` and raise `interval_s`. Benchmark with `tools/benchmark.py`. |
| Weak CPU (old laptop, ARM board) | Build the INT8 model with `tools/quantize_model.py` and evaluate it (EVALUATION § 5) before switching `detector.model_path`. Thresholds may need re-checking, because INT8 scores are lower. |
| Service restarts in a loop | `systemctl status hercules` shows the exit reason. After 10 restarts in 5 minutes systemd stops trying. Run the `ExecStart` command by hand to see the error. |
| `model checksum mismatch` | The download was interrupted or replaced. Delete `models/*.onnx` and run `python -m hercules download-model`. |
