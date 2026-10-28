# BrSeqTB bulk results database

This SQLite database holds the results of `bulk.nf` runs: resistance profiles, every variant call (WHO catalogue or not), QC metrics and IS6110 insertion sites, with one isolate per sample ID. It is built and kept up to date by `bin/load_sqlite.py` from the per-sample result folders, and it is never written by the pipeline itself.

```bash
python bin/load_sqlite.py <outdir> results.db \
    --metadata-db ~/Repositories/bdq_warehouse/production/bdq_warehouse.db \
    --metadata-table bdq_metadata --metadata-key accession
```

- **Idempotent:** a result already loaded is skipped; a re-run sample replaces all of its rows. Each sample and task is loaded in one transaction, so an interrupted load never leaves half a sample.
- **Safe while the run is going:** only published result folders are read (`<id>.partial` folders are ignored).
- **Keep the database on a local disk** (ext4/SSD). SQLite locking is not reliable on FUSE or network filesystems (mergerfs, NTFS-3g, NFS).
- `--prefix brseqtb_` names every table `brseqtb_<table>`, for loading into a database shared with other tables.

## Overview

```
isolate_metadata (1) ──┬── (1) samples             main task: status, settings, QC summary
  sample = accession   ├── (n) variant_calls       every call of GATK, norm, LoFreq, Delly
                       ├── (n) resistance_hits     WHO catalogue matches (final per-isolate table)
                       ├── (n) resistance_profile  one row per drug
                       ├── (n) quality_control     QC metrics, long format
                       ├── (n) oxidative_damage    calls removed by the damage guard
                       ├── (1) is6110_status       IS Sentinel task: status, counts
                       ├── (n) is6110_candidates   IS6110 junction candidates
                       ├── (n) is6110_junctions    candidates collapsed within 10 bp
                       └── (n) failures            isolates a task could not process
```

Every table has a `sample` column holding the isolate's run accession. It is the same value as `bdq_metadata.accession` and the same as the sample ID in the manifest. All joins use `sample`.

The main task (`samples` and the tables built from its outputs) and the IS Sentinel task (`is6110_*`) finish independently, so an isolate can appear in one before the other.

## Tables

### isolate_metadata

A copy of the external metadata table (`--metadata-table`, default `bdq_metadata`), with `sample` added as a copy of the key column. It is replaced on every load that passes `--metadata-db`, so it always matches the source. Its columns are those of the source table; for `bdq_metadata`: `source, accession, country, pDST_phenotype, method, quality, critical_value, mic, species, lineage, sublineage, n_bdq_tests, pDST_all, pDST_discordant, pDST_consensus`.

### samples

One row per isolate that the main task finished (`<id>.sample.json`).

| Column | Meaning |
| --- | --- |
| sample | isolate ID |
| status | `done` |
| finished_utc | when the task finished (ISO 8601, UTC); a re-run sample gets a new value |
| pipeline_commit | BrSeqTB git commit that produced the result |
| filter_mode | `per_sample`: GATK/norm calls use the sample's own filters only |
| lofreq_min_af | LoFreq allele-frequency filter (`0.00` = none) |
| who_catalogue | WHO mutation catalogue version (`WHO-UCN-TB-2023.7`) |
| n_pass_hits | rows of `resistance_hits` with `filter_status = 'PASS'` |
| meta_json | the full `sample.json`: phenotypes, QC block, call counts per caller, step timings |

### variant_calls

**Every call of every caller**, catalogue or not, one row per isolate × caller × ALT allele. This is where non-catalogue mutations are; `resistance_hits` is the catalogue subset. The verbatim snpEff-annotated VCFs are kept next to the results (`samples/<id>/vcf/`).

| Column | Meaning |
| --- | --- |
| sample | isolate ID |
| caller | `gatk` (HaplotypeCaller, diploid), `norm` (the GATK calls split/left-aligned with bcftools norm + vt decompose_blocksub), `lofreq` (low-frequency variants), `delly` (structural variants) |
| pos | position on NC_000962.3 (1-based) |
| ref, alt | alleles; Delly ALTs can be symbolic (`<DEL>`, `<INV>`, `<DUP>`) |
| gene | gene name taken from `nt_change` (text before `_c.`, `_n.`, `_p.`, `_g.`, `_m.`); `PE_PGRS1&PE_PGRS2`-style names for multi-gene effects; empty when snpEff gave no HGVS (about 1–2% of calls, mostly non-coding transcript variants). Database only, not in the exported files |
| nt_change | HGVS c./n. of the first snpEff annotation with a gene or HGVS, `gene_HGVS.c`, e.g. `rpoB_c.1349C>T` |
| aa_change | HGVS p. of the same annotation, e.g. `rpoB_p.Ser450Leu` |
| snpeff_effect | snpEff effect of that annotation, e.g. `missense_variant`, `upstream_gene_variant` |
| zygosity | `HOM` (AF ≥ 0.90) or `HET`; empty for Delly |
| af | allele frequency: GATK/norm `AD[alt] / sum(AD)`, LoFreq `INFO/AF`; empty for Delly |
| alt_reads | GATK/norm `AD[alt]`, LoFreq `DP4[2] + DP4[3]`; empty for Delly |
| total_depth | GATK/norm `sum(AD)`, LoFreq `INFO/DP`; empty for Delly |
| qual | VCF QUAL |
| filter_status | `PASS`, or the failed checks joined by `;` (see below) |
| filter_method | `per_sample` |

