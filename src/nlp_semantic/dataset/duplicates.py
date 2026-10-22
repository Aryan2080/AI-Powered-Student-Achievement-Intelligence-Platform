"""Deterministic duplicate detection for curated records.

Chunk 5 implements only exact / normalized-text / FK-triple duplicates.
Semantic (embedding-based) duplicate detection is deferred.

The detector **flags** suspicious groups for human review. It never
deletes, merges, or mutates records. The caller decides what to do.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field

from nlp_semantic.schema import Achievement


_WHITESPACE_RE = re.compile(r"\s+")


class DuplicateKind:
    """Enum-ish strings naming the detector rules.

    Kept as string constants (not a true Enum) so JSON serialization is
    trivial and callers can grep for the exact string.
    """

    EXACT_TEXT = "exact_text"
    NORMALIZED_TEXT = "normalized_text"
    SOURCE_RECORD_PAIR = "source_record_pair"
    DATE_ORG_EVENT_TRIPLE = "date_org_event_triple"


@dataclass(frozen=True)
class DuplicateGroup:
    """One group of records that collided on one detector rule."""

    kind: str                       # see DuplicateKind
    key: str                        # human-readable collision key
    achievement_ids: list[str]


@dataclass(frozen=True)
class DuplicateReport:
    """Return value of :func:`find_duplicates`.

    Each group lists at least two ``achievement_id`` values that
    collided on one rule. Groups are kind-grouped so downstream review
    can address each rule separately. No records are modified.
    """

    groups: list[DuplicateGroup] = field(default_factory=list)
    total_flagged: int = 0

    def by_kind(self, kind: str) -> list[DuplicateGroup]:
        return [g for g in self.groups if g.kind == kind]


def _normalize_text(text: str) -> str:
    """Lowercase + NFKC-normalize + collapse interior whitespace + strip."""
    # NFKC resolves compatibility codepoints (e.g. full-width digits).
    nfkc = unicodedata.normalize("NFKC", text)
    collapsed = _WHITESPACE_RE.sub(" ", nfkc).strip()
    return collapsed.casefold()


def find_duplicates(records: Iterable[Achievement]) -> DuplicateReport:
    """Return a :class:`DuplicateReport` naming all collision groups.

    Four deterministic rules are applied; each produces its own groups.
    A single record may appear in multiple groups across different
    rules.

    * ``exact_text`` — identical ``achievement_text`` strings (no
      normalization). Catches literal copy-paste.
    * ``normalized_text`` — identical after NFKC, interior-whitespace
      collapse, and case folding. Catches whitespace-only or
      case-only variants and is a superset of ``exact_text``; groups
      are still reported separately so reviewers see both signals.
    * ``source_record_pair`` — identical ``(source_id,
      source_record_id)`` across different ``achievement_id`` values.
      This duplicates the validator check and is included so the
      duplicate report is self-contained; callers that already ran
      ``validate_dataset`` can ignore this kind.
    * ``date_org_event_triple`` — identical ``(achievement_date,
      organization, event_name)`` triple when none of the three are
      ``None`` / empty. Flags "same event, same org, same date" entries
      that may be the same achievement under different sources.

    Chunk 5 does not perform semantic duplicate detection (embedding
    cosine similarity, Jaccard shingles, etc.); that requires
    embeddings and is a later chunk.
    """
    records_list = list(records)
    groups: list[DuplicateGroup] = []
    flagged: set[str] = set()

    def _emit(kind: str, buckets: dict[str, list[str]]) -> None:
        for key, aids in buckets.items():
            if len(aids) > 1:
                groups.append(DuplicateGroup(kind=kind, key=key, achievement_ids=aids))
                flagged.update(aids)

    exact_buckets: dict[str, list[str]] = {}
    norm_buckets: dict[str, list[str]] = {}
    pair_buckets: dict[str, list[str]] = {}
    triple_buckets: dict[str, list[str]] = {}

    for rec in records_list:
        exact_buckets.setdefault(rec.achievement_text, []).append(rec.achievement_id)
        norm_key = _normalize_text(rec.achievement_text)
        norm_buckets.setdefault(norm_key, []).append(rec.achievement_id)

        pair_key = f"{rec.source_id}|{rec.source_record_id}"
        pair_buckets.setdefault(pair_key, []).append(rec.achievement_id)

        if (
            rec.achievement_date is not None
            and rec.organization
            and rec.event_name
        ):
            triple_key = (
                f"{rec.achievement_date.isoformat()}|"
                f"{rec.organization.strip().casefold()}|"
                f"{rec.event_name.strip().casefold()}"
            )
            triple_buckets.setdefault(triple_key, []).append(rec.achievement_id)

    _emit(DuplicateKind.EXACT_TEXT, exact_buckets)
    _emit(DuplicateKind.NORMALIZED_TEXT, norm_buckets)
    _emit(DuplicateKind.SOURCE_RECORD_PAIR, pair_buckets)
    _emit(DuplicateKind.DATE_ORG_EVENT_TRIPLE, triple_buckets)

    return DuplicateReport(groups=groups, total_flagged=len(flagged))
