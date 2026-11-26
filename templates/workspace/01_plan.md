# 01_plan — the pipeline

Living document. `00_brief.md` is frozen; this is where the brief is adjudicated and where stages,
gates and orderings live. `survey status` reads the artifacts and says which stage is next.

## §0 — Verdict on the brief

(Which steps of the request are kept, merged or split, and why. Record any framing correction the
paper depends on here — the original survey could not argue "X instead of Y" because X and Y were
orthogonal; saying so up front saved the contribution.)

## §1 — Stages

```
Stage 0  human     brief frozen + TAXONOMY.md + SEED_MAP.md + kill criteria       ── GATE 0
         early     prior-survey / novelty test (cheapest kill criterion first)
Stage 1  ∥ ×N      survey-indexer → `survey index build` → `survey index timeline`
Stage 2  serial    `survey ledger scan` → `survey ledger propose`   (writes no BibTeX)
Stage 2b           GATE 1 — `survey gate1 sample` → survey-blind-placer → `score`  ── GATE 1
Stage 3  serial    survey-gap-auditor (fresh session)                              ── GATE 2
Stage 4  ∥ ×gaps   survey-scout → `survey candidates merge --wave N`               ── GATE 3
                   ↳ {{owner}} fetches into {{dir_inbox_dir}}/waveN/<citekey>.pdf
Stage 4b           ingest: file sanity, `survey transcriptions`, index rows, GATE 1 re-run
Stage 5  ∥ ×cells  survey-synthesist per cell + context — claims.tsv FIRST
         serial    `survey ledger merge-claims` → survey-ref-curator → `survey ledger emit`
Stage 6  serial    crosscut synthesist (after every cell)  → synthesis cold read
                   → re-derive CONTRACTS.md's governing argument from the syntheses  ── GATE 4
Stage 7  ∥         survey-writer: body → crosscut → gap → intro/context/method LAST → conclusion
Stage 8  serial    `survey verify` → survey-cold-reader (paper)                    ── GATE 5 (human)
Stage 9            targeted rewrites → `survey build`
Stage 10 optional  external review (`survey review`), translation (`survey translate`)
```

**Orderings that must never break:**
- index → gap → scout
- GATE 1 before any web search or prose, and again after every fetch wave
- claims → merge-claims → emit — **the bibliography is an output of the synthesis**
- every cell → crosscut
- body sections → introduction **last** (writing §1 first is how a survey argues what its body does not support)
- cold read only on the assembled paper, never per section
- in revision: production defects first, citation rendering last

## §2 — The gates

- **GATE 1** — the blind shuffle. Thresholds in `TAXONOMY.md` §5 (generated from `survey.toml`).
  Three metrics, three verdicts: doubles fail = the axis is broken; agreement fatal = the cell
  definitions are ambiguous; thin cell = a corpus gap for Stage 3, not an axis defect.
- **GATE 2** — shocked-to-find-missing: for every cell the auditor names the one paper a reviewer
  would be astonished the survey omits. No such paper → the cell is not a research area.
- **GATE 3** — scope: {{owner}} may strike a whole gap; recorded in `gap_report.md` so it is not re-raised.
- **GATE 4** — machine: `survey verify --only 2 3 4 5 5a 6` passes before drafting.
- **GATE 5** — {{owner}}'s review: full `survey verify`, then the cold read.

## §3 — What is already known and must not be re-derived

(Measured facts about the inherited corpus: counts, defects, collisions. Generated numbers go in
`survey stats`, not here.)

## §4 — Open items

- `[[DECIDE:D-01]]` …
