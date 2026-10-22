"""Tests for dataset statistics module."""
from __future__ import annotations

import json
from typing import Any

from nlp_semantic.schema import (
    Achievement,
    AnnotationStatus,
    AnnotationStatusMap,
    make_id,
)
from nlp_semantic.dataset.stats import compute_stats, DatasetStatsReport


def _rec(**overrides: Any) -> Achievement:
    base: dict[str, Any] = dict(
        achievement_id=make_id("ach"),
        source_id=make_id("src"),
        source_record_id="src-ext-" + make_id("ach")[-6:],
        achievement_text="A synthetic achievement.",
        is_synthetic=True,
    )
    base.update(overrides)
    return Achievement(**base)


def test_empty_input_zeroed_report() -> None:
    rep = compute_stats([])
    assert isinstance(rep, DatasetStatsReport)
    assert rep.total_records == 0
    assert rep.synthetic_count == 0
    assert rep.real_count == 0
    assert rep.primary_type_counts == {}
    assert rep.domain_tag_counts == {}
    assert rep.per_source_counts == {}
    assert rep.cooccurrence == {}


def test_synthetic_vs_real_split() -> None:
    rep = compute_stats([
        _rec(is_synthetic=True),
        _rec(is_synthetic=True),
        _rec(is_synthetic=False),
    ])
    assert rep.total_records == 3
    assert rep.synthetic_count == 2
    assert rep.real_count == 1


def test_primary_type_counts_sorted_by_count_desc() -> None:
    rep = compute_stats([
        _rec(
            primary_type="lbl_hackathon",
            annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
        ),
        _rec(
            primary_type="lbl_hackathon",
            annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
        ),
        _rec(
            primary_type="lbl_competition",
            annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
        ),
        _rec(),  # unannotated
    ])
    # Sorted (-count, lex); hackathon leads, remaining two tie at 1 and
    # order lexicographically ("<" < "l").
    assert list(rep.primary_type_counts.keys()) == [
        "lbl_hackathon", "<none>", "lbl_competition",
    ]
    assert rep.primary_type_counts["lbl_hackathon"] == 2
    assert rep.primary_type_counts["lbl_competition"] == 1
    assert rep.primary_type_counts["<none>"] == 1


def test_domain_tag_counts_multilabel() -> None:
    rep = compute_stats([
        _rec(
            domain_tags=["lbl_domain_ai", "lbl_domain_ml"],
            annotation_status=AnnotationStatusMap(domain_tags=AnnotationStatus.VERIFIED),
        ),
        _rec(
            domain_tags=["lbl_domain_ai"],
            annotation_status=AnnotationStatusMap(domain_tags=AnnotationStatus.VERIFIED),
        ),
        _rec(),  # no domain tags, status not_started
    ])
    assert rep.domain_tag_counts["lbl_domain_ai"] == 2
    assert rep.domain_tag_counts["lbl_domain_ml"] == 1
    assert rep.records_with_no_domain_tags == 1


def test_status_counts_present_for_both_tasks() -> None:
    rep = compute_stats([
        _rec(
            primary_type="lbl_hackathon",
            annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
        ),
        _rec(),  # defaults: both NOT_STARTED
    ])
    assert rep.primary_type_status_counts["verified"] == 1
    assert rep.primary_type_status_counts["not_started"] == 1
    assert rep.domain_tag_status_counts["not_started"] == 2


def test_per_source_counts() -> None:
    sid = make_id("src")
    rep = compute_stats([
        _rec(source_id=sid, source_record_id="k1"),
        _rec(source_id=sid, source_record_id="k2"),
        _rec(),  # different source
    ])
    assert rep.per_source_counts[sid] == 2


def test_cooccurrence_matrix() -> None:
    rep = compute_stats([
        _rec(
            primary_type="lbl_hackathon",
            domain_tags=["lbl_domain_ai", "lbl_domain_ml"],
            annotation_status=AnnotationStatusMap(
                primary_type=AnnotationStatus.VERIFIED,
                domain_tags=AnnotationStatus.VERIFIED,
            ),
        ),
        _rec(
            primary_type="lbl_hackathon",
            domain_tags=["lbl_domain_ai"],
            annotation_status=AnnotationStatusMap(
                primary_type=AnnotationStatus.VERIFIED,
                domain_tags=AnnotationStatus.VERIFIED,
            ),
        ),
        _rec(
            primary_type="lbl_research_pub",
            domain_tags=["lbl_domain_nlp"],
            annotation_status=AnnotationStatusMap(
                primary_type=AnnotationStatus.VERIFIED,
                domain_tags=AnnotationStatus.VERIFIED,
            ),
        ),
    ])
    assert rep.cooccurrence["lbl_hackathon"] == {"lbl_domain_ai": 2, "lbl_domain_ml": 1}
    assert rep.cooccurrence["lbl_research_pub"] == {"lbl_domain_nlp": 1}


def test_to_dict_is_json_serializable() -> None:
    rep = compute_stats([
        _rec(
            primary_type="lbl_hackathon",
            domain_tags=["lbl_domain_ai"],
            annotation_status=AnnotationStatusMap(
                primary_type=AnnotationStatus.VERIFIED,
                domain_tags=AnnotationStatus.VERIFIED,
            ),
        ),
    ])
    s = json.dumps(rep.to_dict())
    assert "lbl_hackathon" in s
    assert "lbl_domain_ai" in s


def test_stats_never_mutates_input() -> None:
    r1 = _rec(primary_type=None)
    r2 = _rec(primary_type=None)
    r1_text_before = r1.achievement_text
    compute_stats([r1, r2])
    assert r1.achievement_text == r1_text_before
    assert r1.primary_type is None


def test_cooccurrence_sorted_by_count_desc_within_each_primary() -> None:
    rep = compute_stats([
        _rec(
            primary_type="lbl_hackathon",
            domain_tags=["lbl_domain_ai"],
            annotation_status=AnnotationStatusMap(
                primary_type=AnnotationStatus.VERIFIED,
                domain_tags=AnnotationStatus.VERIFIED,
            ),
        ),
        _rec(
            primary_type="lbl_hackathon",
            domain_tags=["lbl_domain_ai"],
            annotation_status=AnnotationStatusMap(
                primary_type=AnnotationStatus.VERIFIED,
                domain_tags=AnnotationStatus.VERIFIED,
            ),
        ),
        _rec(
            primary_type="lbl_hackathon",
            domain_tags=["lbl_domain_ml"],
            annotation_status=AnnotationStatusMap(
                primary_type=AnnotationStatus.VERIFIED,
                domain_tags=AnnotationStatus.VERIFIED,
            ),
        ),
    ])
    row = rep.cooccurrence["lbl_hackathon"]
    assert list(row.keys()) == ["lbl_domain_ai", "lbl_domain_ml"]
    assert list(row.values()) == [2, 1]
