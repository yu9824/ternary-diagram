"""Side effects of the plotting methods on the figure.

Tests of the processing after drawing: the layout adjustment, the automatic
colorbar and the warnings about their defaults. Tests that check a default
create the diagram without ``tight_layout``; the others pass it explicitly
or use the ``td`` fixture.
"""

import inspect
import warnings

import matplotlib.pyplot as plt
import numpy as np
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


# --- `colorbar` argument and the deprecated `flag_cbar` alias ---------------

COLORED_METHODS = ["scatter", "contour"]
# Positional arguments between `z` and `colorbar`: `z_min`, `z_max`, then
# `annotations` for scatter and `fill` for contour.
BEFORE_COLORBAR = {
    "scatter": (None, None, None),
    "contour": (None, None, True),
}
RENAME_MATCH = "`flag_cbar` of `{method}` was renamed to `colorbar`"
COLORBAR_TYPE_ERROR = "`colorbar` must be None, True or False, but got"
BOTH_VALUE_ERROR = "`flag_cbar` and `colorbar` cannot be specified at the same"


@pytest.fixture
def tight_td(ax) -> TernaryDiagram:
    # `tight_layout` is explicit so that no layout FutureWarning is issued.
    return TernaryDiagram(MATERIALS, ax=ax, tight_layout=True)


def _draw_with_positional_colorbar(td, method, value, **kwargs):
    """Call `method` of `td` with `value` as the sixth positional argument."""
    return getattr(td, method)(
        VECTOR, Z, *BEFORE_COLORBAR[method], value, **kwargs
    )


def _parameter_entries(func) -> dict:
    """Map each name in the Parameters section to its type line and text."""
    lines = inspect.cleandoc(func.__doc__).splitlines()
    # Skip the header and its underline.
    start = lines.index("Parameters") + 2
    entries = {}
    name = None
    for line in lines[start:]:
        if line and not line.startswith(" "):
            if " : " not in line:
                break  # the next section
            name = line.split(" : ")[0]
            entries[name] = (line, [])
        elif name is not None and line.strip():
            entries[name][1].append(line.strip())
    return {
        key: (head, " ".join(text)) for key, (head, text) in entries.items()
    }


@pytest.mark.parametrize("method", COLORED_METHODS)
def test_colorbar_takes_the_sixth_position_formerly_of_flag_cbar(method):
    parameters = list(
        inspect.signature(getattr(TernaryDiagram, method)).parameters.values()
    )

    # `self` comes first, so the sixth argument is at index 6.
    assert parameters[6].name == "colorbar"
    assert parameters[6].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[6].default is None
    assert "flag_cbar" not in [p.name for p in parameters]


