---
name: survey-init
description: Start a new survey workspace — freeze the owner's request verbatim, declare the taxonomy as testable axes in survey.toml, scaffold the frozen contract documents, write kill criteria, and launch the prior-survey novelty test early. Use at the very start of a survey, or when status reports stage 0 incomplete.
argument-hint: "<workspace dir> [title]"
---

# survey-init — Stage 0

Load `survey-method` first.

## Steps

1. **Scaffold.** `survey --ws <ws> init --title "<title>"` writes `survey.toml`. Ask the owner (one
   AskUserQuestion, up to 4 questions): venue and length, language, the organising cut they have in
   mind, and whether fetching is theirs (it is — agents never download; confirm, do not ask whether).
2. **Freeze the brief.** Paste the request **verbatim** into `00_brief.md` — no tidying — then add
   the intake decisions and map every step of the request to a stage and skill. Write
   `**Frozen YYYY-MM-DD.**`. Corrections to the brief go in `01_plan.md` §0, never in the brief.
3. **Adjudicate the brief in `01_plan.md` §0.** Typical corrections from the first run: "a search
   tool" and "a timeline" are projections of the index, not stages; gap-finding needs a gate *before*
   it; importing references and building the outline are two steps; a framing the paper cannot defend
   (two orthogonal things presented as alternatives) is corrected now.
4. **Design the taxonomy as axes.** In `survey.toml` `[taxonomy]`: independent axes with two poles
   each; cells at their crossings, each with a one-line membership test answerable from the work
   itself; optional crosscut track (reads syntheses only) and context track ("why now"). Then
   `[paper].chapters` with roles, `[[origins]]` with seeds if references are inherited, `[guards]`.
   ⚠️ If the cut cannot be stated as axes, it cannot be tested — say so to the owner before going on.
5. **Render the frozen documents.** `survey --ws <ws> init` again. Fill `TAXONOMY.md` §1–§3,
   `CONTEXT_CARD.md` §1–§3, `SEED_MAP.md` failure cases; freeze each with its date.
6. **Kill criteria.** Fill `20_positioning/kill_criteria.md`: what makes the survey redundant (a prior
   survey with the same cut), wrong (the axis does not partition), or a proposal (a cell empty in the
   literature). Order them cheapest-first.
7. **Launch K-0 now, out of stage order** (method II-4): write `03_gap/gaps/G-00.md` (a prior-surveys
   brief with an accept bar: survey/taxonomy/SLR papers, class P or A, landing page opened) and
   dispatch one `survey-agent:survey-scout` on it. It runs in parallel with indexing.
8. `survey verify --only 0 1` and `survey status`; then `survey log "init"`.

## Gate 0

The owner approves the frozen brief, the axes and cells, and the kill criteria. Show them the 2×2 (or
grid) and each cell's membership test; ask whether any canonical work they know would not place.
