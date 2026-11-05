"""Tests of the skeleton through the public API of ``TernaryDiagram``.

The skeleton is drawn at construction and changed afterwards with one
``set_*`` method per part; the artists of each part are read with its
read-only accessor.
"""

from __future__ import annotations

import inspect
from collections import Counter
from typing import Any, NamedTuple

import matplotlib.artist
import matplotlib.collections
import matplotlib.lines
import matplotlib.pyplot as plt
import matplotlib.text
import pytest
from _skeleton_expected import (
    LINE_ZORDER,
    TEXT_ZORDER,
    LineKey,
    TextKey,
    box_aspect,
    expected_view_limits,
    line_key,
    text_key,
)
from matplotlib.colors import to_rgba

from ternary_diagram import TernaryDiagram

MATERIALS = ("Li2O", "La2O3", "TiO2")
AXIS_LABELS = ("Li2O / mol%", "La2O3 / mol%", "TiO2 / mol%")


class Part(NamedTuple):
    """A part of the skeleton as seen from ``TernaryDiagram``."""

    method: str
    accessor: str
    artist_class: type[matplotlib.artist.Artist]
    # name of the list of the Axes that holds the artists
    container: str
    # the named item that can be given positionally, then the keyword-only
    # named items
    positional: str
    keyword_only: tuple[str, ...]
    # number of artists drawn by the ``titled_td`` fixture
    initial_count: int
    # named items and properties given to `method` for a redraw, and the
    # number of artists that it draws
    change: dict[str, Any]
    changed_count: int

    @property
    def named_items(self) -> tuple[str, ...]:
        return (self.positional, *self.keyword_only)


PARTS = (
    Part(
        method="set_border",
        accessor="border_lines_",
        artist_class=matplotlib.lines.Line2D,
        container="lines",
        positional="visible",
        keyword_only=(),
        initial_count=3,
        change={"visible": True, "linestyle": "--", "linewidth": 1},
        changed_count=3,
    ),
    Part(
        method="set_grid",
        accessor="grid_lines_",
        artist_class=matplotlib.lines.Line2D,
        container="lines",
        positional="visible",
        keyword_only=("step",),
        initial_count=27,
        change={"visible": True, "step": 0.05, "color": "red"},
        changed_count=57,
    ),
    Part(
        method="set_ticks",
        accessor="tick_labels_",
        artist_class=matplotlib.text.Text,
        container="texts",
        positional="visible",
        keyword_only=("step", "fmt", "endpoints"),
        initial_count=27,
        change={
            "visible": True,
            "step": 0.05,
            "fmt": "fraction",
            "endpoints": True,
            "fontsize": 8,
        },
        # 21 values from 0 to 1 on each of the 3 edges
        changed_count=63,
    ),
    Part(
        method="set_axis_labels",
        accessor="axis_labels_",
        artist_class=matplotlib.text.Text,
        container="texts",
        positional="labels",
        keyword_only=("visible", "pad"),
        initial_count=3,
        change={
            "labels": ("A / at%", None, "C / at%"),
            "visible": True,
            "pad": 0.2,
            "fontsize": 14,
        },
        changed_count=2,
    ),
    Part(
        method="set_vertex_labels",
        accessor="vertex_labels_",
        artist_class=matplotlib.text.Text,
        container="texts",
        positional="labels",
        keyword_only=("visible", "offsets"),
        initial_count=3,
        change={
            "labels": ("A", "B", "C"),
            "visible": True,
            "offsets": ((0.0, 0.03), (0.0, -0.06), (0.0, -0.06)),
            "fontsize": 20,
        },
        changed_count=3,
    ),
)
PART_PARAMS = [pytest.param(part, id=part.accessor) for part in PARTS]


@pytest.fixture
def titled_td(ax) -> TernaryDiagram:
    """A diagram whose 5 parts all draw artists."""
    return TernaryDiagram(
        MATERIALS,
        ax=ax,
        tight_layout=True,
        axis_label_kw={"labels": AXIS_LABELS},
    )


def _container(td: TernaryDiagram, part: Part) -> list:
    return list(getattr(td.ax, part.container))


def _contains(artists: list, artist: matplotlib.artist.Artist) -> bool:
    return any(item is artist for item in artists)


def _same_artists(left: list, right: list) -> bool:
    return len(left) == len(right) and all(a is b for a, b in zip(left, right))


def _state(artist: matplotlib.artist.Artist) -> tuple:
    """Values that a redraw with the same settings reproduces."""
    if isinstance(artist, matplotlib.lines.Line2D):
        return (
            tuple(artist.get_xdata()),
            tuple(artist.get_ydata()),
            artist.get_color(),
            artist.get_linestyle(),
            artist.get_linewidth(),
            artist.get_zorder(),
        )
    assert isinstance(artist, matplotlib.text.Text)
    return (
        artist.get_text(),
        tuple(artist.get_position()),
        artist.get_rotation(),
        artist.get_horizontalalignment(),
        artist.get_verticalalignment(),
        artist.get_fontsize(),
        artist.get_zorder(),
    )


# --- accessors --------------------------------------------------------------


@pytest.mark.parametrize(
    ("accessor", "count"),
    [
        ("border_lines_", 3),
        ("grid_lines_", 27),
        ("tick_labels_", 27),
        ("axis_labels_", 0),
        ("vertex_labels_", 3),
    ],
)
def test_accessors_of_the_default_skeleton(td, accessor, count):
    artists = getattr(td, accessor)

    assert isinstance(artists, list)
    assert len(artists) == count


