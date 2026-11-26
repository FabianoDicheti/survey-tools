"""`survey status` and `survey log`.

status: infer where the pipeline stands from the artifacts alone, so any session
        — including one restarted after a usage limit killed its agents — resumes
        without relying on memory. Prints each stage as done / partial / next /
        blocked, the blockers, and the single next action.
log:    append a dated State entry to MEMORY.md (newest first). The original
        entry point stopped being updated three sessions before the work did.
"""
import json
import re
from pathlib import Path

from .gate1 import _paths as gate1_paths
from .schema import read_jsonl, read_tsv
from .util import today
from .workspace import WS


def _exists(p):
    return Path(p).exists()


def _frozen(p):
    return _exists(p) and bool(re.search(r"\*\*Frozen [0-9]{4}-[0-9]{2}-[0-9]{2}\.", "\n".join(Path(p).read_text(encoding="utf-8").splitlines()[:20])))


def infer(cfg):
    ws = WS(cfg)
    st = []                                     # (id, name, state, detail, next_action)

    def add(i, name, state, detail="", nxt=""):
        st.append({"id": i, "stage": name, "state": state, "detail": detail, "next": nxt})

    # 0 — frozen inputs
    brief, tax = cfg.ws / "00_brief.md", cfg.path("positioning_dir", "TAXONOMY.md")
    need = [p for p in (brief, tax, cfg.path("bib_dir", "CONTEXT_CARD.md")) if not _frozen(p)]
    add("0", "brief + taxonomy frozen", "done" if not need else "next",
        "" if not need else "not frozen: " + ", ".join(p.name for p in need),
        "skill survey-init: freeze the brief verbatim, draft TAXONOMY.md + seed map, kill criteria")
    # 1 — index
    rows = list(cfg.path("corpus_dir", "rows").glob("*.jsonl")) if cfg.path("corpus_dir", "rows").exists() else []
    corpus = read_jsonl(cfg.corpus)
    add("1", "index (corpus.jsonl, timeline)", "done" if corpus else ("partial" if rows else "next"),
        f"{len(rows)} batch files, {len(corpus)} rows", "skill survey-index: dispatch survey-indexer per batch, then `survey index build` + `timeline`")
    # 2 — ledger
    led = ws.ledger
    seeded = sum(1 for r in led if r.get("reason", "").startswith("SEED:"))
    no_origins = not cfg.origins
    add("2", "ledger scan + seed", "done" if led else ("skip" if no_origins else "next"),
        "no [[origins]] — rows enter the ledger via `ledger sync-corpus`" if no_origins and not led else f"{len(led)} rows, {seeded} seeded",
        "`survey ledger scan` then `survey ledger propose`")
    # 2b — gate 1
    _, _, f_md, f_json, f_hist = gate1_paths(cfg)
    if f_json.exists():
        v = json.loads(f_json.read_text())
        stale = cfg.corpus.exists() and cfg.corpus.stat().st_mtime > f_json.stat().st_mtime + 1
        add("2b", "GATE 1 — taxonomy partitions", "blocked" if v["partition"] == "FAIL" else ("next" if stale else "done"),
            f"partition {v['partition']}, overall {v['overall']}" + (" — corpus changed since; re-run" if stale else ""),
            "skill survey-gate: `survey gate1 sample`, survey-blind-placer, `survey gate1 score`")
    elif f_md.exists():
        add("2b", "GATE 1 — taxonomy partitions", "done", "legacy markdown verdict; re-score to get JSON",
            "`survey gate1 score` to regenerate the JSON verdict")
    else:
        add("2b", "GATE 1 — taxonomy partitions", "next" if corpus else "blocked", "never run",
            "skill survey-gate — BEFORE any web search or prose")
    # 3 — gaps
    gr = cfg.path("gap_dir", "gap_report.md")
    briefs = list(cfg.path("gap_dir", "gaps").glob("G-*.md")) if cfg.path("gap_dir", "gaps").exists() else []
    add("3", "gap audit (GATE 2)", "done" if gr.exists() and briefs else "next", f"{len(briefs)} gap briefs",
        "skill survey-gaps: one fresh survey-gap-auditor")
    # 4 — fetch
    cands = list(cfg.path("fetch_dir", "candidates").glob("G-*.md")) if cfg.path("fetch_dir", "candidates").exists() else []
    waves = sorted(cfg.path("fetch_dir").glob("wave*/fetch_list.md")) if cfg.path("fetch_dir").exists() else []
    pending = []
    if waves:
        last = waves[-1].read_text(encoding="utf-8")
        wanted = re.findall(r"^\|\s*\d+\s*\|\s*`([^`]+)`", last, re.M)
        have = {p.stem for p in cfg.path("inbox_dir").rglob("*.pdf")} if cfg.path("inbox_dir").exists() else set()
        pending = [k for k in wanted if k not in have]
    add("4", "fetch list (GATE 3)", "done" if waves and not pending else ("waiting" if pending else "next"),
        f"{len(cands)} scout files, {len(waves)} wave(s)" + (f", {len(pending)} PDFs awaiting {cfg.owner}" if pending else ""),
        "skill survey-fetchlist" if not pending else f"{cfg.owner} drops PDFs into {cfg.layout['inbox_dir']}/<wave>/<citekey>.pdf")
    # 4b — ingest
    inbox = {p.stem for p in cfg.path("inbox_dir").rglob("*.pdf") if "_unlisted" not in p.parts} \
        if cfg.path("inbox_dir").exists() else set()
    keys = {r["survey_key"] for r in corpus}
    unindexed = sorted(inbox - keys)
    add("4b", "ingest fetched wave", "next" if unindexed else "done", f"{len(unindexed)} inbox PDFs not in corpus",
        "skill survey-ingest: file sanity, transcriptions, index rows, gate re-run")
    # 5 — syntheses (cells + context)
    claimed = [t for t in cfg.cells + ([cfg.context] if cfg.context else []) if cfg.path("tracks_dir", t.dir, "claims.tsv").exists()]
    synth = [t for t in cfg.cells + ([cfg.context] if cfg.context else []) if ws.synthesis(t)]
    tot = len(cfg.cells) + (1 if cfg.context else 0)
    add("5", "cell + context syntheses (claims first)", "done" if len(synth) == tot else ("partial" if claimed else "next"),
        f"claims {len(claimed)}/{tot}, syntheses {len(synth)}/{tot}",
        "skill survey-synthesize: survey-synthesist per track in parallel; re-dispatch only tracks without synthesis.md")
    unplaced = sum(1 for r in led if r.get("locus") in ("?", "") and r.get("citable", "yes") == "yes")
    add("5b", "merge-claims + emit refs.bib", "done" if cfg.refs_bib.exists() and not unplaced else "next",
        f"{unplaced} citable rows at '?'", "`survey ledger merge-claims` → curator fixes → `survey ledger emit`")
    if cfg.crosscut:
        add("6", "crosscut synthesis (after all cells)", "done" if ws.synthesis(cfg.crosscut) else "next", "",
            "survey-synthesist on the crosscut track — reads syntheses only")
    scr = cfg.path("positioning_dir", "SYNTHESIS_COLD_READ.md")
    add("6b", "synthesis cold read + contract re-derivation", "done" if scr.exists() else "next", "",
        "survey-cold-reader mode=synthesis; then re-derive CONTRACTS.md's governing argument")
    # 7 — draft
    written = {p.stem for _, p in ws.chapter_files}
    order = [("body", "body"), ("crosscut", "crosscut"), ("gap", "gap"), ("intro/context/method", ("intro", "context", "method")),
             ("conclusion/front", ("conclusion", "front"))]
    for label, roles in order:
        roles = (roles,) if isinstance(roles, str) else roles
        chs = [c.stem for c in cfg.chapters if c.role in roles]
        if not chs:
            continue
        done = [c for c in chs if c in written]
        add(f"7:{label}", f"draft {label}", "done" if len(done) == len(chs) else ("partial" if done else "next"),
            f"{len(done)}/{len(chs)}", f"skill survey-draft — {label} (order: body → crosscut → gap → intro/method LAST)")
    # 8 — verify + cold read
    cr = cfg.path("paper_dir", "COLD_READ.md")
    vj = cfg.ws / ".survey" / "verify.json"
    vpass = json.loads(vj.read_text())["pass"] if vj.exists() else None
    add("8", "verify + paper cold read (GATE 5)", "done" if cr.exists() and vpass else "next",
        f"verify {'PASS' if vpass else ('FAIL' if vpass is False else 'not run')}; cold read {'yes' if cr.exists() else 'no'}",
        "skill survey-verify")
    # 9 — produce
    built = list(cfg.path("paper_dir", "build").glob("*.docx")) + list(cfg.path("paper_dir", "build").glob("*.tex")) \
        if cfg.path("paper_dir", "build").exists() else []
    add("9", "produce", "done" if built else "next", f"{len(built)} artifacts", "skill survey-produce")
    # 10 — review / translate (optional)
    rv = cfg.path("review_dir", "comments.json")
    if rv.exists():
        disp = read_tsv(cfg.path("review_dir", "comments_disposition.tsv"))
        n = len(json.loads(rv.read_text(encoding="utf-8")))
        open_ = sum(1 for r in disp if r.get("disposition") in ("needs_fix", "needs_review", "in_progress"))
        add("10", "external review", "done" if disp and len(disp) >= n and not open_ else "partial",
            f"{len(disp)}/{n} dispositioned, {open_} open", "skill survey-revise")
    return st


