"""Resource and performance metrics (CPU, RAM, temperature, latency, rates)."""
from __future__ import annotations

import collections
import os
import threading
import time

import numpy as np
import psutil


class Metrics:
    def __init__(self):
        self.proc = psutil.Process(os.getpid())
        self.proc.cpu_percent(None)
        psutil.cpu_percent(None)
        self.latencies = collections.deque(maxlen=200)     # inference ms
        self.loop_ms = collections.deque(maxlen=200)       # full analysis step ms
        self.infer_times = collections.deque(maxlen=200)   # wall times of inferences
        self.counters = collections.Counter()
        self._lock = threading.Lock()
        self._cache = (0.0, {})

    def record(self, latency_ms: float | None, loop_ms: float) -> None:
        with self._lock:
            if latency_ms is not None:
                self.latencies.append(latency_ms)
                self.infer_times.append(time.time())
            self.loop_ms.append(loop_ms)

    def count(self, name: str, n: int = 1) -> None:
        self.counters[name] += n

    def snapshot(self) -> dict:
        now = time.time()
        if now - self._cache[0] < 1.0:
            return self._cache[1]
        with self._lock:
            lat = np.array(self.latencies) if self.latencies else None
            times = list(self.infer_times)
            loop = np.array(self.loop_ms) if self.loop_ms else None
        recent = [t for t in times if t > now - 60]
        vm = psutil.virtual_memory()
        snap = {
            "cpu_system_pct": psutil.cpu_percent(None),
            "cpu_process_pct": self.proc.cpu_percent(None),
            "cpu_count": psutil.cpu_count(),
            "ram_system_pct": vm.percent,
            "ram_system_used_mb": round((vm.total - vm.available) / 2**20),
            "ram_total_mb": round(vm.total / 2**20),
            "ram_process_mb": round(self.proc.memory_info().rss / 2**20, 1),
            "load_avg": [round(x, 2) for x in os.getloadavg()] if hasattr(os, "getloadavg") else None,
            "cpu_temp_c": cpu_temp(),
            "latency_ms_mean": None if lat is None else round(float(lat.mean()), 1),
            "latency_ms_p95": None if lat is None else round(float(np.percentile(lat, 95)), 1),
            "latency_ms_last": None if lat is None else round(float(lat[-1]), 1),
            "analysis_ms_mean": None if loop is None else round(float(loop.mean()), 1),
            "inferences_per_min": len(recent),
            "inference_fps": round(len(recent) / 60.0, 3),
            "counters": dict(self.counters),
        }
        self._cache = (now, snap)
        return snap


def cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        return None
    for key in ("cpu_thermal", "coretemp", "k10temp", "soc_thermal", "cpu-thermal"):
        if temps.get(key):
            return round(temps[key][0].current, 1)
    for entries in temps.values():
        if entries:
            return round(entries[0].current, 1)
    return None
