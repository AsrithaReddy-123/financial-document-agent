from app.anomalies import anomaly_flags
from app.documents import build_pdf, read_pdf_text
from app.extract import extract_invoice
from evaluation.dataset import build_documents


def test_pdf_round_trip_and_clean_extraction():
    docs = build_documents(30, seed=1)
    clean = next(doc for doc in docs if doc["kind"] == "clean" and doc["header"] == "INVOICE")
    parsed = extract_invoice(read_pdf_text(clean["pdf"]))
    assert parsed.vendor == clean["vendor"]
    assert parsed.invoice_number == clean["invoice_number"]
    assert parsed.total is not None
    assert parsed.min_confidence >= 0.85
    assert not parsed.needs_review


def test_total_mismatch_flag():
    text = "\n".join(
        [
            "INVOICE",
            "Vendor: Northwind Metals",
            "Invoice Number: INV-9",
            "Date: 2024-03-02",
            "Item: steel brackets qty 2 price 10.00 amount 20.00",
            "Subtotal: 20.00",
            "Discount: 0.00",
            "Tax: 1.60",
            "Total: 1.00",
        ]
    )
    parsed = extract_invoice(text)
    assert "total_mismatch" in anomaly_flags(parsed, set())


def test_pdf_bytes_start_with_header():
    payload = build_pdf(["INVOICE", "Vendor: Alpine Ski House"])
    assert payload.startswith(b"%PDF-")
    assert "Alpine Ski House" in read_pdf_text(payload)
