import asyncio
import hashlib
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile
from psycopg_pool import AsyncConnectionPool

from app.config import Settings
from app.deps import embedder_dep, pool_dep, settings_dep, workspace_dep
from app.ingest import ingest_document
from app.rag.embed import Embedder
from app.rag.parse import SUPPORTED

router = APIRouter(prefix="/documents", tags=["documents"])

PUBLIC_COLS = "id, title, filename, mime_type, source_url, status, error, page_count, chunk_count, created_at"


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


async def _safe_ingest(pool, settings, embedder, doc_id: str) -> None:
    try:
        await ingest_document(pool, settings, embedder, doc_id)
    except Exception:
        pass  # status='failed' + error are already stored on the document row


@router.post("", status_code=201)
async def upload(
    background: BackgroundTasks,
    file: UploadFile,
    title: str | None = Form(default=None),
    source_url: str | None = Form(default=None),
    pool: AsyncConnectionPool = Depends(pool_dep),
    settings: Settings = Depends(settings_dep),
    embedder: Embedder = Depends(embedder_dep),
    workspace: str = Depends(workspace_dep),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED:
        raise HTTPException(415, f"Unsupported file type '{ext}'. Allowed: {', '.join(SUPPORTED)}")
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File larger than {settings.max_upload_mb} MB")
    if ext == ".pdf" and not data.startswith(b"%PDF-"):
        raise HTTPException(415, "File does not look like a PDF")

    sha = hashlib.sha256(data).hexdigest()
    path = Path(settings.storage_dir) / f"{sha}{ext}"
    await asyncio.to_thread(_write_file, path, data)

    async with pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO documents (workspace_id, title, filename, mime_type, sha256, storage_path, source_url) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (workspace_id, sha256) DO NOTHING "
            f"RETURNING {PUBLIC_COLS}",
            (
                workspace,
                title or Path(file.filename).stem,
                file.filename,
                SUPPORTED[ext],
                sha,
                str(path.resolve()),
                source_url,
            ),
        )
        row = await cur.fetchone()
        if row is None:  # same file already uploaded
            cur = await conn.execute(
                f"SELECT {PUBLIC_COLS} FROM documents WHERE workspace_id = %s AND sha256 = %s",
                (workspace, sha),
            )
            return {**(await cur.fetchone()), "duplicate": True}

    background.add_task(_safe_ingest, pool, settings, embedder, str(row["id"]))
    return {**row, "duplicate": False}


@router.get("")
async def list_documents(
    pool: AsyncConnectionPool = Depends(pool_dep), workspace: str = Depends(workspace_dep)
):
    async with pool.connection() as conn:
        cur = await conn.execute(
            f"SELECT {PUBLIC_COLS} FROM documents WHERE workspace_id = %s ORDER BY created_at DESC",
            (workspace,),
        )
        return await cur.fetchall()


@router.get("/{doc_id}")
async def get_document(
    doc_id: str, pool: AsyncConnectionPool = Depends(pool_dep), workspace: str = Depends(workspace_dep)
):
    async with pool.connection() as conn:
        cur = await conn.execute(
            f"SELECT {PUBLIC_COLS} FROM documents WHERE id::text = %s AND workspace_id = %s",
            (doc_id, workspace),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    return row


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str, pool: AsyncConnectionPool = Depends(pool_dep), workspace: str = Depends(workspace_dep)
):
    async with pool.connection() as conn:
        cur = await conn.execute(
            "DELETE FROM documents WHERE id::text = %s AND workspace_id = %s RETURNING storage_path",
            (doc_id, workspace),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    await asyncio.to_thread(Path(row["storage_path"]).unlink, missing_ok=True)
