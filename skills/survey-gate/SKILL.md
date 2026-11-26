---
name: survey-gate
description: Run GATE 1, the blind shuffle that tests whether the taxonomy partitions the corpus — sample, dispatch one blind placer, score three separate metrics, propose boundary rules, and re-score. Use after indexing and before any web search or prose, after every fetch wave, and after any change to TAXONOMY.md.
---

# survey-gate — GATE 1

Load `survey-method`. Precondition: `corpus.jsonl` exists.

## Steps

1. `survey --ws <ws> gate1 sample` — deterministic, stratified by source cluster, citable rows only.
2. Dispatch **one** `survey-agent:survey-blind-placer`. Its prompt names only two files:
   `<positioning_dir>/gate1_sample.md` and `<positioning_dir>/TAXONOMY.md`. Nothing else — not the
   seed key, not the corpus, not this conversation's reasoning. The comparison is void if it sees
   the other half.
3. `survey --ws <ws> gate1 score` → `TAXONOMY_TEST.{md,json}`, history appended.

## Reading the verdict — three metrics, three meanings

| metric | failing means | remedy | whose call |
|---|---|---|---|
| doubles over the ceiling | **the axis is not a partition** | sharpen axis definitions, add an axis, or promote the crosscut | owner, now |
| agreement under the fatal floor | the cell definitions are ambiguous | rewrite the cell tests | owner |
| agreement 60–70% | read the disagreements: on the seed's known-failure cases it is the design working | maybe none | lead |
| thin cell | a **corpus** gap (or a cell that is not a research area — GATE 2 decides) | Stage 3 | — |

Never relabel papers to pass. Never collapse the three verdicts into one in a report.

## Boundary rules

Read the blind reader's reasons on every disagreement and double. Where §3's prose names an
*implementer* but the axes name a *property*, write a boundary rule in `TAXONOMY.md` §4b as a dated
⚠️ amendment ("the axes win"). A rule may narrow or clarify; it may never widen a cell. **Any added
rule requires a re-score**: re-dispatch a fresh blind placer on the same worksheet.

## Re-runs

After every fetch wave (`survey-ingest` calls this skill). `gate1_history.jsonl` lets you compare: a
falling doubles rate on a larger corpus (the original went 5/30 → 1/30 on +47% corpus) is strong
evidence; a rise means the fetch changed the subject.

## Gate

Report the three metrics, the disagreement table and proposed boundary rules to the owner; on a
partition FAIL, present the remedies as options. `survey log "GATE 1 run N: …"`.
