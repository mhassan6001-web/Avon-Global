# ruff: noqa: E501  (XML/PDF literals read better unwrapped)
"""Minimal PDF 1.4 writer: A4 pages, Helvetica / Helvetica-Bold (standard
Type 1 fonts, WinAnsi encoding), text, lines and filled rectangles."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from ..model import Document

A4 = (595.28, 841.89)
_HELV = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278] + [556] * 10 + [
    278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556,
    833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333,
    500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
]  # fmt: skip
_BOLD = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278] + [556] * 10 + [
    333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611,
    833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389,
    556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584,
]  # fmt: skip
FONTS = {"F1": _HELV, "F2": _BOLD}

# Brand colours (RGB 0-1): midnight navy and champagne gold.
NAVY = (0.06, 0.09, 0.17)
GOLD = (0.78, 0.66, 0.42)
GREY = (0.45, 0.47, 0.52)
LIGHT = (0.95, 0.94, 0.91)


ASSETS = Path(__file__).resolve().parent.parent / "assets"
WHITE = (1.0, 1.0, 1.0)


def jpeg_size(data: bytes) -> tuple[int, int]:
    """Width and height from a baseline or progressive JPEG's SOF marker."""
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack(">HH", data[i + 5 : i + 9])
            return width, height
        i += 2 + length
    raise ValueError("not a JPEG image")


@lru_cache(maxsize=4)
def asset(name: str) -> bytes:
    return (ASSETS / name).read_bytes()


def text_width(text: str, size: float, font: str = "F1") -> float:
    widths = FONTS[font]
    total = 0
    for ch in text:
        code = ord(ch)
        total += widths[code - 32] if 32 <= code <= 126 else 556
    return total * size / 1000


def _esc(text: str) -> bytes:
    raw = text.encode("cp1252", "replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


@dataclass
class Canvas:
    pages: list[list[bytes]] = field(default_factory=lambda: [[]])
    images: dict[str, bytes] = field(default_factory=dict)  # name -> JPEG bytes

    @property
    def ops(self) -> list[bytes]:
        return self.pages[-1]

    def new_page(self) -> None:
        self.pages.append([])

    def text(
        self,
        x: float,
        y: float,
        s: str,
        size: float = 9,
        font: str = "F1",
        align: str = "left",
        color: tuple[float, float, float] = NAVY,
    ) -> None:
        if align == "right":
            x -= text_width(s, size, font)
        r, g, b = color
        self.ops.append(
            b"BT %.3f %.3f %.3f rg /%s %.1f Tf %.2f %.2f Td ("
            % (r, g, b, font.encode(), size, x, y)
            + _esc(s)
            + b") Tj ET"
        )

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: tuple[float, float, float] = GOLD,
        width: float = 0.6,
    ) -> None:
        r, g, b = color
        self.ops.append(
            b"%.3f %.3f %.3f RG %.2f w %.2f %.2f m %.2f %.2f l S" % (r, g, b, width, x1, y1, x2, y2)
        )

    def rect(
        self, x: float, y: float, w: float, h: float, color: tuple[float, float, float] = LIGHT
    ) -> None:
        r, g, b = color
        self.ops.append(b"%.3f %.3f %.3f rg %.2f %.2f %.2f %.2f re f" % (r, g, b, x, y, w, h))

    def image(self, name: str, jpeg: bytes, x: float, y: float, w: float, h: float) -> None:
        """Draw a JPEG (embedded once per document, DCTDecode)."""
        self.images.setdefault(name, jpeg)
        self.ops.append(b"q %.2f 0 0 %.2f %.2f %.2f cm /%s Do Q" % (w, h, x, y, name.encode()))

    def output(self) -> bytes:
        objects: list[bytes] = []
        n_pages = len(self.pages)
        names = list(self.images)
        first_page = 5 + len(names)
        # 1 catalog, 2 pages, 3 F1, 4 F2, images, then (page, content) pairs.
        kids = " ".join(f"{first_page + 2 * i} 0 R" for i in range(n_pages)).encode()
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>" % n_pages)
        for name in (b"Helvetica", b"Helvetica-Bold"):
            objects.append(
                b"<< /Type /Font /Subtype /Type1 /BaseFont /"
                + name
                + b" /Encoding /WinAnsiEncoding >>"
            )
        for image_name in names:
            data = self.images[image_name]
            width, height = jpeg_size(data)
            objects.append(
                b"<< /Type /XObject /Subtype /Image /Width %d /Height %d " % (width, height)
                + b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                + b"/Length %d >>\nstream\n" % len(data)
                + data
                + b"\nendstream"
            )
        xobjects = b" ".join(b"/%s %d 0 R" % (n.encode(), 5 + k) for k, n in enumerate(names))
        for i, ops in enumerate(self.pages):
            content = zlib.compress(b"\n".join(ops))
            objects.append(
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] " % A4
                + b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> /XObject << "
                + xobjects
                + b" >> >> /Contents %d 0 R >>" % (first_page + 1 + 2 * i)
            )
            objects.append(
                b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(content)
                + content
                + b"\nendstream"
            )
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for num, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % num + body + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
        for off in offsets:
            out += b"%010d 00000 n \n" % off
        out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            len(objects) + 1,
            xref,
        )
        return bytes(out)


