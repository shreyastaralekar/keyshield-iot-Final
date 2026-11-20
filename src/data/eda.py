"""EDA figures for the report (class balance, benign-vs-attack distributions, correlation).

Run after build_dataset:  python -m src.data.eda
"""
from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.config import load_config, resolve_path
from src.data.preprocess import signed_log1p
from src.data.schema import BENIGN, LABEL_COL


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    proc, figs = resolve_path(cfg, "processed"), resolve_path(cfg, "figures")
    figs.mkdir(parents=True, exist_ok=True)
    pools = pd.concat([pd.read_parquet(proc / f"pools_{s}.parquet").assign(split=s) for s in ("train", "val", "test")],
                      ignore_index=True)
    feats = [c for c in pools.columns if c not in ("row_id", LABEL_COL, "category", "split")]

    # 1) class balance by category (log scale)
    cat = pools["category"].value_counts()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(cat.index, cat.values)
    ax.set_yscale("log"); ax.set_ylabel("rows (log scale)"); ax.set_title("Rows per category (after cleaning)")
    plt.xticks(rotation=30, ha="right"); fig.tight_layout(); fig.savefig(figs / "eda_class_balance.png", dpi=300); plt.close(fig)

    # 2) benign vs attack distributions for the 6 most useful features
    sample = pools.sample(min(len(pools), 100_000), random_state=0)
    is_b = (sample[LABEL_COL] == BENIGN).to_numpy()
    fig, axes = plt.subplots(2, 3, figsize=(11, 6))
    for ax, f in zip(axes.ravel(), feats[:6]):
        v = signed_log1p(sample[f].to_numpy(np.float64))
        ax.hist(v[is_b], bins=40, alpha=0.6, density=True, label="benign")
        ax.hist(v[~is_b], bins=40, alpha=0.6, density=True, label="attack")
        ax.set_title(f, fontsize=9)
    axes[0, 0].legend(); fig.suptitle("Benign vs attack (signed log1p)"); fig.tight_layout()
    fig.savefig(figs / "eda_feature_distributions.png", dpi=300); plt.close(fig)

    # 3) correlation heatmap of the selected features
    corr = pd.DataFrame(signed_log1p(sample[feats].to_numpy(np.float64)), columns=feats).corr()
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr, cmap="coolwarm", center=0, ax=ax, xticklabels=True, yticklabels=True)
    ax.set_title("Correlation of selected features"); fig.tight_layout()
    fig.savefig(figs / "eda_correlation.png", dpi=300); plt.close(fig)
    print("Saved figures to", figs)


if __name__ == "__main__":
    main()
