#!/usr/bin/env python3
"""Print the Markdown tables of docs/EVALUATION.md from docs/results/*.json,
so no number in the document is typed by hand."""
import glob
import json
import os
import sys

R = sys.argv[1] if len(sys.argv) > 1 else "docs/results"


def load(name):
    p = os.path.join(R, name)
    return json.load(open(p)) if os.path.exists(p) else None


def fmt_list(xs):
    return ", ".join(f"{x:.0f}" for x in xs) if xs else "—"


def sweep(name, title):
    d = load(name)
    if not d:
        return
    print(f"\n#### {title}\n")
    print("| Interval, s | Detected | Latency from first strand, s | from 'obvious', s | Critical (pause) latency, s | False alarms | FA / print hour |")
    print("| ---: | :---: | :--- | :--- | :--- | ---: | ---: |")
    for r in d["runs"]:
        s = r["summary"]
        print(f"| {r['interval_s']} | {s['detected']}/{s['target_sessions']} | {fmt_list(s['latency_s'])} | "
              f"{fmt_list(s['latency_from_obvious_s'])} | {fmt_list(s['critical_latency_s'])} | {s['false_alarms']} | "
              f"{s['false_alarms_per_print_hour']} |")


def per_session(name, interval):
    d = load(name)
    run = next(r for r in d["runs"] if r["interval_s"] == interval)
    print(f"\n| Session | Kind | Length, min | Onset, min | Frames analysed | False alarms | Detected | Latency, s | Critical, s | Max score before onset | Max score after onset |")
    print("| :--- | :--- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: |")
    for n, v in run["sessions"].items():
        after = v["max_score_after_onset"]
        lat = "—" if v["latency_s"] is None else v["latency_s"]
        crit = "—" if v["critical_latency_s"] is None else v["critical_latency_s"]
        print(f"| {n.replace('test_', '').replace('_print', '')} | {v['kind']} | {v['duration_min']} | "
              f"{v['onset_min'] or '—'} | {v['frames_analysed']} | {v['false_alarms']} | "
              f"{'yes' if v['detected'] else 'no'} | {lat} | {crit} | {v['max_score_normal']:.2f} | "
              f"{'—' if after is None else f'{after:.2f}'} |")
    s = run["summary"]
    print(f"\nSession precision {s['session_precision']}, recall {s['session_recall']}, F1 {s['session_f1']} "
          f"(spaghetti sessions = positives; any session with a false alarm = a false positive). "
          f"Normal printing time: {s['normal_print_hours']} h.")


def frame_level(name):
    d = load(name)
    fl = d["frame_level"]
    print(f"\nFrames: {fl['frames']} ({fl['positives']} after a spaghetti onset).\n")
    print("| Frame score threshold | Precision | Recall | F1 | False-positive rate |")
    print("| ---: | ---: | ---: | ---: | ---: |")
    for thr, m in fl["by_threshold"].items():
        print(f"| p ≥ {thr} | {m['precision']} | {m['recall']} | {m['f1']} | {m['fp_rate']} |")


def compare():
    rows = [("Hercules (ours), τ=60 s, gate 3", "eval_hercules.json"), ("Obico original (frame-count EWM)", "eval_obico.json"),
            ("Naive: alert on any frame p ≥ 0.38", "eval_naive.json"), ("Ours, τ=30 s", "eval_tau30.json"),
            ("Ours, τ=120 s", "eval_tau120.json"), ("Ours, evidence gate off", "eval_gate1.json"),
            ("Ours, warning 0.25 instead of 0.38", "eval_warn025.json"), ("Ours, INT8 model", "eval_int8.json")]
    print("\n| Engine / setting | Interval, s | Detected | Latency, s | Critical, s | False alarms (FA/h) | Non-target alerts |")
    print("| :--- | ---: | :---: | :--- | :--- | :--- | :---: |")
    for label, f in rows:
        d = load(f)
        if not d:
            continue
        for r in d["runs"]:
            if r["interval_s"] not in (3.0, 12.0, 24.0):
                continue
            s = r["summary"]
            print(f"| {label} | {r['interval_s']} | {s['detected']}/{s['target_sessions']} | {fmt_list(s['latency_s'])} | "
                  f"{fmt_list(s['critical_latency_s'])} | {s['false_alarms']} ({s['false_alarms_per_print_hour']}) | "
                  f"{s['non_target_failures_alerted']}/{s['non_target_failure_sessions']} |")


