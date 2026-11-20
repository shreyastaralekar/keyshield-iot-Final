"""E3: AI vs conventional policies, with the two attacker scenarios (Section 29) — the biggest single block
of CO3 marks. Reads data/processed/events.parquet (Batch 5) and report/tables/crypto_benchmark.csv (Batch 3).

Run:  python -m src.eval.e3_report
Outputs:
  report/tables/e3_kew_eav_by_policy.{csv,md}   — mean +- std over seeds, per policy x scenario
  report/tables/e3_cost_by_policy.{csv,md}
  report/tables/e3_kew_eav_by_category.csv      — per (policy, scenario, attack category), detail for E2/CO3
  report/tables/e3_failure_highlights.md        — worst category per policy (the "where AI fails" material)
  report/figures/e3_kew_boxplot.png, e3_eav_bar.png, e3_cost_bar.png
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import ROOT, load_config, resolve_path
from src.eval.cost import load_handshake_ms, per_run_cost
from src.eval.kew import episodes_kew_eav

import re

BASE_LABELS = {"ai": "AI (adaptive)", "hybrid": "Hybrid (AI + lifetime cap)", "static_rule": "Static rule"}
_FIXED_RE = re.compile(r"^fixed_T(\d+)$")


def label_for(policy: str) -> str:
    if policy in BASE_LABELS:
        return BASE_LABELS[policy]
    m = _FIXED_RE.match(policy)
    return f"Fixed interval (T={m.group(1)}w)" if m else policy


def _sort_key(policy: str):
    """ai, hybrid, static_rule first (in that order), then every fixed_T<N> sorted by N — works for
    whatever T values configs/engine.yaml actually defines, test fixtures included."""
    base_rank = {"ai": 0, "hybrid": 1, "static_rule": 2}
    if policy in base_rank:
        return (0, base_rank[policy], 0)
    m = _FIXED_RE.match(policy)
    return (1, 0, int(m.group(1))) if m else (2, 0, policy)


def policies_present_sorted(*series: pd.Series) -> list[str]:
    names = set()
    for s in series:
        names |= set(s.unique())
    return sorted(names, key=_sort_key)


class LABELS:  # noqa: N801 -- kept as a name so existing `LABELS.get(p, p)` call sites still read naturally
    @staticmethod
    def get(key, default=None):
        return label_for(key)


def _dir(p: str) -> Path:
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def pm(s: pd.Series, nd: int = 1) -> str:
    return f"{s.mean():.{nd}f} ± {s.std(ddof=0):.{nd}f}"


def to_markdown(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.tolist()) + " |")
    return "\n".join(lines) + "\n"


def order(df: pd.DataFrame, policies: list[str], col: str = "Policy") -> pd.DataFrame:
    """Reindex a table (already converted to display labels in `col`) by the given internal policy
    order, converting each to its label. Policies not present in df are skipped."""
    present = [label_for(p) for p in policies if label_for(p) in set(df[col])]
    return df.set_index(col).loc[present].reset_index()


def run(cfg: dict, ev_cfg: dict, proc: Path | None = None, tables_dir: Path | None = None,
       figures_dir: Path | None = None) -> dict:
    proc = Path(proc) if proc else resolve_path(cfg, "processed")
    tabs = Path(tables_dir) if tables_dir else _dir(ev_cfg["output"]["tables_dir"])
    figs = Path(figures_dir) if figures_dir else _dir(ev_cfg["output"]["figures_dir"])
    tabs.mkdir(parents=True, exist_ok=True); figs.mkdir(parents=True, exist_ok=True)

    events = pd.read_parquet(proc / "events.parquet")
    s = cfg["streams"]
    n_devices_test = cfg["streams"]["n_devices"] - int(round(s["n_devices"] * cfg["split"]["ratios"][0])) \
        - int(round(s["n_devices"] * cfg["split"]["ratios"][1]))
    n_devices_test = max(n_devices_test, events["device_id"].nunique() // len(cfg["seeds"]))
    wpd, spw = s["windows_per_device"], s["seconds_per_window"]

    ep = episodes_kew_eav(events, windows_per_device=wpd, seconds_per_window=spw)
    ep.to_csv(proc / "episodes_kew_eav.parquet".replace(".parquet", ".csv"), index=False)

    handshake_ms = load_handshake_ms(tabs / "crypto_benchmark.csv", ev_cfg["cost"]["default_handshake_ms"])
    cost = per_run_cost(events, n_devices=n_devices_test, windows_per_device=wpd, seconds_per_window=spw,
                        handshake_ms=handshake_ms, revoke_also_handshakes=ev_cfg["cost"]["revoke_also_handshakes"])
    policies = policies_present_sorted(ep["policy"], cost["policy"], events["policy"])

    # --- table 1: KEW/EAV by policy x scenario (mean +- std over seeds; detection rate = 1 - censored share) ---
    rows = []
    for (policy, scenario), g in ep.groupby(["policy", "scenario"]):
        by_seed_kew = g.groupby("seed")["kew_seconds"].mean()
        by_seed_eav = g.groupby("seed")["eav_windows"].mean()
        rows.append({
            "Policy": LABELS.get(policy, policy), "Scenario": scenario,
            "Mean KEW (s)": pm(by_seed_kew, 0), "Mean EAV (windows)": pm(by_seed_eav, 2),
            "Detection rate": f"{1 - g['censored'].mean():.3f}", "Episodes (all seeds)": int(len(g)),
        })
    e3a = order(pd.DataFrame(rows), policies)
    e3a.to_csv(tabs / "e3_kew_eav_by_policy.csv", index=False)
    (tabs / "e3_kew_eav_by_policy.md").write_text(to_markdown(e3a))

    # --- table 2: cost by policy (averaged across both scenarios, since rotation behaviour vs score is the
    #     same regardless of what the attacker turns out to be; scenario only changes what counts as delivered) ---
    crows = []
    for policy, g in cost.groupby("policy"):
        crows.append({
            "Policy": LABELS.get(policy, policy),
            "Rotations / device-hour": pm(g["rotations_per_device_hour"], 2),
            "False rotation rate": pm(g["false_rotation_rate"].fillna(0), 3),
            "Revokes / run": pm(g["revokes"], 2),
            "Crypto overhead (ms / device-hour)": pm(g["crypto_overhead_ms_per_device_hour"], 3),
        })
    e3b = order(pd.DataFrame(crows), policies)
    e3b.to_csv(tabs / "e3_cost_by_policy.csv", index=False)
    (tabs / "e3_cost_by_policy.md").write_text(to_markdown(e3b))

    # --- table 3: per-category detail (for E2 completion / "where AI fails") ---
    cat = (ep.groupby(["policy", "scenario", "category"])
          .agg(mean_kew_s=("kew_seconds", "mean"), mean_eav=("eav_windows", "mean"),
               detection_rate=("censored", lambda x: 1 - x.mean()), n=("censored", "size"))
          .reset_index().round(3))
    cat.to_csv(tabs / "e3_kew_eav_by_category.csv", index=False)

    # --- failure highlights: worst (lowest detection rate, or highest KEW) category per policy ---
    lines = ["# Where AI fails: worst attack category per policy (by detection rate, S1)\n"]
    for policy in policies:
        sub = cat[(cat.policy == policy) & (cat.scenario == "S1")]
        if sub.empty:
            continue
        worst = sub.sort_values(["detection_rate", "mean_kew_s"], ascending=[True, False]).iloc[0]
        lines.append(f"- **{LABELS.get(policy, policy)}**: weakest on **{worst['category']}** "
                     f"(detection rate {worst['detection_rate']:.2f}, mean KEW {worst['mean_kew_s']:.0f}s, "
                     f"n={int(worst['n'])} episodes)")
    (tabs / "e3_failure_highlights.md").write_text("\n".join(lines) + "\n")

    # --- figures ---
    fig, ax = plt.subplots(figsize=(9, 5))
    data, labels, colors = [], [], []
    for p in policies:
        for sc, c in (("S1", "#4C72B0"), ("S2", "#DD8452")):
            vals = ep[(ep.policy == p) & (ep.scenario == sc)]["kew_seconds"]
            if len(vals):
                data.append(vals.to_numpy()); labels.append(f"{LABELS.get(p, p)}\n{sc}"); colors.append(c)
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True)
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
    ax.set_ylabel("Key Exposure Window (seconds)"); ax.set_title("KEW per policy and scenario (test episodes, all seeds)")
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=8); fig.tight_layout()
    fig.savefig(figs / "e3_kew_boxplot.png", dpi=300); plt.close(fig)

    piv = ep.groupby(["policy", "scenario"])["eav_windows"].mean().unstack("scenario").reindex(policies)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(piv)); w = 0.35
    ax.bar(x - w / 2, piv["S1"], w, label="S1 key theft")
    ax.bar(x + w / 2, piv["S2"], w, label="S2 device compromise")
    ax.set_xticks(x); ax.set_xticklabels([LABELS.get(p, p) for p in piv.index], rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("Mean EAV (attack windows delivered)"); ax.set_title("Exposed Attack Volume per policy")
    ax.legend(); fig.tight_layout(); fig.savefig(figs / "e3_eav_bar.png", dpi=300); plt.close(fig)

    cost_mean = cost.groupby("policy")["rotations_per_device_hour"].mean().reindex(policies)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([LABELS.get(p, p) for p in cost_mean.index], cost_mean.values, color="#55A868")
    ax.set_ylabel("Rotations / device-hour"); ax.set_title("Rotation cost per policy")
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=8); fig.tight_layout()
    fig.savefig(figs / "e3_cost_bar.png", dpi=300); plt.close(fig)

    print(to_markdown(e3a)); print(to_markdown(e3b)); print((tabs / "e3_failure_highlights.md").read_text())
    print("Tables ->", tabs, "| Figures ->", figs, f"| handshake_ms used: {handshake_ms}")
    return {"kew_eav_by_policy": e3a, "cost_by_policy": e3b, "by_category": cat, "episodes": ep}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--eval-config", default="configs/eval_e3.yaml")
    args = ap.parse_args()
    run(load_config(args.config), load_config(args.eval_config))


if __name__ == "__main__":
    main()
