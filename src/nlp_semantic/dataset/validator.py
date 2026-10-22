"""Cross-record validation and ground-truth eligibility.

The Chunk 4 handoff deferred cross-record FK checks (does an
``Achievement.source_id`` actually exist in ``sources.yaml``? does a
``primary_type`` label exist in the taxonomy?) to a future
dataset-level validator. This module is that validator.

The validator **returns a report**; it does not raise on dataset
content. The report distinguishes fatal violations from advisory
warnings. Callers (notably the CLI) decide whether to fail the run.
Per-entry format problems were already enforced by Pydantic in the
loader; by the time records reach this validator, each one is
structurally valid.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from nlp_semantic.schema import (
    Achievement,
    Annotation,
    AnnotationStatus,
    AnnotationTask,
    LabelTaxonomy,
    ReviewStatus,
    SourceRegistry,
    TaxonomyStatus,
    TaxonomyTask,
    UNKNOWN_LICENSE,
)


@dataclass(frozen=True)
class DatasetValidationReport:
    """Fatal + advisory findings from a cross-record validation pass.

    ``records`` and ``annotations`` are passed through unchanged so the
    report is self-contained. Lists use ``(achievement_id, label_id)``
    or ``(source_id, source_record_id)`` tuples so the CLI can print
    pointer trails without re-walking the dataset.
    """

    records: list[Achievement]
    annotations: list[Annotation]

    # Fatal: unknown FK references.
    unknown_source_refs: list[tuple[str, str]] = field(default_factory=list)
    unknown_primary_type_refs: list[tuple[str, str]] = field(default_factory=list)
    unknown_domain_tag_refs: list[tuple[str, str]] = field(default_factory=list)
    deprecated_label_refs: list[tuple[str, str]] = field(default_factory=list)
    duplicate_source_record_pairs: list[tuple[str, str]] = field(default_factory=list)
    orphan_annotations: list[tuple[str, str]] = field(default_factory=list)
    annotation_unknown_labels: list[tuple[str, str]] = field(default_factory=list)

    # Advisory: load-time concerns from Chunk 4 + taxonomy-draft refs.
    draft_label_refs: list[tuple[str, str]] = field(default_factory=list)
    unknown_license_source_ids: list[str] = field(default_factory=list)
    unverified_source_ids: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True when no fatal findings were recorded."""
        return not (
            self.unknown_source_refs
            or self.unknown_primary_type_refs
            or self.unknown_domain_tag_refs
            or self.deprecated_label_refs
            or self.duplicate_source_record_pairs
            or self.orphan_annotations
            or self.annotation_unknown_labels
        )

    @property
    def fatal_count(self) -> int:
        return (
            len(self.unknown_source_refs)
            + len(self.unknown_primary_type_refs)
            + len(self.unknown_domain_tag_refs)
            + len(self.deprecated_label_refs)
            + len(self.duplicate_source_record_pairs)
            + len(self.orphan_annotations)
            + len(self.annotation_unknown_labels)
        )

    @property
    def advisory_count(self) -> int:
        return (
            len(self.draft_label_refs)
            + len(self.unknown_license_source_ids)
            + len(self.unverified_source_ids)
        )

    def summary(self) -> dict[str, Any]:
        """Flat dict suitable for JSON serialization by the CLI."""
        return {
            "records": len(self.records),
            "annotations": len(self.annotations),
            "is_valid": self.is_valid,
            "fatal_count": self.fatal_count,
            "advisory_count": self.advisory_count,
            "fatal": {
                "unknown_source_refs": [list(t) for t in self.unknown_source_refs],
                "unknown_primary_type_refs": [list(t) for t in self.unknown_primary_type_refs],
                "unknown_domain_tag_refs": [list(t) for t in self.unknown_domain_tag_refs],
                "deprecated_label_refs": [list(t) for t in self.deprecated_label_refs],
                "duplicate_source_record_pairs": [
                    list(t) for t in self.duplicate_source_record_pairs
                ],
                "orphan_annotations": [list(t) for t in self.orphan_annotations],
                "annotation_unknown_labels": [
                    list(t) for t in self.annotation_unknown_labels
                ],
            },
            "advisory": {
                "draft_label_refs": [list(t) for t in self.draft_label_refs],
                "unknown_license_source_ids": list(self.unknown_license_source_ids),
                "unverified_source_ids": list(self.unverified_source_ids),
            },
        }


def _index_taxonomy(
    entries: Iterable[LabelTaxonomy],
) -> dict[str, LabelTaxonomy]:
    """Return a label_id -> entry map; later duplicates would've been caught upstream."""
    return {e.label_id: e for e in entries}


