# Architecture Principles

This document defines the high-level architectural requirements and constraints that any future modernization of the BrSeqTB software must respect. These principles ensure that the software remains scientifically rigorous, reproducible, and auditable.

## 1. Explicit Scientific Assumptions
Scientific assumptions (e.g., masking specific genes, using specific diagnostic loci) must be explicitly documented and conceptually separated from general data processing logic. The code should reflect the biology intentionally, not accidentally.

## 2. Version-Controlled Parameters
All scientific parameters (e.g., depth cutoffs, allele frequency thresholds, SNP distance limits) must not be hardcoded in executable scripts. They must be managed via centralized, version-controlled configuration files (e.g., Nextflow configs or JSON/YAML parameter files) and passed explicitly to processing scripts.

## 3. Preservation of Provenance
Every output file, especially final clinical reports and cohort summaries, must preserve provenance. This includes the pipeline version, reference genome version, reference database versions (e.g., WHO catalogue date), and the exact parameter set used.

## 4. Distinguish Computational Evidence from Interpretation
The software architecture must maintain a boundary between raw computational observations and biological/clinical interpretations. For example, a variant caller outputs an allele frequency (evidence); a downstream module interprets that frequency as "heteroresistance" (interpretation). These two states must be recorded separately.

## 5. Versioned Reference Data
Reference databases, lineage dictionaries, and annotation sets must not be embedded within source code. They must be externalized as versioned assets. Updating a reference database should not require a code change to the pipeline logic.

## 6. Independent Testability
Pipeline stages and biological decision logic must be independently testable. Monolithic scripts that mix I/O parsing with complex biological rules (e.g., MNP resolution) must be modularized so the biological logic can be unit-tested against synthetic edge cases.

## 7. Documented Scientific Decisions
Any change to a biological rule, threshold, or interpretation logic must be accompanied by documented scientific rationale in the repository (e.g., via the Scientific Decision Framework).

## 8. Regression Testing for Behavioral Changes
Because the system produces clinical diagnostic reports, any architectural refactoring must be verified using regression testing against a baseline set of samples. The modernized pipeline must produce identical clinical interpretations for the baseline cohort, or any deviations must be scientifically justified and approved.
