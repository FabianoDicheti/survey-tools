"""`survey stats` — compute every headline count once.

The original paper said 178 in §3.7, 182 in §3.8, 187 in §9.1 and 211 vs 215 in
the reference header: four denominators for one corpus, in a paper whose pitch
is bookkeeping discipline. Prose now writes `{{n:key}}` and `survey build`
substitutes the value from this one computation.
"""
import re
from collections import Counter

from .schema import write_json
from .workspace import WS

macro_re = re.compile(r"\{\{n:([a-z0-9_.]+)\}\}")


def compute(cfg):
    ws = WS(cfg)
    s = {}
    c = ws.corpus
    s["corpus.total"] = len(c)
    s["corpus.citable"] = sum(1 for r in c if r.get("citable"))
    s["corpus.recent"] = sum(1 for r in c if isinstance(r.get("year"), int) and r["year"] >= cfg.thresholds["recency_year"])
    s["corpus.recency_year"] = cfg.thresholds["recency_year"]
    for k, v in Counter(r.get("origin") for r in c).items():
        s[f"corpus.origin.{k}"] = v
    for k, v in Counter(r.get("class") for r in c if r.get("citable")).items():
        s[f"corpus.class.{k}"] = v
    for k, v in Counter(r.get("doi_class") for r in c).items():
        s[f"corpus.doi.{k}"] = v
    years = [r["year"] for r in c if isinstance(r.get("year"), int)]
    if years:
        s["corpus.year_min"], s["corpus.year_max"] = min(years), max(years)
    L = [r for r in ws.ledger if r.get("citable", "yes") == "yes"]
    placed = [r for r in L if r.get("locus") not in ("?", "")]
    s["ledger.total"] = len(ws.ledger)
    s["ledger.placed"] = len(placed)
    in_tax = [r for r in placed if r["locus"] != cfg.out_label]
    s["ledger.placed_in_taxonomy"] = len(in_tax)
    for t in cfg.all_locus_ids:
        s[f"cell.{t}"] = sum(1 for r in placed if r["locus"] == t)
    sp = [r for r in in_tax if r.get("split", "").strip()]
    s["split.count"] = len(sp)
    s["split.pct"] = round(100 * len(sp) / len(in_tax), 1) if in_tax else 0
    s["bib.entries"] = len(ws.bib)
    s["paper.cited"] = len(ws.paper_keys)
    s["paper.cited_recent"] = sum(1 for k in ws.paper_keys
                                  if (y := re.search(r"(19|20)\d{2}", k)) and int(y.group(0)) >= cfg.thresholds["recency_year"])
    for k, v in Counter(ws.cls(k) for k in ws.paper_keys).items():
        s[f"paper.class.{k}"] = v
    s["paper.derived_doi"] = sum(1 for k in ws.paper_keys if ws.derived(k))
    s["tracks"] = len(cfg.tracks)
    s["cells"] = len(cfg.cells)
    return s


def run(cfg, args):
    s = compute(cfg)
    out = cfg.path("paper_dir", "build")
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "stats.json", s)
    w = max(len(k) for k in s)
    for k, v in s.items():
        print(f"  {k.ljust(w)}  {v}")
    print(f"\n-> {out / 'stats.json'}   (cite in prose as {{{{n:<key>}}}})")
    return 0


def substitute(cfg, text, stats=None):
    s = stats or compute(cfg)
    return macro_re.sub(lambda m: str(s.get(m.group(1), m.group(0))), text)
