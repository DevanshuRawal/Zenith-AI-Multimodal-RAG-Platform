from fastapi.testclient import TestClient

from app import main
from app.rag_service import ArchitectureReviewService


class StandardsStore:
    def __init__(self):
        self.documents = []
        self.searches = []

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
        self.searches.append((query, metadata_filter))
        hits = self.documents
        if metadata_filter:
            hits = [
                hit for hit in hits
                if all(
                    hit["metadata"].get(key) == value
                    for key, value in metadata_filter.items()
                )
            ]
        return hits[:top_k]

    def clear(self):
        self.documents.clear()


class ComplianceGenerator:
    def __init__(self, source_id="security-standard.md::0"):
        self.calls = []
        self.source_id = source_id

    def expand(self, question, history):
        return [question]

    def generate_compliance(self, design, context):
        self.calls.append({"design": design, "context": context})
        return (
            "Status: PARTIAL\n"
            "Gap: The design does not specify encryption at rest "
            f"[{self.source_id}].\n"
            "Recommendation: Define encryption for stored data "
            f"[{self.source_id}]."
        )


class ComplianceReranker:
    def score(self, question, documents):
        return [0.9] * len(documents)


def test_compliance_review_retrieves_only_internal_standards():
    store = StandardsStore()
    store.add_document(
        "security-standard.md::0",
        "All persistent customer data must be encrypted at rest.",
        {"document_name": "security-standard.md", "document_type": "standard"},
    )
    store.add_document(
        "design.md::0",
        "The service stores customer records in a database.",
        {"document_name": "design.md", "document_type": "design"},
    )
    generator = ComplianceGenerator()
    service = ArchitectureReviewService(
        store=store,
        generator=generator,
        reranker=ComplianceReranker(),
    )

    result = service.review_compliance("The service stores customer records.")

    assert store.searches[0][1] == {"document_type": "standard"}
    assert result["status"] == "PARTIAL"
    assert result["sources"][0]["document_name"] == "security-standard.md"
    assert generator.calls[0]["design"] == "The service stores customer records."
    assert "encrypted at rest" in generator.calls[0]["context"]


def test_compliance_review_does_not_generate_when_no_standards_exist():
    store = StandardsStore()
    generator = ComplianceGenerator()
    service = ArchitectureReviewService(
        store=store,
        generator=generator,
        reranker=ComplianceReranker(),
    )

    result = service.review_compliance("A proposed design")

    assert result["status"] == "NOT_REVIEWED"
    assert result["sources"] == []
    assert generator.calls == []


def test_compliance_review_rejects_uncited_or_unverified_findings():
    store = StandardsStore()
    store.add_document(
        "security-standard.md::0",
        "Persistent customer data must be encrypted at rest.",
        {"document_name": "security-standard.md", "document_type": "standard"},
    )
    generator = ComplianceGenerator()
    generator.generate_compliance = lambda design, context: (
        "Status: COMPLIANT\n"
        "Finding: Data is encrypted [unrelated.md::9]."
    )
    service = ArchitectureReviewService(
        store=store,
        generator=generator,
        reranker=ComplianceReranker(),
    )

    result = service.review_compliance("The design encrypts data.")

    assert result["status"] == "REVIEW_BLOCKED"
    assert "citation" in result["review"].lower()


def test_compliance_review_requires_a_citation_on_each_finding():
    store = StandardsStore()
    store.add_document(
        "security-standard.md::0",
        "Persistent customer data must be encrypted at rest.",
        {"document_name": "security-standard.md", "document_type": "standard"},
    )
    generator = ComplianceGenerator()
    generator.generate_compliance = lambda design, context: (
        "Status: PARTIAL\n"
        "Gap: Encryption at rest is not specified.\n"
        "Recommendation: Add encryption [security-standard.md::0]."
    )
    service = ArchitectureReviewService(
        store=store,
        generator=generator,
        reranker=ComplianceReranker(),
    )

    result = service.review_compliance("The design stores customer records.")

    assert result["status"] == "REVIEW_BLOCKED"


def test_standard_upload_then_compliance_review_integration(tmp_path, monkeypatch):
    store = StandardsStore()
    generator = ComplianceGenerator("security-standard.txt::0")
    service = ArchitectureReviewService(
        store=store,
        generator=generator,
        reranker=ComplianceReranker(),
    )
    monkeypatch.setattr(main, "service", service)
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)

    uploaded = client.post(
        "/api/upload",
        data={"document_type": "standard"},
        files={
            "file": (
                "security-standard.txt",
                b"All persistent customer data must be encrypted at rest.",
                "text/plain",
            )
        },
    )
    review = client.post(
        "/api/compliance-review",
        json={"design": "The service stores customer records in a database."},
    )

    assert uploaded.status_code == 200
    assert uploaded.json()["chunks_created"] == 1
    assert store.documents[0]["metadata"]["document_type"] == "standard"
    assert review.status_code == 200
    assert review.json()["status"] == "PARTIAL"
    assert review.json()["sources"][0]["document_name"] == "security-standard.txt"
    assert "[security-standard.txt::0]" in generator.calls[0]["context"]


def test_upload_rejects_unknown_document_type(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    response = TestClient(main.app).post(
        "/api/upload",
        data={"document_type": "private"},
        files={"file": ("design.txt", b"Design proposal.", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "document_type must be knowledge, standard, or design."
    )
