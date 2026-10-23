#!/usr/bin/env python3
# ============================================================
# Compare the per-sample annotated VCFs of two BrSeqTB runs
# (snpeff/<sample>/<sample>_{gatk,norm,lofreq,delly}.vcf.gz).
#
# Works before any cohort step, so it checks per-sample calling
# as soon as both runs have finished a sample.
#
# A record is keyed by CHROM, POS, REF, ALT; FILTER, QUAL, INFO
# and every FORMAT value of the sample are compared exactly
# (QUAL within 1e-3). INFO/ANN is compared too: annotation is
# part of the call set the resistance step reads.
#
# Usage:
#   compare_vcfs.py RUN_A RUN_B [--samples s1,s2] [--out diff.tsv]
#   (RUN_* = directory that contains snpeff/)
# ============================================================

import argparse
import sys
from pathlib import Path

import pysam

CALLERS = ["gatk", "norm", "lofreq", "delly"]

# INFO keys that legitimately differ between identical calls
# (none so far; extend only with a written reason)
IGNORE_INFO = set()


def records(path):
    """CHROM:POS:REF:ALT -> comparable tuple, for every record of a VCF."""
    out = {}
    with pysam.VariantFile(str(path)) as vf:
        sample = list(vf.header.samples)
        for r in vf:
            key = (r.chrom, r.pos, r.ref, ",".join(r.alts or ()))
            info = tuple(sorted((k, str(v)) for k, v in r.info.items() if k not in IGNORE_INFO))
            fmt = tuple(sorted((k, str(v)) for k, v in r.samples[sample[0]].items())) if sample else ()
            qual = None if r.qual is None else round(r.qual, 3)
            out.setdefault(key, []).append((tuple(r.filter.keys()), qual, info, fmt))
    return out


def main():
    ap = argparse.ArgumentParser(description="Compare per-sample annotated VCFs of two BrSeqTB runs")
    ap.add_argument("run_a", type=Path)
    ap.add_argument("run_b", type=Path)
    ap.add_argument("--samples", help="comma-separated (default: every sample with all 4 VCFs in both runs)")
    ap.add_argument("--out", type=Path, help="write differing records to this TSV")
    args = ap.parse_args()

    def vcf(run, s, c):
        return run / "snpeff" / s / f"{s}_{c}.vcf.gz"

    if args.samples:
        samples = args.samples.split(",")
    else:
        samples = sorted(
            d.name for d in (args.run_a / "snpeff").iterdir()
            if all(vcf(args.run_a, d.name, c).exists() and vcf(args.run_b, d.name, c).exists() for c in CALLERS)
        )

    rows = []
    print("sample\tcaller\tn_a\tn_b\tidentical\tchanged\tonly_a\tonly_b")
    for s in samples:
        for c in CALLERS:
            a, b = records(vcf(args.run_a, s, c)), records(vcf(args.run_b, s, c))
            ident = changed = 0
            for k in a.keys() & b.keys():
                if a[k] == b[k]:
                    ident += 1
                else:
                    changed += 1
                    rows.append((s, c, *k, "changed", repr(a[k]), repr(b[k])))
            for k in a.keys() - b.keys():
                rows.append((s, c, *k, "only_a", repr(a[k]), ""))
            for k in b.keys() - a.keys():
                rows.append((s, c, *k, "only_b", "", repr(b[k])))
            print(f"{s}\t{c}\t{len(a)}\t{len(b)}\t{ident}\t{changed}\t"
                  f"{len(a.keys() - b.keys())}\t{len(b.keys() - a.keys())}")

    if args.out:
        with open(args.out, "w") as fh:
            fh.write("sample\tcaller\tchrom\tpos\tref\talt\tstatus\ta\tb\n")
            for r in rows:
                fh.write("\t".join(map(str, r)) + "\n")
    print(f"[{'OK' if not rows else 'DIFF'}] {len(samples)} samples, {len(rows)} differing records", file=sys.stderr)
    return 1 if rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
