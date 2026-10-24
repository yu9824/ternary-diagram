"""Side effects of the plotting methods on the figure.

Tests of the processing after drawing: the layout adjustment, the automatic
colorbar and the warnings about their defaults. Tests that check a default
create the diagram without ``tight_layout``; the others pass it explicitly
or use the ``td`` fixture.
"""

import inspect
import warnings

import matplotlib.pyplot as plt
import pytest
from matplotlib.colorbar import Colorbar

from ternary_diagram import TernaryDiagram, _api, _post_draw
from ternary_diagram._api import _LinePlotter, _ScatterPlotter
from ternary_diagram._post_draw import PostDrawContext

MATERIALS = ("Li2O", "La2O3", "TiO2")
VECTOR = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
Z = [0.0, 1.0, 2.0]
SUBPLOT_PARAMS = ("left", "bottom", "right", "top", "wspace", "hspace")

requires_layout_engine = pytest.mark.skipif(
    not _post_draw._HAS_LAYOUT_ENGINE,
    reason="Figure.get_layout_engine needs matplotlib >= 3.6",
)

# One call of each plotting method. `scatter_z` and `contour` color by `z`.
DRAWS = [
    pytest.param(lambda td: td.scatter(VECTOR), id="scatter"),
    pytest.param(lambda td: td.scatter(VECTOR, z=Z), id="scatter_z"),
    pytest.param(lambda td: td.contour(VECTOR, z=Z), id="contour"),
    pytest.param(lambda td: td.plot(VECTOR), id="plot"),
    pytest.param(lambda td: td.annotate("A", VECTOR[0]), id="annotate"),
]


def _subplotpars(fig) -> dict:
    return {name: getattr(fig.subplotpars, name) for name in SUBPLOT_PARAMS}


def _is_layout_future_warning(warning) -> bool:
    return issubclass(warning.category, FutureWarning) and (
        "tight_layout" in str(warning.message)
    )


def _messages(record) -> list:
    return [f"{w.category.__name__}: {w.message}" for w in record]


def _post_draw_context(td: TernaryDiagram) -> PostDrawContext:
    return td._TernaryDiagram__post_draw_context


# --- layout: figure without a layout engine ---------------------------------


@pytest.mark.parametrize("draw", DRAWS)
def test_default_layout_is_tightened_with_one_future_warning(draw):
    fig, ax = plt.subplots()
    default = _subplotpars(fig)
    # `tight_layout` is omitted on purpose: this checks the default.
    td = TernaryDiagram(MATERIALS, ax=ax)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        draw(td)
        tightened = _subplotpars(fig)
        fig.subplots_adjust(**default)
        draw(td)

    assert tightened != default
    # The second plot adjusts the layout again, without another warning.
    assert _subplotpars(fig) != default
    layout_warnings = [w for w in record if _is_layout_future_warning(w)]
    assert len(layout_warnings) == 1, _messages(record)
    assert layout_warnings[0].filename == __file__
    message = str(layout_warnings[0].message)
    assert "4.0.0" in message
    assert "tight_layout=True" in message


def test_layout_future_warning_is_issued_once_per_diagram():
    _, axes = plt.subplots(1, 2)
    # `tight_layout` is omitted on purpose: this checks the default.
    diagrams = [TernaryDiagram(MATERIALS, ax=ax) for ax in axes]

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        for td in diagrams:
            td.plot(VECTOR)
            td.scatter(VECTOR)

    layout_warnings = [w for w in record if _is_layout_future_warning(w)]
    assert len(layout_warnings) == len(diagrams), _messages(record)


@pytest.mark.parametrize("draw", DRAWS)
def test_tight_layout_true_tightens_without_warnings(draw):
    fig, ax = plt.subplots()
    default = _subplotpars(fig)
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=True)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        draw(td)

    assert _subplotpars(fig) != default


@requires_layout_engine
@pytest.mark.parametrize("draw", DRAWS)
def test_tight_layout_false_leaves_layout_untouched(draw):
    fig, ax = plt.subplots()
    default = _subplotpars(fig)
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=False)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        draw(td)

    assert _subplotpars(fig) == default
    assert fig.get_layout_engine() is None


# --- layout: figure with a layout engine, subfigure -------------------------


@requires_layout_engine
@pytest.mark.parametrize("tight_layout", [None, True, False])
@pytest.mark.parametrize("draw", DRAWS)
def test_constrained_layout_engine_is_kept_without_warnings(
    draw, tight_layout
):
    from matplotlib.layout_engine import ConstrainedLayoutEngine

    fig, ax = plt.subplots(layout="constrained")
    engine = fig.get_layout_engine()
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=tight_layout)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        draw(td)

    assert isinstance(engine, ConstrainedLayoutEngine)
    assert fig.get_layout_engine() is engine
    assert _messages(record) == []


