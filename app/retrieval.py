import logging
import os
from typing import Any

from app.config import RETRIEVAL_CANDIDATE_K, SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)


class MultiQueryRetriever:
    def __init__(
        self,
        store: Any,
        query_expander: Any,
        reranker: Any,
        candidate_k: int = RETRIEVAL_CANDIDATE_K,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ):
        if candidate_k <= 0:
            raise ValueError("candidate_k must be greater than zero.")
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between zero and one.")
        self.store = store
        self.query_expander = query_expander
        self.reranker = reranker
        self.candidate_k = candidate_k
        self.similarity_threshold = similarity_threshold

    def search(
        self,
        question: str,
        top_k: int = 5,
        history: list[dict] | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ):
        queries = self.query_expander.expand(question, history or [])
        unique_queries = list(dict.fromkeys([question, *queries]))
        candidates = {}

        for query in unique_queries:
            search_options = {"top_k": self.candidate_k}
            if metadata_filter:
                search_options["metadata_filter"] = metadata_filter
            for hit in self.store.search(query, **search_options):
                similarity = float(hit["score"])
                candidate = {**hit, "similarity_score": similarity}
                existing = candidates.get(hit["chunk_id"])
                if (
                    existing is None
                    or similarity > existing["similarity_score"]
                ):
                    candidates[hit["chunk_id"]] = candidate

        hits = sorted(
            candidates.values(),
            key=lambda hit: hit["similarity_score"],
            reverse=True,
        )[: self.candidate_k]
        if not hits:
            return []

        scores = self.reranker.score(
            question,
            [hit["content"] for hit in hits],
        )
        if len(scores) != len(hits):
            raise ValueError("Reranker must return one score per retrieved document.")

        for hit, score in zip(hits, scores):
            hit["score"] = float(score)

        filtered = [
            hit
            for hit in hits
            if hit["similarity_score"] >= self.similarity_threshold
        ]
        # In live environments with dense embeddings, if no candidates pass the rigid
        # threshold (e.g. 0.7), use candidates with positive similarity (> 0.1)
        if not filtered and hits and any(h.get("similarity_score", 0) > 0.1 for h in hits):
            filtered = [h for h in hits if h.get("similarity_score", 0) > 0.1]

        hits = filtered
        hits.sort(key=lambda hit: hit["score"], reverse=True)
        return hits[:top_k]


class CrossEncoderReranker:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model: Any = None

    def score(self, question: str, documents: list[str]) -> list[float]:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        pairs = [(question, document) for document in documents]
        return [float(score) for score in self._model.predict(pairs)]
