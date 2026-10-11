# DocuMind

**Ask questions about your documents and get answers that cite the exact page, with retrieval quality measured on every change.**

DocuMind is a multi-tenant retrieval-augmented generation (RAG) platform: upload PDFs, ask questions
in plain language, and get streamed answers where every claim links to the page it came from. It's
built like a production system: hybrid search, background ingestion, tenant isolation, an evaluation
harness and CI quality gates. It isn't a notebook demo.

The demo library is public **government scheme and scholarship documents**: long PDFs that
people need answers from and rarely read.

| Status | |
|---|---|
| Backend: ingest, hybrid search, cited streaming answers | ✅ working, 18 tests |
| Web app (chat + PDF viewer) | 🚧 Phase 1 |
| Eval harness + ablations, multi-tenancy, queue, deployment | ⏳ Phases 2–5 (see [PLAN](docs/PLAN.md)) |

---

## How it works

```mermaid
flowchart LR
  PDF[PDFs] --> P[Parse<br/>page-aware] --> C[Chunk<br/>by section] --> E[Embed] --> DB[(Postgres<br/>pgvector + full-text)]
  Q[Question] --> R[Rewrite follow-ups] --> H[Hybrid search<br/>vector + keyword, RRF]
  DB --> H --> G[Answer with citations<br/>streamed] --> UI[Web app<br/>click a citation → page]
```

- **Page-aware parsing.** Every chunk remembers its page and section heading, which is what makes a citation clickable.
- **Hybrid retrieval.** Vector search finds paraphrases; keyword search finds exact names and codes ("PM-KISAN",
  "SCH-2026-114"). The two rankings are fused with Reciprocal Rank Fusion in a single SQL query.
- **Grounded generation.** The model may only use numbered sources and must cite them. Invented citations are
  detected and counted. When the sources don't contain the answer, it says so.
- **Provider-agnostic.** Any OpenAI-compatible endpoint: Google Gemini by default, **Ollama** for a fully local, free setup.
- **Streaming.** Server-Sent Events; any `<think>` reasoning is stripped before it reaches the user.

More: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Results
_Filled in from `evals/results.md` as phases complete. Every number is reproducible with `evals/run_eval.py`._

| Retrieval setup | Recall@5 | MRR | Faithfulness | p50 time-to-first-token |
|---|---|---|---|---|
| Dense only | | | | |
| Hybrid (RRF) | | | | |
| Hybrid + rerank | | | | |

## Quick start (Windows PowerShell)

Prerequisites: Docker Desktop, [uv](https://docs.astral.sh/uv/), Git, and **either** a free Gemini API key
(Google AI Studio) **or** Ollama. See [docs/NEEDS.md](docs/NEEDS.md).

```powershell
git clone <your-repo-url> documind; cd documind
Copy-Item .env.example .env          # add GEMINI_API_KEY (or switch to the Ollama block)
docker compose up -d db              # Postgres + pgvector

cd apps/api
uv sync
uv run python -m scripts.ingest_folder ../../corpus    # index the PDFs in corpus/
uv run python -m scripts.ask "Who is eligible for PM-KISAN?"
uv run uvicorn app.main:app --reload                   # API docs at http://localhost:8000/docs
```

**No key at all?** Set `LLM_PROVIDER=fake` and `EMBED_PROVIDER=fake`. Everything runs offline with
deterministic stand-ins, which is how the tests run.

## API
| Method | Path | |
|---|---|---|
| `POST` | `/documents` | Upload PDF/MD/TXT (multipart: `file`, optional `title`, `source_url`) |
| `GET` | `/documents` · `/documents/{id}` | List / status (`queued → parsing → embedding → ready / failed`) |
| `DELETE` | `/documents/{id}` | Remove a document and its chunks |
| `POST` | `/chat` | **SSE stream**: `meta` → `token`… → `citations` → `done` |
| `POST` | `/chat/sync` | Same pipeline, one JSON response |
| `GET` | `/conversations/{id}` | History |
| `POST` | `/messages/{id}/feedback` | 👍 / 👎 (`{"value": 1 \| -1}`) |
| `GET` | `/health` | Liveness + configured model |

## Tech stack
FastAPI · Postgres 17 + pgvector (HNSW) + full-text search · psycopg 3 (async) · PyMuPDF · OpenAI SDK
against Gemini / Ollama · Next.js 16 · Docker Compose · GitHub Actions · pytest · ruff

## Tests
```powershell
cd apps/api
uv run pytest -q
$env:TEST_DATABASE_URL="postgresql://documind:documind@localhost:5432/documind_test"; uv run pytest -q
```

## Docs
[PLAN](docs/PLAN.md) (zero → v1.0 with dates) · [NEEDS](docs/NEEDS.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) ·
[PROMPTS for Claude Code](docs/PROMPTS.md) · [decisions](docs/decisions.md) · [PROGRESS](docs/PROGRESS.md)

## Disclaimer
DocuMind summarises documents and can be wrong. Verify anything important in the cited source.

## License
MIT. See [LICENSE](LICENSE).
