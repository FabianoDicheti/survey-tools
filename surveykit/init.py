"""`survey init` — scaffold a workspace from templates/workspace/.

Two passes, both idempotent (existing files are never overwritten without --force):
  1. no survey.toml yet → write the survey.toml skeleton and stop, so the
     taxonomy, origins and chapters can be declared first;
  2. survey.toml present → create every directory (one per track) and render the
     frozen-document templates with values from the config.
Template variables are `{{name}}`. Blocks generated from config (cells table,
spine, thresholds) are rendered here so the documents never restate a number
by hand.
"""
import re
import shutil
from pathlib import Path

from .config import ConfigError, load
from .util import today

TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "workspace"


def _vars(cfg):
    th, g = cfg.thresholds, cfg.gate1
    cells = "\n".join(f"| {c.id} | {c.name} | `{cfg.layout['tracks_dir']}/{c.dir}/` | {c.test} |" for c in cfg.cells)
    others = "\n".join(f"| {t.id} | {t.name} ({t.kind}; not a cell) | `{cfg.layout['tracks_dir']}/{t.dir}/` | — |"
                       for t in (cfg.crosscut, cfg.context) if t)
    axes = cfg.raw.get("taxonomy", {}).get("axes", [])
    grid = ""
    if len(axes) == 2 and all(len(a.get("poles", [])) == 2 for a in axes):
        a1, a2 = axes
        # each cell declares `at = [<axis-1 pole>, <axis-2 pole>]`; the grid is built from that,
        # never from list order (an implicit order put a cell in the wrong quadrant once)
        raw = {c["id"]: c for c in cfg.raw["taxonomy"]["cells"]}
        pos = {tuple(raw[c.id]["at"]): c for c in cfg.cells if raw[c.id].get("at")}
        cell = lambda p, q: (f"{pos[(p, q)].id} — {pos[(p, q)].name}" if (p, q) in pos else "—")
        if pos:
            grid = (f"| | **{a2['poles'][0]}** | **{a2['poles'][1]}** |\n|---|---|---|\n" +
                    "\n".join(f"| **{p}** | {cell(p, a2['poles'][0])} | {cell(p, a2['poles'][1])} |" for p in a1["poles"]))
        else:
            grid = "(declare `at = [<pole>, <pole>]` on each cell in survey.toml to render the grid)"
    spine = "\n".join(f"{i:>2}. `{ch.stem}` — {ch.role}" + (f" (track {ch.track})" if ch.track else "")
                      for i, ch in enumerate(cfg.chapters))
    thresholds = "\n".join([
        "| threshold | value | checked by |", "|---|---|---|",
        f"| citable works per cell | ≥ {th['min_citable_per_cell']} | `survey verify` §5 |",
        f"| works from {th['recency_year']}+ per cell | ≥ {th['min_recent_per_cell']} | `survey index timeline`, gap audit |",
        f"| crosscut share of placed rows | ≤ {th['crosscut_max_share']:.0%} | §5 |",
        f"| split rate (placed citable, in taxonomy) | ≤ {th['split_max_share']:.0%} | §5a, cold reader |",
        f"| unexplained {cfg.out_label} rows | ≤ {th['unexplained_out_max']} | §5 |",
        f"| context section (P+T)/(P+T+M) | ≥ {th['context_pt_min']:.0%} | §5c |",
        f"| class-M citations in the introduction | ≤ {th['market_max_in_intro']} | §8 |",
        f"| GATE 1 sample size / seed | {g['n']} / {g['seed']} | `survey gate1` |",
        f"| GATE 1 agreement | ≥ {g['agree_pass']:.0%} (fatal < {g['agree_fatal']:.0%}) | `survey gate1 score` |",
        f"| GATE 1 doubles | ≤ {g['doubles_max']:.0%} | `survey gate1 score` |",
        f"| GATE 1 spread per cell | ≥ {g['spread_min']} of {g['n']} | `survey gate1 score` |",
    ])
    seeds = "\n".join(f"| {o['id']} | {cl} | {seed} | |" for o in cfg.origins for cl, seed in o.get("seed", {}).items())
    return {
        "title": cfg.survey.get("title", "Untitled survey"), "topic": cfg.survey.get("topic", ""),
        "owner": cfg.owner, "venue": cfg.survey.get("venue", ""), "language": cfg.survey.get("language", "en"),
        "date": today(), "cells_table": cells + ("\n" + others if others else ""), "grid": grid,
        "spine": spine, "thresholds_table": thresholds, "out": cfg.out_label,
        "cell_ids": ", ".join(cfg.cell_ids), "seed_rows": seeds or "| (origin) | (cluster) | (cell or split(a|b)) | |",
        "crosscut": cfg.crosscut.id if cfg.crosscut else "(none)", "context": cfg.context.id if cfg.context else "(none)",
        **{f"dir_{k}": v for k, v in cfg.layout.items()},
    }


def render(text, v):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(v.get(m.group(1), m.group(0))), text)


def run(ws, args):
    ws = Path(ws).resolve()
    ws.mkdir(parents=True, exist_ok=True)
    toml = ws / "survey.toml"
    if not toml.exists():
        t = (TEMPLATES / "survey.toml").read_text(encoding="utf-8")
        toml.write_text(t.replace("{{title}}", args.title or "Untitled survey").replace("{{date}}", today()), encoding="utf-8")
        print(f"wrote {toml}\nDeclare the taxonomy, origins and chapters in it (skill survey-init), then run `survey init` again.")
        return 0
    try:
        cfg = load(ws)
    except ConfigError as e:
        print(f"config error: {e}")
        return 2
    v = _vars(cfg)
    made, kept = [], []
    for src in sorted(TEMPLATES.rglob("*")):
        rel = src.relative_to(TEMPLATES)
        if src.is_dir() or rel.name == "survey.toml" or rel.name == ".DS_Store":
            continue
        parts = [cfg.layout.get(p[2:-2], p) if p.startswith("{{") else p for p in rel.parts]
        dst = ws.joinpath(*parts)
        if dst.exists() and not args.force:
            kept.append(dst)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in (".md", ".tsv", ".txt"):
            dst.write_text(render(src.read_text(encoding="utf-8"), v), encoding="utf-8")
        else:
            shutil.copy(src, dst)
        made.append(dst)
    for key in ("corpus_dir", "gap_dir", "fetch_dir", "tracks_dir", "positioning_dir", "paper_dir", "bib_dir", "inbox_dir"):
        cfg.path(key).mkdir(parents=True, exist_ok=True)
    for sub in (("corpus_dir", "rows"), ("gap_dir", "gaps"), ("fetch_dir", "candidates"), ("bib_dir", "curated"), ("paper_dir", "build")):
        cfg.path(*sub).mkdir(parents=True, exist_ok=True)
    for t in cfg.tracks:
        d = cfg.path("tracks_dir", t.dir)
        d.mkdir(parents=True, exist_ok=True)
        c = d / "claims.tsv"
        if not c.exists():
            c.write_text("survey_key\tlocus\tlocus_secondary\tsplit\treason\n", encoding="utf-8")
    print(f"created {len(made)} files, kept {len(kept)} existing; {len(cfg.tracks)} track dirs")
    print("Next: freeze 00_brief.md (the request, verbatim) and TAXONOMY.md, then `survey status`.")
    return 0
