"""Smoke tests for toolshop.centaur_app — import, function, and signature checks."""

from __future__ import annotations

import inspect

import pytest


# ── Import check ───────────────────────────────────────────────────────

def test_module_importable():
    """Module should be importable without streamlit/plotly installed."""
    import toolshop.centaur_app
    assert hasattr(toolshop.centaur_app, "__file__")


# ── Function existence ─────────────────────────────────────────────────

def test_launch_centaur_exists():
    """launch_centaur function should exist."""
    from toolshop.centaur_app import launch_centaur
    assert callable(launch_centaur)


def test_run_streamlit_app_exists():
    """_run_streamlit_app function should exist."""
    from toolshop.centaur_app import _run_streamlit_app
    assert callable(_run_streamlit_app)


# ── Signature checks ───────────────────────────────────────────────────

def test_launch_centaur_signature():
    """launch_centaur should accept a port keyword argument with default 8501."""
    from toolshop.centaur_app import launch_centaur
    sig = inspect.signature(launch_centaur)
    params = sig.parameters
    assert "port" in params
    assert params["port"].default == 8501


def test_launch_centaur_no_required_args():
    """launch_centaur should be callable with no arguments."""
    from toolshop.centaur_app import launch_centaur
    sig = inspect.signature(launch_centaur)
    required = [
        p for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind != inspect.Parameter.VAR_POSITIONAL
        and p.kind != inspect.Parameter.VAR_KEYWORD
    ]
    assert len(required) == 0


# ── Fallback behavior ──────────────────────────────────────────────────

def test_launch_centaur_streamlit_fallback(capsys):
    """launch_centaur should print install instructions if streamlit missing."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "streamlit":
            raise ImportError("No module named 'streamlit'")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = mock_import
    try:
        from toolshop.centaur_app import launch_centaur
        launch_centaur()
    except SystemExit:
        pass
    finally:
        builtins.__import__ = real_import

    captured = capsys.readouterr()
    assert "streamlit" in captured.out.lower() or "streamlit" in captured.err.lower()


# ── Internal module getter functions ───────────────────────────────────

def test_get_scorer_returns_callable_or_none():
    from toolshop.centaur_app import _get_scorer
    result = _get_scorer()
    assert result is None or callable(result)


def test_get_cliche_checker_returns_callable_or_none():
    from toolshop.centaur_app import _get_cliche_checker
    result = _get_cliche_checker()
    assert result is None or callable(result)


def test_get_scheme_checker_returns_callable_or_none():
    from toolshop.centaur_app import _get_scheme_checker
    result = _get_scheme_checker()
    assert result is None or callable(result)


def test_get_similarity_retriever_returns_callable_or_none():
    from toolshop.centaur_app import _get_similarity_retriever
    result = _get_similarity_retriever()
    assert result is None or callable(result)


def test_get_slang_injector_returns_callable_or_none():
    from toolshop.centaur_app import _get_slang_injector
    result = _get_slang_injector()
    assert result is None or callable(result)


def test_get_theme_comparator_returns_callable_or_none():
    from toolshop.centaur_app import _get_theme_comparator
    result = _get_theme_comparator()
    assert result is None or callable(result)
