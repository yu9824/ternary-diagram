"""Unit tests of the skeleton parts in ``ternary_diagram._skeleton``."""

from __future__ import annotations

import typing
from collections import Counter
from collections.abc import Sequence
from fractions import Fraction
from typing import Any

import matplotlib
import matplotlib.lines
import matplotlib.text
import numpy as np
import pandas as pd
import pytest
from _skeleton_expected import (
    BORDER_COLOR,
    BORDER_LINEWIDTH,
    GRID_COLOR,
    GRID_LINEWIDTH,
    LINE_ZORDER,
    LINESTYLE,
    ROOT3_OVER_2,
    TEXT_ZORDER,
    TICK_LABEL_FONTSIZE,
    VERTEX_LABEL_FONTSIZE,
    expected_border_lines,
    expected_grid_lines,
    expected_tick_label_texts,
    expected_vertex_label_texts,
    line_key,
    point_key,
    text_key,
)
from matplotlib.colors import to_rgba

from ternary_diagram import _skeleton
from ternary_diagram._skeleton import (
    Spec,
    _AxisLabels,
    _Border,
    _Grid,
    _LineSpec,
    _SkeletonPart,
    _TextSpec,
    _TickLabels,
    _VertexLabels,
)
from ternary_diagram.utils import (
    get_axis_label_position,
    get_edge_points,
    get_grid_segments,
    get_label,
    get_tick_formatter,
    get_tick_values,
)

# ---------------------------------------------------------------------------
# _SkeletonPart: minimal parts used only by these tests
# ---------------------------------------------------------------------------


class _LinePart(_SkeletonPart):
    """`n` horizontal lines at y = 0, 1, ..., n - 1.

    The line at index `fail_at` gets a property that matplotlib rejects, so
    that the creation of artists fails after some of them were created.
    """

    OPTION_DEFAULTS = {"visible": True, "n": 2, "fail_at": -1}
    STYLE_DEFAULTS = {"color": "black", "linewidth": 1.0}
    ARTIST_CLASS = matplotlib.lines.Line2D

    def _validate(self, options: dict[str, Any]) -> dict[str, Any]:
        n = options["n"]
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError(f"`n` must be a non-negative int, but got {n!r}.")
        return options

    def _specs(
        self, options: dict[str, Any], style: dict[str, Any]
    ) -> list[Spec]:
        specs: list[Spec] = []
        for i in range(options["n"]):
            kwargs = dict(style)
            if i == options["fail_at"]:
                kwargs["no_such_property"] = 1
            specs.append(_LineSpec([0.0, 1.0], [float(i), float(i)], kwargs))
        return specs


class _TextPart(_SkeletonPart):
    """One text per label at (i, 0.5).

    The text at index `fail_at` gets a property that matplotlib rejects.
    """

    OPTION_DEFAULTS = {"visible": True, "labels": ("a", "b"), "fail_at": -1}
    STYLE_DEFAULTS = {"fontsize": 10, "horizontalalignment": "center"}
    ARTIST_CLASS = matplotlib.text.Text

    def _specs(
        self, options: dict[str, Any], style: dict[str, Any]
    ) -> list[Spec]:
        specs: list[Spec] = []
        for i, label in enumerate(options["labels"]):
            kwargs = dict(style)
            if i == options["fail_at"]:
                kwargs["no_such_property"] = 1
            specs.append(_TextSpec(float(i), 0.5, label, kwargs))
        return specs


def _children(ax, part: _SkeletonPart) -> list:
    """Artists of the Axes that are of the kind the part draws."""
    if part.ARTIST_CLASS is matplotlib.lines.Line2D:
        return list(ax.lines)
    return list(ax.texts)


def _same_objects(actual, expected) -> bool:
    return len(actual) == len(expected) and all(
        a is e for a, e in zip(actual, expected)
    )


@pytest.fixture
def line_part(ax) -> _LinePart:
    return _LinePart(ax, zorder=1)


@pytest.fixture
def text_part(ax) -> _TextPart:
    return _TextPart(ax)


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------


def test_spec_fields():
    assert _LineSpec._fields == ("xdata", "ydata", "kwargs")
    assert _TextSpec._fields == ("x", "y", "s", "kwargs")
    assert typing.get_args(Spec) == (_LineSpec, _TextSpec)


def test_annotations_are_not_evaluated():
    # ``X | None`` and builtin generics would fail on Python 3.9 if the
    # annotations were evaluated at runtime.
    for func in (
        _SkeletonPart.__init__,
        _SkeletonPart.update,
        _SkeletonPart._validate,
        _SkeletonPart._specs,
    ):
        annotations = func.__annotations__
        assert annotations
        assert all(isinstance(value, str) for value in annotations.values())


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_init_draws_line_part_with_defaults(ax, line_part):
    lines = line_part.artists
    assert len(lines) == 2
    assert _same_objects(ax.lines, lines)
    for i, line in enumerate(lines):
        assert list(line.get_xdata()) == [0.0, 1.0]
        assert list(line.get_ydata()) == [float(i), float(i)]
        assert to_rgba(line.get_color()) == to_rgba("black")
        assert line.get_linewidth() == 1.0
        assert line.get_zorder() == 1


def test_init_draws_text_part_with_defaults(ax, text_part):
    texts = text_part.artists
    assert [t.get_text() for t in texts] == ["a", "b"]
    assert _same_objects(ax.texts, texts)
    for i, text in enumerate(texts):
        assert text.get_position() == (float(i), 0.5)
        assert text.get_fontsize() == 10
        assert text.get_horizontalalignment() == "center"
        # Text parts do not set zorder: matplotlib's default stays.
        assert text.get_zorder() == 3


def test_init_without_zorder_keeps_matplotlib_default(ax):
    part = _LinePart(ax)
    assert all(line.get_zorder() == 2 for line in part.artists)


def test_init_calls_update_once_with_initial_settings(ax):
    calls = []

    class _CountingPart(_LinePart):
        def update(self, **kwargs):
            calls.append(kwargs)
            return super().update(**kwargs)

    part = _CountingPart(ax, zorder=1, n=3, color="red")
    assert calls == [{"n": 3, "color": "red"}]
    assert len(part.artists) == 3
    assert all(
        to_rgba(line.get_color()) == to_rgba("red") for line in part.artists
    )


def test_init_invisible_draws_nothing(ax):
    part = _LinePart(ax, zorder=1, visible=False)
    assert part.artists == []
    assert list(ax.lines) == []


def test_init_rejects_non_bool_visible(ax):
    with pytest.raises(TypeError, match="`visible` must be True or False"):
        _LinePart(ax, zorder=1, visible=1)
    assert list(ax.lines) == []


# ---------------------------------------------------------------------------
# update: redrawing and the accessor
# ---------------------------------------------------------------------------


def test_update_replaces_previous_artists(ax, line_part):
    old = line_part.artists
    new = line_part.update(n=3)
    assert len(new) == 3
    assert _same_objects(line_part.artists, new)
    assert _same_objects(ax.lines, new)
    assert all(line not in ax.lines for line in old)
    assert all(line.axes is None for line in old)


def test_artists_and_return_value_are_new_lists(line_part):
    assert line_part.artists is not line_part.artists
    returned = line_part.update()
    current = line_part.artists
    returned.clear()
    current.clear()
    assert len(line_part.artists) == 2


def test_update_does_not_touch_other_artists(ax, line_part):
    (user_line,) = ax.plot([0, 1], [5, 6], color="green", linewidth=7)
    user_text = ax.text(0.2, 0.3, "user", fontsize=20)
    other = _LinePart(ax, zorder=1, n=1, color="blue")
    other_lines = other.artists

    line_part.update(n=4, color="red")
    line_part.update(visible=False)
    line_part.update(visible=True)

    assert user_line in ax.lines
    assert to_rgba(user_line.get_color()) == to_rgba("green")
    assert user_line.get_linewidth() == 7
    assert user_text in ax.texts
    assert user_text.get_fontsize() == 20
    assert _same_objects(other.artists, other_lines)
    assert all(line in ax.lines for line in other_lines)
    assert to_rgba(other_lines[0].get_color()) == to_rgba("blue")


# ---------------------------------------------------------------------------
# update: merging the settings
# ---------------------------------------------------------------------------


def test_update_inherits_unspecified_items(line_part):
    line_part.update(n=3, linewidth=3)
    lines = line_part.update(color="red")
    assert len(lines) == 3
    assert all(line.get_linewidth() == 3 for line in lines)
    assert all(to_rgba(line.get_color()) == to_rgba("red") for line in lines)


def test_update_none_option_keeps_previous_value(line_part):
    line_part.update(n=3)
    assert len(line_part.update(n=None)) == 3
    assert len(line_part.update(n=None, visible=None)) == 3


def test_update_style_overrides_defaults(text_part):
    texts = text_part.update(fontsize=8)
    assert all(text.get_fontsize() == 8 for text in texts)
    assert all(text.get_horizontalalignment() == "center" for text in texts)


def test_update_user_zorder_overrides_default(line_part):
    lines = line_part.update(zorder=5)
    assert all(line.get_zorder() == 5 for line in lines)
    # The user's zorder is kept by later updates.
    lines = line_part.update(n=3)
    assert all(line.get_zorder() == 5 for line in lines)


def test_update_normalizes_aliases_before_merging(line_part):
    # ``c`` replaces the default ``color``: no "both aliases" error.
    lines = line_part.update(c="red", lw=4)
    assert all(to_rgba(line.get_color()) == to_rgba("red") for line in lines)
    assert all(line.get_linewidth() == 4 for line in lines)
    # The canonical name replaces the value given through the alias.
    lines = line_part.update(color="blue", linewidth=5)
    assert all(to_rgba(line.get_color()) == to_rgba("blue") for line in lines)
    assert all(line.get_linewidth() == 5 for line in lines)


def test_update_normalizes_text_aliases(text_part):
    texts = text_part.update(size=7, ha="left")
    assert all(text.get_fontsize() == 7 for text in texts)
    assert all(text.get_horizontalalignment() == "left" for text in texts)
    texts = text_part.update(horizontalalignment="right")
    assert all(text.get_fontsize() == 7 for text in texts)
    assert all(text.get_horizontalalignment() == "right" for text in texts)


# ---------------------------------------------------------------------------
# update: visibility
# ---------------------------------------------------------------------------


def test_update_invisible_draws_nothing(ax, line_part):
    old = line_part.artists
    assert line_part.update(visible=False) == []
    assert line_part.artists == []
    assert list(ax.lines) == []
    assert all(line.axes is None for line in old)


def test_update_visible_again_restores_previous_settings(line_part):
    line_part.update(n=3, color="red")
    line_part.update(visible=False)
    lines = line_part.update(visible=True)
    assert len(lines) == 3
    assert all(to_rgba(line.get_color()) == to_rgba("red") for line in lines)


def test_update_settings_given_while_invisible_apply_when_shown(line_part):
    line_part.update(visible=False)
    assert line_part.update(n=4) == []
    assert len(line_part.update(visible=True)) == 4


def test_update_accepts_numpy_bool(line_part):
    assert line_part.update(visible=np.bool_(False)) == []
    assert len(line_part.update(visible=np.bool_(True))) == 2


@pytest.mark.parametrize("visible", [1, 0, 1.0, "yes"], ids=repr)
def test_update_rejects_non_bool_visible(ax, line_part, visible):
    before = line_part.artists
    with pytest.raises(TypeError, match="`visible` must be True or False"):
        line_part.update(visible=visible)
    assert _same_objects(line_part.artists, before)
    assert _same_objects(ax.lines, before)


# ---------------------------------------------------------------------------
# update: errors keep the previous state
# ---------------------------------------------------------------------------


def _snapshot(ax, part: _SkeletonPart) -> dict[str, Any]:
    return {
        "artists": part.artists,
        "children": _children(ax, part),
        "options": dict(part._options),
        "style": dict(part._style),
    }


def _assert_unchanged(ax, part: _SkeletonPart, before: dict[str, Any]):
    assert _same_objects(part.artists, before["artists"])
    assert _same_objects(_children(ax, part), before["children"])
    assert all(artist.axes is ax for artist in before["artists"])
    assert part._options == before["options"]
    assert part._style == before["style"]


