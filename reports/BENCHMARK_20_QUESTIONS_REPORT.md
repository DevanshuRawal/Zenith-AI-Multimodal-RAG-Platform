# 20-Question RAG Pipeline Investigation Report
**Timestamp:** 2026-11-06T18:33:49.535656+00:00  
**Target System:** Zenith Multi-Modal Architecture Review Assistant  
**Benchmark Scope:** 20 Diverse Technical Questions (10 on `06_architecture_brief.pdf`, 10 on `ZENITH_PROJECT_OVERVIEW.md`)  

---

## 1. Executive Diagnostic Summary

| Pipeline Stage | Success Count | Success Rate | Evaluation Status |
| :--- | :--- | :--- | :--- |
| **Stage 1: RAG Retrieval** | 20 / 20 | **100.0%** | ✅ HEALTHY |
| **Stage 2: Document Extraction** | 5 / 20 | **25.0%** | ⚠️ INVESTIGATE |
| **Stage 3: Question-Specific Synthesis** | 20 / 20 | **100.0%** | ✅ HEALTHY |

> **Key Finding:** Synthesis / LLM Response Generation bottleneck identified in **0** cases where context was successfully retrieved and extracted, but the generated answer did not extract the direct answer to the question.

---

## 2. Detailed Per-Question Investigation Matrix

### Question 1: What database does the Order Service use to store order data?
* **Category:** `Data Storage` | **Target Document:** `06_architecture_brief.pdf`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['PostgreSQL', 'database']`
* **Retrieved Chunks:** `['06_architecture_brief.pdf::0', '06_architecture_brief.pdf::1', '06_architecture_brief.pdf::2']`
* **Facts Found in Context:** `['PostgreSQL', 'database']`
* **Facts Found in Generated Answer:** `['PostgreSQL']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [06_architecture_brief.pdf::0], The Order Service stores order data in PostgreSQL and publishes events to RabbitMQ.

