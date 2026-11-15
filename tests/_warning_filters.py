"""A context manager that turns warnings into errors for the tests.

Tests that check that a plotting call emits no warning use
`raise_on_warnings` instead of ``warnings.simplefilter("error")``. It
ignores the deprecation warnings that pyparsing (>= 3.3) emits when an
older matplotlib (such as 3.9 on Python 3.9) parses mathtext with
pyparsing's old method names: they come from inside matplotlib, not from
ternary-diagram, and only the first parse of each text emits one, so they
would make the tests depend on their order. Every other warning, including
``MatplotlibDeprecationWarning``, is still an error. The module name starts
with ``_`` so that pytest does not collect it as a test module.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from contextlib import contextmanager

try:
    from pyparsing.warnings import PyparsingDeprecationWarning
except ImportError:  # pyparsing < 3.3 has no such warning
    PyparsingDeprecationWarning = None

__all__ = ("raise_on_warnings",)


@contextmanager
def raise_on_warnings() -> Iterator[None]:
    """Turn every warning into an error, except pyparsing's deprecations.

    Filters added inside the ``with`` block take precedence, as with
    ``warnings.catch_warnings``.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        if PyparsingDeprecationWarning is not None:
            warnings.simplefilter("ignore", PyparsingDeprecationWarning)
        yield
