"""Key Exposure Window (KEW) and Exposed Attack Volume (EAV) — pure functions on the events_df produced by
src.sim.run_sim (src/sim/run_sim.py), so they are easy to unit test.

KEW = how long a compromised device's key STAYS VALID after compromise, measured from compromise onset to
the first key-invalidating event that scenario recognises (S1: ROTATE or REVOKE; S2: REVOKE only) —
regardless of whether the attacker happens to still be sending traffic at that moment. If no such event
occurs before the stream ends, the episode is right-censored at the stream's length (reported separately,
never silently averaged in as if it were a real detection).

EAV = how much actual attack TRAFFIC got through while the key was valid (sum of `delivered & label==1`
windows for that episode) — a related but distinct cost: a short KEW with a slow-starting attacker can
still have EAV = 0, and a long KEW with a quiet attacker is not very damaging either.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STOP_EVENTS = {"S1": {"ROTATE", "REVOKE"}, "S2": {"REVOKE"}}


def episodes_kew_eav(events: pd.DataFrame, windows_per_device: int, seconds_per_window: int) -> pd.DataFrame:
    """One row per (policy, scenario, seed, device_id) that has a compromise episode (episode_id >= 0)."""
    rows = []
    group_cols = ["policy", "scenario", "seed", "device_id"]
    for (policy, scenario, seed, device_id), g in events.groupby(group_cols, sort=False):
        g = g.sort_values("t")
        attack = g[g["label"] == 1]
        if attack.empty:
            continue   # this device had no episode in this stream
        onset_t = int(attack["t"].iloc[0])
        category, sublabel = attack["attack_cat"].iloc[0], attack["sublabel"].iloc[0]
        stop = STOP_EVENTS[scenario]
        after = g[g["t"] >= onset_t]
        hit = after[after["event"].isin(stop)]
        if len(hit):
            detection_t, censored = int(hit["t"].iloc[0]), False
        else:
            detection_t, censored = windows_per_device, True   # right-censored: key never invalidated in time
        eav_windows = int((attack["label"] == 1).sum() if False else (attack["delivered"] & (attack["label"] == 1)).sum())
        rows.append({
            "policy": policy, "scenario": scenario, "seed": int(seed), "device_id": device_id,
            "category": category, "sublabel": sublabel, "onset_t": onset_t, "detection_t": detection_t,
            "censored": censored, "kew_windows": detection_t - onset_t,
            "kew_seconds": (detection_t - onset_t) * seconds_per_window,
            "eav_windows": eav_windows, "episode_len_windows": int(len(attack)),
        })
    return pd.DataFrame(rows)
