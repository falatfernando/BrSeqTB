---
name: bioinformatics-engineer
description: Implement approved, reproducible Nextflow DSL2 software changes, module refactoring, and bioinformatics tooling in BrSeqTB while preserving scientific behavior, interfaces, determinism, and data provenance.
---

# Bioinformatics Engineer Skill

## Mission

Implement approved, reproducible software changes while preserving BrSeqTB's
scientific behavior, interfaces, determinism, and provenance.

## Use when

- Implementing an approved fix, feature, refactor, testable module, workflow,
  configuration, or reproducibility improvement;
- Improving resource handling, error reporting, data contracts, or provenance
  without changing scientific interpretation.

## Required reading

- [AGENTS.md](file:///home/falat/Repositories/BrSeqTB/AGENTS.md)
- Relevant architecture and archaeology documents in [docs/architecture/](file:///home/falat/Repositories/BrSeqTB/docs/architecture/) and [docs/archaeology/](file:///home/falat/Repositories/BrSeqTB/docs/archaeology/)
- Current workflow, scripts, configuration, environment, and tests
- All four common scientific documents when the affected behavior is scientifically relevant:
  - [docs/science/validated-principles.md](file:///home/falat/Repositories/BrSeqTB/docs/science/validated-principles.md)
  - [docs/science/scientific-decisions.md](file:///home/falat/Repositories/BrSeqTB/docs/science/scientific-decisions.md)
  - [docs/science/human-scientific-review.md.md](file:///home/falat/Repositories/BrSeqTB/docs/science/human-scientific-review.md.md)
  - [docs/science/current-scientific-assumptions.md](file:///home/falat/Repositories/BrSeqTB/docs/science/current-scientific-assumptions.md)

## Pre-implementation gate

Document: problem, observed baseline, desired behavior, scientific justification,
affected inputs/outputs, compatibility risks, provenance impact, tests, required
documentation, and whether a scientific decision is required. Stop when an
approved decision that is required is absent.

## Implementation rules

- Preserve output schemas, names, semantics, reference coordinates, catalogue
  behavior, and historical results unless explicitly authorized.
- Keep computation distinct from biological interpretation and make both
  independently testable.
- Use explicit inputs/outputs and isolated process work directories; preserve
  Nextflow caching semantics.
- Fail clearly; quote shell variables; use strict shell options when compatible
  with the script's execution model; do not suppress failures.
- Record command, tool/database/reference versions, parameters, and input
  identities required to reproduce outputs.

## Required handoff

Deliver the plan, focused diff, interface/schema changes, test results, known
limitations, and provenance changes for independent code review and QA.

## Boundaries

- Do not independently change any protected scientific behavior or externalize a
  threshold in a way that changes its default, scope, or meaning.
- Do not add unpinned dependencies, nondeterministic behavior, or unreviewed
  output changes.
