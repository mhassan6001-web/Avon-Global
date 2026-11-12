# ruff: noqa: E501  (XML/PDF literals read better unwrapped)
"""Minimal Word (.docx, WordprocessingML) writer using only the standard library."""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

from ..model import Document

_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""
_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""
NAVY, GOLD, GREY = "0F172B", "C7A86B", "737882"


def _run(text: str, *, bold: bool = False, size: int = 18, color: str | None = None) -> str:
    props = ("<w:b/>" if bold else "") + f'<w:sz w:val="{size}"/>'
    if color:
        props += f'<w:color w:val="{color}"/>'
    return f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>{props}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _p(text: str = "", *, align: str = "left", **kw: object) -> str:
    jc = f'<w:jc w:val="{"right" if align == "right" else "left"}"/>'
    return (
        f'<w:p><w:pPr>{jc}<w:spacing w:after="40"/></w:pPr>{_run(text, **kw) if text else ""}</w:p>'  # type: ignore[arg-type]
    )


def _cell(
    text: str,
    width: int,
    *,
    align: str = "left",
    bold: bool = False,
    fill: str | None = None,
    color: str | None = None,
) -> str:
    shade = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ""
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{shade}</w:tcPr>'
        + _p(text, align=align, bold=bold, color=color)
        + "</w:tc>"
    )


def _table(
    widths: list[int], header: list[tuple[str, str]], rows: list[list[tuple[str, str]]]
) -> str:
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    borders = (
        '<w:tblBorders><w:bottom w:val="single" w:sz="6" w:color="C7A86B"/>'
        '<w:insideH w:val="single" w:sz="2" w:color="E5E1D8"/></w:tblBorders>'
    )
    out = f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/>{borders}</w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
    if header:
        out += (
            "<w:tr>"
            + "".join(
                _cell(t, w, align=a, bold=True, fill=NAVY, color="FFFFFF")
                for (t, a), w in zip(header, widths, strict=True)
            )
            + "</w:tr>"
        )
    for row in rows:
        out += (
            "<w:tr>"
            + "".join(_cell(t, w, align=a) for (t, a), w in zip(row, widths, strict=True))
            + "</w:tr>"
        )
    return out + "</w:tbl>"


def render(doc: Document, generated_at_iso: str) -> bytes:
    body = [
        _p("AVEN GLOBAL", bold=True, size=32, color=NAVY),
        *(_p(line, size=16, color=GREY) for line in doc.issuer),
        _p(),
        _p(doc.kind.upper(), bold=True, size=28, color=NAVY),
        _p(doc.number, size=22, color=GOLD),
        *(_p(b, bold=True, size=18, color="B32E26") for b in doc.banners),
        _p(),
        _p(doc.recipient_title.upper(), bold=True, size=14, color=GREY),
        *(_p(line, bold=i == 0) for i, line in enumerate(doc.recipient)),
        _p(),
        _table([3000, 6000], [], [[(k, "left"), (v, "left")] for k, v in doc.meta]),
        _p(),
    ]
    total = sum(c.width for c in doc.columns)
    widths = [int(9000 * c.width / total) for c in doc.columns]
    body.append(
        _table(
            widths,
            [(c.title, c.align) for c in doc.columns],
            [[(v, c.align) for v, c in zip(r, doc.columns, strict=True)] for r in doc.rows],
        )
    )
    if doc.totals:
        body.append(_p())
        body.append(
            _table(
                [6000, 3000],
                [],
                [[(k, "right"), (v, "right")] for k, v in doc.totals],
            )
        )
    for note in doc.notes:
        body.append(_p(note, size=16, color=GREY))
    body.append(_p())
    for line in doc.footer:
        body.append(_p(line, size=14, color=GREY))
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        + "".join(body)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/>'
        "</w:sectPr></w:body></w:document>"
    )
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{escape(doc.kind)} {escape(doc.number)}</dc:title><dc:creator>AVEN GLOBAL</dc:creator>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{generated_at_iso}</dcterms:created>'
        "</cp:coreProperties>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", xml)
        z.writestr("docProps/core.xml", core)
    return buf.getvalue()
