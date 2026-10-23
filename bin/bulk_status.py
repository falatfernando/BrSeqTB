#!/usr/bin/env python3
# ============================================================
# Progress of a bulk.nf run
#
# Usage: python bulk_status.py <manifest.tsv> <outdir> [--parallel 5]
# Reads:  <outdir>/samples/<id>/<id>.sample.json | <id>.failed.json
# Writes: <outdir>/failed.tsv  (sample, status, step, exit_code, reason)
# Prints: done / failed / pending counts, per-step time (median and
#         p95, seconds) and an estimate of the time left.
# ============================================================

import argparse
import json
import math
import statistics
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Progress of a bulk.nf run")
    ap.add_argument("manifest", type=Path)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--parallel", type=int, default=5, help="samples running at once (for the estimate)")
    args = ap.parse_args()

    samples = [l.strip() for l in args.manifest.read_text().splitlines()[1:] if l.strip()]
    root = args.outdir / "samples"

    done, failed, pending = [], [], []
    for s in samples:
        d = root / s
        if (d / f"{s}.sample.json").exists():
            done.append(json.loads((d / f"{s}.sample.json").read_text()))
        elif (d / f"{s}.failed.json").exists():
            failed.append(json.loads((d / f"{s}.failed.json").read_text()))
        else:
            pending.append(s)

    with open(args.outdir / "failed.tsv", "w") as fh:
        fh.write("sample\tstatus\tstep\texit_code\treason\n")
        for f in failed:
            fh.write(f"{f['sample']}\t{f['status']}\t{f['step']}\t{f['exit_code']}\t{f.get('reason', '')}\n")

    n = len(samples)
    print(f"samples: {n}  done: {len(done)} ({100 * len(done) / max(n, 1):.1f}%)  "
          f"failed: {len(failed)}  pending: {len(pending)}")
    if failed:
        by = {}
        for f in failed:
            by[f"{f['status']}:{f['step']}"] = by.get(f"{f['status']}:{f['step']}", 0) + 1
        print("failures by step: " + ", ".join(f"{k} {v}" for k, v in sorted(by.items())))
        print(f"failed list: {args.outdir / 'failed.tsv'}")

    totals = [sum(d.get("step_seconds", {}).values()) for d in done if d.get("step_seconds")]
    if totals:
        steps = sorted({k for d in done for k in d.get("step_seconds", {})})
        print("\nstep seconds (median / p95):")
        for k in steps:
            v = sorted(d["step_seconds"][k] for d in done if k in d.get("step_seconds", {}))
            p95 = v[max(0, math.ceil(0.95 * len(v)) - 1)]  # nearest-rank
            print(f"  {k:<18} {statistics.median(v):>7.0f} / {p95:>7.0f}")
        # Steps after BWA run in parallel, so the sum overstates wall time; the
        # estimate uses the sum as an upper bound
        per_sample = statistics.mean(totals)
        left_h = per_sample * len(pending) / args.parallel / 3600
        print(f"\nmean summed step time: {per_sample / 60:.1f} min/sample; "
              f"upper-bound time left at {args.parallel} in parallel: {left_h:.1f} h ({left_h / 24:.1f} days)")


if __name__ == "__main__":
    main()
