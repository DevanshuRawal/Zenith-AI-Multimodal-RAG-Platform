from qdrant_client import QdrantClient

from app.qdrant_store import QdrantVectorStore


class DeterministicEmbeddingModel:
    def get_embedding_dimension(self):
        return 2

    def encode(self, text):
        return [1.0, 0.0] if "api" in text.lower() else [0.0, 1.0]


def test_qdrant_store_can_store_and_search_text():
    store = QdrantVectorStore(collection_name="test_zenith_docs")
    store.clear()

    store.add_document(
        "doc-1",
        "Service boundaries should separate API, domain, and data access layers.",
        {"document_name": "sample.md", "chunk_index": 0, "source_path": "sample.md"},
    )

    results = store.search("How should we design service boundaries?", top_k=3)

    assert len(results) >= 1
    assert results[0]["metadata"]["document_name"] == "sample.md"
    assert "service" in results[0]["content"].lower()

    store.clear()


def test_qdrant_local_store_upserts_and_searches_stable_chunk_ids():
    client = QdrantClient(":memory:")
    store = QdrantVectorStore(
        collection_name="local_integration",
        client=client,
        model=DeterministicEmbeddingModel(),
    )

    store.add_document(
        "architecture.md::0",
        "A gateway calls the API service.",
        {
            "document_name": "architecture.pdf",
            "chunk_index": 0,
            "document_type": "standard",
            "source_type": "image_caption",
            "page_number": 2,
            "image_index": 0,
            "image_name": None,
        },
    )
    store.add_document(
        "design.md::0",
        "A gateway calls the API service.",
        {"document_name": "design.md", "document_type": "design"},
    )
    results = store.search(
        "gateway API",
        top_k=2,
        metadata_filter={"document_type": "standard"},
    )
    assert results == [
        {
            "chunk_id": "architecture.md::0",
            "content": "A gateway calls the API service.",
            "metadata": {
                "document_name": "architecture.pdf",
                "source_path": "",
                "chunk_index": 0,
                "source_type": "image_caption",
                "page_number": 2,
                "image_index": 0,
                "image_name": None,
                "document_type": "standard",
                "line_start": None,
                "line_end": None,
                "repository": None,
                "branch": None,
                "path": None,
            },
            "score": 1.0,
        }
    ]


def test_qdrant_returns_top_five_in_similarity_order():
    class RankedEmbeddingModel:
        def get_embedding_dimension(self):
            return 2

        def encode(self, text):
            vectors = {
                "query": [1.0, 0.0],
                "best": [1.0, 0.0],
                "close": [0.8, 0.6],
                "middle": [0.6, 0.8],
                "weak": [0.2, 0.98],
                "unrelated": [0.0, 1.0],
            }
            return vectors.get(text, [0.0, 1.0])

    store = QdrantVectorStore(
        collection_name="ranked_top_five",
        client=QdrantClient(":memory:"),
        model=RankedEmbeddingModel(),
    )
    for name in ("best", "close", "middle", "weak", "unrelated"):
        store.add_document(
            name,
            name,
            {
                "document_name": f"{name}.txt",
                "source_type": "original_text",
            },
        )

    results = store.search("query", top_k=5)

    assert [result["chunk_id"] for result in results] == [
        "best",
        "close",
        "middle",
        "weak",
        "unrelated",
    ]
    assert all(
        results[index]["score"] >= results[index + 1]["score"]
        for index in range(len(results) - 1)
    )
    assert results[0]["metadata"]["source_type"] == "original_text"
