# CITATION_CLASSES — what a source is allowed to support

**Frozen {{date}}.** Every entry in `refs.bib` carries exactly one `class = {…}`. The class is not a
quality judgement; it states what kind of claim the source can carry alone.

## P — peer-reviewed
Journal, conference, dissertation that went through review. **May support any claim, alone.**

## A — archival preprint
Stable identifier (arXiv, HAL), named authors, a fixed version.
- Supports a technical claim **only if attributed in the sentence** ("Sheng et al. report…").
- **Never** the sole support against a class-P source.
- Cite the version read (`v3` is not `v1`); the row year follows that version.

## T — primary technical artifact
A standard, a datasheet, released source at a pinned revision, a vendor deck.
- **Supports capability claims only — never performance claims.** A datasheet number is a rating;
  a vendor deck is not a measurement.
- Source code is cited at a commit hash. A tree that is not a git repository is pinned by a SHA-256
  digest over its files, sorted by path, recorded with its date — that pins *what was read*, not what
  the authors released; say so in the method section.
- Prefer moving source-tree citations to an appendix with their digests; reviewers object to them in
  the bibliography.

## M — market and industry evidence
Analyst reports, earnings calls, press releases.
- **Never supports a technical claim.**
- Primary artifact only, never trade press summarising it.
- Requires `urldate` and a committed snapshot in `classes.M.snapshot_dir` (see `survey.toml`).

## Where each class may appear

Roles come from `survey.toml` `[paper].chapters`. Class M is allowed only in the roles listed in
`[classes.M].allowed_roles`, capped in the introduction by `thresholds.market_max_in_intro`, and the
context section must keep `(P+T)/(P+T+M) ≥ thresholds.context_pt_min` — measured over the section's
citations, so a length edit can break it silently (`survey verify` §5c).

## Derived identifiers

A DOI reconstructed rather than read off the document is marked `DOI-DERIVED` in the entry's note.
A derived key may never be the sole support for a quantity (`survey verify` §10). Resolve them with
`survey doi resolve` — exact title+year matches only — rather than hiding the marker: an external
reviewer reads an unexplained marker as "never verified".

## The context section's obligations

1. an honest paragraph: the market data is not peer-reviewed; it establishes that a dated pressure
   exists, nothing more; no quantity in the body depends on it;
2. a falsifiability sentence: what the survey loses if the pressure reverses (the right answer is
   "its motivation, nothing structural").
