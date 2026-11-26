"""Stdlib-only .docx surgery: SBC reference document, table-grid repair.

A .docx is a zip of XML parts. Everything here edits those parts with
ElementTree so the toolkit needs no python-docx.
"""
import re
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
for p, u in {"w": W, "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
             "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
             "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
             "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
             "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
             "w14": "http://schemas.microsoft.com/office/word/2010/wordml"}.items():
    ET.register_namespace(p, u)
q = lambda tag: f"{{{W}}}{tag}"
CM = 567          # twips per cm
JC = {"left": "left", "center": "center", "justify": "both"}


def rewrite_part(src, dst, part, fn):
    """Copy a docx, transforming one XML part with fn(bytes) -> bytes."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d) / "out.docx"
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == part:
                    data = fn(data)
                zout.writestr(item, data)
        shutil.copy(tmp, dst)


def _dump(root):
    body = ET.tostring(root, encoding="unicode")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + body).encode("utf-8")


def _child(el, tag, first=False):
    c = el.find(q(tag))
    if c is None:
        c = ET.Element(q(tag))
        if first:
            el.insert(0, c)
        else:
            el.append(c)
    return c


def _style(root, sid, name=None, kind="paragraph"):
    for s in root.findall("w:style", NS):
        if s.get(q("styleId")) == sid:
            return s
    s = ET.SubElement(root, q("style"), {q("type"): kind, q("styleId"): sid})
    ET.SubElement(s, q("name"), {q("val"): name or sid})
    return s


def _apply(s, font=None, size=None, bold=None, italic=None, align=None, before=None, after=None,
           first=None, left=None, right=None, color=None):
    ppr, rpr = _child(s, "pPr"), _child(s, "rPr")
    if font:
        rf = _child(rpr, "rFonts", first=True)
        for slot in ("ascii", "hAnsi", "cs", "eastAsia"):     # force every script slot
            rf.set(q(slot), font)
        for k in ("asciiTheme", "hAnsiTheme", "cstheme", "eastAsiaTheme"):
            rf.attrib.pop(q(k), None)
    if size:
        _child(rpr, "sz").set(q("val"), str(int(size * 2)))
        _child(rpr, "szCs").set(q("val"), str(int(size * 2)))
    for tag, v in (("b", bold), ("i", italic)):
        if v is not None:
            _child(rpr, tag).set(q("val"), "1" if v else "0")
    if color:
        _child(rpr, "color").set(q("val"), color)
    if align:
        _child(ppr, "jc").set(q("val"), JC[align])
    if before is not None or after is not None:
        sp = _child(ppr, "spacing")
        if before is not None:
            sp.set(q("before"), str(int(before * 20)))
        if after is not None:
            sp.set(q("after"), str(int(after * 20)))
        sp.set(q("line"), "240")
        sp.set(q("lineRule"), "auto")
    if any(v is not None for v in (first, left, right)):
        ind = _child(ppr, "ind")
        if first is not None:
            ind.set(q("firstLine"), str(int(first * CM)))
        if left is not None:
            ind.set(q("left"), str(int(left * CM)))
        if right is not None:
            ind.set(q("right"), str(int(right * CM)))


def sbc_styles(xml, font="Times New Roman", size=12):
    root = ET.fromstring(xml)
    body = dict(font=font, size=size, align="justify", before=0, after=6)
    _apply(_style(root, "Normal"), first=1.25, **body)
    for sid in ("BodyText", "FirstParagraph", "Compact"):
        _apply(_style(root, sid), first=0 if sid != "BodyText" else 1.25, **body)
    _apply(_style(root, "Title"), font=font, size=16, bold=True, align="center", before=0, after=12, first=0, color="000000")
    for sid in ("Subtitle", "Author", "Date"):
        _apply(_style(root, sid), font=font, size=size, bold=False, italic=False, align="center", before=0, after=6, first=0)
    for n in range(1, 7):
        _apply(_style(root, f"Heading{n}"), font=font, size=size, bold=n <= 3, italic=n > 3, align="left",
               before=18 if n == 1 else 12, after=6, first=0, left=0, color="000000")
    _apply(_style(root, "Abstract"), font=font, size=size, italic=True, align="justify", before=6, after=6,
           first=0, left=0.8, right=0.8)
    _apply(_style(root, "BlockText"), font=font, size=size, align="justify", before=6, after=6, first=0, left=0.8, right=0.8)
    for sid in ("TableCaption", "ImageCaption", "Caption"):
        _apply(_style(root, sid), font=font, size=10, italic=True, align="center", before=6, after=6, first=0)
    _apply(_style(root, "FootnoteText"), font=font, size=10)
    _apply(_style(root, "SourceCode"), font="Courier New", size=10, align="left", first=0, left=0.5)
    dd = root.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
    if dd is not None:
        rf = _child(dd, "rFonts", first=True)
        for slot in ("ascii", "hAnsi", "cs", "eastAsia"):
            rf.set(q(slot), font)
        for k in ("asciiTheme", "hAnsiTheme", "cstheme", "eastAsiaTheme"):
            rf.attrib.pop(q(k), None)
    return _dump(root)


def page_geometry(xml, margins, paper="a4"):
    root = ET.fromstring(xml)
    w, h = (21.0, 29.7) if paper.lower() == "a4" else (21.59, 27.94)
    for sp in root.iter(q("sectPr")):
        sz = _child(sp, "pgSz")
        sz.set(q("w"), str(int(w * CM)))
        sz.set(q("h"), str(int(h * CM)))
        mg = _child(sp, "pgMar")
        for k in ("top", "bottom", "left", "right"):
            mg.set(q(k), str(int(margins[k] * CM)))
        for k, v in (("header", "708"), ("footer", "708"), ("gutter", "0")):
            mg.set(q(k), mg.get(q(k), v))
    return _dump(root)


def make_reference(dst, build):
    """SBC "Instruções para autores": A4, TNR 12, margins 3.5/2.5/3.0/3.0 cm,
    title 16pt bold centred, abstract indented 0.8 cm — values from [build]."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "wb") as f:
        subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"], stdout=f, check=True)
    font, size = build.get("font", "Times New Roman"), build.get("font_size_pt", 12)
    margins = {**{"top": 3.5, "bottom": 2.5, "left": 3.0, "right": 3.0}, **build.get("margins_cm", {})}
    rewrite_part(dst, dst, "word/styles.xml", lambda x: sbc_styles(x, font, size))
    rewrite_part(dst, dst, "word/document.xml", lambda x: page_geometry(x, margins, build.get("paper_size", "a4")))
    return dst


def fix_tables(xml_bytes):
    """Reset each table's gridCol widths to an even split of its tblW (dxa), or of
    the text width when tblW is a percentage. The reviewed export had all 14
    tables at 100 twips — the 'empty' Notation section was fully populated."""
    xml = xml_bytes.decode("utf-8")
    n = 0

    def fix(m):
        nonlocal n
        tbl = m.group(0)
        cols = re.findall(r'<w:gridCol w:w="(\d+)"\s*/>', tbl)
        if not cols:
            return tbl
        tw = re.search(r'<w:tblW w:w="(\d+)" w:type="dxa"', tbl)
        total = int(tw.group(1)) if tw and int(tw.group(1)) > 500 else 8500
        if abs(sum(map(int, cols)) - total) <= len(cols) * 2 and min(map(int, cols)) > 200:
            return tbl
        each = total // len(cols)
        n += 1
        return re.sub(r'<w:gridCol w:w="\d+"\s*/>', f'<w:gridCol w:w="{each}"/>', tbl)
    out = re.sub(r"<w:tbl>.*?</w:tbl>", fix, xml, flags=re.S)
    fix_tables.count = n
    return out.encode("utf-8")
