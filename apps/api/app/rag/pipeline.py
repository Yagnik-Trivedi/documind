"""The question-answering pipeline as a stream of events:
condense -> embed -> hybrid retrieve -> generate (streamed) -> resolve citations."""

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from psycopg_pool import AsyncConnectionPool

from app.config import Settings
from app.rag.citations import resolve
from app.rag.embed import Embedder
from app.rag.llm import LLM, Usage
from app.rag.prompt import build_condense_messages, build_messages
from app.rag.retrieve import Mode, retrieve
from app.rag.streaming import ThinkStripper

NOT_FOUND = "I couldn't find this in the uploaded documents. Try rephrasing, or upload the relevant document."


@dataclass
class Event:
    name: str  # "meta" | "token" | "citations" | "done"
    data: object


async def answer(
    *,
    pool: AsyncConnectionPool,
    settings: Settings,
    llm: LLM,
    embedder: Embedder,
    question: str,
    history: list[dict],
    workspace: str,
    mode: Mode = "hybrid",
) -> AsyncIterator[Event]:
    t0 = time.perf_counter()

    query = question
    if history:
        try:
            rewritten = await llm.complete(build_condense_messages(question, history), settings.fast_model)
            query = rewritten or question
        except Exception:  # query rewriting is an optimisation; never fail the request on it
            query = question
    yield Event("meta", {"rewritten_query": query if query != question else None})

    qvec = (await asyncio.to_thread(embedder.embed, [query]))[0]
    hits = await retrieve(pool, settings, query, qvec, workspace, mode=mode)
    context = hits[: settings.context_k]
    t_retrieved = time.perf_counter()

    usage = Usage()
    full, ttft = "", None
    if not context:
        full = NOT_FOUND
        yield Event("token", full)
    else:
        stripper = ThinkStripper()
        async for piece in llm.stream(build_messages(question, context), settings.chat_model, usage):
            visible = stripper.feed(piece)
            if visible:
                ttft = ttft or time.perf_counter()
                full += visible
                yield Event("token", visible)
        tail = stripper.flush()
        if tail:
            full += tail
            yield Event("token", tail)

    citations, phantom = resolve(full, context)
    yield Event("citations", citations)
    t_end = time.perf_counter()
    yield Event(
        "done",
        {
            "answer": full,
            "rewritten_query": query if query != question else None,
            "phantom_citations": phantom,
            "context_chunk_ids": [str(c["id"]) for c in context],
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "retrieval_ms": round((t_retrieved - t0) * 1000),
            "ttft_ms": round((ttft - t0) * 1000) if ttft else None,
            "latency_ms": round((t_end - t0) * 1000),
            "model": settings.chat_model,
        },
    )
