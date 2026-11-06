import re
from pathlib import Path
from typing import Any

from app.config import (
    CHUNK_OVERLAP,
    MAX_CHUNK_SIZE,
    RERANKER_MODEL,
    SESSION_DB_PATH,
    TOP_K,
)
from app.ingestion import chunk_text_with_locations, extract_pdf_images, read_document_text
from app.llm import LangChainHuggingFaceGenerator
from app.memory import SQLiteConversationMemory
from app.qdrant_store import QdrantVectorStore
from app.retrieval import CrossEncoderReranker, MultiQueryRetriever
from app.vision import HuggingFaceImageCaptioner


class ArchitectureReviewService:
    def __init__(
        self,
        store: Any = None,
        generator: Any = None,
        reranker: Any = None,
        vision_captioner: Any = None,
        memory_db_path: str | Path = SESSION_DB_PATH,
    ):
        self.store = store or QdrantVectorStore()
        self.generator = generator or LangChainHuggingFaceGenerator()
        self.vision_captioner = vision_captioner or HuggingFaceImageCaptioner()
        self.retriever = MultiQueryRetriever(
            store=self.store,
            query_expander=self.generator,
            reranker=reranker or CrossEncoderReranker(RERANKER_MODEL),
        )
        self.memory = SQLiteConversationMemory(memory_db_path)
        self.session_memory = self.memory

    def ingest_document(self, file_path: str, document_name: str):
        return self.ingest_typed_document(file_path, document_name, "knowledge")

    def ingest_typed_document(
        self, file_path: str, document_name: str, document_type: str
    ):
        suffix = document_name.rsplit(".", 1)[-1].lower() if "." in document_name else ""
        if suffix in {"png", "jpg", "jpeg", "webp"}:
            images = [
                {
                    "page_number": None,
                    "image_index": 0,
                    "image_name": document_name,
                    "data": Path(file_path).read_bytes(),
                }
            ]
            text = ""
        else:
            text = read_document_text(file_path)
            images = extract_pdf_images(file_path) if suffix == "pdf" else []

        text_chunks = chunk_text_with_locations(
            text, chunk_size=MAX_CHUNK_SIZE, overlap=CHUNK_OVERLAP
        )
        for index, chunk_info in enumerate(text_chunks):
            chunk = chunk_info["content"]
            chunk_id = f"{document_name}::{index}"
            self.store.add_document(
                chunk_id=chunk_id,
                content=chunk,
                metadata={
                    "document_name": document_name,
                    "source_path": document_name,
                    "chunk_index": index,
                    "source_type": "original_text",
                    "document_type": document_type,
                    "line_start": chunk_info["line_start"],
                    "line_end": chunk_info["line_end"],
                },
            )
        for image in images:
            caption = self.vision_captioner.caption(image["data"])
            image_index = image["image_index"]
            chunk_id = f"{document_name}::image::{image_index}"
            self.store.add_document(
                chunk_id=chunk_id,
                content=caption,
                metadata={
                    "document_name": document_name,
                    "source_path": document_name,
                    "source_type": "image_caption",
                    "image_index": image_index,
                    "page_number": image["page_number"],
                    "image_name": image["image_name"],
                    "document_type": document_type,
                },
            )
        return len(text_chunks) + len(images)

    def review_compliance(self, design: str, top_k: int = TOP_K):
        query = (
            "Internal architecture standards and compliance requirements relevant "
            f"to this proposed design:\n{design}"
        )
        hits = self.retriever.search(
            query,
            top_k=top_k,
            metadata_filter={"document_type": "standard"},
        )
        if not hits:
            return {
                "status": "NOT_REVIEWED",
                "review": (
                    "No indexed internal standards were found. Upload documents "
                    "as document_type='standard' before requesting a compliance review."
                ),
                "sources": [],
            }

        context = "\n\n".join(
            f"[{hit['chunk_id']}]\n{hit['content']}" for hit in hits
        )
        review = self.generator.generate_compliance(design=design, context=context)
        citations = set(re.findall(r"\[([^\]]+)\]", review))
        retrieved_ids = {hit["chunk_id"] for hit in hits}
        finding_lines = [
            line
            for line in review.splitlines()
            if re.match(r"(?i)^\s*(finding|gap|recommendation):", line)
        ]
        status_match = re.search(
            r"(?im)^\s*Status:\s*(COMPLIANT|PARTIAL|NON_COMPLIANT)\s*$",
            review,
        )
        if (
            not citations
            or not citations.issubset(retrieved_ids)
            or not finding_lines
            or any(not re.search(r"\[[^\]]+\]", line) for line in finding_lines)
            or status_match is None
        ):
            status = "REVIEW_BLOCKED"
            review = (
                "The compliance review could not be verified against retrieved "
                "standard citations. Inspect the sources and try again."
            )
        else:
            status = status_match.group(1).upper()

        return {
            "status": status,
            "review": review,
            "sources": [
                {
                    "document_name": hit["metadata"].get(
                        "document_name", "unknown"
                    ),
                    "chunk_id": hit["chunk_id"],
                    "score": hit["score"],
                    "similarity_score": hit["similarity_score"],
                    "snippet": hit["content"][:220],
                    "source_type": hit["metadata"].get("source_type", "text"),
                    "page_number": hit["metadata"].get("page_number"),
                    "image_index": hit["metadata"].get("image_index"),
                    "source_path": hit["metadata"].get("source_path"),
                    "line_start": hit["metadata"].get("line_start"),
                    "line_end": hit["metadata"].get("line_end"),
                    "repository": hit["metadata"].get("repository"),
                    "branch": hit["metadata"].get("branch"),
                    "path": hit["metadata"].get("path"),
                }
                for hit in hits
            ],
        }

    def answer_question(
        self,
        question: str,
        top_k: int = TOP_K,
        session_id: str | None = None,
        metadata_filter: dict | None = None,
    ):
        history = (
            self.memory.get_history(session_id, limit=5) if session_id else []
        )
        hits = self.retriever.search(
            question, top_k=top_k, history=history, metadata_filter=metadata_filter
        )

        if not hits:
            answer = (
                "I couldn't find supporting information in the indexed documents, "
                "so I can't answer this reliably."
            )
            if session_id:
                self.memory.append(
                    session_id, {"question": question, "answer": answer}
                )
            return {
                "answer": answer,
                "sources": [],
                "context": "",
            }

        context = "\n\n".join(
            f"[{hit['chunk_id']}]\n{hit['content']}" for hit in hits
        )
        answer = self.generator.generate(
            question=question,
            context=context,
            history=history,
        )
        citations = set(re.findall(r"\[([^\]]+)\]", answer))
        retrieved_ids = {hit["chunk_id"] for hit in hits}
        if not citations or not citations.issubset(retrieved_ids):
            answer = (
                "I couldn't produce an answer with citations that match the retrieved "
                "evidence. Please inspect the source documents or rephrase the question."
            )
        result = {
            "answer": answer,
            "sources": [
                {
                    "document_name": hit["metadata"].get("document_name", "unknown"),
                    "chunk_id": hit["chunk_id"],
                    "score": hit["score"],
                    "similarity_score": hit["similarity_score"],
                    "snippet": hit["content"][:220],
                    "source_type": hit["metadata"].get("source_type", "text"),
                    "page_number": hit["metadata"].get("page_number"),
                    "image_index": hit["metadata"].get("image_index"),
                    "source_path": hit["metadata"].get("source_path"),
                    "line_start": hit["metadata"].get("line_start"),
                    "line_end": hit["metadata"].get("line_end"),
                    "repository": hit["metadata"].get("repository"),
                    "branch": hit["metadata"].get("branch"),
                    "path": hit["metadata"].get("path"),
                }
                for hit in hits
            ],
            "context": context,
        }
        if session_id:
            self.memory.append(session_id, {"question": question, "answer": answer})
        return result

    def list_documents(self):
        if hasattr(self.store, "list_documents"):
            return self.store.list_documents()
        return []

    def delete_document(self, document_name: str):
        if hasattr(self.store, "delete_document"):
            return self.store.delete_document(document_name)
        return False

    def clear_session(self, session_id: str):
        self.memory.clear(session_id)
