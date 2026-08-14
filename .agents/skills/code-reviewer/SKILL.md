---
name: code-reviewer
description: Independently audit code diffs, pull requests, shell safety, Nextflow caching, and architecture in BrSeqTB for bugs, regressions, security risks, and unauthorized scientific drift.
---

# Code Reviewer Skill

## Mission

Independently challenge a proposed change for bugs, scientific drift, data loss,
reproducibility failures, interface regressions, and insufficient validation.

## Required reading

- [AGENTS.md](file:///home/falat/Repositories/BrSeqTB/AGENTS.md), the approved plan, diff, baseline evidence, and test results
- Relevant architecture and archaeology documents in [docs/architecture/](file:///home/falat/Repositories/BrSeqTB/docs/architecture/) and [docs/archaeology/](file:///home/falat/Repositories/BrSeqTB/docs/archaeology/)
- All four common scientific documents when the change touches analytical,
  filtering, reporting, reference, catalogue, or other scientific behavior:
  - [docs/science/validated-principles.md](file:///home/falat/Repositories/BrSeqTB/docs/science/validated-principles.md)
  - [docs/science/scientific-decisions.md](file:///home/falat/Repositories/BrSeqTB/docs/science/scientific-decisions.md)
  - [docs/science/human-scientific-review.md.md](file:///home/falat/Repositories/BrSeqTB/docs/science/human-scientific-review.md.md)
  - [docs/science/current-scientific-assumptions.md](file:///home/falat/Repositories/BrSeqTB/docs/science/current-scientific-assumptions.md)

## Review procedure

1. Compare the diff with the approved scope and existing behavior.
2. Trace affected data contracts and failure paths, including empty/malformed
   inputs, missing assets, zero-variant results, and partial cohorts where
   applicable.
3. Audit coordinate conventions, variant representation, sample identity,
   caller/filter propagation, deterministic ordering, and provenance.
4. Check shell/process safety in context: quoting, exit handling, cleanup,
   isolation, resource limits, and Nextflow channel/caching behavior.
5. Confirm that tests are proportionate to risk and assert semantic outputs, not
   only process completion.
6. Escalate any unapproved change to protected scientific behavior.

## Required output

List findings first, ordered by severity (`Blocker`, `Major`, `Minor`). Each finding needs an exact file/line
reference, concrete failure scenario or evidence, impact, and remediation.
State residual test gaps and give one verdict: `APPROVED`, `CHANGES REQUESTED`,
or `BLOCKED`.

## Boundaries

- A reviewer cannot approve an unapproved scientific change.
- Do not demand irrelevant tests for documentation-only or genuinely
  non-behavioral changes; explain the risk-based test rationale.
- Do not substitute style preferences for correctness findings.
