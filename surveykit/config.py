"""Load a workspace's survey.toml and expose every path, name and threshold.

Nothing else in surveykit may hardcode a cell id, a threshold or a directory.
The original pipeline restated its thresholds in six files although its own
TAXONOMY §5 said no other file may define them; here they live in one place.
"""
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_LAYOUT = {
    "corpus_dir": "02_corpus_index",
    "gap_dir": "03_gap",
    "fetch_dir": "04_fetch",
    "tracks_dir": "10_tracks",
    "positioning_dir": "20_positioning",
    "paper_dir": "40_paper",
    "bib_dir": "90_bib",
    "inbox_dir": "91_inbox",
    "review_dir": "external_revision",
}

DEFAULT_THRESHOLDS = {
    "min_citable_per_cell": 8,
    "recency_year": 2023,
    "min_recent_per_cell": 1,
    "crosscut_max_share": 0.15,
    "split_max_share": 0.15,
    "unexplained_out_max": 5,
    "context_pt_min": 0.50,
    "market_max_in_intro": 2,
}

DEFAULT_GATE1 = {
    "n": 30, "seed": 20260822,
    "agree_pass": 0.70, "agree_fatal": 0.60,
    "doubles_max": 0.20, "spread_min": 3,
}

DEFAULT_PLACEHOLDERS = ["ASK", "MEASURE", "DECIDE", "DRAFT", "FETCH"]


class ConfigError(Exception):
    pass


@dataclass
class Track:
    id: str
    dir: str
    name: str = ""
    kind: str = "cell"          # cell | crosscut | context
    test: str = ""


@dataclass
class Chapter:
    stem: str
    track: str | None = None    # track id whose synthesis feeds it
    role: str = "body"          # front | intro | context | method | body | crosscut | gap | conclusion | references | appendix


@dataclass
class Config:
    ws: Path
    raw: dict
    survey: dict
    layout: dict
    thresholds: dict
    gate1: dict
    cells: list
    crosscut: Track | None
    context: Track | None
    out_label: str
    origins: list
    chapters: list
    placeholders: list
    guards: dict
    eras: list
    build: dict
    review: dict
    translate: dict
    split_pattern: re.Pattern = field(default=re.compile(r"^split\(([^)]*)\)$"))

    # ---- derived --------------------------------------------------------
    @property
    def tracks(self):
        return self.cells + [t for t in (self.crosscut, self.context) if t]

    @property
    def cell_ids(self):
        return [c.id for c in self.cells]

    @property
    def all_locus_ids(self):
        return [t.id for t in self.tracks] + [self.out_label]

    @property
    def owner(self):
        return self.survey.get("owner", "the owner")

    @property
    def source_root(self):
        """Where origin-relative `source_md` paths resolve. The original
        corpus stores paths relative to the repo holding the workspace."""
        return (self.ws / self.survey.get("source_root", "..")).resolve()

    def path(self, key, *parts):
        return self.ws / self.layout[key] / Path(*parts) if parts else self.ws / self.layout[key]

    def track_by_id(self, tid):
        for t in self.tracks:
            if t.id == tid:
                return t
        return None

    def track_for_dir(self, dirname):
        for t in self.tracks:
            if t.dir == dirname:
                return t
        return None

    def parse_locus(self, value):
        """'C2' → ['C2'];  'split(C2|C3)' → ['C2','C3'];  '?'/'' → []."""
        v = (value or "").strip()
        m = self.split_pattern.match(v)
        if m:
            return [x.strip() for x in m.group(1).split("|") if x.strip()]
        if v in ("", "?", "null", "None"):
            return []
        return [v]

    def chapter(self, role):
        return [c for c in self.chapters if c.role == role]

    # files
    @property
    def corpus(self):
        return self.path("corpus_dir", "corpus.jsonl")

    @property
    def ledger(self):
        return self.path("bib_dir", "IMPORT_LEDGER.tsv")

    @property
    def refs_bib(self):
        return self.path("bib_dir", "refs.bib")


def _tracks(tax, key, kind):
    t = tax.get(key)
    if not t:
        return None
    return Track(id=t["id"], dir=t["dir"], name=t.get("name", ""), kind=kind, test=t.get("test", ""))


def load(ws):
    ws = Path(ws).resolve()
    f = ws / "survey.toml"
    if not f.exists():
        raise ConfigError(f"{f} not found — run `survey init` or pass --ws")
    raw = tomllib.loads(f.read_text(encoding="utf-8"))

    tax = raw.get("taxonomy", {})
    cells = [Track(id=c["id"], dir=c["dir"], name=c.get("name", ""), kind="cell", test=c.get("test", ""))
             for c in tax.get("cells", [])]
    if len(cells) < 2:
        raise ConfigError("taxonomy.cells must declare at least two cells")
    axes = tax.get("axes", [])
    for c in tax.get("cells", []):
        if "at" in c:
            if len(c["at"]) != len(axes) or any(p not in a.get("poles", []) for p, a in zip(c["at"], axes)):
                raise ConfigError(f"cell {c['id']}: at={c['at']} does not name one pole per axis {[a.get('poles') for a in axes]}")
    seen_at = [tuple(c["at"]) for c in tax.get("cells", []) if "at" in c]
    if len(set(seen_at)) != len(seen_at):
        raise ConfigError(f"two cells share a grid position: {seen_at}")
    ids = [c.id for c in cells]
    if len(set(ids)) != len(ids):
        raise ConfigError(f"duplicate cell ids: {ids}")

    th = {**DEFAULT_THRESHOLDS, **raw.get("thresholds", {})}
    th.pop("gate1", None)
    gate1 = {**DEFAULT_GATE1, **raw.get("thresholds", {}).get("gate1", {})}

    chapters = [Chapter(stem=c["stem"], track=c.get("track"), role=c.get("role", "body"))
                for c in raw.get("paper", {}).get("chapters", [])]

    return Config(
        ws=ws, raw=raw,
        survey=raw.get("survey", {}),
        layout={**DEFAULT_LAYOUT, **raw.get("layout", {})},
        thresholds=th, gate1=gate1,
        cells=cells,
        crosscut=_tracks(tax, "crosscut", "crosscut"),
        context=_tracks(tax, "context", "context"),
        out_label=tax.get("out", "OUT"),
        origins=raw.get("origins", []),
        chapters=chapters,
        placeholders=raw.get("placeholders", {}).get("namespaces", DEFAULT_PLACEHOLDERS),
        guards=raw.get("guards", {}),
        eras=raw.get("timeline", {}).get("eras", []),
        build=raw.get("build", {}),
        review=raw.get("review", {}),
        translate=raw.get("translate", {}),
    )
