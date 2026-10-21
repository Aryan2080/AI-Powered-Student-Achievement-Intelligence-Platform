"""Load and cross-validate taxonomy YAML files.

Scope (Chunk 3): read a single taxonomy YAML file, validate each entry
with :class:`LabelTaxonomy`, then run file-local invariants
(``validate_taxonomy``). Cross-record / dataset-wide checks (does a
particular ``label_id`` referenced from an ``Achievement`` exist in the
loaded taxonomy?) remain a separate concern for a future dataset
validator.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml

from .label_taxonomy import LabelTaxonomy


class TaxonomyError(ValueError):
    """Raised when a loaded taxonomy violates file-level or cross-entry invariants.

    Per-entry validation errors (bad ``label_id`` format, unknown field,
    missing required field, …) surface as ``pydantic.ValidationError``;
    this type is reserved for issues the Pydantic model cannot see,
    e.g. duplicates across entries or ``supersedes`` cycles.
    """


def load_taxonomy(path: str | Path) -> list[LabelTaxonomy]:
    """Load a taxonomy YAML file into a list of ``LabelTaxonomy`` records.

    The YAML top level must be a sequence (list) of mappings. Each
    mapping is passed to :class:`LabelTaxonomy`, which performs its own
    strict validation (``extra="forbid"``, enum checks, ``label_id``
    format, ``supersedes`` self-reference ban).

    Returns the entries in file order; an empty YAML (or ``null``) is
    treated as an empty list.

    Raises:
        FileNotFoundError: path does not exist.
        TaxonomyError: top-level YAML is not a list, or a list element
            is not a mapping.
        pydantic.ValidationError: a mapping fails ``LabelTaxonomy``
            validation.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return []
    if not isinstance(data, list):
        raise TaxonomyError(
            f"{p}: top-level YAML must be a list; got "
            f"{type(data).__name__}"
        )
    entries: list[LabelTaxonomy] = []
    for i, raw in enumerate(data):
        if not isinstance(raw, dict):
            raise TaxonomyError(
                f"{p}: entry at index {i} must be a mapping; got "
                f"{type(raw).__name__}"
            )
        entries.append(LabelTaxonomy(**raw))
    return entries


def validate_taxonomy(entries: Iterable[LabelTaxonomy]) -> None:
    """Enforce file-level invariants on a loaded taxonomy.

    Invariants (scoped to the entries given — NOT dataset-wide):

    - All entries share a single ``task_name``. One YAML file holds one
      taxonomy task.
    - ``label_id`` values are unique within the file.
    - Every ``supersedes`` reference points to a ``label_id`` present
      in the same set. (The individual-entry self-reference ban is
      enforced by :class:`LabelTaxonomy` itself.)
    - The ``supersedes`` graph is acyclic.

    Raises:
        TaxonomyError: on any violation.
    """
    entries_list = list(entries)
    if not entries_list:
        return

    # 1. single task_name per file
    tasks = {e.task_name for e in entries_list}
    if len(tasks) > 1:
        raise TaxonomyError(
            "taxonomy mixes multiple task_name values: "
            f"{sorted(t.value for t in tasks)}"
        )

    # 2. unique label_id within the set
    by_id: dict[str, LabelTaxonomy] = {}
    for e in entries_list:
        if e.label_id in by_id:
            raise TaxonomyError(
                f"duplicate label_id {e.label_id!r} in taxonomy"
            )
        by_id[e.label_id] = e

    # 3. supersedes points inside the set
    for e in entries_list:
        if e.supersedes is not None and e.supersedes not in by_id:
            raise TaxonomyError(
                f"label {e.label_id!r} supersedes {e.supersedes!r} "
                "which is not present in this taxonomy"
            )

    # 4. no cycles in the supersedes graph (each node has at most one
    #    outgoing edge; walk until None or we revisit)
    for start_id in by_id:
        seen: set[str] = set()
        current: str | None = start_id
        while current is not None:
            if current in seen:
                raise TaxonomyError(
                    f"cycle detected in supersedes graph "
                    f"(involving {start_id!r})"
                )
            seen.add(current)
            current = by_id[current].supersedes


def load_and_validate_taxonomy(path: str | Path) -> list[LabelTaxonomy]:
    """Convenience: load a taxonomy YAML and run the file-local validator.

    Equivalent to ``validate_taxonomy(load_taxonomy(path))`` with the
    loaded entries returned on success.
    """
    entries = load_taxonomy(path)
    validate_taxonomy(entries)
    return entries
