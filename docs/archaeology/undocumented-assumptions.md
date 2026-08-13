# Inventory of Undocumented Assumptions — BrSeqTB

**Document ID**: `ASSUMP-001`  
**Repository**: `LaPAM-USP/BrSeqTB`  
**Date**: August 13, 2026  
**Pipeline Framework**: Nextflow DSL2  

---

## 1. Overview

This document catalogs implicit, unstated, or poorly documented assumptions identified across the codebase. These assumptions govern data formatting, working directories, genomic coordinates, and analytical boundaries.

---

## 2. Undocumented Assumptions Register

### UA-001: Execution Working Directory Must Be the Repository Root
- **Assumption**: Every script and Nextflow task assumes that the current working directory (`CWD`) is the root of the cloned repository, or resolves paths relative to `$(dirname "$0")/..`.
- **Evidence**: `main.nf` explicitly calls `cd "${projectDir}"` in all 30 process blocks; Python scripts calculate `PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))`.
- **Where Observed**: [main.nf:37, 55, 73](file:///home/falat/Repositories/BrSeqTB/main.nf#L37), [bin/resistanceTarget.py:25](file:///home/falat/Repositories/BrSeqTB/bin/resistanceTarget.py#L25), [bin/snpMatrix.py:38](file:///home/falat/Repositories/BrSeqTB/bin/snpMatrix.py#L38).
- **Confidence**: `HIGH`
- **Potential Consequence**: Executing scripts from outside the repository root or attempting to run the workflow in distributed cloud environments where the project directory is read-only will cause immediate failures.
- **Requires Human Confirmation?**: No (Code-evident).

---

### UA-002: Reference Genome Chromosome Identifier Must Strictly Match `NC_000962.3`
- **Assumption**: The pipeline assumes the chromosome name in all VCFs, BAMs, and BED files is exactly `NC_000962.3`.
- **Evidence**:
  - `omsCatalog.py:30`: `REFERENCE_NAME = "NC_000962.3"`
  - `tbdrRCov.py:30`: `REFERENCE_NAME = "NC_000962.3"`
  - `ntmFilter.sh:40`: `REF_CHR="NC_000962.3"`
  - `cohort.sh:93`: `echo -e "NC_000962.3\t1\t4411532" > "$BED"`
- **Where Observed**: Across multiple scripts in `bin/`.
- **Confidence**: `HIGH`
- **Potential Consequence**: If user data is aligned to an alternative reference header (e.g. `NC_0009623`, `gi|448814763|ref|NC_000962.3|`, or `Chromosome`), coordinate fetching in `tbdrRCov.py`, `ntmFilter.sh`, and `cohort.sh` will fail or return empty datasets.
- **Requires Human Confirmation?**: No (Code-evident).

---

### UA-003: Exact Genomic Size of H37Rv is Fixed at 4,411,532 bp
- **Assumption**: The interval for cohort GATK GenomicsDB import is hardcoded as `NC_000962.3:1-4411532`.
- **Evidence**: [bin/cohort.sh:93](file:///home/falat/Repositories/BrSeqTB/bin/cohort.sh#L93): `echo -e "NC_000962.3\t1\t4411532" > "$BED"`.
- **Where Observed**: `bin/cohort.sh`.
- **Confidence**: `HIGH`
- **Potential Consequence**: The pipeline cannot be adapted to other mycobacterial references or revised assemblies without manually editing bash scripts.
- **Requires Human Confirmation?**: No (Code-evident).

---

### UA-004: Position 1472307 is a Definitive Locus for NTM Screening
- **Assumption**: Position `NC_000962.3:1472307` is assumed to be an invariant diagnostic marker for distinguishing *M. tuberculosis* complex from Non-Tuberculous Mycobacteria (NTM).
- **Evidence**: [bin/ntmFilter.sh:41-42](file:///home/falat/Repositories/BrSeqTB/bin/ntmFilter.sh#L41-L42): `NTM_POS=1472307`, `CUTOFF=0.20`.
- **Where Observed**: `bin/ntmFilter.sh`.
- **Confidence**: `HIGH`
- **Potential Consequence**: Samples with sequencing errors, rare MTB polymorphisms, or low depth at this single base are flagged as NTM contamination (`FAIL`), potentially discarding valid MTB samples.
- **Requires Human Confirmation?**: **YES — requires scientific confirmation of marker origin**.

---

### UA-005: All Input FASTQ Files Must Be Gzip Compressed
- **Assumption**: Input sequencing files are assumed to end with `.fastq.gz` (except for a partial fallback in `fastqc.sh`).
- **Evidence**: `make_manifest_validate.py:192` explicitly filters on `f.endswith(".fastq.gz")`.
- **Where Observed**: `bin/make_manifest_validate.py`.
- **Confidence**: `HIGH`
- **Potential Consequence**: Uncompressed `.fastq` files will be rejected during manifest validation.
- **Requires Human Confirmation?**: No (Standard practice).

---

### UA-006: Illumina Read Filename Regular Expression Requirements
- **Assumption**: Under default Illumina naming, files must strictly match `^(.+)_S(\d+)_L(\d{3})_R([12])_001\.fastq\.gz$`.
- **Evidence**: [bin/make_manifest_validate.py:198](file:///home/falat/Repositories/BrSeqTB/bin/make_manifest_validate.py#L198), [bin/bwa.sh:94](file:///home/falat/Repositories/BrSeqTB/bin/bwa.sh#L94).
- **Where Observed**: `make_manifest_validate.py`, `bwa.sh`.
- **Confidence**: `HIGH`
- **Potential Consequence**: Real-world Illumina runs that omit `_001` or use 2-digit lane numbers (`_L01_`) fail validation unless `--readsNaming simplified` is specified.
- **Requires Human Confirmation?**: No (Code-evident).

---

### UA-007: Single Isolate Assumption & Heteroresistance Boundary
- **Assumption**: Any variant with allele frequency $\text{AF} \ge 0.90$ is assumed to be a fixed homozygous clonal mutation (`HOM`), whereas $\text{AF} < 0.90$ (down to 0.05) is assumed to represent true heteroresistance (`HET`).
- **Evidence**: [bin/resistanceTarget.py:272, 292](file:///home/falat/Repositories/BrSeqTB/bin/resistanceTarget.py#L272): `"HOM" if af is not None and af >= 0.90 else "HET"`.
- **Where Observed**: `bin/resistanceTarget.py`.
- **Confidence**: `HIGH`
- **Potential Consequence**: PCR amplification artifacts, sequencing noise, or low-depth sites with AF between 0.80 and 0.89 are categorized as heteroresistance rather than fixed resistance.
- **Requires Human Confirmation?**: **YES — requires scientific review**.

---

### UA-008: 12-SNP Minimum Spanning Tree Distance Defines Transmission
- **Assumption**: Isolates connected by an edge of $\le 12$ SNPs in an MST graph of core non-heterozygous SNPs belong to the same epidemiological transmission cluster.
- **Evidence**: [bin/transmission.py:40, 95](file:///home/falat/Repositories/BrSeqTB/bin/transmission.py#L40): `CUTOFF = 12`.
- **Where Observed**: `bin/transmission.py`.
- **Confidence**: `HIGH`
- **Potential Consequence**: Isolates with 13 SNP differences are split into distinct transmission clusters (`cluster_id`), while isolates with 12 SNPs are grouped together, without temporal or epidemiological weightings.
- **Requires Human Confirmation?**: **YES — requires epidemiological confirmation**.

---

### UA-009: 35% Heterozygous SNP Proportion Defines Mixed Infection
- **Assumption**: If $\ge 35\%$ of core unmasked SNPs in a sample are heterozygous, the isolate is classified as `MIXED` infection; $< 35\%$ is `NOT MIXED`.
- **Evidence**: [bin/mixInfection.py:33, 99](file:///home/falat/Repositories/BrSeqTB/bin/mixInfection.py#L33): `MIX_THRESHOLD = 0.35`.
- **Where Observed**: `bin/mixInfection.py`.
- **Confidence**: `HIGH`
- **Potential Consequence**: Samples with minor sublineage co-infections at proportions $< 35\%$ will be classified as `NOT MIXED`.
- **Requires Human Confirmation?**: **YES — requires biological confirmation**.

---

### UA-010: SnpEff Predictor Database Built Without CDS or Protein Validation
- **Assumption**: The GFF3 annotations in `database/mtbRef/genes.gff` and reference FASTA `sequences.fa` are assumed to be syntactically sufficient for functional effect prediction without CDS length, start/stop codon, or protein translation verification.
- **Evidence**: [bin/snpeffdb.sh:111-112](file:///home/falat/Repositories/BrSeqTB/bin/snpeffdb.sh#L111-L112): `snpEff build ... -noCheckCds -noCheckProtein`.
- **Where Observed**: `bin/snpeffdb.sh`.
- **Confidence**: `HIGH`
- **Potential Consequence**: Any malformed CDS feature in `genes.gff` could lead to incorrect amino acid change predictions (`aa_change`) that propagate into resistance catalog matching.
- **Requires Human Confirmation?**: **YES — requires genomic validation**.

---

### UA-011: Picard MarkDuplicates Stringency Set to `LENIENT`
- **Assumption**: Alignments produced by BWA-MEM may contain non-standard SAM attributes or minor format irregularities that Picard should ignore without throwing fatal errors.
- **Evidence**: [bin/bwa.sh:145](file:///home/falat/Repositories/BrSeqTB/bin/bwa.sh#L145): `VALIDATION_STRINGENCY=LENIENT`.
- **Where Observed**: `bin/bwa.sh`.
- **Confidence**: `HIGH`
- **Potential Consequence**: Truncated or malformed read alignments might pass through MarkDuplicates without raising alerts.
- **Requires Human Confirmation?**: No (Standard practice in HTS pipelines).