def status(cfg, args):
    st = infer(cfg)
    if args.json:
        print(json.dumps(st, indent=1, ensure_ascii=False))
        return 0
    icon = {"skip": "– ", "done": "✅", "partial": "◐ ", "next": "▶ ", "blocked": "🛑", "waiting": "⏳"}
    for s in st:
        print(f"{icon.get(s['state'], '  ')} {s['id']:>14}  {s['stage']:44s} {s['detail']}")
    nxt = next((s for s in st if s["state"] in ("blocked", "waiting", "partial", "next")), None)
    print("\nNEXT: " + (f"[{nxt['id']}] {nxt['next']}" if nxt else "nothing — the pipeline is complete"))
    return 0


def log(cfg, args):
    m = cfg.ws / "MEMORY.md"
    text = m.read_text(encoding="utf-8") if m.exists() else "# MEMORY\n\n## State\n"
    body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else args.body
    d = today()
    n = len(re.findall(rf"^### {d} \(", text, re.M)) + len(re.findall(rf"^### {d} —", text, re.M))
    head = f"### {d} ({chr(97 + n)}) — {args.title}"
    entry = f"{head}\n\n{body.strip()}\n\n" if body.strip() else f"{head}\n\n"
    if "\n## State\n" in text:
        a, b = text.split("\n## State\n", 1)
        text = a + "\n## State\n\n" + entry + b.lstrip("\n")
    else:
        text = text.rstrip() + "\n\n## State\n\n" + entry
    m.write_text(text, encoding="utf-8")
    print(f"logged: {head}")
    return 0
