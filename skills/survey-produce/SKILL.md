---
name: survey-produce
description: Render the verified paper — SBC/JBCS docx (A4, Times New Roman 12pt, 3.5/2.5/3.0/3.0 cm), PDF, LaTeX for generic/IEEE/ACM venues, or an assembled markdown review copy — and inspect every docx for production defects before calling it built. Use only after survey-verify passes.
argument-hint: "[--target sbc-docx|sbc-pdf|latex-generic|latex-ieee|latex-acm|markdown]"
allowed-tools: Bash, Read, Glob
---

# survey-produce — Stage 9

Precondition: `survey verify` passes (or its failures are owner-accepted and logged).

```bash
survey --ws <ws> verify --build          # adds §17: assets, docx grid/merged-paragraph checks
survey --ws <ws> build --target sbc-docx # or the venue's target
```

- The source of truth stays markdown with backtick citekeys; builds write only `<paper_dir>/build/`.
- `sbc-docx` uses APA in-text citations rendered mechanically from `refs.bib`, `{{n:…}}` macros from
  `survey stats`, and an SBC reference document generated from `[build]`. It then inspects the docx:
  table grids vs table width, merged Word citation fields, sentence joins. **A docx with defects is
  not a deliverable** — the original review's 417 comments were inflated by exactly these.
- `latex-*` writes `.tex` with biblatex/natbib citations and compiles if a LaTeX engine exists; say
  plainly when it does not.
- Convert to the venue format **last**; never edit the docx by hand and re-import.

Report: target, output path, page/word count if available, reference count, defects found.
For a translation build, run `survey-translate` first, then `build --lang <code>`.
