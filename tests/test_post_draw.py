import matplotlib
import matplotlib.pyplot as plt
import pytest

from ternary_diagram import _post_draw
from ternary_diagram._deprecation import FUTURE_VERSION
from ternary_diagram._post_draw import (
    COLORBAR_WARNING_KEY,
    LAYOUT_WARNING_KEY,
    ColorbarAction,
    LayoutAction,
    LayoutState,
    PostDrawContext,
    colorbar_warning_message,
    decide_colorbar,
    decide_layout,
    get_layout_state,
    layout_warning_message,
)

requires_layout_engine = pytest.mark.skipif(
    not _post_draw._HAS_LAYOUT_ENGINE,
    reason="Figure.get_layout_engine needs matplotlib >= 3.6",
)


@pytest.fixture
def without_layout_engine(monkeypatch):
    """Take the branch for matplotlib < 3.6."""
    monkeypatch.setattr(_post_draw, "_HAS_LAYOUT_ENGINE", False)


def test_has_layout_engine_matches_matplotlib():
    # The skipif above relies on this constant, so check it independently.
    assert _post_draw._HAS_LAYOUT_ENGINE == hasattr(
        matplotlib.figure.Figure, "get_layout_engine"
    )


def test_get_layout_state_annotations_are_not_evaluated():
    # Evaluating them would fail on old matplotlib (``FigureBase``) and on
    # Python 3.9 (``X | None``).
    annotations = get_layout_state.__annotations__
    assert annotations
    assert all(isinstance(value, str) for value in annotations.values())


@requires_layout_engine
@pytest.mark.parametrize(
    "fig_kw", [{}, {"layout": None}, {"layout": "none"}], ids=repr
)
def test_get_layout_state_new_figure_has_no_engine(fig_kw):
    fig, _ = plt.subplots(**fig_kw)
    assert fig.get_layout_engine() is None
    assert get_layout_state(fig) is LayoutState.NO_ENGINE


@requires_layout_engine
def test_get_layout_state_after_tight_layout_has_no_engine():
    from matplotlib.layout_engine import PlaceHolderLayoutEngine

    fig, _ = plt.subplots()
    fig.tight_layout()
    # Figure.tight_layout() leaves a placeholder engine behind.
    assert isinstance(fig.get_layout_engine(), PlaceHolderLayoutEngine)
    assert get_layout_state(fig) is LayoutState.NO_ENGINE
    # It stays so after a second adjustment.
    fig.tight_layout()
    assert get_layout_state(fig) is LayoutState.NO_ENGINE


@requires_layout_engine
@pytest.mark.parametrize("layout", ["constrained", "compressed", "tight"])
def test_get_layout_state_layout_argument_has_engine(layout):
    fig, _ = plt.subplots(layout=layout)
    assert get_layout_state(fig) is LayoutState.HAS_ENGINE


@requires_layout_engine
@pytest.mark.parametrize(
    "rc", ["figure.autolayout", "figure.constrained_layout.use"]
)
def test_get_layout_state_rcparams_has_engine(rc):
    with matplotlib.rc_context({rc: True}):
        fig, _ = plt.subplots()
    assert fig.get_layout_engine() is not None
    assert get_layout_state(fig) is LayoutState.HAS_ENGINE


@pytest.mark.parametrize("layout", [None, "constrained"])
def test_get_layout_state_subfigure_is_unsupported(layout):
    subfig = plt.figure(layout=layout).subfigures(1, 2)[0]
    assert get_layout_state(subfig) is LayoutState.UNSUPPORTED
    nested = subfig.subfigures(2, 1)[0]
    assert get_layout_state(nested) is LayoutState.UNSUPPORTED


# matplotlib < 3.6: the state comes from the constrained and tight flags.


@pytest.mark.usefixtures("without_layout_engine")
@pytest.mark.parametrize("layout", [None, "constrained"])
@pytest.mark.parametrize(
    ("constrained", "tight", "expected"),
    [
        (False, False, LayoutState.NO_ENGINE),
        (True, False, LayoutState.HAS_ENGINE),
        (False, True, LayoutState.HAS_ENGINE),
        (True, True, LayoutState.HAS_ENGINE),
    ],
)
def test_get_layout_state_old_matplotlib_uses_flags(
    monkeypatch, layout, constrained, tight, expected
):
    # The actual engine of the figure must not matter, only the flags.
    fig = plt.figure(layout=layout)
    monkeypatch.setattr(fig, "get_constrained_layout", lambda: constrained)
    monkeypatch.setattr(fig, "get_tight_layout", lambda: tight)
    assert get_layout_state(fig) is expected


