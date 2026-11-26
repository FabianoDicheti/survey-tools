# SEED_MAP — the seed heuristic

**Frozen {{date}}.** The seed exists only to make GATE 1 measurable: a cheap placement to compare a
blind reader against. It is **never** a placement, never writes `locus`, never writes `{{out}}`, and is
never cited as a reason. The seed table itself lives in `survey.toml` `[[origins]].seed`.

| origin | cluster | seed | expected accuracy |
|---|---|---|---|
{{seed_rows}}

## Known failure cases

Numbered cases where the seed is *expected* to be wrong, so a GATE 1 disagreement there reads as the
design working rather than the taxonomy failing.

1.
