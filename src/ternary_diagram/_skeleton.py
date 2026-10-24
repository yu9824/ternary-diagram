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
from collections.abc import Sequence
from typing import Any, ClassVar, NamedTuple, Union, cast

import matplotlib.artist
import matplotlib.axes
import matplotlib.lines
import matplotlib.text
from matplotlib import cbook
from matplotlib.artist import ArtistInspector

from ternary_diagram.utils import check_bool

__all__ = ("Spec",)


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
        artists.

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
            are both given, or as raised by `_validate`.
        ValueError
            As raised by `_validate`.
        AttributeError
            If matplotlib rejects a property while creating the artists.
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

        # (3) Merge the properties under their canonical names.
        style = {
            **self._style,
            **_normalize_style(style_kw, self.ARTIST_CLASS),
        }

        # (4) Compute the specs. Nothing on the Axes has changed so far.
        specs: list[Spec] = []
        if options["visible"]:
            specs = self._specs(dict(options), dict(style))

        # (5) Create the new artists, all or none.
        artists = self._create_artists(specs)

        # (6) Remove the previous artists and (7) commit.
        for artist in self._artists:
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
        their identity and the changes made to them.

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
        for artist in self._artists:
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
