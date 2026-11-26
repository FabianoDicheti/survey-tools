# MEMORY — {{title}}

**This file is the entry point.** Any session — human or model — starts here, runs `survey status`,
and needs nothing outside this folder except the origin workspaces declared in `survey.toml`.
End every working session with `survey log "<what happened>"`; `survey verify` §20 warns when this
log falls behind the artifacts (the original pipeline's log stopped three sessions early).

## What this survey is

{{topic}}

Venue {{venue}}, language {{language}}. Owner: {{owner}}. Started {{date}}.

## Files, in reading order

| file | what | frozen? |
|---|---|---|
| `survey.toml` | names, cells, thresholds, paths — the single source of truth | edit deliberately |
| `00_brief.md` | the owner's request, verbatim, plus intake decisions | **yes — never edit** |
| `{{dir_positioning_dir}}/TAXONOMY.md` | **the contribution**: axes, cells, boundary rules | **yes** (dated amendments only) |
| `{{dir_bib_dir}}/CONTEXT_CARD.md` | the shared spine every agent reads | **yes** |
| `{{dir_bib_dir}}/CITATION_CLASSES.md` | P / A / T / M and what each may support | **yes** |
| `{{dir_bib_dir}}/DO_NOT_CITE.md` | in-tree sources that are not evidence | **yes** |
| `{{dir_bib_dir}}/SEED_MAP.md` | the seed heuristic and its known failure cases | **yes** |
| `{{dir_bib_dir}}/QUESTIONS.md` | per-track question sets | **yes** |
| `{{dir_bib_dir}}/SYNTHESIS_SPEC.md` | the synthesis output contract | **yes** |
| `01_plan.md` | stages, gates, orderings, open decisions | living |
| `{{dir_corpus_dir}}/corpus.jsonl` | the searchable corpus | regenerated |
| `{{dir_bib_dir}}/IMPORT_LEDGER.tsv` | one row per reference; where it landed, who decided | living |
| `{{dir_tracks_dir}}/*/synthesis.md` | the evidence, one per track | living |
| `{{dir_paper_dir}}/CONTRACTS.md` | per-section contracts + the governing argument | re-derived after synthesis |
| `PLACEHOLDERS.md` | every open hole | regenerated (`survey placeholders`) |

## Standing constraints

- **No citation from memory.** Fetched, opened and DOI-verified only.
- **Quote or drop.** Every number and load-bearing claim carries a citekey and the quoted passage.
- **This survey measures nothing.** Every number is somebody else's, on their hardware, in a stated year.
- **A summary is never quotable.** Quote from the PDF or a measured-VERBATIM transcription.
- **One writer per file; every merge is a tool.**

## Division of labour

- **Claude:** indexing, gap audit, search and DOI verification, syntheses, drafting, the verifier, the build.
- **{{owner}}:** fetching every PDF (agents never download), the taste decisions at every gate,
  any taxonomy repair, and the review.

## State

### {{date}} (a) — workspace scaffolded

`survey init` from the survey-agent templates. Next: freeze the brief, draft the taxonomy, run
`survey status`.
