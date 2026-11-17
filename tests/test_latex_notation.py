"""Formatting of the chemical formulas in ``annotate`` and ``scatter``.

``auto_latex_notation`` of each call chooses the rule of 4.0.0 (``True`` or
``False``). Without it, the v3.x display is kept and a FutureWarning
announces the texts whose display will change.
"""

from __future__ import annotations

import warnings

import pytest
from matplotlib.text import Annotation

from ternary_diagram import TernaryDiagram

MATERIALS = ("Li2O", "La2O3", "TiO2")
VECTOR = [1, 1, 1]
WARNING_MATCH = r"In ternary-diagram 4\.0\.0, .*auto_latex_notation"


def _annotate(td: TernaryDiagram, text, **kwargs) -> str:
    return td.annotate(text, VECTOR, **kwargs).get_text()


def _scatter(td: TernaryDiagram, texts, **kwargs) -> list[str]:
    td.scatter([VECTOR] * len(texts), annotations=texts, **kwargs)
    return [t.get_text() for t in td.ax.texts if isinstance(t, Annotation)]


def _draw(method: str, td: TernaryDiagram, text, **kwargs) -> str:
    if method == "annotate":
        return _annotate(td, text, **kwargs)
    # The annotation of the point drawn by this call.
    return _scatter(td, [text], **kwargs)[-1]


METHODS = ["annotate", "scatter"]


# --- auto_latex_notation given ----------------------------------------------


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("diagram_setting", [True, False])
@pytest.mark.parametrize(
    "text, expected",
    [
        ("Li2O", "Li$_{2}$O"),
        ("LiF + Li2O", "LiF + Li$_{2}$O"),
        ("Sample 1", "Sample 1"),
        ("$x_1$", "$x_1$"),
    ],
)
def test_true_formats_only_the_chemical_formulas(
    ax, method, diagram_setting, text, expected
):
    td = TernaryDiagram(
        MATERIALS,
        ax=ax,
        auto_latex_notation=diagram_setting,
        tight_layout=True,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _draw(method, td, text, auto_latex_notation=True) == expected


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("diagram_setting", [True, False])
@pytest.mark.parametrize("text", ["Li2O", "Sample 1", "$x_1$"])
def test_false_shows_the_text_as_it_is(ax, method, diagram_setting, text):
    td = TernaryDiagram(
        MATERIALS,
        ax=ax,
        auto_latex_notation=diagram_setting,
        tight_layout=True,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _draw(method, td, text, auto_latex_notation=False) == text


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("value", [0, 1, "yes"])
def test_invalid_value_raises_type_error(td, method, value):
    with pytest.raises(TypeError, match="`auto_latex_notation` must be"):
        _draw(method, td, "Li2O", auto_latex_notation=value)
    assert not any(isinstance(t, Annotation) for t in td.ax.texts)


# --- auto_latex_notation not given: v3.x display ----------------------------


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("text", ["Li2O", "(LiLa)0.5TiO3", "LiF", "A"])
def test_default_keeps_formulas_without_warning(td, method, text):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        shown = _draw(method, td, text)
    assert shown == _draw(method, td, text, auto_latex_notation=True)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize(
    "text, shown, future",
    [
        ("Sample 1", "Sample $_{1}$", "Sample 1"),
        ("No.2", "No.$_{2}$", "No.2"),
    ],
)
def test_default_keeps_the_v3_display_and_warns(
    td, method, text, shown, future
):
    with pytest.warns(FutureWarning, match=WARNING_MATCH) as record:
        assert _draw(method, td, text) == shown

    assert len(record) == 1
    message = str(record[0].message)
    assert f"`{method}` formatted {text!r} as {shown!r}" in message
    assert f"shown as {future!r}" in message
    assert record[0].filename == __file__


@pytest.mark.parametrize("method", METHODS)
def test_default_follows_the_diagram_setting_in_the_warning(ax, method):
    td = TernaryDiagram(
        MATERIALS, ax=ax, auto_latex_notation=False, tight_layout=True
    )
    with pytest.warns(FutureWarning, match=WARNING_MATCH) as record:
        # v3.x formats it whatever the setting of the diagram.
        assert _draw(method, td, "Li2O") == "Li$_{2}$O"

    assert "shown as 'Li2O'" in str(record[0].message)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("text", ["$x_1$", "Li2O at $T_1$"])
def test_default_shows_mathtext_as_it_is(td, method, text):
    # v3.x inserted subscripts into the mathtext, which could not be drawn.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _draw(method, td, text) == text
    td.fig.canvas.draw()


@pytest.mark.parametrize("method", METHODS)
def test_default_without_numbers_does_not_warn(ax, method):
    td = TernaryDiagram(
        MATERIALS, ax=ax, auto_latex_notation=False, tight_layout=True
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _draw(method, td, "Sample") == "Sample"


def test_warning_is_emitted_once_per_diagram(ax):
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=True)
    with pytest.warns(FutureWarning, match=WARNING_MATCH) as record:
        td.annotate("Sample 1", VECTOR)
        td.annotate("Sample 2", VECTOR)
        td.scatter([VECTOR, VECTOR], annotations=["Run 1", "Run 2"])
    assert len(record) == 1

    other = TernaryDiagram(MATERIALS, ax=ax, tight_layout=True)
    with pytest.warns(FutureWarning, match=WARNING_MATCH) as record:
        other.scatter([VECTOR], annotations=["Run 3"])
    assert len(record) == 1


# --- texts that are not str ---------------------------------------------------


@pytest.mark.parametrize("auto_latex_notation", [None, True, False])
def test_scatter_annotations_that_are_not_str(td, auto_latex_notation):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        shown = _scatter(td, [1, 2.5], auto_latex_notation=auto_latex_notation)
    assert shown == ["1", "2.5"]


@pytest.mark.parametrize("auto_latex_notation", [None, True, False])
def test_annotate_text_that_is_not_str(td, auto_latex_notation):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        shown = _annotate(td, 5, auto_latex_notation=auto_latex_notation)
    assert shown == "5"
