import shutil

import pytest

from app.ocr import ocr_png, render_invoice_png


def test_ocr_reads_invoice_fields():
    if shutil.which("tesseract") is None:
        pytest.skip("tesseract is not installed")
    png = render_invoice_png(
        [
            "INVOICE",
            "Vendor: Northwind Metals",
            "Invoice Number: INV-10042",
            "Total: 21.60",
        ]
    )
    text = ocr_png(png)
    assert "Northwind" in text
    assert "INV-10042" in text