@requires_layout_engine
def test_constrained_layout_contour_and_scatter_with_colorbars_complete():
    from matplotlib.layout_engine import ConstrainedLayoutEngine

    fig, ax = plt.subplots(layout="constrained")
    engine = fig.get_layout_engine()
    # `tight_layout` is omitted on purpose: this checks the default.
    td = TernaryDiagram(MATERIALS, ax=ax)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        contour = td.contour(VECTOR, z=Z)
        scatter = td.scatter(VECTOR, z=Z)

    assert isinstance(engine, ConstrainedLayoutEngine)
    assert fig.get_layout_engine() is engine
    assert isinstance(contour.colorbar, Colorbar)
    assert isinstance(scatter.colorbar, Colorbar)
    # Neither the layout FutureWarning nor matplotlib's warning that the
    # figure layout has changed.
    assert not [w for w in record if "layout" in str(w.message)], _messages(
        record
    )


@requires_layout_engine
@pytest.mark.parametrize("tight_layout", [None, True])
@pytest.mark.parametrize("draw", DRAWS)
def test_drawing_on_subfigure_leaves_layout_untouched(draw, tight_layout):
    fig = plt.figure()
    subfig, _ = fig.subfigures(1, 2)
    ax = subfig.subplots()
    default = _subplotpars(fig)
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=tight_layout)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        draw(td)

    assert fig.get_layout_engine() is None
    assert _subplotpars(fig) == default
    assert _messages(record) == []


def test_scatter_with_z_on_subfigure_adds_colorbar():
    fig = plt.figure()
    subfig, _ = fig.subfigures(1, 2)
    ax = subfig.subplots()
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=True)

    collection = td.scatter(VECTOR, z=Z)

    assert isinstance(collection.colorbar, Colorbar)
    assert collection.colorbar.ax in subfig.axes


# --- colorbar ---------------------------------------------------------------


def test_scatter_without_z_adds_no_colorbar(td):
    n_axes = len(td.fig.axes)

    collection = td.scatter(VECTOR)

    assert len(td.fig.axes) == n_axes
    assert collection.colorbar is None
    assert not _post_draw_context(td).has_colorbar()


@pytest.mark.parametrize("method", ["scatter", "contour"])
def test_added_colorbar_is_referable_and_registered(td, method):
    n_axes = len(td.fig.axes)

    mappable = getattr(td, method)(VECTOR, z=Z)

    assert len(td.fig.axes) == n_axes + 1
    assert isinstance(mappable.colorbar, Colorbar)
    assert _post_draw_context(td).has_colorbar()


# --- _BasePlotter._post_draw ------------------------------------------------


def test_post_draw_returns_and_registers_the_added_colorbar(ax):
    context = PostDrawContext(tight_layout=False)
    plotter = _LinePlotter(VECTOR, ax=ax, post_draw_context=context)
    mappable = ax.scatter([0.0, 1.0], [0.0, 1.0], c=[0.0, 1.0])

    cbar = plotter._post_draw(mappable=mappable, colorbar=True)

    assert isinstance(cbar, Colorbar)
    assert mappable.colorbar is cbar
    assert context.has_colorbar()
    assert plotter._post_draw(mappable=mappable, colorbar=False) is None
    assert plotter._post_draw() is None


def test_post_draw_warns_about_colorbar_then_layout_once_each(ax):
    context = PostDrawContext()
    existing = ax.scatter([0.0, 1.0], [0.0, 1.0], c=[0.0, 1.0])
    context.register_colorbar(ax.figure.colorbar(existing, ax=ax))
    n_axes = len(ax.figure.axes)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        for _ in range(2):
            _ScatterPlotter(
                VECTOR, ax=ax, z=Z, colorbar=None, post_draw_context=context
            )

    # Both plots add a colorbar, as in v3.x.
    assert len(ax.figure.axes) == n_axes + 2
    assert [w.category for w in record] == [FutureWarning, FutureWarning]
    colorbar_warning, layout_warning = (str(w.message) for w in record)
    assert "`scatter` added another colorbar" in colorbar_warning
    assert "tight_layout=True" in layout_warning
    assert all(w.filename == __file__ for w in record)


def test_plotters_require_post_draw_context(ax):
    with pytest.raises(TypeError, match="post_draw_context"):
        _LinePlotter(VECTOR, ax=ax)


# --- docstrings -------------------------------------------------------------


def _private_docstrings_in_api():
    """Yield ``(qualified name, docstring)`` of the private code in _api."""
    for name, obj in vars(_api).items():
        if getattr(obj, "__module__", None) != _api.__name__:
            continue
        if inspect.isfunction(obj):
            if name.startswith("_"):
                yield name, obj.__doc__
            continue
        if not inspect.isclass(obj):
            continue
        private_class = name.startswith("_")
        if private_class:
            yield name, obj.__doc__
        for attr, value in vars(obj).items():
            if isinstance(value, (staticmethod, classmethod)):
                value = value.__func__
            if isinstance(value, property):
                value = value.fget
            if not inspect.isfunction(value):
                continue
            if private_class or (attr.startswith("_") and attr != "__init__"):
                yield f"{name}.{attr}", value.__doc__


def test_private_docstrings_in_api_have_no_doctest_examples():
    docstrings = dict(_private_docstrings_in_api())

    assert {
        "_BasePlotter._set_default_params",
        "_BasePlotter._merge_alias",
        "_BasePlotter._post_draw",
    } <= docstrings.keys()
    assert [
        name for name, doc in docstrings.items() if doc and ">>>" in doc
    ] == []
