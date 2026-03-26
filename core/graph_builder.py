from __future__ import annotations

import json
import re
from pathlib import Path

import ollama
from jinja2 import Template
from loguru import logger

from core.models import Chunk, Entity, Relation
from storage.graph_store import GraphStore

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_EXTRACTION_TEMPLATE = Template(
    (_PROMPT_DIR / "entity_extraction.txt").read_text(encoding="utf-8")
)


def _extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    patterns = [
        r"```json\s*(.*?)\s*```",
        r"```\s*(.*?)\s*```",
        r"(\{.*\})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No valid JSON found in response: {text[:200]}")


async def extract_entities_from_chunk(
    chunk: Chunk,
    *,
    model: str = "qwen2.5:7b",
    ollama_host: str = "http://localhost:11434",
) -> tuple[list[Entity], list[Relation]]:
    """Use LLM to extract entities and relations from a single chunk."""
    prompt = _EXTRACTION_TEMPLATE.render(text=chunk.content)

    client = ollama.AsyncClient(host=ollama_host)
    try:
        resp = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        raw = resp["message"]["content"]
        data = _extract_json_from_response(raw)
    except Exception as e:
        logger.warning(f"Entity extraction failed for chunk {chunk.id}: {e}")
        return [], []

    entities: list[Entity] = []
    for ent_data in data.get("entities", []):
        entities.append(
            Entity(
                id=ent_data.get("id", ""),
                name=ent_data.get("name", ""),
                type=ent_data.get("type", "Concept"),
                source_doc=chunk.doc_id,
            )
        )

    relations: list[Relation] = []
    for rel_data in data.get("relations", []):
        relations.append(
            Relation(
                source=rel_data.get("source", ""),
                target=rel_data.get("target", ""),
                relation=rel_data.get("relation", ""),
                evidence=chunk.content[:200],
                source_doc=chunk.doc_id,
            )
        )

    return entities, relations


async def build_graph_from_chunks(
    chunks: list[Chunk],
    graph_store: GraphStore,
    *,
    model: str = "qwen2.5:7b",
    ollama_host: str = "http://localhost:11434",
) -> tuple[int, int]:
    """Process all chunks and build the knowledge graph. Returns (entity_count, relation_count)."""
    total_entities = 0
    total_relations = 0

    for i, chunk in enumerate(chunks):
        logger.info(f"Extracting entities from chunk {i+1}/{len(chunks)}")
        entities, relations = await extract_entities_from_chunk(
            chunk, model=model, ollama_host=ollama_host
        )
        if entities or relations:
            graph_store.add_entities_and_relations(entities, relations)
            total_entities += len(entities)
            total_relations += len(relations)

    graph_store.save()
    logger.info(
        f"Graph built: {total_entities} entities, {total_relations} relations extracted"
    )
    return total_entities, total_relations
