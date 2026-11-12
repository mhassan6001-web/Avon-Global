"""Dependency-free writers for PDF, DOCX and XLSX (standard library only)."""

import re

_INVALID_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def escape(text: str) -> str:
    """Escape text for XML output (we only write XML, never parse it) and drop
    characters XML 1.0 forbids, so record text can never corrupt a file."""
    text = _INVALID_XML.sub("", text)
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
