"""
scripts/run_all_tests.py
========================
Master test runner executing all Unit, Contract, API, and End-to-End test suites.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import sys
import unittest

# Import all test suites
from tests.unit.test_config import *
from tests.unit.test_opportunity_schema import *
from tests.unit.test_embeddings import *
from tests.unit.test_profile_aggregator import *
from tests.unit.test_eligibility_filter import *
from tests.unit.test_recommendation_ranker import *
from tests.unit.test_explainer import *
from tests.unit.test_rec_metrics import *
from tests.unit.test_reports import *
from tests.contract.test_member1_adapter import *
from tests.contract.test_member2_predictor import *
from tests.e2e.test_full_system_flow import *


def run_tests():
    print("=" * 70)
    print("AI-POWERED STUDENT ACHIEVEMENT INTELLIGENCE PLATFORM — MEMBER 3")
    print("MASTER TEST SUITE EXECUTION")
    print("=" * 70)

    tests = [
        ("Config Defaults & Settings", test_config_defaults),
        ("Async Database URL Conversion", test_async_database_url_conversion),
        ("Opportunity Schema & Validation", test_valid_opportunity_creation),
        ("Invalid Domain Tag Rejection", test_invalid_domain_tag_rejected),
        ("Embedding Dimension & L2 Norm", test_embedding_dimension_and_norm),
        ("Cosine Similarity Bounds & Logic", test_cosine_similarity_symmetry_and_bounds),
        ("Recency Half-Life Decay Math", test_time_decay_math),
        ("Profile Cold-Start Aggregation", test_profile_cold_start_handling),
        ("Hard Eligibility GPA Pruning", test_hard_eligibility_gpa_pruning),
        ("Expired Opportunity Pruning", test_expired_opportunity_pruning),
        ("Hybrid Multi-Criteria Ranker", test_hybrid_score_bounding_and_components),
        ("Grounded XAI Justification", test_explainer_generates_grounded_justification),
        ("Precision & Recall at K", test_precision_recall_at_k),
        ("NDCG Accuracy Metric", test_ndcg_calculation),
        ("Catalog Coverage Metric", test_catalog_coverage),
        ("Official PDF Transcript Generation", test_pdf_transcript_starts_with_valid_pdf_magic),
        ("Member 1 NLP Normalization Contract", test_member1_adapter_normalization_and_skill_extraction),
        ("Member 1 Domain Tag Inference Contract", test_member1_adapter_domain_tag_inference),
        ("Member 2 Predictor Contract & Fallback", test_member2_fakepredictor_contract),
        ("Full Cross-Member E2E Lifecycle", test_full_system_lifecycle_e2e),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1

    print("=" * 70)
    print(f"TEST RESULTS: {passed} PASSED | {failed} FAILED (Total: {len(tests)})")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
