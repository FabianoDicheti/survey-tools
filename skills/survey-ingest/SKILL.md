---
name: survey-ingest
description: Bring a landed fetch wave into the corpus — check every dropped file is a real PDF named for a fetch-list citekey, measure transcription fidelity, index the new works, dedupe, and re-run GATE 1. Use when the owner says PDFs have been dropped in the inbox, or status reports inbox PDFs not in the corpus.
argument-hint: "[--wave N]"
---

# survey-ingest — Stage 4b

Load `survey-method`.

## Steps

1. **File sanity.** `survey --ws <ws> verify --only 11 12`. Fix before anything else:
   - a "PDF" that is HTML (a saved 404) → tell the owner which, with its size; do not index it;
   - a PDF whose name matches no fetch-list citekey → ask the owner whether it is misnamed or
     `_unlisted`; never guess the key from the filename.
2. **Transcriptions.** If `.md` transcriptions sit beside the PDFs: `survey --ws <ws> transcriptions`.
   PARAPHRASED/PARTIAL files go into `DO_NOT_CITE.md`'s transcription table; synthesists quote only
   from the PDF for those.
3. **Index.** Load `survey-index` and dispatch one indexer per wave batch (`inbox_waveN`), telling it:
   the paper wins over the gap folder's expected cell (scouts over-claim toward thin cells); one row
   per work even when two PDFs are versions of one work (method I-7); the row year is the version read.
4. `survey index build` → `survey ledger sync-corpus` (adds new rows to the ledger, copies OUT verdicts).
5. **Re-check scout claims.** For each new work, compare the fetch list's *why* with the indexer's
   `one_line`. A mismatch is logged in `<corpus_dir>/CORRECTIONS.md`; any contract or brief that
   repeated the scout's claim is corrected now (the "two drives" incident).
6. **GATE 1 re-run** — load `survey-gate`.
7. **Gaps re-audit** if any cell was thin — load `survey-gaps` for the next wave.

`survey log "ingest wave N"`: works added, defects found, gate delta.
