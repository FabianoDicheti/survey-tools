# SYNTHESIS_SPEC — the output contract

**Frozen {{date}}.** `survey verify` §2–§4 read the front-matter block mechanically. It is the interface.

## 1. What you write

Exactly one directory: `{{dir_tracks_dir}}/<your track>/` → `claims.tsv`, `notes.md`, `synthesis.md`
(and optionally `README.md`). **Write nothing else.** One writer per file is why parallel synthesis
produces one document.

## 2. Order of work — checkpoint first

1. **`claims.tsv` first**, before reading deeply. A usage limit killed every synthesist of the
   original run mid-synthesis; the claims files survived because they were written first, and became
   the full-corpus partition test.
2. `notes.md`, one block per document, as you read.
3. `synthesis.md`, **headings first**, then fill — so a killed run leaves a usable skeleton.

## 3. `claims.tsv`

Tab-separated, with this header:

```
survey_key	locus	locus_secondary	split	reason
```

- one row per corpus row you claim: your proposed rows plus the whole `split()` seed pool named for you;
- `locus` is the cell the work's decision belongs to — possibly not yours; a track may claim a work
  and place it elsewhere (it must still discuss it if it placed it);
- `split` is empty, or the cells that fit **equally** (`C2|C3`) — record doubt, never force it;
- `{{out}}` with a reason for works outside the taxonomy.
`survey ledger merge-claims` folds these in: agreement is a cross-reference, disagreement is a dispute.

## 4. Front matter

Cell tracks (9 keys, all present, `[]`/`{}` written out):

```yaml
---
track: <dir>
locus: <cell id>
papers_read: n/n
findings: [F1, F2, …]
axis_verdicts: {F1: <value>, …}      # the crosscut's only input; values defined per survey
taxonomy_stress: [citekey, …]
most_dangerous: citekey
citekeys_used: [citekey, …]
unresolved: ["…"]
---
```

Crosscut (7): `track syntheses_read findings axis_table_rows contradictions most_dangerous unresolved`.
Context (8): `track sources_read class_counts findings strongest_non_market_support staleness_date most_dangerous unresolved`.

## 5. Section order — mandatory

```
## (i)   What this cell decides, and how you know a work belongs here
## (ii)  Findings                    ← 5–9
## (iii) Taxonomy stress
## (iv)  Citekeys used
## (v)   Read, not load-bearing      ← every assigned document not in a finding, with why
## (vi)  Unresolved
```

## 6. A finding

- **The heading is the claim**, not the paper.
- **Quote or drop**: citekey + quoted passage + section/page, from the PDF.
- Attribute every number: whose measurement, what hardware, what year.
- An inference you make is marked as yours and never carries a citekey (a ratio computed by the reader was once
  attributed to a paper that measured only one side of it).
- Two readers of one paragraph corroborate the reading, not the measurement.
- Universal quantifiers ("never", "every", "provably") need universal evidence. Membership is not migration.
- Contradictions between works are the valuable output: name both, say which you believe and why.
- End with `**Use:**` (which section consumes it) and `**Axis:**` (verdict + one clause).
- Mark threats to the framing with ⚠️.

## 7. Length

The binding budget is the **chapter's**, set in `CONTRACTS.md` — not this file's. Never delete
evidence to hit a number; precision and length are independent (the original's worst document was
2,000 words long and wrong in 15 of 29 claims). Output that is structurally complete when stopped
mid-trim is accepted.

## 8. Report back

≤ 400 words: papers read, findings count, verdict distribution, taxonomy-stress count,
`most_dangerous` + why, every `TODO(<track>):` left, every claim in your brief you could not verify.
