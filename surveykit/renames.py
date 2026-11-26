"""`survey renames [--apply]` — apply the curator's citekey renames, in citekey positions only.

Why not sed: some keys are also ordinary words in the prose (`guards.prose_word_keys`
in survey.toml — e.g. system names that are also ordinary words). A
word-boundary substitution rewrites sentences, not citations. So only four positions
are touched: backticked keys, front-matter key lists, front-matter scalars, and
column 1 of claims.tsv. Dry run by default.

The map is the `| \`old\` | \`new\` |` table rows in <bib_dir>/CITEKEY_NOTES.md.
"""
import re
import sys

FM_KEYS = ("citekeys_used", "taxonomy_stress", "findings", "most_dangerous",
           "strongest_non_market_support", "unresolved")


def load_map(cfg):
    f = cfg.path("bib_dir", "CITEKEY_NOTES.md")
    rows = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*`([a-z][a-z0-9_]*)`\s*\|\s*`([a-z][a-z0-9_]*)`", line)
            if m and m.group(1) != m.group(2):
                rows[m.group(1)] = m.group(2)
    return rows


def targets(cfg):
    L = cfg.layout
    pats = [f"{L['tracks_dir']}/*/synthesis.md", f"{L['tracks_dir']}/*/notes.md", f"{L['tracks_dir']}/*/README.md",
            f"{L['tracks_dir']}/*/claims.tsv", f"{L['positioning_dir']}/*.md", f"{L['gap_dir']}/*.md",
            f"{L['gap_dir']}/gaps/*.md", f"{L['corpus_dir']}/*.md", f"{L['paper_dir']}/*.md",
            f"{L['bib_dir']}/*.md", "MEMORY.md", "01_plan.md"]
    out = []
    for p in pats:
        out += sorted(cfg.ws.glob(p))
    return [p for p in out if p.name != "CITEKEY_NOTES.md"]


def sub_text(text, mapping, is_claims=False):
    hits = {}
    for old, new in mapping.items():
        text, n = re.subn(r"`" + re.escape(old) + r"`", f"`{new}`", text)
        if n:
            hits[old] = hits.get(old, 0) + n

    def fm_line(m):
        val = m.group(2)
        for old, new in mapping.items():
            val, n = re.subn(r"(?<![a-z0-9_`])" + re.escape(old) + r"(?![a-z0-9_])", new, val)
            if n:
                hits[old] = hits.get(old, 0) + n
        return f"{m.group(1)}:{val}"
    text = re.sub(r"^(" + "|".join(FM_KEYS) + r"):(.*)$", fm_line, text, flags=re.M)
    if is_claims:
        out = []
        for line in text.splitlines():
            c = line.split("\t")
            if c and c[0] in mapping:
                hits[c[0]] = hits.get(c[0], 0) + 1
                c[0] = mapping[c[0]]
            out.append("\t".join(c))
        text = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    return text, hits


def run(cfg, args):
    mapping = load_map(cfg)
    if not mapping:
        print("no rename map in CITEKEY_NOTES.md", file=sys.stderr)
        return 1
    risky = sorted(set(mapping) & set(cfg.guards.get("prose_word_keys", [])))
    print(f"{len(mapping)} renames in the map" + (f"; prose-word keys guarded: {', '.join(risky)}" if risky else ""))
    files = total = 0
    for t in targets(cfg):
        orig = t.read_text(encoding="utf-8")
        new, hits = sub_text(orig, mapping, t.name == "claims.tsv")
        if new != orig:
            files += 1
            total += sum(hits.values())
            if args.apply:
                t.write_text(new, encoding="utf-8")
            print(f"  {'wrote' if args.apply else 'would'} {t.relative_to(cfg.ws)}  ({sum(hits.values())})")
    print(f"\n{'applied' if args.apply else 'DRY RUN'}: {files} files, {total} substitutions. Prose is never modified.")
    return 0
