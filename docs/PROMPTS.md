# Claude Code Prompts

Paste these into Claude Code opened at the repo root (`D:\projects\documind`). One task per session works best.
Claude Code reads `CLAUDE.md` automatically. Slash commands in `.claude/commands/`: `/start-session`, `/next-task`, `/end-session`.

---

## ▶ Very first session (run once)
```
Step 0: run the PowerShell commands in setup/README.md to move the Claude Code slash commands, the CI
workflow and the pre-commit config into place, delete docs/HACKATHON.md (no longer used), then delete setup/.
Then read CLAUDE.md, README.md, docs/PLAN.md and docs/PROGRESS.md and help me get this running on Windows:
1. Check git, docker, uv and node are installed (version commands); tell me what's missing.
2. Copy .env.example to .env if it doesn't exist. Do NOT print or ask me to paste my API key; I'll edit .env myself.
3. Start the database with docker compose, run `uv sync` in apps/api, and run the unit tests.
4. Run the full test suite with TEST_DATABASE_URL pointing at documind_test.
5. Initialise git if needed, make the first commit, and show me the commands to create the GitHub repo and push.
Report what passed and what failed. Don't change application code in this session.
```

## ▶ Start / end of every session
- Start: `/start-session` (or: "Read CLAUDE.md, PROGRESS.md and the current phase of PLAN.md; summarise in 5 lines; propose the next task and wait.")
- End: `/end-session` (or: "Run ruff + tests, update PROGRESS.md and PLAN.md ticks and the CLAUDE.md status line, show git status, propose a commit message. Don't push.")

---

## Phase 1: Real data + first usable app

### 1.1 Pick models
```
My key (or Ollama setup) is in .env. Run `uv run python -m scripts.list_models` in apps/api and recommend
exact, pinned ids for CHAT_MODEL, FAST_MODEL and EMBED_MODEL (Gemini: strip the "models/" prefix).
Probe the embedding dimension with --probe-embed and confirm EMBED_DIM (≤ 2000; truncation is on).
Test one real chat call with scripts/ask.py on a tiny document. Update .env (and .env.example with
placeholders/defaults only), record the choices and reasons in docs/decisions.md (D8), then reset the
local DB (docker compose down -v; docker compose up -d db) so the vector column matches EMBED_DIM.
```

### 1.2 Corpus check (after I put PDFs in corpus/)
```
I've put PDFs in corpus/ with corpus/sources.csv. Write scripts/check_corpus.py that, for each PDF, reports:
pages, characters per page (flag likely scans with < 200 chars/page), detected headings, and whether it's in
sources.csv. Show me the report and list the files I should replace.
```

### 1.3 Parser hardening on real PDFs
```
Ingest corpus/ with scripts/ingest_folder.py and report per document: pages, chunks, headings, failures.
Fix the top problems (likely: repeated page headers/footers, page numbers inside text, tables flattened
badly, headings not detected). For each fix, add a unit test with a small synthetic PDF built with pymupdf.
Keep parse.py readable.
```

### 1.4 Serve PDFs
```
Add GET /documents/{id}/file that streams the stored PDF (correct content-type, inline disposition, 404 for
other workspaces). Add a test. Make sure citation payloads include document_id, page and a snippet the
frontend can highlight.
```

### 1.5 Scaffold the web app
```
Create apps/web: Next.js 16 (App Router, TypeScript, Tailwind, ESLint) + shadcn/ui.
Pages:
- / : short intro, 4 example questions, chat box
- /chat : streaming chat that POSTs to `${NEXT_PUBLIC_API_URL}/chat` and parses Server-Sent Events (meta, token,
  citations, done, error; see docs/ARCHITECTURE.md). Render [n] markers as clickable chips; a sources panel with
  title, page and snippet.
- citation click → side-panel PDF viewer (react-pdf) at that page, loading `/documents/{id}/file`
- /documents : list with status + upload
Write a small typed SSE client (fetch + ReadableStream, since EventSource can't POST). Mobile-friendly. Add
NEXT_PUBLIC_API_URL to .env.example, `npm run lint`, and a Playwright smoke test.
```

---

## Phase 2: Quality science

### 2.1 Golden set + eval runner
```
Help me build evals/golden.jsonl (format: evals/README.md and golden.template.jsonl): propose 20 candidate
questions per document batch with their page, and I'll verify and edit them. Then write evals/run_eval.py that
for each item runs retrieval (mode configurable) and the full pipeline and computes: Recall@5 and MRR against
relevant (filename, page) pairs; faithfulness and answer relevancy with an LLM judge (FAST_MODEL, rubric in
evals/judge_prompt.md, cached by hash in evals/.cache); unanswerable accuracy; phantom-citation rate;
p50/p95 TTFT. Write to the eval_runs table and append a row to evals/results.md. Support
`--modes dense,lexical,hybrid` and `--limit N`. Unit-test the metric functions.
```

