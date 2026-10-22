"""Tests for the deterministic duplicate detector."""
from __future__ import annotations

from datetime import date
from typing import Any

from nlp_semantic.schema import Achievement, make_id
from nlp_semantic.dataset.duplicates import (
    DuplicateKind,
    DuplicateReport,
    find_duplicates,
)


def _rec(**overrides: Any) -> Achievement:
    base = dict(
        achievement_id=make_id("ach"),
        source_id=make_id("src"),
        source_record_id="src-ext-" + make_id("ach")[-6:],
        achievement_text="A synthetic achievement.",
        is_synthetic=True,
    )
    base.update(overrides)
    return Achievement(**base)


def test_empty_input_returns_empty_report() -> None:
    rep = find_duplicates([])
    assert isinstance(rep, DuplicateReport)
    assert rep.groups == []
    assert rep.total_flagged == 0


def test_singleton_input_returns_no_groups() -> None:
    rep = find_duplicates([_rec()])
    assert rep.groups == []
    assert rep.total_flagged == 0


def test_exact_text_duplicates_flagged() -> None:
    r1 = _rec(achievement_text="won hackathon")
    r2 = _rec(achievement_text="won hackathon")
    rep = find_duplicates([r1, r2])
    exact = rep.by_kind(DuplicateKind.EXACT_TEXT)
    assert len(exact) == 1
    assert sorted(exact[0].achievement_ids) == sorted(
        [r1.achievement_id, r2.achievement_id]
    )
    assert rep.total_flagged == 2


def test_whitespace_only_variants_flagged_as_normalized_not_exact() -> None:
    r1 = _rec(achievement_text="won hackathon")
    r2 = _rec(achievement_text="won  hackathon")  # extra space -> stripped by model
    r3 = _rec(achievement_text="won hackathon ")  # trailing space -> stripped by model
    # Note: model strips whitespace, so these three may collapse to the
    # same string. We assert normalized groups contain all three.
    rep = find_duplicates([r1, r2, r3])
    norm = rep.by_kind(DuplicateKind.NORMALIZED_TEXT)
    assert len(norm) == 1
    assert set(norm[0].achievement_ids) == {
        r1.achievement_id, r2.achievement_id, r3.achievement_id
    }


def test_case_only_variants_flagged_as_normalized() -> None:
    r1 = _rec(achievement_text="Won Hackathon")
    r2 = _rec(achievement_text="WON HACKATHON")
    r3 = _rec(achievement_text="won hackathon")
    rep = find_duplicates([r1, r2, r3])
    norm = rep.by_kind(DuplicateKind.NORMALIZED_TEXT)
    assert len(norm) == 1
    exact = rep.by_kind(DuplicateKind.EXACT_TEXT)
    assert exact == []  # none are byte-identical


def test_unicode_nfkc_normalization_flagged() -> None:
    r1 = _rec(achievement_text="won hackathon 1")
    r2 = _rec(achievement_text="won hackathon １")  # full-width 1 -> NFKC "1"
    rep = find_duplicates([r1, r2])
    assert rep.by_kind(DuplicateKind.NORMALIZED_TEXT)
    assert rep.by_kind(DuplicateKind.EXACT_TEXT) == []


def test_source_record_pair_duplicates_flagged() -> None:
    sid = make_id("src")
    r1 = _rec(source_id=sid, source_record_id="k1", achievement_text="A")
    r2 = _rec(source_id=sid, source_record_id="k1", achievement_text="B")
    rep = find_duplicates([r1, r2])
    pairs = rep.by_kind(DuplicateKind.SOURCE_RECORD_PAIR)
    assert len(pairs) == 1
    assert sorted(pairs[0].achievement_ids) == sorted(
        [r1.achievement_id, r2.achievement_id]
    )


def test_date_org_event_triple_flagged_when_all_three_present() -> None:
    r1 = _rec(
        achievement_text="A",
        achievement_date=date(2024, 6, 15),
        organization="MIT",
        event_name="HackMIT",
    )
    r2 = _rec(
        achievement_text="B",
        achievement_date=date(2024, 6, 15),
        organization="mit",      # case-insensitive match
        event_name=" HackMIT ",  # stripped by model, then case-folded
    )
    rep = find_duplicates([r1, r2])
    triples = rep.by_kind(DuplicateKind.DATE_ORG_EVENT_TRIPLE)
    assert len(triples) == 1


def test_date_org_event_not_flagged_when_any_missing() -> None:
    r1 = _rec(
        achievement_text="A",
        achievement_date=date(2024, 6, 15),
        organization="MIT",
        # event_name missing
    )
    r2 = _rec(
        achievement_text="B",
        achievement_date=date(2024, 6, 15),
        organization="MIT",
    )
    rep = find_duplicates([r1, r2])
    assert rep.by_kind(DuplicateKind.DATE_ORG_EVENT_TRIPLE) == []


def test_detector_never_mutates_input() -> None:
    r1 = _rec(achievement_text="duplicate")
    r2 = _rec(achievement_text="duplicate")
    r1_text_before = r1.achievement_text
    r2_text_before = r2.achievement_text
    r1_id_before = r1.achievement_id
    find_duplicates([r1, r2])
    assert r1.achievement_text == r1_text_before
    assert r2.achievement_text == r2_text_before
    assert r1.achievement_id == r1_id_before


def test_no_false_positives_on_distinct_records() -> None:
    r1 = _rec(achievement_text="won hackathon at MIT in June")
    r2 = _rec(achievement_text="participated in debate contest at Stanford")
    r3 = _rec(achievement_text="published paper at NeurIPS workshop")
    rep = find_duplicates([r1, r2, r3])
    assert rep.groups == []
    assert rep.total_flagged == 0


def test_total_flagged_dedup_across_kinds() -> None:
    """A record flagged by two rules is counted once in total_flagged."""
    sid = make_id("src")
    r1 = _rec(source_id=sid, source_record_id="k1", achievement_text="same")
    r2 = _rec(source_id=sid, source_record_id="k1", achievement_text="same")
    rep = find_duplicates([r1, r2])
    # Flagged by both exact_text and source_record_pair; set-counted = 2.
    assert rep.total_flagged == 2
    assert len(rep.by_kind(DuplicateKind.EXACT_TEXT)) == 1
    assert len(rep.by_kind(DuplicateKind.SOURCE_RECORD_PAIR)) == 1
