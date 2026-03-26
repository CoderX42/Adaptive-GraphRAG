from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import ollama
from jinja2 import Template
from loguru import logger

from core.retrievers.base import BaseRetriever
from storage.graph_store import GraphStore

_PROMPT_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_QUERY_ENTITY_TEMPLATE = Template(
    (_PROMPT_DIR / "extract_query_entities.txt").read_text(encoding="utf-8")
)

# 从查询中提取引号/书名号内词语，作为 LLM 抽取失败时的降级策略
_FALLBACK_PATTERN = re.compile(r'[「」『』"\'《》【】""]([^「」『』"\'《》【】""]{1,20})[「」『』"\'《》【】""]')


class GraphRetriever(BaseRetriever):
    def __init__(
        self,
        graph_store: GraphStore,
        *,
        model: str = "qwen2.5:7b",
        ollama_host: str = "http://localhost:11434",
    ) -> None:
        self._graph_store = graph_store
        self._model = model
        self._ollama_host = ollama_host

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Synchronous wrapper — extracts entities then searches the graph."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.aretrieve(query, top_k)).result()
        return asyncio.run(self.aretrieve(query, top_k))

    async def aretrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        entities = await self.extract_entities(query)
        if not entities:
            logger.info("No entities extracted from query, graph retrieval skipped")
            return []

        logger.info(f"Query entities: {entities}")
        return self._search_graph(entities, top_k=top_k)

    async def extract_entities(self, query: str) -> list[str]:
        """Public method: extract entity names from a query string."""
        prompt = _QUERY_ENTITY_TEMPLATE.render(query=query)
        client = ollama.AsyncClient(host=self._ollama_host)

        try:
            resp = await client.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1},
            )
            raw = resp["message"]["content"]
            entities = self._parse_entity_list(raw)
            if entities:
                return entities
        except Exception as e:
            logger.warning(f"Query entity extraction failed: {e}")

        # 降级：从引号/书名号中直接提取
        fallback = _FALLBACK_PATTERN.findall(query)
        if fallback:
            logger.info(f"Entity extraction fallback: {fallback}")
            return fallback

        return []

    def _search_graph(
        self, entities: list[str], top_k: int = 5
    ) -> list[dict[str, Any]]:
        path_results: list[dict[str, Any]] = []
        nbr_results: list[dict[str, Any]] = []

        # 两两实体之间查最短路径
        if len(entities) >= 2:
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    path = self._graph_store.find_shortest_path(entities[i], entities[j])
                    if path:
                        path_desc = self._format_path(path)
                        # 展示全部 relations，不只取 [0]
                        reasoning_steps = [
                            f"{src} --[{', '.join(d.get('relations', ['?']))}]--> {tgt}"
                            for src, tgt, d in path
                        ]
                        path_results.append(
                            {
                                "content": path_desc,
                                "metadata": {
                                    "doc_id": "graph",
                                    "page_number": 0,
                                    "type": "path",
                                    "entities": [entities[i], entities[j]],
                                },
                                "distance": 0.05 + 0.01 * len(path),
                                "source_type": "graph",
                                "reasoning_path": reasoning_steps,
                            }
                        )

        # 按路径长度升序，截断到 top_k
        path_results.sort(key=lambda x: len(x.get("reasoning_path", [])))
        path_results = path_results[:top_k]

        # 邻域检索：剩余槽位给邻域结果
        remaining = max(1, top_k - len(path_results))
        for entity in entities[:remaining]:
            subgraph = self._graph_store.get_neighborhood(entity, depth=2)
            if subgraph.number_of_nodes() > 0:
                desc = self._format_neighborhood(entity, subgraph)
                nbr_results.append(
                    {
                        "content": desc,
                        "metadata": {
                            "doc_id": "graph",
                            "page_number": 0,
                            "type": "neighborhood",
                            "entity": entity,
                        },
                        "distance": 0.2,
                        "source_type": "graph",
                        "reasoning_path": [],
                    }
                )

        return path_results + nbr_results

    @staticmethod
    def _format_path(path: list[tuple[str, str, dict]]) -> str:
        lines = ["关系路径推理："]
        for src, tgt, data in path:
            rels = data.get("relations", ["相关"])
            lines.append(f"  {src} --[{', '.join(rels)}]--> {tgt}")
        return "\n".join(lines)

    @staticmethod
    def _format_neighborhood(entity: str, subgraph: Any) -> str:
        lines = [f"实体「{entity}」的关系网络："]
        for u, v, data in subgraph.edges(data=True):
            rels = data.get("relations", ["相关"])
            lines.append(f"  {u} --[{', '.join(rels)}]--> {v}")
        return "\n".join(lines)

    @staticmethod
    def _parse_entity_list(raw: str) -> list[str]:
        patterns = [
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
            r"(\[.*?\])",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(1))
                    if isinstance(result, list):
                        return [str(e).strip() for e in result if str(e).strip()]
                except json.JSONDecodeError:
                    continue
        return []
