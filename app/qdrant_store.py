from __future__ import annotations

import math
import threading
import logging
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

from app.config import (
    BASE_DIR,
    EMBEDDING_MODEL,
    QDRANT_COLLECTION,
    QDRANT_STORAGE_PATH,
    QDRANT_URL,
)

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    def __init__(
        self,
        collection_name: str = QDRANT_COLLECTION,
        url: str = QDRANT_URL,
        client: QdrantClient | None = None,
        model: Any = None,
        storage_path: str | Path | None = None,
    ):
        self.collection_name = collection_name
        self.url = url
        self.fallback_store: List[Dict[str, Any]] = []
        self.client = client
        self.model = model
        self._lock = threading.RLock()

        if self.client is None:
            # 1. Try remote Qdrant server if url is provided (with quick timeout)
            if url and url.startswith("http"):
                try:
                    self.client = QdrantClient(url=url, timeout=0.5, check_compatibility=False)
                    self.client.get_collections()
                    logger.info("Connected to remote Qdrant server at %s", url)
                except Exception:
                    self.client = None

            # 2. If remote server is unavailable (e.g. Docker not running), use local embedded Qdrant on disk
            if self.client is None:
                local_dir = storage_path or QDRANT_STORAGE_PATH
                try:
                    Path(local_dir).mkdir(parents=True, exist_ok=True)
                    self.client = QdrantClient(path=str(local_dir))
                    self.client.get_collections()
                    logger.info("Initialized local embedded Qdrant vector store at %s", local_dir)
                except Exception as exc:
                    logger.warning(
                        "Local embedded Qdrant unavailable (%s); using local lexical fallback.",
                        exc,
                    )
                    self.client = None

        if self.client is not None:
            if self.model is None:
                self.model = SentenceTransformer(EMBEDDING_MODEL)
            self._ensure_collection()

    def _ensure_collection(self):
        if self.client is None:
            return
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self.model.get_embedding_dimension(),
                    distance=qmodels.Distance.COSINE,
                ),
            )

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

    def add_document(self, chunk_id: str, content: str, metadata: Dict[str, Any]):
        if self.client is None:
            self.fallback_store.append({
                "chunk_id": chunk_id,
                "content": content,
                "metadata": metadata,
            })
            return

        vector = list(self.model.encode(content))
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"zenith:{chunk_id}"))
        with self._lock:
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        qmodels.PointStruct(
                            id=point_id,
                            vector=vector,
                            payload={**metadata, "content": content, "chunk_id": chunk_id},
                        )
                    ],
                )
            except Exception as exc:
                logger.warning("Upsert error for %s: %s; falling back to memory.", chunk_id, exc)
                self.fallback_store.append({
                    "chunk_id": chunk_id,
                    "content": content,
                    "metadata": metadata,
                })

    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Dict[str, Any] | None = None,
    ):
        if self.client is None:
            query_vec = self._embedding_from_text(query)
            if not query_vec:
                return []
            hits = []
            for item in self.fallback_store:
                if metadata_filter and not all(
                    item["metadata"].get(key) == value
                    for key, value in metadata_filter.items()
                ):
                    continue
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

        query_vector = list(self.model.encode(query))
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
            query_filter=(
                qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key=key, match=qmodels.MatchValue(value=value)
                        )
                        for key, value in metadata_filter.items()
                    ]
                )
                if metadata_filter
                else None
            ),
        )
        return [
            {
                "chunk_id": (hit.payload or {}).get("chunk_id", str(hit.id)),
                "content": (hit.payload or {}).get("content", ""),
                "metadata": {
                    "document_name": (hit.payload or {}).get("document_name", "unknown"),
                    "source_path": (hit.payload or {}).get("source_path", ""),
                    "chunk_index": (hit.payload or {}).get("chunk_index", 0),
                    "source_type": (hit.payload or {}).get("source_type", "text"),
                    "page_number": (hit.payload or {}).get("page_number"),
                    "image_index": (hit.payload or {}).get("image_index"),
                    "image_name": (hit.payload or {}).get("image_name"),
                    "document_type": (hit.payload or {}).get(
                        "document_type", "knowledge"
                    ),
                    "line_start": (hit.payload or {}).get("line_start"),
                    "line_end": (hit.payload or {}).get("line_end"),
                    "repository": (hit.payload or {}).get("repository"),
                    "branch": (hit.payload or {}).get("branch"),
                    "path": (hit.payload or {}).get("path"),
                },
                "score": float(hit.score),
            }
            for hit in result.points
        ]

    def list_documents(self) -> List[Dict[str, Any]]:
        docs = {}
        if self.client is not None:
            with self._lock:
                try:
                    offset = None
                    while True:
                        records, offset = self.client.scroll(
                            collection_name=self.collection_name,
                            limit=100,
                            offset=offset,
                            with_payload=True,
                        )
                        for r in records:
                            payload = r.payload or {}
                            doc_name = payload.get("document_name", "unknown")
                            doc_type = payload.get("document_type", "knowledge")
                            if doc_name not in docs:
                                docs[doc_name] = {
                                    "document_name": doc_name,
                                    "document_type": doc_type,
                                    "chunks": 0,
                                }
                            docs[doc_name]["chunks"] += 1
                        if offset is None:
                            break
                except Exception as exc:
                    logger.warning("Error scrolling documents: %s", exc)
        for item in self.fallback_store:
            meta = item.get("metadata", {})
            doc_name = meta.get("document_name", "unknown")
            doc_type = meta.get("document_type", "knowledge")
            if doc_name not in docs:
                docs[doc_name] = {
                    "document_name": doc_name,
                    "document_type": doc_type,
                    "chunks": 0,
                }
            docs[doc_name]["chunks"] += 1
        return list(docs.values())

    def delete_document(self, document_name: str) -> bool:
        self.fallback_store = [
            doc for doc in self.fallback_store
            if doc.get("metadata", {}).get("document_name") != document_name
        ]
        if self.client is not None:
            with self._lock:
                try:
                    if self.client.collection_exists(self.collection_name):
                        self.client.delete(
                            collection_name=self.collection_name,
                            points_selector=qmodels.FilterSelector(
                                filter=qmodels.Filter(
                                    must=[
                                        qmodels.FieldCondition(
                                            key="document_name",
                                            match=qmodels.MatchValue(value=document_name),
                                        )
                                    ]
                                )
                            ),
                        )
                        return True
                except Exception as exc:
                    logger.warning("Error deleting document %s: %s", document_name, exc)
        return False

    def clear(self):
        self.fallback_store.clear()
        if self.client is None:
            return
        with self._lock:
            try:
                if self.client.collection_exists(self.collection_name):
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=qmodels.FilterSelector(filter=qmodels.Filter()),
                    )
            except Exception as exc:
                logger.warning("Error deleting points in clear: %s", exc)
                try:
                    self.client.delete_collection(self.collection_name)
                    self._ensure_collection()
                except Exception:
                    pass
