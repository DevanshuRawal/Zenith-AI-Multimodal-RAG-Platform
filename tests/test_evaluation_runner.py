import os
from pathlib import Path
from eval.evaluate_rag_pipeline import (
    run_retrieval_evaluation,
    run_generation_evaluation,
    run_edge_cases_evaluation,
    run_performance_evaluation,
    run_security_evaluation,
    run_master_qa_report,
)


def test_retrieval_evaluation_metrics_meet_sla():
    metrics = run_retrieval_evaluation()
    assert metrics["hit_at_5"] >= 0.95
    assert metrics["mrr_at_5"] >= 0.85
    assert metrics["map"] >= 0.80
    assert Path("reports/RETRIEVAL_EVALUATION_REPORT.md").exists()


def test_generation_evaluation_enforces_zero_hallucination():
    results = run_generation_evaluation()
    assert results["citation_precision"] == 100.0
    assert results["faithfulness"] >= 95.0
    assert Path("reports/GENERATION_HALLUCINATION_REPORT.md").exists()


def test_reports_are_generated_and_non_empty():
    run_edge_cases_evaluation()
    run_performance_evaluation()
    run_security_evaluation()
    run_master_qa_report()

    expected_reports = [
        "RETRIEVAL_EVALUATION_REPORT.md",
        "GENERATION_HALLUCINATION_REPORT.md",
        "EDGE_CASES_NOISE_REPORT.md",
        "PERFORMANCE_LOAD_REPORT.md",
        "SECURITY_REPORT.md",
        "COMPREHENSIVE_QA_REPORT.md",
    ]
    for filename in expected_reports:
        path = Path("reports") / filename
        assert path.exists()
        assert path.stat().st_size > 200

