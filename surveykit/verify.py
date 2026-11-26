"""`survey verify` — what a script can check, a script checks.

Ported from the original check_survey.sh (itself extended from check_thesis.sh)
as a registry of independent, config-driven checks. Every threshold comes from
survey.toml. What needs fresh eyes goes to survey-cold-reader; whether the
taxonomy is interesting stays with the owner.
"""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from .gate1 import _paths as gate1_paths
from .schema import read_tsv, write_json
from .util import Report, today
from .workspace import WS, citekeys, front_matter

CHECKS = []
DEFAULT_REQUIRED = ["MEMORY.md", "00_brief.md", "01_plan.md", "PLACEHOLDERS.md",
                    "{positioning_dir}/TAXONOMY.md", "{paper_dir}/CONTRACTS.md",
                    "{bib_dir}/CONTEXT_CARD.md", "{bib_dir}/QUESTIONS.md", "{bib_dir}/SYNTHESIS_SPEC.md",
                    "{bib_dir}/DO_NOT_CITE.md", "{bib_dir}/CITATION_CLASSES.md", "{bib_dir}/SEED_MAP.md|{bib_dir}/LOCUS_MAP.md"]
DEFAULT_FROZEN = ["{positioning_dir}/TAXONOMY.md", "{bib_dir}/CONTEXT_CARD.md", "{bib_dir}/QUESTIONS.md",
                  "{bib_dir}/SYNTHESIS_SPEC.md", "{bib_dir}/DO_NOT_CITE.md", "{bib_dir}/CITATION_CLASSES.md",
                  "{bib_dir}/SEED_MAP.md|{bib_dir}/LOCUS_MAP.md", "00_brief.md"]
FM_KEYS = {
    "cell": "track locus papers_read findings axis_verdicts taxonomy_stress most_dangerous citekeys_used unresolved",
    "crosscut": "track syntheses_read findings axis_table_rows contradictions most_dangerous unresolved",
    "context": "track sources_read class_counts findings strongest_non_market_support staleness_date most_dangerous unresolved",
}
SECTIONS = ["(i)", "(ii)", "(iii)", "(iv)", "(v)", "(vi)"]
QUANTITY = re.compile(r"[0-9]+([.,][0-9]+)?\s*(%|GB|MB|KB|TB|GiB|MiB|KiB|µs|ms|ns|s\b|Gbps|Mbps|GB/s|MMAC|GMAC|×|x speedup)")


def check(cid, title, build_only=False):
    def deco(fn):
        CHECKS.append((cid, title, fn, build_only))
        return fn
    return deco


def _resolve(cfg, spec):
    """'a|b' means either file satisfies the requirement."""
    for alt in spec.split("|"):
        p = cfg.ws / alt.format(**cfg.layout)
        if p.exists():
            return p
    return None


# ------------------------------------------------------------------ 0 shape
@check("0", "Workspace shape")
def c_shape(cfg, ws, R):
    for spec in cfg.raw.get("verify", {}).get("required", DEFAULT_REQUIRED):
        p = _resolve(cfg, spec)
        R.ok(spec.split("|")[0].format(**cfg.layout)) if p else R.fail(f"missing {spec.format(**cfg.layout)}")
    for t in cfg.tracks:
        d = cfg.path("tracks_dir", t.dir)
        R.ok(f"track dir {t.dir}") if d.is_dir() else R.fail(f"missing track dir {t.dir}")


# ------------------------------------------------------------------ 1 frozen
@check("1", "Frozen-doc integrity and taxonomy/track agreement")
def c_frozen(cfg, ws, R):
    for spec in cfg.raw.get("verify", {}).get("frozen", DEFAULT_FROZEN):
        p = _resolve(cfg, spec)
        if not p:
            continue
        head = "\n".join(p.read_text(encoding="utf-8").splitlines()[:20])
        if re.search(r"\*\*Frozen [0-9]{4}-[0-9]{2}-[0-9]{2}\.", head):
            R.ok(f"{p.name} declares a freeze date")
        else:
            R.fail(f"{p.name} has no '**Frozen <date>.**' in its first 20 lines")
    tax = cfg.path("positioning_dir", "TAXONOMY.md")
    if tax.exists():
        text = tax.read_text(encoding="utf-8")
        for t in cfg.tracks:
            R.ok(f"TAXONOMY names {t.dir}") if t.dir in text else R.fail(f"track {t.dir} is not named in TAXONOMY.md")


