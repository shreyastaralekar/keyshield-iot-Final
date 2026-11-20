"""Overhead benchmarks for the report (Section 8 / CO1 validation evidence).

Run:  python -m src.crypto.benchmark
Outputs: report/tables/crypto_benchmark.csv
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd

from src.config import ROOT
from src.crypto.key_manager import KeyManager
from src.crypto.session import aead_decrypt, aead_encrypt


def time_it(fn, n: int) -> float:
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t0) / n


def run(n_handshakes: int = 500, n_messages: int = 2000, msg_sizes=(64, 1024, 8192)) -> pd.DataFrame:
    km = KeyManager()
    km.enroll("bench_dev")
    rows = [{"operation": "handshake (establish_session)", "n": n_handshakes,
            "mean_ms": 1000 * time_it(lambda: km.establish_session("bench_dev"), n_handshakes)}]
    rows.append({"operation": "key rotation (rotate)", "n": n_handshakes,
                "mean_ms": 1000 * time_it(lambda: km.rotate("bench_dev"), n_handshakes)})

    key = km.key_for_epoch("bench_dev", km.current_epoch("bench_dev"))
    for size in msg_sizes:
        msg = os.urandom(size)
        nonce = os.urandom(12)
        rows.append({"operation": f"AES-256-GCM encrypt ({size} B)", "n": n_messages,
                    "mean_ms": 1000 * time_it(lambda: aead_encrypt(key, nonce, msg, b"aad"), n_messages)})
        ct = aead_encrypt(key, nonce, msg, b"aad")
        rows.append({"operation": f"AES-256-GCM decrypt ({size} B)", "n": n_messages,
                    "mean_ms": 1000 * time_it(lambda: aead_decrypt(key, nonce, ct, b"aad"), n_messages)})
    df = pd.DataFrame(rows)
    df["throughput_msgs_per_s"] = 1000.0 / df["mean_ms"]
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="report/tables/crypto_benchmark.csv")
    ap.add_argument("--n-handshakes", type=int, default=500)
    ap.add_argument("--n-messages", type=int, default=2000)
    args = ap.parse_args()
    df = run(args.n_handshakes, args.n_messages)
    out = Path(args.out)
    out = out if out.is_absolute() else ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(df.to_string(index=False))
    print("\nSaved to", out)


if __name__ == "__main__":
    main()