@pytest.mark.usefixtures("without_layout_engine")
@pytest.mark.parametrize(
    ("fig_kw", "rc", "expected"),
    [
        ({}, {}, LayoutState.NO_ENGINE),
        ({"layout": "constrained"}, {}, LayoutState.HAS_ENGINE),
        ({"layout": "tight"}, {}, LayoutState.HAS_ENGINE),
        ({}, {"figure.autolayout": True}, LayoutState.HAS_ENGINE),
        ({}, {"figure.constrained_layout.use": True}, LayoutState.HAS_ENGINE),
    ],
    ids=["new", "constrained", "tight", "autolayout", "constrained_use"],
)
def test_get_layout_state_old_matplotlib_real_figure(fig_kw, rc, expected):
    with matplotlib.rc_context(rc):
        fig, _ = plt.subplots(**fig_kw)
    assert get_layout_state(fig) is expected


@pytest.mark.usefixtures("without_layout_engine")
def test_get_layout_state_old_matplotlib_after_tight_layout():
    fig, _ = plt.subplots()
    fig.tight_layout()
    assert get_layout_state(fig) is LayoutState.NO_ENGINE


@pytest.mark.usefixtures("without_layout_engine")
def test_get_layout_state_old_matplotlib_subfigure_is_unsupported():
    subfig = plt.figure().subfigures(1, 2)[0]
    assert get_layout_state(subfig) is LayoutState.UNSUPPORTED


# Decision tables of design.md "決定表（v3.x）". Each row maps a setting to the
# names of the actions in the order of the columns, so that the tables can be
# compared with the design line by line.

LAYOUT_COLUMNS = (
    LayoutState.NO_ENGINE,
    LayoutState.HAS_ENGINE,
    LayoutState.UNSUPPORTED,
)
LAYOUT_TABLE = {
    None: ("APPLY_AND_WARN", "SKIP", "SKIP"),
    True: ("APPLY", "SKIP", "SKIP"),
    False: ("SKIP", "SKIP", "SKIP"),
}

# Columns as (has_mappable, has_existing): no mappable, a mappable on a
# diagram without a colorbar, and a mappable on a diagram with one.
COLORBAR_COLUMNS = ((False, False), (True, False), (True, True))
COLORBAR_TABLE = {
    None: ("SKIP", "ADD", "ADD_AND_WARN"),
    True: ("SKIP", "ADD", "ADD"),
    False: ("SKIP", "SKIP", "SKIP"),
}

LAYOUT_CELLS = [
    pytest.param(
        setting, state, LayoutAction[name], id=f"{setting}-{state.name}"
    )
    for setting, names in LAYOUT_TABLE.items()
    for state, name in zip(LAYOUT_COLUMNS, names)
]
COLORBAR_CELLS = [
    pytest.param(
        requested,
        has_mappable,
        has_existing,
        ColorbarAction[name],
        id=f"{requested}-mappable={has_mappable}-existing={has_existing}",
    )
    for requested, names in COLORBAR_TABLE.items()
    for (has_mappable, has_existing), name in zip(COLORBAR_COLUMNS, names)
]


@pytest.mark.parametrize(
    ("table", "columns"),
    [(LAYOUT_TABLE, LAYOUT_COLUMNS), (COLORBAR_TABLE, COLORBAR_COLUMNS)],
    ids=["layout", "colorbar"],
)
def test_decision_tables_have_nine_cells(table, columns):
    # zip() above would drop a missing or an extra cell silently.
    assert list(table) == [None, True, False]
    assert len(columns) == 3
    assert all(len(names) == len(columns) for names in table.values())


def test_layout_columns_cover_every_state():
    assert set(LAYOUT_COLUMNS) == set(LayoutState)


@pytest.mark.parametrize(
    ("action", "members"),
    [
        (
            LayoutAction,
            {
                "SKIP": "skip",
                "APPLY": "apply",
                "APPLY_AND_WARN": "apply_and_warn",
            },
        ),
        (
            ColorbarAction,
            {"SKIP": "skip", "ADD": "add", "ADD_AND_WARN": "add_and_warn"},
        ),
    ],
    ids=["layout", "colorbar"],
)
def test_action_members(action, members):
    assert {member.name: member.value for member in action} == members


@pytest.mark.parametrize(("setting", "state", "expected"), LAYOUT_CELLS)
def test_decide_layout(setting, state, expected):
    assert decide_layout(setting, state) is expected


