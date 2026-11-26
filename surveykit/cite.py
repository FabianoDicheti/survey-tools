"""`survey cite references` and `survey cite intext` — APA 7 from refs.bib.

references: render the references chapter with **cited works only** (a list
            longer than the citation set is the first thing a reviewer counts),
            one alphabetical list, each entry tagged `<!-- citekey -->` so the
            verifier can match it back.
intext:     the source keeps backtick citekeys so claims grep back to refs.bib;
            this writes a BUILD COPY with APA in-text citations and never touches
            the source. Mechanical, from refs.bib only — manual Zotero insertion
            in the original reproduced the misattribution it was meant to fix.

Both apply APA same-author-same-year disambiguation (2025a, 2025b) consistently,
which the original renderer lacked.
"""
import re
import unicodedata
from collections import defaultdict

from . import bib as bibmod
from .workspace import WS

LATEX = {r"\&": "&", r"\%": "%", r"\_": "_", r"\#": "#", r"\$": "$", "---": "—", "--": "–", "~": " ", r"\ ": " "}
ACCENT = {r"\'": "́", r"\`": "̀", r'\"': "̈", r"\^": "̂", r"\~": "̃", r"\c": "̧", r"\v": "̌"}
GENERIC_CORP = r"Inc|Consortium|Corp|Corporation|Team|Group|Foundation|Association|Committee|Project|Laboratory|Labs|Institute|University"
KEY_RE = re.compile(r"`([A-Za-z][A-Za-z0-9_]*)`")
PAREN_RE = re.compile(r"\(([^()]*)\)")
LOCATOR_RE = re.compile(r"^\s*(?P<sec>§\s?[0-9][0-9A-Za-z.\-]*)?\s*,?\s*(?P<page>pp?\.\s?[0-9][0-9–\-]*)?")


def detex(t):
    if not t:
        return ""
    for pat, rep in ACCENT.items():
        t = re.sub(re.escape(pat) + r"\{?([A-Za-z])\}?", lambda m, r=rep: unicodedata.normalize("NFC", m.group(1) + r), t)
    for a, b in LATEX.items():
        t = t.replace(a, b)
    return " ".join(t.replace("{", "").replace("}", "").split())


class Styler:
    def __init__(self, cfg):
        extra = cfg.guards.get("corporate_authors", "")
        self.corp = re.compile(r"\b(" + GENERIC_CORP + (("|" + extra) if extra else "") + r")\b", re.I)

    def _is_corp(self, raw):
        return (raw.startswith("{") and raw.endswith("}")) or (self.corp.search(raw) and "," not in raw)

    def author(self, raw):
        """'Surname, F. M.'; corporate names detected BEFORE braces are stripped
        ('Compute Express Link Consortium, Inc.' must not become '…, I.')."""
        raw = raw.strip().rstrip(",")
        if raw.lower() in ("others", "et al", "et al."):
            return "et al."
        if self._is_corp(raw):
            return detex(raw)
        raw = detex(raw).strip().rstrip(".")
        if not raw:
            return ""
        if "," in raw:
            sur, _, given = raw.partition(",")
        else:
            parts = raw.split()
            if len(parts) == 1:
                return parts[0]
            sur, given = parts[-1], " ".join(parts[:-1])
        ini = " ".join(f"{p[0]}." for p in given.replace(".", " ").split() if p[:1].isalpha())
        return f"{sur.strip()}, {ini}".strip().rstrip(",")

    def surname(self, raw):
        raw = raw.strip().rstrip(",")
        if raw.lower() in ("others", "et al", "et al."):
            return "et al."
        if self._is_corp(raw):
            return detex(raw)
        raw = detex(raw).strip().rstrip(".")
        if "," in raw:
            return raw.partition(",")[0].strip()
        return raw.split()[-1] if raw.split() else raw

    def authors(self, field):
        names = [n for n in (self.author(a) for a in re.split(r"\s+and\s+", field or "") if a.strip()) if n]
        if not names:
            return ""
        if len(names) == 1:
            return names[0]
        if names[-1] == "et al.":
            head = names[:-1]
            return (head[0] if len(head) == 1 else ", ".join(head)) + " et al."
        if len(names) <= 20:
            return ", ".join(names[:-1]) + ", & " + names[-1]
        return ", ".join(names[:19]) + ", ... " + names[-1]

    def short(self, field, narrative=False):
        names = [n for n in (self.surname(a) for a in re.split(r"\s+and\s+", field or "") if a.strip()) if n]
        if not names:
            return ""
        if names[-1] == "et al.":
            head = names[:-1]
            return (head[0] if len(head) == 1 else ", ".join(head)) + " et al."
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} {'and' if narrative else '&'} {names[1]}"
        return f"{names[0]} et al."


def year_labels(entries, keys, st):
    """APA: same author string + same year → 2025a, 2025b, ordered by title."""
    groups = defaultdict(list)
    for k in keys:
        e = entries.get(k)
        if e:
            groups[(st.short(e.get("author")), e.get("year", "n.d."))].append(k)
    out = {}
    for (_, y), ks in groups.items():
        if len(ks) == 1:
            out[ks[0]] = y
        else:
            for i, k in enumerate(sorted(ks, key=lambda k: detex(entries[k].get("title", "")).lower())):
                out[k] = f"{y}{chr(97 + i)}"
    return out


