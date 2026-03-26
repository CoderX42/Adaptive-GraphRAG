from __future__ import annotations

from pathlib import Path
from typing import Any

import ollama
from jinja2 import Template
from loguru import logger

from core.models import QueryResult, RetrievalStrategy, SourceReference

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_template(name: str) -> Template:
    path = _PROMPT_DIR / name
    return Template(path.read_text(encoding="utf-8"))


_RESPONSE_TEMPLATE = _load_template("generate_response.txt")
_SUMMARY_TEMPLATE = _load_template("summarize_doc.txt")


async def generate_answer(
    query: str,
    contexts: list[dict[str, Any]],
    *,
    model: str = "qwen2.5:7b",
    strategy: RetrievalStrategy = RetrievalStrategy.VECTOR,
    reasoning_path: list[str] | None = None,
    ollama_host: str = "http://localhost:11434",
) -> QueryResult:
    prompt = _RESPONSE_TEMPLATE.render(query=query, contexts=contexts)

    client = ollama.AsyncClient(host=ollama_host)
    try:
        resp = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.7},
        )
        answer = resp["message"]["content"]
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        answer = f"抱歉，生成回答时出错：{e}"

    sources = _build_sources(contexts)
    confidence = _estimate_confidence(contexts)

    return QueryResult(
        answer=answer,
        sources=sources,
        strategy_used=strategy,
        reasoning_path=reasoning_path or [],
        confidence=confidence,
    )


async def generate_summary(
    content: str,
    *,
    model: str = "qwen2.5:7b",
    ollama_host: str = "http://localhost:11434",
) -> str:
    prompt = _SUMMARY_TEMPLATE.render(content=content[:3000])

    client = ollama.AsyncClient(host=ollama_host)
    try:
        resp = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3},
        )
        return resp["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return ""


def _build_sources(contexts: list[dict[str, Any]]) -> list[SourceReference]:
    sources: list[SourceReference] = []
    for ctx in contexts:
        meta = ctx.get("metadata", {})
        sources.append(
            SourceReference(
                doc_id=meta.get("doc_id", ""),
                filename=meta.get("doc_id", ""),
                page=meta.get("page_number", 0),
                text=ctx.get("content", "")[:200],
            )
        )
    return sources


def _estimate_confidence(contexts: list[dict[str, Any]]) -> float:
    if not contexts:
        return 0.0
    distances = [ctx.get("distance", 1.0) for ctx in contexts]
    avg_distance = sum(distances) / len(distances)
    return round(max(0.0, min(1.0, 1.0 - avg_distance)), 2)