# ------------------------------------------------------------------ 2 front matter
@check("2", "Synthesis front matter")
def c_frontmatter(cfg, ws, R):
    keys = {**FM_KEYS, **cfg.raw.get("synthesis", {}).get("front_matter", {})}
    for t in cfg.tracks:
        p = ws.synthesis(t)
        if not p:
            R.info(f"{t.dir} — no synthesis yet")
            continue
        fm = front_matter(ws.text(p))
        if fm is None:
            R.fail(f"{t.dir} — no YAML front matter")
            continue
        miss = [k for k in keys[t.kind].split() if k not in fm]
        R.ok(f"{t.dir} — all keys") if not miss else R.fail(f"{t.dir} — missing keys: {' '.join(miss)}")
        if t.kind == "cell":
            n = len([x for x in fm.get("citekeys_used", "").strip("[]").split(",") if x.strip()])
            R.ok(f"{t.dir} — {n} citekeys declared") if n else R.warn(f"{t.dir} — citekeys_used is empty")


# ------------------------------------------------------------------ 3 questions
@check("3", "Question coverage")
def c_questions(cfg, ws, R):
    q = cfg.path("bib_dir", "QUESTIONS.md")
    if not q.exists():
        return R.info("no QUESTIONS.md")
    qtext = q.read_text(encoding="utf-8")
    for t in cfg.tracks:
        ids = sorted(set(re.findall(rf"Q-{re.escape(t.id)}-[0-9]+", qtext)))
        p = ws.synthesis(t)
        if not ids or not p:
            R.info(f"{t.id} — {'no questions' if not ids else 'no synthesis yet'}")
            continue
        s = ws.text(p)
        miss = [i for i in ids if i not in s]
        # warn, not fail: faking the tags would be worse
        R.ok(f"{t.id} — all questions tagged") if not miss else R.warn(f"{t.id} — untagged: {' '.join(miss)}")


# ------------------------------------------------------------------ 4 section order
@check("4", "Mandatory synthesis sections")
def c_sections(cfg, ws, R):
    secs = cfg.raw.get("synthesis", {}).get("sections", SECTIONS)
    for t in cfg.tracks:
        p = ws.synthesis(t)
        if not p:
            continue
        s = ws.text(p)
        miss = [h for h in secs if f"## {h}" not in s]
        R.ok(f"{t.dir} — all sections") if not miss else R.fail(f"{t.dir} — missing headings: {' '.join(miss)}")


# ------------------------------------------------------------------ 5 taxonomy
@check("5", "Taxonomy completeness")
def c_taxonomy(cfg, ws, R):
    th = cfg.thresholds
    L = [r for r in ws.ledger if r.get("citable", "yes") == "yes"]
    if not ws.ledger:
        return R.info("no ledger yet")
    for c in cfg.cell_ids:
        n = sum(1 for r in L if r["locus"] == c)
        if n == 0:
            R.info(f"{c} — 0 placed (nothing claimed yet)")
        elif n < th["min_citable_per_cell"]:
            R.fail(f"{c} — {n} citable rows, minimum {th['min_citable_per_cell']}")
        else:
            R.ok(f"{c} — {n} citable rows")
    placed = [r for r in L if r["locus"] not in ("?", "")]
    if placed and cfg.crosscut:
        n5 = sum(1 for r in placed if r["locus"] == cfg.crosscut.id)
        share = n5 / len(placed)
        msg = f"{cfg.crosscut.id}-by-split {share:.0%} ({n5}/{len(placed)}), ceiling {th['crosscut_max_share']:.0%}"
        R.fail(msg + " — the axis is not a partition") if share > th["crosscut_max_share"] else R.ok(msg)
    # Explained OUT rows are scope facts (no ceiling); unexplained ones are rows nobody adjudicated.
    outs = [r for r in ws.ledger if r["locus"] == cfg.out_label]
    bare = [r for r in outs if r.get("reason", "").strip() in ("", "-")]
    msg = f"{cfg.out_label}: {len(outs)} total, {len(bare)} unexplained (ceiling {th['unexplained_out_max']})"
    R.fail(msg) if len(bare) > th["unexplained_out_max"] else R.ok(msg)


