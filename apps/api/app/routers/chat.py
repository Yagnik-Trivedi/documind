import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, Field

from app.config import Settings
from app.deps import embedder_dep, llm_dep, pool_dep, settings_dep, workspace_dep
from app.rag.embed import Embedder
from app.rag.llm import LLM
from app.rag.pipeline import Event, answer
from app.rag.retrieve import Mode

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    mode: Mode = "hybrid"


async def _history(pool: AsyncConnectionPool, conversation_id: str) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id::text = %s ORDER BY created_at",
            (conversation_id,),
        )
        return await cur.fetchall()


async def _ensure_conversation(pool, workspace: str, conversation_id: str | None, title: str) -> str:
    async with pool.connection() as conn:
        if conversation_id:
            cur = await conn.execute(
                "SELECT id FROM conversations WHERE id::text = %s AND workspace_id = %s",
                (conversation_id, workspace),
            )
            if not await cur.fetchone():
                raise HTTPException(404, "Conversation not found")
            return conversation_id
        cur = await conn.execute(
            "INSERT INTO conversations (workspace_id, title) VALUES (%s, %s) RETURNING id",
            (workspace, title[:80]),
        )
        return str((await cur.fetchone())["id"])


async def _save(pool, conversation_id: str, question: str, done: dict, citations: list[dict]) -> str:
    async with pool.connection() as conn, conn.transaction():
        await conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s, 'user', %s)",
            (conversation_id, question),
        )
        cur = await conn.execute(
            "INSERT INTO messages (conversation_id, role, content, rewritten_query, model, input_tokens, "
            "output_tokens, latency_ms, ttft_ms, phantom_citations) "
            "VALUES (%s,'assistant',%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (
                conversation_id,
                done["answer"],
                done["rewritten_query"],
                done["model"],
                done["input_tokens"],
                done["output_tokens"],
                done["latency_ms"],
                done["ttft_ms"],
                len(done["phantom_citations"]),
            ),
        )
        message_id = (await cur.fetchone())["id"]
        for c in citations:
            await conn.execute(
                "INSERT INTO message_citations (message_id, marker, chunk_id) VALUES (%s,%s,%s)",
                (message_id, c["marker"], c["chunk_id"]),
            )
    return str(message_id)


def _sse(name: str, data: object) -> str:
    return f"event: {name}\ndata: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat_stream(
    req: ChatRequest,
    pool: AsyncConnectionPool = Depends(pool_dep),
    settings: Settings = Depends(settings_dep),
    llm: LLM = Depends(llm_dep),
    embedder: Embedder = Depends(embedder_dep),
    workspace: str = Depends(workspace_dep),
):
    """Server-Sent Events: meta -> token* -> citations -> done."""
    conversation_id = await _ensure_conversation(pool, workspace, req.conversation_id, req.message)
    history = await _history(pool, conversation_id)

    async def events() -> AsyncIterator[str]:
        citations: list[dict] = []
        try:
            async for ev in answer(
                pool=pool,
                settings=settings,
                llm=llm,
                embedder=embedder,
                question=req.message,
                history=history,
                workspace=workspace,
                mode=req.mode,
            ):
                if ev.name == "citations":
                    citations = ev.data
                if ev.name == "done":
                    message_id = await _save(pool, conversation_id, req.message, ev.data, citations)
                    ev = Event(
                        "done", {**ev.data, "message_id": message_id, "conversation_id": conversation_id}
                    )
                yield _sse(ev.name, ev.data if ev.name != "token" else {"t": ev.data})
        except Exception as exc:  # surface errors to the client instead of a silently dropped stream
            yield _sse("error", {"message": str(exc)[:500]})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/sync")
async def chat_sync(
    req: ChatRequest,
    pool: AsyncConnectionPool = Depends(pool_dep),
    settings: Settings = Depends(settings_dep),
    llm: LLM = Depends(llm_dep),
    embedder: Embedder = Depends(embedder_dep),
    workspace: str = Depends(workspace_dep),
):
    """Same pipeline, one JSON response. Handy for tests, scripts and the eval harness."""
    conversation_id = await _ensure_conversation(pool, workspace, req.conversation_id, req.message)
    history = await _history(pool, conversation_id)
    citations, done = [], {}
    async for ev in answer(
        pool=pool,
        settings=settings,
        llm=llm,
        embedder=embedder,
        question=req.message,
        history=history,
        workspace=workspace,
        mode=req.mode,
    ):
        if ev.name == "citations":
            citations = ev.data
        elif ev.name == "done":
            done = ev.data
    message_id = await _save(pool, conversation_id, req.message, done, citations)
    return {**done, "citations": citations, "message_id": message_id, "conversation_id": conversation_id}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    pool: AsyncConnectionPool = Depends(pool_dep),
    workspace: str = Depends(workspace_dep),
):
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT id, title, created_at FROM conversations WHERE id::text = %s AND workspace_id = %s",
            (conversation_id, workspace),
        )
        conv = await cur.fetchone()
        if not conv:
            raise HTTPException(404, "Conversation not found")
        cur = await conn.execute(
            "SELECT id, role, content, created_at, feedback FROM messages "
            "WHERE conversation_id::text = %s ORDER BY created_at",
            (conversation_id,),
        )
        return {**conv, "messages": await cur.fetchall()}


class Feedback(BaseModel):
    value: int = Field(ge=-1, le=1)


@router.post("/messages/{message_id}/feedback", status_code=204)
async def feedback(message_id: str, body: Feedback, pool: AsyncConnectionPool = Depends(pool_dep)):
    async with pool.connection() as conn:
        cur = await conn.execute(
            "UPDATE messages SET feedback = %s WHERE id::text = %s AND role = 'assistant' RETURNING id",
            (body.value, message_id),
        )
        if not await cur.fetchone():
            raise HTTPException(404, "Message not found")
