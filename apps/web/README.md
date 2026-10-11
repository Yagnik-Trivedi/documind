# apps/web (Next.js 16): scaffolded in Phase 1

Use the prompt **1.5 Scaffold the web app** in `docs/PROMPTS.md`.

## Pages
| Route | Phase | What |
|---|---|---|
| `/` | 1 | Intro, example questions, chat box |
| `/chat` | 1 | Streaming answers (SSE over `fetch`, since we POST), citation chips `[n]`, sources panel |
| PDF side panel | 1 | `react-pdf`, opens `GET /documents/{id}/file` at the cited page |
| `/documents` | 1 | List with ingestion status, upload |
| Sign-in, workspace switcher, members | 3 | Better Auth + organization plugin |
| Eval trend page | 5 | Metric history from `eval_runs` |

## API contract
See `docs/ARCHITECTURE.md` → "SSE protocol". The base URL comes from `NEXT_PUBLIC_API_URL`.

## UI principles
- Citations are always visible and tappable; never hide the source.
- A small "verify in the cited source" note on answers.
- Mobile-friendly, large tap targets; Noto Sans for Devanagari/Gujarati text in documents.
