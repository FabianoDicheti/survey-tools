---
name: survey-verify
description: GATE 5 — run the full mechanical verifier, then one survey-cold-reader on the assembled paper, and give the owner the gate report (failing checks, section verdicts, split rate, strongest reject reason, open placeholders). Use before every human gate and before any build.
---

# survey-verify — Stage 8, GATE 5

Load `survey-method`.

## Steps

1. `survey --ws <ws> placeholders` then `survey --ws <ws> verify --json`. Every FAIL is fixed (via the
   owning writer/curator) or explicitly accepted by the owner with a logged reason. WARNs are read.
2. Dispatch **one** `survey-agent:survey-cold-reader` in `paper` mode on the assembled paper. It reads
   only the chapters and `refs.bib`; anything the paper does not itself support is unsupported.
   It appends a dated entry to `COLD_READ.md` (append-only; `survey verify` §21 enforces).
3. Read the cold read's findings yourself against the paper. Its verdicts are a reading, not a ruling
   (method III-6, III-10): a surprising verdict may be a bad rule.

## The gate report (to the owner)

- verifier: FAIL count by check, WARN highlights;
- section verdicts: holds / narrow it / unsupported / cut, with counts;
- split rate with its denominator, against the ceiling;
- the strongest reject reason, whether it is fixable, and at what cost;
- open placeholders by namespace (all must become prose before submission);
- what the cold read credits as holding.

Ask for the owner's review (step 9 of most briefs). Their feedback becomes targeted rewrites via
`survey-draft` (single-section mode) — then this skill again. `survey log "GATE 5: …"`.
