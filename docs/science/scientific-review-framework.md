# Scientific Decision Framework

This framework defines how future scientific decisions, modifications, and interpretations should be evaluated within the BrSeqTB project. The goal is to prevent the conflation of computational artifacts with biological reality, and to ensure all scientific changes are rigorously justified.

## Evaluation Workflow

When observing a behavior in the pipeline or proposing a change to scientific logic, follow this sequence:

### 1. Observation
Clearly state the computational output or pipeline behavior.
* *Example: "The pipeline flags sample X as an NTM because it has an AF of 0.25 at position 1472307."*

### 2. Technical Explanation
Identify exactly how the software produced this observation. Which algorithms, thresholds, and files were involved?
* *Example: "LoFreq called a variant at 1472307 with AF 0.25, and ntmFilter.sh classifies AF >= 0.20 as NTM FAIL."*

### 3. Biological Explanation
What is the intended biological meaning of this observation?
* *Example: "The polymorphism at 1472307 is intended to be a unique marker for Non-Tuberculous Mycobacteria."*

### 4. Alternative Hypotheses
What else could cause this observation besides the intended biological explanation?
* *Example: "The AF of 0.25 could be a sequencing artifact, a minor subclonal mutation in a pure MTB sample, or contamination from a different species that shares this polymorphism."*

### 5. Evidence
What empirical or literature evidence exists to support the biological explanation over the alternatives?
* *Example: "Literature search required to confirm if 1472307 is highly conserved in MTB and divergent in all NTMs."*

### 6. Uncertainty
What remains unknown? Are there edge cases where this logic fails?
* *Example: "It is unknown if rare MTB lineages naturally possess this polymorphism."*

### 7. Conclusion & Requirement
Define the final scientific decision and the engineering requirements to support it.
* *Example: "Conclusion: Relying on a single locus is high-risk for false positives. Requirement: Implement a multi-locus or k-mer based NTM screening approach."*

---

## Core Rules for Scientific Changes

1. **Never jump from computational observation directly to biological conclusion.** Always consider sequencing and alignment artifacts.
2. **Parameters require justification.** Do not change a threshold (e.g., AF cutoff, read depth) without documenting the empirical or literature basis for the new value.
3. **Preserve provenance.** If a biological rule is changed, ensure the system can record which rule version was used for a given sample.
4. **Distinguish evidence from interpretation.** Output the raw data (e.g., variant frequency) separately from the interpreted state (e.g., "Heteroresistant").
