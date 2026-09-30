"""Minimal text-layer PDFs and a reader for the strings this writer emits."""

from __future__ import annotations

import re


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(lines: list[str]) -> bytes:
    commands = []
    y = 760
    for line in lines:
        commands.append(f"BT /F1 11 Tf 50 {y} Td ({_escape(line)}) Tj ET")
        y -= 16
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        ),
        b"4 0 obj << /Length " + str(len(stream)).encode() + b" >> stream\n" + stream + b"\nendstream endobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    for obj in objects:
        offsets.append(sum(len(part) for part in parts))
        parts.append(obj)
    xref_at = sum(len(part) for part in parts)
    xref = [f"xref\n0 {len(offsets)}\n", "0000000000 65535 f \n"]
    xref.extend(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    trailer = (
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    )
    return b"".join(parts) + "".join(xref).encode() + trailer.encode()


def read_pdf_text(payload: bytes) -> str:
    texts = re.findall(rb"\((?:\\.|[^\\)])*\)\s*Tj", payload)
    lines = []
    for raw in texts:
        inner = raw.split(b")", 1)[0][1:]
        inner = inner.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
        lines.append(inner.decode("latin-1", errors="replace"))
    if not lines:
        raise ValueError("no text layer found")
    return "\n".join(lines)
