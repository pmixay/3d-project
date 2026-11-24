from hercules.config import DecisionCfg
from hercules.temporal import FailureTracker, Persistent


def run(tr, series, dt):
    out = []
    t = 0.0
    for p in series:
        out.append(tr.update(t, p))
        t += dt
    return out


def cfg(**kw):
    c = DecisionCfg(warmup_s=0, **kw)
    return c


def test_smoothing_is_time_normalised():
    """Same physical signal analysed every 1 s or every 10 s -> similar ewm after 5 min."""
    a = run(FailureTracker(cfg()), [1.0] * 300, 1.0)[-1]
    b = run(FailureTracker(cfg()), [1.0] * 30, 10.0)[-1]
    assert abs(a.ewm - b.ewm) < 0.05


def test_quiet_print_never_alerts():
    res = run(FailureTracker(cfg()), [0.05, 0.1, 0.0, 0.15] * 300, 3.0)
    assert all(r.level == "ok" for r in res)
    assert not any(r.event for r in res)


def test_single_spike_at_long_interval_is_gated():
    """At 30 s per frame one frame with p=3 pushes the ewm over the threshold,
    but the evidence gate (>=3 positive frames) blocks the alert."""
    res = run(FailureTracker(cfg()), [0.0] * 5 + [3.0] + [0.0] * 10, 30.0)
    assert any(r.raw_level != "ok" for r in res)
    assert all(r.level == "ok" for r in res)


def test_sustained_failure_opens_then_escalates_once():
    res = run(FailureTracker(cfg()), [0.0] * 20 + [1.5] * 60, 3.0)
    events = [(r.event, r.level) for r in res if r.event]
    assert events[0] == ("open", "warning")
    assert events[1] == ("escalate", "critical")
    assert len(events) == 2      # no repeated alerts for the same incident


def test_incident_clears_after_hold():
    c = cfg(clear_hold_s=60)
    res = run(FailureTracker(c), [1.5] * 40 + [0.0] * 200, 3.0)
    ev = [r.event for r in res if r.event]
    assert ev[-1] == "close"
    assert not res[-1].incident_open


def test_warmup_blocks_alerts():
    c = DecisionCfg(warmup_s=120)
    res = run(FailureTracker(c), [2.0] * 30, 3.0)   # 90 s of strong signal, all in warm-up
    assert all(r.level == "ok" and r.warmup for r in res)


def test_dismiss_suppresses_then_rearms():
    c = cfg(dismiss_suppress_s=300)
    tr = FailureTracker(c)
    res = run(tr, [1.5] * 30, 3.0)
    assert any(r.event == "open" for r in res)
    tr.dismiss(90.0)
    t = 93.0
    outs = []
    for _ in range(200):           # 600 s of continuing signal
        outs.append(tr.update(t, 1.5))
        t += 3.0
    first = next(o for o in outs if o.event == "open")
    assert first.t >= 90.0 + 300   # nothing during suppression, alert again afterwards


def test_baseline_absorbs_constant_background_but_not_failures():
    c = cfg(baseline_tau_s=600)
    tr = FailureTracker(c)
    res = run(tr, [0.15] * 400, 3.0)    # textured scene: constant small p
    assert res[-1].baseline > 0.1 and res[-1].score < 0.05
    res = run(tr, [1.5] * 60, 3.0)
    assert any(r.event == "open" for r in res)
    frozen = tr.baseline
    run(tr, [1.5] * 100, 3.0)
    assert tr.baseline == frozen         # frozen while the incident is open


def test_persistent_condition():
    pc = Persistent(after_s=10, clear_s=5)
    assert pc.update(0, True) is None
    assert pc.update(9, True) is None
    assert pc.update(10, True) == "open"
    assert pc.update(11, True) is None
    assert pc.update(12, False) is None
    assert pc.update(17, False) == "close"
