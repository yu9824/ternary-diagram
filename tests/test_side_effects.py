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


# Essentials of the warning messages, checked with `match=` instead of the
# full text. The lookaheads let the layout pattern ignore their order.
LAYOUT_WARNING_MATCH = r"(?s)(?=.*4\.0\.0)(?=.*`tight_layout=True`)"
DUPLICATE_COLORBAR_MATCH = "`{method}` added another colorbar"


def _subplotpars(fig) -> dict:
    return {name: getattr(fig.subplotpars, name) for name in SUBPLOT_PARAMS}


def _reset_subplotpars(fig, params: dict) -> None:
    """Restore the margins, so that the next plot shows if it adjusts them."""
    fig.subplots_adjust(**params)
    assert _subplotpars(fig) == params


def _is_layout_future_warning(warning) -> bool:
    return issubclass(warning.category, FutureWarning) and (
        "tight_layout" in str(warning.message)
    )


def _is_duplicate_colorbar_warning(warning) -> bool:
    return issubclass(warning.category, FutureWarning) and (
        "added another colorbar" in str(warning.message)
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

    with pytest.warns(FutureWarning, match=LAYOUT_WARNING_MATCH) as record:
        draw(td)

    assert _subplotpars(fig) != default
    # The layout warning is the only warning of the first plot, and it is
    # located in this file, which called the plotting method.
    assert len(record) == 1, _messages(record)
    assert _is_layout_future_warning(record[0])
    assert record[0].filename == __file__

    _reset_subplotpars(fig, default)
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        draw(td)

    # The second plot adjusts the layout again, without another layout
    # warning. Only `scatter_z` and `contour` warn, about their duplicate
    # colorbar, which has its own reason.
    assert _subplotpars(fig) != default
    assert [
        w for w in record if not _is_duplicate_colorbar_warning(w)
    ] == [], _messages(record)


def test_layout_future_warning_is_issued_once_per_diagram():
    _, axes = plt.subplots(1, 2)
    # `tight_layout` is omitted on purpose: this checks the default.
    diagrams = [TernaryDiagram(MATERIALS, ax=ax) for ax in axes]

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        for td in diagrams:
            # All the plotting methods share the setting of the diagram.
            td.plot(VECTOR)
            td.scatter(VECTOR)
            td.contour(VECTOR, z=Z)
            td.annotate("A", VECTOR[0])

    layout_warnings = [w for w in record if _is_layout_future_warning(w)]
    assert len(layout_warnings) == len(diagrams), _messages(record)
    assert len(record) == len(diagrams), _messages(record)


@pytest.mark.parametrize("draw", DRAWS)
def test_tight_layout_true_tightens_without_warnings(draw):
    fig, ax = plt.subplots()
    default = _subplotpars(fig)
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=True)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        draw(td)

    assert _subplotpars(fig) != default

    _reset_subplotpars(fig, default)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        # The duplicate colorbar of `scatter_z` and `contour` is not about
        # the layout.
        warnings.filterwarnings(
            "ignore",
            message=".*added another colorbar",
            category=FutureWarning,
        )
        draw(td)

    # Every plot adjusts the layout, not only the first one.
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

    with pytest.warns(
        FutureWarning, match=DUPLICATE_COLORBAR_MATCH.format(method="scatter")
    ) as record:
        contour = td.contour(VECTOR, z=Z)
        scatter = td.scatter(VECTOR, z=Z)

    assert isinstance(engine, ConstrainedLayoutEngine)
    assert fig.get_layout_engine() is engine
    assert isinstance(contour.colorbar, Colorbar)
    assert isinstance(scatter.colorbar, Colorbar)
    # The duplicate colorbar warning is the only warning.
    assert len(record) == 1, _messages(record)
    assert _is_duplicate_colorbar_warning(record[0])
    assert record[0].filename == __file__
    # Neither the layout FutureWarning nor matplotlib's warning that the
    # figure layout has changed.
    assert not [w for w in record if "layout" in str(w.message)], _messages(
        record
    )


