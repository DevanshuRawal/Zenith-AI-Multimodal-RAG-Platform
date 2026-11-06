# Zenith Project Overview

## Purpose

Zenith is a multimodal Retrieval-Augmented Generation (RAG) platform for
technical architecture reviews. It indexes project documents, retrieves
relevant evidence, and uses an LLM to draft answers grounded in that evidence.

## Main capabilities

- Upload PDF, TXT, Markdown, PNG, JPG/JPEG, and WEBP files for indexing.
- Extract PDF text and images with PyMuPDF; split text into 1,000-character
  chunks with 100-character overlap by default.
- Generate image captions for diagrams and preserve page/image provenance.
- Create semantic embeddings with Sentence Transformers and store/search vectors
  in Qdrant. If Qdrant is unavailable, the application uses a local lexical
  fallback; this is not combined hybrid vector-plus-keyword ranking.
- Expand queries, collect up to 20 candidates, filter on similarity at or above
  0.7, rerank candidates, and return up to five sources by default.
- Generate evidence-grounded answers with a Hugging Face model through
  LangChain. The app abstains when it cannot find suitable evidence and
  validates citations against retrieved sources.
- Review a proposed design against separately indexed standards.
- Index supported files from GitHub repositories with a Celery worker and Redis.
- Keep conversation history in SQLite and provide a Streamlit web interface.

## Technology

Python, FastAPI, LangChain, Hugging Face Inference API, Sentence Transformers,
Qdrant, PyMuPDF, Streamlit, SQLite, Celery, Redis, and Docker Compose.

## Running locally

1. Install dependencies with `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and configure `HUGGINGFACEHUB_API_TOKEN`.
3. Start Qdrant for vector search; without it the app uses lexical fallback.
4. Start the API with `uvicorn app.main:app --host 127.0.0.1 --port 8000`.
5. Start the UI with `streamlit run streamlit_app.py`.
6. Open the UI at `http://localhost:8501` or API documentation at
   `http://localhost:8000/docs`.

Never put API tokens, passwords, or other secrets in documents uploaded to the
knowledge base.

## API endpoints

- `GET /health` — API health check.
- `POST /api/upload` — upload a supported file; optional `document_type` is
  `knowledge`, `standard`, or `design`.
- `POST /api/query` and `POST /query` — ask a question against indexed content.
- `POST /api/compliance-review` — compare a design with indexed standards.
- `POST /api/index/github` — enqueue a GitHub repository for indexing.
- `GET /api/index/jobs/{job_id}` — check repository indexing progress.
- `POST /api/clear-session` and `POST /api/clear` — clear conversation memory.

## Known limitations and current verification

- Live LLM and vision-model quality cannot be confirmed without available
  Hugging Face inference credits. The live query endpoint returns an explicit
  HTTP 503 when provider credits are unavailable.
- Qdrant was unavailable during the latest local API smoke test, so that
  instance used lexical fallback.
- Docker deployment, external Qdrant connectivity, representative retrieval
  accuracy, load/performance, and live visual reasoning are not yet verified.
- The project has automated unit/integration coverage; the latest full test run
  passed 73 tests. Passing tests do not certify production readiness or live
  model accuracy.
- The application uses custom retrieval and reranking followed by a LangChain
  prompt/model chain; it does not instantiate the legacy `RetrievalQA` wrapper.
- Shared multimodal embeddings, combined hybrid search, and a feedback-driven
  evaluation loop are not currently implemented.
