"""Tests for the dataset CLI subcommands (validate / stats / split)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from nlp_semantic.schema import make_id

from tests.dataset.conftest import REPO_ROOT


def _cli_env() -> dict[str, str]:
    env = dict(os.environ)
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "nlp_semantic.dataset.cli", *args],
        capture_output=True,
        text=True,
        env=_cli_env(),
    )


def _dataset_root_with_sources(tmp_path: Path, *records: dict) -> Path:
    """Build a minimal dataset root with sources.yaml + taxonomies + records."""
    root = tmp_path / "ds"
    (root / "dataset" / "records").mkdir(parents=True)
    (root / "dataset" / "annotations").mkdir(parents=True)
    (root / "metadata").mkdir(parents=True)
    (root / "labels").mkdir(parents=True)

    # Minimum sources.yaml: register every source referenced in records.
    source_ids = {r["source_id"] for r in records}
    sources = [
        {
            "source_id": sid,
            "source_name": "Synthetic Source",
            "source_url": "https://example.org/x",
            "license": "CC-BY-4.0",
            "collection_date": date.today().isoformat(),
            "intended_use": "primary_type_training",
            "review_status": "verified",
            "is_synthetic": True,
        }
        for sid in sorted(source_ids)
    ]
    (root / "metadata" / "sources.yaml").write_text(
        yaml.safe_dump(sources, sort_keys=False), encoding="utf-8"
    )
    # Empty taxonomies are fine; just make the files exist and parse.
    (root / "labels" / "primary_taxonomy.yaml").write_text("[]\n", encoding="utf-8")
    (root / "labels" / "domain_tags.yaml").write_text("[]\n", encoding="utf-8")

    if records:
        (root / "dataset" / "records" / "batch_01.yaml").write_text(
            yaml.safe_dump(list(records), sort_keys=False), encoding="utf-8"
        )
    return root


def _rec(**overrides) -> dict:
    base = dict(
        achievement_id=make_id("ach"),
        source_id=make_id("src"),
        source_record_id="src-ext-" + make_id("ach")[-6:],
        achievement_text="A record.",
        is_synthetic=False,
    )
    base.update(overrides)
    return base


# ---- usage errors -----------------------------------------------------------


def test_cli_no_subcommand_errors_with_exit_2() -> None:
    proc = _run([])
    assert proc.returncode == 2


def test_cli_unknown_subcommand_errors_with_exit_2() -> None:
    proc = _run(["bogus", "./nowhere"])
    assert proc.returncode == 2


# ---- validate ---------------------------------------------------------------


def test_cli_validate_happy_path_on_shipped_dataset() -> None:
    """The shipped dataset is empty but structurally valid."""
    proc = _run(["validate", str(REPO_ROOT / "hybrid_dataset")])
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["load"]["records"] == 0
    assert data["validation"]["is_valid"] is True
    assert "ok" in proc.stderr


def test_cli_validate_on_missing_root_exits_1(tmp_path: Path) -> None:
    proc = _run(["validate", str(tmp_path / "nope")])
    assert proc.returncode == 1
    assert "FileNotFoundError" in proc.stderr


def test_cli_validate_fatal_findings_exit_1(tmp_path: Path) -> None:
    """A record pointing at an unregistered source_id must trip exit=1."""
    rec = _rec()
    # Register a DIFFERENT source so the record's source_id is unknown.
    rogue = _rec()
    root = _dataset_root_with_sources(tmp_path, rogue)  # registers rogue
    # Now write our actual batch containing `rec` whose source is NOT registered.
    (root / "dataset" / "records" / "batch_01.yaml").write_text(
        yaml.safe_dump([rec], sort_keys=False), encoding="utf-8"
    )
    proc = _run(["validate", str(root)])
    assert proc.returncode == 1
    assert "fatal" in proc.stderr


# ---- stats ------------------------------------------------------------------


def test_cli_stats_on_shipped_dataset_exits_0() -> None:
    proc = _run(["stats", str(REPO_ROOT / "hybrid_dataset")])
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["total_records"] == 0
    assert "records=0" in proc.stderr


def test_cli_stats_counts_small_dataset(tmp_path: Path) -> None:
    sid = make_id("src")
    recs = [_rec(source_id=sid, source_record_id=str(i)) for i in range(5)]
    root = _dataset_root_with_sources(tmp_path, *recs)
    proc = _run(["stats", str(root)])
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["total_records"] == 5


# ---- split ------------------------------------------------------------------


def test_cli_split_writes_files_and_manifest(tmp_path: Path) -> None:
    # 6 source groups × 2 records each = 12 real records.
    recs = []
    for _ in range(6):
        sid = make_id("src")
        for i in range(2):
            recs.append(_rec(source_id=sid, source_record_id=str(i)))
    root = _dataset_root_with_sources(tmp_path, *recs)
    proc = _run(["split", str(root), "--seed", "42"])
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["seed"] == 42
    splits_dir = root / "processed" / "splits"
    assert (splits_dir / "train.jsonl").exists()
    assert (splits_dir / "val.jsonl").exists()
    assert (splits_dir / "test.jsonl").exists()
    assert (splits_dir / "split_manifest.json").exists()


def test_cli_split_bad_ratio_syntax_exits_2(tmp_path: Path) -> None:
    root = _dataset_root_with_sources(tmp_path)
    proc = _run(["split", str(root), "--ratios", "train:0.7,val:0.3"])
    assert proc.returncode == 2  # argparse rejects bad --ratios syntax


def test_cli_split_bad_ratio_sum_exits_1(tmp_path: Path) -> None:
    root = _dataset_root_with_sources(tmp_path)
    proc = _run(["split", str(root), "--ratios", "train=0.5,val=0.3,test=0.1"])
    assert proc.returncode == 1
    assert "SplitFeasibilityError" in proc.stderr


def test_cli_split_include_synthetic_flag(tmp_path: Path) -> None:
    sid1 = make_id("src")
    sid2 = make_id("src")
    recs = (
        [_rec(source_id=sid1, source_record_id=str(i), is_synthetic=False) for i in range(3)]
        + [_rec(source_id=sid2, source_record_id=str(i), is_synthetic=True) for i in range(3)]
    )
    root = _dataset_root_with_sources(tmp_path, *recs)
    proc = _run(["split", str(root), "--seed", "0", "--include-synthetic"])
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    total = sum(data["actual_sizes"].values())
    assert total == 6
    assert data["excluded_synthetic_count"] == 0


# ---- readiness --------------------------------------------------------------


def test_cli_readiness_on_shipped_dataset_completes_and_reports_not_ready() -> None:
    """Shipped dataset: no sources, no records, all labels draft.

    Default mode must exit 0 (assessment completed) even though
    is_training_ready is False.
    """
    proc = _run(["readiness", str(REPO_ROOT / "hybrid_dataset")])
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["assessment_status"] == "completed"
    assert data["structurally_valid"] is True
    assert data["approved_label_count"]["primary_type"] == 0
    assert data["approved_label_count"]["domain_tags"] == 0
    assert data["is_training_ready"]["primary_type"] is False
    assert data["is_training_ready"]["domain_tags"] is False
    # Aggregates (post Chunk 6 revision): both aggregates must be False.
    assert data["any_task_training_ready"] is False
    assert data["all_tasks_training_ready"] is False
    assert "overall" not in data["is_training_ready"]
    # Human-review disclaimer always present.
    assert any("human review required" in n.lower() for n in data["notes"])
    # Blockers list the specific gaps.
    codes = {b["code"] for b in data["blockers"]}
    assert "no_approved_labels" in codes


def test_cli_readiness_strict_mode_exits_1_on_shipped_dataset() -> None:
    proc = _run(["readiness", str(REPO_ROOT / "hybrid_dataset"), "--strict"])
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    # Shipped dataset has 0 approved labels for either task -> no task ready.
    assert data["any_task_training_ready"] is False
    assert data["all_tasks_training_ready"] is False
    assert data["strict"]["enabled"] is True


def test_cli_readiness_report_shape_has_required_fields() -> None:
    proc = _run(["readiness", str(REPO_ROOT / "hybrid_dataset")])
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    for key in (
        "assessment_status", "structurally_valid", "approved_label_count",
        "eligible_record_count", "agreement_status", "is_training_ready",
        "blockers", "warnings", "strict", "notes",
    ):
        assert key in data, f"readiness JSON missing {key!r}"
    for task in ("primary_type", "domain_tags"):
        assert task in data["approved_label_count"]
        assert task in data["eligible_record_count"]
        assert task in data["is_training_ready"]
        assert task in data["agreement_status"]


def test_cli_readiness_missing_root_exits_1(tmp_path: Path) -> None:
    proc = _run(["readiness", str(tmp_path / "nope")])
    assert proc.returncode == 1
    assert "FileNotFoundError" in proc.stderr


def test_cli_readiness_default_mode_exits_0_when_dataset_structurally_ok(tmp_path: Path) -> None:
    """Even with 0 eligible records, default mode still exits 0."""
    root = _dataset_root_with_sources(tmp_path)  # empty dataset
    proc = _run(["readiness", str(root)])
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    # New split aggregates: both must be False on the empty fixture.
    assert data["any_task_training_ready"] is False
    assert data["all_tasks_training_ready"] is False
    # "overall" is no longer a key on is_training_ready.
    assert "overall" not in data["is_training_ready"]


# ---- Chunk 6 revision: aggregate rename + strict minimum N -----------------


def _rec_dict_with_verified_primary(
    source_id: str, primary_label_id: str = "lbl_hackathon",
) -> dict:
    """Fully GT-eligible record for primary_type."""
    return _rec(
        source_id=source_id,
        primary_type=primary_label_id,
        annotation_status={
            "primary_type": "verified",
            "domain_tags": "not_started",
        },
    )


def _taxonomies_yaml(root: Path, *, primary_approved: list[str], domain_approved: list[str]) -> None:
    """Overwrite the test fixture taxonomies with the given approved labels."""
    primary_entries = [
        {
            "label_id": lid,
            "task_name": "primary_type",
            "display_name": lid.replace("lbl_", "").title(),
            "definition": "synthetic",
            "status": "approved",
        }
        for lid in primary_approved
    ]
    domain_entries = [
        {
            "label_id": lid,
            "task_name": "domain_tags",
            "display_name": lid.replace("lbl_", "").title(),
            "definition": "synthetic",
            "status": "approved",
        }
        for lid in domain_approved
    ]
    (root / "labels" / "primary_taxonomy.yaml").write_text(
        yaml.safe_dump(primary_entries, sort_keys=False), encoding="utf-8"
    )
    (root / "labels" / "domain_tags.yaml").write_text(
        yaml.safe_dump(domain_entries, sort_keys=False), encoding="utf-8"
    )


def test_cli_readiness_one_task_ready_other_not(tmp_path: Path) -> None:
    """Primary ready, domain not ready -> any_task=True, all_tasks=False."""
    sid = make_id("src")
    rec = _rec_dict_with_verified_primary(sid)
    root = _dataset_root_with_sources(tmp_path, rec)
    # Approve only lbl_hackathon on primary; approve nothing on domain.
    _taxonomies_yaml(root, primary_approved=["lbl_hackathon"], domain_approved=[])

    proc = _run(["readiness", str(root)])
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["is_training_ready"]["primary_type"] is True
    assert data["is_training_ready"]["domain_tags"] is False
    assert data["any_task_training_ready"] is True
    assert data["all_tasks_training_ready"] is False
    # strict mode still exits 0 because any_task is ready.
    proc_strict = _run(["readiness", str(root), "--strict"])
    assert proc_strict.returncode == 0, proc_strict.stderr


def test_cli_readiness_fully_eligible_fixture_strict_exits_0(tmp_path: Path) -> None:
    """Both tasks have approved labels + eligible records -> both aggregates True."""
    sid = make_id("src")
    rec = _rec(
        source_id=sid,
        primary_type="lbl_hackathon",
        domain_tags=["lbl_domain_ai"],
        annotation_status={
            "primary_type": "verified",
            "domain_tags": "verified",
        },
    )
    root = _dataset_root_with_sources(tmp_path, rec)
    _taxonomies_yaml(
        root,
        primary_approved=["lbl_hackathon"],
        domain_approved=["lbl_domain_ai"],
    )

    proc = _run(["readiness", str(root), "--strict"])
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["any_task_training_ready"] is True
    assert data["all_tasks_training_ready"] is True
    assert data["is_training_ready"]["primary_type"] is True
    assert data["is_training_ready"]["domain_tags"] is True


def test_cli_readiness_strict_min_n_2_fails_when_coverage_insufficient(tmp_path: Path) -> None:
    """Approved: 2 labels; eligible: 1 record. 1 < 2*2 -> strict fails."""
    sid = make_id("src")
    rec = _rec_dict_with_verified_primary(sid, primary_label_id="lbl_hackathon")
    root = _dataset_root_with_sources(tmp_path, rec)
    _taxonomies_yaml(
        root,
        primary_approved=["lbl_hackathon", "lbl_competition"],
        domain_approved=[],
    )
    proc = _run([
        "readiness", str(root),
        "--strict", "--min-records-per-approved-label", "2",
    ])
    assert proc.returncode == 1, proc.stdout
    data = json.loads(proc.stdout)
    codes = {b["code"] for b in data["blockers"]}
    assert "strict_minimum_records_per_approved_label" in codes
    assert data["strict"]["min_records_per_approved_label"] == 2


def test_cli_readiness_strict_min_n_2_passes_with_adequate_coverage(tmp_path: Path) -> None:
    """Approved: 1 label; eligible: 2 records of that label. 2 >= 2*1 -> OK."""
    sid = make_id("src")
    recs = [
        _rec(
            source_id=sid,
            source_record_id=f"k{i}",
            primary_type="lbl_hackathon",
            annotation_status={
                "primary_type": "verified",
                "domain_tags": "not_started",
            },
        )
        for i in range(2)
    ]
    root = _dataset_root_with_sources(tmp_path, *recs)
    _taxonomies_yaml(
        root,
        primary_approved=["lbl_hackathon"],
        domain_approved=[],
    )
    proc = _run([
        "readiness", str(root),
        "--strict", "--min-records-per-approved-label", "2",
    ])
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["any_task_training_ready"] is True
    assert data["strict"]["min_records_per_approved_label"] == 2
