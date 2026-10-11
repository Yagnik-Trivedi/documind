from fastapi import Request
from psycopg_pool import AsyncConnectionPool

from app.config import Settings, get_settings
from app.rag.embed import Embedder
from app.rag.llm import LLM


def settings_dep() -> Settings:
    return get_settings()


def pool_dep(request: Request) -> AsyncConnectionPool:
    return request.app.state.pool


def embedder_dep(request: Request) -> Embedder:
    return request.app.state.embedder


def llm_dep(request: Request) -> LLM:
    return request.app.state.llm


def workspace_dep(request: Request) -> str:
    # Auth + multi-tenant workspaces come later (Better Auth JWT). Until then everyone shares one.
    return get_settings().default_workspace
