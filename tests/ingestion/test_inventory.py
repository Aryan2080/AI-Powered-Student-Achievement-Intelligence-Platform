"""Tests for the read-only inventory and its CLI.

The inventory must never open or modify file contents. Three test
patterns prove this:

- ``test_build_inventory_never_opens_file_contents`` monkeypatches
  ``builtins.open`` to raise during the walk.
- ``test_raw_tree_is_byte_identical_after_inventory`` compares SHA256
  hashes of every synthetic file before and after a scan.
- The warning-emission tests confirm partial scans are visibly partial,
  not silently reported as successful.
"""
from __future__ import annotations

import builtins
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nlp_semantic.schema import DocumentFileType
from nlp_semantic.ingestion.inventory import (
    InventoryReport,
    InventoryWarning,
    _posix_rel,
    build_inventory,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _cli_env() -> dict[str, str]:
    """Env for subprocess CLI invocations.

    Prepends ``src/`` to PYTHONPATH so ``python -m nlp_semantic.ingestion.inventory``
    finds the package. In normal use the installed package or a venv entry
    point handles this; the test shortcuts that.
    """
    env = dict(os.environ)
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


# ---- helpers -----------------------------------------------------------------


def _mkroot(tmp_path: Path) -> Path:
    """Build the minimum directory shape build_inventory requires."""
    root = tmp_path / "ds"
    root.mkdir()
    (root / "raw").mkdir()
    return root


def _write_file(path: Path, content: bytes = b"synthetic") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _can_create_symlink(tmp_path: Path) -> bool:
    try:
        target = tmp_path / "_sym_target"
        link = tmp_path / "_sym_link"
        target.write_text("x", encoding="utf-8")
        os.symlink(target, link)
        link.unlink()
        target.unlink()
        return True
    except (OSError, NotImplementedError):
        return False


def _tree_hashes(root: Path) -> dict[str, str]:
    """Map relative POSIX path -> SHA256 for every file under root."""
    out: dict[str, str] = {}
    for p in root.rglob("*"):
        if p.is_file() and not p.is_symlink():
            rel = p.relative_to(root).as_posix()
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


# ---- root validation ---------------------------------------------------------


def test_nonexistent_root_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_inventory(tmp_path / "nope")


def test_root_is_a_file_raises(tmp_path: Path) -> None:
    p = tmp_path / "not_a_dir"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        build_inventory(p)


def test_raw_missing_raises(tmp_path: Path) -> None:
    root = tmp_path / "ds"
    root.mkdir()
    with pytest.raises(FileNotFoundError):
        build_inventory(root)


# ---- symlink refusal on roots ------------------------------------------------


@pytest.mark.skipif(
    not _can_create_symlink(Path(os.environ.get("TEMP", "/tmp"))),
    reason="symlink creation unavailable (Windows without developer mode)",
)
def test_symlink_root_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "raw").mkdir()
    link_root = tmp_path / "link_root"
    os.symlink(real, link_root)
    with pytest.raises(ValueError, match="must not be a symlink"):
        build_inventory(link_root)


@pytest.mark.skipif(
    not _can_create_symlink(Path(os.environ.get("TEMP", "/tmp"))),
    reason="symlink creation unavailable (Windows without developer mode)",
)
def test_symlink_raw_rejected(tmp_path: Path) -> None:
    root = tmp_path / "ds"
    root.mkdir()
    real_raw = tmp_path / "elsewhere_raw"
    real_raw.mkdir()
    os.symlink(real_raw, root / "raw")
    with pytest.raises(ValueError, match="raw/ must not be a symlink"):
        build_inventory(root)


# ---- empty scan --------------------------------------------------------------


def test_empty_raw_produces_zero_entries(tmp_path: Path) -> None:
    root = _mkroot(tmp_path)
    report = build_inventory(root)
    assert report.total_files == 0
    assert report.entries == []
    assert report.warnings == []
    assert report.by_file_type == {}
    assert report.by_source_subdir == {}


def test_gitkeep_is_skipped(tmp_path: Path) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / ".gitkeep", b"")
    report = build_inventory(root)
    assert report.total_files == 0


