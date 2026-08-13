# Human Scientific Review — Current BrSeqTB Scientific & Analytical Assumptions

**Document ID:** SCI-001-HR  
**Repository:** LaPAM-USP/BrSeqTB  
**Reviewer:** Fernando Falat  
**Role:** Main bioinformatician / developer and scientific reviewer  
**Date:** 2026-08-13  
**Review target:** `docs/science/current-scientific-assumptions.md`

---

## 1. Purpose

This document provides the human/domain-expert review of the scientific and
analytical assumptions identified during repository archaeology.

Its purpose is to distinguish:

1. assumptions that are accepted and should be preserved;
2. assumptions that are accepted but require better documentation;
3. assumptions that require scientific investigation;
4. historical behaviors that should be intentionally preserved;
5. unresolved questions that require experimental, computational, or expert
   validation.

This document represents the current scientific reviewer's assessment. It does
**not** authorize implementation changes.

---

# 2. Review Status Vocabulary

Each assumption receives one of the following statuses:

### VALIDATED

The reviewer accepts the assumption as scientifically appropriate for the
current project scope.

### VALIDATED — PRESERVE

The assumption is accepted and should remain unchanged unless new evidence
justifies reconsideration.

### VALIDATED — DOCUMENTATION REQUIRED

The behavior is accepted, but its scientific rationale or provenance should be
better documented.

### PARTIALLY VALIDATED

The general concept is accepted, but one or more details require further
investigation.

### REQUIRES INVESTIGATION

There is insufficient evidence to establish scientific validity.

### HISTORICAL / INTENTIONALLY PRESERVED

The behavior is an intentional project decision and should not be changed
without explicit scientific-owner approval.

### UNKNOWN

The reviewer cannot currently determine whether the assumption is correct.

---

# 3. Executive Summary

The review identifies several assumptions that can currently be accepted as
part of the intended BrSeqTB methodology, while several others require
additional investigation before modernization.

The most important unresolved scientific questions are:

1. Whether the current 5% allele-frequency threshold is unnecessarily
   restrictive for low-frequency resistance-associated variants.
2. Whether the current single-locus NTM detection strategy is sufficient.
3. Whether phylogenetic execution behaves correctly for datasets containing
   only one or two samples.
4. Whether the current complex-variant resolution logic contributes to
   apparent heteroresistance/frameshift calls, particularly in bedaquiline
   resistance-associated loci.
5. Whether sequencing/alignment artifacts, particularly in homopolymeric
   regions, explain some apparently resistance-associated GATK calls.

These issues should remain **open scientific questions** until appropriately
validated.

No production implementation changes are authorized by this document.

---

# 4. Scientific Assumption Review

## SA-001 — Reference Genome Model & Sequence Definition

### Current assumption

BrSeqTB models *Mycobacterium tuberculosis* using a haploid genome with a
single circular chromosome and uses H37Rv reference coordinates
(NC_000962.3) as the coordinate system for genomic analysis.

### Human assessment

**VALIDATED — PRESERVE**

The use of H37Rv / NC_000962.3 as the reference coordinate system is accepted
for the current pipeline.

### Scientific assessment

The reference coordinate system is appropriate for the current MTB genomic
analysis workflow.

The assumption that MTB is represented as a haploid genome is appropriate for
the intended single-strain genomic representation, while mixed infection and
within-host variation are handled separately by dedicated pipeline logic.

### Required action

- Preserve the reference genome.
- Ensure the exact reference version remains explicit and version-controlled.
- Ensure future pipeline outputs retain reference provenance.

### Implementation change authorized?

**NO**

---

# SA-002 — Hypervariable / Repetitive Region Masking

### Current assumption

The predefined `forbidden_genes.txt` set is excluded from core SNP matrices
and phylogenetic analyses because these regions are prone to alignment
ambiguity and other sources of unreliable phylogenetic signal.

### Human assessment

**VALIDATED — PRESERVE**

The use of repetitive/hypervariable region masking is accepted as standard
practice for MTB genomic analyses of this type.

### Scientific assessment

The masking strategy is considered appropriate for reducing problematic
phylogenetic signal originating from repetitive or highly variable regions.

### Required action

The scientific rationale and provenance of the current forbidden-region list
should eventually be documented more explicitly.

### Implementation change authorized?

**NO**

---

# SA-003 — Low-Frequency Variant Detection and 5% AF Threshold

### Current assumption

The pipeline uses LoFreq to identify low-frequency variants and applies a
minimum allele-frequency threshold of approximately 5%.

### Human assessment

**REQUIRES INVESTIGATION**

The use of LoFreq for low-frequency variant detection is accepted.

However, the current 5% AF reporting threshold may be unnecessarily
restrictive for some MTB resistance-associated variants.

