"""
scripts/evaluate_recommendations.py
===================================
Python offline evaluation benchmark script for recommendation ranking.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import json
from pathlib import Path
from src.core.config import settings
from src.recommendation.engine.recommendation_service import RecommendationService
from src.recommendation.evaluation.metrics import evaluate_ranking_suite
from src.recommendation.domain.student_profile import StudentProfile


def main():
    service = RecommendationService()
    profiles_path = settings.BENCHMARK_PROFILES_PATH

    print(f"Loading benchmark profiles from {profiles_path}...")
    with open(profiles_path, "r", encoding="utf-8") as f:
        raw_profiles = json.load(f)

    profiles = [StudentProfile(**p) for p in raw_profiles]
    catalog_ids = set(opp.opportunity_id for opp in service.opportunities)

    recommendations_list = []
    ground_truth_list = []

    print(f"Evaluating {len(profiles)} student profiles...")
    for prof in profiles:
        res = service.recommend(prof, top_k=10)
        rec_ids = [item.opportunity.opportunity_id for item in res.recommendations]
        recommendations_list.append(rec_ids)

        # Build ground truth relevance: 1.0 if skill match >= 0.5 or domain affinity >= 0.6
        rels = {}
        for opp in service.opportunities:
            score, _, _ = service.hybrid_ranker.skill_ranker.calculate_skill_overlap(prof, opp)
            dom_score = service.hybrid_ranker.skill_ranker.calculate_domain_score(prof, opp)
            if score >= 0.5 or dom_score >= 0.6:
                rels[opp.opportunity_id] = 1.0
        ground_truth_list.append(rels)

    metrics = evaluate_ranking_suite(recommendations_list, ground_truth_list, catalog_ids, k=5)
    print("\nBenchmark Evaluation Results (K=5):")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
