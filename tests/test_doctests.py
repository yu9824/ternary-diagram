"""Run the usage examples in the docstrings of the public API.

This is the one doctest runner shared by every spec (tech.md "Docstring
Examples"). It collects the docstrings of

- the objects in ``ternary_diagram.__all__``, and
- the public functions and classes defined in the public submodules
  (names not starting with ``_``; new ones are picked up automatically),

where a class contributes its own docstring, ``__init__`` and its public
methods and properties. Private modules and private methods are never
collected. Each docstring with ``>>>`` examples becomes one test that runs
in a temporary working directory, with FutureWarning turned into an error,
in the globals of the module that defines it.
"""

from __future__ import annotations

import doctest
import importlib
import inspect
import io
import pkgutil
import sys
import warnings
from collections.abc import Iterator
from types import ModuleType

import pytest

import ternary_diagram

OPTIONFLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE

# Docstrings whose examples are known to fail. Keep this to the one entry
# below and do not add others.
KNOWN_FAILURES = {
    "ternary_diagram._api.TernaryDiagram.__init__": (
        "The existing Examples section prints reprs, omits `ax=` and calls "
        "`savefig`. Remove this entry once `user-guide-docs` rewrites it."
    ),
}


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _is_function_or_class(obj: object) -> bool:
    return inspect.isfunction(obj) or inspect.isclass(obj)


def _class_members(cls: type) -> Iterator[tuple[str, object]]:
    """Yield the class, ``__init__`` and the public methods and properties.

    Each item is ``(qualified name, object)``. Only members defined in the
    class body itself are yielded.
    """
    yield cls.__qualname__, cls
    for name, value in vars(cls).items():
        if name != "__init__" and not _is_public(name):
            continue
        if isinstance(value, (staticmethod, classmethod)):
            value = value.__func__
        if inspect.isfunction(value) or isinstance(value, property):
            yield f"{cls.__qualname__}.{name}", value


def _public_modules() -> Iterator[ModuleType]:
    for info in pkgutil.iter_modules(ternary_diagram.__path__):
        if _is_public(info.name):
            yield importlib.import_module(
                f"{ternary_diagram.__name__}.{info.name}"
            )


def _public_objects() -> Iterator[tuple[ModuleType, object]]:
    """Yield ``(defining module, object)`` for the public API."""
    for name in ternary_diagram.__all__:
        obj = getattr(ternary_diagram, name)
        if _is_function_or_class(obj):
            yield sys.modules[obj.__module__], obj
    for module in _public_modules():
        for name, obj in vars(module).items():
            # Skip names that the module only imports.
            if (
                _is_public(name)
                and _is_function_or_class(obj)
                and obj.__module__ == module.__name__
            ):
                yield module, obj


def collect_doctests() -> list[doctest.DocTest]:
    """Return one DocTest per public docstring with examples, by name."""
    finder = doctest.DocTestFinder(recurse=False)
    tests = {}
    for module, obj in _public_objects():
        members = (
            _class_members(obj)
            if inspect.isclass(obj)
            else [(obj.__qualname__, obj)]
        )
        for qualname, member in members:
            # Without ``globs`` the finder uses a copy of the module globals.
            for test in finder.find(
                member, f"{module.__name__}.{qualname}", module=module
            ):
                if test.examples:
                    tests[test.name] = test
    return [tests[name] for name in sorted(tests)]


def run_examples(test: doctest.DocTest) -> None:
    """Run the examples of ``test`` and fail with the report if any fails.

    FutureWarning is turned into an error. ``test`` itself is not changed:
    the examples run on a copy with its own copy of the globals.
    """
    copied = doctest.DocTest(
        test.examples,
        dict(test.globs),
        test.name,
        test.filename,
        test.lineno,
        test.docstring,
    )
    runner = doctest.DocTestRunner(verbose=False, optionflags=OPTIONFLAGS)
    report = io.StringIO()
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        result = runner.run(copied, out=report.write)
    if result.failed:
        pytest.fail(
            f"{result.failed} of {result.attempted} examples failed in "
            f"{test.name}:\n{report.getvalue()}",
            pytrace=False,
        )


DOCTESTS = collect_doctests()
COLLECTED = {test.name for test in DOCTESTS}


def _param(test: doctest.DocTest):
    reason = KNOWN_FAILURES.get(test.name)
    marks = (
        () if reason is None else pytest.mark.xfail(strict=True, reason=reason)
    )
    return pytest.param(test, id=test.name, marks=marks)


