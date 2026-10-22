"""Inter-annotator agreement (IAA) for dual-reviewed records.

Pure functions over :class:`Annotation` + :class:`Achievement` lists.
No I/O, no side effects. Agreement numbers are **advisory** and must
not drive any automatic status change, taxonomy promotion, or
training-readiness certification; the CLI's readiness report prints a
standing disclaimer to that effect.

Design decisions (per Chunk 6 approval):

* **Same-annotator collapse.** The Annotation schema does not forbid
  multiple rows for the same ``(achievement_id, task, annotator)``
  triple. Within each triple we keep the row with the greatest
  ``created_at`` (ties broken by ``annotation_id`` for determinism)
  and report the collapsed count. Collapsed rows are NOT counted as
  independent reviewers.
* **Review-status filtering.** Rows with
  :attr:`AnnotationStatus.REJECTED` are excluded entirely (a
  withdrawn label is not an opinion).
  :attr:`AnnotationStatus.CONFLICTED` rows are included — the label
  still represents the annotator's position — and their count is
  reported separately.
* **Independent reviewers.** Only *distinct annotator pseudonyms*
  count. One annotator submitting twice (which `created_at` collapse
  reduces to one row) does not constitute independent review.
* **Undefined kappa.** Cohen's kappa is undefined when no pairs are
  observed, or when the expected-by-chance agreement equals 1 (every
  annotator used a single class). In those cases we return ``None``;
  we never substitute 1.0.
* **Empty-set Jaccard.** For :attr:`AnnotationTask.DOMAIN_TAGS` we
  treat ``jaccard(set(), set()) == 1.0`` because both annotators
  independently agree that no tags apply — a legitimate schema state
  (``[]`` + ``VERIFIED`` means "reviewer confirmed none apply").
  Documented in-code and in the annotation guidelines.
* **Pseudonym-only output.** :class:`Disagreement` carries only the
  annotator pseudonyms already in the Annotation row; no real-name
  mapping is read, built, or exposed.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from nlp_semantic.schema import Annotation, AnnotationStatus, AnnotationTask


@dataclass(frozen=True)
class Disagreement:
    """One record with ≥ 2 independent annotators who disagreed.

    ``annotators_and_labels`` is a sorted list of
    ``(annotator_pseudonym, label_ids_sorted)`` tuples. Only the
    annotator's existing pseudonym is used; no identity resolution is
    performed. All entries are post-collapse (one entry per distinct
    annotator pseudonym).
    """

    achievement_id: str
    task: AnnotationTask
    annotators_and_labels: list[tuple[str, list[str]]]


@dataclass(frozen=True)
class AgreementReport:
    """IAA summary for one annotation task.

    ``cohen_kappa`` is reported only for :attr:`AnnotationTask.PRIMARY_TYPE`
    and is ``None`` when the statistic is mathematically undefined.
    ``mean_jaccard`` is reported only for
    :attr:`AnnotationTask.DOMAIN_TAGS` and is ``None`` when no pairs
    exist. Both metrics are advisory; no threshold or interpretation
    is baked into this module.
    """

    task: AnnotationTask
    pairs_evaluated: int
    records_eligible_for_agreement: int
    records_single_annotator_only: int
    records_with_rejected_only: int
    self_reannotation_count: int
    conflict_count: int
    exact_agreement_rate: float | None
    cohen_kappa: float | None
    mean_jaccard: float | None
    disagreements: list[Disagreement] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable view (used by the readiness CLI)."""
        return {
            "task": self.task.value,
            "pairs_evaluated": self.pairs_evaluated,
            "records_eligible_for_agreement": self.records_eligible_for_agreement,
            "records_single_annotator_only": self.records_single_annotator_only,
            "records_with_rejected_only": self.records_with_rejected_only,
            "self_reannotation_count": self.self_reannotation_count,
            "conflict_count": self.conflict_count,
            "exact_agreement_rate": self.exact_agreement_rate,
            "cohen_kappa": self.cohen_kappa,
            "mean_jaccard": self.mean_jaccard,
            "disagreements": [
                {
                    "achievement_id": d.achievement_id,
                    "task": d.task.value,
                    "annotators_and_labels": [
                        {"annotator": a, "label_ids": list(labels)}
                        for a, labels in d.annotators_and_labels
                    ],
                }
                for d in self.disagreements
            ],
        }


