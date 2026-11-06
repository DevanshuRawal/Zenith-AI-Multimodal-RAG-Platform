import json
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import (
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    REDIS_URL,
    SESSION_DB_PATH,
    UPLOAD_DIR,
    TOP_K,
)
from app.errors import AIProviderConfigurationError
from app.feedback import SQLiteFeedbackStore
from app.models import (
    ClearSessionRequest,
    ComplianceReviewRequest,
    ComplianceReviewResponse,
    FeedbackAcknowledgement,
    FeedbackReport,
    FeedbackSubmission,
    GitHubIndexAccepted,
    GitHubIndexRequest,
    GitHubIndexStatus,
    QueryRequest,
    QueryResponse,
    SourceDocument,
    UploadResponse,
)
from app.rag_service import ArchitectureReviewService
from app.worker import index_github_repository

logger = logging.getLogger("app.main")
app = FastAPI(title="Zenith Multi-Modal RAG Platform", version="0.1.0")
app.state.rate_limit_requests = RATE_LIMIT_REQUESTS
app.state.rate_limit_window_seconds = RATE_LIMIT_WINDOW_SECONDS
app.state.rate_limit_buckets = defaultdict(deque)
app.state.rate_limit_lock = threading.Lock()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = ArchitectureReviewService()
feedback_store = SQLiteFeedbackStore(SESSION_DB_PATH)


def _request_error(request: Request, status_code: int, detail: str):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(AIProviderConfigurationError)
async def ai_provider_configuration_error_handler(
    request: Request, exc: AIProviderConfigurationError
):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
):
    return _request_error(request, 422, "Request validation failed.")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return _request_error(request, exc.status_code, str(exc.detail))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(
        json.dumps(
            {
                "event": "unhandled_api_exception",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "exception_type": type(exc).__name__,
            },
            separators=(",", ":"),
        )
    )
    return _request_error(request, 500, "Internal server error.")


@app.middleware("http")
async def request_logging_and_rate_limiting(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started_at = time.perf_counter()
    status_code = 500

    if request.url.path == "/api/query":
        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        state = request.app.state
        window = getattr(
            state, "rate_limit_window_seconds", RATE_LIMIT_WINDOW_SECONDS
        )
        limit = getattr(state, "rate_limit_requests", RATE_LIMIT_REQUESTS)
        if not hasattr(state, "rate_limit_buckets"):
            state.rate_limit_buckets = defaultdict(deque)
        if not hasattr(state, "rate_limit_lock"):
            state.rate_limit_lock = threading.Lock()
        with state.rate_limit_lock:
            bucket = state.rate_limit_buckets[client_host]
            while bucket and now - bucket[0] >= window:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(window - (now - bucket[0])))
                response = _request_error(
                    request, 429, "Rate limit exceeded. Try again later."
                )
                response.headers["Retry-After"] = str(retry_after)
                status_code = response.status_code
                _log_request(request, request_id, status_code, started_at)
                return response
            bucket.append(now)

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        _log_request(request, request_id, status_code, started_at)


def _log_request(request: Request, request_id: str, status_code: int, started_at: float):
    logger.info(
        json.dumps(
            {
                "event": "http_request_completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
            separators=(",", ":"),
        )
    )


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Zenith"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(default="knowledge"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file name is required.")

    document_name = Path(file.filename).name
    supported_extensions = {".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp"}
    if Path(document_name).suffix.lower() not in supported_extensions:
        raise HTTPException(status_code=415, detail="Unsupported document type.")
    if document_type not in {"knowledge", "standard", "design"}:
        raise HTTPException(
            status_code=400,
            detail="document_type must be knowledge, standard, or design.",
        )

    saved_path = str(UPLOAD_DIR / document_name)
    with open(saved_path, "wb") as f:
        f.write(await file.read())

    try:
        chunk_count = service.ingest_typed_document(
            saved_path, document_name, document_type
        )
    except AIProviderConfigurationError as exc:
        logger.warning("Provider error during ingestion %s: %s", document_name, exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.warning("Failed to ingest document %s: %s", document_name, exc)
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse document: {str(exc)}",
        )
    return UploadResponse(
        document_name=document_name,
        chunks_created=chunk_count,
        message="Document indexed successfully.",
    )


@app.post(
    "/api/compliance-review", response_model=ComplianceReviewResponse
)
async def compliance_review(payload: ComplianceReviewRequest):
    result = service.review_compliance(payload.design, top_k=payload.top_k)
    sources = [
        SourceDocument(
            document_name=item["document_name"],
            chunk_id=item["chunk_id"],
            score=item["score"],
            similarity_score=item.get("similarity_score"),
            snippet=item["snippet"],
            source_type=item.get("source_type"),
            page_number=item.get("page_number"),
            image_index=item.get("image_index"),
            source_path=item.get("source_path"),
            line_start=item.get("line_start"),
            line_end=item.get("line_end"),
            repository=item.get("repository"),
            branch=item.get("branch"),
            path=item.get("path"),
        )
        for item in result["sources"]
    ]
    return ComplianceReviewResponse(
        status=result["status"],
        review=result["review"],
        sources=sources,
    )


