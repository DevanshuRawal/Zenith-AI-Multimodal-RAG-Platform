# Zenith Multi-Modal RAG Platform - API Documentation & Swagger Reference

This document provides the complete API reference for the **Zenith Multi-Modal RAG Platform**.  
Interactive Swagger UI is exported at [`docs/index.html`](./index.html) and [`openapi.json`](./openapi.json).

---

## 1. Architecture & Gateway Specifications

* **Base URL (Local):** `http://127.0.0.1:8000`
* **Swagger UI (Live Server):** `http://127.0.0.1:8000/docs`
* **ReDoc (Live Server):** `http://127.0.0.1:8000/redoc`
* **OpenAPI Schema (JSON):** [`openapi.json`](./openapi.json)
* **Rate Limiting:** Enforces 30 requests per 60 seconds per IP on query endpoints. Returns `HTTP 429 Too Many Requests` with `Retry-After` header when exceeded.
* **Request Tracing:** All responses include a unique `X-Request-ID` header.

---

## 2. Endpoints Catalog

### `GET /health`
Verify API service health and operational status.
* **Method:** `GET`
* **Response (200 OK):**
```json
{
  "status": "ok",
  "service": "Zenith"
}
```

---

### `POST /api/upload`
Upload and index technical architecture documents, PDFs, Markdown specifications, or visual system diagrams.
* **Method:** `POST`
* **Content-Type:** `multipart/form-data`
* **Parameters:**
  * `file`: Binary file stream (Supported: `.pdf`, `.txt`, `.md`, `.png`, `.jpg`, `.jpeg`, `.webp`).
  * `document_type`: `knowledge`, `standard`, or `design` (Default: `knowledge`).
* **Response (200 OK):**
```json
{
  "document_name": "Zenith_Standards.pdf",
  "chunks_created": 14,
  "message": "Document indexed successfully."
}
```

---

### `POST /api/query` (or `POST /query`)
Submit an architectural inquiry against indexed technical documents and codebase repositories.
* **Method:** `POST`
* **Content-Type:** `application/json`
* **Request Body:**
```json
{
  "question": "How should we design the service boundaries for this architecture?",
  "top_k": 5,
  "session_id": "optional-uuid-for-conversational-memory",
  "document_name": "optional-filter-to-specific-document.pdf"
}
```
* **Response (200 OK):**
```json
{
  "answer": "As Senior Architect, here is the evidence-grounded review:\n\n### Executive Summary\nBased on verified technical documentation [Zenith_Standards.pdf::0]...",
  "sources": [
    {
      "document_name": "Zenith_Standards.pdf",
      "chunk_id": "Zenith_Standards.pdf::0",
      "score": 0.942,
      "similarity_score": 0.812,
      "snippet": "ZENITH: Multi-Modal RAG Platform for Technical Architecture Reviews...",
      "source_type": "original_text",
      "line_start": 1,
      "line_end": 28
    }
  ],
  "session_id": "user-session-uuid",
  "interaction_id": "feedback-interaction-uuid"
}
```

---

### `GET /api/documents`
List all currently indexed documents in the Qdrant vector store along with chunk counts.
* **Method:** `GET`
* **Response (200 OK):**
```json
{
  "documents": [
    {
      "document_name": "Zenith_Standards.pdf",
      "document_type": "standard",
      "chunks": 14
    },
    {
      "document_name": "ZENITH_PROJECT_OVERVIEW.md",
      "document_type": "knowledge",
      "chunks": 4
    }
  ]
}
```

---

### `DELETE /api/documents/{document_name}`
Delete all indexed vector chunks belonging to a specific document without wiping the entire vector store.
* **Method:** `DELETE`
* **Response (200 OK):**
```json
{
  "status": "deleted",
  "document_name": "Zenith_Standards.pdf"
}
```

---

### `POST /api/clear`
Reset and clear all indexed documents from the Qdrant vector store.
* **Method:** `POST`
* **Response (200 OK):**
```json
{
  "status": "cleared"
}
```

---

### `POST /api/clear-session`
Clear multi-turn conversational memory for a given browser session.
* **Method:** `POST`
* **Request Body:**
```json
{
  "session_id": "session-uuid"
}
```
* **Response (200 OK):**
```json
{
  "status": "cleared",
  "session_id": "session-uuid"
}
```

---

### `POST /api/compliance-review`
Evaluate a proposed system design strictly against internal architectural standards.
* **Method:** `POST`
* **Request Body:**
```json
{
  "design": "The service stores customer data and exposes a gRPC interface.",
  "top_k": 5
}
```
* **Response (200 OK):**
```json
{
  "status": "COMPLIANT",
  "review": "Status: COMPLIANT\nFinding: Design adheres to interface boundary policies [standards.pdf::0].",
  "sources": []
}
```

---

### `POST /api/index/github`
Enqueue background asynchronous crawling and embedding of a GitHub repository via Celery & Redis.
* **Method:** `POST`
* **Request Body:**
```json
{
  "owner": "DevanshuRawal",
  "repository": "Zenith-AI-Multimodal-RAG-Platform"
}
```
* **Response (202 Accepted):**
```json
{
  "job_id": "3b29013e-f14d-44ce-b930-b328148b5949",
  "status": "queued"
}
```

---

### `GET /api/index/jobs/{job_id}`
Check the indexing progress of a queued GitHub indexing job.
* **Method:** `GET`
* **Response (200 OK):**
```json
{
  "job_id": "3b29013e-f14d-44ce-b930-b328148b5949",
  "status": "SUCCESS",
  "result": {
    "files_indexed": 42,
    "chunks_created": 128
  },
  "error": null
}
```

---

### `POST /api/feedback`
Submit end-user ratings (1 to 5 stars) and comments on generated architecture reviews.
* **Method:** `POST`
* **Request Body:**
```json
{
  "interaction_id": "feedback-interaction-uuid",
  "rating": 5,
  "comment": "Accurate service boundary recommendations and strict citations."
}
```
* **Response (200 OK):**
```json
{
  "status": "recorded",
  "interaction_id": "feedback-interaction-uuid"
}
```

---

### `GET /api/feedback/report`
Retrieve aggregate quality metrics, average rating score, and rating distribution.
* **Method:** `GET`
* **Response (200 OK):**
```json
{
  "total_interactions": 24,
  "average_rating": 4.85,
  "rating_counts": {
    "5": 20,
    "4": 4
  }
}
```
