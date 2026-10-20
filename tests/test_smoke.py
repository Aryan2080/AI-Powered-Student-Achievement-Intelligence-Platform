"""Smoke test: pytest wiring works and the nlp_semantic package imports."""
import importlib


def test_pytest_runs() -> None:
    assert True


def test_nlp_semantic_imports() -> None:
    pkg = importlib.import_module("nlp_semantic")
    assert pkg is not None


def test_nlp_semantic_has_version() -> None:
    import nlp_semantic

    assert isinstance(nlp_semantic.__version__, str)
    assert nlp_semantic.__version__