@requires_layout_engine
@pytest.mark.parametrize("tight_layout", [None, True, False])
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


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"colorbar": True}, {"colorbar": False}],
    ids=["omitted", "true", "false"],
)
def test_scatter_without_z_adds_no_colorbar(td, kwargs):
    n_axes = len(td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        # Even `colorbar=True` adds none: the points are not colored by
        # values.
        collection = td.scatter(VECTOR, **kwargs)

    assert len(td.fig.axes) == n_axes
    assert collection.colorbar is None
    assert not _post_draw_context(td).has_colorbar()


@pytest.mark.parametrize("method", ["scatter", "contour"])
def test_added_colorbar_is_referable_and_registered(td, method):
    axes_before = list(td.fig.axes)
    n_axes = len(td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        # The first colorbar of the diagram is added without any warning.
        mappable = getattr(td, method)(VECTOR, z=Z)

    assert len(td.fig.axes) == n_axes + 1
    assert isinstance(mappable.colorbar, Colorbar)
    # The returned object refers to the colorbar that was added.
    added_axes = [a for a in td.fig.axes if a not in axes_before]
    assert added_axes == [mappable.colorbar.ax]
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


# --- colorbar: diagrams that already have a colorbar ------------------------

# One call of each plotting method colored by `z`. Each lambda stays on one
# line, the line of the plotting call, so that a warning located at the call
# is located at the first line of the lambda.
COLORED_DRAWS = {
    "scatter": lambda td, **kwargs: td.scatter(VECTOR, z=Z, **kwargs),
    "contour": lambda td, **kwargs: td.contour(VECTOR, z=Z, **kwargs),
}


def _assert_located_at_call(warning, draw) -> None:
    """Assert that `warning` points to the plotting call in `draw`."""
    assert warning.filename == __file__
    assert warning.lineno == draw.__code__.co_firstlineno


@pytest.mark.parametrize("third", COLORED_METHODS)
def test_default_duplicate_colorbar_is_added_with_one_future_warning(
    tight_td, third
):
    n_axes = len(tight_td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        tight_td.contour(VECTOR, z=Z)
    with pytest.warns(
        FutureWarning, match=DUPLICATE_COLORBAR_MATCH.format(method="scatter")
    ) as record:
        scatter = COLORED_DRAWS["scatter"](tight_td)

    # Two colorbars, as in v3.x, and one warning located at the call.
    assert len(tight_td.fig.axes) == n_axes + 2
    assert isinstance(scatter.colorbar, Colorbar)
    assert len(record) == 1, _messages(record)
    _assert_located_at_call(record[0], COLORED_DRAWS["scatter"])
    assert "4.0.0" in str(record[0].message)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mappable = COLORED_DRAWS[third](tight_td)

    # The third plot adds a colorbar again, without another warning.
    assert len(tight_td.fig.axes) == n_axes + 3
    assert isinstance(mappable.colorbar, Colorbar)


def test_duplicate_colorbar_warning_is_issued_once_per_diagram():
    _, axes = plt.subplots(1, 2)
    diagrams = [
        TernaryDiagram(MATERIALS, ax=ax, tight_layout=True) for ax in axes
    ]

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        for td in diagrams:
            for method in ["contour", "scatter", "scatter"]:
                COLORED_DRAWS[method](td)

    assert len(record) == len(diagrams), _messages(record)
    assert all(_is_duplicate_colorbar_warning(w) for w in record)


@pytest.mark.parametrize("explicit", [True, False])
@pytest.mark.parametrize("method", COLORED_METHODS)
def test_explicit_colorbar_does_not_use_up_the_duplicate_warning(
    tight_td, method, explicit
):
    draw = COLORED_DRAWS[method]
    tight_td.contour(VECTOR, z=Z)  # the diagram has a colorbar now
    n_axes = len(tight_td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        draw(tight_td, colorbar=explicit)
    # The explicit `colorbar` issued no warning, so the first plot with the
    # default still warns.
    with pytest.warns(
        FutureWarning, match=DUPLICATE_COLORBAR_MATCH.format(method=method)
    ) as record:
        draw(tight_td)

    assert len(tight_td.fig.axes) == n_axes + explicit + 1
    assert len(record) == 1, _messages(record)


@pytest.mark.parametrize("method", COLORED_METHODS)
def test_colorbar_made_with_colorbar_method_counts(tight_td, method):
    tight_td.colorbar(tight_td.scatter(VECTOR, z=Z, colorbar=False))
    n_axes = len(tight_td.fig.axes)

    with pytest.warns(
        FutureWarning, match=DUPLICATE_COLORBAR_MATCH.format(method=method)
    ) as record:
        mappable = COLORED_DRAWS[method](tight_td)

    assert len(tight_td.fig.axes) == n_axes + 1
    assert isinstance(mappable.colorbar, Colorbar)
    assert len(record) == 1, _messages(record)


@pytest.mark.parametrize("method", COLORED_METHODS)
def test_colorbar_made_with_fig_colorbar_is_not_counted(tight_td, method):
    existing = tight_td.scatter(VECTOR, z=Z, colorbar=False)
    tight_td.fig.colorbar(existing, ax=tight_td.ax)
    n_axes = len(tight_td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mappable = COLORED_DRAWS[method](tight_td)

    # Added as the first colorbar of the diagram, without a warning.
    assert len(tight_td.fig.axes) == n_axes + 1
    assert isinstance(mappable.colorbar, Colorbar)


@pytest.mark.parametrize("made_with", ["plotting", "colorbar_method"])
@pytest.mark.parametrize("method", COLORED_METHODS)
def test_removed_colorbar_is_not_counted(tight_td, method, made_with):
    if made_with == "plotting":
        cbar = tight_td.contour(VECTOR, z=Z).colorbar
    else:
        cbar = tight_td.colorbar(tight_td.scatter(VECTOR, z=Z, colorbar=False))
    cbar.remove()
    n_axes = len(tight_td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        mappable = COLORED_DRAWS[method](tight_td)

    assert len(tight_td.fig.axes) == n_axes + 1
    assert isinstance(mappable.colorbar, Colorbar)


@pytest.mark.parametrize("method", COLORED_METHODS)
def test_colorbar_left_after_removing_another_counts(tight_td, method):
    removed = tight_td.contour(VECTOR, z=Z).colorbar
    tight_td.scatter(VECTOR, z=Z, colorbar=True)
    removed.remove()

    with pytest.warns(
        FutureWarning, match=DUPLICATE_COLORBAR_MATCH.format(method=method)
    ) as record:
        COLORED_DRAWS[method](tight_td)

    assert len(record) == 1, _messages(record)


@pytest.mark.parametrize("colorbar", [None, True])
def test_scatter_without_z_adds_no_colorbar_to_diagram_with_one(
    tight_td, colorbar
):
    tight_td.contour(VECTOR, z=Z)  # the diagram has a colorbar now
    n_axes = len(tight_td.fig.axes)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        collection = tight_td.scatter(VECTOR, colorbar=colorbar)

    assert len(tight_td.fig.axes) == n_axes
    assert collection.colorbar is None


@pytest.mark.parametrize("method", COLORED_METHODS)
def test_rename_and_duplicate_warnings_point_to_the_plotting_call(
    tight_td, method
):
    draw = COLORED_DRAWS[method]
    tight_td.contour(VECTOR, z=Z)  # the diagram has a colorbar now

    with pytest.warns(FutureWarning) as record:
        draw(tight_td)
        draw(tight_td, flag_cbar=True)

    assert len(record) == 2, _messages(record)
    duplicate, rename = record
    assert _is_duplicate_colorbar_warning(duplicate)
    assert RENAME_MATCH.format(method=method) in str(rename.message)
    _assert_located_at_call(duplicate, draw)
    _assert_located_at_call(rename, draw)


# --- colorbar: defaults on a figure without a layout engine -----------------

# Keyword arguments of the colorbar that v3.2.1 added after plotting, which
# are the defaults of `TernaryDiagram.colorbar`.
V3_COLORBAR_KWARGS = {
    "shrink": 0.8,
    "format": "%.1f",
    "label": "",
    "orientation": "vertical",
    "location": "right",
}


def test_defaults_add_a_colorbar_for_each_plot_colored_by_values():
    fig, ax = plt.subplots()
    # `tight_layout` is omitted on purpose: this checks the defaults.
    td = TernaryDiagram(MATERIALS, ax=ax)
    n_axes = len(fig.axes)
    methods = ["contour", "scatter", "scatter", "contour"]

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        for n_colorbars, method in enumerate(methods, start=1):
            mappable = COLORED_DRAWS[method](td)
            # As in v3.2.1, each plot colored by values adds a colorbar.
            assert len(fig.axes) == n_axes + n_colorbars
            assert isinstance(mappable.colorbar, Colorbar)
        # The plots not colored by values add none.
        td.scatter(VECTOR)
        td.plot(VECTOR)

    assert len(fig.axes) == n_axes + len(methods)
    # Each default that changes in 4.0.0 warns once for the diagram.
    assert len(record) == 2, _messages(record)
    assert sum(_is_layout_future_warning(w) for w in record) == 1
    assert sum(_is_duplicate_colorbar_warning(w) for w in record) == 1


def _layout_of(fig) -> tuple:
    """Margins and the position of every Axes, colorbars included."""
    return _subplotpars(fig), [a.get_position().bounds for a in fig.axes]


def _layout_of_contour_processed_directly(colorbar_first: bool) -> tuple:
    """Layout of a contour whose colorbar and layout are left to the user.

    The diagram neither adds the colorbar nor adjusts the layout itself:
    ``fig.colorbar`` and ``fig.tight_layout`` are called here directly, in
    the order that `colorbar_first` tells.
    """
    fig, ax = plt.subplots()
    td = TernaryDiagram(MATERIALS, ax=ax, tight_layout=False)
    contour = td.contour(VECTOR, z=Z, colorbar=False)
    steps = [
        lambda: fig.colorbar(contour, ax=ax, **V3_COLORBAR_KWARGS),
        fig.tight_layout,
    ]
    for step in steps if colorbar_first else reversed(steps):
        step()
    return _layout_of(fig)


def test_default_margins_are_those_of_colorbar_then_tight_layout():
    fig, ax = plt.subplots()
    # `tight_layout` is omitted on purpose: this checks the defaults.
    td = TernaryDiagram(MATERIALS, ax=ax)

    with pytest.warns(FutureWarning, match=LAYOUT_WARNING_MATCH):
        td.contour(VECTOR, z=Z)

    # The same margins and colorbar position as v3.2.1, which added the
    # colorbar first and then called `Figure.tight_layout()`.
    layout = _layout_of(fig)
    assert layout == _layout_of_contour_processed_directly(True)
    # The other order gives another layout, so the order is checked above.
    assert layout != _layout_of_contour_processed_directly(False)


# --- flag_cbar with None, as its value or as `colorbar` ----------------------


@pytest.mark.parametrize("method", COLORED_METHODS)
def test_flag_cbar_none_adds_no_colorbar_as_before(tight_td, method):
    draw = COLORED_DRAWS[method]
    n_axes = len(tight_td.fig.axes)

    with pytest.warns(
        FutureWarning, match=RENAME_MATCH.format(method=method)
    ) as record:
        mappable = draw(tight_td, flag_cbar=None)

    # `flag_cbar` is interpreted as true or false, and None is false.
    assert len(tight_td.fig.axes) == n_axes
    assert mappable.colorbar is None
    assert len(record) == 1, _messages(record)
    _assert_located_at_call(record[0], draw)


@pytest.mark.parametrize("positional", [False, True])
@pytest.mark.parametrize(
    ("flag_cbar", "added"), [(True, True), (False, False)]
)
@pytest.mark.parametrize("method", COLORED_METHODS)
def test_colorbar_none_with_flag_cbar_lets_flag_cbar_decide(
    tight_td, method, flag_cbar, added, positional
):
    n_axes = len(tight_td.fig.axes)

    # None means that `colorbar` is not specified, so no ValueError.
    with pytest.warns(
        FutureWarning, match=RENAME_MATCH.format(method=method)
    ) as record:
        if positional:
            mappable = _draw_with_positional_colorbar(
                tight_td, method, None, flag_cbar=flag_cbar
            )
        else:
            mappable = getattr(tight_td, method)(
                VECTOR, z=Z, colorbar=None, flag_cbar=flag_cbar
            )

    assert len(tight_td.fig.axes) == n_axes + added
    assert (mappable.colorbar is not None) is added
    assert len(record) == 1, _messages(record)
