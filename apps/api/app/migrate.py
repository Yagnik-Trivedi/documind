"""Tiny SQL migration runner: applies migrations/*.sql in order, once each."""

from pathlib import Path

import psycopg

from app.config import Settings, get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def render(sql: str, settings: Settings) -> str:
    if not settings.ts_config.replace("_", "").isalnum():
        raise ValueError(f"invalid ts_config: {settings.ts_config!r}")
    return sql.replace("{{EMBED_DIM}}", str(int(settings.embed_dim))).replace(
        "{{TS_CONFIG}}", settings.ts_config
    )


async def migrate(settings: Settings | None = None) -> list[str]:
    settings = settings or get_settings()
    applied_now: list[str] = []
    async with await psycopg.AsyncConnection.connect(settings.database_url, autocommit=True) as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        cur = await conn.execute("SELECT name FROM schema_migrations")
        done = {row[0] for row in await cur.fetchall()}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            async with conn.transaction():
                await conn.execute(render(path.read_text(encoding="utf-8"), settings))
                await conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
            applied_now.append(path.name)
    return applied_now


if __name__ == "__main__":
    import asyncio

    print("applied:", asyncio.run(migrate()) or "nothing (up to date)")
