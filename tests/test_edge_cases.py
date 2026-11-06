import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ingestion import read_document_text, chunk_text_with_locations
from app.llm import LocalGroundedGenerator


@pytest.fixture
def client():
    return TestClient(app)


def test_corrupted_pdf_upload_handled_gracefully(client, tmp_path):
    """Uploading a corrupted PDF should return 400/422 without crashing the backend."""
    corrupted_bytes = b"%PDF-1.4\n corrupted stream data not closed %%EOF"
    response = client.post(
        "/api/upload",
        files={"file": ("corrupt_sample.pdf", corrupted_bytes, "application/pdf")},
        data={"document_type": "knowledge"},
    )
    # Backend should handle cleanly (either 400 error or safely parsed without unhandled crash)
    assert response.status_code in [200, 400, 422]


def test_empty_file_upload(client):
    """Uploading an empty 0-byte file should be rejected or indexed with 0 chunks."""
    response = client.post(
        "/api/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
        data={"document_type": "knowledge"},
    )
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        assert response.json()["chunks_created"] == 0


def test_chunking_with_special_characters_and_whitespace():
    """Verify chunking handles Unicode symbols, emojis, and unusual whitespace."""
    text = "Architecture Review 🚀\n\n\t• Boundary: Service A ➔ Service B\n\n" * 20
    chunks = chunk_text_with_locations(text, chunk_size=200, overlap=30)

    assert len(chunks) > 0
    for chunk in chunks:
        assert "Service A" in chunk["content"]
        assert chunk["line_start"] >= 1
        assert chunk["line_end"] >= chunk["line_start"]


def test_synthesis_handles_conflicting_spec_details():
    """Verify synthesis when documents contain overlapping or varying architecture tiers."""
    context = (
        "[gateway_specs.md::0]\n"
        "Standard API Gateway configuration supports up to 5,000 requests per second.\n\n"
        "[gateway_specs.md::1]\n"
        "Enterprise API Gateway cluster configuration scales up to 25,000 requests per second."
    )
    generator = LocalGroundedGenerator()
    question = "What is the supported throughput for the API Gateway?"
    response = generator.generate(question, context, history=[])

    assert "5,000" in response or "25,000" in response
    assert "[gateway_specs.md::0]" in response or "[gateway_specs.md::1]" in response


def test_unsupported_file_extension_rejected(client):
    """Uploading executable or unsupported binary formats should be rejected."""
    response = client.post(
        "/api/upload",
        files={"file": ("malware.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/octet-stream")},
        data={"document_type": "knowledge"},
    )
    assert response.status_code in [400, 415, 422]
