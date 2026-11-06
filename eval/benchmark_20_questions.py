"""
Benchmark script: Executes 20 targeted architecture questions across indexed documents.
Analyzes:
1. Retrieval Quality (Were the correct chunks retrieved?)
2. Document Extraction Quality (Was chunk text properly extracted and uncorrupted?)
3. Generation & Synthesis Quality (Did the output answer the question specifically, or output generic boilerplate?)
Outputs full diagnostic report to reports/BENCHMARK_20_QUESTIONS_REPORT.md.
"""

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

BACKEND_URL = "http://127.0.0.1:8000"
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARK_QUESTIONS = [
    # --- ShopSphere Architecture Brief (06_architecture_brief.pdf) ---
    {
        "id": 1,
        "question": "What database does the Order Service use to store order data?",
        "target_doc": "06_architecture_brief.pdf",
        "expected_facts": ["PostgreSQL", "database"],
        "category": "Data Storage",
    },
    {
        "id": 2,
        "question": "How does the React client communicate with the backend services?",
        "target_doc": "06_architecture_brief.pdf",
        "expected_facts": ["API Gateway", "HTTPS"],
        "category": "Client-Server Communication",
    },
    {
        "id": 3,
        "question": "What message broker is used for publishing order events?",
        "target_doc": "06_architecture_brief.pdf",
        "expected_facts": ["RabbitMQ"],
        "category": "Message Brokering",
    },
    {
        "id": 4,
        "question": "Which event does the Inventory Service consume?",
        "target_doc": "06_architecture_brief.pdf",
        "expected_facts": ["order.created"],
        "category": "Event Consumption",
    },
    {
        "id": 5,
        "question": "What is the retry policy and backoff mechanism for failed messages?",
        "target_doc": "06_architecture_brief.pdf",
        "expected_facts": ["three times", "exponential backoff"],
        "category": "Resilience & Retries",
    },
    {
        "id": 6,
        "question": "Where are failed messages moved after retries are exhausted?",
        "target_doc": "06_architecture_brief.pdf",
        "expected_facts": ["dead-letter queue"],
        "category": "Dead Letter Handling",
    },
    {
        "id": 7,
        "question": "What is the proposed monthly availability target for ShopSphere?",
        "target_doc": "06_architecture_brief.pdf",
        "expected_facts": ["99.9%", "monthly availability"],
        "category": "SLA & Availability",
    },
    {
        "id": 8,
        "question": "Is the 99.9% availability a measured production result or a target?",
        "target_doc": "06_architecture_brief.pdf",
        "expected_facts": ["target", "not a measured production result"],
        "category": "SLA Nuance & Precision",
    },
    {
        "id": 9,
        "question": "What framework and language is the Order Service built with?",
        "target_doc": "06_architecture_brief.pdf",
        "expected_facts": ["Python", "FastAPI"],
        "category": "Technology Stack",
    },
    {
        "id": 10,
        "question": "Who is the owner and what is the Document ID of the ShopSphere architecture brief?",
        "target_doc": "06_architecture_brief.pdf",
        "expected_facts": ["SS-KB-001", "Platform Engineering"],
        "category": "Metadata & Provenance",
    },

    # --- Zenith Platform Overview (ZENITH_PROJECT_OVERVIEW.md) ---
    {
        "id": 11,
        "question": "What embedding model does Zenith use for generating vector embeddings?",
        "target_doc": "ZENITH_PROJECT_OVERVIEW.md",
        "expected_facts": ["Sentence Transformers"],
        "category": "Embeddings & Vectors",
    },
    {
        "id": 12,
        "question": "What vector database is used by Zenith and what is the fallback if unavailable?",
        "target_doc": "ZENITH_PROJECT_OVERVIEW.md",
        "expected_facts": ["Qdrant", "lexical fallback"],
        "category": "Vector DB & Fallback",
    },
    {
        "id": 13,
        "question": "What is the default chunk size and chunk overlap used by Zenith for text splitting?",
        "target_doc": "ZENITH_PROJECT_OVERVIEW.md",
        "expected_facts": ["1,000", "100"],
        "category": "Chunking Strategy",
    },
    {
        "id": 14,
        "question": "How does Zenith handle architectural diagrams found in PDFs?",
        "target_doc": "ZENITH_PROJECT_OVERVIEW.md",
        "expected_facts": ["captions", "diagram"],
        "category": "Multi-Modal Reasoning",
    },
    {
        "id": 15,
        "question": "What cross-encoder model or technique is used for re-ranking retrieval candidates?",
        "target_doc": "ZENITH_PROJECT_OVERVIEW.md",
        "expected_facts": ["rerank", "candidates"],
        "category": "Re-Ranking & Precision",
    },
    {
        "id": 16,
        "question": "How many retrieval candidates are collected before re-ranking?",
        "target_doc": "ZENITH_PROJECT_OVERVIEW.md",
        "expected_facts": ["20"],
        "category": "Candidate Retrieval",
    },
    {
        "id": 17,
        "question": "What similarity threshold filter is applied to retrieval candidates?",
        "target_doc": "ZENITH_PROJECT_OVERVIEW.md",
        "expected_facts": ["0.7"],
        "category": "Similarity Filtering",
    },
    {
        "id": 18,
        "question": "What HTTP status code does the live query endpoint return when provider credits are unavailable?",
        "target_doc": "ZENITH_PROJECT_OVERVIEW.md",
        "expected_facts": ["503", "credits"],
        "category": "API Status & Provider Verification",
    },
    {
        "id": 19,
        "question": "Where is conversation memory stored across browser sessions?",
        "target_doc": "ZENITH_PROJECT_OVERVIEW.md",
        "expected_facts": ["SQLite"],
        "category": "Session Persistence",
    },
    {
        "id": 20,
        "question": "What technologies are used for background asynchronous GitHub repository indexing?",
        "target_doc": "ZENITH_PROJECT_OVERVIEW.md",
        "expected_facts": ["Celery", "Redis"],
        "category": "Background Task Queue",
    },
]


