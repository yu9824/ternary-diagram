"""Options passed by position to the public methods of TernaryDiagram.

The data (``materials``, ``vector``, ``z``, ``mappable``) may be passed by
position. The options after them will be keyword-only in 4.0.0; in 3.4.0,
passing them by position keeps their meaning and emits a FutureWarning
once per diagram and method (every time for ``TernaryDiagram`` itself,
which creates a new diagram).
"""

from __future__ import annotations

import inspect
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pytest

from ternary_diagram import TernaryDiagram

MATERIALS = ("Li2O", "La2O3", "TiO2")
VECTOR = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1], [2, 1, 1], [1, 2, 1]]
Z = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]


def _new_td() -> TernaryDiagram:
    _, ax = plt.subplots()
    return TernaryDiagram(MATERIALS, ax=ax, tight_layout=True)


def _next_lineno() -> int:
    """Return the line number just after the caller's current line."""
    return inspect.currentframe().f_back.f_lineno + 1


def _positional_match(names: str, func: str) -> str:
    return f"{names} of `{func}` by position is deprecated"


def _only_record(record) -> warnings.WarningMessage:
    messages = [str(w.message) for w in record]
    assert len(record) == 1, messages
    return record[0]


# --- TernaryDiagram -----------------------------------------------------


@pytest.mark.parametrize(
    ("extra", "names"),
    [
        ((), "`ax`"),
        ((False,), "`ax` and `auto_latex_notation`"),
    ],
)
def test_init_options_by_position_warn(ax, extra, names):
    with pytest.warns(
        FutureWarning, match=_positional_match(names, "TernaryDiagram")
    ) as record:
        lineno = _next_lineno()
        td = TernaryDiagram(MATERIALS, ax, *extra, tight_layout=True)

    warning = _only_record(record)
    assert warning.filename == __file__
    assert warning.lineno == lineno
    assert "4.0.0" in str(warning.message)
    assert td.ax is ax


def test_init_options_by_position_keep_their_meaning():
    _, ax_positional = plt.subplots()
    _, ax_keyword = plt.subplots()

    with pytest.warns(FutureWarning):
        positional = TernaryDiagram(
            MATERIALS, ax_positional, False, tight_layout=True
        )
    keyword = TernaryDiagram(
        MATERIALS, ax=ax_keyword, auto_latex_notation=False, tight_layout=True
    )

    assert positional.ax is ax_positional
    assert [t.get_text() for t in positional.vertex_labels_] == [
        t.get_text() for t in keyword.vertex_labels_
    ]
    # Without the chemical formatting, the labels are the raw materials.
    assert [t.get_text() for t in positional.vertex_labels_] == list(MATERIALS)


def test_init_warns_for_every_new_diagram(ax):
    for _ in range(2):
        with pytest.warns(FutureWarning) as record:
            TernaryDiagram(MATERIALS, ax, tight_layout=True)
        _only_record(record)


