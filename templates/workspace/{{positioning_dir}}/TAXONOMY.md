# TAXONOMY — the organising cut

**Frozen: not yet** (write `**Frozen YYYY-MM-DD.**` when §2–§3 are settled; later changes are dated
⚠️ amendments, never rewrites). This file is the survey's contribution. Every later stage is checked
against it. Track directory names must match `survey.toml` exactly (`survey verify` §1).

---

## 1. The question the taxonomy answers

(The one question every work in scope answers, stated so a reader can apply it. Then: how the
literature is conventionally organised, and which closely related works that cut scatters apart.)

## 2. The axes

State the cut as **independent axes with two poles each**, not as a list of labels. A taxonomy that
cannot be stated as axes cannot be tested, and a work that cannot be placed on every axis is not a
work this taxonomy covers. **Where §3's prose and §2's axes disagree, the axes win** — all three
boundary rules the original GATE 1 produced were cases of prose naming an *implementer* while the
axes named a *property*.

{{grid}}

## 3. The cells

{{cells_table}}

For each cell: definition, canonical examples, and a one-line **membership test** that can be
answered from the work itself. If a cell is deliberately narrower than its axes, say so here and in
the method section, with a table separating what is in from what looks in but is not — a reader who
reconstructs the grid and finds a fourth thing in a cell will otherwise conclude the taxonomy leaks.

The crosscut track (`{{crosscut}}`) is **not a cell**: it reads the cell syntheses and introduces no
evidence. Its primary evidence is the *seams* — works whose decision genuinely splits across two cells.
The context track (`{{context}}`) is **not a cell**: it carries the "why now" and is governed by
`CITATION_CLASSES.md`.

## 4. What the axes answer

(What the taxonomy says about the motivating question, with every claim at a stated strength —
**observation**, **argued**, or **proposal** — and its kill criterion. A claim whose kill criterion
fired becomes a proposal and is written as one.)

## 4b. Boundary rules

Added after GATE 1 from the blind reader's feedback; each must be **re-scored** by re-running GATE 1.
None may widen a cell.

## 5. Health thresholds

Generated from `survey.toml` — the single source; no other file may restate these numbers.

{{thresholds_table}}

## 6. Placement rules

1. Classify **the decision**, not the system. One system may make decisions in two cells; place the
   work by the decision it is *about*.
2. A work that fits two cells equally is a **split**: record it in `claims.tsv`'s `split` column
   (e.g. `C2|C3`) with a reason. Splits are the crosscut's evidence; a split rate above the ceiling
   means the axis is not a partition.
3. `{{out}}` = read, in the corpus, outside the taxonomy — always with a recorded reason.
4. `locus_secondary` = cited in another cell, analysed in the primary. Agreement between tracks is a
   cross-reference, not a dispute.
5. The track that places a work analyses it.
6. The seed in `SEED_MAP.md` is never a placement and never a reason.
