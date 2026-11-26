"""`survey candidates merge --wave N` — scout candidate files → one fetch list.

Parallel scouts each write <fetch_dir>/candidates/G-nn.md and never a shared
file; N agents appending to one list is N-1 lost writes.

Dedupe sources, all needed (each caught a real miss in the original pipeline):
  inbox stems  — what the owner fetched this morning; refs.bib may not exist yet
  ledger keys  — the imported corpus
  corpus DOIs  — a scout minting a near-miss key for a held work
  ALT-DOI:     — one work, two DOIs, recorded in ledger reasons
  prior waves  — a work already requested and not yet dropped
"""
import re
import sys

from .schema import norm_doi, read_jsonl, read_tsv, CITEKEY_RE

ENTRY_RE = re.compile(r"^###\s+(?:\d+\.\s*)?`([^`]+)`", re.M)
FIELD_RE = {
    "doi": re.compile(r"^-\s*(?:DOI|arXiv|Identifier):\s*(.+)$", re.M | re.I),
    "why": re.compile(r"^-\s*Why:\s*(.+)$", re.M),
    "cls": re.compile(r"^-\s*Class:\s*(\w+)", re.M),
    "title": re.compile(r"^-\s*(?:Authors?\s*/\s*Title:?|Title:)\s*(.+)$", re.M),
}
ROUTES = (("unverified", "unverified"), ("market", "market"), ("rejected", "rejected"),
          ("already", "already_listed"), ("ranked", "ranked"))


def split_sections(text):
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if cur:
                out[cur] = "\n".join(buf)
            cur, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf)
    return out


def parse_entries(body):
    out = []
    for b in re.split(r"(?=^###\s)", body, flags=re.M):
        m = ENTRY_RE.search(b)
        if not m:
            continue
        e = {"key": m.group(1).strip()}
        for name, rx in FIELD_RE.items():
            mm = rx.search(b)
            e[name] = mm.group(1).strip() if mm else ""
        e["stated"] = bool(re.search(r"doi_status:\s*stated", b))
        out.append(e)
    return out


def _known(cfg, wave):
    keys = {r["survey_key"] for r in read_tsv(cfg.ledger)} if cfg.ledger.exists() else set()
    keys |= {r["survey_key"] for r in read_jsonl(cfg.corpus)}
    dois = {norm_doi(r.get("doi")) for r in read_jsonl(cfg.corpus) if r.get("doi")}
    for r in (read_tsv(cfg.ledger) if cfg.ledger.exists() else []):
        for m in re.finditer(r"ALT-DOI:\s*(\S+)", r.get("reason", "")):
            dois.add(norm_doi(m.group(1).rstrip(".,;")))
    inbox = {p.stem for p in cfg.path("inbox_dir").rglob("*.pdf") if "_unlisted" not in p.parts} \
        if cfg.path("inbox_dir").exists() else set()
    prior = {}
    for p in sorted(cfg.path("fetch_dir").glob("wave*/fetch_list.md")):
        w = p.parent.name
        if w == f"wave{wave}":
            continue
        for k in re.findall(r"^\|\s*\d+\s*\|\s*`([^`]+)`", p.read_text(encoding="utf-8"), re.M):
            prior.setdefault(k, w)
    return keys, dois, inbox, prior