def run_benchmark():
    print(f"Starting 20-Question RAG Investigation Benchmark against {BACKEND_URL}...")
    results = []

    for item in BENCHMARK_QUESTIONS:
        qid = item["id"]
        qtext = item["question"]
        doc = item["target_doc"]
        expected = item["expected_facts"]
        cat = item["category"]

        print(f"\n[{qid}/20] Testing: '{qtext}' (Target: {doc})")

        payload = {
            "question": qtext,
            "top_k": 5,
            "document_name": doc,
        }

        t0 = time.perf_counter()
        try:
            resp = requests.post(f"{BACKEND_URL}/api/query", json=payload, timeout=30)
            latency_ms = (time.perf_counter() - t0) * 1000
            if resp.status_code != 200:
                print(f"  ❌ Error HTTP {resp.status_code}: {resp.text}")
                results.append({
                    **item,
                    "status": "HTTP_ERROR",
                    "latency_ms": latency_ms,
                    "retrieved_chunks": [],
                    "answer": resp.text,
                    "retrieval_ok": False,
                    "extraction_ok": False,
                    "generation_ok": False,
                    "diagnosis": f"HTTP {resp.status_code} Error",
                })
                continue

            data = resp.json()
            answer = data.get("answer", "")
            sources = data.get("sources", [])

            # 1. Retrieval Diagnosis: Did we retrieve chunks from the target doc?
            retrieved_cids = [s["chunk_id"] for s in sources]
            target_chunks = [s for s in sources if doc in s.get("document_name", "")]
            retrieval_ok = len(target_chunks) > 0

            # 2. Document Extraction Diagnosis: Did the retrieved chunk text actually contain the expected facts?
            combined_context = data.get("context") or " ".join(s.get("snippet", "") for s in target_chunks)
            facts_in_context = [f for f in expected if f.lower() in combined_context.lower()]
            extraction_ok = len(facts_in_context) >= 1

            # 3. Generation Diagnosis: Did the final generated answer contain the specific expected facts?
            facts_in_answer = [f for f in expected if f.lower() in answer.lower()]
            generation_ok = len(facts_in_answer) >= 1

            # Determine root cause failure stage if generation failed
            if generation_ok:
                diagnosis = "✅ PASSED: Accurate Question-Specific Answer"
            elif not retrieval_ok:
                diagnosis = "❌ RETRIEVAL FAILURE: Relevant document chunk was not retrieved"
            elif not extraction_ok:
                diagnosis = "⚠️ EXTRACTION FAILURE: Target chunks retrieved but missing expected facts"
            else:
                diagnosis = "⚠️ SYNTHESIS / LLM FAILURE: Facts present in context, but answer failed to synthesize specific response"

            print(f"  Retrieved Chunks: {retrieved_cids[:3]}")
            print(f"  Facts in Context: {facts_in_context} / {expected}")
            print(f"  Facts in Answer:  {facts_in_answer} / {expected}")
            print(f"  Diagnosis:        {diagnosis}")

            results.append({
                **item,
                "status": "SUCCESS",
                "latency_ms": latency_ms,
                "retrieved_chunks": retrieved_cids,
                "retrieved_snippets": [s.get("snippet", "")[:120] for s in target_chunks[:2]],
                "answer": answer,
                "facts_in_context": facts_in_context,
                "facts_in_answer": facts_in_answer,
                "retrieval_ok": retrieval_ok,
                "extraction_ok": extraction_ok,
                "generation_ok": generation_ok,
                "diagnosis": diagnosis,
            })

        except Exception as exc:
            print(f"  ❌ Exception: {exc}")
            results.append({
                **item,
                "status": "EXCEPTION",
                "latency_ms": 0,
                "retrieved_chunks": [],
                "answer": str(exc),
                "retrieval_ok": False,
                "extraction_ok": False,
                "generation_ok": False,
                "diagnosis": f"Exception: {exc}",
            })

    # Generate Markdown Report
    generate_markdown_report(results)
    return results


