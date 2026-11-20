"""Batch 6 tests: KEW/EAV correctness (pure-function level) + the E3 report end to end on the small fixture.
The key cross-check: a policy that NEVER revokes (fixed-interval) must show 0% detection under Scenario S2
(device compromise) — that contrast is the entire point of running both scenarios."""
import numpy as np
import pandas as pd
import pytest

from src.eval import e3_report
from src.eval.cost import load_handshake_ms, per_run_cost
from src.eval.kew import episodes_kew_eav
from src.sim.run_sim import run_all
from tests.helpers import make_small_ecfg


def _toy_device(events, policy, scenario, seed, device_id, t_range, onset, stop_t, stop_event, category="DDoS"):
    for t in t_range:
        label = 1 if onset <= t < onset + 4 else 0
        event = stop_event if t == stop_t else "WINDOW"
        delivered = not (label == 1 and stop_t is not None and t >= stop_t)
        events.append({"policy": policy, "scenario": scenario, "seed": seed, "device_id": device_id, "t": t,
                       "event": event, "label": label, "attack_cat": category if label else "Benign",
                       "sublabel": "X", "delivered": delivered, "episode_id": 0 if label else -1})


def test_kew_eav_hand_built_cases():
    rows = []
    _toy_device(rows, "ai", "S1", 1, "d_detected", range(20), onset=5, stop_t=8, stop_event="ROTATE")
    _toy_device(rows, "ai", "S2", 1, "d_censored", range(20), onset=5, stop_t=None, stop_event="ROTATE")
    df = pd.DataFrame(rows)
    out = episodes_kew_eav(df, windows_per_device=20, seconds_per_window=60)
    a = out[out.device_id == "d_detected"].iloc[0]
    assert not a.censored and a.kew_windows == 3 and a.kew_seconds == 180
    b = out[out.device_id == "d_censored"].iloc[0]
    assert b.censored and b.kew_windows == 15   # right-censored at stream end (20 - onset 5)


def test_cost_metrics_and_handshake_fallback(tmp_path):
    rows = [{"policy": "ai", "scenario": "S1", "seed": 1, "t": t,
            "event": "ROTATE" if t % 4 == 0 else "WINDOW", "label": 1 if t % 4 == 0 else 0} for t in range(12)]
    df = pd.DataFrame(rows)
    out = per_run_cost(df, n_devices=1, windows_per_device=12, seconds_per_window=60, handshake_ms=0.5)
    row = out.iloc[0]
    assert row.rotations == 3 and row.false_rotation_rate == 0.0   # every rotate happened on an attack window
    assert load_handshake_ms(tmp_path / "missing.csv", default_ms=0.42) == 0.42


def test_e3_report_end_to_end_small_fixture(trained):
    cfg, mcfg, ecfg, proc, base, levels = trained
    events = run_all(cfg, ecfg, proc, scenarios=("S1", "S2"), save=True)
    assert len(events) > 0

    ev_cfg = {"cost": {"default_handshake_ms": 0.3, "revoke_also_handshakes": True},
             "output": {"tables_dir": str(base / "e3tabs"), "figures_dir": str(base / "e3figs")}}
    res = e3_report.run(cfg, ev_cfg, proc=proc)

    e3a = res["kew_eav_by_policy"]
    assert {"Policy", "Scenario", "Mean KEW (s)", "Mean EAV (windows)", "Detection rate"} <= set(e3a.columns)
    assert (e3a["Detection rate"].astype(float) >= 0).all() and (e3a["Detection rate"].astype(float) <= 1).all()

    # the core cross-scenario finding: fixed-interval policies NEVER revoke -> 0% detection under S2
    fixed_rows = e3a[e3a["Policy"].str.startswith("Fixed interval") & (e3a["Scenario"] == "S2")]
    assert len(fixed_rows) > 0
    assert (fixed_rows["Detection rate"].astype(float) == 0.0).all()

    for f in ("e3_kew_eav_by_policy.csv", "e3_cost_by_policy.csv", "e3_kew_eav_by_category.csv",
             "e3_failure_highlights.md"):
        assert (base / "e3tabs" / f).exists()
    for f in ("e3_kew_boxplot.png", "e3_eav_bar.png", "e3_cost_bar.png"):
        assert (base / "e3figs" / f).exists()

    cost = res["cost_by_policy"]
    assert (cost["Policy"] == "AI (adaptive)").any()
