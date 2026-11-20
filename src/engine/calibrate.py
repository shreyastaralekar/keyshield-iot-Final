"""Calibrate warn/rotate/revoke score levels from BENIGN validation windows only (never test data).

Run:  python -m src.engine.calibrate
Output: data/processed/thresholds.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import load_config, resolve_path


def compute_thresholds(benign_scores: np.ndarray, quantiles: dict, min_revoke_margin: float = 1.05) -> dict:
    """Pure function (no file IO) so it's easy to unit test."""
    benign_scores = np.asarray(benign_scores, dtype=float)
    warn = float(np.quantile(benign_scores, quantiles["warn"]))
    rotate = float(np.quantile(benign_scores, quantiles["rotate"]))
    rotate = max(rotate, warn)
    revoke = float(np.quantile(benign_scores, quantiles["revoke"]))
    revoke = max(revoke, rotate * min_revoke_margin)
    return {"warn": warn, "rotate": rotate, "revoke": revoke, "n_benign_windows": int(len(benign_scores))}


def run(cfg: dict, ecfg: dict, proc: Path | None = None) -> dict:
    proc = Path(proc) if proc else resolve_path(cfg, "processed")
    seed = cfg["seeds"][ecfg["calibration"]["seed_index"]]
    col = f"score_{ecfg['live_model']}"
    val = pd.read_parquet(proc / f"scores_val_s{seed}.parquet")
    benign = val.loc[val["label"] == 0, col].to_numpy()
    levels = compute_thresholds(benign, ecfg["calibration"]["quantiles"], ecfg["calibration"]["min_revoke_margin"])
    out = {"live_model": ecfg["live_model"], "calibration_seed": int(seed), **levels}
    (proc / "thresholds.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--engine-config", default="configs/engine.yaml")
    args = ap.parse_args()
    run(load_config(args.config), load_config(args.engine_config))


if __name__ == "__main__":
    main()
