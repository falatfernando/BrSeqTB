# BrSeqTB Agent Skills

These portable instruction packs define complementary roles for agents working on
BrSeqTB. They are plain Markdown so they can be used by any agent platform.
`AGENTS.md` is the governing authority; a skill may add procedure, but never
override it.

## Use the right skill

| Skill | Use for | Does not authorize |
|---|---|---|
| `repository-archaeologist` | Establishing what legacy code does | Refactoring or scientific conclusions |
| `scientific-architect` | Governance, risk classification, decision records | Scientific-owner decisions |
| `mtb-genomics-specialist` | Biological and artifact assessment | Clinical reporting changes |
| `scientific-evidence-analyst` | Empirical investigation of open questions | Production changes or closing decisions |
| `bioinformatics-engineer` | Approved implementation and reproducible engineering | Scientific parameter changes |
| `code-reviewer` | Independent review of a proposed change | Scientific approval |
| `qa-validation` | Test design and validation evidence | Changing expected scientific behavior |

## Common operating rules

1. Read `AGENTS.md` first. For scientifically relevant work also read:
   `validated-principles.md`, `scientific-decisions.md`,
   `human-scientific-review.md.md`, and `current-scientific-assumptions.md`.
2. Label claims as `OBSERVED`, `ASSUMPTION`, `VALIDATED PRINCIPLE`,
   `HYPOTHESIS`, `SCIENTIFIC DECISION`, or `UNKNOWN`.
3. Current behavior is not proof of scientific validity. Preserve it unless an
   explicit scientific-owner decision authorizes change.
4. Do not change protected behavior: thresholds, reference data, catalogues,
   masking, biological interpretation, phylogeny, transmission, NTM, IS6110,
   or variant normalization/resolution.
5. Preserve traceability from raw evidence through caller, annotation, reference
   or catalogue version, interpretation, and report.
6. Record exact commands, tool versions, inputs, parameters, outputs, and file
   locations needed to reproduce a finding.

## Typical handoffs

`Archaeologist -> Engineer -> Reviewer + QA` for implementation.

`Evidence Analyst + MTB Specialist -> Scientific Architect -> human scientific
owner` for unresolved scientific questions.

Agents must stop and escalate rather than resolve an open scientific question by
consensus, intuition, or a code cleanup.
