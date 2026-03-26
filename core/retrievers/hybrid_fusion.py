from __future__ import annotations

from typing import Any

from loguru import logger

from core.retrievers.base import BaseRetriever
from core.retrievers.graph_retriever import GraphRetriever
from core.retrievers.vector_retriever import VectorRetriever


class HybridFusionRetriever(BaseRetriever):
    """Fuse vector and graph retrieval results using Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        graph_retriever: GraphRetriever,
        *,
        rrf_k: int = 60,
    ) -> None:
        self._vector = vector_retriever
        self._graph = graph_retriever
        self._rrf_k = rrf_k

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        vector_results = self._vector.retrieve(query, top_k=top_k)
        graph_results = self._graph.retrieve(query, top_k=top_k)

        # 标注来源类型
        for item in vector_results:
            item.setdefault("source_type", "vector")
        for item in graph_results:
            item.setdefault("source_type", "graph")

        if not graph_results:
            return vector_results
        if not vector_results:
            return graph_results

        fused = self._rrf_fuse(vector_results, graph_results)
        logger.info(
            f"Hybrid fusion: {len(vector_results)} vector + "
            f"{len(graph_results)} graph -> {len(fused)} fused"
        )
        return fused[:top_k]

    def _rrf_fuse(
        self,
        *result_lists: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        scores: dict[str, float] = {}
        item_map: dict[str, dict[str, Any]] = {}

        for results in result_lists:
            for rank, item in enumerate(results):
                key = self._item_key(item)
                scores[key] = scores.get(key, 0.0) + 1.0 / (self._rrf_k + rank + 1)
                if key not in item_map:
                    item_map[key] = item

        sorted_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
        fused: list[dict[str, Any]] = []
        for key in sorted_keys:
            item = item_map[key].copy()
            item["rrf_score"] = round(scores[key], 6)
            fused.append(item)

        return fused

    @staticmethod
    def _item_key(item: dict[str, Any]) -> str:
        # 向量结果：用 chunk_id
        if chunk_id := item.get("chunk_id", ""):
            return f"vec:{chunk_id}"

        # 图结果：用 type + 实体组合键，避免 content[:100] 碰撞
        meta = item.get("metadata", {})
        item_type = meta.get("type", "")
        if item_type == "path":
            entities = meta.get("entities", [])
            return f"graph:path:{':'.join(sorted(entities))}"
        if item_type == "neighborhood":
            entity = meta.get("entity", "")
            return f"graph:nbr:{entity}"

        # 兜底：对 content 做 hash
        return f"graph:{hash(item.get('content', ''))}"
