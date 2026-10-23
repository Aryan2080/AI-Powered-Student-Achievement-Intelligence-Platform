"""Tests for the dataset YAML batch loader."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from nlp_semantic.schema import make_id
from nlp_semantic.dataset.loader import (
    DatasetError,
    DatasetLoadReport,
    load_annotations,
    load_dataset,
    load_records,
    record_ids,
)

from tests.dataset.conftest import REPO_ROOT, annotation_dict, record_dict, write_yaml


# ---- shipped dataset directory (empty) ---------------------------------------


def test_shipped_records_dir_loads_sih_pilot() -> None:
    """Shipped records/ carries the Chunk 7.4-A SIH pilot batch.

    The pilot ships with 7 team-level records, all citing the Chunk
    7.3-A.5 source and all tentatively labelled `lbl_hackathon` with
    `annotation_status.primary_type: draft`. Source governance remains
    conservative (UNKNOWN license, unreviewed), so these records are
    not training-ready; they are present for workflow verification.
    """
    records = load_records(REPO_ROOT / "hybrid_dataset")
    assert len(records) == 7
    source_ids_seen = {r.source_id for r in records}
    assert source_ids_seen == {"src_5a8a2998d6f44055a42dcfd8991e4d12"}
    primary_types = {r.primary_type for r in records}
    assert primary_types == {"lbl_hackathon"}
    primary_statuses = {r.annotation_status.primary_type.value for r in records}
    assert primary_statuses == {"draft"}


def test_shipped_annotations_dir_loads_empty() -> None:
    assert load_annotations(REPO_ROOT / "hybrid_dataset") == []


def test_shipped_dataset_load_report_contains_sih_pilot() -> None:
    """Report reflects the Chunk 7.4-A pilot: 7 records in >=1 batch file;
    annotations/ still empty.
    """
    report = load_dataset(REPO_ROOT / "hybrid_dataset")
    assert isinstance(report, DatasetLoadReport)
    assert len(report.records) == 7
    assert report.annotations == []
    assert len(report.record_files) >= 1
    assert any(
        "batch_01_sih2024.yaml" in rf for rf in report.record_files
    )
    assert report.annotation_files == []


# ---- happy paths -------------------------------------------------------------


def test_single_record_batch_loads(dataset_root: Path) -> None:
    r = record_dict(achievement_text="single-record-batch")
    write_yaml(dataset_root / "dataset" / "records" / "batch_01.yaml", [r])
    records = load_records(dataset_root)
    assert len(records) == 1
    assert records[0].achievement_text == "single-record-batch"


def test_multiple_batches_concatenate_in_filename_order(dataset_root: Path) -> None:
    r1 = record_dict(achievement_text="first")
    r2 = record_dict(achievement_text="second")
    r3 = record_dict(achievement_text="third")
    write_yaml(dataset_root / "dataset" / "records" / "batch_01.yaml", [r1])
    write_yaml(dataset_root / "dataset" / "records" / "batch_02.yaml", [r2])
    write_yaml(dataset_root / "dataset" / "records" / "batch_03.yaml", [r3])
    records = load_records(dataset_root)
    assert [r.achievement_text for r in records] == ["first", "second", "third"]


def test_non_batch_yaml_files_are_ignored(dataset_root: Path) -> None:
    r = record_dict()
    write_yaml(dataset_root / "dataset" / "records" / "batch_01.yaml", [r])
    # README-ish YAML sitting next to batches should be skipped (not glob'd).
    write_yaml(
        dataset_root / "dataset" / "records" / "notes.yaml",
        None,
        raw="this is intentionally not a list\n",
    )
    assert len(load_records(dataset_root)) == 1


# ---- shape failures ---------------------------------------------------------


def test_top_level_not_list_rejected(dataset_root: Path) -> None:
    write_yaml(
        dataset_root / "dataset" / "records" / "batch_01.yaml",
        None,
        raw="achievement_id: ach_abc\n",
    )
    with pytest.raises(DatasetError, match="top-level YAML must be a list"):
        load_records(dataset_root)


def test_entry_not_mapping_rejected(dataset_root: Path) -> None:
    write_yaml(
        dataset_root / "dataset" / "records" / "batch_01.yaml",
        None,
        raw="- just_a_string\n",
    )
    with pytest.raises(DatasetError, match="must be a mapping"):
        load_records(dataset_root)


def test_empty_yaml_returns_empty_list(dataset_root: Path) -> None:
    write_yaml(dataset_root / "dataset" / "records" / "batch_01.yaml", None, raw="")
    assert load_records(dataset_root) == []


def test_per_entry_bad_id_raises_validation_error(dataset_root: Path) -> None:
    r = record_dict(achievement_id="src_" + "a" * 32)  # wrong prefix
    write_yaml(dataset_root / "dataset" / "records" / "batch_01.yaml", [r])
    with pytest.raises(ValidationError):
        load_records(dataset_root)


def test_per_entry_extra_field_rejected(dataset_root: Path) -> None:
    r = record_dict(mystery_field="x")
    write_yaml(dataset_root / "dataset" / "records" / "batch_01.yaml", [r])
    with pytest.raises(ValidationError):
        load_records(dataset_root)


# ---- duplicate detection ----------------------------------------------------


def test_duplicate_achievement_id_within_file_rejected(dataset_root: Path) -> None:
    aid = make_id("ach")
    r1 = record_dict(achievement_id=aid, source_record_id="a")
    r2 = record_dict(achievement_id=aid, source_record_id="b")
    write_yaml(dataset_root / "dataset" / "records" / "batch_01.yaml", [r1, r2])
    with pytest.raises(DatasetError, match="duplicate achievement_id"):
        load_records(dataset_root)


def test_duplicate_achievement_id_across_batches_rejected(dataset_root: Path) -> None:
    aid = make_id("ach")
    r1 = record_dict(achievement_id=aid, source_record_id="first")
    r2 = record_dict(achievement_id=aid, source_record_id="second")
    write_yaml(dataset_root / "dataset" / "records" / "batch_01.yaml", [r1])
    write_yaml(dataset_root / "dataset" / "records" / "batch_02.yaml", [r2])
    with pytest.raises(DatasetError, match="duplicate achievement_id"):
        load_records(dataset_root)


# ---- annotations loader -----------------------------------------------------


def test_annotations_directory_absent_returns_empty(dataset_root: Path) -> None:
    # Remove the pre-created annotations/ dir to prove absence is OK.
    (dataset_root / "dataset" / "annotations").rmdir()
    assert load_annotations(dataset_root) == []


def test_annotation_batch_loads(dataset_root: Path) -> None:
    a = annotation_dict()
    write_yaml(dataset_root / "dataset" / "annotations" / "batch_01.yaml", [a])
    anns = load_annotations(dataset_root)
    assert len(anns) == 1
    assert anns[0].annotator == "labeler_001"


def test_duplicate_annotation_id_across_batches_rejected(dataset_root: Path) -> None:
    annid = make_id("ann")
    a1 = annotation_dict(annotation_id=annid)
    a2 = annotation_dict(annotation_id=annid)
    write_yaml(dataset_root / "dataset" / "annotations" / "batch_01.yaml", [a1])
    write_yaml(dataset_root / "dataset" / "annotations" / "batch_02.yaml", [a2])
    with pytest.raises(DatasetError, match="duplicate annotation_id"):
        load_annotations(dataset_root)


# ---- load_dataset -----------------------------------------------------------


def test_load_dataset_report_counts(dataset_root: Path) -> None:
    r1 = record_dict()
    r2 = record_dict()
    a1 = annotation_dict()
    write_yaml(dataset_root / "dataset" / "records" / "batch_01.yaml", [r1, r2])
    write_yaml(dataset_root / "dataset" / "annotations" / "batch_01.yaml", [a1])
    report = load_dataset(dataset_root)
    assert len(report.records) == 2
    assert len(report.annotations) == 1
    assert len(report.record_files) == 1
    assert len(report.annotation_files) == 1
    # Forward-slash normalization on Windows.
    assert all("\\" not in p for p in report.record_files + report.annotation_files)


def test_load_dataset_root_must_exist(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "does_not_exist")


def test_load_dataset_root_must_be_a_directory(tmp_path: Path) -> None:
    f = tmp_path / "not_a_dir"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        load_dataset(f)


# ---- helper ------------------------------------------------------------------


def test_record_ids_helper(dataset_root: Path) -> None:
    r1 = record_dict()
    r2 = record_dict()
    write_yaml(dataset_root / "dataset" / "records" / "batch_01.yaml", [r1, r2])
    records = load_records(dataset_root)
    assert record_ids(records) == {r1["achievement_id"], r2["achievement_id"]}
    assert record_ids([]) == set()