@check("5a", "Split rate (with a denominator)")
def c_split(cfg, ws, R):
    """The original cold-reader rule '≥3 splits = failure' had no denominator and,
    on a corpus of a few hundred works, produced a false taxonomy-failure verdict."""
    placed = [r for r in ws.ledger if r.get("citable", "yes") == "yes" and r["locus"] not in ("?", "", cfg.out_label)]
    if not placed:
        return R.info("nothing placed yet")
    splits = [r for r in placed if r.get("split", "").strip()]
    share = len(splits) / len(placed)
    msg = f"split rate {share:.1%} ({len(splits)}/{len(placed)} placed citable), ceiling {cfg.thresholds['split_max_share']:.0%}"
    R.fail(msg) if share > cfg.thresholds["split_max_share"] else R.ok(msg)


@check("5c", "Context-section class ratio")
def c_context_ratio(cfg, ws, R):
    ch = ws.chapters_with_role("context")
    if not ch or not ws.bib:
        return R.info("context section not written yet")
    keys = citekeys(ws.text(ch[0][1]))
    cls = [ws.cls(k) for k in keys]
    np_, nt, nm = cls.count("P"), cls.count("T"), cls.count("M")
    tot = np_ + nt + nm
    if not tot:
        return R.info("context section has no resolvable citekeys")
    r = (np_ + nt) / tot
    msg = f"context section (P+T)/(P+T+M) = {r:.0%} (P={np_} T={nt} M={nm}), minimum {cfg.thresholds['context_pt_min']:.0%}"
    R.ok(msg) if r >= cfg.thresholds["context_pt_min"] else R.fail(msg)


# ------------------------------------------------------------------ 5b gate 1
@check("5b", "GATE 1 (does the taxonomy partition?)")
def c_gate1(cfg, ws, R):
    _, _, f_md, f_json, _ = gate1_paths(cfg)
    body = [p for c, p in ws.chapter_files if c and c.role == "body"]
    if f_json.exists():
        v = json.loads(f_json.read_text(encoding="utf-8"))
        a, d = v["agreement"], v["doubles"]
        thin = v["spread"]["thin"]
    elif f_md.exists():                       # legacy markdown verdict from the original tool
        t = f_md.read_text(encoding="utf-8")
        ma = re.search(r"agreement \| \*\*([0-9]+)%", t)
        md = re.search(r"doubles[^|]*\| \*\*[0-9]+/[0-9]+ = ([0-9]+)%", t)
        mt = re.search(r"thin cells[^|]*\| \*\*(.*?)\*\*", t)
        if not (ma and md):
            return R.warn(f"could not parse legacy {f_md.name}; re-run `survey gate1 score`")
        g = cfg.gate1
        av, dv = int(ma.group(1)) / 100, int(md.group(1)) / 100
        a = {"value": av, "verdict": "PASS" if av >= g["agree_pass"] else ("FATAL" if av < g["agree_fatal"] else "WARN")}
        d = {"value": dv, "verdict": "PASS" if dv <= g["doubles_max"] else "FAIL"}
        thin = [] if not mt or mt.group(1) == "none" else [x.strip() for x in mt.group(1).split(",")]
    else:
        return R.fail("chapters exist but GATE 1 never ran") if body else R.info("GATE 1 not run yet")
    # three metrics, three verdicts — collapsing them told the reader the taxonomy was broken when it was not
    if d["verdict"] == "FAIL":
        R.fail(f"GATE 1 doubles {d['value']:.0%} — the axis does not partition")
    else:
        R.ok(f"GATE 1 doubles {d['value']:.0%} — the axis partitions")
    {"FATAL": R.fail, "WARN": R.warn, "PASS": R.ok}[a["verdict"]](f"GATE 1 agreement {a['value']:.0%} [{a['verdict']}]")
    R.warn(f"GATE 1 thin cells: {', '.join(thin)} — a corpus gap, not an axis defect") if thin else R.ok("GATE 1 spread: no thin cells")
    corpus_mtime = cfg.corpus.stat().st_mtime if cfg.corpus.exists() else 0
    gate_mtime = (f_json if f_json.exists() else f_md).stat().st_mtime
    if corpus_mtime > gate_mtime + 1:
        R.warn("corpus changed since GATE 1 last ran — re-run it after every fetch wave")


