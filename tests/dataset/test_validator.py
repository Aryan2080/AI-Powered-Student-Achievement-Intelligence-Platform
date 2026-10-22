"""Tests for cross-record validator + ground-truth eligibility filter."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from nlp_semantic.schema import (
    Achievement,
    Annotation,
    AnnotationStatus,
    AnnotationStatusMap,
    AnnotationTask,
    LabelTaxonomy,
    ReviewStatus,
    SourceRegistry,
    TaxonomyStatus,
    TaxonomyTask,
    UNKNOWN_LICENSE,
    make_id,
    load_and_validate_taxonomy,
)
from nlp_semantic.dataset.validator import (
    DatasetValidationReport,
    eligible_ground_truth,
    validate_dataset,
)

from tests.dataset.conftest import REPO_ROOT


# ---- fixture helpers ---------------------------------------------------------


def _source(**overrides: Any) -> SourceRegistry:
    base = dict(
        source_id=make_id("src"),
        source_name="Synthetic",
        source_url="https://example.org/x",
        license="CC-BY-4.0",
        collection_date=date.today(),
        intended_use="primary_type_training",
        review_status=ReviewStatus.VERIFIED,
        is_synthetic=True,
    )
    base.update(overrides)
    return SourceRegistry(**base)


def _primary_label(label_id: str, *, status: TaxonomyStatus = TaxonomyStatus.DRAFT) -> LabelTaxonomy:
    return LabelTaxonomy(
        label_id=label_id,
        task_name=TaxonomyTask.PRIMARY_TYPE,
        display_name=label_id.replace("lbl_", "").title(),
        definition="synthetic test entry",
        status=status,
    )


def _domain_label(label_id: str, *, status: TaxonomyStatus = TaxonomyStatus.DRAFT) -> LabelTaxonomy:
    return LabelTaxonomy(
        label_id=label_id,
        task_name=TaxonomyTask.DOMAIN_TAGS,
        display_name=label_id.replace("lbl_", "").title(),
        definition="synthetic test entry",
        status=status,
    )


def _rec(
    source_id: str,
    *,
    primary_type: str | None = None,
    domain_tags: list[str] | None = None,
    annotation_status: AnnotationStatusMap | None = None,
    source_record_id: str = "src-ext-001",
    **overrides: Any,
) -> Achievement:
    data: dict[str, Any] = dict(
        achievement_id=make_id("ach"),
        source_id=source_id,
        source_record_id=source_record_id,
        achievement_text="Synthetic record.",
        primary_type=primary_type,
        domain_tags=list(domain_tags or []),
        annotation_status=annotation_status or AnnotationStatusMap(),
        is_synthetic=True,
    )
    data.update(overrides)
    return Achievement(**data)


def _ann(
    *,
    achievement_id: str,
    task: AnnotationTask = AnnotationTask.PRIMARY_TYPE,
    label_ids: list[str] | None = None,
    **overrides: Any,
) -> Annotation:
    if label_ids is None:
        label_ids = ["lbl_hackathon"] if task == AnnotationTask.PRIMARY_TYPE else []
    data: dict[str, Any] = dict(
        annotation_id=make_id("ann"),
        achievement_id=achievement_id,
        task=task,
        label_ids=list(label_ids),
        annotator="labeler_001",
        review_status=AnnotationStatus.DRAFT,
        created_at=datetime(2024, 6, 15, tzinfo=timezone.utc),
        is_synthetic=True,
    )
    data.update(overrides)
    return Annotation(**data)


# ---- happy path --------------------------------------------------------------


def test_empty_dataset_validates_clean() -> None:
    rep = validate_dataset(
        records=[],
        annotations=[],
        sources=[],
        primary_taxonomy=[],
        domain_taxonomy=[],
    )
    assert isinstance(rep, DatasetValidationReport)
    assert rep.is_valid
    assert rep.fatal_count == 0
    assert rep.advisory_count == 0


def test_single_clean_record_validates() -> None:
    src = _source()
    rec = _rec(
        src.source_id,
        primary_type="lbl_hackathon",
        annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
    )
    rep = validate_dataset(
        records=[rec],
        annotations=[],
        sources=[src],
        primary_taxonomy=[_primary_label("lbl_hackathon", status=TaxonomyStatus.APPROVED)],
        domain_taxonomy=[],
    )
    assert rep.is_valid
    assert rep.fatal_count == 0
    assert rep.advisory_count == 0


# ---- fatal: FK violations ----------------------------------------------------


def test_unknown_source_id_is_fatal() -> None:
    rec = _rec(source_id=make_id("src"))  # not registered
    rep = validate_dataset(
        records=[rec],
        annotations=[],
        sources=[],
        primary_taxonomy=[],
        domain_taxonomy=[],
    )
    assert not rep.is_valid
    assert len(rep.unknown_source_refs) == 1
    assert rep.unknown_source_refs[0] == (rec.achievement_id, rec.source_id)


def test_unknown_primary_type_is_fatal() -> None:
    src = _source()
    rec = _rec(
        src.source_id,
        primary_type="lbl_unknown",
        annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
    )
    rep = validate_dataset(
        records=[rec],
        annotations=[],
        sources=[src],
        primary_taxonomy=[],  # label not present
        domain_taxonomy=[],
    )
    assert not rep.is_valid
    assert rep.unknown_primary_type_refs == [(rec.achievement_id, "lbl_unknown")]


def test_unknown_domain_tag_is_fatal() -> None:
    src = _source()
    rec = _rec(
        src.source_id,
        domain_tags=["lbl_domain_unknown"],
        annotation_status=AnnotationStatusMap(domain_tags=AnnotationStatus.VERIFIED),
    )
    rep = validate_dataset(
        records=[rec],
        annotations=[],
        sources=[src],
        primary_taxonomy=[],
        domain_taxonomy=[],
    )
    assert not rep.is_valid
    assert rep.unknown_domain_tag_refs == [(rec.achievement_id, "lbl_domain_unknown")]


def test_deprecated_label_is_fatal() -> None:
    src = _source()
    rec = _rec(
        src.source_id,
        primary_type="lbl_old",
        annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
    )
    rep = validate_dataset(
        records=[rec],
        annotations=[],
        sources=[src],
        primary_taxonomy=[_primary_label("lbl_old", status=TaxonomyStatus.DEPRECATED)],
        domain_taxonomy=[],
    )
    assert not rep.is_valid
    assert rep.deprecated_label_refs == [(rec.achievement_id, "lbl_old")]


def test_duplicate_source_record_pair_is_fatal() -> None:
    src = _source()
    r1 = _rec(src.source_id, source_record_id="dup-key")
    r2 = _rec(src.source_id, source_record_id="dup-key")
    rep = validate_dataset(
        records=[r1, r2],
        annotations=[],
        sources=[src],
        primary_taxonomy=[],
        domain_taxonomy=[],
    )
    assert not rep.is_valid
    assert rep.duplicate_source_record_pairs == [(src.source_id, "dup-key")]


def test_orphan_annotation_is_fatal() -> None:
    src = _source()
    rec = _rec(src.source_id)
    orphan = _ann(achievement_id=make_id("ach"))  # points to a non-existent record
    rep = validate_dataset(
        records=[rec],
        annotations=[orphan],
        sources=[src],
        primary_taxonomy=[_primary_label("lbl_hackathon", status=TaxonomyStatus.APPROVED)],
        domain_taxonomy=[],
    )
    assert not rep.is_valid
    assert rep.orphan_annotations == [(orphan.annotation_id, orphan.achievement_id)]


def test_annotation_unknown_label_is_fatal() -> None:
    src = _source()
    rec = _rec(src.source_id)
    ann = _ann(achievement_id=rec.achievement_id, label_ids=["lbl_mystery"])
    rep = validate_dataset(
        records=[rec],
        annotations=[ann],
        sources=[src],
        primary_taxonomy=[_primary_label("lbl_hackathon", status=TaxonomyStatus.APPROVED)],
        domain_taxonomy=[],
    )
    assert not rep.is_valid
    assert rep.annotation_unknown_labels == [(ann.annotation_id, "lbl_mystery")]


# ---- advisory: license, review status, draft label refs ---------------------


def test_unknown_license_surfaces_as_advisory() -> None:
    src = _source(license=UNKNOWN_LICENSE)
    rec = _rec(src.source_id)
    rep = validate_dataset(
        records=[rec],
        annotations=[],
        sources=[src],
        primary_taxonomy=[],
        domain_taxonomy=[],
    )
    assert rep.is_valid  # advisory doesn't flip the fatal flag
    assert rep.unknown_license_source_ids == [src.source_id]


def test_unverified_source_surfaces_as_advisory() -> None:
    src = _source(review_status=ReviewStatus.UNREVIEWED)
    rec = _rec(src.source_id)
    rep = validate_dataset(
        records=[rec],
        annotations=[],
        sources=[src],
        primary_taxonomy=[],
        domain_taxonomy=[],
    )
    assert rep.is_valid
    assert rep.unverified_source_ids == [src.source_id]


def test_draft_label_reference_is_advisory_not_fatal() -> None:
    src = _source()
    rec = _rec(
        src.source_id,
        primary_type="lbl_hackathon",
        annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
    )
    rep = validate_dataset(
        records=[rec],
        annotations=[],
        sources=[src],
        primary_taxonomy=[_primary_label("lbl_hackathon", status=TaxonomyStatus.DRAFT)],
        domain_taxonomy=[],
    )
    assert rep.is_valid
    assert rep.draft_label_refs == [(rec.achievement_id, "lbl_hackathon")]


# ---- taxonomy homogeneity guard ---------------------------------------------


def test_mixed_task_in_primary_taxonomy_raises() -> None:
    with pytest.raises(ValueError, match="task_name"):
        validate_dataset(
            records=[],
            annotations=[],
            sources=[],
            primary_taxonomy=[_domain_label("lbl_domain_ai")],  # wrong task
            domain_taxonomy=[],
        )


# ---- summary() serializes cleanly -------------------------------------------


def test_summary_is_json_shaped(dataset_root: Path) -> None:
    src = _source()
    rec = _rec(
        src.source_id,
        primary_type="lbl_hackathon",
        annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
    )
    rep = validate_dataset(
        records=[rec],
        annotations=[],
        sources=[src],
        primary_taxonomy=[_primary_label("lbl_hackathon", status=TaxonomyStatus.APPROVED)],
        domain_taxonomy=[],
    )
    import json

    summary = rep.summary()
    s = json.dumps(summary)  # must not raise
    reparsed = json.loads(s)
    assert reparsed["records"] == 1
    assert reparsed["is_valid"] is True
    assert reparsed["fatal_count"] == 0


# ---- eligible_ground_truth (primary_type) -----------------------------------


def test_gt_primary_type_requires_verified_and_approved() -> None:
    src = _source()
    r_verified_approved = _rec(
        src.source_id,
        primary_type="lbl_hackathon",
        source_record_id="r1",
        annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
    )
    r_draft_status = _rec(
        src.source_id,
        primary_type="lbl_hackathon",
        source_record_id="r2",
        annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.DRAFT),
    )
    r_draft_label = _rec(
        src.source_id,
        primary_type="lbl_draft_only",
        source_record_id="r3",
        annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
    )
    taxonomy = [
        _primary_label("lbl_hackathon", status=TaxonomyStatus.APPROVED),
        _primary_label("lbl_draft_only", status=TaxonomyStatus.DRAFT),
    ]
    out = eligible_ground_truth(
        [r_verified_approved, r_draft_status, r_draft_label],
        primary_taxonomy=taxonomy,
        task=AnnotationTask.PRIMARY_TYPE,
    )
    assert [r.achievement_id for r in out] == [r_verified_approved.achievement_id]


def test_gt_domain_tags_requires_all_tags_approved() -> None:
    src = _source()
    rec_ok = _rec(
        src.source_id,
        domain_tags=["lbl_domain_ai", "lbl_domain_ml"],
        annotation_status=AnnotationStatusMap(domain_tags=AnnotationStatus.VERIFIED),
    )
    rec_mixed = _rec(
        src.source_id,
        domain_tags=["lbl_domain_ai", "lbl_domain_drafted"],
        source_record_id="r2",
        annotation_status=AnnotationStatusMap(domain_tags=AnnotationStatus.VERIFIED),
    )
    taxonomy = [
        _domain_label("lbl_domain_ai", status=TaxonomyStatus.APPROVED),
        _domain_label("lbl_domain_ml", status=TaxonomyStatus.APPROVED),
        _domain_label("lbl_domain_drafted", status=TaxonomyStatus.DRAFT),
    ]
    out = eligible_ground_truth(
        [rec_ok, rec_mixed],
        domain_taxonomy=taxonomy,
        task=AnnotationTask.DOMAIN_TAGS,
    )
    assert [r.achievement_id for r in out] == [rec_ok.achievement_id]


def test_gt_shipped_taxonomies_yield_empty_set() -> None:
    """Chunk 3 taxonomies are all draft, so no record is yet GT eligible."""
    primary = load_and_validate_taxonomy(
        REPO_ROOT / "hybrid_dataset" / "labels" / "primary_taxonomy.yaml"
    )
    src = _source()
    # even a fully "verified" record referencing a shipped label is not GT.
    rec = _rec(
        src.source_id,
        primary_type="lbl_hackathon",
        annotation_status=AnnotationStatusMap(primary_type=AnnotationStatus.VERIFIED),
    )
    out = eligible_ground_truth([rec], primary_taxonomy=primary, task=AnnotationTask.PRIMARY_TYPE)
    assert out == []


def test_gt_extraction_review_task_returns_empty() -> None:
    assert eligible_ground_truth([], task=AnnotationTask.EXTRACTION_REVIEW) == []


def test_gt_primary_type_requires_primary_taxonomy_kw() -> None:
    with pytest.raises(ValueError, match="primary_taxonomy is required"):
        eligible_ground_truth([], task=AnnotationTask.PRIMARY_TYPE)


def test_gt_domain_tags_requires_domain_taxonomy_kw() -> None:
    with pytest.raises(ValueError, match="domain_taxonomy is required"):
        eligible_ground_truth([], task=AnnotationTask.DOMAIN_TAGS)
