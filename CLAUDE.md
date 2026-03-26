# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Adaptive-GraphRAG is a local-first intelligent document Q&A system with adaptive retrieval routing. It uploads PDFs, chunks them, builds vector embeddings (ChromaDB) and a knowledge graph (NetworkX), then routes queries to vector search, graph traversal, or hybrid (RRF fusion) based on query complexity.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and edit config
cp .env.example .env

# Start the server (development mode with auto-reload)
python main.py
```

- **Gradio UI**: http://localhost:8000/ui
- **FastAPI docs**: http://localhost:8000/docs

**Prerequisites**: Ollama must be running at `http://localhost:11434` with the models specified in `.env` (default: `llama3.1:8b` for chat, `nomic-embed-text` for embeddings).

## Architecture

```
User (Gradio UI / HTTP API)
         │
         ▼
   FastAPI (main.py)
         │
    QueryClassifier ──► Rule-based: keywords + regex
         │
         ├─► VectorRetriever ──► ChromaDB + Ollama embeddings
         ├─► GraphRetriever  ──► NetworkX (shortest path / neighborhood)
         └─► HybridFusionRetriever ──► RRF fusion of both
         │
         ▼
   Ollama LLM ──► generate_answer() / generate_summary()
```

### Directory Structure

| Directory | Purpose |
|-----------|---------|
| `core/` | Core business logic: query classification, response generation, graph building |
| `core/retrievers/` | `VectorRetriever` (ChromaDB), `GraphRetriever` (NetworkX), `HybridFusionRetriever` (RRF) |
| `storage/` | Persistence: `VectorStore` (ChromaDB), `GraphStore` (NetworkX + pickle), `MetadataStore` (SQLite) |
| `processors/` | PDF extraction and text chunking |
| `ui/` | Gradio web interface |
| `prompts/` | Jinja2 templates for LLM entity extraction and answer generation |

### Key Classes

- **`QueryClassifier`** (`core/query_classifier.py`): Rule-based classifier using keyword matching and regex patterns to route queries to `VECTOR`, `GRAPH`, or `HYBRID` strategy.
- **`HybridFusionRetriever`** (`core/retrievers/hybrid_fusion.py`): Fuses vector and graph results using Reciprocal Rank Fusion (RRF).
- **`GraphStore`** (`storage/graph_store.py`): NetworkX-based knowledge graph with `find_shortest_path()`, `get_neighborhood()`, and entity merging via fuzzy name matching.
- **`build_graph_from_chunks`** (`core/graph_builder.py`): Async pipeline that extracts entities/relations from chunks using Ollama LLM and populates the graph store.

### Data Flow

1. **Upload**: PDF → `extract_pdf_pages()` → `chunk_pages()` → ChromaDB (vectors) + `build_graph_from_chunks()` (entities/relations) → SQLite metadata
2. **Query**: `_adaptive_retrieve()` → `QueryClassifier.classify()` → selected retriever → `generate_answer()` with contexts and reasoning path

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `llama3.1:8b` | Ollama chat model |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `CHUNK_SIZE` | `512` | Text chunk size in characters |
| `CHUNK_OVERLAP` | `128` | Overlap between chunks |
| `TOP_K` | `5` | Number of retrieval results |

Data directories (`data/raw_docs/`, `data/chroma_db/`, `data/graph_cache.pkl`, `data/metadata.db`) are created automatically.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload PDF, process, and index |
| `GET` | `/api/v1/retrieval/query` | Query with `mode=auto\|vector\|graph\|hybrid` |
| `GET` | `/api/v1/documents` | List all documents |
| `GET` | `/api/v1/graph/visualize` | Get graph nodes/edges (optional query filter) |
| `GET` | `/api/v1/graph/stats` | Node and edge counts |
