"""`survey transcriptions` — classify each inbox .md as VERBATIM / PARTIAL / PARAPHRASED.

Quote or drop: a synthesist reading a .md instead of the PDF quotes whatever the
.md says. If the .md paraphrased, the result is a quotation that appears in no
paper — the worst defect a survey can ship. (A summary that put quotation marks
around its own paraphrase produced exactly this, and it spread into six
documents including a produced thesis.) So the class is measured, never assumed.

Two measurements, because whole-sentence matching cannot tell a paraphrase from
a two-column PDF that pdftotext reflowed:
  exact   — whole sampled sentences found verbatim (harsh on reflow)
  shingle — any K-word run of the sentence survives; this one decides the class
Requires pdftotext (poppler). Fixes vs the original: an unreadable PDF no longer
crashes the run (3-tuple unpacked as 4), and the declared thresholds are the
ones used.
"""
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from .schema import write_json

VERBATIM_MIN = 0.75
PARAPHRASE_MAX = 0.25
SHINGLE_K = 10
SAMPLE = 40


def norm(t):
    t = unicodedata.normalize("NFKC", t)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), ("­", "")):
        t = t.replace(a, b)
    t = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", t)
    return " ".join(t.split())


def preserved(sent, mtxt, k=SHINGLE_K):
    w = sent.split()
    if len(w) < k:
        return sent in mtxt
    return any(" ".join(w[i:i + k]) in mtxt for i in range(len(w) - k + 1))


def pdf_text(pdf, pages):
    lo, _, hi = pages.partition("-")
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "t.txt"
        r = subprocess.run(["pdftotext", "-f", lo or "1", "-l", hi or lo or "6", str(pdf), str(out)],
                           capture_output=True)
        if r.returncode != 0 or not out.exists():
            return None
        return out.read_text(errors="replace")


def classify(pdf, md, pages="1-6"):
    """Returns dict(cls, exact, n, shingle). cls is UNREADABLE when the PDF has no text."""
    raw = pdf_text(pdf, pages)
    if raw is None:
        return {"cls": "UNREADABLE", "exact": 0, "n": 0, "shingle": 0.0}
    ptxt, mtxt = norm(raw), norm(md.read_text(errors="replace"))
    sents = [s.strip() for s in re.split(r"(?<=[.])\s+", ptxt) if 60 < len(s.strip()) < 200][:SAMPLE]
    if not sents:
        return {"cls": "UNREADABLE", "exact": 0, "n": 0, "shingle": 0.0}
    exact = sum(1 for s in sents if s in mtxt)
    sh = sum(1 for s in sents if preserved(s, mtxt)) / len(sents)
    cls = "VERBATIM" if sh >= VERBATIM_MIN else ("PARAPHRASED" if sh <= PARAPHRASE_MAX else "PARTIAL")
    return {"cls": cls, "exact": exact, "n": len(sents), "shingle": round(sh, 3)}


def run(cfg, args):
    if not shutil.which("pdftotext"):
        print("pdftotext not found — install poppler", file=sys.stderr)
        return 2
    inbox = cfg.path("inbox_dir")
    rows, unpaired = [], []
    for md in sorted(inbox.rglob("*.md")) if inbox.exists() else []:
        if md.name == "README.md":
            continue
        pdf = md.with_suffix(".pdf")
        if not pdf.exists():
            unpaired.append(md)
            continue
        r = classify(pdf, md, args.pages)
        r["file"] = str(md.relative_to(cfg.ws))
        r["declared"] = "Transcription note" in md.read_text(errors="replace")[:2000]
        rows.append(r)
    print(f"{'file':44s} {'exact':>7s} {'shingle':>8s}  class")
    for r in rows:
        print(f"{r['file'][-44:]:44s} {r['exact']:>3}/{r['n']:<3} {r['shingle']:>8.0%}  {r['cls']}"
              f"{'  (declared)' if r['declared'] else ''}")
    counts = {c: sum(1 for r in rows if r["cls"] == c) for c in ("VERBATIM", "PARTIAL", "PARAPHRASED", "UNREADABLE")}
    print("\n" + "  ".join(f"{k} {v}" for k, v in counts.items()))
    print("Quotable from the .md: VERBATIM only. PARTIAL/PARAPHRASED/UNREADABLE: quote from the PDF.")
    for md in unpaired:
        print(f"⚠️  no PDF beside {md.relative_to(cfg.ws)}")
    out = cfg.ws / ".survey" / "transcriptions.json"
    out.parent.mkdir(exist_ok=True)
    write_json(out, rows)
    return 1 if counts["PARAPHRASED"] or counts["PARTIAL"] else 0
