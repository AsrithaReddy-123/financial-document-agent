"""Synthetic invoices, receipts, and statements with known fields and anomaly labels."""

from __future__ import annotations

import random

from app.documents import build_pdf

VENDORS = [
    "Northwind Metals",
    "Contoso Freight",
    "Fabrikam Paper",
    "Adventure Works",
    "Wide World Importers",
    "Litware Studio",
    "Tailspin Toys",
    "Alpine Ski House",
]


def _invoice_text(vendor: str, number: str, date: str, qty: int, price: float, tax_rate: float, discount: float, total_override: float | None = None) -> str:
    amount = round(qty * price, 2)
    subtotal = amount
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal - discount + tax, 2) if total_override is None else total_override
    lines = [
        "INVOICE",
        f"Vendor: {vendor}",
        f"Invoice Number: {number}",
        f"Date: {date}",
        f"Item: steel brackets qty {qty} price {price:.2f} amount {amount:.2f}",
        f"Subtotal: {subtotal:.2f}",
        f"Discount: {discount:.2f}",
        f"Tax: {tax:.2f}",
        f"Total: {total:.2f}",
    ]
    return "\n".join(lines)


def build_documents(n: int = 5000, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    docs = []
    seen_numbers: dict[tuple[str, str], str] = {}
    for index in range(n):
        vendor = VENDORS[index % len(VENDORS)]
        number = f"INV-{10000 + index}"
        date = f"2024-{(index % 12) + 1:02d}-{(index % 27) + 1:02d}"
        qty = 1 + (index % 6)
        price = round(10 + (index % 40) + (index % 3) * 0.25, 2)
        tax_rate = (0.0, 0.05, 0.08, 0.10)[index % 4]
        discount = 5.0 if index % 17 == 0 else 0.0
        labels: list[str] = []
        total_override = None
        kind = "clean"
        if index % 40 == 0 and index > 0:
            previous = docs[index - 1]
            vendor = previous["vendor"]
            number = previous["invoice_number"]
            labels.append("duplicate_invoice")
            kind = "anomaly"
        elif index % 23 == 0:
            total_override = 1.0
            labels.append("total_mismatch")
            kind = "anomaly"
        elif index % 29 == 0:
            tax_rate = 0.22
            labels.append("tax_mismatch")
            kind = "anomaly"
        text = _invoice_text(vendor, number, date, qty, price, tax_rate, discount, total_override)
        if index % 11 == 0:
            text = text.replace("0", "O", 1)
            kind = "noisy" if kind == "clean" else kind
        header = "INVOICE"
        if index % 50 == 0:
            header = "RECEIPT"
            text = text.replace("INVOICE", "RECEIPT", 1)
        elif index % 70 == 0:
            header = "STATEMENT"
            text = text.replace("INVOICE", "STATEMENT", 1)
        doc_id = f"doc-{index}"
        seen_numbers[(vendor, number)] = doc_id
        docs.append(
            {
                "id": doc_id,
                "seq": index,
                "text": text,
                "pdf": build_pdf(text.splitlines()),
                "vendor": vendor,
                "invoice_number": number,
                "header": header,
                "labels": labels,
                "kind": kind,
                "gold_total_line": f"Total: {total_override:.2f}" if total_override is not None else None,
            }
        )
    rng.shuffle(docs)
    return docs


def retrieval_questions(docs: list[dict], n: int = 200, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    pool = [doc for doc in docs if doc["kind"] == "clean" and doc["header"] == "INVOICE"]
    rng.shuffle(pool)
    questions = []
    for doc in pool[:n]:
        questions.append(
            {
                "question": f"What is the total on invoice {doc['invoice_number']} from {doc['vendor']}?",
                "gold_id": doc["id"],
            }
        )
    return questions