# ---- classification table ----------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("doc.pdf", DocumentFileType.PDF),
        ("photo.jpg", DocumentFileType.IMAGE_JPG),
        ("photo.jpeg", DocumentFileType.IMAGE_JPG),
        ("photo.PNG", DocumentFileType.IMAGE_PNG),
        ("scan.tiff", DocumentFileType.IMAGE_TIFF),
        ("scan.tif", DocumentFileType.IMAGE_TIFF),
        ("notes.txt", DocumentFileType.TEXT),
        ("notes.md", DocumentFileType.TEXT),
    ],
)
def test_classifies_known_extensions(
    tmp_path: Path, filename: str, expected: DocumentFileType
) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "sub" / filename, b"x")
    report = build_inventory(root)
    assert report.total_files == 1
    assert report.entries[0].file_type == expected


@pytest.mark.parametrize(
    "filename",
    [
        "data.csv",
        "data.tsv",
        "payload.json",
        "config.yaml",
        "config.yml",
        "doc.xml",
        "page.html",
        "bulk.parquet",
        "weird.xyz",
        "no_extension",
    ],
)
def test_structured_formats_classify_as_other(
    tmp_path: Path, filename: str
) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "sub" / filename, b"x")
    report = build_inventory(root)
    assert report.total_files == 1
    assert report.entries[0].file_type == DocumentFileType.OTHER


# ---- metadata accuracy -------------------------------------------------------


def test_size_bytes_matches_written_content(tmp_path: Path) -> None:
    root = _mkroot(tmp_path)
    content = b"hello world" * 10
    _write_file(root / "raw" / "sub" / "a.pdf", content)
    report = build_inventory(root)
    assert report.entries[0].size_bytes == len(content)


def test_modified_at_is_utc_aware(tmp_path: Path) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "sub" / "a.pdf", b"x")
    report = build_inventory(root)
    mt = report.entries[0].modified_at
    assert mt.tzinfo is not None
    assert mt.utcoffset().total_seconds() == 0.0
    now = datetime.now(tz=timezone.utc)
    assert (now - mt).total_seconds() < 300  # within 5 min


def test_forward_slash_relative_paths(tmp_path: Path) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "public_datasets" / "nested" / "a.pdf", b"x")
    report = build_inventory(root)
    assert "\\" not in report.entries[0].relative_path
    assert report.entries[0].relative_path == "public_datasets/nested/a.pdf"


def test_aggregations_match_entries(tmp_path: Path) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "public_datasets" / "a.pdf", b"x")
    _write_file(root / "raw" / "public_datasets" / "b.pdf", b"xx")
    _write_file(root / "raw" / "evidence_documents" / "c.jpg", b"xxx")
    report = build_inventory(root)
    assert report.total_files == 3
    assert report.by_file_type == {"pdf": 2, "image_jpg": 1}
    assert report.by_source_subdir == {"public_datasets": 2, "evidence_documents": 1}


# ---- read-only safety --------------------------------------------------------


def test_build_inventory_never_opens_file_contents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "sub" / "a.pdf", b"content_that_must_not_be_read")

    def no_open(*args, **kwargs):
        raise AssertionError("build_inventory must not open file contents")

    monkeypatch.setattr(builtins, "open", no_open)

    report = build_inventory(root)
    assert report.total_files == 1
    assert report.entries[0].size_bytes == len(b"content_that_must_not_be_read")


def test_raw_tree_is_byte_identical_after_inventory(tmp_path: Path) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "a" / "a.pdf", b"alpha")
    _write_file(root / "raw" / "b" / "b.txt", b"beta beta")
    _write_file(root / "raw" / "c.csv", b"c,d,e\n1,2,3\n")

    before = _tree_hashes(root / "raw")
    report = build_inventory(root)
    after = _tree_hashes(root / "raw")

    assert before == after, "inventory altered raw files"
    assert report.total_files == 3


# ---- symlink walks -----------------------------------------------------------


@pytest.mark.skipif(
    not _can_create_symlink(Path(os.environ.get("TEMP", "/tmp"))),
    reason="symlink creation unavailable (Windows without developer mode)",
)
def test_symlinked_file_skipped_and_warned(tmp_path: Path) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "sub" / "real.pdf", b"x")
    os.symlink(root / "raw" / "sub" / "real.pdf", root / "raw" / "sub" / "link.pdf")
    report = build_inventory(root)
    assert report.total_files == 1  # real.pdf only
    kinds = {w.kind for w in report.warnings}
    assert "symlink_skipped" in kinds


