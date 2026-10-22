"""Policy of the processing after drawing on a ternary diagram.

The functions here read the figure, decide what to do after drawing and
build the messages of the warnings about it. None of them changes the
figure. ``PostDrawContext`` holds the state of this processing for one
ternary diagram.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import matplotlib
import matplotlib.colorbar
import matplotlib.figure

from ternary_diagram._deprecation import format_default_change

__all__ = (
    "COLORBAR_WARNING_KEY",
    "ColorbarAction",
    "LAYOUT_WARNING_KEY",
    "LayoutAction",
    "LayoutState",
    "PostDrawContext",
    "colorbar_warning_message",
    "decide_colorbar",
    "decide_layout",
    "get_layout_state",
    "layout_warning_message",
)

# Figure.get_layout_engine and PlaceHolderLayoutEngine exist since
# matplotlib 3.6. Older versions only tell the constrained and tight flags.
_HAS_LAYOUT_ENGINE: bool = tuple(
    map(int, matplotlib.__version__.split(".")[:2])
) >= (3, 6)
if _HAS_LAYOUT_ENGINE:
    from matplotlib.layout_engine import PlaceHolderLayoutEngine


class LayoutState(Enum):
    """Layout state of the figure that a ternary diagram draws on.

    Attributes
    ----------
    NO_ENGINE
        The figure has no layout engine, or only the placeholder engine that
        ``Figure.tight_layout()`` leaves behind, for example after an earlier
        adjustment by this library.
    HAS_ENGINE
        The figure has a layout engine set by the user or by rcParams, such
        as constrained, compressed or tight.
    UNSUPPORTED
        The figure is not a top-level ``Figure``, such as a ``SubFigure``.
    """

    NO_ENGINE = "no_engine"
    HAS_ENGINE = "has_engine"
    UNSUPPORTED = "unsupported"


def get_layout_state(fig: matplotlib.figure.FigureBase) -> LayoutState:
    """Tell whether the figure has a layout engine.

    Parameters
    ----------
    fig : matplotlib.figure.FigureBase
        Figure or subfigure that holds the Axes of the ternary diagram.

    Returns
    -------
    LayoutState
        ``UNSUPPORTED`` when `fig` is not a top-level ``Figure``. With
        matplotlib 3.6 or later, ``NO_ENGINE`` when `fig` has no layout
        engine or a ``PlaceHolderLayoutEngine``, ``HAS_ENGINE`` otherwise.
        With older matplotlib, ``HAS_ENGINE`` when the constrained layout or
        the tight layout of `fig` is enabled, ``NO_ENGINE`` otherwise.
    """
    if not isinstance(fig, matplotlib.figure.Figure):
        return LayoutState.UNSUPPORTED
    if _HAS_LAYOUT_ENGINE:
        engine = fig.get_layout_engine()
        if engine is None or isinstance(engine, PlaceHolderLayoutEngine):
            return LayoutState.NO_ENGINE
        return LayoutState.HAS_ENGINE
    if fig.get_constrained_layout() or fig.get_tight_layout():
        return LayoutState.HAS_ENGINE
    return LayoutState.NO_ENGINE


class LayoutAction(Enum):
    """What to do with the figure layout after drawing.

    Attributes
    ----------
    SKIP
        Leave the figure layout as it is.
    APPLY
        Call ``Figure.tight_layout()``.
    APPLY_AND_WARN
        Call ``Figure.tight_layout()`` and warn that the default changes in
        ternary-diagram 4.0.0.
    """

    SKIP = "skip"
    APPLY = "apply"
    APPLY_AND_WARN = "apply_and_warn"


class ColorbarAction(Enum):
    """Whether to add a colorbar automatically after drawing.

    Attributes
    ----------
    SKIP
        Add no colorbar.
    ADD
        Add a colorbar.
    ADD_AND_WARN
        Add a colorbar and warn that the default changes in ternary-diagram
        4.0.0.
    """

    SKIP = "skip"
    ADD = "add"
    ADD_AND_WARN = "add_and_warn"


LAYOUT_WARNING_KEY: str = "layout.tight_layout"
"""Key of the warning issued for ``LayoutAction.APPLY_AND_WARN``."""

COLORBAR_WARNING_KEY: str = "colorbar.duplicate"
"""Key of the warning issued for ``ColorbarAction.ADD_AND_WARN``."""


def decide_layout(setting: bool | None, state: LayoutState) -> LayoutAction:
    """Decide what to do with the figure layout after drawing.

    Only the figure without a layout engine is adjusted. The warning is
    needed only when the default leads to an adjustment, which the default
    of ternary-diagram 4.0.0 will not do.

    Parameters
    ----------
    setting : bool | None
        ``tight_layout`` of the ternary diagram. None means that it was not
        specified.
    state : LayoutState
        Layout state of the figure, from ``get_layout_state``.

    Returns
    -------
    LayoutAction
        ``APPLY_AND_WARN`` when `setting` is None and `state` is
        ``NO_ENGINE``, ``APPLY`` when `setting` is True and `state` is
        ``NO_ENGINE``, ``SKIP`` otherwise.
    """
    adjustable = state is LayoutState.NO_ENGINE
    if setting is None:
        # The only row that ternary-diagram 4.0.0 changes, to SKIP.
        return LayoutAction.APPLY_AND_WARN if adjustable else LayoutAction.SKIP
    return LayoutAction.APPLY if setting and adjustable else LayoutAction.SKIP


def decide_colorbar(
    requested: bool | None, *, has_mappable: bool, has_existing: bool
) -> ColorbarAction:
    """Decide whether to add a colorbar automatically after drawing.

    A colorbar is added only for a plot colored by values. The warning is
    needed only when the default adds another colorbar to a diagram that
    already has one, which the default of ternary-diagram 4.0.0 will not do.

    Parameters
    ----------
    requested : bool | None
        ``colorbar`` of the plot. None means that it was not specified.
    has_mappable : bool
        Whether the plot is colored by values.
    has_existing : bool
        Whether the diagram already has a colorbar that it added and that
        is not removed.

    Returns
    -------
    ColorbarAction
        ``SKIP`` when `has_mappable` is False or `requested` is False.
        Otherwise ``ADD_AND_WARN`` when `requested` is None and
        `has_existing` is True, ``ADD`` in the other cases.
    """
    if not has_mappable:
        return ColorbarAction.SKIP
    if requested is None:
        # The only row that ternary-diagram 4.0.0 changes: ADD_AND_WARN to
        # SKIP.
        return (
            ColorbarAction.ADD_AND_WARN if has_existing else ColorbarAction.ADD
        )
    return ColorbarAction.ADD if requested else ColorbarAction.SKIP


def layout_warning_message() -> str:
    """Build the message of the warning for ``LayoutAction.APPLY_AND_WARN``.

    Returns
    -------
    str
        The message announcing that the figure layout will no longer be
        adjusted by default, with how to keep the current behavior and how
        to adopt the new one.
    """
    return format_default_change(
        current=(
            "TernaryDiagram called `Figure.tight_layout()` after plotting "
            "because the figure has no layout engine and `tight_layout` was "
            "not specified."
        ),
        future=(
            "TernaryDiagram will no longer adjust the figure layout by "
            "default (tight_layout=False)."
        ),
        keep="pass `tight_layout=True` to `TernaryDiagram`",
        adopt=(
            "pass `tight_layout=False` and call `fig.tight_layout()` "
            'yourself, or create the figure with `layout="constrained"`'
        ),
    )


def colorbar_warning_message(func: str) -> str:
    """Build the message of the warning for ``ColorbarAction.ADD_AND_WARN``.

    The message does not mention ``z``, so that plots colored by values
    without ``z`` can issue it too.

    Parameters
    ----------
    func : str
        Name of the plotting method that the user called, such as
        ``"scatter"`` or ``"heatmapf"``.

    Returns
    -------
    str
        The message announcing that a colorbar will be added automatically
        only to a diagram without one, with how to keep the current behavior
        and how to adopt the new one.
    """
    return format_default_change(
        current=(
            f"`{func}` added another colorbar to this diagram, which already "
            "has one, because `colorbar` was not specified."
        ),
        future=(
            "a colorbar will be added automatically only when the diagram "
            "has none."
        ),
        keep="pass `colorbar=True`",
        adopt="pass `colorbar=False`",
    )


# eq=False: each diagram owns its context, so compare by identity.
@dataclass(frozen=True, eq=False)
class PostDrawContext:
    """State of the processing after drawing for one ternary diagram.

    A ``TernaryDiagram`` creates one instance, and all of its plots share
    it. The state is only added to through the methods.

    Parameters
    ----------
    tight_layout : bool | None, optional
        ``tight_layout`` of the ternary diagram, which cannot be changed
        afterwards. None means that it was not specified, by default None
    """

    tight_layout: bool | None = None
    _colorbars: list[matplotlib.colorbar.Colorbar] = field(
        default_factory=list, init=False, repr=False
    )
    _warned: set[str] = field(default_factory=set, init=False, repr=False)

    def register_colorbar(
        self, colorbar: matplotlib.colorbar.Colorbar
    ) -> None:
        """Register a colorbar created through the ternary diagram.

        Parameters
        ----------
        colorbar : matplotlib.colorbar.Colorbar
            Colorbar that the ternary diagram added automatically or through
            ``TernaryDiagram.colorbar``.
        """
        self._colorbars.append(colorbar)

    def has_colorbar(self) -> bool:
        """Tell whether a registered colorbar is not removed yet.

        A colorbar counts as removed when its mappable no longer points to
        it, which ``Colorbar.remove()`` causes. Colorbars added with
        matplotlib directly are not registered, so they do not count.

        Returns
        -------
        bool
            True when at least one registered colorbar is not removed.
        """
        return any(cb.mappable.colorbar is cb for cb in self._colorbars)

    def first_time(self, key: str) -> bool:
        """Tell whether `key` is received for the first time, and record it.

        Parameters
        ----------
        key : str
            Reason of a warning, namespaced by the feature, such as
            ``"layout.tight_layout"``.

        Returns
        -------
        bool
            True only the first time `key` is received by this instance.
        """
        if key in self._warned:
            return False
        self._warned.add(key)
        return True