@pytest.mark.parametrize("test", [_param(test) for test in DOCTESTS])
def test_docstring_examples(test, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_examples(test)


def test_public_examples_are_collected():
    assert {
        "ternary_diagram._api.TernaryDiagram.__init__",
        "ternary_diagram.utils.check_1d_vector",
        "ternary_diagram.utils.three2two",
        "ternary_diagram.utils.get_label",
        "ternary_diagram.utils.check_optional_bool",
        "ternary_diagram.utils.check_bool",
    } <= COLLECTED


def test_private_api_is_not_collected():
    for name in (
        "ternary_diagram._api._BasePlotter._set_default_params",
        "ternary_diagram._api._BasePlotter._merge_alias",
    ):
        assert name not in COLLECTED
    for module_name in (
        "ternary_diagram._deprecation",
        "ternary_diagram._post_draw",
        "ternary_diagram.__main__",
    ):
        assert not any(
            name.startswith(f"{module_name}.") for name in COLLECTED
        )
    for test in DOCTESTS:
        module_name = test.globs["__name__"]
        path = test.name[len(module_name) + 1 :].split(".")
        # A private module only contributes the objects in ``__all__``.
        assert (
            _is_public(module_name.rpartition(".")[2])
            or path[0] in ternary_diagram.__all__
        ), test.name
        assert all(part == "__init__" or _is_public(part) for part in path), (
            test.name
        )


def test_known_failures_are_collected():
    assert set(KNOWN_FAILURES) <= COLLECTED


def test_namespace_is_module_globals():
    # Python adds ``__warningregistry__`` to a module once a warning is
    # attributed to it, so it may appear after collection.
    ignored = {"__warningregistry__"}
    for test in DOCTESTS:
        module = sys.modules[test.globs["__name__"]]
        assert test.globs.keys() - ignored == vars(module).keys() - ignored, (
            test.name
        )


def _doctest_from(source: str) -> doctest.DocTest:
    return doctest.DocTestParser().get_doctest(
        source, {"__name__": "sample"}, "sample", None, 0
    )


def test_runner_fails_with_failing_example_and_diff(tmp_path, monkeypatch):
    test = _doctest_from(">>> 1 + 1\n3\n")
    with pytest.raises(pytest.fail.Exception) as excinfo:
        test_docstring_examples(test, tmp_path, monkeypatch)
    message = str(excinfo.value)
    assert "sample" in message
    assert "Failed example:\n    1 + 1\n" in message
    assert "Expected:\n    3\nGot:\n    2\n" in message


def test_runner_treats_future_warning_as_error(tmp_path, monkeypatch):
    test = _doctest_from(
        ">>> import warnings\n"
        ">>> warnings.warn('changes in 4.0.0', FutureWarning)\n"
    )
    with pytest.raises(
        pytest.fail.Exception, match="FutureWarning: changes in 4.0.0"
    ):
        test_docstring_examples(test, tmp_path, monkeypatch)


def test_runner_uses_ellipsis_and_normalize_whitespace(tmp_path, monkeypatch):
    test = _doctest_from(">>> list(range(30))\n[0,   1, ..., 29]\n")
    test_docstring_examples(test, tmp_path, monkeypatch)


def test_runner_works_in_temporary_directory(tmp_path, monkeypatch):
    test = _doctest_from(
        ">>> from pathlib import Path\n"
        ">>> _ = Path('out.txt').write_text('x')\n"
    )
    test_docstring_examples(test, tmp_path, monkeypatch)
    assert (tmp_path / "out.txt").is_file()


class _Sample:
    """Class docstring.

    >>> 1
    1
    """

    def __init__(self):
        """Initialize.

        >>> 1
        1
        """

    def method(self):
        """Do nothing.

        >>> 1
        1
        """

    @property
    def prop(self):
        """Return nothing.

        >>> 1
        1
        """

    @staticmethod
    def static():
        """Do nothing.

        >>> 1
        1
        """

    def _private(self):
        """Do nothing.

        >>> self._private()
        """

    def __repr__(self):
        """Return the repr.

        >>> 1
        1
        """
        return "_Sample()"


def test_class_members_skip_private_methods():
    names = {name for name, _ in _class_members(_Sample)}
    assert names == {
        "_Sample",
        "_Sample.__init__",
        "_Sample.method",
        "_Sample.prop",
        "_Sample.static",
    }
