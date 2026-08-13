# Senior Scientist Assessment

## Executive Summary
This document provides a critical scientific evaluation of the BrSeqTB repository. Based on the archaeological findings, this assessment separates verified scientific facts from assumptions, identifies critical scientific and analytical risks, and establishes the requirements for modernizing the pipeline without compromising its biological integrity. 

**No production code was modified during this assessment.**

## What We Believe the System Does
The system processes Illumina sequencing data for *Mycobacterium tuberculosis* (MTB) to identify genetic variants, infer phylogenetic lineages, detect transmission clusters, and generate clinical drug resistance reports based on the WHO 2023 catalogue. It uses multiple variant callers and attempts to handle complex issues such as mixed infections and heteroresistance.

## What We Know With High Confidence
* The pipeline strictly uses the `NC_000962.3` reference genome.
* Resistance prediction relies heavily on the WHO 2023 2nd Edition Catalogue.
* Regions associated with high GC content or repetitive elements (PE/PPE genes) are actively masked from transmission analysis via `forbidden_genes.txt`.
* The pipeline uses GATK, LoFreq, and Delly for variant calling, prioritizing GATK calls over others during resistance reporting.
* No IS6110 specific detection or analysis is currently implemented in the pipeline.

## What We Suspect
* The hardcoded threshold of 35% for mixed infections is likely too high and may miss clinically relevant low-frequency mixed populations.
* The reliance on a single genomic locus (`1472307`) for NTM screening is likely fragile and prone to false positives/negatives due to sequencing noise or natural variation.
* The 12-SNP transmission threshold may have been selected as a generic default rather than calibrated to the specific epidemiology of this cohort.

## What We Do Not Know
* The exact empirical or literature basis for several hardcoded thresholds (e.g., 35% mixed infection, 12-SNP transmission).
* Whether the 8 hardcoded borderline *rpoB* mutations represent an exhaustive list for this clinical setting, or if others (e.g., *inhA* promoter mutations) should be included.
* The origin and curation protocol for the 5,760-SNP `BrSeq_db` lineage dictionary embedded in `bin/lineage.py`.

## Most Important Scientific Risks
1. **12-SNP Transmission Clustering Threshold**: Using an unvalidated hard cutoff could severely misclassify epidemiological links.
2. **35% Heterozygous SNP Threshold for Mixed Infections**: Extremely high cutoff risks missing true polyclonal infections.
3. **Single-Locus NTM Screening**: Relying on position `1472307` is analytically fragile.
4. **Incomplete Borderline Resistance Flagging**: Hardcoding only 8 *rpoB* mutations risks misinterpreting other borderline resistance markers.
5. **Heteroresistance AF Boundary**: Strict $AF \ge 0.90$ for homozygous calls may misclassify slightly noisy clonal reads as heteroresistance.

## Most Important Engineering Risks
1. **Hardcoded Scientific Parameters**: Parameters are buried in Bash/Python scripts rather than exposed in configuration files.
2. **Embedded Reference Data**: The lineage dictionary is hardcoded into `bin/lineage.py`, complicating updates and provenance tracking.
3. **INDEL Filter Bug**: `FS200 > 200.0` typo in GATK filtering means INDELs are not being correctly filtered for strand bias.
4. **Lack of Unit Tests for Biological Logic**: Complex rules (like MNP decomposition) cannot be tested in isolation.
5. **Missing Provenance in Reports**: Final clinical reports do not explicitly state the WHO catalogue version or pipeline version used.

## MTB-Specific Concerns
* **PE/PPE Masking**: While standard, fully ignoring these regions eliminates the possibility of studying variation within them, which might become relevant later.
* **Large Deletions**: Delly is used to call structural variants, but large deletions (e.g., full *katG* loss) may not map correctly to the single-nucleotide entries in the WHO catalogue, potentially leading to false susceptibility calls for INH.

## IS6110 Concerns
* The repository does **not** contain code to detect or analyze IS6110 insertion elements. Thus, resistance caused by gene disruption via IS6110 (e.g., in *ethA*) will not be detected, representing a known false-negative mechanism.

## Critical Scientific Invariants
* Computational evidence (allele frequencies, read depths) must not be conflated with biological interpretation (heteroresistance, clinical resistance).
* Any clinical interpretation must be traceable back to specific variant evidence and reference database versions.
* Modifications to thresholds must not occur silently; they require empirical validation.

## Critical Architectural Requirements
* All scientific thresholds must be externalized to version-controlled configuration files.
* Reference databases (lineage dictionaries, catalogues) must be decoupled from source code.
* The biological decision logic (e.g., WHO catalogue matching) must be modularized and unit-testable.

## Required Validation Before Modernization
* Validate the 12-SNP transmission threshold.
* Validate the 35% mixed infection threshold.
* Validate the single-locus NTM marker (`1472307`).
* Confirm the intended INDEL filter syntax (`FS > 200.0`).

## Things We Must NOT Change Without Evidence
* The WHO catalogue mapping logic and MNP resolution rules.
* The list of masked genes (`forbidden_genes.txt`).

## Questions Requiring Human Decision (For the Human Scientific Owner)
1. **Transmission Cutoff**: Is the 12-SNP cutoff for transmission clustering based on a specific clinical standard for this cohort, or should it be configurable?
2. **Mixed Infections**: Is the 35% heterozygous SNP threshold intentional? What is the acceptable false-negative rate for low-frequency mixed infections?
3. **NTM Screening**: Is position `NC_000962.3:1472307` an established diagnostic marker for NTM, or should we rely on the broader taxonomic classification (Kaiju) already in the pipeline?
4. **Borderline Mutations**: Should the clinical report flag *all* WHO borderline mutations dynamically, or only the 8 hardcoded *rpoB* mutations?
5. **Heteroresistance Cutoff**: Is the boundary for fixed, homozygous mutation strictly $AF \ge 0.90$, or should this be adjusted based on sequencing depth?
6. **Backward Compatibility**: When fixing the `FS200 > 200.0` INDEL bug, do we need to re-run historical samples to correct their reports?

## Recommended Next Investigation
The next phase (Architecture & Modernization Planning) should focus on designing a modular architecture that externalizes parameters and reference data, fixes the INDEL filtering bug, and creates unit tests for the core biological logic, without altering the underlying (and potentially flawed) scientific assumptions until they are explicitly addressed by the human scientific owner.