### 2.2 Reranking experiment
```
Add an optional reranking step (setting RERANK=none|llm|cross_encoder). llm: send the question + top 20
chunks (truncated) to FAST_MODEL and ask for a JSON list of the 8 most relevant indices; fall back to the
original order on any parse error. cross_encoder: BAAI/bge-reranker-v2-m3 via sentence-transformers (optional
extra, runs on my GPU). Unit-test parsing/fallback with the fake LLM. Run evals for none/llm/cross_encoder and
record results in evals/results.md and docs/decisions.md (D9).
```

### 2.3 Chunking ablation
```
Make chunk target size and contextual headers configurable (CHUNK_TARGET_TOKENS, CONTEXTUAL_HEADERS). Write
scripts/reindex.py to re-chunk and re-embed everything into a fresh DB for a given config. Run evals for
300/450/700 tokens × headers on/off and add the rows to evals/results.md. Then update the README results table
with the winning configuration.
```

---

## Phase 3: Multi-tenant product

### 3.1 Auth + workspaces + RLS
```
Add Better Auth to apps/web (Google + email/password) with the organization plugin as workspaces (invites,
roles owner/editor/viewer) and the JWT plugin exposing JWKS. In FastAPI, replace workspace_dep with a
dependency that verifies the JWT via JWKS (pyjwt[crypto]), checks membership and role, and runs
`SET LOCAL app.workspace_id` inside each request transaction. Add a migration enabling Row-Level Security on
documents, chunks, conversations and messages, with a non-superuser API role. Tests: user A cannot read
user B's data even through a query that forgets the WHERE clause; viewers can't upload or delete.
```
```
Add a public read-only "demo" workspace that signed-out visitors can chat with, plus a workspace switcher,
members page and per-workspace documents page in the web app.
```

---

## Phase 4: Production plumbing

### 4.1 Queue + object storage
```
Move ingestion to an arq worker (Redis), keeping ingest_document as the job function, with retries and a
`failed` state. Add SSE GET /documents/{id}/events for progress. Store files in S3-compatible storage
(MinIO locally, Cloudflare R2 in prod) with presigned uploads from the browser. Add redis, minio and worker to
docker-compose. Tests use arq's test utilities / a fake storage class.
```

### 4.2 Safety + tracing
```
Add: per-user/IP rate limiting (Redis token bucket), max message length, LLM request timeouts, a per-workspace
DAILY_TOKEN_BUDGET (friendly 429 when exceeded), structured JSON logs, and Langfuse tracing around rewrite /
retrieve / rerank / generate behind LANGFUSE_* settings. Store cost per answer on messages using a
model_prices table. Tests for the limits.
```

---

## Phase 5: Deploy + CI gate

### 5.1 Deployment
```
Help me deploy: Postgres on Neon (pgvector enabled), Redis on Upstash, API + worker from apps/api/Dockerfile
on <Render|Fly|Railway>, web on <Vercel|Netlify>, files on R2. Walk me through each step, write docs/DEPLOY.md
with exact settings (env var NAMES only, never values), and ingest the demo corpus into production from my machine.
```

### 5.2 CI quality gate + load test
```
Add a DeepEval pytest quality gate on a 15-question mini golden set (thresholds in evals/thresholds.toml) that
runs in CI when a GEMINI key secret is present (skip otherwise), plus a nightly workflow for the full eval. Then
write a Locust load test (20 users) and record p50/p95 TTFT and the error rate in README.
```

---

## Phase 6: Ship v1.0
```
Draft the final README (problem, demo link, GIF placeholder, architecture, results + ablation table from
evals/results.md, limitations, how to run), a 2-minute demo video script, and a blog post outline. Then fill
the resume bullets in D:\projects\TODOP\01-DocuMind-production-RAG-platform.md with the measured numbers.
```

---

## Handy prompts
- **Debug:** `This fails: <paste error>. Reproduce it with a test first, then fix it. Explain the root cause in 3 lines.`
- **Review before commit:** `Review my uncommitted changes like a strict senior engineer: bugs, security, missing tests, naming. List issues by severity; don't fix yet.`
- **Interview prep:** `Explain how <file/feature> works as if I'm in an interview: 6–8 sentences, then 5 likely follow-up questions with short answers.`
