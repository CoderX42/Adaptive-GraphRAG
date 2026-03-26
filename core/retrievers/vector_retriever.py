from __future__ import annotations

from typing import Any

from core.retrievers.base import BaseRetriever
from storage.vector_store import VectorStore


class VectorRetriever(BaseRetriever):
    def __init__(self, vector_store: VectorStore) -> None:
        self._store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return self._store.search(query, top_k=top_k)