def merge(cfg, args):
    cand = cfg.path("fetch_dir", "candidates")
    files = sorted(cand.glob("G-*.md"))
    if not files:
        print(f"no candidate files in {cand} — dispatch survey-scout first", file=sys.stderr)
        return 1
    keys, dois, inbox, prior = _known(cfg, args.wave)
    buckets = {b: [] for _, b in ROUTES}
    buckets["already"], seen, unrouted, defects = [], {}, [], []
    for f in files:
        gap = f.stem
        for heading, body in split_sections(f.read_text(encoding="utf-8")).items():
            h = heading.lower()
            route = next((b for word, b in ROUTES if word in h), None)
            for e in parse_entries(body):
                e["gap"] = gap
                d = norm_doi(re.split(r"\s+[-—(]", e.get("doi", ""))[0])
                if e["key"] in inbox:
                    e["dupe"] = "already in inbox"
                elif e["key"] in keys:
                    e["dupe"] = "key in corpus/ledger"
                elif d and d in dois:
                    e["dupe"] = f"DOI {d}"
                elif e["key"] in prior:
                    e["dupe"] = f"requested in {prior[e['key']]}, not yet dropped"
                if route is None:
                    unrouted.append((gap, heading, e["key"]))
                    continue
                if route in ("ranked", "market") and "dupe" in e:
                    buckets["already"].append(e)
                    continue
                if route in ("ranked", "market"):
                    if e["key"] in seen:
                        seen[e["key"]].append(gap)
                        continue
                    seen[e["key"]] = [gap]
                    if not CITEKEY_RE.match(e["key"]):
                        defects.append(f"{gap}: `{e['key']}` violates author-year_topic")
                    for fld in ("doi", "why", "cls"):
                        if not e.get(fld):
                            defects.append(f"{gap}: `{e['key']}` has no {fld}")
                buckets[route].append(e)
    multi = {k: v for k, v in seen.items() if len(v) > 1}
    wavedir = cfg.path("fetch_dir", f"wave{args.wave}")
    wavedir.mkdir(parents=True, exist_ok=True)
    text = render(cfg, args.wave, buckets, multi, files, defects)
    (wavedir / "fetch_list.md").write_text(text, encoding="utf-8")
    cfg.path("fetch_dir", "FETCH_LIST.md").write_text(text, encoding="utf-8")
    r = buckets["ranked"]
    print(f"gaps merged        {len(files)}\nranked to fetch    {len(r)}\nclass-M            {len(buckets['market'])}\n"
          f"already held       {len(buckets['already'])}\nunverified         {len(buckets['unverified'])}")
    if multi:
        print(f"wanted by 2+ gaps  {len(multi)} (fetch once)")
    if unrouted:
        print(f"⚠️  {len(unrouted)} entries in unrecognised sections — NOT listed:")
        for g, h, k in unrouted[:10]:
            print(f"      {g} under '## {h}' -> {k}")
    unstated = [e for e in r if not e["stated"]]
    if unstated:
        print(f"⚠️  {len(unstated)} ranked entries lack `doi_status: stated` — confirm before fetching")
    for d in defects[:20]:
        print(f"⚠️  {d}")
    return 1 if unrouted else 0


def render(cfg, wave, b, multi, files, defects):
    inbox = cfg.layout["inbox_dir"]
    L = [f"# FETCH LIST — wave {wave}", "", "**Generated by `survey candidates merge`. Do not edit — edit the "
         "candidate files.**", "", "## How to use this", "",
         f"Fetch each PDF below into `{inbox}/wave{wave}/` **named exactly as its citekey** "
         "(`<citekey>.pdf`). A misnamed drop is the likeliest human error in the pipeline; `survey verify` "
         "catches it, but only after the fact.", "",
         "Nothing here was downloaded. A scout's line is a pointer to a paper, not a source.", "",
         "Merged from: " + ", ".join(f.stem for f in files), "",
         f"## To fetch — {len(b['ranked'])} works", "", "| # | citekey | gap | class | DOI | verified | why |",
         "|---|---|---|---|---|---|---|"]
    for i, e in enumerate(sorted(b["ranked"], key=lambda x: (x["gap"], x["key"])), 1):
        L.append(f"| {i} | `{e['key']}` | {e['gap']} | {e.get('cls') or '?'} | {e.get('doi') or '—'} | "
                 f"{'✓' if e['stated'] else '⚠ unresolved'} | {e.get('why', '')} |")
    if multi:
        L += ["", "**Wanted by more than one gap — fetch once:** " +
              ", ".join(f"`{k}` ({', '.join(v)})" for k, v in multi.items())]
    if b["market"]:
        L += ["", f"## Class-M market evidence — {len(b['market'])}", "",
              "Primary artifacts only; each needs a `urldate` and a committed snapshot. May support no "
              "technical claim.", "", "| citekey | gap | source | why |", "|---|---|---|---|"]
        L += [f"| `{e['key']}` | {e['gap']} | {e.get('doi') or '—'} | {e.get('why', '')} |" for e in b["market"]]
    if b["already"]:
        L += ["", f"## Already held — {len(b['already'])}, do not fetch", ""]
        L += [f"- `{e['key']}` ({e['gap']}) — {e['dupe']}" for e in b["already"]]
    if b["unverified"]:
        L += ["", f"## Unverified — {len(b['unverified'])}, do not fetch", "",
              "The scout could not open the landing page. Not citations, not fetch targets.", ""]
        L += [f"- `{e['key']}` ({e['gap']}) — {e.get('why', '')}" for e in b["unverified"]]
    if defects:
        L += ["", "## Format defects (fix in the candidate file)", ""] + [f"- {d}" for d in defects]
    return "\n".join(L) + "\n"