def _wrap(text: str, width: float, size: float, font: str = "F1") -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if text_width(trial, size, font) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def render(doc: Document) -> bytes:
    c = Canvas()
    w, h = A4
    left, right, bottom = 48.0, w - 48.0, 60.0

    banner = asset("letterhead-banner.jpg")
    bw, bh = jpeg_size(banner)
    band = w * bh / bw  # full-width letterhead band, aspect preserved

    def header() -> float:
        c.image("Logo", banner, 0, h - band, w, band)
        mid = h - band / 2
        c.text(right, mid + 8, doc.kind.upper(), 17, "F2", "right", WHITE)
        c.text(right, mid - 10, doc.number, 11, "F1", "right", GOLD)
        yy = mid - 26
        for b in doc.banners:
            c.text(right, yy, b, 8, "F2", "right", (0.98, 0.55, 0.50))
            yy -= 11
        y = h - band - 18
        for line in doc.issuer:
            c.text(left, y, line, 8, color=GREY)
            y -= 11
        return y - 8

    def footer(page: int) -> None:
        c.line(left, bottom - 6, right, bottom - 6, GOLD, 0.4)
        y = bottom - 18
        for line in doc.footer:
            c.text(left, y, line, 7, color=GREY)
            y -= 9
        c.text(right, bottom - 18, f"Page {page}", 7, "F1", "right", GREY)

    page = 1
    y = header()
    # Recipient and meta blocks side by side.
    c.text(left, y, doc.recipient_title.upper(), 7, "F2", color=GREY)
    c.text(w / 2 + 20, y, "DETAILS", 7, "F2", color=GREY)
    y -= 12
    ry, my = y, y
    for line in doc.recipient:
        c.text(left, ry, line, 9, "F2" if ry == y else "F1")
        ry -= 12
    for label, value in doc.meta:
        c.text(w / 2 + 20, my, label, 8, color=GREY)
        c.text(right, my, value, 9, "F1", "right")
        my -= 12
    y = min(ry, my) - 14

    total_w = sum(col.width for col in doc.columns)
    xs, x = [], left
    for col in doc.columns:
        cw = (right - left) * col.width / total_w
        xs.append((x, cw))
        x += cw

    def table_head(y: float) -> float:
        c.rect(left, y - 4, right - left, 16, NAVY)
        for col, (cx, cw) in zip(doc.columns, xs, strict=True):
            tx = cx + cw - 4 if col.align == "right" else cx + 4
            c.text(tx, y + 1, col.title, 8, "F2", col.align, (1, 1, 1))
        return y - 18

    y = table_head(y)
    for i, row in enumerate(doc.rows):
        cells = [
            _wrap(val, cw - 8, 9) if col.align == "left" else [val]
            for val, col, (_, cw) in zip(row, doc.columns, xs, strict=True)
        ]
        height = 12 * max(len(cl) for cl in cells) + 4
        if y - height < bottom + 20:
            footer(page)
            c.new_page()
            page += 1
            y = table_head(header())
        if i % 2:
            c.rect(left, y - height + 10, right - left, height, LIGHT)
        for cl, col, (cx, cw) in zip(cells, doc.columns, xs, strict=True):
            ty = y
            for part in cl:
                tx = cx + cw - 4 if col.align == "right" else cx + 4
                c.text(tx, ty, part, 9, "F1", col.align)
                ty -= 12
        y -= height
    c.line(left, y + 6, right, y + 6, GOLD, 0.6)
    y -= 6
    for label, value in doc.totals:
        if y < bottom + 20:
            footer(page)
            c.new_page()
            page += 1
            y = header()
        bold = label.lower().startswith(("total", "balance", "amount"))
        c.text(right - 150, y, label, 9, "F2" if bold else "F1", "right")
        c.text(right, y, value, 9, "F2" if bold else "F1", "right")
        y -= 13
    y -= 8
    for note in doc.notes:
        for part in _wrap(note, right - left, 8):
            if y < bottom + 20:
                footer(page)
                c.new_page()
                page += 1
                y = header()
            c.text(left, y, part, 8, color=GREY)
            y -= 11
    footer(page)
    return c.output()


def letterhead(issuer: list[str]) -> bytes:
    """A blank A4 page on the AVEN GLOBAL letterhead, for printing letters."""
    c = Canvas()
    w, h = A4
    banner = asset("letterhead-banner-centred.jpg")
    bw, bh = jpeg_size(banner)
    band = w * bh / bw
    c.image("Logo", banner, 0, h - band, w, band)
    y = h - band - 18
    for line in issuer:
        c.text(48, y, line, 8, color=GREY)
        y -= 11
    c.line(48, 54, w - 48, 54, GOLD, 0.4)
    return c.output()
