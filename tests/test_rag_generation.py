from fastapi.testclient import TestClient
from huggingface_hub.errors import HfHubHTTPError

from app import main
from app.llm import LangChainHuggingFaceGenerator
from app.rag_service import ArchitectureReviewService


class FakeStore:
    def __init__(self):
        self.documents = []

    def add_document(self, chunk_id, content, metadata):
        self.documents.append(
            {
                "chunk_id": chunk_id,
                "content": content,
                "metadata": metadata,
                "score": 0.9,
            }
        )

    def search(self, query, top_k=5, metadata_filter=None):
        docs = self.documents
        if metadata_filter:
            docs = [
                d for d in docs
                if all(d["metadata"].get(k) == v for k, v in metadata_filter.items())
            ]
        return docs[:top_k]

    def clear(self):
        self.documents.clear()


class FakeGenerator:
    def __init__(self, answer="The API and worker should be separate [architecture.md::0]."):
        self.answer = answer
        self.calls = []

    def expand(self, question, history):
        return [question]

    def generate(self, question, context, history):
        self.calls.append(
            {"question": question, "context": context, "history": history}
        )
        return self.answer


class FakeReranker:
    def score(self, question, documents):
        return [0.9] * len(documents)


def test_rag_answer_is_generated_from_retrieved_context():
    store = FakeStore()
    store.add_document(
        "architecture.md::0",
        "The API handles requests, while a worker runs background jobs.",
        {"document_name": "architecture.md", "chunk_index": 0},
    )
    generator = FakeGenerator()
    service = ArchitectureReviewService(
        store=store, generator=generator, reranker=FakeReranker()
    )

    result = service.answer_question("How should API and jobs be separated?")

    assert result["answer"] == generator.answer
    assert generator.calls[0]["context"] == (
        "[architecture.md::0]\n"
        "The API handles requests, while a worker runs background jobs."
    )
    assert result["sources"][0]["chunk_id"] == "architecture.md::0"


def test_rag_does_not_call_llm_when_retrieval_returns_no_evidence():
    generator = FakeGenerator()
    service = ArchitectureReviewService(
        store=FakeStore(), generator=generator, reranker=FakeReranker()
    )

    result = service.answer_question("What is our disaster recovery plan?")

    assert result["sources"] == []
    assert result["answer"] == (
        "I couldn't find supporting information in the indexed documents, "
        "so I can't answer this reliably."
    )
    assert generator.calls == []


def test_rag_rejects_answer_with_unverified_source_citation():
    store = FakeStore()
    store.add_document(
        "architecture.md::0",
        "The API handles requests, while a worker runs background jobs.",
        {"document_name": "architecture.md", "chunk_index": 0},
    )
    generator = FakeGenerator("The database is PostgreSQL [database.md::8].")
    service = ArchitectureReviewService(
        store=store, generator=generator, reranker=FakeReranker()
    )

    result = service.answer_question("Which database is used?")

    assert result["answer"] == (
        "I couldn't produce an answer with citations that match the retrieved "
        "evidence. Please inspect the source documents or rephrase the question."
    )


def test_rag_rejects_answer_without_source_citation():
    store = FakeStore()
    store.add_document(
        "architecture.md::0",
        "The API handles requests, while a worker runs background jobs.",
        {"document_name": "architecture.md", "chunk_index": 0},
    )
    generator = FakeGenerator("The API and worker should be separate.")
    service = ArchitectureReviewService(
        store=store, generator=generator, reranker=FakeReranker()
    )

    result = service.answer_question("How should API and jobs be separated?")

    assert result["answer"] == (
        "I couldn't produce an answer with citations that match the retrieved "
        "evidence. Please inspect the source documents or rephrase the question."
    )


def test_follow_up_generation_receives_session_history(tmp_path):
    store = FakeStore()
    store.add_document(
        "architecture.md::0",
        "The API handles requests, while a worker runs background jobs.",
        {"document_name": "architecture.md", "chunk_index": 0},
    )
    generator = FakeGenerator()
    service = ArchitectureReviewService(
        store=store,
        generator=generator,
        reranker=FakeReranker(),
        memory_db_path=tmp_path / "sessions.sqlite3",
    )
    service.answer_question("What components are involved?", session_id="review-1")

    service.answer_question("How do they interact?", session_id="review-1")

    assert generator.calls[1]["history"] == [
        {
            "question": "What components are involved?",
            "answer": generator.answer,
        }
    ]


def test_upload_then_query_integration_uses_retrieved_evidence(
    tmp_path, monkeypatch
):
    store = FakeStore()
    generator = FakeGenerator("Separate API and background work [design.txt::0].")
    service = ArchitectureReviewService(
        store=store, generator=generator, reranker=FakeReranker()
    )
    monkeypatch.setattr(main, "service", service)
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)

    upload = client.post(
        "/api/upload",
        files={
            "file": (
                "design.txt",
                b"The API handles requests, while a worker runs background jobs.",
                "text/plain",
            )
        },
    )
    query = client.post(
        "/api/query",
        json={"question": "How should API and background jobs be separated?"},
    )

    assert upload.status_code == 200
    assert upload.json()["chunks_created"] == 1
    assert query.status_code == 200
    assert query.json()["answer"] == generator.answer
    assert query.json()["sources"][0]["document_name"] == "design.txt"
    assert generator.calls[0]["context"].startswith("[design.txt::0]")


