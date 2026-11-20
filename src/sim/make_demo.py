"""Builds the deterministic demo scenario (configs/demo.yaml) through the REAL AIPolicy, DeviceFSM and
KeyManager (Batches 3-4), for both attacker scenarios, so the dashboard has something true to replay.

Run:  python -m src.sim.make_demo
Outputs: data/processed/demo_events.parquet, data/processed/demo_audit_log.jsonl
(the audit log is for the device that actually gets rotated/revoked/recovered: dev_demo_04)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.config import ROOT, load_config
from src.crypto.key_manager import KeyManager
from src.engine.mitigation import DeviceFSM
from src.engine.policies import AIPolicy


def _scripted_score(t: int, phases: list[dict]) -> tuple[float, int, str, int]:
    for ph in phases:
        if ph["start"] <= t < ph["end"]:
            return ph["score"], ph.get("label", 0), ph.get("category", "Benign"), ph.get("episode_id", -1)
    return 0.1, 0, "Benign", -1


def run(dcfg: dict, proc: Path) -> pd.DataFrame:
    proc.mkdir(parents=True, exist_ok=True)
    rows, demo_audit = [], None
    for scenario in ("S1", "S2"):
        for d in range(dcfg["n_devices"]):
            device_id = f"dev_demo_{d:02d}"
            km = KeyManager()
            km.enroll(device_id)
            fsm = DeviceFSM(device_id)
            is_target = d == dcfg["compromised_device_index"]
            policy = AIPolicy(dcfg["levels"], **dcfg["policy"])
            pstate = policy.init_state()
            compromise_epoch, revoked_before = None, False

            for t in range(dcfg["windows_per_device"]):
                score, label, category, episode_id = (_scripted_score(t, dcfg["phases"]) if is_target
                                                       else (0.1, 0, "Benign", -1))
                epoch_before = km.current_epoch(device_id)
                if label == 1 and compromise_epoch is None:
                    compromise_epoch = epoch_before

                action = policy.decide(pstate, score, t)
                fsm.apply(action, t, km, cooldown_windows=dcfg["policy"]["cooldown_windows"])

                if is_target and t == dcfg["recover_at_t"] and fsm.state == "QUARANTINED":
                    fsm.recover(t)

                epoch_after = km.current_epoch(device_id)
                revoked_now = km.ca.is_revoked(device_id)
                if revoked_now and not revoked_before:
                    event = "REVOKE"
                elif epoch_after != epoch_before:
                    event = "ROTATE"
                elif action == "WARN" and fsm.state != "QUARANTINED":
                    event = "WARN"
                elif fsm.history and fsm.history[-1][1] == "RECOVER" and fsm.history[-1][0] == t:
                    event = "RECOVER"
                else:
                    event = "WINDOW"
                revoked_before = revoked_now

                not_q = fsm.state != "QUARANTINED"
                if label == 0:
                    delivered = not_q
                elif scenario == "S1":
                    delivered = not_q and (epoch_after == compromise_epoch)
                else:
                    delivered = not_q

                rows.append({"t": t, "device_id": device_id, "event": event, "score": score,
                            "epoch": epoch_after, "label": label, "attack_cat": category,
                            "sublabel": category, "episode_id": episode_id, "delivered": bool(delivered),
                            "fsm_state": fsm.state, "policy": "ai_demo", "scenario": scenario, "seed": 0})

            if is_target and scenario == "S1":
                demo_audit, demo_ca_cert = km.audit, km.ca.public_bytes()

    out = pd.DataFrame(rows)
    out.to_parquet(proc / "demo_events.parquet", index=False)
    if demo_audit is not None:
        demo_audit.to_jsonl(proc / "demo_audit_log.jsonl")
        (proc / "demo_ca_cert.pem").write_bytes(demo_ca_cert)   # the CA's PUBLIC cert only, for verification
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo-config", default="configs/demo.yaml")
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()
    dcfg = load_config(args.demo_config)
    cfg = load_config(args.config)
    proc = Path(cfg["paths"]["processed"])
    proc = proc if proc.is_absolute() else ROOT / proc
    out = run(dcfg, proc)
    print(out.groupby(["scenario", "event"]).size().unstack(fill_value=0))
    print(f"\nSaved {len(out):,} rows to {proc / 'demo_events.parquet'}")
    print(f"Audit log -> {proc / 'demo_audit_log.jsonl'}")


if __name__ == "__main__":
    main()