def render_entry(e, year, st):
    f = e.fields
    a = st.authors(f.get("author", ""))
    title = detex(f.get("title", "(no title)")).rstrip(".")
    doi, eprint = f.get("doi", "").strip(), f.get("eprint", "").strip()
    pages = detex(f.get("pages", ""))
    out = f"{a} ({year}). " if a else f"({year}). "
    arxid = eprint or (doi.split(":", 1)[1] if doi.lower().startswith("arxiv:") else "")
    t = e.type
    if t == "article":
        out += f"{title}. *{detex(f.get('journal', ''))}*"
        if f.get("volume"):
            out += f", *{f['volume']}*" + (f"({f['number']})" if f.get("number") else "")
        out += (f", {pages}" if pages else "") + "."
    elif t in ("inproceedings", "incollection", "conference"):
        out += f"{title}. In *{detex(f.get('booktitle', ''))}*" + (f" (pp. {pages})" if pages else "") + "."
        if f.get("publisher"):
            out += f" {detex(f['publisher'])}."
    elif t == "techreport":
        out += f"*{title}*" + (f" (Report No. {detex(f['number'])})" if f.get("number") else "") + "."
        if f.get("institution"):
            out += f" {detex(f['institution'])}."
    else:
        if arxid:
            out += f"*{title}* (arXiv:{arxid}). arXiv."
        else:
            out += f"*{title}*."
            for k in ("howpublished", "publisher"):
                if f.get(k):
                    out += f" {detex(f[k])}."
    if doi and not doi.lower().startswith("arxiv:"):
        out += f" https://doi.org/{doi}"
    elif arxid:
        out += f" https://arxiv.org/abs/{arxid}"
    elif f.get("url") and f["url"] not in out:
        out += f" {f['url']}"
    if "DOI-DERIVED" in f.get("note", ""):
        out += " *[Identifier reconstructed, not read from the document.]*"
    if f.get("class", "").strip("{} ") == "M":
        out += " *[Industry source; supports no technical claim." + (f" Retrieved {f['urldate']}.]*" if f.get("urldate") else "]*")
    out = re.sub(r"\s+", " ", out).replace(" .", ".")
    return re.sub(r"\.{2,}", ".", out).strip()


def references(cfg, args):
    ws = WS(cfg)
    if not ws.bib:
        print("no refs.bib — run `survey ledger emit`")
        return 1
    st = Styler(cfg)
    cited = sorted(k for k in ws.paper_keys if k in ws.bib)
    labels = year_labels(ws.bib, cited, st)

    def sortkey(k):
        e = ws.bib[k]
        first = re.split(r"\s+and\s+", e.get("author", "") or e.get("title", ""))[0]
        return (st.surname(first).lower() if first else "", labels[k])
    ch = next((c for c in cfg.chapters if c.role == "references"), None)
    out = cfg.path("paper_dir", f"{ch.stem if ch else '90_references'}.md")
    body = ["# References", "", f"{len(cited)} works, every one cited in the text. APA 7th edition, ordered by "
            "first-author surname.", ""]
    for k in sorted(cited, key=sortkey):
        body += [f"<!-- {k} -->", render_entry(ws.bib[k], labels[k], st), ""]
    out.write_text("\n".join(body) + "\n", encoding="utf-8")
    missing = sorted(ws.paper_keys - set(ws.bib))
    print(f"rendered {len(cited)} works -> {out.relative_to(cfg.ws)}; excluded {len(ws.bib) - len(cited)} uncited")
    if missing:
        print(f"⚠️  {len(missing)} cited keys not in refs.bib: {', '.join(missing[:10])}")
    return 0


def intext_text(cfg, text, entries, labels, st):
    def group(inner):
        ms = list(KEY_RE.finditer(inner))
        cites = []
        for i, m in enumerate(ms):
            k = m.group(1)
            if k not in entries:
                return None                     # a code span, not a citation group
            tail = inner[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(inner)].lstrip(" ;,")
            lm = LOCATOR_RE.match(tail)
            loc = ", ".join(p.strip() for p in (lm.group("sec"), lm.group("page")) if p) if lm else ""
            base = f"{st.short(entries[k].get('author')) or detex(entries[k].get('title', ''))}, {labels.get(k, entries[k].get('year', 'n.d.'))}"
            cites.append(f"{base}, {loc}" if loc else base)
        return "(" + "; ".join(cites) + ")" if cites else None

    text = PAREN_RE.sub(lambda m: (group(m.group(1)) or m.group(0)) if KEY_RE.search(m.group(1)) else m.group(0), text)

    def bare(m):
        k = m.group(1)
        if k not in entries:
            return m.group(0)
        return f"{st.short(entries[k].get('author'), narrative=True) or detex(entries[k].get('title', ''))} ({labels.get(k, entries[k].get('year', 'n.d.'))})"
    return KEY_RE.sub(bare, text)


def intext(cfg, args, write=True):
    ws = WS(cfg)
    st = Styler(cfg)
    labels = year_labels(ws.bib, sorted(ws.paper_keys), st)
    parts = []
    n_in = 0
    for _, p in ws.chapter_files:
        raw = p.read_text(encoding="utf-8")
        n_in += len(KEY_RE.findall(raw))
        parts.append(intext_text(cfg, raw, ws.bib, labels, st))
    text = "\n\n".join(parts) + "\n"
    if write:
        out = cfg.path("paper_dir", "build", "survey_review.md")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out.relative_to(cfg.ws)}; citekey tokens in source {n_in}, "
              f"unresolved backtick spans left {len(KEY_RE.findall(text))} (code spans stay)")
    return text if not write else 0
