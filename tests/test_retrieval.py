from app.retrieval import MultiQueryRetriever


class FakeStore:
    def __init__(self):
        self.queries = []
        self.results = {
            "How should uploads be handled?": [
                {
                    "chunk_id": "upload::0",
                    "content": "The API accepts uploaded PDF documents.",
                    "metadata": {"document_name": "upload.md"},
                    "score": 0.6,
                },
                {
                    "chunk_id": "worker::0",
                    "content": "A worker processes jobs asynchronously.",
                    "metadata": {"document_name": "worker.md"},
                    "score": 0.3,
                },
            ],
            "PDF ingestion pipeline": [
                {
                    "chunk_id": "upload::0",
                    "content": "The API accepts uploaded PDF documents.",
                    "metadata": {"document_name": "upload.md"},
                    "score": 0.7,
                },
                {
                    "chunk_id": "parser::0",
                    "content": "PyMuPDF extracts text from PDFs.",
                    "metadata": {"document_name": "parser.md"},
                    "score": 0.4,
                },
            ],
        }

    def search(self, query, top_k=5):
        self.queries.append(query)
        return self.results.get(query, [])[:top_k]


class FakeQueryExpander:
    def expand(self, question, history):
        return [question, "PDF ingestion pipeline"]


class FakeReranker:
    def score(self, question, documents):
        scores = {
            "The API accepts uploaded PDF documents.": 0.2,
            "A worker processes jobs asynchronously.": 0.3,
            "PyMuPDF extracts text from PDFs.": 0.95,
        }
        return [scores[document] for document in documents]


def test_multi_query_retrieval_deduplicates_and_reranks_documents():
    store = FakeStore()
    retriever = MultiQueryRetriever(
        store=store,
        query_expander=FakeQueryExpander(),
        reranker=FakeReranker(),
    )

    results = retriever.search("How should uploads be handled?", top_k=3)

    assert store.queries == [
        "How should uploads be handled?",
        "PDF ingestion pipeline",
    ]
    assert [result["chunk_id"] for result in results] == ["upload::0"]
    assert results[0]["score"] == 0.2
    assert results[0]["similarity_score"] == 0.7


def test_multi_query_retrieval_passes_session_history_to_query_expander():
    class HistoryExpander:
        def __init__(self):
            self.history = None

        def expand(self, question, history):
            self.history = history
            return [question]

    expander = HistoryExpander()
    retriever = MultiQueryRetriever(
        store=FakeStore(),
        query_expander=expander,
        reranker=FakeReranker(),
    )
    history = [{"question": "What handles uploads?", "answer": "The API."}]

    retriever.search("How does it validate files?", top_k=2, history=history)

    assert expander.history == history


def test_retriever_fetches_and_reranks_at_most_twenty_candidates():
    class CandidateStore:
        def __init__(self):
            self.requested_limits = []

        def search(self, query, top_k=5, metadata_filter=None):
            self.requested_limits.append(top_k)
            return [
                {
                    "chunk_id": f"chunk-{index}",
                    "content": f"candidate {index}",
                    "metadata": {},
                    "score": 0.9,
                }
                for index in range(30)
            ][:top_k]

    class CandidateExpander:
        def expand(self, question, history):
            return []

    class RecordingReranker:
        def __init__(self):
            self.document_count = 0

        def score(self, question, documents):
            self.document_count = len(documents)
            return [1.0] * len(documents)

    store = CandidateStore()
    reranker = RecordingReranker()
    retriever = MultiQueryRetriever(store, CandidateExpander(), reranker)

    results = retriever.search("architecture", top_k=20)

    assert store.requested_limits == [20]
    assert reranker.document_count == 20
    assert len(results) == 20


def test_retriever_filters_below_similarity_threshold_and_keeps_boundary():
    class ThresholdStore:
        def search(self, query, top_k=5, metadata_filter=None):
            return [
                {
                    "chunk_id": "below",
                    "content": "below cutoff",
                    "metadata": {},
                    "score": 0.699,
                },
                {
                    "chunk_id": "at-cutoff",
                    "content": "at cutoff",
                    "metadata": {},
                    "score": 0.7,
                },
                {
                    "chunk_id": "above",
                    "content": "above cutoff",
                    "metadata": {},
                    "score": 0.9,
                },
            ][:top_k]

    class ThresholdExpander:
        def expand(self, question, history):
            return []

    class ThresholdReranker:
        def score(self, question, documents):
            return [0.9, 0.8, 0.7]

    retriever = MultiQueryRetriever(
        ThresholdStore(), ThresholdExpander(), ThresholdReranker()
    )

    results = retriever.search("architecture", top_k=5)

    assert {result["chunk_id"] for result in results} == {"at-cutoff", "above"}


def test_retriever_keeps_best_similarity_for_duplicate_multi_query_hits():
    class DuplicateStore:
        def search(self, query, top_k=5, metadata_filter=None):
            similarity = 0.6 if query == "architecture" else 0.8
            return [
                {
                    "chunk_id": "shared",
                    "content": "shared evidence",
                    "metadata": {},
                    "score": similarity,
                }
            ]

    class DuplicateExpander:
        def expand(self, question, history):
            return ["architecture variant"]

    class DuplicateReranker:
        def score(self, question, documents):
            return [0.9] * len(documents)

    retriever = MultiQueryRetriever(
        DuplicateStore(), DuplicateExpander(), DuplicateReranker()
    )

    results = retriever.search("architecture", top_k=5)

    assert len(results) == 1
    assert results[0]["similarity_score"] == 0.8
