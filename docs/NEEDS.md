# What You Need

## Accounts (all free to start)
| Account | Why | When |
|---|---|---|
| GitHub | Repo, CI, Projects board | Now |
| **Google AI Studio** (Gemini API key) | Default LLM + embeddings (free tier with rate limits) | Now, or use Ollama instead |
| Neon or Supabase | Hosted Postgres with pgvector | Phase 5 |
| Render / Fly.io / Railway | Host API + worker | Phase 5 |
| Vercel or Netlify | Host the Next.js app | Phase 5 |
| Cloudflare (R2) | File storage, 10 GB free, no egress fees | Phase 4 |
| Upstash | Hosted Redis for the queue | Phase 5 |
| Langfuse Cloud (or self-host) | Tracing | Phase 4 |
| Sentry, UptimeRobot | Errors, uptime | Phase 5 |

## Keys and secrets
- `GEMINI_API_KEY` (or nothing at all with Ollama)
- Later: R2 keys, Better Auth secret, Langfuse keys, Sentry DSN
- Rule: only in `.env` locally and the platform's env settings in production. Pre-commit + CI run gitleaks.

## Two ways to run the models
| Mode | Set in `.env` | Pros | Cons |
|---|---|---|---|
| **Gemini (default)** | `GEMINI_API_KEY`, default base URL and models | Strong quality, nothing to run locally, same setup as deployment | Free-tier rate limits |
| **Ollama (local)** | `LLM_BASE_URL=http://localhost:11434/v1/`, e.g. `CHAT_MODEL=qwen2.5:14b`, `EMBED_MODEL=bge-m3`, `EMBED_DIM=1024` | Free, private, unlimited; runs on your RTX 5060 | Slower; local only (deploy uses an API) |

Pick one embedding model and keep it: `EMBED_DIM` fixes the database vector column. Switching means resetting the DB and re-ingesting.

## Software (Windows 11)
| Tool | Install | Check |
|---|---|---|
| Git | `winget install Git.Git` | `git --version` |
| Docker Desktop (WSL2) | `winget install Docker.DockerDesktop` | `docker compose version` |
| uv | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` | `uv --version` |
| Python 3.12 | `uv python install 3.12` | `uv run python --version` |
| Node.js 22 LTS | `winget install OpenJS.NodeJS.LTS` | `node --version` |
| pre-commit | `uv tool install pre-commit`, then `pre-commit install` in the repo | `pre-commit --version` |
| Ollama (optional) | already installed; `ollama pull bge-m3` and a chat model | `ollama list` |
| OBS Studio (demo video, Phase 6) | `winget install OBSProject.OBSStudio` | |

## Data
40–60 **text-based** public PDFs (scheme guidelines, scholarship rules, circulars) from official sites,
recorded in `corpus/sources.csv`. Check that you can select text in the PDF; skip scans for now.

## Costs
| Item | Estimate |
|---|---|
| LLM + embeddings | $0 on the Gemini free tier or Ollama during development; a few dollars if you exceed free limits during evals |
| Hosting | $0 on free tiers; ~$5–7/month if you want the API always-on (no cold starts) for recruiters |
| Domain (optional) | ~₹800/year |
