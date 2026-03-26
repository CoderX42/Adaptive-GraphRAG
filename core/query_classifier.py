from __future__ import annotations

import re

from loguru import logger

from core.models import RetrievalStrategy


class QueryClassifier:
    """Rule-based classifier that decides which retrieval strategy to use."""

    GRAPH_KEYWORDS: list[str] = [
        "关系", "关联", "影响", "导致", "为什么", "如何",
        "对比", "区别", "联系", "上级", "下级", "下属",
        "汇报", "属于", "包含", "因果", "之间",
    ]

    VECTOR_PATTERNS: list[str] = [
        r"什么是", r"谁是", r"是什么", r"定义",
        r"什么时候", r"多少", r"列表", r"列出",
        r"哪些", r"简述", r"概述",
    ]

    GRAPH_PATTERNS: list[str] = [
        r".+和.+[的是]什么关系",
        r".+与.+[有的].*关[联系]",
        r".+[的]上[级司]",
        r".+[的]下[级属]",
        r"从.+到.+",
    ]

    def classify(self, query: str) -> RetrievalStrategy:
        query_clean = query.strip()

        for pattern in self.GRAPH_PATTERNS:
            if re.search(pattern, query_clean):
                logger.info(f"Query classified as GRAPH (pattern match): {query_clean}")
                return RetrievalStrategy.GRAPH

        graph_score = sum(1 for kw in self.GRAPH_KEYWORDS if kw in query_clean)
        vector_score = sum(
            1 for p in self.VECTOR_PATTERNS if re.search(p, query_clean)
        )

        if graph_score >= 2:
            logger.info(
                f"Query classified as GRAPH (keywords={graph_score}): {query_clean}"
            )
            return RetrievalStrategy.GRAPH

        if graph_score >= 1 and vector_score == 0:
            logger.info(
                f"Query classified as HYBRID (graph_kw={graph_score}): {query_clean}"
            )
            return RetrievalStrategy.HYBRID

        if vector_score >= 1 and graph_score == 0:
            logger.info(
                f"Query classified as VECTOR (vector_pattern={vector_score}): {query_clean}"
            )
            return RetrievalStrategy.VECTOR

        if graph_score > 0 and vector_score > 0:
            logger.info(
                f"Query classified as HYBRID (mixed signals): {query_clean}"
            )
            return RetrievalStrategy.HYBRID

        logger.info(f"Query classified as VECTOR (default): {query_clean}")
        return RetrievalStrategy.VECTOR
