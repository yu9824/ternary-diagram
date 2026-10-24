"""Expected values of the v3 default skeleton of ``TernaryDiagram``.

The skeleton is what ``TernaryDiagram(materials)`` draws before any
plotting call: 3 border lines, 27 grid lines, 3 vertex labels and 27 tick
labels. The values below are computed from the drawing formulas of
ternary-diagram v3 (``TernaryDiagram.__init__``), not from the code under
test, so that the characterization tests, the unit tests of the skeleton
parts and the unit tests of the aggregate all compare against the same
reference.

Artists are reduced to hashable keys (`LineKey` and `TextKey`) with floats
rounded to `DIGITS` decimal places, so that results computed in a
different order or orientation compare equal while a changed offset such
as 0.02 does not. The module name starts with ``_`` so that pytest does
not collect it as a test module.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt
from typing import NamedTuple

import matplotlib.axes
import matplotlib.lines
import matplotlib.text
from matplotlib.colors import to_rgba

ROOT3_OVER_2 = sqrt(3.0) / 2.0

# Floats are rounded to this many decimal places before comparison.
DIGITS = 9

# zorder of the border and grid lines (``DEFAULT_ZORDER_GRIDS`` in v3)
LINE_ZORDER = 1
# zorder of the labels (matplotlib's default for ``Text``)
TEXT_ZORDER = 3

BORDER_COLOR = "black"
BORDER_LINEWIDTH = 2.0
GRID_COLOR = "gray"
GRID_LINEWIDTH = 0.5
# v3 passes ``linestyle="-"`` to the border and nothing to the grid, which
# then uses matplotlib's default solid line.
LINESTYLE = "-"

# v3 sets no color on the labels, so they use matplotlib's default
# ``text.color``.
TEXT_COLOR = "black"

VERTEX_LABEL_FONTSIZE = 16.0
TICK_LABEL_FONTSIZE = 10.0

# The default margins of matplotlib's autoscaling (``axes.xmargin`` and
# ``axes.ymargin``).
AUTOSCALE_MARGIN = 0.05

Point = tuple[float, float]
Segment = tuple[Point, Point]
Limits = tuple[float, float]


class LineKey(NamedTuple):
    """Comparable summary of a straight line of the skeleton."""

    segment: Segment
    color: tuple[float, float, float, float]
    linewidth: float
    linestyle: str
    zorder: float


class TextKey(NamedTuple):
    """Comparable summary of a label of the skeleton."""

    text: str
    position: Point
    rotation: float
    horizontalalignment: str
    verticalalignment: str
    color: tuple[float, float, float, float]
    fontsize: float
    zorder: float


def _round(value: float) -> float:
    # `+ 0.0` turns -0.0 into 0.0
    return round(float(value), DIGITS) + 0.0


def point_key(x: float, y: float) -> Point:
    """Return the rounded point ``(x, y)``."""
    return (_round(x), _round(y))


def segment_key(start: Point, end: Point) -> Segment:
    """Return the segment between two points regardless of its direction."""
    first, second = sorted((point_key(*start), point_key(*end)))
    return (first, second)


def _color_key(color: object) -> tuple[float, float, float, float]:
    red, green, blue, alpha = to_rgba(color)
    return (_round(red), _round(green), _round(blue), _round(alpha))


def _line(start: Point, end: Point, color: str, linewidth: float) -> LineKey:
    return LineKey(
        segment=segment_key(start, end),
        color=_color_key(color),
        linewidth=_round(linewidth),
        linestyle=LINESTYLE,
        zorder=_round(LINE_ZORDER),
    )


def _text(
    text: str,
    x: float,
    y: float,
    *,
    rotation: float,
    horizontalalignment: str,
    verticalalignment: str,
    fontsize: float,
) -> TextKey:
    return TextKey(
        text=text,
        position=point_key(x, y),
        rotation=_round(rotation),
        horizontalalignment=horizontalalignment,
        verticalalignment=verticalalignment,
        color=_color_key(TEXT_COLOR),
        fontsize=_round(fontsize),
        zorder=_round(TEXT_ZORDER),
    )


def line_key(line: matplotlib.lines.Line2D) -> LineKey:
    """Summarize a drawn line made of exactly two points.

    Raises
    ------
    ValueError
        If the line does not consist of exactly two points.
    """
    xdata, ydata = line.get_data()
    if len(xdata) != 2 or len(ydata) != 2:
        raise ValueError(
            f"a skeleton line must have 2 points, got {len(xdata)}"
        )
    return LineKey(
        segment=segment_key((xdata[0], ydata[0]), (xdata[1], ydata[1])),
        color=_color_key(line.get_color()),
        linewidth=_round(line.get_linewidth()),
        linestyle=line.get_linestyle(),
        zorder=_round(line.get_zorder()),
    )


def text_key(text: matplotlib.text.Text) -> TextKey:
    """Summarize a drawn label."""
    x, y = text.get_position()
    return TextKey(
        text=text.get_text(),
        position=point_key(x, y),
        rotation=_round(text.get_rotation()),
        horizontalalignment=text.get_horizontalalignment(),
        verticalalignment=text.get_verticalalignment(),
        color=_color_key(text.get_color()),
        fontsize=_round(text.get_fontsize()),
        zorder=_round(text.get_zorder()),
    )


def expected_border_lines() -> list[LineKey]:
    """Return the 3 border lines: bottom, left and right edges."""
    return [
        _line((0.0, 0.0), (1.0, 0.0), BORDER_COLOR, BORDER_LINEWIDTH),
        _line((0.0, 0.0), (0.5, ROOT3_OVER_2), BORDER_COLOR, BORDER_LINEWIDTH),
        _line((1.0, 0.0), (0.5, ROOT3_OVER_2), BORDER_COLOR, BORDER_LINEWIDTH),
    ]


def expected_grid_lines() -> list[LineKey]:
    """Return the 27 grid lines, 9 parallel to each edge at 10% steps."""
    lines = []
    for i in range(1, 10):
        height = ROOT3_OVER_2 * i / 10.0
        lines.append(
            _line(
                (i / 20.0, height),
                (1.0 - i / 20.0, height),
                GRID_COLOR,
                GRID_LINEWIDTH,
            )
        )
        lines.append(
            _line(
                (i / 20.0, height),
                (i / 10.0, 0.0),
                GRID_COLOR,
                GRID_LINEWIDTH,
            )
        )
        lines.append(
            _line(
                (0.5 + i / 20.0, ROOT3_OVER_2 * (1.0 - i / 10.0)),
                (i / 10.0, 0.0),
                GRID_COLOR,
                GRID_LINEWIDTH,
            )
        )
    return lines


def expected_vertex_label_texts(labels: Sequence[str]) -> list[TextKey]:
    """Return the 3 vertex labels: top, bottom left and bottom right.

    Parameters
    ----------
    labels : Sequence[str]
        The 3 strings as displayed, i.e. after the LaTeX notation is
        applied when ``auto_latex_notation`` is true.
    """
    if len(labels) != 3:
        raise ValueError(f"3 labels are required, got {len(labels)}")
    return [
        _text(
            labels[0],
            0.5,
            ROOT3_OVER_2 + 0.02,
            rotation=0.0,
            horizontalalignment="center",
            verticalalignment="bottom",
            fontsize=VERTEX_LABEL_FONTSIZE,
        ),
        _text(
            labels[1],
            0.0,
            -0.05,
            rotation=0.0,
            horizontalalignment="right",
            verticalalignment="top",
            fontsize=VERTEX_LABEL_FONTSIZE,
        ),
        _text(
            labels[2],
            1.0,
            -0.05,
            rotation=0.0,
            horizontalalignment="left",
            verticalalignment="top",
            fontsize=VERTEX_LABEL_FONTSIZE,
        ),
    ]


def expected_tick_label_texts() -> list[TextKey]:
    """Return the 27 tick labels, "10" to "90" on each edge."""
    texts = []
    for i in range(1, 10):
        label = "%d0" % i
        # on the right edge, for the top component
        texts.append(
            _text(
                label,
                0.5 + (10 - i) / 20.0,
                ROOT3_OVER_2 * (1.0 - (10 - i) / 10.0),
                rotation=0.0,
                horizontalalignment="left",
                verticalalignment="bottom",
                fontsize=TICK_LABEL_FONTSIZE,
            )
        )
        # on the left edge, for the bottom-left component
        texts.append(
            _text(
                label,
                (10 - i) / 20.0 - 0.01,
                ROOT3_OVER_2 * (10 - i) / 10.0 + 0.04,
                rotation=300.0,
                horizontalalignment="right",
                verticalalignment="top",
                fontsize=TICK_LABEL_FONTSIZE,
            )
        )
        # on the bottom edge, for the bottom-right component
        texts.append(
            _text(
                label,
                i / 10.0 + 0.02,
                0.0,
                rotation=60.0,
                horizontalalignment="right",
                verticalalignment="top",
                fontsize=TICK_LABEL_FONTSIZE,
            )
        )
    return texts


def box_aspect(ax: matplotlib.axes.Axes) -> float:
    """Return the height / width ratio of the Axes box in display units.

    The original position is used, as ``Axes.apply_aspect`` does with
    ``adjustable="datalim"``.
    """
    fig_width, fig_height = ax.figure.get_size_inches()
    position = ax.get_position(original=True)
    return (fig_height * position.height) / (fig_width * position.width)


def expected_view_limits(aspect: float) -> tuple[Limits, Limits]:
    """Return the xlim and ylim of the skeleton after the figure is drawn.

    The data limits of the skeleton are the bounding box of the triangle,
    ``[0, 1] x [0, sqrt(3)/2]``. Autoscaling adds `AUTOSCALE_MARGIN` on
    each side, and then the ``set_aspect("equal", adjustable="datalim")``
    of v3 changes one of the intervals around its center so that the data
    keep an aspect ratio of 1 in a box of the given `aspect`. The choice of
    the interval follows ``Axes.apply_aspect`` for unshared linear axes.
    With matplotlib's default figure, the result is about
    ``((-0.139, 1.139), (-0.043, 0.909))``.

    Parameters
    ----------
    aspect : float
        Height / width ratio of the Axes box in display units, as returned
        by `box_aspect`.
    """
    data_x0, data_x1 = 0.0, 1.0
    data_y0, data_y1 = 0.0, ROOT3_OVER_2
    x_pad = AUTOSCALE_MARGIN * (data_x1 - data_x0)
    y_pad = AUTOSCALE_MARGIN * (data_y1 - data_y0)
    xlim = (data_x0 - x_pad, data_x1 + x_pad)
    ylim = (data_y0 - y_pad, data_y1 + y_pad)

    xsize = xlim[1] - xlim[0]
    ysize = ylim[1] - ylim[0]
    y_expander = aspect * xsize / ysize - 1
    if abs(y_expander) < 0.005:
        return xlim, ylim

    xr = 1.05 * (data_x1 - data_x0)
    yr = 1.05 * (data_y1 - data_y0)
    new_ysize = aspect * xsize
    new_xsize = ysize / aspect
    if xsize > xr and ysize > yr:
        adjust_y = (new_ysize > yr and y_expander < 0) or (
            new_xsize < xr and y_expander > 0
        )
    else:
        adjust_y = y_expander > 0

    if adjust_y:
        center = (ylim[0] + ylim[1]) / 2.0
        return xlim, (center - new_ysize / 2.0, center + new_ysize / 2.0)
    center = (xlim[0] + xlim[1]) / 2.0
    return (center - new_xsize / 2.0, center + new_xsize / 2.0), ylim
