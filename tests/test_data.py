"""Batch 1 tests: schema, loader cleaning, split leakage, scaler fit, stream/ground-truth consistency, determinism."""
import copy

import numpy as np
import pandas as pd
import pytest

from src.config import load_config
from src.data import build_dataset
from src.data.loader import convert_csvs
from src.data.schema import FEATURES, LABEL_COL, label_to_category
from src.data.synthetic import LABEL_WEIGHTS, make_synthetic_csv


def small_cfg(tmp_path):
    cfg = load_config("configs/default.yaml")
    cfg["paths"] = {"raw": str(tmp_path / "raw"), "processed": str(tmp_path / "proc"), "figures": str(tmp_path / "fig")}
    cfg["data"]["max_rows_per_label"] = 20000
    cfg["features"].update({"top_k": 8, "importance_sample": 20000})
    cfg["streams"].update({"n_devices": 10, "windows_per_device": 100, "flows_per_window": 5,
                           "episode_len_windows": [8, 15], "min_start_window": 30, "end_margin_windows": 10,
                           "min_pool_rows": 50})
    return cfg


@pytest.fixture(scope="module")
def raw_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("raw")
    for i in range(3):
        make_synthetic_csv(d / f"synthetic_{i}.csv", 50_000, seed=i)
    return d


def test_all_labels_mapped():
    assert all(label_to_category(l) != "Unknown" for l in LABEL_WEIGHTS)
    assert len(LABEL_WEIGHTS) == 34 and len(FEATURES) == 39


def test_loader_cleans_bad_values(raw_dir, tmp_path):
    rep = convert_csvs(raw_dir, tmp_path / "pq", chunksize=20_000, dedup=False)
    assert sum(f["dropped_nan_inf"] for f in rep["files"]) > 0
    df = pd.read_parquet(next((tmp_path / "pq").glob("*.parquet")))
    assert set(df.columns) == set(FEATURES) | {LABEL_COL}
    assert np.isfinite(df[FEATURES].to_numpy()).all()
    assert str(df[FEATURES[0]].dtype) == "float32"


def test_pipeline_end_to_end(raw_dir, tmp_path):
    cfg = small_cfg(tmp_path)
    cfg["paths"]["raw"] = str(raw_dir)
    rep = build_dataset.run(cfg, seeds=[42, 43])
    proc = tmp_path / "proc"
    for name in ["features.json", "scaler.joblib", "build_report.json", "streams_train.parquet",
                 "streams_val_s42.parquet", "streams_test_s43.parquet", "ground_truth_test_s42.csv"]:
        assert (proc / name).exists(), name

    # no flow row appears in two splits
    ids = {sp: set(pd.read_parquet(proc / f"pools_{sp}.parquet")["row_id"]) for sp in ("train", "val", "test")}
    assert not (ids["train"] & ids["val"]) and not (ids["train"] & ids["test"]) and not (ids["val"] & ids["test"])

    # device sets are disjoint across splits
    dev = {sp: set(pd.read_parquet(proc / f"streams_{t}.parquet")["device_id"])
           for sp, t in (("train", "train"), ("val", "val_s42"), ("test", "test_s42"))}
    assert not (dev["train"] & dev["val"]) and not (dev["train"] & dev["test"]) and not (dev["val"] & dev["test"])

    # ground truth matches window labels exactly
    for tag in ("train", "val_s42", "test_s43"):
        st = pd.read_parquet(proc / f"streams_{tag}.parquet")
        gt = pd.read_csv(proc / f"ground_truth_{tag}.csv")
        assert (st.groupby("device_id").size() == 100).all()
        assert st["label"].sum() == gt["n_windows"].sum()
        for _, e in gt.iterrows():
            seg = st[(st.device_id == e.device_id) & (st.t >= e.start_t) & (st.t < e.end_t)]
            assert (seg.label == 1).all() and (seg.episode_id == e.episode_id).all() and (seg.category == e.category).all()
        assert (st.loc[st.episode_id == -1, "label"] == 0).all()

    # scaler fitted on benign TRAIN windows only
    feat = pd.read_json(proc / "features.json", typ="series")
    cols = feat["window_columns"]
    tr = pd.read_parquet(proc / "streams_train.parquet")
    va = pd.read_parquet(proc / "streams_val_s42.parquet")
    assert np.abs(tr.loc[tr.label == 0, cols].mean().to_numpy()).max() < 1e-3
    assert np.abs(va.loc[va.label == 0, cols].mean().to_numpy()).max() > 1e-3

    # different seeds -> different episode placement
    g42 = pd.read_csv(proc / "ground_truth_test_s42.csv")
    g43 = pd.read_csv(proc / "ground_truth_test_s43.csv")
    assert not g42[["device_id", "start_t", "sublabel"]].equals(g43[["device_id", "start_t", "sublabel"]])
    assert rep["benign_rows_available"] > 0


def test_determinism(raw_dir, tmp_path):
    outs = []
    for k in range(2):
        cfg = small_cfg(tmp_path / f"run{k}")
        cfg["paths"]["raw"] = str(raw_dir)
        build_dataset.run(cfg, seeds=[7])
        outs.append(pd.read_parquet(tmp_path / f"run{k}" / "proc" / "streams_test_s7.parquet"))
    pd.testing.assert_frame_equal(outs[0], outs[1])
