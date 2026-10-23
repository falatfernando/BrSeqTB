# Validation

Proves that changes to BrSeqTB do not change biological results without us knowing, and measures exactly what changed when they do.

## Validation set

`validation_set.tsv` (96 isolates):

- **20260729P** (36): an in-house Illumina run with known expected results.
- **bdq60** (60): a stratified pick from the BDQ dataset (`bdq_warehouse.db`, table `bdq_metadata`). It covers BDQ R/S/borderline across sources, all lineages, rare species, IS6110 in Rv0678, low quality, and the smallest and largest read files. `pick_bdq60.py` regenerates it (fixed seed); `bdq60_metadata.tsv` has the metadata.

## Baseline

The f3ccebd code runs on the validation set in cohort mode, using the exact env in `envs/brseqtb.lock.txt`. The run directory is `/mnt/mgd_storage/brseqtb_bulk/baseline_f3ccebd`.

Baseline notes (run of 2026-10-23):

- **SRR34768910 (IAL) is excluded from the baseline.** Its `_1.fastq.gz` is corrupt partway through (`gzip -t`: invalid compressed data; about 625k lines vs 3.1M in R2), and the old code stops the whole run on any task error. It stays in the validation set as a known-bad input: the bulk pipeline must reject it cleanly.
- The BDQ reads are symlinked under Illumina-style names (`<acc>_S1_L001_R{1,2}_001.fastq.gz`), because f3ccebd only accepts that naming. Only the read-group ID/PU strings differ from an ENA-named run.
- `fastqc/` is a symlink to NVMe: `unzip` cannot set file attributes on the mergerfs mount.
- After two forced stops, LoFreq folders without a final VCF were moved to `stale_partial/` before resuming. f3ccebd's `lofreq indelqual` refuses to overwrite a partial BAM.

## Harness

```bash
PY=~/.nextflow_conda_cache/env-32c0894fbe15ec0ef7251acbaeb9e8fd/bin/python

# 1. normalize each run into canonical tables
$PY -I validation/harness/normalize_v1.py RUN_DIR OUT/run_a
# 2. compare two normalized runs
$PY -I validation/harness/compare.py OUT/run_a OUT/run_b OUT/cmp --label-a baseline --label-b new [--ignore filter_method]
```

Canonical tables, one row per:

| table | key | content |
|---|---|---|
| `calls.tsv.gz` | sample, caller, pos, ref, alt | annotation, zygosity, AF, depth, QUAL, filter status for all four callers (gatk, norm, lofreq, delly) |
| `resistance_hits.tsv.gz` | sample, drug, variant | final per-isolate table (`results/resistance/<bs>.xlsx`) |
| `resistance_profile.tsv` | sample, drug | phenotype + annotation (`resistance_summary.xlsx`) |
| `qc.tsv` | sample, section, metric | fastqc, trimmomatic, bwa, NTM, mixed infection, oxidative damage, lineage, low-coverage R positions |

`compare.py` writes `summary.md` (headline counts: phenotype transitions, calls identical/changed/only-in-one-run per caller, both overall and for PASS calls) plus one `*_diff.tsv` per table listing every differing row with both values. AF and QUAL are compared within a small tolerance (1e-6, 1e-3); everything else must match exactly.

The bulk pipeline writes these canonical tables directly, so it needs no normalizer.
