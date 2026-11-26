---
name: survey-revise
description: Respond to an external review of the survey — extract the returned docx's comments with their anchors, separate production defects from substance first, verify the reviewer's sharpest charges against the artifacts, triage every comment in parallel batches under a fixed vocabulary, and sequence the fixes. Use when a reviewed .docx (or comment export) comes back.
argument-hint: "<returned.docx>"
---

# survey-revise — Stage 10

Load `survey-method`. Ordering (method II-9): **production defects first, citation rendering last.**

## W0 — Measure what came back

```bash
survey --ws <ws> review extract <returned.docx>
```
Count comments, anchored comments, suspected production defects (raw CITATION fields, mid-word joins,
author names absent from `refs.bib`). Note whether the reviewer edited text or only commented.

## W1 — Production defects (before judging any comment)

1. Establish what artifact the reviewer read (a one-off export is not the submission artifact).
2. `survey review fix-docx <returned.docx> <fixed.docx>` and diff what remains (`\m` merged fields,
   negation flips inside merged runs) — those need a human.
3. Fix the pipeline, rebuild with `survey build`, and mark every comment the rebuild alone resolves.

## Check the sharpest charges against the artifacts

Pick the three charges that would hurt most if true. Verify each against the PDF/bib (method I-11).
A charge can be a conflation (two adjacent citations merged into one complaint) — rebut with the
artifact, *and* narrow the text that invited it.

## Triage

1. Write `<review_dir>/known_resolutions.md`: what the reviewer saw, defect classes with their anchor
   symptoms, charges already settled, the vocabulary.
2. `survey review batch --n 6`, then dispatch one `survey-agent:survey-comment-triager` per batch in
   one message. Triage only — no file edits — so fixes never race.
3. `survey review merge` — it normalises vocabulary drift and refuses missing or doubly-dispositioned
   ids. Read `DISPOSITION_SUMMARY.md`; never hand-count categories.

## Workstreams and decisions

Group `needs_fix` into workstreams (bibliography acquisitions → `survey-fetchlist`/`survey-ingest`;
taxonomy scope; evidentiary/tone → `survey-draft` single-section). **Scope decisions are the owner's**
— present options with a recommendation that preserves the contribution (e.g. a new *scope*
dimension crossed with the grid rather than a fifth cell). Acquired works go through the same
pipeline as every other work, never bolted into the bibliography.

## Done when

Every comment has a disposition with artifact evidence (resolved / rebuttal / declined with reason),
`survey verify --build` passes, a fresh cold read runs on the revised assembly, and the rebuilt docx
has no production defects. Then `survey cite intext` / build as the last step. `survey log` throughout.