# ------------------------------------------------------------------ 6 traceability
@check("6", "Import traceability")
def c_trace(cfg, ws, R):
    if not ws.bib or not ws.ledger:
        return R.info("no refs.bib or ledger yet")
    orphans = [k for k in ws.bib if k not in ws.ledger_by_key]
    for k in orphans:
        R.fail(f"refs.bib key '{k}' has no ledger row")
    if not orphans:
        R.ok("every refs.bib entry has a ledger row")
    unres = [r for r in ws.ledger if r["source_md"] != "UNJOINED"
             and not (cfg.source_root / r["source_md"]).exists() and not (cfg.ws / r["source_md"]).exists()]
    R.ok("every joined source_md resolves") if not unres else R.fail(
        f"{len(unres)} ledger rows have an unresolvable source_md: " + ", ".join(r["survey_key"] for r in unres[:8]))
    keys = [r["survey_key"] for r in ws.ledger]
    dups = sorted({k for k in keys if keys.count(k) > 1})
    R.ok("survey_key unique") if not dups else R.fail(f"duplicate survey_key: {' '.join(dups)}")
    # a citable=no row needs no cell — forcing one would spend the OUT budget on fiction
    q = [r for r in ws.ledger if r["locus"] in ("?", "") and r.get("citable", "yes") == "yes"]
    R.ok("no citable rows left at locus='?'") if not q else R.fail(f"{len(q)} citable rows still locus='?' while refs.bib exists")


# ------------------------------------------------------------------ 7 citekey chain
@check("7", "Citekey resolution: paper -> refs.bib -> a synthesis")
def c_chain(cfg, ws, R):
    if not ws.chapter_files:
        return R.info("no chapters yet")
    syn = "\n".join(ws.synthesis_text.values())
    prior = cfg.path("positioning_dir", "prior_surveys.md")
    prior_t = prior.read_text(encoding="utf-8") if prior.exists() else ""
    analytic = {p for c, p in ws.chapter_files if c and c.role in ("body", "crosscut", "gap", "conclusion")}
    analytic_keys = set()
    for p in analytic:
        analytic_keys |= citekeys(ws.text(p))
    bad = 0
    for k in sorted(ws.paper_keys):
        if k not in ws.bib:
            R.fail(f"cited but not in refs.bib: {k}")
            bad += 1
        if k in syn:
            continue
        # §3 exceptions: prior surveys (analysed in prior_surveys.md) and OUT scope rows,
        # cited only outside the analytic chapters.
        if k in prior_t and k not in analytic_keys:
            R.warn(f"cited only via prior_surveys.md (method-section exception): {k}")
        elif ws.ledger_by_key.get(k, {}).get("locus") == cfg.out_label and k not in analytic_keys:
            R.warn(f"cited only as an {cfg.out_label} scope row: {k}")
        else:
            R.fail(f"cited but in no synthesis: {k}")
            bad += 1
    if not bad:
        R.ok(f"{len(ws.paper_keys)} citekeys resolve both ways")


@check("7b", "Rendered reference list = citation set")
def c_reflist(cfg, ws, R):
    refs = ws.chapters_with_role("references")
    if not refs or not ws.bib:
        return R.info("reference list not rendered yet")
    listed = citekeys(ws.text(refs[0][1])) | set(re.findall(r"<!--\s*([a-z0-9_]+)\s*-->", ws.text(refs[0][1])))
    extra = sorted(k for k in listed if k in ws.bib and k not in ws.paper_keys)
    for k in extra:
        R.fail(f"reference list includes '{k}', which the paper never cites")
    missing = sorted(k for k in ws.paper_keys if k in ws.bib and k not in listed)
    if missing:
        R.warn(f"{len(missing)} cited keys absent from the rendered list — re-run `survey cite references`")
    if not extra:
        R.ok("rendered reference list checked against the citation set")


