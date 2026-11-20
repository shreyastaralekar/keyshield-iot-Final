"""Cost metrics: how much the policy's own activity costs, independent of how well it detects anything.
Pure functions on events_df (and, for crypto cost, a handshake time in milliseconds from Batch 3's own
benchmark) — this is what keeps a policy honest: catching every attack by rotating every window is free
in the KEW/EAV numbers alone, but shows up here as an absurd rotation rate and overhead cost.
"""
from __future__ import annotations

import pandas as pd


def per_run_cost(events: pd.DataFrame, n_devices: int, windows_per_device: int, seconds_per_window: int,
                 handshake_ms: float, revoke_also_handshakes: bool = True) -> pd.DataFrame:
    """One row per (policy, scenario, seed)."""
    device_hours = n_devices * windows_per_device * seconds_per_window / 3600.0
    rows = []
    for (policy, scenario, seed), g in events.groupby(["policy", "scenario", "seed"], sort=False):
        n_rot = int((g["event"] == "ROTATE").sum())
        n_rev = int((g["event"] == "REVOKE").sum())
        n_rot_benign = int(((g["event"] == "ROTATE") & (g["label"] == 0)).sum())
        n_rev_benign = int(((g["event"] == "REVOKE") & (g["label"] == 0)).sum())
        key_events = n_rot + (n_rev if revoke_also_handshakes else 0)
        rows.append({
            "policy": policy, "scenario": scenario, "seed": int(seed),
            "rotations": n_rot, "revokes": n_rev,
            "rotations_per_device_hour": n_rot / device_hours,
            "false_rotation_rate": n_rot_benign / n_rot if n_rot else float("nan"),
            "false_revoke_rate": n_rev_benign / n_rev if n_rev else float("nan"),
            "crypto_overhead_ms_total": key_events * handshake_ms,
            "crypto_overhead_ms_per_device_hour": key_events * handshake_ms / device_hours,
        })
    return pd.DataFrame(rows)


def load_handshake_ms(benchmark_csv, default_ms: float) -> float:
    """Reads the user's own report/tables/crypto_benchmark.csv (Batch 3) if present; falls back otherwise."""
    try:
        df = pd.read_csv(benchmark_csv)
        row = df[df["operation"].str.contains("handshake", case=False, na=False)]
        if len(row):
            return float(row["mean_ms"].iloc[0])
    except (FileNotFoundError, OSError, KeyError):
        pass
    return default_ms
