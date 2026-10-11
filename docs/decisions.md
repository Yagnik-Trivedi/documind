# Decision Log

Short records of why we chose things. New decision → new entry at the bottom. Interviewers ask exactly these questions.

### D1: Postgres + pgvector instead of a separate vector database (Oct 11)
One database for documents, chunks, vectors, full-text search and chat history. Hybrid search is a
single SQL query, with transactions and backups in one place. Qdrant/Pinecone would add a second
system to keep in sync for no benefit at our scale (thousands of chunks).

### D2: Hybrid retrieval with Reciprocal Rank Fusion (Oct 11)
Dense vectors miss exact tokens (scheme codes, acronyms like "PMAY-G"); keyword search misses
paraphrases. RRF fuses *ranks*, not raw scores, so it needs no score normalisation between cosine
distance and `ts_rank_cd`. k=60 is the standard constant and is tunable. Built-in `tsvector` is not
true BM25. ParadeDB `pg_search` is an option later, but it's AGPL-licensed.

### D3: FastAPI (Python) backend, Next.js frontend (Oct 11)
The RAG/ML ecosystem is Python; async streaming is first-class in FastAPI. Next.js is the frontend
skill already on my resume and deploys easily.

### D4: Any OpenAI-compatible endpoint; Gemini default, Ollama local (Oct 11)
Gemini, Ollama, OpenAI, Groq and most hosts expose the OpenAI API, so one client (`openai` SDK +
`base_url`) covers them all and switching is a config change. Gemini's free tier gives strong
quality for development and the hosted demo. Ollama gives a free, private, offline mode on the RTX 5060.
A fast/cheap model handles rewriting, judging and reranking; a stronger model writes answers.

### D4b: Matryoshka truncation for embeddings (Oct 11)
Gemini embeddings return 3072 dims, but pgvector's HNSW index supports at most 2000. Matryoshka-trained
models keep most quality in their first dims, so we store the first `EMBED_DIM` (768) and re-normalise.
Fewer dims also mean a smaller index and faster search. To be verified in the Phase 2 ablation (768 vs 1536).

### D5: Fake providers for tests (Oct 11)
`LLM_PROVIDER=fake` / `EMBED_PROVIDER=fake` let CI run the full pipeline offline, deterministically
and for free. Real-model quality is measured separately by the eval harness.

### D6: Plain SQL migrations instead of Alembic (Oct 11)
The schema is small and hand-written SQL is easier to read and explain. Revisit if the schema churns a lot.

### D7: Background tasks now, queue later (Oct 11)
FastAPI BackgroundTasks are enough for a curated corpus ingested by admins. Phase 4 moves to arq + Redis
for retries and restart safety.

### D8: Models chosen (fill in during Phase 1)
- CHAT_MODEL:
- FAST_MODEL:
- EMBED_MODEL / EMBED_DIM:
- Reason:

### D9: Reranker choice (fill in after the Phase 2 experiment)
