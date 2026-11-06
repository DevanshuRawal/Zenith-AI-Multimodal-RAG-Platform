from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main
from app.ingestion import chunk_text, chunk_text_with_locations, extract_pdf_images, extract_text_from_pdf
from app.rag_service import ArchitectureReviewService


def test_default_chunking_uses_one_thousand_characters_and_one_hundred_overlap():
    chunks = chunk_text("x" * 2100)

    assert [len(chunk) for chunk in chunks] == [1000, 1000, 300]
    assert chunks[0][-100:] == chunks[1][:100]
    assert chunks[1][-100:] == chunks[2][:100]


def test_pdf_extraction_uses_pymupdf_text_and_image_bytes(monkeypatch, tmp_path):
    class Page:
        def __init__(self, text, images=()):
            self._text = text
            self._images = images

        def get_text(self, kind):
            assert kind == "text"
            return self._text

        def get_images(self, full):
            assert full is True
            return self._images

    class Document:
        pages = [Page("First page.", [(11,)]), Page("Second page.")]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def __iter__(self):
            return iter(self.pages)

        def extract_image(self, xref):
            assert xref == 11
            return {"ext": "png", "image": b"\x89PNG\r\n"}

    import app.ingestion

    monkeypatch.setattr(
        app.ingestion, "pymupdf", SimpleNamespace(open=lambda path: Document())
    )
    pdf_path = str(tmp_path / "architecture.pdf")

    assert extract_text_from_pdf(pdf_path) == "First page.\n\nSecond page."
    assert extract_pdf_images(pdf_path) == [
        {
            "page_number": 1,
            "image_index": 0,
            "image_name": "image_11.png",
            "data": b"\x89PNG\r\n",
        }
    ]


def test_chunk_locations_map_normalized_chunks_to_original_line_numbers():
    text = "def first():\n    return 'alpha beta'\n\n\ndef second():\n    return 'gamma delta'\n"

    chunks = chunk_text_with_locations(text, chunk_size=36, overlap=0)

    assert chunks == [
        {
            "content": "def first(): return 'alpha beta' def",
            "line_start": 1,
            "line_end": 5,
        },
        {
            "content": " second(): return 'gamma delta'",
            "line_start": 5,
            "line_end": 6,
        },
    ]


def test_chunk_locations_handle_blank_text_and_overlap():
    assert chunk_text_with_locations(" \n\t ") == []

    chunks = chunk_text_with_locations(
        "first line\nsecond line\nthird line", chunk_size=16, overlap=4
    )

    assert len(chunks) > 1
    assert chunks[0]["content"][-4:] == chunks[1]["content"][:4]
    assert all(chunk["line_start"] <= chunk["line_end"] for chunk in chunks)


def test_chunk_location_does_not_attribute_trailing_separator_to_next_line():
    chunks = chunk_text_with_locations("alpha\nbeta", chunk_size=6, overlap=0)

    assert chunks == [
        {"content": "alpha ", "line_start": 1, "line_end": 1},
        {"content": "beta", "line_start": 2, "line_end": 2},
    ]


def test_upload_query_returns_file_and_line_citation(tmp_path, monkeypatch):
    class Store:
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
            hits = self.documents
            if metadata_filter:
                hits = [
                    hit
                    for hit in hits
                    if all(
                        hit["metadata"].get(key) == value
                        for key, value in metadata_filter.items()
                    )
                ]
            return hits[:top_k]

        def clear(self):
            self.documents.clear()

    class Generator:
        def expand(self, question, history):
            return [question]

        def generate(self, question, context, history):
            return "The route returns alpha [src/routes.py::0]."

    class Reranker:
        def score(self, question, documents):
            return [0.9] * len(documents)

    store = Store()
    service = ArchitectureReviewService(
        store=store,
        generator=Generator(),
        reranker=Reranker(),
        memory_db_path=tmp_path / "sessions.sqlite3",
    )
    monkeypatch.setattr(main, "service", service)
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)

    upload = client.post(
        "/api/upload",
        files={
            "file": (
                "routes.txt",
                b"def route():\n    return 'alpha'\n",
                "text/plain",
            )
        },
    )
    query = client.post("/api/query", json={"question": "What does route return?"})

    assert upload.status_code == 200
    assert query.status_code == 200
    assert query.json()["sources"][0]["source_path"].endswith("routes.txt")
    assert query.json()["sources"][0]["source_type"] == "original_text"
    assert query.json()["sources"][0]["line_start"] == 1
    assert query.json()["sources"][0]["line_end"] == 2
