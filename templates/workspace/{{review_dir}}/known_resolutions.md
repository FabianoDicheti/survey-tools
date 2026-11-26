# Known resolutions — read before triaging any comment batch

Preamble for every `survey-comment-triager`. Fill it **after** `survey review extract` and the
production-defect diagnosis, **before** `survey review batch`.

## What the reviewer actually read

(Which artifact went out — the repo build, or a one-off export? If an export, it is not the
submission artifact; fixes to it are off the critical path. Name the export's known defects.)

## Production-defect classes

If a comment's anchor (`comments.json` → `anchor`, `flags`) contains a raw `CITATION` field code,
garbled or merged text, or a mid-word break, the comment is almost certainly about conversion
damage, not content. Check the anchor before believing the comment. Grep `refs.bib` for every author
the comment names — a name the bibliography does not hold points at the export, not the manuscript.

| defect | symptom in anchors | status |
|---|---|---|

## Settled charges — do not re-litigate

| charge | resolution | evidence (artifact, not manuscript) |
|---|---|---|

## Vocabulary

category ∈ production_defect · bibliography · taxonomy_scope · evidentiary · overclaim ·
tone_clarity · attribution · formatting · other
disposition ∈ resolved · production_defect · rebuttal · declined · needs_fix · needs_review

Evidence cites an artifact: `file:line`, DOI, PDF page. Never restate the manuscript. Never invent a
file:line — use `needs_review`. A rebuttal is legitimate, but it still narrows the text that invited
the confusion (the reviewer twice merged two adjacent citations into one complaint).