@pytest.mark.parametrize("part", PART_PARAMS)
def test_accessor_returns_the_artists_of_the_part_on_the_axes(titled_td, part):
    artists = getattr(titled_td, part.accessor)

    assert isinstance(artists, list)
    assert len(artists) == part.initial_count
    assert all(isinstance(artist, part.artist_class) for artist in artists)
    container = _container(titled_td, part)
    assert all(_contains(container, artist) for artist in artists)


def test_accessors_split_the_skeleton_by_part(titled_td):
    # Each artist of the skeleton belongs to exactly one part.
    for container in ("lines", "texts"):
        parts = [part for part in PARTS if part.container == container]
        artists = [
            artist
            for part in parts
            for artist in getattr(titled_td, part.accessor)
        ]
        on_axes = list(getattr(titled_td.ax, container))
        assert len(artists) == len(on_axes)
        assert {id(artist) for artist in artists} == {
            id(artist) for artist in on_axes
        }


@pytest.mark.parametrize("part", PART_PARAMS)
def test_accessor_returns_a_new_list(titled_td, part):
    artists = getattr(titled_td, part.accessor)
    again = getattr(titled_td, part.accessor)

    assert artists is not again
    assert _same_artists(artists, again)
    artists.clear()
    assert len(getattr(titled_td, part.accessor)) == part.initial_count


@pytest.mark.parametrize("part", PART_PARAMS)
def test_accessor_is_read_only(titled_td, part):
    artists = getattr(titled_td, part.accessor)

    with pytest.raises(AttributeError, match=f"{part.accessor} is read-only"):
        setattr(titled_td, part.accessor, [])

    assert _same_artists(getattr(titled_td, part.accessor), artists)


# --- change methods ---------------------------------------------------------


