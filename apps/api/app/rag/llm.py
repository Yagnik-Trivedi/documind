"""Chat LLM providers. Gemini, Ollama, OpenAI, Groq and most hosts speak the OpenAI API, so the
official SDK works with a custom base_url. Swap providers by changing LLM_BASE_URL / CHAT_MODEL only."""

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol

from app.config import Settings


@dataclass
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    extra: dict = field(default_factory=dict)


class LLM(Protocol):
    async def stream(self, messages: list[dict], model: str, usage: Usage) -> AsyncIterator[str]: ...
    async def complete(self, messages: list[dict], model: str) -> str: ...


class OpenAICompatLLM:
    def __init__(self, settings: Settings):
        from openai import AsyncOpenAI

        is_local = "localhost" in settings.llm_base_url or "127.0.0.1" in settings.llm_base_url
        if not settings.llm_api_key and not is_local:
            raise ValueError("LLM_API_KEY / GEMINI_API_KEY is not set (not needed for a local Ollama URL).")
        self.client = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key or "ollama")
        self.temperature, self.max_tokens = settings.llm_temperature, settings.llm_max_tokens
        self.extra = (
            {"reasoning_effort": settings.llm_reasoning_effort} if settings.llm_reasoning_effort else {}
        )

    async def stream(self, messages: list[dict], model: str, usage: Usage) -> AsyncIterator[str]:
        resp = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
            **self.extra,
        )
        async for event in resp:
            if event.usage:
                usage.input_tokens = event.usage.prompt_tokens
                usage.output_tokens = event.usage.completion_tokens
            if not event.choices:
                continue
            delta = event.choices[0].delta
            # Some reasoning models send their thinking in a separate field; we never show it.
            if delta.content:
                yield delta.content

    async def complete(self, messages: list[dict], model: str) -> str:
        resp = await self.client.chat.completions.create(
            model=model, messages=messages, temperature=0, max_tokens=256, **self.extra
        )
        return strip_think(resp.choices[0].message.content or "")


class FakeLLM:
    """Deterministic stand-in for tests: answers with the first sentence of source [1]."""

    def __init__(self, settings: Settings | None = None):
        pass

    async def stream(self, messages: list[dict], model: str, usage: Usage) -> AsyncIterator[str]:
        prompt = messages[-1]["content"]
        m = re.search(r"\[1\][^\n]*\n(.+?)(?:\n\n\[2\]|\n\nQuestion:|$)", prompt, re.S)
        if not m:
            answer = "I couldn't find this in the provided documents."
        else:
            first_sentence = re.split(r"(?<=[.!?])\s", m.group(1).strip())[0]
            answer = f"<think>scratch work</think>According to the documents, {first_sentence} [1]"
        usage.input_tokens, usage.output_tokens = len(prompt.split()), len(answer.split())
        for i in range(0, len(answer), 7):  # odd-sized pieces exercise the streaming parsers
            yield answer[i : i + 7]

    async def complete(self, messages: list[dict], model: str) -> str:
        question = messages[-1]["content"].split("Follow-up question:")[-1].strip()
        return f"{question} (standalone)"


_THINK = re.compile(r"<think>.*?</think>", re.S)


def strip_think(text: str) -> str:
    return _THINK.sub("", text).strip()


def make_llm(settings: Settings) -> LLM:
    return {"openai_compat": OpenAICompatLLM, "fake": FakeLLM}[settings.llm_provider](settings)
