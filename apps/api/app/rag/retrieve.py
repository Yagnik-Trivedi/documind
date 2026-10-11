"""Hybrid retrieval in a single SQL statement: pgvector (dense) + Postgres full-text (lexical),
fused with Reciprocal Rank Fusion. `mode` lets the eval harness run ablations
(dense only / lexical only / hybrid) with the exact same code path."""

from typing import Literal

import numpy as np
from psycopg_pool import AsyncConnectionPool

from app.config import Settings

Mode = Literal["hybrid", "dense", "lexical"]

HYBRID_SQL = """
WITH semantic AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(qvec)s) AS r
  FROM chunks
  WHERE workspace_id = %(ws)s
  ORDER BY embedding <=> %(qvec)s
  LIMIT %(k)s
),
lexical AS (
  SELECT c.id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(c.tsv, q) DESC) AS r
  FROM chunks c, websearch_to_tsquery(%(cfg)s::regconfig, %(q)s) AS q
  WHERE c.workspace_id = %(ws)s AND c.tsv @@ q
  ORDER BY ts_rank_cd(c.tsv, q) DESC
  LIMIT %(k)s
),
fused AS (
  SELECT COALESCE(s.id, l.id) AS id,
         %(w_dense)s  * COALESCE(1.0 / (%(rrf_k)s + s.r), 0)
       + %(w_lex)s    * COALESCE(1.0 / (%(rrf_k)s + l.r), 0) AS rrf,
         s.r AS dense_rank, l.r AS lexical_rank
  FROM semantic s FULL OUTER JOIN lexical l ON s.id = l.id
)
SELECT f.id, f.rrf, f.dense_rank, f.lexical_rank,
       c.content, c.section_path, c.page_start, c.page_end, c.document_id, d.title
FROM fused f
JOIN chunks c ON c.id = f.id
JOIN documents d ON d.id = c.document_id
WHERE f.rrf > 0
ORDER BY f.rrf DESC
LIMIT %(k)s
"""


async def retrieve(
    pool: AsyncConnectionPool,
    settings: Settings,
    query: str,
    qvec: np.ndarray,
    workspace: str,
    mode: Mode = "hybrid",
    k: int | None = None,
) -> list[dict]:
    params = {
        "qvec": qvec,
        "q": query,
        "ws": workspace,
        "cfg": settings.ts_config,
        "k": k or settings.retrieve_k,
        "rrf_k": settings.rrf_k,
        "w_dense": 0.0 if mode == "lexical" else 1.0,
        "w_lex": 0.0 if mode == "dense" else 1.0,
    }
    async with pool.connection() as conn, conn.transaction():
        await conn.execute(f"SET LOCAL hnsw.ef_search = {int(settings.hnsw_ef_search)}")
        cur = await conn.execute(HYBRID_SQL, params)
        return await cur.fetchall()