def test_validation_error_keeps_state(ax, line_part):
    line_part.update(n=3, color="red")
    before = _snapshot(ax, line_part)
    with pytest.raises(ValueError, match="`n` must be"):
        line_part.update(n=-1, color="blue")
    _assert_unchanged(ax, line_part, before)


def test_error_in_specs_keeps_state(ax, line_part, monkeypatch):
    line_part.update(n=3, color="red")
    before = _snapshot(ax, line_part)

    def _raise(options, style):
        raise RuntimeError("formatter failed")

    monkeypatch.setattr(line_part, "_specs", _raise)
    with pytest.raises(RuntimeError, match="formatter failed"):
        line_part.update(n=4, color="blue")
    _assert_unchanged(ax, line_part, before)


def test_alias_and_canonical_name_in_one_call_raise(ax, line_part):
    before = _snapshot(ax, line_part)
    with pytest.raises(TypeError, match="lw"):
        line_part.update(lw=1, linewidth=2)
    _assert_unchanged(ax, line_part, before)


@pytest.mark.parametrize("part_class", [_LinePart, _TextPart])
def test_unknown_property_raises_matplotlib_error(ax, part_class):
    part = part_class(ax)
    before = _snapshot(ax, part)
    with pytest.raises(AttributeError, match="colour"):
        part.update(colour="red")
    _assert_unchanged(ax, part, before)


@pytest.mark.parametrize(
    ("part_class", "method", "settings", "failing"),
    [
        (_LinePart, "plot", {"n": 3}, {"n": 4, "color": "blue"}),
        (
            _TextPart,
            "text",
            {"labels": ("x", "y", "z")},
            {"labels": ("p", "q", "r", "s"), "fontsize": 20},
        ),
    ],
    ids=["line", "text"],
)
def test_failure_while_creating_removes_partial_artists(
    ax, monkeypatch, part_class, method, settings, failing
):
    part = part_class(ax, **settings)
    before = _snapshot(ax, part)

    # Record what the Axes creates during the failing update.
    created = []
    original = getattr(ax, method)

    def _recording(*args, **kwargs):
        result = original(*args, **kwargs)
        created.extend(result if isinstance(result, list) else [result])
        return result

    monkeypatch.setattr(ax, method, _recording)
    with pytest.raises(AttributeError, match="no_such_property"):
        part.update(fail_at=2, **failing)

    # Two artists were created before matplotlib rejected the third one.
    assert len(created) == 2
    assert all(artist.axes is None for artist in created)
    assert all(artist not in _children(ax, part) for artist in created)
    _assert_unchanged(ax, part, before)

    # The kept settings are the ones in effect before the failing call.
    monkeypatch.undo()
    redrawn = part.update()
    assert len(redrawn) == len(before["artists"])


# ---------------------------------------------------------------------------
# restack
# ---------------------------------------------------------------------------


def test_restack_moves_same_lines_to_the_end(ax, line_part):
    lines = line_part.update(n=3)
    (user_line,) = ax.plot([0, 1], [0, 1], color="green")
    assert ax.lines[-1] is user_line

    line_part.restack()

    assert ax.lines[0] is user_line
    assert _same_objects(ax.lines[-3:], lines)
    assert _same_objects(line_part.artists, lines)
    assert len(ax.lines) == 4
    assert all(line.axes is ax for line in lines)
    assert list(lines[2].get_ydata()) == [2.0, 2.0]


def test_restack_invisible_part_does_nothing(ax, line_part):
    line_part.update(visible=False)
    (user_line,) = ax.plot([0, 1], [0, 1])
    line_part.restack()
    assert list(ax.lines) == [user_line]


def test_restack_text_part_raises(text_part):
    with pytest.raises(TypeError, match="Line2D"):
        text_part.restack()


# ---------------------------------------------------------------------------
# Alias normalization on old matplotlib
# ---------------------------------------------------------------------------


def test_normalize_kwargs_accepts_artist_on_this_matplotlib():
    # The Artist class form exists in every matplotlib that supports
    # Python 3.9, so the fallback is only taken on older versions.
    version = tuple(map(int, matplotlib.__version__.split(".")[:2]))
    assert version >= (3, 3)
    assert _skeleton._NORMALIZE_KWARGS_ACCEPTS_ARTIST is True


# Passing a dict to ``normalize_kwargs`` is deprecated since matplotlib 3.11,
# but it is the only form that old matplotlib accepts.
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.mark.parametrize(
    ("artist_class", "kwargs", "expected"),
    [
        (
            matplotlib.lines.Line2D,
            {"lw": 1, "c": "r", "ls": "--", "aa": True, "zorder": 4},
            {
                "linewidth": 1,
                "color": "r",
                "linestyle": "--",
                "antialiased": True,
                "zorder": 4,
            },
        ),
        (
            matplotlib.text.Text,
            {
                "size": 3,
                "ha": "left",
                "va": "top",
                "family": "serif",
                "name": "DejaVu Sans",
                "weight": "bold",
            },
            {
                "fontsize": 3,
                "horizontalalignment": "left",
                "verticalalignment": "top",
                "fontfamily": "serif",
                "fontname": "DejaVu Sans",
                "fontweight": "bold",
            },
        ),
    ],
    ids=["Line2D", "Text"],
)
@pytest.mark.parametrize("accepts_artist", [True, False])
def test_normalize_style(
    monkeypatch, artist_class, kwargs, expected, accepts_artist
):
    monkeypatch.setattr(
        _skeleton, "_NORMALIZE_KWARGS_ACCEPTS_ARTIST", accepts_artist
    )
    assert _skeleton._normalize_style(kwargs, artist_class) == expected


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.mark.parametrize("accepts_artist", [True, False])
def test_normalize_style_rejects_alias_and_canonical_name(
    monkeypatch, accepts_artist
):
    monkeypatch.setattr(
        _skeleton, "_NORMALIZE_KWARGS_ACCEPTS_ARTIST", accepts_artist
    )
    with pytest.raises(TypeError, match="lw"):
        _skeleton._normalize_style(
            {"lw": 1, "linewidth": 2}, matplotlib.lines.Line2D
        )


@pytest.mark.parametrize(
    "artist_class", [matplotlib.lines.Line2D, matplotlib.text.Text]
)
def test_normalize_style_fallback_passes_the_alias_dict(
    monkeypatch, artist_class
):
    # Current matplotlib also accepts the class, so check what is passed.
    monkeypatch.setattr(_skeleton, "_NORMALIZE_KWARGS_ACCEPTS_ARTIST", False)
    calls = []

    def spy(kw, alias_mapping=None):
        calls.append(alias_mapping)
        return dict(kw)

    monkeypatch.setattr(_skeleton.cbook, "normalize_kwargs", spy)
    _skeleton._normalize_style({"zorder": 1}, artist_class)

    assert len(calls) == 1
    assert isinstance(calls[0], dict)
    assert calls[0] == _skeleton._alias_mapping(artist_class)


@pytest.mark.parametrize(
    "artist_class", [matplotlib.lines.Line2D, matplotlib.text.Text]
)
def test_alias_mapping_matches_matplotlib(artist_class):
    # Every alias in the fallback mapping is resolved the same way by the
    # Artist class form of ``normalize_kwargs``.
    from matplotlib import cbook

    mapping = _skeleton._alias_mapping(artist_class)
    assert mapping
    all_aliases = {alias for names in mapping.values() for alias in names}
    for canonical, aliases in mapping.items():
        assert canonical not in all_aliases
        for alias in aliases:
            assert cbook.normalize_kwargs({alias: 0}, artist_class) == {
                canonical: 0
            }


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_part_uses_fallback_normalization(ax, monkeypatch):
    monkeypatch.setattr(_skeleton, "_NORMALIZE_KWARGS_ACCEPTS_ARTIST", False)
    part = _LinePart(ax, zorder=1, lw=3, c="red")
    assert all(line.get_linewidth() == 3 for line in part.artists)
    assert all(
        to_rgba(line.get_color()) == to_rgba("red") for line in part.artists
    )


# ---------------------------------------------------------------------------
# Line parts: helpers
# ---------------------------------------------------------------------------


def _line_data(lines) -> list[tuple[list[float], list[float]]]:
    """The (xdata, ydata) of each line as lists, in the order of `lines`."""
    return [
        (
            [float(x) for x in line.get_xdata()],
            [float(y) for y in line.get_ydata()],
        )
        for line in lines
    ]


def _assert_line_style(lines, *, color, linewidth, linestyle, zorder):
    assert lines
    for line in lines:
        assert to_rgba(line.get_color()) == to_rgba(color)
        assert line.get_linewidth() == linewidth
        assert line.get_linestyle() == linestyle
        assert line.get_zorder() == zorder


def test_line_part_annotations_are_not_evaluated():
    for func in (_Border._specs, _Grid._validate, _Grid._specs):
        annotations = func.__annotations__
        assert annotations
        assert all(isinstance(value, str) for value in annotations.values())


@pytest.mark.parametrize("part_class", [_Border, _Grid])
def test_line_parts_draw_line2d_only(ax, part_class):
    part = part_class(ax, zorder=LINE_ZORDER)
    assert part.ARTIST_CLASS is matplotlib.lines.Line2D
    assert part.artists
    assert all(isinstance(a, matplotlib.lines.Line2D) for a in part.artists)
    assert list(ax.texts) == []


@pytest.mark.parametrize("part_class", [_Border, _Grid])
def test_line_parts_do_not_advance_color_cycle(ax, part_class):
    part_class(ax, zorder=LINE_ZORDER)
    (line,) = ax.plot([0, 1], [0, 1])
    assert to_rgba(line.get_color()) == to_rgba("C0")


# ---------------------------------------------------------------------------
# _Border
# ---------------------------------------------------------------------------


def test_border_defaults():
    assert _Border.OPTION_DEFAULTS == {"visible": True}
    assert _Border.STYLE_DEFAULTS == {
        "color": BORDER_COLOR,
        "linewidth": BORDER_LINEWIDTH,
        "linestyle": LINESTYLE,
    }
    assert _skeleton.DEFAULT_BORDER_COLOR == BORDER_COLOR
    assert _skeleton.DEFAULT_BORDER_LINEWIDTH == BORDER_LINEWIDTH
    assert _skeleton.DEFAULT_BORDER_LINESTYLE == LINESTYLE


def test_border_default_lines_match_v3(ax):
    lines = _Border(ax, zorder=LINE_ZORDER).artists
    assert _same_objects(ax.lines, lines)
    # The bottom, left and right edges, in this order.
    assert [line_key(line) for line in lines] == expected_border_lines()


def test_border_lines_have_v3_data(ax):
    lines = _Border(ax, zorder=LINE_ZORDER).artists
    assert _line_data(lines) == [
        ([0.0, 1.0], [0.0, 0.0]),
        ([0.0, 0.5], [0.0, ROOT3_OVER_2]),
        ([1.0, 0.5], [0.0, ROOT3_OVER_2]),
    ]


def test_border_uses_zorder_given_at_construction(ax):
    border = _Border(ax, zorder=7)
    assert all(line.get_zorder() == 7 for line in border.artists)
    # Redrawing keeps the zorder given at construction.
    assert all(line.get_zorder() == 7 for line in border.update(color="red"))


def test_border_user_zorder_overrides_default(ax):
    border = _Border(ax, zorder=LINE_ZORDER)
    assert all(line.get_zorder() == 4 for line in border.update(zorder=4))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"linestyle": "--", "linewidth": 1, "color": "red"},
        {"ls": "--", "lw": 1, "c": "red"},
    ],
    ids=["canonical", "aliases"],
)
def test_border_style_applies_to_all_edges(ax, kwargs):
    border = _Border(ax, zorder=LINE_ZORDER)
    lines = border.update(**kwargs)
    assert len(lines) == 3
    assert _same_objects(ax.lines, lines)
    _assert_line_style(
        lines, color="red", linewidth=1, linestyle="--", zorder=LINE_ZORDER
    )
    # Only the style changed, not the edges.
    assert [line_key(line).segment for line in lines] == [
        key.segment for key in expected_border_lines()
    ]