### Evidence / observations

The reviewer has observed evidence of resistance-associated variants occurring
at allele frequencies below 5%, including:

- bedaquiline-associated resistance-associated variants observed at
  approximately 1% AF;
- variants around 4% AF identified in another pipeline and associated with
  confirmed resistance phenotypes.

These observations suggest that a 5% global reporting threshold may exclude
potentially biologically relevant low-frequency variants.

### Important scientific distinction

Evidence that some resistance-associated variants can occur below 5% AF does
**not** establish that all variants detected at 1–5% AF are genuine or should
automatically be interpreted as resistance.

Lowering the threshold will increase sensitivity but may also increase:

- sequencing-error-derived calls;
- alignment artifacts;
- false positives;
- spurious low-frequency variants.

Therefore the AF threshold should not be changed in isolation.

### Future investigation

Evaluate candidate lower thresholds using, at minimum:

- mapping quality;
- base quality;
- alternative read count;
- sequencing depth;
- strand support;
- strand bias;
- local sequence context;
- homopolymers / low-complexity regions;
- LoFreq quality metrics;
- phenotype-confirmed isolates;
- comparison with MAGMA parameters;
- comparison with other validated MTB pipelines.

### Current decision

The hypothesis is:

> The 5% AF threshold may be unnecessarily restrictive for MTB
> resistance surveillance.

This hypothesis requires validation before implementation.

### Implementation change authorized?

**NO**

---

# SA-004 — Heteroresistance vs Fixed Mutation Classification

### Current assumption

Variants with:

- AF >= 0.90 → `HOM`
- 0.05 <= AF < 0.90 → `HET`

are interpreted as fixed versus heteroresistant/subclonal variants.

### Human assessment

**HISTORICAL / INTENTIONALLY PRESERVED**

This classification represents an expert rule established by the project's
scientific leadership.

### Scientific assessment

The rule is intentionally part of the project's current interpretation
framework and should not be changed casually.

### Required action

The provenance of this rule should eventually be documented, including:

- scientific rationale;
- project owner;
- date/origin;
- intended interpretation;
- limitations.

### Implementation change authorized?

**NO**

Any future modification requires explicit scientific-owner review.

---

# SA-005 — Minimum Sequencing Depth for Diagnostic Loci

### Current assumption

A minimum sequencing depth of 10× is required at diagnostic loci used for
resistance/susceptibility interpretation.

### Human assessment

**VALIDATED — DOCUMENTATION REQUIRED**

The 10× threshold is accepted for the current pipeline.

### Evidence

The threshold was established empirically during the development and use of
the pipeline.

### Required action

The empirical basis for the 10× threshold should eventually be documented
more explicitly so that future maintainers understand its origin.

### Implementation change authorized?

**NO**

---

# SA-006 — Single-Locus NTM Detection

### Current assumption

Potential NTM contamination is identified using a specific genomic locus
(NC_000962.3:1472307) and allele-frequency/genotype criteria.

### Human assessment

**PARTIALLY VALIDATED / REQUIRES INVESTIGATION**

The current rule is recognized as a useful component of NTM detection, but it
has not yet been established that this single-locus strategy is sufficient for
robust NTM detection.

### Scientific concern

NTM contamination and its effect on MTB genomic analysis are known concerns
for this pipeline, particularly because contamination can also affect
phylogenetic interpretation.

### Required investigation

Compare the current approach against strategies implemented by relevant
MTB genomic pipelines, including:

- MAGMA;
- TB-Profiler;
- other appropriate MTB WGS pipelines.

Investigate:

- whether NTM detection is performed at additional loci;
- whether genome-wide taxonomic classification is used;
- contamination thresholds;
- how mixed MTB/NTM samples are handled;
- implications for downstream phylogenetics.

### Current decision

Preserve the current implementation while treating the sufficiency of the
strategy as an open scientific question.

### Implementation change authorized?

**NO**

---

# SA-007 — Mixed Clonal Infection Detection

### Current assumption

Mixed/polyclonal MTB infection is identified using the proportion of
heterozygous SNPs after exclusion of known resistance loci, with a threshold
of approximately 35%.

### Human assessment

**VALIDATED — PRESERVE**

The current mixed-infection detection strategy is considered to be working
satisfactorily in the project.

### Required action

Future modernization should preserve its current behavior unless new
validation demonstrates a need for modification.

The existing behavior should eventually be protected by regression tests.

### Implementation change authorized?

**NO**

---

# SA-008 — 12-SNP Transmission Cluster Threshold

### Current assumption

Transmission clusters are identified using a maximum pairwise distance of
12 core SNPs, implemented through an MST-based clustering procedure.

### Human assessment

