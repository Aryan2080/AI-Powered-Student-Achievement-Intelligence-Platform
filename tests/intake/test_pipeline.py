"""Tests for the reviewer-gated evidence intake pipeline.

Covers the 20 required cases from the Chunk 7.39 brief §5:

1   Successful intake of a valid evidence file.
2   Missing evidence file.
3   Unsupported file type.
4   Duplicate evidence content.
5   Hash stability.
6   Existing evidence preservation.
7   Manifest validation (round-trip).
8   Invalid source reference.
9   Invalid achievement reference.
10  Missing source or achievement association.
11  Invalid intake status.
12  Evidence path-traversal attempts.
13  Evidence filename collisions.
14  Empty evidence file.
15  Preservation of original evidence bytes.
16  No automatic reviewer approval.
17  No source-review status changes.
18  No annotation verification changes.
19  No taxonomy status changes.
20  No training-readiness changes.

Fixtures are all synthetic (inline bytes, tmp_path directories). No
file in ``hybrid_dataset/`` is touched by any test.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from nlp_semantic.intake import (
    AchievementCandidate,
    INTAKE_ROOT_PREFIX,
    IntakeEntry,
    IntakeError,
    IntakeStatus,
    IntakeValidationCode,
    classify_file_type,
    find_duplicate_hashes,
    ingest_evidence,
    list_intake_entries,
    load_intake_entry,
    make_candidate_id,
    make_intake_id,
    validate_candidate_id,
    validate_intake_entry,
    validate_intake_id,
)
from nlp_semantic.schema import DocumentFileType


# ---- helpers --------------------------------------------------------------


SYNTHETIC_PDF_BYTES = b"%PDF-1.4\nsynthetic test fixture, not real evidence\n"
SYNTHETIC_TEXT_BYTES = b"synthetic test fixture, not real evidence\n"


def _write_source_file(
    tmp_path: Path,
    name: str = "fixture.pdf",
    content: bytes = SYNTHETIC_PDF_BYTES,
) -> Path:
    """Write a synthetic reviewer-supplied evidence file to tmp_path.

    Named loudly as a test fixture so it is never mistaken for real
    evidence if someone grepped the test outputs.
    """
    path = tmp_path / "reviewer_inbox" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _intake_dirs(tmp_path: Path) -> tuple[Path, Path]:
    evidence_root = tmp_path / "evidence_root"
    manifest_dir = tmp_path / "manifests"
    return evidence_root, manifest_dir


# ---- required case 1: successful intake ----------------------------------


def test_01_successful_intake(tmp_path: Path):
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)

    result = ingest_evidence(
        src,
        evidence_root=evidence_root,
        manifest_dir=manifest_dir,
    )
    entry = result.entry

    assert entry.intake_id.startswith("intk_")
    assert entry.original_filename == "fixture.pdf"
    assert entry.file_type == DocumentFileType.PDF
    assert entry.size_bytes == len(SYNTHETIC_PDF_BYTES)
    assert entry.sha256 == hashlib.sha256(SYNTHETIC_PDF_BYTES).hexdigest()
    assert entry.status == IntakeStatus.RECEIVED
    # intake_timestamp is timezone-aware
    assert entry.intake_timestamp.tzinfo is not None
    # Stored file exists
    assert result.stored_file_path.exists()
    assert result.stored_file_path.read_bytes() == SYNTHETIC_PDF_BYTES
    # Manifest file exists
    assert result.manifest_path.exists()


# ---- required case 2: missing evidence file ------------------------------


def test_02_missing_evidence_file(tmp_path: Path):
    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    with pytest.raises(IntakeError):
        ingest_evidence(
            tmp_path / "nonexistent.pdf",
            evidence_root=evidence_root,
            manifest_dir=manifest_dir,
        )


# ---- required case 3: unsupported file type ------------------------------


def test_03_unsupported_file_type(tmp_path: Path):
    src = _write_source_file(tmp_path, name="fixture.exe", content=b"X" * 10)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    with pytest.raises(ValueError, match="unsupported file extension"):
        ingest_evidence(
            src,
            evidence_root=evidence_root,
            manifest_dir=manifest_dir,
        )


def test_03b_classify_file_type_rejects_extensionless_name():
    with pytest.raises(ValueError, match="no extension"):
        classify_file_type("README")


# ---- required case 4: duplicate content ----------------------------------


def test_04_duplicate_content_flagged(tmp_path: Path):
    src1 = _write_source_file(tmp_path, name="first.pdf")
    src2 = _write_source_file(tmp_path, name="second.pdf")  # identical content
    evidence_root, manifest_dir = _intake_dirs(tmp_path)

    r1 = ingest_evidence(
        src1,
        evidence_root=evidence_root,
        manifest_dir=manifest_dir,
    )
    r2 = ingest_evidence(
        src2,
        evidence_root=evidence_root,
        manifest_dir=manifest_dir,
    )

    assert r2.duplicate_of_intake_ids == [r1.entry.intake_id]
    # The second entry has a DUPLICATE_HASH advisory
    codes = [f.code for f in r2.entry.validation_findings]
    assert IntakeValidationCode.DUPLICATE_HASH in codes

    # And find_duplicate_hashes agrees
    groups = find_duplicate_hashes(manifest_dir)
    assert len(groups) == 1
    sha = next(iter(groups))
    assert set(groups[sha]) == {r1.entry.intake_id, r2.entry.intake_id}


# ---- required case 5: hash stability -------------------------------------


def test_05_hash_stability(tmp_path: Path):
    src1 = _write_source_file(tmp_path, name="a.pdf")
    src2 = _write_source_file(tmp_path, name="b.pdf")  # same bytes
    evidence_root, manifest_dir = _intake_dirs(tmp_path)

    r1 = ingest_evidence(
        src1, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    r2 = ingest_evidence(
        src2, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    assert r1.entry.sha256 == r2.entry.sha256
    expected = hashlib.sha256(SYNTHETIC_PDF_BYTES).hexdigest()
    assert r1.entry.sha256 == expected


# ---- required case 6: existing evidence preservation ---------------------


def test_06_existing_evidence_preservation(tmp_path: Path):
    """Each ingest allocates a fresh intake_id and never overwrites.

    Uses two distinct source files in different inbox directories so the
    second write cannot overwrite the first in the reviewer's inbox.
    """
    src1 = tmp_path / "inbox_a" / "x.pdf"
    src1.parent.mkdir(parents=True, exist_ok=True)
    src1.write_bytes(SYNTHETIC_PDF_BYTES)

    src2 = tmp_path / "inbox_b" / "x.pdf"
    src2.parent.mkdir(parents=True, exist_ok=True)
    src2.write_bytes(b"different bytes\n")

    evidence_root, manifest_dir = _intake_dirs(tmp_path)

    r1 = ingest_evidence(
        src1, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    r2 = ingest_evidence(
        src2, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    # Both files survive; distinct intake_ids
    assert r1.entry.intake_id != r2.entry.intake_id
    assert r1.stored_file_path.exists()
    assert r2.stored_file_path.exists()
    assert r1.stored_file_path.read_bytes() == SYNTHETIC_PDF_BYTES
    assert r2.stored_file_path.read_bytes() == b"different bytes\n"


# ---- required case 7: manifest validation (round-trip) -------------------


def test_07_manifest_round_trip(tmp_path: Path):
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)

    r = ingest_evidence(
        src, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    # Load back from disk
    reloaded = load_intake_entry(r.manifest_path)
    assert reloaded.model_dump() == r.entry.model_dump()


def test_07b_malformed_manifest_raises(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(IntakeError):
        load_intake_entry(bad)


# ---- required case 8: invalid source reference ---------------------------


def test_08_invalid_source_reference_rejected_at_pydantic_layer(tmp_path: Path):
    """A bogus source_id (not src_<32-hex>) is rejected at ingest time."""
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    with pytest.raises((ValidationError, ValueError)):
        ingest_evidence(
            src,
            evidence_root=evidence_root,
            manifest_dir=manifest_dir,
            source_id="not_a_valid_source_id",
        )


def test_08b_unknown_source_reference_cross_check(tmp_path: Path):
    """A well-formed but non-existent source_id is caught by validate_intake_entry."""
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)

    r = ingest_evidence(
        src,
        evidence_root=evidence_root,
        manifest_dir=manifest_dir,
        source_id="src_" + "0" * 32,  # well-formed but not registered
    )
    # Empty sources.yaml
    sources_yaml = tmp_path / "sources.yaml"
    sources_yaml.write_text("[]\n", encoding="utf-8")

    findings = validate_intake_entry(
        r.entry,
        evidence_root=evidence_root,
        sources_yaml=sources_yaml,
    )
    codes = [f.code for f in findings]
    assert IntakeValidationCode.UNKNOWN_SOURCE_REFERENCE in codes


# ---- required case 9: invalid achievement reference ----------------------


def test_09_invalid_achievement_reference(tmp_path: Path):
    """An invalid candidate_id format is rejected at Pydantic layer."""
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    with pytest.raises((ValidationError, ValueError)):
        ingest_evidence(
            src,
            evidence_root=evidence_root,
            manifest_dir=manifest_dir,
            achievement_candidate_ids=["not_a_cand_id"],
        )


def test_09b_unknown_candidate_cross_check(tmp_path: Path):
    """A well-formed candidate_id not in the known set is a cross-check finding."""
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)

    unknown_cand = make_candidate_id()
    r = ingest_evidence(
        src,
        evidence_root=evidence_root,
        manifest_dir=manifest_dir,
        achievement_candidate_ids=[unknown_cand],
    )
    findings = validate_intake_entry(
        r.entry,
        evidence_root=evidence_root,
        known_candidate_ids=set(),
    )
    assert any(
        f.code == IntakeValidationCode.UNKNOWN_ACHIEVEMENT_REFERENCE
        for f in findings
    )


# ---- required case 10: missing associations ------------------------------


def test_10_missing_source_and_achievement_associations_flagged(tmp_path: Path):
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)

    r = ingest_evidence(
        src,
        evidence_root=evidence_root,
        manifest_dir=manifest_dir,
    )
    codes = [f.code for f in r.entry.validation_findings]
    assert IntakeValidationCode.MISSING_SOURCE_ASSOCIATION in codes
    assert IntakeValidationCode.MISSING_ACHIEVEMENT_ASSOCIATION in codes


# ---- required case 11: invalid intake status -----------------------------


def test_11_invalid_intake_status():
    """An invalid status value is rejected at Pydantic layer."""
    with pytest.raises(ValidationError):
        IntakeEntry(
            intake_id="intk_" + "a" * 32,
            original_filename="x.pdf",
            file_type=DocumentFileType.PDF,
            relative_path=f"{INTAKE_ROOT_PREFIX}intk_{'a' * 32}/x.pdf",
            sha256="0" * 64,
            size_bytes=0,
            intake_timestamp=datetime.now(timezone.utc),
            status="not_a_real_status",
        )


# ---- required case 12: path-traversal attempts ---------------------------


def test_12_path_traversal_filename_rejected(tmp_path: Path):
    src = _write_source_file(tmp_path, name="normal.pdf")
    # Rename to a path-traversal attempt — passing a Path works via tmp_path
    traversal_name = tmp_path / "nested" / "sub" / "x.pdf"
    traversal_name.parent.mkdir(parents=True, exist_ok=True)
    traversal_name.write_bytes(SYNTHETIC_PDF_BYTES)

    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    # The ingest function uses src.name which strips directories.
    # But if someone constructs an IntakeEntry directly with a traversal
    # relative_path, Pydantic rejects it:
    with pytest.raises((ValidationError, ValueError)):
        IntakeEntry(
            intake_id="intk_" + "a" * 32,
            original_filename="x.pdf",
            file_type=DocumentFileType.PDF,
            relative_path=f"{INTAKE_ROOT_PREFIX}../../etc/passwd",
            sha256="0" * 64,
            size_bytes=0,
            intake_timestamp=datetime.now(timezone.utc),
        )


def test_12b_backslash_in_relative_path_rejected():
    with pytest.raises((ValidationError, ValueError)):
        IntakeEntry(
            intake_id="intk_" + "a" * 32,
            original_filename="x.pdf",
            file_type=DocumentFileType.PDF,
            relative_path="hybrid_dataset\\raw\\evidence_intake\\x.pdf",
            sha256="0" * 64,
            size_bytes=0,
            intake_timestamp=datetime.now(timezone.utc),
        )


def test_12c_absolute_relative_path_rejected():
    with pytest.raises((ValidationError, ValueError)):
        IntakeEntry(
            intake_id="intk_" + "a" * 32,
            original_filename="x.pdf",
            file_type=DocumentFileType.PDF,
            relative_path="/etc/passwd",
            sha256="0" * 64,
            size_bytes=0,
            intake_timestamp=datetime.now(timezone.utc),
        )


def test_12d_path_separator_in_filename_rejected(tmp_path: Path):
    """A directly constructed entry with a filename containing / is rejected."""
    with pytest.raises((ValidationError, ValueError)):
        IntakeEntry(
            intake_id="intk_" + "a" * 32,
            original_filename="../x.pdf",
            file_type=DocumentFileType.PDF,
            relative_path=f"{INTAKE_ROOT_PREFIX}intk_{'a' * 32}/x.pdf",
            sha256="0" * 64,
            size_bytes=0,
            intake_timestamp=datetime.now(timezone.utc),
        )


# ---- required case 13: filename collisions -------------------------------


def test_13_filename_collisions_get_distinct_intake_ids(tmp_path: Path):
    """Two files with the same filename but different content get distinct ids."""
    src1 = _write_source_file(tmp_path, name="report.pdf", content=b"version A")
    src2 = _write_source_file(
        tmp_path / "second_inbox", name="report.pdf", content=b"version B"
    )
    # Place src2 at a different source directory so the test can distinguish them
    src2 = tmp_path / "another" / "report.pdf"
    src2.parent.mkdir(parents=True, exist_ok=True)
    src2.write_bytes(b"version B")

    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    r1 = ingest_evidence(
        src1, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    r2 = ingest_evidence(
        src2, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    assert r1.entry.intake_id != r2.entry.intake_id
    assert r1.entry.sha256 != r2.entry.sha256
    assert r1.stored_file_path != r2.stored_file_path
    # Both files preserved under their own intake_id directories
    assert r1.stored_file_path.read_bytes() == b"version A"
    assert r2.stored_file_path.read_bytes() == b"version B"


# ---- required case 14: empty evidence file -------------------------------


def test_14_empty_file_flagged(tmp_path: Path):
    src = _write_source_file(tmp_path, name="empty.pdf", content=b"")
    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    r = ingest_evidence(
        src, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    assert r.entry.size_bytes == 0
    codes = [f.code for f in r.entry.validation_findings]
    assert IntakeValidationCode.EMPTY_FILE in codes


# ---- required case 15: preservation of original bytes --------------------


def test_15_original_bytes_preserved(tmp_path: Path):
    """Round-trip the exact bytes through intake storage."""
    original = bytes(range(256)) * 4  # 1024 bytes, every value 0-255
    src = _write_source_file(tmp_path, name="binary.pdf", content=original)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    r = ingest_evidence(
        src, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    assert r.stored_file_path.read_bytes() == original
    # SHA matches
    assert r.entry.sha256 == hashlib.sha256(original).hexdigest()


# ---- required case 16: no automatic reviewer approval --------------------


def test_16_status_starts_received_never_auto_validated(tmp_path: Path):
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    r = ingest_evidence(
        src, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    assert r.entry.status == IntakeStatus.RECEIVED
    # authentication-not-established is in the findings
    codes = [f.code for f in r.entry.validation_findings]
    assert IntakeValidationCode.AUTHENTICATION_NOT_ESTABLISHED in codes


# ---- required cases 17-20: no touch of taxonomy/dataset/source/readiness

# These are AST-based assertions: the intake module does not import or
# call the state-mutating functions / fields it must not touch.


def _module_identifier_names(module) -> set[str]:
    src = inspect.getsource(module)
    tree = ast.parse(src)

    def _strip_docstring(node):
        if (
            hasattr(node, "body")
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body = node.body[1:]

    _strip_docstring(tree)
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            _strip_docstring(n)

    names: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.Attribute):
            names.add(n.attr)
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                names.add(a.asname or a.name)
    return names


def test_17_pipeline_does_not_touch_source_statuses():
    import nlp_semantic.intake.pipeline as mod

    names = _module_identifier_names(mod)
    assert "ReviewStatus" not in names
    assert "SourceRegistry" not in names


def test_18_pipeline_does_not_touch_annotation_statuses():
    import nlp_semantic.intake.pipeline as mod

    names = _module_identifier_names(mod)
    assert "AnnotationStatus" not in names
    assert "AnnotationStatusMap" not in names
    assert "Annotation" not in names


def test_19_pipeline_does_not_touch_taxonomy_status():
    import nlp_semantic.intake.pipeline as mod

    names = _module_identifier_names(mod)
    assert "TaxonomyStatus" not in names
    assert "load_and_validate_taxonomy" not in names


def test_20_pipeline_does_not_touch_training_readiness():
    import nlp_semantic.intake.pipeline as mod

    names = _module_identifier_names(mod)
    assert "training_ready_subset" not in names
    assert "eligible_ground_truth" not in names


# ---- additional coverage -------------------------------------------------


def test_make_intake_id_uniqueness_and_format():
    ids = {make_intake_id() for _ in range(100)}
    assert len(ids) == 100
    for i in ids:
        assert validate_intake_id(i) == i


def test_make_candidate_id_uniqueness_and_format():
    ids = {make_candidate_id() for _ in range(100)}
    assert len(ids) == 100
    for i in ids:
        assert validate_candidate_id(i) == i


def test_naive_timestamp_rejected():
    with pytest.raises(ValidationError):
        IntakeEntry(
            intake_id="intk_" + "a" * 32,
            original_filename="x.pdf",
            file_type=DocumentFileType.PDF,
            relative_path=f"{INTAKE_ROOT_PREFIX}intk_{'a' * 32}/x.pdf",
            sha256="0" * 64,
            size_bytes=0,
            intake_timestamp=datetime(2026, 10, 25, 12, 0, 0),  # naive
        )


def test_candidate_is_not_an_achievement():
    """AchievementCandidate must not accept Achievement-shaped fields it
    does not define — e.g. achievement_id is not a candidate field."""
    with pytest.raises(ValidationError):
        AchievementCandidate(
            candidate_id=make_candidate_id(),
            achievement_id="ach_" + "a" * 32,  # not a candidate field
        )


def test_candidate_evidence_intake_ids_validated():
    with pytest.raises(ValidationError):
        AchievementCandidate(
            candidate_id=make_candidate_id(),
            evidence_intake_ids=["not_an_intake_id"],
        )


def test_pseudonym_rejected_as_email():
    """A proposer that looks like an email is rejected at Pydantic layer."""
    with pytest.raises(ValidationError):
        IntakeEntry(
            intake_id="intk_" + "a" * 32,
            original_filename="x.pdf",
            file_type=DocumentFileType.PDF,
            relative_path=f"{INTAKE_ROOT_PREFIX}intk_{'a' * 32}/x.pdf",
            sha256="0" * 64,
            size_bytes=0,
            intake_timestamp=datetime.now(timezone.utc),
            proposer="user@example.org",
        )


def test_list_intake_entries_empty_dir_returns_empty(tmp_path: Path):
    assert list_intake_entries(tmp_path / "nonexistent") == []


def test_classify_file_type_extensions():
    assert classify_file_type("a.pdf") == DocumentFileType.PDF
    assert classify_file_type("a.jpg") == DocumentFileType.IMAGE_JPG
    assert classify_file_type("a.jpeg") == DocumentFileType.IMAGE_JPG
    assert classify_file_type("a.PNG") == DocumentFileType.IMAGE_PNG  # case insensitive
    assert classify_file_type("a.tiff") == DocumentFileType.IMAGE_TIFF
    assert classify_file_type("a.txt") == DocumentFileType.TEXT
    assert classify_file_type("a.md") == DocumentFileType.TEXT
    assert classify_file_type("a.html") == DocumentFileType.TEXT
    assert classify_file_type("a.json") == DocumentFileType.TEXT
    assert classify_file_type("a.yaml") == DocumentFileType.TEXT


def test_validate_intake_entry_hash_mismatch(tmp_path: Path):
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    r = ingest_evidence(
        src, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    # Tamper with the stored file
    r.stored_file_path.write_bytes(b"tampered content")

    findings = validate_intake_entry(
        r.entry,
        evidence_root=evidence_root,
    )
    codes = [f.code for f in findings]
    assert IntakeValidationCode.HASH_MISMATCH_ON_DISK in codes


def test_validate_intake_entry_missing_file(tmp_path: Path):
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    r = ingest_evidence(
        src, evidence_root=evidence_root, manifest_dir=manifest_dir
    )
    # Delete the stored file
    r.stored_file_path.unlink()

    findings = validate_intake_entry(
        r.entry,
        evidence_root=evidence_root,
    )
    codes = [f.code for f in findings]
    assert IntakeValidationCode.FILE_NOT_FOUND in codes


def test_source_cross_check_with_registered_source(tmp_path: Path):
    """When the source_id IS registered, no UNKNOWN_SOURCE_REFERENCE."""
    src = _write_source_file(tmp_path)
    evidence_root, manifest_dir = _intake_dirs(tmp_path)
    src_id = "src_" + "a" * 32
    r = ingest_evidence(
        src,
        evidence_root=evidence_root,
        manifest_dir=manifest_dir,
        source_id=src_id,
    )
    sources_yaml = tmp_path / "sources.yaml"
    sources_yaml.write_text(
        yaml.safe_dump([{"source_id": src_id}]),
        encoding="utf-8",
    )
    findings = validate_intake_entry(
        r.entry,
        evidence_root=evidence_root,
        sources_yaml=sources_yaml,
    )
    codes = [f.code for f in findings]
    assert IntakeValidationCode.UNKNOWN_SOURCE_REFERENCE not in codes


def test_pipeline_module_does_not_write_to_real_dataset():
    """Static assertion: the pipeline module does not reference the real
    hybrid_dataset record batch file by name."""
    import nlp_semantic.intake.pipeline as mod

    src = inspect.getsource(mod)
    assert "batch_01_sih2024" not in src
    assert "batch_01" not in src
