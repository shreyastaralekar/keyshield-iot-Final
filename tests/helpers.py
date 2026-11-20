from src.config import load_config


def make_small_cfg(base, raw):
    cfg = load_config("configs/default.yaml")
    cfg["paths"] = {"raw": str(raw), "processed": str(base / "proc"), "figures": str(base / "fig")}
    cfg["data"]["max_rows_per_label"] = 20000
    cfg["features"].update({"top_k": 8, "importance_sample": 20000})
    cfg["streams"].update({"n_devices": 10, "windows_per_device": 100, "flows_per_window": 5,
                           "episode_len_windows": [8, 15], "min_start_window": 30, "end_margin_windows": 10,
                           "min_pool_rows": 50})
    cfg["seeds"] = [42, 43]
    return cfg


def make_small_mcfg(base):
    return {
        "models": ["iforest", "ocsvm", "ae", "rf"],
        "params": {"iforest": {"n_estimators": 50, "max_samples": 256}, "ocsvm": {"nu": 0.05, "gamma": "scale", "max_train": 2000},
                   "ae": {"hidden": [16, 8, 16], "max_iter": 40}, "rf": {"n_estimators": 40, "windows_per_label": 20}},
        "tuning": {"seed_index": 0, "grids": {"iforest": {"n_estimators": [30, 60]}}},
        "evaluation": {"threshold_quantile": 0.99, "figures_dir": str(base / "figs"), "tables_dir": str(base / "tabs")},
    }


def make_small_ecfg(base):
    return {
        "live_model": "iforest",
        "calibration": {"seed_index": 0, "quantiles": {"warn": 0.90, "rotate": 0.97, "revoke": 0.995},
                        "min_revoke_margin": 1.05},
        "policies": {
            "ai": {"hysteresis_n": 3, "hysteresis_k": 2, "fast_path_multiplier": 1.5, "cooldown_windows": 5,
                  "revoke_persist_windows": 3, "ewma_alpha": 0.1, "warn_z": 2.0},
            "fixed_interval": {"T_values": [10, 25]},
            "static_rule": {"use_hysteresis": False},
            "hybrid": {"max_lifetime_windows": 30},
        },
    }
