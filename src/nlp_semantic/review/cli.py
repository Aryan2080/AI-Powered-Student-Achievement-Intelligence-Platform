"""Reviewer-evidence bundle CLI: ``validate`` subcommand.

Shared contract with the dataset and ingestion CLIs:

* ``PYTHONPATH=src`` required; no entry-point installation.
* stdout carries machine-readable JSON (the full :class:`ValidationReport`).
* stderr carries a concise one-line human summary with an ASCII ``|``
  separator so Windows code pages do not mojibake.
* Exit codes: ``0`` structurally valid, ``1`` fatal error or load
  failure, ``2`` CLI usage error (argparse).

The CLI does **not** authenticate reviewer identity and does **not**
approve any status; see
:mod:`nlp_semantic.review.evidence_bundle` for the fail-closed
contract.
"""
from __future__ import annotations

import argparse
import json
import sys

from pydantic import ValidationError

from .evidence_bundle import BundleLoadError, load_bundle, validate_bundle


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        bundle = load_bundle(args.bundle_path)
    except FileNotFoundError as e:
        print(f"review-evidence: FileNotFoundError: {e}", file=sys.stderr)
        return 1
    except BundleLoadError as e:
        print(f"review-evidence: BundleLoadError: {e}", file=sys.stderr)
        return 1
    except ValidationError as e:
        # Per-entry Pydantic failures carry the structural message.
        print(f"review-evidence: ValidationError: {e}", file=sys.stderr)
        return 1

    report = validate_bundle(bundle)
    sys.stdout.write(json.dumps(report.to_dict(), indent=2) + "\n")

    status = "ok" if report.structurally_valid else "fatal"
    print(
        f"review-evidence: {status} | bundle={bundle.bundle_id} | "
        f"type={report.bundle_type} | target={report.target_id} | "
        f"fatal={len(report.fatal_errors)} | "
        f"advisory={len(report.advisories)} | "
        f"limitations={len(report.limitations)} | "
        f"authenticated={report.authenticated}",
        file=sys.stderr,
    )
    return 0 if report.structurally_valid else 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m nlp_semantic.review.cli",
        description=(
            "Validate reviewer-evidence bundles against structural "
            "requirements from TAXONOMY_APPROVAL_CHECKLIST.md and "
            "ANNOTATION_GUIDELINES.md. Does NOT authenticate reviewer "
            "identity, approve taxonomy labels, verify annotations, or "
            "approve sources."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)
    v = sub.add_parser(
        "validate",
        help="validate one evidence bundle YAML file",
    )
    v.add_argument(
        "bundle_path",
        help="path to the evidence bundle YAML",
    )
    return p


_DISPATCH = {"validate": _cmd_validate}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return _DISPATCH[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
