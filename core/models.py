from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RetrievalStrategy(str, Enum):
    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    filename: str
    page_count: int = 0
    summary: str = ""
    status: DocumentStatus = DocumentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    doc_id: str
    content: str
    page_number: int
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class Entity(BaseModel):
    id: str
    name: str
    type: str
    source_doc: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class Relation(BaseModel):
    source: str
    target: str
    relation: str
    evidence: str = ""
    source_doc: str = ""


class SourceReference(BaseModel):
    doc_id: str
    filename: str
    page: int
    text: str


class QueryResult(BaseModel):
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    strategy_used: RetrievalStrategy = RetrievalStrategy.VECTOR
    reasoning_path: list[str] = Field(default_factory=list)
    confidence: float = 0.0
