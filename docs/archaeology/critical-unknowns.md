# Critical Unknowns & Investigation Questions — BrSeqTB

**Document ID**: `UNK-001`  
**Repository**: `LaPAM-USP/BrSeqTB`  
**Date**: August 13, 2026  
**Pipeline Framework**: Nextflow DSL2  

---

## 1. Overview

This document specifies the critical scientific, architectural, and operational questions that must be resolved by the **Senior Scientist**, **Senior Engineer**, and **QA Engineer** before production refactoring or scientific modification can proceed safely.

---

## 2. Prioritized Unknowns Register

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           CRITICAL UNKNOWNS                              │
├───────────────────┬──────────────────────────────────────────────────────┤
│ 🔴 BLOCKING       │ Must be resolved before any analytical modifications │
│ 🟡 IMPORTANT      │ Must be resolved before architectural refactoring    │
│ 🟢 NON-BLOCKING   │ Operational questions for optimization & maintenance │
└───────────────────┴──────────────────────────────────────────────────────┘
```

---

### 2.1 BLOCKING Questions (Scientific & Analytical Invariants)

#### CU-001: Scientific Derivation of the 12-SNP Transmission Threshold
- **Priority**: `BLOCKING`
- **Location**: [bin/transmission.py:40](file:///home/falat/Repositories/BrSeqTB/bin/transmission.py#L40) (`CUTOFF = 12`)
- **Question**: What is the biological and epidemiological publication or clinical validation basis for using exactly 12 SNPs on a Minimum Spanning Tree (MST) as the transmission cluster boundary in this cohort?
- **Why it is blocking**: Modernizing or refactoring the transmission clustering algorithm without knowing whether 12 SNPs is a hard clinical standard (e.g. Walker et al. / Roetzer et al.) or an arbitrary default risks altering epidemiological reporting.
- **Required Action**: Confirmation from Senior Scientist / MTB Specialist.

---

#### CU-002: Biological Basis of the 35% Heterozygous SNP Threshold for Mixed Infections
- **Priority**: `BLOCKING`
- **Location**: [bin/mixInfection.py:33](file:///home/falat/Repositories/BrSeqTB/bin/mixInfection.py#L33) (`MIX_THRESHOLD = 0.35`)
- **Question**: Why is a 35% proportion of heterozygous SNPs across unmasked core loci used to classify an isolate as `MIXED` vs `NOT MIXED`?
- **Why it is blocking**: Mixed clonal infections in MTB often occur with minor strain frequencies between 5% and 20%. A 35% cutoff may fail to detect low-frequency polyclonal infections or may have been calibrated for a specific sequencing depth model.
- **Required Action**: Senior Scientist must define the expected sensitivity/specificity targets for mixed infection detection.

---

#### CU-003: Clinical Translation Dictionary Schema & Content
- **Priority**: `BLOCKING`
- **Location**: [bin/clinicalReport.py:49](file:///home/falat/Repositories/BrSeqTB/bin/clinicalReport.py#L49) (`database/omsCatalog/dictionary.xlsx`)
- **Question**: What is the required schema, translation mapping, and authoritative source for the missing `dictionary.xlsx` file?
- **Why it is blocking**: The script relies on this file to translate WHO catalogue comments into Portuguese. Without it, medical reports may output raw or incomplete technical strings to clinicians.
- **Required Action**: Retrieve or author the validated `dictionary.xlsx` translation table.

---

#### CU-004: Diagnostic Validity of Position `NC_000962.3:1472307` for NTM Screening
- **Priority**: `BLOCKING`
- **Location**: [bin/ntmFilter.sh:41-42](file:///home/falat/Repositories/BrSeqTB/bin/ntmFilter.sh#L41-L42) (`NTM_POS=1472307`, `CUTOFF=0.20`)
- **Question**: What specific 16S rRNA / gene polymorphism occurs at position 1,472,307, and what peer-reviewed evidence establishes it as a single-point diagnostic filter for NTM contamination?
- **Why it is blocking**: If a valid MTB isolate harbors a natural polymorphism or sequencing error at base 1,472,307 with AF $\ge 0.20$, the pipeline marks it as `FAIL` and flags it as NTM.
- **Required Action**: Senior Scientist confirmation of marker validity and acceptable false-positive risk.

---

### 2.2 IMPORTANT Questions (Architecture, Engineering & Tooling)

#### CU-005: Lineage Marker Database Curation & Origin (`BrSeq_db`)
- **Priority**: `IMPORTANT`
- **Location**: [bin/lineage.py:23-5640](file:///home/falat/Repositories/BrSeqTB/bin/lineage.py#L23-L5640)
- **Question**: What is the source publication (e.g. Coll et al. 2014, Freschi et al. 2021, Napier et al. 2020) for the 5,760 SNP entries in `BrSeq_db`?
- **Why it matters**: To extract this database into an external, versioned reference asset (e.g. `database/lineage/markers.tsv`), we must establish its schema, lineage nomenclature standard (e.g. Gagneux vs Coll), and update protocol.
- **Required Action**: Establish lineage marker database provenance.

---

#### CU-006: Intended Behavior of GATK VariantFiltration on Cohort INDELs
- **Priority**: `IMPORTANT`
- **Location**: [bin/cohort.sh:202](file:///home/falat/Repositories/BrSeqTB/bin/cohort.sh#L202) (`-filter "FS200 > 200.0" --filter-name "FS"`)
- **Question**: Was line 202 intended to filter on `-filter "FS > 200.0" --filter-name "FS200"`?
- **Why it matters**: The existing syntax references an invalid annotation tag `FS200`, causing GATK to ignore the filter. Fixing it will change the set of passing cohort INDELs.
- **Required Action**: Confirm whether standard GATK INDEL filter `FS > 200.0` should be applied.

---

#### CU-007: Clinical Justification for the 8 Hardcoded *rpoB* Borderline Mutations
- **Priority**: `IMPORTANT`
- **Location**: [bin/clinicalReport.py:252-255](file:///home/falat/Repositories/BrSeqTB/bin/clinicalReport.py#L252-L255)
- **Question**: Why are specifically `rpoB_p.Leu430Pro`, `rpoB_p.Leu452Pro`, `rpoB_p.His445Tyr`, `rpoB_p.His445Leu`, `rpoB_p.Asp435Tyr`, `rpoB_p.His445Asn`, `rpoB_p.His445Arg`, `rpoB_p.His445Cys` hardcoded as borderline resistance mutations?
- **Why it matters**: Other borderline mutations recognized by the WHO (e.g. in *rpoB*, *inhA*, *embB*) are not in this list. Should this list be expanded or dynamically derived from the WHO catalogue `Comment` field?
- **Required Action**: Senior Scientist alignment on borderline mutation flagging rules.

---

#### CU-008: Heteroresistance Allele Frequency Lower & Upper Boundaries
- **Priority**: `IMPORTANT`
- **Location**: [bin/resistanceTarget.py:272, 292](file:///home/falat/Repositories/BrSeqTB/bin/resistanceTarget.py#L272)
- **Question**: Is `0.05 <= AF < 0.90` the intended clinical definition for heteroresistance, and why is `0.90` used as the fixed homozygous cutoff instead of `0.80` or `0.95`?
- **Why it matters**: Affects clinical report annotations (`ʰ`) and downstream resistance interpretation.
- **Required Action**: Clinical consensus on heteroresistance reporting cutoffs.

---

### 2.3 NON-BLOCKING Questions (Operational & Optimization)

#### CU-009: Inclusion of Delly Structural Variants in Multi-Drug Summary
- **Priority**: `NON-BLOCKING`
- **Location**: [bin/resistanceSummary.py:78-86](file:///home/falat/Repositories/BrSeqTB/bin/resistanceSummary.py#L78-L86)
- **Question**: Delly structural variants are annotated and matched in `resistanceTarget.py`, but large deletions (e.g. *katG* or *pncA* complete gene deletions) may not match standard point-mutation catalogue entries. How should large gene deletions be summarized?
- **Why it matters**: Major resistance mechanism for isoniazid (*katG* deletion) and pyrazinamide (*pncA* deletion).
- **Required Action**: Investigation of SV-to-AMR mapping rules in future phases.

---

#### CU-010: Selection Criteria for Auxiliary Cohort Reference Isolates
- **Priority**: `NON-BLOCKING`
- **Location**: `assets/auxCohort/gatk/` (SRR34768817 to SRR34768879)
- **Question**: What lineages and resistance phenotypes are represented by the 9 pre-computed auxiliary isolates, and why were these specific accessions selected?
- **Why it matters**: Useful for documentation and cohort baseline benchmarking.
- **Required Action**: Document metadata for the 9 auxiliary isolates.