# ------------------------------------------------------------------ 8 class M
@check("8", "Class-M segregation")
def c_classm(cfg, ws, R):
    mkeys = sorted(k for k in ws.bib if ws.cls(k) == "M")
    if not mkeys:
        return R.info("no class-M entries")
    mc = cfg.raw.get("classes", {}).get("M", {})
    allowed = set(mc.get("allowed_roles", ["intro", "context"]))
    snap = cfg.ws / mc["snapshot_dir"] if mc.get("snapshot_dir") else None
    v = 0
    for c, p in ws.prose_chapters:
        if c and c.role in allowed:
            continue
        for k in citekeys(ws.text(p)) & set(mkeys):
            R.fail(f"class-M '{k}' cited in {p.name} — allowed only in roles {sorted(allowed)}")
            v += 1
    for t in cfg.cells:
        p = ws.synthesis(t)
        if p:
            for k in set(mkeys) & set(re.findall(r"[a-z0-9_]+", ws.text(p))):
                R.fail(f"class-M '{k}' used in {t.dir} synthesis — cells may not")
                v += 1
    for k in mkeys:
        if not ws.bib[k].get("urldate"):
            R.fail(f"class-M '{k}' has no urldate")
        if snap and not list(snap.glob(f"{k}.*")):
            R.fail(f"class-M '{k}' has no snapshot in {snap.name}/")
    intro = ws.chapters_with_role("intro")
    if intro:
        n1 = len(citekeys(ws.text(intro[0][1])) & set(mkeys))
        cap = cfg.thresholds["market_max_in_intro"]
        R.ok(f"intro has {n1} class-M citations (cap {cap})") if n1 <= cap else R.fail(f"intro has {n1} class-M citations, cap {cap}")
    if not v:
        R.ok(f"{len(mkeys)} class-M keys confined to {sorted(allowed)}")


# ------------------------------------------------------------------ 9 crosscut
@check("9", "Crosscut introduces no evidence; forbidden framings")
def c_crosscut(cfg, ws, R):
    x = ws.chapters_with_role("crosscut")
    body = ws.chapters_with_role("body")
    if x and body:
        bk = set()
        for _, p in body:
            bk |= citekeys(ws.text(p))
        xt = ws.text(x[0][1])
        stray = sorted(citekeys(xt) - bk)
        for k in stray:
            R.fail(f"crosscut cites '{k}', which appears in no body chapter")
        if not stray:
            R.ok("every crosscut citekey is grounded in the body chapters")
        nback = len(re.findall(r"§[0-9]+\.[0-9]+", xt))
        npara = len([b for b in re.split(r"\n\s*\n", xt) if b.strip() and not b.lstrip().startswith("#")])
        (R.ok if nback >= npara else R.warn)(f"{nback} back-references for {npara} paragraphs")
    for fp in cfg.guards.get("forbidden_phrases", []):
        rx = re.compile(fp["regex"], re.I)
        roles = set(fp.get("roles", [])) or None
        for c, p in ws.prose_chapters:
            if roles and not (c and c.role in roles):
                continue
            m = rx.search(ws.text(p))
            if m:
                R.fail(f"{p.name}: forbidden framing '{m.group(0)}' — {fp.get('why', '')}")


# ------------------------------------------------------------------ 10 derived DOI
@check("10", "Derived DOIs may not solely support a quantity")
def c_derived(cfg, ws, R):
    if not ws.bib or not ws.chapter_files:
        return R.info("nothing to check yet")
    v = 0
    for _, p in ws.prose_chapters:
        for line in ws.text(p).splitlines():
            if not QUANTITY.search(line):
                continue
            ks = citekeys(line)
            if ks and all(ws.derived(k) for k in ks):
                R.fail(f"{p.name}: quantity supported only by derived-DOI keys {sorted(ks)}: {line[:90]}")
                v += 1
    if not v:
        R.ok("no quantity rests solely on a derived DOI")


# ------------------------------------------------------------------ 11 pairing
@check("11", "Fetched PDFs have summaries")
def c_pairing(cfg, ws, R):
    n = 0
    for d in [cfg.path("bib_dir", t.id) for t in cfg.tracks] + [cfg.path("inbox_dir")]:
        if not d.is_dir():
            continue
        for p in d.rglob("*.pdf"):
            if p.with_suffix(".md").exists():
                n += 1
            elif d.name != cfg.layout["inbox_dir"]:
                R.fail(f"fetched {p.relative_to(cfg.ws)} has no .md summary")
        for p in d.rglob("*.pdf"):
            if p.stat().st_size < 4096 and b"%PDF" not in p.read_bytes()[:1024]:
                # a 324-byte HTML 404 saved with a .pdf extension once passed for a paper
                R.fail(f"{p.relative_to(cfg.ws)} is not a PDF ({p.stat().st_size} bytes) — check files, not names")
    R.ok(f"{n} pdf/md pairs intact")


