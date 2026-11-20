"""Configuration helpers: load YAML, resolve paths, set seeds."""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path = "configs/default.yaml") -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(cfg: dict, key: str) -> Path:
    """Return cfg['paths'][key] as an absolute Path (relative paths are relative to the project root)."""
    p = Path(cfg["paths"][key])
    return p if p.is_absolute() else ROOT / p


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
