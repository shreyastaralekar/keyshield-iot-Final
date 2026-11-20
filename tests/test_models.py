"""Batch 2 tests: metrics, models, training/scoring outputs, evaluation outputs."""
import numpy as np
import pandas as pd
import pytest

from src.eval.metrics import (auc_metrics, best_f1_threshold, classification_metrics, episode_detection,
                              threshold_at_benign_quantile)
from src.models import evaluate, train
from src.models.data_access import benign_train_matrix, load_features, supervised_train
from src.models.registry import build
from tests.helpers import make_small_mcfg


def test_classification_metrics_toy():
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    s = np.array([0.1, 0.2, 0.3, 0.9, 0.4, 0.6, 0.8, 0.95])
    m = classification_metrics(y, s, 0.5)
    assert (m["tp"], m["fp"], m["tn"], m["fn"]) == (3, 1, 3, 1)
    assert m["precision"] == pytest.approx(0.75) and m["recall"] == pytest.approx(0.75) and m["fpr"] == pytest.approx(0.25)
    assert auc_metrics(y, s)["roc_auc"] == pytest.approx(0.8125)


def test_threshold_uses_only_given_benign_scores():
    benign = np.arange(100, dtype=float)
    assert threshold_at_benign_quantile(benign, 0.99) == pytest.approx(98.01)
    y = np.array([0, 0, 1, 1]); s = np.array([0.1, 0.4, 0.6, 0.9])
    assert 0.4 < best_f1_threshold(y, s) <= 0.6


def test_episode_detection():
    df = pd.DataFrame({"device_id": ["a"] * 6, "t": range(6), "episode_id": [-1, -1, 0, 0, 0, -1],
                       "s": [0.1, 0.1, 0.1, 0.9, 0.9, 0.1]})
    r = episode_detection(df, "s", 0.5)
    assert r["episodes"] == 1 and r["episode_detect_rate"] == 1.0 and r["median_delay_windows"] == 1.0


def test_models_fit_score_save_load(built, tmp_path):
    cfg, proc, _ = built
    X = benign_train_matrix(proc)
    for name, params in make_small_mcfg(tmp_path)["params"].items():
        det = build(name, params, 42)
        if det.supervised:
            Xs, ys = supervised_train(cfg, proc, windows_per_label=params["windows_per_label"])
            assert ys.sum() > 0 and (ys == 0).sum() == len(X)
            det.fit(Xs, ys)
        else:
            det.fit(X)
        s = det.score(X[:200])
        assert s.shape == (200,) and np.isfinite(s).all()
        det.save(tmp_path / f"{name}.joblib")
        det2 = build(name, params, 42); det2.load(tmp_path / f"{name}.joblib")
        np.testing.assert_allclose(det2.score(X[:200]), s)


def test_isolation_forest_deterministic(built):
    _, proc, _ = built
    X = benign_train_matrix(proc)
    a = build("iforest", {"n_estimators": 30, "max_samples": 128}, 7).fit(X).score(X[:100])
    b = build("iforest", {"n_estimators": 30, "max_samples": 128}, 7).fit(X).score(X[:100])
    np.testing.assert_allclose(a, b)


def test_train_and_evaluate_pipeline(built):
    cfg, proc, base = built
    mcfg = make_small_mcfg(base)
    rep = train.run(cfg, mcfg, do_tune=True, proc=proc)
    assert set(rep["models"]) == {"iforest", "ocsvm", "ae", "rf"}
    assert (proc / "tuning_results.json").exists() and (proc / "models" / "ae.joblib").exists()

    feat_cols = load_features(proc)["window_columns"]
    for sd in cfg["seeds"]:
        for sp in ("val", "test"):
            sc = pd.read_parquet(proc / f"scores_{sp}_s{sd}.parquet")
            st = pd.read_parquet(proc / f"streams_{sp}_s{sd}.parquet")
            assert len(sc) == len(st) and (sc["label"].to_numpy() == st["label"].to_numpy()).all()
            assert not set(feat_cols) & set(sc.columns)          # scores files carry no feature columns
            for m in mcfg["models"]:
                assert np.isfinite(sc[f"score_{m}"]).all()
                assert auc_metrics(sc["label"], sc[f"score_{m}"])["roc_auc"] > 0.6, m

    res = evaluate.run(cfg, mcfg, proc=proc, figures_dir=base / "figs", tables_dir=base / "tabs")
    assert len(res["e1"]) == 4 and (base / "tabs" / "e1_model_comparison.md").exists()
    for f in ("e1_roc.png", "e1_pr.png", "e2_category_recall.png"):
        assert (base / "figs" / f).exists()