### Evidence & Architectural Findings
• **Component Specification:** The gateway routes requests to the Order Service (Python FastAPI). [06_architecture_brief.pdf::0]
• **Component Specification:** Order Service: validates requests and manages order state. [06_architecture_brief.pdf::0]
• **Component Specification:** Order Service validates the cart and writes an order with status PENDING. [06_architecture_brief.pdf::1]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [06_architecture_brief.pdf::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [06_architecture_brief.pdf::0].
```

---

### Question 2: How does the React client communicate with the backend services?
* **Category:** `Client-Server Communication` | **Target Document:** `06_architecture_brief.pdf`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['API Gateway', 'HTTPS']`
* **Retrieved Chunks:** `['06_architecture_brief.pdf::0', '06_architecture_brief.pdf::1', '06_architecture_brief.pdf::2']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['API Gateway', 'HTTPS']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [06_architecture_brief.pdf::0], The React web client calls the API Gateway over HTTPS.

### Evidence & Architectural Findings
• **Component Specification:** API Gateway: authentication enforcement, routing, request throttling. [06_architecture_brief.pdf::0]
• **Component Specification:** Client sends POST /v1/orders with an idempotency key. [06_architecture_brief.pdf::1]
• **Component Specification:** Payment Adapter: communicates. [06_architecture_brief.pdf::0]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [06_architecture_brief.pdf::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [06_architecture_brief.pdf::0].
```

---

### Question 3: What message broker is used for publishing order events?
* **Category:** `Message Brokering` | **Target Document:** `06_architecture_brief.pdf`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['RabbitMQ']`
* **Retrieved Chunks:** `['06_architecture_brief.pdf::0', '06_architecture_brief.pdf::1', '06_architecture_brief.pdf::2']`
* **Facts Found in Context:** `['RabbitMQ']`
* **Facts Found in Generated Answer:** `['RabbitMQ']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [06_architecture_brief.pdf::0], The Order Service stores order data in PostgreSQL and publishes events to RabbitMQ.

### Evidence & Architectural Findings
• **Component Specification:** The service publishes order.created to RabbitMQ using a transactional outbox. [06_architecture_brief.pdf::1]
• **Component Specification:** The transactional outbox prevents a database. [06_architecture_brief.pdf::1]
• **Component Specification:** The transactional outbox prevents a database commit from succeeding while its event is silently lost. [06_architecture_brief.pdf::2]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [06_architecture_brief.pdf::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [06_architecture_brief.pdf::0].
```

---

### Question 4: Which event does the Inventory Service consume?
* **Category:** `Event Consumption` | **Target Document:** `06_architecture_brief.pdf`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['order.created']`
* **Retrieved Chunks:** `['06_architecture_brief.pdf::0', '06_architecture_brief.pdf::1', '06_architecture_brief.pdf::2']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['order.created']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [06_architecture_brief.pdf::0], The Inventory Service consumes order.created events and reserves stock.

### Evidence & Architectural Findings
• **Component Specification:** Inventory Service: reserves and releases stock. [06_architecture_brief.pdf::0]
• **Component Specification:** Inventory Service attempts reservation and emits inventory.reserved or inventory.rejected. [06_architecture_brief.pdf::1]
• **Component Specification:** The service publishes order.created to RabbitMQ using a transactional outbox. [06_architecture_brief.pdf::1]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [06_architecture_brief.pdf::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [06_architecture_brief.pdf::0].
```

---

### Question 5: What is the retry policy and backoff mechanism for failed messages?
* **Category:** `Resilience & Retries` | **Target Document:** `06_architecture_brief.pdf`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['three times', 'exponential backoff']`
* **Retrieved Chunks:** `['06_architecture_brief.pdf::2', '06_architecture_brief.pdf::0', '06_architecture_brief.pdf::1']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['three times', 'exponential backoff']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [06_architecture_brief.pdf::2], Failed messages are retried three times with exponential backoff, then moved to a dead-letter queue.

### Evidence & Architectural Findings
• **Component Specification:** Failed messages are retried three times with exponential backoff, then moved to a dead-letter queue. [06_architecture_brief.pdf::2]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [06_architecture_brief.pdf::2].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [06_architecture_brief.pdf::2].
```

---

### Question 6: Where are failed messages moved after retries are exhausted?
* **Category:** `Dead Letter Handling` | **Target Document:** `06_architecture_brief.pdf`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['dead-letter queue']`
* **Retrieved Chunks:** `['06_architecture_brief.pdf::2', '06_architecture_brief.pdf::1', '06_architecture_brief.pdf::0']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['dead-letter queue']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [06_architecture_brief.pdf::2], Failed messages are retried three times with exponential backoff, then moved to a dead-letter queue.

### Evidence & Architectural Findings
• **Component Specification:** Payment Adapter requests authorization after inventory is reserved. [06_architecture_brief.pdf::1]
• **Component Specification:** Order becomes CONFIRMED after successful authorization; otherwise it becomes CANCELLED and inventory is released. [06_architecture_brief.pdf::1]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [06_architecture_brief.pdf::2].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [06_architecture_brief.pdf::2].
```

---

### Question 7: What is the proposed monthly availability target for ShopSphere?
* **Category:** `SLA & Availability` | **Target Document:** `06_architecture_brief.pdf`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['99.9%', 'monthly availability']`
* **Retrieved Chunks:** `['06_architecture_brief.pdf::2', '06_architecture_brief.pdf::0', '06_architecture_brief.pdf::1']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['99.9%', 'monthly availability']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [06_architecture_brief.pdf::2], The proposed service objective is 99.9% monthly availability.

### Evidence & Architectural Findings
• **Component Specification:** This is a target, not a measured production result. [06_architecture_brief.pdf::2]
• **Component Specification:** ShopSphere Architecture Brief ShopSphere Order Management Platform Document ID: SS-KB-001 | Version: 1.2 | Owner: Platform Engineering Purpose ShopSphere is a fictional online retail platform. [06_architecture_brief.pdf::0]
• **Component Specification:** Redis stores short-lived idempotency keys and product availability cache entries. [06_architecture_brief.pdf::0]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [06_architecture_brief.pdf::2].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [06_architecture_brief.pdf::2].
```

---

### Question 8: Is the 99.9% availability a measured production result or a target?
* **Category:** `SLA Nuance & Precision` | **Target Document:** `06_architecture_brief.pdf`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['target', 'not a measured production result']`
* **Retrieved Chunks:** `['06_architecture_brief.pdf::2', '06_architecture_brief.pdf::0', '06_architecture_brief.pdf::1']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['target', 'not a measured production result']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [06_architecture_brief.pdf::2], the 99.9% availability is an architectural target and not a measured production result (This is a target, not a measured production result).

### Evidence & Architectural Findings
• **Component Specification:** The proposed service objective is 99.9% monthly availability. [06_architecture_brief.pdf::2]
• **Component Specification:** Redis stores short-lived idempotency keys and product availability cache entries. [06_architecture_brief.pdf::0]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [06_architecture_brief.pdf::2].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [06_architecture_brief.pdf::2].
```

---

### Question 9: What framework and language is the Order Service built with?
* **Category:** `Technology Stack` | **Target Document:** `06_architecture_brief.pdf`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['Python', 'FastAPI']`
* **Retrieved Chunks:** `['06_architecture_brief.pdf::0', '06_architecture_brief.pdf::1', '06_architecture_brief.pdf::2']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['Python', 'FastAPI']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [06_architecture_brief.pdf::0], The gateway routes requests to the Order Service (Python FastAPI).

### Evidence & Architectural Findings
• **Component Specification:** The Order Service stores order data in PostgreSQL and publishes events to RabbitMQ. [06_architecture_brief.pdf::0]
• **Component Specification:** Order Service: validates requests and manages order state. [06_architecture_brief.pdf::0]
• **Component Specification:** Order Service validates the cart and writes an order with status PENDING. [06_architecture_brief.pdf::1]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [06_architecture_brief.pdf::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [06_architecture_brief.pdf::0].
```

---

### Question 10: Who is the owner and what is the Document ID of the ShopSphere architecture brief?
* **Category:** `Metadata & Provenance` | **Target Document:** `06_architecture_brief.pdf`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['SS-KB-001', 'Platform Engineering']`
* **Retrieved Chunks:** `['06_architecture_brief.pdf::0', '06_architecture_brief.pdf::1', '06_architecture_brief.pdf::2']`
* **Facts Found in Context:** `['SS-KB-001', 'Platform Engineering']`
* **Facts Found in Generated Answer:** `['SS-KB-001', 'Platform Engineering']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [06_architecture_brief.pdf::0], ShopSphere Architecture Brief ShopSphere Order Management Platform Document ID: SS-KB-001 | Version: 1.2 | Owner: Platform Engineering Purpose ShopSphere is a fictional online retail platform.

### Evidence & Architectural Findings
• **Component Specification:** The React web client calls the API Gateway over HTTPS. [06_architecture_brief.pdf::0]
• **Component Specification:** The Payment Adapter calls an external payment provider. [06_architecture_brief.pdf::0]
• **Component Specification:** Redis stores short-lived idempotency keys and product availability cache entries. [06_architecture_brief.pdf::0]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [06_architecture_brief.pdf::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [06_architecture_brief.pdf::0].
```

---

### Question 11: What embedding model does Zenith use for generating vector embeddings?
* **Category:** `Embeddings & Vectors` | **Target Document:** `ZENITH_PROJECT_OVERVIEW.md`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['Sentence Transformers']`
* **Retrieved Chunks:** `['ZENITH_PROJECT_OVERVIEW.md::0', 'ZENITH_PROJECT_OVERVIEW.md::3', 'ZENITH_PROJECT_OVERVIEW.md::1', 'ZENITH_PROJECT_OVERVIEW.md::2']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['Sentence Transformers']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [ZENITH_PROJECT_OVERVIEW.md::0], Create semantic embeddings with Sentence Transformers and store/search vectors in Qdrant.

### Evidence & Architectural Findings
• **Component Specification:** If Qdrant is unavailable, the application uses a local lexical fallback; this is not combined hybrid vector-plus-keyword ranking. [ZENITH_PROJECT_OVERVIEW.md::0]
• **Component Specification:** Start Qdrant for vector search; without it the app uses lexical fallback. [ZENITH_PROJECT_OVERVIEW.md::1]
• **Component Specification:** Qdrant was unavailable during the latest local API smoke test, so that instance used lexical fallback. [ZENITH_PROJECT_OVERVIEW.md::3]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [ZENITH_PROJECT_OVERVIEW.md::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [ZENITH_PROJECT_OVERVIEW.md::0].
```

---

### Question 12: What vector database is used by Zenith and what is the fallback if unavailable?
* **Category:** `Vector DB & Fallback` | **Target Document:** `ZENITH_PROJECT_OVERVIEW.md`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['Qdrant', 'lexical fallback']`
* **Retrieved Chunks:** `['ZENITH_PROJECT_OVERVIEW.md::0', 'ZENITH_PROJECT_OVERVIEW.md::3', 'ZENITH_PROJECT_OVERVIEW.md::1', 'ZENITH_PROJECT_OVERVIEW.md::2']`
* **Facts Found in Context:** `['Qdrant']`
* **Facts Found in Generated Answer:** `['Qdrant', 'lexical fallback']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [ZENITH_PROJECT_OVERVIEW.md::0], If Qdrant is unavailable, the application uses a local lexical fallback; this is not combined hybrid vector-plus-keyword ranking.

### Evidence & Architectural Findings
• **Component Specification:** Qdrant was unavailable during the latest local API smoke test, so that instance used lexical fallback. [ZENITH_PROJECT_OVERVIEW.md::3]
• **Component Specification:** Start Qdrant for vector search; without it the app uses lexical fallback. [ZENITH_PROJECT_OVERVIEW.md::1]
• **Component Specification:** Create semantic embeddings with Sentence Transformers and store/search vectors in Qdrant. [ZENITH_PROJECT_OVERVIEW.md::0]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [ZENITH_PROJECT_OVERVIEW.md::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [ZENITH_PROJECT_OVERVIEW.md::0].
```

---

### Question 13: What is the default chunk size and chunk overlap used by Zenith for text splitting?
* **Category:** `Chunking Strategy` | **Target Document:** `ZENITH_PROJECT_OVERVIEW.md`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['1,000', '100']`
* **Retrieved Chunks:** `['ZENITH_PROJECT_OVERVIEW.md::0', 'ZENITH_PROJECT_OVERVIEW.md::1', 'ZENITH_PROJECT_OVERVIEW.md::3', 'ZENITH_PROJECT_OVERVIEW.md::2']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['1,000', '100']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [ZENITH_PROJECT_OVERVIEW.md::0], Extract PDF text and images with PyMuPDF; split text into 1,000-character chunks with 100-character overlap by default.

### Evidence & Architectural Findings
• **Component Specification:** Zenith Project Overview. [ZENITH_PROJECT_OVERVIEW.md::0]
• **Component Specification:** Purpose Zenith is a multimodal Retrieval-Augmented Generation (RAG) platform for technical architecture reviews. [ZENITH_PROJECT_OVERVIEW.md::0]
• **Component Specification:** Expand queries, collect up to 20 candidates, filter on similarity at or above 0.7, rerank candidates, and return up to five sources by default. [ZENITH_PROJECT_OVERVIEW.md::0]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [ZENITH_PROJECT_OVERVIEW.md::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [ZENITH_PROJECT_OVERVIEW.md::0].
```

---

### Question 14: How does Zenith handle architectural diagrams found in PDFs?
* **Category:** `Multi-Modal Reasoning` | **Target Document:** `ZENITH_PROJECT_OVERVIEW.md`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['captions', 'diagram']`
* **Retrieved Chunks:** `['ZENITH_PROJECT_OVERVIEW.md::0', 'ZENITH_PROJECT_OVERVIEW.md::1', 'ZENITH_PROJECT_OVERVIEW.md::2', 'ZENITH_PROJECT_OVERVIEW.md::3']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['captions', 'diagram']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [ZENITH_PROJECT_OVERVIEW.md::0], Generate image captions for diagrams and preserve page/image provenance.

### Evidence & Architectural Findings
• **Component Specification:** Zenith Project Overview. [ZENITH_PROJECT_OVERVIEW.md::0]
• **Component Specification:** Purpose Zenith is a multimodal Retrieval-Augmented Generation (RAG) platform for technical architecture reviews. [ZENITH_PROJECT_OVERVIEW.md::0]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [ZENITH_PROJECT_OVERVIEW.md::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [ZENITH_PROJECT_OVERVIEW.md::0].
```

---

### Question 15: What cross-encoder model or technique is used for re-ranking retrieval candidates?
* **Category:** `Re-Ranking & Precision` | **Target Document:** `ZENITH_PROJECT_OVERVIEW.md`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['rerank', 'candidates']`
* **Retrieved Chunks:** `['ZENITH_PROJECT_OVERVIEW.md::0', 'ZENITH_PROJECT_OVERVIEW.md::3', 'ZENITH_PROJECT_OVERVIEW.md::1', 'ZENITH_PROJECT_OVERVIEW.md::2']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['rerank', 'candidates']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [ZENITH_PROJECT_OVERVIEW.md::3], The application uses custom retrieval and reranking followed by a LangChain prompt/model chain; it does not instantiate the legacy `RetrievalQA` wrapper.

### Evidence & Architectural Findings
• **Component Specification:** Expand queries, collect up to 20 candidates, filter on similarity at or above 0.7, rerank candidates, and return up to five sources by default. [ZENITH_PROJECT_OVERVIEW.md::0]
• **Component Specification:** Purpose Zenith is a multimodal Retrieval-Augmented Generation (RAG) platform for technical architecture reviews. [ZENITH_PROJECT_OVERVIEW.md::0]
• **Component Specification:** Generate evidence-grounded answers with a Hugging Face model through LangChain. [ZENITH_PROJECT_OVERVIEW.md::0]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [ZENITH_PROJECT_OVERVIEW.md::3].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [ZENITH_PROJECT_OVERVIEW.md::3].
```

---

### Question 16: How many retrieval candidates are collected before re-ranking?
* **Category:** `Candidate Retrieval` | **Target Document:** `ZENITH_PROJECT_OVERVIEW.md`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['20']`
* **Retrieved Chunks:** `['ZENITH_PROJECT_OVERVIEW.md::0', 'ZENITH_PROJECT_OVERVIEW.md::3', 'ZENITH_PROJECT_OVERVIEW.md::1', 'ZENITH_PROJECT_OVERVIEW.md::2']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['20']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [ZENITH_PROJECT_OVERVIEW.md::0], Expand queries, collect up to 20 candidates, filter on similarity at or above 0.7, rerank candidates, and return up to five sources by default.

### Evidence & Architectural Findings
• **Component Specification:** The application uses custom retrieval and reranking followed by a LangChain prompt/model chain; it does not instantiate the legacy `RetrievalQA` wrapper. [ZENITH_PROJECT_OVERVIEW.md::3]
• **Component Specification:** Purpose Zenith is a multimodal Retrieval-Augmented Generation (RAG) platform for technical architecture reviews. [ZENITH_PROJECT_OVERVIEW.md::0]
• **Component Specification:** Docker deployment, external Qdrant connectivity, representative retrieval accuracy, load/performance, and live visual reasoning are not yet verified. [ZENITH_PROJECT_OVERVIEW.md::3]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [ZENITH_PROJECT_OVERVIEW.md::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [ZENITH_PROJECT_OVERVIEW.md::0].
```

---

### Question 17: What similarity threshold filter is applied to retrieval candidates?
* **Category:** `Similarity Filtering` | **Target Document:** `ZENITH_PROJECT_OVERVIEW.md`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['0.7']`
* **Retrieved Chunks:** `['ZENITH_PROJECT_OVERVIEW.md::0', 'ZENITH_PROJECT_OVERVIEW.md::3', 'ZENITH_PROJECT_OVERVIEW.md::1', 'ZENITH_PROJECT_OVERVIEW.md::2']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['0.7']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [ZENITH_PROJECT_OVERVIEW.md::0], Expand queries, collect up to 20 candidates, filter on similarity at or above 0.7, rerank candidates, and return up to five sources by default.

### Evidence & Architectural Findings
• **Component Specification:** The application uses custom retrieval and reranking followed by a LangChain prompt/model chain; it does not instantiate the legacy `RetrievalQA` wrapper. [ZENITH_PROJECT_OVERVIEW.md::3]
• **Component Specification:** Purpose Zenith is a multimodal Retrieval-Augmented Generation (RAG) platform for technical architecture reviews. [ZENITH_PROJECT_OVERVIEW.md::0]
• **Component Specification:** Docker deployment, external Qdrant connectivity, representative retrieval accuracy, load/performance, and live visual reasoning are not yet verified. [ZENITH_PROJECT_OVERVIEW.md::3]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [ZENITH_PROJECT_OVERVIEW.md::0].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [ZENITH_PROJECT_OVERVIEW.md::0].
```

---

### Question 18: What HTTP status code does the live query endpoint return when provider credits are unavailable?
* **Category:** `API Status & Provider Verification` | **Target Document:** `ZENITH_PROJECT_OVERVIEW.md`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['503', 'credits']`
* **Retrieved Chunks:** `['ZENITH_PROJECT_OVERVIEW.md::3', 'ZENITH_PROJECT_OVERVIEW.md::2', 'ZENITH_PROJECT_OVERVIEW.md::1']`
* **Facts Found in Context:** `['503', 'credits']`
* **Facts Found in Generated Answer:** `['503', 'credits']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [ZENITH_PROJECT_OVERVIEW.md::3], The live query endpoint returns an explicit HTTP 503 when provider credits are unavailable.

### Evidence & Architectural Findings
• **Component Specification:** The live query endpoint returns an explicit HTTP 503 w. [ZENITH_PROJECT_OVERVIEW.md::2]
• **Component Specification:** Live LLM and vision-model quality cannot be confirmed without available Hugging Face inference credits. [ZENITH_PROJECT_OVERVIEW.md::2]
• **Component Specification:** out available Hugging Face inference credits. [ZENITH_PROJECT_OVERVIEW.md::3]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [ZENITH_PROJECT_OVERVIEW.md::3].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [ZENITH_PROJECT_OVERVIEW.md::3].
```

---

### Question 19: Where is conversation memory stored across browser sessions?
* **Category:** `Session Persistence` | **Target Document:** `ZENITH_PROJECT_OVERVIEW.md`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['SQLite']`
* **Retrieved Chunks:** `['ZENITH_PROJECT_OVERVIEW.md::2', 'ZENITH_PROJECT_OVERVIEW.md::1', 'ZENITH_PROJECT_OVERVIEW.md::0', 'ZENITH_PROJECT_OVERVIEW.md::3']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['SQLite']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [ZENITH_PROJECT_OVERVIEW.md::1], Keep conversation history in SQLite and provide a Streamlit web interface.

### Evidence & Architectural Findings
• **Component Specification:** `POST /api/clear-session` and `POST /api/clear` — clear conversation memory. [ZENITH_PROJECT_OVERVIEW.md::2]
• **Component Specification:** Technology Python, FastAPI, LangChain, Hugging Face Inference API, Sentence Transformers, Qdrant, PyMuPDF, Streamlit, SQLite, Celery, Redis, and Docker Compose. [ZENITH_PROJECT_OVERVIEW.md::1]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [ZENITH_PROJECT_OVERVIEW.md::1].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [ZENITH_PROJECT_OVERVIEW.md::1].
```

---

### Question 20: What technologies are used for background asynchronous GitHub repository indexing?
* **Category:** `Background Task Queue` | **Target Document:** `ZENITH_PROJECT_OVERVIEW.md`
* **Diagnosis:** **✅ PASSED: Accurate Question-Specific Answer**
* **Expected Facts:** `['Celery', 'Redis']`
* **Retrieved Chunks:** `['ZENITH_PROJECT_OVERVIEW.md::1', 'ZENITH_PROJECT_OVERVIEW.md::0', 'ZENITH_PROJECT_OVERVIEW.md::2', 'ZENITH_PROJECT_OVERVIEW.md::3']`
* **Facts Found in Context:** `[]`
* **Facts Found in Generated Answer:** `['Celery', 'Redis']`

**Generated Review Output:**
```markdown
As Senior Architect, here is the evidence-grounded architecture review:

### Executive Assessment
Based on the verified architecture documentation [ZENITH_PROJECT_OVERVIEW.md::2], `POST /api/index/github` — enqueue a GitHub repository for indexing.

### Evidence & Architectural Findings
• **Component Specification:** `GET /api/index/jobs/{job_id}` — check repository indexing progress. [ZENITH_PROJECT_OVERVIEW.md::2]
• **Component Specification:** Index supported files from GitHub repositories with a Celery worker and Redis. [ZENITH_PROJECT_OVERVIEW.md::1]
• **Component Specification:** Technology Python, FastAPI, LangChain, Hugging Face Inference API, Sentence Transformers, Qdrant, PyMuPDF, Streamlit, SQLite, Celery, Redis, and Docker Compose. [ZENITH_PROJECT_OVERVIEW.md::1]

### Architectural Recommendations
• Ensure system boundaries are strictly isolated between ingestion and query layers [ZENITH_PROJECT_OVERVIEW.md::2].
• Apply cross-encoder re-ranking to prioritize high-relevance architectural context [ZENITH_PROJECT_OVERVIEW.md::2].
```

---
