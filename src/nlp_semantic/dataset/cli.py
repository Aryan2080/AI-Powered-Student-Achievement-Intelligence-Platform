"""Dataset CLI: ``validate``, ``stats``, ``split`` subcommands.

Shared contract (matches the Chunk 4 inventory CLI):

* ``PYTHONPATH=src`` required; the package is not pip-installed in
  Chunk 5. The project README documents the per-shell invocation.
* stdout carries machine-readable JSON (the full report).
* stderr carries a concise one-line human summary using an ASCII
  separator (``|``) so Windows code pages do not mojibake.
* Exit codes: ``0`` success, ``1`` dataset or build error, ``2`` CLI
  usage error (argparse).

Design decision — one module, three subcommands via argparse. No
``__main__.py`` router (same as the inventory CLI).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nlp_semantic.ingestion.registry import load_and_validate_sources

from nlp_semantic.schema import load_and_validate_taxonomy

from nlp_semantic.schema import AnnotationTask, TaxonomyStatus

from .agreement import compute_agreement
from .duplicates import find_duplicates
from .loader import DatasetError, load_dataset
from .splits import (
    DEFAULT_RATIOS,
    SplitFeasibilityError,
    generate_splits,
    write_splits,
)
from .stats import compute_stats
from .validator import training_ready_subset, validate_dataset


# Default locations are relative to the given --dataset-root (which is
# the hybrid_dataset directory itself). Pass an absolute path to any of
# these flags to override.
DEFAULT_PRIMARY = "labels/primary_taxonomy.yaml"
DEFAULT_DOMAIN = "labels/domain_tags.yaml"
DEFAULT_SOURCES = "metadata/sources.yaml"


def _resolve(root: Path, rel: str) -> Path:
    """Resolve a repo-relative path argument against ``<root>/...``."""
    p = Path(rel)
    if p.is_absolute():
        return p
    return root / rel


# ---- subcommand runners -----------------------------------------------------


def _cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.dataset_root)
    try:
        load_report = load_dataset(root)
    except (FileNotFoundError, NotADirectoryError, DatasetError) as e:
        print(f"dataset: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    source_report = load_and_validate_sources(_resolve(root, args.sources))
    primary = load_and_validate_taxonomy(_resolve(root, args.primary_taxonomy))
    domain = load_and_validate_taxonomy(_resolve(root, args.domain_taxonomy))

    rep = validate_dataset(
        records=load_report.records,
        annotations=load_report.annotations,
        sources=source_report.entries,
        primary_taxonomy=primary,
        domain_taxonomy=domain,
    )
    duplicates = find_duplicates(load_report.records)

    payload = {
        "load": {
            "records": len(load_report.records),
            "annotations": len(load_report.annotations),
            "record_files": load_report.record_files,
            "annotation_files": load_report.annotation_files,
        },
        "validation": rep.summary(),
        "duplicates": {
            "total_flagged": duplicates.total_flagged,
            "groups": [
                {"kind": g.kind, "key": g.key, "achievement_ids": g.achievement_ids}
                for g in duplicates.groups
            ],
        },
        "source_advisory": {
            "unknown_license_source_ids": source_report.unknown_license_ids,
            "unverified_source_ids": source_report.unverified_source_ids,
        },
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    status = "ok" if rep.is_valid else "fatal"
    print(
        f"dataset: {status} | records={len(load_report.records)} | "
        f"fatal={rep.fatal_count} | advisory={rep.advisory_count} | "
        f"duplicates_flagged={duplicates.total_flagged}",
        file=sys.stderr,
    )
    return 0 if rep.is_valid else 1


def _cmd_stats(args: argparse.Namespace) -> int:
    root = Path(args.dataset_root)
    try:
        load_report = load_dataset(root)
    except (FileNotFoundError, NotADirectoryError, DatasetError) as e:
        print(f"dataset: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    report = compute_stats(load_report.records)
    sys.stdout.write(json.dumps(report.to_dict(), indent=2) + "\n")
    print(
        f"dataset: stats | records={report.total_records} | "
        f"synthetic={report.synthetic_count} | real={report.real_count} | "
        f"primary_classes={len(report.primary_type_counts)}",
        file=sys.stderr,
    )
    return 0


def _parse_ratios(spec: str) -> dict[str, float]:
    """Parse 'train=0.7,val=0.15,test=0.15' into {name: float}."""
    out: dict[str, float] = {}
    for raw in spec.split(","):
        if "=" not in raw:
            raise argparse.ArgumentTypeError(
                f"ratio entry {raw!r} missing '='; use NAME=FLOAT"
            )
        name, value = raw.split("=", 1)
        name = name.strip()
        if not name:
            raise argparse.ArgumentTypeError("ratio entry has empty NAME")
        try:
            out[name] = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"ratio value {value!r} is not a valid float"
            ) from None
    return out


def _cmd_split(args: argparse.Namespace) -> int:
    root = Path(args.dataset_root)
    try:
        load_report = load_dataset(root)
    except (FileNotFoundError, NotADirectoryError, DatasetError) as e:
        print(f"dataset: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    try:
        result = generate_splits(
            load_report.records,
            seed=args.seed,
            ratios=args.ratios,
            exclude_synthetic=not args.include_synthetic,
        )
    except SplitFeasibilityError as e:
        print(f"dataset: SplitFeasibilityError: {e}", file=sys.stderr)
        return 1

    manifest = write_splits(result, root)
    sys.stdout.write(json.dumps(manifest.to_dict(), indent=2) + "\n")
    print(
        f"dataset: split written | seed={manifest.seed} | "
        f"sizes={manifest.actual_sizes} | "
        f"excluded_synthetic={manifest.excluded_synthetic_count} | "
        f"warnings={len(manifest.warnings)}",
        file=sys.stderr,
    )
    return 0


# ---- argument parsing -------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m nlp_semantic.dataset.cli",
        description=(
            "Dataset tooling: validate records against sources + taxonomies, "
            "compute class-distribution statistics, generate reproducible "
            "train/val/test splits. Read-only against raw data."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    for name in ("validate", "stats", "split", "readiness"):
        s = sub.add_parser(name, help=f"{name} subcommand")
        s.add_argument(
            "dataset_root",
            help="Path to the hybrid_dataset root (the directory that contains "
            "dataset/, metadata/, labels/).",
        )
        if name in ("validate", "readiness"):
            s.add_argument("--sources", default=DEFAULT_SOURCES,
                           help="Relative path to sources.yaml (default: %(default)s)")
            s.add_argument("--primary-taxonomy", default=DEFAULT_PRIMARY,
                           help="Relative path to primary_taxonomy.yaml")
            s.add_argument("--domain-taxonomy", default=DEFAULT_DOMAIN,
                           help="Relative path to domain_tags.yaml")
        if name == "readiness":
            s.add_argument(
                "--strict",
                action="store_true",
                help="Opt-in CI gate: exit 1 if machine-checkable readiness "
                     "criteria are not met. Default mode exits 0 on a completed "
                     "assessment regardless of readiness state.",
            )
            s.add_argument(
                "--min-records-per-approved-label",
                type=int,
                default=1,
                help="Strict-mode floor: minimum eligible records per approved "
                     "label (per task). Default 1 is an eligibility floor, "
                     "NOT a quality threshold.",
            )
        if name == "split":
            s.add_argument("--seed", type=int, default=0,
                           help="Deterministic shuffle seed (default: 0)")
            s.add_argument(
                "--ratios",
                type=_parse_ratios,
                default=dict(DEFAULT_RATIOS),
                help="Comma-separated split=ratio pairs; must sum to 1 "
                     "(default: train=0.70,val=0.15,test=0.15)",
            )
            s.add_argument(
                "--include-synthetic",
                action="store_true",
                help="Include is_synthetic records in the splits "
                     "(default: synthetic records are excluded)",
            )
    return p


_READINESS_DISCLAIMER = (
    "Structural validation does not verify factual correctness of labels, "
    "legal compliance of sources, or representativeness of the dataset. "
    "Human review required."
)


def _cmd_readiness(args: argparse.Namespace) -> int:
    """Assemble a per-task readiness report.

    Default mode: exit 0 on completed assessment, regardless of readiness.
    --strict: exit 1 if the machine-checkable criteria are not met.
    """
    root = Path(args.dataset_root)
    try:
        load_report = load_dataset(root)
        source_report = load_and_validate_sources(_resolve(root, args.sources))
        primary = load_and_validate_taxonomy(_resolve(root, args.primary_taxonomy))
        domain = load_and_validate_taxonomy(_resolve(root, args.domain_taxonomy))
    except (FileNotFoundError, NotADirectoryError, DatasetError) as e:
        print(f"dataset: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    validation = validate_dataset(
        records=load_report.records,
        annotations=load_report.annotations,
        sources=source_report.entries,
        primary_taxonomy=primary,
        domain_taxonomy=domain,
    )

    # Approved label counts per task.
    approved_primary = [e for e in primary if e.status == TaxonomyStatus.APPROVED]
    approved_domain = [e for e in domain if e.status == TaxonomyStatus.APPROVED]
    approved_label_count = {
        "primary_type": len(approved_primary),
        "domain_tags": len(approved_domain),
    }

    # Eligible training-ready records per task.
    eligible_primary = training_ready_subset(
        load_report.records,
        sources=source_report.entries,
        primary_taxonomy=primary,
        task=AnnotationTask.PRIMARY_TYPE,
    )
    eligible_domain = training_ready_subset(
        load_report.records,
        sources=source_report.entries,
        domain_taxonomy=domain,
        task=AnnotationTask.DOMAIN_TAGS,
    )
    eligible_record_count = {
        "primary_type": len(eligible_primary),
        "domain_tags": len(eligible_domain),
    }

    agreement = {
        "primary_type": compute_agreement(
            load_report.annotations, task=AnnotationTask.PRIMARY_TYPE
        ).to_dict(),
        "domain_tags": compute_agreement(
            load_report.annotations, task=AnnotationTask.DOMAIN_TAGS
        ).to_dict(),
    }

    # Machine-checkable readiness criteria. Deliberately minimal:
    # structural validity AND >= 1 approved label AND >= 1 eligible record
    # per task. Representativeness, correctness, legality stay with humans.
    structurally_valid = validation.is_valid
    is_training_ready = {
        "primary_type": bool(
            structurally_valid
            and approved_label_count["primary_type"] >= 1
            and eligible_record_count["primary_type"] >= 1
        ),
        "domain_tags": bool(
            structurally_valid
            and approved_label_count["domain_tags"] >= 1
            and eligible_record_count["domain_tags"] >= 1
        ),
    }
    # Two explicit aggregates. ``is_training_ready`` carries only the
    # per-task booleans so the field name is unambiguous.
    #   - any_task_training_ready: True if either task meets its
    #     machine-checkable prerequisites. This is the strict-mode gate.
    #   - all_tasks_training_ready: True only if BOTH tasks meet them.
    # Neither aggregate implies statistical sufficiency, factual
    # correctness, or legal compliance; see the standing disclaimer in
    # the ``notes`` list.
    any_task_training_ready = any(
        is_training_ready[t] for t in ("primary_type", "domain_tags")
    )
    all_tasks_training_ready = all(
        is_training_ready[t] for t in ("primary_type", "domain_tags")
    )

    # Blockers (structured; one entry per failed machine-checkable criterion).
    blockers: list[dict] = []
    if not structurally_valid:
        blockers.append({
            "code": "structural_validation_failed",
            "detail": f"{validation.fatal_count} fatal findings in validate_dataset",
        })
    for t_name in ("primary_type", "domain_tags"):
        if approved_label_count[t_name] == 0:
            blockers.append({
                "code": "no_approved_labels",
                "task": t_name,
                "detail": f"0 {t_name} labels at status=approved",
            })
        if eligible_record_count[t_name] == 0:
            blockers.append({
                "code": "no_eligible_records",
                "task": t_name,
                "detail": f"0 records pass training_ready_subset for {t_name}",
            })

    # Strict-mode additional check.
    strict_blockers: list[dict] = []
    if args.strict:
        min_n = args.min_records_per_approved_label
        for t_name, eligible_list, approved_list in (
            ("primary_type", eligible_primary, approved_primary),
            ("domain_tags", eligible_domain, approved_domain),
        ):
            if approved_list and len(eligible_list) < min_n * len(approved_list):
                strict_blockers.append({
                    "code": "strict_minimum_records_per_approved_label",
                    "task": t_name,
                    "detail": (
                        f"{len(eligible_list)} eligible records < "
                        f"{min_n} per approved label x "
                        f"{len(approved_list)} approved labels = "
                        f"{min_n * len(approved_list)} required"
                    ),
                })

    warnings: list[dict] = []
    if source_report.unknown_license_ids:
        warnings.append({
            "code": "unknown_license",
            "source_ids": list(source_report.unknown_license_ids),
        })
    if source_report.unverified_source_ids:
        warnings.append({
            "code": "unverified_source",
            "source_ids": list(source_report.unverified_source_ids),
        })
    for t_name in ("primary_type", "domain_tags"):
        self_re = agreement[t_name].get("self_reannotation_count", 0)
        if self_re:
            warnings.append({
                "code": "self_reannotation",
                "task": t_name,
                "count": self_re,
            })

    payload = {
        "assessment_status": "completed",
        "structurally_valid": structurally_valid,
        "approved_label_count": approved_label_count,
        "eligible_record_count": eligible_record_count,
        "agreement_status": agreement,
        "is_training_ready": is_training_ready,
        "any_task_training_ready": any_task_training_ready,
        "all_tasks_training_ready": all_tasks_training_ready,
        "blockers": blockers + strict_blockers,
        "warnings": warnings,
        "strict": {
            "enabled": bool(args.strict),
            "min_records_per_approved_label": args.min_records_per_approved_label,
        },
        "notes": [_READINESS_DISCLAIMER],
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")

    # Preserve the documented strict-mode gating semantics: strict mode
    # exits 1 when NO task is ready (i.e. not any_task_training_ready) OR
    # when strict-specific blockers fired.
    any_ready_label = "ready" if any_task_training_ready else "not_ready"
    all_ready_label = "ready" if all_tasks_training_ready else "not_ready"
    print(
        f"dataset: readiness | any_task={any_ready_label} | "
        f"all_tasks={all_ready_label} | "
        f"approved(pt={approved_label_count['primary_type']},"
        f"dt={approved_label_count['domain_tags']}) | "
        f"eligible(pt={eligible_record_count['primary_type']},"
        f"dt={eligible_record_count['domain_tags']}) | "
        f"blockers={len(payload['blockers'])} | "
        f"strict={'on' if args.strict else 'off'}",
        file=sys.stderr,
    )

    if args.strict and (strict_blockers or not any_task_training_ready):
        return 1
    return 0


# ---- entry point ------------------------------------------------------------


_DISPATCH = {
    "validate": _cmd_validate,
    "stats": _cmd_stats,
    "split": _cmd_split,
    "readiness": _cmd_readiness,
}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handler = _DISPATCH[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
