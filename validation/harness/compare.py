#!/usr/bin/env python3
# ============================================================
# Compare two normalized BrSeqTB runs (see normalize_v1.py) and
# report every difference.
#
# Outputs in OUT_DIR:
#   summary.md                 headline numbers
#   calls_diff.tsv.gz          calls added / removed / changed
#   resistance_hits_diff.tsv   final per-isolate table differences
#   resistance_profile_diff.tsv per sample x drug phenotype differences
#   qc_diff.tsv                QC metric differences
#
# Usage:
#   compare.py A_DIR B_DIR OUT_DIR [--label-a baseline] [--label-b new]
#              [--ignore filter_method,...]
# ============================================================

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CALL_KEY = ["sample", "caller", "pos", "ref", "alt"]
CALL_FIELDS = ["nt_change", "aa_change", "snpeff_effect", "zygosity", "af",
               "alt_reads", "total_depth", "qual", "filter_status", "filter_method"]

HIT_KEY = ["sample", "drug", "variant"]
HIT_FIELDS = ["gene", "tier", "effect", "evidence", "af", "alt_reads",
              "heteroresistance", "filter_status", "filter_method", "caller"]

PROFILE_KEY = ["sample", "drug"]
PROFILE_FIELDS = ["phenotype", "annotation"]

QC_KEY = ["sample", "section", "metric"]
QC_FIELDS = ["value"]

# Numeric comparison tolerances (absolute); everything else is compared as text
TOLERANCE = {"af": 1e-6, "qual": 1e-3, "value": 1e-6}


def read(path):
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)


def same(a, b, field):
    """Element-wise equality of two string Series, numeric-aware."""
    eq = a == b
    tol = TOLERANCE.get(field)
    if tol is not None:
        na = pd.to_numeric(a, errors="coerce")
        nb = pd.to_numeric(b, errors="coerce")
        both = na.notna() & nb.notna()
        eq = eq | (both & (np.abs(na - nb) <= tol))
    else:
        # integers written as 12 vs 12.0 by different writers
        na = pd.to_numeric(a, errors="coerce")
        nb = pd.to_numeric(b, errors="coerce")
        eq = eq | (na.notna() & nb.notna() & (na == nb))
    return eq


def diff_table(a, b, key, fields, ignore=()):
    """Outer-join two tables on key and classify each row.

    Returns (diff rows, per-row status Series over the full join).
    Duplicate keys inside one run are kept apart by occurrence number.
    """
    a = a.copy()
    b = b.copy()
    a["_occ"] = a.groupby(key).cumcount()
    b["_occ"] = b.groupby(key).cumcount()
    k = key + ["_occ"]
    m = a[k + fields].merge(b[k + fields], on=k, how="outer",
                            suffixes=("_a", "_b"), indicator=True)

    changed = pd.Series([[] for _ in range(len(m))], index=m.index)
    both = m["_merge"] == "both"
    for f in fields:
        if f in ignore:
            continue
        ne = both & ~same(m[f + "_a"].fillna(""), m[f + "_b"].fillna(""), f)
        for i in m.index[ne]:
            changed[i].append(f)

    status = np.select(
        [m["_merge"] == "left_only", m["_merge"] == "right_only", changed.str.len() > 0],
        ["only_a", "only_b", "changed"], default="identical")
    m["status"] = status
    m["changed_fields"] = changed.str.join(",")
    m = m.drop(columns="_merge")
    out = m[m["status"] != "identical"].drop(columns="_occ")
    cols = key + ["status", "changed_fields"] + [c for c in out.columns
                                                 if c not in key + ["status", "changed_fields"]]
    return out[cols], m


def count(m, by):
    t = m.groupby(by)["status"].value_counts().unstack(fill_value=0)
    for c in ["identical", "changed", "only_a", "only_b"]:
        if c not in t:
            t[c] = 0
    t = t[["identical", "changed", "only_a", "only_b"]]
    t["n_a"] = t["identical"] + t["changed"] + t["only_a"]
    t["n_b"] = t["identical"] + t["changed"] + t["only_b"]
    return t


def md_table(df):
    df = df.reset_index()
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    rows = ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep] + rows)


