"""Unit tests of the skeleton parts in ``ternary_diagram._skeleton``."""

from __future__ import annotations

import typing
from typing import Any

import matplotlib
import matplotlib.lines
import matplotlib.text
import numpy as np
import pytest
from matplotlib.colors import to_rgba

from ternary_diagram import _skeleton
from ternary_diagram._skeleton import (
    Spec,
    _LineSpec,
    _SkeletonPart,
    _TextSpec,
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