def test_border_style_at_construction(ax):
    lines = _Border(ax, zorder=LINE_ZORDER, linestyle=":").artists
    _assert_line_style(
        lines,
        color=BORDER_COLOR,
        linewidth=BORDER_LINEWIDTH,
        linestyle=":",
        zorder=LINE_ZORDER,
    )


def test_border_invisible_at_construction_draws_nothing(ax):
    border = _Border(ax, zorder=LINE_ZORDER, visible=False)
    assert border.artists == []
    assert list(ax.lines) == []


def test_border_invisible_removes_lines_and_visible_restores_them(ax):
    border = _Border(ax, zorder=LINE_ZORDER)
    border.update(color="red")
    old = border.artists
    assert border.update(visible=False) == []
    assert border.artists == []
    assert list(ax.lines) == []
    assert all(line.axes is None for line in old)

    lines = border.update(visible=True)
    assert len(lines) == 3
    assert all(to_rgba(line.get_color()) == to_rgba("red") for line in lines)


# ---------------------------------------------------------------------------
# _Grid
# ---------------------------------------------------------------------------


def _expected_grid_data(step: float) -> list[tuple[list[float], list[float]]]:
    """(xdata, ydata) of the grid lines given by the geometry functions.

    The lines of the components 0, 1 and 2 follow in turn, each with its
    values in ascending order.
    """
    values = get_tick_values(step)
    segments = [get_grid_segments(values, k) for k in range(3)]
    return [
        (xdata, ydata)
        for xs, ys in segments
        for xdata, ydata in zip(xs.tolist(), ys.tolist())
    ]


def test_grid_defaults():
    assert _Grid.OPTION_DEFAULTS == {"visible": True, "step": 0.1}
    assert _Grid.STYLE_DEFAULTS == {
        "color": GRID_COLOR,
        "linewidth": GRID_LINEWIDTH,
    }
    assert _skeleton.DEFAULT_GRID_STEP == 0.1
    assert _skeleton.DEFAULT_GRID_COLOR == GRID_COLOR
    assert _skeleton.DEFAULT_GRID_LINEWIDTH == GRID_LINEWIDTH


def test_grid_default_lines_match_v3(ax):
    lines = _Grid(ax, zorder=LINE_ZORDER).artists
    assert len(lines) == 27
    assert _same_objects(ax.lines, lines)
    # The order within the grid is not the one of v3: compare as multisets.
    assert Counter(map(line_key, lines)) == Counter(expected_grid_lines())


@pytest.mark.parametrize("step", [0.1, 0.05, 0.25, 0.3, 0.5])
def test_grid_lines_come_from_geometry_functions(ax, step):
    lines = _Grid(ax, zorder=LINE_ZORDER, step=step).artists
    assert _line_data(lines) == _expected_grid_data(step)


def test_grid_step_005_draws_57_lines(ax):
    grid = _Grid(ax, zorder=LINE_ZORDER)
    old = grid.artists
    lines = grid.update(step=0.05)

    assert len(lines) == 57
    assert _same_objects(ax.lines, lines)
    assert all(line.axes is None for line in old)
    # 19 iso-composition lines of the top component are horizontal.
    segments = [line_key(line).segment for line in lines]
    assert sum(start[1] == end[1] for start, end in segments) == 19
    # The lines at 10% steps are among them, each exactly once.
    keys = Counter(map(line_key, lines))
    assert all(keys[key] == 1 for key in expected_grid_lines())
    _assert_line_style(
        lines,
        color=GRID_COLOR,
        linewidth=GRID_LINEWIDTH,
        linestyle=LINESTYLE,
        zorder=LINE_ZORDER,
    )


def test_grid_step_at_construction(ax):
    grid = _Grid(ax, zorder=LINE_ZORDER, step=0.05)
    assert len(grid.artists) == 57
    assert len(ax.lines) == 57


def test_grid_step_one_draws_no_lines(ax):
    grid = _Grid(ax, zorder=LINE_ZORDER, step=1)
    assert grid.artists == []
    assert list(ax.lines) == []


def test_grid_uses_zorder_given_at_construction(ax):
    grid = _Grid(ax, zorder=7)
    assert all(line.get_zorder() == 7 for line in grid.artists)
    # Redrawing with another step keeps the zorder given at construction.
    assert all(line.get_zorder() == 7 for line in grid.update(step=0.05))


def test_grid_user_zorder_overrides_default(ax):
    grid = _Grid(ax, zorder=LINE_ZORDER)
    assert all(line.get_zorder() == 5 for line in grid.update(zorder=5))


def test_grid_style_applies_to_all_lines(ax):
    grid = _Grid(ax, zorder=LINE_ZORDER)
    lines = grid.update(color="red", linewidth=1.5, linestyle="--")
    assert len(lines) == 27
    _assert_line_style(
        lines, color="red", linewidth=1.5, linestyle="--", zorder=LINE_ZORDER
    )
    # Only the style changed, not the lines.
    assert Counter(line_key(line).segment for line in lines) == Counter(
        key.segment for key in expected_grid_lines()
    )


def test_grid_keeps_step_when_only_style_changes(ax):
    grid = _Grid(ax, zorder=LINE_ZORDER)
    grid.update(step=0.05)
    lines = grid.update(color="red")
    assert len(lines) == 57
    assert all(to_rgba(line.get_color()) == to_rgba("red") for line in lines)


def test_grid_keeps_style_when_only_step_changes(ax):
    grid = _Grid(ax, zorder=LINE_ZORDER, lw=2, color="blue")
    lines = grid.update(step=0.25)
    assert len(lines) == 9
    _assert_line_style(
        lines, color="blue", linewidth=2, linestyle="-", zorder=LINE_ZORDER
    )


def test_grid_invisible_at_construction_draws_nothing(ax):
    grid = _Grid(ax, zorder=LINE_ZORDER, visible=False)
    assert grid.artists == []
    assert list(ax.lines) == []


def test_grid_invisible_removes_lines_and_visible_restores_them(ax):
    grid = _Grid(ax, zorder=LINE_ZORDER, step=0.05)
    old = grid.artists
    assert grid.update(visible=False) == []
    assert grid.artists == []
    assert list(ax.lines) == []
    assert all(line.axes is None for line in old)

    # The step given before hiding the grid is used again.
    assert len(grid.update(visible=True)) == 57


@pytest.mark.parametrize(
    ("step", "error"),
    [
        (0, ValueError),
        (-0.1, ValueError),
        (1.5, ValueError),
        (float("nan"), ValueError),
        (float("inf"), ValueError),
        ("0.1", TypeError),
        (True, TypeError),
    ],
    ids=repr,
)
def test_grid_rejects_invalid_step(ax, step, error):
    grid = _Grid(ax, zorder=LINE_ZORDER)
    before = _snapshot(ax, grid)
    with pytest.raises(error, match="`step`"):
        grid.update(step=step, color="red")
    _assert_unchanged(ax, grid, before)


def test_grid_rejects_invalid_step_while_invisible(ax):
    # Nothing is drawn, so only the validation step can catch it.
    grid = _Grid(ax, zorder=LINE_ZORDER, visible=False)
    before = _snapshot(ax, grid)
    with pytest.raises(ValueError, match="`step` must satisfy 0 < step <= 1"):
        grid.update(step=0)
    _assert_unchanged(ax, grid, before)
    with pytest.raises(ValueError, match="`step` must satisfy 0 < step <= 1"):
        _Grid(ax, zorder=LINE_ZORDER, visible=False, step=0)


def test_grid_invalid_step_at_construction_leaves_nothing(ax):
    with pytest.raises(ValueError, match="`step` must satisfy 0 < step <= 1"):
        _Grid(ax, zorder=LINE_ZORDER, step=0)
    assert list(ax.lines) == []


# ---------------------------------------------------------------------------
# _TickLabels
# ---------------------------------------------------------------------------

# Offset from the point on the edge, rotation, horizontal alignment and
# vertical alignment of the tick labels of the components 0 (right edge),
# 1 (left edge) and 2 (bottom edge), as given by the design.
TICK_EDGE_LAYOUT = (
    ((0.0, 0.0), 0.0, "left", "bottom"),
    ((-0.01, 0.04), 300.0, "right", "top"),
    ((0.02, 0.0), 60.0, "right", "top"),
)


def _tick_layout(texts) -> list[tuple]:
    """(text, position, rotation, ha, va) of each label, in order."""
    return [
        (
            key.text,
            key.position,
            key.rotation,
            key.horizontalalignment,
            key.verticalalignment,
        )
        for key in map(text_key, texts)
    ]


def _expected_tick_layout(
    step: float = 0.1, *, endpoints: bool = False, fmt: Any = "percent"
) -> list[tuple]:
    """Layout of the tick labels given by the geometry functions.

    For each value in ascending order, the labels of the components 0, 1
    and 2 follow in turn, in the form returned by `_tick_layout`.
    """
    values = get_tick_values(step, endpoints=endpoints)
    format_value = get_tick_formatter(fmt)
    points = [get_edge_points(values, k) for k in range(3)]
    layout = []
    for i, value in enumerate(values.tolist()):
        for (xs, ys), ((dx, dy), rotation, ha, va) in zip(
            points, TICK_EDGE_LAYOUT
        ):
            layout.append(
                (
                    format_value(value),
                    point_key(xs[i] + dx, ys[i] + dy),
                    rotation,
                    ha,
                    va,
                )
            )
    return layout


def test_tick_labels_annotations_are_not_evaluated():
    for func in (_TickLabels._validate, _TickLabels._specs):
        annotations = func.__annotations__
        assert annotations
        assert all(isinstance(value, str) for value in annotations.values())


def test_tick_labels_defaults():
    assert _TickLabels.OPTION_DEFAULTS == {
        "visible": True,
        "step": 0.1,
        "fmt": "percent",
        "endpoints": False,
    }
    assert _TickLabels.STYLE_DEFAULTS == {"fontsize": TICK_LABEL_FONTSIZE}
    assert _TickLabels.ARTIST_CLASS is matplotlib.text.Text
    assert _skeleton.DEFAULT_TICK_STEP == 0.1
    assert _skeleton.DEFAULT_TICK_FORMAT == "percent"
    assert _skeleton.DEFAULT_TICK_ENDPOINTS is False
    assert _skeleton.DEFAULT_TICK_FONTSIZE == TICK_LABEL_FONTSIZE


def test_tick_labels_default_texts_match_v3(ax):
    texts = _TickLabels(ax).artists
    assert len(texts) == 27
    assert all(isinstance(text, matplotlib.text.Text) for text in texts)
    assert _same_objects(ax.texts, texts)
    assert list(ax.lines) == []
    # For each value from "10" to "90": the right, left and bottom edges.
    assert [text_key(text) for text in texts] == expected_tick_label_texts()


@pytest.mark.parametrize("endpoints", [False, True])
@pytest.mark.parametrize("step", [0.1, 0.05, 0.25, 0.3])
def test_tick_labels_layout_comes_from_geometry_functions(ax, step, endpoints):
    texts = _TickLabels(ax, step=step, endpoints=endpoints).artists
    assert _tick_layout(texts) == _expected_tick_layout(
        step, endpoints=endpoints
    )


def test_tick_labels_follow_the_placement_convention(ax):
    # Component 0 on the right edge, 1 on the left edge and 2 on the bottom
    # edge, with the values increasing counterclockwise from 0 to 1.
    texts = _TickLabels(ax, endpoints=True).artists
    right, left, bottom = texts[0::3], texts[1::3], texts[2::3]

    def ends(edge):
        return text_key(edge[0]).position, text_key(edge[-1]).position

    assert ends(right) == (point_key(1.0, 0.0), point_key(0.5, ROOT3_OVER_2))
    assert ends(left) == (
        point_key(0.5 - 0.01, ROOT3_OVER_2 + 0.04),
        point_key(-0.01, 0.04),
    )
    assert ends(bottom) == (point_key(0.02, 0.0), point_key(1.02, 0.0))


def test_tick_labels_endpoints_draw_11_labels_per_edge(ax):
    part = _TickLabels(ax)
    old = part.artists
    texts = part.update(endpoints=True)

    assert len(texts) == 33
    assert _same_objects(ax.texts, texts)
    assert all(text.axes is None for text in old)
    labels = [str(10 * i) for i in range(11)]
    for k in range(3):
        assert [text.get_text() for text in texts[k::3]] == labels


