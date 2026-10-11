"""Fast unit tests: no database, no network."""

import itertools

import pytest

from app.rag.chunk import chunk_blocks, est_tokens
from app.rag.citations import cited_markers, resolve
from app.rag.parse import Block, parse_markdown
from app.rag.streaming import ThinkStripper


def test_markdown_headings_and_paragraphs():
    blocks = parse_markdown("# Scheme\n\nIntro text.\n\n## Eligibility\nFarmers with land.\nMore.\n")
    assert [(b.kind, b.level) for b in blocks] == [("heading", 1), ("para", 0), ("heading", 2), ("para", 0)]
    assert blocks[3].text == "Farmers with land. More."


def test_chunks_carry_section_path_and_never_cross_sections():
    blocks = [
        Block("PM-KISAN", 1, "heading", 1),
        Block("Eligibility", 1, "heading", 2),
        Block("All landholding farmer families are eligible.", 1),
        Block("Benefits", 2, "heading", 2),
        Block("Rs 6000 per year in three instalments.", 2),
    ]
    chunks = chunk_blocks(blocks)
    assert [c.section_path for c in chunks] == ["PM-KISAN > Eligibility", "PM-KISAN > Benefits"]
    assert chunks[1].page_start == 2
    assert "landholding" not in chunks[1].content


def test_chunk_size_bounded_and_long_paragraph_split():
    para = " ".join(["word"] * 2000) + "."
    chunks = chunk_blocks([Block("Intro", 1, "heading", 1), Block(para, 3)], target=450, max_tokens=700)
    assert len(chunks) >= 3
    assert all(c.token_count <= 700 * 1.4 for c in chunks)
    assert all(c.page_start == 3 for c in chunks)


def test_no_duplicate_tail_chunk_from_overlap():
    blocks = [Block(f"Paragraph number {i}. " + "text " * 120, 1) for i in range(6)]
    chunks = chunk_blocks(blocks, target=300)
    contents = [c.content for c in chunks]
    assert len(contents) == len(set(contents))
    assert est_tokens(contents[-1]) > 10


def test_citation_markers():
    assert cited_markers("A [2]. B [1][3]. C [1, 4]. D [2].") == [2, 1, 3, 4]


def test_resolve_flags_phantom_citations():
    ctx = [
        {"id": "c1", "document_id": "d", "title": "T", "section_path": "", "page_start": 4, "content": "x"}
    ]
    cites, phantom = resolve("Claim [1]. Invented [7].", ctx)
    assert [c["page"] for c in cites] == [4]
    assert phantom == [7]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<think>plan</think>Hello [1].", "Hello [1]."),
        ("No reasoning here.", "No reasoning here."),
        ("<think>a</think>\n\nOne. <think>b</think>Two.", "One. Two."),
        ("Use x < y and <b>bold</b>.", "Use x < y and <b>bold</b>."),
    ],
)
def test_think_stripper_every_split(text, expected):
    # Split the stream at every pair of positions: tags broken across chunks must still be removed.
    for i, j in itertools.combinations(range(len(text) + 1), 2):
        s = ThinkStripper()
        out = s.feed(text[:i]) + s.feed(text[i:j]) + s.feed(text[j:]) + s.flush()
        assert out == expected, (i, j, out)


def test_fit_dim_truncates_matryoshka_and_renormalises():
    import numpy as np

    from app.rag.embed import fit_dim

    v = np.arange(1, 3073, dtype=np.float32)
    (out,) = fit_dim([v], 768, "m", truncate=True)
    assert out.shape == (768,) and abs(float(np.linalg.norm(out)) - 1.0) < 1e-5
    with pytest.raises(ValueError):
        fit_dim([v], 768, "m", truncate=False)
    with pytest.raises(ValueError):
        fit_dim([v[:512]], 768, "m", truncate=True)  # never pad smaller vectors
