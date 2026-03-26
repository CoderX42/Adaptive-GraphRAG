from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import networkx as nx
from loguru import logger

from core.models import Entity, Relation


class GraphStore:
    def __init__(self, cache_path: Path | str) -> None:
        self._cache_path = Path(cache_path)
        self._graph: nx.DiGraph = nx.DiGraph()
        self._load()

    def _load(self) -> None:
        if self._cache_path.exists():
            try:
                with open(self._cache_path, "rb") as f:
                    self._graph = pickle.load(f)
                logger.info(
                    f"Graph loaded: {self._graph.number_of_nodes()} nodes, "
                    f"{self._graph.number_of_edges()} edges"
                )
            except Exception as e:
                logger.warning(f"Failed to load graph cache, starting fresh: {e}")
                self._graph = nx.DiGraph()
        else:
            logger.info("No graph cache found, starting with empty graph")

    def save(self) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, "wb") as f:
            pickle.dump(self._graph, f)
        logger.info(
            f"Graph saved: {self._graph.number_of_nodes()} nodes, "
            f"{self._graph.number_of_edges()} edges"
        )

    def add_entities_and_relations(
        self,
        entities: list[Entity],
        relations: list[Relation],
    ) -> None:
        # 过滤空 name 实体
        valid_entities = [e for e in entities if e.name and e.name.strip()]

        for ent in valid_entities:
            existing = self._find_similar_node(ent.name)
            if existing:
                attrs = self._graph.nodes[existing]
                if ent.name not in attrs.get("aliases", []) and ent.name != existing:
                    attrs.setdefault("aliases", []).append(ent.name)
                if ent.source_doc and ent.source_doc not in attrs.get("source_docs", []):
                    attrs.setdefault("source_docs", []).append(ent.source_doc)
            else:
                self._graph.add_node(
                    ent.name,
                    type=ent.type,
                    original_id=ent.id,
                    source_docs=[ent.source_doc] if ent.source_doc else [],
                    aliases=[],
                )

        for rel in relations:
            src = self._resolve_entity_name(rel.source, valid_entities)
            tgt = self._resolve_entity_name(rel.target, valid_entities)
            # 找不到 id 映射则跳过，不产生孤立字符串节点
            if not src or not tgt or src == tgt:
                continue
            src_node = self._find_similar_node(src) or src
            tgt_node = self._find_similar_node(tgt) or tgt

            if self._graph.has_edge(src_node, tgt_node):
                edge_data = self._graph[src_node][tgt_node]
                existing_rels = edge_data.get("relations", [])
                if rel.relation and rel.relation not in existing_rels:
                    existing_rels.append(rel.relation)
                    edge_data["relations"] = existing_rels
                # 补充来源文档
                if rel.source_doc and rel.source_doc not in edge_data.get("source_docs", []):
                    edge_data.setdefault("source_docs", []).append(rel.source_doc)
            else:
                self._graph.add_edge(
                    src_node,
                    tgt_node,
                    relations=[rel.relation] if rel.relation else [],
                    evidence=rel.evidence,
                    source_docs=[rel.source_doc] if rel.source_doc else [],
                )

    def find_shortest_path(
        self, entity_a: str, entity_b: str
    ) -> list[tuple[str, str, dict]]:
        node_a = self._find_similar_node(entity_a)
        node_b = self._find_similar_node(entity_b)
        if not node_a or not node_b:
            return []

        try:
            path_nodes = nx.shortest_path(self._graph, source=node_a, target=node_b)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            try:
                path_nodes = nx.shortest_path(self._graph, source=node_b, target=node_a)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return []

        edges: list[tuple[str, str, dict]] = []
        for i in range(len(path_nodes) - 1):
            src, tgt = path_nodes[i], path_nodes[i + 1]
            data = self._graph.get_edge_data(src, tgt, default={})
            edges.append((src, tgt, data))
        return edges

    def get_neighborhood(self, entity: str, depth: int = 2) -> nx.DiGraph:
        node = self._find_similar_node(entity)
        if not node or node not in self._graph:
            return nx.DiGraph()

        nodes: set[str] = set()
        current_layer = {node}
        for _ in range(depth):
            next_layer: set[str] = set()
            for n in current_layer:
                next_layer.update(self._graph.successors(n))
                next_layer.update(self._graph.predecessors(n))
            nodes.update(current_layer)
            current_layer = next_layer - nodes
        nodes.update(current_layer)

        return self._graph.subgraph(nodes).copy()

    def get_all_entities(self) -> list[dict[str, Any]]:
        return [{"name": n, **self._graph.nodes[n]} for n in self._graph.nodes]

    def get_all_relations(self) -> list[dict[str, Any]]:
        return [{"source": u, "target": v, **d} for u, v, d in self._graph.edges(data=True)]

    def get_entities_by_doc(self, doc_id: str) -> list[dict[str, Any]]:
        """Return entities whose source_docs includes the given doc_id."""
        return [
            {"name": n, **self._graph.nodes[n]}
            for n in self._graph.nodes
            if doc_id in self._graph.nodes[n].get("source_docs", [])
        ]

    def get_graph_data(
        self,
        doc_id: str | None = None,
        max_nodes: int = 150,
        max_edges: int = 300,
    ) -> dict[str, Any]:
        """Unified method: return {nodes, edges, stats} optionally filtered by doc_id."""
        if doc_id:
            relevant = self.get_entities_by_doc(doc_id)
            node_names = {e["name"] for e in relevant}
            subgraph = self._graph.subgraph(node_names)
        else:
            all_nodes = list(self._graph.nodes)[:max_nodes]
            subgraph = self._graph.subgraph(all_nodes)

        nodes = [
            {
                "id": n,
                "label": n,
                "type": subgraph.nodes[n].get("type", ""),
                "source_docs": subgraph.nodes[n].get("source_docs", []),
                "aliases": subgraph.nodes[n].get("aliases", []),
            }
            for n in subgraph.nodes
        ]
        edges = [
            {
                "source": u,
                "target": v,
                "label": ", ".join(d.get("relations", [])),
                "relations": d.get("relations", []),
            }
            for u, v, d in list(subgraph.edges(data=True))[:max_edges]
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "nodes": self._graph.number_of_nodes(),
                "edges": self._graph.number_of_edges(),
                "shown_nodes": len(nodes),
                "shown_edges": len(edges),
            },
        }

    def get_subgraph_data(self, entities: list[str]) -> dict[str, Any]:
        """Return {nodes, edges, stats} for a subgraph around given entities."""
        relevant_nodes: set[str] = set()
        for ent in entities:
            sub = self.get_neighborhood(ent, depth=2)
            relevant_nodes.update(sub.nodes)

        if not relevant_nodes:
            return {"nodes": [], "edges": [], "stats": {"nodes": 0, "edges": 0, "shown_nodes": 0, "shown_edges": 0}}

        subgraph = self._graph.subgraph(relevant_nodes)
        nodes = [
            {
                "id": n,
                "label": n,
                "type": subgraph.nodes[n].get("type", ""),
                "source_docs": subgraph.nodes[n].get("source_docs", []),
                "aliases": subgraph.nodes[n].get("aliases", []),
            }
            for n in subgraph.nodes
        ]
        edges = [
            {
                "source": u,
                "target": v,
                "label": ", ".join(d.get("relations", [])),
                "relations": d.get("relations", []),
            }
            for u, v, d in subgraph.edges(data=True)
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "nodes": self._graph.number_of_nodes(),
                "edges": self._graph.number_of_edges(),
                "shown_nodes": len(nodes),
                "shown_edges": len(edges),
            },
        }

    def _find_similar_node(self, name: str) -> str | None:
        if not name or not name.strip():
            return None
        if name in self._graph:
            return name
        name_lower = name.lower().strip()
        for node in self._graph.nodes:
            if node.lower().strip() == name_lower:
                return node
            aliases = self._graph.nodes[node].get("aliases", [])
            if any(a.lower().strip() == name_lower for a in aliases):
                return node
        return None

    @staticmethod
    def _resolve_entity_name(
        entity_id: str, entities: list[Entity]
    ) -> str | None:
        """Map entity id to its name. Returns None if not found (do NOT fall back to raw id)."""
        for ent in entities:
            if ent.id == entity_id:
                return ent.name if ent.name and ent.name.strip() else None
        return None

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()
