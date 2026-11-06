# Zenith: Multi-Modal RAG Platform for Technical Architecture Reviews

A starter for a multi-modal RAG application that ingests technical PDFs and text documents, retrieves relevant context, and uses a LangChain Hugging Face model to generate architecture reviews grounded in source evidence.

## What this project provides

- FastAPI backend for upload and query endpoints
- Qdrant vector storage with a local lexical fallback when Qdrant is unavailable
- PyMuPDF PDF/text ingestion with 1,000-character chunks and 100-character overlap
- Vision-model captions for embedded PDF diagrams and uploaded image files
- Sentence-transformer embeddings and semantic retrieval when Qdrant is available
- LLM-generated multi-query retrieval with duplicate removal
- Similarity filtering at 0.7 followed by cross-encoder re-ranking of up to
  20 candidates
- Automated design compliance checks against separately indexed internal standards
- SQLite-backed conversation memory for follow-up questions across restarts
- Evidence-only LangChain/Hugging Face answer generation with verified source IDs
- Background GitHub repository indexing through Celery and Redis
- Streamlit frontend for a browser-based demo
- Docker Compose deployment for the API, worker, Redis, Streamlit UI, and Qdrant
- Request IDs, structured API logs, stable error responses, and query rate limiting

## Stack

- Python 3.10+
- FastAPI
- LangChain
- Hugging Face Inference API
- Qdrant
- Sentence Transformers
- Streamlit
- PyMuPDF
- Docker + Qdrant

## Docker quick start

1. Copy the environment template and add your Hugging Face token to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
   Keep the token only in `.env`; `.env` is ignored by Git and excluded from the
   Docker build context.

2. Build and launch the full stack:
   ```bash
   docker compose up --build
   ```

3. Open the UI at `http://localhost:8501` and the API docs at
   `http://localhost:8000/docs`. Docker Compose waits for Qdrant and API
   healthchecks before starting dependent services. The GitHub indexing worker
   and Redis queue also start as part of the stack.

Data and downloaded model files are stored in named Docker volumes. Set
`API_PORT`, `UI_PORT`, or `QDRANT_PORT` in `.env` to change published ports.
Stop the stack with `docker compose down`; add `-v` only if you intend to delete
all persisted database, document, session, and model-cache data.
The query endpoint rate limit defaults to 30 requests per client IP per 60
seconds; configure it with `RATE_LIMIT_REQUESTS` and
`RATE_LIMIT_WINDOW_SECONDS`. This limiter is process-local, so put a shared
gateway or distributed limiter in front of multiple API replicas.

API responses include an `X-Request-ID` header. Errors return a stable JSON
shape with that ID, while structured logs record method, path, status, duration,
and request ID without logging request bodies or exception messages.

## Local development

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the model and vector database:
   ```powershell
   Copy-Item .env.example .env
   ```
   Add a Hugging Face access token to `.env` as `HUGGINGFACEHUB_API_TOKEN`.
   The default chat model is `meta-llama/Llama-3.1-8B-Instruct`; Hugging Face
   Inference Providers may also require available credits and model access for
   the provider selected by your account. Provider errors are reported directly
   by the API instead of appearing as an unhandled server error.
   Start Qdrant with `docker compose up -d qdrant`. For this Qdrant-only local
   workflow, use `QDRANT_URL=http://localhost:6333` in `.env`.

4. Start the backend:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Start the frontend:
   ```bash
   streamlit run streamlit_app.py
   ```