# ------------------------------------------------------------------ 12 fetch hygiene
@check("12", "Fetch-list hygiene and inbox naming")
def c_fetch(cfg, ws, R):
    lists = sorted(cfg.path("fetch_dir").glob("wave*/fetch_list.md")) if cfg.path("fetch_dir").exists() else []
    if not lists:
        return R.info("no fetch list yet")
    keys = set()
    for p in lists:
        keys |= citekeys(p.read_text(encoding="utf-8"))
    R.ok(f"{len(keys)} citekeys across {len(lists)} wave(s)")
    inbox = cfg.path("inbox_dir")
    v = 0
    for p in (inbox.rglob("*.pdf") if inbox.exists() else []):
        if "_unlisted" in p.parts:
            continue
        if p.stem not in keys:
            R.fail(f"inbox PDF '{p.relative_to(cfg.ws)}' matches no fetch-list citekey — misnamed drop?")
            v += 1
    if not v:
        R.ok("every inbox PDF matches a fetch-list citekey")


# ------------------------------------------------------------------ 13 blocked
@check("13", "DO_NOT_CITE enforcement")
def c_blocked(cfg, ws, R):
    targets = [p for _, p in ws.prose_chapters] + [s for t in cfg.tracks if (s := ws.synthesis(t))]
    if not targets:
        return R.info("no prose yet")
    v = 0
    for b in cfg.guards.get("blocked", []):
        hits = [p.name for p in targets if b in p.read_text(encoding="utf-8")]
        if hits:
            R.fail(f"blocked source '{b}' referenced in: {' '.join(hits)}")
            v += 1
    if not v:
        R.ok("no blocked source referenced in prose")


# ------------------------------------------------------------------ 14 measured vs cited
@check("14", "Measured-vs-cited discipline")
def c_measured(cfg, ws, R):
    targets = [p for _, p in ws.prose_chapters] + [s for t in cfg.tracks if (s := ws.synthesis(t))]
    if not targets:
        return R.info("no prose yet")
    claim = re.compile(r"\b(we|this survey|the survey) (measured|achieved|sustained|reached|observed)\b", re.I)
    # a negated claim is the discipline working ("no section in this survey measured …")
    neg = re.compile(r"\b(no|not|never|none|cannot|nothing|neither|nor|without)\b[^.]{0,60}"
                     r"(we|this survey|the survey) (measured|achieved|sustained|reached|observed)", re.I)
    v = 0
    for p in targets:
        for line in p.read_text(encoding="utf-8").splitlines():
            if claim.search(line) and not neg.search(line):
                R.fail(f"{p.name}: first-person measurement claim: {line.strip()[:100]}")
                v += 1
    if not v:
        R.ok("no first-person measurement claims")
    attr = re.compile(cfg.guards.get("attribution_regex", r"(reported by|according to|[A-Z][a-z]+ et al)"))
    for n in cfg.guards.get("inherited_numbers", []):
        for p in targets:
            t = p.read_text(encoding="utf-8")
            if n in t and not attr.search(t):
                R.fail(f"{p.name} quotes {n} without attributing whose measurement it was")


# ------------------------------------------------------------------ 15 placeholders
@check("15", "Placeholder index regenerates")
def c_placeholders(cfg, ws, R):
    from .placeholders import scan
    idx = cfg.ws / "PLACEHOLDERS.md"
    if not idx.exists():
        return R.fail("no PLACEHOLDERS.md — run `survey placeholders`")
    text = idx.read_text(encoding="utf-8")
    live = {f"{ns}:{i}" for ns, i, _ in scan(cfg)}
    miss = sorted(x for x in live if x not in text)
    R.ok(f"{len(live)} ids all indexed") if not miss else R.fail(f"not in PLACEHOLDERS.md: {' '.join(miss[:12])} (run `survey placeholders`)")
    stale = sorted(set(re.findall(r"`((?:" + "|".join(cfg.placeholders) + r"):[^`]+)`", text)) - live)
    if stale:
        R.warn(f"PLACEHOLDERS.md lists {len(stale)} ids no longer in any file — regenerate")