def validate_dataset(
    *,
    records: Iterable[Achievement],
    annotations: Iterable[Annotation],
    sources: Iterable[SourceRegistry],
    primary_taxonomy: Iterable[LabelTaxonomy],
    domain_taxonomy: Iterable[LabelTaxonomy],
) -> DatasetValidationReport:
    """Run the deferred Chunk 4 FK checks + collect advisory warnings.

    Fatal findings (populate ``report.*_refs`` / ``_pairs`` /
    ``orphan_*``):

    * Record references a ``source_id`` not present in ``sources``.
    * Record's ``primary_type`` is not in ``primary_taxonomy``.
    * Record's ``domain_tags`` entry is not in ``domain_taxonomy``.
    * Record references a taxonomy entry whose ``status`` is
      ``deprecated``.
    * Duplicate ``(source_id, source_record_id)`` pair across records.
    * Annotation whose ``achievement_id`` is not among the loaded
      records.
    * Annotation's ``label_ids`` references an unknown or
      wrong-task label.

    Advisory findings (``report.draft_label_refs``,
    ``unknown_license_source_ids``, ``unverified_source_ids``):

    * Record references a label that is still ``draft`` or
      ``under_review`` — informational only; label promotion is a
      separate human PR.
    * Record points at a source whose ``license == UNKNOWN``.
    * Record points at a source whose ``review_status != VERIFIED``.
    """
    records_list = list(records)
    annotations_list = list(annotations)
    sources_list = list(sources)
    primary_list = list(primary_taxonomy)
    domain_list = list(domain_taxonomy)

    # Guard: each taxonomy must be homogeneous w.r.t. its task.
    for entry in primary_list:
        if entry.task_name != TaxonomyTask.PRIMARY_TYPE:
            raise ValueError(
                f"primary_taxonomy entry {entry.label_id!r} has "
                f"task_name={entry.task_name.value!r}; expected "
                "'primary_type'"
            )
    for entry in domain_list:
        if entry.task_name != TaxonomyTask.DOMAIN_TAGS:
            raise ValueError(
                f"domain_taxonomy entry {entry.label_id!r} has "
                f"task_name={entry.task_name.value!r}; expected "
                "'domain_tags'"
            )

    sources_by_id: dict[str, SourceRegistry] = {s.source_id: s for s in sources_list}
    primary_by_id = _index_taxonomy(primary_list)
    domain_by_id = _index_taxonomy(domain_list)
    record_ids = {r.achievement_id for r in records_list}

    rep = DatasetValidationReport(records=records_list, annotations=annotations_list)

    # Build (source_id, source_record_id) duplicate check once.
    seen_source_record: dict[tuple[str, str], str] = {}

    for rec in records_list:
        aid = rec.achievement_id

        # FK: source
        if rec.source_id not in sources_by_id:
            rep.unknown_source_refs.append((aid, rec.source_id))
        else:
            src = sources_by_id[rec.source_id]
            if src.license == UNKNOWN_LICENSE and src.source_id not in rep.unknown_license_source_ids:
                rep.unknown_license_source_ids.append(src.source_id)
            if src.review_status != ReviewStatus.VERIFIED and src.source_id not in rep.unverified_source_ids:
                rep.unverified_source_ids.append(src.source_id)

        # Duplicate (source_id, source_record_id)
        key = (rec.source_id, rec.source_record_id)
        if key in seen_source_record:
            rep.duplicate_source_record_pairs.append(key)
        else:
            seen_source_record[key] = aid

        # primary_type reference
        if rec.primary_type is not None:
            entry = primary_by_id.get(rec.primary_type)
            if entry is None:
                rep.unknown_primary_type_refs.append((aid, rec.primary_type))
            elif entry.status == TaxonomyStatus.DEPRECATED:
                rep.deprecated_label_refs.append((aid, rec.primary_type))
            elif entry.status != TaxonomyStatus.APPROVED:
                rep.draft_label_refs.append((aid, rec.primary_type))

        # domain_tags references
        for tag in rec.domain_tags:
            entry = domain_by_id.get(tag)
            if entry is None:
                rep.unknown_domain_tag_refs.append((aid, tag))
            elif entry.status == TaxonomyStatus.DEPRECATED:
                rep.deprecated_label_refs.append((aid, tag))
            elif entry.status != TaxonomyStatus.APPROVED:
                rep.draft_label_refs.append((aid, tag))

    # Annotation checks
    for ann in annotations_list:
        if ann.achievement_id not in record_ids:
            rep.orphan_annotations.append((ann.annotation_id, ann.achievement_id))
        # Per-task label-reference check
        if ann.task == AnnotationTask.PRIMARY_TYPE:
            for lid in ann.label_ids:
                entry = primary_by_id.get(lid)
                if entry is None:
                    rep.annotation_unknown_labels.append((ann.annotation_id, lid))
        elif ann.task == AnnotationTask.DOMAIN_TAGS:
            for lid in ann.label_ids:
                entry = domain_by_id.get(lid)
                if entry is None:
                    rep.annotation_unknown_labels.append((ann.annotation_id, lid))
        # EXTRACTION_REVIEW has empty label_ids by schema invariant.

    return rep


