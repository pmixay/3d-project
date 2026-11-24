"""Configuration: TOML file -> environment overrides -> dashboard overrides.

Precedence (last wins):
  1. built-in defaults (the dataclasses below)
  2. the TOML file given with --config (default config/hercules.toml)
  3. environment variables HERCULES_<SECTION>__<KEY>, e.g.
     HERCULES_CAMERA__SOURCE=http://printer.local/webcam/?action=stream
     HERCULES_MOONRAKER__URL=http://192.168.1.50:7125
  4. settings changed in the dashboard, persisted to <state_dir>/settings.json

Only keys listed in RUNTIME_EDITABLE may be changed from the dashboard.
"""
from __future__ import annotations

import copy
import dataclasses as dc
import json
import os
import threading
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib
from typing import Any


@dc.dataclass
class CameraCfg:
    # "0" or "/dev/video0" -> USB (V4L2); "http(s)://..." -> MJPEG stream or JPEG
    # snapshot URL (auto-detected); a video file or a directory of JPEGs -> replay.
    source: str = "0"
    width: int = 1280
    height: int = 720
    fps: int = 15
    fourcc: str = "MJPG"          # USB cameras deliver 720p/1080p at full rate only as MJPG
    average_frames: int = 1       # >1: average the last N frames before analysis (noisy/cheap cameras)
    snapshot_interval_s: float = 1.0
    replay_speed: float = 1.0     # files only: 1.0 = real time, 4.0 = 4x faster
    replay_frame_interval_s: float = 0.0  # directories: seconds per frame (0 = read frames.csv / 1 s)
    loop: bool = False
    stale_after_s: float = 5.0    # no new frame for this long -> camera "stalled"
    reconnect_max_s: float = 30.0


@dc.dataclass
class DetectorCfg:
    model_path: str = "models/obico-failure-5a6b1be1fa.onnx"
    model_url: str = "https://www.obico.io/static_pub/ml-models/model-weights-5a6b1be1fa.onnx"
    model_sha256: str = "0a6ebd8e30dbf6a450c50f9c0a5406f04ba7eb1c99fd5996e888c78bb383b9aa"
    # used when model_path is missing and has no URL (e.g. the INT8 model was not copied to the Pi yet)
    fallback_model_path: str = ""
    backend: str = "onnxruntime"  # onnxruntime | opencv
    providers: str = "auto"       # auto | cpu | comma list of ORT providers
    threads: int = 0              # 0 = library default
    box_threshold: float = 0.08   # per-box confidence floor (Obico ml_api default)
    nms_threshold: float = 0.45


@dc.dataclass
class PipelineCfg:
    interval_s: float = 3.0       # seconds between inferences
    monitor_when: str = "printing"  # printing | always
    roi: list = dc.field(default_factory=lambda: [0.0, 0.0, 1.0, 1.0])  # x0,y0,x1,y1 normalised
    roi_mode: str = "crop"        # crop: only the ROI goes to the network (more pixels on the print,
                                  # measured faster, EVALUATION 5c); filter: full frame, drop boxes outside
    ignore_zones: list = dc.field(default_factory=list)  # [[x0,y0,x1,y1], ...] boxes centred here are dropped
    skip_duplicates: bool = True
    duplicate_diff: float = 0.8   # mean abs grey diff (0-255) below which a frame counts as unchanged
    skip_blurred: bool = True
    blur_ratio: float = 0.35      # sharpness below this fraction of the running median -> blurred
    max_consecutive_skips: int = 5
    dark_level: float = 20.0
    bright_level: float = 240.0
    frozen_after_s: float = 30.0
    obstructed_fraction: float = 0.75
    noise_sigma_max: float = 4.0  # clean frames measure ~1-2, sigma-18 sensor noise ~6 (EVALUATION 5b)


