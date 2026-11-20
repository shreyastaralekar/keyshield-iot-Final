"""Phase 5 MERGE: runs one policy, under one attacker scenario, over the real device streams, calling the
REAL KeyManager (Batch 3) for every rotate/revoke — producing the event log that Batch 6's KEW/EAV
evaluation reads.

Two attacker scenarios (see the project plan, Section 29):
  S1 key_theft         — the attacker holds a key stolen from OUTSIDE the device. A stolen key goes dead
                         the moment its epoch changes, whether by ROTATE or REVOKE.
  S2 device_compromise — the attacker CONTROLS the device itself, so it simply re-handshakes under any new
                         key. Only REVOKE (quarantine) stops it.

Simplification stated for the report: the window that triggers a rotation is evaluated using the epoch
AFTER that rotation is applied (i.e. detection-to-rotation latency within one window is treated as
instantaneous). This is slightly favourable to the AI/Hybrid policies and is noted as a limitation.

Run:  python -m src.sim.run_sim --policy ai --scenario S1 --seed 42     (one run, prints a summary)
      python -m src.sim.run_sim --all                                   (every policy x scenario x seed)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.config import load_config, resolve_path
from src.crypto.key_manager import KeyManager
from src.engine.factory import build_policy, fsm_cooldown_for, policy_names
from src.engine.mitigation import DeviceFSM

SCENARIOS = ("S1", "S2")


def run_one(cfg: dict, ecfg: dict, proc: Path, policy_name: str, scenario: str, seed: int,
           levels: dict | None = None) -> pd.DataFrame:
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {SCENARIOS}")
    levels = levels or __import__("json").loads((Path(proc) / "thresholds.json").read_text())
    col = f"score_{ecfg['live_model']}"
    df = pd.read_parquet(Path(proc) / f"scores_test_s{seed}.parquet")
    policy = build_policy(policy_name, ecfg, levels)
    cooldown = fsm_cooldown_for(policy_name, ecfg)

    rows = []
    for device_id, g in df.groupby("device_id", sort=True):
        g = g.sort_values("t").reset_index(drop=True)
        km = KeyManager()
        km.enroll(device_id)
        fsm = DeviceFSM(device_id)
        pstate = policy.init_state()
        compromise_epoch, revoked_before = None, False

        for r in g.itertuples(index=False):
            epoch_before = km.current_epoch(device_id)
            if r.label == 1 and compromise_epoch is None:
                compromise_epoch = epoch_before   # the epoch the attacker "steals" at compromise onset

            action = policy.decide(pstate, float(getattr(r, col)), int(r.t))
            fsm.apply(action, int(r.t), km, cooldown_windows=cooldown)

            epoch_after = km.current_epoch(device_id)
            revoked_now = km.ca.is_revoked(device_id)
            if revoked_now and not revoked_before:
                event = "REVOKE"
            elif epoch_after != epoch_before:
                event = "ROTATE"
            elif action == "WARN" and fsm.state != "QUARANTINED":
                event = "WARN"
            else:
                event = "WINDOW"
            revoked_before = revoked_now

            not_quarantined = fsm.state != "QUARANTINED"
            if r.label == 0:
                delivered = not_quarantined
            elif scenario == "S1":
                delivered = not_quarantined and (epoch_after == compromise_epoch)
            else:
                delivered = not_quarantined

            rows.append({"t": int(r.t), "device_id": device_id, "event": event, "score": float(getattr(r, col)),
                        "epoch": int(epoch_after), "label": int(r.label), "attack_cat": r.category,
                        "sublabel": r.sublabel, "episode_id": int(r.episode_id), "delivered": bool(delivered),
                        "fsm_state": fsm.state, "policy": policy_name, "scenario": scenario, "seed": int(seed)})

        ok, bad = km.audit.verify_chain()
        assert ok, f"audit chain broke for {device_id} at entry {bad}"
        n_rot = sum(1 for e in km.audit.entries if e["event"] == "ROTATE")
        n_rev = sum(1 for e in km.audit.entries if e["event"] == "REVOKE")
        logged_rot = sum(1 for row in rows if row["device_id"] == device_id and row["event"] == "ROTATE")
        logged_rev = sum(1 for row in rows if row["device_id"] == device_id and row["event"] == "REVOKE")
        assert n_rot == logged_rot and n_rev == logged_rev, f"audit/event mismatch for {device_id}"

    return pd.DataFrame(rows)


def run_all(cfg: dict, ecfg: dict, proc: Path, policies: list[str] | None = None,
           scenarios=SCENARIOS, seeds: list[int] | None = None, save: bool = True) -> pd.DataFrame:
    import json
    levels = json.loads((Path(proc) / "thresholds.json").read_text())
    policies = policies or policy_names(ecfg)
    seeds = seeds or cfg["seeds"]
    frames = []
    for seed in seeds:
        for name in policies:
            for scenario in scenarios:
                frames.append(run_one(cfg, ecfg, proc, name, scenario, seed, levels))
                print(f"  ran {name} / {scenario} / seed {seed}: "
                     f"{frames[-1]['event'].value_counts().to_dict()}")
    out = pd.concat(frames, ignore_index=True)
    if save:
        out.to_parquet(Path(proc) / "events.parquet", index=False)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--engine-config", default="configs/engine.yaml")
    ap.add_argument("--policy", default=None)
    ap.add_argument("--scenario", default=None, choices=list(SCENARIOS))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    cfg, ecfg = load_config(args.config), load_config(args.engine_config)
    proc = resolve_path(cfg, "processed")
    if args.all or not (args.policy and args.scenario and args.seed):
        if not args.all:
            print("No single --policy/--scenario/--seed given; running --all.")
        out = run_all(cfg, ecfg, proc)
        print(f"\nSaved {len(out):,} rows to {proc / 'events.parquet'}")
    else:
        out = run_one(cfg, ecfg, proc, args.policy, args.scenario, args.seed)
        print(out["event"].value_counts())


if __name__ == "__main__":
    main()
