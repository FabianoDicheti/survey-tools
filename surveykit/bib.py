"""BibTeX parsing and writing, brace-aware.

Field values span lines and nest braces, and a line-oriented parser gets wrong
exactly the entries whose `note` matters — the note carries the only
citekey → document join (`Source: <path>`).
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

YEAR_RE = re.compile(r"(19|20)[0-9]{2}")
FIELD_ORDER = ["author", "title", "booktitle", "journal", "volume", "number", "pages",
               "publisher", "institution", "howpublished", "year", "month", "doi",
               "eprint", "archiveprefix", "url", "urldate", "class", "note"]


@dataclass
class Entry:
    type: str
    key: str
    fields: dict = field(default_factory=dict)

    def get(self, k, default=""):
        return self.fields.get(k, default)


def _match_brace(text, j):
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return k
    return len(text)


def parse_fields(body):
    fields, i = {}, 0
    fre = re.compile(r"(\w+)\s*=\s*")
    while i < len(body):
        m = fre.search(body, i)
        if not m:
            break
        name, j = m.group(1).lower(), m.end()
        while j < len(body) and body[j] in " \t\r\n":
            j += 1
        if j >= len(body):
            break
        if body[j] == "{":
            k = _match_brace(body, j)
            value, i = body[j + 1:k], k + 1
        elif body[j] == '"':
            k = body.find('"', j + 1)
            value, i = body[j + 1:k], k + 1
        else:
            k = j
            while k < len(body) and body[k] not in ",\n":
                k += 1
            value, i = body[j:k], k
        fields[name] = " ".join(value.split())
    return fields


def parse_text(text):
    out, i = [], 0
    while True:
        at = text.find("@", i)
        if at == -1:
            break
        m = re.match(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text[at:])
        if not m or m.group(1).lower() in ("comment", "string", "preamble"):
            i = at + 1
            continue
        k = _match_brace(text, text.find("{", at))
        out.append(Entry(m.group(1).lower(), m.group(2), parse_fields(text[at + m.end():k])))
        i = k + 1
    return out


def parse(path):
    return parse_text(Path(path).read_text(encoding="utf-8", errors="replace"))


def render(e):
    keys = [k for k in FIELD_ORDER if k in e.fields] + \
           sorted(k for k in e.fields if k not in FIELD_ORDER)
    w = max((len(k) for k in keys), default=4)
    lines = [f"@{e.type}{{{e.key},"]
    for k in keys:
        lines.append(f"  {k.ljust(w)} = {{{e.fields[k]}}},")
    lines.append("}")
    return "\n".join(lines)


def write(path, entries, header=""):
    body = "\n\n".join(render(e) for e in entries)
    Path(path).write_text((header + "\n\n" if header else "") + body + "\n", encoding="utf-8")


# ---- helpers shared by ledger / cite ---------------------------------------
def surname(author_field):
    """First author's surname, from either 'Kahn, Gilles' or 'Gilles Kahn'."""
    if not author_field:
        return "unknown"
    first = re.split(r"\s+and\s+", author_field)[0].strip().strip("{}")
    name = first.split(",")[0].strip() if "," in first else (first.split() or ["unknown"])[-1]
    name = re.sub(r"[^A-Za-z]", "", name).lower()
    return name or "unknown"


def propose_key(origin_key, fields):
    """Rebuild a non-conforming key as author-year_topic. Proposal only."""
    year = fields.get("year", "")
    if not YEAR_RE.fullmatch(year or ""):
        m = YEAR_RE.search(origin_key)
        year = m.group(0) if m else ""
    sn = surname(fields.get("author", ""))
    topic = origin_key.lower()
    if year:
        topic = topic.replace(year, "")
    topic = re.sub(r"[^a-z0-9]+", "_", topic).strip("_")
    # whole-token match only — a prefix match turns `deepseek_v3` into `ek_v3`
    if topic == sn or topic.startswith(sn + "_"):
        topic = topic[len(sn):].strip("_")
    topic = topic or "paper"
    return f"{sn}{year}_{topic}" if year else f"{sn}_NEEDS_YEAR_{topic}"


def classify_doi(fields):
    """`stated` requires an identifier actually present. The original marked
    eprint-only entries `stated` with a null DOI; here an eprint counts only if
    it is non-empty."""
    if "DOI-DERIVED" in fields.get("note", ""):
        return "derived"
    if fields.get("doi", "").strip():
        return "stated"
    if fields.get("eprint", "").strip():
        return "stated"
    return "none"


def guess_class(entrytype, fields):
    """Provisional citation class; never silently claims peer review."""
    if entrytype == "misc":
        note = (fields.get("note", "") + fields.get("howpublished", "")).lower()
        return "A" if ("arxiv" in note or fields.get("eprint")) else "T"
    if entrytype == "techreport":
        return "T"
    return "P"
