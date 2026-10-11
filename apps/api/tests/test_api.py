"""End-to-end API test against a real Postgres + pgvector, with fake embeddings and a fake LLM.

Runs only when TEST_DATABASE_URL is set, e.g.
  TEST_DATABASE_URL=postgresql://documind:documind@localhost:5432/documind_test uv run pytest
WARNING: the test database's public schema is wiped.
"""

import json
import os

import psycopg
import pymupdf
import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL not set")


def _make_pdf() -> bytes:
    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "Scholarship Scheme Guidelines", fontsize=20)
    p1.insert_text((72, 110), "Eligibility", fontsize=15)
    p1.insert_text(
        (72, 140), "Students whose family income is below Rs 2.5 lakh per year are eligible.", fontsize=10
    )
    p2 = doc.new_page()
    p2.insert_text((72, 72), "How to apply", fontsize=15)
    p2.insert_text(
        (72, 100),
        "Apply online on the portal with reference code SCH-2026-114 before 31 October.",
        fontsize=10,
    )
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    os.environ.update(
        DATABASE_URL=TEST_DB,
        EMBED_PROVIDER="fake",
        LLM_PROVIDER="fake",
        EMBED_DIM="256",
        STORAGE_DIR=str(tmp_path_factory.mktemp("uploads")),
        TS_CONFIG="english",
    )
    from app.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_rejects_non_pdf_bytes(client):
    r = client.post("/documents", files={"file": ("fake.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 415


def test_upload_ingest_and_dedupe(client):
    pdf = _make_pdf()
    r = client.post(
        "/documents",
        files={"file": ("guidelines.pdf", pdf, "application/pdf")},
        data={"title": "Scholarship Guidelines 2026"},
    )
    assert r.status_code == 201, r.text
    doc_id = r.json()["id"]
    doc = client.get(f"/documents/{doc_id}").json()  # TestClient runs background tasks before returning
    assert doc["status"] == "ready", doc
    assert doc["page_count"] == 2 and doc["chunk_count"] >= 2

    again = client.post("/documents", files={"file": ("copy.pdf", pdf, "application/pdf")})
    assert again.json()["duplicate"] is True


def test_chat_sync_cites_the_right_page(client):
    r = client.post("/chat/sync", json={"message": "how do I apply online and what is the reference code?"})
    body = r.json()
    assert r.status_code == 200, body
    assert body["citations"], body
    assert body["citations"][0]["page"] == 2
    assert "<think>" not in body["answer"] and "SCH-2026-114" in body["answer"]
    assert body["phantom_citations"] == []


def test_lexical_mode_finds_exact_code(client):
    r = client.post("/chat/sync", json={"message": "SCH-2026-114", "mode": "lexical"}).json()
    assert r["citations"] and r["citations"][0]["page"] == 2


def test_chat_stream_sse_and_followup(client):
    with client.stream("POST", "/chat", json={"message": "who is eligible for the scholarship income"}) as r:
        raw = "".join(r.iter_text())
    events = [blk for blk in raw.split("\n\n") if blk.strip()]
    names = [e.split("\n")[0].removeprefix("event: ") for e in events]
    assert names[0] == "meta" and names[-2:] == ["citations", "done"] and "token" in names
    done = json.loads(events[-1].split("data: ", 1)[1])

    follow = client.post(
        "/chat/sync", json={"message": "and how do I apply?", "conversation_id": done["conversation_id"]}
    ).json()
    assert follow["rewritten_query"] is not None
    conv = client.get(f"/conversations/{done['conversation_id']}").json()
    assert len(conv["messages"]) == 4


def test_feedback(client):
    r = client.post("/chat/sync", json={"message": "eligibility income limit"}).json()
    assert client.post(f"/messages/{r['message_id']}/feedback", json={"value": 1}).status_code == 204