def test_query_endpoint_supports_short_query_alias(tmp_path, monkeypatch):
    store = FakeStore()
    store.add_document(
        "design.txt::0",
        "The API handles requests, while a worker runs background jobs.",
        {"document_name": "design.txt", "chunk_index": 0},
    )
    service = ArchitectureReviewService(
        store=store,
        generator=FakeGenerator(),
        reranker=FakeReranker(),
        memory_db_path=tmp_path / "sessions.sqlite3",
    )
    monkeypatch.setattr(main, "service", service)
    main.app.state.rate_limit_buckets.clear()

    response = TestClient(main.app).post(
        "/query",
        json={"question": "How are requests handled?"},
    )

    assert response.status_code == 200
    assert response.json()["sources"][0]["chunk_id"] == "design.txt::0"


def test_query_reports_missing_llm_configuration_as_service_unavailable(monkeypatch):
    monkeypatch.delenv("HUGGINGFACEHUB_API_TOKEN", raising=False)
    store = FakeStore()
    store.add_document(
        "architecture.md::0",
        "The API handles requests, while a worker runs background jobs.",
        {"document_name": "architecture.md", "chunk_index": 0},
    )
    monkeypatch.setattr(
        main,
        "service",
        ArchitectureReviewService(
            store=store,
            generator=LangChainHuggingFaceGenerator(),
            reranker=FakeReranker(),
        ),
    )
    client = TestClient(main.app)

    response = client.post(
        "/api/query",
        json={"question": "How are requests handled?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "HUGGINGFACEHUB_API_TOKEN is required to generate an answer."
    )


def test_query_reports_provider_credit_exhaustion_as_service_unavailable(
    tmp_path, monkeypatch
):
    class FailedChain:
        def invoke(self, inputs):
            import httpx

            response = httpx.Response(
                402,
                request=httpx.Request(
                    "POST", "https://router.huggingface.co/v1/chat/completions"
                ),
            )
            raise HfHubHTTPError("private provider response", response=response)

    generator = LangChainHuggingFaceGenerator()
    generator._query_chain = FailedChain()
    monkeypatch.setattr(
        main,
        "service",
        ArchitectureReviewService(
            store=FakeStore(),
            generator=generator,
            reranker=FakeReranker(),
            memory_db_path=tmp_path / "sessions.sqlite3",
        ),
    )
    main.app.state.rate_limit_buckets.clear()

    response = TestClient(main.app).post(
        "/api/query",
        json={"question": "How does the architecture work?"},
    )

    assert response.status_code == 503
    assert "no available inference credits" in response.json()["detail"]
    assert "private provider response" not in response.text


def test_query_endpoint_persists_follow_up_history_and_clears_one_session(
    tmp_path, monkeypatch
):
    store = FakeStore()
    store.add_document(
        "architecture.md::0",
        "The API routes requests to domain services.",
        {"document_name": "architecture.md", "chunk_index": 0},
    )
    generator = FakeGenerator()
    service = ArchitectureReviewService(
        store=store,
        generator=generator,
        reranker=FakeReranker(),
        memory_db_path=tmp_path / "sessions.sqlite3",
    )
    monkeypatch.setattr(main, "service", service)
    client = TestClient(main.app)

    first = client.post(
        "/api/query",
        json={"question": "What routes requests?", "session_id": "review-1"},
    )
    second = client.post(
        "/api/query",
        json={"question": "What does it call?", "session_id": "review-1"},
    )
    cleared = client.post("/api/clear-session", json={"session_id": "review-1"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert generator.calls[1]["history"] == [
        {
            "question": "What routes requests?",
            "answer": generator.answer,
        }
    ]
    assert cleared.status_code == 200
    assert cleared.json() == {"status": "cleared", "session_id": "review-1"}
    assert service.memory.get_history("review-1") == []


def test_rag_scopes_query_to_selected_document():
    store = FakeStore()
    store.add_document(
        "old_file.pdf::0",
        "Old legacy specification from past project.",
        {"document_name": "old_file.pdf", "chunk_index": 0},
    )
    store.add_document(
        "new_architecture.pdf::0",
        "New microservices architecture specification with Kafka event bus.",
        {"document_name": "new_architecture.pdf", "chunk_index": 0},
    )
    generator = FakeGenerator("Review grounded in new architecture [new_architecture.pdf::0].")
    service = ArchitectureReviewService(
        store=store, generator=generator, reranker=FakeReranker()
    )

    result = service.answer_question(
        "What is the architecture?",
        metadata_filter={"document_name": "new_architecture.pdf"},
    )

    assert len(result["sources"]) == 1
    assert result["sources"][0]["document_name"] == "new_architecture.pdf"
    assert result["sources"][0]["chunk_id"] == "new_architecture.pdf::0"
    assert "old_file.pdf" not in result["answer"]
