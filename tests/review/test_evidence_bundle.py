"""Tests for the reviewer-evidence bundle validator.

Covers the 18 required test cases from the Chunk 7.38B brief §8:
1   valid structural bundle (taxonomy + annotation variants)
2   missing required field
3   invalid reviewer decision
4   duplicate reviewer identity
5   missing reviewer rationale when required
6   missing evidence reference (advisory, not fatal)
7   mismatched taxonomy label id
8   mismatched achievement record id
9   unsupported bundle type
10  reviewer independence not established (proposer-reviewer overlap)
11  evidence structurally valid but authentication unavailable
12  incomplete bundle remains incomplete (wrong reviewer count)
13  validation does not mutate input data
14  validation does not modify taxonomy
15  validation does not modify achievement records
16  validation does not modify annotation statuses
17  validation does not modify source statuses
18  validation does not change training-readiness results

All fixtures are inline and synthetic. No file in hybrid_dataset/ is
touched; no real reviewer identity is referenced.
"""
from __future__ import annotations

import ast
import copy
import inspect
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError


def _module_identifier_names(module) -> set[str]:
    """Return every identifier referenced in the module's AST, excluding
    bare string expressions (module / function / class docstrings and
    comments). Used to assert that specific function names are not
    imported or called by the module, while allowing them to appear in
    docstrings that document what the module does NOT do.
    """
    src = inspect.getsource(module)
    tree = ast.parse(src)
    names: set[str] = set()

    def _strip_docstring_bodies(node: ast.AST) -> None:
        """Remove docstring Expr nodes from the body of a module /
        function / class so their contents don't contribute to the
        name set."""
        if not hasattr(node, "body") or not isinstance(getattr(node, "body"), list):
            return
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:]

    # Strip top-level and nested docstrings.
    _strip_docstring_bodies(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            _strip_docstring_bodies(node)

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
    return names

from nlp_semantic.review import (
    BundleType,
    Decision,
    ErrorCode,
    EvidenceBundle,
    ReviewerSignOff,
    ValidationReport,
    validate_bundle,
)
from nlp_semantic.schema import AnnotationTask, TaxonomyStatus


# ---- fixtures (synthetic, inline, isolated) ---------------------------------


def _taxonomy_bundle() -> EvidenceBundle:
    """A structurally valid taxonomy-promotion bundle."""
    return EvidenceBundle(
        bundle_id="evb_test_taxonomy_01",
        bundle_type=BundleType.TAXONOMY_PROMOTION,
        target_id="lbl_hackathon",
        target_current_status=TaxonomyStatus.DRAFT,
        proposer="labeler_proposer_test",
        reviewers=[
            ReviewerSignOff(
                reviewer="labeler_a_test",
                date=date(2026, 10, 25),
                decision=Decision.APPROVE,
                rationale="Reviewed definition and examples; approve.",
                evidence_refs=["reports/synthetic_packet.md"],
            ),
            ReviewerSignOff(
                reviewer="labeler_b_test",
                date=date(2026, 10, 25),
                decision=Decision.APPROVE,
                rationale="Independent read; approve.",
                evidence_refs=["reports/synthetic_packet.md"],
            ),
        ],
    )


def _annotation_bundle() -> EvidenceBundle:
    """A structurally valid annotation-review bundle."""
    return EvidenceBundle(
        bundle_id="evb_test_annotation_01",
        bundle_type=BundleType.ANNOTATION_REVIEW,
        target_id="ach_" + "a" * 32,
        task=AnnotationTask.PRIMARY_TYPE,
        proposed_label_ids=["lbl_hackathon"],
        reviewers=[
            ReviewerSignOff(
                reviewer="labeler_x_test",
                date=date(2026, 10, 25),
                decision=Decision.APPROVE,
                rationale="Reviewed against synthetic source.",
                evidence_refs=["reports/synthetic.md"],
            ),
        ],
    )


# ---- the 18 required cases --------------------------------------------------


def test_01_valid_structural_taxonomy_bundle():
    b = _taxonomy_bundle()
    r = validate_bundle(b)
    assert r.structurally_valid
    assert len(r.fatal_errors) == 0
    # authentication is unconditionally not established
    codes = [limitation.code for limitation in r.limitations]
    assert ErrorCode.IDENTITY_AUTHENTICATION_NOT_ESTABLISHED in codes


def test_01b_valid_structural_annotation_bundle():
    b = _annotation_bundle()
    r = validate_bundle(b)
    assert r.structurally_valid
    assert len(r.fatal_errors) == 0


def test_02_missing_required_field():
    """target_id missing at Pydantic level."""
    with pytest.raises(ValidationError):
        EvidenceBundle(
            bundle_id="evb_bad",
            bundle_type=BundleType.TAXONOMY_PROMOTION,
        )


def test_03_invalid_reviewer_decision():
    """A decision that is not in the Decision enum."""
    with pytest.raises(ValidationError):
        ReviewerSignOff(
            reviewer="labeler_x_test",
            date=date(2026, 10, 25),
            decision="maybe",
            rationale="x",
        )


def test_04_duplicate_reviewer_identity():
    b = _taxonomy_bundle()
    # Replace the second reviewer with a duplicate pseudonym
    b.reviewers[1] = ReviewerSignOff(
        reviewer="labeler_a_test",  # same as reviewers[0]
        date=date(2026, 10, 25),
        decision=Decision.APPROVE,
        rationale="duplicate attempt.",
        evidence_refs=["reports/synthetic.md"],
    )
    r = validate_bundle(b)
    assert not r.structurally_valid
    assert any(f.code == ErrorCode.DUPLICATE_REVIEWER for f in r.fatal_errors)


def test_05_missing_reviewer_rationale_when_required():
    """Empty rationale rejected at Pydantic level (str_strip_whitespace + min_length)."""
    with pytest.raises(ValidationError):
        ReviewerSignOff(
            reviewer="labeler_x_test",
            date=date(2026, 10, 25),
            decision=Decision.APPROVE,
            rationale="   ",  # strips to empty
        )


def test_06_missing_evidence_reference_advisory():
    """Missing evidence refs is advisory, not fatal."""
    b = _taxonomy_bundle()
    b.reviewers[0].evidence_refs.clear()
    r = validate_bundle(b)
    assert r.structurally_valid
    assert any(
        a.code == ErrorCode.MISSING_EVIDENCE_REFERENCE for a in r.advisories
    )


def test_07_mismatched_taxonomy_label_id():
    """target_id not a valid lbl_... format on a taxonomy bundle."""
    b = _taxonomy_bundle()
    b.target_id = "not_a_label_id"
    r = validate_bundle(b)
    assert not r.structurally_valid
    assert any(f.code == ErrorCode.TARGET_ID_MISMATCH for f in r.fatal_errors)


def test_08_mismatched_achievement_record_id():
    """target_id not a valid ach_... format on an annotation bundle."""
    b = _annotation_bundle()
    b.target_id = "not_an_ach_id"
    r = validate_bundle(b)
    assert not r.structurally_valid
    assert any(f.code == ErrorCode.TARGET_ID_MISMATCH for f in r.fatal_errors)


def test_09_unsupported_bundle_type():
    """A bundle_type string not in the BundleType enum."""
    with pytest.raises(ValidationError):
        EvidenceBundle(
            bundle_id="evb_bad",
            bundle_type="unsupported_type",
            target_id="lbl_x",
        )


def test_10_reviewer_independence_proposer_overlap():
    """Proposer appearing as a reviewer violates TAXONOMY_APPROVAL_CHECKLIST §104-106."""
    b = _taxonomy_bundle()
    b.proposer = "labeler_a_test"  # same as reviewers[0]
    r = validate_bundle(b)
    assert not r.structurally_valid
    assert any(
        f.code == ErrorCode.PROPOSER_IS_REVIEWER for f in r.fatal_errors
    )


def test_11_structurally_valid_but_authentication_unavailable():
    """Even a perfectly structured bundle is NOT authenticated."""
    b = _taxonomy_bundle()
    r = validate_bundle(b)
    assert r.structurally_valid
    # authenticated is always False by design
    assert r.authenticated is False
    assert any(
        lim.code == ErrorCode.IDENTITY_AUTHENTICATION_NOT_ESTABLISHED
        for lim in r.limitations
    )


def test_12_incomplete_bundle_remains_incomplete():
    """Dropping to 1 reviewer makes a taxonomy bundle incomplete."""
    b = _taxonomy_bundle()
    b.reviewers.pop()
    r = validate_bundle(b)
    assert not r.structurally_valid
    assert any(
        f.code == ErrorCode.WRONG_REVIEWER_COUNT for f in r.fatal_errors
    )


def test_13_validation_does_not_mutate_input():
    b = _taxonomy_bundle()
    snapshot = b.model_dump()
    validate_bundle(b)
    assert b.model_dump() == snapshot


def test_14_validation_does_not_modify_taxonomy_file():
    """Validation never touches taxonomy YAML; the module does not import
    the YAML loader for primary_taxonomy or domain_tags."""
    import nlp_semantic.review.evidence_bundle as mod

    names = _module_identifier_names(mod)
    assert "load_and_validate_taxonomy" not in names
    assert "load_taxonomy" not in names
    assert "validate_taxonomy" not in names


def test_15_validation_does_not_modify_achievement_records():
    """Validator does not touch any record batch."""
    import nlp_semantic.review.evidence_bundle as mod

    names = _module_identifier_names(mod)
    assert "load_dataset" not in names
    assert "load_records" not in names
    assert "load_annotations" not in names


def test_16_validation_does_not_modify_annotation_statuses():
    """Validator never sets or returns AnnotationStatus values."""
    import nlp_semantic.review.evidence_bundle as mod

    names = _module_identifier_names(mod)
    # It may import AnnotationTask for enum validation; it must NOT touch
    # AnnotationStatus (the mutable state field) or AnnotationStatusMap.
    assert "AnnotationStatus" not in names
    assert "AnnotationStatusMap" not in names
    # Report dict has no annotation_status key
    b = _annotation_bundle()
    r = validate_bundle(b)
    assert "annotation_status" not in r.to_dict()


def test_17_validation_does_not_modify_source_statuses():
    """Validator never writes to the source registry."""
    import nlp_semantic.review.evidence_bundle as mod

    names = _module_identifier_names(mod)
    assert "SourceRegistry" not in names
    assert "ReviewStatus" not in names
    b = _annotation_bundle()
    r = validate_bundle(b)
    assert "review_status" not in r.to_dict()


def test_18_validation_does_not_change_training_readiness():
    """Validator never imports or invokes the training-readiness gate."""
    import nlp_semantic.review.evidence_bundle as mod

    names = _module_identifier_names(mod)
    assert "training_ready_subset" not in names
    assert "eligible_ground_truth" not in names


# ---- additional coverage ---------------------------------------------------


def test_annotation_review_primary_type_arity_zero_fatal():
    """primary_type task with empty proposed_label_ids is a fatal arity error."""
    b = _annotation_bundle()
    b.proposed_label_ids = []
    r = validate_bundle(b)
    assert not r.structurally_valid
    assert any(
        f.code == ErrorCode.INVALID_LABEL_ARITY for f in r.fatal_errors
    )


def test_annotation_review_primary_type_arity_two_fatal():
    """primary_type task with two proposed_label_ids is a fatal arity error."""
    b = _annotation_bundle()
    b.proposed_label_ids = ["lbl_hackathon", "lbl_competition"]
    r = validate_bundle(b)
    assert not r.structurally_valid
    assert any(
        f.code == ErrorCode.INVALID_LABEL_ARITY for f in r.fatal_errors
    )


def test_annotation_review_extraction_review_arity_zero_ok():
    """extraction_review with zero labels is structurally valid."""
    b = _annotation_bundle()
    b.task = AnnotationTask.EXTRACTION_REVIEW
    b.proposed_label_ids = []
    r = validate_bundle(b)
    assert r.structurally_valid


def test_annotation_review_domain_tags_arity_any():
    """domain_tags accepts 0..N labels."""
    for labels in ([], ["lbl_domain_ai"], ["lbl_domain_ai", "lbl_domain_ml"]):
        b = _annotation_bundle()
        b.task = AnnotationTask.DOMAIN_TAGS
        b.proposed_label_ids = labels
        r = validate_bundle(b)
        assert r.structurally_valid


def test_reviewer_pseudonym_email_rejected():
    """Email-shaped pseudonyms are rejected at Pydantic layer."""
    with pytest.raises(ValidationError):
        ReviewerSignOff(
            reviewer="person@example.org",
            date=date(2026, 10, 25),
            decision=Decision.APPROVE,
            rationale="x",
        )


def test_taxonomy_bundle_missing_proposer_advisory():
    """Missing proposer surfaces a REVIEWER_INDEPENDENCE_NOT_ESTABLISHED
    advisory, not a fatal error — the checklist's intent is clear but the
    validator cannot enforce independence without a proposer id."""
    b = _taxonomy_bundle()
    b.proposer = None
    r = validate_bundle(b)
    assert r.structurally_valid
    assert any(
        a.code == ErrorCode.REVIEWER_INDEPENDENCE_NOT_ESTABLISHED
        for a in r.advisories
    )


def test_taxonomy_bundle_three_reviewers_fatal():
    """TAXONOMY_APPROVAL_CHECKLIST requires exactly two sign-offs."""
    b = _taxonomy_bundle()
    b.reviewers.append(
        ReviewerSignOff(
            reviewer="labeler_c_test",
            date=date(2026, 10, 25),
            decision=Decision.APPROVE,
            rationale="A third sign-off not permitted by the baseline template.",
            evidence_refs=["reports/synthetic.md"],
        )
    )
    r = validate_bundle(b)
    assert not r.structurally_valid
    assert any(
        f.code == ErrorCode.WRONG_REVIEWER_COUNT for f in r.fatal_errors
    )


def test_taxonomy_bundle_annotation_fields_advisory():
    """Setting annotation-only fields on a taxonomy bundle is advisory."""
    b = _taxonomy_bundle()
    b.task = AnnotationTask.PRIMARY_TYPE
    b.proposed_label_ids = ["lbl_hackathon"]
    r = validate_bundle(b)
    # Still structurally valid; just advisories.
    assert r.structurally_valid
    assert any(a.code == ErrorCode.MIXED_BUNDLE_FIELDS for a in r.advisories)


def test_annotation_bundle_taxonomy_fields_advisory():
    """Setting taxonomy-only fields on an annotation bundle is advisory."""
    b = _annotation_bundle()
    b.target_current_status = TaxonomyStatus.DRAFT
    r = validate_bundle(b)
    assert r.structurally_valid
    assert any(a.code == ErrorCode.MIXED_BUNDLE_FIELDS for a in r.advisories)


def test_report_is_json_serializable():
    """The report must be JSON-serializable without custom encoders."""
    import json

    b = _taxonomy_bundle()
    r = validate_bundle(b)
    # Should not raise
    json.dumps(r.to_dict())


def test_report_structurally_valid_property():
    """structurally_valid is derived from fatal_errors being empty."""
    b = _taxonomy_bundle()
    r = validate_bundle(b)
    assert r.structurally_valid == (len(r.fatal_errors) == 0)


def test_load_bundle_from_yaml(tmp_path: Path):
    """Round-trip through the YAML loader."""
    import yaml as yaml_mod

    from nlp_semantic.review import load_bundle

    payload = {
        "bundle_id": "evb_round_trip",
        "bundle_type": "taxonomy_promotion",
        "target_id": "lbl_hackathon",
        "target_current_status": "draft",
        "proposer": "labeler_proposer_test",
        "reviewers": [
            {
                "reviewer": "labeler_a_test",
                "date": "2026-10-25",
                "decision": "approve",
                "rationale": "Reviewed; approve.",
                "evidence_refs": ["reports/synthetic.md"],
            },
            {
                "reviewer": "labeler_b_test",
                "date": "2026-10-25",
                "decision": "approve",
                "rationale": "Independent review; approve.",
                "evidence_refs": ["reports/synthetic.md"],
            },
        ],
    }
    path = tmp_path / "bundle.yaml"
    path.write_text(yaml_mod.safe_dump(payload), encoding="utf-8")

    bundle = load_bundle(path)
    assert bundle.bundle_id == "evb_round_trip"
    report = validate_bundle(bundle)
    assert report.structurally_valid


def test_load_bundle_malformed_yaml_raises(tmp_path: Path):
    """Top-level non-mapping YAML raises BundleLoadError."""
    from nlp_semantic.review import BundleLoadError, load_bundle

    path = tmp_path / "bundle.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(BundleLoadError):
        load_bundle(path)


def test_load_bundle_missing_file_raises(tmp_path: Path):
    """Missing file surfaces a FileNotFoundError."""
    from nlp_semantic.review import load_bundle

    with pytest.raises(FileNotFoundError):
        load_bundle(tmp_path / "nonexistent.yaml")


def test_authenticated_is_always_false():
    """The report's `authenticated` property is False by design, always."""
    b = _taxonomy_bundle()
    r = validate_bundle(b)
    assert r.authenticated is False


def test_extra_fields_forbidden_on_bundle():
    """ConfigDict(extra='forbid') rejects unknown fields on the bundle."""
    with pytest.raises(ValidationError):
        EvidenceBundle(
            bundle_id="evb_x",
            bundle_type=BundleType.TAXONOMY_PROMOTION,
            target_id="lbl_hackathon",
            target_current_status=TaxonomyStatus.DRAFT,
            reviewers=[
                ReviewerSignOff(
                    reviewer="labeler_a_test",
                    date=date(2026, 10, 25),
                    decision=Decision.APPROVE,
                    rationale="x",
                ),
                ReviewerSignOff(
                    reviewer="labeler_b_test",
                    date=date(2026, 10, 25),
                    decision=Decision.APPROVE,
                    rationale="y",
                ),
            ],
            unknown_field="should_be_rejected",
        )