def test_tick_labels_endpoints_at_construction(ax):
    part = _TickLabels(ax, endpoints=True)
    assert len(part.artists) == 33
    assert len(ax.texts) == 33


def test_tick_labels_fraction_format(ax):
    part = _TickLabels(ax)
    texts = part.update(fmt="fraction")

    assert texts[0].get_text() == "0.1"
    fractions = [f"0.{i}" for i in range(1, 10)]
    for k in range(3):
        assert [text.get_text() for text in texts[k::3]] == fractions
    # Only the strings changed.
    assert [key[1:] for key in _tick_layout(texts)] == [
        key[1:] for key in _expected_tick_layout()
    ]


@pytest.mark.parametrize(
    ("fmt", "first", "last"),
    [
        ("percent", "10", "90"),
        ("fraction", "0.1", "0.9"),
        ("%.2f", "0.10", "0.90"),
        ("{:.0%}", "10%", "90%"),
        ("{x:.1f}", "0.1", "0.9"),
        (lambda value: f"{value * 100:.1f}%", "10.0%", "90.0%"),
    ],
    ids=["percent", "fraction", "%-style", "{}-style", "{x}-style", "func"],
)
def test_tick_labels_format(ax, fmt, first, last):
    texts = _TickLabels(ax, fmt=fmt).artists
    assert len(texts) == 27
    for k in range(3):
        edge = texts[k::3]
        assert edge[0].get_text() == first
        assert edge[-1].get_text() == last


def test_tick_labels_format_callable_receives_fractions(ax):
    received = []

    def fmt(value):
        received.append(value)
        return "x"

    texts = _TickLabels(ax, fmt=fmt).artists
    assert [text.get_text() for text in texts] == ["x"] * 27
    assert all(type(value) is float for value in received)
    assert sorted(set(received)) == get_tick_values(0.1).tolist()


@pytest.mark.parametrize(
    ("step", "per_edge"), [(0.1, 9), (0.05, 19), (0.25, 3), (0.5, 1), (1, 0)]
)
def test_tick_labels_step(ax, step, per_edge):
    texts = _TickLabels(ax, step=step).artists
    assert len(texts) == 3 * per_edge
    assert len(ax.texts) == 3 * per_edge


def test_tick_labels_step_005_replaces_labels(ax):
    part = _TickLabels(ax)
    old = part.artists
    texts = part.update(step=0.05)

    assert len(texts) == 57
    assert _same_objects(ax.texts, texts)
    assert all(text.axes is None for text in old)
    assert [text.get_text() for text in texts[2::3]][:3] == ["5", "10", "15"]
    assert _tick_layout(texts) == _expected_tick_layout(0.05)


@pytest.mark.parametrize(
    "kwargs",
    [{"fontsize": 8, "color": "red"}, {"size": 8, "c": "red"}],
    ids=["canonical", "aliases"],
)
def test_tick_labels_style_applies_to_all_labels(ax, kwargs):
    part = _TickLabels(ax)
    texts = part.update(**kwargs)

    assert len(texts) == 27
    assert all(text.get_fontsize() == 8 for text in texts)
    assert all(to_rgba(text.get_color()) == to_rgba("red") for text in texts)
    # The per-edge layout is kept.
    assert _tick_layout(texts) == _expected_tick_layout()


def test_tick_labels_style_at_construction(ax):
    texts = _TickLabels(ax, fontsize=12).artists
    assert len(texts) == 27
    assert all(text.get_fontsize() == 12 for text in texts)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rotation": 45, "ha": "center"},
        {"rotation": 45, "horizontalalignment": "center"},
    ],
    ids=["alias", "canonical"],
)
def test_tick_labels_user_properties_override_edge_defaults(ax, kwargs):
    texts = _TickLabels(ax).update(**kwargs)

    # The same value applies to the labels of every edge.
    assert all(text.get_rotation() == 45 for text in texts)
    assert all(text.get_horizontalalignment() == "center" for text in texts)
    # Properties not given keep their per-edge defaults, and the positions
    # do not change.
    assert [text.get_verticalalignment() for text in texts[:3]] == [
        "bottom",
        "top",
        "top",
    ]
    assert [text_key(text).position for text in texts] == [
        key[1] for key in _expected_tick_layout()
    ]


def test_tick_labels_keep_matplotlib_default_zorder(ax):
    part = _TickLabels(ax)
    assert len(part.artists) == 27
    assert all(text.get_zorder() == TEXT_ZORDER for text in part.artists)
    # Redrawing keeps the zorder of the labels of v3.
    texts = part.update(step=0.05, fontsize=8)
    assert len(texts) == 57
    assert all(text.get_zorder() == TEXT_ZORDER for text in texts)


def test_tick_labels_user_zorder_overrides_default(ax):
    texts = _TickLabels(ax).update(zorder=5)
    assert len(texts) == 27
    assert all(text.get_zorder() == 5 for text in texts)


def test_tick_labels_keep_options_when_only_style_changes(ax):
    part = _TickLabels(ax)
    part.update(step=0.05, fmt="fraction", endpoints=True)
    texts = part.update(color="red")

    assert len(texts) == 63
    assert _tick_layout(texts) == _expected_tick_layout(
        0.05, endpoints=True, fmt="fraction"
    )
    assert all(to_rgba(text.get_color()) == to_rgba("red") for text in texts)


def test_tick_labels_keep_style_when_only_options_change(ax):
    part = _TickLabels(ax, fontsize=8, color="blue")
    texts = part.update(fmt="fraction", step=0.25)

    assert [text.get_text() for text in texts] == [
        label for label in ("0.25", "0.5", "0.75") for _ in range(3)
    ]
    assert all(text.get_fontsize() == 8 for text in texts)
    assert all(to_rgba(text.get_color()) == to_rgba("blue") for text in texts)


def test_tick_labels_invisible_at_construction_draws_nothing(ax):
    part = _TickLabels(ax, visible=False)
    assert part.artists == []
    assert list(ax.texts) == []


def test_tick_labels_invisible_removes_labels_and_visible_restores_them(ax):
    part = _TickLabels(ax, step=0.25, fmt="fraction", endpoints=True, size=8)
    old = part.artists
    assert part.update(visible=False) == []
    assert part.artists == []
    assert list(ax.texts) == []
    assert all(text.axes is None for text in old)

    # The settings given before hiding the labels are used again.
    texts = part.update(visible=True)
    assert _tick_layout(texts) == _expected_tick_layout(
        0.25, endpoints=True, fmt="fraction"
    )
    assert all(text.get_fontsize() == 8 for text in texts)


@pytest.mark.parametrize(
    ("step", "error"),
    [
        (0, ValueError),
        (-0.1, ValueError),
        (1.5, ValueError),
        (float("nan"), ValueError),
        (float("inf"), ValueError),
        ("0.1", TypeError),
        (True, TypeError),
    ],
    ids=repr,
)
def test_tick_labels_reject_invalid_step(ax, step, error):
    part = _TickLabels(ax)
    before = _snapshot(ax, part)
    with pytest.raises(error, match="`step`"):
        part.update(step=step, fontsize=20)
    _assert_unchanged(ax, part, before)


@pytest.mark.parametrize(
    ("fmt", "error"),
    [("abc", ValueError), ("{y}", ValueError), (1, TypeError)],
    ids=repr,
)
def test_tick_labels_reject_invalid_fmt(ax, fmt, error):
    part = _TickLabels(ax)
    before = _snapshot(ax, part)
    with pytest.raises(error, match="`fmt`"):
        part.update(fmt=fmt, fontsize=20)
    _assert_unchanged(ax, part, before)


@pytest.mark.parametrize("endpoints", [1, 0, 1.0, "yes"], ids=repr)
def test_tick_labels_reject_non_bool_endpoints(ax, endpoints):
    part = _TickLabels(ax)
    before = _snapshot(ax, part)
    with pytest.raises(TypeError, match="`endpoints` must be True or False"):
        part.update(endpoints=endpoints, fontsize=20)
    _assert_unchanged(ax, part, before)


def test_tick_labels_accept_numpy_bool_endpoints(ax):
    part = _TickLabels(ax)
    assert len(part.update(endpoints=np.bool_(True))) == 33
    # Kept as the built-in bool returned by check_bool.
    assert part._options["endpoints"] is True
    assert len(part.update(endpoints=np.bool_(False))) == 27
    assert part._options["endpoints"] is False


@pytest.mark.parametrize(
    ("kwargs", "error", "match"),
    [
        ({"step": 0}, ValueError, "`step` must satisfy 0 < step <= 1"),
        ({"step": "0.1"}, TypeError, "`step` must be a real number"),
        ({"fmt": "abc"}, ValueError, "`fmt` must be"),
        ({"fmt": 1}, TypeError, "`fmt` must be a str or a callable"),
        ({"endpoints": 1}, TypeError, "`endpoints` must be True or False"),
    ],
    ids=["step-value", "step-type", "fmt-value", "fmt-type", "endpoints"],
)
def test_tick_labels_validate_options_while_invisible(
    ax, kwargs, error, match
):
    # Nothing is drawn, so only the validation step can catch these.
    part = _TickLabels(ax, visible=False)
    before = _snapshot(ax, part)
    with pytest.raises(error, match=match):
        part.update(**kwargs)
    _assert_unchanged(ax, part, before)
    with pytest.raises(error, match=match):
        _TickLabels(ax, visible=False, **kwargs)
    assert list(ax.texts) == []


def test_tick_labels_invalid_step_at_construction_leaves_nothing(ax):
    with pytest.raises(ValueError, match="`step` must satisfy 0 < step <= 1"):
        _TickLabels(ax, step=0)
    assert list(ax.texts) == []


def test_tick_labels_raising_format_callable_keeps_state(ax):
    part = _TickLabels(ax, fmt="fraction", fontsize=8)
    before = _snapshot(ax, part)

    def fmt(value):
        # Some values are formatted before the error.
        if value > 0.5:
            raise RuntimeError("cannot format the value")
        return f"{value:.1f}"

    with pytest.raises(RuntimeError, match="cannot format the value"):
        part.update(fmt=fmt, step=0.05, color="red")
    # The same texts and settings, and no new texts on the Axes.
    _assert_unchanged(ax, part, before)

    # The settings in effect before the failing call are used again.
    texts = part.update()
    assert _tick_layout(texts) == _expected_tick_layout(fmt="fraction")
    assert all(text.get_fontsize() == 8 for text in texts)


def test_tick_labels_raising_format_callable_at_construction(ax):
    def fmt(value):
        raise RuntimeError("cannot format the value")

    with pytest.raises(RuntimeError, match="cannot format the value"):
        _TickLabels(ax, fmt=fmt)
    assert list(ax.texts) == []


# ---------------------------------------------------------------------------
# _AxisLabels
# ---------------------------------------------------------------------------

AXIS_LABEL_FONTSIZE = 12.0
AXIS_LABEL_PAD = 0.15
THREE_TITLES = ("Li2O / mol%", "La2O3 / mol%", "TiO2 / mol%")


def _expected_axis_label_layout(
    titles: dict[int, str], pad: float = AXIS_LABEL_PAD
) -> list[tuple]:
    """Layout of the axis titles given by ``get_axis_label_position``.

    `titles` maps the components that have a title to the title. The
    titles follow in the order of the components, centered, in the form
    returned by `_tick_layout`.
    """
    layout = []
    for component in sorted(titles):
        x, y, rotation = get_axis_label_position(component, pad)
        layout.append(
            (titles[component], point_key(x, y), rotation, "center", "center")
        )
    return layout


def test_axis_labels_annotations_are_not_evaluated():
    for func in (_AxisLabels._validate, _AxisLabels._specs):
        annotations = func.__annotations__
        assert annotations
        assert all(isinstance(value, str) for value in annotations.values())