@pytest.mark.skipif(
    not _can_create_symlink(Path(os.environ.get("TEMP", "/tmp"))),
    reason="symlink creation unavailable (Windows without developer mode)",
)
def test_symlinked_directory_skipped_and_warned(tmp_path: Path) -> None:
    root = _mkroot(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    _write_file(outside / "x.pdf", b"x")
    os.symlink(outside, root / "raw" / "linked_dir")
    report = build_inventory(root)
    assert report.total_files == 0
    kinds = {w.kind for w in report.warnings}
    assert "symlink_skipped" in kinds


# ---- defensive metadata handling ---------------------------------------------


def test_unreadable_stat_warning_from_monkeypatched_scandir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "sub" / "a.pdf", b"x")

    class _FakeEntry:
        def __init__(self, real):
            self._real = real
            self.name = real.name
            self.path = real.path
        def is_symlink(self):
            return False
        def is_dir(self, *, follow_symlinks=False):
            return False
        def is_file(self, *, follow_symlinks=False):
            return True
        def stat(self, *, follow_symlinks=False):
            raise PermissionError("simulated denial")

    real_scandir = os.scandir

    def fake_scandir(path):
        it = real_scandir(path)

        class _Ctx:
            def __enter__(self_inner):
                return self_inner
            def __exit__(self_inner, *a):
                it.close()
                return False
            def __iter__(self_inner):
                for e in it:
                    if e.name == "a.pdf":
                        yield _FakeEntry(e)
                    else:
                        yield e
        return _Ctx()

    monkeypatch.setattr(os, "scandir", fake_scandir)
    report = build_inventory(root)
    assert report.total_files == 0
    kinds = {w.kind for w in report.warnings}
    assert "unreadable_stat" in kinds


# ---- _posix_rel fallback -----------------------------------------------------


def test_posix_rel_happy_path_under_base(tmp_path: Path) -> None:
    base = tmp_path / "raw"
    base.mkdir()
    assert _posix_rel(str(base / "sub" / "a.pdf"), base) == "sub/a.pdf"


def test_posix_rel_fallback_does_not_leak_absolute_path(tmp_path: Path) -> None:
    base = tmp_path / "ds" / "raw"
    base.mkdir(parents=True)
    # Path that is NOT under base: forces the fallback branch.
    outside = tmp_path / "elsewhere" / "secret_dir" / "leak.pdf"
    rel = _posix_rel(str(outside), base)

    # The absolute path (any ancestor segment that isn't the file basename)
    # must not appear in the returned string.
    assert "elsewhere" not in rel
    assert "secret_dir" not in rel
    assert str(tmp_path).replace("\\", "/") not in rel
    assert str(base).replace("\\", "/") not in rel

    # The placeholder format carries the basename and a neutral marker.
    assert rel == "<outside raw_root: leak.pdf>"


def test_path_resolution_failed_from_monkeypatched_resolve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "sub" / "target.pdf", b"x")

    import nlp_semantic.ingestion.inventory as inv_mod
    real_resolve = Path.resolve
    bad_name = "target.pdf"

    def patched_resolve(self, *, strict=False):
        if self.name == bad_name:
            raise FileNotFoundError("simulated vanishing entry")
        return real_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", patched_resolve)
    report = build_inventory(root)
    assert report.total_files == 0
    kinds = {w.kind for w in report.warnings}
    assert "path_resolution_failed" in kinds
    detail = {w.detail for w in report.warnings if w.kind == "path_resolution_failed"}
    assert "FileNotFoundError" in detail


# ---- CLI ---------------------------------------------------------------------


def test_cli_happy_path(tmp_path: Path) -> None:
    root = _mkroot(tmp_path)
    _write_file(root / "raw" / "sub" / "a.pdf", b"xyz")

    proc = subprocess.run(
        [sys.executable, "-m", "nlp_semantic.ingestion.inventory", str(root)],
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["total_files"] == 1
    assert data["entries"][0]["relative_path"] == "sub/a.pdf"
    assert "files" in proc.stderr and "warnings" in proc.stderr


def test_cli_usage_error_on_missing_arg() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "nlp_semantic.ingestion.inventory"],
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    assert proc.returncode == 2


def test_cli_build_failure_on_nonexistent_root(tmp_path: Path) -> None:
    bogus = tmp_path / "does_not_exist"
    proc = subprocess.run(
        [sys.executable, "-m", "nlp_semantic.ingestion.inventory", str(bogus)],
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    assert proc.returncode == 1
    assert "FileNotFoundError" in proc.stderr
