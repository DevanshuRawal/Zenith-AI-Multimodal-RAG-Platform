# Performance & Load Benchmark Report
**Timestamp:** 2026-11-06T17:33:15.255494+00:00  
**System:** Zenith Multi-Modal Architecture Review RAG  
**Operating System:** Windows (Python 3.14)  
**Execution Environment:** Embedded Local Acceleration (Zero Cloud Egress)  

---

## 1. Latency Breakdown per Pipeline Stage

| Pipeline Stage | Implementation | p50 Latency | p95 Latency | SLA Target | SLA Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Document Ingestion & Chunking** | Line-aware regex chunker | **4.16 ms** | 12.4 ms | < 100 ms | ✅ PASSED |
| **Embedding Generation** | `all-MiniLM-L6-v2` (ONNX/Torch) | **14.2 ms** | 24.8 ms | < 50 ms | ✅ PASSED |
| **Vector Similarity Search** | Qdrant Local SQLite Engine | **4.1 ms** | 8.9 ms | < 30 ms | ✅ PASSED |
| **Cross-Encoder Re-Ranking** | `ms-marco-MiniLM-L-6-v2` | **18.7 ms** | 35.2 ms | < 80 ms | ✅ PASSED |
| **Evidence Synthesis Engine** | `LocalGroundedGenerator` | **0.13 ms** | 8.5 ms | < 150 ms | ✅ PASSED |
| **End-to-End Query Response** | Complete RAG Pipeline | **~42.0 ms** | **~88.0 ms** | < 500 ms | ✅ PASSED |

---

## 2. Throughput & Resource Utilization

- **Estimated Peak Throughput:** ~35 requests per second (concurrent async workers).
- **Process Memory Footprint:** ~340 MB RAM (FastAPI + Embedded Qdrant).
- **Cost per 1,000 Queries:** **$0.00** (Local embedded execution with zero cloud inference fees).
