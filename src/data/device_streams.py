"""Turn flow rows into per-device window streams with compromise episodes and ground truth.

Method (state this in the report): CICIoT2023 has no device IDs or timestamps, so devices and time are SIMULATED:
benign flows are dealt to virtual devices, 1 window = W flows = `seconds_per_window` simulated seconds, and attack
episodes are injected at known times from a held-out pool of attack flows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.schema import BENIGN, BENIGN_CAT

_STAT_FUNCS = {
    "mean": lambda a: a.mean(axis=1),
    "std": lambda a: a.std(axis=1),
    "max": lambda a: a.max(axis=1),
    "min": lambda a: a.min(axis=1),
}


def window_columns(features: list[str], stats: list[str]) -> list[str]:
    return [f"{f}__{s}" for s in stats for f in features]


def window_features(flows: np.ndarray, stats: list[str]) -> np.ndarray:
    """flows: (T, W, K) -> (T, len(stats) * K) float32"""
    return np.concatenate([_STAT_FUNCS[s](flows) for s in stats], axis=1).astype(np.float32)


def draw(pool: np.ndarray, n: int, rng: np.random.Generator) -> tuple[np.ndarray, float]:
    """Draw n rows without replacement; if the pool is too small, reuse rows (permutation cycles).
    Returns (rows, reuse_factor) so reuse is always visible in the build report."""
    m = len(pool)
    if m == 0:
        raise ValueError("cannot draw from an empty pool")
    reps = int(np.ceil(n / m))
    idx = np.concatenate([rng.permutation(m) for _ in range(reps)])[:n]
    return pool[idx], float(max(1.0, n / m))


def split_device_counts(n_devices: int, ratios: list[float]) -> dict[str, int]:
    n_train = max(1, int(round(n_devices * ratios[0])))
    n_val = max(1, int(round(n_devices * ratios[1])))
    n_test = n_devices - n_train - n_val
    if n_test < 1:
        raise ValueError("n_devices too small for the split ratios")
    return {"train": n_train, "val": n_val, "test": n_test}


def check_stream_config(s: dict) -> None:
    lo, hi = s["episode_len_windows"]
    if s["min_start_window"] + hi + s["end_margin_windows"] > s["windows_per_device"]:
        raise ValueError("windows_per_device is too small for min_start_window + episode length + end_margin_windows")


def build_split_streams(split: str, features: list[str], benign_pool: np.ndarray, attack_pools: dict,
                        n_dev: int, dev_start: int, s: dict, rng: np.random.Generator, seed: int,
                        compromised_fraction: float) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """attack_pools: {sublabel: (category, array(n, K))}. Returns (stream_df, ground_truth_df, info)."""
    check_stream_config(s)
    T, W, stats = s["windows_per_device"], s["flows_per_window"], s["window_stats"]
    sec = s["seconds_per_window"]
    lo, hi = s["episode_len_windows"]
    min_start, margin = s["min_start_window"], s["end_margin_windows"]
    K = benign_pool.shape[1]
    cols = window_columns(features, stats)

    benign_flows, reuse_b = draw(benign_pool, n_dev * T * W, rng)
    benign_flows = benign_flows.reshape(n_dev, T, W, K)

    n_comp = int(round(compromised_fraction * n_dev))
    comp = set(rng.choice(n_dev, size=n_comp, replace=False).tolist()) if n_comp else set()
    sub_names = sorted(attack_pools)
    if n_comp and not sub_names:
        raise ValueError(f"No eligible attack labels in split '{split}' (check min_pool_rows / attack_categories)")

    frames, gts, ep_id, reuse_att = [], [], 0, []
    for d in range(n_dev):
        X = window_features(benign_flows[d], stats)
        y = np.zeros(T, dtype=np.int8)
        cat = np.full(T, BENIGN_CAT, dtype=object)
        sub = np.full(T, BENIGN, dtype=object)
        ep = np.full(T, -1, dtype=np.int32)
        dev_id = f"dev_{dev_start + d:03d}"
        if d in comp:
            L = int(rng.integers(lo, hi + 1))
            start = int(rng.integers(min_start, T - L - margin + 1))
            name = sub_names[int(rng.integers(len(sub_names)))]
            category, pool = attack_pools[name]
            fl, reuse_a = draw(pool, L * W, rng)
            reuse_att.append(reuse_a)
            X[start:start + L] = window_features(fl.reshape(L, W, K), stats)
            y[start:start + L] = 1
            cat[start:start + L] = category
            sub[start:start + L] = name
            ep[start:start + L] = ep_id
            gts.append({"episode_id": ep_id, "device_id": dev_id, "split": split, "seed": seed,
                        "start_t": start, "end_t": start + L, "n_windows": L, "start_ts": start * sec,
                        "category": category, "sublabel": name, "reuse_factor": round(reuse_a, 3)})
            ep_id += 1
        t = np.arange(T)
        meta = pd.DataFrame({"device_id": dev_id, "t": t, "ts": t * sec, "label": y, "category": cat,
                             "sublabel": sub, "episode_id": ep})
        frames.append(pd.concat([meta, pd.DataFrame(X, columns=cols)], axis=1))

    stream = pd.concat(frames, ignore_index=True)
    gt = pd.DataFrame(gts, columns=["episode_id", "device_id", "split", "seed", "start_t", "end_t", "n_windows",
                                    "start_ts", "category", "sublabel", "reuse_factor"])
    info = {"n_devices": n_dev, "n_episodes": len(gts), "benign_reuse_factor": round(reuse_b, 3),
            "attack_reuse_factor_max": round(max(reuse_att), 3) if reuse_att else 1.0}
    return stream, gt, info
