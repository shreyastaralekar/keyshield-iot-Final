"""Chunked CSV -> clean Parquet conversion (keeps RAM low: 16 GB is enough)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.schema import BENIGN, FEATURES, LABEL_COL, label_to_category


def list_csvs(raw_dir: Path) -> list[Path]:
    raw_dir = Path(raw_dir)
    return sorted(p for p in raw_dir.rglob("*.csv") if p.is_file())


def read_header_map(csv_path: Path) -> tuple[dict, list]:
    """Return ({original_col: clean_col}, columns_to_keep). Strips spaces; accepts 'label' in any case."""
    header = list(pd.read_csv(csv_path, nrows=0).columns)
    rename = {c: (LABEL_COL if c.strip().lower() == "label" else c.strip()) for c in header}
    clean = set(rename.values())
    missing = [f for f in FEATURES if f not in clean]
    if missing or LABEL_COL not in clean:
        raise ValueError(
            f"{csv_path.name}: expected columns missing: {missing + ([LABEL_COL] if LABEL_COL not in clean else [])}. "
            f"Found: {sorted(clean)}"
        )
    keep = [c for c in header if rename[c] in FEATURES or rename[c] == LABEL_COL]
    return rename, keep


def clean_chunk(chunk: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Numeric coercion, inf/NaN removal, float32 downcast, label normalisation. Returns (clean_df, n_dropped)."""
    feats = chunk[FEATURES].apply(pd.to_numeric, errors="coerce")
    feats = feats.replace([np.inf, -np.inf], np.nan)
    ok = feats.notna().all(axis=1) & chunk[LABEL_COL].notna()
    out = feats[ok].astype("float32").reset_index(drop=True)
    out[LABEL_COL] = chunk.loc[ok, LABEL_COL].astype(str).str.strip().str.upper().to_numpy()
    return out, int((~ok).sum())


def convert_csvs(raw_dir: Path, out_dir: Path, chunksize: int = 500_000, dedup: bool = True) -> dict:
    """Convert every CSV in raw_dir to a clean Parquet file in out_dir. Returns (and saves) a report."""
    files = list_csvs(raw_dir)
    if not files:
        raise FileNotFoundError(f"No CSV files found under {raw_dir}. Put the MERGED_CSV files there.")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"files": []}
    unknown_labels: set[str] = set()

    for f in files:
        rename, keep = read_header_map(f)
        parts, rows_in, dropped_bad = [], 0, 0
        for chunk in pd.read_csv(f, usecols=keep, chunksize=chunksize, low_memory=False):
            rows_in += len(chunk)
            chunk = chunk.rename(columns=rename)
            clean, bad = clean_chunk(chunk)
            dropped_bad += bad
            parts.append(clean)
        df = pd.concat(parts, ignore_index=True)
        dup_dropped = 0
        if dedup:
            before = len(df)
            df = df.drop_duplicates(ignore_index=True)
            dup_dropped = before - len(df)
        cats = df[LABEL_COL].map(label_to_category)
        unknown_labels |= set(df.loc[cats == "Unknown", LABEL_COL].unique())
        out_path = out_dir / f"{f.stem}.parquet"
        df.to_parquet(out_path, index=False)
        rep = {
            "file": f.name, "rows_in": int(rows_in), "dropped_nan_inf": int(dropped_bad),
            "dropped_duplicates": int(dup_dropped), "rows_out": int(len(df)),
            "benign_rows": int((df[LABEL_COL] == BENIGN).sum()),
        }
        report["files"].append(rep)
        print(f"  {f.name}: {rep['rows_in']:,} rows in -> {rep['rows_out']:,} out "
              f"(bad {rep['dropped_nan_inf']:,}, dup {rep['dropped_duplicates']:,}, benign {rep['benign_rows']:,})")

    if unknown_labels:
        raise ValueError(f"Unknown labels found (add them to src/data/schema.py): {sorted(unknown_labels)}")
    (out_dir / "convert_report.json").write_text(json.dumps(report, indent=2))
    return report
