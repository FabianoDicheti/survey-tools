"""Fixtures: a toy 12-document survey built through `survey init`, and an origin workspace."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from surveykit.cli import main  # noqa: E402

TOML = '''
[survey]
title = "Toy survey of cache placement"
topic = "Who decides cache placement."
venue = "TEST"
owner = "Tester"
source_root = ".."

[taxonomy]
axes = [{ id = "time", poles = ["static", "dynamic"] }, { id = "knowledge", poles = ["agnostic", "aware"] }]
cells = [
  { id = "C1", dir = "C1_hw", name = "hardware", at = ["static", "agnostic"], test = "t1" },
  { id = "C2", dir = "C2_os", name = "os", test = "t2" },
  { id = "C3", dir = "C3_rt", name = "runtime", test = "t3" },
  { id = "C4", dir = "C4_cc", name = "compiler", test = "t4" },
]
crosscut = { id = "X", dir = "X_cross", name = "crosscut" }
out = "OUT"

[thresholds]
min_citable_per_cell = 2
split_max_share = 0.15

[thresholds.gate1]
n = 8
seed = 7
spread_min = 1

[[origins]]
id = "prior"
adapter = "bib"
root = "../prior"
bib = ["refs_*.bib"]
cluster_regex = "refs_([A-Z])\\\\.bib"
corrections = "CORRECTIONS.md"
seed = { A = "C1", B = "split(C2|C3)", "*" = "C4" }

[paper]
chapters = [
  { stem = "01_intro", role = "intro" },
  { stem = "02_c1", role = "body", track = "C1" },
  { stem = "03_cross", role = "crosscut", track = "X" },
  { stem = "90_references", role = "references" },
]

[guards]
forbidden_phrases = [{ regex = "hardware instead of software", why = "orthogonal", roles = [] }]
'''

DOCS = [  # key, cluster, cell, year, doi
    ("alpha2001_cache", "A", "C1", 2001, "10.1/a"), ("beta2005_tlb", "A", "C1", 2005, "10.1/b"),
    ("gamma2010_swap", "B", "C2", 2010, "10.1/c"), ("delta2012_pagecache", "B", "C2", 2012, None),
    ("eps2020_kv", "B", "C3", 2020, "10.1/e"), ("zeta2023_expert", "B", "C3", 2023, "10.1/f"),
    ("eta1999_spm", "C", "C4", 1999, "10.1/g"), ("theta2024_plan", "C", "C4", 2024, "10.1/h"),
    ("iota2015_blk", "C", "OUT", 2015, "10.1/i"), ("kappa2018_mix", "B", "C2", 2018, "10.1/k"),
    ("lambda2021_tier", "A", "C1", 2021, "10.1/l"), ("mu2022_pref", "C", "C4", 2022, "10.1/m"),
]


def sv(ws, *args):
    return main(["--ws", str(ws), *args])


@pytest.fixture
def mini(tmp_path):
    prior = tmp_path / "prior"
    prior.mkdir()
    for cl in "ABC":
        entries = []
        for key, c, cell, y, doi in DOCS:
            if c != cl:
                continue
            (prior / f"{key}.md").write_text(f"# {key}\nsummary", encoding="utf-8")
            note = f"Source: {key}.md." + (" DOI-DERIVED from filename." if key == "eta1999_spm" else "")
            d = f"  doi = {{{doi}}},\n" if doi else ""
            entries.append(f"@inproceedings{{{key},\n  author = {{Ann Author and Bob Writer}},\n  title = {{Title of {key}}},\n"
                           f"  booktitle = {{Proc}},\n  year = {{{y}}},\n{d}  note = {{{note}}},\n}}\n")
        (prior / f"refs_{cl}.bib").write_text("\n".join(entries), encoding="utf-8")
    (prior / "CORRECTIONS.md").write_text("| `mu2022_pref` | version differs |\n", encoding="utf-8")
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "survey.toml").write_text(TOML, encoding="utf-8")
    assert sv(ws, "init") == 0
    rows = []
    for key, c, cell, y, doi in DOCS:
        rows.append({"survey_key": key, "origin": "prior", "origin_key": key, "source_cluster": c,
                     "source_md": f"prior/{key}.md", "source_pdf": None, "year": y, "venue": "Proc",
                     "doi": doi, "doi_class": "stated" if doi else "none", "class": "P", "citable": True,
                     "locus_proposed": cell, "locus_reason": "r", "one_line": f"{key} concludes something."})
    (ws / "02_corpus_index/rows/batch1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return ws


def write_claims(ws, track_dir, rows):
    p = ws / "10_tracks" / track_dir / "claims.tsv"
    p.write_text("survey_key\tlocus\tlocus_secondary\tsplit\treason\n" +
                 "".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")


def claim_all(ws):
    by = {}
    for key, c, cell, y, doi in DOCS:
        track = {"C1": "C1_hw", "C2": "C2_os", "C3": "C3_rt", "C4": "C4_cc", "OUT": "C4_cc"}[cell]
        by.setdefault(track, []).append((key, cell, "", "", f"reason {key}"))
    for t, rows in by.items():
        write_claims(ws, t, rows)
