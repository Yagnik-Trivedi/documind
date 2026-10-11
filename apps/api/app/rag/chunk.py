"""Structure-aware chunking.

Rules:
- A heading always starts a new chunk, and every chunk remembers its heading path
  ("Eligibility > Income criteria"), which is prepended before embedding.
- Paragraphs are packed until ~target tokens; a paragraph bigger than max_tokens is split by sentence.
- The last short paragraph of a chunk is repeated at the start of the next one (overlap),
  but never across a section boundary.
"""

import re
from dataclasses import dataclass, replace

from app.rag.parse import Block


@dataclass
class Chunk:
    content: str
    section_path: str
    page_start: int
    page_end: int
    token_count: int
    ordinal: int


def est_tokens(text: str) -> int:
    # Fast approximation (~1.3 tokens per word for English). Good enough for packing.
    return max(1, round(len(text.split()) * 1.3))


def _split_long(block: Block, max_tokens: int) -> list[Block]:
    if est_tokens(block.text) <= max_tokens:
        return [block]
    sentences = re.split(r"(?<=[.!?।])\s+", block.text)
    out, cur = [], ""
    for s in sentences:
        candidate = f"{cur} {s}".strip()
        if cur and est_tokens(candidate) > max_tokens:
            out.append(replace(block, text=cur))
            cur = s
        else:
            cur = candidate
    if cur:
        out.append(replace(block, text=cur))
    # A single giant "sentence" (e.g. a table flattened to text): hard-split by words.
    final: list[Block] = []
    words_per = max(1, int(max_tokens / 1.3))
    for b in out:
        words = b.text.split()
        for i in range(0, len(words), words_per):
            final.append(replace(b, text=" ".join(words[i : i + words_per])))
    return final


def chunk_blocks(blocks: list[Block], target: int = 450, max_tokens: int = 700) -> list[Chunk]:
    chunks: list[Chunk] = []
    stack: list[tuple[int, str]] = []
    section = ""
    cur: list[Block] = []
    new_in_cur = 0

    def flush(keep_overlap: bool) -> None:
        nonlocal cur, new_in_cur
        if new_in_cur == 0:
            cur = [] if not keep_overlap else cur
            return
        text = "\n\n".join(b.text for b in cur)
        chunks.append(Chunk(text, section, cur[0].page, cur[-1].page, est_tokens(text), len(chunks)))
        last = cur[-1]
        cur = [last] if keep_overlap and est_tokens(last.text) <= target // 3 else []
        new_in_cur = 0

    for block in blocks:
        if block.kind == "heading":
            flush(keep_overlap=False)
            cur, new_in_cur = [], 0
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block.text))
            section = " > ".join(t for _, t in stack)
            continue
        for piece in _split_long(block, max_tokens):
            size = est_tokens(piece.text)
            cur_size = sum(est_tokens(b.text) for b in cur)
            if new_in_cur and cur_size + size > target:
                flush(keep_overlap=True)
            cur.append(piece)
            new_in_cur += 1
    flush(keep_overlap=False)
    return chunks


def embedding_text(title: str, chunk: Chunk) -> str:
    """Contextual header: cheap trick that measurably improves retrieval."""
    header = f"{title} > {chunk.section_path}" if chunk.section_path else title
    return f"{header}\n\n{chunk.content}"