**VALIDATED — PRESERVE**

The 12-SNP threshold and current clustering behavior are accepted for the
current project.

### Required action

The scientific provenance and intended interpretation of the 12-SNP
threshold should be documented if not already available.

### Implementation change authorized?

**NO**

---

# SA-009 — Phylogenetic Model and Bootstrap Strategy

### Current assumption

Phylogenetic analysis uses HKY+I+G with 1000 ultrafast bootstrap replicates.

### Human assessment

**PARTIALLY VALIDATED / REGRESSION TEST REQUIRED**

The current phylogenetic model has been used successfully and is considered
to be working well for the project's normal use cases.

### Known historical concern

The reviewer remembers previous problems when running phylogenetic analysis
with:

- a single sample;
- two samples.

It is currently unknown whether this issue was fixed.

### Required investigation

Explicitly test the current pipeline with:

1. one sample;
2. two samples;
3. a small multi-sample dataset;
4. a normal production-sized dataset.

Determine whether the current implementation:

- fails;
- produces an invalid tree;
- produces a trivial tree;
- produces misleading bootstrap values;
- or handles these cases appropriately.

### Current decision

Do not change the phylogenetic implementation until the current behavior is
reproduced and characterized.

### Implementation change authorized?

**NO**

---

# SA-010 — WHO 2023 2nd Edition Catalogue Interpretation

### Current assumption

Resistance interpretation follows the WHO 2023 2nd Edition catalogue and
the corresponding grading hierarchy implemented in the pipeline.

### Human assessment

**VALIDATED — PRESERVE**

The pipeline's implementation of the catalogue-based resistance reporting
framework is accepted.

### Scientific assessment

The pipeline reports resistance according to the catalogue classification
implemented in its current version.

### Required action

Future modernization must preserve:

- catalogue provenance;
- catalogue version;
- grading information;
- distinction between resistance categories;
- traceability from mutation to catalogue annotation.

The interpretation should not silently change when the software architecture
is modernized.

### Implementation change authorized?

**NO**

---

# SA-011 — Complex Variant and MNP Resolution

### Current assumption

The pipeline applies specific rules for resolving overlapping MNPs, SNPs,
insertions, and deletions.

### Human assessment

**UNKNOWN / REQUIRES INVESTIGATION**

The reviewer cannot currently establish whether the current complex-variant
resolution rules are scientifically appropriate in all cases.

### Known related problem

A separate problem has been observed involving GATK-generated apparent
heteroresistance-associated frameshift variants, particularly in the context
of bedaquiline resistance-associated loci.

These calls have been excluded by other pipelines and were contradicted by
phenotypic susceptibility results.

### Important distinction

It is currently **unknown** whether this problem is caused by the
`resolve_complex_variants()` logic itself.

Possible alternative explanations include:

- sequencing artifacts;
- homopolymer-associated errors;
- local alignment ambiguity;
- indel representation;
- GATK local assembly behavior;
- variant normalization;
- annotation of apparent frameshifts;
- low-frequency sequencing noise;
- interaction between variant calling and downstream interpretation.

### Required investigation

The BDQ-associated false-positive cases should be investigated independently
from the general MNP-resolution rule.

The investigation should examine:

- raw reads;
- alignment;
- local sequence context;
- homopolymer structure;
- mapping quality;
- base quality;
- allele frequency;
- alternative read support;
- strand support;
- GATK representation;
- normalized representation;
- annotation;
- comparison with LoFreq;
- comparison with MAGMA;
- comparison with other validated pipelines;
- phenotype.

### Current decision

Do not modify complex-variant resolution or GATK calling until the failure
mechanism is established.

### Implementation change authorized?

**NO**

---

# SA-012 — Explicit Borderline rpoB Mutation Flagging

### Current assumption

A predefined set of eight rpoB mutations is explicitly flagged as
borderline/low-level rifampicin resistance in clinical reports.

### Human assessment

**VALIDATED — PRESERVE**

The current borderline mutation rule is accepted.

### Required action

The list should remain explicitly version-controlled and documented.

Any future modification should require scientific-owner review.

### Future IS6110 integration

A new IS6110 detection module is currently under development and is intended
to become part of BrSeqTB.

Whether IS6110 evidence should interact with the existing borderline
resistance reporting framework is a **separate future scientific decision**.

This should not be implicitly coupled to SA-012.

### Implementation change authorized?

**NO**

---

# 5. Consolidated Status

