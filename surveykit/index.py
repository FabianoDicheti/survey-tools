"""`survey index build` and `survey index timeline`.

build:    merge the per-batch indexer files rows/*.jsonl into corpus.jsonl and
          render INDEX.md. Indexer agents each write one batch file and never a
          shared one; the merge is a tool because a merge done by an agent is a
          merge with a race in it.
timeline: a projection of corpus.jsonl's year column. A hand-maintained
          timeline drifts the moment a fetch wave lands.
"""
import sys
from collections import Counter, defaultdict

from .schema import CORPUS_KEYS, DOI_CLASSES, CITATION_CLASSES, read_jsonl, write_jsonl, norm_doi
from .util import banner


def load_batches(cfg):
    rows_dir = cfg.path("corpus_dir", "rows")
    files = sorted(rows_dir.glob("*.jsonl"))
    rows, seen, dois, bad = [], {}, {}, []
    for f in files:
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            import json
            try:
                r = json.loads(line)
            except json.JSONDecodeError as e:
                bad.append(f"{f.name}:{n} not JSON — {e}")
                continue
            missing = [k for k in CORPUS_KEYS if k not in r]
            if missing:
                bad.append(f"{f.name}:{n} {r.get('survey_key', '?')} missing {missing}")
                continue
            bad += validate_row(cfg, r, f"{f.name}:{n}")
            key = r["survey_key"]
            if key in seen:
                # last-wins on a duplicate is how two batches silently disagree
                bad.append(f"DUPLICATE key {key}: {seen[key]} and {f.name}")
                continue
            d = norm_doi(r.get("doi"))
            if d and d in dois:
                # one work, two keys — an extended version once double-counted a cell
                bad.append(f"DUPLICATE doi {d}: {dois[d]} and {key} — one work, one key "
                           f"(record a second DOI of the same work as ALT-DOI: in notes)")
                continue
            seen[key] = f.name
            if d:
                dois[d] = key
            rows.append(r)
    return files, rows, bad


def validate_row(cfg, r, where):
    bad = []
    if r["doi_class"] not in DOI_CLASSES:
        bad.append(f"{where} {r['survey_key']}: doi_class {r['doi_class']!r} not in {DOI_CLASSES}")
    if r["doi_class"] == "stated" and not r.get("doi"):
        bad.append(f"{where} {r['survey_key']}: doi_class stated but doi is null")
    if r["class"] not in CITATION_CLASSES:
        bad.append(f"{where} {r['survey_key']}: class {r['class']!r} not in {CITATION_CLASSES}")
    lp = r.get("locus_proposed")
    if lp is not None and lp not in cfg.all_locus_ids:
        bad.append(f"{where} {r['survey_key']}: locus_proposed {lp!r} not a declared cell")
    if r.get("year") is not None and not isinstance(r["year"], int):
        bad.append(f"{where} {r['survey_key']}: year must be int or null")
    return bad


def build(cfg, args):
    files, rows, bad = load_batches(cfg)
    if not files:
        print(f"no row files in {cfg.path('corpus_dir', 'rows')} — dispatch survey-indexer first",
              file=sys.stderr)
        return 1
    if bad:
        print("⚠️  defects — nothing written:", file=sys.stderr)
        for b in bad:
            print(f"   {b}", file=sys.stderr)
        return 1
    rows.sort(key=lambda r: (r["locus_proposed"] or "~", r["year"] or 0, r["survey_key"]))
    write_jsonl(cfg.corpus, rows, CORPUS_KEYS)
    render_index(cfg, rows, files)
    report(cfg, rows)
    return 0


