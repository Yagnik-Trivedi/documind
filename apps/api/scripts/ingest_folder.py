"""Bulk-ingest a folder of PDFs/MD/TXT straight into the database (no API server needed).

Usage (from apps/api):  uv run python -m scripts.ingest_folder ../../corpus
Optional sidecar: a `sources.csv` in the folder with columns `filename,title,source_url` gives each
document a clean title and a link to the official source.
"""

import argparse
import asyncio
import csv
import hashlib
import shutil
from pathlib import Path

from app.config import get_settings
from app.db import make_pool
from app.ingest import ingest_document
from app.migrate import migrate
from app.rag.embed import make_embedder
from app.rag.parse import SUPPORTED


async def main(folder: Path) -> None:
    settings = get_settings()
    await migrate(settings)
    meta: dict[str, dict] = {}
    if (folder / "sources.csv").exists():
        with open(folder / "sources.csv", encoding="utf-8") as f:
            meta = {r["filename"]: r for r in csv.DictReader(f)}

    pool = make_pool(settings)
    await pool.open()
    embedder = make_embedder(settings)
    storage = Path(settings.storage_dir)
    storage.mkdir(parents=True, exist_ok=True)
    try:
        for path in sorted(
            p
            for p in folder.iterdir()
            if p.suffix.lower() in SUPPORTED and not p.name.upper().startswith("README")
        ):
            data = path.read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            dest = storage / f"{sha}{path.suffix.lower()}"
            shutil.copyfile(path, dest)
            m = meta.get(path.name, {})
            async with pool.connection() as conn:
                cur = await conn.execute(
                    "INSERT INTO documents (workspace_id, title, filename, mime_type, sha256, storage_path, "
                    "source_url) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (workspace_id, sha256) DO NOTHING "
                    "RETURNING id",
                    (
                        settings.default_workspace,
                        m.get("title") or path.stem,
                        path.name,
                        SUPPORTED[path.suffix.lower()],
                        sha,
                        str(dest.resolve()),
                        m.get("source_url"),
                    ),
                )
                row = await cur.fetchone()
            if row is None:
                print(f"skip (already ingested): {path.name}")
                continue
            try:
                n = await ingest_document(pool, settings, embedder, str(row["id"]))
                print(f"ok   {path.name}: {n} chunks")
            except Exception as exc:
                print(f"FAIL {path.name}: {exc}")
    finally:
        await pool.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    asyncio.run(main(ap.parse_args().folder))
