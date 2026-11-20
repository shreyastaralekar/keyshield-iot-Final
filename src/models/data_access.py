"""Helpers to read the Batch 1 outputs (streams, features, scaler, pools)."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.data.device_streams import draw, window_features
from src.data.preprocess import signed_log1p
from src.data.schema import BENIGN

META_COLS = ["device_id", "t", "ts", "label", "category", "sublabel", "episode_id"]


def load_features(proc: Path) -> dict:
    return json.loads((Path(proc) / "features.json").read_text())


def stream_path(proc: Path, split: str, seed: int | None = None) -> Path:
    name = "streams_train.parquet" if split == "train" else f"streams_{split}_s{seed}.parquet"
    return Path(proc) / name


def load_stream(proc: Path, split: str, seed: int | None = None) -> pd.DataFrame:
    return pd.read_parquet(stream_path(proc, split, seed))


def benign_train_matrix(proc: Path) -> np.ndarray:
    cols = load_features(proc)["window_columns"]
    st = load_stream(proc, "train")
    return st.loc[st["label"] == 0, cols].to_numpy(np.float32)


def supervised_train(cfg: dict, proc: Path, windows_per_label: int = 100, seed: int = 42,
                     exclude_categories: tuple = ()) -> tuple[np.ndarray, np.ndarray]:
    """Labelled training set for the supervised reference: benign TRAIN windows + attack windows built from the
    TRAIN pool (every eligible attack label). Same transforms and scaler as the streams. Test rows are never used."""
    proc = Path(proc)
    feat = load_features(proc)
    flow_feats, stats, W = feat["flow_features"], feat["window_stats"], feat["flows_per_window"]
    scaler = joblib.load(proc / "scaler.joblib")
    s = cfg["streams"]
    pools = pd.read_parquet(proc / "pools_train.parquet")
    pools = pools[pools["Label"] != BENIGN]
    rng = np.random.default_rng([seed, 99])
    Xb = benign_train_matrix(proc)
    parts = [Xb]
    for lab, grp in pools.groupby("Label"):
        cat = grp["category"].iloc[0]
        if cat not in s["attack_categories"] or cat in exclude_categories or len(grp) < s["min_pool_rows"]:
            continue
        arr = signed_log1p(grp[flow_feats].to_numpy(np.float64)).astype(np.float32)
        fl, _ = draw(arr, windows_per_label * W, rng)
        xw = window_features(fl.reshape(windows_per_label, W, len(flow_feats)), stats)
        parts.append(scaler.transform(xw).astype(np.float32))
    Xa = np.vstack(parts[1:]) if len(parts) > 1 else np.empty((0, Xb.shape[1]), np.float32)
    X = np.vstack([Xb, Xa])
    y = np.concatenate([np.zeros(len(Xb), int), np.ones(len(Xa), int)])
    return X, y
