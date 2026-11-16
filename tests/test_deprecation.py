import ast
import inspect
import types
import warnings
from pathlib import Path

import pytest

from ternary_diagram import _deprecation
from ternary_diagram._deprecation import (
    FUTURE_VERSION,
    UNSET,
    format_default_change,
    format_renamed_parameter,
    resolve_renamed_parameter,
    warn_external,
)

DEFAULT_CHANGE_PARTS = {
    "current": "The figure was laid out again after drawing.",
    "future": "drawing will no longer lay out the figure.",
    "keep": "pass `tight_layout=True`",
    "adopt": "pass `tight_layout=False`",
}
RENAME = {"func": "scatter", "old": "flag_cbar", "new": "colorbar"}

# Source of helpers that run as if they were defined in a module named
# ``module_name``. ``outer`` reaches ``warn_external`` through two levels.
HELPER_SOURCE = """\
from ternary_diagram._deprecation import warn_external


def inner(message, category):
    warn_external(message, category)


def outer(message, category):
    inner(message, category)
"""
# Line of ``warn_external(...)`` inside ``HELPER_SOURCE``.
HELPER_WARN_LINENO = 5


def _make_helper_module(module_name: str) -> types.ModuleType:
    module = types.ModuleType(module_name)
    code = compile(HELPER_SOURCE, f"<{module_name}>", "exec")
    exec(code, module.__dict__)
    return module


def _next_lineno() -> int:
    """Return the line number just after the caller's current line."""
    return inspect.currentframe().f_back.f_lineno + 1


def test_future_version():
    assert FUTURE_VERSION == "4.0.0"


def test_unset_is_distinct_from_none():
    assert UNSET is not None
    assert repr(UNSET) == "<UNSET>"
    assert isinstance(UNSET, _deprecation._Unset)


def test_warn_external_defaults_to_future_warning():
    with pytest.warns(FutureWarning) as record:
        lineno = _next_lineno()
        warn_external("something will change")
    assert len(record) == 1
    assert record[0].category is FutureWarning
    assert str(record[0].message) == "something will change"
    assert record[0].filename == __file__
    assert record[0].lineno == lineno


def test_warn_external_accepts_category():
    with pytest.warns(UserWarning) as record:
        lineno = _next_lineno()
        warn_external("check your input", UserWarning)
    assert len(record) == 1
    assert record[0].category is UserWarning
    assert record[0].filename == __file__
    assert record[0].lineno == lineno


@pytest.mark.parametrize("category", [FutureWarning, UserWarning])
@pytest.mark.parametrize(
    "module_name", ["ternary_diagram", "ternary_diagram._fake_internal"]
)
def test_warn_external_skips_package_frames(module_name, category):
    helper = _make_helper_module(module_name)
    with pytest.warns(category) as record:
        lineno = _next_lineno()
        helper.outer("through two package levels", category)
    assert len(record) == 1
    assert record[0].category is category
    assert record[0].filename == __file__
    assert record[0].lineno == lineno


@pytest.mark.parametrize(
    "module_name", ["ternary_diagram_extra", "my_ternary_diagram", "tests"]
)
def test_warn_external_stops_at_first_outside_frame(module_name):
    helper = _make_helper_module(module_name)
    with pytest.warns(FutureWarning) as record:
        helper.outer("from a module outside the package", FutureWarning)
    assert len(record) == 1
    assert record[0].filename == f"<{module_name}>"
    assert record[0].lineno == HELPER_WARN_LINENO


def _fake_frame(module_name, f_back=None):
    return types.SimpleNamespace(
        f_globals={"__name__": module_name}, f_back=f_back
    )


def test_external_stacklevel_counts_package_frames():
    frame = _fake_frame(
        "ternary_diagram._deprecation",
        _fake_frame(
            "ternary_diagram._api",
            _fake_frame("ternary_diagram", _fake_frame("user_code")),
        ),
    )
    assert _deprecation._external_stacklevel(frame) == 4


def test_external_stacklevel_treats_missing_name_as_outside():
    frame = _fake_frame(
        "ternary_diagram._deprecation",
        types.SimpleNamespace(f_globals={}, f_back=None),
    )
    assert _deprecation._external_stacklevel(frame) == 2


