"""`survey ledger scan|propose|merge-claims|sync-corpus|emit|adopt-bib`.

Re-home references from origin workspaces into this survey's taxonomy and record
every decision in IMPORT_LEDGER.tsv. Origins are organised by topic; the taxonomy
is not, so the unit of decision is the paper and only an agent that has read it
may place it.

Ordering that must never break (corrected 2026-08-24 in the original plan):
    claims.tsv (synthesists) → merge-claims → emit
**The bibliography is an output of the synthesis, not an input to it.** emit
refuses any row still at locus '?', and locus only exists once a reader claims it.
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from . import bib
from .schema import (CITEKEY_RE, LEDGER_COLS as _BASE_COLS, CLAIMS_COLS, PROTECTED_PREFIXES,
                     read_jsonl, read_tsv, write_tsv)
from .util import today

LEDGER_COLS = _BASE_COLS[:7] + ["split"] + _BASE_COLS[7:]
LEGACY_CLAIMS_COLS = ["survey_key", "locus", "locus_secondary", "reason"]
YEAR_RE = bib.YEAR_RE


# ---- origins ----------------------------------------------------------------
def origin_entries(cfg, origin):
    """Yield (cluster, Entry, base_dir, source_prefix) for one [[origins]] block.

    adapter = "bib": parse every file in `bib` (globs, relative to `root`).
    `cluster_regex` extracts the source cluster from the filename (group 1);
    without it the cluster is `cluster` (default '-')."""
    root = (cfg.ws / origin["root"]).resolve()
    prefix = origin.get("source_prefix")
    if prefix is None:
        try:
            prefix = str(root.relative_to(cfg.source_root)) + "/"
        except ValueError:
            prefix = str(root) + "/"
    rx = re.compile(origin["cluster_regex"]) if origin.get("cluster_regex") else None
    for pattern in origin.get("bib", []):
        for path in sorted(root.glob(pattern)):
            cluster = origin.get("cluster", "-")
            if rx:
                m = rx.search(path.name)
                if m:
                    cluster = m.group(1)
            for e in bib.parse(path):
                yield cluster, e, root, prefix, path


def source_md(fields, base):
    r"""Extract and resolve the `Source: <path>.md` join from a note.

    Undo BibTeX's `\%` escape; resolve a `...` elision by glob ONLY when exactly
    one file matches — an ambiguous elision is a judgement call for the curator."""
    m = re.search(r"Source:\s*(\S+?\.md)", fields.get("note", ""))
    if not m:
        return None, "no Source: in note"
    raw = m.group(1).rstrip(".").replace("\\%", "%")
    if (base / raw).exists():
        return raw, None
    if "..." in raw:
        head, _, tail = raw.partition("...")
        d = (base / head).parent
        hits = sorted(d.glob(f"{Path(head).name}*{tail}")) if d.is_dir() else []
        if len(hits) == 1:
            return str(hits[0].relative_to(base)), None
        return None, f"elided, {len(hits)} matches — hand resolution"
    return None, "path does not resolve"


def corrections_keys(cfg):
    keys = set()
    for o in cfg.origins:
        if o.get("corrections"):
            p = (cfg.ws / o["root"]).resolve() / o["corrections"]
            if p.exists():
                keys |= set(re.findall(r"`([a-z][a-z0-9_]+)`", p.read_text(encoding="utf-8")))
    return keys


# ---- ledger io --------------------------------------------------------------
def read_ledger(cfg):
    if not cfg.ledger.exists():
        sys.exit("no IMPORT_LEDGER.tsv — run `survey ledger scan` first")
    rows = read_tsv(cfg.ledger)
    for r in rows:
        for c in LEDGER_COLS:
            r.setdefault(c, "")
    return rows


def write_ledger(cfg, rows):
    cfg.ledger.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(cfg.ledger, rows, LEDGER_COLS)


def read_claims(path):
    """Claims files with a header are read by name. Headerless files are the
    original 4-column shape (no split column)."""
    lines = [l for l in Path(path).read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    if not lines:
        return []
    if lines[0].split("\t")[0] == "survey_key":
        return read_tsv(path)
    width = max(len(l.split("\t")) for l in lines)
    cols = CLAIMS_COLS if width >= 5 else LEGACY_CLAIMS_COLS
    out = []
    for l in lines:
        v = [x.strip() for x in l.split("\t")]
        v += [""] * (len(cols) - len(v))
        out.append(dict(zip(cols, v)))
    return out


SEP = " || "


def protected_segments(reason):
    """Provenance segments of a ' || '-joined reason. A marker counts in ANY
    segment, not only as a prefix: the original tool checked startswith(), so
    `DOI-UPGRADED: … || CORR: …` silently lost its CORR guard in the first run."""
    return [s.strip() for s in (reason or "").split("||")
            if s.strip().startswith(PROTECTED_PREFIXES)]


def has_marker(reason, marker):
    return any(s.startswith(marker) for s in protected_segments(reason))


def merge_reason(old, new):
    """Keep every protected provenance segment already in the reason, then the new text."""
    keep = protected_segments(old)
    new = (new or "").strip()
    if new and any(new == s or new in s for s in keep):
        new = ""
    return SEP.join(keep + ([new] if new else [])) or new


# ---- commands ---------------------------------------------------------------
def scan(cfg, args):
    rows, seen, unjoined, malformed, collisions = [], {}, [], [], []
    for o in cfg.origins:
        if o.get("adapter", "bib") != "bib":
            continue
        n = 0
        for cluster, e, base, prefix, path in origin_entries(cfg, o):
            n += 1
            smd, defect = source_md(e.fields, base)
            resolved = prefix + smd if smd else "UNJOINED"
            if not smd:
                unjoined.append((o["id"], cluster, e.key, e.get("title", "?"), e.get("year", "?"), defect))
            if not CITEKEY_RE.match(e.key):
                kind = "misplaced year" if YEAR_RE.search(e.key) else "no year"
                malformed.append((o["id"], e.key, e.get("title", "?"), e.get("year", "?"),
                                  bib.propose_key(e.key, e.fields), kind))
            if e.key in seen:
                collisions.append(f"{e.key}: {seen[e.key]} and {o['id']}")
            seen[e.key] = o["id"]
            rows.append({"origin": o["id"], "origin_key": e.key, "survey_key": e.key,
                         "source_cluster": cluster, "source_md": resolved, "locus": "?",
                         "locus_secondary": "", "split": "", "decided_by": "-", "decided_on": "-",
                         "doi_class": bib.classify_doi(e.fields), "class": bib.guess_class(e.type, e.fields),
                         "citable": "yes", "reason": "-"})
        print(f"  origin {o['id']}: {n} entries")
    write_ledger(cfg, rows)
    _write_worklist(cfg, "import_unjoined.md", "references with no machine-readable summary path",
                    ["origin", "cluster", "origin_key", "title", "year", "defect"], unjoined,
                    "The only citekey→document join is a `Source: <path>.md` note. emit refuses these "
                    "until source_md resolves. ⚠️ Publisher PDF filenames look like DOIs — never join on a filename.")
    _write_worklist(cfg, "import_malformed.md", "citekeys that violate author-year_topic",
                    ["origin", "origin_key", "title", "year", "proposed", "defect"], malformed,
                    "A misplaced year is worse than none: a citekey grep extracts `jones1990` from "
                    "`smith_jones1990`. The curator applies renames; nothing is renamed automatically.")
    print(f"\nledger rows         {len(rows)}\nunjoined (hand)     {len(unjoined)}\n"
          f"malformed citekeys  {len(malformed)}\ndoi_class           {dict(Counter(r['doi_class'] for r in rows))}")
    for c in collisions:
        print(f"  ⚠️  COLLISION {c} — hard error at emit", file=sys.stderr)
    return 0


def _write_worklist(cfg, name, title, cols, items, note):
    lines = [f"# {name[:-3]} — {title}", "", "**Generated by `survey ledger scan`. Hand resolution, one at a time.**",
             "", note, "", f"**{len(items)} entries.**", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for it in items:
        lines.append("| " + " | ".join(str(x)[:70] for x in it) + " |")
    cfg.path("bib_dir", name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def propose(cfg, args):
    rows = read_ledger(cfg)
    seeds = {o["id"]: o.get("seed", {}) for o in cfg.origins}
    n = 0
    for r in rows:
        if r["locus"] not in ("?", ""):
            continue                      # never overwrite a real decision
        s = seeds.get(r["origin"], {})
        seed = s.get(r["source_cluster"]) or s.get("*")
        if not seed:
            continue
        r["reason"], r["decided_by"] = f"SEED:{seed}", "heuristic"
        n += 1
    write_ledger(cfg, rows)
    print(f"proposed seeds for {n} rows (locus stays '?' — only a reader may set it)")
    for seed, c in Counter(r["reason"] for r in rows if r["reason"].startswith("SEED:")).most_common():
        print(f"  {seed:24s} {c}")
    return 0


def _syntheses_text(cfg):
    out = {}
    for t in cfg.tracks:
        p = cfg.path("tracks_dir", t.dir, "synthesis.md")
        if p.exists():
            out[t.id] = p.read_text(encoding="utf-8")
    return out


def merge_claims(cfg, args):
    rows = read_ledger(cfg)
    by_key = {r["survey_key"]: r for r in rows}
    claims = defaultdict(list)          # key -> [(track_id, claim_row)]
    malformed = []
    for t in cfg.tracks:
        p = cfg.path("tracks_dir", t.dir, "claims.tsv")
        if not p.exists():
            continue
        for c in read_claims(p):
            if not c.get("survey_key") or not c.get("locus"):
                malformed.append(f"{t.dir}: {c}")
                continue
            claims[c["survey_key"]].append((t.id, c))

    multi = {k: v for k, v in claims.items() if len(v) > 1}
    # Two tracks naming one work is a conflict only if they disagree about the CELL.
    # Agreement = one analyses, the others cite (locus_secondary). The original tool
    # counted agreement as conflict, making a clean result look alarming.
    disputed = {k: v for k, v in multi.items() if len({c["locus"] for _, c in v}) > 1}
    crossref = {k: v for k, v in multi.items() if k not in disputed}
    corpus_locus = {r["survey_key"]: r.get("locus_proposed") for r in read_jsonl(cfg.corpus)}
    # A row placed OUT is *correctly* unclaimed; only an in-taxonomy row without a claim is a gap.
    unclaimed = [k for k, r in by_key.items() if k not in claims and r.get("citable", "yes") == "yes"
                 and r["locus"] in ("?", "") and corpus_locus.get(k) not in (cfg.out_label, None)]
    unknown = sorted(k for k in claims if k not in by_key)
    splits = []
    for key, cl in claims.items():
        if key not in by_key or key in disputed:
            continue
        locus = cl[0][1]["locus"]
        owner = next(((tid, c) for tid, c in cl if tid == locus), cl[0])
        citing = [tid for tid, _ in cl if tid != owner[0]]
        c = owner[1]
        sec = ",".join(x for x in [c.get("locus_secondary", "").strip("-")] + citing if x)
        reason = c.get("reason", "") if len(cl) == 1 else "CROSSREF: " + c.get("reason", "")
        if c.get("split"):
            splits.append(key)
        by_key[key].update(locus=locus, locus_secondary=sec, split=c.get("split", ""),
                           decided_by=f"agent:{cfg.track_by_id(owner[0]).dir}",
                           decided_on=today(),
                           reason=merge_reason(by_key[key]["reason"], reason))
    write_ledger(cfg, rows)

    # Orphans: placed in a cell yet discussed by NO synthesis. (A first version asked
    # whether the receiving track also claimed it — every hit was a false positive.)
    syn = _syntheses_text(cfg)
    orphaned = []
    if syn:
        for key, cl in claims.items():
            placed = {c["locus"] for _, c in cl} - {cfg.out_label, "?", "-", ""}
            if placed and not any(f"`{key}`" in s or key in s for s in syn.values()):
                orphaned.append((key, cl[0][0], cl[0][1]["locus"]))

    print(f"claimed once             {len(claims) - len(multi)}")
    print(f"cross-referenced (agree) {len(crossref)}")
    print(f"DISPUTED (disagree)      {len(disputed)}")
    print(f"split (recorded)         {len(splits)}")
    print(f"unclaimed (in taxonomy)  {len(unclaimed)}")
    print(f"placed but undiscussed   {len(orphaned)}" + ("" if syn else "  (no syntheses yet)"))
    fail = False
    for k, cl in sorted(disputed.items()):
        fail = True
        print(f"⚠️  DISPUTED {k}: " + "; ".join(f"{tid}->{c['locus']}" for tid, c in cl))
    for k in sorted(unclaimed)[:40]:
        fail = True
        print(f"⚠️  UNCLAIMED {k}")
    for k, tid, loc in orphaned:
        fail = True
        print(f"⚠️  ORPHAN {k}: claimed by {tid} as {loc}, discussed in no synthesis")
    for k in unknown:
        fail = True
        print(f"⚠️  claimed but not in ledger: {k}")
    for m in malformed:
        fail = True
        print(f"⚠️  malformed claim {m}")
    return 1 if fail else 0


def sync_corpus(cfg, args):
    """Copy what the readers already decided from corpus.jsonl into the ledger —
    new inbox rows, and OUT verdicts. No judgement is involved."""
    rows = read_ledger(cfg)
    by_key = {r["survey_key"]: r for r in rows}
    corpus = read_jsonl(cfg.corpus)
    if not corpus:
        sys.exit("no corpus.jsonl")
    added = promoted = 0
    for c in corpus:
        k, locus = c["survey_key"], c.get("locus_proposed")
        if k not in by_key:
            rows.append({"origin": c.get("origin") or "inbox", "origin_key": c.get("origin_key") or k,
                         "survey_key": k, "source_cluster": c.get("source_cluster") or "-",
                         "source_md": c.get("source_md") or c.get("source_pdf") or "UNJOINED",
                         "locus": "?", "locus_secondary": "", "split": "",
                         "decided_by": "corpus-sync", "decided_on": today(),
                         "doi_class": c.get("doi_class") or "none", "class": c.get("class") or "P",
                         "citable": "yes" if c.get("citable") else "no",
                         "reason": "SYNCED from corpus.jsonl"})
            by_key[k] = rows[-1]
            added += 1
        if by_key[k]["locus"] in ("?", "") and locus == cfg.out_label:
            by_key[k].update(locus=cfg.out_label, decided_by="corpus-sync", decided_on=today(),
                             reason=merge_reason(by_key[k]["reason"], f"{cfg.out_label}: outside the taxonomy per corpus"))
            promoted += 1
    write_ledger(cfg, rows)
    print(f"added from corpus   {added}\n{cfg.out_label} placements set  {promoted}\nledger now          {len(rows)} rows")
    return 0


def _entry_pool(cfg):
    """origin entries keyed (origin, origin_key); curated entries keyed survey_key."""
    pool = {}
    for o in cfg.origins:
        if o.get("adapter", "bib") == "bib":
            for _c, e, *_ in origin_entries(cfg, o):
                pool[(o["id"], e.key)] = e
    curated = {}
    cdir = cfg.path("bib_dir", "curated")
    if cdir.is_dir():
        for p in sorted(cdir.glob("*.bib")):
            for e in bib.parse(p):
                curated[e.key] = e
    return pool, curated


def emit(cfg, args):
    """Refuse everything unsafe, then write refs.bib mechanically. Its most
    important property is that it says no."""
    rows = read_ledger(cfg)
    corr = corrections_keys(cfg)
    pool, curated = _entry_pool(cfg)
    refused, ok, seen = [], [], {}
    for r in rows:
        if r.get("citable", "yes") != "yes":
            continue
        why = []
        if r["locus"] in ("?", ""):
            why.append("locus is '?' — run merge-claims; there is no default cell")
        src = r["source_md"]
        if src == "UNJOINED":
            why.append("no Source: path — see import_unjoined.md")
        elif not (cfg.source_root / src).exists() and not (cfg.ws / src).exists():
            why.append("source_md does not resolve on disk")
        if r["origin_key"] in corr and not has_marker(r["reason"], "CORR:"):
            why.append("named in an origin's corrections file — reason needs a 'CORR:' segment")
        if not CITEKEY_RE.match(r["survey_key"]):
            why.append("survey_key violates author-year_topic")
        if r["survey_key"] in seen:
            why.append(f"survey_key collides with {seen[r['survey_key']]}")
        seen[r["survey_key"]] = r["origin"]
        e = curated.get(r["survey_key"]) or pool.get((r["origin"], r["origin_key"]))
        if e is None:
            why.append("no BibTeX entry (origin or 90_bib/curated/<key>.bib)")
        (refused if why else ok).append((r, e, why))

    print(f"would emit   {len(ok)}\nrefused      {len(refused)}")
    if refused:
        for w, c in Counter(w for _, _, ws in refused for w in ws).most_common():
            print(f"  {c:4d}  {w}")
        if args.verbose:
            for r, _, ws in refused:
                print(f"    {r['survey_key']}: {'; '.join(ws)}")
        print("\nNothing written. Resolve the refusals (survey-ref-curator, serially) and re-run.")
        return 1
    if args.check:
        return 0
    entries = []
    for r, e, _ in sorted(ok, key=lambda x: x[0]["survey_key"]):
        f = dict(e.fields)
        f["class"] = r["class"] or f.get("class", "P")
        if "Source:" not in f.get("note", ""):
            f["note"] = (f.get("note", "") + f" Source: {r['source_md']}. Origin: {r['origin']}:{r['origin_key']}.").strip()
        entries.append(bib.Entry(e.type, r["survey_key"], f))
    bib.write(cfg.refs_bib, entries,
              header=f"% Generated by `survey ledger emit` on {today()} from IMPORT_LEDGER.tsv. Do not edit;\n"
                     f"% edit 90_bib/curated/<key>.bib or the ledger and re-emit.")
    print(f"refs.bib     {len(entries)} entries written")
    return 0


def adopt_bib(cfg, args):
    """Bootstrap: split an existing hand-curated refs.bib into curated/<key>.bib,
    so a workspace migrated from the original pipeline re-emits identically."""
    cdir = cfg.path("bib_dir", "curated")
    cdir.mkdir(parents=True, exist_ok=True)
    n = 0
    for e in bib.parse(args.file):
        (cdir / f"{e.key}.bib").write_text(bib.render(e) + "\n", encoding="utf-8")
        n += 1
    print(f"adopted {n} entries into {cdir}")
    return 0
