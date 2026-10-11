---
description: Pick up and complete the next unchecked task in the current phase
argument-hint: [optional task text or number]
---
Find the next unchecked task in the current phase of docs/PLAN.md (or the task I named: $ARGUMENTS).
If docs/PROMPTS.md has a prompt for it, follow that prompt.
1. Restate the task and your plan in a few bullets; list the files you'll touch.
2. Write or update tests first where practical.
3. Implement it, following every rule in CLAUDE.md.
4. Run `uv run ruff check .`, `uv run ruff format .` and the tests (with TEST_DATABASE_URL if you touched SQL or routers).
5. Tick the task in PLAN.md, add a line to PROGRESS.md, and propose a commit message. Don't push.
