from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from loguru import logger

from core.models import Document, DocumentStatus


class MetadataStore:
    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    page_count INTEGER DEFAULT 0,
                    summary TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
        logger.info(f"MetadataStore initialised at {self._db_path}")

    def add_document(self, doc: Document) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO documents (id, filename, page_count, summary, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    doc.id,
                    doc.filename,
                    doc.page_count,
                    doc.summary,
                    doc.status.value,
                    doc.created_at.isoformat(),
                ),
            )
            conn.commit()

    def update_status(self, doc_id: str, status: DocumentStatus) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE documents SET status = ? WHERE id = ?",
                (status.value, doc_id),
            )
            conn.commit()

    def update_summary(self, doc_id: str, summary: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE documents SET summary = ? WHERE id = ?",
                (summary, doc_id),
            )
            conn.commit()

    def get_document(self, doc_id: str) -> Document | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_document(row)

    def list_documents(self) -> list[Document]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_document(r) for r in rows]

    def delete_document(self, doc_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()

    @staticmethod
    def _row_to_document(row: sqlite3.Row) -> Document:
        return Document(
            id=row["id"],
            filename=row["filename"],
            page_count=row["page_count"],
            summary=row["summary"],
            status=DocumentStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
