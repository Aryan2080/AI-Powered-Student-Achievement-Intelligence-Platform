# Marker file. Makes the repository-local `tests` directory a regular
# Python package so `from tests.dataset.conftest import ...`-style
# imports in `tests/dataset/test_*.py` resolve to the LOCAL package
# instead of an unrelated `tests` namespace that happens to be installed
# in the user's Python site-packages.
#
# Added in Chunk 7.24 to resolve the pre-existing collection error
# first reported in Chunk 7.15:
#
#     ModuleNotFoundError: No module named 'tests.dataset'
#
# Companion changes:
#   - `pyproject.toml` adds "." to `[tool.pytest.ini_options].pythonpath`
#     so the repo root is on sys.path at test time.
#   - `tests/schema/__init__.py` is also added for consistency with
#     the other test subpackages.
