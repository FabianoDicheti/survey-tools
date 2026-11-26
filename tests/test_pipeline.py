"""End-to-end over the toy workspace, plus one test per historical defect."""
import json

from conftest import DOCS, claim_all, sv, write_claims
from surveykit import bib, config
from surveykit.ledger import merge_reason, read_ledger, write_ledger
from surveykit.schema import read_jsonl, read_tsv


def test_init_scaffolds_tracks_and_templates(mini):
    assert (mini / "20_positioning/TAXONOMY.md").exists()
    assert "| C1 | hardware |" in (mini / "20_positioning/TAXONOMY.md").read_text()
    for d in ("C1_hw", "C2_os", "C3_rt", "C4_cc", "X_cross"):
        assert (mini / "10_tracks" / d / "claims.tsv").read_text().startswith("survey_key\tlocus")


def test_index_build_and_timeline(mini):
    assert sv(mini, "index", "build") == 0
    assert len(read_jsonl(mini / "02_corpus_index/corpus.jsonl")) == 12
    assert sv(mini, "index", "timeline") == 0
    assert "Density by decade" in (mini / "02_corpus_index/timeline.md").read_text()


def test_index_refuses_duplicate_doi(mini):
    rows = (mini / "02_corpus_index/rows/batch1.jsonl").read_text().splitlines()
    r = json.loads(rows[0])
    r["survey_key"] = "alpha2001_cache_again"              # near-miss key, same DOI
    (mini / "02_corpus_index/rows/batch2.jsonl").write_text(json.dumps(r) + "\n")
    assert sv(mini, "index", "build") == 1
    assert not (mini / "02_corpus_index/corpus.jsonl").exists()


def test_index_refuses_stated_doi_without_doi(mini):
    p = mini / "02_corpus_index/rows/batch1.jsonl"
    rows = [json.loads(l) for l in p.read_text().splitlines()]
    rows[3]["doi_class"] = "stated"                         # classify_doi defect: eprint-only marked stated
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert sv(mini, "index", "build") == 1


def _ledger(mini):
    assert sv(mini, "index", "build") == 0
    assert sv(mini, "ledger", "scan") == 0
    assert sv(mini, "ledger", "propose") == 0


def test_ledger_scan_propose(mini):
    _ledger(mini)
    cfg = config.load(mini)
    rows = read_ledger(cfg)
    assert len(rows) == 12
    assert all(r["locus"] == "?" for r in rows)              # a seed is never a placement
    seeds = {r["survey_key"]: r["reason"] for r in rows}
    assert seeds["alpha2001_cache"] == "SEED:C1"
    assert seeds["gamma2010_swap"] == "SEED:split(C2|C3)"
    assert {r["survey_key"]: r["doi_class"] for r in rows}["eta1999_spm"] == "derived"


def test_emit_refuses_before_synthesis(mini):
    _ledger(mini)
    assert sv(mini, "ledger", "emit") == 1                   # the bibliography is an output of synthesis
    assert not (mini / "90_bib/refs.bib").exists()


def test_merge_agreement_is_crossref_not_dispute(mini):
    _ledger(mini)
    claim_all(mini)
    write_claims(mini, "C2_os", [(k, c, "", "", "r") for k, cl, c, *_ in DOCS if c == "C2"] +
                 [("eps2020_kv", "C3", "", "", "cited here, analysed in C3")])
    assert sv(mini, "ledger", "merge-claims") == 0
    r = {x["survey_key"]: x for x in read_ledger(config.load(mini))}
    assert r["eps2020_kv"]["locus"] == "C3"
    assert "C2" in r["eps2020_kv"]["locus_secondary"]
    assert r["eps2020_kv"]["decided_by"] == "agent:C3_rt"


def test_merge_disagreement_is_dispute(mini):
    _ledger(mini)
    claim_all(mini)
    write_claims(mini, "C1_hw", [(k, c, "", "", "r") for k, cl, c, *_ in DOCS if c == "C1"] +
                 [("eps2020_kv", "C1", "", "", "I say hardware")])
    assert sv(mini, "ledger", "merge-claims") == 1


def test_merge_keeps_corr_marker_in_any_segment(mini):
    """A CORR: marker in the second ' || ' segment was invisible to a prefix check."""
    _ledger(mini)
    cfg = config.load(mini)
    rows = read_ledger(cfg)
    for r in rows:
        if r["survey_key"] == "mu2022_pref":
            r["reason"] = "DOI-UPGRADED: crossref || CORR: cite the version read"
    write_ledger(cfg, rows)
    claim_all(mini)
    assert sv(mini, "ledger", "merge-claims") == 0
    r = {x["survey_key"]: x for x in read_ledger(cfg)}["mu2022_pref"]
    assert "CORR:" in r["reason"] and "DOI-UPGRADED:" in r["reason"] and "reason mu2022_pref" in r["reason"]
    assert merge_reason("CORR: a || x", "new") == "CORR: a || new"