@pytest.mark.parametrize("part", PART_PARAMS)
def test_change_method_has_the_named_items_then_properties(part):
    signature = inspect.signature(getattr(TernaryDiagram, part.method))
    params = list(signature.parameters.values())

    assert [param.name for param in params] == [
        "self",
        *part.named_items,
        "kwargs",
    ]
    assert params[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert all(
        param.kind is inspect.Parameter.KEYWORD_ONLY for param in params[2:-1]
    )
    assert params[-1].kind is inspect.Parameter.VAR_KEYWORD
    assert all(param.default is None for param in params[1:-1])


@pytest.mark.parametrize("part", PART_PARAMS)
def test_change_returns_the_new_artists_of_the_accessor(titled_td, part):
    returned = getattr(titled_td, part.method)(**part.change)

    assert isinstance(returned, list)
    assert len(returned) == part.changed_count
    assert all(isinstance(artist, part.artist_class) for artist in returned)
    accessor = getattr(titled_td, part.accessor)
    assert accessor is not returned
    assert _same_artists(returned, accessor)
    container = _container(titled_td, part)
    assert all(_contains(container, artist) for artist in returned)


@pytest.mark.parametrize("part", PART_PARAMS)
def test_change_removes_the_previous_artists(titled_td, part):
    previous = getattr(titled_td, part.accessor)
    n_on_axes = len(_container(titled_td, part))
    assert len(previous) == part.initial_count

    returned = getattr(titled_td, part.method)(**part.change)

    accessor = getattr(titled_td, part.accessor)
    container = _container(titled_td, part)
    assert not any(_contains(returned, artist) for artist in previous)
    assert not any(_contains(accessor, artist) for artist in previous)
    assert not any(_contains(container, artist) for artist in previous)
    assert len(container) == (
        n_on_axes - part.initial_count + part.changed_count
    )


@pytest.mark.parametrize("part", PART_PARAMS)
def test_change_with_the_positional_named_item(titled_td, ax, part):
    # ``visible=False`` for the parts whose first named item is ``visible``
    value = part.change["labels"] if part.positional == "labels" else False
    keyword_td = TernaryDiagram(
        MATERIALS,
        ax=ax.figure.add_subplot(2, 1, 2),
        tight_layout=True,
        axis_label_kw={"labels": AXIS_LABELS},
    )
    initial = [_state(artist) for artist in getattr(titled_td, part.accessor)]
    n_on_axes = len(_container(titled_td, part))

    returned = getattr(titled_td, part.method)(value)
    expected = getattr(keyword_td, part.method)(**{part.positional: value})

    assert len(initial) == part.initial_count
    assert len(_container(titled_td, part)) == (
        n_on_axes - part.initial_count + len(returned)
    )
    assert [_state(artist) for artist in returned] != initial
    assert [_state(artist) for artist in returned] == [
        _state(artist) for artist in expected
    ]
    assert _same_artists(returned, getattr(titled_td, part.accessor))


@pytest.mark.parametrize("part", PART_PARAMS)
def test_change_with_named_items_none_keeps_the_previous_settings(
    titled_td, part
):
    previous = getattr(titled_td, part.method)(**part.change)
    states = [_state(artist) for artist in previous]
    assert len(previous) == part.changed_count

    returned = getattr(titled_td, part.method)(
        **dict.fromkeys(part.named_items)
    )

    # redrawn with new artists from the same settings
    assert not any(_contains(returned, artist) for artist in previous)
    assert [_state(artist) for artist in returned] == states
    assert _same_artists(returned, getattr(titled_td, part.accessor))


@pytest.mark.parametrize("part", PART_PARAMS)
def test_change_returns_an_empty_list_when_hidden(titled_td, part):
    assert len(getattr(titled_td, part.accessor)) == part.initial_count

    returned = getattr(titled_td, part.method)(visible=False)

    assert returned == []
    assert getattr(titled_td, part.accessor) == []


@pytest.mark.parametrize(
    "part",
    [
        pytest.param(part, id=part.accessor)
        for part in PARTS
        if part.artist_class is matplotlib.text.Text
    ],
)
def test_change_passes_a_property_called_name(titled_td, part):
    # ``name`` is an alias of ``fontname`` of ``Text``.
    returned = getattr(titled_td, part.method)(name="DejaVu Sans")

    assert len(returned) == part.initial_count
    assert all(
        artist.get_fontfamily() == ["DejaVu Sans"] for artist in returned
    )


# --- changes of the parts through the public API ----------------------------
#
# The settings at construction (`*_kw`) and the change methods (`set_*`)
# correspond as in the table "`*_kw` と `set_*` の対応" of the design. The
# artists are compared through the keys of `_skeleton_expected`: the text,
# position, rotation, alignments, color, font size and zorder of a label,
# and the segment, color, line width, line style and zorder of a line.

# The argument at construction of each change method.
KW_NAME_OF_METHOD = {
    "set_border": "border_kw",
    "set_grid": "grid_kw",
    "set_ticks": "tick_kw",
    "set_axis_labels": "axis_label_kw",
    "set_vertex_labels": "vertex_label_kw",
}
PART_OF_KW_NAME = {KW_NAME_OF_METHOD[part.method]: part for part in PARTS}
PART_OF_METHOD = {part.method: part for part in PARTS}

# The settings of the `titled_td` fixture.
TITLED_KW = {"axis_label_kw": {"labels": AXIS_LABELS}}
OFFSETS = ((0.0, 0.1), (-0.1, 0.0), (0.1, 0.0))
RED = to_rgba("red")
# Points inside the triangle, as (top, bottom left, bottom right).
POINTS = [[0.2, 0.3, 0.5], [0.6, 0.2, 0.2], [0.1, 0.8, 0.1]]


def _key(artist: matplotlib.artist.Artist) -> LineKey | TextKey:
    if isinstance(artist, matplotlib.lines.Line2D):
        return line_key(artist)
    assert isinstance(artist, matplotlib.text.Text)
    return text_key(artist)


def _keys(artists: list) -> list[LineKey | TextKey]:
    return [_key(artist) for artist in artists]


def _diagram(**part_kw: Any) -> TernaryDiagram:
    """Create a diagram on a new figure with the given ``*_kw``."""
    _, ax = plt.subplots()
    return TernaryDiagram(MATERIALS, ax=ax, tight_layout=True, **part_kw)


def _skeleton_keys(td: TernaryDiagram) -> tuple[list[LineKey], Counter]:
    """Return the keys of all lines and labels of the Axes.

    The lines keep their order on the Axes, which decides the line drawn
    on top among those with the same zorder. The labels of different parts
    do not overlap, so they are compared regardless of their order.
    """
    return (
        [line_key(line) for line in td.ax.lines],
        Counter(text_key(text) for text in td.ax.texts),
    )


def _format_tick(value: float) -> str:
    return f"{value * 100:.0f} %"


class KwCase(NamedTuple):
    """Settings given as ``*_kw`` at construction or to ``set_*`` after."""

    kw_name: str
    settings: dict[str, Any]
    # Settings that draw the part differently from `settings` although they
    # differ only in the checked items, so that a change method that drops
    # those items is detected. The default settings unless given.
    reference: dict[str, Any] | None = None


# Each named item of the table and the matplotlib properties, for each part.
KW_CASES = {
    "border_kw-visible": KwCase("border_kw", {"visible": False}),
    "border_kw-properties": KwCase(
        "border_kw", {"linestyle": "--", "linewidth": 1, "color": "blue"}
    ),
    "border_kw-zorder": KwCase("border_kw", {"zorder": 5}),
    "grid_kw-visible": KwCase("grid_kw", {"visible": False}),
    "grid_kw-step": KwCase("grid_kw", {"step": 0.05}),
    "grid_kw-property-aliases": KwCase(
        "grid_kw", {"ls": ":", "lw": 1, "c": "red"}
    ),
    "grid_kw-zorder": KwCase("grid_kw", {"zorder": 5}),
    "grid_kw-all": KwCase(
        "grid_kw", {"visible": True, "step": 0.25, "color": "red"}
    ),
    "tick_kw-visible": KwCase("tick_kw", {"visible": False}),
    "tick_kw-step": KwCase("tick_kw", {"step": 0.25}),
    "tick_kw-fmt-fraction": KwCase("tick_kw", {"fmt": "fraction"}),
    "tick_kw-fmt-format-string": KwCase("tick_kw", {"fmt": "{:.0%}"}),
    "tick_kw-fmt-callable": KwCase("tick_kw", {"fmt": _format_tick}),
    "tick_kw-endpoints": KwCase("tick_kw", {"endpoints": True}),
    "tick_kw-properties": KwCase(
        "tick_kw", {"fontsize": 8, "color": "red", "rotation": 0}
    ),
    "tick_kw-all": KwCase(
        "tick_kw",
        {
            "visible": True,
            "step": 0.05,
            "fmt": "fraction",
            "endpoints": True,
            "fontsize": 8,
        },
    ),
    "axis_label_kw-labels": KwCase("axis_label_kw", {"labels": AXIS_LABELS}),
    "axis_label_kw-some-labels": KwCase(
        "axis_label_kw", {"labels": ("A", None, "")}
    ),
    "axis_label_kw-visible": KwCase(
        "axis_label_kw",
        {"labels": AXIS_LABELS, "visible": False},
        reference={"labels": AXIS_LABELS},
    ),
    "axis_label_kw-pad": KwCase(
        "axis_label_kw",
        {"labels": AXIS_LABELS, "pad": 0.25},
        reference={"labels": AXIS_LABELS},
    ),
    "axis_label_kw-properties": KwCase(
        "axis_label_kw",
        {"labels": AXIS_LABELS, "fontsize": 14, "color": "red"},
        reference={"labels": AXIS_LABELS},
    ),
    "axis_label_kw-all": KwCase(
        "axis_label_kw",
        {
            "labels": ("A / at%", None, "C / at%"),
            "visible": True,
            "pad": 0.2,
            "fontsize": 14,
        },
    ),
    # `labels` of the vertex labels are given by `materials` at
    # construction, so `vertex_label_kw` cannot contain them.
    "vertex_label_kw-visible": KwCase("vertex_label_kw", {"visible": False}),
    "vertex_label_kw-offsets": KwCase("vertex_label_kw", {"offsets": OFFSETS}),
    "vertex_label_kw-properties": KwCase(
        "vertex_label_kw", {"fontsize": 20, "color": "red"}
    ),
    "vertex_label_kw-all": KwCase(
        "vertex_label_kw",
        {"visible": True, "offsets": OFFSETS, "fontsize": 20},
    ),
}


@pytest.mark.parametrize(
    "case", [pytest.param(case, id=name) for name, case in KW_CASES.items()]
)
def test_part_kw_and_change_method_draw_the_same_artists(case):
    part = PART_OF_KW_NAME[case.kw_name]
    created = _diagram(**{case.kw_name: case.settings})
    changed = _diagram()
    reference = _diagram(**{case.kw_name: case.reference or {}})

    returned = getattr(changed, part.method)(**case.settings)

    expected = _keys(getattr(created, part.accessor))
    assert expected != _keys(getattr(reference, part.accessor))
    assert _keys(returned) == expected
    assert _keys(getattr(changed, part.accessor)) == expected
    # The other parts and the stacking of the lines are the same as well.
    assert _skeleton_keys(changed) == _skeleton_keys(created)


def test_changing_only_the_color_keeps_the_step_of_the_grid(td):
    td.set_grid(step=0.05)

    returned = td.set_grid(color="red")

    assert len(returned) == 57
    assert all(to_rgba(line.get_color()) == RED for line in returned)
    # The line width is still the default.
    assert all(line.get_linewidth() == 0.5 for line in returned)
    expected = _diagram(grid_kw={"step": 0.05, "color": "red"})
    assert _keys(returned) == _keys(expected.grid_lines_)


# A first change, then a second change that gives only some of the items.
INHERITANCE_CASES = {
    "border-property-then-property": (
        "set_border",
        {"linestyle": "--"},
        {"linewidth": 1},
    ),
    "grid-step-then-color": ("set_grid", {"step": 0.05}, {"color": "red"}),
    "grid-properties-then-step": (
        "set_grid",
        {"color": "red", "linewidth": 1},
        {"step": 0.05},
    ),
    "ticks-named-items-then-fontsize": (
        "set_ticks",
        {"step": 0.25, "fmt": "fraction", "endpoints": True},
        {"fontsize": 8},
    ),
    "ticks-fontsize-and-step-then-fmt": (
        "set_ticks",
        {"fontsize": 8, "step": 0.25},
        {"fmt": "{:.0%}"},
    ),
    "axis-labels-pad-then-fontsize": (
        "set_axis_labels",
        {"labels": AXIS_LABELS, "pad": 0.25},
        {"fontsize": 14},
    ),
    "axis-labels-fontsize-then-labels": (
        "set_axis_labels",
        {"labels": AXIS_LABELS, "fontsize": 14},
        {"labels": ("A", None, "C")},
    ),
    "vertex-labels-offsets-then-fontsize": (
        "set_vertex_labels",
        {"offsets": OFFSETS},
        {"fontsize": 20},
    ),
    "vertex-labels-fontsize-and-offsets-then-labels": (
        "set_vertex_labels",
        {"fontsize": 20, "offsets": OFFSETS},
        {"labels": ("A", "B", "C")},
    ),
}


@pytest.mark.parametrize(
    ("method", "first", "second"),
    [pytest.param(*case, id=name) for name, case in INHERITANCE_CASES.items()],
)
def test_change_keeps_the_previous_settings_not_given(
    td, method, first, second
):
    getattr(td, method)(**first)

    returned = getattr(td, method)(**second)

    merged = getattr(_diagram(), method)(**{**first, **second})
    only_second = getattr(_diagram(), method)(**second)
    # The first change matters, so that the case checks the inheritance.
    assert _keys(merged) != _keys(only_second)
    assert _keys(returned) == _keys(merged)
    assert _same_artists(
        returned, getattr(td, PART_OF_METHOD[method].accessor)
    )


@pytest.mark.parametrize("part", PART_PARAMS)
def test_showing_a_hidden_part_draws_it_with_the_settings_before_hiding(
    titled_td, part
):
    change = getattr(titled_td, part.method)
    before = change(**part.change)
    keys = _keys(before)
    assert len(before) == part.changed_count

    assert change(visible=False) == []
    shown = change(visible=True)

    assert _keys(shown) == keys
    # drawn again with new artists
    assert not any(_contains(shown, artist) for artist in before)
    assert _same_artists(shown, getattr(titled_td, part.accessor))
    container = _container(titled_td, part)
    assert all(_contains(container, artist) for artist in shown)
    assert not any(_contains(container, artist) for artist in before)


@pytest.mark.parametrize("part", PART_PARAMS)
def test_settings_changed_while_hidden_are_used_when_shown(titled_td, part):
    settings = {k: v for k, v in part.change.items() if k != "visible"}
    change = getattr(titled_td, part.method)
    change(visible=False)

    # `visible` not given keeps the part hidden.
    assert change(**settings) == []
    assert getattr(titled_td, part.accessor) == []
    shown = change(visible=True)

    expected = getattr(_diagram(**TITLED_KW), part.method)(**settings)
    assert len(shown) == part.changed_count
    assert _keys(shown) == _keys(expected)


# Settings of each part other than `visible`, given while it is hidden.
HIDDEN_PART_SETTINGS = {
    "border_kw": {"linestyle": "--", "linewidth": 1},
    "grid_kw": {"step": 0.05, "color": "red"},
    "tick_kw": {"fmt": "fraction", "endpoints": True, "fontsize": 8},
    "axis_label_kw": {"labels": AXIS_LABELS, "pad": 0.25},
    "vertex_label_kw": {"offsets": OFFSETS, "fontsize": 20},
}


@pytest.mark.parametrize(
    ("kw_name", "settings"),
    [
        pytest.param(kw_name, settings, id=kw_name)
        for kw_name, settings in HIDDEN_PART_SETTINGS.items()
    ],
)
def test_part_hidden_at_construction_is_shown_with_its_initial_settings(
    kw_name, settings
):
    part = PART_OF_KW_NAME[kw_name]
    td = _diagram(**{kw_name: {**settings, "visible": False}})
    assert getattr(td, part.accessor) == []

    shown = getattr(td, part.method)(visible=True)

    expected = _diagram(**{kw_name: settings})
    assert len(shown) > 0
    assert _keys(shown) == _keys(getattr(expected, part.accessor))
    assert _skeleton_keys(td) == _skeleton_keys(expected)


# A change of matplotlib properties, and the fields of `LineKey` or
# `TextKey` that it changes on every artist of the part.
PROPERTY_CASES = {
    "border-linestyle-and-linewidth": (
        "set_border",
        {"linestyle": "--", "linewidth": 1},
        {"linestyle": "--", "linewidth": 1.0},
    ),
    "border-color": ("set_border", {"color": "red"}, {"color": RED}),
    "grid-property-aliases": (
        "set_grid",
        {"ls": ":", "lw": 1.5, "c": "red"},
        {"linestyle": ":", "linewidth": 1.5, "color": RED},
    ),
    "ticks-fontsize": ("set_ticks", {"fontsize": 8}, {"fontsize": 8.0}),
    # over the rotation and alignments that differ from edge to edge
    "ticks-over-the-edge-defaults": (
        "set_ticks",
        {"rotation": 0, "ha": "center", "va": "baseline"},
        {
            "rotation": 0.0,
            "horizontalalignment": "center",
            "verticalalignment": "baseline",
        },
    ),
    "axis-labels-fontsize": (
        "set_axis_labels",
        {"fontsize": 14},
        {"fontsize": 14.0},
    ),
    # over the rotation that differs from edge to edge
    "axis-labels-over-the-edge-defaults": (
        "set_axis_labels",
        {"rotation": 0, "color": "red"},
        {"rotation": 0.0, "color": RED},
    ),
    "vertex-labels-fontsize": (
        "set_vertex_labels",
        {"fontsize": 20},
        {"fontsize": 20.0},
    ),
    # over the alignments that differ from vertex to vertex
    "vertex-labels-over-the-vertex-defaults": (
        "set_vertex_labels",
        {"ha": "center", "va": "center", "color": "red"},
        {
            "horizontalalignment": "center",
            "verticalalignment": "center",
            "color": RED,
        },
    ),
}


@pytest.mark.parametrize(
    ("method", "properties", "fields"),
    [pytest.param(*case, id=name) for name, case in PROPERTY_CASES.items()],
)
def test_properties_apply_to_all_artists_of_the_part(
    titled_td, method, properties, fields
):
    part = PART_OF_METHOD[method]
    default = _keys(getattr(titled_td, part.accessor))

    returned = getattr(titled_td, method)(**properties)

    assert len(returned) == part.initial_count
    # Every artist takes the properties and keeps everything else.
    expected = [key._replace(**fields) for key in default]
    assert expected != default
    assert _keys(returned) == expected


@pytest.mark.parametrize("hidden", [False, True], ids=["changed", "hidden"])
@pytest.mark.parametrize("part", PART_PARAMS)
def test_change_leaves_the_other_parts(titled_td, part, hidden):
    others = [other for other in PARTS if other is not part]
    before = {
        other.accessor: getattr(titled_td, other.accessor) for other in others
    }
    keys = {accessor: _keys(artists) for accessor, artists in before.items()}

    getattr(titled_td, part.method)(
        **({"visible": False} if hidden else part.change)
    )

    for other in others:
        after = getattr(titled_td, other.accessor)
        assert _same_artists(after, before[other.accessor])
        assert _keys(after) == keys[other.accessor]
        container = _container(titled_td, other)
        assert all(_contains(container, artist) for artist in after)


def _user_artists(td: TernaryDiagram) -> list:
    """Return the collections, lines and labels not drawn by the parts."""
    skeleton = [
        artist for part in PARTS for artist in getattr(td, part.accessor)
    ]
    return [
        artist
        for artist in (*td.ax.collections, *td.ax.lines, *td.ax.texts)
        if not _contains(skeleton, artist)
    ]


def _user_state(artist: matplotlib.artist.Artist) -> tuple:
    if isinstance(artist, matplotlib.collections.PathCollection):
        return (
            artist.get_offsets().tolist(),
            artist.get_facecolor().tolist(),
            artist.get_edgecolor().tolist(),
            artist.get_sizes().tolist(),
            artist.get_zorder(),
            artist.get_visible(),
        )
    if isinstance(artist, matplotlib.text.Annotation):
        return (text_key(artist), tuple(artist.xy), artist.get_visible())
    return (_state(artist), artist.get_visible())


@pytest.mark.parametrize("hidden", [False, True], ids=["changed", "hidden"])
def test_changes_of_all_parts_leave_the_artists_drawn_by_the_user(td, hidden):
    collection = td.scatter(POINTS, annotations=["a", "b", "c"])
    (line,) = td.ax.plot(
        [0.2, 0.8], [0.1, 0.5], color="purple", linewidth=3, linestyle="-."
    )
    user = _user_artists(td)
    # the points, their 3 annotations and the line
    assert len(user) == 5
    assert _contains(user, collection)
    assert _contains(user, line)
    assert sum(isinstance(a, matplotlib.text.Annotation) for a in user) == 3
    states = [_user_state(artist) for artist in user]

    for part in PARTS:
        getattr(td, part.method)(
            **({"visible": False} if hidden else part.change)
        )

    assert _same_artists(_user_artists(td), user)
    assert all(artist.axes is td.ax for artist in user)
    assert [_user_state(artist) for artist in user] == states


@pytest.mark.parametrize("part", PART_PARAMS)
def test_hiding_a_part_removes_its_artists_from_the_axes(titled_td, part):
    previous = getattr(titled_td, part.accessor)
    others = [
        artist
        for artist in _container(titled_td, part)
        if not _contains(previous, artist)
    ]
    assert len(previous) == part.initial_count

    returned = getattr(titled_td, part.method)(visible=False)

    assert returned == []
    assert getattr(titled_td, part.accessor) == []
    container = _container(titled_td, part)
    assert not any(_contains(container, artist) for artist in previous)
    # Only the artists of the part are removed.
    assert _same_artists(container, others)


@pytest.mark.parametrize("part", PART_PARAMS)
def test_part_hidden_at_construction_draws_nothing(part):
    kw_name = KW_NAME_OF_METHOD[part.method]
    shown = _diagram(**TITLED_KW)
    hidden = _diagram(
        **{
            **TITLED_KW,
            kw_name: {**TITLED_KW.get(kw_name, {}), "visible": False},
        }
    )

    assert getattr(hidden, part.accessor) == []
    part_artists = getattr(shown, part.accessor)
    assert len(part_artists) == part.initial_count
    for container in ("lines", "texts"):
        expected = [
            artist
            for artist in getattr(shown.ax, container)
            if not _contains(part_artists, artist)
        ]
        assert _keys(list(getattr(hidden.ax, container))) == _keys(expected)


# --- stacking order ---------------------------------------------------------
#
# The border and grid lines keep the zorder 1 of ternary-diagram v3, above
# the contour (0) and below the lines and points plotted by the user (2 and
# 3); the labels keep matplotlib's default zorder 3 of ``Text``.


def _default_zorder(part: Part) -> float:
    if part.artist_class is matplotlib.lines.Line2D:
        return LINE_ZORDER
    return TEXT_ZORDER


def _zorders(artists: list) -> list[float]:
    return [artist.get_zorder() for artist in artists]


@pytest.mark.parametrize("part", PART_PARAMS)
def test_redrawn_part_keeps_the_default_zorder(titled_td, part):
    change = getattr(titled_td, part.method)
    zorder = _default_zorder(part)
    initial = _zorders(getattr(titled_td, part.accessor))
    assert initial == [zorder] * part.initial_count

    changed = change(**part.change)
    change(visible=False)
    shown = change(visible=True)

    assert _zorders(changed) == [zorder] * part.changed_count
    assert _zorders(shown) == [zorder] * part.changed_count
    assert _zorders(getattr(titled_td, part.accessor)) == _zorders(shown)


@pytest.mark.parametrize("given", ["created", "changed"])
@pytest.mark.parametrize("zorder", [5, 0.5])
@pytest.mark.parametrize("part", PART_PARAMS)
def test_user_zorder_wins_and_is_kept_on_redraws(part, zorder, given):
    kw_name = KW_NAME_OF_METHOD[part.method]
    if given == "created":
        td = _diagram(
            **{
                **TITLED_KW,
                kw_name: {**TITLED_KW.get(kw_name, {}), "zorder": zorder},
            }
        )
    else:
        td = _diagram(**TITLED_KW)
        returned = getattr(td, part.method)(zorder=zorder)
        assert _zorders(returned) == [zorder] * part.initial_count
    change = getattr(td, part.method)
    assert _zorders(getattr(td, part.accessor)) == [zorder] * (
        part.initial_count
    )

    # Redraws that do not give `zorder` keep the one given by the user.
    changed = change(**part.change)
    change(visible=False)
    shown = change(visible=True)

    assert _zorders(changed) == [zorder] * part.changed_count
    assert _zorders(shown) == [zorder] * part.changed_count
    # The other parts keep their default zorder.
    for other in PARTS:
        if other is not part:
            artists = getattr(td, other.accessor)
            assert len(artists) == other.initial_count
            assert _zorders(artists) == [_default_zorder(other)] * len(artists)


# Changes of the border and the grid in different orders. The border must
# end up after the grid in ``ax.lines``, so that it is drawn over the grid
# lines that have the same zorder.
BORDER_GRID_SEQUENCES = {
    "grid": [("set_grid", {"step": 0.05})],
    "border-then-grid": [
        ("set_border", {"linewidth": 1}),
        ("set_grid", {"step": 0.05}),
    ],
    "grid-then-border": [
        ("set_grid", {"step": 0.05}),
        ("set_border", {"linewidth": 1}),
    ],
    "grid-hidden-border-changed-grid-shown": [
        ("set_grid", {"visible": False}),
        ("set_border", {"linewidth": 1}),
        ("set_grid", {"visible": True}),
    ],
    "border-hidden-grid-changed-border-shown": [
        ("set_border", {"visible": False}),
        ("set_grid", {"step": 0.05}),
        ("set_border", {"visible": True}),
    ],
    "all-parts": [(part.method, part.change) for part in PARTS],
    "all-parts-reversed": [
        (part.method, part.change) for part in reversed(PARTS)
    ],
}


@pytest.mark.parametrize(
    "sequence",
    [
        pytest.param(sequence, id=name)
        for name, sequence in BORDER_GRID_SEQUENCES.items()
    ],
)
def test_border_is_drawn_over_the_grid_in_any_order_of_changes(td, sequence):
    for method, kwargs in sequence:
        getattr(td, method)(**kwargs)

    lines = list(td.ax.lines)
    border = td.border_lines_
    grid = td.grid_lines_
    assert len(border) == 3
    assert len(grid) > 0
    assert len(lines) == len(border) + len(grid)
    assert set(_zorders(lines)) == {LINE_ZORDER}
    assert _same_artists(lines[-len(border) :], border)


# --- view limits ------------------------------------------------------------

HIDDEN_LINE_PARTS = {
    "border": ("set_border",),
    "grid": ("set_grid",),
    "border-and-grid": ("set_border", "set_grid"),
}


@pytest.mark.parametrize("when", ["created", "changed"])
@pytest.mark.parametrize(
    "methods",
    [
        pytest.param(methods, id=name)
        for name, methods in HIDDEN_LINE_PARTS.items()
    ],
)
def test_hidden_border_and_grid_keep_the_view_limits(methods, when):
    default = _diagram()
    if when == "created":
        td = _diagram(
            **{
                KW_NAME_OF_METHOD[method]: {"visible": False}
                for method in methods
            }
        )
    else:
        td = _diagram()
        for method in methods:
            assert getattr(td, method)(visible=False) == []
    assert all(getattr(td, PART_OF_METHOD[m].accessor) == [] for m in methods)
    expected_xlim, expected_ylim = expected_view_limits(box_aspect(td.ax))

    default.fig.canvas.draw()
    td.fig.canvas.draw()

    assert td.ax.get_xlim() == pytest.approx(default.ax.get_xlim(), abs=1e-9)
    assert td.ax.get_ylim() == pytest.approx(default.ax.get_ylim(), abs=1e-9)
    assert td.ax.get_xlim() == pytest.approx(expected_xlim, abs=1e-9)
    assert td.ax.get_ylim() == pytest.approx(expected_ylim, abs=1e-9)


# --- layout -----------------------------------------------------------------


def _layout(td: TernaryDiagram) -> tuple:
    """Return the position of the Axes and the layout of its figure."""
    params = td.fig.subplotpars
    return (
        td.ax.get_position().bounds,
        td.ax.get_position(original=True).bounds,
        (
            params.left,
            params.right,
            params.bottom,
            params.top,
            params.wspace,
            params.hspace,
        ),
        td.fig.get_layout_engine(),
    )


@pytest.mark.parametrize("hidden", [False, True], ids=["changed", "hidden"])
@pytest.mark.parametrize(
    "plotted", [False, True], ids=["skeleton-only", "after-scatter"]
)
def test_changes_of_all_parts_keep_the_layout(td, plotted, hidden):
    if plotted:
        # `tight_layout=True` of the fixture adjusts the layout here.
        td.scatter(POINTS)
    before = _layout(td)

    for part in PARTS:
        getattr(td, part.method)(
            **({"visible": False} if hidden else part.change)
        )
        assert _layout(td) == before
    # Showing the hidden parts again does not change it either.
    for part in PARTS:
        getattr(td, part.method)(visible=True)
        assert _layout(td) == before


# --- contour ----------------------------------------------------------------


def _contour_state(contour: Any) -> tuple:
    """Values of a contour set, through API common to matplotlib versions."""
    return (
        contour.filled,
        list(contour.levels),
        contour.get_cmap().name,
        contour.norm.vmin,
        contour.norm.vmax,
    )


def _collection_state(collection: matplotlib.collections.Collection) -> tuple:
    return (
        [path.vertices.tolist() for path in collection.get_paths()],
        collection.get_facecolor().tolist(),
        collection.get_edgecolor().tolist(),
        collection.get_zorder(),
        collection.get_alpha(),
        collection.get_visible(),
    )


@pytest.mark.parametrize("hidden", [False, True], ids=["changed", "hidden"])
@pytest.mark.parametrize("fill", [True, False], ids=["filled", "lines"])
def test_changes_of_all_parts_leave_the_contour(td, df_contour, fill, hidden):
    vector = df_contour.iloc[:, :3].to_numpy()
    z = df_contour.iloc[:, 3].to_numpy()
    contour = td.contour(vector, z=z, fill=fill)
    (tie_line,) = td.plot([[0.2, 0.3, 0.5], [0.6, 0.2, 0.2]])
    points = td.scatter(POINTS)
    # The contour sets of matplotlib >= 3.8 are collections themselves,
    # older ones hold one collection per level.
    collections = list(td.ax.collections)
    assert _contains(collections, points)
    n_axes = len(td.fig.axes)
    state = _contour_state(contour)
    collection_states = [_collection_state(c) for c in collections]
    line_state = _state(tie_line)

    for part in PARTS:
        getattr(td, part.method)(
            **({"visible": False} if hidden else part.change)
        )

    assert _same_artists(list(td.ax.collections), collections)
    assert all(collection.axes is td.ax for collection in collections)
    assert _contour_state(contour) == state
    assert [_collection_state(c) for c in collections] == collection_states
    assert tie_line.axes is td.ax
    assert _state(tie_line) == line_state
    # The colorbar of the contour is kept.
    assert len(td.fig.axes) == n_axes
    # The redrawn lines stay above the contour and below the tie line and
    # the points.
    skeleton_lines = [*td.border_lines_, *td.grid_lines_]
    assert len(skeleton_lines) == (0 if hidden else 3 + 57)
    contour_zorder = max(
        c.get_zorder() for c in collections if c is not points
    )
    for line in skeleton_lines:
        assert contour_zorder < line.get_zorder() < tie_line.get_zorder()
        assert line.get_zorder() < points.get_zorder()


# --- errors and rollback ----------------------------------------------------


def _raise_in_format(value: float) -> str:
    raise RuntimeError("cannot format the tick label")


# An invalid change of a part, the error and a pattern of its message.
FAILED_CHANGES = {
    "grid-step-zero": ("set_grid", {"step": 0}, ValueError, "0 < step <= 1"),
    "ticks-step-over-one": (
        "set_ticks",
        {"step": 1.5},
        ValueError,
        "0 < step <= 1",
    ),
    "ticks-step-nan": (
        "set_ticks",
        {"step": float("nan")},
        ValueError,
        "0 < step <= 1",
    ),
    "ticks-unparsable-fmt": (
        "set_ticks",
        {"fmt": "abc"},
        ValueError,
        "`fmt` must be 'percent', 'fraction'",
    ),
    "ticks-raising-fmt": (
        "set_ticks",
        {"fmt": _raise_in_format},
        RuntimeError,
        "cannot format the tick label",
    ),
    **{
        f"{part.accessor}-unknown-property": (
            part.method,
            {"colour": "red"},
            AttributeError,
            "unexpected keyword argument 'colour'",
        )
        for part in PARTS
    },
    # rejected by matplotlib while creating the artists
    **{
        f"{part.accessor}-invalid-color": (
            part.method,
            {"color": "not-a-color"},
            ValueError,
            "'not-a-color' is not a valid value for color",
        )
        for part in PARTS
    },
}


@pytest.mark.parametrize(
    ("method", "kwargs", "error", "match"),
    [pytest.param(*case, id=name) for name, case in FAILED_CHANGES.items()],
)
def test_failed_change_keeps_the_parts_and_the_axes(
    titled_td, method, kwargs, error, match
):
    part = PART_OF_METHOD[method]
    # Settings other than the defaults, so that keeping them is visible.
    getattr(titled_td, method)(**part.change)
    before = {
        other.accessor: getattr(titled_td, other.accessor) for other in PARTS
    }
    keys = {accessor: _keys(artists) for accessor, artists in before.items()}
    lines = list(titled_td.ax.lines)
    texts = list(titled_td.ax.texts)
    n_children = len(titled_td.ax.get_children())

    with pytest.raises(error, match=match):
        getattr(titled_td, method)(**kwargs)

    for other in PARTS:
        after = getattr(titled_td, other.accessor)
        assert _same_artists(after, before[other.accessor])
        assert _keys(after) == keys[other.accessor]
    assert _same_artists(list(titled_td.ax.lines), lines)
    assert _same_artists(list(titled_td.ax.texts), texts)
    assert len(titled_td.ax.get_children()) == n_children
    # The settings are kept as well: a redraw without settings draws the
    # part as before the failed change.
    redrawn = getattr(titled_td, method)()
    assert len(redrawn) == part.changed_count
    assert _keys(redrawn) == keys[part.accessor]


def test_raising_format_given_while_hidden_fails_when_shown(titled_td):
    titled_td.set_ticks(visible=False)
    # The format is called only when the tick labels are drawn.
    assert titled_td.set_ticks(fmt=_raise_in_format) == []
    texts = list(titled_td.ax.texts)

    with pytest.raises(RuntimeError, match="cannot format the tick label"):
        titled_td.set_ticks(visible=True)

    # still hidden, with nothing added to the Axes
    assert titled_td.tick_labels_ == []
    assert _same_artists(list(titled_td.ax.texts), texts)
    # `visible=True` of the failed change is not kept either.
    assert titled_td.set_ticks() == []
    shown = titled_td.set_ticks(visible=True, fmt="fraction")
    assert len(shown) == 27
    assert "0.1" in [text.get_text() for text in shown]


# An invalid setting at construction. The tick labels and the axis titles
# are drawn after the grid, the border and the vertex labels, so that these
# must be removed again.
FAILED_CONSTRUCTIONS = {
    "tick-step-zero": ("tick_kw", {"step": 0}, ValueError, "0 < step <= 1"),
    "tick-unparsable-fmt": (
        "tick_kw",
        {"fmt": "abc"},
        ValueError,
        "`fmt` must be 'percent', 'fraction'",
    ),
    "tick-raising-fmt": (
        "tick_kw",
        {"fmt": _raise_in_format},
        RuntimeError,
        "cannot format the tick label",
    ),
    "axis-label-unknown-property": (
        "axis_label_kw",
        {"labels": AXIS_LABELS, "colour": "red"},
        AttributeError,
        "unexpected keyword argument 'colour'",
    ),
    "axis-label-invalid-color": (
        "axis_label_kw",
        {"labels": AXIS_LABELS, "color": "not-a-color"},
        ValueError,
        "'not-a-color' is not a valid value for color",
    ),
}


@pytest.mark.parametrize(
    ("kw_name", "settings", "error", "match"),
    [
        pytest.param(*case, id=name)
        for name, case in FAILED_CONSTRUCTIONS.items()
    ],
)
def test_invalid_setting_at_construction_leaves_no_skeleton_artist(
    ax, kw_name, settings, error, match
):
    (user_line,) = ax.plot([0.2, 0.8], [0.1, 0.5])
    user_text = ax.text(0.5, 0.5, "user")

    with pytest.raises(error, match=match):
        TernaryDiagram(
            MATERIALS, ax=ax, tight_layout=True, **{kw_name: settings}
        )

    assert _same_artists(list(ax.lines), [user_line])
    assert _same_artists(list(ax.texts), [user_text])