# ------------------------------------------------------------------ 16 brief
@check("16", "Brief coverage")
def c_brief(cfg, ws, R):
    b = cfg.ws / "00_brief.md"
    if not b.exists():
        return R.info("no brief")
    need = cfg.raw.get("verify", {}).get("brief_steps", 0)
    n = len(re.findall(r"^\| *[0-9]+ ", b.read_text(encoding="utf-8"), re.M))
    if need:
        R.ok(f"all {n} brief steps mapped") if n >= need else R.fail(f"only {n} of {need} brief steps mapped")
    else:
        R.ok(f"{n} brief steps mapped") if n else R.warn("brief maps no steps to stages")


# ------------------------------------------------------------------ NEW checks
@check("18", "Prose hygiene: internal names and placeholder residue")
def c_hygiene(cfg, ws, R):
    internal = re.compile(r"\b[\w./-]+\.(?:tsv|jsonl|py|sh)\b|\b(?:synthesis|notes|claims|CONTRACTS|MEMORY)\.md\b")
    ph = re.compile(r"\[\[(" + "|".join(cfg.placeholders) + r"):")
    v = 0
    for c, p in ws.prose_chapters:
        if c and c.role == "appendix":
            continue
        t = ws.text(p)
        for m in internal.finditer(t):
            R.warn(f"{p.name}: internal file name in prose: {m.group(0)}")
            v += 1
        n = len(ph.findall(t))
        if n:
            R.warn(f"{p.name}: {n} open placeholder(s) — all must become prose before submission")
    if not v:
        R.ok("no internal file names in prose")


@check("19", "Headline numbers come from stats.json")
def c_stats(cfg, ws, R):
    from .stats import compute, macro_re
    if not ws.chapter_files:
        return R.info("no chapters yet")
    s = compute(cfg)
    unknown = set()
    n = 0
    for _, p in ws.prose_chapters:
        for m in macro_re.finditer(ws.text(p)):
            n += 1
            if m.group(1) not in s:
                unknown.add(m.group(1))
    for k in sorted(unknown):
        R.fail(f"{{{{n:{k}}}}} macro names no statistic (see `survey stats`)")
    if not unknown:
        R.ok(f"{n} number macros resolve") if n else R.warn(
            "no {{n:…}} macros — headline counts typed by hand drift apart (the original paper had three denominators)")


@check("20", "MEMORY State log is current")
def c_memory(cfg, ws, R):
    m = cfg.ws / "MEMORY.md"
    if not m.exists():
        return R.fail("no MEMORY.md")
    dates = re.findall(r"^### ([0-9]{4}-[0-9]{2}-[0-9]{2})", m.read_text(encoding="utf-8"), re.M)
    if not dates:
        return R.warn("MEMORY.md has no dated State entries (`survey log`)")
    last = max(dates)
    import datetime
    newest = max((p.stat().st_mtime for p in cfg.ws.rglob("*.md") if "build" not in p.parts), default=0)
    nd = datetime.date.fromtimestamp(newest).isoformat()
    (R.ok if nd <= last else R.warn)(f"last State entry {last}; newest artifact {nd}"
                                     + ("" if nd <= last else " — log the session (`survey log`)"))


@check("21", "Cold-read log is append-only")
def c_coldread(cfg, ws, R):
    state = cfg.ws / ".survey" / "coldread.json"
    found = False
    rec = json.loads(state.read_text()) if state.exists() else {}
    for name in ("COLD_READ.md",):
        for p in [cfg.path("paper_dir", name), cfg.path("positioning_dir", "SYNTHESIS_COLD_READ.md")]:
            if not p.exists():
                continue
            found = True
            secs = re.split(r"(?m)^(?=## Cold read)", p.read_text(encoding="utf-8"))
            cur = {s.splitlines()[0]: hashlib.sha256(s.encode()).hexdigest() for s in secs if s.startswith("## Cold read")}
            old = rec.get(str(p.relative_to(cfg.ws)), {})
            for h, digest in old.items():
                if h not in cur:
                    R.fail(f"{p.name}: earlier entry '{h}' was removed")
                elif cur[h] != digest:
                    R.fail(f"{p.name}: earlier entry '{h}' was edited")
            rec[str(p.relative_to(cfg.ws))] = cur
            R.ok(f"{p.name}: {len(cur)} entries")
    if found:
        state.parent.mkdir(exist_ok=True)
        state.write_text(json.dumps(rec, indent=1))
    else:
        R.info("no cold read yet")


