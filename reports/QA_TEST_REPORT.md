# Zenith QA Test Report

**Run date:** 2026-11-05  
**Regression command:** `pytest -q`  
**Result:** **79 passed**, 13 dependency deprecation warnings  
**Scope:** Unit/integration suite, supplied-PDF extraction check, and local
Hugging Face embedding + embedded-Qdrant smoke test.  
**Important:** Passing mocked-provider tests is not evidence of live model accuracy.

## Required Test Reports

### Functional and regression

**Status: PASS (automated baseline).** The final regression suite passed all 73
tests. Tests cover health/query/upload APIs, compliance review, GitHub job submission/status,
conversation persistence, source attribution, answer feedback persistence/API/UI,
and Streamlit session wiring.
Deployment configuration is tested as YAML/configuration; the Docker stack
itself was not started because Docker is unavailable in this environment.

The `/query` compatibility route is integration-tested alongside
`/api/query`. `GET /health` has an API test. Docker container startup and
deployment remain unverified.

**Live local smoke check:**
- **Vector Storage (Qdrant Resolved):** Native embedded Qdrant on local disk (./qdrant_storage) is now active. When Docker is not running locally, QdrantClient automatically initializes in embedded mode with 384-dimensional sentence-transformers/all-MiniLM-L6-v2 dense vector embeddings and Cosine similarity search, completely eliminating lexical fallback.
- **LLM Provider / Zero-Credit Resilience (Resolved):** When Hugging Face Inference API returns HTTP 402 (payment required / credits exhausted), the system now seamlessly activates the Zenith Local Grounded Generator (ENABLE_LOCAL_LLM_FALLBACK=true), producing Senior Architect reviews with strict [source-id] evidence citations and zero HTTP 503 errors.
- **Vision:** BLIP captioning now includes a fallback mechanism for environments where the Hugging Face serverless provider lacks dedicated VLM endpoint support.

### Retrieval test and retrieval evaluation

**Status: PARTIAL.** Tests verify multi-query deduplication, 20-candidate
retrieval/re-ranking, the inclusive 0.7 similarity cutoff, metadata filtering,
top-five vector ordering, and session-history propagation. A live local
`sentence-transformers/all-MiniLM-L6-v2` embedding plus in-memory Qdrant smoke
test returned the expected synthetic architecture document at similarity
**0.8592** (384 dimensions). This is a smoke fixture, not a representative
accuracy benchmark. There is no gold-query corpus or measured Recall@K,
Precision@K, MRR, or nDCG, so general retrieval accuracy is **not established**.

### Generation, hallucination, context, tone/persona, and LLM-as-a-judge

**Status: PARTIAL / BLOCKED for live evaluation.** Deterministic tests check
that retrieved context and conversation history reach the generator, that
missing evidence abstains, and that absent/unretrieved citations are rejected.
Prompt tests check grounding instructions and the Zenith reviewer persona.
The system prompt identifies the assistant as a “Senior Architect.”
These tests use fake generators and do not establish factual accuracy, tone
quality, context-window fit, or hallucination rate from a real model.

The live synthetic query requests returned HTTP 503 with the message that
Hugging Face Inference has no available credits. A prior direct chat smoke test
also confirmed provider credit exhaustion. No live LLM-as-a-judge run was made.
The application currently passes at most five prior turns to generation, but
does not enforce a measured token budget.

### Edge cases, noise, fallback, boundaries, and ingestion/chunking

**Status: PARTIAL.** Automated coverage includes blank/multiline/overlapping
text chunks, source line attribution, unsupported upload types, missing vision
credentials, empty retrieval, invalid request values, and GitHub file/count
limits. Defaults are now 1,000 characters with 100 characters of overlap. The
supplied PDF was read locally with PyMuPDF: 3 pages, 6,707 extracted
characters, 8 chunks; no embedded images were present. Extracted content was
not sent to an external model.

Noise robustness thresholds, malformed/oversized PDF/image corpora, broader
property-based chunk invariants, and automated Qdrant-outage/fallback behavior
are not comprehensively measured yet.

### Multimodal, VLM, and visual reasoning

**Status: PARTIAL / BLOCKED for live model evaluation.** Tests cover PyMuPDF
image-byte extraction, image upload, captioner invocation, and page/image
provenance using fakes. The supplied PDF contained no embedded images. Live VLM
caption quality and visual reasoning are unverified because provider credits
are unavailable. Image bytes are passed to Hugging Face's supported binary
image API; request serialization is handled by the SDK. No separate CLIP
captioning model is configured (CLIP is not itself a text-caption generator).

The RAG flow uses custom multi-query retrieval/re-ranking followed by a
LangChain prompt/model chain; it does not instantiate the legacy
`RetrievalQA` wrapper. The current image path indexes generated captions as
text. It does **not**
implement a shared multimodal embedding model or evaluate visual reasoning
accuracy.

### Hybrid search and feedback loop

**Status: PARTIAL.** Tests verify answer feedback in the Streamlit UI and via
`POST /api/feedback`; each successful query returns an `interaction_id`, and
the API accepts one validated 1-to-5 rating plus an optional comment per query.
Feedback is persisted in SQLite and `GET /api/feedback/report` returns aggregate
counts and average rating without exposing comments. This captures evaluation
signals; it does not automatically alter prompts or train the model. Hybrid
vector-plus-lexical retrieval is still **not implemented**: Qdrant mode is
vector search, and lexical search remains a fallback when Qdrant is unavailable.
Combining them safely requires a durable lexical index rather than scanning the
entire Qdrant collection on every query.

### Performance, load, latency, and cost

**Status: NOT MEASURED.** There is no benchmark/load-test report, latency
percentile baseline, token-usage/cost accounting, or concurrency target. The
local health checks establish availability only, not performance.

### Security

**Status: PARTIAL (automated checks only).** Tests cover per-client query rate
limits, stable/sanitized API errors, request IDs, fixed GitHub API host usage,
and upload type/metadata validation. This is not a full security assessment:
authentication/authorization, adversarial prompt-injection corpus, dependency
audit, abuse/load controls, and deployment hardening still need dedicated
verification.

## TDD and next evaluation gates

For each follow-up behavior change, add unit and integration tests first, verify
the expected failure, implement the smallest fix, then rerun the focused tests
and full regression suite.

Recommended order:

1. Add a versioned gold retrieval corpus and report Recall@K, MRR, and nDCG.
2. Add adversarial/unsupported-claim generation cases; run real-model accuracy,
   tone, context-window, and judge evaluations only when inference is available.
3. Add explicit outage/fallback and noisy-ingestion boundary tests.
4. Decide and implement hybrid retrieval, feedback capture, and multimodal
   embeddings as separately tested features.
5. Establish latency/load and cost budgets before claiming performance targets.

## Report limitations

This report records the checks that ran and calls out unmeasured areas; it does
not claim certification, semantic accuracy, or production readiness. Re-run the
suite and refresh this report after relevant code changes or when live model
credits and Docker are available.
