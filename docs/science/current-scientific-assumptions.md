# Inventory of Current Scientific & Analytical Assumptions — BrSeqTB

**Document ID**: `SCI-001`  
**Repository**: `LaPAM-USP/BrSeqTB`  
**Date**: August 13, 2026  
**Pipeline Framework**: Nextflow DSL2  

> [!IMPORTANT]
> **Scientific Validity Note**: In accordance with Phase 0 Hard Rules, the scientific validity of the assumptions listed below has **NOT YET BEEN ASSESSED**. This document inventories the exact analytical and biological assumptions currently encoded in the software without passing judgment on their clinical or biological correctness.

---

## 1. Classification Scheme

Each assumption is categorized into one of four evidence tiers:
- **DOCUMENTED**: Explicitly stated in user-facing documentation or formal code comments.
- **CODE-DEFINED**: Clearly implemented in executable code but omitted from documentation.
- **INFERRED**: Strongly suggested by algorithmic behavior but not explicitly stated.
- **UNKNOWN**: Rationale or origin cannot be confidently determined from the repository.

---

## 2. Scientific Assumptions Inventory

### SA-001: Reference Genome Model & Sequence Definition
- **Assumption**: *Mycobacterium tuberculosis* is modeled as a haploid, single circular chromosome with invariant sequence coordinates identical to reference strain H37Rv (RefSeq `NC_000962.3`, length 4,411,532 bp).
- **How It Is Implemented**: All alignment (`bwa.sh`), variant calling (`gatkVcf.sh`, `lofreq.sh`, `delly.sh`), coordinate indexing (`gatkdict.sh`), and interval tiling (`cohort.sh`) use `database/mtbRef/NC0009623.fasta`.
- **Evidence**:
  - `database/mtbRef/NC0009623.fasta`
  - [bin/cohort.sh:93](file:///home/falat/Repositories/BrSeqTB/bin/cohort.sh#L93): `NC_000962.3 1 4411532`
- **Source / Documentation**: Documented in `README.md` and `docs/archeology/baseline.md`.
- **Confidence**: `HIGH`
- **Classification**: `DOCUMENTED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-002: Hypervariable / Repetitive Region Masking (`forbidden_genes.txt`)
- **Assumption**: A predefined list of 488 genes—comprising PE/PPE family proteins, transposases, maturases, integrases, and resolvases—must be excluded from core SNP matrices and phylogenetic alignments due to high GC content, homologous recombination, and alignment artifacts.
- **How It Is Implemented**: `bin/snpMatrix.py` checks both `Gene_Name` and `Gene_ID` against `forbidden_genes.txt` (case-insensitive) and ignores any variant falling within these annotations.
- **Evidence**:
  - `database/mtbRef/forbidden_genes.txt` (488 lines)
  - [bin/snpMatrix.py:69-125](file:///home/falat/Repositories/BrSeqTB/bin/snpMatrix.py#L69-L125)
- **Source / Documentation**: Code comments in `snpMatrix.py:15-25`.
- **Confidence**: `HIGH`
- **Classification**: `DOCUMENTED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-003: Subclonal / Low-Frequency Variant Calling & Allele Frequency Cutoff
- **Assumption**: Genuine subclonal single-nucleotide variants and INDELs down to an allele frequency ($\text{AF}$) of 0.05 (5%) can be accurately detected by LoFreq with IndelQual calibration, mapping quality $\ge 60$, base quality $\ge 30$, and a minimum of 3 alternative reads.
- **How It Is Implemented**:
  - `bin/lofreq.sh:101-133`: `lofreq indelqual --dindel`, `lofreq call-parallel -m 60 -Q 30`, `lofreq filter -a 0.05`.
  - `bin/resistanceTarget.py:108-113`: requires `alt_reads >= 3` and `af >= 0.05`.
- **Evidence**: [bin/lofreq.sh:113-134](file:///home/falat/Repositories/BrSeqTB/bin/lofreq.sh#L113-L134), [bin/resistanceTarget.py:108-113](file:///home/falat/Repositories/BrSeqTB/bin/resistanceTarget.py#L108-L113).
- **Source / Documentation**: `README.md` section "Set the Minimum Allele Frequency for LoFreq".
- **Confidence**: `HIGH`
- **Classification**: `DOCUMENTED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-004: Heteroresistance vs Fixed Mutation Classification
- **Assumption**: Variant allele frequencies $\text{AF} \ge 0.90$ represent fixed, homozygous clonal resistance (`HOM`), whereas $0.05 \le \text{AF} < 0.90$ represents heteroresistance / within-host subclonal mixture (`HET`).
- **How It Is Implemented**: `bin/resistanceTarget.py` evaluates `zygosity` as `"HOM" if af >= 0.90 else "HET"`. In `clinicalReport.py`, variants flagged with `HET` are annotated with superscript `ʰ` along with AF and alt read counts.
- **Evidence**: [bin/resistanceTarget.py:271-275, 291-294](file:///home/falat/Repositories/BrSeqTB/bin/resistanceTarget.py#L271-L275), [bin/clinicalReport.py:278-285](file:///home/falat/Repositories/BrSeqTB/bin/clinicalReport.py#L278-L285).
- **Source / Documentation**: None in user documentation.
- **Confidence**: `HIGH`
- **Classification**: `CODE-DEFINED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-005: Sequencing Depth Threshold for Diagnostic Loci
- **Assumption**: A minimum sequencing depth of $10\times$ ($\text{DP} \ge 10$) across WHO catalogue candidate loci is required for reliable resistance and susceptibility inference. Positions with $\text{DP} < 10$ are treated as sequencing coverage failures.
- **How It Is Implemented**:
  - `bin/tbdrRCov.py:173`: flags any position in `tbdrR.csv` with $\text{DP} < 10$.
  - `bin/resistanceTarget.py:115, 131`: adds `DP_FAIL` if $\text{DP} < 10$.
  - `bin/clinicalReport.py:330-338`: reports loci with $\text{DP} < 10$ under "Falharam em cobertura do sequenciamento".
- **Evidence**: [bin/tbdrRCov.py:173](file:///home/falat/Repositories/BrSeqTB/bin/tbdrRCov.py#L173), [bin/resistanceTarget.py:115](file:///home/falat/Repositories/BrSeqTB/bin/resistanceTarget.py#L115).
- **Source / Documentation**: Code comments in `tbdrRCov.py`.
- **Confidence**: `HIGH`
- **Classification**: `CODE-DEFINED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-006: Diagnostic Single-Locus Screening for Non-Tuberculous Mycobacteria (NTM)
- **Assumption**: Non-tuberculous mycobacterial contamination can be definitively detected by checking genomic locus `NC_000962.3:1472307`. If LoFreq reports an allele frequency $\ge 0.20$ or GATK reports an alternative allele (`0/1` or `1/1`), the sample is flagged as `FAIL` for NTM.
- **How It Is Implemented**: `bin/ntmFilter.sh` queries position 1,472,307 using `bcftools` on both `lofreq.vcf.gz` and `.g.vcf.gz`.
- **Evidence**: [bin/ntmFilter.sh:41-42, 96-100, 125-126](file:///home/falat/Repositories/BrSeqTB/bin/ntmFilter.sh#L41-L42).
- **Source / Documentation**: None in documentation.
- **Confidence**: `HIGH`
- **Classification**: `CODE-DEFINED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-007: Mixed Clonal Infection Detection via Non-Resistance Heterozygous SNPs
- **Assumption**: Polyclonal mixed tuberculosis infections can be distinguished from single-strain microevolution by evaluating the genome-wide proportion of heterozygous SNPs after masking all known drug-resistance loci (`tbdr.bed`). A sample with $\ge 35\%$ heterozygous SNPs is classified as `MIXED`.
- **How It Is Implemented**: `bin/mixInfection.py` parses `mixInfection/<sample>/<sample>.tsv`, excludes any SNP falling within intervals in `tbdr.bed`, computes $\text{proportion} = \text{het} / \text{total}$, and assigns `MIXED` if $\ge 0.35$.
- **Evidence**: [bin/mixInfection.py:33, 55-59, 98-99](file:///home/falat/Repositories/BrSeqTB/bin/mixInfection.py#L33).
- **Source / Documentation**: None in documentation.
- **Confidence**: `HIGH`
- **Classification**: `CODE-DEFINED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-008: Transmission Cluster Cutoff (12-SNP Threshold on Core MST)
- **Assumption**: Genomic transmission clusters representing recent direct or close epidemiologic links are defined by connected components on a Minimum Spanning Tree (MST) pruned at a maximum pairwise Hamming distance of 12 core SNPs.
- **How It Is Implemented**: `bin/transmission.py` generates a pairwise distance matrix from `snpmatrix.fasta`, builds an MST using `networkx.minimum_spanning_tree`, retains edges with $\text{weight} \le 12$, and outputs connected component IDs (`cluster_id`).
- **Evidence**: [bin/transmission.py:40, 89-108](file:///home/falat/Repositories/BrSeqTB/bin/transmission.py#L40).
- **Source / Documentation**: None in documentation.
- **Confidence**: `HIGH`
- **Classification**: `CODE-DEFINED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-009: Phylogenetic Evolutionary Model & Bootstrap Policy
- **Assumption**: Molecular evolution across core, non-heterozygous tuberculosis SNPs is best modeled by the Hasegawa-Kishino-Yano substitution model with invariant sites and gamma-distributed rate heterogeneity (`HKY+I+G`), evaluated with 1000 ultrafast bootstrap replicates.
- **How It Is Implemented**: `bin/iqtree.sh` executes `iqtree -s snpmatrix.fasta -m HKY+I+G -B 1000`.
- **Evidence**: [bin/iqtree.sh:16-17, 56-62](file:///home/falat/Repositories/BrSeqTB/bin/iqtree.sh#L16-L17).
- **Source / Documentation**: Script comments in `iqtree.sh`.
- **Confidence**: `HIGH`
- **Classification**: `CODE-DEFINED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-010: WHO 2023 2nd Edition Catalogue Interpretation Hierarchy
- **Assumption**: Antimicrobial resistance prediction follows the WHO 2023 2nd Edition Catalogue grading system. Variants graded `1) Assoc w R` (R) and `2) Assoc w R - Interim` (r) confer resistance. A drug's phenotype resolves to `R` if any `flagR` variant is present, then `r` (`flagr`), `u` (`flagu`), `S` (`flagnR`), and `s` (`flagnr`). In the absence of mutations, the drug is assumed susceptible (`S`).
- **How It Is Implemented**:
  - `bin/omsCatalog.py:132-136`: filters on `1) Assoc w R` and `2) Assoc w R - Interim`.
  - `bin/resistanceReport.py:52-58`: maps confidence grading to `R/r/u/s/S`.
  - `bin/resistanceSummary.py:50-63`: evaluates priority hierarchy and sets default to `S`.
- **Evidence**: [bin/omsCatalog.py:132-136](file:///home/falat/Repositories/BrSeqTB/bin/omsCatalog.py#L132-L136), [bin/resistanceReport.py:52-58](file:///home/falat/Repositories/BrSeqTB/bin/resistanceReport.py#L52-L58), [bin/resistanceSummary.py:50-63](file:///home/falat/Repositories/BrSeqTB/bin/resistanceSummary.py#L50-L63).
- **Source / Documentation**: WHO 2023 Catalogue documentation.
- **Confidence**: `HIGH`
- **Classification**: `DOCUMENTED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-011: Complex Variant & MNP Decomposition Resolution Rules
- **Assumption**: When a complex multinucleotide polymorphism (MNP, e.g. `CA -> TG`) is called alongside decomposed single-nucleotide primitives (e.g. `C -> T` and `A -> G`), the MNP is biologically primary and redundant atomic SNPs must be removed. For deletions, overlapping homozygous SNPs are purged. For insertions, overlapping SNPs are preserved.
- **How It Is Implemented**: `bin/resistanceReport.py:resolve_complex_variants()` inspects overlapping positions, zygosity, and reference/alternative allele lengths.
- **Evidence**: [bin/resistanceReport.py:106-193](file:///home/falat/Repositories/BrSeqTB/bin/resistanceReport.py#L106-L193).
- **Source / Documentation**: Code comments in `resistanceReport.py:18-25`.
- **Confidence**: `HIGH`
- **Classification**: `DOCUMENTED`
- **Scientific Validity**: **NOT YET ASSESSED**

---

### SA-012: Explicit Borderline *rpoB* Mutations Flagging
- **Assumption**: Exactly 8 *rpoB* mutations (`Leu430Pro`, `Leu452Pro`, `His445Tyr`, `His445Leu`, `Asp435Tyr`, `His445Asn`, `His445Arg`, `His445Cys`) confer low-level / borderline rifampicin resistance and must be explicitly flagged with a dagger symbol (`†`) on clinical reports.
- **How It Is Implemented**: `bin/clinicalReport.py:252-255` maintains a hardcoded set `borderline_set`.
- **Evidence**: [bin/clinicalReport.py:252-255](file:///home/falat/Repositories/BrSeqTB/bin/clinicalReport.py#L252-L255).
- **Source / Documentation**: None in documentation.
- **Confidence**: `HIGH`
- **Classification**: `CODE-DEFINED`
- **Scientific Validity**: **NOT YET ASSESSED**
