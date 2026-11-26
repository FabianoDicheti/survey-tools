"""`survey translate chunk|assemble|check` — a translation pass that keeps evidence verifiable.

Rule that governs everything here: **direct quotations stay in the source
language, byte-identical.** They are evidence, not commentary; translating a
quote destroys its verifiability against the cited PDF. Citekeys, system names,
placeholders and code spans stay untouched too.

chunk     split each chapter at H2 boundaries into chunks of ≤ --max-words, so
          one survey-translator agent handles one chunk (long chapters were
          split _A/_B in the original pass).
assemble  join translated chunks back into <paper_dir>/<lang>/<stem>.md.
check     per chunk: quotes and backtick spans preserved, heading/table shape
          preserved, no em-dash (if configured), decimal comma (if configured),
          glossary terms rendered consistently.
"""
import json
import re
from collections import Counter

from .workspace import WS

# opening quote after start/space/bracket and not followed by space; closing quote not after
# space — otherwise the span BETWEEN two quotations pairs up as a false "quote".
QUOTE = re.compile(r'(?:(?<=^)|(?<=[\s(\[—–*]))"(?![\s*])([^"\n]{20,}?)(?<![\s*])"(?=[\s).,;:?!*\]—–]|$)|“([^”\n]{20,}?)”', re.M)
TICK = re.compile(r"`[^`\n]+`")
PLACE = re.compile(r"\[\[[A-Z]+:[^\]\s]+")


def _dirs(cfg):
    t = cfg.translate
    lang = t.get("target", "pt-BR")
    base = cfg.path("review_dir")
    src = cfg.ws / t["src_dir"] if t.get("src_dir") else base / "translate_src"
    out = cfg.ws / t["out_dir"] if t.get("out_dir") else base / f"translate_{lang}"
    return lang, src, out


def chunk(cfg, args):
    ws = WS(cfg)
    lang, src, out = _dirs(cfg)
    src.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for c, p in ws.chapter_files:
        text = p.read_text(encoding="utf-8")
        if c and c.role == "references":           # titles and authors are not translated
            manifest.append({"stem": p.stem, "chunks": [], "copy": True})
            continue
        if len(text.split()) <= args.max_words:
            parts = [text]
        else:
            secs = re.split(r"(?m)^(?=## )", text)
            parts, cur = [], ""
            for s in secs:
                if cur and len((cur + s).split()) > args.max_words:
                    parts.append(cur)
                    cur = s
                else:
                    cur += s
            if cur:
                parts.append(cur)
        names = [f"{p.stem}.md"] if len(parts) == 1 else [f"{p.stem}_{chr(65 + i)}.md" for i in range(len(parts))]
        for n, part in zip(names, parts):
            (src / n).write_text(part, encoding="utf-8")
        manifest.append({"stem": p.stem, "chunks": names})
    (src / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    n = sum(len(m["chunks"]) for m in manifest)
    print(f"{n} chunks -> {src.relative_to(cfg.ws)}; translators write the same names into {out.relative_to(cfg.ws)}")
    return 0


def assemble(cfg, args):
    lang, src, out = _dirs(cfg)
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    dest = cfg.path("paper_dir", lang)
    dest.mkdir(parents=True, exist_ok=True)
    missing = []
    for m in manifest:
        if m.get("copy"):
            (dest / f"{m['stem']}.md").write_text(cfg.path("paper_dir", f"{m['stem']}.md").read_text(encoding="utf-8"), encoding="utf-8")
            continue
        parts = []
        for n in m["chunks"]:
            p = out / n
            if not p.exists():
                missing.append(n)
                continue
            parts.append(p.read_text(encoding="utf-8").rstrip("\n") + "\n")
        if parts and not any(n in missing for n in m["chunks"]):
            (dest / f"{m['stem']}.md").write_text("\n".join(parts), encoding="utf-8")
    print(f"assembled into {dest.relative_to(cfg.ws)}" + (f"; missing chunks: {', '.join(missing)}" if missing else ""))
    return 1 if missing else 0


def glossary(cfg):
    g = cfg.translate.get("glossary")
    if not g or not (cfg.ws / g).exists():
        return []
    rows = []
    for line in (cfg.ws / g).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$", line)
        if m and not set(m.group(1)) <= set("-: ") and m.group(1).upper() != "EN":
            en = re.sub(r"\s*\(.*?\)", "", m.group(1)).strip()
            pt = re.sub(r"\s*\(.*?\)", "", m.group(2)).strip()
            if en and pt and "/" not in en and len(en) > 3:
                rows.append((en.lower(), pt.lower()))
    return rows


def check_pair(cfg, s, t, gl):
    issues = []
    tn = " ".join(t.split())                   # markdown re-wrapping may break a line inside a quote
    for m in QUOTE.finditer(" ".join(s.split())):
        q = m.group(1) or m.group(2)
        if len(q.split()) >= 4 and q not in tn:
            issues.append(("FAIL", f"quotation not preserved verbatim: \"{q[:70]}\""))
    ts, tt = Counter(TICK.findall(s)), Counter(TICK.findall(t))
    if ts != tt:
        lost = list((ts - tt).elements())[:5]
        issues.append(("FAIL", f"backtick spans changed (lost {lost})"))
    if Counter(PLACE.findall(s)) != Counter(PLACE.findall(t)):
        issues.append(("FAIL", "typed placeholders changed"))
    hs, ht = len(re.findall(r"(?m)^#{1,6} ", s)), len(re.findall(r"(?m)^#{1,6} ", t))
    if hs != ht:
        issues.append(("FAIL", f"heading count {hs} → {ht}"))
    rs, rt = len(re.findall(r"(?m)^\|", s)), len(re.findall(r"(?m)^\|", t))
    if rs != rt:
        issues.append(("FAIL", f"table rows {rs} → {rt}"))
    tr = t
    for m in QUOTE.finditer(s):            # a quotation may legitimately contain an em-dash or a decimal point
        tr = tr.replace(m.group(1) or m.group(2), "")
    tr = TICK.sub("", tr)
    if cfg.translate.get("forbid_em_dash") and "—" in tr:
        issues.append(("WARN", f"{tr.count('—')} em-dash(es) in translated prose"))
    if cfg.translate.get("decimal_comma"):
        dots = re.findall(r"(?<![\w.§])\d+\.\d+\s?%", tr)
        if dots:
            issues.append(("WARN", f"decimal point in {len(dots)} percentage(s), e.g. {dots[0]} (use a comma)"))
    sl, tl = s.lower(), t.lower()
    for en, pt in gl:
        if re.search(rf"\b{re.escape(en)}\b", sl) and pt not in tl:
            issues.append(("WARN", f"glossary: '{en}' present in source; '{pt}' absent in translation"))
    return issues


def check(cfg, args):
    lang, src, out = _dirs(cfg)
    gl = glossary(cfg)
    fails = n = 0
    for sp in sorted(src.glob("*.md")):
        tp = out / sp.name
        if not tp.exists():
            print(f"  ----  {sp.name}: not translated yet")
            continue
        n += 1
        issues = check_pair(cfg, sp.read_text(encoding="utf-8"), tp.read_text(encoding="utf-8"), gl)
        if not issues:
            print(f"  PASS  {sp.name}")
        for lvl, msg in issues:
            fails += lvl == "FAIL"
            print(f"  {lvl}  {sp.name}: {msg}")
    print(f"\n{n} chunk pairs checked, {len(gl)} glossary terms, {fails} failures")
    return 1 if fails else 0
