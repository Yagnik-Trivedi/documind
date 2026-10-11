import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import make_pool
from app.migrate import migrate
from app.rag.embed import make_embedder
from app.rag.llm import make_llm
from app.routers import chat, documents

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.auto_migrate:
        applied = await migrate(settings)
        if applied:
            logging.getLogger("documind").info("applied migrations: %s", applied)
    app.state.pool = make_pool(settings)
    await app.state.pool.open()
    app.state.embedder = make_embedder(settings)
    app.state.llm = make_llm(settings)
    yield
    await app.state.pool.close()


app = FastAPI(title="DocuMind API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/health")
async def health():
    async with app.state.pool.connection() as conn:
        await conn.execute("SELECT 1")
    s = get_settings()
    return {"status": "ok", "chat_model": s.chat_model, "embed_provider": s.embed_provider}
