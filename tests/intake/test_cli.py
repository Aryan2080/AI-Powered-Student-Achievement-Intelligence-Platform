"""Tests for the intake CLI (`python -m nlp_semantic.intake.cli`)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nlp_semantic.intake.cli import main


_SYNTHETIC = b"synthetic test fixture, not real evidence\n"


def _write_fixture(path: Path, name: str = "fixture.pdf", content: bytes = _SYNTHETIC) -> Path:
    p = path / name
    p.write_bytes(content)
    return p


def test_cli_ingest_valid_file(tmp_path: Path, capsys):
    src = _write_fixture(tmp_path)
    evidence_root = tmp_path / "store"
    manifests = tmp_path / "manifests"

    exit_code = main(
        [
            "ingest",
            str(src),
            "--evidence-root",
            str(evidence_root),
            "--manifest-dir",
            str(manifests),
        ]
    )
    out = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(out.out)
    assert payload["entry"]["intake_id"].startswith("intk_")
    assert payload["entry"]["status"] == "received"
    assert "intake: ingested" in out.err


def test_cli_ingest_missing_file(tmp_path: Path, capsys):
    exit_code = main(
        [
            "ingest",
            str(tmp_path / "nonexistent.pdf"),
            "--evidence-root",
            str(tmp_path / "store"),
            "--manifest-dir",
            str(tmp_path / "manifests"),
        ]
    )
    out = capsys.readouterr()
    assert exit_code == 1
    assert "IntakeError" in out.err


def test_cli_ingest_unsupported_type(tmp_path: Path, capsys):
    bad = _write_fixture(tmp_path, name="virus.exe", content=b"X")
    exit_code = main(
        [
            "ingest",
            str(bad),
            "--evidence-root",
            str(tmp_path / "store"),
            "--manifest-dir",
            str(tmp_path / "manifests"),
        ]
    )
    out = capsys.readouterr()
    assert exit_code == 1
    assert "ValueError" in out.err or "unsupported" in out.err.lower()


def test_cli_validate_round_trip(tmp_path: Path, capsys):
    src = _write_fixture(tmp_path)
    evidence_root = tmp_path / "store"
    manifests = tmp_path / "manifests"
    # ingest
    main(
        [
            "ingest",
            str(src),
            "--evidence-root",
            str(evidence_root),
            "--manifest-dir",
            str(manifests),
        ]
    )
    capsys.readouterr()  # drain

    # validate the manifest
    manifest = next(manifests.glob("intk_*.yaml"))
    exit_code = main(
        [
            "validate",
            str(manifest),
            "--evidence-root",
            str(evidence_root),
        ]
    )
    out = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(out.out)
    assert payload["ok"] is True


def test_cli_status(tmp_path: Path, capsys):
    src = _write_fixture(tmp_path)
    evidence_root = tmp_path / "store"
    manifests = tmp_path / "manifests"
    main(
        [
            "ingest",
            str(src),
            "--evidence-root",
            str(evidence_root),
            "--manifest-dir",
            str(manifests),
        ]
    )
    capsys.readouterr()

    exit_code = main(["status", "--manifest-dir", str(manifests)])
    out = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(out.out)
    assert payload["count"] == 1


def test_cli_duplicates(tmp_path: Path, capsys):
    src1 = _write_fixture(tmp_path, name="a.pdf")
    src2 = _write_fixture(tmp_path, name="b.pdf")  # same content
    evidence_root = tmp_path / "store"
    manifests = tmp_path / "manifests"

    main(
        [
            "ingest",
            str(src1),
            "--evidence-root",
            str(evidence_root),
            "--manifest-dir",
            str(manifests),
        ]
    )
    capsys.readouterr()
    main(
        [
            "ingest",
            str(src2),
            "--evidence-root",
            str(evidence_root),
            "--manifest-dir",
            str(manifests),
        ]
    )
    capsys.readouterr()

    exit_code = main(["duplicates", "--manifest-dir", str(manifests)])
    out = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(out.out)
    assert payload["total_duplicate_hashes"] == 1


def test_cli_requires_subcommand(capsys):
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_cli_validate_missing_manifest(tmp_path: Path, capsys):
    exit_code = main(
        [
            "validate",
            str(tmp_path / "nonexistent.yaml"),
            "--evidence-root",
            str(tmp_path / "store"),
        ]
    )
    out = capsys.readouterr()
    assert exit_code == 1
    assert "FileNotFoundError" in out.err
