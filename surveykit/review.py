"""`survey review extract|batch|merge|fix-docx` — answer an external review.

Order that is not a preference (the original revision's W1 rule): **find the
production defects first.** A reviewer who read a document with merged
sentences and displaced citation markers files scholarship complaints about
conversion damage; until those are separated, no judgement about whether a
comment is substantive can be trusted.

extract   comments.xml + the text each comment is anchored to; flags anchors
          that look like conversion damage (raw CITATION field codes, mid-word
          joins, empty anchors) and author names the bibliography does not hold.
batch     split comments into N worksheets for parallel survey-comment-triager
          agents, one disposition TSV each (triage only; fixes never race).
merge     fold batch TSVs into comments_disposition.tsv under a FIXED vocabulary
          (six parallel agents without one produced ~40 category spellings), and
          generate the summary tables from the per-ID rows — never hand-count.
fix-docx  repair table grid widths in a returned docx.
"""
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from . import docxkit
from .schema import COMMENT_CATEGORIES, DISPOSITIONS, DISPOSITION_COLS, read_tsv, write_json, write_tsv
from .workspace import WS

TOKEN = re.compile(r'<w:commentRangeStart w:id="(\d+)"/>|<w:commentRangeEnd w:id="(\d+)"/>|<w:t(?: [^>]*)?>([^<]*)</w:t>'
                   r'|<w:instrText(?: [^>]*)?>([^<]*)</w:instrText>|(</w:p>)')
KEYWORDS = [
    ("production_defect", r"corromp|ininteligí|fundid|merged|garbled|corrupt|formata|vazia|empty|typo|erro de digita"),
    ("bibliography", r"bibliograf|referênc|reference|citar|cite|incluir.*(trabalho|estudo)|2024|2025|literature|literatura"),
    ("taxonomy_scope", r"taxonom|fabric manager|quinto agente|fifth|eixo|axis|aloca(dor|ção).*aprendiz|learned|machine learning"),
    ("attribution", r"atribui|attribut|misattrib"),
    ("overclaim", r"exager|overclaim|restritiv|too strong|forte demais|absolut"),
    ("tone_clarity", r"tom |tone|clareza|clarity|gramát|grammar|redação"),
    ("evidentiary", r"evidên|evidence|métric|metric|medi[çd]|measure|metodolog|method|defini"),
]
NORMALISE = {
    "docx_production_defect": "production_defect", "production": "production_defect",
    "resolved — production defect": "production_defect", "biblio": "bibliography", "references": "bibliography",
    "scope": "taxonomy_scope", "taxonomy": "taxonomy_scope", "method": "evidentiary", "methodological": "evidentiary",
    "tone": "tone_clarity", "clarity": "tone_clarity", "grammar": "tone_clarity", "typo": "formatting",
    "wrong_attribution": "attribution", "in_progress": "needs_fix", "fixed": "resolved", "done": "resolved",
    "rebutted": "rebuttal", "decline": "declined", "review": "needs_review",
}


