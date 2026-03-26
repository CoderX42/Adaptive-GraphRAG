from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from loguru import logger

from core.models import Chunk


class VectorStore:
    def __init__(
        self,
        persist_dir: Path | str,
        ollama_host: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
        collection_name: str = "documents",
    ) -> None:
        self._embedding_fn = OllamaEmbeddingFunction(
            url=ollama_host,
            model_name=embedding_model,
        )
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"VectorStore ready – collection '{collection_name}' "
            f"({self._collection.count()} vectors)"
        )

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        self._collection.upsert(
            ids=[c.id for c in chunks],
            documents=[c.content for c in chunks],
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                }
                for c in chunks
            ],
        )
        logger.info(f"Upserted {len(chunks)} chunks into vector store")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_doc_id: str | None = None,
    ) -> list[dict]:
        where = {"doc_id": filter_doc_id} if filter_doc_id else None
        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        items: list[dict] = []
        if not results["ids"] or not results["ids"][0]:
            return items

        for i, doc_id in enumerate(results["ids"][0]):
            items.append(
                {
                    "chunk_id": doc_id,
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )
        return items

    def delete_by_doc_id(self, doc_id: str) -> None:
        self._collection.delete(where={"doc_id": doc_id})
        logger.info(f"Deleted chunks for doc_id={doc_id}")

    @property
    def count(self) -> int:
        return self._collection.count()
