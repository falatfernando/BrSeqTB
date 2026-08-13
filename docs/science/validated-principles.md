# Validated Scientific Principles

This document records the established, scientifically validated principles that underpin the BrSeqTB project. 

> [!IMPORTANT]
> Only include principles here if there is sufficient evidence to treat them as project-level scientific facts. Assumptions requiring validation remain in `current-scientific-assumptions.md`.

## Principle 1: Reference Coordinate System

### Statement
All genomic coordinates, variant calls, and annotations must be strictly based on the *Mycobacterium tuberculosis* H37Rv reference genome.

### Evidence
The global MTB genomics community and the WHO drug resistance catalogue standardized on H37Rv.

### Scope
Applies to all alignment, variant calling, and annotation stages.

### Limitations
May poorly represent large structural insertions present in clinical strains but absent in H37Rv.

### Confidence
HIGH

### Date validated
August 13, 2026

---

## Principle 2: Repetitive Region Masking

### Statement
Variants within PE/PPE family genes and highly repetitive elements (e.g., transposases) are prone to alignment artifacts and must be excluded from core genome phylogenetic analysis to prevent false transmission clustering.

### Evidence
Standard bioinformatics consensus in MTB genomic epidemiology (e.g., universal masking of PE/PPE genes).

### Scope
Applies to the generation of the SNP matrix and downstream phylogenetic/transmission analysis.

### Limitations
Excludes potentially biologically relevant adaptive mutations occurring in these regions.

### Confidence
HIGH

### Date validated
August 13, 2026

---

## Principle 3: WHO Catalogue Hierarchy

### Statement
Drug resistance prediction must strictly adhere to the confidence grading hierarchy established by the WHO catalogue. Only variants graded as "Assoc w R" or "Assoc w R - Interim" are sufficient to predict phenotypic resistance.

### Evidence
WHO 2023 2nd Edition Catalogue guidelines.

### Scope
Applies to the interpretation of variant calls for clinical reporting.

### Limitations
Catalogue is periodically updated; predictions are bound to the specific catalogue version used.

### Confidence
HIGH

### Date validated
August 13, 2026
