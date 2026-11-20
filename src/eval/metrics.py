"""Detection metrics. A window is flagged when score >= threshold."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score


def threshold_at_benign_quantile(benign_scores, q: float = 0.99) -> float:
    """Alarm threshold = q-quantile of BENIGN validation scores (never uses test data)."""
    return float(np.quantile(np.asarray(benign_scores, dtype=float), q))


def best_f1_threshold(y, s) -> float:
    p, r, t = precision_recall_curve(y, s)
    f1 = 2 * p[:-1] * r[:-1] / (p[:-1] + r[:-1] + 1e-12)
    return float(t[int(np.argmax(f1))])


def auc_metrics(y, s) -> dict:
    y = np.asarray(y)
    if y.min() == y.max():
        return {"roc_auc": float("nan"), "pr_auc": float("nan")}
    return {"roc_auc": float(roc_auc_score(y, s)), "pr_auc": float(average_precision_score(y, s))}


def classification_metrics(y, s, thr: float) -> dict:
    y = np.asarray(y).astype(int)
    pred = (np.asarray(s) >= thr).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum()); fp = int(((pred == 1) & (y == 0)).sum())
    tn = int(((pred == 0) & (y == 0)).sum()); fn = int(((pred == 0) & (y == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "fpr": fpr, "tp": tp, "fp": fp, "tn": tn, "fn": fn}


def episode_detection(df: pd.DataFrame, score_col: str, thr: float) -> dict:
    """Per compromise episode: was at least one window flagged, and after how many windows (detection delay)."""
    flagged = (df[score_col] >= thr).to_numpy()
    detected, delays = [], []
    for _, g in df[df["episode_id"] >= 0].groupby(["device_id", "episode_id"]):
        g = g.sort_values("t")
        fl = flagged[df.index.get_indexer(g.index)]
        detected.append(bool(fl.any()))
        if fl.any():
            delays.append(int(np.argmax(fl)))
    n = len(detected)
    return {"episodes": n, "episode_detect_rate": float(np.mean(detected)) if n else float("nan"),
            "median_delay_windows": float(np.median(delays)) if delays else float("nan")}