| ID | Assumption | Status | Immediate Action |
|---|---|---|---|
| SA-001 | H37Rv reference model | VALIDATED — PRESERVE | None |
| SA-002 | Repetitive/hypervariable masking | VALIDATED — PRESERVE | Document provenance |
| SA-003 | 5% AF threshold | REQUIRES INVESTIGATION | Evaluate lower thresholds |
| SA-004 | HOM/HET classification | HISTORICAL / INTENTIONALLY PRESERVED | Document provenance |
| SA-005 | 10× diagnostic coverage | VALIDATED — DOCUMENTATION REQUIRED | Document empirical basis |
| SA-006 | Single-locus NTM detection | PARTIALLY VALIDATED | Compare with other pipelines |
| SA-007 | Mixed infection detection | VALIDATED — PRESERVE | Add regression tests |
| SA-008 | 12-SNP transmission threshold | VALIDATED — PRESERVE | Document provenance |
| SA-009 | HKY+I+G phylogeny | PARTIALLY VALIDATED | Test n=1/n=2 behavior |
| SA-010 | WHO catalogue interpretation | VALIDATED — PRESERVE | Preserve provenance/versioning |
| SA-011 | Complex variant resolution | REQUIRES INVESTIGATION | Investigate BDQ/frameshift cases |
| SA-012 | Borderline rpoB flags | VALIDATED — PRESERVE | Preserve and document |

---

# 6. Scientific Issues Requiring Priority Investigation

## Priority 1 — Low-Frequency Resistance Variants

Determine whether the current 5% AF threshold causes clinically/scientifically
relevant resistance-associated variants to be missed.

This investigation should evaluate sensitivity/specificity tradeoffs rather
than simply lowering the threshold.

---

## Priority 2 — BDQ-Associated Apparent Frameshift/Heteroresistance Calls

Determine the source of apparent bedaquiline resistance-associated frameshift
calls that are:

- detected by GATK;
- excluded by other pipelines;
- contradicted by susceptible phenotypes.

This should include investigation of sequencing and alignment artifacts,
particularly homopolymeric regions.

---

## Priority 3 — NTM Detection

Determine whether the current single-locus NTM screening strategy is
sufficient and how it compares with established MTB WGS pipelines.

---

## Priority 4 — Small-Sample Phylogenetics

Determine whether phylogenetic analysis behaves correctly for datasets with
one or two samples.

---

# 7. Scientific Principles Currently Considered Safe to Preserve

The following principles can currently be treated as project-level
constraints:

1. H37Rv / NC_000962.3 is the current reference coordinate system.
2. Repetitive/hypervariable regions are excluded from the core phylogenetic
   signal according to the project's masking strategy.
3. The current mixed-infection detection behavior should be preserved.
4. The current 12-SNP transmission-clustering behavior should be preserved.
5. WHO catalogue provenance must remain explicit in resistance interpretation.
6. The current borderline rpoB flagging behavior should be preserved.
7. Scientific interpretation must remain traceable to the underlying genomic
   evidence.

These principles should still be reviewed by the Senior Scientist before being
copied into `validated-principles.md`.

---

# 8. Explicitly Unresolved Questions

The following questions remain open:

### Q1 — Low-frequency variants

What is the empirically defensible minimum AF for reporting resistance-
associated variants in this pipeline?

### Q2 — NTM

Is the current single-locus NTM detection mechanism sufficiently sensitive
and specific?

### Q3 — Phylogeny

Does the current phylogenetic implementation behave correctly for n=1 and n=2?

### Q4 — BDQ false positives

What mechanism produces the apparent GATK-derived BDQ frameshift/
heteroresistance calls?

### Q5 — Homopolymers

To what extent do homopolymeric regions contribute to false-positive indel or
frameshift calls?

### Q6 — Complex variants

Are the current MNP/indel/SNP resolution rules scientifically correct across
the variant representations produced by the current callers?

---

# 9. Prohibited Premature Changes

Based on this review, future agents MUST NOT independently:

- lower the AF threshold;
- modify the HOM/HET classification;
- change the 10× coverage threshold;
- modify mixed-infection classification;
- change the 12-SNP transmission threshold;
- change the phylogenetic model;
- change WHO resistance interpretation;
- modify borderline rpoB rules;
- alter complex-variant resolution;
- modify GATK/LoFreq filtering;

without scientific review and appropriate validation.

The existence of a suspected problem is not sufficient justification for
changing production behavior.

---

# 10. Review Conclusion

The repository archaeology successfully identified the major scientific and
analytical assumptions currently encoded in BrSeqTB.

The human review confirms that several assumptions represent intentional and
accepted project behavior.

However, four areas require additional scientific investigation before
modernization:

1. low-frequency resistance-associated variants;
2. NTM detection;
3. small-sample phylogenetic behavior;
4. apparent BDQ-associated frameshift/heteroresistance calls.

These issues should be carried forward into the Senior Scientist's scientific
risk assessment and into future QA/regression testing.

**No production implementation changes are authorized by this document.**