@pytest.mark.parametrize("value", [False, np.bool_(False)])
@pytest.mark.parametrize("method", COLORED_METHODS)
def test_colorbar_false_adds_no_colorbar(tight_td, method, value):
    n_axes = len(tight_td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mappable = getattr(tight_td, method)(VECTOR, z=Z, colorbar=value)

    assert len(tight_td.fig.axes) == n_axes
    assert mappable.colorbar is None
    assert not _post_draw_context(tight_td).has_colorbar()


@pytest.mark.parametrize(
    ("kwargs", "added", "n_warnings"),
    [
        pytest.param({"colorbar": True}, True, 0, id="true"),
        pytest.param({}, True, 1, id="omitted"),
        pytest.param({"colorbar": False}, False, 0, id="false"),
    ],
)
@pytest.mark.parametrize("method", COLORED_METHODS)
def test_colorbar_value_reaches_the_plotter(
    tight_td, method, kwargs, added, n_warnings
):
    tight_td.contour(VECTOR, z=Z)  # the diagram has a colorbar now
    n_axes = len(tight_td.fig.axes)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        mappable = getattr(tight_td, method)(VECTOR, z=Z, **kwargs)

    assert len(tight_td.fig.axes) == n_axes + added
    assert (mappable.colorbar is not None) is added
    # Only the omitted `colorbar` warns about the duplicate colorbar.
    assert len(record) == n_warnings, _messages(record)
    assert all("added another colorbar" in str(w.message) for w in record)


@pytest.mark.parametrize("value", [1, 0, "yes"])
@pytest.mark.parametrize("method", COLORED_METHODS)
def test_non_bool_colorbar_raises_type_error(tight_td, method, value):
    with pytest.raises(TypeError, match=COLORBAR_TYPE_ERROR):
        getattr(tight_td, method)(VECTOR, z=Z, colorbar=value)


@pytest.mark.parametrize(("value", "added"), [(True, True), (False, False)])
@pytest.mark.parametrize("method", COLORED_METHODS)
def test_sixth_positional_bool_keeps_its_meaning(
    tight_td, method, value, added
):
    n_axes = len(tight_td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mappable = _draw_with_positional_colorbar(tight_td, method, value)

    assert len(tight_td.fig.axes) == n_axes + added
    assert (mappable.colorbar is not None) is added


@pytest.mark.parametrize("value", [1, 0])
@pytest.mark.parametrize("method", COLORED_METHODS)
def test_sixth_positional_non_bool_raises_type_error(tight_td, method, value):
    n_children = len(tight_td.ax.get_children())

    with pytest.raises(TypeError, match=COLORBAR_TYPE_ERROR):
        _draw_with_positional_colorbar(tight_td, method, value)

    # The value is checked before anything is drawn.
    assert len(tight_td.ax.get_children()) == n_children


@pytest.mark.parametrize(
    ("flag_cbar", "added"),
    [(True, True), (False, False), (1, True), (0, False)],
)
@pytest.mark.parametrize("method", COLORED_METHODS)
def test_flag_cbar_keeps_its_meaning_with_a_rename_warning(
    tight_td, method, flag_cbar, added
):
    n_axes = len(tight_td.fig.axes)

    with pytest.warns(
        FutureWarning, match=RENAME_MATCH.format(method=method)
    ) as record:
        mappable = getattr(tight_td, method)(VECTOR, z=Z, flag_cbar=flag_cbar)

    assert len(tight_td.fig.axes) == n_axes + added
    assert (mappable.colorbar is not None) is added
    assert len(record) == 1, _messages(record)
    assert record[0].filename == __file__
    assert "4.0.0" in str(record[0].message)


@pytest.mark.parametrize("method", COLORED_METHODS)
def test_flag_cbar_is_explicit_and_skips_the_duplicate_warning(
    tight_td, method
):
    tight_td.contour(VECTOR, z=Z)  # the diagram has a colorbar now
    n_axes = len(tight_td.fig.axes)

    with pytest.warns(FutureWarning) as record:
        getattr(tight_td, method)(VECTOR, z=Z, flag_cbar=True)

    assert len(tight_td.fig.axes) == n_axes + 1
    # The rename warning only, without the duplicate colorbar warning.
    assert len(record) == 1, _messages(record)
    assert RENAME_MATCH.format(method=method) in str(record[0].message)


@pytest.mark.parametrize(
    ("flag_cbar", "colorbar"), [(True, False), (False, True), (False, False)]
)
@pytest.mark.parametrize("positional", [False, True])
@pytest.mark.parametrize("method", COLORED_METHODS)
def test_flag_cbar_with_colorbar_raises_value_error(
    tight_td, method, positional, flag_cbar, colorbar
):
    n_children = len(tight_td.ax.get_children())

    with pytest.raises(ValueError, match=BOTH_VALUE_ERROR):
        if positional:
            _draw_with_positional_colorbar(
                tight_td, method, colorbar, flag_cbar=flag_cbar
            )
        else:
            getattr(tight_td, method)(
                VECTOR, z=Z, colorbar=colorbar, flag_cbar=flag_cbar
            )

    # The arguments are resolved before anything is drawn.
    assert len(tight_td.ax.get_children()) == n_children


@pytest.mark.parametrize("method", COLORED_METHODS)
def test_colorbar_and_flag_cbar_parameter_entries(method):
    entries = _parameter_entries(getattr(TernaryDiagram, method))
    names = list(entries)

    assert names[names.index("colorbar") + 1] == "flag_cbar"
    colorbar_head, colorbar_text = entries["colorbar"]
    assert colorbar_head == "colorbar : bool or None, optional"
    assert colorbar_text.startswith("Whether to add a colorbar automatically")
    assert colorbar_text.endswith(", by default None")
    assert "4.0.0" in colorbar_text
    # The colorbars added directly with matplotlib are not counted.
    assert "fig.colorbar" in colorbar_text
    flag_head, flag_text = entries["flag_cbar"]
    assert flag_head == "flag_cbar : bool, optional"
    assert flag_text.startswith("Deprecated alias of `colorbar`")
    assert "4.0.0" in flag_text
    assert "ValueError" in flag_text
    assert "by default" not in flag_text
