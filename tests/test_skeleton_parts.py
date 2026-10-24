"""Unit tests of the skeleton parts in ``ternary_diagram._skeleton``."""

from __future__ import annotations

import typing
from collections import Counter
from typing import Any

import matplotlib
import matplotlib.lines
import matplotlib.text
import numpy as np
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
    expected_border_lines,
    expected_grid_lines,
    expected_tick_label_texts,
    line_key,
    point_key,
    text_key,
)
from matplotlib.colors import to_rgba

from ternary_diagram import _skeleton
from ternary_diagram._skeleton import (
    Spec,
    _Border,
    _Grid,
    _LineSpec,
    _SkeletonPart,
    _TextSpec,
    _TickLabels,
)
from ternary_diagram.utils import (
    get_edge_points,
    get_grid_segments,
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
