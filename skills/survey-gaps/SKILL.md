---
name: survey-gaps
description: Audit the indexed corpus against the taxonomy — coverage matrix by cell and decade, the per-gap briefs scouts will work from, and GATE 2 (the paper a reviewer would be shocked to find missing from each cell). Use after GATE 1 and again after every fetch wave, before any web search.
---

# survey-gaps — Stage 3, GATE 2

Load `survey-method`. Preconditions: `corpus.jsonl` exists; GATE 1 run (partition PASS).

## Steps

1. Dispatch **one fresh** `survey-agent:survey-gap-auditor` — never the agent or session that built the
   index (no self-audit). Its prompt names: the workspace, the wave number, `gap_report.md`'s struck
   gaps to carry forward, and any gaps already open (e.g. G-00 from init).
2. When it returns, check every brief in `<gap_dir>/gaps/G-nn.md` has: the cell, what is missing,
   what a paper must say to close it, an **accept bar**, a class-M cap, and whether it is a corpus or
   a literature gap (the latter only with the failed search named).
3. **GATE 2.** For each cell the auditor must name the one paper a reviewer would be astonished the
   survey omits, and say whether the corpus holds it. If it cannot name one, the cell is not a
   recognised research area — that is a taxonomy problem for the owner, not a search problem.
4. Read the accept bars critically: a bar written to fill a thin cell makes scouts over-select toward
   it (method III-8). Bars name a *property* of the paper, not the cell.
5. Taxonomy repairs appear only in the auditor's `## Taxonomy stress` section, as questions. Put
   them to the owner; do not apply them.

## Gate

Show the owner the coverage matrix, the GATE 2 table and the gap list. They may **strike** gaps
(GATE 3 begins here); record strikes with the reason in `gap_report.md` so the next wave's auditor
does not re-raise them. `survey log "gap audit wave N"`.
