# CLAUDE.md: instructions for Claude Code in this repo

Read this file first in every session, then `docs/PROGRESS.md` (where we left off) and the current
phase in `docs/PLAN.md`. When you finish a task, tick it in PLAN.md and add a dated entry to PROGRESS.md.

## What this project is
**DocuMind** is a multi-tenant "ask your documents" platform built the way a company would build an
internal knowledge assistant. Documents are parsed page-aware, retrieval is hybrid (vector + keyword),
answers stream with **citations to the exact page**, and quality is **measured** with an eval harness
that runs in CI.
- It is a **solo resume project** for Yagnik (3rd-year CS, aiming at SDE + AI/ML engineering roles).
  The bar: deployed, tested, measured, and explainable in an interview.
- The demo corpus is public government documents (schemes, scholarships, circulars). The platform
  itself is domain-agnostic.
- LLM and embeddings use any **OpenAI-compatible endpoint**: Google Gemini by default, Ollama for
  fully local runs. Never hard-code a provider.

## Repo map
```
apps/api/            FastAPI backend (Python 3.11+, uv)
  app/main.py        app + lifespan (migrations, pool, providers)
  app/config.py      ALL settings (env vars) live here
  app/rag/           parse.py chunk.py embed.py retrieve.py prompt.py llm.py streaming.py citations.py pipeline.py
  app/routers/       documents.py (upload/list/delete), chat.py (SSE + sync + feedback)
  app/ingest.py      parse -> chunk -> embed -> insert
  migrations/        plain SQL, applied in order by app/migrate.py ({{EMBED_DIM}}, {{TS_CONFIG}} templated)
  scripts/           list_models.py, ingest_folder.py, ask.py
  tests/             test_units.py (no DB), test_api.py (needs TEST_DATABASE_URL)
apps/web/            Next.js 16 frontend (scaffolded in Phase 1; see docs/PROMPTS.md)
corpus/              demo PDFs + sources.csv (official URLs). PDFs are gitignored.
evals/               golden question set, eval runner, results.md
docs/                PLAN, PROGRESS, ARCHITECTURE, NEEDS, PROMPTS, decisions
```

## Commands (Windows PowerShell; run from repo root unless noted)
```powershell
docker compose up -d db                        # Postgres 17 + pgvector on localhost:5432
cd apps/api
uv sync                                        # install deps (add --extra local for BGE-M3)
uv run uvicorn app.main:app --reload           # API on http://localhost:8000 (docs at /docs)
uv run pytest -q                               # unit tests (DB tests skip without TEST_DATABASE_URL)
$env:TEST_DATABASE_URL="postgresql://documind:documind@localhost:5432/documind_test"; uv run pytest -q
uv run ruff check . ; uv run ruff format .     # lint + format
uv run python -m scripts.list_models           # model ids at the configured endpoint
uv run python -m scripts.ingest_folder ../../corpus
uv run python -m scripts.ask "your question"   # --mode dense|lexical|hybrid
```

## Rules (follow strictly)
1. **Never commit secrets.** Keys only in `.env` (gitignored). `.env.example` documents every variable
   with a placeholder. If you see a real key in a tracked file, stop and tell the user.
2. **Tests stay green.** Run the tests (with TEST_DATABASE_URL when touching SQL/routers) and
   `uv run ruff check .` before calling a task done. Every feature gets tests.
3. **Config goes through `app/config.py`.** No `os.environ` reads elsewhere. New settings get a default
   and a line in `.env.example`.
4. **Providers stay swappable.** Chat/embeddings go through `make_llm` / `make_embedder`. Tests use
   `LLM_PROVIDER=fake` and `EMBED_PROVIDER=fake`, so tests never call paid APIs or the network.
5. **SQL:** parameterised queries only. Schema changes = a NEW numbered file in `migrations/`
   (never edit an applied migration).
6. **Citations are the product.** Every answer goes through `citations.resolve`; never show `<think>`
   content; keep the "not found" path working.
7. **Measure claims.** Quality changes (chunking, retrieval, reranking, prompts) are judged by
   `evals/run_eval.py` results, recorded in `evals/results.md`. Never invent numbers for the README.
8. **Simple and explainable.** Prefer readable code to clever abstractions; a new framework or service
   needs a reason in `docs/decisions.md`.
9. **Scope discipline:** work only on the current phase of `docs/PLAN.md`; ideas go to "Later".
10. Small conventional commits (`feat(api): …`, `fix(rag): …`, `docs: …`). Don't push unless asked.
11. The user is on **Windows 11** (PowerShell, Docker Desktop, RTX 5060 8 GB, Ollama installed).
    Give Windows-friendly commands.

## Current status (update this line when it changes)
Phase 0 done: backend vertical slice works with fake providers (18 tests passing). Next: Phase 1 in PLAN.md.
