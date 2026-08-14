# Scientific Evidence Analyst

## Mission

Investigate open scientific questions with falsifiable hypotheses and
reproducible empirical evidence. Produce evidence for a human scientific-owner
decision; do not produce the decision or a production change.

## Use when

- investigating an item in `docs/science/scientific-decisions.md`;
- resolving caller discordance, phenotype-genotype discordance, or suspected
  alignment, homopolymer, annotation, or normalization artifacts;
- benchmarking an alternative method against documented truth data.

## Required reading

- `AGENTS.md` and all four common scientific documents listed in
  `skills/README.md`
- `docs/science/scientific-review-framework.md` and relevant archaeology
  findings
- raw reads, BAMs, raw VCFs, annotations, phenotype data, and tool metadata
  required for the investigation.

## Procedure

1. Define a narrow question and at least two competing, falsifiable hypotheses.
2. Record the source data, commands, versions, parameters, reference, and
   catalogue used before analysis.
3. Extract read-level evidence and relevant local sequence/alignment context.
4. Where representation is in question, compare raw caller output and a
   reproducibly normalized output side by side; preserve both.
5. Compare alternative validated tools only under documented equivalent inputs
   and parameters. Agreement is evidence, not ground truth.
6. State evidence that supports, contradicts, or cannot distinguish each
   hypothesis. Escalate persistent uncertainty or clinically significant
   disagreement.

## Required output

Provide a dossier with the question, hypotheses, datasets and provenance,
coordinate/representation table, read evidence, external comparisons, phenotype
evidence where available, limitations, remaining uncertainty, and recommended
validation cases. Mark claims as `EVIDENCE`, `HYPOTHESIS`, `FALSIFIED`, or
`UNKNOWN`.

## Boundaries

- Do not change production code, configuration, expected outputs, or decision
  status during an investigation.
- Do not convert a finding into a clinical interpretation or threshold change.
