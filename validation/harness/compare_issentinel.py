#!/usr/bin/env python3
# ============================================================
# Compare IS Sentinel results of the original nf-core-issentinel
# run with the bulk.nf IS Sentinel module, sample by sample.
#
#   candidates: <orig>/extract/<s>_is_candidates.csv
#           vs  <bulk>/is6110/<s>/<s>_is_candidates.csv
#   junctions:  <orig>/compile/is_sentinel_results_formatted.csv (rows of <s>)
#           vs  <bulk>/is6110/<s>/<s>_is_formatted.csv
#
# Every column must match exactly (as text); rows are compared as
# sorted multisets, so only content matters, not row order.
#
# Usage: compare_issentinel.py ORIG_RESULTS BULK_OUTDIR samples.txt [--out diff.tsv]
# ============================================================

import argparse
import sys
from pathlib import Path

import pandas as pd


def read(path):
    if not path.exists() or path.stat().st_size == 0:
        return None
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def rows(df):
    return sorted(map(tuple, df.itertuples(index=False))) if df is not None else []


def compare(a, b):
    """(n_a, n_b, n_identical, only_a rows, only_b rows) for two tables."""
    if a is not None and b is not None and list(a.columns) != list(b.columns):
        raise SystemExit(f"column mismatch: {list(a.columns)} vs {list(b.columns)}")
    ra, rb = rows(a), rows(b)
    sa, sb = list(ra), list(rb)
    common = 0
    for r in list(sa):
        if r in sb:
            sb.remove(r)
            sa.remove(r)
            common += 1
    return len(ra), len(rb), common, sa, sb


def main():
    ap = argparse.ArgumentParser(description="Compare original IS Sentinel vs bulk.nf module")
    ap.add_argument("orig", type=Path, help="nf-core-issentinel --outdir")
    ap.add_argument("bulk", type=Path, help="bulk.nf --outdir")
    ap.add_argument("samples", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    samples = [l.strip() for l in args.samples.read_text().splitlines() if l.strip() and l.strip() != "biosample"]
    formatted = read(args.orig / "compile" / "is_sentinel_results_formatted.csv")

    diffs = []
    print("sample\ttable\tn_orig\tn_bulk\tidentical\tonly_orig\tonly_bulk")
    for s in samples:
        tables = {
            "candidates": (read(args.orig / "extract" / f"{s}_is_candidates.csv"),
                           read(args.bulk / "is6110" / s / f"{s}_is_candidates.csv")),
            "junctions": (formatted[formatted["Sample"] == s] if formatted is not None else None,
                          read(args.bulk / "is6110" / s / f"{s}_is_formatted.csv")),
        }
        for name, (a, b) in tables.items():
            na, nb, same, only_a, only_b = compare(a, b)
            print(f"{s}\t{name}\t{na}\t{nb}\t{same}\t{len(only_a)}\t{len(only_b)}")
            diffs += [(s, name, "only_orig", r) for r in only_a] + [(s, name, "only_bulk", r) for r in only_b]

    if args.out:
        with open(args.out, "w") as fh:
            fh.write("sample\ttable\tstatus\trow\n")
            for s, t, st, r in diffs:
                fh.write(f"{s}\t{t}\t{st}\t{'|'.join(r)}\n")
    print(f"[{'OK' if not diffs else 'DIFF'}] {len(samples)} samples, {len(diffs)} differing rows", file=sys.stderr)
    return 1 if diffs else 0


if __name__ == "__main__":
    raise SystemExit(main())
