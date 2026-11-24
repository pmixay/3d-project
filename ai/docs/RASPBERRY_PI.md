# Running Hercules AI on a Raspberry Pi with a CSI camera

Target setup: a **Raspberry Pi** runs the AI monitor with a **CSI ribbon camera** (the small board camera with an M12 lens and a flat cable). The **BTT Pi** keeps running Klipper and Moonraker. The two talk over the LAN.

```
CSI camera ──ribbon──► Raspberry Pi (Hercules AI, dashboard :8090) ──LAN──► BTT Pi (Moonraker :7125 → Klipper)
```

Why not plug the camera into the BTT Pi: it has **no CSI connector**. Its listed ports are 4× USB 2.0, micro-HDMI, Ethernet, GPIO, SPI-screen and UART. Laptops and PCs cannot take a CSI ribbon camera either. A separate Pi also keeps the neural network off the board that runs Klipper's real-time work.

## 1. What you need

| Item | Requirement |
| :--- | :--- |
| Raspberry Pi | Pi 4 or Pi 5 recommended (2 GB+ RAM). Pi 3B/3B+ (1 GB) should work with the INT8 model and a long interval, **not measured**. |
| OS | **Raspberry Pi OS (64-bit)**, Lite is enough. A 32-bit OS cannot install ONNX Runtime; the installer stops with a message. |
| Camera | CSI module supported by libcamera: OV5647 (Camera v1 / most cheap M12 modules), IMX219 (v2), IMX708 (v3), IMX477 (HQ). Check the chip marking or the seller page. |
| Cable | Pi 4/3: standard 15-pin 1 mm cable. **Pi 5 / Zero: 22-pin 0.5 mm cable** (a "Pi 5 camera cable", 15→22 pin). |
| Light | The bed must be lit (the planned 24 V LED strip). Cheap modules get noisy in dim light, and noise is the measured weak point. |
| Cooling | A heatsink or fan. Inference is sustained CPU load, and a throttling Pi gets slower. |

## 2. Connect and check the camera (5 minutes)

1. Power off. Lift the CSI connector latch, insert the ribbon (contacts towards the contacts), and close the latch.
2. Boot and run:
   ```bash
   rpicam-hello --list-cameras        # Bullseye: libcamera-hello --list-cameras
   ```
   The sensor (e.g. `ov5647`) should be listed with its modes.
3. If it reports *"no cameras available"*:
   - Check the cable direction and the latch, the most common cause.
   - Cheap clones are sometimes not auto-detected. Edit `/boot/firmware/config.txt` (Bullseye: `/boot/config.txt`), set `camera_auto_detect=0`, add `dtoverlay=ov5647` (or `imx219`, …), then reboot.
4. Take a test picture: `rpicam-jpeg -o test.jpg`, then copy it to the laptop and look at focus and framing. M12 lenses are focused by turning the lens; fix it with a drop of glue once sharp at the bed distance.

## 3. Install

```bash
sudo apt install -y git
git clone https://github.com/pmixay/3d-project && cd 3d-project/ai
./deploy/install.sh
```

On a Pi the installer also installs `rpicam-apps`, checks for a 64-bit OS and RAM, and creates `config/hercules.local.toml` from **`config/hercules.rpi.toml`**. Edit one line, the BTT Pi address:

```toml
[moonraker]
url = "http://192.168.1.50:7125"
```

Then:
```bash
.venv/bin/python -m hercules check-camera --source csi --seconds 10 --save cam.jpg   # frames arrive?
sudo systemctl restart hercules
journalctl -u hercules -f
```
Open `http://<raspberry-pi-ip>:8090` from the laptop or a phone. Drag the region of interest around the bed in Settings.

On the BTT Pi, allow the Raspberry Pi to use Moonraker. In `moonraker.conf`, under `[authorization]`, add its address to `trusted_clients` (or set `moonraker.api_key` instead).

