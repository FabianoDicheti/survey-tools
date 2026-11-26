"""Read-side helpers over a workspace: chapters, syntheses, citekeys, bib, ledger.

Shared by verify, stats, cite, build and status so every tool sees the same
files the same way (the original scripts each re-derived chapter globs).
"""
import re
from functools import cached_property

from . import bib
from .schema import read_jsonl, read_tsv

KEY_IN_TICKS = re.compile(r"`([a-z][a-z0-9]*(?:19|20)[0-9]{2}[a-z]?(?:_[a-z0-9_]+)?)`")
FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def citekeys(text):
    return set(KEY_IN_TICKS.findall(text))


def front_matter(text):
    m = FM_RE.match(text)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if mm:
            out[mm.group(1)] = mm.group(2).strip()
    return out


class WS:
    def __init__(self, cfg):
        self.cfg = cfg

    # --- paper ---------------------------------------------------------------
    @cached_property
    def chapter_files(self):
        """[(Chapter|None, Path)] for numbered chapter files that exist, in order."""
        pdir = self.cfg.path("paper_dir")
        if self.cfg.chapters:
            out = [(c, pdir / f"{c.stem}.md") for c in self.cfg.chapters]
            return [(c, p) for c, p in out if p.exists()]
        return [(None, p) for p in sorted(pdir.glob("[0-9][0-9]_*.md"))] if pdir.exists() else []

    def chapters_with_role(self, *roles):
        return [(c, p) for c, p in self.chapter_files if c and c.role in roles]

    @cached_property
    def prose_chapters(self):
        """Chapters that carry argument — not the generated reference list."""
        return [(c, p) for c, p in self.chapter_files if not (c and c.role == "references")]

    def text(self, p):
        return p.read_text(encoding="utf-8")

    @cached_property
    def paper_keys(self):
        ks = set()
        for _, p in self.prose_chapters:
            if not (_ and _.role == "appendix"):
                ks |= citekeys(self.text(p))
        return ks

    # --- tracks --------------------------------------------------------------
    def synthesis(self, track):
        p = self.cfg.path("tracks_dir", track.dir, "synthesis.md")
        return p if p.exists() else None

    @cached_property
    def synthesis_text(self):
        out = {}
        for t in self.cfg.tracks:
            for name in ("synthesis.md", "notes.md"):
                p = self.cfg.path("tracks_dir", t.dir, name)
                if p.exists():
                    out[f"{t.dir}/{name}"] = p.read_text(encoding="utf-8")
        return out

    # --- data ----------------------------------------------------------------
    @cached_property
    def ledger(self):
        return read_tsv(self.cfg.ledger) if self.cfg.ledger.exists() else []

    @cached_property
    def ledger_by_key(self):
        return {r["survey_key"]: r for r in self.ledger}

    @cached_property
    def corpus(self):
        return read_jsonl(self.cfg.corpus)

    @cached_property
    def bib(self):
        return {e.key: e for e in bib.parse(self.cfg.refs_bib)} if self.cfg.refs_bib.exists() else {}

    def cls(self, key):
        e = self.bib.get(key)
        if e and e.get("class"):
            return e.get("class").strip("{} ")
        r = self.ledger_by_key.get(key)
        return r.get("class") if r else None

    def derived(self, key):
        e = self.bib.get(key)
        return bool(e and "DOI-DERIVED" in e.get("note", ""))
