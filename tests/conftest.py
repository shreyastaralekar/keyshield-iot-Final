import pytest

from src.data import build_dataset
from src.data.synthetic import make_synthetic_csv
from tests.helpers import make_small_cfg


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    """Builds a small synthetic dataset once for all Batch 2 tests."""
    base = tmp_path_factory.mktemp("batch2")
    raw = base / "raw"
    for i in range(3):
        make_synthetic_csv(raw / f"s{i}.csv", 50_000, seed=i)
    cfg = make_small_cfg(base, raw)
    build_dataset.run(cfg, seeds=[42, 43])
    return cfg, base / "proc", base


@pytest.fixture(scope="session")
def trained(built):
    """Extends `built` with trained models, scored streams, and calibrated thresholds — everything
    src.sim.run_sim needs. Session-scoped: training/calibration run once and are reused by every test."""
    from src.engine import calibrate
    from src.models import train
    from tests.helpers import make_small_ecfg, make_small_mcfg

    cfg, proc, base = built
    mcfg = make_small_mcfg(base)
    train.run(cfg, mcfg, proc=proc)
    ecfg = make_small_ecfg(base)
    levels = calibrate.run(cfg, ecfg, proc=proc)
    return cfg, mcfg, ecfg, proc, base, levels
