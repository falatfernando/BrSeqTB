#!/usr/bin/env python3
# ============================================================
# Normalize a BrSeqTB v1 run directory (f3ccebd layout: xlsx +
# per-module CSVs under projectDir) into the canonical tables
# compared by compare.py:
#
#   calls.tsv.gz           one row per sample x caller x allele
#   resistance_hits.tsv.gz final per-isolate table (results/resistance)
#   resistance_profile.tsv one row per sample x catalogue drug
#   qc.tsv                 long format: sample, section, metric, value
#   oxidative_damage.tsv   calls removed by the damage guard
#
# The table builders are bin/canonical_tables.py, the same code
# the bulk pipeline uses to write its per-sample outputs. Only the
# profile differs: here it is read from the cohort-wide
# results/resistance_summary.xlsx that v1 writes.
#
# Usage:
#   normalize_v1.py RUN_DIR OUT_DIR [--samples samples.txt]
# ============================================================

import argparse
import sys
from pathlib import Path

import pandas as pd

BIN_DIR = Path(__file__).resolve().parents[2] / "bin"
sys.path.insert(0, str(BIN_DIR))
import canonical_tables as ct  # noqa: E402


def read_samples(run_dir, samples_file):
    if samples_file:
        return [l.strip() for l in open(samples_file) if l.strip()]
    manifest = run_dir / "manifest.tsv"
    return pd.read_csv(manifest, sep="\t", dtype=str)["biosample"].tolist()


def load_profile(run_dir, samples, drugs):
    f = run_dir / "results" / "resistance_summary.xlsx"
    if not f.exists():
        ct.warn("missing results/resistance_summary.xlsx")
        return pd.DataFrame(columns=ct.PROFILE_COLS)
    wide = pd.read_excel(f, dtype=str).fillna("")
    wide = wide[wide["biosample"].isin(samples)]
    cols = [c for c in wide.columns
            if c not in ("biosample", "damage_flag") and not c.endswith("_annotation")]
    rows = []
    for _, r in wide.iterrows():
        sample_rows = [{"sample": r["biosample"], "drug": d, "phenotype": r[d],
                        "annotation": r.get(f"{d}_annotation", "")} for d in cols]
        rows += ct.fill_profile(sample_rows, r["biosample"], drugs)
    return pd.DataFrame(rows, columns=ct.PROFILE_COLS)


def main():
    ap = argparse.ArgumentParser(description="Normalize a BrSeqTB v1 run directory into canonical tables")
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--samples", help="file with one sample per line (default: RUN_DIR/manifest.tsv)")
    args = ap.parse_args()

    samples = read_samples(args.run_dir, args.samples)
    drugs = ct.catalogue_drugs(args.run_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    calls, hits, qc, damage = [], [], [], []
    for s in samples:
        calls.append(ct.load_calls(args.run_dir, s))
        h = ct.load_hits(args.run_dir, s)
        if h is not None:
            hits.append(h)
        qc += ct.qc_rows(args.run_dir, s)
        d = ct.load_damage(args.run_dir, s)
        if d is not None:
            damage.append(d)

    out = args.out_dir
    pd.concat(calls, ignore_index=True).to_csv(out / "calls.tsv.gz", sep="\t", index=False)
    pd.concat(hits, ignore_index=True).reindex(columns=ct.HIT_COLS).to_csv(
        out / "resistance_hits.tsv.gz", sep="\t", index=False)
    load_profile(args.run_dir, samples, drugs).to_csv(out / "resistance_profile.tsv", sep="\t", index=False)
    pd.DataFrame(qc, columns=ct.QC_COLS).to_csv(out / "qc.tsv", sep="\t", index=False)
    (pd.concat(damage, ignore_index=True) if damage else pd.DataFrame(columns=["sample"])).to_csv(
        out / "oxidative_damage.tsv", sep="\t", index=False)
    (out / "samples.txt").write_text("\n".join(samples) + "\n")
    print(f"[OK] {len(samples)} samples -> {out}")


if __name__ == "__main__":
    main()
