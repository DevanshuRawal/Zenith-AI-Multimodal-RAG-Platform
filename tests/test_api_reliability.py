import json
import logging

from fastapi.testclient import TestClient

from app import main
from app.rag_service import ArchitectureReviewService


class EmptyStore:
    def search(self, query, top_k=5):
        return []

    def clear(self):
        pass


class TestGenerator:
    def expand(self, question, history):
        return [question]

    def generate(self, question, context, history):
        return ""


class TestReranker:
    def score(self, question, documents):
        return [1.0] * len(documents)


def install_test_service(monkeypatch, service=None):
    service = service or ArchitectureReviewService(
        store=EmptyStore(),
        generator=TestGenerator(),
        reranker=TestReranker(),
    )
    monkeypatch.setattr(main, "service", service)
    return service


def test_query_requests_are_rate_limited_per_client(monkeypatch):
    install_test_service(monkeypatch)
    main.app.state.rate_limit_buckets.clear()
    monkeypatch.setattr(main.app.state, "rate_limit_requests", 1, raising=False)
    monkeypatch.setattr(main.app.state, "rate_limit_window_seconds", 60, raising=False)
    client = TestClient(main.app)
    payload = {"question": "What does the architecture say?"}

    first = client.post("/api/query", json=payload)
    second = client.post("/api/query", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "Rate limit exceeded. Try again later."
    assert second.headers["retry-after"]
    assert second.headers["x-request-id"]


def test_api_errors_include_request_id_without_exposing_exception(monkeypatch, caplog):
    class BrokenService:
        def answer_question(self, question, top_k, session_id):
            raise RuntimeError("private upstream token must not be exposed")

    install_test_service(monkeypatch, BrokenService())
    monkeypatch.setattr(main.app.state, "rate_limit_requests", 100, raising=False)
    caplog.set_level(logging.ERROR, logger="app.main")
    client = TestClient(main.app, raise_server_exceptions=False)

    response = client.post(
        "/api/query",
        json={"question": "Review this architecture?"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error."
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "private upstream token" not in response.text
    assert "private upstream token" not in caplog.text
    event = json.loads(caplog.records[-1].message)
    assert event["event"] == "unhandled_api_exception"
    assert event["request_id"] == response.headers["x-request-id"]


def test_validation_error_has_stable_shape_and_request_id():
    response = TestClient(main.app).post("/api/query", json={"question": ""})

    assert response.status_code == 422
    assert response.json()["detail"] == "Request validation failed."
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_successful_request_emits_structured_completion_log(monkeypatch, caplog):
    install_test_service(monkeypatch)
    caplog.set_level(logging.INFO, logger="app.main")

    response = TestClient(main.app).get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    event = next(
        json.loads(record.message)
        for record in reversed(caplog.records)
        if record.name == "app.main" and record.message.startswith("{")
    )
    assert event["event"] == "http_request_completed"
    assert event["method"] == "GET"
    assert event["path"] == "/health"
    assert event["status_code"] == 200
    assert event["request_id"] == response.headers["x-request-id"]