def main():
    ap = argparse.ArgumentParser(description="Compare two normalized BrSeqTB runs")
    ap.add_argument("a_dir", type=Path)
    ap.add_argument("b_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--ignore", default="",
                    help="comma-separated fields to leave out of 'changed' (still written to the diff)")
    args = ap.parse_args()
    ignore = {f for f in args.ignore.split(",") if f}
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    A, B = args.label_a, args.label_b

    sa = set(read_lines(args.a_dir / "samples.txt"))
    sb = set(read_lines(args.b_dir / "samples.txt"))
    common = sa & sb

    def load(name):
        a = read(args.a_dir / name)
        b = read(args.b_dir / name)
        return a[a["sample"].isin(common)], b[b["sample"].isin(common)]

    md = [f"# BrSeqTB run comparison: {A} vs {B}", ""]
    md.append(f"- Samples: {len(common)} in both, {len(sa - sb)} only in {A}, {len(sb - sa)} only in {B}")
    if sa ^ sb:
        md.append(f"  - only in {A}: {', '.join(sorted(sa - sb)) or '-'}")
        md.append(f"  - only in {B}: {', '.join(sorted(sb - sa)) or '-'}")
    if ignore:
        md.append(f"- Fields not counted as changes: {', '.join(sorted(ignore))}")
    md.append(f"- `only_a` = present only in {A}; `only_b` = present only in {B}")
    md.append("")

    # --- resistance profile (headline) ---
    pa, pb = load("resistance_profile.tsv")
    d, m = diff_table(pa, pb, PROFILE_KEY, PROFILE_FIELDS, ignore)
    d.to_csv(out / "resistance_profile_diff.tsv", sep="\t", index=False)
    both = m[m["status"].isin(["identical", "changed"])]
    pheno_same = (both["phenotype_a"] == both["phenotype_b"]).sum()
    md.append("## Resistance profile (sample x drug)")
    md.append("")
    md.append(f"Phenotype identical in **{pheno_same} / {len(both)}** sample-drug pairs; "
              f"annotation string identical in {(both['annotation_a'] == both['annotation_b']).sum()}.")
    md.append("")
    trans = both.groupby(["phenotype_a", "phenotype_b"]).size().rename("n")
    trans = trans[trans.index.get_level_values(0) != trans.index.get_level_values(1)]
    if len(trans):
        md.append(f"Phenotype transitions ({A} -> {B}):")
        md.append("")
        md.append(md_table(trans.to_frame()))
        md.append("")
        per_drug = both[both["phenotype_a"] != both["phenotype_b"]].groupby("drug").size().rename("n_changed")
        md.append(md_table(per_drug.to_frame()))
        md.append("")

    # --- final per-isolate table ---
    ha, hb = load("resistance_hits.tsv.gz")
    d, m = diff_table(ha, hb, HIT_KEY, HIT_FIELDS, ignore)
    d.to_csv(out / "resistance_hits_diff.tsv", sep="\t", index=False)
    md.append("## Final per-isolate resistance table (sample x drug x variant)")
    md.append("")
    md.append(md_table(count(m.assign(table="all"), "table")))
    pass_any = m[(m["filter_status_a"] == "PASS") | (m["filter_status_b"] == "PASS")]
    md.append("")
    md.append("Rows that PASS in either run:")
    md.append("")
    md.append(md_table(count(pass_any.assign(table="PASS"), "table")))
    md.append("")
    md.append(field_breakdown(m))

    # --- calls ---
    ca, cb = load("calls.tsv.gz")
    d, m = diff_table(ca, cb, CALL_KEY, CALL_FIELDS, ignore)
    d.to_csv(out / "calls_diff.tsv.gz", sep="\t", index=False)
    md.append("## Variant calls (sample x caller x allele)")
    md.append("")
    md.append(md_table(count(m, "caller")))
    md.append("")
    pass_any = m[(m["filter_status_a"] == "PASS") | (m["filter_status_b"] == "PASS")]
    md.append("Calls that PASS in either run:")
    md.append("")
    md.append(md_table(count(pass_any, "caller")))
    md.append("")
    md.append(field_breakdown(m))

    # --- QC ---
    qa, qb = load("qc.tsv")
    d, m = diff_table(qa, qb, QC_KEY, QC_FIELDS, ignore)
    d.to_csv(out / "qc_diff.tsv", sep="\t", index=False)
    md.append("## QC metrics")
    md.append("")
    md.append(md_table(count(m, "section")))
    md.append("")

    (out / "summary.md").write_text("\n".join(md) + "\n")
    print((out / "summary.md").read_text())


def field_breakdown(m):
    ch = m.loc[m["status"] == "changed", "changed_fields"]
    if ch.empty:
        return ""
    counts = ch.str.split(",").explode().value_counts().rename("rows").to_frame()
    counts.index.name = "changed field"
    return "Changed rows by field:\n\n" + md_table(counts) + "\n"


def read_lines(path):
    return [l.strip() for l in open(path) if l.strip()]


if __name__ == "__main__":
    main()