@pytest.mark.parametrize(
    ("requested", "has_mappable", "has_existing", "expected"),
    COLORBAR_CELLS,
)
def test_decide_colorbar(requested, has_mappable, has_existing, expected):
    action = decide_colorbar(
        requested, has_mappable=has_mappable, has_existing=has_existing
    )
    assert action is expected


@pytest.mark.parametrize("requested", [None, True, False])
def test_decide_colorbar_without_mappable_ignores_existing(requested):
    # The "no mappable" column holds whether the diagram has a colorbar or
    # not.
    action = decide_colorbar(requested, has_mappable=False, has_existing=True)
    assert action is ColorbarAction.SKIP


def test_decide_colorbar_flags_are_keyword_only():
    with pytest.raises(TypeError):
        decide_colorbar(None, True, False)


@pytest.mark.parametrize(
    "func",
    [
        decide_layout,
        decide_colorbar,
        layout_warning_message,
        colorbar_warning_message,
    ],
    ids=lambda func: func.__name__,
)
def test_policy_annotations_are_not_evaluated(func):
    # ``bool | None`` would fail on Python 3.9 if it were evaluated.
    annotations = func.__annotations__
    assert annotations
    assert all(isinstance(value, str) for value in annotations.values())


def test_warning_keys():
    assert LAYOUT_WARNING_KEY == "layout.tight_layout"
    assert COLORBAR_WARNING_KEY == "colorbar.duplicate"


def _assert_contains_in_order(text, parts):
    for part in parts:
        assert part in text
    positions = [text.index(part) for part in parts]
    assert positions == sorted(positions)


def test_layout_warning_message():
    message = layout_warning_message()
    assert "4.0.0" in message
    # The order of format_default_change: what happened, the version and the
    # new behavior, how to keep the current behavior, how to adopt the new.
    _assert_contains_in_order(
        message,
        [
            "TernaryDiagram called `Figure.tight_layout()` after plotting",
            "`tight_layout` was not specified.",
            f"In ternary-diagram {FUTURE_VERSION}, ",
            "(tight_layout=False).",
            "To keep the current behavior, pass `tight_layout=True` to "
            "`TernaryDiagram`.",
            "To adopt the new behavior now, pass `tight_layout=False` and "
            "call `fig.tight_layout()` yourself",
            'create the figure with `layout="constrained"`.',
        ],
    )


FUNCS_WITH_COLORBAR = ["scatter", "contour", "tripcolor", "heatmapf"]


@pytest.mark.parametrize("func", FUNCS_WITH_COLORBAR)
def test_colorbar_warning_message(func):
    message = colorbar_warning_message(func)
    assert message.startswith(
        f"`{func}` added another colorbar to this diagram, which already "
        "has one, because `colorbar` was not specified. "
    )
    assert "4.0.0" in message
    _assert_contains_in_order(
        message,
        [
            f"In ternary-diagram {FUTURE_VERSION}, ",
            "only when the diagram has none.",
            "To keep the current behavior, pass `colorbar=True`.",
            "To adopt the new behavior now, pass `colorbar=False`.",
        ],
    )


@pytest.mark.parametrize("func", FUNCS_WITH_COLORBAR)
def test_colorbar_warning_message_does_not_mention_z(func):
    # Plots colored by values without ``z``, such as heatmapf, issue the
    # same message.
    assert "`z`" not in colorbar_warning_message(func)


# PostDrawContext: the state of the processing after drawing, one per
# ternary diagram.

TRIANGLE_X = [0.0, 1.0, 0.5]
TRIANGLE_Y = [0.0, 0.0, 1.0]
TRIANGLE_Z = [0.0, 1.0, 2.0]


def _add_colorbar(ax, plot="scatter"):
    """Add a colorbar of a plot colored by values, as the plotters do."""
    if plot == "scatter":
        mappable = ax.scatter(TRIANGLE_X, TRIANGLE_Y, c=TRIANGLE_Z)
    else:
        mappable = ax.tricontourf(TRIANGLE_X, TRIANGLE_Y, TRIANGLE_Z)
    return ax.figure.colorbar(mappable, ax=ax)


def test_post_draw_context_tight_layout_defaults_to_none():
    assert PostDrawContext().tight_layout is None


@pytest.mark.parametrize("tight_layout", [None, True, False])
def test_post_draw_context_holds_tight_layout(tight_layout):
    context = PostDrawContext(tight_layout=tight_layout)
    assert context.tight_layout is tight_layout


