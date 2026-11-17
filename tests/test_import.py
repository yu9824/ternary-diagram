# ruff : noqa : F401
from __future__ import annotations


def test_import():
    import ternary_diagram
    from ternary_diagram import TernaryDiagram

    assert ternary_diagram.__all__ == ("TernaryDiagram",)


def test_version():
    from ternary_diagram import __version__

    assert isinstance(__version__, str)
    assert __version__