def test_axis_labels_defaults():
    assert _AxisLabels.OPTION_DEFAULTS == {
        "visible": True,
        "labels": (None, None, None),
        "pad": AXIS_LABEL_PAD,
    }
    assert _AxisLabels.STYLE_DEFAULTS == {
        "fontsize": AXIS_LABEL_FONTSIZE,
        "horizontalalignment": "center",
        "verticalalignment": "center",
    }
    assert _AxisLabels.ARTIST_CLASS is matplotlib.text.Text
    assert _skeleton.DEFAULT_AXIS_LABELS == (None, None, None)
    assert _skeleton.DEFAULT_AXIS_LABEL_PAD == AXIS_LABEL_PAD
    assert _skeleton.DEFAULT_AXIS_LABEL_FONTSIZE == AXIS_LABEL_FONTSIZE
    assert _skeleton.DEFAULT_AXIS_LABEL_HORIZONTALALIGNMENT == "center"
    assert _skeleton.DEFAULT_AXIS_LABEL_VERTICALALIGNMENT == "center"


def test_axis_labels_draw_nothing_by_default(ax):
    part = _AxisLabels(ax)
    assert part.artists == []
    assert list(ax.texts) == []
    assert list(ax.lines) == []
    # The part is visible; it only has no titles.
    assert part._options["visible"] is True


def test_axis_labels_three_titles_draw_three_texts(ax):
    texts = _AxisLabels(ax, labels=THREE_TITLES).artists

    assert len(texts) == 3
    assert all(isinstance(text, matplotlib.text.Text) for text in texts)
    assert _same_objects(ax.texts, texts)
    assert list(ax.lines) == []
    assert _tick_layout(texts) == _expected_axis_label_layout(
        dict(enumerate(THREE_TITLES))
    )
    # Parallel to the right, left and bottom edges, never upside down.
    assert [text.get_rotation() for text in texts] == [300.0, 60.0, 0.0]
    assert text_key(texts[2]).position == point_key(0.5, -AXIS_LABEL_PAD)
    assert all(text.get_fontsize() == AXIS_LABEL_FONTSIZE for text in texts)


@pytest.mark.parametrize(
    ("labels", "titles"),
    [
        (("A", None, ""), {0: "A"}),
        ((None, "B", None), {1: "B"}),
        (("", "", "C"), {2: "C"}),
        (("A", None, "C"), {0: "A", 2: "C"}),
        ((None, None, None), {}),
        (("", "", ""), {}),
    ],
    ids=repr,
)
def test_axis_labels_draw_only_given_titles(ax, labels, titles):
    texts = _AxisLabels(ax, labels=labels).artists

    assert len(texts) == len(titles)
    assert _same_objects(ax.texts, texts)
    assert _tick_layout(texts) == _expected_axis_label_layout(titles)


@pytest.mark.parametrize(
    "label", ["Li2O / mol%", "La2O3", "TiO$_2$ (at.%)", " "], ids=repr
)
def test_axis_labels_are_shown_as_given(ax, label):
    # Unlike the vertex labels, the titles are not turned into chemical
    # formulas such as "Li$_{2}$O".
    texts = _AxisLabels(ax, labels=(label, label, label)).artists
    assert [text.get_text() for text in texts] == [label] * 3


@pytest.mark.parametrize("pad", [0.0, 0.05, 0.15, 0.3, -0.05, 1], ids=repr)
def test_axis_labels_layout_comes_from_geometry_function(ax, pad):
    texts = _AxisLabels(ax, labels=("A", "B", "C"), pad=pad).artists
    assert _tick_layout(texts) == _expected_axis_label_layout(
        {0: "A", 1: "B", 2: "C"}, pad
    )


def test_axis_labels_are_outside_the_middle_of_their_tick_edges(ax):
    pad = 0.2
    texts = _AxisLabels(ax, labels=("A", "B", "C"), pad=pad).artists
    centroid = (0.5, ROOT3_OVER_2 / 3.0)

    for component, text in enumerate(texts):
        # The edge that carries the ticks of the component, from 0 to 1.
        (x0, x1), (y0, y1) = get_edge_points([0.0, 1.0], component)
        mid_x, mid_y = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        x, y = text.get_position()

        def side(px, py):
            return (x1 - x0) * (py - y0) - (y1 - y0) * (px - x0)

        # `pad` away from the midpoint, perpendicular to the edge, on the
        # other side of the edge than the triangle.
        assert np.hypot(x - mid_x, y - mid_y) == pytest.approx(pad)
        assert (x - mid_x) * (x1 - x0) + (y - mid_y) * (
            y1 - y0
        ) == pytest.approx(0.0, abs=1e-12)
        assert side(x, y) * side(*centroid) < 0
        # Parallel to the edge and not upside down.
        edge_angle = np.degrees(np.arctan2(y1 - y0, x1 - x0))
        rotation = text.get_rotation()
        assert (rotation - edge_angle) % 180.0 == pytest.approx(
            0.0, abs=1e-9
        ) or (rotation - edge_angle) % 180.0 == pytest.approx(180.0)
        assert rotation <= 90.0 or rotation > 270.0


def test_axis_labels_update_replaces_titles(ax):
    part = _AxisLabels(ax, labels=("A", "B", "C"))
    old = part.artists
    texts = part.update(labels=("X", None, "Z"))

    assert [text.get_text() for text in texts] == ["X", "Z"]
    assert _same_objects(ax.texts, texts)
    assert _same_objects(part.artists, texts)
    assert all(text.axes is None for text in old)


def test_axis_labels_update_adds_titles_to_the_default(ax):
    part = _AxisLabels(ax)
    texts = part.update(labels=THREE_TITLES)
    assert _tick_layout(texts) == _expected_axis_label_layout(
        dict(enumerate(THREE_TITLES))
    )
    assert _same_objects(ax.texts, texts)


@pytest.mark.parametrize(
    "kwargs",
    [{"fontsize": 14, "color": "red"}, {"size": 14, "c": "red"}],
    ids=["canonical", "aliases"],
)
def test_axis_labels_style_applies_to_all_titles(ax, kwargs):
    part = _AxisLabels(ax, labels=("A", "B", "C"))
    texts = part.update(**kwargs)

    assert len(texts) == 3
    assert all(text.get_fontsize() == 14 for text in texts)
    assert all(to_rgba(text.get_color()) == to_rgba("red") for text in texts)
    # The positions, rotations and alignments are kept.
    assert _tick_layout(texts) == _expected_axis_label_layout(
        {0: "A", 1: "B", 2: "C"}
    )


def test_axis_labels_style_at_construction(ax):
    texts = _AxisLabels(ax, labels=("A", "B", "C"), fontsize=16).artists
    assert len(texts) == 3
    assert all(text.get_fontsize() == 16 for text in texts)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rotation": 0, "ha": "left", "va": "top"},
        {
            "rotation": 0,
            "horizontalalignment": "left",
            "verticalalignment": "top",
        },
    ],
    ids=["aliases", "canonical"],
)
def test_axis_labels_user_properties_override_defaults(ax, kwargs):
    texts = _AxisLabels(ax, labels=("A", "B", "C")).update(**kwargs)

    # The same value applies to the titles of every edge.
    assert all(text.get_rotation() == 0 for text in texts)
    assert all(text.get_horizontalalignment() == "left" for text in texts)
    assert all(text.get_verticalalignment() == "top" for text in texts)
    # The positions do not change.
    assert [text_key(text).position for text in texts] == [
        key[1] for key in _expected_axis_label_layout({0: "A", 1: "B", 2: "C"})
    ]


def test_axis_labels_keep_matplotlib_default_zorder(ax):
    part = _AxisLabels(ax, labels=("A", "B", "C"))
    assert len(part.artists) == 3
    assert all(text.get_zorder() == TEXT_ZORDER for text in part.artists)
    # Redrawing keeps the zorder of the other labels.
    texts = part.update(pad=0.2, fontsize=8)
    assert len(texts) == 3
    assert all(text.get_zorder() == TEXT_ZORDER for text in texts)


def test_axis_labels_user_zorder_overrides_default(ax):
    texts = _AxisLabels(ax, labels=("A", "B", "C")).update(zorder=5)
    assert len(texts) == 3
    assert all(text.get_zorder() == 5 for text in texts)


def test_axis_labels_keep_options_when_only_style_changes(ax):
    part = _AxisLabels(ax, labels=("A", None, "C"), pad=0.25)
    texts = part.update(color="red")

    assert _tick_layout(texts) == _expected_axis_label_layout(
        {0: "A", 2: "C"}, 0.25
    )
    assert all(to_rgba(text.get_color()) == to_rgba("red") for text in texts)


def test_axis_labels_keep_style_when_only_options_change(ax):
    part = _AxisLabels(ax, labels=("A", "B", "C"), fontsize=8, color="blue")
    texts = part.update(labels=(None, "Y", None), pad=0.3)

    assert _tick_layout(texts) == _expected_axis_label_layout({1: "Y"}, 0.3)
    assert all(text.get_fontsize() == 8 for text in texts)
    assert all(to_rgba(text.get_color()) == to_rgba("blue") for text in texts)


def test_axis_labels_keep_titles_when_only_pad_changes(ax):
    part = _AxisLabels(ax, labels=("A", None, "C"))
    texts = part.update(labels=None, pad=0.05)
    assert _tick_layout(texts) == _expected_axis_label_layout(
        {0: "A", 2: "C"}, 0.05
    )


def test_axis_labels_keep_a_copy_of_the_titles(ax):
    labels = ["A", None, "C"]
    part = _AxisLabels(ax, labels=labels)
    # Changing the given list afterwards does not change the part.
    labels[1] = "B"
    assert part._options["labels"] == ("A", None, "C")
    texts = part.update(fontsize=14)
    assert [text.get_text() for text in texts] == ["A", "C"]


def test_axis_labels_accept_numpy_str_titles(ax):
    part = _AxisLabels(ax, labels=[np.str_("A"), None, np.str_("C")])
    assert [text.get_text() for text in part.artists] == ["A", "C"]
    # Kept as the built-in str, as matplotlib converts them when drawing.
    assert part._options["labels"] == ("A", None, "C")
    assert [type(item) for item in part._options["labels"]] == [
        str,
        type(None),
        str,
    ]


def _assert_titles_stored(part: _AxisLabels, expected: tuple) -> None:
    """The part keeps `expected` as a tuple of built-in str and None."""
    stored = part._options["labels"]
    assert type(stored) is tuple
    assert stored == expected
    assert all(item is None or type(item) is str for item in stored)


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (["A", None, "C"], ("A", None, "C")),
        (("A", "B", ""), ("A", "B", "")),
        (pd.Index(["Li2O", "La2O3", "TiO2"]), ("Li2O", "La2O3", "TiO2")),
        (
            pd.Index(["Li2O", "La2O3", "TiO2"]) + " / mol%",
            ("Li2O / mol%", "La2O3 / mol%", "TiO2 / mol%"),
        ),
        (pd.Series(["A", "", "C"]), ("A", "", "C")),
        (np.array(["A", "B", "C"]), ("A", "B", "C")),
        (np.array(["A", None, "C"], dtype=object), ("A", None, "C")),
    ],
    ids=[
        "list",
        "tuple",
        "pandas-index",
        "pandas-index-with-unit",
        "pandas-series",
        "numpy-str",
        "numpy-object",
    ],
)
def test_axis_labels_accept_ordered_iterables(ax, labels, expected):
    part = _AxisLabels(ax, labels=labels)

    _assert_titles_stored(part, expected)
    titles = {k: title for k, title in enumerate(expected) if title}
    assert _tick_layout(part.artists) == _expected_axis_label_layout(titles)
    assert _same_objects(ax.texts, part.artists)


def test_axis_labels_accept_dataframe_columns(ax, df_contour):
    # The same usage as ``TernaryDiagram(materials=df.columns[:3])``.
    part = _AxisLabels(ax)
    texts = part.update(labels=df_contour.columns[:3] + " / mol%")

    expected = ("Li2O / mol%", "TiO2 / mol%", "La2O3 / mol%")
    _assert_titles_stored(part, expected)
    assert [text.get_text() for text in texts] == list(expected)


def test_axis_labels_accept_a_generator_consumed_once(ax):
    part = _AxisLabels(ax, labels=(f"{m} / mol%" for m in ("A", "B", "C")))
    expected = ("A / mol%", "B / mol%", "C / mol%")
    _assert_titles_stored(part, expected)

    # Redrawing uses the stored titles, not the exhausted generator.
    texts = part.update(fontsize=14)
    assert [text.get_text() for text in texts] == list(expected)


