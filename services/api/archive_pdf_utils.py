"""
PDF rendering helpers for DSP archive packaging.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import io

try:
    from reportlab.lib.colors import Color
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    _HAS_REPORTLAB = True
except Exception:
    _HAS_REPORTLAB = False


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def _pdf_escape(text: str) -> str:
    return _to_text(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_report_bytes_legacy(lines: list[str], *, watermark: str, trust_ok: bool) -> bytes:
    body = ["BT", "/F1 12 Tf", "50 780 Td"]
    first = True
    for raw in lines[:42]:
        line = _pdf_escape(raw)
        if not first:
            body.append("0 -16 Td")
        body.append(f"({line}) Tj")
        first = False
    body.append("ET")

    wm_color = "0.15 0.62 0.37 rg" if trust_ok else "0.78 0.18 0.24 rg"
    wm = [
        "BT",
        "/F1 10 Tf",
        wm_color,
        "360 812 Td",
        f"({_pdf_escape(watermark)}) Tj",
        "ET",
    ]
    stream = "\n".join(body + wm).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
    )
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(
        f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii")
        + stream
        + b"\nendstream endobj\n"
    )

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(out.tell())
        out.write(obj)
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode("ascii"))
    out.write(
        (
            "trailer << /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".format(
                size=len(objects) + 1,
                xref=xref_pos,
            )
        ).encode("ascii")
    )
    return out.getvalue()


def _candidate_cjk_font_paths() -> list[Path]:
    return [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/msyh.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ]


def _register_pdf_font() -> str:
    if not _HAS_REPORTLAB:
        raise RuntimeError("reportlab unavailable")

    for path in _candidate_cjk_font_paths():
        if not path.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("QCSpecCJK", str(path)))
            return "QCSpecCJK"
        except Exception:
            continue
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception as exc:
        raise RuntimeError(f"no_cjk_font: {exc}") from exc


def _wrap_line(text: str, *, font_name: str, font_size: int, max_width: float) -> list[str]:
    src = _to_text(text)
    if not src:
        return [""]
    out: list[str] = []
    current = ""
    for ch in src:
        probe = f"{current}{ch}"
        width = pdfmetrics.stringWidth(probe, font_name, font_size)
        if width <= max_width:
            current = probe
            continue
        if current:
            out.append(current)
            current = ch
        else:
            out.append(ch)
            current = ""
    if current:
        out.append(current)
    return out or [src]


def pdf_report_bytes(lines: list[str], *, watermark: str, trust_ok: bool) -> bytes:
    if not _HAS_REPORTLAB:
        return _pdf_report_bytes_legacy(lines, watermark=watermark, trust_ok=trust_ok)

    try:
        font_name = _register_pdf_font()
    except Exception:
        return _pdf_report_bytes_legacy(lines, watermark=watermark, trust_ok=trust_ok)

    buf = io.BytesIO()
    w, h = A4
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("QCSpec Data Sovereignty Report")

    c.setFont(font_name, 11)
    c.setFillColor(Color(0.15, 0.62, 0.37) if trust_ok else Color(0.78, 0.18, 0.24))
    c.drawRightString(w - 36, h - 36, watermark)

    c.setFillColor(Color(0, 0, 0))
    text_font_size = 16
    body_font_size = 11
    left = 48
    top = h - 78
    max_width = w - 2 * left

    c.setFont(font_name, text_font_size)
    c.drawString(left, top, _to_text(lines[0] if lines else "QCSpec Data Sovereignty Report"))

    y = top - 30
    c.setFont(font_name, body_font_size)
    for line in lines[1:]:
        wrapped = _wrap_line(line, font_name=font_name, font_size=body_font_size, max_width=max_width)
        for sub in wrapped:
            if y < 50:
                c.showPage()
                c.setFont(font_name, body_font_size)
                y = h - 56
            c.drawString(left, y, _to_text(sub))
            y -= 20

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
