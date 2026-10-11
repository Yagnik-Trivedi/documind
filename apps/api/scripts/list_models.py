"""List models available on the configured OpenAI-compatible endpoint (Gemini, Ollama, OpenAI, ...).

Usage (from apps/api):  uv run python -m scripts.list_models
Then put the exact ids you want into CHAT_MODEL / FAST_MODEL / EMBED_MODEL in .env
(Gemini lists ids as "models/<name>": use just <name>).
Optionally checks an embedding model's dimension:  uv run python -m scripts.list_models --probe-embed <model-id>
"""

import argparse

from openai import OpenAI

from app.config import get_settings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-embed", help="embedding model id to test (prints its dimension)")
    args = ap.parse_args()

    s = get_settings()
    client = OpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key or "ollama")  # Ollama ignores the key
    ids = sorted(m.id for m in client.models.list().data)
    print(f"{len(ids)} models at {s.llm_base_url}\n")
    for mid in ids:
        tag = ""
        low = mid.lower()
        if any(k in low for k in ("embed", "bge", "e5", "gte")):
            tag = "   <- likely an embedding model"
        print(f"  {mid}{tag}")

    if args.probe_embed:
        emb = client.embeddings.create(model=args.probe_embed, input=["hello world"]).data[0].embedding
        n = len(emb)
        hint = (
            f"set EMBED_DIM={n}"
            if n <= 2000
            else "keep EMBED_DIM <= 2000 with EMBED_TRUNCATE=true (pgvector HNSW limit)"
        )
        print(f"\n{args.probe_embed}: dimension = {n}  -> {hint}")


if __name__ == "__main__":
    main()
