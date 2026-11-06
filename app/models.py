from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class DocumentChunk(BaseModel):
    chunk_id: str
    document_name: str
    content: str
    metadata: dict = Field(default_factory=dict)
    score: float = 0.0


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    session_id: Optional[str] = None
    document_name: Optional[str] = None


class ClearSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class ComplianceReviewRequest(BaseModel):
    design: str = Field(..., min_length=1, max_length=20000)
    top_k: int = Field(default=5, ge=1, le=20)


class GitHubIndexRequest(BaseModel):
    owner: str = Field(..., min_length=1, max_length=39, pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
    repository: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )

    @field_validator("repository")
    @classmethod
    def reject_dot_segments(cls, value: str):
        if value in {".", ".."}:
            raise ValueError("Invalid GitHub repository name.")
        return value


class GitHubIndexAccepted(BaseModel):
    job_id: str
    status: str


class GitHubIndexStatus(BaseModel):
    job_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class SourceDocument(BaseModel):
    document_name: str
    chunk_id: str
    score: float
    similarity_score: Optional[float] = None
    snippet: str
    source_type: Optional[str] = None
    page_number: Optional[int] = None
    image_index: Optional[int] = None
    source_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    repository: Optional[str] = None
    branch: Optional[str] = None
    path: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument] = []
    session_id: Optional[str] = None
    interaction_id: Optional[str] = None


class FeedbackSubmission(BaseModel):
    interaction_id: str = Field(..., min_length=1, max_length=64)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class FeedbackAcknowledgement(BaseModel):
    status: Literal["recorded"]
    interaction_id: str


class FeedbackReport(BaseModel):
    total_feedback: int
    average_rating: Optional[float] = None
    ratings: dict[int, int] = Field(default_factory=dict)


class ComplianceReviewResponse(BaseModel):
    status: Literal[
        "COMPLIANT",
        "PARTIAL",
        "NON_COMPLIANT",
        "NOT_REVIEWED",
        "REVIEW_BLOCKED",
    ]
    review: str
    sources: List[SourceDocument] = Field(default_factory=list)


class UploadResponse(BaseModel):
    document_name: str
    chunks_created: int
    message: str
