# CONTEXT_CARD — the shared spine

**Frozen: not yet** (write `**Frozen YYYY-MM-DD.**` when §1–§3 are settled). One source of truth for
every agent. Numbers live in `survey.toml` and `survey stats`, never here.

If you are a `survey-synthesist`: **this file, your section of `QUESTIONS.md`, `SYNTHESIS_SPEC.md`,
`DO_NOT_CITE.md`, `CITATION_CLASSES.md`, `TAXONOMY.md`, your rows in `corpus.jsonl`, and the
documents those rows point at** are everything you may read. Do not open a sibling track, the paper,
another agent's output, or the web. **Never block on the lead** — write `TODO(<track>):` at the point
of use and continue.

---

## 1. What this survey is

{{topic}} Venue {{venue}}, language {{language}}. The taxonomy in `TAXONOMY.md` is the contribution.

The paper's spine (from `survey.toml`):

{{spine}}

## 2. The corpus

(Where the references come from, and the facts about that inheritance an agent will hit: the only
citekey→document join, how many are unjoined, reconstructed DOIs, malformed keys, version mismatches.
Counts are cited as `survey stats` keys, not typed.)

## 3. Standing constraints

1. **No citation from memory.** If you did not open it this session, or it is not in the corpus, it
   is not a citation.
2. **Quote or drop.** Every number and every load-bearing claim carries a citekey *and* the quoted
   passage with a section or page. If you cannot quote it, you do not have it.
3. **Quote from the PDF.** A summary `.md` locates a claim; it is never the source of a quotation.
   A transcription is quotable only if `survey transcriptions` measured it VERBATIM. (The worst defect
   the original pipeline found was a summary that put quotation marks around its own paraphrase; the
   "quote" travelled into six documents. The citekey resolved, the DOI resolved, the paper existed,
   the claim was true — and the sentence was fiction.)
4. **Every number is somebody else's measurement**, on somebody else's hardware, in a stated year.
   This survey measures nothing.
5. **A brief can be wrong.** If a question in `QUESTIONS.md` hands you a quotation or a fact, verify it
   against the document like any other claim. Lead-written briefs carry the lead's errors.
6. (Topic-specific framing prohibitions, mirrored in `survey.toml` `guards.forbidden_phrases`.)

## 4. Citekey convention

`author-year_topic`, lowercase, underscore-separated. The year is mandatory and comes right after the
surname — a misplaced year (`smith_jones1990`) is worse than none, because a grep extracts `jones1990`.
The **row year follows the version you read** (a v3 preprint from 2025 is 2025 even if the key says
2024); do not "correct" a row back to its key. An eval-copy watermark year is not a document date.

## 5. Typed placeholders

`[[ASK:A-nn]]` a question for {{owner}} · `[[DECIDE:D-nn]]` an open decision ·
`[[DRAFT:T-nn]]` a drafting obligation · `[[FETCH:G-nn]]` a hole a fetch would close ·
`[[MEASURE:M-nn]]` a number nobody has measured. Use an existing ID where one fits; one ID, one item.
Every placeholder becomes prose before submission. `survey placeholders` regenerates the index.

## 6. Notation

| symbol | meaning |
|---|---|
{{cells_table}}
| `{{out}}` | read, in the corpus, outside the taxonomy |
| `locus_secondary` | cited in another cell, analysed in the primary |
| split | two cells fit equally — recorded, never forced |
| class P / A / T / M | citation classes (`CITATION_CLASSES.md`) |
| G-nn / K-nn | gap id / kill criterion |

## 7. Division of labour

**Claude** — indexing, gap audit, search and DOI verification, syntheses, drafting, the verifier, the build.
**{{owner}}** — fetching every PDF (scouts list, they never download), the taste decisions at each
gate, any taxonomy repair, and the review.
