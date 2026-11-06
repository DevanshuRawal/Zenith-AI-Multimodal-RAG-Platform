from fastapi.testclient import TestClient

import app.main as main
from app.main import app
from app.feedback import SQLiteFeedbackStore
from app.rag_service import ArchitectureReviewService

client = TestClient(app)


class TestGenerator:
    def expand(self, question, history):
        return [question]

    def generate(self, question, context, history):
        return f"Grounded answer about service boundaries. Sources: {context}"


class TestReranker:
    def score(self, question, documents):
        return [1.0] * len(documents)


class EmptyStore:
    def search(self, query, top_k=5):
        return []

    def clear(self):
        pass


def use_test_service(monkeypatch, store=None):
    monkeypatch.setattr(
        "app.main.service",
        ArchitectureReviewService(
            store=store or EmptyStore(),
            generator=TestGenerator(),
            reranker=TestReranker(),
        ),
    )


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_query_without_data_returns_grounded_response(monkeypatch):
    use_test_service(monkeypatch)
    response = client.post("/api/query", json={"question": "How should we design system boundaries?"})
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert isinstance(payload["sources"], list)


def test_service_uses_rag_context_for_answer_generation():
    service = ArchitectureReviewService(generator=TestGenerator(), reranker=TestReranker())
    service.store.add_document(
        "doc-1",
        "Service boundaries should separate API, worker, and data access modules.",
        {"document_name": "architecture.md", "chunk_index": 0},
    )

    result = service.answer_question(
        "Service boundaries should separate API worker and data access modules.",
        top_k=3,
    )

    assert "architecture.md" in [source["document_name"] for source in result["sources"]]
    assert "service boundaries" in result["answer"].lower()
    assert "context" in result


def test_session_memory_tracks_followup_questions(tmp_path):
    service = ArchitectureReviewService(
        generator=TestGenerator(),
        reranker=TestReranker(),
        memory_db_path=tmp_path / "sessions.sqlite3",
    )
    service.store.add_document(
        "doc-2",
        "The system uses a gateway, domain services, and persistence layers.",
        {"document_name": "system.md", "chunk_index": 0},
    )

    service.answer_question("What are the major layers?", session_id="session-123", top_k=1)
    service.answer_question("How do they interact?", session_id="session-123", top_k=1)

    assert "session-123" in service.session_memory
    assert len(service.session_memory["session-123"]) == 2
    assert service.session_memory["session-123"][0]["question"] == "What are the major layers?"


def test_query_endpoint_supports_session_memory(monkeypatch):
    use_test_service(monkeypatch)
    response = client.post(
        "/api/query",
        json={
            "question": "What architecture pattern is most relevant?",
            "session_id": "integration-session",
            "top_k": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
    assert isinstance(payload["sources"], list)


def test_query_response_can_be_rated_and_feedback_is_persisted(monkeypatch, tmp_path):
    use_test_service(monkeypatch)
    monkeypatch.setattr(
        main,
        "feedback_store",
        SQLiteFeedbackStore(tmp_path / "feedback.sqlite3"),
        raising=False,
    )

    query = client.post(
        "/api/query",
        json={"question": "What does the architecture say?"},
    )

    assert query.status_code == 200
    interaction_id = query.json()["interaction_id"]
    feedback = client.post(
        "/api/feedback",
        json={
            "interaction_id": interaction_id,
            "rating": 5,
            "comment": "This was useful.",
        },
    )

    assert feedback.status_code == 200
    assert feedback.json() == {
        "status": "recorded",
        "interaction_id": interaction_id,
    }
    duplicate = client.post(
        "/api/feedback",
        json={"interaction_id": interaction_id, "rating": 4},
    )
    assert duplicate.status_code == 409
    report = client.get("/api/feedback/report")
    assert report.status_code == 200
    assert report.json() == {
        "total_feedback": 1,
        "average_rating": 5.0,
        "ratings": {"5": 1},
    }


def test_feedback_api_rejects_unknown_interactions_and_invalid_ratings(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        main,
        "feedback_store",
        SQLiteFeedbackStore(tmp_path / "feedback.sqlite3"),
        raising=False,
    )

    unknown = client.post(
        "/api/feedback",
        json={"interaction_id": "missing", "rating": 4},
    )
    invalid_rating = client.post(
        "/api/feedback",
        json={"interaction_id": "missing", "rating": 6},
    )

    assert unknown.status_code == 404
    assert invalid_rating.status_code == 422
