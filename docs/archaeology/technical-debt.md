# Technical Debt & Architectural Risk Register — BrSeqTB

**Document ID**: `DEBT-001`  
**Repository**: `LaPAM-USP/BrSeqTB`  
**Date**: August 13, 2026  
**Pipeline Framework**: Nextflow DSL2  

---

## 1. Summary of Identified Technical Debt

| ID | Title | Severity | Location | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| **TD-001** | Global Project Root Execution (`cd ${projectDir}`) & In-Place Mutation | **CRITICAL** | `main.nf` (All 30 processes) | HIGH |
| **TD-002** | Invalid GATK Annotation Key in Cohort INDEL VariantFiltration (`FS200`) | **CRITICAL** | `bin/cohort.sh:202` | HIGH |
| **TD-003** | Hardcoded 5,700-Line In-Memory Database Literal in Lineage Typing Script | **HIGH** | `bin/lineage.py:23-5640` | HIGH |
| **TD-004** | Missing Clinical Translation Dictionary Dependency (`dictionary.xlsx`) | **HIGH** | `bin/clinicalReport.py:49` | HIGH |
| **TD-005** | Nextflow 26.04+ Strict Syntax Incompatibility at Config Root | **HIGH** | `nextflow.config:16-17` | HIGH |
| **TD-006** | Discrepancy Between Declared and Evaluated FastQC GC Thresholds | **MEDIUM** | `bin/fastqc.sh:29-30, 127-130` | HIGH |
| **TD-007** | Single-Lane Restriction in Kaiju Taxonomic Screening | **MEDIUM** | `bin/kaiju.sh:46-47` | HIGH |
| **TD-008** | Lack of Trap-Based Cleanup for Large Temporary Intermediates | **MEDIUM** | `bin/bwa.sh`, `bin/delly.sh` | HIGH |
| **TD-009** | Total Absence of Automated Test Suite and CI/CD Verification | **MEDIUM** | `tests/` directory | HIGH |
| **TD-010** | Inconsistent Documentation Directory Orthography (`archeology` vs `archaeology`) | **LOW** | `docs/` tree | HIGH |

---

## 2. Detailed Technical Debt Findings

