"""Classify, extract, validate, and answer from a document."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.anomalies import anomaly_flags
from app.extract import extract_invoice


class DocState(TypedDict, total=False):
    text: str
    doc_type: str
    extraction: dict
    flags: list[str]
    needs_review: bool
    answer: str


def build_graph(seen_keys: set[tuple[str, str]] | None = None):
    keys = seen_keys if seen_keys is not None else set()

    def classify(state: DocState) -> dict:
        text = state["text"]
        if text.startswith("INVOICE"):
            doc_type = "invoice"
        elif text.startswith("RECEIPT"):
            doc_type = "receipt"
        else:
            doc_type = "statement"
        return {"doc_type": doc_type}

    def extract(state: DocState) -> dict:
        parsed = extract_invoice(state["text"])
        return {
            "extraction": {
                "vendor": parsed.vendor,
                "invoice_number": parsed.invoice_number,
                "invoice_date": parsed.invoice_date,
                "subtotal": parsed.subtotal,
                "tax": parsed.tax,
                "discount": parsed.discount,
                "total": parsed.total,
                "line_items": parsed.line_items,
                "confidence": parsed.confidence,
                "min_confidence": parsed.min_confidence,
            },
            "needs_review": parsed.needs_review,
            "flags": anomaly_flags(parsed, keys),
        }

    def respond(state: DocState) -> dict:
        extracted = state.get("extraction", {})
        vendor = extracted.get("vendor") or "unknown vendor"
        total = extracted.get("total")
        flags = ", ".join(state.get("flags") or []) or "none"
        review = "queued for human review" if state.get("needs_review") else "accepted"
        return {
            "answer": f"{state.get('doc_type', 'document')} from {vendor} totals {total}. Anomalies: {flags}. Status: {review}."
        }

    graph = StateGraph(DocState)
    graph.add_node("classify", classify)
    graph.add_node("extract", extract)
    graph.add_node("respond", respond)
    graph.set_entry_point("classify")
    graph.add_edge("classify", "extract")
    graph.add_edge("extract", "respond")
    graph.add_edge("respond", END)
    return graph.compile()
