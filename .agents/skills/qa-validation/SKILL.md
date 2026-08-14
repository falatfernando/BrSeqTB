---
name: qa-validation
description: Design and execute multi-tier verification test harnesses (unit, integration, regression, edge cases, semantic concordance) and audit test fixture provenance for BrSeqTB.
---

# QA and Scientific Validation Engineer Skill

## Mission

Design and execute proportionate tests that establish computational correctness,
behavioral preservation, reproducibility, and, where a documented truth set
exists, scientific validity.

## Required reading

- [AGENTS.md](file:///home/falat/Repositories/BrSeqTB/AGENTS.md), approved plan, review findings, baseline, tests, and affected
  implementation
- All four common scientific documents for scientifically relevant work:
  - [docs/science/validated-principles.md](file:///home/falat/Repositories/BrSeqTB/docs/science/validated-principles.md)
  - [docs/science/scientific-decisions.md](file:///home/falat/Repositories/BrSeqTB/docs/science/scientific-decisions.md)
  - [docs/science/human-scientific-review.md.md](file:///home/falat/Repositories/BrSeqTB/docs/science/human-scientific-review.md.md)
  - [docs/science/current-scientific-assumptions.md](file:///home/falat/Repositories/BrSeqTB/docs/science/current-scientific-assumptions.md)
- Fixture provenance and documented expected outcomes.

## Test design

Choose tests according to risk:

- Unit tests for isolated transformation or decision logic;
- Integration tests for workflow/data contracts;
- Regression tests for changed core or clinically relevant behavior;
- Negative and edge cases for malformed input, absent data, low coverage,
  ambiguous mappings, mixed infection, NTM, indels, and small cohorts when
  relevant;
- Scientific validation only against a documented, fit-for-purpose truth set.

`assets/auxCohort` is a regression fixture unless its biological truth and
intended coverage are explicitly documented. It must not be called a
gold-standard truth set by default.

## Execution and assessment

1. Record commands, environment, versions, parameters, fixture provenance, and
   resource use.
2. Assert content, schema, semantics, negative paths, and sample completeness;
   exit status alone is insufficient.
3. Compare baseline and candidate outputs semantically, accounting only for
   documented nondeterministic metadata such as timestamps.
4. Require exact preservation for unchanged behavior. Treat a justified,
   approved behavioral change as a separately versioned expected result.
5. Escalate clinical divergence, data truncation, nondeterminism, or a missing
   scientific decision rather than changing expectations.

## Required output

Report the test matrix, fixtures and their provenance, expected/actual semantic
results, concordance metrics where meaningful, failures, residual gaps, and one
verdict: `PASSED`, `FAILED`, or `BLOCKED`.

## Boundaries

- Do not change expected scientific results to accommodate code.
- Do not claim biological validation without documented truth data.
- Do not waive baseline regression for core behavior without a recorded,
  risk-based justification.