`filter_status` checks:

| Caller | PASS requires | Failure codes |
| --- | --- | --- |
| gatk, norm | VCF FILTER PASS, ≥ 3 ALT reads, depth ≥ 10 | GATK filter names (`QD2`, `QUAL30`, `SOR3`, `FS60`, `MQ40`, `MQRankSum`, `ReadPosRankSum`, `FS200`), `ALT_READS_BELOW_3`, `DP_FAIL`, `AF_FAIL` (AF missing) |
| lofreq | VCF FILTER PASS, ≥ 3 ALT reads, depth ≥ 10 | LoFreq filter names, `ALT_READS_BELOW_3`, `DP_FAIL`, `OXIDATIVE_DAMAGE_SUSPECT` (see `oxidative_damage`) |
| delly | VCF FILTER PASS | `LowQual` |

### resistance_hits

The final per-isolate resistance table: `variant_calls` matched to the WHO catalogue by coordinate, HGVS c. or HGVS p. It is deduplicated per drug and variant: a PASS row wins, then caller priority gatk > norm > lofreq > delly. Non-PASS rows are kept.

| Column | Meaning |
| --- | --- |
| sample | isolate ID |
| drug | drug name as in the catalogue (`Rifampicin`, `Bedaquiline`, ...) |
| gene, tier | catalogue gene and tier |
| variant | catalogue variant name, e.g. `rpoB_p.Ser450Leu` |
| effect | catalogue effect |
| evidence | WHO confidence grading: `R` assoc. w R, `r` assoc. w R – interim, `u` uncertain significance, `s` not assoc. w R – interim, `S` not assoc. w R |
| af, alt_reads | as in `variant_calls` |
| heteroresistance | `HOM` / `HET` (zygosity of the call) |
| filter_status, filter_method, caller | of the call that was kept |

### resistance_profile

One row per isolate × catalogue drug (all 15 drugs, always).

| Column | Meaning |
| --- | --- |
| sample | isolate ID |
| drug | lower-case drug name (`rifampicin`, ...) |
| phenotype | `R`, `r`, `u`, `S` or `s`, from the PASS rows of `resistance_hits` for that drug, by priority R > r > u > S > s |
| annotation | the PASS variants behind it, `variant_flagX` joined by `,` (`flagR`, `flagr`, `flagu`, `flagnr` = s, `flagnR` = S) |

> **A drug with no PASS catalogue variant is `S`.** It means no variant graded R, r or u was called. It is not evidence of susceptibility when the positions were not covered: check `v_qc.mean_depth` and `n_low_cov_resistance_positions` before reading `S` as susceptible.

### quality_control

QC metrics in long format, one row per isolate × section × metric. `value` is text; `v_qc` has the common metrics as numbers.

| section | metrics |
| --- | --- |
| fastqc | per read file, prefixed `R1.` / `R2.`: `total_sequences, poor_quality_sequences, sequence_length, percent_GC, mean_per_base_quality, status` |
| trimmomatic | `input_read_pairs, both_surviving, both_surviving_pct, forward_only, forward_only_pct, reverse_only, reverse_only_pct, dropped, dropped_pct, status` |
| bwa | `total_reads, mapped_reads, mapped_pct, duplicates_pct, properly_paired_pct, coverage_pct` (% of genome covered), `mean_depth`, `status` |
| ntm | NTM check at rrs 1472307: `genotype, position, allele_frequency, depth, status` |
| mix_infection | `total_snps, heterozygous_snps, proportion, status` (`MIXED` when proportion ≥ 0.32, else `NOT MIXED`) |
| oxidative_damage | LoFreq damage score: `low_af_snvs, low_af_damage_snvs, damage_fraction, af_max, min_calls, min_fraction, status` |
| lineage | `LINEAGE, LINEAGE_DETAILS, COMMENT` |
| tbdr_rcov | resistance positions with depth < 10: `n_low_cov_positions, low_cov_positions` (`;`-separated) |

Status thresholds (unchanged from the full pipeline): FastQC FAIL if mean quality < 20 or GC outside 62–68%; Trimmomatic FAIL if < 75% of pairs survive; BWA FAIL if < 95% mapped or < 90% of the genome covered. **None of these checks sequencing depth**; use `mean_depth`.

### oxidative_damage

Calls removed from `resistance_hits` by the oxidative-damage guard. These are LoFreq G>T/C>A calls with AF < 0.05 and a stop-gained or start-lost effect, in an isolate whose low-AF SNVs are mostly G>T/C>A. One row per removed call, with the isolate's damage score.

### is6110_status

One row per isolate that the IS Sentinel task finished (`<id>.issentinel.json`): `sample, status, finished_utc, method, n_candidates, n_junctions, meta_json` (gates and step timings).

### is6110_candidates

