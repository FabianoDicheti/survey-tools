---
name: survey-synthesize
description: Produce the evidence — one survey-synthesist per cell and context track (claims.tsv first), merge the claims, have the curator clear refusals, emit refs.bib, then the crosscut synthesis, the synthesis cold read, and the re-derivation of the governing argument in CONTRACTS.md. Use after the corpus is complete and GATE 1 passes.
argument-hint: "[track ids | --resume]"
---

# survey-synthesize — Stages 5–6, GATE 4

Load `survey-method`. Preconditions: GATE 1 partition PASS on the current corpus; `QUESTIONS.md`
frozen (write it now if not — one section per track, ~7 questions, **no quotations inside
questions**, method III-7).

## 1. Cells + context, in parallel

Dispatch one `survey-agent:survey-synthesist` per cell track **and** the context track, all in one
message. Each prompt names: the track id and dir, its corpus rows (`locus_proposed` = the cell, plus
the whole `split()` seed pool that includes it), its `QUESTIONS.md` section, and the blocked prior
prose it must not open. Repeat the read-block in the prompt, not only in the agent file.

`--resume`: dispatch only tracks without `synthesis.md`; a track with `claims.tsv` but no synthesis
keeps its claims.

## 2. Claims → ledger → bibliography (tools + one curator)

```bash
survey --ws <ws> ledger merge-claims
```
- **disputed** (tracks disagree on the cell): adjudicate each with the two reasons side by side; a
  genuine equal fit becomes a recorded split, not a deleted claim;
- **unclaimed in-taxonomy rows**: send back to the track that should have claimed them;
- **orphans** (placed, discussed nowhere): the placing track must discuss or re-place.

Then `survey ledger emit --check -v`. Hand the refusal list to **one** `survey-agent:survey-ref-curator`
(serial, never two): renames, CORR rows, unjoined sources, curated entries for inbox works, DOI
checks via `survey doi resolve`. Re-run until `survey ledger emit` writes `refs.bib`.

## 3. Crosscut — strictly after every cell

One `survey-agent:survey-synthesist` on the crosscut track; it reads the cell syntheses only. If its
argument for the poles is circular (verdicts built from rows it then reads back), it must say so and
supply a non-circular argument or downgrade the claim.

## 4. Synthesis cold read

One `survey-agent:survey-cold-reader` in `synthesis` mode on all syntheses **together** against the
current `CONTRACTS.md` governing argument → `<positioning_dir>/SYNTHESIS_COLD_READ.md`. It checks
every track pair for contradictions nobody read against each other.

## 5. Re-derive the contract

Rewrite `CONTRACTS.md`'s governing argument and claims-at-strength table **from the syntheses and the
cold read**, not from the plan. Resolve each kill criterion (fires / weakens / retires) in
`kill_criteria.md`; a fired criterion turns its claim into a proposal. Set per-section contracts
(word band from the syntheses' actual size — never cut evidence to fit, method IV-7).

## GATE 4

`survey verify --only 2 3 4 5 5a 6` passes. Show the owner: the three results that changed the paper,
the contract diff, any fired kill criterion. `survey log "syntheses + contract vN"`.
