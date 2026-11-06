import pytest
from fastapi.testclient import TestClient

from app import main
from app.ingestion import extract_pdf_images
from app.rag_service import ArchitectureReviewService
from app.vision import HuggingFaceImageCaptioner


class FakePage:
    def __init__(self, images):
        self._images = images

    def get_images(self, full):
        assert full is True
        return self._images


def test_extract_pdf_images_includes_page_and_image_indexes(monkeypatch, tmp_path):
    class FakeDocument:
        pages = [FakePage([(11,)]), FakePage([])]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def __iter__(self):
            return iter(self.pages)

        def extract_image(self, xref):
            assert xref == 11
            return {"ext": "png", "image": b"diagram-bytes"}

    import app.ingestion

    from types import SimpleNamespace

    monkeypatch.setattr(
        app.ingestion, "pymupdf", SimpleNamespace(open=lambda path: FakeDocument())
    )

    images = extract_pdf_images(str(tmp_path / "architecture.pdf"))

    assert images == [
        {
            "page_number": 1,
            "image_index": 0,
            "image_name": "image_11.png",
            "data": b"diagram-bytes",
        }
    ]


def test_huggingface_captioner_uses_configured_vision_model(monkeypatch):
    import huggingface_hub

    calls = {}

    class FakeInferenceClient:
        def __init__(self, token, model):
            calls["token"] = token
            calls["model"] = model

        def image_to_text(self, image):
            calls["image"] = image
            return [type("Caption", (), {"text": "A gateway connects to two services."})()]

    monkeypatch.setenv("HUGGINGFACEHUB_API_TOKEN", "test-token")
    monkeypatch.setattr(huggingface_hub, "InferenceClient", FakeInferenceClient)
    captioner = HuggingFaceImageCaptioner(model_name="test/vision-model")

    caption = captioner.caption(b"diagram-bytes")

    assert caption == "A gateway connects to two services."
    assert calls == {
        "token": "test-token",
        "model": "test/vision-model",
        "image": b"diagram-bytes",
    }


def test_captioner_requires_token_explicitly(monkeypatch):
    monkeypatch.delenv("HUGGINGFACEHUB_API_TOKEN", raising=False)
    captioner = HuggingFaceImageCaptioner(model_name="test/vision-model")

    with pytest.raises(RuntimeError, match="HUGGINGFACEHUB_API_TOKEN"):
        captioner.caption(b"diagram-bytes")


def test_image_upload_is_captioned_and_indexed_with_provenance(tmp_path, monkeypatch):
    class Store:
        def __init__(self):
            self.documents = []

        def add_document(self, chunk_id, content, metadata):
            self.documents.append(
                {"chunk_id": chunk_id, "content": content, "metadata": metadata}
            )

        def search(self, query, top_k=5):
            return [
                {
                    **document,
                    "score": 0.9,
                }
                for document in self.documents[:top_k]
            ]

        def clear(self):
            self.documents.clear()

    class Captioner:
        def caption(self, image_bytes):
            assert image_bytes == b"image-bytes"
            return "A gateway routes traffic to the API service."

    class Generator:
        def __init__(self):
            self.context = None

        def expand(self, question, history):
            return [question]

        def generate(self, question, context, history):
            self.context = context
            return "The diagram shows a gateway routing traffic [diagram.png::image::0]."

    class Reranker:
        def score(self, question, documents):
            return [0.9] * len(documents)

    store = Store()
    generator = Generator()
    service = ArchitectureReviewService(
        store=store,
        generator=generator,
        reranker=Reranker(),
        vision_captioner=Captioner(),
    )
    monkeypatch.setattr(main, "service", service)
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)

    response = client.post(
        "/api/upload",
        files={"file": ("diagram.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["chunks_created"] == 1
    assert store.documents == [
        {
            "chunk_id": "diagram.png::image::0",
            "content": "A gateway routes traffic to the API service.",
            "metadata": {
                "document_name": "diagram.png",
                "source_path": "diagram.png",
                "source_type": "image_caption",
                "image_index": 0,
                "page_number": None,
                "image_name": "diagram.png",
                "document_type": "knowledge",
            },
        }
    ]
    query = client.post(
        "/api/query",
        json={"question": "What does the uploaded diagram show?"},
    )
    assert query.status_code == 200
    assert query.json()["answer"] == (
        "The diagram shows a gateway routing traffic [diagram.png::image::0]."
    )
    assert query.json()["sources"][0]["snippet"] == (
        "A gateway routes traffic to the API service."
    )
    assert query.json()["sources"][0]["source_type"] == "image_caption"
    assert query.json()["sources"][0]["image_index"] == 0
    assert "A gateway routes traffic to the API service." in generator.context


def test_pdf_upload_indexes_text_and_captions_for_diagrams(tmp_path, monkeypatch):
    class Store:
        def __init__(self):
            self.documents = []

        def add_document(self, chunk_id, content, metadata):
            self.documents.append(
                {"chunk_id": chunk_id, "content": content, "metadata": metadata}
            )

        def search(self, query, top_k=5):
            return []

        def clear(self):
            self.documents.clear()

    class Captioner:
        def caption(self, image_bytes):
            return "A client calls an API gateway."

    class Generator:
        def expand(self, question, history):
            return [question]

        def generate(self, question, context, history):
            return ""

    import app.rag_service

    monkeypatch.setattr(app.rag_service, "read_document_text", lambda path: "The system has an API.")
    monkeypatch.setattr(
        app.rag_service,
        "extract_pdf_images",
        lambda path: [
            {
                "page_number": 2,
                "image_index": 0,
                "image_name": "diagram.png",
                "data": b"diagram-bytes",
            }
        ],
    )
    store = Store()
    service = ArchitectureReviewService(
        store=store, generator=Generator(), vision_captioner=Captioner()
    )

    count = service.ingest_document(str(tmp_path / "architecture.pdf"), "architecture.pdf")

    assert count == 2
    assert [doc["metadata"]["source_type"] for doc in store.documents] == [
        "original_text",
        "image_caption",
    ]
    assert store.documents[1]["metadata"]["page_number"] == 2
    assert store.documents[1]["chunk_id"] == "architecture.pdf::image::0"


def test_upload_rejects_unsupported_file_type(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    response = TestClient(main.app).post(
        "/api/upload",
        files={"file": ("payload.bin", b"binary", "application/octet-stream")},
    )

    assert response.status_code == 415


def test_image_upload_reports_missing_vision_credentials(tmp_path, monkeypatch):
    class Store:
        def add_document(self, chunk_id, content, metadata):
            raise AssertionError("The image must not be indexed without a caption.")

        def search(self, query, top_k=5):
            return []

        def clear(self):
            pass

    class Generator:
        def expand(self, question, history):
            return [question]

        def generate(self, question, context, history):
            return ""

    monkeypatch.delenv("HUGGINGFACEHUB_API_TOKEN", raising=False)
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(
        main,
        "service",
        ArchitectureReviewService(
            store=Store(),
            generator=Generator(),
            reranker=object(),
            vision_captioner=HuggingFaceImageCaptioner(),
        ),
    )

    response = TestClient(main.app).post(
        "/api/upload",
        files={"file": ("diagram.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "HUGGINGFACEHUB_API_TOKEN is required to caption diagrams."
    )
