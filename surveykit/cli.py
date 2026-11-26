"""`survey` — command-line entry point. Every subcommand takes --ws."""
import argparse
import importlib
import os
import sys

from .config import ConfigError, load

# command -> (module, function, configure(parser))
COMMANDS = {}


def cmd(name, module, func, help_):
    def deco(conf):
        COMMANDS[name] = (module, func, help_, conf)
        return conf
    return deco


@cmd("init", "init", "run", "scaffold a new survey workspace from templates")
def _(p):
    p.add_argument("--title", required=False)
    p.add_argument("--force", action="store_true", help="overwrite existing template files")


@cmd("index build", "index", "build", "merge rows/*.jsonl into corpus.jsonl + INDEX.md")
def _(p): pass


@cmd("index timeline", "index", "timeline", "render timeline.md from corpus.jsonl")
def _(p): pass


for _n, _f, _h in [("scan", "scan", "parse origin bibliographies into IMPORT_LEDGER.tsv"),
                   ("propose", "propose", "write seed proposals (locus stays '?')"),
                   ("merge-claims", "merge_claims", "fold track claims.tsv into the ledger"),
                   ("sync-corpus", "sync_corpus", "copy corpus-only rows and OUT verdicts into the ledger")]:
    cmd(f"ledger {_n}", "ledger", _f, _h)(lambda p: None)


@cmd("ledger emit", "ledger", "emit", "refuse unsafe rows, then write refs.bib")
def _(p):
    p.add_argument("--check", action="store_true", help="refusal report only; write nothing")
    p.add_argument("-v", "--verbose", action="store_true")


@cmd("ledger adopt-bib", "ledger", "adopt_bib", "split an existing refs.bib into 90_bib/curated/")
def _(p):
    p.add_argument("file")


@cmd("gate1 sample", "gate1", "sample", "write the blind worksheet and hidden seed key")
def _(p): pass


@cmd("gate1 score", "gate1", "score", "score blind placements; write TAXONOMY_TEST.{md,json}")
def _(p):
    p.add_argument("blind", nargs="?")


@cmd("candidates merge", "candidates", "merge", "merge scout candidate files into the wave fetch list")
def _(p):
    p.add_argument("--wave", type=int, required=True)


@cmd("verify", "verify", "run", "run the mechanical verifier")
def _(p):
    p.add_argument("--build", action="store_true", help="also run build preflight checks")
    p.add_argument("--only", nargs="*", help="run only these check ids")
    p.add_argument("--json", action="store_true", help="write verify.json")
    p.add_argument("--list", action="store_true", help="list checks and exit")


@cmd("stats", "stats", "run", "compute every headline count once -> stats.json")
def _(p): pass


@cmd("placeholders", "placeholders", "run", "regenerate PLACEHOLDERS.md")
def _(p): pass


@cmd("transcriptions", "transcriptions", "run", "classify inbox transcriptions verbatim/paraphrased")
def _(p):
    p.add_argument("--pages", default="1-6")


@cmd("renames", "renames", "run", "apply the citekey rename map where citekeys can appear")
def _(p):
    p.add_argument("--apply", action="store_true")


@cmd("doi resolve", "doi", "resolve", "look up derived/unresolved DOIs; record evidence")
def _(p):
    p.add_argument("--apply", action="store_true", help="write upgrades into the ledger")
    p.add_argument("--keys", nargs="*")
    p.add_argument("--offline", action="store_true", help="use cached responses only")


@cmd("cite references", "cite", "references", "render the APA reference list chapter")
def _(p): pass


@cmd("cite intext", "cite", "intext", "write a build copy with APA in-text citations")
def _(p): pass


@cmd("build", "build", "run", "assemble and render the paper")
def _(p):
    p.add_argument("--target", default="sbc-docx",
                   choices=["sbc-docx", "sbc-pdf", "latex-generic", "latex-ieee", "latex-acm", "markdown"])
    p.add_argument("--lang", default=None)
    p.add_argument("--no-intext", action="store_true", help="keep backtick citekeys")


@cmd("review extract", "review", "extract", "extract docx comments with anchors -> comments.json")
def _(p):
    p.add_argument("docx")


@cmd("review batch", "review", "batch", "split comments into triage batches")
def _(p):
    p.add_argument("--n", type=int, default=6)


@cmd("review merge", "review", "merge", "merge batch dispositions under the fixed vocabulary")
def _(p): pass


@cmd("review fix-docx", "review", "fix_docx", "repair table grid widths in a docx")
def _(p):
    p.add_argument("src")
    p.add_argument("dst")


@cmd("translate chunk", "translate", "chunk", "split chapters into translation chunks")
def _(p):
    p.add_argument("--max-words", type=int, default=2500)


@cmd("translate assemble", "translate", "assemble", "reassemble translated chunks into chapters")
def _(p): pass


@cmd("translate check", "translate", "check", "check translated chunks against the source")
def _(p): pass


@cmd("status", "status", "status", "infer the current stage and next action from artifacts")
def _(p):
    p.add_argument("--json", action="store_true")


@cmd("log", "status", "log", "append a dated State entry to MEMORY.md")
def _(p):
    p.add_argument("title")
    p.add_argument("--body", default="")
    p.add_argument("--body-file")


def build_parser():
    ap = argparse.ArgumentParser(prog="survey", description=__doc__)
    ap.add_argument("--ws", default=os.environ.get("SURVEY_WS", "."), help="workspace dir (default: $SURVEY_WS or .)")
    sub = ap.add_subparsers(dest="group", required=True)
    groups = {}
    for name, (_m, _f, help_, conf) in COMMANDS.items():
        parts = name.split(" ")
        if len(parts) == 1:
            p = sub.add_parser(parts[0], help=help_)
            p.set_defaults(_cmd=name)
            conf(p)
        else:
            g, leaf = parts
            if g not in groups:
                gp = sub.add_parser(g, help=f"{g} commands")
                groups[g] = gp.add_subparsers(dest="leaf", required=True)
            p = groups[g].add_parser(leaf, help=help_)
            p.set_defaults(_cmd=name)
            conf(p)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    module, func, _h, _c = COMMANDS[args._cmd]
    mod = importlib.import_module(f"surveykit.{module}")
    try:
        if args._cmd == "init":
            return mod.run(args.ws, args) or 0
        cfg = load(args.ws)
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    return getattr(mod, func)(cfg, args) or 0


if __name__ == "__main__":
    sys.exit(main())
