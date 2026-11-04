"""
src/recommendation/engine/recommendation_service.py
===================================================
Unified recommendation orchestrator connecting vector matching, hard eligibility,
multi-criteria ranking, and explainability.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import settings
from src.core.logging import logger
from src.recommendation.domain.student_profile import StudentProfile
from src.recommendation.embeddings import (
    TextEmbeddingEngine,
    compute_cosine_similarity,
    load_npy_array,
)
from src.recommendation.engine.eligibility import EligibilityFilter
from src.recommendation.engine.explainer import RecommendationExplainer
from src.recommendation.engine.matcher import SemanticMatcher
from src.recommendation.engine.ranker import HybridRanker
from src.recommendation.schemas.opportunity import Opportunity
from src.recommendation.schemas.recommendation import (
    RecommendationItem,
    RecommendationResponse,
    ScoreBreakdown,
)
from src.recommendation.vector_store import VectorStore


class RecommendationService:
    """Production service for personalized student opportunity recommendations."""

    def __init__(
        self,
        opportunities_json_path: Optional[Path] = None,
        embeddings_npy_path: Optional[Path] = None,
        reference_date: Optional[date] = None,
    ):
        self.json_path = opportunities_json_path or settings.OPPORTUNITIES_JSON_PATH
        self.npy_path = embeddings_npy_path or settings.OPPORTUNITY_EMBEDDINGS_PATH
        self.reference_date = reference_date or date.today()

        self.eligibility_filter = EligibilityFilter(reference_date=self.reference_date)
        self.semantic_matcher = SemanticMatcher()
        self.hybrid_ranker = HybridRanker(reference_date=self.reference_date)
        self.explainer = RecommendationExplainer()
        self.embedding_engine = TextEmbeddingEngine(settings.EMBEDDING_MODEL_NAME)

        self.opportunities: List[Opportunity] = []
        self.opportunity_map: Dict[str, Opportunity] = {}
        self.opportunity_vectors: Dict[str, List[float]] = {}
        self.vector_store = VectorStore(dimension=384)

        self._load_corpus()

    def _load_corpus(self) -> None:
        """Load opportunity catalog and precomputed embeddings."""
        if not self.json_path.exists():
            logger.warning("Opportunity JSON dataset not found at %s. Corpus is empty.", self.json_path)
            return

        with open(self.json_path, "r", encoding="utf-8") as f:
            raw_opps = json.load(f)

        self.opportunities = [Opportunity(**item) for item in raw_opps]
        self.opportunity_map = {opp.opportunity_id: opp for opp in self.opportunities}

        # Load embeddings if available
        if self.npy_path.exists():
            try:
                opp_ids = [opp.opportunity_id for opp in self.opportunities]
                vectors = load_npy_array(self.npy_path)
                if len(vectors) == len(opp_ids):
                    for opp_id, vec in zip(opp_ids, vectors):
                        self.opportunity_vectors[opp_id] = vec
                        self.vector_store.add(opp_id, vec)
                    logger.info("Loaded %d opportunity embeddings into VectorStore.", len(vectors))
                else:
                    logger.warning(
                        "Mismatch in vectors count (%d) vs opportunities count (%d). Generating on the fly.",
                        len(vectors), len(opp_ids)
                    )
            except Exception as e:
                logger.error("Error loading embeddings from %s: %s", self.npy_path, e)

        # Fallback: encode any missing opportunity vector on-the-fly
        for opp in self.opportunities:
            if opp.opportunity_id not in self.opportunity_vectors:
                comp_text = self.embedding_engine.compose_opportunity_text(opp.model_dump())
                vec = self.embedding_engine.encode(comp_text)
                self.opportunity_vectors[opp.opportunity_id] = vec
                self.vector_store.add(opp.opportunity_id, vec)

    def recommend(
        self,
        student: StudentProfile,
        top_k: int = 10,
        filter_type: Optional[str] = None,
    ) -> RecommendationResponse:
        """Generate top_k eligible, ranked recommendations with grounded explanations."""
        if not student.profile_vector or len(student.profile_vector) != 384:
            # Fallback compute profile vector if absent
            comp_text = f"Student in {student.department} Year {student.year_of_study} Skills: {', '.join(student.declared_skills)}"
            student.profile_vector = self.embedding_engine.encode(comp_text)

        eligible_items: List[Opportunity] = []
        for opp in self.opportunities:
            if filter_type and opp.opportunity_type.value != filter_type and opp.opportunity_type != filter_type:
                continue
            elig_res = self.eligibility_filter.evaluate(student, opp)
            if elig_res.is_eligible:
                eligible_items.append(opp)

        scored_candidates: List[Tuple[Opportunity, ScoreBreakdown, List[str], List[str]]] = []

        for opp in eligible_items:
            opp_vec = self.opportunity_vectors.get(opp.opportunity_id)
            if not opp_vec:
                comp_text = self.embedding_engine.compose_opportunity_text(opp.model_dump())
                opp_vec = self.embedding_engine.encode(comp_text)
                self.opportunity_vectors[opp.opportunity_id] = opp_vec

            semantic_sim = self.semantic_matcher.match(student.profile_vector, opp_vec)
            scores, matched_skills, missing_skills = self.hybrid_ranker.score_opportunity(
                student, opp, semantic_sim
            )
            scored_candidates.append((opp, scores, matched_skills, missing_skills))

        # Sort descending by composite_score, then skill_match_score, then semantic_similarity
        scored_candidates.sort(
            key=lambda x: (
                x[1].composite_score,
                x[1].skill_match_score,
                x[1].semantic_similarity,
                x[0].opportunity_id,
            ),
            reverse=True,
        )

        top_candidates = scored_candidates[:top_k]
        recommendation_items: List[RecommendationItem] = []

        for rank_idx, (opp, scores, matched, missing) in enumerate(top_candidates, start=1):
            explanation, closest_id, closest_title = self.explainer.explain(
                student, opp, scores, matched, missing
            )

            rec_item = RecommendationItem(
                rank=rank_idx,
                opportunity=opp,
                match_score=scores.composite_score,
                scores=scores,
                matched_skills=matched,
                missing_skills=missing,
                eligibility_status="ELIGIBLE",
                explanation=explanation,
                closest_achievement_id=closest_id,
                closest_achievement_title=closest_title,
            )
            recommendation_items.append(rec_item)

        return RecommendationResponse(
            student_id=student.student_id,
            generated_at=datetime.now(timezone.utc),
            total_recommendations=len(recommendation_items),
            algorithm_version="v1.2.0-hybrid",
            encoder_model=settings.EMBEDDING_MODEL_NAME,
            recommendations=recommendation_items,
        )
