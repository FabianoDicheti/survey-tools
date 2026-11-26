---
name: survey-translate
description: Translate the finished survey (e.g. to pt-BR) without destroying its evidence — chunk the chapters, one survey-translator per chunk with the style guide and glossary, mechanical checks that quotations, citekeys and structure survived, then reassemble and build. Use when a translated version is requested, after content is frozen.
argument-hint: "[--max-words N]"
---

# survey-translate

Load `survey-method`. Precondition: content frozen (`survey verify` passes). Translating a moving
target doubles every later fix.

## Steps

1. **Style guide and glossary.** `survey.toml` `[translate]` names the target, a glossary file (a
   markdown table `| EN | TARGET |`) and the rules (`decimal_comma`, `forbid_em_dash`). The glossary
   fixes the taxonomy's vocabulary — one rendering per term across every chapter. Rules that held in
   the first run: third person; no rhetorical flourishes; never call the survey a thesis; first
   occurrence of a technical term per chapter gives the original in italics.
2. `survey --ws <ws> translate chunk --max-words 2500`.
3. Dispatch one `survey-agent:survey-translator` per chunk, in one message (batches of ≤ 8 if many).
4. `survey --ws <ws> translate check`. FAIL = a quotation, citekey, code span, placeholder, heading or
   table row changed. Send the chunk back to a translator with the check output. A glossary that
   conflicts with the code-span rule (translating a backticked verdict value) is fixed in the
   glossary, not by breaking the rule.
5. `survey translate assemble` → `<paper_dir>/<lang>/`; then `survey-produce` with `--lang`.

**Never translate**: direct quotations (evidence — translating destroys verifiability against the
PDF), citekeys and backtick spans, APA in-text citations, titles and authors in the reference list,
system and project names, placeholders. `survey log "translation <lang>"`.
