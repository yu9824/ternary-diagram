"""Tests of the skeleton through the public API of ``TernaryDiagram``.

The skeleton is drawn at construction and changed afterwards with one
``set_*`` method per part; the artists of each part are read with its
read-only accessor.
"""

from __future__ import annotations

import inspect
from typing import Any, NamedTuple

import matplotlib.artist
import matplotlib.lines
import matplotlib.text
import pytest

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
