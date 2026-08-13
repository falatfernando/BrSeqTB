# Repository Archaeology Report — BrSeqTB

**Document ID**: `ARCH-REPORT-001`  
**Repository**: `LaPAM-USP/BrSeqTB`  
**Date of Assessment**: August 13, 2026  
**Pipeline Framework**: Nextflow DSL2  
**Assessor**: Repository Archaeologist (Phase 0)  

---

## 1. Executive Summary

This archaeology report presents a reverse-engineered architectural and scientific baseline of the **BrSeqTB** repository. BrSeqTB is a specialized bioinformatics pipeline developed for *Mycobacterium tuberculosis* (MTB) whole-genome sequencing (WGS) data (Illumina paired-end).

The system integrates raw read quality control, taxonomic screening, reference alignment, multi-caller variant detection (GATK4, LoFreq, Delly), variant normalization, lineage typing, NTM contamination filtering, SnpEff functional annotation, GATK cohort joint genotyping, phylogenetic tree reconstruction (IQ-TREE 2), transmission cluster detection, mixed infection inference, WHO 2023 2nd Edition antimicrobial resistance (AMR) profiling, and automated Microsoft Word clinical report generation.

**Key Archaeological Findings**:
1. **Architectural Decoupling from Nextflow Workspace**: The pipeline utilizes Nextflow DSL2 primarily as a task scheduler and synchronization barrier, but bypasses Nextflow's native file staging mechanism by forcing `cd "${projectDir}"` across all 30 process blocks. All processes read and write in-place to root-level project directories.
2. **Defect in Cohort INDEL Hard-Filtering**: In `bin/cohort.sh:202`, a syntax error (`-filter "FS200 > 200.0"`) causes GATK `VariantFiltration` to query a non-existent annotation attribute, leaving high-strand-bias INDELs unfiltered during cohort joint calling.
3. **Missing Clinical Dependency**: `bin/clinicalReport.py` expects `database/omsCatalog/dictionary.xlsx` to translate technical comments into Portuguese. The file is absent from the repository, causing comment translation to silently fail.
4. **Hardcoded In-Memory Lineage Database**: `bin/lineage.py` contains 5,760 lines (~170 KB) of embedded Python dictionary literals (`BrSeq_db`) containing canonical SNP markers, preventing modular database updates.
5. **Critical Scientific Assumptions Requiring Validation**: Several analytical thresholds—such as the 12-SNP transmission cutoff, the 35% heterozygous SNP mixed infection threshold, and the single-point NTM diagnostic locus (`NC_000962.3:1472307`)—are hardcoded without documented scientific derivation.

---

## 2. What the Repository Actually Does

Starting from raw paired-end Illumina FASTQ files and a sample sheet (`input_table.csv` or `.xlsx`), BrSeqTB executes the following sequence:

```
[Raw FASTQ Reads & Sample Table]
       │
       ▼
1. FASTQ validation & Manifest generation (bin/make_manifest_validate.py)
       │
       ▼
2. Quality Control & Trimming (FastQC & Trimmomatic)
       │
       ▼
3. Taxonomic Contamination Screening (Kaiju against custom Mycobacterium DB)
       │
       ▼
4. Alignment & Duplicate Marking (BWA-MEM -> samtools merge/sort -> Picard MarkDuplicates)
       │
       ├─────────────────────────────────────────┬───────────────────────┐
       ▼                                         ▼                       ▼
5. GATK HaplotypeCaller (MNP VCF + gVCF)   6. LoFreq (Low-AF)     7. Delly (Structural)
       │                                         │                       │
       ▼                                         │                       │
8. bcftools norm + vt decompose_blocksub         │                       │
       │                                         │                       │
       ├─────────────────────────────────────────┴───────────────────────┘
       ▼
9. SnpEff Functional Annotation (Custom NC_0009623 DB)
       │
       ├─────────────────────────────────────────┐
       ▼                                         ▼
10. GATK Cohort Joint Genotyping          11. Lineage Typing & NTM Screening
    (GenomicsDB -> GenotypeGVCFs)             (Lineage SNP DB + Pos 1472307)
       │                                         │
       ▼                                         │
12. SNP Pseudo-Alignment Matrix (snpMatrix.py)   │
       │                                         │
       ├────────────────────────┐                │
       ▼                        ▼                │
13. IQ-TREE Phylogeny   14. MST Transmission     │
    (HKY+I+G, 1000 boot)    (Hamming <= 12 SNPs) │
       │                        │                │
       └────────────────────────┴────────────────┘
       │
       ▼
15. Mixed Infection Inference (mixInfection.py: unmasked core het SNPs >= 35%)
       │
       ▼
16. WHO 2023 AMR Target Matching & Complex MNP Resolution (resistanceTarget.py & resistanceReport.py)
       │
       ▼
17. Global QC & Resistance Summarization (qcSummary.py & resistanceSummary.py)
       │
       ▼
18. Clinical Diagnostic Word Report Assembly (clinicalReport.py -> .docx)
```

