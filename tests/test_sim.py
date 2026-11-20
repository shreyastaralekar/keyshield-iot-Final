"""Batch 5 tests: the Phase 5 merge invariants from the project plan (Section 29).
Uses the small synthetic dataset + trained models + calibrated thresholds (the `trained` fixture)."""
import pandas as pd
import pytest

from src.engine.factory import policy_names
from src.sim.run_sim import run_all, run_one


def test_policy_catalog_matches_config(trained):
    _, _, ecfg, _, _, _ = trained
    names = policy_names(ecfg)
    assert names == ["ai", "static_rule", "hybrid", "fixed_T10", "fixed_T25"]


def test_after_revoke_no_further_delivery_for_that_device(trained):
    cfg, _, ecfg, proc, _, levels = trained
    out = run_one(cfg, ecfg, proc, "static_rule", "S2", cfg["seeds"][0], levels)   # most rotation-prone
    for device_id, g in out.groupby("device_id"):
        g = g.sort_values("t")
        rev_idx = g.index[g["event"] == "REVOKE"]
        if len(rev_idx):
            after = g.loc[g["t"] > g.loc[rev_idx[0], "t"]]
            assert not after["delivered"].any(), f"{device_id} delivered traffic after REVOKE"
            assert (after["fsm_state"] == "QUARANTINED").all()


def test_epoch_rises_by_exactly_one_per_rotate(trained):
    cfg, _, ecfg, proc, _, levels = trained
    out = run_one(cfg, ecfg, proc, "fixed_T10", "S1", cfg["seeds"][0], levels)
    for device_id, g in out.groupby("device_id"):
        g = g.sort_values("t").reset_index(drop=True)
        prev_epoch = g.loc[0, "epoch"] if g.loc[0, "event"] != "ROTATE" else g.loc[0, "epoch"] - 1
        for _, row in g.iterrows():
            if row["event"] == "ROTATE":
                assert row["epoch"] == prev_epoch + 1, device_id
            else:
                assert row["epoch"] == prev_epoch, device_id
            prev_epoch = row["epoch"]


def test_audit_chain_and_event_counts_match_for_every_device(trained):
    # run_one() itself asserts this internally (it would raise on mismatch); re-run to confirm no exception
    cfg, _, ecfg, proc, _, levels = trained
    out = run_one(cfg, ecfg, proc, "ai", "S1", cfg["seeds"][0], levels)
    assert set(out["event"].unique()) <= {"WINDOW", "WARN", "ROTATE", "REVOKE"}


def test_no_action_before_first_window_and_scenarios_differ(trained):
    cfg, _, ecfg, proc, _, levels = trained
    s1 = run_one(cfg, ecfg, proc, "ai", "S1", cfg["seeds"][0], levels)
    s2 = run_one(cfg, ecfg, proc, "ai", "S2", cfg["seeds"][0], levels)
    assert (s1.groupby("device_id")["t"].min() == 0).all()
    # S1 (key theft) must never deliver MORE attack traffic than S2 (device compromise) for any device,
    # since S1 additionally requires the stolen epoch to still be current.
    for device_id in s1["device_id"].unique():
        a1 = s1[(s1.device_id == device_id) & (s1.label == 1)]["delivered"].sum()
        a2 = s2[(s2.device_id == device_id) & (s2.label == 1)]["delivered"].sum()
        assert a1 <= a2, device_id


def test_same_seed_is_deterministic(trained):
    cfg, _, ecfg, proc, _, levels = trained
    a = run_one(cfg, ecfg, proc, "hybrid", "S1", cfg["seeds"][0], levels)
    b = run_one(cfg, ecfg, proc, "hybrid", "S1", cfg["seeds"][0], levels)
    pd.testing.assert_frame_equal(a, b)


def test_hybrid_guarantees_at_least_one_rotation_per_device(trained):
    # Either the AI side detects the episode, or (worst case) the max-lifetime safety net forces a rotation
    # regardless — see test_hybrid_forces_rotation_after_max_lifetime_even_without_anomaly (Batch 4 unit
    # test) for the safety net in isolation with a genuinely clean (no-episode) device.
    cfg, _, ecfg, proc, _, levels = trained
    out = run_one(cfg, ecfg, proc, "hybrid", "S1", cfg["seeds"][0], levels)
    rotated = out[out["event"] == "ROTATE"]["device_id"].unique()
    assert set(rotated) == set(out["device_id"].unique()), "hybrid left at least one device key never rotated"


def test_run_all_small(trained):
    cfg, _, ecfg, proc, _, levels = trained
    out = run_all(cfg, ecfg, proc, policies=["ai", "fixed_T10"], scenarios=("S1", "S2"),
                 seeds=cfg["seeds"][:1], save=False)
    assert set(out["policy"]) == {"ai", "fixed_T10"} and set(out["scenario"]) == {"S1", "S2"}
    assert len(out) == out.groupby(["policy", "scenario"]).size().iloc[0] * 2 * 2   # 2 policies x 2 scenarios
