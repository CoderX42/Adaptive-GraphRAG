from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import gradio as gr
import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from config import settings
from core.graph_builder import build_graph_from_chunks
from core.models import Document, DocumentStatus, QueryResult, RetrievalStrategy
from core.query_classifier import QueryClassifier
from core.response_generator import generate_answer, generate_summary
from core.retrievers.graph_retriever import GraphRetriever
from core.retrievers.hybrid_fusion import HybridFusionRetriever
from core.retrievers.vector_retriever import VectorRetriever
from processors.chunker import chunk_pages
from processors.pdf_processor import extract_pdf_pages, get_pdf_page_count
from storage.graph_store import GraphStore
from storage.metadata_store import MetadataStore
from storage.vector_store import VectorStore

# ── Initialise services ──

settings.ensure_dirs()

vector_store = VectorStore(
    persist_dir=settings.chroma_dir,
    ollama_host=settings.ollama_host,
    embedding_model=settings.embedding_model,
)
metadata_store = MetadataStore(db_path=settings.sqlite_path)
graph_store = GraphStore(cache_path=settings.graph_cache_path)

vector_retriever = VectorRetriever(vector_store)
graph_retriever = GraphRetriever(
    graph_store,
    model=settings.llm_model,
    ollama_host=settings.ollama_host,
)
hybrid_retriever = HybridFusionRetriever(vector_retriever, graph_retriever)
query_classifier = QueryClassifier()

# ── FastAPI app ──

api = FastAPI(title="Adaptive-GraphRAG", version="1.0.0")


