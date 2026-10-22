"""Policy of the processing after drawing on a ternary diagram.

The functions here read the figure and decide what to do after drawing.
None of them changes the figure.
"""

from __future__ import annotations

from enum import Enum

import matplotlib
import matplotlib.figure

__all__ = (
    "LayoutState",
    "get_layout_state",
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