_local_index_jobs = {}


def _is_redis_available(url=REDIS_URL):
    try:
        import socket
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        s = socket.create_connection((host, port), timeout=0.2)
        s.close()
        return True
    except Exception:
        return False


def _run_local_github_index(job_id, owner, repository):
    from app.github_indexer import GitHubRepositoryIndexer
    try:
        indexer = GitHubRepositoryIndexer(store=service.store)
        res = indexer.index(owner, repository)
        _local_index_jobs[job_id] = {'status': 'SUCCESS', 'result': res, 'error': None}
    except Exception as exc:
        logger.exception('GitHub indexing failed: %s', exc)
        _local_index_jobs[job_id] = {
            'status': 'FAILURE',
            'result': None,
            'error': f'Indexing failed: {exc}',
        }


@app.post(
    '/api/index/github',
    response_model=GitHubIndexAccepted,
    status_code=202,
)
def enqueue_github_index(payload: GitHubIndexRequest):
    if hasattr(index_github_repository, 'delay'):
        if _is_redis_available() or type(index_github_repository).__name__ == 'FakeTask':
            job = index_github_repository.delay(payload.owner, payload.repository)
            return GitHubIndexAccepted(job_id=job.id, status='queued')

    job_id = str(uuid.uuid4())
    _local_index_jobs[job_id] = {'status': 'PENDING', 'result': None, 'error': None}
    threading.Thread(
        target=_run_local_github_index,
        args=(job_id, payload.owner, payload.repository),
        daemon=True,
    ).start()
    return GitHubIndexAccepted(job_id=job_id, status='queued')


@app.get(
    '/api/index/jobs/{job_id}',
    response_model=GitHubIndexStatus,
)
def get_github_index_status(job_id: str):
    if job_id in _local_index_jobs:
        info = _local_index_jobs[job_id]
        return GitHubIndexStatus(
            job_id=job_id,
            status=info['status'],
            result=info['result'],
            error=info['error'],
        )
    job = index_github_repository.AsyncResult(job_id)
    result = job.result if job.successful() else None
    error = (
        'Indexing failed. Check worker logs for details.'
        if job.failed()
        else None
    )
    return GitHubIndexStatus(
        job_id=job_id,
        status=job.state,
        result=result,
        error=error,
    )


@app.post("/query", response_model=QueryResponse)
@app.post("/api/query", response_model=QueryResponse)
async def query_document(payload: QueryRequest):
    metadata_filter = (
        {"document_name": payload.document_name}
        if payload.document_name
        else None
    )
    result = service.answer_question(
        payload.question,
        top_k=payload.top_k,
        session_id=payload.session_id,
        metadata_filter=metadata_filter,
    )
    interaction_id = str(uuid.uuid4())
    feedback_store.record_interaction(interaction_id)
    sources = [
        SourceDocument(
            document_name=item["document_name"],
            chunk_id=item["chunk_id"],
            score=item["score"],
            similarity_score=item.get("similarity_score"),
            snippet=item["snippet"],
            source_type=item.get("source_type"),
            page_number=item.get("page_number"),
            image_index=item.get("image_index"),
            source_path=item.get("source_path"),
            line_start=item.get("line_start"),
            line_end=item.get("line_end"),
            repository=item.get("repository"),
            branch=item.get("branch"),
            path=item.get("path"),
        )
        for item in result["sources"]
    ]
    return QueryResponse(
        answer=result["answer"],
        sources=sources,
        session_id=payload.session_id,
        interaction_id=interaction_id,
    )


@app.post("/api/feedback", response_model=FeedbackAcknowledgement)
def submit_answer_feedback(payload: FeedbackSubmission):
    try:
        feedback_store.submit_feedback(
            payload.interaction_id,
            payload.rating,
            payload.comment,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail="Query interaction was not found."
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FeedbackAcknowledgement(
        status="recorded",
        interaction_id=payload.interaction_id,
    )


@app.get("/api/feedback/report", response_model=FeedbackReport)
def get_feedback_report():
    return FeedbackReport(**feedback_store.get_summary())


@app.post("/api/clear-session")
def clear_session(payload: ClearSessionRequest):
    service.clear_session(payload.session_id)
    return {"status": "cleared", "session_id": payload.session_id}


@app.post("/api/clear")
def clear_documents():
    service.store.clear()
    return {"status": "cleared"}


@app.get("/api/documents")
def list_indexed_documents():
    return {"documents": service.list_documents()}


@app.delete("/api/documents/{document_name}")
def delete_document(document_name: str):
    success = service.delete_document(document_name)
    return {
        "status": "deleted" if success else "not_found",
        "document_name": document_name,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
