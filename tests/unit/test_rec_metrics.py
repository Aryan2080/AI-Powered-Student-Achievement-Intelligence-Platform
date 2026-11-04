"""Unit tests for offline recommendation evaluation metrics."""
import pytest
from src.recommendation.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    average_precision_at_k,
    ndcg_at_k,
    catalog_coverage,
)


def test_precision_recall_at_k():
    recs = ["OPP-1", "OPP-2", "OPP-3", "OPP-4", "OPP-5"]
    gt = {"OPP-1", "OPP-3", "OPP-7"}

    p5 = precision_at_k(recs, gt, k=5)
    r5 = recall_at_k(recs, gt, k=5)

    assert p5 == 2.0 / 5.0
    assert r5 == 2.0 / 3.0


def test_ndcg_calculation():
    recs = ["OPP-1", "OPP-2", "OPP-3"]
    # Perfect ranking
    rels_perfect = {"OPP-1": 1.0, "OPP-2": 1.0, "OPP-3": 0.0}
    ndcg_perfect = ndcg_at_k(recs, rels_perfect, k=3)
    assert ndcg_perfect == pytest.approx(1.0, rel=1e-3)


def test_catalog_coverage():
    all_recs = {"OPP-1", "OPP-2", "OPP-3"}
    catalog = {"OPP-1", "OPP-2", "OPP-3", "OPP-4", "OPP-5", "OPP-6"}
    cov = catalog_coverage(all_recs, catalog)
    assert cov == pytest.approx(0.50, rel=1e-3)
