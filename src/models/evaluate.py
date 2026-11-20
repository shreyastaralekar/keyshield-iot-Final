"""E1 (model comparison) and first part of E2 (per-category recall).

Run:  python -m src.models.evaluate
Thresholds are chosen on VALIDATION scores only; all reported numbers are on TEST streams (mean +- std over seeds).
Outputs: report/tables/e1_model_comparison.{csv,md}, e2_category_recall.{csv,md}, e2_sublabel_recall.csv,
         report/figures/e1_roc.png, e1_pr.png, e2_category_recall.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve

from src.config import ROOT, load_config, resolve_path
from src.eval.metrics import (auc_metrics, best_f1_threshold, classification_metrics, episode_detection,
                              threshold_at_benign_quantile)

LABELS = {"iforest": "Isolation Forest", "ocsvm": "One-Class SVM", "ae": "Autoencoder", "rf": "Random Forest (supervised ref.)"}


def to_markdown(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.tolist()) + " |")
    return "\n".join(lines) + "\n"


def pm(values, nd=3) -> str:
    v = np.asarray(values, dtype=float)
    return f"{np.nanmean(v):.{nd}f} ± {np.nanstd(v):.{nd}f}"


def _dir(cfg_value: str) -> Path:
    p = Path(cfg_value)
    return p if p.is_absolute() else ROOT / p


def run(cfg: dict, mcfg: dict, proc: Path | None = None, figures_dir: Path | None = None,
        tables_dir: Path | None = None) -> dict:
    proc = Path(proc) if proc else resolve_path(cfg, "processed")
    ev = mcfg["evaluation"]
    figs = Path(figures_dir) if figures_dir else _dir(ev["figures_dir"])
    tabs = Path(tables_dir) if tables_dir else _dir(ev["tables_dir"])
    figs.mkdir(parents=True, exist_ok=True); tabs.mkdir(parents=True, exist_ok=True)
    seeds, q = cfg["seeds"], ev["threshold_quantile"]
    val = {sd: pd.read_parquet(proc / f"scores_val_s{sd}.parquet") for sd in seeds}
    test = {sd: pd.read_parquet(proc / f"scores_test_s{sd}.parquet") for sd in seeds}
    models = [m for m in mcfg["models"] if f"score_{m}" in test[seeds[0]].columns]
    tr_report = json.loads((proc / "train_report.json").read_text()) if (proc / "train_report.json").exists() else {"models": {}}

    rows, cat_parts, curves = [], [], {}
    for m in models:
        col = f"score_{m}"
        per_seed = []
        ys, ss = [], []
        for sd in seeds:
            v, t = val[sd], test[sd]
            thr99 = threshold_at_benign_quantile(v.loc[v["label"] == 0, col], q)
            thrf1 = best_f1_threshold(v["label"], v[col])
            auc = auc_metrics(t["label"], t[col])
            m99 = classification_metrics(t["label"], t[col], thr99)
            mf1 = classification_metrics(t["label"], t[col], thrf1)
            epd = episode_detection(t, col, thr99)
            per_seed.append({**auc, **{f"q_{k}": x for k, x in m99.items()}, **{f"bf1_{k}": x for k, x in mf1.items()},
                             **epd})
            ys.append(t["label"].to_numpy()); ss.append(t[col].to_numpy())
            tt = t[["category", "sublabel", "label"]].copy()
            tt["flag"] = (t[col] >= thr99).astype(int); tt["model"] = m; tt["seed"] = sd
            cat_parts.append(tt[tt["label"] == 1])
        curves[m] = (np.concatenate(ys), np.concatenate(ss))
        g = lambda k: [d[k] for d in per_seed]
        trm = tr_report["models"].get(m, {})
        rows.append({
            "Model": LABELS.get(m, m), "ROC-AUC": pm(g("roc_auc")), "PR-AUC": pm(g("pr_auc")),
            f"Precision@q{int(q * 100)}": pm(g("q_precision")), f"Recall@q{int(q * 100)}": pm(g("q_recall")),
            f"F1@q{int(q * 100)}": pm(g("q_f1")), f"FPR@q{int(q * 100)}": pm(g("q_fpr")),
            "F1 (best on val)": pm(g("bf1_f1")), "Episode detect rate": pm(g("episode_detect_rate")),
            "Median delay (windows)": pm(g("median_delay_windows"), 1),
            "Train time (s)": trm.get("fit_seconds", ""), "Inference (ms/1000 windows)": trm.get("inference_ms_per_1000_windows", ""),
        })
    e1 = pd.DataFrame(rows)
    e1.to_csv(tabs / "e1_model_comparison.csv", index=False)
    (tabs / "e1_model_comparison.md").write_text(to_markdown(e1))

    # E2 (part): recall per attack category and per sublabel at the validation-chosen threshold
    allc = pd.concat(cat_parts, ignore_index=True)
    cat = allc.groupby(["model", "category"])["flag"].agg(recall="mean", windows="size").reset_index()
    cat_pivot = cat.pivot(index="category", columns="model", values="recall").reindex(columns=models)
    cat_pivot.columns = [LABELS.get(c, c) for c in cat_pivot.columns]
    counts = allc[allc["model"] == models[0]].groupby("category").size().rename("attack windows (all seeds)")
    e2 = cat_pivot.join(counts).reset_index().round(3)
    e2.to_csv(tabs / "e2_category_recall.csv", index=False)
    (tabs / "e2_category_recall.md").write_text(to_markdown(e2))
    sub = allc.groupby(["sublabel", "model"])["flag"].mean().unstack("model").reindex(columns=models).round(3)
    sub.join(allc[allc["model"] == models[0]].groupby("sublabel").size().rename("windows")).to_csv(tabs / "e2_sublabel_recall.csv")

    # figures
    fig, ax = plt.subplots(figsize=(6, 5))
    for m, (y, s) in curves.items():
        fpr, tpr, _ = roc_curve(y, s); ax.plot(fpr, tpr, label=LABELS.get(m, m))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8); ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("ROC curves (test windows, all seeds)"); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(figs / "e1_roc.png", dpi=300); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    for m, (y, s) in curves.items():
        p, r, _ = precision_recall_curve(y, s); ax.plot(r, p, label=LABELS.get(m, m))
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision"); ax.set_title("Precision-recall curves (test windows)")
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(figs / "e1_pr.png", dpi=300); plt.close(fig)

    hm = cat_pivot.to_numpy()
    fig, ax = plt.subplots(figsize=(1.6 * hm.shape[1] + 2, 0.55 * hm.shape[0] + 1.5))
    im = ax.imshow(hm, vmin=0, vmax=1, cmap="viridis", aspect="auto")
    ax.set_xticks(range(hm.shape[1])); ax.set_xticklabels(cat_pivot.columns, rotation=25, ha="right", fontsize=8)
    ax.set_yticks(range(hm.shape[0])); ax.set_yticklabels(cat_pivot.index)
    for i in range(hm.shape[0]):
        for j in range(hm.shape[1]):
            ax.text(j, i, f"{hm[i, j]:.2f}", ha="center", va="center", color="w" if hm[i, j] < 0.6 else "k", fontsize=8)
    ax.set_title("Recall per attack category (threshold = 99th pct of benign val scores)"); fig.colorbar(im, ax=ax)
    fig.tight_layout(); fig.savefig(figs / "e2_category_recall.png", dpi=300); plt.close(fig)

    print(to_markdown(e1)); print(to_markdown(e2))
    print("Tables ->", tabs, "| Figures ->", figs)
    return {"e1": e1, "e2": e2}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--models-config", default="configs/models.yaml")
    args = ap.parse_args()
    run(load_config(args.config), load_config(args.models_config))


if __name__ == "__main__":
    main()
