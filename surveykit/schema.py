"""Every file format the pipeline exchanges, defined once.

Tools read TSVs by header name, never by column position: the original
check_survey.sh read the ledger with awk $3/$6/$12/$13, a hidden contract that
broke silently whenever a column was added.
"""
import csv
import io
import json
import re
from pathlib import Path

# ---- corpus row (02_corpus_index/rows/*.jsonl → corpus.jsonl) -------------
CORPUS_KEYS = [
    "survey_key", "origin", "origin_key", "source_cluster", "source_md",
    "source_pdf", "year", "venue", "doi", "doi_class", "class", "citable",
    "locus_proposed", "locus_reason", "one_line",
]
DOI_CLASSES = ("stated", "derived", "unresolved", "none")
CITATION_CLASSES = ("P", "A", "T", "M")

# ---- import ledger (90_bib/IMPORT_LEDGER.tsv) ------------------------------
LEDGER_COLS = [
    "origin", "origin_key", "survey_key", "source_cluster", "source_md",
    "locus", "locus_secondary", "decided_by", "decided_on", "doi_class",
    "class", "citable", "reason",
]
# Reason prefixes that record provenance. A merge must never overwrite them:
# on 2026-08-25 five of seven CORR: markers vanished mid-pass in the original
# import_refs.py, taking the guard on six citekey corrections with them.
PROTECTED_PREFIXES = ("CORR:", "SUPERSEDES:", "RENAME:", "ALT-DOI:", "SYNCED",
                      "DOI-UPGRADED:", "DOI UPGRADE")

# ---- claims (10_tracks/<track>/claims.tsv) ---------------------------------
# `split` was missing from the original schema, so a synthesist that judged a
# work to sit equally in two cells had nowhere to say so — GATE 1's 3% doubles
# "were measuring the form, not the reading".
CLAIMS_COLS = ["survey_key", "locus", "locus_secondary", "split", "reason"]

# ---- reviewer-comment dispositions -----------------------------------------
# Six parallel triage agents without a fixed vocabulary produced ~40 spellings.
DISPOSITIONS = ("resolved", "production_defect", "rebuttal", "declined",
                "needs_fix", "needs_review")
COMMENT_CATEGORIES = ("production_defect", "bibliography", "taxonomy_scope",
                      "evidentiary", "overclaim", "tone_clarity", "attribution",
                      "formatting", "other")
DISPOSITION_COLS = ["id", "category", "disposition", "evidence"]

# ---- citekeys ---------------------------------------------------------------
CITEKEY_RE = re.compile(r"^[a-z][a-z0-9]*(19|20)[0-9]{2}[a-z]?(_[a-z0-9_]+)?$")
BACKTICK_KEY_RE = re.compile(r"`([a-z][a-z0-9_]*(?:19|20)[0-9]{2}[a-z0-9_]*)`")
PLACEHOLDER_RE_T = r"\[\[({ns}):([A-Za-z0-9][A-Za-z0-9_.-]*)"


# ---- io helpers -------------------------------------------------------------
def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(path, rows, keys=None):
    with Path(path).open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({k: r.get(k) for k in keys} if keys else r,
                               ensure_ascii=False) + "\n")


def read_tsv(path, cols=None):
    """Read a TSV with a header. A leading '#' on the header line is tolerated
    (the original ledger wrote '#origin\t...'). Headerless files (the original
    claims.tsv) are read with `cols` as the header."""
    path = Path(path)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return []
    first = [h.strip() for h in lines[0].lstrip("#").split("\t")]
    if cols and first[0] != cols[0]:
        header, body = cols, lines
    else:
        header, body = first, lines[1:]
    out = []
    for l in body:
        if l.startswith("#"):
            continue
        vals = l.split("\t")
        vals += [""] * (len(header) - len(vals))
        out.append(dict(zip(header, vals)))
    return out


def write_tsv(path, rows, cols):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_NONE,
                   escapechar="\\")
    w.writerow(cols)
    for r in rows:
        w.writerow([str(r.get(c, "") if r.get(c) is not None else "").replace("\t", " ")
                    for c in cols])
    Path(path).write_text(buf.getvalue(), encoding="utf-8")


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def norm_doi(doi):
    if not doi:
        return None
    d = doi.strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "doi:", "https://dx.doi.org/"):
        if d.startswith(p):
            d = d[len(p):]
    d = d.replace("10.48550/arxiv.", "arxiv:")
    return d or None
