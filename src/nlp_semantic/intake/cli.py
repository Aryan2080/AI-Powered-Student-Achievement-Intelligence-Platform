"""Intake CLI: ``ingest | validate | status | duplicates`` subcommands.

Shared contract with the dataset / ingestion / review CLIs:

* ``PYTHONPATH=src`` required.
* stdout carries machine-readable JSON.
* stderr carries a concise one-line summary with ASCII ``|`` separators.
* Exit codes: ``0`` success, ``1`` runtime / validation failure, ``2``
  argparse usage error.

The CLI does **not** authenticate reviewer identity, approve sources,
promote taxonomy labels, or verify annotations.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date as _date
from pathlib import Path

import yaml
from pydantic import ValidationError

from nlp_semantic.dataset.loader import load_dataset
from nlp_semantic.ingestion.registry import load_and_validate_sources
from nlp_semantic.schema import load_and_validate_taxonomy

from .pipeline import (
    DEFAULT_EVIDENCE_ROOT,
    DEFAULT_MANIFEST_DIR,
    AchievementCandidate,
    IntakeError,
    find_duplicate_hashes,
    ingest_evidence,
    list_intake_entries,
    load_intake_entry,
    make_candidate_id,
    validate_intake_entry,
)
from .create_achievement import (
    CreateAchievementError,
    create_achievement_from_review,
)
from .promote_evidence import (
    DEFAULT_EVIDENCE_DOCUMENTS_ROOT,
    DEFAULT_EVIDENCE_RECORD_DIR,
    PromoteEvidenceError,
    list_evidence_records,
    load_evidence_record,
    promote_evidence,
)
from .review import (
    CandidateDecision,
    CandidateReviewError,
    load_candidate_review,
    review_candidate,
)


def _entry_to_json(entry) -> dict:
    return {
        "intake_id": entry.intake_id,
        "original_filename": entry.original_filename,
        "file_type": entry.file_type.value,
        "relative_path": entry.relative_path,
        "sha256": entry.sha256,
        "size_bytes": entry.size_bytes,
        "intake_timestamp": entry.intake_timestamp.isoformat(),
        "source_id": entry.source_id,
        "achievement_candidate_ids": list(entry.achievement_candidate_ids),
        "proposer": entry.proposer,
        "status": entry.status.value,
        "validation_findings": [f.to_dict() for f in entry.validation_findings],
    }


# ---- subcommands ----------------------------------------------------------


def _cmd_ingest(args: argparse.Namespace) -> int:
    try:
        candidate_ids = args.candidate_id or []
        result = ingest_evidence(
            args.source_file,
            evidence_root=args.evidence_root,
            manifest_dir=args.manifest_dir,
            source_id=args.source_id,
            achievement_candidate_ids=candidate_ids,
            proposer=args.proposer,
        )
    except (FileNotFoundError, IntakeError, ValueError, ValidationError) as e:
        print(f"intake: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    payload = {
        "entry": _entry_to_json(result.entry),
        "manifest_path": str(result.manifest_path),
        "stored_file_path": str(result.stored_file_path),
        "duplicate_of_intake_ids": list(result.duplicate_of_intake_ids),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    print(
        f"intake: ingested | intake_id={result.entry.intake_id} | "
        f"sha256={result.entry.sha256[:16]}... | "
        f"size={result.entry.size_bytes} | "
        f"duplicates={len(result.duplicate_of_intake_ids)} | "
        f"findings={len(result.entry.validation_findings)}",
        file=sys.stderr,
    )
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        entry = load_intake_entry(args.manifest_file)
    except (FileNotFoundError, IntakeError, ValidationError) as e:
        print(f"intake: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    findings = validate_intake_entry(
        entry,
        evidence_root=args.evidence_root,
        sources_yaml=args.sources_yaml,
    )
    all_findings = list(entry.validation_findings) + findings
    is_ok = all(
        f.code
        not in {
            "FILE_NOT_FOUND",
            "HASH_MISMATCH_ON_DISK",
            "UNKNOWN_SOURCE_REFERENCE",
            "UNKNOWN_ACHIEVEMENT_REFERENCE",
        }
        for f in all_findings
    )
    payload = {
        "entry": _entry_to_json(entry),
        "cross_reference_findings": [f.to_dict() for f in findings],
        "ok": is_ok,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    print(
        f"intake: {'ok' if is_ok else 'fatal'} | "
        f"intake_id={entry.intake_id} | "
        f"cross_findings={len(findings)}",
        file=sys.stderr,
    )
    return 0 if is_ok else 1


def _cmd_status(args: argparse.Namespace) -> int:
    try:
        entries = list_intake_entries(args.manifest_dir)
    except (FileNotFoundError, IntakeError, ValidationError) as e:
        print(f"intake: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    payload = {
        "count": len(entries),
        "entries": [_entry_to_json(e) for e in entries],
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    print(
        f"intake: status | count={len(entries)}",
        file=sys.stderr,
    )
    return 0


def _cmd_duplicates(args: argparse.Namespace) -> int:
    try:
        groups = find_duplicate_hashes(args.manifest_dir)
    except (FileNotFoundError, IntakeError, ValidationError) as e:
        print(f"intake: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    payload = {
        "duplicate_groups": {h: list(ids) for h, ids in groups.items()},
        "total_duplicate_hashes": len(groups),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    print(
        f"intake: duplicates | groups={len(groups)}",
        file=sys.stderr,
    )
    return 0


# ---- parser ---------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m nlp_semantic.intake.cli",
        description=(
            "Reviewer-gated evidence intake pipeline. Does NOT "
            "authenticate reviewer identity, approve sources, promote "
            "taxonomy, or verify annotations."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    ing = sub.add_parser(
        "ingest",
        help="intake a reviewer-supplied evidence file",
    )
    ing.add_argument("source_file", help="path to the evidence file")
    ing.add_argument(
        "--evidence-root",
        default=DEFAULT_EVIDENCE_ROOT,
        help="raw-file store (default: %(default)s)",
    )
    ing.add_argument(
        "--manifest-dir",
        default=DEFAULT_MANIFEST_DIR,
        help="manifest directory (default: %(default)s)",
    )
    ing.add_argument(
        "--source-id",
        default=None,
        help="optional src_<hex> reference",
    )
    ing.add_argument(
        "--candidate-id",
        action="append",
        default=[],
        help=(
            "optional cand_<hex> reference; repeat to add more than one"
        ),
    )
    ing.add_argument(
        "--proposer",
        default=None,
        help="optional pseudonym of the reviewer submitting the evidence",
    )

    val = sub.add_parser(
        "validate",
        help="validate one intake manifest",
    )
    val.add_argument("manifest_file", help="path to the manifest YAML")
    val.add_argument(
        "--evidence-root",
        default=DEFAULT_EVIDENCE_ROOT,
        help="raw-file store for the on-disk hash check (default: %(default)s)",
    )
    val.add_argument(
        "--sources-yaml",
        default=None,
        help=(
            "optional sources.yaml path for source_id existence check"
        ),
    )

    stat = sub.add_parser(
        "status",
        help="list intake entries under a manifest directory",
    )
    stat.add_argument(
        "--manifest-dir",
        default=DEFAULT_MANIFEST_DIR,
        help="manifest directory (default: %(default)s)",
    )

    dup = sub.add_parser(
        "duplicates",
        help="report hashes shared by multiple intake entries",
    )
    dup.add_argument(
        "--manifest-dir",
        default=DEFAULT_MANIFEST_DIR,
        help="manifest directory (default: %(default)s)",
    )

    # review-candidate (Chunk 7.45): ACCEPT and REJECT only.
    rev = sub.add_parser(
        "review-candidate",
        help=(
            "run an ACCEPT or REJECT review on an in-memory "
            "AchievementCandidate (Chunk 7.45)"
        ),
    )
    rev.add_argument(
        "--decision",
        required=True,
        choices=["accept", "reject"],
        help="ACCEPT or REJECT only; REVISE and DEFER are deferred",
    )
    rev.add_argument(
        "--reviewer",
        required=True,
        help="reviewer pseudonym (same convention as Annotation.annotator)",
    )
    rev.add_argument(
        "--rationale",
        required=True,
        help="2-3 sentence rationale",
    )
    rev.add_argument(
        "--output-dir",
        default="hybrid_dataset/dataset/candidate_reviews",
        help="where CandidateReview files are written (default: %(default)s)",
    )
    # Candidate construction (in-memory; no persistence yet).
    rev.add_argument("--candidate-id", default=None, help="optional cand_<hex>")
    rev.add_argument(
        "--intake-id",
        action="append",
        default=[],
        help="repeatable intk_<hex> reference the candidate carries",
    )
    rev.add_argument(
        "--candidate-source-id",
        default=None,
        help="optional src_<hex> on the candidate itself",
    )
    rev.add_argument(
        "--proposed-text",
        default=None,
        help="candidate.proposed_achievement_text",
    )
    rev.add_argument(
        "--proposed-primary-type",
        default=None,
        help="candidate.proposed_primary_type (lbl_<name>)",
    )
    rev.add_argument(
        "--proposer",
        default=None,
        help="candidate.proposer pseudonym (must differ from --reviewer)",
    )
    # Reviewer attestations (used on ACCEPT).
    rev.add_argument(
        "--source-id",
        default=None,
        help="override the candidate's source_id for this acceptance",
    )
    rev.add_argument(
        "--source-record-id",
        default=None,
        help="REQUIRED on ACCEPT (P-3)",
    )
    rev.add_argument(
        "--primary-type",
        default=None,
        help="override proposed_primary_type (lbl_<name>)",
    )
    rev.add_argument(
        "--domain-tag",
        action="append",
        default=[],
        help="repeatable domain tag (lbl_domain_<name>)",
    )
    rev.add_argument("--level", default=None)
    rev.add_argument("--outcome", default=None)
    rev.add_argument("--event-name", default=None)
    rev.add_argument("--organization", default=None)
    rev.add_argument(
        "--achievement-date",
        default=None,
        help="ISO date (YYYY-MM-DD)",
    )
    rev.add_argument("--rank", type=int, default=None)
    rev.add_argument(
        "--skill",
        action="append",
        default=[],
        help="repeatable skill string",
    )
    rev.add_argument("--evidence-id", default=None, help="evd_<hex>")
    # Validation inputs for the preconditions.
    rev.add_argument(
        "--intake-manifest-dir",
        default=DEFAULT_MANIFEST_DIR,
        help="where to find intake manifests for P-2 (default: %(default)s)",
    )
    rev.add_argument(
        "--evidence-root",
        default=DEFAULT_EVIDENCE_ROOT,
        help="where intake files live on disk for P-2 (default: %(default)s)",
    )
    rev.add_argument(
        "--sources-yaml",
        default=None,
        help="sources.yaml for source cross-references",
    )
    rev.add_argument(
        "--primary-taxonomy-yaml",
        default=None,
        help="primary_taxonomy.yaml for P-5",
    )
    rev.add_argument(
        "--domain-taxonomy-yaml",
        default=None,
        help="domain_tags.yaml for P-6",
    )
    rev.add_argument(
        "--dataset-root",
        default=None,
        help="dataset root for P-4 duplicate-pair check (uses load_dataset)",
    )

    # promote-evidence (Chunk 7.46)
    prom = sub.add_parser(
        "promote-evidence",
        help=(
            "promote an IntakeEntry to an Evidence row by copying its file "
            "under evidence_documents/ and writing an Evidence YAML record "
            "(Chunk 7.46)"
        ),
    )
    prom.add_argument(
        "intake_manifest",
        help="path to the intake manifest YAML (e.g. hybrid_dataset/intake/manifests/intk_<hex>.yaml)",
    )
    prom.add_argument(
        "--reviewer",
        required=True,
        help="reviewer pseudonym (must differ from the intake's proposer)",
    )
    prom.add_argument(
        "--evidence-root",
        default=DEFAULT_EVIDENCE_ROOT,
        help="on-disk root where intake files currently live (default: %(default)s)",
    )
    prom.add_argument(
        "--evidence-documents-root",
        default=DEFAULT_EVIDENCE_DOCUMENTS_ROOT,
        help="on-disk destination root for promoted evidence (default: %(default)s)",
    )
    prom.add_argument(
        "--evidence-record-dir",
        default=DEFAULT_EVIDENCE_RECORD_DIR,
        help="directory for per-Evidence YAML records (default: %(default)s)",
    )
    prom.add_argument(
        "--document-type",
        default=None,
        help="optional short descriptor (e.g. 'press_release', 'certificate')",
    )

    # create-achievement (Chunk 7.47)
    conv = sub.add_parser(
        "create-achievement",
        help=(
            "convert an ACCEPT-ed CandidateReview into an Achievement row "
            "written to a batch YAML (Chunk 7.47)"
        ),
    )
    conv.add_argument(
        "review_file",
        help="path to the CandidateReview YAML (produced by review-candidate)",
    )
    conv.add_argument(
        "--achievement-text",
        required=True,
        help=(
            "achievement_text for the new Achievement; typically the "
            "candidate's proposed_achievement_text"
        ),
    )
    conv.add_argument(
        "--output-batch-file",
        required=True,
        help="target batch YAML (e.g. hybrid_dataset/dataset/records/batch_02_<slug>.yaml)",
    )
    conv.add_argument(
        "--sources-yaml",
        required=True,
        help="sources.yaml for source cross-reference",
    )
    conv.add_argument(
        "--primary-taxonomy-yaml",
        required=True,
        help="primary_taxonomy.yaml for taxonomy cross-reference",
    )
    conv.add_argument(
        "--domain-taxonomy-yaml",
        default=None,
        help="optional domain_tags.yaml",
    )
    conv.add_argument(
        "--dataset-root",
        default=None,
        help="dataset root to load existing records from (P-4 duplicate check)",
    )
    conv.add_argument(
        "--evidence-record-dir",
        default=DEFAULT_EVIDENCE_RECORD_DIR,
        help=(
            "directory of Evidence YAML records for the attested_evidence_id "
            "cross-reference"
        ),
    )
    conv.add_argument(
        "--evidence-documents-root",
        default=DEFAULT_EVIDENCE_DOCUMENTS_ROOT,
        help="on-disk root containing the Evidence files",
    )
    conv.add_argument(
        "--intake-manifest-dir",
        default=None,
        help=(
            "optional intake manifest directory; when supplied, the function "
            "re-hashes the Evidence file against the originating intake"
        ),
    )

    return p


def _cmd_review_candidate(args: argparse.Namespace) -> int:
    """Run a Chunk 7.45 ACCEPT/REJECT review against an in-memory Candidate.

    The CLI constructs an :class:`AchievementCandidate` from the per-call
    flags, then invokes :func:`review_candidate`. Candidate persistence
    is deferred to a later chunk; the CandidateReview is the only
    record this command writes to disk.
    """
    try:
        decision = CandidateDecision(args.decision)
    except ValueError:
        print(
            f"intake: ValueError: unsupported decision {args.decision!r}; "
            "must be 'accept' or 'reject'",
            file=sys.stderr,
        )
        return 1

    # Build the AchievementCandidate from CLI flags.
    try:
        candidate = AchievementCandidate(
            candidate_id=(args.candidate_id or make_candidate_id()),
            evidence_intake_ids=list(args.intake_id or []),
            source_id=args.candidate_source_id,
            proposed_achievement_text=args.proposed_text,
            proposed_primary_type=args.proposed_primary_type,
            proposer=args.proposer,
        )
    except ValidationError as e:
        print(f"intake: ValidationError (candidate): {e}", file=sys.stderr)
        return 1

    # Optional validation inputs (needed for ACCEPT preconditions).
    sources = None
    primary_tax = None
    domain_tax = None
    existing_records = None
    if args.sources_yaml:
        try:
            sources = load_and_validate_sources(args.sources_yaml).entries
        except Exception as e:
            print(f"intake: sources load failed: {e}", file=sys.stderr)
            return 1
    if args.primary_taxonomy_yaml:
        try:
            primary_tax = load_and_validate_taxonomy(args.primary_taxonomy_yaml)
        except Exception as e:
            print(f"intake: primary taxonomy load failed: {e}", file=sys.stderr)
            return 1
    if args.domain_taxonomy_yaml:
        try:
            domain_tax = load_and_validate_taxonomy(args.domain_taxonomy_yaml)
        except Exception as e:
            print(f"intake: domain taxonomy load failed: {e}", file=sys.stderr)
            return 1
    if args.dataset_root:
        try:
            existing_records = load_dataset(args.dataset_root).records
        except Exception as e:
            print(f"intake: dataset load failed: {e}", file=sys.stderr)
            return 1

    achievement_date = None
    if args.achievement_date:
        try:
            achievement_date = _date.fromisoformat(args.achievement_date)
        except ValueError as e:
            print(f"intake: ValueError (achievement-date): {e}", file=sys.stderr)
            return 1

    try:
        review = review_candidate(
            candidate,
            decision=decision,
            reviewer=args.reviewer,
            rationale=args.rationale,
            output_dir=args.output_dir,
            source_id=args.source_id,
            source_record_id=args.source_record_id,
            primary_type=args.primary_type,
            domain_tags=args.domain_tag or None,
            level=args.level,
            outcome=args.outcome,
            event_name=args.event_name,
            organization=args.organization,
            achievement_date=achievement_date,
            rank=args.rank,
            skills=args.skill or None,
            evidence_id=args.evidence_id,
            intake_manifest_dir=args.intake_manifest_dir,
            evidence_root=args.evidence_root,
            sources=sources,
            primary_taxonomy=primary_tax,
            domain_taxonomy=domain_tax,
            existing_records=existing_records,
        )
    except CandidateReviewError as e:
        payload = {
            "ok": False,
            "message": str(e),
            "findings": [f.to_dict() for f in e.findings],
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        print(
            f"intake: review-candidate fatal | findings={len(e.findings)}",
            file=sys.stderr,
        )
        return 1
    except ValidationError as e:
        print(f"intake: ValidationError (review): {e}", file=sys.stderr)
        return 1

    payload = {
        "ok": True,
        "review_id": review.review_id,
        "candidate_id": review.candidate_id,
        "decision": review.decision.value,
        "reviewer": review.reviewer,
        "created_at": review.created_at.isoformat(),
        "attested_source_record_id": review.attested_source_record_id,
        "attested_primary_type": review.attested_primary_type,
        "attested_evidence_id": review.attested_evidence_id,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    print(
        f"intake: review-candidate ok | review_id={review.review_id} | "
        f"decision={review.decision.value} | "
        f"candidate_id={review.candidate_id}",
        file=sys.stderr,
    )
    return 0


def _cmd_promote_evidence(args: argparse.Namespace) -> int:
    """Promote one intake entry to an Evidence row (Chunk 7.46)."""
    manifest_path = Path(args.intake_manifest)
    try:
        intake = load_intake_entry(manifest_path)
    except (FileNotFoundError, IntakeError, ValidationError) as e:
        print(f"intake: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    try:
        result = promote_evidence(
            intake,
            reviewer=args.reviewer,
            evidence_root=args.evidence_root,
            evidence_documents_root=args.evidence_documents_root,
            evidence_record_dir=args.evidence_record_dir,
            document_type=args.document_type,
        )
    except PromoteEvidenceError as e:
        payload = {
            "ok": False,
            "message": str(e),
            "findings": [f.to_dict() for f in e.findings],
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        print(
            f"intake: promote-evidence fatal | findings={len(e.findings)}",
            file=sys.stderr,
        )
        return 1
    except (ValidationError, ValueError) as e:
        print(
            f"intake: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 1

    payload = {
        "ok": True,
        "evidence_id": result.evidence.evidence_id,
        "source_intake_id": result.source_intake_id,
        "source_file_path": str(result.source_file_path),
        "destination_file_path": str(result.destination_file_path),
        "evidence_record_path": str(result.evidence_record_path),
        "relative_path": result.evidence.relative_path,
        "review_status": result.evidence.review_status.value,
        "extraction_method": result.evidence.extraction_method.value,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    print(
        f"intake: promote-evidence ok | evidence_id={result.evidence.evidence_id} | "
        f"intake_id={result.source_intake_id}",
        file=sys.stderr,
    )
    return 0


def _cmd_create_achievement(args: argparse.Namespace) -> int:
    """Convert an ACCEPT-ed CandidateReview into an Achievement row (Chunk 7.47)."""
    try:
        review = load_candidate_review(args.review_file)
    except (FileNotFoundError, ValueError, ValidationError) as e:
        print(f"intake: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    # Load validation inputs
    try:
        sources = load_and_validate_sources(args.sources_yaml).entries
        primary = load_and_validate_taxonomy(args.primary_taxonomy_yaml)
    except Exception as e:
        print(f"intake: taxonomy/sources load failed: {e}", file=sys.stderr)
        return 1
    domain = None
    if args.domain_taxonomy_yaml:
        try:
            domain = load_and_validate_taxonomy(args.domain_taxonomy_yaml)
        except Exception as e:
            print(f"intake: domain taxonomy load failed: {e}", file=sys.stderr)
            return 1

    existing_records = None
    if args.dataset_root:
        try:
            existing_records = load_dataset(args.dataset_root).records
        except Exception as e:
            print(f"intake: dataset load failed: {e}", file=sys.stderr)
            return 1

    existing_evidence = None
    if args.evidence_record_dir:
        try:
            existing_evidence = list_evidence_records(args.evidence_record_dir)
        except Exception as e:
            print(f"intake: evidence load failed: {e}", file=sys.stderr)
            return 1

    try:
        result = create_achievement_from_review(
            review,
            achievement_text=args.achievement_text,
            output_batch_file=args.output_batch_file,
            sources=sources,
            primary_taxonomy=primary,
            domain_taxonomy=domain,
            existing_records=existing_records,
            existing_evidence=existing_evidence,
            evidence_documents_root=args.evidence_documents_root,
            intake_manifest_dir=args.intake_manifest_dir,
        )
    except CreateAchievementError as e:
        payload = {
            "ok": False,
            "message": str(e),
            "findings": [f.to_dict() for f in e.findings],
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        print(
            f"intake: create-achievement fatal | findings={len(e.findings)}",
            file=sys.stderr,
        )
        return 1
    except (ValidationError, ValueError) as e:
        print(f"intake: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    payload = {
        "ok": True,
        "achievement_id": result.achievement.achievement_id,
        "source_id": result.achievement.source_id,
        "source_record_id": result.achievement.source_record_id,
        "primary_type": result.achievement.primary_type,
        "annotation_status": {
            "primary_type": result.achievement.annotation_status.primary_type.value,
            "domain_tags": result.achievement.annotation_status.domain_tags.value,
        },
        "linked_review_id": result.linked_review_id,
        "linked_evidence_id": result.linked_evidence_id,
        "batch_file": str(result.batch_file),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    print(
        f"intake: create-achievement ok | "
        f"achievement_id={result.achievement.achievement_id} | "
        f"batch_file={result.batch_file!s}",
        file=sys.stderr,
    )
    return 0


_DISPATCH = {
    "ingest": _cmd_ingest,
    "validate": _cmd_validate,
    "status": _cmd_status,
    "duplicates": _cmd_duplicates,
    "review-candidate": _cmd_review_candidate,
    "promote-evidence": _cmd_promote_evidence,
    "create-achievement": _cmd_create_achievement,
}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return _DISPATCH[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
