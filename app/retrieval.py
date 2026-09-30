"""Hybrid retrieval over invoice text."""

from __future__ import annotations

import hashlib
import re

import numpy as np
from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    tokens = [tok for tok in _TOKEN.findall(text.lower()) if len(tok) > 1]
    return tokens or ["blank"]


class HashEmbedder:
    model_name = "hash"

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def encode(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in tokenize(text):
                digest = hashlib.md5(token.encode()).digest()
                matrix[row, int.from_bytes(digest[:4], "little") % self.dim] += 1 if digest[4] % 2 == 0 else -1
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms


class MiniLM:
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.model = SentenceTransformer(self.model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            self.model.encode(texts, normalize_embeddings=True, batch_size=64, show_progress_bar=len(texts) > 256),
            dtype=np.float32,
        )


def load_embedder(name: str):
    if name == "hash":
        return HashEmbedder()
    return MiniLM()


class InvoiceRetriever:
    def __init__(self, docs: list[dict], embedder) -> None:
        self.docs = docs
        self.embedder = embedder
        self.bm25 = BM25Okapi([tokenize(doc["text"]) for doc in docs])
        self.matrix = embedder.encode([doc["text"] for doc in docs])

    def search(self, query: str, k: int = 5) -> list[dict]:
        fused: dict[int, float] = {}
        q = self.embedder.encode([query])[0]
        for rank, index in enumerate(np.argsort(-(self.matrix @ q))[:40]):
            fused[int(index)] = fused.get(int(index), 0.0) + 1 / (60 + rank + 1)
        scores = self.bm25.get_scores(tokenize(query))
        for rank, index in enumerate(np.argsort(-scores)[:40]):
            fused[int(index)] = fused.get(int(index), 0.0) + 1 / (60 + rank + 1)
        order = sorted(fused, key=fused.get, reverse=True)[:k]
        return [self.docs[index] | {"score": fused[index]} for index in order]
