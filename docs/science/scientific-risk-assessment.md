# Scientific Risk Assessment

## Executive Summary
This document assesses the scientific and analytical risks embedded within the BrSeqTB pipeline. It evaluates whether the computational methods appropriately capture the biological reality of *Mycobacterium tuberculosis* (MTB) and whether the parameters used are scientifically justifiable.

## Current Scientific Methodology
The pipeline relies on reference-based mapping to `NC_000962.3` (H37Rv). It employs multiple variant callers (GATK, LoFreq, Delly) to capture a wide spectrum of variations (SNPs, INDELs, low-frequency variants, and SVs). Functional annotation is performed using a custom SnpEff database. Resistance prediction maps variants to the WHO 2023 TB drug resistance catalogue. Transmission clustering uses a 12-SNP cutoff on a Minimum Spanning Tree of core genome SNPs.

## Major Scientific Risks

### SR-001: 12-SNP Transmission Cluster Threshold
* **Risk**: Using a hardcoded 12-SNP cutoff for transmission clustering may misclassify epidemiological links depending on the mutation rate and time elapsed.
* **Evidence**: `bin/transmission.py:40` (`CUTOFF = 12`).
* **Affected component**: Transmission clustering (`transmission.py`).
* **Potential biological consequence**: False positive or false negative clustering of patient isolates, misleading public health interventions.
* **Confidence**: HIGH
* **Severity**: HIGH
* **Recommended investigation**: Consult with epidemiologists to validate if 12 SNPs is appropriate for this specific cohort's expected mutation rate and time-scale (e.g., standard is often 5 or 12 depending on context, such as Walker et al.).

### SR-002: Mixed Infection Threshold (35% Heterozygous SNPs)
* **Risk**: Polyclonal mixed infections are defined by $\ge 35\%$ heterozygous SNPs. This is a very high threshold that likely misses low-frequency mixed infections (e.g., a 10% minor strain).
* **Evidence**: `bin/mixInfection.py:33` (`MIX_THRESHOLD = 0.35`).
* **Affected component**: Mixed infection detection (`mixInfection.py`).
* **Potential biological consequence**: False negatives in detecting mixed infections, leading to incomplete treatment if a resistant minor strain is present but ignored in the overall analysis.
* **Confidence**: HIGH
* **Severity**: HIGH
* **Recommended investigation**: Re-evaluate the sensitivity and specificity of the 0.35 threshold against synthetic mixed populations or known clinical mixed samples.

### SR-003: Incomplete Borderline Resistance Flagging
* **Risk**: Only 8 *rpoB* mutations are hardcoded to be flagged as borderline/low-level resistance. Other known borderline mutations (e.g., in *inhA* or *embB*) are not flagged.
* **Evidence**: `bin/clinicalReport.py:252-255`.
* **Affected component**: Clinical reporting (`clinicalReport.py`).
* **Potential biological consequence**: Clinicians may misinterpret intermediate resistance as high-level resistance for unflagged borderline mutations, leading to suboptimal regimen design.
* **Confidence**: HIGH
* **Severity**: MEDIUM
* **Recommended investigation**: Align the borderline mutation list with the comprehensive WHO catalogue or derive it dynamically from the 'Comment' field in the catalogue.

## Analytical Risks

### AR-001: INDEL Quality Filtering Bug
* **Risk**: An incorrect filter name `FS200 > 200.0` is used for INDELs instead of `FS > 200.0`, rendering the filter ineffective.
* **Evidence**: `bin/cohort.sh:202`.
* **Affected component**: Cohort joint genotyping (`cohort.sh`).
* **Potential biological consequence**: High false-positive rate for INDELs due to strand bias not being properly filtered.
* **Confidence**: HIGH
* **Severity**: HIGH
* **Recommended investigation**: Fix the typo and re-evaluate INDEL calling accuracy.

### AR-002: Heteroresistance Definition Boundaries
* **Risk**: The boundary for fixed, homozygous mutation is strictly set at $AF \ge 0.90$. 
* **Evidence**: `bin/resistanceTarget.py`.
* **Affected component**: AMR profiling (`resistanceTarget.py`).
* **Potential biological consequence**: True clonal mutations with slight sequencing noise ($0.85 < AF < 0.90$) may be misclassified as heteroresistance.
* **Confidence**: HIGH
* **Severity**: MEDIUM
* **Recommended investigation**: Confirm if $AF \ge 0.90$ is the clinically accepted cutoff or if it should be dynamically adjusted based on depth/quality.

## Sequencing and Alignment Risks

### SQA-001: NTM Single-Locus Diagnostic Marker
* **Risk**: Relying exclusively on position `1472307` for Non-Tuberculous Mycobacteria (NTM) screening. A single sequencing error or natural polymorphism in an MTB strain could flag it as NTM.
* **Evidence**: `bin/ntmFilter.sh:41-42`.
* **Affected component**: NTM screening (`ntmFilter.sh`).
* **Potential biological consequence**: False positives for NTM leading to discarding valid MTB clinical samples.
* **Confidence**: HIGH
* **Severity**: HIGH
* **Recommended investigation**: Validate this locus's specificity and sensitivity. Consider using multiple loci or k-mer based approaches (e.g., Kaiju, which is already in the pipeline) for primary NTM diagnosis.

## Variant Calling Risks
* Fixed parameters like MQ=60, BQ=30 for LoFreq may be too stringent for certain datasets, potentially missing true low-frequency variants.
* Relying on hard filters for GATK SNPs instead of VQSR (though understandable given MTB's lack of true truth sets, the hard filters need empirical backing).

## MTB-Specific Risks
* The exclusion of 488 PE/PPE and repetitive genes (`forbidden_genes.txt`) is standard practice but completely blinds the analysis to any biologically relevant variation in these regions. 
* Structural variants (large deletions like *katG* or *pncA*) are called by Delly but their integration into the final resistance summary may be incomplete (e.g., large deletions might not match single point mutations in the WHO catalogue).

## IS6110 Risks
* **No IS6110 detection is currently implemented.** A search of the repository yielded no results for IS6110. Therefore, transposition events that could cause gene disruption (e.g., in *ethA* or *katG*) are not being explicitly modeled, potentially leading to false-susceptible predictions.

## Interpretation Risks
* Translating computational evidence directly to clinical reports without manual review for edge cases (e.g., complex MNPs, overlapping variants).

## Reproducibility Risks
* Hardcoded thresholds distributed across multiple bash and python scripts (e.g., `transmission.py`, `mixInfection.py`, `ntmFilter.sh`).
* Unversioned reference databases embedded in code (`bin/lineage.py` contains a 5,760 SNP dictionary).

## Scientific Unknowns
* Are the 9 auxiliary isolates in `assets/auxCohort` meant to represent all major lineages to stabilize joint genotyping?
* What is the clinical validation basis for the 35% mixed infection threshold?

## Required Validation
* The 12-SNP transmission threshold.
* The `NC_000962.3:1472307` NTM marker.
* The 35% mixed infection threshold.

## Scientific Invariants
* Every reported resistance variant must map cleanly to the WHO catalogue.
* Changes to filtering thresholds must be validated against a known truth set.
* The reference genome coordinates must strictly follow `NC_000962.3`.

## High-Priority Issues
* Fix the GATK INDEL filter syntax (`FS200 > 200.0`).
* Validate the NTM single-locus screening logic.
* Assess the risk of the 35% mixed infection threshold.

## Issues That Should NOT Be Changed Without Evidence
* The list of `forbidden_genes.txt`. This likely represents accumulated domain knowledge.
* The WHO catalogue mapping logic, including the resolution of complex MNPs.
