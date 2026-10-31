"""Tests for the `review-candidate` CLI subcommand (Chunk 7.45)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from nlp_semantic.intake.cli import main


_SOURCES_YAML = """\
- source_id: src_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  source_name: synthetic test source
  source_url: https://example.org/synthetic
  license: CC0-1.0
  collection_date: 2026-10-25
  original_labels: []
  intended_use: test fixture
  is_synthetic: true
"""


_PRIMARY_TAX_YAML = """\
- label_id: lbl_hackathon
  task_name: primary_type
  display_name: Hackathon
  definition: synthetic test entry
  inclusion_rules: ["x"]
  exclusion_rules: ["y"]
  examples: ["a", "b", "c"]
  status: draft
"""


_DOMAIN_TAX_YAML = """\
- label_id: lbl_domain_ai
  task_name: domain_tags
  display_name: AI
  definition: synthetic
  inclusion_rules: ["x"]
  exclusion_rules: ["y"]
  examples: ["a", "b", "c"]
  status: draft
"""


def _write_fixture_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    sources = tmp_path / "sources.yaml"
    sources.write_text(_SOURCES_YAML, encoding="utf-8")
    pt = tmp_path / "primary_taxonomy.yaml"
    pt.write_text(_PRIMARY_TAX_YAML, encoding="utf-8")
    dt = tmp_path / "domain_tags.yaml"
    dt.write_text(_DOMAIN_TAX_YAML, encoding="utf-8")
    return sources, pt, dt


def test_cli_accept_valid_exits_zero(tmp_path: Path, capsys):
    sources, pt, dt = _write_fixture_files(tmp_path)
    out_dir = tmp_path / "reviews_out"

    exit_code = main(
        [
            "review-candidate",
            "--decision", "accept",
            "--reviewer", "labeler_cli_test",
            "--rationale", "CLI acceptance.",
            "--output-dir", str(out_dir),
            "--candidate-source-id", "src_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "--proposed-text", "CLI test achievement.",
            "--proposed-primary-type", "lbl_hackathon",
            "--proposer", "labeler_proposer_test",
            "--source-record-id", "cli-test-record-01",
            "--sources-yaml", str(sources),
            "--primary-taxonomy-yaml", str(pt),
            "--domain-taxonomy-yaml", str(dt),
        ]
    )
    out = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(out.out)
    assert payload["ok"] is True
    assert payload["decision"] == "accept"
    assert payload["review_id"].startswith("crev_")
    assert "review-candidate ok" in out.err
    # Review file was written
    assert any(out_dir.glob("crev_*.yaml"))


def test_cli_reject_valid_exits_zero(tmp_path: Path, capsys):
    sources, pt, dt = _write_fixture_files(tmp_path)
    out_dir = tmp_path / "reviews_out"

    exit_code = main(
        [
            "review-candidate",
            "--decision", "reject",
            "--reviewer", "labeler_cli_test",
            "--rationale", "CLI rejection.",
            "--output-dir", str(out_dir),
            "--proposed-text", "CLI test achievement to reject.",
            "--proposer", "labeler_proposer_test",
        ]
    )
    out = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(out.out)
    assert payload["ok"] is True
    assert payload["decision"] == "reject"


def test_cli_accept_missing_source_record_id_exits_one(tmp_path: Path, capsys):
    sources, pt, dt = _write_fixture_files(tmp_path)
    out_dir = tmp_path / "reviews_out"

    exit_code = main(
        [
            "review-candidate",
            "--decision", "accept",
            "--reviewer", "labeler_cli_test",
            "--rationale", "Missing source_record_id.",
            "--output-dir", str(out_dir),
            "--candidate-source-id", "src_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "--proposed-text", "Will fail P-3.",
            "--proposed-primary-type", "lbl_hackathon",
            "--proposer", "labeler_proposer_test",
            # No --source-record-id → P-3 fails
            "--sources-yaml", str(sources),
            "--primary-taxonomy-yaml", str(pt),
            "--domain-taxonomy-yaml", str(dt),
        ]
    )
    out = capsys.readouterr()
    assert exit_code == 1
    payload = json.loads(out.out)
    assert payload["ok"] is False
    codes = [f["code"] for f in payload["findings"]]
    assert "MISSING_SOURCE_RECORD_ID" in codes


def test_cli_accept_proposer_self_accept_exits_one(tmp_path: Path, capsys):
    sources, pt, dt = _write_fixture_files(tmp_path)
    out_dir = tmp_path / "reviews_out"

    exit_code = main(
        [
            "review-candidate",
            "--decision", "accept",
            "--reviewer", "labeler_same",
            "--rationale", "Self-accept attempt.",
            "--output-dir", str(out_dir),
            "--candidate-source-id", "src_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "--proposed-text", "Self accept.",
            "--proposed-primary-type", "lbl_hackathon",
            "--proposer", "labeler_same",  # same as reviewer
            "--source-record-id", "x",
            "--sources-yaml", str(sources),
            "--primary-taxonomy-yaml", str(pt),
            "--domain-taxonomy-yaml", str(dt),
        ]
    )
    out = capsys.readouterr()
    assert exit_code == 1
    payload = json.loads(out.out)
    assert payload["ok"] is False
    codes = [f["code"] for f in payload["findings"]]
    assert "PROPOSER_IS_REVIEWER" in codes


def test_cli_unsupported_decision_rejected_by_argparse(tmp_path: Path, capsys):
    """argparse `choices` constrains --decision to accept/reject;
    passing 'revise' triggers argparse's usage error (SystemExit(2)),
    enforcing the Chunk 7.45 scope at the CLI boundary."""
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "review-candidate",
                "--decision", "revise",
                "--reviewer", "labeler_test",
                "--rationale", "x",
                "--output-dir", str(tmp_path / "reviews_out"),
            ]
        )
    assert exc.value.code == 2


def test_cli_requires_subcommand_still_works(capsys):
    """Pre-existing behaviour unchanged: no subcommand → SystemExit(2)."""
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
