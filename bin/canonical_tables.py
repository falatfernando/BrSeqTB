#!/usr/bin/env python3
# ============================================================
# Canonical per-sample tables (shared by export_sample.py and
# validation/harness/normalize_v1.py)
#
# Built from the per-sample outputs under a results root
# (projectDir, or the task scratch in bulk mode):
#
#   calls              resistance/<s>/<s>_{gatk,norm,lofreq,delly}_ANN.xlsx
#   resistance hits    results/resistance/<s>.xlsx
#   resistance profile per drug, from the hits (resistanceSummary logic)
#   qc                 per-module summary CSVs, long format
#   oxidative damage   resistance/<s>/<s>_oxidative_damage.csv
# ============================================================

import os
import sys
from pathlib import Path

import pandas as pd

CALLERS = ["gatk", "norm", "lofreq", "delly"]

CALL_COLS = [
    "sample", "caller", "pos", "ref", "alt", "nt_change", "aa_change",
    "snpeff_effect", "zygosity", "af", "alt_reads", "total_depth", "qual",
    "filter_status", "filter_method",
]

HIT_COLS = [
    "sample", "drug", "gene", "tier", "variant", "effect", "evidence",
    "af", "alt_reads", "heteroresistance", "filter_status", "filter_method", "caller",
]

PROFILE_COLS = ["sample", "drug", "phenotype", "annotation"]

QC_COLS = ["sample", "section", "metric", "value"]

# Per-sample QC CSVs: (section, path relative to the results root)
QC_FILES = [
    ("fastqc", "fastqc/{s}/{s}_fastqc_summary.csv"),
    ("trimmomatic", "trimmomatic/{s}/{s}_trimmomatic_summary.csv"),
    ("bwa", "bwa/{s}/{s}_bwa_summary.csv"),
    ("ntm", "ntmFilter/{s}/{s}_ntm_summary.csv"),
    ("mix_infection", "mixInfection/{s}/{s}_mixinfection_summary.csv"),
    ("oxidative_damage", "resistance/{s}/{s}_lofreq_damage_summary.csv"),
]

# Columns that identify a file, not a measurement
QC_SKIP = {"biosample", "filename", "file"}


def warn(msg):
    print(f"[WARN] {msg}", file=sys.stderr)


def load_calls(root: Path, sample):
    """All four callers' annotated call tables, one row per ALT allele."""
    frames = []
    for caller in CALLERS:
        f = root / "resistance" / sample / f"{sample}_{caller}_ANN.xlsx"
        if not f.exists():
            warn(f"{sample}: missing {f.name}")
            continue
        df = pd.read_excel(f)
        df = df.rename(columns={"position": "pos"})
        df["sample"] = sample
        df["caller"] = caller
        frames.append(df.reindex(columns=CALL_COLS))
    if not frames:
        return pd.DataFrame(columns=CALL_COLS)
    return pd.concat(frames, ignore_index=True)


def load_hits(root: Path, sample):
    """Final per-isolate resistance table (PASS and non-PASS rows)."""
    f = root / "results" / "resistance" / f"{sample}.xlsx"
    if not f.exists():
        warn(f"{sample}: missing results/resistance/{sample}.xlsx")
        return None
    df = pd.read_excel(f)
    df["sample"] = sample
    return df.reindex(columns=HIT_COLS)


def catalogue_drugs(project_dir: Path):
    """Every drug in the WHO catalogue, lower-case (resistance_summary column names)."""
    f = project_dir / "database" / "omsCatalog" / "tbdr_catalogue_master_file.csv"
    return sorted(pd.read_csv(f, usecols=["drug"])["drug"].dropna().str.lower().unique())


def fill_profile(rows, sample, drugs):
    """One row per catalogue drug: a drug without a PASS hit is S with no
    annotation, as resistanceSummary.py fills empty phenotype cells."""
    have = {r["drug"] for r in rows}
    rows = rows + [{"sample": sample, "drug": d, "phenotype": "S", "annotation": ""}
                   for d in drugs if d not in have]
    return sorted(rows, key=lambda r: r["drug"])


def profile_rows(root: Path, sample, drugs):
    """Per-drug phenotype + annotation for one sample, with the exact
    resistanceSummary.process_biosample logic."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import resistanceSummary

    resistanceSummary.INPUT_DIR = str(root / "results" / "resistance")
    data = resistanceSummary.process_biosample(sample)
    rows = []
    if data:
        for key, val in data.items():
            if key == "biosample" or key.endswith("_annotation"):
                continue
            rows.append({"sample": sample, "drug": key, "phenotype": val,
                         "annotation": data.get(f"{key}_annotation", "")})
    return fill_profile(rows, sample, drugs)


def qc_rows(root: Path, sample):
    rows = []

    def add(section, metric, value):
        rows.append({"sample": sample, "section": section, "metric": metric,
                     "value": "" if pd.isna(value) else str(value)})

    for section, pattern in QC_FILES:
        f = root / pattern.format(s=sample)
        if not f.exists():
            warn(f"{sample}: missing {pattern.format(s=sample)}")
            continue
        df = pd.read_csv(f)
        for i, r in df.iterrows():
            # fastqc has one row per read file: prefix metrics with R1/R2
            prefix = f"R{i + 1}." if len(df) > 1 else ""
            for col, val in r.items():
                if col not in QC_SKIP:
                    add(section, prefix + col, val)

    # lineage: collapse exactly as qcSummary.process_lineage does
    f = root / "lineage" / sample / f"{sample}_lineage_summary.csv"
    if f.exists():
        df = pd.read_csv(f, usecols=["LINEAGE", "LINEAGE_DETAILS", "COMMENT"])
        for col in ["LINEAGE", "LINEAGE_DETAILS", "COMMENT"]:
            add("lineage", col, ";".join(sorted(df[col].dropna().astype(str).unique())))
    else:
        warn(f"{sample}: missing lineage summary")

    # tbdrRCov: resistance positions with DP < 10, as a sorted position list
    f = root / "tbdrRCov" / sample / f"{sample}_tbdrRcov_summary.csv"
    if f.exists():
        df = pd.read_csv(f)
        add("tbdr_rcov", "n_low_cov_positions", len(df))
        add("tbdr_rcov", "low_cov_positions", ";".join(str(p) for p in sorted(df["POS"].unique())))
    else:
        warn(f"{sample}: missing tbdrRCov summary")

    return rows


def load_damage(root: Path, sample):
    """Calls removed by the oxidative-damage guard (may be absent)."""
    f = root / "resistance" / sample / f"{sample}_oxidative_damage.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    d.insert(0, "sample", sample)
    return d