def _rdir(cfg):
    d = cfg.path("review_dir")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _text(xml):
    return " ".join("".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", xml)).split())


def anchors(document_xml):
    open_, out, fields = {}, defaultdict(list), defaultdict(list)
    for m in TOKEN.finditer(document_xml):
        s, e, t, instr, para = m.groups()
        if s:
            open_[s] = True
        elif e:
            open_.pop(e, None)
        elif t is not None or instr is not None or para:
            for cid in open_:
                if t is not None:
                    out[cid].append(t)
                elif instr is not None:
                    fields[cid].append(instr)
                else:
                    out[cid].append("¶")
    return {k: "".join(v).strip() for k, v in out.items()}, {k: " ".join(v) for k, v in fields.items()}


def suspicion(anchor, field, comment, bib_surnames):
    flags = []
    if field and "CITATION" in field:
        flags.append("citation_field:" + " ".join(field.split())[:80])
    if re.search(r"CITATION\s+\S+", anchor):
        flags.append("raw_citation_code_in_text")
    if re.search(r"\b[a-z]{1,2}[A-Z]{2,}[a-z-]*\b|[a-z]{3,}\.[A-Z][a-z]{2,}", anchor):
        flags.append("mid_word_or_sentence_join")
    if not anchor:
        flags.append("no_inline_anchor")
    for name in set(re.findall(r"\b([A-Z][a-zà-ÿ]+)(?: et al\.?)?,? \(?(?:19|20)\d{2}", comment)):
        if bib_surnames and name.lower() not in bib_surnames:
            flags.append(f"author_not_in_bib:{name}")
    return flags


def guess_category(text):
    t = text.lower()
    for cat, rx in KEYWORDS:
        if re.search(rx, t):
            return cat
    return "other"


def extract(cfg, args):
    z = zipfile.ZipFile(args.docx)
    try:
        cx = z.read("word/comments.xml").decode("utf-8")
    except KeyError:
        print("docx has no comments")
        return 1
    dx = z.read("word/document.xml").decode("utf-8")
    anc, fld = anchors(dx)
    ws = WS(cfg)
    from .cite import Styler
    st = Styler(cfg)
    bib_surnames = {st.surname(a).lower() for e in ws.bib.values()
                    for a in re.split(r"\s+and\s+", e.get("author", "")) if a.strip()}
    out = []
    for m in re.finditer(r'<w:comment w:id="(\d+)"([^>]*)>(.*?)</w:comment>', cx, re.S):
        cid, attrs, body = m.groups()
        text = _text(body)
        author = re.search(r'w:author="([^"]*)"', attrs)
        a = anc.get(cid, "")
        flags = suspicion(a, fld.get(cid, ""), text, bib_surnames)
        out.append({"id": int(cid), "author": author.group(1) if author else "", "text": text, "anchor": a,
                    "flags": flags, "suggested_category": "production_defect" if any(
                        f.startswith(("citation_field", "raw_citation", "mid_word")) for f in flags) else guess_category(text)})
    out.sort(key=lambda c: c["id"])
    d = _rdir(cfg)
    write_json(d / "comments.json", out)
    n_anchor = sum(1 for c in out if c["anchor"])
    sus = sum(1 for c in out if c["suggested_category"] == "production_defect")
    print(f"{len(out)} comments; {n_anchor} with an inline anchor; {sus} suspected production defects")
    print("suggested categories:", dict(Counter(c["suggested_category"] for c in out)))
    print(f"-> {d / 'comments.json'}\nNext: write known_resolutions.md (settled items + defect classes), then `survey review batch`.")
    return 0


def batch(cfg, args):
    d = _rdir(cfg)
    cs = json.loads((d / "comments.json").read_text(encoding="utf-8"))
    n = max(1, args.n)
    size = -(-len(cs) // n)
    bdir = d / "batches"
    bdir.mkdir(exist_ok=True)
    for i in range(n):
        part = cs[i * size:(i + 1) * size]
        if not part:
            continue
        L = chr(65 + i)
        write_json(bdir / f"batch_{L}.json", part)
        tsv = d / f"disposition_batch_{L}.tsv"
        if not tsv.exists():
            write_tsv(tsv, [], DISPOSITION_COLS)
        print(f"batch {L}: ids {part[0]['id']}–{part[-1]['id']} ({len(part)}) -> {tsv.name}")
    print(f"Vocabulary — category: {', '.join(COMMENT_CATEGORIES)}\n"
          f"             disposition: {', '.join(DISPOSITIONS)}\n"
          "Evidence must cite an artifact (file:line, DOI, PDF page), never restate the manuscript.")
    return 0


def _norm(v, allowed):
    v = (v or "").strip().lower()
    v = NORMALISE.get(v, v).replace(" ", "_")
    if v in allowed:
        return v, True
    for a in allowed:                      # "resolved (part A); needs_fix (part B)" → first legal token
        if v.startswith(a):
            return a, False
    return v, False


def merge(cfg, args):
    d = _rdir(cfg)
    cs = {c["id"]: c for c in json.loads((d / "comments.json").read_text(encoding="utf-8"))} \
        if (d / "comments.json").exists() else {}
    rows, issues, seen = [], [], {}
    for f in sorted(d.glob("disposition_batch_*.tsv")):
        for r in read_tsv(f):
            try:
                cid = int(r["id"])
            except (ValueError, KeyError):
                issues.append(f"{f.name}: bad id {r.get('id')!r}")
                continue
            cat, ok1 = _norm(r.get("category"), COMMENT_CATEGORIES)
            disp, ok2 = _norm(r.get("disposition"), DISPOSITIONS)
            if not ok1:
                issues.append(f"id {cid}: category {r.get('category')!r} → {cat!r}" + ("" if cat in COMMENT_CATEGORIES else " (UNKNOWN)"))
            if not ok2:
                issues.append(f"id {cid}: disposition {r.get('disposition')!r} → {disp!r}" + ("" if disp in DISPOSITIONS else " (UNKNOWN)"))
            if not r.get("evidence", "").strip():
                issues.append(f"id {cid}: no evidence")
            if cid in seen:
                issues.append(f"id {cid}: dispositioned in both {seen[cid]} and {f.name}")
                continue
            seen[cid] = f.name
            rows.append({"id": cid, "category": cat, "disposition": disp, "evidence": r.get("evidence", "")})
    rows.sort(key=lambda r: r["id"])
    missing = sorted(set(cs) - set(seen))
    write_tsv(d / "comments_disposition.tsv", rows, DISPOSITION_COLS)
    open_ = [r for r in rows if r["disposition"] in ("needs_fix", "needs_review")]
    L = ["# Review disposition summary", "", "**Generated by `survey review merge` from comments_disposition.tsv. "
         "Do not edit.**", "", f"{len(rows)} of {len(cs) or len(rows)} comments dispositioned; "
         f"{len(missing)} without a disposition; {len(open_)} still open.", "",
         "| category | " + " | ".join(DISPOSITIONS) + " | total |", "|---" * (len(DISPOSITIONS) + 2) + "|"]
    grid = defaultdict(Counter)
    for r in rows:
        grid[r["category"]][r["disposition"]] += 1
    for cat in sorted(grid):
        L.append(f"| {cat} | " + " | ".join(str(grid[cat][x]) for x in DISPOSITIONS) + f" | {sum(grid[cat].values())} |")
    if missing:
        L += ["", "## Not yet dispositioned", "", ", ".join(map(str, missing))]
    if issues:
        L += ["", "## Vocabulary and evidence issues", ""] + [f"- {i}" for i in issues]
    (d / "DISPOSITION_SUMMARY.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"merged {len(rows)} dispositions; missing {len(missing)}; open {len(open_)}; issues {len(issues)}")
    print("by disposition:", dict(Counter(r["disposition"] for r in rows)))
    return 1 if missing or any("UNKNOWN" in i or "both" in i for i in issues) else 0


def fix_docx(cfg, args):
    docxkit.rewrite_part(args.src, args.dst, "word/document.xml", docxkit.fix_tables)
    print(f"repaired {getattr(docxkit.fix_tables, 'count', 0)} table grids -> {args.dst}")
    from .verify import docx_defects
    for d in docx_defects(Path(args.dst)):
        print(f"  remaining: {d}")
    return 0
