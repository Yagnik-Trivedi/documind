"""Turn files into a flat list of blocks (headings + paragraphs) that remember their page number.

Page numbers are what make citations clickable, so every block keeps one.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf  # PyMuPDF

BOLD_FLAG = 16  # PyMuPDF span flag for bold text


@dataclass
class Block:
    text: str
    page: int  # 1-based
    kind: str = "para"  # "heading" | "para"
    level: int = 0  # heading level (1 = biggest)


SUPPORTED = {".pdf": "application/pdf", ".md": "text/markdown", ".txt": "text/plain"}


def parse_file(path: str | Path) -> tuple[list[Block], int]:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return parse_pdf(path)
    if ext in (".md", ".txt"):
        return parse_markdown(path.read_text(encoding="utf-8", errors="replace")), 1
    raise ValueError(f"unsupported file type: {ext}")


def _clean(text: str) -> str:
    text = text.replace("­", "")  # soft hyphens
    text = re.sub(r"([a-z])-\s+([a-z])", r"\1\2", text)  # re-join words hyphenated across lines
    return re.sub(r"\s+", " ", text).strip()


def _body_size(size_chars: dict[float, int]) -> float:
    """Body text size = the font size most characters are set in (character-weighted median)."""
    if not size_chars:
        return 10.0
    total, acc = sum(size_chars.values()), 0
    for size in sorted(size_chars):
        acc += size_chars[size]
        if acc * 2 >= total:
            return size
    return 10.0


def parse_pdf(path: Path) -> tuple[list[Block], int]:
    doc = pymupdf.open(path)
    raw: list[tuple[str, int, float, bool]] = []
    size_chars: dict[float, int] = {}  # font size -> number of characters set in it
    for page_no, page in enumerate(doc, start=1):
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:  # 0 = text block; skip images
                continue
            lines, sizes, all_bold = [], [], True
            for line in b["lines"]:
                t = "".join(s["text"] for s in line["spans"]).strip()
                if t:
                    lines.append(t)
                for s in line["spans"]:
                    if s["text"].strip():
                        sizes.append(s["size"])
                        size_chars[round(s["size"], 1)] = size_chars.get(round(s["size"], 1), 0) + len(
                            s["text"]
                        )
                        all_bold = all_bold and bool(s["flags"] & BOLD_FLAG)
            text = _clean(" ".join(lines))
            if not text:
                continue
            raw.append((text, page_no, max(sizes), all_bold))
    page_count = doc.page_count
    doc.close()

    body = _body_size(size_chars)
    blocks: list[Block] = []
    for text, page_no, size, bold in raw:
        looks_short = len(text) <= 120 and not text.endswith((".", ":", ";", ","))
        bigger = size >= body * 1.15
        if looks_short and (bigger or (bold and size >= body * 0.98)):
            level = 1 if size >= body * 1.5 else 2 if bigger else 3
            blocks.append(Block(text, page_no, "heading", level))
        else:
            blocks.append(Block(text, page_no))
    return blocks, page_count


def parse_markdown(text: str) -> list[Block]:
    blocks: list[Block] = []
    para: list[str] = []

    def flush() -> None:
        if para:
            blocks.append(Block(_clean(" ".join(para)), 1))
            para.clear()

    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            flush()
            blocks.append(Block(m.group(2).strip(), 1, "heading", len(m.group(1))))
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
    flush()
    return blocks
