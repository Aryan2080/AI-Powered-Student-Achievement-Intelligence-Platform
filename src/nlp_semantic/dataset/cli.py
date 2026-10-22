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

from .duplicates import find_duplicates
from .loader import DatasetError, load_dataset
from .splits import (
    DEFAULT_RATIOS,
    SplitFeasibilityError,
    generate_splits,
    write_splits,
)
from .stats import compute_stats
from .validator import validate_dataset


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

    for name in ("validate", "stats", "split"):
        s = sub.add_parser(name, help=f"{name} subcommand")
        s.add_argument(
            "dataset_root",
            help="Path to the hybrid_dataset root (the directory that contains "
            "dataset/, metadata/, labels/).",
        )
        if name == "validate":
            s.add_argument("--sources", default=DEFAULT_SOURCES,
                           help="Relative path to sources.yaml (default: %(default)s)")
            s.add_argument("--primary-taxonomy", default=DEFAULT_PRIMARY,
                           help="Relative path to primary_taxonomy.yaml")
            s.add_argument("--domain-taxonomy", default=DEFAULT_DOMAIN,
                           help="Relative path to domain_tags.yaml")
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


# ---- entry point ------------------------------------------------------------


_DISPATCH = {
    "validate": _cmd_validate,
    "stats": _cmd_stats,
    "split": _cmd_split,
}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handler = _DISPATCH[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
