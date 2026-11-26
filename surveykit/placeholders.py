"""`survey placeholders` — regenerate PLACEHOLDERS.md from every typed hole.

A hole marked is found; a hole smoothed over is a defect. Scans *.md except
generated build copies (the original index scanned build/ and listed ids that
no longer existed in any source file).
"""
import re
from collections import defaultdict

from .util import banner

SKIP_PARTS = {"build", ".survey", "node_modules", ".git", "ptbr_chunks_en", "ptbr_chunks_pt"}


def scan(cfg):
    rx = re.compile(r"\[\[(" + "|".join(map(re.escape, cfg.placeholders)) + r"):([A-Za-z0-9][A-Za-z0-9_.|-]*)")
    out = []
    for p in sorted(cfg.ws.rglob("*.md")):
        rel = p.relative_to(cfg.ws)
        if SKIP_PARTS & set(rel.parts) or rel.name == "PLACEHOLDERS.md":
            continue
        for m in rx.finditer(p.read_text(encoding="utf-8", errors="replace")):
            ident = m.group(2)
            if ident.endswith("-nn") or ident in ("id", "nn"):      # template forms in the context card
                continue
            out.append((m.group(1), ident, str(rel)))
    return out


def run(cfg, args):
    items = scan(cfg)
    by = defaultdict(lambda: defaultdict(set))
    for ns, ident, f in items:
        by[ns][ident].add(f)
    L = ["# PLACEHOLDERS — every open hole", "", banner("placeholders"), "",
         f"{sum(len(v) for v in by.values())} distinct ids, {len(items)} occurrences. Namespaces: "
         + ", ".join(cfg.placeholders) + ".", ""]
    for ns in cfg.placeholders:
        if ns not in by:
            continue
        L += [f"## {ns} — {len(by[ns])}", "", "| id | files |", "|---|---|"]
        for ident in sorted(by[ns]):
            L.append(f"| `{ns}:{ident}` | {', '.join(sorted(by[ns][ident]))} |")
        L.append("")
    (cfg.ws / "PLACEHOLDERS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"PLACEHOLDERS.md  {sum(len(v) for v in by.values())} ids: "
          + ", ".join(f"{ns} {len(by[ns])}" for ns in cfg.placeholders if ns in by))
    return 0