def test_axis_labels_reject_a_generator_of_wrong_length(ax):
    part = _AxisLabels(ax, labels=("A", "B", "C"))
    before = _snapshot(ax, part)
    with pytest.raises(ValueError, match="`labels` must have 3 items"):
        part.update(labels=(m for m in ("A", "B")))
    _assert_unchanged(ax, part, before)


def test_axis_labels_reject_0d_array_from_the_iteration_error(ax):
    part = _AxisLabels(ax, labels=("A", "B", "C"))
    before = _snapshot(ax, part)
    with pytest.raises(
        TypeError, match="`labels` must be a sequence .* iterating over"
    ) as excinfo:
        part.update(labels=np.array("ABC"))
    # The error of numpy is kept as the cause.
    assert isinstance(excinfo.value.__cause__, TypeError)
    _assert_unchanged(ax, part, before)


def test_axis_labels_invisible_at_construction_draws_nothing(ax):
    part = _AxisLabels(ax, labels=("A", "B", "C"), visible=False)
    assert part.artists == []
    assert list(ax.texts) == []


def test_axis_labels_invisible_removes_titles_and_visible_restores_them(ax):
    part = _AxisLabels(ax, labels=("A", None, "C"), pad=0.2, size=14)
    old = part.artists
    assert len(old) == 2
    assert part.update(visible=False) == []
    assert part.artists == []
    assert list(ax.texts) == []
    assert all(text.axes is None for text in old)

    # The settings given before hiding the titles are used again.
    texts = part.update(visible=True)
    assert _tick_layout(texts) == _expected_axis_label_layout(
        {0: "A", 2: "C"}, 0.2
    )
    assert all(text.get_fontsize() == 14 for text in texts)


@pytest.mark.parametrize(
    "labels",
    [
        ("A", "B"),
        ("A", "B", "C", "D"),
        (),
        ["A"],
        (None, None),
        np.array(["A", "B"]),
        pd.Index(["A", "B", "C", "D"]),
    ],
    ids=[
        "tuple-2",
        "tuple-4",
        "empty",
        "list-1",
        "none-2",
        "numpy-2",
        "pandas-index-4",
    ],
)
def test_axis_labels_reject_wrong_number_of_titles(ax, labels):
    part = _AxisLabels(ax, labels=("A", "B", "C"))
    before = _snapshot(ax, part)
    with pytest.raises(ValueError, match="`labels` must have 3 items"):
        part.update(labels=labels, fontsize=20)
    _assert_unchanged(ax, part, before)


@pytest.mark.parametrize(
    "labels",
    [
        "ABC",
        np.str_("ABC"),
        b"ABC",
        3,
        3.0,
        {"A", "B", "C"},
        frozenset({"A", "B", "C"}),
        {"A": 0, "B": 1, "C": 2},
        np.array("ABC"),
    ],
    ids=[
        "str",
        "numpy-str",
        "bytes",
        "int",
        "float",
        "set",
        "frozenset",
        "dict",
        "numpy-0d",
    ],
)
def test_axis_labels_reject_non_sequence_titles(ax, labels):
    part = _AxisLabels(ax, labels=("A", "B", "C"))
    before = _snapshot(ax, part)
    # The message names the accepted types.
    with pytest.raises(
        TypeError,
        match=(
            "`labels` must be a sequence of 3 titles \\(str or None\\) such "
            "as a list, a tuple, a numpy array or a pandas Index"
        ),
    ):
        part.update(labels=labels, fontsize=20)
    _assert_unchanged(ax, part, before)


@pytest.mark.parametrize(
    "labels",
    [
        ("A", 1, None),
        (b"A", None, None),
        (None, None, ["C"]),
        ("A", "B", 0.5),
        ("A", "B", float("nan")),
        np.array([["A"], ["B"], ["C"]]),
        pd.Series(["A", "B", 1]),
    ],
    ids=[
        "int",
        "bytes",
        "list",
        "float",
        "nan",
        "numpy-shape-3x1",
        "pandas-series-int",
    ],
)
def test_axis_labels_reject_non_str_titles(ax, labels):
    part = _AxisLabels(ax, labels=("A", "B", "C"))
    before = _snapshot(ax, part)
    with pytest.raises(
        TypeError, match="Each item of `labels` must be a str or None"
    ):
        part.update(labels=labels, fontsize=20)
    _assert_unchanged(ax, part, before)


@pytest.mark.parametrize(
    ("pad", "error"),
    [
        ("0.15", TypeError),
        (True, TypeError),
        (np.bool_(True), TypeError),
        (float("nan"), ValueError),
        (float("inf"), ValueError),
        (-float("inf"), ValueError),
    ],
    ids=repr,
)
def test_axis_labels_reject_invalid_pad(ax, pad, error):
    part = _AxisLabels(ax, labels=("A", "B", "C"))
    before = _snapshot(ax, part)
    with pytest.raises(error, match="`pad`"):
        part.update(pad=pad, fontsize=20)
    _assert_unchanged(ax, part, before)


AXIS_LABEL_INVALID_OPTIONS = [
    ({"labels": ("A", "B")}, ValueError, "`labels` must have 3 items"),
    ({"labels": "ABC"}, TypeError, "`labels` must be a sequence"),
    ({"labels": ("A", 1, None)}, TypeError, "Each item of `labels`"),
    ({"pad": "0.15"}, TypeError, "`pad` must be a real number"),
    ({"pad": float("nan")}, ValueError, "`pad` must be a finite real number"),
]
AXIS_LABEL_INVALID_OPTION_IDS = [
    "labels-count",
    "labels-type",
    "labels-item",
    "pad-type",
    "pad-value",
]


@pytest.mark.parametrize(
    ("kwargs", "error", "match"),
    AXIS_LABEL_INVALID_OPTIONS,
    ids=AXIS_LABEL_INVALID_OPTION_IDS,
)
def test_axis_labels_validate_options_while_invisible(
    ax, kwargs, error, match
):
    # Nothing is drawn, so only the validation step can catch these.
    part = _AxisLabels(ax, labels=("A", "B", "C"), visible=False)
    before = _snapshot(ax, part)
    with pytest.raises(error, match=match):
        part.update(**kwargs)
    _assert_unchanged(ax, part, before)
    with pytest.raises(error, match=match):
        _AxisLabels(ax, visible=False, **kwargs)
    assert list(ax.texts) == []


@pytest.mark.parametrize(
    ("kwargs", "error", "match"),
    AXIS_LABEL_INVALID_OPTIONS,
    ids=AXIS_LABEL_INVALID_OPTION_IDS,
)
def test_axis_labels_invalid_options_at_construction_leave_nothing(
    ax, kwargs, error, match
):
    with pytest.raises(error, match=match):
        _AxisLabels(ax, **{"labels": ("A", "B", "C"), **kwargs})
    assert list(ax.texts) == []


def test_axis_labels_validate_pad_without_titles(ax):
    # No title is drawn, so the position of a title is never computed.
    part = _AxisLabels(ax)
    before = _snapshot(ax, part)
    with pytest.raises(TypeError, match="`pad` must be a real number"):
        part.update(pad="0.15")
    _assert_unchanged(ax, part, before)
    with pytest.raises(ValueError, match="`pad` must be a finite real number"):
        _AxisLabels(ax, pad=float("inf"))
    assert list(ax.texts) == []


# ---------------------------------------------------------------------------
# _VertexLabels
# ---------------------------------------------------------------------------

MATERIALS = ("Li2O", "La2O3", "TiO2")
# MATERIALS in the LaTeX notation of ``get_label``.
MATERIAL_LABELS = ("Li$_{2}$O", "La$_{2}$O$_{3}$", "TiO$_{2}$")
VERTEX_LABEL_OFFSETS = ((0.0, 0.02), (0.0, -0.05), (0.0, -0.05))
NEW_VERTEX_LABEL_OFFSETS = ((0.05, 0.03), (-0.04, -0.02), (0.04, -0.08))
# The top, bottom left and bottom right vertices of the triangle, and the
# horizontal and vertical alignments of their labels, as given by the
# design.
VERTICES = ((0.5, ROOT3_OVER_2), (0.0, 0.0), (1.0, 0.0))
VERTEX_ALIGNMENTS = (("center", "bottom"), ("right", "top"), ("left", "top"))


def _vertex_labels(
    ax, labels: Any = MATERIALS, *, auto_latex_notation: Any = True, **kwargs
) -> _VertexLabels:
    return _VertexLabels(
        ax, auto_latex_notation=auto_latex_notation, labels=labels, **kwargs
    )


def _expected_vertex_label_layout(
    texts: Sequence[str],
    offsets: Sequence[tuple[float, float]] = VERTEX_LABEL_OFFSETS,
) -> list[tuple]:
    """Layout of the vertex labels: top, bottom left and bottom right.

    Each label is at its vertex moved by its offset, not rotated, in the
    form returned by `_tick_layout`.
    """
    return [
        (text, point_key(vx + dx, vy + dy), 0.0, ha, va)
        for text, (vx, vy), (dx, dy), (ha, va) in zip(
            texts, VERTICES, offsets, VERTEX_ALIGNMENTS
        )
    ]


def _assert_labels_stored(part: _VertexLabels, expected: tuple) -> None:
    """The part keeps `expected` as a tuple of 3 built-in str."""
    stored = part._options["labels"]
    assert type(stored) is tuple
    assert stored == expected
    assert all(type(item) is str for item in stored)


def test_vertex_labels_annotations_are_not_evaluated():
    for func in (
        _VertexLabels.__init__,
        _VertexLabels._validate,
        _VertexLabels._specs,
    ):
        annotations = func.__annotations__
        assert annotations
        assert all(isinstance(value, str) for value in annotations.values())


def test_vertex_labels_defaults():
    assert _VertexLabels.OPTION_DEFAULTS == {
        "visible": True,
        # No default labels: they are given at construction.
        "labels": None,
        "offsets": VERTEX_LABEL_OFFSETS,
    }
    assert _VertexLabels.STYLE_DEFAULTS == {"fontsize": VERTEX_LABEL_FONTSIZE}
    assert _VertexLabels.ARTIST_CLASS is matplotlib.text.Text
    assert _skeleton.DEFAULT_VERTEX_LABEL_OFFSETS == VERTEX_LABEL_OFFSETS
    assert _skeleton.DEFAULT_VERTEX_LABEL_FONTSIZE == VERTEX_LABEL_FONTSIZE
    assert _skeleton.DEFAULT_VERTEX_LABEL_STYLES == tuple(
        {"horizontalalignment": ha, "verticalalignment": va}
        for ha, va in VERTEX_ALIGNMENTS
    )


def test_vertex_labels_default_texts_match_v3(ax):
    part = _vertex_labels(ax)
    texts = part.artists

    assert len(texts) == 3
    assert all(isinstance(text, matplotlib.text.Text) for text in texts)
    assert _same_objects(ax.texts, texts)
    assert list(ax.lines) == []
    # Top, bottom left and bottom right, in the LaTeX notation.
    assert [text_key(text) for text in texts] == expected_vertex_label_texts(
        MATERIAL_LABELS
    )
    _assert_labels_stored(part, MATERIALS)


def test_vertex_labels_without_auto_latex_notation_match_v3(ax):
    part = _vertex_labels(ax, auto_latex_notation=False)
    assert [
        text_key(text) for text in part.artists
    ] == expected_vertex_label_texts(MATERIALS)
    _assert_labels_stored(part, MATERIALS)


def test_vertex_labels_accept_dataframe_columns(ax, df_contour):
    # The labels of ``TernaryDiagram(materials=df.columns[:3])``.
    part = _vertex_labels(ax, df_contour.columns[:3])

    _assert_labels_stored(part, ("Li2O", "TiO2", "La2O3"))
    assert [
        text_key(text) for text in part.artists
    ] == expected_vertex_label_texts(
        ("Li$_{2}$O", "TiO$_{2}$", "La$_{2}$O$_{3}$")
    )


