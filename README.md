# survey-tools — the survey-agent plugin

A Claude Code plugin for writing literature surveys with agents: **tools** that do every merge and
check mechanically, **skills** that encode the method and the lessons of a first full run, and
**agents** — ten single-purpose workers and one lead — that do the reading and writing.

It generalises a pipeline that took one long-form journal survey from a request to a reviewed
manuscript (a corpus of a few hundred works, external review and translation included) to any topic
and corpus. `examples/energy-scheduling/survey.toml` is a complete worked configuration.

## Install

```bash
# try it for one session
claude --plugin-dir /path/to/survey-agent

# or install from GitHub (the repo is its own marketplace)
claude plugin marketplace add FabianoDicheti/survey-tools
claude plugin install survey-agent@survey-agent-local
```

Requirements: `python3 ≥ 3.11` (the tools are stdlib-only), `pandoc` for builds, `pdftotext`
(poppler) for transcription checks, a LaTeX engine only if you want PDFs from the LaTeX targets.
While the plugin is enabled, `survey` is on the Bash PATH; otherwise call `bin/survey`.

## Use

```bash
claude --agent survey-agent:survey-lead      # the lead as the main thread
```
or in any session: `/survey-agent:survey <workspace>`. The lead reads `survey status`, loads the
stage skill, fans out workers, runs the tools, and **stops at every gate** for you.

## The pipeline

```
0  survey-init        brief frozen verbatim · taxonomy as axes in survey.toml · kill criteria · prior-survey test (early)
1  survey-index       survey-indexer ×batches → survey index build/timeline → ledger scan/propose
2b survey-gate        GATE 1: survey gate1 sample → survey-blind-placer → score (three verdicts)
3  survey-gaps        survey-gap-auditor → coverage matrix, gap briefs, GATE 2
4  survey-fetchlist   survey-scout ×gaps → survey candidates merge → you fetch PDFs (GATE 3)
4b survey-ingest      file sanity · transcriptions · index · GATE 1 re-run
5  survey-synthesize  survey-synthesist ×cells (claims first) → merge-claims → ref-curator → emit refs.bib
6                     crosscut synthesis → synthesis cold read → CONTRACTS re-derived (GATE 4)
7  survey-draft       survey-writer ×chapters: body → crosscut → gap → intro LAST
8  survey-verify      survey verify → survey-cold-reader (GATE 5, your review)
9  survey-produce     survey build: sbc-docx | sbc-pdf | latex-generic | latex-ieee | latex-acm
10 survey-revise      review extract → production defects first → survey-comment-triager ×batches → merge
   survey-translate   translate chunk → survey-translator ×chunks → translate check → assemble
```

`skills/survey-method/SKILL.md` holds the rules every stage follows, each with the incident that
produced it.

## Tools (`survey <command> --ws <workspace>`)

| command | does |
|---|---|
| `init` | scaffold a workspace; render the frozen contract docs from `survey.toml` |
| `index build` / `timeline` | merge indexer batches into `corpus.jsonl` (refuses dup keys/DOIs) · timeline |
| `ledger scan/propose/merge-claims/sync-corpus/emit/adopt-bib` | the import ledger; `emit` writes `refs.bib` only after claims are merged |
| `gate1 sample/score` | GATE 1 blind shuffle; JSON verdict + history |
| `candidates merge --wave N` | scout files → fetch list, deduped against inbox, ledger, DOIs, ALT-DOIs, prior waves |
| `verify [--build] [--only …]` | 26 config-driven checks (`--list`) |
| `stats` | every headline count once; prose uses `{{n:key}}` |
| `placeholders` | regenerate PLACEHOLDERS.md |
| `transcriptions` | VERBATIM / PARTIAL / PARAPHRASED per inbox transcription |
| `renames [--apply]` | citekey renames in citekey positions only |
| `doi resolve [--apply]` | Crossref/DataCite/arXiv check of derived DOIs with recorded evidence |
| `cite references` / `intext` | APA 7 list (cited only, 2025a/b) · APA in-text build copy |
| `build --target …` | SBC docx (self-generated reference.docx) / LaTeX; inspects docx for production defects |
| `review extract/batch/merge/fix-docx` | external-review triage with anchors and a fixed vocabulary |
| `translate chunk/assemble/check` | translation that keeps quotations and citekeys byte-identical |
| `status` / `log` | stage inference from artifacts · dated MEMORY.md entries |

## Configuration

One `survey.toml` per workspace holds names, cells, thresholds, paths, chapters, guards and build
settings; nothing else restates a threshold. Start from `templates/workspace/survey.toml` (written
by `survey init`) or the worked example.

## Tests

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest -q
```

The suite runs the whole tool chain on a toy 12-document workspace, with one regression test per
defect class the first run hit (lost provenance markers, agreement counted as dispute, inbox/DOI
dedup misses, fake PDFs, split rates without a denominator, translated quotations, broken docx
table grids). A replay against a real survey can be kept in a git-ignored `local/` folder.
