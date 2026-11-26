---
name: survey-method
description: The method and the hard-won rules of the survey-agent pipeline — evidence integrity, stage ordering, agent orchestration, writing discipline and the human's role — each with the incident that produced it. Load before running any survey-* stage skill, before dispatching any survey-* agent, and whenever a judgement call in a survey workspace is not covered by a stage skill.
---

# The survey method

A literature survey built by agents fails in specific, repeatable ways. Each rule below exists
because the first run of this pipeline (a long-form journal survey over a corpus of a few hundred works) hit that
failure. The tools in `surveykit` enforce what can be enforced mechanically; this file is for the
rest. Rules are numbered so agents and logs can cite them (`method I-3`).

## How to call the tools

Every tool is `survey <command> --ws <workspace>` (or set `SURVEY_WS`). The launcher is
`${CLAUDE_PLUGIN_ROOT}/bin/survey`; if `survey` is not on PATH, call it by that path. It needs only
`python3 ≥ 3.11`. `survey status` tells you the stage; `survey verify` tells you what is broken;
`survey log "<title>" --body "<what happened>"` records the session in MEMORY.md. **Never** do by
hand, or by agent, what a tool does: a merge done by an agent is a merge with a race in it.

## I — Evidence integrity

1. **Quote or drop.** Every number and every load-bearing claim carries a citekey *and* the quoted
   passage with section/page. No quote, no claim.
2. **Quote from the PDF, never from a summary.** A summary that put quotation marks around its own
   paraphrase produced a "quotation" that appears in no paper; it travelled through six documents,
   including a produced thesis. The citekey resolved, the DOI resolved, the paper existed, the claim
   was true, and the sentence was fiction. Only opening the PDF caught it. Transcriptions are
   quotable only when `survey transcriptions` measures them VERBATIM.
3. **A scout's report is a pointer, not a source.** A claim repeated from a 250-word scout summary
   ("two drives amplify differently") was false — the paper tested one drive. Re-verify every
   agent-reported claim against the artifact before it enters a contract or a synthesis.
4. **Check files, not names.** A 324-byte HTML 404 saved with a `.pdf` extension convinced a
   whole workspace it held the paper. `survey verify` §11 now checks the magic bytes.
5. **Never derive a DOI from a filename.** Publisher PDF names (`1013208.1013209.pdf`) look like
   DOIs. Resolve with `survey doi resolve`: exact title+year matches only; mismatches go to the curator.
6. **The row year follows the version read.** A v3 preprint from 2025 is 2025; an eval-copy
   watermark year is not a document date; the key may lag and is left alone to avoid churn.
7. **One work, one key.** Extended versions and reprints double-count a cell silently (an extended
   version indexed beside its conference paper). Second DOIs are recorded as `ALT-DOI:`.
8. **Class discipline** (`CITATION_CLASSES.md`): class T never supports a performance claim (a vendor
   deck is not a measurement); class A is attributed in the sentence and never sole support against P;
   class M supports no technical claim and lives only where `survey.toml` allows.
9. **Corpus gap ≠ literature gap.** Assert a literature gap only after naming the search that failed;
   `inconclusive` is acceptable, `confirmed` on a thin search is not. Do not close a gap that has no
   paper with a blog post — say the mechanism exists, not what it achieves.
10. **An inference is yours.** Never attach a citekey to a conclusion the paper did not draw. Two
    readers of one paragraph corroborate the reading, not the measurement.
11. **Verify reviewer-suggested sources and your own fixes** exactly like any candidate. A reviewer's
    "2024" paper was a 2020 paper's reprint; a confident edit of our own was wrong against
    the PDF and caught only because it was checked.
12. **Never cite what was not read.** Disclosing "not read" in prose while citing the key still puts
    the work in the reference list; the mechanical `emit` exposes it. Mention without a citekey, or fetch and read.

## II — Ordering

1. **The bibliography is an output of the synthesis, not an input.** `emit` refuses rows still at
   `locus = ?`, and only a reader who claimed the row can set it. The original plan put emit before
   synthesis; that plan was impossible, not the tool.
2. **Gate the taxonomy before finding gaps**, and **before any web search or prose**. Gaps found
   against a taxonomy that does not partition are artefacts of the cells. Twenty minutes against fifty
   thousand words.
3. **Re-run GATE 1 after every fetch wave** (same deterministic sample design) and after adding any
   boundary rule. A gate that passes on the inherited corpus and fails on the fetched one is telling
   you the fetch changed the subject.
