"""Synthetic CSV generator with the exact CICIoT2023 MERGED_CSV schema (for testing / dry runs).

Label proportions copy the real 200k-row sample. Values are NOT real network traffic.
Run:  python -m src.data.synthetic --out data/raw_synth --files 3 --rows 100000
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.schema import FEATURES, LABEL_COL, label_to_category

LABEL_WEIGHTS = {
    "DDOS-ICMP_FLOOD": 30609, "DDOS-UDP_FLOOD": 22849, "DDOS-TCP_FLOOD": 19381, "DDOS-RSTFINFLOOD": 17309,
    "DDOS-PSHACK_FLOOD": 17198, "DDOS-SYN_FLOOD": 17184, "DDOS-SYNONYMOUSIP_FLOOD": 15017, "DOS-UDP_FLOOD": 14291,
    "DOS-TCP_FLOOD": 11372, "DOS-SYN_FLOOD": 8744, "BENIGN": 4706, "MIRAI-GREETH_FLOOD": 4281,
    "MIRAI-UDPPLAIN": 3736, "MIRAI-GREIP_FLOOD": 3195, "DDOS-ICMP_FRAGMENTATION": 1968, "VULNERABILITYSCAN": 1630,
    "MITM-ARPSPOOFING": 1275, "DDOS-ACK_FRAGMENTATION": 1258, "DDOS-UDP_FRAGMENTATION": 1210, "DNS_SPOOFING": 752,
    "RECON-HOSTDISCOVERY": 586, "RECON-OSSCAN": 422, "RECON-PORTSCAN": 347, "DOS-HTTP_FLOOD": 291,
    "DDOS-SLOWLORIS": 115, "DDOS-HTTP_FLOOD": 115, "DICTIONARYBRUTEFORCE": 61, "BROWSERHIJACKING": 25,
    "COMMANDINJECTION": 19, "XSS": 16, "SQLINJECTION": 15, "RECON-PINGSWEEP": 12, "BACKDOOR_MALWARE": 8,
    "UPLOADING_ATTACK": 3,
}


def make_synthetic_csv(path: Path, n_rows: int, seed: int = 0, bad_fraction: float = 0.0005) -> None:
    rng = np.random.default_rng(seed)
    labels = list(LABEL_WEIGHTS)
    p = np.array([LABEL_WEIGHTS[l] for l in labels], dtype=float)
    p /= p.sum()
    y = rng.choice(labels, size=n_rows, p=p)

    X = rng.lognormal(mean=1.0, sigma=0.6, size=(n_rows, len(FEATURES)))
    # class-dependent shifts so that models have something to learn (stable across files via fixed rng)
    shift_rng = np.random.default_rng(12345)
    uniq = sorted(set(labels))
    cat_shift = {c: shift_rng.normal(0, 0.9, len(FEATURES)) for c in sorted({label_to_category(l) for l in uniq})}
    lab_shift = {l: shift_rng.normal(0, 0.25, len(FEATURES)) for l in uniq}
    shifts = np.stack([cat_shift[label_to_category(l)] + lab_shift[l] for l in y])
    X = X * np.exp(shifts)

    df = pd.DataFrame(X, columns=FEATURES)
    # inject a few bad values to exercise the cleaning code
    n_bad = int(n_rows * bad_fraction)
    if n_bad:
        rows = rng.choice(n_rows, size=n_bad, replace=False)
        df.loc[rows[: n_bad // 2], "Rate"] = np.inf
        df.loc[rows[n_bad // 2:], "Std"] = np.nan
    df[LABEL_COL] = y
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw_synth")
    ap.add_argument("--files", type=int, default=3)
    ap.add_argument("--rows", type=int, default=100_000)
    args = ap.parse_args()
    for i in range(args.files):
        p = Path(args.out) / f"synthetic_{i:02d}.csv"
        make_synthetic_csv(p, args.rows, seed=i)
        print("wrote", p)


if __name__ == "__main__":
    main()