async def _process_document(save_path: Path, doc: Document) -> tuple[int, int, int, str]:
    """Shared processing pipeline: parse -> chunk -> vectorize -> build graph -> summarize."""
    doc.page_count = get_pdf_page_count(save_path)
    doc.status = DocumentStatus.PROCESSING
    metadata_store.add_document(doc)

    pages = extract_pdf_pages(save_path)
    chunks = chunk_pages(
        pages,
        doc_id=doc.id,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    vector_store.add_chunks(chunks)

    entity_count, relation_count = await build_graph_from_chunks(
        chunks,
        graph_store,
        model=settings.llm_model,
        ollama_host=settings.ollama_host,
    )

    full_text = "\n".join(p.text[:500] for p in pages[:5])
    summary = await generate_summary(
        full_text, model=settings.llm_model, ollama_host=settings.ollama_host
    )
    metadata_store.update_summary(doc.id, summary)
    metadata_store.update_status(doc.id, DocumentStatus.READY)

    return len(chunks), entity_count, relation_count, summary


@api.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    doc = Document(filename=file.filename)
    save_path = settings.data_dir / "raw_docs" / f"{doc.id}_{file.filename}"

    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        chunk_count, ent_count, rel_count, _ = await _process_document(save_path, doc)

        return JSONResponse({
            "doc_id": doc.id,
            "status": "ready",
            "chunks": chunk_count,
            "entities": ent_count,
            "relations": rel_count,
        })
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        metadata_store.update_status(doc.id, DocumentStatus.FAILED)
        raise HTTPException(status_code=500, detail=str(e))


async def _adaptive_retrieve(
    text: str, mode: str
) -> tuple[list[dict[str, Any]], RetrievalStrategy, list[str]]:
    """Select retriever based on mode and return (contexts, strategy, reasoning_path)."""
    if mode == "auto":
        strategy = query_classifier.classify(text)
    else:
        strategy = RetrievalStrategy(mode)

    reasoning_path: list[str] = []

    if strategy == RetrievalStrategy.VECTOR:
        contexts = vector_retriever.retrieve(text, top_k=settings.top_k)
    elif strategy == RetrievalStrategy.GRAPH:
        contexts = graph_retriever.retrieve(text, top_k=settings.top_k)
        for ctx in contexts:
            reasoning_path.extend(ctx.get("reasoning_path", []))
        if not contexts:
            logger.info("Graph retrieval returned nothing, falling back to vector")
            contexts = vector_retriever.retrieve(text, top_k=settings.top_k)
            strategy = RetrievalStrategy.VECTOR
    else:
        contexts = hybrid_retriever.retrieve(text, top_k=settings.top_k)
        for ctx in contexts:
            reasoning_path.extend(ctx.get("reasoning_path", []))

    return contexts, strategy, reasoning_path


@api.get("/api/v1/retrieval/query")
async def query_documents(
    text: str = Query(..., description="查询文本"),
    mode: str = Query("auto", description="检索模式: auto, vector, graph, hybrid"),
) -> QueryResult:
    contexts, strategy, reasoning_path = await _adaptive_retrieve(text, mode)

    if not contexts:
        return QueryResult(
            answer="未找到相关文档内容，请先上传文档。",
            strategy_used=strategy,
        )

    result = await generate_answer(
        query=text,
        contexts=contexts,
        model=settings.llm_model,
        strategy=strategy,
        reasoning_path=reasoning_path,
        ollama_host=settings.ollama_host,
    )
    return result


@api.get("/api/v1/documents")
async def list_documents() -> list[dict[str, Any]]:
    docs = metadata_store.list_documents()
    return [d.model_dump(mode="json") for d in docs]


@api.get("/api/v1/graph/visualize")
async def visualize_graph(
    query: str = Query("", description="可选：围绕查询实体展示子图"),
    doc_id: str = Query("", description="可选：只展示该文档的图谱"),
) -> dict[str, Any]:
    if query:
        entities = await graph_retriever.extract_entities(query)
        if entities:
            return graph_store.get_subgraph_data(entities)

    return graph_store.get_graph_data(
        doc_id=doc_id or None,
        max_nodes=150,
        max_edges=300,
    )


@api.get("/api/v1/graph/stats")
async def graph_stats() -> dict[str, int]:
    return {
        "nodes": graph_store.node_count,
        "edges": graph_store.edge_count,
    }


# ── Gradio handlers ──


async def _handle_upload(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        return "文件不存在"

    doc = Document(filename=path.name)
    save_path = settings.data_dir / "raw_docs" / f"{doc.id}_{path.name}"
    shutil.copy2(path, save_path)

    try:
        chunk_count, ent_count, rel_count, summary = await _process_document(
            save_path, doc
        )
        return (
            f"上传成功！\n"
            f"文档ID: {doc.id}\n"
            f"页数: {doc.page_count}\n"
            f"分块数: {chunk_count}\n"
            f"抽取实体: {ent_count}，关系: {rel_count}\n"
            f"摘要: {summary[:100]}..."
        )
    except Exception as e:
        metadata_store.update_status(doc.id, DocumentStatus.FAILED)
        return f"处理失败: {e}"


async def _handle_query(question: str, mode: str) -> QueryResult:
    contexts, strategy, reasoning_path = await _adaptive_retrieve(question, mode)

    if not contexts:
        return QueryResult(
            answer="未找到相关文档内容，请先上传文档。",
            strategy_used=strategy,
        )

    return await generate_answer(
        query=question,
        contexts=contexts,
        model=settings.llm_model,
        strategy=strategy,
        reasoning_path=reasoning_path,
        ollama_host=settings.ollama_host,
    )


def _handle_list_docs() -> list[Document]:
    return metadata_store.list_documents()


def _handle_graph_data(doc_id: str | None = None) -> dict[str, Any]:
    return graph_store.get_graph_data(
        doc_id=doc_id,
        max_nodes=150,
        max_edges=300,
    )


def _handle_list_doc_ids() -> list[str]:
    """Return doc_ids of all READY documents, for UI filter dropdown."""
    return [
        d.id for d in metadata_store.list_documents()
        if d.status.value == "ready"
    ]


# ── Vue SPA (production build) ──

@api.get("/")
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/app/", status_code=307)


# ── Mount Gradio ──

from ui.app import create_ui

gradio_app = create_ui(
    upload_handler=_handle_upload,
    query_handler=_handle_query,
    list_docs_handler=_handle_list_docs,
    graph_data_handler=_handle_graph_data,
    list_doc_ids_handler=_handle_list_doc_ids,
)
api = gr.mount_gradio_app(api, gradio_app, path="/ui")

_frontend_dist = Path(__file__).resolve().parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    api.mount(
        "/app",
        StaticFiles(directory=str(_frontend_dist), html=True),
        name="vue_app",
    )

if __name__ == "__main__":
    logger.info("Starting Adaptive-GraphRAG server on http://localhost:8000")
    logger.info("Vue UI: http://localhost:8000/app/ (after npm run build in frontend/)")
    logger.info("Gradio UI: http://localhost:8000/ui")
    uvicorn.run("main:api", host="0.0.0.0", port=8000, reload=True)
