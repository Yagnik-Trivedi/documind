"""Embedding providers behind one tiny interface.

- openai_compat: any OpenAI-compatible /v1/embeddings endpoint (Gemini by default; Ollama, OpenAI, ...)
- local:         sentence-transformers on your own machine (BGE-M3 on the RTX 5060)
- fake:          deterministic hashing embedder for tests and offline dev (no API key needed)
"""

import hashlib
import re
from typing import Protocol

import numpy as np

from app.config import Settings


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[np.ndarray]: ...


def _normalise(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) or 1.0)


def fit_dim(vectors: list[np.ndarray], dim: int, model: str, truncate: bool) -> list[np.ndarray]:
    """Return unit vectors of exactly `dim` dims.

    Larger outputs are cut to their first `dim` values when `truncate` is on (valid for
    Matryoshka-trained models), then re-normalised. Anything else is a configuration error.
    """
    if not vectors:
        return vectors
    got = len(vectors[0])
    if got == dim:
        return [_normalise(v) for v in vectors]
    if got > dim and truncate:
        return [_normalise(v[:dim]) for v in vectors]
    raise ValueError(
        f"Embedding model '{model}' returned {got} dims but EMBED_DIM={dim}. Set EMBED_DIM to match "
        "(or enable EMBED_TRUNCATE for Matryoshka models) and reset the database: the vector column is fixed-size."
    )


class OpenAICompatEmbedder:
    def __init__(self, settings: Settings):
        from openai import OpenAI

        if not settings.embed_model:
            raise ValueError("EMBED_MODEL is empty. Run `python -m scripts.list_models` and pick one.")
        self.client = OpenAI(
            base_url=settings.embed_base_url or settings.llm_base_url,
            api_key=settings.embed_api_key or settings.llm_api_key or "not-needed-for-ollama",
        )
        self.model, self.dim, self.batch = settings.embed_model, settings.embed_dim, 32
        self.truncate = settings.embed_truncate
        self.extra = {"dimensions": settings.embed_dim} if settings.embed_send_dimensions else {}

    def embed(self, texts: list[str]) -> list[np.ndarray]:
        out: list[np.ndarray] = []
        for i in range(0, len(texts), self.batch):
            resp = self.client.embeddings.create(
                model=self.model, input=texts[i : i + self.batch], **self.extra
            )
            out.extend(np.asarray(d.embedding, dtype=np.float32) for d in resp.data)
        return fit_dim(out, self.dim, self.model, self.truncate)


class LocalEmbedder:
    def __init__(self, settings: Settings):
        from sentence_transformers import SentenceTransformer  # optional extra: `uv sync --extra local`

        self.model_name = settings.local_embed_model
        self.model = SentenceTransformer(self.model_name)
        self.dim, self.truncate = settings.embed_dim, settings.embed_truncate

    def embed(self, texts: list[str]) -> list[np.ndarray]:
        vecs = self.model.encode(texts, batch_size=16, normalize_embeddings=True)
        out = [np.asarray(v, dtype=np.float32) for v in vecs]
        return fit_dim(out, self.dim, self.model_name, self.truncate)


class FakeEmbedder:
    """Signed feature hashing of lowercase words. Similar wording -> similar vectors. Tests only."""

    def __init__(self, settings: Settings):
        self.dim = settings.embed_dim

    def embed(self, texts: list[str]) -> list[np.ndarray]:
        out = []
        for text in texts:
            v = np.zeros(self.dim, dtype=np.float32)
            for word in re.findall(r"\w+", text.lower()):
                h = int.from_bytes(hashlib.md5(word.encode()).digest()[:8], "little")
                v[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
            out.append(v / (np.linalg.norm(v) or 1.0))
        return out


def make_embedder(settings: Settings) -> Embedder:
    return {"openai_compat": OpenAICompatEmbedder, "local": LocalEmbedder, "fake": FakeEmbedder}[
        settings.embed_provider
    ](settings)