@pytest.mark.parametrize("new_value", [None, True, False])
def test_post_draw_context_tight_layout_is_read_only(new_value):
    context = PostDrawContext(tight_layout=True)
    with pytest.raises(AttributeError):
        context.tight_layout = new_value
    with pytest.raises(AttributeError):
        del context.tight_layout
    assert context.tight_layout is True


@pytest.mark.parametrize("name", ["_colorbars", "_warned"])
def test_post_draw_context_state_is_not_a_constructor_argument(name):
    with pytest.raises(TypeError):
        PostDrawContext(**{name: []})


def test_post_draw_context_repr_shows_only_tight_layout():
    _, ax = plt.subplots()
    context = PostDrawContext(tight_layout=False)
    context.register_colorbar(_add_colorbar(ax))
    context.first_time(LAYOUT_WARNING_KEY)
    assert repr(context) == "PostDrawContext(tight_layout=False)"


def test_post_draw_context_has_no_colorbar_at_first():
    assert PostDrawContext().has_colorbar() is False


@pytest.mark.parametrize("plot", ["scatter", "tricontourf"])
def test_post_draw_context_has_registered_colorbar(plot):
    _, ax = plt.subplots()
    context = PostDrawContext()
    context.register_colorbar(_add_colorbar(ax, plot))
    assert context.has_colorbar() is True


@pytest.mark.parametrize("plot", ["scatter", "tricontourf"])
def test_post_draw_context_does_not_count_removed_colorbar(plot):
    _, ax = plt.subplots()
    context = PostDrawContext()
    colorbar = _add_colorbar(ax, plot)
    context.register_colorbar(colorbar)
    colorbar.remove()
    # Colorbar.remove() makes the mappable stop pointing to the colorbar.
    assert colorbar.mappable.colorbar is None
    assert context.has_colorbar() is False


@pytest.mark.parametrize("remove_first", [0, 1], ids=["first", "last"])
def test_post_draw_context_counts_colorbars_until_all_are_removed(
    remove_first,
):
    _, ax = plt.subplots()
    context = PostDrawContext()
    colorbars = [
        _add_colorbar(ax, "tricontourf"),
        _add_colorbar(ax, "scatter"),
    ]
    for colorbar in colorbars:
        context.register_colorbar(colorbar)
    colorbars.pop(remove_first).remove()
    assert context.has_colorbar() is True
    colorbars.pop().remove()
    assert context.has_colorbar() is False


def test_post_draw_contexts_compare_by_identity():
    first, second = PostDrawContext(), PostDrawContext()
    assert first != second
    assert first == first
    assert len({first, second}) == 2


def test_post_draw_context_does_not_count_unregistered_colorbar():
    # A colorbar added with matplotlib directly is not counted.
    fig, ax = plt.subplots()
    context = PostDrawContext()
    colorbar = _add_colorbar(ax)
    assert colorbar.mappable.colorbar is colorbar
    assert len(fig.axes) == 2
    assert context.has_colorbar() is False


def test_post_draw_context_first_time_only_once_per_key():
    context = PostDrawContext()
    assert context.first_time(LAYOUT_WARNING_KEY) is True
    assert context.first_time(LAYOUT_WARNING_KEY) is False
    assert context.first_time(LAYOUT_WARNING_KEY) is False
    # Each reason is counted on its own, including keys of later specs.
    assert context.first_time(COLORBAR_WARNING_KEY) is True
    assert context.first_time(COLORBAR_WARNING_KEY) is False
    assert context.first_time("feature.topic") is True
    assert context.first_time(LAYOUT_WARNING_KEY) is False


def test_post_draw_contexts_are_independent():
    # Two ternary diagrams on one figure keep their own state.
    _, (ax1, _) = plt.subplots(1, 2)
    context1 = PostDrawContext()
    context2 = PostDrawContext()
    context1.register_colorbar(_add_colorbar(ax1))
    assert context1.first_time(COLORBAR_WARNING_KEY) is True
    assert context1.has_colorbar() is True
    assert context2.has_colorbar() is False
    assert context2.first_time(COLORBAR_WARNING_KEY) is True


@pytest.mark.parametrize(
    "obj",
    [
        PostDrawContext,
        PostDrawContext.register_colorbar,
        PostDrawContext.has_colorbar,
        PostDrawContext.first_time,
    ],
    ids=lambda obj: obj.__qualname__,
)
def test_post_draw_context_annotations_are_not_evaluated(obj):
    # ``bool | None`` would fail on Python 3.9 if it were evaluated.
    annotations = obj.__annotations__
    assert annotations
    assert all(isinstance(value, str) for value in annotations.values())
