# Architectural Risk Assessment

## Executive Summary
This document evaluates the software architecture of BrSeqTB from a scientific-software perspective. The focus is on whether the current architecture allows scientific assumptions to be made explicit, tested, versioned, and reproduced.

## 1. Coupling and Hardcoded Scientific Parameters
**Risk**: Scientific parameters (e.g., thresholds for AF, read depth, clustering distances) are hardcoded directly into execution scripts rather than being exposed as configurable, versioned parameters.
* **Evidence**: `bin/transmission.py` (`CUTOFF = 12`), `bin/mixInfection.py` (`MIX_THRESHOLD = 0.35`), `bin/ntmFilter.sh` (`NTM_POS=1472307`, `CUTOFF=0.20`), `bin/clinicalReport.py` (borderline mutations set).
* **Impact**: Changing a scientific parameter requires modifying source code, making it difficult to track parameter provenance across different runs or to perform parameter sweeps. 
* **Requirement**: Extract all scientific parameters into a centralized, version-controlled configuration file (e.g., a JSON or YAML parameters file).

## 2. Hidden Dependencies and Embedded Data
**Risk**: Significant reference data is embedded directly within source code.
* **Evidence**: `bin/lineage.py` contains a 5,760-line dictionary of lineage SNPs. 
* **Impact**: Updating the lineage database requires a code change. This conflates data updates with code updates and hinders reproducibility if the dictionary is changed without a code version bump.
* **Requirement**: Extract embedded data into external, versioned reference files (e.g., TSV/CSV) that are read by the pipeline.

## 3. Provenance and Traceability
**Risk**: The final clinical report (`results/clinicalReport/<sample>.docx`) and resistance summaries do not embed the exact versions of the databases used (e.g., the specific version/date of the WHO catalogue, the exact version of the pipeline).
* **Impact**: Years later, it may be impossible to know exactly which rule set produced a specific clinical result.
* **Requirement**: Ensure all outputs, especially clinical reports and final tables, embed metadata regarding pipeline version, reference genome version, and WHO catalogue version.

## 4. Testability and Modularity
**Risk**: The pipeline consists of monolithic Python and Bash scripts that mix data parsing, biological logic, and file I/O.
* **Evidence**: `bin/resistanceTarget.py` and `bin/clinicalReport.py` are large scripts lacking isolated functions with unit tests.
* **Impact**: It is nearly impossible to unit-test the biological logic (e.g., complex MNP resolution) without running the entire script on disk-based inputs.
* **Requirement**: Refactor scripts to separate I/O from scientific logic, enabling unit testing of critical biological decisions (e.g., WHO catalogue matching).

## 5. Configuration Management
**Risk**: Nextflow is used for workflow orchestration, but the scripts themselves do not accept command-line arguments for many of their key parameters, bypassing Nextflow's ability to track parameter changes.
* **Impact**: Nextflow's execution logs will not capture the internal parameters used by the Python/Bash scripts.
* **Requirement**: All scientifically relevant variables must be passed as arguments from Nextflow to the scripts.

## 6. External Tools and Environments
**Risk**: The pipeline relies on specific versions of tools (e.g., GATK4, LoFreq) but it's unclear if these are rigorously locked in a container or conda environment in a way that guarantees bit-for-bit reproducibility.
* **Requirement**: Strict containerization (Docker/Singularity) or strict Conda lockfiles must be enforced for all environments.

## 7. Scientific Traceability (Separation of Observation and Interpretation)
**Risk**: The pipeline often jumps from a computational observation directly to a clinical interpretation without intermediate evidence preservation.
* **Evidence**: The NTM filter directly outputs `FAIL` if AF >= 0.20 at position 1472307, discarding the nuanced evidence that might suggest a minor sequencing artifact.
* **Requirement**: The architecture should emit "computational evidence" (e.g., "AF=0.22 at 1472307") and separately apply an "interpretation rule" (e.g., "If AF >= 0.20, classify as NTM").

## Summary of Architectural Requirements
1. **Centralized Parameters**: All scientific thresholds must be externalized to configuration files.
2. **Data Separation**: No reference databases or dictionaries should be embedded in code.
3. **Provenance Logging**: All final reports must include version metadata for code and data.
4. **Logic Isolation**: Biological decision logic must be decoupled from I/O to allow unit testing.
5. **Observation vs. Interpretation**: The system must store raw computational observations independently of their downstream clinical interpretation.
