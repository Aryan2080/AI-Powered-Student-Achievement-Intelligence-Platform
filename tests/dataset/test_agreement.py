"""Tests for inter-annotator agreement."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from nlp_semantic.schema import (
    Annotation,
    AnnotationStatus,
    AnnotationTask,
    make_id,
)
from nlp_semantic.dataset.agreement import (
    AgreementReport,
    Disagreement,
    cohen_kappa_single_label,
    compute_agreement,
    find_disagreements,
    jaccard_multilabel,
)


def _ann(
    *,
    achievement_id: str | None = None,
    task: AnnotationTask = AnnotationTask.PRIMARY_TYPE,
    label_ids: list[str] | None = None,
    annotator: str = "labeler_001",
    review_status: AnnotationStatus = AnnotationStatus.DRAFT,
    created_at: datetime | None = None,
    **overrides: Any,
) -> Annotation:
    if label_ids is None:
        label_ids = ["lbl_hackathon"] if task == AnnotationTask.PRIMARY_TYPE else []
    if created_at is None:
        created_at = datetime(2024, 6, 15, tzinfo=timezone.utc)
    data = dict(
        annotation_id=make_id("ann"),
        achievement_id=achievement_id or make_id("ach"),
        task=task,
        label_ids=label_ids,
        annotator=annotator,
        review_status=review_status,
        created_at=created_at,
        is_synthetic=True,
    )
    data.update(overrides)
    return Annotation(**data)


# ---- metric helpers ---------------------------------------------------------


def test_cohen_kappa_empty_pairs_is_none() -> None:
    assert cohen_kappa_single_label([]) is None


def test_cohen_kappa_single_class_is_undefined_none() -> None:
    """All pairs on one class -> expected agreement = 1 -> undefined (None)."""
    pairs = [("lbl_hackathon", "lbl_hackathon")] * 5
    assert cohen_kappa_single_label(pairs) is None


def test_cohen_kappa_full_disagreement() -> None:
    """Alternating pattern across two labels; kappa approaches 0 or negative."""
    pairs = [("lbl_a", "lbl_b"), ("lbl_b", "lbl_a")] * 10
    k = cohen_kappa_single_label(pairs)
    assert k is not None
    assert k < 0.5


def test_cohen_kappa_mixed_agreement_within_01_range() -> None:
    pairs = [("lbl_a", "lbl_a")] * 7 + [("lbl_a", "lbl_b")] * 3
    k = cohen_kappa_single_label(pairs)
    assert k is not None
    assert 0.0 <= k <= 1.0


def test_jaccard_empty_vs_empty_convention_is_1() -> None:
    assert jaccard_multilabel(set(), set()) == 1.0


def test_jaccard_identical_sets() -> None:
    assert jaccard_multilabel({"a", "b"}, {"a", "b"}) == 1.0


def test_jaccard_disjoint_sets_is_zero() -> None:
    assert jaccard_multilabel({"a"}, {"b"}) == 0.0


def test_jaccard_partial_overlap() -> None:
    # |{a,b} ∩ {b,c}| = 1, |{a,b,c}| = 3 -> 1/3
    assert jaccard_multilabel({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)


# ---- compute_agreement -----------------------------------------------------


def test_empty_annotations_returns_zeroed_report() -> None:
    rep = compute_agreement([], task=AnnotationTask.PRIMARY_TYPE)
    assert isinstance(rep, AgreementReport)
    assert rep.pairs_evaluated == 0
    assert rep.records_eligible_for_agreement == 0
    assert rep.cohen_kappa is None
    assert rep.mean_jaccard is None
    assert rep.exact_agreement_rate is None


def test_extraction_review_task_returns_empty_report() -> None:
    rep = compute_agreement([], task=AnnotationTask.EXTRACTION_REVIEW)
    assert rep.task == AnnotationTask.EXTRACTION_REVIEW
    assert rep.pairs_evaluated == 0
    assert rep.cohen_kappa is None
    assert rep.mean_jaccard is None


def test_single_annotator_record_contributes_zero_pairs() -> None:
    aid = make_id("ach")
    anns = [_ann(achievement_id=aid, annotator="labeler_001")]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.pairs_evaluated == 0
    assert rep.records_eligible_for_agreement == 0
    assert rep.records_single_annotator_only == 1


def test_two_agreeing_annotators_perfect_exact_rate() -> None:
    aid = make_id("ach")
    anns = [
        _ann(achievement_id=aid, annotator="labeler_001", label_ids=["lbl_hackathon"]),
        _ann(achievement_id=aid, annotator="labeler_002", label_ids=["lbl_hackathon"]),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.pairs_evaluated == 1
    assert rep.exact_agreement_rate == 1.0
    # single-class -> kappa undefined
    assert rep.cohen_kappa is None
    assert rep.disagreements == []


def test_two_disagreeing_annotators_populate_disagreement_list() -> None:
    aid = make_id("ach")
    anns = [
        _ann(achievement_id=aid, annotator="labeler_001", label_ids=["lbl_hackathon"]),
        _ann(achievement_id=aid, annotator="labeler_002", label_ids=["lbl_competition"]),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.pairs_evaluated == 1
    assert rep.exact_agreement_rate == 0.0
    assert len(rep.disagreements) == 1
    d = rep.disagreements[0]
    assert d.achievement_id == aid
    assert d.task == AnnotationTask.PRIMARY_TYPE
    labels_by_annotator = dict(d.annotators_and_labels)
    assert labels_by_annotator["labeler_001"] == ["lbl_hackathon"]
    assert labels_by_annotator["labeler_002"] == ["lbl_competition"]


def test_disagreement_output_contains_only_pseudonyms() -> None:
    aid = make_id("ach")
    anns = [
        _ann(achievement_id=aid, annotator="labeler_001", label_ids=["lbl_hackathon"]),
        _ann(achievement_id=aid, annotator="labeler_002", label_ids=["lbl_competition"]),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    # The reported strings must be exactly the pseudonyms we supplied.
    for d in rep.disagreements:
        for annotator, _ in d.annotators_and_labels:
            assert "@" not in annotator
            assert annotator.startswith("labeler_")


# ---- same-annotator collapse ------------------------------------------------


def test_self_reannotation_keeps_latest_by_created_at() -> None:
    aid = make_id("ach")
    older = _ann(
        achievement_id=aid, annotator="labeler_001",
        label_ids=["lbl_hackathon"],
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    newer = _ann(
        achievement_id=aid, annotator="labeler_001",
        label_ids=["lbl_competition"],
        created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    other = _ann(
        achievement_id=aid, annotator="labeler_002",
        label_ids=["lbl_competition"],
    )
    rep = compute_agreement([older, newer, other], task=AnnotationTask.PRIMARY_TYPE)
    # Only one pair: (labeler_001-latest=lbl_competition) vs labeler_002=lbl_competition -> agree
    assert rep.pairs_evaluated == 1
    assert rep.self_reannotation_count == 1
    assert rep.exact_agreement_rate == 1.0


def test_same_annotator_duplicate_not_counted_as_independent() -> None:
    aid = make_id("ach")
    # Only one distinct annotator across two rows -> single annotator only.
    anns = [
        _ann(
            achievement_id=aid, annotator="labeler_001",
            label_ids=["lbl_hackathon"],
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        _ann(
            achievement_id=aid, annotator="labeler_001",
            label_ids=["lbl_competition"],
            created_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
        ),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.pairs_evaluated == 0
    assert rep.records_eligible_for_agreement == 0
    assert rep.records_single_annotator_only == 1
    assert rep.self_reannotation_count == 1


# ---- review-status handling ------------------------------------------------


def test_rejected_annotations_excluded() -> None:
    aid = make_id("ach")
    anns = [
        _ann(
            achievement_id=aid, annotator="labeler_001",
            label_ids=["lbl_hackathon"],
            review_status=AnnotationStatus.REJECTED,
        ),
        _ann(
            achievement_id=aid, annotator="labeler_002",
            label_ids=["lbl_hackathon"],
            review_status=AnnotationStatus.VERIFIED,
        ),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.pairs_evaluated == 0
    assert rep.records_single_annotator_only == 1
    assert rep.conflict_count == 0


def test_record_with_only_rejected_annotations_counted() -> None:
    aid = make_id("ach")
    anns = [
        _ann(
            achievement_id=aid, annotator="labeler_001",
            label_ids=["lbl_hackathon"],
            review_status=AnnotationStatus.REJECTED,
        ),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.records_with_rejected_only == 1


def test_conflicted_annotations_included_and_counted() -> None:
    aid = make_id("ach")
    anns = [
        _ann(
            achievement_id=aid, annotator="labeler_001",
            label_ids=["lbl_hackathon"],
            review_status=AnnotationStatus.CONFLICTED,
        ),
        _ann(
            achievement_id=aid, annotator="labeler_002",
            label_ids=["lbl_competition"],
            review_status=AnnotationStatus.CONFLICTED,
        ),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.pairs_evaluated == 1
    assert rep.conflict_count == 2
    assert rep.exact_agreement_rate == 0.0


# ---- multi-label (domain_tags) ---------------------------------------------


def test_domain_tags_empty_sets_agree_perfectly() -> None:
    aid = make_id("ach")
    anns = [
        _ann(
            achievement_id=aid, annotator="labeler_001",
            task=AnnotationTask.DOMAIN_TAGS, label_ids=[],
        ),
        _ann(
            achievement_id=aid, annotator="labeler_002",
            task=AnnotationTask.DOMAIN_TAGS, label_ids=[],
        ),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.DOMAIN_TAGS)
    assert rep.pairs_evaluated == 1
    assert rep.mean_jaccard == 1.0
    assert rep.exact_agreement_rate == 1.0
    assert rep.cohen_kappa is None  # kappa not computed for multi-label


def test_domain_tags_partial_overlap_jaccard() -> None:
    aid = make_id("ach")
    anns = [
        _ann(
            achievement_id=aid, annotator="labeler_001",
            task=AnnotationTask.DOMAIN_TAGS, label_ids=["lbl_domain_ai", "lbl_domain_ml"],
        ),
        _ann(
            achievement_id=aid, annotator="labeler_002",
            task=AnnotationTask.DOMAIN_TAGS, label_ids=["lbl_domain_ml", "lbl_domain_nlp"],
        ),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.DOMAIN_TAGS)
    assert rep.mean_jaccard == pytest.approx(1 / 3)
    assert rep.exact_agreement_rate == 0.0


# ---- task filtering --------------------------------------------------------


def test_other_task_annotations_are_ignored() -> None:
    """Only the requested task counts; cross-task rows don't form pairs."""
    aid = make_id("ach")
    anns = [
        _ann(
            achievement_id=aid, annotator="labeler_001",
            task=AnnotationTask.PRIMARY_TYPE, label_ids=["lbl_hackathon"],
        ),
        _ann(
            achievement_id=aid, annotator="labeler_002",
            task=AnnotationTask.DOMAIN_TAGS, label_ids=["lbl_domain_ai"],
        ),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.pairs_evaluated == 0
    assert rep.records_single_annotator_only == 1


# ---- multi-annotator (3+ reviewers) ----------------------------------------


def test_three_annotators_two_agree_one_differs_primary_type() -> None:
    """X=A, Y=A, Z=B produces 3 ordered pairs: (A,A), (A,B), (A,B).

    - exact_agreement_rate = 1/3
    - freq_a = {A:3}, freq_b = {A:1, B:2}
    - pe = (3*1 + 0*2)/9 = 1/3
    - po = 1/3 -> kappa = 0.0
    """
    aid = make_id("ach")
    anns = [
        _ann(achievement_id=aid, annotator="labeler_001", label_ids=["lbl_hackathon"]),
        _ann(achievement_id=aid, annotator="labeler_002", label_ids=["lbl_hackathon"]),
        _ann(achievement_id=aid, annotator="labeler_003", label_ids=["lbl_competition"]),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.pairs_evaluated == 3           # C(3,2) = 3 pairs
    assert rep.records_eligible_for_agreement == 1
    assert rep.exact_agreement_rate == pytest.approx(1 / 3)
    assert rep.cohen_kappa == pytest.approx(0.0)
    # Record disagreed on at least one pair.
    assert len(rep.disagreements) == 1
    annotators = {a for a, _ in rep.disagreements[0].annotators_and_labels}
    assert annotators == {"labeler_001", "labeler_002", "labeler_003"}


def test_three_annotators_all_different_labels_primary_type() -> None:
    """X=A, Y=B, Z=C produces 3 pairs: (A,B), (A,C), (B,C). All disagree.

    - exact_agreement_rate = 0
    - freq_a = {A:2, B:1}, freq_b = {B:1, C:2}
    - pe = (2*0 + 1*1 + 0*2)/9 = 1/9
    - po = 0 -> kappa = (0 - 1/9) / (1 - 1/9) = -1/8
    """
    aid = make_id("ach")
    anns = [
        _ann(achievement_id=aid, annotator="labeler_001", label_ids=["lbl_hackathon"]),
        _ann(achievement_id=aid, annotator="labeler_002", label_ids=["lbl_competition"]),
        _ann(achievement_id=aid, annotator="labeler_003", label_ids=["lbl_research_pub"]),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.pairs_evaluated == 3
    assert rep.exact_agreement_rate == 0.0
    assert rep.cohen_kappa == pytest.approx(-1 / 8)


def test_three_annotators_all_agree_single_class_kappa_none() -> None:
    """All three annotators agree on the same single label -> kappa undefined."""
    aid = make_id("ach")
    anns = [
        _ann(achievement_id=aid, annotator="labeler_001", label_ids=["lbl_hackathon"]),
        _ann(achievement_id=aid, annotator="labeler_002", label_ids=["lbl_hackathon"]),
        _ann(achievement_id=aid, annotator="labeler_003", label_ids=["lbl_hackathon"]),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert rep.pairs_evaluated == 3
    assert rep.exact_agreement_rate == 1.0
    # Single class -> expected agreement = 1 -> kappa undefined -> None.
    assert rep.cohen_kappa is None


# ---- find_disagreements convenience ----------------------------------------


def test_find_disagreements_matches_report_field() -> None:
    aid = make_id("ach")
    anns = [
        _ann(achievement_id=aid, annotator="labeler_001", label_ids=["lbl_hackathon"]),
        _ann(achievement_id=aid, annotator="labeler_002", label_ids=["lbl_competition"]),
    ]
    full = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    just = find_disagreements(anns, task=AnnotationTask.PRIMARY_TYPE)
    assert len(just) == 1 == len(full.disagreements)
    assert just[0].achievement_id == full.disagreements[0].achievement_id


# ---- to_dict is JSON-serializable ------------------------------------------


def test_to_dict_is_json_serializable() -> None:
    import json
    aid = make_id("ach")
    anns = [
        _ann(achievement_id=aid, annotator="labeler_001", label_ids=["lbl_hackathon"]),
        _ann(achievement_id=aid, annotator="labeler_002", label_ids=["lbl_competition"]),
    ]
    rep = compute_agreement(anns, task=AnnotationTask.PRIMARY_TYPE)
    s = json.dumps(rep.to_dict())
    data = json.loads(s)
    assert data["task"] == "primary_type"
    assert data["pairs_evaluated"] == 1
    # Two labels, pair-wise exact disagreement -> kappa is defined.
    assert isinstance(data["cohen_kappa"], float)