IS6110 insertion candidates from IS Sentinel (`extract_is_candidates.py`). Reads are aligned to H37Rv with its 16 IS6110 copies masked plus an IS6110 decoy contig; a candidate is a Delly junction between the genome and the decoy that passes the PE/SR gates.

| Column | Meaning |
| --- | --- |
| sample | isolate ID |
| chrom, pos | insertion site on the genome |
| detection_method | `Decoy (New Insertion)`, `Decoy (Reference Copy)` (within 50 bp of an H37Rv copy), or the other strategies of IS Sentinel |
| sv_type | Delly SV type of the junction |
| pe, sr | Delly paired-end / split-read support |
| dv, rv, dr, rr | Delly variant / reference pair and junction counts |
| vaf | (dv + rv) / (dv + rv + dr + rr) |
| is_heteroresistant | 0.05 ≤ vaf ≤ 0.9 |
| is_precise | Delly PRECISE flag |
| orientation | `Forward` / `Reverse` |
| overlapping_genes, nearest_gene, dist_to_nearest | annotation from the H37Rv GenBank file |
| info | Delly INFO string |

### is6110_junctions

Candidates within 10 bp collapsed into one site (`compile_results.py`), per isolate and chromosome: `sample, chrom, dsb_breakpoint_a, dsb_breakpoint_b, orientation, overlapping_genes, nearest_gene, dist_to_nearest, pe_a, pe_b, sr_a, sr_b, dv, rv, dr, rr, vaf, is_heteroresistant, precision_a, precision_b, detection_method`. PE/SR are summed over the cluster. Here `is_heteroresistant` means 0.05 ≤ vaf ≤ **0.35**, which is narrower than in `is6110_candidates`; the two thresholds come from IS Sentinel unchanged.

### failures

Isolates a task could not process, from `<id>.failed.json`. Primary key `(sample, task)`.

| Column | Meaning |
| --- | --- |
| task | `bulk` (main task) or `issentinel` |
| status | `bad_input` (reads failed the integrity check; never retried) or `failed` (still failing after 2 retries) |
| step | the step that failed (`check_reads`, `bwa`, `gatk_vcf`, ...) |
| exit_code, reason | exit code; reason for bad input (e.g. `corrupt gzip stream`) |
| meta_json | the full record, including the last stderr lines |

## Views

Rebuilt after every load.

| View | Content |
| --- | --- |
| v_profile | one row per isolate, one phenotype column per drug |
| v_qc | one row per isolate: `mean_depth, coverage_pct, mapped_pct, duplicates_pct, n_low_cov_resistance_positions` (numbers), `lineage`, `bwa_status, trimmomatic_status, fastqc_r1_status, fastqc_r2_status, ntm_status, mix_infection_status, mix_het_proportion, oxidative_damage_status` |
| v_pass_calls | `variant_calls` rows with `filter_status = 'PASS'`, plus the isolate's `mean_depth, coverage_pct, lineage` |

## Example queries

```sql
-- Bedaquiline: BrSeqTB call vs phenotypic DST, isolates with >= 20x
SELECT m.sample, m.source, m.pDST_consensus, p.bedaquiline, q.mean_depth
FROM isolate_metadata m
JOIN v_profile p USING (sample)
JOIN v_qc q USING (sample)
WHERE q.mean_depth >= 20;

-- Every PASS mutation in Rv0678 / mmpL5, catalogue or not, one row per isolate and variant
SELECT sample, pos, ref, alt, aa_change, group_concat(caller) AS callers, max(af) AS af
FROM v_pass_calls
WHERE gene IN ('Rv0678', 'mmpL5') AND mean_depth >= 20
GROUP BY sample, pos, ref, alt;

-- Non-catalogue PASS mutations in Rv0678: in variant_calls but not in resistance_hits
-- (approximate: matches catalogue names on HGVS p. only; resistance_hits has no position)
SELECT c.sample, c.pos, c.aa_change, c.af
FROM v_pass_calls c
WHERE c.gene = 'Rv0678' AND c.caller = 'gatk'
  AND NOT EXISTS (SELECT 1 FROM resistance_hits h
                  WHERE h.sample = c.sample AND h.variant = c.aa_change);

-- IS6110 insertions in the mmpL5-Rv0678 region (775586-779487)
SELECT sample, dsb_breakpoint_a, orientation, nearest_gene, pe_a, sr_a, vaf, detection_method
FROM is6110_junctions
WHERE chrom = 'NC_000962.3' AND dsb_breakpoint_a BETWEEN 775586 AND 779487;

-- Isolates still to check: failed, or below 20x
SELECT sample, task, status, step, reason FROM failures
UNION ALL
SELECT sample, 'qc', 'low_depth', NULL, printf('%.1fx', mean_depth) FROM v_qc WHERE mean_depth < 20;

-- Query together with the warehouse, without copying
ATTACH '/home/falat/Repositories/bdq_warehouse/production/bdq_warehouse.db' AS w;
SELECT p.sample, p.bedaquiline, w.bdq_pipeline_calls.magma_call
FROM v_profile p JOIN w.bdq_pipeline_calls ON w.bdq_pipeline_calls.accession = p.sample;
```