@dc.dataclass
class DecisionCfg:
    enabled_categories: list = dc.field(default_factory=lambda: [
        "failure", "camera_offline", "camera_frozen", "camera_obstructed", "bad_lighting"])
    ewm_tau_s: float = 60.0       # smoothing time constant (Obico: EWM span 12 at ~10 s/frame)
    baseline_tau_s: float = 3600.0  # slow baseline subtracted from the smoothed score
    warn_threshold: float = 0.38  # Obico THRESHOLD_LOW
    critical_factor: float = 1.75 # Obico ESCALATING_FACTOR: critical = warn * factor
    min_positive_frames: int = 3  # at least N recent frames with p >= positive_p before alerting
    positive_p: float = 0.2
    evidence_window_s: float = 120.0
    warmup_s: float = 60.0        # no failure alerts this long after monitoring starts
    clear_ratio: float = 0.5      # incident clears when score < warn * clear_ratio ...
    clear_hold_s: float = 120.0   # ... for this long
    dismiss_suppress_s: float = 600.0  # after a false alarm is dismissed
    camera_alert_after_s: float = 20.0  # camera problem must persist this long


@dc.dataclass
class ActionsCfg:
    # auto   : critical incidents pause the print through Moonraker, verified via print_stats (default)
    # confirm: critical incidents wait for a person to press "Pause" in the dashboard
    # notify : alert only, never pauses
    pause_policy: str = "auto"
    pause_on_camera_loss: bool = False
    gcode_notify: bool = True     # show a message on the printer display (M117)
    notify_gcode: str = "M117 {text}"   # e.g. 'RESPOND TYPE=error MSG="{text}"' if [respond] is enabled
    webhook_url: str = ""         # optional: POST JSON incidents (e.g. a local ntfy server)


@dc.dataclass
class MoonrakerCfg:
    url: str = ""                 # e.g. http://192.168.1.50:7125 ; empty = no printer link
    api_key: str = ""
    poll_interval_s: float = 2.0
    timeout_s: float = 3.0


@dc.dataclass
class WebCfg:
    host: str = "0.0.0.0"
    port: int = 8090
    auth_token: str = ""          # if set, POST endpoints require header X-Hercules-Token
    stream_fps: float = 5.0
    stream_width: int = 960


@dc.dataclass
class Config:
    camera: CameraCfg = dc.field(default_factory=CameraCfg)
    detector: DetectorCfg = dc.field(default_factory=DetectorCfg)
    pipeline: PipelineCfg = dc.field(default_factory=PipelineCfg)
    decision: DecisionCfg = dc.field(default_factory=DecisionCfg)
    actions: ActionsCfg = dc.field(default_factory=ActionsCfg)
    moonraker: MoonrakerCfg = dc.field(default_factory=MoonrakerCfg)
    web: WebCfg = dc.field(default_factory=WebCfg)
    state_dir: str = "state"
    log_level: str = "INFO"

    def to_dict(self) -> dict:
        return dc.asdict(self)


RUNTIME_EDITABLE = {
    "camera": {"source", "width", "height", "fps", "replay_speed", "loop", "average_frames"},
    "detector": {"box_threshold"},
    "pipeline": {"interval_s", "monitor_when", "roi", "roi_mode", "ignore_zones",
                 "skip_duplicates", "skip_blurred"},
    "decision": {"enabled_categories", "warn_threshold", "critical_factor",
                 "min_positive_frames", "ewm_tau_s", "warmup_s"},
    "actions": {"pause_policy", "pause_on_camera_loss", "gcode_notify"},
}


def _coerce(value: Any, like: Any) -> Any:
    if isinstance(like, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if isinstance(like, int) and not isinstance(like, bool):
        return int(value)
    if isinstance(like, float):
        return float(value)
    if isinstance(like, list):
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, list):
            raise ValueError("expected a list")
        return value
    return str(value)


def _apply(cfg: Config, data: dict, allowed: dict | None = None) -> None:
    for section, values in data.items():
        if section in ("state_dir", "log_level") and not isinstance(values, dict):
            if allowed is None:
                setattr(cfg, section, str(values))
            continue
        sub = getattr(cfg, section, None)
        if sub is None or not isinstance(values, dict):
            raise ValueError(f"unknown config section: {section}")
        for key, value in values.items():
            if not hasattr(sub, key):
                raise ValueError(f"unknown config key: {section}.{key}")
            if allowed is not None and key not in allowed.get(section, ()):
                raise ValueError(f"{section}.{key} cannot be changed at runtime")
            setattr(sub, key, _coerce(value, getattr(sub, key)))


