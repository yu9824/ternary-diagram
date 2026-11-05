"""Parts of the skeleton of a ternary diagram.

The skeleton is what ``TernaryDiagram`` draws before any plotting call:
the border, the grid, the tick labels, the axis titles and the vertex
labels. Each part keeps its settings and the artists it drew, so that it
can redraw itself with new settings and remove only its own artists.

``_SkeletonPart`` holds the procedure shared by all parts: merge the new
settings with the previous ones, validate them, compute the specs of the
artists as plain values, create the artists and, only when all of them were
created, remove the previous artists. Each part only defines its defaults,
its validation and the computation of its specs.

This module may import ``ternary_diagram.utils`` but not
``ternary_diagram._api``: values owned by ``_api`` (such as the zorder of
the lines) are passed as arguments.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence, Set
from math import isfinite, sqrt
from numbers import Real
from typing import Any, ClassVar, Literal, NamedTuple, Union, cast, get_args

import matplotlib.artist
import matplotlib.axes
import matplotlib.lines
import matplotlib.text
from matplotlib import cbook
from matplotlib.artist import ArtistInspector

from ternary_diagram.utils import (
    check_bool,
    get_axis_label_position,
    get_edge_points,
    get_grid_segments,
    get_label,
    get_tick_formatter,
    get_tick_values,
)

__all__ = ("PartName", "Spec")

# Height of the triangle whose edges have length 1.
ROOT3_OVER_2 = sqrt(3.0) / 2.0

# Defaults of the border (``_Border``), the same as ternary-diagram v3.
DEFAULT_BORDER_COLOR = "black"
DEFAULT_BORDER_LINEWIDTH = 2
DEFAULT_BORDER_LINESTYLE = "-"

# Defaults of the grid (``_Grid``), the same as ternary-diagram v3. The
# linestyle is left to matplotlib, as v3 does not set it.
DEFAULT_GRID_STEP = 0.1
DEFAULT_GRID_COLOR = "gray"
DEFAULT_GRID_LINEWIDTH = 0.5

# Defaults of the tick labels (``_TickLabels``), the same as
# ternary-diagram v3.
DEFAULT_TICK_STEP = 0.1
DEFAULT_TICK_FORMAT = "percent"
DEFAULT_TICK_ENDPOINTS = False
DEFAULT_TICK_FONTSIZE = 10
# Offsets of the tick labels from their points on the edges, for the
# components 0 (right edge), 1 (left edge) and 2 (bottom edge).
DEFAULT_TICK_OFFSETS: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (-0.01, 0.04),
    (0.02, 0.0),
)
# Alignments and rotations of the tick labels for the same components, with
# canonical names. The style of the part overrides them on every edge.
DEFAULT_TICK_EDGE_STYLES: tuple[dict[str, Any], ...] = (
    {"verticalalignment": "bottom", "horizontalalignment": "left"},
    {
        "rotation": 300,
        "verticalalignment": "top",
        "horizontalalignment": "right",
    },
    {
        "rotation": 60,
        "verticalalignment": "top",
        "horizontalalignment": "right",
    },
)

# Defaults of the axis titles (``_AxisLabels``), which ternary-diagram v3
# does not draw: no titles, centered at 0.15 from the midpoints of their
# edges (checked by eye on the example figures to clear the tick labels).
DEFAULT_AXIS_LABELS: tuple[str | None, ...] = (None, None, None)
DEFAULT_AXIS_LABEL_PAD = 0.15
DEFAULT_AXIS_LABEL_FONTSIZE = 12
DEFAULT_AXIS_LABEL_HORIZONTALALIGNMENT = "center"
DEFAULT_AXIS_LABEL_VERTICALALIGNMENT = "center"

# Defaults of the vertex labels (``_VertexLabels``), the same as
# ternary-diagram v3. The labels themselves have no default: they are the
# materials given to ``TernaryDiagram``.
DEFAULT_VERTEX_LABEL_FONTSIZE = 16
# Offsets of the labels from the top, bottom left and bottom right vertices,
# where each edge has length 1.
DEFAULT_VERTEX_LABEL_OFFSETS: tuple[tuple[float, float], ...] = (
    (0.0, 0.02),
    (0.0, -0.05),
    (0.0, -0.05),
)
# Alignments of the labels of the same vertices, with canonical names. The
# style of the part overrides them on every vertex.
DEFAULT_VERTEX_LABEL_STYLES: tuple[dict[str, Any], ...] = (
    {"horizontalalignment": "center", "verticalalignment": "bottom"},
    {"horizontalalignment": "right", "verticalalignment": "top"},
    {"horizontalalignment": "left", "verticalalignment": "top"},
)


class _LineSpec(NamedTuple):
    """Spec of a line drawn with ``Axes.plot(xdata, ydata, **kwargs)``."""

    xdata: Sequence[float]
    ydata: Sequence[float]
    kwargs: dict[str, Any]
    """Properties of ``Line2D`` with canonical names."""


class _TextSpec(NamedTuple):
    """Spec of a text drawn with ``Axes.text(x, y, s, **kwargs)``."""

    x: float
    y: float
    s: str
    kwargs: dict[str, Any]
    """Properties of ``Text`` with canonical names."""


# Evaluated at runtime, so ``|`` cannot be used on Python 3.9.
Spec = Union[_LineSpec, _TextSpec]

# Names of the parts of the skeleton, by which ``_Skeleton`` updates them
# and returns their artists.
PartName = Literal["border", "grid", "ticks", "axis_labels", "vertex_labels"]
_PART_NAMES: tuple[str, ...] = get_args(PartName)


def _normalize_kwargs_accepts_artist() -> bool:
    """Tell whether ``cbook.normalize_kwargs`` takes an Artist class.

    Old matplotlib only takes a dict that maps each canonical name to its
    aliases, and fails on an Artist class.
    """
    try:
        normalized = cbook.normalize_kwargs({"lw": 1}, matplotlib.lines.Line2D)
    except (AttributeError, TypeError):
        return False
    return normalized == {"linewidth": 1}


_NORMALIZE_KWARGS_ACCEPTS_ARTIST: bool = _normalize_kwargs_accepts_artist()


def _alias_mapping(
    artist_class: type[matplotlib.artist.Artist],
) -> dict[str, list[str]]:
    """Map each canonical property name of an Artist class to its aliases.

    ``ArtistInspector.get_aliases`` also reports one-way aliases: a setter
    that forwards to another setter while its name is a property of its
    own, with a real getter and aliases of its own (such as ``fontname`` of
    ``Text``, whose setter forwards to ``set_fontfamily``). They are left
    out, so that the result matches the mapping that matplotlib uses for an
    Artist class.

    Parameters
    ----------
    artist_class : type[matplotlib.artist.Artist]
        Artist class whose aliases are collected.

    Returns
    -------
    dict[str, list[str]]
        Mapping in the dict form accepted by ``cbook.normalize_kwargs``.
    """
    inspector = ArtistInspector(artist_class)
    aliases = inspector.get_aliases()

    def is_one_way(alias: str) -> bool:
        getter = getattr(artist_class, f"get_{alias}", None)
        return (
            alias in aliases
            and getter is not None
            and not inspector.is_alias(getter)
        )

    mapping: dict[str, list[str]] = {}
    for name, names in aliases.items():
        two_way = sorted(alias for alias in names if not is_one_way(alias))
        if two_way:
            mapping[name] = two_way
    return mapping


def _normalize_style(
    style: dict[str, Any], artist_class: type[matplotlib.artist.Artist]
) -> dict[str, Any]:
    """Rename the aliases of matplotlib properties to their canonical names.

    Parameters
    ----------
    style : dict[str, Any]
        Properties of `artist_class`, possibly given by their aliases (such
        as ``lw`` for ``linewidth``).
    artist_class : type[matplotlib.artist.Artist]
        Artist class that the properties belong to.

    Returns
    -------
    dict[str, Any]
        A new dict with the same properties under their canonical names.
        Names that are not aliases are kept as they are.

    Raises
    ------
    TypeError
        If an alias and its canonical name (or two aliases of the same
        property) are both given. Raised by matplotlib.
    """
    if _NORMALIZE_KWARGS_ACCEPTS_ARTIST:
        return cbook.normalize_kwargs(dict(style), artist_class)
    # The dict form is deprecated since matplotlib 3.11, whose stubs reject
    # it, but it is the only form that old matplotlib accepts. The stubs of
    # matplotlib 3.10 accept it, hence also "unused-ignore".
    return cbook.normalize_kwargs(
        dict(style),
        _alias_mapping(artist_class),  # type: ignore[arg-type, unused-ignore]
    )


# Properties that ``_SkeletonPart`` gives itself to the call that creates
# each artist: ``Axes.plot(xdata, ydata, ...)`` and ``Axes.text(x, y, s,
# ...)``. Given again in the style, matplotlib raises TypeError ("got
# multiple values") whatever their values.
_PROPERTIES_SET_BY_THE_PART: tuple[
    tuple[type[matplotlib.artist.Artist], frozenset[str]], ...
] = (
    (matplotlib.lines.Line2D, frozenset({"xdata", "ydata"})),
    (matplotlib.text.Text, frozenset({"x", "y", "text"})),
)


def _check_style_names(
    style: Mapping[str, Any], artist_class: type[matplotlib.artist.Artist]
) -> None:
    """Check that the artists can be created with these property names.

    matplotlib only rejects a name when it creates an artist, which never
    happens while a part draws nothing (for example while it is invisible).
    Checking the names first keeps a part from storing a name that would
    make every later redraw fail, and raises the same type of error as
    matplotlib does when the artists are created.

    Parameters
    ----------
    style : Mapping[str, Any]
        Properties with canonical names, as returned by `_normalize_style`.
    artist_class : type[matplotlib.artist.Artist]
        Artist class that the properties belong to.

    Raises
    ------
    AttributeError
        If a name is not a property of `artist_class`, that is, the class
        has no setter ``set_<name>``, with the message of ``Artist.set``.
    TypeError
        If a name is a property that the part sets for each artist: the
        data of a ``Line2D`` or the position and the string of a ``Text``.
    """
    set_by_the_part = frozenset(
        name
        for owner, names in _PROPERTIES_SET_BY_THE_PART
        if issubclass(artist_class, owner)
        for name in names
    )
    for name in style:
        if not callable(getattr(artist_class, f"set_{name}", None)):
            raise AttributeError(
                f"{artist_class.__name__}.set() got an unexpected keyword "
                f"argument {name!r}"
            )
        if name in set_by_the_part:
            raise TypeError(
                f"{artist_class.__name__} property {name!r} cannot be given: "
                f"it is set by the part for each artist."
            )


def _attached(
    artists: Sequence[matplotlib.artist.Artist], ax: matplotlib.axes.Axes
) -> list[matplotlib.artist.Artist]:
    """Return the artists that are still children of `ax`, in their order.

    An artist of a part leaves the Axes when the user removes it
    (``Artist.remove``) or clears the Axes (``Axes.cla``). Such an artist
    can be neither removed again nor moved, so it is skipped.

    Parameters
    ----------
    artists : Sequence[matplotlib.artist.Artist]
        Artists drawn by a part.
    ax : matplotlib.axes.Axes
        Axes the part draws on.

    Returns
    -------
    list[matplotlib.artist.Artist]
        The artists of `artists` found among the children of `ax`.
    """
    children = {id(child) for child in ax.get_children()}
    return [artist for artist in artists if id(artist) in children]


def _ordered_items(
    value: object, count: int, name: str, accepted: str, each: str
) -> tuple[Any, ...]:
    """Turn an ordered iterable of `count` items into a tuple.

    Shared by the options that take one item per component, per vertex or
    per coordinate, so that they accept the same kinds of containers: any
    ordered iterable, such as a list, a tuple, a numpy array, a pandas Index
    or Series, or a generator, which is consumed once. The items themselves
    are not checked.

    Parameters
    ----------
    value : object
        The value given to the option.
    count : int
        Number of items that `value` must have.
    name : str
        Name of the option in the messages, such as ``labels``.
    accepted : str
        Description of the accepted values in the messages of TypeError,
        completing "`name` must be ...".
    each : str
        Meaning of the items in the message of ValueError, completing
        "`name` must have `count` items, ...", such as "one title per
        component".

    Returns
    -------
    tuple[Any, ...]
        The `count` items of `value`, in order.

    Raises
    ------
    TypeError
        If `value` is a str, bytes, a mapping, a set or not iterable, or if
        iterating over it fails with a TypeError (such as a 0-d numpy array,
        whose error is kept as the cause).
    ValueError
        If `value` does not have `count` items.
    """
    if isinstance(value, (str, bytes, Mapping, Set)) or not isinstance(
        value, Iterable
    ):
        raise TypeError(f"`{name}` must be {accepted}, but got {value!r}.")
    try:
        items = tuple(value)
    except TypeError as error:
        raise TypeError(
            f"`{name}` must be {accepted}, but iterating over {value!r} "
            f"failed: {error}"
        ) from error
    if len(items) != count:
        raise ValueError(
            f"`{name}` must have {count} items, {each}, but got "
            f"{len(items)}: {value!r}."
        )
    return items


def _finite_real(value: object, name: str) -> float:
    """Check that `value` is a finite real number, with the rules of ``pad``.

    Parameters
    ----------
    value : object
        The value to check.
    name : str
        Name of the value in the messages.

    Returns
    -------
    float
        `value` as a built-in float.

    Raises
    ------
    TypeError
        If `value` is not a real number (``bool`` and ``numpy.bool_`` are
        rejected).
    ValueError
        If `value` is not finite, including an int too large for a float.
    """
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"`{name}` must be a real number, but got {value!r}.")
    try:
        number = float(value)
    except OverflowError:
        # An int or a Fraction too large for a float
        number = float("inf")
    if not isfinite(number):
        raise ValueError(
            f"`{name}` must be a finite real number, but got {value!r}."
        )
    return number


class _SkeletonPart(ABC):
    """Common procedure of a part of the skeleton.

    A part keeps two kinds of settings. Options are the named items of the
    part (``visible``, ``step``, ...); ``None`` given to an option keeps its
    previous value. The style holds the matplotlib properties of the
    artists of the part, under their canonical names; properties given by
    a call override the previous ones, which start from the defaults.

    Subclasses define `OPTION_DEFAULTS`, `STYLE_DEFAULTS` and
    `ARTIST_CLASS`, implement `_specs`, and override `_validate` when they
    have options other than ``visible``.

    Attributes
    ----------
    OPTION_DEFAULTS : dict[str, Any]
        Initial values of the options. It must contain ``"visible": True``.
        A keyword whose name is a key of this dict is an option, any other
        keyword is a property of `ARTIST_CLASS`.
    STYLE_DEFAULTS : dict[str, Any]
        Default properties of the artists. The zorder given at construction
        is added to them.
    ARTIST_CLASS : type[matplotlib.artist.Artist]
        Class of the artists of the part: ``Line2D`` or ``Text``.
    """

    OPTION_DEFAULTS: ClassVar[dict[str, Any]]
    STYLE_DEFAULTS: ClassVar[dict[str, Any]]
    ARTIST_CLASS: ClassVar[type[matplotlib.artist.Artist]]

    def __init__(
        self,
        ax: matplotlib.axes.Axes,
        *,
        zorder: float | None = None,
        **initial: Any,
    ) -> None:
        """Draw the part once with the initial settings.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            Axes to draw on.
        zorder : float or None, optional
            Default zorder of the artists, added to `STYLE_DEFAULTS`. Line
            parts receive it from the caller; text parts leave it to
            matplotlib, by default None
        **initial
            Initial options and properties, merged with the defaults in the
            same way as by `update`.

        Raises
        ------
        TypeError, ValueError, AttributeError
            Raised by `update` for invalid initial settings. Nothing is left
            on `ax` in that case.
        """
        self._ax = ax
        style = _normalize_style(self.STYLE_DEFAULTS, self.ARTIST_CLASS)
        if zorder is not None:
            style["zorder"] = zorder
        self._options: dict[str, Any] = dict(self.OPTION_DEFAULTS)
        self._style: dict[str, Any] = style
        self._artists: list[matplotlib.artist.Artist] = []
        self.update(**initial)

    def update(self, **kwargs: Any) -> list[matplotlib.artist.Artist]:
        """Redraw the part with new settings.

        The new artists are created before the previous ones are removed.
        If anything fails, the artists created by this call are removed, the
        error is raised again and the part keeps its previous settings and
        artists. Previous artists that are no longer on the Axes, because
        the user removed them or cleared the Axes, are left as they are.

        Parameters
        ----------
        **kwargs
            Options (keys of `OPTION_DEFAULTS`) and matplotlib properties of
            `ARTIST_CLASS`, which may be given by their aliases. Options set
            to ``None`` and properties not given keep their previous values.

        Returns
        -------
        list[matplotlib.artist.Artist]
            A new list of the artists drawn by this call, empty when the
            part is invisible.

        Raises
        ------
        TypeError
            If ``visible`` is not a bool, if an alias and its canonical name
            are both given, if a property is one that the part sets for each
            artist (``xdata`` and ``ydata`` of ``Line2D``, ``x``, ``y`` and
            ``text`` of ``Text``), or as raised by `_validate`.
        ValueError
            As raised by `_validate`.
        AttributeError
            If a keyword is neither an option nor a property of
            `ARTIST_CLASS`, checked even while the part is invisible, or if
            matplotlib rejects a property while creating the artists.
        """
        # (1) Split the keywords into options and matplotlib properties.
        option_kw = {
            key: value
            for key, value in kwargs.items()
            if key in self.OPTION_DEFAULTS
        }
        style_kw = {
            key: value
            for key, value in kwargs.items()
            if key not in self.OPTION_DEFAULTS
        }

        # (2) Merge the options given as other than None, then validate.
        options = {
            **self._options,
            **{
                key: value
                for key, value in option_kw.items()
                if value is not None
            },
        }
        options["visible"] = check_bool(options["visible"], "visible")
        options = self._validate(options)

        # (3) Merge the properties under their canonical names, then check
        # their names even when nothing will be drawn, so that a name that
        # matplotlib rejects is never kept.
        style = {
            **self._style,
            **_normalize_style(style_kw, self.ARTIST_CLASS),
        }
        _check_style_names(style, self.ARTIST_CLASS)

        # (4) Compute the specs. Nothing on the Axes has changed so far.
        specs: list[Spec] = []
        if options["visible"]:
            specs = self._specs(dict(options), dict(style))

        # (5) Create the new artists, all or none.
        artists = self._create_artists(specs)

        # (6) Remove the previous artists still on the Axes and (7) commit.
        # Those that the user removed or cleared are already gone.
        for artist in _attached(self._artists, self._ax):
            artist.remove()
        self._options = options
        self._style = style
        self._artists = artists
        return list(artists)

    @property
    def artists(self) -> list[matplotlib.artist.Artist]:
        """A new list of the artists that the part draws now."""
        return list(self._artists)

    def restack(self) -> None:
        """Move the lines of the part to the end of the lines of the Axes.

        The same ``Line2D`` objects are removed and added back, so that they
        are drawn after the other artists with the same zorder while keeping
        their identity and the changes made to them. Lines that are no
        longer on the Axes, because the user removed them or cleared the
        Axes, are not added back.

        Raises
        ------
        TypeError
            If the part does not draw ``Line2D``.
        """
        if not issubclass(self.ARTIST_CLASS, matplotlib.lines.Line2D):
            raise TypeError(
                f"Only parts that draw Line2D can be restacked, but "
                f"{type(self).__name__} draws "
                f"{self.ARTIST_CLASS.__name__}."
            )
        for artist in _attached(self._artists, self._ax):
            # Created by Axes.plot, as checked through ARTIST_CLASS above.
            line = cast(matplotlib.lines.Line2D, artist)
            line.remove()
            self._ax.add_line(line)

    def _validate(self, options: dict[str, Any]) -> dict[str, Any]:
        """Validate the merged options other than ``visible``.

        Parameters
        ----------
        options : dict[str, Any]
            All options of the part after merging. ``visible`` is already
            checked.

        Returns
        -------
        dict[str, Any]
            The options to keep, possibly converted.

        Raises
        ------
        TypeError, ValueError
            If an option is invalid.
        """
        return options

    @abstractmethod
    def _specs(
        self, options: dict[str, Any], style: dict[str, Any]
    ) -> list[Spec]:
        """Compute the specs of the artists from the settings.

        Called only while the part is visible. It must not change the Axes.

        Parameters
        ----------
        options : dict[str, Any]
            Validated options of the part.
        style : dict[str, Any]
            Merged matplotlib properties with canonical names. They take
            precedence over any per-artist defaults of the part.

        Returns
        -------
        list[Spec]
            Specs of the artists in the order they are created.
        """

    def _create_artists(
        self, specs: Sequence[Spec]
    ) -> list[matplotlib.artist.Artist]:
        """Create the artists of the specs on the Axes, all or none.

        Parameters
        ----------
        specs : Sequence[Spec]
            Specs of the artists to create.

        Returns
        -------
        list[matplotlib.artist.Artist]
            The created artists, in the order of `specs`.

        Raises
        ------
        Exception
            Whatever creating an artist raises (for example the
            ``AttributeError`` of matplotlib for an unknown property), after
            the artists created so far are removed.
        """
        created: list[matplotlib.artist.Artist] = []
        try:
            for spec in specs:
                created.append(self._create_artist(spec))
        except BaseException:
            # Leave the Axes as it was before this call, even on
            # KeyboardInterrupt, then let the original error propagate.
            for artist in created:
                artist.remove()
            raise
        return created

    def _create_artist(self, spec: Spec) -> matplotlib.artist.Artist:
        """Create one artist with the same call as ternary-diagram v3."""
        if isinstance(spec, _LineSpec):
            return self._ax.plot(spec.xdata, spec.ydata, **spec.kwargs)[0]
        if isinstance(spec, _TextSpec):
            return self._ax.text(spec.x, spec.y, spec.s, **spec.kwargs)
        raise TypeError(
            f"A spec must be _LineSpec or _TextSpec, but got "
            f"{type(spec).__name__}."
        )


class _Border(_SkeletonPart):
    """The border of the triangle: its 3 edges.

    The edges are drawn in the order bottom, left, right with the same data
    as ternary-diagram v3. The only option is ``visible``. The zorder given
    at construction is the default zorder of the lines.
    """

    OPTION_DEFAULTS: ClassVar[dict[str, Any]] = {"visible": True}
    STYLE_DEFAULTS: ClassVar[dict[str, Any]] = {
        "color": DEFAULT_BORDER_COLOR,
        "linewidth": DEFAULT_BORDER_LINEWIDTH,
        "linestyle": DEFAULT_BORDER_LINESTYLE,
    }
    ARTIST_CLASS: ClassVar[type[matplotlib.artist.Artist]] = (
        matplotlib.lines.Line2D
    )

    def _specs(
        self, options: dict[str, Any], style: dict[str, Any]
    ) -> list[Spec]:
        edges = (
            ([0.0, 1.0], [0.0, 0.0]),  # bottom
            ([0.0, 0.5], [0.0, ROOT3_OVER_2]),  # left
            ([1.0, 0.5], [0.0, ROOT3_OVER_2]),  # right
        )
        return [_LineSpec(xdata, ydata, dict(style)) for xdata, ydata in edges]


class _Grid(_SkeletonPart):
    """The grid: iso-composition lines of the 3 components.

    The options are ``visible`` and ``step``, the interval of the lines as
    a fraction in ``(0, 1]``. The lines are drawn at the values returned by
    ``get_tick_values(step)``, between the end points returned by
    ``get_grid_segments``, for the components 0, 1 and 2 in turn. The step
    is independent of the interval of the tick labels. The zorder given at
    construction is the default zorder of the lines.
    """

    OPTION_DEFAULTS: ClassVar[dict[str, Any]] = {
        "visible": True,
        "step": DEFAULT_GRID_STEP,
    }
    STYLE_DEFAULTS: ClassVar[dict[str, Any]] = {
        "color": DEFAULT_GRID_COLOR,
        "linewidth": DEFAULT_GRID_LINEWIDTH,
    }
    ARTIST_CLASS: ClassVar[type[matplotlib.artist.Artist]] = (
        matplotlib.lines.Line2D
    )

    def _validate(self, options: dict[str, Any]) -> dict[str, Any]:
        """Validate ``step`` with ``get_tick_values``.

        Raises
        ------
        TypeError
            If ``step`` is not a real number (``bool`` is rejected).
        ValueError
            If ``step`` is not finite or not in ``(0, 1]``.
        """
        get_tick_values(options["step"])
        return options

    def _specs(
        self, options: dict[str, Any], style: dict[str, Any]
    ) -> list[Spec]:
        values = get_tick_values(options["step"])
        specs: list[Spec] = []
        for component in range(3):
            xs, ys = get_grid_segments(values, component)
            for xdata, ydata in zip(xs.tolist(), ys.tolist()):
                specs.append(_LineSpec(xdata, ydata, dict(style)))
        return specs


class _TickLabels(_SkeletonPart):
    """The tick labels on the 3 edges.

    The ticks of component ``k`` are on the edge where component
    ``(k + 1) % 3`` is 0 (see ``get_edge_points``): component 0 on the right
    edge, 1 on the left edge and 2 on the bottom edge, with the values
    increasing counterclockwise.

    The options are ``visible``; ``step``, the interval of the labels as a
    fraction in ``(0, 1]``; ``fmt``, the format given to
    ``get_tick_formatter``; and ``endpoints``, whether to also label the
    values 0 and 1. The step is independent of the interval of the grid.

    For each value returned by ``get_tick_values`` in ascending order, the
    labels of the components 0, 1 and 2 are drawn in turn, at the point of
    ``get_edge_points`` moved by the offset of the edge
    (`DEFAULT_TICK_OFFSETS`). The alignments and the rotation of the edge
    (`DEFAULT_TICK_EDGE_STYLES`) are overridden by the style of the part,
    so a property given by the user applies to the labels of every edge.
    The zorder is left to matplotlib, as in ternary-diagram v3.
    """

    OPTION_DEFAULTS: ClassVar[dict[str, Any]] = {
        "visible": True,
        "step": DEFAULT_TICK_STEP,
        "fmt": DEFAULT_TICK_FORMAT,
        "endpoints": DEFAULT_TICK_ENDPOINTS,
    }
    STYLE_DEFAULTS: ClassVar[dict[str, Any]] = {
        "fontsize": DEFAULT_TICK_FONTSIZE,
    }
    ARTIST_CLASS: ClassVar[type[matplotlib.artist.Artist]] = (
        matplotlib.text.Text
    )

    def _validate(self, options: dict[str, Any]) -> dict[str, Any]:
        """Validate ``step``, ``fmt`` and ``endpoints``.

        Returns
        -------
        dict[str, Any]
            A new dict of the options, with ``endpoints`` converted to the
            built-in ``bool``.

        Raises
        ------
        TypeError
            If ``step`` is not a real number (``bool`` is rejected), if
            ``fmt`` is neither a str nor a callable, or if ``endpoints`` is
            neither True nor False.
        ValueError
            If ``step`` is not finite or not in ``(0, 1]``, or if ``fmt`` is
            a str that cannot be used as a format.
        """
        get_tick_values(options["step"])
        get_tick_formatter(options["fmt"])
        return {
            **options,
            "endpoints": check_bool(options["endpoints"], "endpoints"),
        }

    def _specs(
        self, options: dict[str, Any], style: dict[str, Any]
    ) -> list[Spec]:
        """Compute the specs of the labels.

        Raises
        ------
        Exception
            Whatever a callable ``fmt`` raises. No artist has been created
            at that point, so the part keeps its previous state.
        """
        values = get_tick_values(
            options["step"], endpoints=options["endpoints"]
        )
        format_value = get_tick_formatter(options["fmt"])
        labels = [format_value(value) for value in values.tolist()]

        # Positions of the labels of each component, in the order of values.
        positions: list[list[tuple[float, float]]] = []
        for component, (dx, dy) in enumerate(DEFAULT_TICK_OFFSETS):
            xs, ys = get_edge_points(values, component)
            positions.append(
                [(x + dx, y + dy) for x, y in zip(xs.tolist(), ys.tolist())]
            )

        specs: list[Spec] = []
        for i, label in enumerate(labels):
            for component, edge_style in enumerate(DEFAULT_TICK_EDGE_STYLES):
                x, y = positions[component][i]
                specs.append(_TextSpec(x, y, label, {**edge_style, **style}))
        return specs


class _AxisLabels(_SkeletonPart):
    """The axis titles: one title per component, outside its tick edge.

    The options are ``visible``; ``labels``, the titles of the components
    0, 1 and 2, where ``None`` or ``""`` draws no title; and ``pad``, the
    distance of the titles from the midpoints of their edges, where each
    edge has length 1.

    The title of component ``k`` is drawn at the position and with the
    rotation returned by ``get_axis_label_position(k, pad)``: outside the
    middle of the edge that carries the ticks of the component, parallel to
    it and never upside down. The rotation of the edge is overridden by the
    style of the part. The titles are shown as given, without the
    conversion to chemical formulas applied to the vertex labels. The zorder
    is left to matplotlib, like the other labels.
    """

    OPTION_DEFAULTS: ClassVar[dict[str, Any]] = {
        "visible": True,
        "labels": DEFAULT_AXIS_LABELS,
        "pad": DEFAULT_AXIS_LABEL_PAD,
    }
    STYLE_DEFAULTS: ClassVar[dict[str, Any]] = {
        "fontsize": DEFAULT_AXIS_LABEL_FONTSIZE,
        "horizontalalignment": DEFAULT_AXIS_LABEL_HORIZONTALALIGNMENT,
        "verticalalignment": DEFAULT_AXIS_LABEL_VERTICALALIGNMENT,
    }
    ARTIST_CLASS: ClassVar[type[matplotlib.artist.Artist]] = (
        matplotlib.text.Text
    )

    def _validate(self, options: dict[str, Any]) -> dict[str, Any]:
        """Validate ``labels`` and ``pad``.

        ``labels`` may be any ordered iterable of 3 titles, such as a list,
        a tuple, a numpy array, a pandas Index or Series, or a generator,
        which is consumed once. ``pad`` is validated even when no title is
        drawn.

        Returns
        -------
        dict[str, Any]
            A new dict of the options, with ``labels`` converted to a tuple
            of built-in str (str subclasses such as ``numpy.str_`` are
            converted with ``str``, as matplotlib does when it draws them)
            and None, so that later changes to the given object have no
            effect.

        Raises
        ------
        TypeError
            If ``labels`` is a str, bytes, a mapping, a set or not iterable,
            if iterating over it fails with a TypeError (such as a 0-d numpy
            array), if an item of ``labels`` is neither a str nor None, or
            if ``pad`` is not a real number (``bool`` is rejected).
        ValueError
            If ``labels`` does not have 3 items, or if ``pad`` is not
            finite.
        """
        labels = self._titles(options["labels"])
        get_axis_label_position(0, options["pad"])
        return {**options, "labels": labels}

    @staticmethod
    def _titles(labels: object) -> tuple[str | None, ...]:
        """Turn ``labels`` into a tuple of 3 built-in str or None.

        Raises
        ------
        TypeError, ValueError
            As described in `_validate`.
        """
        items = _ordered_items(
            labels,
            3,
            "labels",
            "a sequence of 3 titles (str or None) such as a list, a tuple, "
            "a numpy array or a pandas Index, not a str, bytes, mapping or "
            "set",
            "one title per component",
        )
        for index, item in enumerate(items):
            if item is not None and not isinstance(item, str):
                raise TypeError(
                    f"Each item of `labels` must be a str or None, but got "
                    f"{item!r} at index {index}."
                )
        return tuple(None if item is None else str(item) for item in items)

    def _specs(
        self, options: dict[str, Any], style: dict[str, Any]
    ) -> list[Spec]:
        specs: list[Spec] = []
        for component, label in enumerate(options["labels"]):
            if label is None or label == "":
                continue
            x, y, rotation = get_axis_label_position(component, options["pad"])
            specs.append(
                _TextSpec(x, y, label, {"rotation": rotation, **style})
            )
        return specs


class _VertexLabels(_SkeletonPart):
    """The vertex labels: the materials at the 3 vertices of the triangle.

    The options are ``visible``; ``labels``, the labels of the top, bottom
    left and bottom right vertices, which are the materials given to
    ``TernaryDiagram`` at construction; and ``offsets``, the offsets
    ``(dx, dy)`` of the labels from their vertices, where each edge has
    length 1.

    Whether the labels are turned into chemical formulas by ``get_label``
    (``auto_latex_notation``) is fixed at construction and also applies to
    the labels given later. Each label is drawn at its vertex moved by its
    offset, with the alignments of the vertex
    (`DEFAULT_VERTEX_LABEL_STYLES`) overridden by the style of the part, so
    a property given by the user applies to the labels of every vertex. The
    zorder is left to matplotlib, as in ternary-diagram v3.
    """

    OPTION_DEFAULTS: ClassVar[dict[str, Any]] = {
        "visible": True,
        # Given at construction; None given later keeps the labels.
        "labels": None,
        "offsets": DEFAULT_VERTEX_LABEL_OFFSETS,
    }
    STYLE_DEFAULTS: ClassVar[dict[str, Any]] = {
        "fontsize": DEFAULT_VERTEX_LABEL_FONTSIZE,
    }
    ARTIST_CLASS: ClassVar[type[matplotlib.artist.Artist]] = (
        matplotlib.text.Text
    )

    def __init__(
        self,
        ax: matplotlib.axes.Axes,
        *,
        auto_latex_notation: bool,
        labels: Sequence[Any],
        **initial: Any,
    ) -> None:
        """Draw the labels once with the initial settings.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            Axes to draw on.
        auto_latex_notation : bool
            Whether to turn the labels into chemical formulas with
            ``get_label``, now and on every later change. Only its truth
            value is used, as in ternary-diagram v3.
        labels : Sequence[Any]
            Labels of the top, bottom left and bottom right vertices: the
            first 3 materials. See `_validate` for the accepted values.
        **initial
            Other initial options and properties, as accepted by `update`.

        Raises
        ------
        TypeError, ValueError, AttributeError
            Raised by `update` for invalid initial settings. Nothing is left
            on `ax` in that case.
        """
        # Set before the first update, which validates the labels with it.
        self._auto_latex_notation = bool(auto_latex_notation)
        super().__init__(ax, labels=labels, **initial)

    def _validate(self, options: dict[str, Any]) -> dict[str, Any]:
        """Validate ``labels`` and ``offsets``.

        ``labels`` may be any ordered iterable of 3 labels, with the same
        rules as the titles of ``_AxisLabels``. With ``auto_latex_notation``,
        each label must be a str, which ``get_label`` checks before any spec
        is computed, as in ternary-diagram v3. Without it, any object is
        shown as matplotlib shows it: ``str(label)``, or ``""`` for None.

        ``offsets`` may be any ordered iterable of 3 pairs ``(dx, dy)`` of
        finite real numbers, such as a tuple of tuples or a numpy array of
        shape ``(3, 2)``.

        Returns
        -------
        dict[str, Any]
            A new dict of the options, with ``labels`` converted to a tuple
            of 3 built-in str (before the conversion to chemical formulas)
            and ``offsets`` to a tuple of 3 pairs of built-in float, so that
            later changes to the given objects have no effect.

        Raises
        ------
        TypeError
            If ``labels`` or ``offsets`` or a pair of ``offsets`` is a str,
            bytes, a mapping, a set or not iterable, if iterating over it
            fails with a TypeError, or if a value of ``offsets`` is not a
            real number (``bool`` is rejected).
        ValueError
            If ``labels`` or ``offsets`` does not have 3 items, if a pair of
            ``offsets`` does not have 2 items, if a value of ``offsets`` is
            not finite, or, with ``auto_latex_notation``, if a label is not
            a str (raised by ``get_label``).
        """
        return {
            **options,
            "labels": self._labels(options["labels"]),
            "offsets": self._offsets(options["offsets"]),
        }

    def _labels(self, labels: object) -> tuple[str, ...]:
        """Turn ``labels`` into a tuple of 3 built-in str.

        Raises
        ------
        TypeError, ValueError
            As described in `_validate`.
        """
        items = _ordered_items(
            labels,
            3,
            "labels",
            "a sequence of 3 labels such as a list, a tuple, a numpy array "
            "or a pandas Index, not a str, bytes, mapping or set",
            "one label per vertex",
        )
        if self._auto_latex_notation:
            for item in items:
                # The ValueError of ternary-diagram v3 for a non-str label.
                get_label(item)
            return tuple(str(item) for item in items)
        # The text that ``Axes.text`` shows for any object.
        return tuple("" if item is None else str(item) for item in items)

    @staticmethod
    def _offsets(offsets: object) -> tuple[tuple[float, float], ...]:
        """Turn ``offsets`` into a tuple of 3 pairs of built-in float.

        Raises
        ------
        TypeError, ValueError
            As described in `_validate`.
        """
        pairs = _ordered_items(
            offsets,
            3,
            "offsets",
            "a sequence of 3 offsets (dx, dy) such as a list, a tuple or a "
            "numpy array of shape (3, 2), not a str, bytes, mapping or set",
            "one offset per vertex",
        )
        converted: list[tuple[float, float]] = []
        for index, pair in enumerate(pairs):
            dx, dy = _ordered_items(
                pair,
                2,
                f"offsets[{index}]",
                "a pair (dx, dy) of real numbers such as a tuple, a list or "
                "a numpy array, not a str, bytes, mapping or set",
                "dx and dy",
            )
            converted.append(
                (
                    _finite_real(dx, f"offsets[{index}][0]"),
                    _finite_real(dy, f"offsets[{index}][1]"),
                )
            )
        return tuple(converted)

    def _specs(
        self, options: dict[str, Any], style: dict[str, Any]
    ) -> list[Spec]:
        # The top, bottom left and bottom right vertices, as for _Border.
        vertices = ((0.5, ROOT3_OVER_2), (0.0, 0.0), (1.0, 0.0))
        specs: list[Spec] = []
        for label, (x, y), (dx, dy), vertex_style in zip(
            options["labels"],
            vertices,
            options["offsets"],
            DEFAULT_VERTEX_LABEL_STYLES,
        ):
            text = get_label(label) if self._auto_latex_notation else label
            specs.append(
                _TextSpec(x + dx, y + dy, text, {**vertex_style, **style})
            )
        return specs


# The vertices of the triangle whose edges have length 1: top, bottom left
# and bottom right.
TRIANGLE_VERTICES: tuple[tuple[float, float], ...] = (
    (0.5, ROOT3_OVER_2),
    (0.0, 0.0),
    (1.0, 0.0),
)

# Arguments of the constructors of the parts other than ``zorder``, which
# cannot be passed through ``**initial``. They are neither options nor
# properties, so ``update`` rejects them as unknown properties.
_PART_CONSTRUCTOR_ARGUMENTS: frozenset[str] = frozenset({"self", "ax"})
# The same for ``_VertexLabels``, whose ``labels`` are checked separately as
# they are an option given by the materials.
_VERTEX_LABELS_CONSTRUCTOR_ARGUMENTS: frozenset[str] = (
    _PART_CONSTRUCTOR_ARGUMENTS | {"auto_latex_notation"}
)
# The argument of ``_SkeletonPart.update`` that cannot be passed through
# ``**kwargs``.
_PART_UPDATE_ARGUMENTS: frozenset[str] = frozenset({"self"})


def _reject_arguments(
    kwargs: Mapping[str, Any],
    arguments: frozenset[str],
    artist_class: type[matplotlib.artist.Artist],
) -> None:
    """Reject keywords that would collide with the arguments of a method.

    A part receives its settings through ``**kwargs``, so a setting named
    like another argument of the method would reach it twice and fail with
    a TypeError that names the internal method. Such names are neither
    options nor properties, so they are rejected with the error that the
    part raises for any unknown property.

    Parameters
    ----------
    kwargs : Mapping[str, Any]
        Settings to pass to the part.
    arguments : frozenset[str]
        Names of the other arguments of the method that receives them.
    artist_class : type[matplotlib.artist.Artist]
        Class of the artists of the part.

    Raises
    ------
    AttributeError
        If a key of `kwargs` is in `arguments`, with the message of
        ``Artist.set``, as raised by the part for an unknown property.
    """
    _check_style_names(
        {name: kwargs[name] for name in sorted(arguments) if name in kwargs},
        artist_class,
    )


def _initial_settings(
    settings: Mapping[str, Any],
    artist_class: type[matplotlib.artist.Artist],
    zorder: float | None,
    arguments: frozenset[str] = _PART_CONSTRUCTOR_ARGUMENTS,
) -> dict[str, Any]:
    """Turn the initial settings of a part into keywords of its constructor.

    The constructors take the default zorder of the part as an argument of
    their own, while ``update`` takes ``zorder`` as a property like the
    others. A ``zorder`` in `settings` is passed as that argument in place
    of `zorder`, so that it wins over the default, as it does when given to
    ``update``.

    Parameters
    ----------
    settings : Mapping[str, Any]
        Initial options and properties of the part. It is not changed.
    artist_class : type[matplotlib.artist.Artist]
        Class of the artists of the part.
    zorder : float or None
        Default zorder of the artists of the part. None leaves it to
        matplotlib.
    arguments : frozenset[str], optional
        The other arguments of the constructor of the part, which `settings`
        cannot contain, by default ``_PART_CONSTRUCTOR_ARGUMENTS``

    Returns
    -------
    dict[str, Any]
        A new dict of `settings` with ``zorder``.

    Raises
    ------
    AttributeError
        If `settings` contains one of `arguments`.
    """
    _reject_arguments(settings, arguments, artist_class)
    return {"zorder": zorder, **settings}


def _check_vertex_label_kw(vertex_label_kw: Mapping[str, Any]) -> None:
    """Reject ``labels`` among the initial settings of the vertex labels.

    At construction, the vertex labels are given by the materials, so
    ``labels`` in `vertex_label_kw` would give them twice. Both
    ``TernaryDiagram`` (before changing the Axes) and `_Skeleton` check it
    with this function, so that the message is the same.

    Parameters
    ----------
    vertex_label_kw : Mapping[str, Any]
        Initial settings of the vertex labels.

    Raises
    ------
    ValueError
        If `vertex_label_kw` contains ``labels``, whatever its value.
    """
    if "labels" in vertex_label_kw:
        raise ValueError(
            "`vertex_label_kw` cannot contain `labels`: the vertex labels "
            "are given by `materials`, so it is ambiguous which to use."
        )


class _Skeleton:
    """The skeleton of a ternary diagram: its 5 parts.

    At construction, the vertices of the triangle are added to the data
    limits of the Axes and the view is autoscaled, so that the view limits
    are the same whether the border and the grid are drawn or not. Then the
    parts are drawn once each with their initial settings, in the order
    grid, border, vertex labels, tick labels and axis titles: the order of
    ternary-diagram v3, with the new axis titles last.

    After that, a part is updated and its artists are returned by its name
    (`PartName`). The border and the grid have the same zorder, so the lines
    added last are drawn on top: whenever the grid is updated, the border
    lines are moved back to the end of the lines of the Axes, so that the
    border is always drawn over the grid.

    The skeleton never changes the layout of the figure or the position of
    the Axes. The other settings of the Axes (the aspect ratio, the ticks
    and the spines) are made by ``TernaryDiagram``.
    """

    def __init__(
        self,
        ax: matplotlib.axes.Axes,
        materials: Sequence[Any],
        auto_latex_notation: bool,
        *,
        zorder: float,
        border_kw: Mapping[str, Any],
        grid_kw: Mapping[str, Any],
        tick_kw: Mapping[str, Any],
        axis_label_kw: Mapping[str, Any],
        vertex_label_kw: Mapping[str, Any],
    ) -> None:
        """Draw the 5 parts with their initial settings.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            Axes to draw on.
        materials : Sequence[Any]
            Materials of the diagram, already validated by the caller. The
            first 3 are the labels of the top, bottom left and bottom right
            vertices.
        auto_latex_notation : bool
            Whether to turn the vertex labels into chemical formulas, now
            and on every later change (see ``_VertexLabels``).
        zorder : float
            Default zorder of the border and grid lines. The labels keep
            the default zorder of matplotlib.
        border_kw : Mapping[str, Any]
            Initial settings of the border: what `update` accepts for the
            part ``"border"``, with the same meaning. A ``zorder`` among
            them wins over `zorder`. It is not changed, nor are the other
            mappings below.
        grid_kw : Mapping[str, Any]
            Initial settings of the grid, as for the part ``"grid"``. A
            ``zorder`` among them wins over `zorder`.
        tick_kw : Mapping[str, Any]
            Initial settings of the tick labels, as for the part
            ``"ticks"``.
        axis_label_kw : Mapping[str, Any]
            Initial settings of the axis titles, as for the part
            ``"axis_labels"``.
        vertex_label_kw : Mapping[str, Any]
            Initial settings of the vertex labels, as for the part
            ``"vertex_labels"``, except ``labels``, which are given by
            `materials`.

        Raises
        ------
        ValueError
            If `vertex_label_kw` contains ``labels``, or as raised by the
            parts for invalid settings.
        AttributeError
            If a setting is neither an option of its part nor a property of
            its artists, including ``ax``, ``self`` and, in
            `vertex_label_kw`, ``auto_latex_notation``, which `update`
            rejects in the same way.
        Exception
            Whatever validating or drawing a part raises (see
            ``_SkeletonPart.update``). The artists of the parts drawn
            before are removed first, so that no artist of the skeleton is
            left on `ax`. The data limits registered before are kept.
        """
        # Settings that the parts cannot check, checked before drawing.
        grid_settings = _initial_settings(grid_kw, _Grid.ARTIST_CLASS, zorder)
        border_settings = _initial_settings(
            border_kw, _Border.ARTIST_CLASS, zorder
        )
        _check_vertex_label_kw(vertex_label_kw)
        vertex_label_settings = _initial_settings(
            vertex_label_kw,
            _VertexLabels.ARTIST_CLASS,
            None,
            _VERTEX_LABELS_CONSTRUCTOR_ARGUMENTS,
        )
        tick_settings = _initial_settings(
            tick_kw, _TickLabels.ARTIST_CLASS, None
        )
        axis_label_settings = _initial_settings(
            axis_label_kw, _AxisLabels.ARTIST_CLASS, None
        )
        labels = tuple(materials)[:3]

        ax.update_datalim(TRIANGLE_VERTICES)
        ax.autoscale_view()

        parts: dict[PartName, _SkeletonPart] = {}
        try:
            parts["grid"] = _Grid(ax, **grid_settings)
            parts["border"] = _Border(ax, **border_settings)
            parts["vertex_labels"] = _VertexLabels(
                ax,
                auto_latex_notation=auto_latex_notation,
                labels=labels,
                **vertex_label_settings,
            )
            parts["ticks"] = _TickLabels(ax, **tick_settings)
            parts["axis_labels"] = _AxisLabels(ax, **axis_label_settings)
        except BaseException:
            # A part that fails leaves nothing on the Axes. Remove the parts
            # drawn before it, even on KeyboardInterrupt, then let the
            # original error propagate.
            for part in parts.values():
                for artist in part.artists:
                    artist.remove()
            raise
        self._parts = parts

    def update(
        self, name: PartName, /, **kwargs: Any
    ) -> list[matplotlib.artist.Artist]:
        """Redraw a part with new settings.

        Parameters
        ----------
        name : PartName
            Name of the part. It is positional only, so that a property
            called ``name`` (an alias of ``fontname`` of ``Text``) can be
            given in `kwargs`.
        **kwargs
            Options of the part and properties of its artists, merged with
            its current settings by ``_SkeletonPart.update``.

        Returns
        -------
        list[matplotlib.artist.Artist]
            A new list of the artists drawn by the part, empty when it is
            invisible.

        Raises
        ------
        ValueError
            If `name` is not the name of a part, or as raised by the part
            for invalid settings.
        AttributeError
            If a setting is neither an option of the part nor a property of
            its artists, including ``self``.
        Exception
            Whatever validating or drawing the part raises (see
            ``_SkeletonPart.update``). The part then keeps its previous
            settings and artists, and the border lines are not moved.
        """
        part = self._part(name)
        _reject_arguments(kwargs, _PART_UPDATE_ARGUMENTS, part.ARTIST_CLASS)
        artists = part.update(**kwargs)
        if name == "grid":
            self._parts["border"].restack()
        return artists

    def artists(self, name: PartName) -> list[matplotlib.artist.Artist]:
        """Return a new list of the artists that a part draws now.

        Parameters
        ----------
        name : PartName
            Name of the part.

        Returns
        -------
        list[matplotlib.artist.Artist]
            The artists of the part, empty when it is invisible.

        Raises
        ------
        ValueError
            If `name` is not the name of a part.
        """
        return self._part(name).artists

    def _part(self, name: PartName) -> _SkeletonPart:
        """Return the part called `name`.

        Raises
        ------
        ValueError
            If `name` is not the name of a part.
        """
        part = self._parts.get(name)
        if part is None:
            raise ValueError(
                f"`name` must be one of {', '.join(map(repr, _PART_NAMES))}, "
                f"but got {name!r}."
            )
        return part