# ---- metric helpers ---------------------------------------------------------


def cohen_kappa_single_label(
    pairs: list[tuple[str, str]],
) -> float | None:
    """Aggregated pairwise Cohen's kappa on a list of (label_a, label_b).

    Returns ``None`` when ``pairs`` is empty or expected agreement is 1
    (division by zero). Never returns a spurious 1.0 for the
    all-same-label case; that collapses to the undefined denominator.
    """
    n = len(pairs)
    if n == 0:
        return None
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / n
    freq_a: Counter[str] = Counter(a for a, _ in pairs)
    freq_b: Counter[str] = Counter(b for _, b in pairs)
    labels = set(freq_a) | set(freq_b)
    pe = sum(freq_a[l] * freq_b[l] for l in labels) / (n * n)
    denom = 1.0 - pe
    if denom == 0.0:
        return None
    return (po - pe) / denom


def jaccard_multilabel(a: set[str], b: set[str]) -> float:
    """Jaccard similarity on two label sets.

    By documented convention (Chunk 6), ``jaccard(set(), set()) == 1.0``:
    both annotators independently agree that no tags apply. For all
    other inputs, returns ``|a ∩ b| / |a ∪ b|``.
    """
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union


# ---- grouping / collapse ---------------------------------------------------


def _collapse_latest_per_annotator(
    annotations: list[Annotation],
) -> tuple[list[Annotation], int]:
    """Within each (achievement_id, task, annotator) keep latest-by-created_at.

    Returns the kept annotations and the number of rows collapsed
    (dropped). Deterministic: ties on ``created_at`` are broken by
    ``annotation_id``.
    """
    buckets: dict[tuple[str, AnnotationTask, str], list[Annotation]] = {}
    for ann in annotations:
        buckets.setdefault(
            (ann.achievement_id, ann.task, ann.annotator), []
        ).append(ann)

    kept: list[Annotation] = []
    dropped = 0
    for anns in buckets.values():
        if len(anns) == 1:
            kept.append(anns[0])
            continue
        # Sort by (created_at, annotation_id) ascending; keep the last.
        anns_sorted = sorted(anns, key=lambda a: (a.created_at, a.annotation_id))
        kept.append(anns_sorted[-1])
        dropped += len(anns) - 1
    return kept, dropped


def _filter_for_task(
    annotations: Iterable[Annotation],
    task: AnnotationTask,
) -> tuple[list[Annotation], int]:
    """Keep annotations for ``task`` whose review_status is not REJECTED.

    Returns (kept, rejected_count). CONFLICTED is NOT filtered here —
    it is reported separately.
    """
    kept: list[Annotation] = []
    rejected = 0
    for ann in annotations:
        if ann.task != task:
            continue
        if ann.review_status == AnnotationStatus.REJECTED:
            rejected += 1
            continue
        kept.append(ann)
    return kept, rejected


# ---- public API ------------------------------------------------------------