4. **Test the cheapest decisive kill criterion first, out of order if it has no dependency** — prior
   surveys (K-0) before indexing finishes. It narrowed the original contribution to "the crossing and
   the span" because one axis had been published in 2020.
5. **Dedupe before every fetch wave**: inbox, ledger, corpus DOI, ALT-DOI, prior waves. The owner's
   fetching is the only manual step; never spend it twice.
6. **Crosscut after every cell. Body before introduction. Introduction LAST.** Writing §1 first is the
   most common way a survey argues something its body does not support.
7. **Re-derive the governing argument after the synthesis cold read**, before drafting. The
   pre-synthesis argument was wrong in five places and four chapters would have inherited them.
8. **Cold read only the assembled artifact**, never per section.
9. **In revision: production defects first, citation rendering last.** Every judgement about whether
   a comment is substantive depends on knowing what the reviewer actually saw.

## III — Orchestration

1. **One writer per file; every merge is a tool.** Parallel agents each write one batch file or one
   track directory; `survey index build`, `ledger merge-claims`, `candidates merge`, `review merge`
   combine them.
2. **Checkpoint first.** Synthesists write `claims.tsv` before reading deeply and syntheses
   headings-first. A usage limit killed all five synthesists once; the claims survived and became
   the strongest partition test of the run.
3. **On a usage limit, re-run only what did not finish.** Batches are idempotent; `survey status`
   names what is missing. Size fan-out so a killed batch costs little.
4. **Workers get a preamble of settled items** (`known_resolutions.md`, the gap report's struck gaps)
   so they do not re-litigate them and can recognise known defect classes.
5. **Fixed vocabularies** for every field agents fill in parallel. Six triage agents without one
   produced ~40 category spellings; `survey review merge` now normalises and reports drift.
6. **Agreement ≠ correctness.** Five agents applying the same frozen definitions agree whether or not
   the definitions are right. A clean partition result is necessary, not sufficient.
7. **Lead-written briefs carry the lead's errors.** Tell every worker to verify claims in its own
   brief; one synthesist's most valuable act was refusing a fabricated quote its question handed it.
8. **Scouts over-select toward the cell their accept bar was written to fill** — eight of eight
   placement mismatches in one wave came from the thin cell's gap folders. The indexer that reads the
   paper places it; the paper wins.
9. **Tool grants are structural.** Scouts have no Bash (they cannot download), writers no Bash,
   synthesists no web, the cold reader no working notes. Never dispatch `general-purpose` "pretending"
   to be one: it carries every tool, and a scout dispatched that way used Bash.
10. **An instruction the agent follows correctly can still be the defect** (a "≥3 splits = failure"
    rule with no denominator produced a false taxonomy failure). When a verdict surprises, read the
    rule before the work.

## IV — Writing

1. **Claims at strength.** Every governing claim is an *observation*, *argued*, or a *proposal*; a
   fired kill criterion turns an observation into a proposal. Writers may not blur them.
2. **Raise the strongest objection yourself** and label the defence a hypothesis when it is one.
3. **Concede staleness as well as singularity** of a key measurement, everywhere the number repeats.
4. **Headline counts come from one computation**: `{{n:key}}` macros from `survey stats`. The
   original had four denominators for one corpus in a paper whose pitch was bookkeeping.
5. **No universal quantifiers without universal evidence**; membership is not migration.
6. **Typed placeholders** (`[[ASK|DECIDE|DRAFT|FETCH|MEASURE:id]]`) for every hole — a hole marked is
   found, a hole smoothed over is a defect — and all become prose before submission. No internal file
   names in prose.
7. **Never delete evidence to hit a word budget.** Over-specific budgets set before reading cost a day
   (10/10 agents overran; five were killed mid-trim). Precision and length are independent.
8. **Credit what holds.** An adversarial read that only lists defects is half a read.

## V — The human

1. **Agents never download.** Scouts list; the owner fetches into `<inbox>/wave<N>/<citekey>.pdf`.
2. **Gates and taste calls belong to the owner**, presented as 2–4 options with a recommendation and
   its cost. Log the decision and the reason, especially when it overrides the recommendation.
3. **Defects in another workspace are reported to its owner, not fixed** (the fabricated quotation
   in the owner's thesis; the fake PDF in a sibling workspace).
4. **Frozen means frozen.** Brief, taxonomy and contracts change only by dated ⚠️ amendment.