---

## 3. Architecture

BrSeqTB employs a hybrid architecture:
- **Orchestration Layer**: Nextflow DSL2 ([main.nf](file:///home/falat/Repositories/BrSeqTB/main.nf), [nextflow.config](file:///home/falat/Repositories/BrSeqTB/nextflow.config)).
- **Execution Modules**: 17 Bash scripts and 13 Python scripts in [bin/](file:///home/falat/Repositories/BrSeqTB/bin).
- **Environment**: Pinned Bioconda/Conda-Forge environment ([envs/brseqtb.yml](file:///home/falat/Repositories/BrSeqTB/envs/brseqtb.yml)).
- **State Storage**: File-system-based state shared in the repository root directory.

### Key Architectural Characteristics:
- **Global Synchronization Barriers**: The pipeline uses explicit Nextflow channel collection operators (`.collect().map { true }`) to create hard execution barriers between Block 1 (sample-level calling), Block 2 (cohort-level joint calling & phylogenetics), Block 3 (resistance matching), and Block 4 (global summaries).
- **Module Execution Mode**: Supports single-module execution via `--module <name>` and optional module exclusion via `--exclude <modules>`.
- **In-Place File System Mutation**: Modules do not use Nextflow input/output file declarations for data passing; instead, downstream scripts hardcode paths to upstream folders (e.g. `trimmomatic/<sample>/`, `bwa/<sample>/`, `snpeff/<sample>/`).

---

## 4. Data Flow

Data flows across standard genomic and clinical formats:
1. **Reads**: FASTQ paired-end format (`.fastq.gz`), Phred+33 quality encoding.
2. **Alignments**: Coordinate-sorted, duplicate-marked BAM files (`.bam`, `.bam.bai`) with strict `@RG` read group headers (`ID`, `SM`, `PL:ILLUMINA`, `LB`, `PU`).
3. **Variants**:
   - GATK VCF (`_gatk.vcf.gz`): Single-sample calls with MNP distance 1.
   - GATK gVCF (`.g.vcf.gz`): Genomic records with non-variant confidence blocks.
   - LoFreq VCF (`_lofreq.vcf.gz`): Low-frequency calls ($\text{AF} \ge 0.05$).
   - Delly VCF (`_delly.vcf.gz`): Structural variant breakpoints.
   - Normalized VCF (`_norm.vcf.gz`): Left-aligned, decomposed primitives.
4. **Phylogenetic Alignments**: FASTA pseudo-alignment (`snpmatrix.fasta`) constructed from core homozygous SNPs (excluding 488 forbidden genes).
5. **AMR Profiles**: Excel workbooks (`_OMStarget.xlsx`, `<sample>.xlsx`, `resistance_summary.xlsx`) mapping mutations to WHO 2023 confidence grades (`R`, `r`, `u`, `s`, `S`).
6. **Reports**: Microsoft Word documents (`.docx`) assembled using `python-docx` placeholder replacement.

---

## 5. Scientific Assumptions

The pipeline encodes 12 major scientific assumptions (detailed in [docs/science/current-scientific-assumptions.md](file:///home/falat/Repositories/BrSeqTB/docs/science/current-scientific-assumptions.md)):
1. **Reference Invariance**: H37Rv (`NC_000962.3`, 4,411,532 bp) is assumed to be the sole reference coordinate system.
2. **Hypervariable Masking**: 488 PE/PPE and repetitive mobile genes (`forbidden_genes.txt`) are excluded from SNP matrix and phylogenetic inference.
3. **Subclonal Frequency Limit**: LoFreq variants with $\text{AF} \ge 0.05$, $\text{alt\_reads} \ge 3$, $\text{MQ} \ge 60$, and $\text{BQ} \ge 30$ are treated as genuine subclonal variants.
4. **Heteroresistance Cutoff**: Allele frequency $\text{AF} \ge 0.90$ is classified as homozygous fixed resistance (`HOM`), whereas $0.05 \le \text{AF} < 0.90$ is classified as heteroresistance (`HET`).
5. **Coverage Depth Threshold**: Sequencing depth $\text{DP} < 10$ across WHO candidate loci is classified as a coverage failure (`DP_FAIL`).
6. **NTM Screening Marker**: Locus `NC_000962.3:1472307` is treated as a single-point diagnostic marker for non-tuberculous mycobacterial contamination ($\text{AF} \ge 0.20 \to \text{FAIL}$).
7. **Mixed Infection Threshold**: If $\ge 35\%$ of core unmasked SNPs are heterozygous, the sample is classified as `MIXED` infection.
8. **Transmission Distance Cutoff**: Minimum Spanning Tree (MST) distance $\le 12$ SNPs defines transmission clusters.
9. **Evolutionary Substitution Model**: Core SNP alignments are modeled under `HKY+I+G` with 1000 ultrafast bootstrap replicates in IQ-TREE 2.
10. **WHO AMR Catalogue Hierarchy**: Resistance resolves in order `flagR` > `flagr` > `flagu` > `flagnR` > `flagnr`. Default is `S`.
11. **MNP Dominance**: When MNPs overlap decomposed SNPs, the MNP is biologically primary and constituent SNPs are removed.
12. **Borderline *rpoB* Flagging**: Exactly 8 *rpoB* mutations are flagged with `†` as borderline resistance markers.

---

## 6. Engineering Risks

1. **FileSystem Coupling & Concurrency Hazard**: Because all tasks execute in `${projectDir}`, concurrent pipeline executions in the same repository will overwrite intermediate files and cause race conditions.
2. **HPC & Cloud Incompatibility**: The pipeline cannot execute in environments where `${projectDir}` is mounted read-only or where compute nodes lack a shared POSIX file system.
3. **Silent Exception Catching in Reporting**: `bin/clinicalReport.py` catches all exceptions during dictionary loading without logging warnings, masking missing dependencies.
4. **Unbounded Intermediate Disk Usage**: Incomplete executions leave multi-gigabyte unindexed `.raw.bam` and `.bcf` files in working directories due to absence of shell cleanup traps.

---

## 7. Reproducibility Assessment

- **Qualitative Rating**: `PARTIALLY REPRODUCIBLE`
- **Justification**:
  - **Strengths**: The Conda environment specification (`envs/brseqtb.yml`) is functional; reference genome FASTA, GFF3, and WHO catalogue files are committed to the repository; static auxiliary reference isolates are bundled in `assets/auxCohort/`.
  - **Weaknesses**:
    - `database/omsCatalog/dictionary.xlsx` is missing.
    - Kaiju database relies on an external Zenodo download URL.
    - Several Conda packages (`gatk4`, `picard`, `delly`, `lofreq`, `fastqc`, `trimmomatic`, `iqtree`, `kaiju`) are unpinned to minor/patch versions.
    - File system side effects prevent standard Nextflow caching and deterministic work directory isolation.

---

## 8. Testing and Validation Assessment

- **Qualitative Rating**: `UNVALIDATED`
- **Justification**:
  - The [tests/](file:///home/falat/Repositories/BrSeqTB/tests) directory is empty.
  - No automated unit, integration, or end-to-end regression tests exist.
  - No CI/CD workflows are configured.
  - No golden standard dataset or expected output baseline is stored in the repository.

---

## 9. Technical Debt Register

Detailed findings from [docs/archaeology/technical-debt.md](file:///home/falat/Repositories/BrSeqTB/docs/archaeology/technical-debt.md):

| ID | Title | Severity | Impact |
| :--- | :--- | :--- | :--- |
| **TD-001** | Global Project Root Execution (`cd ${projectDir}`) | **CRITICAL** | Breaks multi-tenancy, cloud execution, and Nextflow resume caching. |
| **TD-002** | Invalid GATK Annotation Key in Cohort INDEL Filter (`FS200`) | **CRITICAL** | High-strand-bias INDELs fail to be filtered during cohort joint calling. |
| **TD-003** | Hardcoded 5,700-Line Database Literal in `bin/lineage.py` | **HIGH** | Prevents modular maintenance and versioning of lineage SNP markers. |
| **TD-004** | Missing Clinical Translation Dictionary (`dictionary.xlsx`) | **HIGH** | Clinical reports omit Portuguese translation of catalogue comments. |
| **TD-005** | Nextflow 26.04+ Strict Syntax Incompatibility at Config Root | **HIGH** | Parser error on modern Nextflow runtimes. |
| **TD-006** | FastQC GC Threshold Discrepancy (Declared vs Evaluated) | **MEDIUM** | Inactive configuration variables in `fastqc.sh`. |
| **TD-007** | Single-Lane Restriction in Kaiju Taxonomic Screening | **MEDIUM** | Multi-lane libraries only partially screened for taxonomy. |
| **TD-008** | Lack of Trap-Based Cleanup for Intermediate BAM/BCF Files | **MEDIUM** | Orphaned multi-GB temporary files upon task failure. |
| **TD-009** | Absence of Automated Test Suite and CI/CD Verification | **MEDIUM** | High regression risk during refactoring. |
| **TD-010** | Inconsistent Documentation Directory Orthography | **LOW** | Minor directory naming discrepancy (`archeology` vs `archaeology`). |

---

## 10. Undocumented Assumptions

Detailed findings from [docs/archaeology/undocumented-assumptions.md](file:///home/falat/Repositories/BrSeqTB/docs/archaeology/undocumented-assumptions.md):
- **UA-001**: Execution working directory must be repository root.
- **UA-002**: Reference chromosome header must strictly match `NC_000962.3`.
- **UA-003**: H37Rv genome size is assumed to be exactly 4,411,532 bp.
- **UA-004**: Position 1472307 is assumed to be a definitive single-point diagnostic marker for NTM contamination.
- **UA-005**: All paired FASTQs must be gzip-compressed.
- **UA-006**: Illumina FASTQ naming regex requires strict `_S<num>_L<3digit>_R<1|2>_001.fastq.gz`.
- **UA-007**: Variant AF $< 0.90$ is assumed to represent heteroresistance rather than sequencing noise or diploidy.
- **UA-008**: 12-SNP MST distance cutoff is assumed to define recent tuberculosis transmission.
- **UA-009**: 35% heterozygous SNP cutoff is assumed to distinguish polyclonal mixed infections from within-host microevolution.
- **UA-010**: SnpEff predictor database is built without CDS length or protein translation validation.
- **UA-011**: Picard `MarkDuplicates` stringency is set to `LENIENT`.

---

## 11. Critical Unknowns

Prioritized findings from [docs/archaeology/critical-unknowns.md](file:///home/falat/Repositories/BrSeqTB/docs/archaeology/critical-unknowns.md):
- **🔴 BLOCKING**:
  - `CU-001`: Scientific derivation of the 12-SNP transmission clustering cutoff (`transmission.py:40`).
  - `CU-002`: Biological rationale for the 35% heterozygous SNP threshold in mixed infection detection (`mixInfection.py:33`).
  - `CU-003`: Missing schema and authoritative content for `database/omsCatalog/dictionary.xlsx` (`clinicalReport.py:49`).
  - `CU-004`: Diagnostic validity and origin of position `NC_000962.3:1472307` for NTM screening (`ntmFilter.sh:41-42`).
- **🟡 IMPORTANT**:
  - `CU-005`: Provenance, version, and curation protocol for the 5,760 lineage SNPs embedded in `bin/lineage.py`.
  - `CU-006`: Intended behavior of GATK VariantFiltration on cohort INDELs (confirming `FS > 200.0` vs `FS200 > 200.0`).
  - `CU-007`: Clinical justification for the 8 hardcoded borderline *rpoB* mutations in `clinicalReport.py:252-255`.
  - `CU-008`: Clinical consensus on heteroresistance reporting boundaries (`0.05 <= AF < 0.90`).
- **🟢 NON-BLOCKING**:
  - `CU-009`: Strategy for mapping Delly large structural deletions to WHO resistance phenotypes.
  - `CU-010`: Provenance and phenotypic metadata of the 9 auxiliary reference isolates in `assets/auxCohort/gatk/`.

---

## 12. Most Dangerous Areas to Modify

1. **`bin/cohort.sh` (GenomicsDB & Genotyping)**: Changes to GenomicsDB interval definitions, sample arrays, or GATK filter expressions will alter the entire cohort variant set and change downstream SNP matrices, phylogenies, and transmission clusters.
2. **`bin/resistanceTarget.py` & `bin/resistanceReport.py` (AMR Resolution Logic)**: These scripts contain intricate, multi-tier matching rules and complex MNP/INDEL/SNP overlay resolution logic. Any modification risks altering drug resistance classifications.
3. **`main.nf` Sockets & Synchronization Barriers**: Modifying channel joins or barrier synchronization without transitioning to full Nextflow channel-based file staging could introduce race conditions or deadlocks.
4. **`bin/lineage.py` (`BrSeq_db` Mapping)**: Altering the dictionary parsing logic could misassign phylogenetic lineages or break sublineage annotations.

---

## 13. Recommended Investigation Priorities

For the upcoming architectural planning and modernization phase:
1. **Resolve Blocking Scientific Questions**: Senior Scientist must review and confirm the 12-SNP transmission threshold, the 35% mixed infection threshold, and the 1472307 NTM marker locus.
2. **Provide Missing Clinical Translation Dictionary**: Retrieve or author `database/omsCatalog/dictionary.xlsx`.
3. **Design Standard Nextflow DSL2 Channel Refactoring**: Plan the migration of all 30 process blocks from `cd "${projectDir}"` to pure Nextflow channel-based input/output staging in `work/` with `publishDir`.
4. **Externalize Lineage Database**: Extract `BrSeq_db` from `bin/lineage.py` into a versioned TSV asset (`database/lineage/markers.tsv`).
5. **Construct Automated QA Test Suite**: Create synthetic mini-datasets in `tests/` with ground-truth expected outputs to enable regression testing during refactoring.

---

## 14. What We Still Do Not Know

1. **We do not know** the scientific publication or clinical trial from which the 12-SNP transmission distance threshold in `bin/transmission.py` was derived.
2. **We do not know** the empirical sensitivity and specificity of the 35% heterozygous SNP cutoff in `bin/mixInfection.py` across varying sequencing depths (e.g. $30\times$ vs $100\times$).
3. **We do not know** the biological identity of the mutation at position `NC_000962.3:1472307` in `bin/ntmFilter.sh` or whether it induces false-positive NTM calls on rare MTB sublineages.
4. **We do not know** the authoritative translation mapping intended for `database/omsCatalog/dictionary.xlsx`.
5. **We do not know** whether the author of `bin/cohort.sh:202` intended `-filter "FS > 200.0"` or a different GATK INDEL filtering strategy.
6. **We do not know** the specific lineage and drug-resistance profile for each of the 9 precomputed auxiliary cohort isolates in `assets/auxCohort/gatk/`.

---
*Report concluded by Repository Archaeologist (Phase 0).*
