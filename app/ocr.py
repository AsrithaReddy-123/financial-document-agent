"""Read text from a rendered invoice image when Tesseract is installed."""

from __future__ import annotations

import io


def render_invoice_png(lines: list[str]) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1100, 48 + 42 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            font = ImageFont.truetype(path, 28)
            break
        except OSError:
            continue
    y = 24
    for line in lines:
        draw.text((24, y), line, fill="black", font=font)
        y += 42
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def ocr_png(payload: bytes) -> str:
    import pytesseract
    from PIL import Image

    return pytesseract.image_to_string(Image.open(io.BytesIO(payload)))
