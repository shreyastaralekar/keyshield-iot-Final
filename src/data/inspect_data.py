"""Count labels across the raw CSVs and estimate how many files you need.

Run:  python -m src.data.inspect_data
"""
from __future__ import annotations

import argparse
import math

import pandas as pd

from src.config import load_config, resolve_path
from src.data.loader import list_csvs
from src.data.schema import BENIGN, label_to_category


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    raw = resolve_path(cfg, "raw")
    files = list_csvs(raw)
    if not files:
        raise SystemExit(f"No CSV files under {raw}")

    total = pd.Series(dtype="int64")
    print(f"Reading labels from {len(files)} file(s) in {raw} ...")
    for f in files:
        rows = 0
        for chunk in pd.read_csv(f, usecols=lambda c: c.strip().lower() == "label", chunksize=500_000):
            labels = chunk.iloc[:, 0].astype(str).str.strip().str.upper()
            total = total.add(labels.value_counts(), fill_value=0)
            rows += len(chunk)
        print(f"  {f.name}: {rows:,} rows")
    total = total.astype(int).sort_values(ascending=False)

    n_rows = int(total.sum())
    benign = int(total.get(BENIGN, 0))
    print(f"\nTotal rows: {n_rows:,} | benign: {benign:,} ({100 * benign / max(n_rows, 1):.2f}%)")

    by_cat = total.groupby(lambda l: label_to_category(l)).sum().sort_values(ascending=False)
    print("\nRows per category:")
    print(by_cat.to_string())
    print("\nRows per label:")
    print(total.to_string())

    s = cfg["streams"]
    need = s["n_devices"] * s["windows_per_device"] * s["flows_per_window"]
    per_file = benign / len(files) if files else 0
    print(f"\nBenign flows needed by the current config (devices x windows x flows/window): {need:,}")
    if benign >= need:
        print("OK: you already have enough benign rows without reuse.")
    elif per_file > 0:
        more = math.ceil((need - benign) / per_file)
        print(f"You have ~{per_file:,.0f} benign rows per file. Download about {more} more file(s) "
              f"(total ~{len(files) + more}) to avoid benign reuse.")
    print("\nCategories with few rows (<%d) cannot support attack episodes; they are reported as low-support." % s["min_pool_rows"])


if __name__ == "__main__":
    main()
