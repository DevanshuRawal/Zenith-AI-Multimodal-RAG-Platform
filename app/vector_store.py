import math
from collections import Counter
from typing import Any, Dict, List


class InMemoryVectorStore:
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []

    def add_document(self, chunk_id: str, content: str, metadata: Dict[str, Any]):
        self.documents.append({
            "chunk_id": chunk_id,
            "content": content,
            "metadata": metadata,
        })

    def _tokenize(self, text: str) -> List[str]:
        return [token.lower() for token in text.replace("\n", " ").split() if token.strip()]

    def _embedding_from_text(self, text: str):
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        counts = Counter(tokens)
        normalizer = math.sqrt(sum(value * value for value in counts.values()))
        if normalizer == 0:
            return {}
        return {token: value / normalizer for token, value in counts.items()}

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vec = self._embedding_from_text(query)
        if not query_vec:
            return []

        hits = []
        for item in self.documents:
            item_vec = self._embedding_from_text(item["content"])
            score = 0.0
            for token, weight in query_vec.items():
                score += weight * item_vec.get(token, 0.0)

            if score > 0:
                hits.append({
                    "chunk_id": item["chunk_id"],
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "score": round(float(score), 4),
                })

        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits[:top_k]

    def clear(self):
        self.documents.clear()