### TD-001: Global Project Root Execution (`cd ${projectDir}`) & In-Place Mutation
- **Severity**: `CRITICAL`
- **Location**: [main.nf](file:///home/falat/Repositories/BrSeqTB/main.nf) (Across all 30 process blocks, e.g. lines 37, 55, 73, 91, 109, 158, 176, 212, etc.)
- **Evidence**:
  ```groovy
  process BWA {
      script:
      """
      cd "${projectDir}"
      bash bin/bwa.sh ${biosample}
      """
  }
  ```
- **Why it matters**: In standard Nextflow architecture, tasks execute inside isolated working directories (`work/<hash>`), staging input files via channels and capturing declared output artifacts. In BrSeqTB, every task forces its execution context back to `${projectDir}` and directly writes files into root-level folders (`bwa/`, `gatk/`, `norm/`, etc.).
- **Potential impact**:
  1. Completely breaks multi-tenancy and concurrent workflow runs on the same codebase.
  2. Prevents native Nextflow task hashing and resume caching (`-resume` cannot track staged files).
  3. Fails in containerized or cloud environments (e.g. AWS Batch, Google Cloud Life Sciences, Kubernetes) where `${projectDir}` is mounted read-only.
  4. Creates severe race conditions if multiple tasks access or write to the same directory without explicit Nextflow channel barriers.
- **Confidence**: `HIGH`

---

### TD-002: Invalid GATK Annotation Key in Cohort INDEL VariantFiltration (`FS200`)
- **Severity**: `CRITICAL`
- **Location**: [bin/cohort.sh:202](file:///home/falat/Repositories/BrSeqTB/bin/cohort.sh#L202)
- **Evidence**:
  ```bash
  # bin/cohort.sh:198-207
  gatk VariantFiltration \
      -V "$COHORT_INDELS" \
      -filter "QUAL < 30.0" \
      --filter-name "QUAL30" \
      -filter "FS200 > 200.0" \
      --filter-name "FS" \
      -filter "ReadPosRankSum < -20.0" \
      --filter-name "ReadPosRankSum" \
      -O "$INDELS_FILTERED"
  ```
- **Why it matters**: In GATK VCF files, the FisherStrand annotation is stored in the INFO field as `FS`. In single-sample calling ([bin/gatkVcf.sh:114](file:///home/falat/Repositories/BrSeqTB/bin/gatkVcf.sh#L114)), the command is correctly written as `--filter-expression "vc.isIndel() && FS > 200.0" --filter-name "FS200"`. However, in `bin/cohort.sh:202`, the filter expression was written as `-filter "FS200 > 200.0"`. GATK looks for an attribute named `FS200`, which does not exist in standard VCF records.
- **Potential impact**: The filter expression fails to match or evaluates to missing/null. High-strand-bias INDELs (Phred-scaled FisherStrand $> 200.0$) in cohort joint calling are not filtered out as intended, potentially propagating false-positive INDEL calls into downstream resistance matrices.
- **Confidence**: `HIGH`

---

### TD-003: Hardcoded 5,700-Line In-Memory Database Literal in Lineage Typing Script
- **Severity**: `HIGH`
- **Location**: [bin/lineage.py:23-5640](file:///home/falat/Repositories/BrSeqTB/bin/lineage.py#L23-L5640)
- **Evidence**:
  ```python
  # bin/lineage.py:22-27
  # ================== DATABASE ==================
  BrSeq_db = [{'Alternative allele': 'A',
    'Comment': 'LAM7-TUR;None',
    'Lineage': 'lineage4.2.2.1',
    'Lineage details': 'Euro-American',
    'Position': 1131},
   ...
   {'Alternative allele': 'C', 'Comment': 'NA;RD239', 'Lineage': 'lineage1.2.1', 'Position': 458156}]
  ```
- **Why it matters**: Over 5,600 lines of static Python dictionary definitions (~170 KB) are embedded directly within the script source code instead of being managed as an external, versioned reference database (`.csv`, `.tsv`, or `.json`).
- **Potential impact**:
  1. Prevents independent updates, version tracking, and curation of lineage marker SNPs without modifying application source code.
  2. Substantially slows code parsing, linting, and diffing.
  3. Obscures scientific provenance of marker definitions.
- **Confidence**: `HIGH`

---

### TD-004: Missing Clinical Translation Dictionary Dependency (`dictionary.xlsx`)
- **Severity**: `HIGH`
- **Location**: [bin/clinicalReport.py:49, 239-244](file:///home/falat/Repositories/BrSeqTB/bin/clinicalReport.py#L49)
- **Evidence**:
  ```python
  DICTIONARY = os.path.join(PROJECT_DIR, "database", "omsCatalog", "dictionary.xlsx")
  ...
  try:
      df_dict = pd.read_excel(DICTIONARY, dtype=str).fillna("")
      dict_map = dict(zip(df_dict["comment"].str.strip(), df_dict["Tradução"].str.strip()))
  except:
      dict_map = {}
  ```
- **Why it matters**: The script explicitly references `database/omsCatalog/dictionary.xlsx` to translate technical WHO catalogue comments into Portuguese for clinical reports. However, `dictionary.xlsx` does not exist in `database/omsCatalog/` or anywhere in the repository.
- **Potential impact**: The `try...except` block silently catches the `FileNotFoundError` and defaults to an empty dictionary, resulting in untranslated English comments or raw technical identifiers appearing in Brazilian medical reports.
- **Confidence**: `HIGH`

---

### TD-005: Nextflow 26.04+ Strict Syntax Incompatibility at Config Root
- **Severity**: `HIGH`
- **Location**: [nextflow.config:16-17](file:///home/falat/Repositories/BrSeqTB/nextflow.config#L16-L17)
- **Evidence**:
  ```groovy
  def totalCpus = Runtime.runtime.availableProcessors()
  def usable    = Math.max(2, (totalCpus * 0.65) as int)
  ```
- **Why it matters**: Nextflow 26.04+ and upcoming Nextflow versions operating under strict declarative configuration reject dynamic Groovy statements (`def ...`) declared at the root configuration scope.
- **Potential impact**: Running the pipeline with newer Nextflow versions causes an immediate parser fatal error prior to workflow initialization.
- **Confidence**: `HIGH`

---

### TD-006: Discrepancy Between Declared and Evaluated FastQC GC Thresholds
- **Severity**: `MEDIUM`
- **Location**: [bin/fastqc.sh:29-30, 127-130](file:///home/falat/Repositories/BrSeqTB/bin/fastqc.sh#L29-L30)
- **Evidence**:
  ```bash
  # bin/fastqc.sh:29-30
  GC_MIN=64.5         # lower GC threshold for M. tuberculosis
  GC_MAX=66.5         # upper GC threshold for M. tuberculosis
  ...
  # bin/fastqc.sh:127-130
  if (( $(echo "$gc < 62" | bc -l) )) || (( $(echo "$gc > 68" | bc -l) )); then
      status="FAIL"
  elif (( $(echo "$gc < 63" | bc -l) )) || (( $(echo "$gc > 67" | bc -l) )); then
      status="WARNING"
  else
      status="PASS"
  fi
  ```
- **Why it matters**: Variables `GC_MIN=64.5` and `GC_MAX=66.5` are declared at the top of the script but are completely ignored in the actual status evaluation logic, which hardcodes `62/68` for FAIL and `63/67` for WARNING.
- **Potential impact**: Developers modifying `GC_MIN` or `GC_MAX` will see no change in pipeline behavior.
- **Confidence**: `HIGH`

---

### TD-007: Single-Lane Restriction in Kaiju Taxonomic Screening
- **Severity**: `MEDIUM`
- **Location**: [bin/kaiju.sh:46-47](file:///home/falat/Repositories/BrSeqTB/bin/kaiju.sh#L46-L47)
- **Evidence**:
  ```bash
  R1=$(find "$TRIM_DIR" -type f -name "*_R1_001.fastq.gz" | head -n 1)
  R2=$(find "$TRIM_DIR" -type f -name "*_R2_001.fastq.gz" | head -n 1)
  ```
- **Why it matters**: While `bwa.sh` correctly iterates over and merges all sequencing lanes for a biosample, `kaiju.sh` uses `head -n 1` and analyzes only the first lane.
- **Potential impact**: If contamination is lane-specific or if reads are partitioned across multiple flowcell lanes, Kaiju taxonomic metrics will reflect only a fraction of the library.
- **Confidence**: `HIGH`

---

### TD-008: Lack of Trap-Based Cleanup for Large Temporary Intermediates
- **Severity**: `MEDIUM`
- **Location**: [bin/bwa.sh:41-44](file:///home/falat/Repositories/BrSeqTB/bin/bwa.sh#L41-L44), [bin/delly.sh:52](file:///home/falat/Repositories/BrSeqTB/bin/delly.sh#L52)
- **Evidence**:
  ```bash
  RAW_BAM="${TMP_DIR}/${BIOSAMPLE}.raw.bam"
  SORTED_BAM="${TMP_DIR}/${BIOSAMPLE}.sorted.bam"
  ```
- **Why it matters**: Temporary unindexed BAMs (`.raw.bam`, `.sorted.bam`) and uncompressed BCFs are created without bash `trap 'rm -f ...' EXIT INT TERM` handlers.
- **Potential impact**: If a task fails mid-execution (e.g. killed by OOM or user cancellation), multi-gigabyte intermediate BAM files remain on disk indefinitely.
- **Confidence**: `HIGH`

---

### TD-009: Total Absence of Automated Test Suite and CI/CD Verification
- **Severity**: `MEDIUM`
- **Location**: [tests/](file:///home/falat/Repositories/BrSeqTB/tests)
- **Evidence**: The `tests/` directory is empty; `.github/workflows` does not exist.
- **Why it matters**: There is no automated framework to run unit tests, test edge cases in FASTQ parsing, or verify end-to-end regression consistency against golden outputs.
- **Potential impact**: Any refactoring or dependency update risks silently altering scientific outputs without automated detection.
- **Confidence**: `HIGH`

---

### TD-010: Inconsistent Documentation Directory Orthography
- **Severity**: `LOW`
- **Location**: `docs/archeology` vs `docs/archaeology`
- **Evidence**: Baseline document exists at `docs/archeology/baseline.md` (using Latin/Portuguese spelling `archeology`).
- **Why it matters**: Inconsistent spelling creates navigational ambiguity across documentation files.
- **Potential impact**: Negligible technical risk; minor organizational friction.
- **Confidence**: `HIGH`