@pytest.mark.parametrize(
    ("auto_latex_notation", "formatted"),
    [(1, True), (0, False), (np.bool_(True), True), (np.bool_(False), False)],
    ids=repr,
)
def test_vertex_labels_auto_latex_notation_keeps_v3_truthiness(
    ax, auto_latex_notation, formatted
):
    # ternary-diagram v3 only tests the truth value of the flag.
    part = _vertex_labels(ax, auto_latex_notation=auto_latex_notation)
    assert [text.get_text() for text in part.artists] == list(
        MATERIAL_LABELS if formatted else MATERIALS
    )
    texts = part.update(labels=("Li2O", "B", "C"))
    assert [text.get_text() for text in texts] == [
        "Li$_{2}$O" if formatted else "Li2O",
        "B",
        "C",
    ]


def test_vertex_labels_require_labels_and_auto_latex_notation(ax):
    with pytest.raises(TypeError, match="labels"):
        _VertexLabels(ax, auto_latex_notation=True)
    with pytest.raises(TypeError, match="auto_latex_notation"):
        _VertexLabels(ax, labels=MATERIALS)
    assert list(ax.texts) == []


def test_vertex_labels_reject_none_labels_at_construction(ax):
    # None keeps the previous labels, and there are none at construction.
    with pytest.raises(TypeError, match="`labels` must be a sequence"):
        _vertex_labels(ax, None)
    assert list(ax.texts) == []


def test_vertex_labels_update_formats_new_labels(ax):
    part = _vertex_labels(ax)
    old = part.artists
    texts = part.update(labels=["Li2O", "B", "C"])

    assert [text.get_text() for text in texts] == ["Li$_{2}$O", "B", "C"]
    assert _tick_layout(texts) == _expected_vertex_label_layout(
        ["Li$_{2}$O", "B", "C"]
    )
    assert all(text.get_fontsize() == VERTEX_LABEL_FONTSIZE for text in texts)
    assert _same_objects(ax.texts, texts)
    assert _same_objects(part.artists, texts)
    assert all(text.axes is None for text in old)
    _assert_labels_stored(part, ("Li2O", "B", "C"))


def test_vertex_labels_update_without_auto_latex_notation_keeps_labels(ax):
    part = _vertex_labels(ax, auto_latex_notation=False)
    texts = part.update(labels=["Li2O", "B", "C"])

    assert [text.get_text() for text in texts] == ["Li2O", "B", "C"]
    assert _tick_layout(texts) == _expected_vertex_label_layout(
        ["Li2O", "B", "C"]
    )
    assert _same_objects(ax.texts, texts)


@pytest.mark.parametrize("auto_latex_notation", [True, False])
def test_vertex_labels_auto_latex_notation_is_fixed_at_construction(
    ax, auto_latex_notation
):
    part = _vertex_labels(ax, auto_latex_notation=auto_latex_notation)
    before = _snapshot(ax, part)
    # It is not an option of the part, so matplotlib rejects it as a
    # property of Text.
    with pytest.raises(AttributeError, match="auto_latex_notation"):
        part.update(auto_latex_notation=not auto_latex_notation)
    _assert_unchanged(ax, part, before)


def test_vertex_labels_offsets_move_the_labels(ax):
    part = _vertex_labels(ax)
    old = part.artists
    texts = part.update(offsets=NEW_VERTEX_LABEL_OFFSETS)

    assert _tick_layout(texts) == _expected_vertex_label_layout(
        MATERIAL_LABELS, NEW_VERTEX_LABEL_OFFSETS
    )
    # Each label is its offset away from its vertex.
    for text, (vx, vy), (dx, dy) in zip(
        texts, VERTICES, NEW_VERTEX_LABEL_OFFSETS
    ):
        x, y = text.get_position()
        assert (x - vx, y - vy) == pytest.approx((dx, dy))
    assert _same_objects(ax.texts, texts)
    assert all(text.axes is None for text in old)


def test_vertex_labels_offsets_at_construction(ax):
    texts = _vertex_labels(ax, offsets=NEW_VERTEX_LABEL_OFFSETS).artists
    assert _tick_layout(texts) == _expected_vertex_label_layout(
        MATERIAL_LABELS, NEW_VERTEX_LABEL_OFFSETS
    )


@pytest.mark.parametrize(
    ("offsets", "expected"),
    [
        (
            [list(pair) for pair in NEW_VERTEX_LABEL_OFFSETS],
            NEW_VERTEX_LABEL_OFFSETS,
        ),
        (np.array(NEW_VERTEX_LABEL_OFFSETS), NEW_VERTEX_LABEL_OFFSETS),
        (
            ((0, 1), (np.int64(-1), np.float32(0.5)), (Fraction(1, 4), -2)),
            ((0.0, 1.0), (-1.0, 0.5), (0.25, -2.0)),
        ),
        (((0, 0), (0, 0), (0, 0)), ((0.0, 0.0),) * 3),
    ],
    ids=["list-of-lists", "numpy-3x2", "mixed-reals", "zeros"],
)
def test_vertex_labels_accept_offsets_of_3_pairs_of_reals(
    ax, offsets, expected
):
    part = _vertex_labels(ax, offsets=offsets)

    stored = part._options["offsets"]
    assert stored == expected
    # Kept as built-in floats, so that later changes to the given object
    # have no effect.
    assert type(stored) is tuple
    assert all(type(pair) is tuple for pair in stored)
    assert all(type(value) is float for pair in stored for value in pair)
    assert _tick_layout(part.artists) == _expected_vertex_label_layout(
        MATERIAL_LABELS, expected
    )


def test_vertex_labels_accept_a_generator_of_offsets(ax):
    part = _vertex_labels(
        ax, offsets=(pair for pair in NEW_VERTEX_LABEL_OFFSETS)
    )
    assert part._options["offsets"] == NEW_VERTEX_LABEL_OFFSETS
    # Redrawing uses the stored offsets, not the exhausted generator.
    texts = part.update(fontsize=14)
    assert _tick_layout(texts) == _expected_vertex_label_layout(
        MATERIAL_LABELS, NEW_VERTEX_LABEL_OFFSETS
    )


def test_vertex_labels_keep_a_copy_of_the_offsets(ax):
    offsets = np.array(NEW_VERTEX_LABEL_OFFSETS)
    part = _vertex_labels(ax, offsets=offsets)
    offsets[0] = (9.0, 9.0)
    texts = part.update(fontsize=14)
    assert _tick_layout(texts) == _expected_vertex_label_layout(
        MATERIAL_LABELS, NEW_VERTEX_LABEL_OFFSETS
    )


def test_vertex_labels_keep_offsets_when_labels_change(ax):
    part = _vertex_labels(ax, offsets=NEW_VERTEX_LABEL_OFFSETS, fontsize=20)
    texts = part.update(labels=("A", "B", "C"))

    assert _tick_layout(texts) == _expected_vertex_label_layout(
        ("A", "B", "C"), NEW_VERTEX_LABEL_OFFSETS
    )
    assert all(text.get_fontsize() == 20 for text in texts)


def test_vertex_labels_keep_labels_when_offsets_change(ax):
    part = _vertex_labels(ax, ("A2", "B", "C"))
    texts = part.update(labels=None, offsets=NEW_VERTEX_LABEL_OFFSETS)

    # The stored labels are converted again with the same setting.
    assert _tick_layout(texts) == _expected_vertex_label_layout(
        ("A$_{2}$", "B", "C"), NEW_VERTEX_LABEL_OFFSETS
    )


def test_vertex_labels_keep_options_when_only_style_changes(ax):
    part = _vertex_labels(
        ax, ("A", "B", "C"), offsets=NEW_VERTEX_LABEL_OFFSETS
    )
    texts = part.update(color="red")

    assert _tick_layout(texts) == _expected_vertex_label_layout(
        ("A", "B", "C"), NEW_VERTEX_LABEL_OFFSETS
    )
    assert all(to_rgba(text.get_color()) == to_rgba("red") for text in texts)


@pytest.mark.parametrize(
    "kwargs",
    [{"fontsize": 20, "color": "red"}, {"size": 20, "c": "red"}],
    ids=["canonical", "aliases"],
)
def test_vertex_labels_style_applies_to_all_labels(ax, kwargs):
    texts = _vertex_labels(ax).update(**kwargs)

    assert len(texts) == 3
    assert all(text.get_fontsize() == 20 for text in texts)
    assert all(to_rgba(text.get_color()) == to_rgba("red") for text in texts)
    # The positions and the alignments are kept.
    assert _tick_layout(texts) == _expected_vertex_label_layout(
        MATERIAL_LABELS
    )


def test_vertex_labels_style_at_construction(ax):
    texts = _vertex_labels(ax, fontsize=20).artists
    assert len(texts) == 3
    assert all(text.get_fontsize() == 20 for text in texts)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ha": "left", "va": "center"},
        {"horizontalalignment": "left", "verticalalignment": "center"},
    ],
    ids=["aliases", "canonical"],
)
def test_vertex_labels_user_alignments_override_vertex_defaults(ax, kwargs):
    texts = _vertex_labels(ax).update(**kwargs)

    # The same value applies to the labels of every vertex.
    assert all(text.get_horizontalalignment() == "left" for text in texts)
    assert all(text.get_verticalalignment() == "center" for text in texts)
    # The positions do not change.
    assert [text_key(text).position for text in texts] == [
        key[1] for key in _expected_vertex_label_layout(MATERIAL_LABELS)
    ]


def test_vertex_labels_keep_matplotlib_default_zorder(ax):
    part = _vertex_labels(ax)
    assert all(text.get_zorder() == TEXT_ZORDER for text in part.artists)
    texts = part.update(offsets=NEW_VERTEX_LABEL_OFFSETS, fontsize=8)
    assert len(texts) == 3
    assert all(text.get_zorder() == TEXT_ZORDER for text in texts)


def test_vertex_labels_user_zorder_overrides_default(ax):
    texts = _vertex_labels(ax).update(zorder=5)
    assert len(texts) == 3
    assert all(text.get_zorder() == 5 for text in texts)


def test_vertex_labels_invisible_at_construction_draws_nothing(ax):
    part = _vertex_labels(ax, visible=False)
    assert part.artists == []
    assert list(ax.texts) == []


def test_vertex_labels_invisible_removes_labels_and_visible_restores_them(ax):
    part = _vertex_labels(
        ax, ("A2", "B", "C"), offsets=NEW_VERTEX_LABEL_OFFSETS, size=20
    )
    old = part.artists
    assert len(old) == 3
    assert part.update(visible=False) == []
    assert part.artists == []
    assert list(ax.texts) == []
    assert all(text.axes is None for text in old)

    # The settings given before hiding the labels are used again.
    texts = part.update(visible=True)
    assert _tick_layout(texts) == _expected_vertex_label_layout(
        ("A$_{2}$", "B", "C"), NEW_VERTEX_LABEL_OFFSETS
    )
    assert all(text.get_fontsize() == 20 for text in texts)


@pytest.mark.parametrize(
    "labels",
    [
        list(MATERIALS),
        pd.Index(MATERIALS),
        pd.Series(MATERIALS),
        np.array(MATERIALS),
        np.array(MATERIALS, dtype=object),
    ],
    ids=["list", "pandas-index", "pandas-series", "numpy-str", "numpy-object"],
)
@pytest.mark.parametrize("auto_latex_notation", [True, False])
def test_vertex_labels_accept_ordered_iterables(
    ax, labels, auto_latex_notation
):
    part = _vertex_labels(
        ax, labels=labels, auto_latex_notation=auto_latex_notation
    )

    # str subclasses such as numpy.str_ are kept as the built-in str.
    _assert_labels_stored(part, MATERIALS)
    expected = MATERIAL_LABELS if auto_latex_notation else MATERIALS
    assert _tick_layout(part.artists) == _expected_vertex_label_layout(
        expected
    )
    assert _same_objects(ax.texts, part.artists)


def test_vertex_labels_accept_a_generator_consumed_once(ax):
    part = _vertex_labels(ax, (material for material in MATERIALS))
    _assert_labels_stored(part, MATERIALS)

    # Redrawing uses the stored labels, not the exhausted generator.
    texts = part.update(fontsize=14)
    assert [text.get_text() for text in texts] == list(MATERIAL_LABELS)