def validate(cfg: Config) -> None:
    p, d = cfg.pipeline, cfg.decision
    for name, rect in [("roi", p.roi)] + [("ignore_zones", z) for z in p.ignore_zones]:
        if len(rect) != 4 or not all(0.0 <= float(v) <= 1.0 for v in rect):
            raise ValueError(f"{name}: expected [x0,y0,x1,y1] in 0..1")
        if rect[2] - rect[0] < 0.02 or rect[3] - rect[1] < 0.02:
            raise ValueError(f"{name}: rectangle too small or inverted")
    if p.interval_s < 0.05 or p.interval_s > 600:
        raise ValueError("pipeline.interval_s out of range 0.05..600")
    if p.monitor_when not in ("printing", "always"):
        raise ValueError("pipeline.monitor_when must be 'printing' or 'always'")
    if p.roi_mode not in ("filter", "crop"):
        raise ValueError("pipeline.roi_mode must be 'filter' or 'crop'")
    if not 0.0 < cfg.detector.box_threshold < 1.0:
        raise ValueError("detector.box_threshold must be in (0,1)")
    if d.warn_threshold <= 0 or d.critical_factor < 1.0:
        raise ValueError("decision thresholds invalid")
    if not 1 <= cfg.camera.average_frames <= 16:
        raise ValueError("camera.average_frames must be 1..16")
    src = cfg.camera.source.strip()
    if src.startswith("csi:") and not src[4:].isdigit():
        raise ValueError("camera.source: use csi or csi:<camera number>")
    if cfg.actions.pause_policy not in ("notify", "confirm", "auto"):
        raise ValueError("actions.pause_policy must be notify, confirm or auto")
    if cfg.detector.backend not in ("onnxruntime", "opencv"):
        raise ValueError("detector.backend must be onnxruntime or opencv")


def load(path: str | None = None, env: dict | None = None, use_overrides: bool = True) -> Config:
    cfg = Config()
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            _apply(cfg, tomllib.load(f))
    env = os.environ if env is None else env
    for k, v in env.items():
        if not k.startswith("HERCULES_"):
            continue
        rest = k[len("HERCULES_"):].lower()
        if rest in ("state_dir", "log_level"):
            setattr(cfg, rest, v)
        elif "__" in rest:
            section, key = rest.split("__", 1)
            _apply(cfg, {section: {key: v}})
    if use_overrides:
        ov = overrides_path(cfg)
        if os.path.exists(ov):
            with open(ov) as f:
                _apply(cfg, json.load(f), RUNTIME_EDITABLE)
    validate(cfg)
    return cfg


def overrides_path(cfg: Config) -> str:
    return os.path.join(cfg.state_dir, "settings.json")


class LiveConfig:
    """Thread-safe holder; dashboard edits are validated, applied and persisted."""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._lock = threading.Lock()
        self.version = 0

    @property
    def cfg(self) -> Config:
        return self._cfg

    def update(self, changes: dict) -> Config:
        with self._lock:
            trial = copy.deepcopy(self._cfg)
            _apply(trial, changes, RUNTIME_EDITABLE)
            validate(trial)
            path = overrides_path(trial)
            saved = {}
            if os.path.exists(path):
                with open(path) as f:
                    saved = json.load(f)
            for section, values in changes.items():
                saved.setdefault(section, {}).update(
                    {k: getattr(getattr(trial, section), k) for k in values})
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(saved, f, indent=2)
            os.replace(tmp, path)
            # mutate in place so components holding sub-config references see the change
            for section in changes:
                src, dst = getattr(trial, section), getattr(self._cfg, section)
                for field in dc.fields(src):
                    setattr(dst, field.name, getattr(src, field.name))
            self.version += 1
            return self._cfg