def perturb():
    base = load("eval_perturb_none.json")
    if not base:
        return
    print("\n| Condition | Detected | Latency, s | False alarms | Frames not sent to the network (unusable / blurred / unchanged) | Max score after onset (per session) |")
    print("| :--- | :---: | :--- | ---: | ---: | :--- |")
    for k in ["none", "dark", "noise", "blur", "occlusion"]:
        d = load(f"eval_perturb_{k}.json")
        if not d:
            continue
        r = d["runs"][0]
        s = r["summary"]
        tgt = [v for v in r["sessions"].values() if v["kind"] == "spaghetti"]
        skipped = sum(v["frames_analysed"] - v["inferences"] for v in r["sessions"].values())
        mx = ", ".join(f"{v['max_score_after_onset']:.2f}" for v in tgt)
        print(f"| {k} | {s['detected']}/{s['target_sessions']} | {fmt_list(s['latency_s'])} | {s['false_alarms']} | {skipped} | {mx} |")


def bench():
    for p in sorted(glob.glob(os.path.join(R, "benchmark_*.json"))):
        d = json.load(open(p))
        h = d["host"]
        print(f"\n#### {os.path.basename(p)}: {h['cpu']}, {h['cores']} logical cores, {h['ram_mb']} MB RAM, "
              f"{h['machine']}, ONNX Runtime {h['onnxruntime']}, OpenCV {h['opencv']}\n")
        if d.get("model"):
            print("| Model | Backend | Threads | Median, ms | p95, ms | Load, s | Process RAM, MB |")
            print("| :--- | :--- | ---: | ---: | ---: | ---: | ---: |")
            for m in d["model"]:
                if "error" in m:
                    print(f"| {m['model']} | {m['backend']} | {m['threads']} | error: {m['error'][:60]} | | | |")
                    continue
                print(f"| {m['model']} | {m['backend']} | {m['threads']} | {m['median_ms']} | {m['p95_ms']} | {m['load_s']} | {m['rss_mb']} |")
        if d.get("resolution"):
            print("\n| Camera frame | Full analysis step, ms | of which inference, ms | Validation + resize + decision, ms |")
            print("| :--- | ---: | ---: | ---: |")
            for x in d["resolution"]:
                print(f"| {x['resolution']} | {x['step_median_ms']} | {x['inference_median_ms']} | {x['overhead_median_ms']} |")
        if d.get("sustained"):
            print("\n| Interval, s | Analyses | Process CPU, % of one core | Process CPU, % of machine | System CPU, % | Peak RAM, MB |")
            print("| ---: | ---: | ---: | ---: | ---: | ---: |")
            for x in d["sustained"]:
                print(f"| {x['interval_s']} | {x['analyses']} | {x['process_cpu_pct_of_one_core']} | "
                      f"{x['process_cpu_pct_of_machine']} | {x['system_cpu_pct']} | {x['peak_rss_mb']} |")


if __name__ == "__main__":
    print("### Per session (3 s interval)")
    per_session("eval_hercules.json", 3.0)
    sweep("eval_hercules.json", "Inference interval sweep — our engine")
    sweep("eval_obico.json", "Inference interval sweep — Obico's original frame-count scheme")
    print("\n### Comparison")
    compare()
    print("\n### Frame level")
    frame_level("eval_hercules.json")
    print("\n### Robustness")
    perturb()
    print("\n### Benchmarks")
    bench()
