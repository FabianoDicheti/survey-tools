"""`survey build --target …` — assemble and render the paper.

Converts to the target format LAST, from the markdown source of truth: the
reviewed docx of the original survey was a one-off export whose conversion
merged sentences and displaced citations, and a production defect presented to
the reviewer as a scholarship defect (W1). Every docx this tool writes is
inspected for those defects before it is reported as built.

Targets
  sbc-docx       APA in-text (build copy) + SBC reference.docx          → .docx
  sbc-pdf        same markdown → LaTeX (xelatex/lualatex/tectonic)        → .pdf
  latex-generic  pandoc citations → biblatex, article class              → .tex (+ .pdf if an engine exists)
  latex-ieee     natbib, IEEEtran                                        → .tex
  latex-acm      natbib, acmart sigconf                                  → .tex
  markdown       assembled build copy with APA in-text citations         → .md
"""
import re
import shutil
import subprocess
import sys

from . import cite, docxkit, stats
from .verify import docx_defects
from .workspace import WS

KEY = r"[a-z][a-z0-9]*(?:19|20)[0-9]{2}[a-z]?(?:_[a-z0-9_]+)?"
LATEX_CLASS = {"latex-generic": ("article", None, "--biblatex"),
               "latex-ieee": ("IEEEtran", "conference", "--natbib"),
               "latex-acm": ("acmart", "sigconf", "--natbib")}


def to_pandoc_cites(text, keys):
    """`k` → @k; (`a`, §2, p. 4; `b`) → [@a, §2, p. 4; @b]. Only known keys."""
    def paren(m):
        inner = m.group(1)
        if not re.search(rf"`{KEY}`", inner):
            return m.group(0)
        found = re.findall(rf"`({KEY})`", inner)
        if any(k not in keys for k in found):
            return m.group(0)
        inner = re.sub(rf"`({KEY})`", r"@\1", inner)
        return "[" + inner + "]"
    text = re.sub(r"\(([^()]*)\)", paren, text)
    return re.sub(rf"`({KEY})`", lambda m: f"@{m.group(1)}" if m.group(1) in keys else m.group(0), text)


def meta_yaml(cfg, extra=None):
    b, s = cfg.build, cfg.survey
    m = {**{"top": 3.5, "bottom": 2.5, "left": 3.0, "right": 3.0}, **b.get("margins_cm", {})}
    lines = [f'title: "{s.get("title", "")}"', f'lang: {s.get("language", "en")}',
             f'papersize: {b.get("paper_size", "a4")}', f'mainfont: "{b.get("font", "Times New Roman")}"',
             f'fontsize: {b.get("font_size_pt", 12)}pt', "geometry:"] + \
            [f"  - {k}={v}cm" for k, v in m.items()] + ["linestretch: 1.0"]
    if b.get("authors"):
        lines += ["author:"] + [f"  - {a}" for a in b["authors"]]
    for k, v in (extra or {}).items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines) + "\n"


def run(cfg, args):
    if not shutil.which("pandoc"):
        print("pandoc not on PATH", file=sys.stderr)
        return 2
    ws = WS(cfg)
    if not ws.chapter_files:
        print("no chapters to build", file=sys.stderr)
        return 1
    missing = [c.stem for c in cfg.chapters if not cfg.path("paper_dir", f"{c.stem}.md").exists()]
    if missing:
        print(f"⚠️  {len(missing)} chapters not written yet: {', '.join(missing)}")
    out = cfg.path("paper_dir", "build")
    out.mkdir(parents=True, exist_ok=True)
    st = stats.compute(cfg)
    t = args.target
    lang = args.lang or cfg.survey.get("language", "en")
    stem = f"survey_{lang}"
    (out / "stats.json").write_text(__import__("json").dumps(st, indent=2), encoding="utf-8")

    if t in ("sbc-docx", "markdown"):
        src = cite.intext(cfg, args, write=False) if not args.no_intext else \
            "\n\n".join(p.read_text(encoding="utf-8") for _, p in ws.chapter_files)
        src = stats.substitute(cfg, src, st)
        md = out / f"{stem}.md"
        md.write_text(src, encoding="utf-8")
        print(f"assembled {len(ws.chapter_files)} chapters -> {md.relative_to(cfg.ws)}")
        if t == "markdown":
            return 0
        meta = out / "meta.yaml"
        meta.write_text(meta_yaml(cfg), encoding="utf-8")
        ref = out / "sbc-reference.docx"
        docxkit.make_reference(ref, cfg.build)
        docx = out / f"{stem}.docx"
        rc = subprocess.run(["pandoc", str(md), "--metadata-file", str(meta), f"--reference-doc={ref}",
                             "-o", str(docx)]).returncode
        if rc:
            return rc
        docxkit.rewrite_part(docx, docx, "word/document.xml", docxkit.fix_tables)
        defects = docx_defects(docx)
        print(f"wrote {docx.relative_to(cfg.ws)}" + (f"  ⚠️ {len(defects)} defects:" if defects else "  (no production defects)"))
        for d in defects:
            print(f"   - {d}")
        return 1 if defects else 0

    # LaTeX family
    raw = "\n\n".join(p.read_text(encoding="utf-8") for _, p in ws.chapter_files
                      if not (_ and _.role == "references"))      # biblatex/natbib render the list
    src = stats.substitute(cfg, to_pandoc_cites(raw, set(ws.bib)), st)
    md = out / f"{stem}_latex.md"
    md.write_text(src, encoding="utf-8")
    bibfile = out / "refs.bib"
    shutil.copy(cfg.refs_bib, bibfile)
    if t == "sbc-pdf":
        cls, opt, citemode = "article", None, "--biblatex"
    else:
        cls, opt, citemode = LATEX_CLASS[t]
    extra = {"documentclass": cls}
    if opt:
        extra["classoption"] = opt
    if cls != "article":
        extra["geometry"] = "[]"              # venue classes own their geometry
    meta = out / f"meta_{t}.yaml"
    meta.write_text(meta_yaml(cfg, extra).replace("geometry:\n", "geometry:\n" if cls == "article" else "geometry_unused:\n"), encoding="utf-8")
    tex = out / f"{stem}_{t}.tex"
    rc = subprocess.run(["pandoc", str(md), "--metadata-file", str(meta), "-s", citemode,
                         f"--bibliography={bibfile}", "-o", str(tex)]).returncode
    if rc:
        return rc
    print(f"wrote {tex.relative_to(cfg.ws)}")
    engine = next((e for e in ("latexmk", "tectonic", "xelatex", "lualatex") if shutil.which(e)), None)
    if not engine:
        print("no LaTeX engine on PATH (latexmk/tectonic/xelatex/lualatex) — .tex written, PDF not compiled")
        return 0 if t != "sbc-pdf" else 1
    cmd = {"latexmk": ["latexmk", "-xelatex", "-interaction=nonstopmode", tex.name],
           "tectonic": ["tectonic", tex.name]}.get(engine, [engine, "-interaction=nonstopmode", tex.name])
    rc = subprocess.run(cmd, cwd=out).returncode
    print(f"{engine}: {'ok' if rc == 0 else f'exit {rc}'} -> {tex.with_suffix('.pdf').name}")
    return rc
