"""Train all detectors on BENIGN train windows and score every val/test stream.

Run:  python -m src.models.train            (add --tune for a small validation grid search)
Outputs (data/processed/): models/<name>.joblib, scores_{val,test}_s<seed>.parquet, train_report.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from src.config import load_config, resolve_path
from src.models.data_access import (META_COLS, benign_train_matrix, load_features, load_stream, supervised_train)
from src.models.registry import MODEL_REGISTRY, build


def tune(name, base_params, grid, Xb, Xval, yval, seed):
    results, best, best_auc = [], dict(base_params), -1.0
    keys = list(grid)
    for combo in itertools.product(*[grid[k] for k in keys]):
        params = {**base_params, **dict(zip(keys, combo))}
        det = build(name, params, seed).fit(Xb)
        auc = float(roc_auc_score(yval, det.score(Xval)))
        results.append({"params": {k: (list(v) if isinstance(v, tuple) else v) for k, v in params.items()}, "val_roc_auc": auc})
        print(f"    {name} {params} -> val ROC-AUC {auc:.4f}")
        if auc > best_auc:
            best, best_auc = params, auc
    return best, results


def run(cfg: dict, mcfg: dict, do_tune: bool = False, proc: Path | None = None) -> dict:
    proc = Path(proc) if proc else resolve_path(cfg, "processed")
    seeds, seed0 = cfg["seeds"], cfg["seed"]
    cols = load_features(proc)["window_columns"]
    Xb = benign_train_matrix(proc)
    print(f"Benign training windows: {len(Xb):,} x {Xb.shape[1]} features")
    (proc / "models").mkdir(exist_ok=True)
    params = {m: dict(mcfg["params"].get(m, {})) for m in mcfg["models"]}
    report = {"n_train_benign_windows": int(len(Xb)), "models": {}}

    if do_tune:
        tcfg = mcfg["tuning"]
        sd = seeds[tcfg["seed_index"]]
        val = load_stream(proc, "val", sd)
        Xval, yval = val[cols].to_numpy(np.float32), val["label"].to_numpy()
        tuning = {}
        for name, grid in tcfg["grids"].items():
            if name in params:
                print(f"  tuning {name} on val_s{sd} ...")
                params[name], tuning[name] = tune(name, params[name], grid, Xb, Xval, yval, seed0)
        (proc / "tuning_results.json").write_text(json.dumps(tuning, indent=2, default=str))

    fitted = {}
    for name in mcfg["models"]:
        t0 = time.perf_counter()
        det = build(name, params[name], seed0)
        if det.supervised:
            X, y = supervised_train(cfg, proc, params[name].get("windows_per_label", 100), seed0)
            det.fit(X, y)
            n_rows = len(X)
        else:
            det.fit(Xb)
            n_rows = len(Xb)
        fit_s = time.perf_counter() - t0
        det.save(proc / "models" / f"{name}.joblib")
        fitted[name] = det
        report["models"][name] = {"fit_seconds": round(fit_s, 2), "train_rows": int(n_rows), "params": params[name],
                                  "supervised": det.supervised}
        print(f"  trained {name}: {fit_s:.1f}s on {n_rows:,} rows")

    print("Scoring val/test streams ...")
    infer = {n: [0.0, 0] for n in fitted}
    for sd in seeds:
        for sp in ("val", "test"):
            st = load_stream(proc, sp, sd)
            X = st[cols].to_numpy(np.float32)
            out = st[META_COLS].copy()
            for name, det in fitted.items():
                t0 = time.perf_counter()
                out[f"score_{name}"] = det.score(X).astype(np.float32)
                infer[name][0] += time.perf_counter() - t0
                infer[name][1] += len(X)
            out.to_parquet(proc / f"scores_{sp}_s{sd}.parquet", index=False)
    for n, (sec, cnt) in infer.items():
        report["models"][n]["inference_ms_per_1000_windows"] = round(1000 * sec / max(cnt, 1) * 1000, 3)
    (proc / "train_report.json").write_text(json.dumps(report, indent=2))
    print("Done. Scores saved as scores_{val,test}_s<seed>.parquet in", proc)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--models-config", default="configs/models.yaml")
    ap.add_argument("--tune", action="store_true")
    args = ap.parse_args()
    run(load_config(args.config), load_config(args.models_config), do_tune=args.tune)


if __name__ == "__main__":
    main()
