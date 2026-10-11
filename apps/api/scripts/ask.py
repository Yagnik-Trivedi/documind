"""Ask a question from the terminal, streaming the answer, then print the citations.

Usage (from apps/api):  uv run python -m scripts.ask "Who is eligible for PM-KISAN?" [--mode dense|lexical|hybrid]
"""

import argparse
import asyncio

from app.config import get_settings
from app.db import make_pool
from app.rag.embed import make_embedder
from app.rag.llm import make_llm
from app.rag.pipeline import answer


async def main(question: str, mode: str) -> None:
    s = get_settings()
    pool = make_pool(s)
    await pool.open()
    try:
        async for ev in answer(
            pool=pool,
            settings=s,
            llm=make_llm(s),
            embedder=make_embedder(s),
            question=question,
            history=[],
            workspace=s.default_workspace,
            mode=mode,
        ):
            if ev.name == "token":
                print(ev.data, end="", flush=True)
            elif ev.name == "citations":
                print("\n\nSources:")
                for c in ev.data:
                    print(f"  [{c['marker']}] {c['title']}, p.{c['page']}  {c['section']}")
            elif ev.name == "done":
                d = ev.data
                print(
                    f"\nretrieval {d['retrieval_ms']} ms | first token {d['ttft_ms']} ms | "
                    f"total {d['latency_ms']} ms | phantom citations {d['phantom_citations']}"
                )
    finally:
        await pool.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--mode", default="hybrid", choices=["hybrid", "dense", "lexical"])
    a = ap.parse_args()
    asyncio.run(main(a.question, a.mode))
