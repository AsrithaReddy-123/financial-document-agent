"""Field extraction with per-field confidence. Low confidence is routed to review."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

REVIEW_THRESHOLD = 0.85

_VENDOR = re.compile(r"^Vendor:\s*(.+)$", re.M)
_INVOICE = re.compile(r"^Invoice Number:\s*([A-Z0-9-]+)$", re.M)
_DATE = re.compile(r"^Date:\s*(\d{4}-\d{2}-\d{2})$", re.M)
_MONEY = re.compile(r"^-?\d+\.\d{2}$")
_LINE = re.compile(
    r"^Item:\s*(.+?)\s+qty\s+(\d+)\s+price\s+(\d+\.\d{2})\s+amount\s+(\d+\.\d{2})$",
    re.M,
)


@dataclass
class Extraction:
    vendor: str | None
    invoice_number: str | None
    invoice_date: str | None
    subtotal: float | None
    tax: float | None
    discount: float | None
    total: float | None
    line_items: list[dict]
    confidence: dict[str, float] = field(default_factory=dict)

    @property
    def min_confidence(self) -> float:
        if not self.confidence:
            return 0.0
        return min(self.confidence.values())

    @property
    def needs_review(self) -> bool:
        return self.min_confidence < REVIEW_THRESHOLD


def _money(text: str, label: str) -> tuple[float | None, float]:
    match = re.search(rf"^{label}:\s*(-?\d+\.\d{{2}})$", text, re.M)
    if not match:
        return None, 0.4
    raw = match.group(1)
    if _MONEY.match(raw):
        return float(raw), 0.97
    return None, 0.5


def extract_invoice(text: str) -> Extraction:
    vendor_match = _VENDOR.search(text)
    invoice_match = _INVOICE.search(text)
    date_match = _DATE.search(text)
    vendor = vendor_match.group(1).strip() if vendor_match else None
    invoice_number = invoice_match.group(1) if invoice_match else None
    invoice_date = date_match.group(1) if date_match else None
    subtotal, subtotal_conf = _money(text, "Subtotal")
    tax, tax_conf = _money(text, "Tax")
    discount, discount_conf = _money(text, "Discount")
    total, total_conf = _money(text, "Total")
    if "Discount:" not in text:
        discount, discount_conf = 0.0, 0.97
    items = []
    for match in _LINE.finditer(text):
        items.append(
            {
                "description": match.group(1).strip(),
                "qty": int(match.group(2)),
                "price": float(match.group(3)),
                "amount": float(match.group(4)),
            }
        )
    confidence = {
        "vendor": 0.96 if vendor else 0.4,
        "invoice_number": 0.97 if invoice_number else 0.4,
        "invoice_date": 0.97 if invoice_date else 0.4,
        "subtotal": subtotal_conf,
        "tax": tax_conf,
        "discount": discount_conf,
        "total": total_conf,
        "line_items": 0.95 if items else 0.45,
    }
    return Extraction(
        vendor=vendor,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        subtotal=subtotal,
        tax=tax,
        discount=discount,
        total=total,
        line_items=items,
        confidence=confidence,
    )
