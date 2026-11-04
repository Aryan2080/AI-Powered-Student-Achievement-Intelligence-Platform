"""
src/recommendation/evaluation/metrics.py
========================================
Offline recommendation evaluation metrics: Precision@K, Recall@K, MAP@K, NDCG@K,
Intra-List Diversity, and Catalog Coverage.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Set, Tuple


def precision_at_k(recommended: List[str], ground_truth: Set[str], k: int = 5) -> float:
    """Calculate Precision@K: fraction of top-k recommended items that are relevant."""
    if k <= 0 or not recommended:
        return 0.0
    top_k = recommended[:k]
    hits = sum(1 for item in top_k if item in ground_truth)
    return round(hits / k, 4)


def recall_at_k(recommended: List[str], ground_truth: Set[str], k: int = 5) -> float:
    """Calculate Recall@K: fraction of relevant items captured in top-k recommendations."""
    if not ground_truth or k <= 0 or not recommended:
        return 0.0
    top_k = recommended[:k]
    hits = sum(1 for item in top_k if item in ground_truth)
    return round(hits / len(ground_truth), 4)


def average_precision_at_k(recommended: List[str], ground_truth: Set[str], k: int = 5) -> float:
    """Calculate Average Precision@K (AP@K) for a single query."""
    if not ground_truth or k <= 0 or not recommended:
        return 0.0

    score = 0.0
    hits = 0
    top_k = recommended[:k]

    for i, item in enumerate(top_k, start=1):
        if item in ground_truth:
            hits += 1
            score += hits / i

    num_relevant = min(len(ground_truth), k)
    return round(score / num_relevant, 4) if num_relevant > 0 else 0.0


def mean_average_precision_at_k(
    recommendations: List[List[str]], ground_truths: List[Set[str]], k: int = 5
) -> float:
    """Calculate Mean Average Precision@K (MAP@K) across multiple students."""
    if not recommendations or len(recommendations) != len(ground_truths):
        return 0.0
    aps = [
        average_precision_at_k(rec, gt, k)
        for rec, gt in zip(recommendations, ground_truths)
    ]
    return round(sum(aps) / len(aps), 4)


def dcg_at_k(recommended: List[str], relevance_scores: Dict[str, float], k: int = 5) -> float:
    """Calculate Discounted Cumulative Gain at K (DCG@K)."""
    dcg = 0.0
    for i, item in enumerate(recommended[:k], start=1):
        rel = relevance_scores.get(item, 0.0)
        dcg += (2.0 ** rel - 1.0) / math.log2(i + 1.0)
    return dcg


def ndcg_at_k(
    recommended: List[str], relevance_scores: Dict[str, float], k: int = 5
) -> float:
    """Calculate Normalized Discounted Cumulative Gain at K (NDCG@K)."""
    actual_dcg = dcg_at_k(recommended, relevance_scores, k)
    
    # Ideal DCG (IDCG)
    sorted_rels = sorted(relevance_scores.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(sorted_rels, start=1):
        idcg += (2.0 ** rel - 1.0) / math.log2(i + 1.0)

    if idcg <= 0.0:
        return 0.0
    return round(actual_dcg / idcg, 4)


def intra_list_diversity(vectors: List[List[float]]) -> float:
    """Calculate Intra-List Diversity (ILD) using average pairwise cosine distance."""
    n = len(vectors)
    if n < 2:
        return 0.0

    total_distance = 0.0
    pair_count = 0

    for i in range(n):
        for j in range(i + 1, n):
            dot = sum(a * b for a, b in zip(vectors[i], vectors[j]))
            dist = 1.0 - max(0.0, min(1.0, (dot + 1.0) / 2.0))
            total_distance += dist
            pair_count += 1

    return round(total_distance / pair_count, 4) if pair_count > 0 else 0.0


def catalog_coverage(all_recommended_ids: Set[str], total_catalog_ids: Set[str]) -> float:
    """Calculate Catalog Coverage: percentage of available catalog items recommended."""
    if not total_catalog_ids:
        return 0.0
    coverage = len(all_recommended_ids & total_catalog_ids) / len(total_catalog_ids)
    return round(coverage, 4)


def evaluate_ranking_suite(
    student_recommendations: List[List[str]],
    ground_truth_relevance: List[Dict[str, float]],
    catalog_ids: Set[str],
    k: int = 5,
) -> Dict[str, float]:
    """Execute complete standard offline evaluation benchmark."""
    p_k_list = []
    r_k_list = []
    ap_k_list = []
    ndcg_k_list = []
    recommended_set: Set[str] = set()

    for recs, rels in zip(student_recommendations, ground_truth_relevance):
        gt_set = set(k for k, v in rels.items() if v >= 1.0)
        p_k_list.append(precision_at_k(recs, gt_set, k))
        r_k_list.append(recall_at_k(recs, gt_set, k))
        ap_k_list.append(average_precision_at_k(recs, gt_set, k))
        ndcg_k_list.append(ndcg_at_k(recs, rels, k))
        recommended_set.update(recs[:k])

    coverage = catalog_coverage(recommended_set, catalog_ids)

    return {
        f"Precision@{k}": round(sum(p_k_list) / len(p_k_list), 4),
        f"Recall@{k}": round(sum(r_k_list) / len(r_k_list), 4),
        f"MAP@{k}": round(sum(ap_k_list) / len(ap_k_list), 4),
        f"NDCG@{k}": round(sum(ndcg_k_list) / len(ndcg_k_list), 4),
        "Catalog_Coverage": coverage,
    }