@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        ((MATERIALS,), {"tight_layout": True}),
        ((), {"materials": MATERIALS, "tight_layout": True}),
        ((MATERIALS,), {"auto_latex_notation": False, "tight_layout": True}),
    ],
)
def test_init_without_positional_options_is_silent(ax, args, kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        TernaryDiagram(*args, ax=ax, **kwargs)


# --- scatter, contour and colorbar --------------------------------------


def _scatter_state(collection) -> tuple:
    return (
        collection.get_offsets().tolist(),
        np.asarray(collection.get_array()).tolist(),
        collection.get_clim(),
        collection.colorbar is not None,
    )


def _contour_state(contour_set) -> tuple:
    return (
        contour_set.filled,
        list(contour_set.levels),
        contour_set.colorbar is not None,
    )


# method, positional options, the same options by keyword, names, state
METHOD_CASES = {
    "scatter": (
        (0.5, 4.0, None, False),
        {"z_min": 0.5, "z_max": 4.0, "annotations": None, "colorbar": False},
        "`z_min`, `z_max`, `annotations` and `colorbar`",
        _scatter_state,
    ),
    "contour": (
        (0.5, 4.0, False, False),
        {"z_min": 0.5, "z_max": 4.0, "fill": False, "colorbar": False},
        "`z_min`, `z_max`, `fill` and `colorbar`",
        _contour_state,
    ),
}


@pytest.mark.parametrize("method", list(METHOD_CASES))
def test_plot_options_by_position_warn(method):
    td = _new_td()
    options, _, names, _ = METHOD_CASES[method]

    with pytest.warns(
        FutureWarning, match=_positional_match(names, method)
    ) as record:
        lineno = _next_lineno()
        getattr(td, method)(VECTOR, Z, *options)

    warning = _only_record(record)
    assert warning.filename == __file__
    assert warning.lineno == lineno
    assert "4.0.0" in str(warning.message)


@pytest.mark.parametrize("method", list(METHOD_CASES))
def test_plot_options_by_position_keep_their_meaning(method):
    options, keywords, _, state = METHOD_CASES[method]

    with pytest.warns(FutureWarning):
        positional = getattr(_new_td(), method)(VECTOR, Z, *options)
    keyword = getattr(_new_td(), method)(VECTOR, Z, **keywords)

    assert state(positional) == state(keyword)


@pytest.mark.parametrize("method", list(METHOD_CASES))
def test_plot_options_by_position_warn_once_per_diagram(method):
    options = METHOD_CASES[method][0]
    td = _new_td()

    with pytest.warns(FutureWarning) as record:
        getattr(td, method)(VECTOR, Z, *options)
        getattr(td, method)(VECTOR, Z, *options)
    _only_record(record)

    # Another diagram has its own record.
    with pytest.warns(FutureWarning) as record:
        getattr(_new_td(), method)(VECTOR, Z, *options)
    _only_record(record)


@pytest.mark.parametrize("method", list(METHOD_CASES))
@pytest.mark.parametrize("data", ["vector", "vector_and_z"])
def test_plot_without_positional_options_is_silent(method, data):
    keywords = METHOD_CASES[method][1]
    td = _new_td()

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        if data == "vector":
            getattr(td, method)(VECTOR, z=Z, **keywords)
        else:
            getattr(td, method)(VECTOR, Z, **keywords)


def test_colorbar_options_by_position_warn():
    td = _new_td()
    mappable = td.scatter(VECTOR, z=Z, colorbar=False)

    with pytest.warns(
        FutureWarning,
        match=_positional_match("`shrink` and `format`", "colorbar"),
    ) as record:
        lineno = _next_lineno()
        td.colorbar(mappable, 0.5, "%.2f")

    warning = _only_record(record)
    assert warning.filename == __file__
    assert warning.lineno == lineno
    assert "4.0.0" in str(warning.message)


def test_colorbar_options_by_position_keep_their_meaning():
    def draw(positional: bool):
        td = _new_td()
        mappable = td.scatter(VECTOR, z=Z, colorbar=False)
        if positional:
            with pytest.warns(FutureWarning):
                return td.colorbar(mappable, 0.5, "%.2f", "label")
        return td.colorbar(mappable, shrink=0.5, format="%.2f", label="label")

    positional = draw(positional=True)
    keyword = draw(positional=False)

    assert positional.ax.get_position().bounds == pytest.approx(
        keyword.ax.get_position().bounds
    )
    assert positional.ax.get_ylabel() == keyword.ax.get_ylabel() == "label"


def test_colorbar_options_by_position_warn_once_per_diagram():
    td = _new_td()
    mappable = td.scatter(VECTOR, z=Z, colorbar=False)

    with pytest.warns(FutureWarning) as record:
        td.colorbar(mappable, 0.5)
        td.colorbar(mappable, 0.5)
    _only_record(record)


def test_colorbar_without_positional_options_is_silent():
    td = _new_td()
    mappable = td.scatter(VECTOR, z=Z, colorbar=False)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        td.colorbar(mappable, shrink=0.5)
        td.colorbar(mappable=mappable)


def test_each_method_has_its_own_record():
    td = _new_td()

    with pytest.warns(FutureWarning) as record:
        mappable = td.scatter(VECTOR, Z, 0.5, colorbar=False)
        td.contour(VECTOR, Z, 0.5, colorbar=False)
        td.colorbar(mappable, 0.5)

    assert len(record) == 3, [str(w.message) for w in record]
