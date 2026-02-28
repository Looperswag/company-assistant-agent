"""Tests for FastAPI web API endpoints."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

import src.web.api as web_api


class FakeAssistant:
    """Minimal fake assistant used by API tests."""

    def __init__(self) -> None:
        self.cleared_sessions = []

    def process_query_with_metadata(self, query: str, use_history: bool = True, session_id: str | None = None) -> dict:
        return {
            "response": f"echo:{query}",
            "sources": [
                {
                    "title": "Doc A",
                    "source": "Knowledge Base/Company Policies.md",
                    "chunk_index": 0,
                    "similarity": 0.91,
                    "strategy": "hybrid",
                    "snippet": "policy snippet",
                }
            ],
        }

    def stream_query_with_metadata(self, query: str, use_history: bool = True, session_id: str | None = None):
        return iter(["hello", " world"]), [
            {
                "title": "Doc Stream",
                "source": "Knowledge Base/Coding Style.md",
                "chunk_index": 1,
                "similarity": 0.88,
                "strategy": "vector",
                "snippet": "stream snippet",
            }
        ]

    def search_knowledge(self, query: str, top_k: int = 8, min_similarity: float = 0.2):
        return [
            {
                "text": "knowledge chunk",
                "metadata": {
                    "title": "Knowledge Doc",
                    "source": "Knowledge Base/Company Procedures & Guidelines.md",
                    "chunk_index": 3,
                },
                "similarity": 0.72,
                "strategy": "hybrid",
            }
        ]

    def get_history(self, session_id: str | None = None):
        return [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]

    def get_session_last_access(self, session_id: str | None = None):
        return datetime.now(timezone.utc)

    def clear_history(self, session_id: str | None = None) -> None:
        self.cleared_sessions.append(session_id)


class FakeVectorStore:
    """Minimal fake vector store for overview endpoint."""

    def get_document_overview(self) -> dict:
        return {
            "total_chunks": 8,
            "total_documents": 2,
            "documents": [
                {
                    "source": "Knowledge Base/Company Policies.md",
                    "title": "Company Policies",
                    "chunks": 5,
                },
                {
                    "source": "Knowledge Base/Coding Style.md",
                    "title": "Coding Style",
                    "chunks": 3,
                },
            ],
        }

    def get_collection_size(self) -> int:
        return 8


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setattr(web_api, "assistant", FakeAssistant())
    monkeypatch.setattr(web_api, "VectorStore", FakeVectorStore)
    return TestClient(web_api.app)


def test_query_endpoint_returns_extended_payload(monkeypatch) -> None:
    """POST /api/query should include sources and latency fields."""
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/query",
        json={"query": "test", "session_id": "s-123", "use_history": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "echo:test"
    assert payload["session_id"] == "s-123"
    assert isinstance(payload["latency_ms"], int)
    assert len(payload["sources"]) == 1


def test_stream_endpoint_emits_sse_events(monkeypatch) -> None:
    """POST /api/query/stream should emit sources/chunk/done SSE events."""
    client = _build_client(monkeypatch)

    with client.stream(
        "POST",
        "/api/query/stream",
        json={"query": "stream", "session_id": "session-stream", "use_history": True},
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "event: sources" in body
    assert "event: chunk" in body
    assert "event: done" in body
    assert "\n\n" in body
    assert "\\n\\n" not in body


def test_knowledge_search_endpoint(monkeypatch) -> None:
    """POST /api/knowledge/search should return normalized items."""
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/knowledge/search",
        json={"query": "policy", "top_k": 5, "min_similarity": 0.2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["title"] == "Knowledge Doc"


def test_knowledge_overview_endpoint(monkeypatch) -> None:
    """GET /api/knowledge/overview should return aggregated stats."""
    client = _build_client(monkeypatch)

    response = client.get("/api/knowledge/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_chunks"] == 8
    assert payload["total_documents"] == 2
    assert len(payload["documents"]) == 2


def test_session_history_endpoints(monkeypatch) -> None:
    """Session history GET/DELETE endpoints should respond successfully."""
    client = _build_client(monkeypatch)

    get_resp = client.get("/api/sessions/session-a/history")
    delete_resp = client.delete("/api/sessions/session-a/history")

    assert get_resp.status_code == 200
    assert len(get_resp.json()["history"]) == 2
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "success"


def test_legacy_history_endpoints_still_work(monkeypatch) -> None:
    """Legacy /api/history and /api/clear-history should be backward compatible."""
    client = _build_client(monkeypatch)

    history_resp = client.get("/api/history")
    clear_resp = client.post("/api/clear-history", json={})

    assert history_resp.status_code == 200
    assert len(history_resp.json()["history"]) == 2
    assert clear_resp.status_code == 200
    assert clear_resp.json()["status"] == "success"