def test_merge_records_split_and_out_is_not_a_gap(mini):
    _ledger(mini)
    claim_all(mini)
    rows = [(k, c, "", "C2|C3" if k == "kappa2018_mix" else "", "r") for k, cl, c, *_ in DOCS if c == "C2"]
    write_claims(mini, "C2_os", rows)
    assert sv(mini, "ledger", "merge-claims") == 0
    r = {x["survey_key"]: x for x in read_ledger(config.load(mini))}
    assert r["kappa2018_mix"]["split"] == "C2|C3"
    assert r["iota2015_blk"]["locus"] == "OUT"


def test_emit_writes_bib_and_guards_corrections(mini):
    _ledger(mini)
    claim_all(mini)
    assert sv(mini, "ledger", "merge-claims") == 0
    assert sv(mini, "ledger", "emit") == 1                   # mu2022_pref is in CORRECTIONS without CORR:
    cfg = config.load(mini)
    rows = read_ledger(cfg)
    for r in rows:
        if r["survey_key"] == "mu2022_pref":
            r["reason"] = "CORR: version differs; cite the one read || " + r["reason"]
    write_ledger(cfg, rows)
    assert sv(mini, "ledger", "emit") == 0
    entries = {e.key: e for e in bib.parse(mini / "90_bib/refs.bib")}
    assert len(entries) == 12 and entries["alpha2001_cache"].get("class") == "P"


def test_gate1_sample_score_separate_verdicts(mini):
    assert sv(mini, "index", "build") == 0
    assert sv(mini, "gate1", "sample") == 0
    seed = read_tsv(mini / "20_positioning/.gate1_seed.tsv")
    assert len(seed) == 8
    # blind reader agrees everywhere and marks one double
    lines = [f"{r['id']}\t{r['seed_cell']}\t{'yes' if i == 0 else 'no'}\tr" for i, r in enumerate(seed)]
    (mini / "20_positioning/gate1_blind.tsv").write_text("\n".join(lines) + "\n")
    assert sv(mini, "gate1", "score") == 0
    v = json.loads((mini / "20_positioning/TAXONOMY_TEST.json").read_text())
    assert v["agreement"]["verdict"] == "PASS" and v["doubles"]["count"] == 1
    # many doubles → partition FAIL, independently of agreement
    lines = [f"{r['id']}\t{r['seed_cell']}\tyes\tr" for r in seed]
    (mini / "20_positioning/gate1_blind.tsv").write_text("\n".join(lines) + "\n")
    assert sv(mini, "gate1", "score") == 1
    v = json.loads((mini / "20_positioning/TAXONOMY_TEST.json").read_text())
    assert v["doubles"]["verdict"] == "FAIL" and v["agreement"]["verdict"] == "PASS"
    assert len((mini / "20_positioning/gate1_history.jsonl").read_text().splitlines()) == 2


def test_gate1_split_seed_parse_not_substring(mini):
    cfg = config.load(mini)
    from surveykit.gate1 import _seed_cells
    assert _seed_cells(cfg, "split(C2|C3)") == {"C2", "C3"}
    assert "C1" not in _seed_cells(cfg, "C10")


def test_candidates_dedupe_inbox_doi_prior_wave(mini):
    assert sv(mini, "index", "build") == 0
    (mini / "91_inbox/wave1").mkdir(parents=True)
    (mini / "91_inbox/wave1/nu2025_fetched.pdf").write_bytes(b"%PDF-1.4 x")
    (mini / "04_fetch/candidates/G-01.md").write_text(
        "# G-01\n\n## Ranked candidates\n\n"
        "### 1. `nu2025_fetched`\n- DOI: 10.9/nu\n- Why: w\n- Class: P\ndoi_status: stated\n\n"
        "### 2. `alpha2001_cache_long`\n- DOI: https://doi.org/10.1/a\n- Why: near-miss key\n- Class: P\ndoi_status: stated\n\n"
        "### 3. `xi2025_new`\n- DOI: 10.9/xi\n- Why: new\n- Class: P\ndoi_status: stated\n\n"
        "## Weird section\n\n### `omicron2025_lost`\n- DOI: 10.9/o\n")
    assert sv(mini, "candidates", "merge", "--wave", "2") == 1   # unrouted section must not vanish silently
    fl = (mini / "04_fetch/wave2/fetch_list.md").read_text()
    to_fetch = fl.split("## To fetch")[1].split("##")[0]
    assert "xi2025_new" in to_fetch and "nu2025_fetched" not in to_fetch and "alpha2001_cache_long" not in to_fetch
    assert "already in inbox" in fl and "DOI 10.1/a" in fl


