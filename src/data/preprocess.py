"""Row splitting, transforms and feature selection. Everything that learns from data is fitted on TRAIN only."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from src.data.schema import BENIGN, LABEL_COL


def signed_log1p(a: np.ndarray) -> np.ndarray:
    """Tames heavy-tailed features (e.g. IAT, Tot sum) while keeping the sign."""
    return np.sign(a) * np.log1p(np.abs(a))


def assign_splits(df: pd.DataFrame, ratios: list[float], seed: int) -> np.ndarray:
    """Stratified (per label) train/val/test assignment of rows. Rows never appear in two splits."""
    rng = np.random.default_rng(seed)
    split = np.empty(len(df), dtype=object)
    for _, idx in df.groupby(LABEL_COL).indices.items():
        idx = rng.permutation(idx)
        n = len(idx)
        n_tr = int(round(n * ratios[0]))
        n_va = int(round(n * ratios[1]))
        split[idx[:n_tr]] = "train"
        split[idx[n_tr:n_tr + n_va]] = "val"
        split[idx[n_tr + n_va:]] = "test"
    return split


def select_features(train_df: pd.DataFrame, features: list[str], top_k: int, corr_threshold: float,
                    importance_sample: int, seed: int) -> tuple[list[str], dict]:
    """Variance filter -> correlation filter -> Random Forest importance (benign vs attack), on TRAIN rows only.

    The binary label is used ONLY to rank features (documented in the report); the detectors themselves
    are trained on benign windows.
    """
    benign = train_df[train_df[LABEL_COL] == BENIGN]
    attack = train_df[train_df[LABEL_COL] != BENIGN]
    n_b = min(len(benign), importance_sample // 2)
    n_a = min(len(attack), importance_sample - n_b)
    sample = pd.concat([benign.sample(n_b, random_state=seed), attack.sample(n_a, random_state=seed)])
    X = signed_log1p(sample[features].to_numpy(np.float64))
    y = (sample[LABEL_COL] != BENIGN).to_numpy().astype(int)

    # 1) constant / near-constant columns
    var = X.var(axis=0)
    keep = [i for i in range(len(features)) if var[i] > 1e-12]
    dropped_constant = [features[i] for i in range(len(features)) if i not in keep]

    # 2) highly correlated columns (greedy: keep the first of every correlated pair)
    corr = np.abs(np.corrcoef(X[:, keep], rowvar=False))
    corr = np.nan_to_num(corr)
    kept: list[int] = []
    dropped_corr: list[str] = []
    for a in range(len(keep)):
        if any(corr[a, b] > corr_threshold for b in kept):
            dropped_corr.append(features[keep[a]])
        else:
            kept.append(a)
    cand = [keep[a] for a in kept]

    # 3) Random Forest importance, keep top_k
    rf = RandomForestClassifier(n_estimators=100, max_depth=12, min_samples_leaf=5, n_jobs=-1,
                                class_weight="balanced", random_state=seed)
    rf.fit(X[:, cand], y)
    order = np.argsort(-rf.feature_importances_)
    top = [cand[i] for i in order[:top_k]]
    selected = [features[i] for i in top]
    importances = {features[cand[i]]: float(rf.feature_importances_[i]) for i in order}
    info = {
        "n_start": len(features), "dropped_constant": dropped_constant, "dropped_correlated": dropped_corr,
        "n_after_filters": len(cand), "importances": importances, "selected": selected,
        "sample_rows": int(len(sample)),
    }
    return selected, info