def test_external_stacklevel_uses_last_frame_when_exhausted():
    frame = _fake_frame(
        "ternary_diagram._deprecation",
        _fake_frame("ternary_diagram._api"),
    )
    assert _deprecation._external_stacklevel(frame) == 2


def test_format_default_change():
    message = format_default_change(**DEFAULT_CHANGE_PARTS)
    assert message == (
        "The figure was laid out again after drawing. "
        "In ternary-diagram 4.0.0, drawing will no longer lay out the "
        "figure. To keep the current behavior, pass `tight_layout=True`. "
        "To adopt the new behavior now, pass `tight_layout=False`."
    )


def test_format_default_change_order():
    message = format_default_change(**DEFAULT_CHANGE_PARTS)
    positions = [
        message.index(DEFAULT_CHANGE_PARTS["current"]),
        message.index(FUTURE_VERSION),
        message.index(DEFAULT_CHANGE_PARTS["future"]),
        message.index(DEFAULT_CHANGE_PARTS["keep"]),
        message.index(DEFAULT_CHANGE_PARTS["adopt"]),
    ]
    assert positions == sorted(positions)


def test_format_default_change_version():
    message = format_default_change(**DEFAULT_CHANGE_PARTS, version="5.0.0")
    assert "In ternary-diagram 5.0.0, " in message
    assert FUTURE_VERSION not in message


@pytest.mark.parametrize("name", ["current", "future", "keep", "adopt"])
def test_format_default_change_empty_part(name):
    parts = {**DEFAULT_CHANGE_PARTS, name: ""}
    with pytest.raises(ValueError, match=f"`{name}`"):
        format_default_change(**parts)


def test_format_renamed_parameter():
    message = format_renamed_parameter(
        func="scatter", old="flag_cbar", new="colorbar"
    )
    assert message == (
        "`flag_cbar` of `scatter` was renamed to `colorbar`. "
        "`flag_cbar` will be removed in ternary-diagram 4.0.0. "
        "Pass `colorbar` instead."
    )


def test_format_renamed_parameter_version():
    message = format_renamed_parameter(
        func="contour", old="flag_cbar", new="colorbar", version="5.0.0"
    )
    assert "will be removed in ternary-diagram 5.0.0." in message
    assert "`contour`" in message


def test_resolve_renamed_parameter_both_omitted():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = resolve_renamed_parameter(
            **RENAME, old_value=UNSET, new_value=None
        )
    assert result is None


@pytest.mark.parametrize("new_value", [True, False])
def test_resolve_renamed_parameter_new_only(new_value):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = resolve_renamed_parameter(
            **RENAME, old_value=UNSET, new_value=new_value
        )
    assert result is new_value


@pytest.mark.parametrize("old_value", [True, False, 0, None])
def test_resolve_renamed_parameter_old_only(old_value):
    kwargs = {**RENAME, "old_value": old_value, "new_value": None}
    with pytest.warns(FutureWarning) as record:
        lineno = _next_lineno()
        result = resolve_renamed_parameter(**kwargs)
    assert result is old_value
    assert len(record) == 1
    assert record[0].category is FutureWarning
    assert str(record[0].message) == format_renamed_parameter(**RENAME)
    assert record[0].filename == __file__
    assert record[0].lineno == lineno


def test_resolve_renamed_parameter_old_only_version():
    with pytest.warns(FutureWarning, match="ternary-diagram 5.0.0"):
        resolve_renamed_parameter(
            **RENAME, old_value=True, new_value=None, version="5.0.0"
        )


@pytest.mark.parametrize(
    "old_value, new_value", [(True, True), (False, True), (None, False)]
)
def test_resolve_renamed_parameter_both(old_value, new_value):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(ValueError) as excinfo:
            resolve_renamed_parameter(
                **RENAME, old_value=old_value, new_value=new_value
            )
    assert str(excinfo.value) == (
        "`flag_cbar` and `colorbar` cannot be specified at the same time."
    )


def test_module_imports_nothing_from_the_package():
    tree = ast.parse(Path(_deprecation.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0
            names = [node.module or ""]
        elif isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        else:
            continue
        for name in names:
            assert name.split(".")[0] != "ternary_diagram"
