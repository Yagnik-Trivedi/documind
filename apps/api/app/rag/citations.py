import re

_MARK = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def cited_markers(answer: str) -> list[int]:
    """All [n] / [n, m] markers in order of first appearance, deduplicated."""
    seen: dict[int, None] = {}
    for group in _MARK.findall(answer):
        for n in group.split(","):
            seen.setdefault(int(n), None)
    return list(seen)


def resolve(answer: str, context: list[dict]) -> tuple[list[dict], list[int]]:
    """Map markers to the context chunks they point at. Returns (citations, phantom_markers)."""
    citations, phantom = [], []
    for n in cited_markers(answer):
        if 1 <= n <= len(context):
            c = context[n - 1]
            citations.append(
                {
                    "marker": n,
                    "chunk_id": str(c["id"]),
                    "document_id": str(c["document_id"]),
                    "title": c["title"],
                    "section": c["section_path"],
                    "page": c["page_start"],
                    "snippet": c["content"][:400],
                }
            )
        else:
            phantom.append(n)
    return citations, phantom
