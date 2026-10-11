"""Document ingestion: parse -> chunk -> embed -> index.

Runs as a FastAPI background task for now. Moving it to a real queue (arq + Redis) is on the
roadmap so that ingestion survives API restarts and can scale independently."""

import asyncio
import logging

from psycopg_pool import AsyncConnectionPool

from app.config import Settings
from app.rag.chunk import chunk_blocks, embedding_text
from app.rag.embed import Embedder
from app.rag.parse import parse_file

log = logging.getLogger("documind.ingest")


async def _set_status(pool: AsyncConnectionPool, doc_id: str, status: str, **extra) -> None:
    cols = ", ".join(f"{k} = %({k})s" for k in extra)
    sql = f"UPDATE documents SET status = %(status)s{', ' + cols if cols else ''} WHERE id = %(id)s"
    async with pool.connection() as conn:
        await conn.execute(sql, {"status": status, "id": doc_id, **extra})


async def ingest_document(
    pool: AsyncConnectionPool, settings: Settings, embedder: Embedder, doc_id: str
) -> int:
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
        doc = await cur.fetchone()
    if doc is None:
        raise ValueError(f"document {doc_id} not found")

    try:
        await _set_status(pool, doc_id, "parsing", error=None)
        blocks, page_count = await asyncio.to_thread(parse_file, doc["storage_path"])
        chunks = chunk_blocks(blocks)
        if not chunks:
            raise ValueError("No extractable text. Scanned PDFs need OCR (not supported yet).")

        await _set_status(pool, doc_id, "embedding", page_count=page_count)
        texts = [embedding_text(doc["title"], c) for c in chunks]
        vectors = await asyncio.to_thread(embedder.embed, texts)

        rows = [
            (
                doc["workspace_id"],
                doc_id,
                c.ordinal,
                c.section_path,
                c.page_start,
                c.page_end,
                c.content,
                c.token_count,
                v,
            )
            for c, v in zip(chunks, vectors, strict=True)
        ]
        async with pool.connection() as conn, conn.transaction():
            await conn.execute("DELETE FROM chunks WHERE document_id = %s", (doc_id,))
            async with conn.cursor() as cur:
                await cur.executemany(
                    "INSERT INTO chunks (workspace_id, document_id, ordinal, section_path, page_start, "
                    "page_end, content, token_count, embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    rows,
                )
        await _set_status(pool, doc_id, "ready", chunk_count=len(chunks))
        log.info("ingested %s: %d pages, %d chunks", doc["title"], page_count, len(chunks))
        return len(chunks)
    except Exception as exc:
        log.exception("ingestion failed for %s", doc_id)
        await _set_status(pool, doc_id, "failed", error=str(exc)[:1000])
        raise