def generate_markdown_report(results):
    total = len(results)
    passed = sum(1 for r in results if r["generation_ok"])
    retrieval_success = sum(1 for r in results if r["retrieval_ok"])
    extraction_success = sum(1 for r in results if r["extraction_ok"])
    synthesis_failures = sum(
        1 for r in results
        if r["retrieval_ok"] and r["extraction_ok"] and not r["generation_ok"]
    )

    pass_rate = (passed / total) * 100
    retrieval_rate = (retrieval_success / total) * 100
    extraction_rate = (extraction_success / total) * 100

    report_lines = [
        "# 20-Question RAG Pipeline Investigation Report",
        f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}  ",
        f"**Target System:** Zenith Multi-Modal Architecture Review Assistant  ",
        f"**Benchmark Scope:** 20 Diverse Technical Questions (10 on `06_architecture_brief.pdf`, 10 on `ZENITH_PROJECT_OVERVIEW.md`)  ",
        "",
        "---",
        "",
        "## 1. Executive Diagnostic Summary",
        "",
        "| Pipeline Stage | Success Count | Success Rate | Evaluation Status |",
        "| :--- | :--- | :--- | :--- |",
        f"| **Stage 1: RAG Retrieval** | {retrieval_success} / {total} | **{retrieval_rate:.1f}%** | {'✅ HEALTHY' if retrieval_rate >= 90 else '⚠️ INVESTIGATE'} |",
        f"| **Stage 2: Document Extraction** | {extraction_success} / {total} | **{extraction_rate:.1f}%** | {'✅ HEALTHY' if extraction_rate >= 90 else '⚠️ INVESTIGATE'} |",
        f"| **Stage 3: Question-Specific Synthesis** | {passed} / {total} | **{pass_rate:.1f}%** | {'✅ HEALTHY' if pass_rate >= 80 else '⚠️ BOTTLENECK IDENTIFIED'} |",
        "",
        f"> **Key Finding:** Synthesis / LLM Response Generation bottleneck identified in **{synthesis_failures}** cases where context was successfully retrieved and extracted, but the generated answer did not extract the direct answer to the question.",
        "",
        "---",
        "",
        "## 2. Detailed Per-Question Investigation Matrix",
        "",
    ]

    for r in results:
        report_lines.extend([
            f"### Question {r['id']}: {r['question']}",
            f"* **Category:** `{r['category']}` | **Target Document:** `{r['target_doc']}`",
            f"* **Diagnosis:** **{r['diagnosis']}**",
            f"* **Expected Facts:** `{r['expected_facts']}`",
            f"* **Retrieved Chunks:** `{r['retrieved_chunks']}`",
            f"* **Facts Found in Context:** `{r.get('facts_in_context', [])}`",
            f"* **Facts Found in Generated Answer:** `{r.get('facts_in_answer', [])}`",
            "",
            "**Generated Review Output:**",
            "```markdown",
            r["answer"].strip(),
            "```",
            "",
            "---",
            "",
        ])

    report_path = REPORTS_DIR / "BENCHMARK_20_QUESTIONS_REPORT.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nBenchmark completed! Report saved to {report_path}")


if __name__ == "__main__":
    run_benchmark()