## 4. Pi defaults and why

| Setting (`hercules.rpi.toml`) | Value | Reason |
| :--- | :--- | :--- |
| `camera.source` | `csi` | rpicam-vid streams MJPEG to the monitor (no Crowsnest needed on this Pi) |
| `camera.width × height, fps` | 1280×720, 5 fps | the network sees 416×416 anyway; fewer frames = less CPU for JPEG encoding |
| `detector.threads` | 3 | one core stays free for the camera, the dashboard and the OS |
| `pipeline.interval_s` | 6 s | measured on recorded prints: 6–12 s detects as fast as analysing every frame (EVALUATION § 3) |
| `web.stream_fps / stream_width` | 2 fps, 640 px | live-view encoding costs CPU |
| `camera.average_frames` | 1 | set to **4** if the camera is noisy (grainy image, "Image quality poor" incidents) |

## 5. Measure the Pi: this has not been done yet

Every performance number in EVALUATION was measured on an x86 VM. **No Raspberry Pi has been measured.** Do this once the Pi is set up:

```bash
sudo systemctl stop hercules                      # free the camera and the CPU for the benchmark
.venv/bin/python -m hercules record --source csi --out /tmp/bench --interval 2 --duration 40
.venv/bin/python tools/benchmark.py --frames /tmp/bench --n 20 --threads 1 2 3 4 --intervals 3 6 12 \
    --duration 60 --out docs/results/benchmark_raspberry-pi.json
vcgencmd measure_temp; vcgencmd get_throttled     # 0x0 = never throttled
```
Commit the JSON. How to read the result:
- If one analysis takes less than `interval_s`, the system keeps up. Raise `interval_s` to 12 if the CPU stays busy: per the measured sweep, detection speed is the same up to 12 s.
- If RAM is tight (1 GB Pi), or one analysis takes longer than about 5 s, build the INT8 model on the Pi from your own normal-print frames. It was measured on x86 as 2.3× faster, 150 MB less RAM, still 3/3 detected with 0 false alarms, but 15–35 s later:
  ```bash
  .venv/bin/pip install onnx sympy
  .venv/bin/python -m hercules record --source csi --out data/own/calib --interval 5 --duration 600
  .venv/bin/python tools/quantize_model.py --mode qdq --calib data/own/calib
  # config/hercules.local.toml:  [detector] model_path = "models/obico-failure-int8-qdq.onnx"
  #                              model_sha256 = ""
  ```

## 6. Troubleshooting (Pi-specific)

| Symptom | Fix |
| :--- | :--- |
| Dashboard: camera offline, error mentions `no cameras available` | Cable or latch, or the overlay for a clone module (§ 2.3). `rpicam-hello --list-cameras` must work first. |
| Error mentions `rpicam-vid or libcamera-vid` | `sudo apt install rpicam-apps` (Bookworm) / `libcamera-apps` (Bullseye). |
| `Pipeline handler in use by another process` | Another program holds the camera (Crowsnest/camera-streamer, a forgotten `rpicam-hello`). Stop it; only one program can open a CSI camera. |
| Want the camera in Mainsail too | One program per camera: either use the Hercules dashboard as the live view, or run Crowsnest on this Pi and point Hercules at `http://localhost/webcam/?action=snapshot`. |
| Grainy picture, "Image quality poor" incidents | More light first; then `camera.average_frames = 4` (dashboard → Settings → Camera). |
| Image too dark / colours odd | Cheap modules without an IR-cut filter look pink in daylight. The effect on detection has **not been measured**; light the bed with the LED strip and record a normal print to check for false alarms. |
| `install.sh` stops: 32-bit OS | Re-flash *Raspberry Pi OS (64-bit)* with Raspberry Pi Imager. |
| Analyses fall behind, CPU 100 %, temperature > 80 °C | Heatsink/fan; `interval_s = 12`; `detector.threads = 2`; INT8 model (§ 5). |
