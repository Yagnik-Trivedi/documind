from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a .env file).

    See the repo-root `.env.example` for documentation of every value.
    """

    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    # --- Database -------------------------------------------------------------
    database_url: str = "postgresql://documind:documind@localhost:5432/documind"
    auto_migrate: bool = True

    # --- Chat LLM: any OpenAI-compatible endpoint ----------------------------
    # Default: Google Gemini's OpenAI-compatible API. Local alternative: Ollama at
    # http://localhost:11434/v1/ (see .env.example). Switching providers is config only.
    llm_provider: Literal["openai_compat", "fake"] = "openai_compat"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_api_key: str = Field(default="", validation_alias=AliasChoices("LLM_API_KEY", "GEMINI_API_KEY"))
    chat_model: str = "gemini-flash-latest"  # pin an exact version for reproducible evals
    fast_model: str = "gemini-flash-lite-latest"  # query rewriting, LLM judge, reranking
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    llm_reasoning_effort: str | None = None  # e.g. "low" to cut latency on thinking models

    # --- Embeddings -----------------------------------------------------------
    embed_provider: Literal["openai_compat", "local", "fake"] = "openai_compat"
    embed_base_url: str | None = None  # defaults to llm_base_url
    embed_api_key: str | None = None  # defaults to llm_api_key
    embed_model: str = "gemini-embedding-001"
    # Vector size stored in Postgres. MUST stay fixed after the first ingest (changing it = re-index).
    # pgvector's HNSW index supports at most 2000 dims, so large models are truncated (see below).
    embed_dim: int = 768
    # Matryoshka-trained models (Gemini, OpenAI text-embedding-3, Qwen3-Embedding) can be cut to their
    # first N dims and re-normalised with little quality loss. Allowed only when the model returns more.
    embed_truncate: bool = True
    embed_send_dimensions: bool = False  # also send `dimensions=embed_dim` (OpenAI supports it)
    local_embed_model: str = "BAAI/bge-m3"  # 1024 dims

    # --- Retrieval ------------------------------------------------------------
    ts_config: str = "simple"  # 'english' for English-only corpora; 'simple' works for any language
    retrieve_k: int = 40
    context_k: int = 8
    rrf_k: int = 60
    hnsw_ef_search: int = 100

    # --- Files ----------------------------------------------------------------
    storage_dir: str = "./data/uploads"
    max_upload_mb: int = 25

    # --- Web ------------------------------------------------------------------
    cors_origins: str = "http://localhost:3000"
    default_workspace: str = "public"


@lru_cache
def get_settings() -> Settings:
    return Settings()