6. Upload a PDF, `.txt`/`.md` document, or a PNG/JPEG/WebP diagram and ask a
   technical architecture question. PDF text and embedded images are indexed
   with page/image provenance; image captions are retrievable RAG evidence.
   PyMuPDF extracts page text and image bytes; the Hugging Face SDK handles
   binary request serialization. Text is tagged `original_text`, while generated
   diagram captions are tagged `image_caption`.
   Text is split into 1,000-character chunks with 100 characters of overlap by
   default.    Retrieval fetches up to 20 candidates, re-ranks them, and keeps only
   candidates whose vector/lexical similarity score is at least 0.7.
   `TOP_K` controls how many final sources are returned (default 5).
   Text and GitHub code citations include their source path and original line
   range when available.
   The answer is generated only when retrieval finds context and the model
   returns citations matching retrieved chunk IDs. Query is available at
   `POST /api/query` and the compatibility alias `POST /query`. The Streamlit UI keeps a
   conversation session for follow-up context and offers a control to clear its
   memory. API clients can set `session_id` and use `POST /api/clear-session`.
   Query responses include an `interaction_id`; the Streamlit UI can submit a
   1-to-5 rating and optional comment for that answer. Feedback is stored in
   SQLite at `SESSION_DB_PATH`, accepts one rating per interaction, and is
   summarized by `GET /api/feedback/report`. The report contains aggregate
   ratings only; avoid entering secrets or personal data in feedback comments.
   Query expansion and answer generation use the configured Hugging Face model;
   retrieved candidates are re-ranked with the configured cross-encoder.
   To run compliance checks, upload policy files with `document_type=standard`,
   then send the proposed design to `POST /api/compliance-review`. The endpoint
   searches only standard-tagged chunks and reports `NOT_REVIEWED` if no
   standards are indexed.
   To index a repository, submit `owner` and `repository` to
   `POST /api/index/github`; poll `GET /api/index/jobs/{job_id}` for progress.
   The worker indexes up to `GITHUB_MAX_FILES` supported text files, skips
   excluded/generated directories and files larger than
   `GITHUB_MAX_FILE_BYTES`, and stores repository/path/branch provenance.
   Public repositories need no GitHub token. Set `GITHUB_API_TOKEN` in `.env`
   for private repository access or higher GitHub API limits.

## API endpoints

- `GET /health`
- `POST /api/upload`
- `POST /api/query`
- `POST /api/feedback`
- `GET /api/feedback/report`
- `POST /api/compliance-review`
- `POST /api/index/github`
- `GET /api/index/jobs/{job_id}`
- `POST /api/clear-session`
- `POST /api/clear`

Example query payload:

```json
{
  "question": "How should we structure service boundaries for a platform with a PDF knowledge base?",
  "top_k": 5
}
```

Compliance request:

```json
{
  "design": "The service stores customer records in a database.",
  "top_k": 5
}
```

Queue GitHub indexing:

```json
{
  "owner": "example-org",
  "repository": "example-repo"
}
```

The enqueue endpoint returns `202 Accepted` with a `job_id`; poll the job
endpoint until it reports `SUCCESS` or `FAILURE`.

Submit answer feedback using the `interaction_id` returned by a query:

```json
{
  "interaction_id": "returned-interaction-id",
  "rating": 5,
  "comment": "The cited explanation was helpful."
}
```

The report endpoint returns only the total, average rating, and rating counts.
Feedback is collected for evaluation; it does not automatically train or
change the language model.

## Architecture overview

```text
Upload PDF/text/diagram -> text + image extraction -> vision captions -> vector store -> multi-query retrieval + re-ranking -> cited architecture review
```

## Roadmap

This project follows the same 10-week plan shown in the mockup:

1. Document ingestion and chunking
2. Vector storage setup
3. Embedding and similarity search
4. Multi-modal PDF/image processing and diagram captions (implemented)
5. LangChain RAG pipeline (implemented)
6. Multi-query retrieval and re-ranking (implemented)
7. Conversation memory (SQLite persistence implemented)
8. Streamlit UI (document, diagram, compliance, GitHub indexing, and answer-feedback flows)
9. Error handling and monitoring (request IDs, structured logs, stable errors, and API rate limiting implemented)
10. Deployment and optimization (Docker Compose API/worker/UI/Qdrant/Redis baseline implemented)

## Notes

Automated tests include local embedded-Qdrant and API integration coverage with fake GitHub/model providers; they do not call live GitHub or Hugging Face services. Repository indexing runs in Celery via Redis, and `GET /api/index/jobs/{job_id}` returns terminal status. Conversation turns are persisted in SQLite at `SESSION_DB_PATH` (default: `sessions.sqlite3`). Run tests with `pytest -q`. Live GitHub indexing needs network access and a token for private repos. Live multi-query expansion, answer generation, and image captioning require a valid Hugging Face token and network access. The cross-encoder model is loaded on first use and requires model download access on the first run.