def render_index(cfg, rows, files):
    out = [
        "# INDEX — the survey corpus", "", banner("index build"),
        f"Merged from {len(files)} batch files: " + ", ".join(f.name for f in files), "",
        f"**{len(rows)} documents.** The searchable artifact is `corpus.jsonl`; this file is the",
        "human view of it. `locus_proposed` is a seed, never a placement — only a synthesist that",
        "has read the document writes `locus`, in the import ledger.", "",
        "| cell | key | year | venue | class | DOI | conclusion |",
        "|---|---|---|---|---|---|---|",
    ]
    glyph = {"stated": "✓", "derived": "⚠ derived", "unresolved": "?", "none": "—"}
    for r in rows:
        flag = "" if r["citable"] else " ⛔"
        one = (r["one_line"] or "").replace("|", "\\|")
        out.append(f"| {r['locus_proposed'] or '?'}{flag} | `{r['survey_key']}` | "
                   f"{r['year'] or '—'} | {r['venue'] or '—'} | {r['class']} | "
                   f"{glyph.get(r['doi_class'], '—')} | {one} |")
    out += ["", "⛔ = indexed but not citable; see `DO_NOT_CITE.md`.",
            "⚠ derived = the DOI was reconstructed, not read off the document. A derived key may",
            "not be the sole support for a quantity."]
    cfg.path("corpus_dir", "INDEX.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def report(cfg, rows):
    thin = cfg.thresholds["min_citable_per_cell"]
    print(f"corpus.jsonl   {len(rows)} rows\nINDEX.md       rendered")
    print("\nlocus_proposed histogram (citable rows):")
    hist = Counter(r["locus_proposed"] or "?" for r in rows if r["citable"])
    for cell in cfg.all_locus_ids + ["?"]:
        n = hist.get(cell, 0)
        warn = f"   <-- thin (< {thin})" if cell in cfg.cell_ids and n < thin else ""
        print(f"  {cell:6s} {n:4d}  {'#' * min(n, 60)}{warn}")
    print(f"\nSPLIT: proposals  {sum(1 for r in rows if (r['locus_reason'] or '').startswith('SPLIT:'))}")
    print(f"citable:false     {sum(1 for r in rows if not r['citable'])}")
    print(f"class             {dict(Counter(r['class'] for r in rows))}")
    print(f"doi_class         {dict(Counter(r['doi_class'] for r in rows))}")


def timeline(cfg, args):
    rows = read_jsonl(cfg.corpus)
    if not rows:
        print("no corpus.jsonl — run `survey index build` first", file=sys.stderr)
        return 1
    rec = cfg.thresholds["recency_year"]
    dated = [r for r in rows if isinstance(r.get("year"), int)]
    undated = [r for r in rows if not isinstance(r.get("year"), int)]
    title = cfg.survey.get("short_title") or cfg.survey.get("title", "the survey")
    out = [f"# TIMELINE — {title}", "", banner("index timeline"), "",
           f"{len(dated)} dated works, {len(undated)} undated. Era boundaries are editorial and are",
           "declared in survey.toml; the contents of each era are not.", "",
           "## Density by decade and cell", ""]
    decades = sorted({(r["year"] // 10) * 10 for r in dated})
    present = [c for c in cfg.all_locus_ids + ["?"]
               if any((r.get("locus_proposed") or "?") == c for r in dated)]
    out.append("| decade | " + " | ".join(present) + " | total |")
    out.append("|---" * (len(present) + 2) + "|")
    for d in decades:
        inrow = [r for r in dated if (r["year"] // 10) * 10 == d]
        cnt = Counter(r.get("locus_proposed") or "?" for r in inrow)
        out.append(f"| {d}s | " + " | ".join(str(cnt.get(c, 0)) for c in present)
                   + f" | **{len(inrow)}** |")
    recent = [r for r in dated if r["year"] >= rec]
    bycell = defaultdict(int)
    for r in recent:
        bycell[r.get("locus_proposed") or "?"] += 1
    out += ["", f"**Published {rec} or later: {len(recent)}.** Each cell needs at least "
            f"{cfg.thresholds['min_recent_per_cell']}.", "", "| cell | works from "
            f"{rec}+ |", "|---|---|"]
    for c in cfg.cell_ids:
        n = bycell.get(c, 0)
        out.append(f"| {c} | {n}{' ⚠️ thin' if n < cfg.thresholds['min_recent_per_cell'] else ''} |")
    out.append("")
    if cfg.eras:
        out += ["## The eras", ""]
        for era in cfg.eras:
            lo, hi = era.get("from", 0), era.get("to", 9999)
            items = sorted([r for r in dated if lo <= r["year"] <= hi], key=lambda r: r["year"])
            span = f"{lo}–{hi}" if hi < 9999 else f"{lo}–"
            out += [f"### {span} — {era.get('title', '')}", "", era.get("gloss", ""), "",
                    f"*{len(items)} works.*", ""]
            for r in items:
                out.append(f"- **{r['year']}** `{r['survey_key']}` [{r.get('locus_proposed') or '?'}]"
                           f" — {r.get('one_line') or ''}")
            out.append("")
    if undated:
        out += ["## Undated", "", "No year could be read from the source. Never guessed — an",
                "undated row is a hand-resolution item.", ""]
        out += [f"- `{r['survey_key']}` — {r.get('one_line') or ''}" for r in undated]
    cfg.path("corpus_dir", "timeline.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"timeline.md    {len(dated)} dated, {len(undated)} undated, {len(recent)} from {rec}+")
    for c in cfg.cell_ids:
        if bycell.get(c, 0) < cfg.thresholds["min_recent_per_cell"]:
            print(f"  ⚠️  {c} has fewer than {cfg.thresholds['min_recent_per_cell']} source(s) from {rec}+")
    return 0
