---
name: survey
description: Entry point for running a literature survey with the survey-agent pipeline — start a new survey workspace, resume one after a break or a usage limit, or ask "where are we and what's next". Use when the user asks to build, continue, check or revise a survey paper / literature review in a workspace with a survey.toml (or to create one).
argument-hint: "[workspace dir] [stage or request]"
---

# /survey — run or resume the pipeline

You are the lead. Follow `survey-method` (load it now if it is not loaded) and drive the pipeline
stage by stage. The same loop is what the `survey-agent:survey-lead` main-thread agent runs.

## 1. Locate the workspace

The workspace is the directory holding `survey.toml` — the argument, `$SURVEY_WS`, or the current
directory. None exists and the user wants a new survey → skill `survey-init`.

## 2. Read the state from artifacts, not memory

```bash
survey --ws <ws> status
```

Read `MEMORY.md`'s newest State entry as well. If they disagree, the artifacts win.

## 3. Run the next stage

| status says next | load skill |
|---|---|
| 0 brief + taxonomy | `survey-init` |
| 1 index · 2 ledger | `survey-index` |
| 2b GATE 1 | `survey-gate` |
| 3 gap audit | `survey-gaps` |
| 4 fetch list | `survey-fetchlist` |
| 4 waiting on PDFs | stop: tell the owner exactly which `<citekey>.pdf` files to drop where |
| 4b ingest | `survey-ingest` |
| 5 / 5b / 6 / 6b | `survey-synthesize` |
| 7:* | `survey-draft` |
| 8 | `survey-verify` |
| 9 | `survey-produce` |
| 10 review | `survey-revise` |
| translation requested | `survey-translate` |

A user request for a specific stage overrides the table, **except** where it breaks a `survey-method`
§II ordering. Then say which ordering it breaks and what it would cost, and ask.

## 4. At every gate, stop

Present the verdict, the evidence and 2–4 options with your recommendation (AskUserQuestion). Never
decide a gate, a scope strike or a taxonomy repair for the owner.

## 5. Close the session

```bash
survey --ws <ws> verify --json      # cheap; shows what this session broke
survey --ws <ws> log "<stage: what happened>" --body "<counts, decisions, defects found, next>"
```

Every session ends with a log entry: results, corrections found (and in which artifact), decisions
taken with their reason, and the next action.
