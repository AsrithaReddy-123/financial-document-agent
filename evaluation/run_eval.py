"""Measure field accuracy, anomaly precision, and Recall@5."""

from __future__ import annotations

import json
from pathlib import Path

from app.agents import build_graph
from app.documents import read_pdf_text
from app.extract import extract_invoice
from app.retrieval import InvoiceRetriever, load_embedder
from evaluation.dataset import build_documents, retrieval_questions


def main() -> None:
    docs = build_documents(5000)
    clean = [doc for doc in docs if doc["kind"] == "clean"]
    field_hits = 0
    field_total = 0
    for doc in clean:
        text = read_pdf_text(doc["pdf"])
        parsed = extract_invoice(text)
        for name in ("vendor", "invoice_number", "invoice_date", "total"):
            field_total += 1
            original = extract_invoice(doc["text"])
            if getattr(parsed, name) == getattr(original, name) and getattr(parsed, name) is not None:
                field_hits += 1
    graph = build_graph()
    predicted_positive = 0
    true_positive = 0
    labeled_positive = 0
    review = 0
    for doc in sorted(docs, key=lambda item: item["seq"]):
        result = graph.invoke({"text": doc["text"]})
        flags = set(result.get("flags") or [])
        truth = set(doc["labels"])
        if result.get("needs_review"):
            review += 1
        if truth:
            labeled_positive += 1
        if flags:
            predicted_positive += 1
            if flags & truth:
                true_positive += 1
    precision = true_positive / predicted_positive if predicted_positive else 0.0
    questions = retrieval_questions(docs, 200)
    retriever = InvoiceRetriever(docs, load_embedder("sentence-transformers/all-MiniLM-L6-v2"))
    hits = 0
    for question in questions:
        found = retriever.search(question["question"], k=5)
        if any(item["id"] == question["gold_id"] for item in found):
            hits += 1
    payload = {
        "project": "financial-document-agent",
        "documents": len(docs),
        "clean_field_accuracy": round(field_hits / field_total, 4),
        "anomaly_precision": round(precision, 4),
        "labeled_anomalies": labeled_positive,
        "review_rate": round(review / len(docs), 4),
        "retrieval_questions": len(questions),
        "recall@5": round(hits / len(questions), 4) if questions else 0.0,
        "embedder": retriever.embedder.model_name,
        "notes": (
            "Synthetic invoices. Field accuracy is measured on the clean subset after a PDF text-layer round trip. "
            "Anomaly precision compares detector flags with generator labels. "
            "Image OCR is not run in this benchmark; digital PDFs use the text layer."
        ),
    }
    out = Path("evaluation/results/benchmark.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
