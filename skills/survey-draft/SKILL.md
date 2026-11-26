---
name: survey-draft
description: Write the paper from the syntheses — one survey-writer per section against its contract in CONTRACTS.md, in the fixed order body → crosscut → gap → introduction/context/method → conclusion/front. Also handles a single-section rewrite after review. Use after GATE 4.
argument-hint: "[--all | <chapter stem> ...]"
---

# survey-draft — Stage 7

Load `survey-method`. Preconditions: GATE 4 passed; `refs.bib` emitted; `CONTRACTS.md` re-derived
after the synthesis cold read (not the planning draft).

## Order — not a preference

1. **body** chapters (one writer each, in parallel, one message);
2. **crosscut** — after every body chapter exists; introduces no evidence;
3. **gap**;
4. **intro / context / method — LAST** among the argument (they promise what the body delivers);
5. **conclusion**, then **front** (abstract, contributions, notation table).

Roles come from `survey.toml` `[paper].chapters`. A request to write the introduction first is
answered with method II-6 and a question.

## Each writer's prompt

Names: the chapter stem and output path, its contract heading in `CONTRACTS.md`, the synthesis it
draws on, the neighbouring sections it must not re-argue, and the governing argument's version.

## After each wave of writers

```bash
survey --ws <ws> stats              # headline numbers for {{n:…}} macros
survey --ws <ws> cite references    # regenerated reference list, cited works only
survey --ws <ws> placeholders
survey --ws <ws> verify --only 7 7b 8 9 10 13 14 18 19
```

Fix failures by sending the failing section back to **its** writer with the verifier output. Never
patch a section yourself in a way its contract would not allow.

## Single-section rewrite (after review)

One writer, that section only, with the reviewer comments or cold-read findings that apply to it
quoted in the prompt; then the same verify set. If the fix changes a headline claim, propagate it to
the abstract/contributions (the original's front matter lagged its body fixes).

`survey log "draft: <sections>"`.
