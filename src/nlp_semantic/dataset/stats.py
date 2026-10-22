"""Dataset statistics and class-distribution reporting.

Pure functions over a loaded record list. Output is JSON-serializable
so the CLI can emit it unchanged. Pandas is deliberately not used
here: the counts are small (≤ hundreds of records, ≤ 14 primary types,
≤ 10 domain tags), stdlib ``Counter`` is clearer, and avoiding pandas
on this hot path keeps the stats module importable even in restricted
environments.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from nlp_semantic.schema import Achievement


_NONE_KEY = "<none>"


@dataclass(frozen=True)
class DatasetStatsReport:
    total_records: int
    synthetic_count: int
    real_count: int

    primary_type_counts: dict[str, int] = field(default_factory=dict)
    primary_type_status_counts: dict[str, int] = field(default_factory=dict)

    domain_tag_counts: dict[str, int] = field(default_factory=dict)
    domain_tag_status_counts: dict[str, int] = field(default_factory=dict)
    records_with_no_domain_tags: int = 0

    per_source_counts: dict[str, int] = field(default_factory=dict)
    cooccurrence: dict[str, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Flat, JSON-serializable view suitable for the CLI."""
        return {
            "total_records": self.total_records,
            "synthetic_count": self.synthetic_count,
            "real_count": self.real_count,
            "primary_type_counts": dict(self.primary_type_counts),
            "primary_type_status_counts": dict(self.primary_type_status_counts),
            "domain_tag_counts": dict(self.domain_tag_counts),
            "domain_tag_status_counts": dict(self.domain_tag_status_counts),
            "records_with_no_domain_tags": self.records_with_no_domain_tags,
            "per_source_counts": dict(self.per_source_counts),
            "cooccurrence": {k: dict(v) for k, v in self.cooccurrence.items()},
        }


def _sorted_counter(c: Counter) -> dict[str, int]:
    """Sort by (-count, key) so top classes come first with stable tie order."""
    return {k: v for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))}


def compute_stats(records: Iterable[Achievement]) -> DatasetStatsReport:
    """Compute a :class:`DatasetStatsReport` from the loaded records.

    No cross-record validation is performed here (that is the
    validator's job). An empty input returns a zeroed report.
    """
    records_list = list(records)
    total = len(records_list)

    synthetic_count = sum(1 for r in records_list if r.is_synthetic)
    real_count = total - synthetic_count

    primary_counter: Counter[str] = Counter()
    primary_status_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    domain_status_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    records_with_no_domain = 0
    cooccurrence: dict[str, dict[str, int]] = {}

    for rec in records_list:
        pt_key = rec.primary_type if rec.primary_type is not None else _NONE_KEY
        primary_counter[pt_key] += 1
        primary_status_counter[rec.annotation_status.primary_type.value] += 1

        if rec.domain_tags:
            for tag in rec.domain_tags:
                domain_counter[tag] += 1
                cooccurrence.setdefault(pt_key, {}).setdefault(tag, 0)
                cooccurrence[pt_key][tag] += 1
        else:
            records_with_no_domain += 1

        domain_status_counter[rec.annotation_status.domain_tags.value] += 1
        source_counter[rec.source_id] += 1

    return DatasetStatsReport(
        total_records=total,
        synthetic_count=synthetic_count,
        real_count=real_count,
        primary_type_counts=_sorted_counter(primary_counter),
        primary_type_status_counts=_sorted_counter(primary_status_counter),
        domain_tag_counts=_sorted_counter(domain_counter),
        domain_tag_status_counts=_sorted_counter(domain_status_counter),
        records_with_no_domain_tags=records_with_no_domain,
        per_source_counts=_sorted_counter(source_counter),
        cooccurrence={
            pt: {dt: cnt for dt, cnt in sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))}
            for pt, d in sorted(cooccurrence.items())
        },
    )
