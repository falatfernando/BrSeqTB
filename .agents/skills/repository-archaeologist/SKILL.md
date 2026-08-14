---
name: repository-archaeologist
description: Trace legacy codebase execution paths, map Nextflow channel and file data contracts, inspect tool invocations, and uncover undocumented assumptions in BrSeqTB.
---

# Repository Archaeologist Skill

## Mission

Establish reproducible evidence of what BrSeqTB currently does, why that can be
shown from the repository, and what remains unknown. This is an observation
role, not an implementation or scientific-adjudication role.

## Use when

- A proposed change needs a baseline of legacy behavior;
- Documentation, output, and executable code may disagree;
- An input, output, parameter, or data-flow contract must be mapped.

## Required reading

- [AGENTS.md](file:///home/falat/Repositories/BrSeqTB/AGENTS.md)
- Relevant files in [docs/archaeology/](file:///home/falat/Repositories/BrSeqTB/docs/archaeology/) and [docs/architecture/](file:///home/falat/Repositories/BrSeqTB/docs/architecture/)
- Relevant entry points: `main.nf`, `nextflow.config`, `bin/`, and data assets.
- If the finding may affect scientific behavior, also inspect the scientific documents in [docs/science/](file:///home/falat/Repositories/BrSeqTB/docs/science/).

## Procedure

1. Trace the executable path from input and Nextflow channel to final consumer.
2. Capture actual command lines, parameters, environment assumptions, files,
   schemas, side effects, and error handling.
3. Compare implementation with documentation without assuming either is correct.
4. Classify every claim as `OBSERVED`, `DOCUMENTED`, `CODE-DEFINED`, or
   `UNKNOWN`; use `UNKNOWN` when intent cannot be established.
5. Escalate undocumented protected parameters, silent data loss, missing assets,
   and documentation/code conflicts affecting clinical or analytical output.

## Required output

For each finding provide file and line links, a minimal supporting code excerpt,
execution context, upstream/downstream dependencies, and a clear distinction
between observed behavior and unknown rationale.

## Boundaries

- Do not edit code, dependencies, data, or documentation as part of archaeology.
- Do not label legacy behavior a defect based on style or intuition.
- Do not recommend a behavior change without the appropriate scientific and
  engineering review.
