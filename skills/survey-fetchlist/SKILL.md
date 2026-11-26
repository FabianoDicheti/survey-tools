---
name: survey-fetchlist
description: Turn open gap briefs into the ranked, DOI-verified fetch list the owner downloads from — one survey-scout per gap in parallel, then `survey candidates merge`. Search and list only; nothing is downloaded. Use after the gap audit (GATE 2/3).
argument-hint: "[G-nn ...] [--wave N]"
---

# survey-fetchlist — Stage 4, GATE 3

Load `survey-method`. Preconditions: gap briefs with accept bars exist; struck gaps recorded.

## Steps

1. Choose the wave number N (next after the existing `<fetch_dir>/wave*/`).
2. Dispatch one `survey-agent:survey-scout` **per open gap, all in one message**. Each prompt names the
   gap brief path, the output `<fetch_dir>/candidates/G-nn.md`, the max candidates (default 8), the
   class-M cap from the brief, and for context-track gaps: "the peer-reviewed share must stay above
   the floor — search the venues, not the trade press".
3. Merge — a tool, never an agent:
   ```bash
   survey --ws <ws> candidates merge --wave N
   ```
   It dedupes against the inbox, ledger, corpus DOIs, ALT-DOIs and earlier waves; it exits non-zero
   if a scout used a section heading it cannot route (fix the candidate file, re-run).
4. Review `FETCH_LIST.md` before handing it over: ranked entries without `doi_status: stated` are
   confirmed or demoted; any entry whose *why* rests on a claim only the scout made is marked for
   checking at ingest (method I-3).
5. **GATE 3 — hand over.** Tell the owner: the list's path, the count, the drop convention
   `<inbox>/waveN/<citekey>.pdf` (exact citekey), and that anything extra goes to `waveN/_unlisted/`.
   They may strike entries or whole gaps; record that in `gap_report.md`.

Agents never download, not even "just to check". `survey log "fetch list wave N: k works"`.
