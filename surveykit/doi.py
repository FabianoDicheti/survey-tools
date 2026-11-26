"""`survey doi resolve [--apply]` — check reconstructed identifiers against live registries.

The original pipeline kept `DOI-DERIVED` markers for transparency; an external
reviewer read them as "never verified" (a fair reading of the surface). The fix
is to resolve them, not to hide them — and the automatable resolver's failure
mode is silently accepting a plausible wrong DOI, so:

  * an upgrade derived→stated happens only on an exact match of normalised title
    (similarity ≥ 0.92) AND year (or a recorded version-year difference);
  * every lookup, match or not, is written to <bib_dir>/doi_evidence.jsonl with
    the resolver URL, the returned title and year — the ledger cites that row;
  * entries with no DOI get title-search CANDIDATES for the curator, never an
    automatic DOI.
Registries: Crossref (api.crossref.org), DataCite (api.datacite.org), arXiv
(export.arxiv.org). No credentials, no personal data in requests.
"""
import difflib
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from . import bib
from .ledger import SEP, read_ledger, write_ledger
from .util import today
from .workspace import WS

UA = {"User-Agent": "surveykit/0.1 (literature-survey DOI verification)"}


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def norm_title(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t.lower().replace("{", "").replace("}", "")).split())


def lookup(ident):
    """Return dict(resolver, url, title, year) or dict(error)."""
    if ident.lower().startswith("arxiv:") or re.fullmatch(r"\d{4}\.\d{4,5}(v\d+)?", ident):
        aid = ident.split(":", 1)[-1]
        url = f"http://export.arxiv.org/api/query?id_list={urllib.parse.quote(re.sub(r'v\\d+$', '', aid))}"
        try:
            x = ET.fromstring(_get(url))
        except Exception as e:
            return {"resolver": "arxiv", "url": url, "error": str(e)}
        ns = {"a": "http://www.w3.org/2005/Atom"}
        e = x.find("a:entry", ns)
        if e is None or e.find("a:title", ns) is None:
            return {"resolver": "arxiv", "url": url, "error": "no entry"}
        return {"resolver": "arxiv", "url": url, "title": " ".join(e.find("a:title", ns).text.split()),
                "year": int(e.find("a:published", ns).text[:4])}
    for name, base in (("crossref", "https://api.crossref.org/works/"), ("datacite", "https://api.datacite.org/dois/")):
        url = base + urllib.parse.quote(ident)
        try:
            j = json.loads(_get(url))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            return {"resolver": name, "url": url, "error": f"HTTP {e.code}"}
        except Exception as e:
            return {"resolver": name, "url": url, "error": str(e)}
        if name == "crossref":
            m = j.get("message", {})
            title = (m.get("title") or [""])[0]
            if m.get("subtitle"):                 # Crossref splits "Main: Subtitle"
                title = f"{title}: {m['subtitle'][0]}"
            parts = (m.get("published-print") or m.get("published-online") or m.get("issued") or {}).get("date-parts", [[None]])
            year = parts[0][0]
        else:
            a = j.get("data", {}).get("attributes", {})
            title = (a.get("titles") or [{}])[0].get("title", "")
            year = a.get("publicationYear")
        return {"resolver": name, "url": url, "title": title, "year": int(year) if year else None}
    return {"resolver": "crossref+datacite", "url": ident, "error": "not registered (404 at both)"}


def search_title(title, year):
    url = "https://api.crossref.org/works?rows=3&query.bibliographic=" + urllib.parse.quote(title)
    try:
        items = json.loads(_get(url)).get("message", {}).get("items", [])
    except Exception as e:
        return [{"error": str(e)}]
    out = []
    for it in items:
        t = (it.get("title") or [""])[0]
        y = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        out.append({"doi": it.get("DOI"), "title": t, "year": y,
                    "similarity": round(difflib.SequenceMatcher(None, norm_title(t), norm_title(title)).ratio(), 3)})
    return out


def verdict(entry, res):
    if "error" in res:
        return "unresolved", res["error"]
    sim = difflib.SequenceMatcher(None, norm_title(res.get("title")), norm_title(entry.get("title"))).ratio()
    ey = int(entry.get("year")) if (entry.get("year") or "").isdigit() else None
    if sim >= 0.92 and ey and res.get("year") == ey:
        return "match", f"title {sim:.2f}, year {ey}"
    if sim >= 0.92 and ey and res.get("year") and abs(res["year"] - ey) <= 1:
        return "version_year", f"title {sim:.2f}; registry year {res['year']} vs entry {ey} — confirm the version read"
    return "mismatch", f"title {sim:.2f} ({res.get('title', '')[:60]!r}); year {res.get('year')} vs {ey}"


def resolve(cfg, args):
    ws = WS(cfg)
    rows = read_ledger(cfg)
    ev_path = cfg.path("bib_dir", "doi_evidence.jsonl")
    cache = {}
    if ev_path.exists():
        for line in ev_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r["key"]] = r
    targets = [r for r in rows if (args.keys and r["survey_key"] in args.keys)
               or (not args.keys and r.get("doi_class") in ("derived", "unresolved", "none") and r.get("citable", "yes") == "yes")]
    print(f"{len(targets)} entries to check" + (" (offline: cache only)" if args.offline else ""))
    out, upgrades = [], 0
    for r in targets:
        k = r["survey_key"]
        e = ws.bib.get(k)
        if e is None:
            continue
        ident = (e.get("doi") or "").strip() or ((("arXiv:" + e.get("eprint")) if e.get("eprint") else ""))
        if k in cache and cache[k].get("ident") == ident:
            rec = cache[k]
        elif args.offline:
            continue
        else:
            if ident:
                res = lookup(ident)
                v, why = verdict(e.fields, res)
                rec = {"key": k, "ident": ident, "date": today(), **res, "verdict": v, "why": why}
            else:
                rec = {"key": k, "ident": "", "date": today(), "verdict": "no_identifier",
                       "candidates": search_title(e.get("title", ""), e.get("year"))}
            time.sleep(0.2)                                   # be polite to public registries
            with ev_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.append(rec)
        print(f"  {rec['verdict']:14s} {k}  {rec.get('why', '')}")
        if args.apply and rec["verdict"] == "match" and r.get("doi_class") != "stated":
            r["doi_class"] = "stated"
            r["reason"] = SEP.join(x for x in [f"DOI-UPGRADED: {rec['resolver']} {rec['url']} on {rec['date']}; {rec['why']}",
                                               r.get("reason", "").strip()] if x and x != "-")
            cur = cfg.path("bib_dir", "curated", f"{k}.bib")
            if cur.exists():
                ent = bib.parse(cur)[0]
                ent.fields["note"] = ent.fields.get("note", "").replace("DOI-DERIVED", f"DOI-VERIFIED {rec['date']} ({rec['resolver']})")
                cur.write_text(bib.render(ent) + "\n", encoding="utf-8")
            upgrades += 1
    if args.apply:
        write_ledger(cfg, rows)
    from collections import Counter
    print(f"\nverdicts: {dict(Counter(r['verdict'] for r in out))}" + (f"; {upgrades} upgraded" if args.apply else
          "; dry run — re-run with --apply to upgrade exact matches"))
    print(f"evidence -> {ev_path.relative_to(cfg.ws)}. 'mismatch' and 'version_year' rows go to survey-ref-curator; never bulk-accept.")
    return 0
