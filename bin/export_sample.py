#!/usr/bin/env python3
# ============================================================
# Export one biosample's results as the canonical tables (bulk mode)
#
# Usage: python export_sample.py <biosample ID> <out dir> [timings.tsv]
# Input:  per-sample outputs under $BRSEQTB_OUT (default projectDir)
# Output: <out dir>/<id>.calls.tsv.gz
#         <out dir>/<id>.resistance_hits.tsv
#         <out dir>/<id>.resistance_profile.tsv
#         <out dir>/<id>.qc.tsv
#         <out dir>/<id>.oxidative_damage.tsv   (only if calls were flagged)
#         <out dir>/<id>.sample.json            (status, run settings, timings)
#
# The tables are built by canonical_tables.py, the same code the
# validation harness uses, so bulk outputs compare 1:1 with v1 runs.
# ============================================================

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canonical_tables as ct  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_ROOT = Path(os.environ.get("BRSEQTB_OUT", PROJECT_DIR))

CATALOGUE = "WHO-UCN-TB-2023.7"


def git_commit():
    try:
        return subprocess.run(["git", "-C", str(PROJECT_DIR), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit("Usage: python export_sample.py <biosample ID> <out dir> [timings.tsv]")

    sample, out_dir = sys.argv[1], Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    hits = ct.load_hits(OUT_ROOT, sample)
    if hits is None:
        sys.exit(f"[ERROR] {sample}: final resistance table missing, nothing to export")

    calls = ct.load_calls(OUT_ROOT, sample)
    missing = sorted(set(ct.CALLERS) - set(calls["caller"].unique()))
    if missing:
        sys.exit(f"[ERROR] {sample}: call tables missing for {', '.join(missing)}")

    profile = ct.profile_rows(OUT_ROOT, sample, ct.catalogue_drugs(PROJECT_DIR))
    qc = ct.qc_rows(OUT_ROOT, sample)
    damage = ct.load_damage(OUT_ROOT, sample)

    calls.to_csv(out_dir / f"{sample}.calls.tsv.gz", sep="\t", index=False)
    hits.to_csv(out_dir / f"{sample}.resistance_hits.tsv", sep="\t", index=False)
    pd.DataFrame(profile, columns=ct.PROFILE_COLS).to_csv(
        out_dir / f"{sample}.resistance_profile.tsv", sep="\t", index=False)
    pd.DataFrame(qc, columns=ct.QC_COLS).to_csv(out_dir / f"{sample}.qc.tsv", sep="\t", index=False)
    if damage is not None and not damage.empty:
        damage.to_csv(out_dir / f"{sample}.oxidative_damage.tsv", sep="\t", index=False)

    # QC block: headline values and every module's own status (no new thresholds)
    qv = {(r["section"], r["metric"]): r["value"] for r in qc}
    # fastqc has one status per read file (R1.status, R2.status)
    statuses = {(sec if met == "status" else f"{sec}.{met}"): val
                for (sec, met), val in qv.items() if met.endswith("status")}
    qc_block = {
        "mean_depth": qv.get(("bwa", "mean_depth")),
        "coverage_pct": qv.get(("bwa", "coverage_pct")),
        "mapped_pct": qv.get(("bwa", "mapped_pct")),
        "n_low_cov_resistance_positions": qv.get(("tbdr_rcov", "n_low_cov_positions")),
        "lineage": qv.get(("lineage", "LINEAGE")),
        "statuses": statuses,
        # mixInfection reports NOT MIXED / MIXED instead of PASS / FAIL
        "not_pass": sorted(f"{k}:{v}" for k, v in statuses.items() if v not in ("PASS", "NOT MIXED")),
    }

    timings = {}
    if len(sys.argv) == 4 and Path(sys.argv[3]).exists():
        t = pd.read_csv(sys.argv[3], sep="\t")
        timings = dict(zip(t["step"], t["seconds"].astype(int)))

    meta = {
        "sample": sample,
        "status": "done",
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pipeline_commit": git_commit(),
        "filter_mode": os.environ.get("BRSEQTB_FILTER_MODE", "cohort"),
        "lofreq_min_af": os.environ.get("BRSEQTB_LOFREQ_MIN_AF", ""),
        "who_catalogue": CATALOGUE,
        "n_calls": {c: int((calls["caller"] == c).sum()) for c in ct.CALLERS},
        "n_pass_hits": int((hits["filter_status"] == "PASS").sum()),
        "phenotypes": {r["drug"]: r["phenotype"] for r in profile},
        "qc": qc_block,
        "step_seconds": timings,
    }
    (out_dir / f"{sample}.sample.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"[OK] {sample} exported to {out_dir}")


if __name__ == "__main__":
    main()
