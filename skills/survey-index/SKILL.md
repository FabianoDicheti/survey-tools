---
name: survey-index
description: Build or extend the searchable corpus — dispatch one survey-indexer per batch of source documents, merge with `survey index build`, render the timeline, and scan/seed the import ledger. Use to start Stage 1, after a fetch wave is ingested, or when status reports index/ledger incomplete.
argument-hint: "[--batches name,...] [--rebuild]"
---

# survey-index — Stages 1–2

Load `survey-method`. Preconditions: `TAXONOMY.md` and `CONTEXT_CARD.md` frozen (status stage 0 ✅).

## 1. Plan batches

A batch is a set of documents one agent can read in one sitting — about 30–60 summaries or 10–15
PDFs. One batch per origin cluster or inbox wave is the natural cut. Name them (`orig_AB`, `wave2`, …).
Batches already present in `<corpus_dir>/rows/` are done: **never re-index a surviving batch** — rows
are immutable; corrections are `CORRECTION:` lines in the batch's notes file.

## 2. Fan out

Dispatch one `survey-agent:survey-indexer` per missing batch, **all in one message**. Each prompt
names: the batch id, the exact source paths, the output `rows/<batch>.jsonl` + `<batch>.notes.md`,
the origin label, and any known traps for that batch (e.g. "PDF filenames are publisher artefacts";
"these 9 works are already indexed from the BibTeX side — log CORRECTION lines, do not duplicate").
If a batch dies on a usage limit, re-dispatch only that batch.

## 3. Merge (tools, never agents)

```bash
survey --ws <ws> index build        # refuses duplicate keys/DOIs, unknown cells, stated-DOI-without-DOI
survey --ws <ws> index timeline
survey --ws <ws> ledger scan        # only if [[origins]] exist; writes no BibTeX
survey --ws <ws> ledger propose     # seeds; locus stays '?'
```

On refusal, read the defect list, fix the offending batch file's row via its indexer (or apply a
logged `CORRECTION:` yourself) and re-run. Never hand-edit `corpus.jsonl`.

## 4. Read the free signal

The histogram of `locus_proposed` is the first look at the taxonomy: a cell under the thin threshold
is a likely corpus gap (Stage 3 will confirm). Count `SPLIT:` reasons — many SPLIT reasons with zero
split placements means indexers recorded doubt in prose and forced one cell. Note every
`CORRECTION:` line and apply/log them in `<corpus_dir>/CORRECTIONS.md`.

## 5. Log

`survey log "index: N rows"` with counts per cell, citable:false, SPLIT count, defects found.
Next: `survey-gate`.
