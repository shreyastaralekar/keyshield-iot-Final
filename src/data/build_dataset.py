"""Phase 1 pipeline: raw CSVs -> clean Parquet -> split pools -> feature selection -> scaled device streams.

Run:  python -m src.data.build_dataset --config configs/default.yaml
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.config import load_config, resolve_path
from src.data.device_streams import (build_split_streams, check_stream_config, split_device_counts,
                                     window_columns)
from src.data.loader import convert_csvs
from src.data.preprocess import assign_splits, select_features, signed_log1p
from src.data.schema import BENIGN, FEATURES, LABEL_COL, label_to_category

SPLITS = ["train", "val", "test"]
SPLIT_CODE = {"train": 1, "val": 2, "test": 3}


def load_capped(parquet_dir: Path, cap_per_label: int, seed: int) -> pd.DataFrame:
    """Load all Parquet files; keep every benign row, cap each attack label (sampled evenly across files)."""
    files = sorted(Path(parquet_dir).glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No Parquet files in {parquet_dir}")
    rng = np.random.default_rng(seed)
    per_file_cap = int(np.ceil(cap_per_label / len(files)))
    parts = []
    for f in files:
        df = pd.read_parquet(f)
        for lab, idx in df.groupby(LABEL_COL).indices.items():
            if lab != BENIGN and len(idx) > per_file_cap:
                idx = rng.choice(idx, size=per_file_cap, replace=False)
            parts.append(df.iloc[np.sort(idx)])
    out = pd.concat(parts, ignore_index=True)
    out["category"] = out[LABEL_COL].map(label_to_category)
    out["row_id"] = np.arange(len(out), dtype=np.int64)
    return out


def run(cfg: dict, seeds: list[int] | None = None, force: bool = False) -> dict:
    seeds = seeds or cfg.get("seeds") or [cfg["seed"]]
    s = cfg["streams"]
    check_stream_config(s)
    raw, proc = resolve_path(cfg, "raw"), resolve_path(cfg, "processed")
    pq_dir = proc / "parquet"
    proc.mkdir(parents=True, exist_ok=True)

    # 1) CSV -> Parquet
    if force or not list(pq_dir.glob("*.parquet")):
        print("Step 1/5: converting CSV files to clean Parquet ...")
        convert_csvs(raw, pq_dir, cfg["data"]["chunksize"], cfg["data"]["drop_duplicates"])
    else:
        print("Step 1/5: Parquet files exist, skipping conversion (use --force to redo)")

    # 2) pools + row-level split
    print("Step 2/5: building train/val/test row pools ...")
    df = load_capped(pq_dir, cfg["data"]["max_rows_per_label"], cfg["seed"])
    df["split"] = assign_splits(df, cfg["split"]["ratios"], cfg["seed"])

    # 3) feature selection on TRAIN rows only
    print("Step 3/5: selecting features (train rows only) ...")
    fcfg = cfg["features"]
    selected, finfo = select_features(df[df.split == "train"], FEATURES, fcfg["top_k"], fcfg["corr_threshold"],
                                      fcfg["importance_sample"], cfg["seed"])
    print(f"  kept {len(selected)} of {len(FEATURES)} features: {selected}")

    # 4) flow pools per split (log-transformed arrays) + saved Parquet
    pools, report_pools = {}, {}
    for sp in SPLITS:
        sdf = df[df.split == sp].reset_index(drop=True)
        sdf[["row_id", LABEL_COL, "category"] + selected].to_parquet(proc / f"pools_{sp}.parquet", index=False)
        arr = signed_log1p(sdf[selected].to_numpy(np.float64)).astype(np.float32)
        is_b = (sdf[LABEL_COL] == BENIGN).to_numpy()
        attack_pools, excluded = {}, {}
        for lab, idx in sdf[~is_b].groupby(LABEL_COL).indices.items():
            rows = np.flatnonzero(~is_b)[idx]
            cat = label_to_category(lab)
            if cat in s["attack_categories"] and len(rows) >= s["min_pool_rows"]:
                attack_pools[lab] = (cat, arr[rows])
            else:
                excluded[lab] = int(len(rows))
        pools[sp] = (arr[is_b], attack_pools)
        report_pools[sp] = {"rows": int(len(sdf)), "benign_rows": int(is_b.sum()),
                            "attack_labels_used": {k: int(len(v[1])) for k, v in attack_pools.items()},
                            "attack_labels_excluded_low_support_or_category": excluded}

    # 5) streams
    print("Step 4/5: building device streams ...")
    counts = split_device_counts(s["n_devices"], cfg["split"]["ratios"])
    dev_start = {"train": 0, "val": counts["train"], "test": counts["train"] + counts["val"]}
    cols = window_columns(selected, s["window_stats"])
    cf = s["compromised_fraction"]
    stream_info, scaler = {}, None
    jobs = [("train", seeds[0])] + [(sp, sd) for sd in seeds for sp in ("val", "test")]
    built = {}
    for sp, sd in jobs:
        rng = np.random.default_rng([int(sd), SPLIT_CODE[sp]])
        benign_pool, attack_pools = pools[sp]
        stream, gt, info = build_split_streams(sp, selected, benign_pool, attack_pools, counts[sp],
                                               dev_start[sp], s, rng, sd, cf[sp])
        built[(sp, sd)] = (stream, gt)
        stream_info[f"{sp}_s{sd}"] = info
        if sp == "train":
            # scaler is fitted on BENIGN TRAIN windows only
            scaler = StandardScaler().fit(stream.loc[stream.label == 0, cols].to_numpy())

    print("Step 5/5: scaling and saving ...")
    for (sp, sd), (stream, gt) in built.items():
        stream[cols] = scaler.transform(stream[cols].to_numpy()).astype(np.float32)
        tag = "train" if sp == "train" else f"{sp}_s{sd}"
        stream.to_parquet(proc / f"streams_{tag}.parquet", index=False)
        gt.to_csv(proc / f"ground_truth_{tag}.csv", index=False)

    joblib.dump(scaler, proc / "scaler.joblib")
    (proc / "features.json").write_text(json.dumps({
        "flow_features": selected, "window_stats": s["window_stats"], "window_columns": cols,
        "flows_per_window": s["flows_per_window"], "seconds_per_window": s["seconds_per_window"],
        "windows_per_device": s["windows_per_device"], "feature_selection": finfo}, indent=2))

    need = s["n_devices"] * s["windows_per_device"] * s["flows_per_window"]
    label_counts = df[LABEL_COL].value_counts().to_dict()
    report = {
        "seeds": seeds, "device_counts": counts, "benign_flows_needed": need,
        "benign_rows_available": int((df[LABEL_COL] == BENIGN).sum()),
        "pool_rows_per_label": {k: int(v) for k, v in label_counts.items()},
        "pools": report_pools, "streams": stream_info,
    }
    (proc / "build_report.json").write_text(json.dumps(report, indent=2))
    print("\nDone. Outputs in", proc)
    print(f"  benign rows available: {report['benign_rows_available']:,} | needed: {need:,} "
          f"(reuse factors are listed in build_report.json)")
    for k, v in stream_info.items():
        print(f"  {k}: {v}")
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--seeds", default=None, help="comma-separated, e.g. 42,43,44")
    ap.add_argument("--force", action="store_true", help="re-convert CSVs even if Parquet files exist")
    ap.add_argument("--no-dedup", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.no_dedup:
        cfg["data"]["drop_duplicates"] = False
    seeds = [int(x) for x in args.seeds.split(",")] if args.seeds else None
    run(cfg, seeds=seeds, force=args.force)


if __name__ == "__main__":
    main()
