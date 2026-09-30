"""Duplicate and business-rule checks over extracted invoices."""

from __future__ import annotations

from app.extract import Extraction


def anomaly_flags(extraction: Extraction, seen_keys: set[tuple[str, str]]) -> list[str]:
    flags = []
    key = (extraction.vendor or "", extraction.invoice_number or "")
    if extraction.vendor and extraction.invoice_number:
        if key in seen_keys:
            flags.append("duplicate_invoice")
        seen_keys.add(key)
    if None not in (extraction.subtotal, extraction.tax, extraction.discount, extraction.total):
        expected = round(extraction.subtotal - extraction.discount + extraction.tax, 2)
        if abs(expected - extraction.total) > 0.05:
            flags.append("total_mismatch")
    if extraction.subtotal and extraction.tax is not None and extraction.subtotal > 0:
        rate = extraction.tax / extraction.subtotal
        if not any(abs(rate - allowed) < 0.01 for allowed in (0.0, 0.05, 0.08, 0.10)):
            flags.append("tax_mismatch")
    return flags
