"""Invoice ingestion, extraction, and question answering."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agents import build_graph
from app.documents import read_pdf_text
from app.retrieval import InvoiceRetriever, load_embedder
from evaluation.dataset import build_documents


class IngestRequest(BaseModel):
    filename: str
    text: str | None = None
    pdf_base64: str | None = None


class AskRequest(BaseModel):
    question: str
    k: int = Field(default=5, ge=1, le=20)


def create_app(embedder_name: str | None = None, corpus_size: int | None = None) -> FastAPI:
    name = embedder_name or os.getenv("EMBEDDER", "sentence-transformers/all-MiniLM-L6-v2")
    size = corpus_size if corpus_size is not None else int(os.getenv("CORPUS_SIZE", "500"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        docs = build_documents(size)
        app.state.docs = docs
        app.state.retriever = InvoiceRetriever(docs, load_embedder(name))
        app.state.graph = build_graph()
        app.state.review_queue: list[dict] = []
        yield

    app = FastAPI(title="Financial Document Agent", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/ingest")
    def ingest(body: IngestRequest) -> dict:
        text = body.text or ""
        if body.pdf_base64:
            import base64

            text = read_pdf_text(base64.b64decode(body.pdf_base64))
        result = app.state.graph.invoke({"text": text})
        record = {"filename": body.filename, **result}
        app.state.docs.append({"id": body.filename, "text": text, "vendor": result.get("extraction", {}).get("vendor")})
        if result.get("needs_review"):
            app.state.review_queue.append(record)
        return record

    @app.post("/ask")
    def ask(body: AskRequest) -> dict:
        hits = app.state.retriever.search(body.question, k=body.k)
        return {"hits": [{"id": hit["id"], "score": hit["score"], "snippet": hit["text"][:240]} for hit in hits]}

    @app.get("/review")
    def review() -> dict:
        return {"count": len(app.state.review_queue), "items": app.state.review_queue[:20]}

    return app


app = create_app()
