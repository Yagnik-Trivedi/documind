# DocuMind: Plan from Zero to Complete

**Start:** Sun Oct 11, 2026 · **v1.0 (resume-ready):** Sun Dec 6, 2026 · **Pace:** solo, part-time (~2–3 h on most days)
**Parallel project:** FraudShield runs in light mode until Oct 31 and then alongside this. DocuMind has priority.

Tick boxes as you go (`- [x]`). Claude Code: only work on the current phase; park new ideas in "Later" at the bottom.

---

## The product in one paragraph
A team (or a person) creates a workspace, uploads documents, and asks questions in plain language.
DocuMind answers only from those documents. Every claim cites the exact page, and clicking a citation
opens the PDF at that page. Under the hood it is built like a production system:
hybrid retrieval, a background ingestion queue, tenant isolation enforced by the database, tracing,
and an evaluation harness that blocks regressions in CI. The public demo workspace contains
government scheme and scholarship PDFs.

## What it proves on a resume
| Skill area | Evidence in this project |
|---|---|
| AI/ML engineering | Hybrid retrieval, reranking, chunking experiments, LLM-as-judge evals, ablation table |
| Backend | Async FastAPI, SSE streaming, Postgres (pgvector, full-text, RLS), queues, idempotent ingestion |
| Full stack | Next.js 16 app: chat, PDF viewer with cited page, auth, workspaces |
| Production habits | CI quality gates, tracing, rate limits, secrets hygiene, load test, deployed demo |

---

## Definition of complete (v1.0, Dec 6)
- [ ] Public demo URL; anyone can try the public workspace; sign-in gives private workspaces
- [ ] Answers cite pages; clicking a citation opens the PDF at that page
- [ ] Workspaces isolated by Postgres Row-Level Security (tests prove it)
- [ ] Ingestion through a queue (arq + Redis) with progress; files in object storage (Cloudflare R2)
- [ ] Golden set of ≥ 80 questions; ablation table (dense / hybrid / +rerank / +contextual headers / chunk sizes) in README
- [ ] CI: lint, unit + DB tests, and an eval quality gate on a mini golden set
- [ ] Tracing (Langfuse): per-step latency, tokens, cost; load test with p95 time-to-first-token
- [ ] README with architecture, results, limitations; 2-minute demo video; blog post; resume bullets with real numbers
- [ ] Tagged `v1.0.0`

---

## Phase 0: Foundation ✅ (Sun Oct 11)
- [x] Repo structure, MIT license, `.gitignore`, `.env.example`, docker-compose (Postgres + pgvector), CI workflow, pre-commit config
- [x] FastAPI: migrations, connection pool, upload → parse (page-aware) → chunk (section-aware) → embed → index
- [x] Hybrid retrieval (pgvector + full-text, RRF) with dense / lexical / hybrid modes for ablations
- [x] Chat: follow-up rewriting, streamed SSE answers, `<think>` stripping, citation resolution + phantom detection, persistence, feedback
- [x] Provider-agnostic LLM/embeddings (Gemini default, Ollama local, fake for tests); Matryoshka truncation for large embeddings
- [x] Scripts: `list_models`, `ingest_folder`, `ask`; 18 tests passing
- [ ] **You, tonight:** GitHub repo + push; Gemini API key into `.env` (or Ollama); run the "Very first session" prompt

## Phase 1: Real data + first usable app (Oct 12 – Oct 18)
Goal: chat with real documents in a browser.
- [ ] Choose models (chat, fast, embedding) and EMBED_DIM; record them in decisions.md (PROMPTS 1.1)
- [ ] Collect 40–60 text-based demo PDFs into `corpus/` with `sources.csv` (see corpus/README.md)
- [ ] Ingest; fix parser issues found on real PDFs (repeated headers/footers, page numbers, tables, headings), each with a test (PROMPTS 1.3)
- [ ] `GET /documents/{id}/file` to serve PDFs (PROMPTS 1.4)
- [ ] Scaffold `apps/web` (Next.js 16) with chat (SSE), citation chips, sources panel, PDF viewer at the cited page, documents page (PROMPTS 1.5)
- **Exit check:** ask → cited answer → click → PDF opens at the right page, on real documents.