def eligible_ground_truth(
    records: Iterable[Achievement],
    *,
    primary_taxonomy: Iterable[LabelTaxonomy] | None = None,
    domain_taxonomy: Iterable[LabelTaxonomy] | None = None,
    task: AnnotationTask,
) -> list[Achievement]:
    """Return the subset of ``records`` eligible as training ground truth.

    Both of these must hold for a record to be included:

    1. ``Achievement.annotation_status.<task> == AnnotationStatus.VERIFIED``.
    2. Every referenced ``label_id`` has
       ``LabelTaxonomy.status == TaxonomyStatus.APPROVED`` in the task's
       taxonomy.

    For :attr:`AnnotationTask.EXTRACTION_REVIEW` there are no labels,
    so the function always returns ``[]`` — extraction-review
    eligibility is not a classification concept.

    With the current all-draft taxonomies (Chunk 3 ships every label at
    ``status: draft``), this function returns ``[]`` by design.
    Promoting labels to ``approved`` is a separate human-review PR; it
    is not performed here.
    """
    if task == AnnotationTask.EXTRACTION_REVIEW:
        return []

    if task == AnnotationTask.PRIMARY_TYPE:
        if primary_taxonomy is None:
            raise ValueError("primary_taxonomy is required for task=primary_type")
        approved_labels = {
            e.label_id
            for e in primary_taxonomy
            if e.status == TaxonomyStatus.APPROVED
        }
        out: list[Achievement] = []
        for rec in records:
            if rec.annotation_status.primary_type != AnnotationStatus.VERIFIED:
                continue
            if rec.primary_type is None:
                continue
            if rec.primary_type in approved_labels:
                out.append(rec)
        return out

    if task == AnnotationTask.DOMAIN_TAGS:
        if domain_taxonomy is None:
            raise ValueError("domain_taxonomy is required for task=domain_tags")
        approved_labels = {
            e.label_id
            for e in domain_taxonomy
            if e.status == TaxonomyStatus.APPROVED
        }
        out = []
        for rec in records:
            if rec.annotation_status.domain_tags != AnnotationStatus.VERIFIED:
                continue
            if all(tag in approved_labels for tag in rec.domain_tags):
                out.append(rec)
        return out

    raise ValueError(f"unknown task: {task!r}")


def training_ready_subset(
    records: Iterable[Achievement],
    *,
    sources: Iterable[SourceRegistry],
    primary_taxonomy: Iterable[LabelTaxonomy] | None = None,
    domain_taxonomy: Iterable[LabelTaxonomy] | None = None,
    task: AnnotationTask,
) -> list[Achievement]:
    """Return records eligible as training data under source governance.

    Layers two extra source-governance checks on top of
    :func:`eligible_ground_truth`:

    * The record's ``source_id`` must belong to a ``SourceRegistry``
      entry with ``review_status == VERIFIED``, AND
    * that entry's ``license`` must not equal ``UNKNOWN``.

    Both conditions are **code-level** eligibility checks. They do
    **not** independently verify legal compliance. ``review_status ==
    VERIFIED`` is a human-set flag; the human reviewer is responsible
    for checking that the documented license / reuse terms are
    compatible with the source's ``intended_use`` (see
    ``hybrid_dataset/metadata/SOURCE_REGISTRATION_GUIDE.md``). This
    function trusts that flag; it does not re-verify compliance.

    Backward-compatibility: :func:`eligible_ground_truth` is unchanged
    and continues to work without source information. Existing
    callers of that function see no behavior change.

    Returns ``[]`` for :attr:`AnnotationTask.EXTRACTION_REVIEW` since
    extraction review has no classification labels.
    """
    eligible = eligible_ground_truth(
        records,
        primary_taxonomy=primary_taxonomy,
        domain_taxonomy=domain_taxonomy,
        task=task,
    )
    # The license sentinel comparison is case-insensitive. The schema's
    # ``license`` field is free text, so a reviewer could write
    # ``unknown``, ``Unknown``, or ``UNKNOWN`` and intend the same sentinel.
    # ``SOURCE_REGISTRATION_GUIDE.md`` recommends the canonical upper-case
    # form; the code additionally normalises here so a case-variant does
    # NOT quietly admit a record whose license was never reviewed.
    governed_source_ids: set[str] = {
        s.source_id
        for s in sources
        if s.review_status == ReviewStatus.VERIFIED
        and s.license.strip().upper() != UNKNOWN_LICENSE
    }
    return [r for r in eligible if r.source_id in governed_source_ids]
