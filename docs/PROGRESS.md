# Progress Log

Newest entry on top. One entry per working session: what was done, what's next, open issues.

---

## 2026-10-11: Project started (Phase 0)
**Done**
- Repo structure and docs (PLAN, NEEDS, ARCHITECTURE, PROMPTS, decisions), CLAUDE.md
- Backend vertical slice in `apps/api`: SQL migrations; page-aware PDF/MD parsing; section-aware chunking;
  provider-agnostic embeddings (Gemini/Ollama/any OpenAI-compatible, local BGE-M3, fake) with
  Matryoshka truncation; hybrid retrieval (pgvector + full-text, RRF; dense/lexical/hybrid modes);
  streamed chat over SSE with follow-up rewriting, `<think>` stripping, citation resolution and
  phantom-citation detection; persistence and feedback
- Scripts: `list_models`, `ingest_folder`, `ask`
- 18 tests passing (unit + end-to-end against Postgres with fake providers); ruff clean
- docker-compose (Postgres 17 + pgvector, API), Dockerfile, CI workflow, pre-commit (gitleaks, ruff)
- Decided: solo resume project (not a hackathon entry); Gemini by default, Ollama for local runs

**Next (Phase 1)**
- GitHub repo + push; Gemini key (or Ollama) in `.env`; run the "Very first session" prompt
- Pick models + EMBED_DIM (PROMPTS 1.1), collect the demo corpus, harden the parser, scaffold the web app

**Open issues / notes**
- Confirm Gemini's exact model ids with `scripts/list_models.py`; pin versions before running evals
- Run `pre-commit autoupdate` once to bump hook versions