## Phase 2: Quality science (Oct 19 – Oct 28)
Goal: numbers that prove the retrieval is good, and the experiments that improved it.
- [ ] Golden set v1: 50 questions in `evals/golden.jsonl` (single / multi-hop / unanswerable / paraphrase; see evals/README.md)
- [ ] `evals/run_eval.py`: Recall@5, MRR, faithfulness + relevancy (LLM judge), unanswerable accuracy, phantom-citation rate, TTFT; writes `eval_runs` + `evals/results.md` (PROMPTS 2.1)
- [ ] Ablation 1: dense vs lexical vs hybrid
- [ ] Reranking: LLM listwise reranker with FAST_MODEL; optional local cross-encoder (bge-reranker-v2-m3 on your GPU); keep whichever wins (PROMPTS 2.2)
- [ ] Ablation 2: contextual chunk headers on/off; chunk size 300 / 450 / 700
- [ ] Golden set to 80 questions; re-run; first README results table
- **Exit check:** `evals/results.md` has at least 6 comparable rows, and README shows the winning config with its numbers.

## Phase 3: Multi-tenant product (Oct 29 – Nov 8)
Goal: real users with private, isolated workspaces.
- [ ] Better Auth in the web app (Google + email), organization plugin = workspaces, invites, roles (owner / editor / viewer)
- [ ] FastAPI verifies the Better Auth JWT via JWKS; membership check; `SET LOCAL app.workspace_id` per transaction (PROMPTS 3.1)
- [ ] Migration: Row-Level Security on documents, chunks, conversations, messages; API DB role is not a superuser; isolation tests
- [ ] Web: workspace switcher, members page, upload page with live status
- [ ] Public read-only demo workspace for visitors
- **Exit check:** user A can never see user B's documents, even through a deliberately unfiltered query in a test.

## Phase 4: Production plumbing (Nov 9 – Nov 18)
- [ ] Ingestion via arq + Redis worker with retries; SSE `GET /documents/{id}/events` for progress (PROMPTS 4.1)
- [ ] Files in Cloudflare R2 with presigned uploads (MinIO locally)
- [ ] Rate limiting per user/IP, request timeouts, max sizes, per-workspace daily token budget (PROMPTS 4.2)
- [ ] Langfuse tracing around rewrite / retrieve / rerank / generate; cost per answer stored on messages
- [ ] Docker Compose: db, redis, minio, api, worker, web; one command to run everything

## Phase 5: Deploy + CI quality gate (Nov 19 – Nov 28)
- [ ] Deploy: Postgres (Neon/Supabase), Redis (Upstash), API + worker (Render/Fly/Railway), web (Vercel/Netlify), R2. Write `docs/DEPLOY.md` (PROMPTS 5.1)
- [ ] CI: DB tests on every PR; DeepEval quality gate on a 15-question mini set; nightly full eval
- [ ] Load test (Locust/k6): 20 concurrent users; record p50/p95 TTFT and error rate
- [ ] Uptime monitor; error tracking (Sentry)

## Phase 6: Ship v1.0 (Nov 29 – Dec 6)
- [ ] README final: problem, demo link, GIF, architecture diagram, results + ablation table, limitations
- [ ] 2-minute demo video; blog post ("Hybrid search + citations: what actually improved my RAG")
- [ ] Fill the resume bullets in `TODOP/01-DocuMind…md` with measured numbers
- [ ] Tag `v1.0.0`

## v1.1 stretch (December, only after v1.0)
- [ ] **Eligibility checker** for the demo corpus: extract scheme criteria as structured JSON at ingest; profile form → met / not met / unknown per criterion, with citations
- [ ] Multilingual Q&A (Hindi/Gujarati) with an eval subset
- [ ] Semantic cache for repeated questions
- [ ] ParadeDB `pg_search` (true BM25) vs built-in full-text, as an ablation (AGPL license note)

---

## Risks and mitigations
| Risk | Mitigation |
|---|---|
| Free-tier rate limits on the LLM API slow evals | Run evals with FAST_MODEL as the judge; cache judge results by (question, answer) hash; Ollama for bulk dev runs |
| Embedding model or EMBED_DIM changes after ingest | Decide in Phase 1 and record it; changing later = reset DB + re-ingest (script it) |
| Government PDFs are scans | Filter while collecting (try selecting text); OCR is in "Later" |
| Two projects in parallel | DocuMind first; FraudShield light until Oct 31; each phase has an exit check, so stop at a clean boundary |
| Exams | Shift dates, keep the order; never start a phase you can't finish within ~10 days |
| Scope creep | CLAUDE.md rule 9; the Later list |

## Later (parking lot; not before v1.0)
- OCR for scanned PDFs
- Replace pgvector with Annex (your own C++ HNSW index) behind the retrieval interface
- Put PIIGuard in front of LLM calls
- TraceLens instead of Langfuse
- Slack/WhatsApp front-end
