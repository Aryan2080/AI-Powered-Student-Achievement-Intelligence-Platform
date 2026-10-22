"""Read-only, metadata-only inventory of ``<root>/raw/``.

Guarantees:

- Never opens or reads file contents. Uses ``Path.stat`` /
  ``DirEntry.stat`` with ``follow_symlinks=False`` only.
- Never follows symlinked files or symlinked directories.
- Never creates, deletes, renames, or modifies files.
- Every per-entry failure is captured as a structured
  :class:`InventoryWarning` and the scan continues. A scan that produced
  warnings is **not** silently presented as fully successful; callers
  must inspect ``report.warnings``.

Known limits (restated here so callers see them in the module docstring):

- Pure-metadata inspection cannot be atomic. Files may be created,
  deleted, renamed, or truncated between any two syscalls. The report is
  a best-effort view of filesystem metadata at scan time.
- On an actively hostile filesystem, a writer racing every syscall can
  present a well-formed entry whose ``size_bytes`` / ``modified_at``
  reflect a different file than the one the enumerator saw. Addressing
  that would require opening file descriptors, which this module's
  read-only mandate forbids.

CLI (run as a module, no ``__main__.py`` router):

    python -m nlp_semantic.ingestion.inventory <hybrid_dataset_root>

      stdout: InventoryReport serialized as pretty JSON
      stderr: one-line summary "<N> files · <M> warnings · raw_root=<path>"
      exit:   0 on success; 2 on CLI usage error; 1 on build failure.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict

from nlp_semantic.schema import DocumentFileType


# ---- extension classifier ----------------------------------------------------


_EXTENSION_MAP: dict[str, DocumentFileType] = {
    ".pdf":   DocumentFileType.PDF,
    ".jpg":   DocumentFileType.IMAGE_JPG,
    ".jpeg":  DocumentFileType.IMAGE_JPG,
    ".png":   DocumentFileType.IMAGE_PNG,
    ".tif":   DocumentFileType.IMAGE_TIFF,
    ".tiff":  DocumentFileType.IMAGE_TIFF,
    ".txt":   DocumentFileType.TEXT,
    ".md":    DocumentFileType.TEXT,
}


def _classify_suffix(name: str) -> DocumentFileType:
    """Map a filename to a :class:`DocumentFileType` via its extension.

    Structured / binary / unknown formats (``.csv``, ``.json``, ``.yaml``,
    ``.xml``, ``.html``, ``.parquet``, anything else, no extension) land
    in :attr:`DocumentFileType.OTHER` — a classification, not a judgment
    of relevance.
    """
    suffix = Path(name).suffix.lower()
    return _EXTENSION_MAP.get(suffix, DocumentFileType.OTHER)


# ---- data model --------------------------------------------------------------


_WARNING_KINDS = (
    "symlink_skipped",
    "unreadable_stat",
    "unreadable_dir",
    "non_file_entry_skipped",
    "path_resolution_failed",
)


class InventoryWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "symlink_skipped",
        "unreadable_stat",
        "unreadable_dir",
        "non_file_entry_skipped",
        "path_resolution_failed",
    ]
    path: str
    detail: str | None = None


class InventoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relative_path: str
    file_type: DocumentFileType
    size_bytes: int
    modified_at: datetime


class InventoryReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root: str
    raw_root: str
    generated_at: datetime
    entries: list[InventoryEntry]
    warnings: list[InventoryWarning]
    total_files: int
    by_file_type: dict[str, int]
    by_source_subdir: dict[str, int]


# ---- scanner -----------------------------------------------------------------


def _posix_rel(abs_path: str, base: Path) -> str:
    """Return ``abs_path`` relative to ``base`` with forward slashes.

    If ``abs_path`` is not under ``base`` (post-resolution symlink that
    escaped the raw root, drive-letter mismatch after resolution,
    etc.), the function returns a bounded placeholder of the form
    ``<outside raw_root: <basename>>`` so the warning stays
    informative but no absolute filesystem path appears in the report.
    Never raises.
    """
    try:
        rel = Path(abs_path).relative_to(base)
    except ValueError:
        return f"<outside raw_root: {Path(abs_path).name}>"
    return str(PurePosixPath(str(rel).replace("\\", "/")))


def _utc_mtime(st_mtime: float) -> datetime:
    """Convert a POSIX mtime to a timezone-aware UTC datetime."""
    return datetime.fromtimestamp(st_mtime, tz=timezone.utc)


def build_inventory(hybrid_dataset_root: str | Path) -> InventoryReport:
    """Walk ``<hybrid_dataset_root>/raw/`` and report filesystem metadata.

    Validates the root and the ``raw/`` subdirectory; neither may be a
    symlink. Resolves both to their absolute real paths. Never follows
    symlinks encountered during the walk.

    Returns:
        InventoryReport. A non-empty ``warnings`` list means the scan
        was partial; callers must inspect it.

    Raises:
        FileNotFoundError: root or ``raw/`` does not exist.
        NotADirectoryError: root or ``raw/`` is not a directory.
        ValueError: root or ``raw/`` is a symlink, or ``raw/`` escapes
            the resolved root after resolution.
    """
    root_in = Path(hybrid_dataset_root)
    if not root_in.exists():
        raise FileNotFoundError(
            f"hybrid_dataset_root does not exist: {root_in}"
        )
    if root_in.is_symlink():
        raise ValueError(
            f"hybrid_dataset_root must not be a symlink: {root_in}"
        )
    if not root_in.is_dir():
        raise NotADirectoryError(
            f"hybrid_dataset_root is not a directory: {root_in}"
        )
    root_resolved = root_in.resolve(strict=True)

    raw_in = root_in / "raw"
    if not raw_in.exists():
        raise FileNotFoundError(f"raw/ not found under root: {raw_in}")
    if raw_in.is_symlink():
        raise ValueError(f"raw/ must not be a symlink: {raw_in}")
    if not raw_in.is_dir():
        raise NotADirectoryError(f"raw/ is not a directory: {raw_in}")
    raw_resolved = raw_in.resolve(strict=True)

    if not raw_resolved.is_relative_to(root_resolved):
        raise ValueError(
            f"resolved raw/ escapes the dataset root: {raw_resolved}"
        )

    generated_at = datetime.now(tz=timezone.utc)
    entries: list[InventoryEntry] = []
    warnings: list[InventoryWarning] = []

    def _scan(dir_path: Path) -> None:
        try:
            scanner = os.scandir(dir_path)
        except (PermissionError, OSError) as e:
            warnings.append(
                InventoryWarning(
                    kind="unreadable_dir",
                    path=_posix_rel(str(dir_path), raw_resolved),
                    detail=type(e).__name__,
                )
            )
            return
        with scanner as it:
            for entry in it:
                _process_entry(entry)

    def _process_entry(entry: os.DirEntry) -> None:
        name = entry.name
        if name == ".gitkeep":
            return

        if entry.is_symlink():
            warnings.append(
                InventoryWarning(
                    kind="symlink_skipped",
                    path=_posix_rel(entry.path, raw_resolved),
                )
            )
            return

        try:
            is_dir = entry.is_dir(follow_symlinks=False)
            is_file = entry.is_file(follow_symlinks=False)
        except OSError as e:
            warnings.append(
                InventoryWarning(
                    kind="unreadable_stat",
                    path=_posix_rel(entry.path, raw_resolved),
                    detail=type(e).__name__,
                )
            )
            return

        if is_dir:
            _scan(Path(entry.path))
            return

        if not is_file:
            warnings.append(
                InventoryWarning(
                    kind="non_file_entry_skipped",
                    path=_posix_rel(entry.path, raw_resolved),
                )
            )
            return

        try:
            st = entry.stat(follow_symlinks=False)
        except (FileNotFoundError, PermissionError, OSError) as e:
            warnings.append(
                InventoryWarning(
                    kind="unreadable_stat",
                    path=_posix_rel(entry.path, raw_resolved),
                    detail=type(e).__name__,
                )
            )
            return

        try:
            resolved = Path(entry.path).resolve(strict=True)
        except (FileNotFoundError, PermissionError, OSError, RuntimeError) as e:
            warnings.append(
                InventoryWarning(
                    kind="path_resolution_failed",
                    path=_posix_rel(entry.path, raw_resolved),
                    detail=type(e).__name__,
                )
            )
            return

        try:
            contained = resolved.is_relative_to(raw_resolved)
        except ValueError as e:
            warnings.append(
                InventoryWarning(
                    kind="path_resolution_failed",
                    path=_posix_rel(entry.path, raw_resolved),
                    detail=type(e).__name__,
                )
            )
            return

        if not contained:
            warnings.append(
                InventoryWarning(
                    kind="symlink_skipped",
                    path=_posix_rel(entry.path, raw_resolved),
                    detail="resolved outside raw_root",
                )
            )
            return

        entries.append(
            InventoryEntry(
                relative_path=_posix_rel(entry.path, raw_resolved),
                file_type=_classify_suffix(name),
                size_bytes=st.st_size,
                modified_at=_utc_mtime(st.st_mtime),
            )
        )

    _scan(raw_resolved)

    by_file_type: dict[str, int] = {}
    by_source_subdir: dict[str, int] = {}
    for e in entries:
        by_file_type[e.file_type.value] = by_file_type.get(e.file_type.value, 0) + 1
        first_segment = e.relative_path.split("/", 1)[0] if "/" in e.relative_path else e.relative_path
        by_source_subdir[first_segment] = by_source_subdir.get(first_segment, 0) + 1

    return InventoryReport(
        root=str(root_in),
        raw_root=str(PurePosixPath(str(raw_resolved).replace("\\", "/"))),
        generated_at=generated_at,
        entries=entries,
        warnings=warnings,
        total_files=len(entries),
        by_file_type=by_file_type,
        by_source_subdir=by_source_subdir,
    )


# ---- CLI ---------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m nlp_semantic.ingestion.inventory",
        description=(
            "Read-only inventory of a hybrid_dataset root's raw/ subtree. "
            "Writes a JSON InventoryReport to stdout and a one-line summary "
            "to stderr. Never opens or modifies file contents."
        ),
    )
    p.add_argument(
        "hybrid_dataset_root",
        help="Path to the hybrid_dataset root (the directory that contains raw/).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        report = build_inventory(args.hybrid_dataset_root)
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        print(f"inventory: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    sys.stdout.write(report.model_dump_json(indent=2))
    sys.stdout.write("\n")
    # ASCII separator keeps the summary legible under every Windows code
    # page (cp1252 / cp437 / cp850) without relying on terminal Unicode
    # support.
    print(
        f"{report.total_files} files | {len(report.warnings)} warnings | "
        f"raw_root={report.raw_root}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
