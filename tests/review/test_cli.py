"""Tests for the review-evidence CLI (python -m nlp_semantic.review.cli)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nlp_semantic.review.cli import main


_VALID_TAXONOMY_YAML = """\
bundle_id: evb_cli_taxonomy_01
bundle_type: taxonomy_promotion
target_id: lbl_hackathon
target_current_status: draft
proposer: labeler_proposer_test
reviewers:
  - reviewer: labeler_a_test
    date: 2026-10-25
    decision: approve
    rationale: "Reviewed and approve."
    evidence_refs: ["reports/synthetic.md"]
  - reviewer: labeler_b_test
    date: 2026-10-25
    decision: approve
    rationale: "Independent review; approve."
    evidence_refs: ["reports/synthetic.md"]
"""


_INVALID_WRONG_REVIEWER_COUNT = """\
bundle_id: evb_cli_taxonomy_bad
bundle_type: taxonomy_promotion
target_id: lbl_hackathon
target_current_status: draft
proposer: labeler_proposer_test
reviewers:
  - reviewer: labeler_only_test
    date: 2026-10-25
    decision: approve
    rationale: "Only one reviewer."
    evidence_refs: ["reports/synthetic.md"]
"""


def test_cli_valid_bundle_exits_zero(tmp_path: Path, capsys):
    path = tmp_path / "bundle.yaml"
    path.write_text(_VALID_TAXONOMY_YAML, encoding="utf-8")
    exit_code = main(["validate", str(path)])
    captured = capsys.readouterr()
    assert exit_code == 0
    # JSON goes to stdout
    payload = json.loads(captured.out)
    assert payload["structurally_valid"] is True
    assert payload["authenticated"] is False
    # concise human summary goes to stderr
    assert "review-evidence: ok" in captured.err
    assert "authenticated=False" in captured.err


def test_cli_wrong_reviewer_count_exits_one(tmp_path: Path, capsys):
    path = tmp_path / "bundle.yaml"
    path.write_text(_INVALID_WRONG_REVIEWER_COUNT, encoding="utf-8")
    exit_code = main(["validate", str(path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    payload = json.loads(captured.out)
    assert payload["structurally_valid"] is False
    assert payload["fatal_count"] >= 1
    assert "review-evidence: fatal" in captured.err


def test_cli_missing_file_exits_one(tmp_path: Path, capsys):
    exit_code = main(["validate", str(tmp_path / "nonexistent.yaml")])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FileNotFoundError" in captured.err


def test_cli_malformed_toplevel_exits_one(tmp_path: Path, capsys):
    """Top-level YAML as a list (not a mapping) is a BundleLoadError."""
    path = tmp_path / "bundle.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    exit_code = main(["validate", str(path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "BundleLoadError" in captured.err


def test_cli_pydantic_validation_error_exits_one(tmp_path: Path, capsys):
    """A YAML missing a required field surfaces as a ValidationError."""
    path = tmp_path / "bundle.yaml"
    path.write_text(
        "bundle_id: evb_x\nbundle_type: taxonomy_promotion\n",
        encoding="utf-8",
    )
    exit_code = main(["validate", str(path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ValidationError" in captured.err


def test_cli_requires_subcommand(capsys):
    """Argparse exits with code 2 on usage error (no subcommand)."""
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