# ------------------------------------------------------------------ 17 build preflight
@check("17", "Build preflight", build_only=True)
def c_build(cfg, ws, R):
    b = cfg.build
    if not b:
        R.warn("no [build] section in survey.toml")
    for c, p in ws.prose_chapters:
        for img in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", ws.text(p)):
            if not (p.parent / img).exists():
                R.fail(f"{p.name} references missing asset {img}")
    docx = sorted(cfg.path("paper_dir", "build").glob("*.docx")) if cfg.path("paper_dir", "build").exists() else []
    for d in docx:
        if d.name.startswith("reference"):
            continue
        for msg in docx_defects(d):
            R.fail(f"{d.name}: {msg}")
    R.ok(f"assets checked; {len(docx)} docx inspected")


def docx_defects(path):
    """The two production defects that inflated an external review (W1):
    table grids not summing to the table width, and paragraphs merged by the
    converter."""
    out = []
    try:
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    except (KeyError, zipfile.BadZipFile):
        return ["not a readable docx"]
    for i, tbl in enumerate(re.findall(r"<w:tbl>.*?</w:tbl>", xml, re.S), 1):
        tw = re.search(r'<w:tblW w:w="(\d+)" w:type="dxa"', tbl)
        cols = [int(x) for x in re.findall(r'<w:gridCol w:w="(\d+)"', tbl)]
        if tw and cols and abs(sum(cols) - int(tw.group(1))) > len(cols) * 2:
            out.append(f"table {i}: gridCol sum {sum(cols)} ≠ tblW {tw.group(1)}")
        if cols and max(cols) <= 200:
            out.append(f"table {i}: column widths ≤200 twips — renders as an empty table")
    for m in re.finditer(r"CITATION\s+\S+\s+\\m", xml):
        out.append("merged Word CITATION field (\\m) — check the citation it renders")
        break
    txt = re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", xml))
    merged = re.findall(r"[a-z]{3,}\.[A-Z][a-z]{2,}\s", txt)
    if len(merged) > 3:
        out.append(f"{len(merged)} sentence joins without a space (merged paragraphs?) e.g. {merged[0]!r}")
    return out


# ------------------------------------------------------------------ runner
def run(cfg, args):
    if args.list:
        for cid, title, _, bo in CHECKS:
            print(f"{cid:>4}  {title}{'  (--build)' if bo else ''}")
        return 0
    ws = WS(cfg)
    total, results = 0, {}
    for cid, title, fn, build_only in sorted(CHECKS, key=lambda c: _order(c[0])):
        if args.only and cid not in args.only:
            continue
        if build_only and not args.build:
            continue
        R = Report()
        print(f"\n== {cid}. {title} ==")
        try:
            fn(cfg, ws, R)
        except Exception as e:                    # a crashing check is a failing check
            R.fail(f"check crashed: {type(e).__name__}: {e}")
        R.print()
        total |= R.rc
        results[cid] = {"title": title, "fails": R.fails, "warns": R.warns,
                        "lines": [{"level": k.strip() or "INFO", "msg": m} for k, m in R.lines]}
    print("\n== Not checked here, by design ==")
    print(f"  - whether the taxonomy is INTERESTING          -> {cfg.owner}")
    print("  - whether any single placement is RIGHT        -> survey-synthesist, then the cold reader")
    print("  - whether the argument holds                   -> survey-cold-reader")
    print("  - the arithmetic inside quoted passages        -> by hand")
    print("\n" + ("PASS" if not total else "FAIL"))
    if args.json:
        out = cfg.ws / ".survey" / "verify.json"
        out.parent.mkdir(exist_ok=True)
        write_json(out, {"date": today(), "pass": not total, "checks": results})
        print(f"machine report -> {out}")
    return total


def _order(cid):
    m = re.match(r"(\d+)([a-z]?)", cid)
    return (int(m.group(1)), m.group(2))
