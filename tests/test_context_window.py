import pytest
from app.rag_service import ArchitectureReviewService
from app.retrieval import MultiQueryRetriever


class MockStore:
    def __init__(self, docs):
        self.docs = docs

    def search(self, query, top_k=5):
        return self.docs[:top_k]


class MockGenerator:
    def __init__(self):
        self.received_context = ""
        self.received_history = []

    def expand(self, question, history):
        return [question]

    def generate(self, question, context, history=None):
        self.received_context = context
        self.received_history = history or []
        # Return answer with citation from first chunk
        first_cid = context.split("]")[0].lstrip("[") if "[" in context else "doc::0"
        return f"Synthesized architecture assessment [{first_cid}]."


class MockReranker:
    def score(self, query, docs):
        return [1.0 - (i * 0.1) for i in range(len(docs))]


def test_context_window_budget_pruning():
    """Verify that when context exceeds token/character limit, chunks are preserved up to top_k without crash."""
    giant_docs = [
        {
            "chunk_id": f"large_doc.md::{i}",
            "content": f"Architectural specification paragraph {i}: " + ("data " * 150),
            "metadata": {"document_name": "large_doc.md", "chunk_index": i},
            "score": 0.95 - (i * 0.05),
            "similarity_score": 0.95 - (i * 0.05),
        }
        for i in range(10)
    ]
    store = MockStore(giant_docs)
    generator = MockGenerator()
    reranker = MockReranker()
    service = ArchitectureReviewService(store=store, generator=generator, reranker=reranker)

    result = service.answer_question("What is the architecture?", top_k=3)

    assert result["answer"] == "Synthesized architecture assessment [large_doc.md::0]."
    # Must only contain top_k chunks in context
    assert generator.received_context.count("large_doc.md::") == 3


def test_conversational_context_window_preserves_recent_turns(tmp_path):
    """Verify that multi-turn history maintains the most recent conversational context for follow-up questions."""
    docs = [
        {
            "chunk_id": "payment_service.md::0",
            "content": "Payment Service implements a decoupled event-driven architecture using Kafka, with 99.99% SLA availability.",
            "metadata": {"document_name": "payment_service.md", "chunk_index": 0},
            "score": 0.9,
            "similarity_score": 0.9,
        }
    ]
    store = MockStore(docs)
    generator = MockGenerator()
    reranker = MockReranker()
    session_db = tmp_path / "sessions.sqlite3"
    service = ArchitectureReviewService(
        store=store, generator=generator, reranker=reranker, memory_db_path=session_db
    )

    # Turn 1
    service.answer_question("Tell me about the Payment Service", session_id="user-123")
    assert len(generator.received_history) == 0

    # Turn 2: Follow-up question with pronoun "its"
    service.answer_question("What about its SLA?", session_id="user-123")
    assert len(generator.received_history) == 1
    assert generator.received_history[0]["question"] == "Tell me about the Payment Service"