def test_verify_split_rate_has_denominator(mini):
    _ledger(mini)
    claim_all(mini)
    write_claims(mini, "C2_os", [(k, c, "", "C2|C3", "r") for k, cl, c, *_ in DOCS if c == "C2"])
    sv(mini, "ledger", "merge-claims")
    assert sv(mini, "verify", "--only", "5a") == 1           # 3 of 11 = 27% > 15%


def test_verify_detects_fake_pdf(mini):
    (mini / "91_inbox/wave1").mkdir(parents=True)
    (mini / "91_inbox/wave1/fake1995.pdf").write_bytes(b"<html>404 Not Found</html>")
    assert sv(mini, "verify", "--only", "11") == 1


def test_verify_forbidden_phrase_and_crosscut_grounding(mini):
    _ledger(mini)
    (mini / "40_paper/02_c1.md").write_text("# C1\n\nAs `alpha2001_cache` shows (§2.1).\n")
    (mini / "40_paper/03_cross.md").write_text("# X\n\nUse hardware instead of software, per `beta2005_tlb` (§2.1).\n")
    assert sv(mini, "verify", "--only", "9") == 1


def test_stats_macros_and_build_markdown(mini):
    _ledger(mini)
    claim_all(mini)
    sv(mini, "ledger", "merge-claims")
    cfg = config.load(mini)
    rows = read_ledger(cfg)
    for r in rows:
        if r["survey_key"] == "mu2022_pref":
            r["reason"] = "CORR: x || " + r["reason"]
    write_ledger(cfg, rows)
    assert sv(mini, "ledger", "emit") == 0
    (mini / "40_paper/01_intro.md").write_text("# Intro\n\nWe read {{n:corpus.total}} works (`alpha2001_cache`; `beta2005_tlb`, §3, p. 4).\n")
    assert sv(mini, "cite", "references") == 0
    assert sv(mini, "build", "--target", "markdown") == 0
    out = (mini / "40_paper/build/survey_en.md").read_text()
    assert "We read 12 works" in out
    assert "(Author & Writer, 2001; Author & Writer, 2005, §3, p. 4)" in out
    assert sv(mini, "verify", "--only", "7b", "19") == 0


def test_apa_year_disambiguation():
    from surveykit.cite import Styler, year_labels
    from surveykit.config import Config
    class C:  # minimal cfg stand-in
        guards = {}
    st = Styler(C)
    es = {k: bib.Entry("article", k, {"author": "Ann Author and Bob Writer", "year": "2025", "title": t})
          for k, t in (("author2025_b", "Beta"), ("author2025_a", "Alpha"))}
    lab = year_labels(es, list(es), st)
    assert lab == {"author2025_a": "2025a", "author2025_b": "2025b"}


def test_placeholders_and_status(mini):
    (mini / "01_plan.md").write_text("x [[DECIDE:D-07]] y [[ASK:A-nn]]\n")
    assert sv(mini, "placeholders") == 0
    t = (mini / "PLACEHOLDERS.md").read_text()
    assert "DECIDE:D-07" in t and "A-nn" not in t
    assert sv(mini, "verify", "--only", "15") == 0
    assert sv(mini, "status") == 0


def test_log_appends_newest_first(mini):
    assert sv(mini, "log", "first") == 0
    assert sv(mini, "log", "second", "--body", "b") == 0
    m = (mini / "MEMORY.md").read_text()
    assert m.index("second") < m.index("first")


def test_translate_check_catches_translated_quote(mini):
    src = mini / "external_revision/translate_src"
    out = mini / "external_revision/translate_pt-BR"
    src.mkdir(parents=True)
    out.mkdir(parents=True)
    (src / "01.md").write_text('# T\n\nThe paper says "plans do not compose across concurrent queries" (`a2020_x`).\n')
    (out / "01.md").write_text('# T\n\nO artigo diz "planos não se compõem entre consultas concorrentes" (`a2020_x`).\n')
    assert sv(mini, "translate", "check") == 1
    (out / "01.md").write_text('# T\n\nO artigo diz "plans do not compose across concurrent queries" (`a2020_x`).\n')
    assert sv(mini, "translate", "check") == 0


def test_docx_defect_detector():
    from surveykit.verify import docx_defects
    import tempfile, zipfile, pathlib
    xml = ('<w:document><w:body><w:tbl><w:tblPr><w:tblW w:w="10000" w:type="dxa"/></w:tblPr>'
           '<w:tblGrid><w:gridCol w:w="100"/><w:gridCol w:w="100"/></w:tblGrid></w:tbl></w:body></w:document>')
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "x.docx"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("word/document.xml", xml)
        assert any("gridCol" in m for m in docx_defects(p))
        from surveykit import docxkit
        docxkit.rewrite_part(p, p, "word/document.xml", docxkit.fix_tables)
        assert not any("gridCol" in m for m in docx_defects(p))