def test_vertex_labels_keep_a_copy_of_the_labels(ax):
    labels = ["A", "B", "C"]
    part = _vertex_labels(ax, labels)
    # Changing the given list afterwards does not change the part.
    labels[1] = "X"
    _assert_labels_stored(part, ("A", "B", "C"))
    texts = part.update(fontsize=14)
    assert [text.get_text() for text in texts] == ["A", "B", "C"]


@pytest.mark.parametrize(
    "labels",
    [
        (1, 2.5, None),
        (b"A", ["B"], np.float64(0.5)),
        pd.Index([1, 2, 3]),
        ("Li2O", None, ""),
    ],
    ids=["numbers-and-none", "other-objects", "pandas-index-int", "str"],
)
def test_vertex_labels_show_any_object_without_auto_latex_notation(ax, labels):
    # ternary-diagram v3 passes the materials to ``Axes.text`` as they are,
    # which shows ``str(label)``, or "" for None.
    expected = tuple(
        matplotlib.text.Text(0, 0, label).get_text() for label in labels
    )
    part = _vertex_labels(ax, labels, auto_latex_notation=False)

    _assert_labels_stored(part, expected)
    assert _tick_layout(part.artists) == _expected_vertex_label_layout(
        expected
    )


@pytest.mark.parametrize(
    "labels",
    [
        ("Li2O", 1, "TiO2"),
        (None, "B", "C"),
        ("A", "B", b"C"),
        ("A", "B", ["C"]),
        ("A", "B", float("nan")),
        pd.Index([1, 2, 3]),
        np.array(["A", None, "C"], dtype=object),
    ],
    ids=[
        "int",
        "none",
        "bytes",
        "list",
        "nan",
        "pandas-index-int",
        "numpy-object-none",
    ],
)
def test_vertex_labels_reject_non_str_labels_with_auto_latex_notation(
    ax, labels
):
    part = _vertex_labels(ax, ("A", "B", "C"))
    before = _snapshot(ax, part)
    non_str = next(label for label in labels if not isinstance(label, str))
    with pytest.raises(ValueError) as expected:
        get_label(non_str)

    with pytest.raises(ValueError) as excinfo:
        part.update(labels=labels, fontsize=20)
    # The same error as ``get_label``, as in ternary-diagram v3.
    assert type(excinfo.value) is ValueError
    assert str(excinfo.value) == str(expected.value)
    _assert_unchanged(ax, part, before)

    with pytest.raises(ValueError, match=str(expected.value)):
        _vertex_labels(ax, labels)
    assert _same_objects(ax.texts, before["children"])


@pytest.mark.parametrize(
    "labels",
    [
        ("A", "B"),
        ("A", "B", "C", "D"),
        (),
        np.array(["A", "B"]),
        pd.Index(["A", "B", "C", "D"]),
    ],
    ids=["tuple-2", "tuple-4", "empty", "numpy-2", "pandas-index-4"],
)
@pytest.mark.parametrize("auto_latex_notation", [True, False])
def test_vertex_labels_reject_wrong_number_of_labels(
    ax, labels, auto_latex_notation
):
    part = _vertex_labels(ax, auto_latex_notation=auto_latex_notation)
    before = _snapshot(ax, part)
    with pytest.raises(
        ValueError, match="`labels` must have 3 items, one label per vertex"
    ):
        part.update(labels=labels, fontsize=20)
    _assert_unchanged(ax, part, before)


@pytest.mark.parametrize(
    "labels",
    [
        "ABC",
        np.str_("ABC"),
        b"ABC",
        3,
        3.0,
        {"A", "B", "C"},
        frozenset({"A", "B", "C"}),
        {"A": 0, "B": 1, "C": 2},
        np.array("ABC"),
    ],
    ids=[
        "str",
        "numpy-str",
        "bytes",
        "int",
        "float",
        "set",
        "frozenset",
        "dict",
        "numpy-0d",
    ],
)
@pytest.mark.parametrize("auto_latex_notation", [True, False])
def test_vertex_labels_reject_non_sequence_labels(
    ax, labels, auto_latex_notation
):
    part = _vertex_labels(ax, auto_latex_notation=auto_latex_notation)
    before = _snapshot(ax, part)
    # The same kinds of containers as the axis titles; the message names
    # the accepted types.
    with pytest.raises(
        TypeError,
        match=(
            "`labels` must be a sequence of 3 labels such as a list, a "
            "tuple, a numpy array or a pandas Index"
        ),
    ):
        part.update(labels=labels, fontsize=20)
    _assert_unchanged(ax, part, before)


def test_vertex_labels_reject_0d_array_from_the_iteration_error(ax):
    part = _vertex_labels(ax)
    before = _snapshot(ax, part)
    with pytest.raises(
        TypeError, match="`labels` must be a sequence .* iterating over"
    ) as excinfo:
        part.update(labels=np.array("ABC"))
    # The error of numpy is kept as the cause.
    assert isinstance(excinfo.value.__cause__, TypeError)
    _assert_unchanged(ax, part, before)


def test_vertex_labels_reject_a_generator_of_wrong_length(ax):
    part = _vertex_labels(ax)
    before = _snapshot(ax, part)
    with pytest.raises(ValueError, match="`labels` must have 3 items"):
        part.update(labels=(label for label in ("A", "B")))
    _assert_unchanged(ax, part, before)


_OFFSETS_COUNT = "`offsets` must have 3 items, one offset per vertex"
_OFFSETS_TYPE = (
    "`offsets` must be a sequence of 3 offsets \\(dx, dy\\) such as a list, "
    "a tuple or a numpy array of shape \\(3, 2\\)"
)


@pytest.mark.parametrize(
    ("offsets", "error", "match"),
    [
        (((0, 0.02), (0, -0.05)), ValueError, _OFFSETS_COUNT),
        (((0, 0.02),) * 4, ValueError, _OFFSETS_COUNT),
        ((), ValueError, _OFFSETS_COUNT),
        (np.zeros((2, 2)), ValueError, _OFFSETS_COUNT),
        (np.zeros((3, 3)), ValueError, r"`offsets\[0\]` must have 2 items"),
        (
            ((0, 0.02), (0, -0.05, 0), (0, -0.05)),
            ValueError,
            r"`offsets\[1\]` must have 2 items, dx and dy",
        ),
        (
            ((0, 0.02), (0, -0.05), (0,)),
            ValueError,
            r"`offsets\[2\]` must have 2 items, dx and dy",
        ),
        ("abc", TypeError, _OFFSETS_TYPE),
        (0.1, TypeError, _OFFSETS_TYPE),
        ({"a": (0, 0), "b": (0, 0), "c": (0, 0)}, TypeError, _OFFSETS_TYPE),
        ({(0, 0), (1, 1), (2, 2)}, TypeError, _OFFSETS_TYPE),
        (np.array(0.1), TypeError, "iterating over"),
        ((0.1, 0.2, 0.3), TypeError, r"`offsets\[0\]` must be a pair"),
        (np.zeros(3), TypeError, r"`offsets\[0\]` must be a pair"),
        (
            ((0, 0.02), "ab", (0, -0.05)),
            TypeError,
            r"`offsets\[1\]` must be a pair",
        ),
        (
            ((0, 0.02), {"dx": 0, "dy": 0}, (0, -0.05)),
            TypeError,
            r"`offsets\[1\]` must be a pair",
        ),
        (
            ((0, 0.02), (0, "-0.05"), (0, -0.05)),
            TypeError,
            r"`offsets\[1\]\[1\]` must be a real number",
        ),
        (
            ((True, 0.02), (0, -0.05), (0, -0.05)),
            TypeError,
            r"`offsets\[0\]\[0\]` must be a real number",
        ),
        (
            ((0, 0.02), (0, -0.05), (np.bool_(False), -0.05)),
            TypeError,
            r"`offsets\[2\]\[0\]` must be a real number",
        ),
        (
            ((0, None), (0, -0.05), (0, -0.05)),
            TypeError,
            r"`offsets\[0\]\[1\]` must be a real number",
        ),
        (
            ((0, 0.02), (0, 1j), (0, -0.05)),
            TypeError,
            r"`offsets\[1\]\[1\]` must be a real number",
        ),
        (
            ((0, float("nan")), (0, -0.05), (0, -0.05)),
            ValueError,
            r"`offsets\[0\]\[1\]` must be a finite real number",
        ),
        (
            ((0, 0.02), (float("inf"), -0.05), (0, -0.05)),
            ValueError,
            r"`offsets\[1\]\[0\]` must be a finite real number",
        ),
        (
            ((0, 0.02), (0, -0.05), (0, -float("inf"))),
            ValueError,
            r"`offsets\[2\]\[1\]` must be a finite real number",
        ),
        (
            ((0, 0.02), (0, -0.05), (0, 10**400)),
            ValueError,
            r"`offsets\[2\]\[1\]` must be a finite real number",
        ),
        (
            np.array([[0, 0.02], [0, np.nan], [0, -0.05]]),
            ValueError,
            r"`offsets\[1\]\[1\]` must be a finite real number",
        ),
    ],
    ids=[
        "count-2",
        "count-4",
        "empty",
        "numpy-2x2",
        "numpy-3x3",
        "pair-of-3",
        "pair-of-1",
        "str",
        "float",
        "dict",
        "set",
        "numpy-0d",
        "flat-floats",
        "numpy-flat",
        "pair-str",
        "pair-dict",
        "value-str",
        "value-bool",
        "value-numpy-bool",
        "value-none",
        "value-complex",
        "value-nan",
        "value-inf",
        "value-minus-inf",
        "value-huge-int",
        "numpy-nan",
    ],
)
def test_vertex_labels_reject_invalid_offsets(ax, offsets, error, match):
    part = _vertex_labels(ax)
    before = _snapshot(ax, part)
    with pytest.raises(error, match=match):
        part.update(offsets=offsets, fontsize=20)
    _assert_unchanged(ax, part, before)


VERTEX_LABEL_INVALID_OPTIONS = [
    ({"labels": ("A", "B")}, ValueError, "`labels` must have 3 items"),
    ({"labels": "ABC"}, TypeError, "`labels` must be a sequence"),
    ({"labels": ("A", 1, "C")}, ValueError, "The `compound_name` must be"),
    (
        {"offsets": ((0, 0.02), (0, -0.05))},
        ValueError,
        "`offsets` must have 3 items",
    ),
    ({"offsets": "abc"}, TypeError, "`offsets` must be a sequence"),
    (
        {"offsets": ((0, 0.02), (0, "x"), (0, 0))},
        TypeError,
        "must be a real number",
    ),
    (
        {"offsets": ((0, 0.02), (0, float("nan")), (0, 0))},
        ValueError,
        "must be a finite real number",
    ),
]
VERTEX_LABEL_INVALID_OPTION_IDS = [
    "labels-count",
    "labels-type",
    "labels-item",
    "offsets-count",
    "offsets-type",
    "offsets-item-type",
    "offsets-item-value",
]


@pytest.mark.parametrize(
    ("kwargs", "error", "match"),
    VERTEX_LABEL_INVALID_OPTIONS,
    ids=VERTEX_LABEL_INVALID_OPTION_IDS,
)
def test_vertex_labels_validate_options_while_invisible(
    ax, kwargs, error, match
):
    # Nothing is drawn, so only the validation step can catch these.
    part = _vertex_labels(ax, visible=False)
    before = _snapshot(ax, part)
    with pytest.raises(error, match=match):
        part.update(**kwargs)
    _assert_unchanged(ax, part, before)
    with pytest.raises(error, match=match):
        _VertexLabels(
            ax,
            auto_latex_notation=True,
            visible=False,
            **{"labels": MATERIALS, **kwargs},
        )
    assert list(ax.texts) == []


@pytest.mark.parametrize(
    ("kwargs", "error", "match"),
    VERTEX_LABEL_INVALID_OPTIONS,
    ids=VERTEX_LABEL_INVALID_OPTION_IDS,
)
def test_vertex_labels_invalid_options_at_construction_leave_nothing(
    ax, kwargs, error, match
):
    with pytest.raises(error, match=match):
        _VertexLabels(
            ax, auto_latex_notation=True, **{"labels": MATERIALS, **kwargs}
        )
    assert list(ax.texts) == []