def compute_agreement(
    annotations: Iterable[Annotation],
    *,
    task: AnnotationTask,
) -> AgreementReport:
    """Compute an :class:`AgreementReport` for one annotation task.

    EXTRACTION_REVIEW has no classification labels; the report
    returned for that task carries zeroed/None metrics and an empty
    disagreement list.
    """
    all_task_annotations = list(annotations)

    if task == AnnotationTask.EXTRACTION_REVIEW:
        # No labels on this task; agreement is not meaningful.
        return AgreementReport(
            task=task,
            pairs_evaluated=0,
            records_eligible_for_agreement=0,
            records_single_annotator_only=0,
            records_with_rejected_only=0,
            self_reannotation_count=0,
            conflict_count=0,
            exact_agreement_rate=None,
            cohen_kappa=None,
            mean_jaccard=None,
        )

    for_task, _rejected_dropped = _filter_for_task(all_task_annotations, task)

    # records with ONLY rejected annotations should still be reportable.
    records_with_any_task_annotation = {
        a.achievement_id for a in all_task_annotations if a.task == task
    }
    records_with_non_rejected = {a.achievement_id for a in for_task}
    records_with_rejected_only = len(
        records_with_any_task_annotation - records_with_non_rejected
    )

    collapsed, self_reannotation = _collapse_latest_per_annotator(for_task)
    conflicts = sum(
        1 for a in collapsed if a.review_status == AnnotationStatus.CONFLICTED
    )

    # Group by achievement_id -> list of (annotator, labels).
    per_record: dict[str, list[tuple[str, list[str]]]] = {}
    for ann in collapsed:
        per_record.setdefault(ann.achievement_id, []).append(
            (ann.annotator, list(ann.label_ids))
        )

    single_annotator_only = 0
    pairs_singlelabel: list[tuple[str, str]] = []
    pairs_multilabel_jaccards: list[float] = []
    pairs_multilabel_exacts: list[bool] = []
    pairs_singlelabel_exacts: list[bool] = []
    records_eligible = 0
    disagreements: list[Disagreement] = []

    for aid, entries in per_record.items():
        # Distinct-annotator check (post-collapse there is at most one row per
        # annotator, so this is just len > 1).
        if len({a for a, _ in entries}) < 2:
            single_annotator_only += 1
            continue
        records_eligible += 1

        # Deterministic pair enumeration: sort by annotator pseudonym.
        entries_sorted = sorted(entries, key=lambda e: e[0])
        disagreed_here = False
        for (ann_a, labels_a), (ann_b, labels_b) in combinations(entries_sorted, 2):
            if task == AnnotationTask.PRIMARY_TYPE:
                # Schema invariant: PRIMARY_TYPE arity is exactly 1.
                la = labels_a[0] if labels_a else ""
                lb = labels_b[0] if labels_b else ""
                pairs_singlelabel.append((la, lb))
                pairs_singlelabel_exacts.append(la == lb)
                if la != lb:
                    disagreed_here = True
            elif task == AnnotationTask.DOMAIN_TAGS:
                set_a = set(labels_a)
                set_b = set(labels_b)
                pairs_multilabel_jaccards.append(jaccard_multilabel(set_a, set_b))
                exact = set_a == set_b
                pairs_multilabel_exacts.append(exact)
                if not exact:
                    disagreed_here = True

        if disagreed_here:
            disagreements.append(
                Disagreement(
                    achievement_id=aid,
                    task=task,
                    annotators_and_labels=[
                        (a, sorted(labels)) for a, labels in entries_sorted
                    ],
                )
            )

    pairs_evaluated = (
        len(pairs_singlelabel) if task == AnnotationTask.PRIMARY_TYPE
        else len(pairs_multilabel_jaccards)
    )

    if task == AnnotationTask.PRIMARY_TYPE:
        exact_rate = (
            sum(pairs_singlelabel_exacts) / len(pairs_singlelabel_exacts)
            if pairs_singlelabel_exacts
            else None
        )
        kappa = cohen_kappa_single_label(pairs_singlelabel)
        mean_j = None
    else:  # DOMAIN_TAGS
        exact_rate = (
            sum(pairs_multilabel_exacts) / len(pairs_multilabel_exacts)
            if pairs_multilabel_exacts
            else None
        )
        kappa = None
        mean_j = (
            sum(pairs_multilabel_jaccards) / len(pairs_multilabel_jaccards)
            if pairs_multilabel_jaccards
            else None
        )

    return AgreementReport(
        task=task,
        pairs_evaluated=pairs_evaluated,
        records_eligible_for_agreement=records_eligible,
        records_single_annotator_only=single_annotator_only,
        records_with_rejected_only=records_with_rejected_only,
        self_reannotation_count=self_reannotation,
        conflict_count=conflicts,
        exact_agreement_rate=exact_rate,
        cohen_kappa=kappa,
        mean_jaccard=mean_j,
        disagreements=disagreements,
    )


def find_disagreements(
    annotations: Iterable[Annotation],
    *,
    task: AnnotationTask,
) -> list[Disagreement]:
    """Convenience: return the disagreement list that
    :func:`compute_agreement` would populate for ``task``.
    """
    return compute_agreement(annotations, task=task).disagreements
