"""
Copyright © 2021 yu9824
"""

# deprecated from python>=3.9
from typing import Tuple, List  # isort: skip

from abc import abstractmethod
from collections import defaultdict
from collections.abc import Mapping, Sequence
from numbers import Number
from typing import Any, Optional, Union, cast

import matplotlib
import matplotlib.axes
import matplotlib.cm
import matplotlib.collections
import matplotlib.colorbar
import matplotlib.figure
import matplotlib.lines
import matplotlib.patches
import matplotlib.text
import numpy as np

# import matplotlib.cm as cm      # ternary内にカラーマップを創設する
if tuple(map(int, matplotlib.__version__.split(".")[:2])) >= (3, 7):
    from matplotlib.tri import Triangulation, TriContourSet
else:
    from matplotlib.tri.triangulation import Triangulation
    from matplotlib.tri.tricontour import TriContourSet
from numpy.typing import ArrayLike

from ternary_diagram._deprecation import (
    UNSET,
    format_default_change,
    resolve_renamed_parameter,
    warn_external,
)
from ternary_diagram._mesh import (
    DEFAULT_HEATMAPF_SCALE,
    HeatmapFunc,
    MeshCollection,
    Shading,
    check_mesh_kwargs,
    check_shading,
    default_color_range,
    duplicate_points_message,
    evaluate_function,
    triangulate,
    unpaintable_mask,
)
from ternary_diagram._post_draw import (
    COLORBAR_WARNING_KEY,
    LAYOUT_WARNING_KEY,
    ColorbarAction,
    LayoutAction,
    PostDrawContext,
    colorbar_warning_message,
    decide_colorbar,
    decide_layout,
    get_layout_state,
    layout_warning_message,
)
from ternary_diagram._skeleton import _check_vertex_label_kw, _Skeleton
from ternary_diagram.utils import (
    TickFormat,
    check_1d_vector,
    check_2d_vector,
    check_ax,
    check_optional_bool,
    get_label,
    get_triangular_lattice,
    three2two,
    to_latex_notation,
)

# default parameters
DEFAULT_CMAP = "rainbow"
DEFAULT_ZORDER_CONTOUR = 0
DEFAULT_ZORDER_GRIDS = 1
DEFAULT_ZORDER_PLOTS = 2
DEFAULT_ZORDER_SCATTER = 3
# fill: in front of contours, behind the grid and the outline
DEFAULT_ZORDER_FILL = 0.5
# text: in front of scatter, annotations and labels (matplotlib default: 3)
DEFAULT_ZORDER_TEXT = 4
# heatmap (tripcolor): behind the contours, the deepest data layer
DEFAULT_ZORDER_HEATMAP = -1

#: Reason of the FutureWarning about the formatting of the annotations,
#: shared by ``annotate`` and ``scatter`` so that it is emitted once per
#: diagram.
LATEX_NOTATION_WARNING_KEY = "annotate.auto_latex_notation"


def _format_text(text: object, auto_latex_notation: bool) -> object:
    """Return the text to display under the formatting rule of 4.0.0.

    Parameters
    ----------
    text : object
        Text given by the user. Objects other than str are not formatted.
    auto_latex_notation : bool
        Whether the chemical formulas in `text` are written in LaTeX
        notation by ``utils.to_latex_notation``.

    Returns
    -------
    object
        `text` with its chemical formulas formatted, or `text` itself.
    """
    if auto_latex_notation and isinstance(text, str):
        return to_latex_notation(text)
    return text


def _latex_notation_warning_message(
    func: str, text: str, shown: str, future: object
) -> str:
    """Build the FutureWarning about the formatting of an annotation."""
    return format_default_change(
        current=(
            f"`{func}` formatted {text!r} as {shown!r}, writing every "
            f"number as a subscript."
        ),
        future=(
            f"only the words that look like chemical formulas are "
            f"formatted, and only when `auto_latex_notation` of "
            f"`TernaryDiagram` is True, so it will be shown as {future!r}."
        ),
        keep=(
            "pass the text formatted with `ternary_diagram.utils.get_label` "
            "together with `auto_latex_notation=False`"
        ),
        adopt=(
            "pass `auto_latex_notation=True` to format the chemical formulas "
            "or `auto_latex_notation=False` to show the text as it is"
        ),
    )


def _resolve_annotation_text(
    text: object,
    auto_latex_notation: Optional[bool],
    *,
    default: bool,
    func: str,
    context: PostDrawContext,
) -> object:
    """Return the text to display for an annotation.

    With `auto_latex_notation` given, the rule of 4.0.0 applies. Without
    it, the v3.x display is kept (every number of a str is written as a
    subscript by ``get_label``), and a FutureWarning is emitted once per
    diagram when the rule of 4.0.0 with the setting of the diagram would
    display the text differently. A str containing ``$`` is shown as it
    is, because the subscripts inserted into mathtext by v3.x could not be
    rendered.

    Parameters
    ----------
    text : object
        Text given by the user.
    auto_latex_notation : Optional[bool]
        Value passed by the user, already checked. None means that it was
        not specified.
    default : bool
        ``auto_latex_notation`` of the diagram, which the rule of 4.0.0 uses
        when `auto_latex_notation` is not specified.
    func : str
        Name of the plotting method, shown in the warning.
    context : PostDrawContext
        State of the diagram, which records that the warning was emitted.

    Returns
    -------
    object
        The text to pass to matplotlib.
    """
    if auto_latex_notation is not None:
        return _format_text(text, auto_latex_notation)
    if not isinstance(text, str) or "$" in text:
        return text
    shown = get_label(text)
    future = _format_text(text, default)
    if shown != future and context.first_time(LATEX_NOTATION_WARNING_KEY):
        warn_external(
            _latex_notation_warning_message(func, text, shown, future)
        )
    return shown


def _resolve_colorbar_arg(
    func: str, colorbar: Optional[bool], kwargs: dict
) -> Optional[bool]:
    """Remove `flag_cbar` from `kwargs` and return the colorbar request.

    `flag_cbar` is the deprecated name of `colorbar`. When it is passed, it
    is interpreted as true or false as before and counts as an explicit
    request, after a FutureWarning about the rename. Otherwise `colorbar`
    is checked strictly.

    Parameters
    ----------
    func : str
        Name of the plotting method, shown in the messages.
    colorbar : Optional[bool]
        Value passed as `colorbar`. None means that it was not specified.
    kwargs : dict
        Keyword arguments of the plotting method. `flag_cbar` is removed
        from it when present.

    Returns
    -------
    Optional[bool]
        ``bool(flag_cbar)`` when `flag_cbar` is passed, otherwise
        `colorbar` as the built-in ``bool``, or None when it was not
        specified.

    Raises
    ------
    ValueError
        When both `flag_cbar` and `colorbar` are specified.
    TypeError
        When `colorbar` is neither None, True nor False.
    """
    flag_cbar = kwargs.pop("flag_cbar", UNSET)
    resolved = resolve_renamed_parameter(
        func=func,
        old="flag_cbar",
        new="colorbar",
        old_value=flag_cbar,
        new_value=colorbar,
    )
    if flag_cbar is not UNSET:
        # interpreted as before, as an explicit request
        return bool(resolved)
    return check_optional_bool(colorbar, "colorbar")


class TernaryDiagram:
    """Ternary diagram drawn on a matplotlib Axes.

    At construction, the diagram draws its skeleton on the Axes in 5
    parts: the border of the triangle, the grid, the tick labels, the axis
    titles (none by default) and the vertex labels (the materials). The
    look of each part can be given at construction with its ``*_kw``
    argument and changed afterwards with its change method, and the
    artists that it draws are returned by its read-only accessor:

    ===================  =========================  ==================
    At construction      After construction         Artists
    ===================  =========================  ==================
    ``border_kw``        :meth:`set_border`         `border_lines_`
    ``grid_kw``          :meth:`set_grid`           `grid_lines_`
    ``tick_kw``          :meth:`set_ticks`          `tick_labels_`
    ``axis_label_kw``    :meth:`set_axis_labels`    `axis_labels_`
    ``vertex_label_kw``  :meth:`set_vertex_labels`  `vertex_labels_`
    ===================  =========================  ==================

    Notes
    -----
    The materials are given counterclockwise from the top vertex. The
    ticks of each material are on one edge, and along that edge its value
    increases counterclockwise, from 0 to 1 at the vertex of the material
    (0 to 100 with the default format):

    - The 1st material (top vertex): on the right edge, increasing from
      the bottom right vertex to the top vertex.
    - The 2nd material (bottom left vertex): on the left edge, increasing
      from the top vertex to the bottom left vertex.
    - The 3rd material (bottom right vertex): on the bottom edge,
      increasing from the bottom left vertex to the bottom right vertex.

    The grid line of a value starts at that value on the tick edge of the
    material and runs parallel to the edge opposite to the vertex of the
    material: the points on it have that value. With ``endpoints=True``
    (see :meth:`set_ticks`), the labels of the values 0 and 1 are also
    drawn, and the label of 1 of the 2nd material and that of 0 of the 3rd
    material come close to each other at the bottom left vertex.

    A change method removes all the artists that its part drew before and
    draws new ones. The other parts, the artists drawn by the user
    (scatter points, contours, lines, annotations, ...) and the position
    and size of the Axes are not changed. Settings not given keep their
    previous values: a named item (such as ``step``) given as ``None``,
    and a matplotlib property left out. A part hidden with
    ``visible=False`` keeps its settings and is drawn with them again
    with ``visible=True``. If a change raises an error, the part keeps its
    previous settings and artists. Artists of a part that are no longer on
    the Axes, because they were removed with ``Artist.remove`` or the Axes
    was cleared, are left as they are by the change methods.

    The matplotlib properties given to a part apply to all its artists
    and override the defaults of the part, including those that differ by
    edge or by vertex (the rotation and the alignments of the labels).
    Once such a property is given, the defaults of the edges or the
    vertices cannot be restored. The ``*_kw`` arguments and the change
    methods take only the named items of the part and the properties of
    its artists (:class:`matplotlib.lines.Line2D` or
    :class:`matplotlib.text.Text`), not the other arguments of
    ``Axes.plot`` and ``Axes.text``, such as ``scalex`` or ``fontdict``:
    pass the items of a ``fontdict`` as keywords (``**fontdict``).

    A redrawn part keeps its zorder unless ``zorder`` is given: 1 for the
    border and the grid, and the default of matplotlib for the labels (3
    for text). With the same zorder, the border is always drawn over the
    grid. Among artists with the same zorder, the one added to the Axes
    later is drawn on top, so a redrawn part is drawn over the artists
    with the same zorder that were drawn before the change: for example,
    the labels over scatter points (zorder 3 by default) and, after a
    change of the grid, the grid and the border over lines drawn with
    ``zorder=1``. Give ``zorder`` to the change method or to your own
    artists to choose the order.
    """

    def __init__(
        self,
        materials: Tuple[str, str, str],
        ax: Optional[matplotlib.axes.Axes] = None,
        auto_latex_notation: bool = True,
        *,
        tight_layout: Optional[bool] = None,
        border_kw: Optional[Mapping[str, Any]] = None,
        grid_kw: Optional[Mapping[str, Any]] = None,
        tick_kw: Optional[Mapping[str, Any]] = None,
        axis_label_kw: Optional[Mapping[str, Any]] = None,
        vertex_label_kw: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """
        Make instance.

        Create borders, etc. for triangulation diagrams.


        Parameters
        ----------
        materials : Tuple[str, str, str]
            A one-dimensional list of compounds that constitute an endpoint
            when generating a ternary_diagram.

            Specify counterclockwise from the top vertex of the triangle.

        ax : Optional[matplotlib.axes.Axes], optional
            Axes object to draw a diagram. If None, automatically generate.
            , by default None

        auto_latex_notation : bool, optional
            If True, the LaTeX notation of the material is automatically
            generated. If False, the material is displayed as it is. In
            ternary-diagram 4.0.0, it will also decide whether
            :meth:`annotate` and the annotations of :meth:`scatter` format
            the chemical formulas when their own `auto_latex_notation` is
            not given, by default True

        tight_layout : bool or None, optional
            Whether to adjust the figure margins with
            ``Figure.tight_layout()`` after each plotting call. ``True``
            adjusts them, and ``False`` leaves the layout untouched.
            ``None`` keeps the v3.x behavior: the margins are adjusted and
            a FutureWarning is emitted once per diagram. The default will
            change to ``tight_layout=False`` in ternary-diagram 4.0.0.
            Figures with a layout engine (e.g. ``layout="constrained"``)
            and subfigures are never adjusted, whatever the value,
            by default None

        border_kw : dict or None, optional
            Settings of the border of the triangle. Passing ``border_kw``
            is equivalent to calling ``set_border(**border_kw)`` right
            after construction; see :meth:`set_border` for the accepted
            keys. ``None`` draws the border with the default appearance,
            by default None

        grid_kw : dict or None, optional
            Settings of the grid. Passing ``grid_kw`` is equivalent to
            calling ``set_grid(**grid_kw)`` right after construction; see
            :meth:`set_grid` for the accepted keys. ``None`` draws the
            grid with the default appearance, by default None

        tick_kw : dict or None, optional
            Settings of the tick labels. Passing ``tick_kw`` is equivalent
            to calling ``set_ticks(**tick_kw)`` right after construction;
            see :meth:`set_ticks` for the accepted keys. ``None`` draws the
            tick labels with the default appearance, by default None

        axis_label_kw : dict or None, optional
            Settings of the axis titles along the edges. Passing
            ``axis_label_kw`` is equivalent to calling
            ``set_axis_labels(**axis_label_kw)`` right after construction;
            see :meth:`set_axis_labels` for the accepted keys, such as
            ``labels`` for the titles. ``None`` uses the default
            appearance, which draws no titles, by default None

        vertex_label_kw : dict or None, optional
            Settings of the vertex labels. Passing ``vertex_label_kw`` is
            equivalent to calling ``set_vertex_labels(**vertex_label_kw)``
            right after construction; see :meth:`set_vertex_labels` for
            the accepted keys, except ``labels``: the labels are given by
            `materials`, and ``labels`` here raises a ValueError. ``None``
            draws the vertex labels with the default appearance,
            by default None


        Examples
        --------
        >>> from ternary_diagram import TernaryDiagram

        >>> # You can set `ax` to select which axes to draw.
        >>> # If not, the current axes will be used.
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"])

        >>> # scatter
        >>> td.scatter(vector=[[1, 1, 1], [1, 2, 3]], z=[0, 1])
        >>> # You can set some options in `plt.scatter` like `marker`, `c` etc.
        >>> td.scatter([[2, 1, 3], [3, 2, 1]], marker="s", c="#022c5e", s=30)

        >>> # line plot
        >>> # You can set some options in `plt.plot` like `lw`, `c`, and so on.
        >>> td.plot([[1, 1, 1], [1, 2, 3]], color="black")

        >>> # save figure
        >>> td.fig.savefig("figure.png", dpi=144)


        """

        # check `ax`
        self.__ax = check_ax(ax)
        # check `materials` before changing anything on `ax`. A str is a
        # sequence of 1-letter materials, as in ternary-diagram v3.
        try:
            material_items = tuple(materials)
        except TypeError as error:
            raise TypeError(
                "`materials` must be a sequence of 3 materials, such as a "
                f"list or a tuple, but got {materials!r}."
            ) from error
        if len(material_items) < 3:
            raise ValueError(
                "`materials` needs 3 materials, for the top, bottom left and "
                f"bottom right vertices, but got {len(material_items)}: "
                f"{material_items!r}."
            )
        # check `tight_layout` before drawing anything on `ax`
        self.__post_draw_context = PostDrawContext(
            tight_layout=check_optional_bool(tight_layout, "tight_layout")
        )
        part_kw = {
            "border_kw": border_kw,
            "grid_kw": grid_kw,
            "tick_kw": tick_kw,
            "axis_label_kw": axis_label_kw,
            "vertex_label_kw": vertex_label_kw,
        }
        # check the settings of the parts before changing anything on `ax`.
        # The parts check their content when they are drawn.
        for name, kw in part_kw.items():
            if kw is not None and not (
                isinstance(kw, Mapping)
                and all(isinstance(key, str) for key in kw)
            ):
                raise TypeError(
                    f"`{name}` must be None or a mapping of str names to "
                    f"values, such as a dict, but got {kw!r}."
                )
        if vertex_label_kw is not None:
            _check_vertex_label_kw(vertex_label_kw)
        self.__fig = self.ax.figure

        # Allign the aspect
        self.ax.set_aspect("equal", adjustable="datalim")

        # 目盛りや目盛りにつくラベルを表示しない
        self.ax.tick_params(
            labelbottom=False,
            labelleft=False,
            labelright=False,
            labeltop=False,
        )
        self.ax.tick_params(bottom=False, left=False, right=False, top=False)

        # clear borders
        for position in ("bottom", "left", "right", "top"):
            self.ax.spines[position].set_visible(False)

        # Draw the parts of the skeleton with their initial settings. The
        # parts drawn before a part that fails are removed.
        self.__skeleton = _Skeleton(
            self.ax,
            material_items,
            auto_latex_notation,
            zorder=DEFAULT_ZORDER_GRIDS,
            **{name: {} if kw is None else kw for name, kw in part_kw.items()},
        )

        # Formatting of the annotations under the rule of 4.0.0, shared with
        # the plotting methods that take `auto_latex_notation=None`.
        self.__auto_latex_notation = bool(auto_latex_notation)

        # FIXME: mypy
        # 二次元に変換したデータを保存しておく (Save the data converted to two dimensions)
        self.x_ = defaultdict(list)
        self.y_ = defaultdict(list)

    @property
    def ax(self) -> matplotlib.axes.Axes:
        """Axes object"""
        return self.__ax

    @ax.setter
    def ax(self, _ax):
        raise AttributeError("ax is read-only")

    @property
    def fig(self) -> matplotlib.figure.Figure:
        """Figure object"""
        return self.__fig

    @property
    def border_lines_(self) -> List[matplotlib.lines.Line2D]:
        """Lines of the border drawn now.

        Use them to adjust a single edge. Each access returns a new list.
        :meth:`set_border` replaces the lines with new ones, which drops
        the changes made to them directly. To hide the border, use
        ``set_border(visible=False)`` rather than removing the lines.

        Returns
        -------
        List[matplotlib.lines.Line2D]
            A new list of the bottom, left and right edges, empty while the
            border is hidden.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> bottom, left, right = td.border_lines_
        >>> bottom.set_color("tab:blue")
        >>> bottom.get_color(), left.get_color()
        ('tab:blue', 'black')
        """
        return cast(
            List[matplotlib.lines.Line2D], self.__skeleton.artists("border")
        )

    @border_lines_.setter
    def border_lines_(self, _lines):
        raise AttributeError("border_lines_ is read-only")

    @property
    def grid_lines_(self) -> List[matplotlib.lines.Line2D]:
        """Lines of the grid drawn now.

        Use them to adjust single grid lines. Each access returns a new
        list. :meth:`set_grid` replaces the lines with new ones, which
        drops the changes made to them directly. To hide the grid, use
        ``set_grid(visible=False)`` rather than removing the lines.

        Returns
        -------
        List[matplotlib.lines.Line2D]
            A new list of the lines of the 1st, 2nd and 3rd materials in
            this order, each in ascending order of value, empty while the
            grid is hidden.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> lines = td.grid_lines_
        >>> len(lines)  # 9 values for each of the 3 materials
        27
        >>> lines[4].set_linestyle("--")  # 0.5 of the 1st material
        """
        return cast(
            List[matplotlib.lines.Line2D], self.__skeleton.artists("grid")
        )

    @grid_lines_.setter
    def grid_lines_(self, _lines):
        raise AttributeError("grid_lines_ is read-only")

    @property
    def tick_labels_(self) -> List[matplotlib.text.Text]:
        """Tick labels drawn now.

        Use them to adjust single labels, such as one of the labels that
        come close at the bottom left vertex with ``endpoints=True`` (see
        :meth:`set_ticks`). Each access returns a new list.
        :meth:`set_ticks` replaces the labels with new ones, which drops
        the changes made to them directly. To hide the tick labels, use
        ``set_ticks(visible=False)`` rather than removing the labels.

        Returns
        -------
        List[matplotlib.text.Text]
            A new list of the tick labels in ascending order of value, each
            value for the 1st, 2nd and 3rd materials in this order, empty
            while the tick labels are hidden.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> labels = td.tick_labels_
        >>> len(labels)  # 9 values for each of the 3 materials
        27
        >>> [label.get_text() for label in labels[:3]]  # 0.1 of each
        ['10', '10', '10']
        >>> labels[12].set_color("tab:red")  # 0.5 of the 1st material
        """
        return cast(
            List[matplotlib.text.Text], self.__skeleton.artists("ticks")
        )

    @tick_labels_.setter
    def tick_labels_(self, _labels):
        raise AttributeError("tick_labels_ is read-only")

    @property
    def axis_labels_(self) -> List[matplotlib.text.Text]:
        """Axis titles drawn now.

        Use them to adjust a single title. Each access returns a new list.
        :meth:`set_axis_labels` replaces the titles with new ones, which
        drops the changes made to them directly. To hide the titles, use
        ``set_axis_labels(visible=False)`` rather than removing them.

        Returns
        -------
        List[matplotlib.text.Text]
            A new list of the drawn axis titles in the order of the
            materials, without the materials that have no title, empty
            while the axis titles are hidden. No titles are drawn by
            default.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> td.axis_labels_  # no titles by default
        []
        >>> _ = td.set_axis_labels([None, None, "TiO2 / mol%"])
        >>> [title.get_text() for title in td.axis_labels_]
        ['TiO2 / mol%']
        """
        return cast(
            List[matplotlib.text.Text], self.__skeleton.artists("axis_labels")
        )

    @axis_labels_.setter
    def axis_labels_(self, _labels):
        raise AttributeError("axis_labels_ is read-only")

    @property
    def vertex_labels_(self) -> List[matplotlib.text.Text]:
        """Vertex labels drawn now.

        Use them to adjust a single label. Each access returns a new list.
        :meth:`set_vertex_labels` replaces the labels with new ones, which
        drops the changes made to them directly. To hide the labels, use
        ``set_vertex_labels(visible=False)`` rather than removing them.

        Returns
        -------
        List[matplotlib.text.Text]
            A new list of the labels of the top, bottom left and bottom
            right vertices, empty while the vertex labels are hidden.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> top, left, right = td.vertex_labels_
        >>> top.get_text()
        'Li$_{2}$O'
        >>> top.set_color("tab:red")
        """
        return cast(
            List[matplotlib.text.Text],
            self.__skeleton.artists("vertex_labels"),
        )

    @vertex_labels_.setter
    def vertex_labels_(self, _labels):
        raise AttributeError("vertex_labels_ is read-only")

    def set_border(
        self, visible: Optional[bool] = None, **kwargs: Any
    ) -> List[matplotlib.lines.Line2D]:
        """Redraw the border of the triangle with new settings.

        The lines of the border are removed and drawn again with the
        settings given, merged with the current ones: settings not given
        keep their previous values. The other parts and the artists drawn
        by the user are not changed. If an error is raised, the border
        keeps its previous settings and lines.

        Parameters
        ----------
        visible : bool or None, optional
            Whether to draw the border. ``None`` keeps the current setting
            (initially True), by default None
        **kwargs
            Properties of :class:`matplotlib.lines.Line2D`, or their
            aliases such as ``lw``, applied to all lines of the border.
            They override the defaults (``color="black"``,
            ``linewidth=2``, ``linestyle="-"``, ``zorder=1``), and
            properties not given keep their current values. Arguments of
            ``Axes.plot`` that are not properties, such as ``scalex``, are
            not accepted.

        Returns
        -------
        List[matplotlib.lines.Line2D]
            A new list of the border lines drawn by this call (the bottom,
            left and right edges), the same lines as `border_lines_`. It is
            empty when the border is hidden.

        Raises
        ------
        TypeError
            If `visible` is not a bool, if a property is given by both its
            name and an alias, or if it is ``xdata`` or ``ydata``, which
            the border sets itself.
        AttributeError
            If a keyword is not a property of ``Line2D``.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> lines = td.set_border(linewidth=1, linestyle="--")
        >>> len(lines), lines[0].get_linewidth()
        (3, 1.0)
        >>> td.set_border(visible=False)
        []
        >>> lines = td.set_border(visible=True)  # keeps the dashed lines
        >>> lines[0].get_linestyle()
        '--'

        ``border_kw`` at construction is equivalent to calling
        ``set_border`` with the same settings right after construction:

        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(
        ...     ["Li2O", "La2O3", "TiO2"],
        ...     ax=ax,
        ...     border_kw={"linewidth": 1, "linestyle": "--"},
        ... )
        >>> len(td.border_lines_), td.border_lines_[0].get_linewidth()
        (3, 1.0)
        """
        return cast(
            List[matplotlib.lines.Line2D],
            self.__skeleton.update("border", visible=visible, **kwargs),
        )

    def set_grid(
        self,
        visible: Optional[bool] = None,
        *,
        step: Optional[float] = None,
        **kwargs: Any,
    ) -> List[matplotlib.lines.Line2D]:
        """Redraw the grid with new settings.

        The grid lines are drawn for each material at the multiples of
        `step` strictly between 0 and 1. The line of a value starts at
        that value on the tick edge of the material and runs parallel to
        the edge opposite to the vertex of the material (see the Notes of
        :class:`TernaryDiagram`).

        All the grid lines are removed and drawn again with the settings
        given, merged with the current ones: settings not given keep their
        previous values. The border is then moved back over the new grid
        lines. The other parts and the artists drawn by the user are not
        changed. If an error is raised, the grid keeps its previous
        settings and lines.

        Parameters
        ----------
        visible : bool or None, optional
            Whether to draw the grid. ``None`` keeps the current setting
            (initially True), by default None
        step : float or None, optional
            Interval of the grid lines as a fraction in (0, 1], such as
            0.05 for every 5 %. It is independent of the interval of the
            tick labels. ``None`` keeps the current setting (initially
            0.1), by default None
        **kwargs
            Properties of :class:`matplotlib.lines.Line2D`, or their
            aliases such as ``lw``, applied to all grid lines. They
            override the defaults (``color="gray"``, ``linewidth=0.5``,
            ``zorder=1``), and properties not given keep their current
            values. Arguments of ``Axes.plot`` that are not properties,
            such as ``scalex``, are not accepted.

        Returns
        -------
        List[matplotlib.lines.Line2D]
            A new list of the grid lines drawn by this call, the same lines
            as `grid_lines_`. It is empty when the grid is hidden.

        Raises
        ------
        TypeError
            If `visible` is not a bool, if `step` is not a real number, if
            a property is given by both its name and an alias, or if it is
            ``xdata`` or ``ydata``, which the grid sets itself.
        ValueError
            If `step` is not finite or not in (0, 1].
        AttributeError
            If a keyword is not a property of ``Line2D``.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> lines = td.set_grid(step=0.05, color="lightgray")
        >>> len(lines)  # 19 values for each of the 3 materials
        57
        >>> lines = td.set_grid(linestyle=":")  # keeps step and color
        >>> len(lines), lines[0].get_color()
        (57, 'lightgray')

        ``grid_kw`` at construction is equivalent to calling ``set_grid``
        with the same settings right after construction:

        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(
        ...     ["Li2O", "La2O3", "TiO2"],
        ...     ax=ax,
        ...     grid_kw={"step": 0.05, "color": "lightgray"},
        ... )
        >>> len(td.grid_lines_)
        57
        """
        return cast(
            List[matplotlib.lines.Line2D],
            self.__skeleton.update(
                "grid", visible=visible, step=step, **kwargs
            ),
        )

    def set_ticks(
        self,
        visible: Optional[bool] = None,
        *,
        step: Optional[float] = None,
        fmt: Optional[TickFormat] = None,
        endpoints: Optional[bool] = None,
        **kwargs: Any,
    ) -> List[matplotlib.text.Text]:
        """Redraw the tick labels with new settings.

        The tick labels of the 1st material (top vertex) are on the right
        edge, those of the 2nd material (bottom left vertex) on the left
        edge and those of the 3rd material (bottom right vertex) on the
        bottom edge. Along each edge the values increase counterclockwise,
        toward the vertex of the material: from the bottom right vertex to
        the top vertex on the right edge, from the top vertex to the
        bottom left vertex on the left edge, and from the bottom left
        vertex to the bottom right vertex on the bottom edge.

        All the tick labels are removed and drawn again with the settings
        given, merged with the current ones: settings not given keep their
        previous values. The other parts and the artists drawn by the user
        are not changed. If an error is raised, the tick labels keep their
        previous settings and artists.

        Parameters
        ----------
        visible : bool or None, optional
            Whether to draw the tick labels. ``None`` keeps the current
            setting (initially True), by default None
        step : float or None, optional
            Interval of the tick labels as a fraction in (0, 1], such as
            0.25 for every 25 %. It is independent of the interval of the
            grid. ``None`` keeps the current setting (initially 0.1),
            by default None
        fmt : str, callable or None, optional
            Format of the labels, applied to the values as fractions in
            [0, 1]: ``"percent"`` (0.1 gives ``"10"``), ``"fraction"``
            (0.1 gives ``"0.1"``), a %-style or {}-style format string such
            as ``"%.2f"`` or ``"{:.0%}"``, or a callable that takes the
            value as a float and returns the label (see
            :func:`ternary_diagram.utils.get_tick_formatter`). A callable
            is first called when the labels are drawn, not when it is
            given: given while the labels are hidden, its errors are raised
            only when they are shown again (pass a valid `fmt` together
            with ``visible=True`` in that case). ``None`` keeps the
            current setting (initially ``"percent"``), by default None
        endpoints : bool or None, optional
            Whether to also label the values 0 and 1 at the vertices.
            ``None`` keeps the current setting (initially False),
            by default None
        **kwargs
            Properties of :class:`matplotlib.text.Text`, or their aliases
            such as ``ha``, applied to the labels of all edges. They
            override the default ``fontsize=10`` and the rotation and the
            alignments that differ by edge, and properties not given keep
            their current values. Once ``rotation`` or an alignment is
            given, the different defaults of the edges cannot be restored:
            ``rotation=None`` draws the labels of all edges at 0 degrees.
            Arguments of ``Axes.text`` that are not properties are not
            accepted: pass the items of a ``fontdict`` as keywords.

        Returns
        -------
        List[matplotlib.text.Text]
            A new list of the tick labels drawn by this call, the same
            labels as `tick_labels_`. It is empty when the tick labels are
            hidden.

        Raises
        ------
        TypeError
            If `visible` or `endpoints` is not a bool, if `step` is not a
            real number, if `fmt` is neither a str nor a callable, if a
            property is given by both its name and an alias, or if it is
            ``x``, ``y`` or ``text``, which the tick labels set themselves.
        ValueError
            If `step` is not finite or not in (0, 1], or if `fmt` is a str
            that cannot be used as a format.
        AttributeError
            If a keyword is not a property of ``Text``.
        Exception
            Whatever a callable `fmt` raises.

        Notes
        -----
        With ``endpoints=True``, the label of 1 of the 2nd material and
        that of 0 of the 3rd material come close to each other at the
        bottom left vertex. Adjust or hide one of them through
        `tick_labels_` if they overlap.

        The tick labels keep the default zorder of matplotlib for text (3)
        unless ``zorder`` is given. Among artists with the same zorder, the
        one added to the Axes later is drawn on top, so the redrawn labels
        are drawn over the artists with zorder 3 drawn before this call,
        such as scatter points. Give ``zorder`` to choose the order.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> labels = td.set_ticks(step=0.25, fmt="{:.0%}")
        >>> len(labels)  # 3 values for each of the 3 materials
        9
        >>> [label.get_text() for label in labels[::3]]  # the 1st material
        ['25%', '50%', '75%']
        >>> labels = td.set_ticks(endpoints=True)  # keeps step and fmt
        >>> [label.get_text() for label in labels[::3]]
        ['0%', '25%', '50%', '75%', '100%']

        ``tick_kw`` at construction is equivalent to calling ``set_ticks``
        with the same settings right after construction:

        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(
        ...     ["Li2O", "La2O3", "TiO2"],
        ...     ax=ax,
        ...     tick_kw={"step": 0.25, "fmt": "{:.0%}"},
        ... )
        >>> [label.get_text() for label in td.tick_labels_[::3]]
        ['25%', '50%', '75%']
        """
        return cast(
            List[matplotlib.text.Text],
            self.__skeleton.update(
                "ticks",
                visible=visible,
                step=step,
                fmt=fmt,
                endpoints=endpoints,
                **kwargs,
            ),
        )

    def set_axis_labels(
        self,
        labels: Optional[Sequence[Optional[str]]] = None,
        *,
        visible: Optional[bool] = None,
        pad: Optional[float] = None,
        **kwargs: Any,
    ) -> List[matplotlib.text.Text]:
        """Redraw the axis titles with new settings.

        The title of a material is drawn outside the middle of the edge
        that carries its ticks, parallel to the edge and never upside
        down: the 1st material on the right edge, the 2nd on the left edge
        and the 3rd on the bottom edge. No titles are drawn by default.
        The titles are shown as given, without the conversion to chemical
        formulas applied to the vertex labels; write mathtext such as
        ``"Li$_2$O"`` for subscripts.

        All the titles are removed and drawn again with the settings
        given, merged with the current ones: settings not given keep their
        previous values. The other parts and the artists drawn by the user
        are not changed. If an error is raised, the titles keep their
        previous settings and artists.

        Parameters
        ----------
        labels : sequence of (str or None), or None, optional
            Titles of the 1st, 2nd and 3rd materials, such as a list, a
            tuple, a numpy array or a pandas Index (for example
            ``df.columns[:3] + " / mol%"``). A title that is ``None`` or
            ``""`` is not drawn. ``None`` keeps the current titles
            (initially ``(None, None, None)``: no titles), by default None
        visible : bool or None, optional
            Whether to draw the titles. ``None`` keeps the current setting
            (initially True), by default None
        pad : float or None, optional
            Distance from the midpoints of the edges to the centers of the
            titles in data coordinates, where each edge has length 1.
            Positive values move the titles away from the triangle. As the
            text is sized in points, on a small figure (about 3 by 3
            inches) the titles may touch the tick labels: increase `pad`
            or decrease ``fontsize`` then. ``None`` keeps the current
            setting (initially 0.15), by default None
        **kwargs
            Properties of :class:`matplotlib.text.Text`, or their aliases
            such as ``ha``, applied to all titles. They override the
            defaults (``fontsize=12``, ``horizontalalignment="center"``,
            ``verticalalignment="center"``) and the rotation that differs
            by edge, and properties not given keep their current values.
            Once ``rotation`` is given, the different rotations of the
            edges cannot be restored. Arguments of ``Axes.text`` that are
            not properties are not accepted: pass the items of a
            ``fontdict`` as keywords.

        Returns
        -------
        List[matplotlib.text.Text]
            A new list of the axis titles drawn by this call in the order
            of the materials, the same titles as `axis_labels_`. It is
            empty when the axis titles are hidden or none is given.

        Raises
        ------
        TypeError
            If `labels` is a str, bytes, a mapping, a set or not iterable,
            if a title is neither a str nor None, if `visible` is not a
            bool, if `pad` is not a real number, if a property is given by
            both its name and an alias, or if it is ``x``, ``y`` or
            ``text``, which the titles set themselves.
        ValueError
            If `labels` does not have 3 items, or if `pad` is not finite.
        AttributeError
            If a keyword is not a property of ``Text``.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> names = ["Li2O / mol%", "La2O3 / mol%", "TiO2 / mol%"]
        >>> titles = td.set_axis_labels(names, fontsize=10)
        >>> [title.get_text() for title in titles]
        ['Li2O / mol%', 'La2O3 / mol%', 'TiO2 / mol%']
        >>> titles = td.set_axis_labels([None, None, "TiO2 / mol%"])
        >>> [(title.get_text(), title.get_fontsize()) for title in titles]
        [('TiO2 / mol%', 10.0)]

        ``axis_label_kw`` at construction is equivalent to calling
        ``set_axis_labels`` with the same settings right after
        construction:

        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(
        ...     ["Li2O", "La2O3", "TiO2"],
        ...     ax=ax,
        ...     axis_label_kw={"labels": names, "fontsize": 10},
        ... )
        >>> [title.get_text() for title in td.axis_labels_]
        ['Li2O / mol%', 'La2O3 / mol%', 'TiO2 / mol%']
        """
        return cast(
            List[matplotlib.text.Text],
            self.__skeleton.update(
                "axis_labels",
                labels=labels,
                visible=visible,
                pad=pad,
                **kwargs,
            ),
        )

    def set_vertex_labels(
        self,
        labels: Optional[Sequence[str]] = None,
        *,
        visible: Optional[bool] = None,
        offsets: Optional[Sequence[Tuple[float, float]]] = None,
        **kwargs: Any,
    ) -> List[matplotlib.text.Text]:
        """Redraw the vertex labels with new settings.

        The labels are drawn next to the top, bottom left and bottom right
        vertices, initially with the first 3 materials. Whether they are
        converted to chemical formulas (``"Li2O"`` is shown as
        ``"Li$_{2}$O"``) is decided by ``auto_latex_notation`` at
        construction, which also applies to the labels given here and
        cannot be changed by this method.

        All the labels are removed and drawn again with the settings
        given, merged with the current ones: settings not given keep their
        previous values. The other parts and the artists drawn by the user
        are not changed. If an error is raised, the labels keep their
        previous settings and artists.

        Parameters
        ----------
        labels : sequence of str or None, optional
            Labels of the top, bottom left and bottom right vertices, such
            as a list, a tuple, a numpy array or a pandas Index (for
            example ``df.columns[:3]``). With ``auto_latex_notation``, each
            label must be a str; without it, any object is shown as
            ``Axes.text`` shows it. ``None`` keeps the current labels
            (initially the first 3 materials), by default None
        visible : bool or None, optional
            Whether to draw the labels. ``None`` keeps the current setting
            (initially True), by default None
        offsets : sequence of (float, float) or None, optional
            Offsets ``(dx, dy)`` of the labels from the top, bottom left
            and bottom right vertices in data coordinates, where each edge
            has length 1: 3 pairs of finite real numbers, such as a list of
            tuples or a numpy array of shape (3, 2). Convert a pandas
            DataFrame with ``to_numpy()`` first. ``None`` keeps the current
            setting (initially ``((0, 0.02), (0, -0.05), (0, -0.05))``),
            by default None
        **kwargs
            Properties of :class:`matplotlib.text.Text`, or their aliases
            such as ``ha``, applied to all labels. They override the
            default ``fontsize=16`` and the alignments that differ by
            vertex, and properties not given keep their current values.
            Once an alignment is given, the different alignments of the
            vertices cannot be restored. Arguments of ``Axes.text`` that
            are not properties are not accepted: pass the items of a
            ``fontdict`` as keywords.

        Returns
        -------
        List[matplotlib.text.Text]
            A new list of the vertex labels drawn by this call (the top,
            bottom left and bottom right vertices), the same labels as
            `vertex_labels_`. It is empty when the vertex labels are
            hidden.

        Raises
        ------
        TypeError
            If `labels`, `offsets` or a pair of `offsets` is a str, bytes,
            a mapping, a set or not iterable, if a value of `offsets` is
            not a real number, if `visible` is not a bool, if a property is
            given by both its name and an alias, or if it is ``x``, ``y``
            or ``text``, which the labels set themselves.
        ValueError
            If `labels` or `offsets` does not have 3 items, if a pair of
            `offsets` does not have 2 items, if a value of `offsets` is not
            finite, or, with ``auto_latex_notation``, if a label is not a
            str.
        AttributeError
            If a keyword is not a property of ``Text``.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> labels = td.set_vertex_labels(fontsize=12)
        >>> [label.get_text() for label in labels]
        ['Li$_{2}$O', 'La$_{2}$O$_{3}$', 'TiO$_{2}$']
        >>> offsets = [(0, 0.02), (-0.02, -0.04), (0.02, -0.04)]
        >>> labels = td.set_vertex_labels(offsets=offsets)  # keeps fontsize
        >>> labels[1].get_position(), labels[1].get_fontsize()
        ((-0.02, -0.04), 12.0)
        >>> labels = td.set_vertex_labels(["Li2O", "La2O3", "SrTiO3"])
        >>> labels[2].get_text()
        'SrTiO$_{3}$'

        ``vertex_label_kw`` at construction is equivalent to calling
        ``set_vertex_labels`` with the same settings right after
        construction. It cannot contain ``labels``, which are given by the
        materials:

        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(
        ...     ["Li2O", "La2O3", "TiO2"],
        ...     ax=ax,
        ...     vertex_label_kw={"fontsize": 12, "offsets": offsets},
        ... )
        >>> label = td.vertex_labels_[1]
        >>> label.get_position(), label.get_fontsize()
        ((-0.02, -0.04), 12.0)
        """
        return cast(
            List[matplotlib.text.Text],
            self.__skeleton.update(
                "vertex_labels",
                labels=labels,
                visible=visible,
                offsets=offsets,
                **kwargs,
            ),
        )

    def scatter(
        self,
        vector: ArrayLike,
        z: Optional[ArrayLike] = None,
        z_min: Optional[Number] = None,
        z_max: Optional[Number] = None,
        annotations: Optional[List[str]] = None,
        colorbar: Optional[bool] = None,
        *,
        auto_latex_notation: Optional[bool] = None,
        **kwargs,
    ) -> matplotlib.collections.PathCollection:
        """
        Plot scatter points.

        This is a wrapper of `matplotlib.pyplot.scatter`.

        Parameters
        ----------
        vector : ArrayLike | shape = (n, 3)
            vector : ArrayLike | shape = (n, 3)
            2D vector whose shape is (n, 3). It represents the ratio of
            each component (the sum does not have to be 1).

            The vectors are specified in semi-clockwise order starting
            from the vertex of the triangle.

        z : ArrayLike, shape = (n,), optional
            Values used to color the points. It cannot be used together
            with `c`. , by default None

        z_min : Optional[Number] , optional
            Lower limit of the color scale. `vmin` is accepted as an alias.
            , by default None

        z_max : Optional[Number], optional
            Upper limit of the color scale. `vmax` is accepted as an alias.
            , by default None

        annotations : Optional[List[str]], optional
            instance annotations, by default None
            if None, nothing is annotated.

        colorbar : bool or None, optional
            Whether to add a colorbar automatically when the points are
            colored by `z`. ``True`` adds one and ``False`` adds none;
            without `z`, no colorbar is added whatever the value. ``None``
            keeps the v3.x behavior: it adds one, and when the diagram
            already has a colorbar, it also emits a FutureWarning once per
            diagram. In ternary-diagram 4.0.0, ``None`` will add none to a
            diagram that already has a colorbar. The colorbars counted are
            those added through this TernaryDiagram (automatically or with
            its ``colorbar()`` method) and not removed; colorbars added
            directly with matplotlib, such as with ``fig.colorbar``, are not
            counted, by default None

        flag_cbar : bool, optional
            Deprecated alias of `colorbar`, interpreted as true or false as
            before. Passing it emits a FutureWarning; it will be removed in
            ternary-diagram 4.0.0, so pass `colorbar` instead. Passing it
            together with `colorbar` raises a ValueError. When it is
            omitted, `colorbar` decides.

        auto_latex_notation : bool or None, optional
            Whether to write the chemical formulas in `annotations` in LaTeX
            notation (``"Li2O"`` to ``"Li$_{2}$O"``). ``True`` formats each
            word that looks like a chemical formula (see
            :func:`ternary_diagram.utils.to_latex_notation`) and keeps the
            other words, and ``False`` shows the text as it is. ``None``
            keeps the v3.x behavior: every number in a str is written as a
            subscript (``"Sample 1"`` to ``"Sample $_{1}$"``), except in a
            text containing ``$``, and a FutureWarning is emitted once per
            diagram when the display will change. In ternary-diagram
            4.0.0, ``None`` will follow `auto_latex_notation` of
            :class:`TernaryDiagram`, by default None

        kwargs : parameter of `matplotlib.pyplot.scatter`, optional
            For example, `marker='x'`, `facecolor='blue'` etc.

            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.scatter.html.


        Returns
        -------
        matplotlib.collections.PathCollection
            A collection of scatter points.
        """  # noqa: E501

        colorbar = _resolve_colorbar_arg("scatter", colorbar, kwargs)
        auto_latex_notation = check_optional_bool(
            auto_latex_notation, "auto_latex_notation"
        )
        plotter = _ScatterPlotter(
            vector=vector,
            ax=self.ax,
            z=z,
            z_min=z_min,
            z_max=z_max,
            annotations=annotations,
            colorbar=colorbar,
            post_draw_context=self.__post_draw_context,
            auto_latex_notation=auto_latex_notation,
            default_auto_latex_notation=self.__auto_latex_notation,
            **kwargs,
        )
        self._append_x_y(plotter)
        return plotter.collection_

    def contour(
        self,
        vector: ArrayLike,
        z: Optional[ArrayLike] = None,
        z_min: Optional[Number] = None,
        z_max: Optional[Number] = None,
        fill: bool = True,
        colorbar: Optional[bool] = None,
        **kwargs,
    ) -> TriContourSet:
        """
        To create a contour map.

        This is a wrapper of `plt.tricontour` or `plt.tricontourf`.

        See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.tricontour.html
        or https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.tricontourf.html

        - When fill is `True`, this is a wrapper of `plt.tricontourf`.
        - When fill is `False`, this is a wrapper of `plt.tricontour`.

        Parameters
        ----------
        vector : ArrayLike | shape = (n, 3)
            2D vector whose shape is (n, 3). It represents the ratio of
            each component (the sum does not have to be 1).

            The vectors are specified in semi-clockwise order starting
            from the vertex of the triangle.

        z : Optional[ArrayLike], shape = (n,)
            , by default None

        z_min : Optional[Number], optional
            Lower limit of the automatic levels. If None, the minimum of `z`.
            , by default None

        z_max : Optional[Number], optional
            Upper limit of the automatic levels. If None, the maximum of `z`.
            , by default None

        colorbar : bool or None, optional
            Whether to add a colorbar automatically for the contours
            colored by `z`. ``True`` adds one and ``False`` adds none.
            ``None`` keeps the v3.x behavior: it adds one, and when the
            diagram already has a colorbar, it also emits a FutureWarning
            once per diagram. In ternary-diagram 4.0.0, ``None`` will add
            none to a diagram that already has a colorbar. The colorbars
            counted are those added through this TernaryDiagram
            (automatically or with its ``colorbar()`` method) and not
            removed; colorbars added directly with matplotlib, such as with
            ``fig.colorbar``, are not counted, by default None

        flag_cbar : bool, optional
            Deprecated alias of `colorbar`, interpreted as true or false as
            before. Passing it emits a FutureWarning; it will be removed in
            ternary-diagram 4.0.0, so pass `colorbar` instead. Passing it
            together with `colorbar` raises a ValueError. When it is
            omitted, `colorbar` decides.

        kwargs : parameter of `matplotlib.pyplot.contour`, optional
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.contour.html.

            If `levels` is given, it is used instead of the automatic
            levels and cannot be combined with `z_min` or `z_max`.

        Returns
        -------
        matplotlib.tri.tricontour.TriContourSet
            A collection of contour lines.
        """  # noqa: E501

        colorbar = _resolve_colorbar_arg("contour", colorbar, kwargs)
        plotter = _ContourPlotter(
            vector=vector,
            ax=self.ax,
            z=z,
            z_min=z_min,
            z_max=z_max,
            fill=fill,
            colorbar=colorbar,
            post_draw_context=self.__post_draw_context,
            **kwargs,
        )
        self._append_x_y(plotter)
        return plotter.collection_

    def plot(
        self, vector: ArrayLike, **kwargs
    ) -> List[matplotlib.lines.Line2D]:
        """
        To draw a tie line.

        This is a wrapper of `matplotlib.pyplot.plot`.

        Parameters
        ----------
        vector : ArrayLike | shape = (n, 3)
            vector : ArrayLike | shape = (n, 3)
            2D vector whose shape is (n, 3). It represents the ratio of
            each component (the sum does not have to be 1).

            The vectors are specified in semi-clockwise order starting
            from the vertex of the triangle.

        kwargs : parameter of `matplotlib.pyplot.plot`, optional
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.plot.html


        Returns
        -------
        List[matplotlib.lines.Line2D]
            lines.
        """  # noqa: E501

        plotter = _LinePlotter(
            vector=vector,
            ax=self.ax,
            post_draw_context=self.__post_draw_context,
            **kwargs,
        )
        self._append_x_y(plotter)
        return plotter.collection_

    def annotate(
        self,
        text: str,
        vector: ArrayLike,
        *,
        auto_latex_notation: Optional[bool] = None,
        **kwargs,
    ) -> matplotlib.text.Annotation:
        """Annotate text.

        This is a wrapper of `matplotlib.pyplot.annotate`.

        Parameters
        ----------
        text : str
            Text to be displayed.

        vector : 1D ArrayLike, whose length is 3.
            vector : ArrayLike | shape = (3,)
            It represents the ratio of
            each component (the sum does not have to be 1).

            The vectors are specified in semi-clockwise order starting
            from the vertex of the triangle.

        auto_latex_notation : bool or None, optional
            Whether to write the chemical formulas in `text` in LaTeX
            notation (``"Li2O"`` to ``"Li$_{2}$O"``). ``True`` formats each
            word that looks like a chemical formula (see
            :func:`ternary_diagram.utils.to_latex_notation`) and keeps the
            other words, and ``False`` shows the text as it is. ``None``
            keeps the v3.x behavior: every number in a str is written as a
            subscript (``"Sample 1"`` to ``"Sample $_{1}$"``), except in a
            text containing ``$``, and a FutureWarning is emitted once per
            diagram when the display will change. In ternary-diagram
            4.0.0, ``None`` will follow `auto_latex_notation` of
            :class:`TernaryDiagram`, by default None

        kwargs : parameter of matplotlib.pyplot.annotate, optional
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.annotate.html


        Returns
        -------
        matplotlib.text.Annotation
            An annotation.
        """  # noqa: E501
        auto_latex_notation = check_optional_bool(
            auto_latex_notation, "auto_latex_notation"
        )
        plotter = _AnnotatePlotter(
            text,
            vector,
            ax=self.ax,
            post_draw_context=self.__post_draw_context,
            auto_latex_notation=auto_latex_notation,
            default_auto_latex_notation=self.__auto_latex_notation,
            **kwargs,
        )
        self._append_x_y(plotter)
        return plotter.collection_

    def fill(
        self, vector: ArrayLike, **kwargs: Any
    ) -> List[matplotlib.patches.Polygon]:
        """Fill a polygon whose vertices are given as compositions.

        This is a wrapper of `matplotlib.pyplot.fill`.

        See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.fill.html

        Parameters
        ----------
        vector : ArrayLike | shape = (n, 3)
            Compositions of the vertices of the polygon, one row per
            vertex. Each row represents the ratio of each component (the
            sum does not have to be 1), in the same order as `materials`.
            At least 3 vertices are needed. The vertices are joined in the
            order given and the polygon is closed automatically; they are
            not sorted and no convex hull is computed.

        kwargs : parameter of `matplotlib.pyplot.fill`, optional
            Properties of :class:`matplotlib.patches.Polygon`, such as
            `label`, `facecolor`, `edgecolor`, `alpha` or `hatch`, passed
            to matplotlib as they are. They take precedence over the
            defaults of this method.
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.fill.html

        Returns
        -------
        List[matplotlib.patches.Polygon]
            A list of one element, the filled polygon, as returned by
            `matplotlib.axes.Axes.fill`.

        Raises
        ------
        ValueError
            If the shape of `vector` is not (n, 3) or it has fewer than 3
            vertices.

        Notes
        -----
        The polygon is drawn with ``zorder=0.5`` by default: in front of
        the contours of :meth:`contour` and behind the grid, the border,
        the tie lines of :meth:`plot`, the points of :meth:`scatter` and
        the annotations and the texts of :meth:`text`. Pass `zorder` to
        change it, for example ``zorder=-0.5`` to draw the polygon behind
        the contours.

        Without a color, the polygon is filled with the next color of the
        matplotlib color cycle, so consecutive calls get different colors.
        The polygon is opaque by default and hides what is behind it; pass
        `alpha` to make it translucent, for example over a contour plot.

        Examples
        --------
        Fill a three-phase region translucently and show it in the legend.

        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> (polygon,) = td.fill(
        ...     [[0.5, 0.25, 0.25], [0.25, 0.5, 0.25], [0.25, 0.25, 0.5]],
        ...     alpha=0.5,
        ...     label="three-phase region",
        ... )
        >>> legend = td.ax.legend()
        """  # noqa: E501
        plotter = _FillPlotter(
            vector=vector,
            ax=self.ax,
            post_draw_context=self.__post_draw_context,
            **kwargs,
        )
        self._append_x_y(plotter)
        return plotter.collection_

    def text(
        self,
        text: str,
        vector: ArrayLike,
        *,
        auto_latex_notation: Optional[bool] = None,
        **kwargs: Any,
    ) -> matplotlib.text.Text:
        """Place a text at a composition.

        This is a wrapper of `matplotlib.pyplot.text`.

        See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.text.html

        Parameters
        ----------
        text : str
            Text to be displayed, such as the name of a phase. An object
            other than str is not formatted and is converted to a string
            by matplotlib.

        vector : ArrayLike | shape = (3,) or (1, 3)
            Composition of the point where the text is placed. It
            represents the ratio of each component (the sum does not have
            to be 1), in the same order as `materials`.

        auto_latex_notation : bool or None, optional
            Whether to write the chemical formulas in `text` in LaTeX
            notation (``"Li2O"`` to ``"Li$_{2}$O"``), with the same rule
            as :meth:`annotate` with ``auto_latex_notation=True`` (see
            :func:`ternary_diagram.utils.to_latex_notation`). ``None``
            follows `auto_latex_notation` of :class:`TernaryDiagram`, the
            setting of the diagram also used for the vertex labels
            (``True`` unless changed). ``True`` / ``False`` apply only to
            the text of this call and change neither the setting of the
            diagram, the vertex labels nor the other calls of
            :meth:`text` and :meth:`annotate`. Pass ``False`` to show a
            word that looks like a chemical formula, such as a sample name
            ``"S1"``, as it is. A text containing ``$`` (mathtext) is
            always shown as it is, by default None (the setting of the
            diagram)

        kwargs : parameter of `matplotlib.pyplot.text`, optional
            Properties of :class:`matplotlib.text.Text`, such as
            `fontsize`, `color`, `ha` or `fontdict`, passed to matplotlib
            as they are. They take precedence over the defaults of this
            method.
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.text.html

        Returns
        -------
        matplotlib.text.Text
            The text placed at the composition.

        Raises
        ------
        TypeError
            If `auto_latex_notation` is neither None, True nor False.
        ValueError
            If `vector` does not have 3 components.

        Notes
        -----
        The center of the text is placed exactly at the composition by
        default (``horizontalalignment="center"`` and
        ``verticalalignment="center"``). Pass `ha` / `va` (or their full
        names, also in `fontdict`) to change it.

        The text is drawn with ``zorder=4`` by default: in front of the
        polygons of :meth:`fill`, the grid, the border, the tie lines of
        :meth:`plot` and the points of :meth:`scatter`. Pass `zorder` to
        change it. The font size is left to matplotlib (rcParams).

        Examples
        --------
        Place the name of a phase on a default diagram, which formats the
        chemical formulas, and show another text as it is only in that
        call.

        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> label = td.text("Li2TiO3", [0.5, 0, 0.5])
        >>> label.get_text()
        'Li$_{2}$TiO$_{3}$'
        >>> plain = td.text(
        ...     "Phase 1", [0.2, 0.4, 0.4], auto_latex_notation=False
        ... )
        >>> plain.get_text()
        'Phase 1'

        On a diagram that does not format the chemical formulas, the text
        is shown as it is unless ``auto_latex_notation=True`` is passed.

        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(
        ...     ["Li2O", "La2O3", "TiO2"], ax=ax, auto_latex_notation=False
        ... )
        >>> label = td.text("Li2TiO3", [0.5, 0, 0.5])
        >>> label.get_text()
        'Li2TiO3'
        >>> formula = td.text(
        ...     "Li2TiO3", [0.5, 0, 0.5], auto_latex_notation=True
        ... )
        >>> formula.get_text()
        'Li$_{2}$TiO$_{3}$'
        """  # noqa: E501
        flag = check_optional_bool(auto_latex_notation, "auto_latex_notation")
        if flag is None:
            # inherit the setting of the diagram (not overwritten)
            flag = self.__auto_latex_notation
        plotter = _TextPlotter(
            text,
            vector,
            ax=self.ax,
            auto_latex_notation=flag,
            post_draw_context=self.__post_draw_context,
            **kwargs,
        )
        self._append_x_y(plotter)
        return plotter.collection_

    def tripcolor(
        self,
        vector: ArrayLike,
        z: ArrayLike,
        *,
        z_min: Optional[Number] = None,
        z_max: Optional[Number] = None,
        shading: Shading = "flat",
        colorbar: Optional[bool] = None,
        **kwargs: Any,
    ) -> MeshCollection:
        """Paint the triangles joining the compositions with their values.

        The compositions are joined into triangles and each triangle is
        painted from the values `z` of its 3 vertices, without
        interpolating values elsewhere. This is a wrapper of
        `matplotlib.pyplot.tripcolor`.

        See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.tripcolor.html

        Parameters
        ----------
        vector : ArrayLike | shape = (n, 3)
            Compositions of the points, one row per point. Each row
            represents the ratio of each component (the sum does not have
            to be 1), in the same order as `materials`.

        z : ArrayLike | shape = (n,)
            Values of the points, one per composition, which determine the
            colors. A NaN or infinite value leaves every triangle having
            that point as a vertex unpainted.

        z_min : Number or None, optional
            Lower limit of the color scale. `vmin` is accepted as an alias,
            and passing both raises a ValueError. If None, the minimum of
            the finite values of `z` is used. Do not pass it together with
            `norm`: leave both `z_min` and `z_max` as None so that `norm`
            decides the range, since matplotlib raises a ValueError when
            `norm` is given with either of them, by default None (the
            minimum of `z`)

        z_max : Number or None, optional
            Upper limit of the color scale. `vmax` is accepted as an alias,
            and passing both raises a ValueError. If None, the maximum of
            the finite values of `z` is used. Do not pass it together with
            `norm`: leave both `z_min` and `z_max` as None so that `norm`
            decides the range, since matplotlib raises a ValueError when
            `norm` is given with either of them, by default None (the
            maximum of `z`)

        shading : {'flat', 'gouraud'}, optional
            How to paint each triangle. ``'flat'`` paints it with one color,
            that of the mean of `z` at its 3 vertices. ``'gouraud'`` paints
            it with colors varying linearly between the values of `z` at
            its 3 vertices, by default 'flat'

        colorbar : bool or None, optional
            Whether to add a colorbar automatically for the triangles
            colored by `z`. ``True`` adds one and ``False`` adds none.
            ``None`` keeps the v3.x behavior: it adds one, and when the
            diagram already has a colorbar, it also emits a FutureWarning
            once per diagram. In ternary-diagram 4.0.0, ``None`` will add
            none to a diagram that already has a colorbar. The colorbars
            counted are those added through this TernaryDiagram
            (automatically or with its ``colorbar()`` method) and not
            removed; colorbars added directly with matplotlib, such as with
            ``fig.colorbar``, are not counted. The colorbar added is
            available as the ``colorbar`` attribute of the returned
            object, by default None

        kwargs : parameter of `matplotlib.pyplot.tripcolor`, optional
            Passed to matplotlib as they are, such as `cmap`, `norm`,
            `alpha`, `edgecolors` or `zorder`. They take precedence over
            the defaults of this method (``cmap="rainbow"`` and
            ``zorder=-1``). `triangles` (indices of the 3 points of each
            triangle, shape (ntri, 3)) replaces the automatic
            triangulation, and `mask` (boolean, shape (ntri,)) leaves the
            triangles that are true unpainted. `c` and `facecolors` cannot
            be used because the colors are determined by `z`, and the old
            name `flag_cbar` is not accepted; use `colorbar` instead.
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.tripcolor.html

        Returns
        -------
        matplotlib.collections.PolyCollection or matplotlib.collections.TriMesh
            The painted triangles: a ``PolyCollection`` with
            ``shading='flat'`` and a ``TriMesh`` with ``shading='gouraud'``.
            It can be passed to :meth:`colorbar` to draw a colorbar with
            the same color range and colormap.

        Raises
        ------
        TypeError
            If `colorbar` is neither None, True nor False, or if
            `flag_cbar` is passed.
        ValueError
            If `z` is None or does not have one value per composition, if
            `shading` is neither 'flat' nor 'gouraud', if `c` or
            `facecolors` is passed, if both `z_min` and `vmin` (or `z_max`
            and `vmax`) are passed, if the compositions cannot be
            triangulated automatically (fewer than 3 distinct compositions,
            or all of them on one straight line), or if no triangle can be
            painted. Nothing is added to the diagram in these cases.

        Warns
        -----
        UserWarning
            If some compositions are the same after normalization. Only the
            value of one of them is drawn.

        See Also
        --------
        contour : Contours interpolated from the values of the points.
        scatter : Points colored by their values.
        heatmapf : A function painted on a regular triangular lattice.
        ternary_diagram.utils.get_triangular_lattice : The regular
            triangular lattice used by :meth:`heatmapf`.

        Notes
        -----
        Without `triangles`, the compositions are triangulated
        automatically (Delaunay), so only the inside of their convex hull
        is painted and nothing is painted outside it. Compositions that
        are the same after normalization are used only once: aggregate
        their values (for example, by averaging them) before calling this
        method.

        With ``shading='flat'``, each triangle shows the mean of the values
        at its 3 vertices, so no triangle may reach the colors at the ends
        of the colorbar, whose range is that of `z` itself.

        The triangles are drawn with ``zorder=-1`` by default: behind the
        contours of :meth:`contour`, the polygons of :meth:`fill`, the
        grid, the border, the tie lines of :meth:`plot` and the points of
        :meth:`scatter`, whatever the order of the calls. Pass `zorder` to
        change it. Thin lines may appear between the triangles depending
        on the renderer; pass ``edgecolors="face"`` to hide them.

        Examples
        --------
        Paint the triangles joining the 3 vertices and a point inside the
        diagram, which adds a colorbar.

        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> mesh = td.tripcolor(
        ...     [[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1]],
        ...     [1.0, 2.0, 3.0, 4.0],
        ... )
        >>> type(mesh).__name__
        'PolyCollection'
        >>> len(mesh.get_paths())
        3
        >>> mesh.colorbar is not None
        True
        """  # noqa: E501
        colorbar = check_optional_bool(colorbar, "colorbar")
        plotter = _TripcolorPlotter(
            vector=vector,
            ax=self.ax,
            z=z,
            z_min=z_min,
            z_max=z_max,
            shading=shading,
            colorbar=colorbar,
            post_draw_context=self.__post_draw_context,
            **kwargs,
        )
        self._append_x_y(plotter)
        return plotter.collection_

    def heatmapf(
        self,
        func: HeatmapFunc,
        *,
        scale: int = DEFAULT_HEATMAPF_SCALE,
        z_min: Optional[Number] = None,
        z_max: Optional[Number] = None,
        shading: Shading = "flat",
        colorbar: Optional[bool] = None,
        **kwargs: Any,
    ) -> MeshCollection:
        """Paint a function of the composition over the whole diagram.

        The diagram is divided into a regular triangular lattice of small
        triangles, `func` is evaluated once at all the evaluation points,
        and the small triangles are painted from the values. This is a
        wrapper of `matplotlib.pyplot.tripcolor`.

        See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.tripcolor.html

        Parameters
        ----------
        func : callable
            Function of the composition, called only once as
            ``func(a, b, c)``. `a`, `b` and `c` are 1-D float arrays of the
            same length, one element per evaluation point, holding the
            components in the order of the vertex labels (top, bottom
            left, bottom right); ``a + b + c`` is 1 at each point. It must
            return one numeric value per evaluation point, as an array of
            shape (m,), (m, 1) or (1, m), in the same order. Return NaN
            (or an infinite value) where the function is not defined: the
            small triangles colored by such values are left unpainted.

        scale : int, optional
            Number of parts into which each edge of the diagram is
            divided. The lattice has ``scale ** 2`` small triangles, by
            default 50

        z_min : Number or None, optional
            Lower limit of the color scale. `vmin` is accepted as an alias,
            and passing both raises a ValueError. If None, the minimum of
            the finite values returned by `func` is used. Do not pass it
            together with `norm`: leave both `z_min` and `z_max` as None so
            that `norm` decides the range, since matplotlib raises a
            ValueError when `norm` is given with either of them, by default
            None (the minimum of the values)

        z_max : Number or None, optional
            Upper limit of the color scale. `vmax` is accepted as an alias,
            and passing both raises a ValueError. If None, the maximum of
            the finite values returned by `func` is used. Do not pass it
            together with `norm`: leave both `z_min` and `z_max` as None so
            that `norm` decides the range, since matplotlib raises a
            ValueError when `norm` is given with either of them, by default
            None (the maximum of the values)

        shading : {'flat', 'gouraud'}, optional
            How to evaluate `func` and paint the small triangles.
            ``'flat'`` evaluates `func` at the centroid of each small
            triangle (never on the edges or at the vertices of the diagram)
            and paints the triangle with that one color. ``'gouraud'``
            evaluates `func` at the lattice points, including those on the
            edges and at the vertices, and paints each small triangle with
            colors varying linearly between the values at its 3 vertices,
            by default 'flat'

        colorbar : bool or None, optional
            Whether to add a colorbar automatically for the triangles
            colored by the values of `func`. ``True`` adds one and
            ``False`` adds none. ``None`` keeps the v3.x behavior: it adds
            one, and when the diagram already has a colorbar, it also emits
            a FutureWarning once per diagram. In ternary-diagram 4.0.0,
            ``None`` will add none to a diagram that already has a
            colorbar. The colorbars counted are those added through this
            TernaryDiagram (automatically or with its ``colorbar()``
            method) and not removed; colorbars added directly with
            matplotlib, such as with ``fig.colorbar``, are not counted. The
            colorbar added is available as the ``colorbar`` attribute of
            the returned object, by default None

        kwargs : parameter of `matplotlib.pyplot.tripcolor`, optional
            Passed to matplotlib as they are, such as `cmap`, `norm`,
            `alpha`, `edgecolors` or `zorder`. They take precedence over
            the defaults of this method (``cmap="rainbow"`` and
            ``zorder=-1``). `c` and `facecolors` cannot be used because the
            colors are determined by `func`, `triangles` and `mask` cannot
            be used because the lattice is fixed (return NaN from `func` to
            leave a region unpainted), and the old name `flag_cbar` is not
            accepted; use `colorbar` instead.
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.tripcolor.html

        Returns
        -------
        matplotlib.collections.PolyCollection or matplotlib.collections.TriMesh
            The painted small triangles: a ``PolyCollection`` with
            ``shading='flat'`` and a ``TriMesh`` with ``shading='gouraud'``.
            It can be passed to :meth:`colorbar` to draw a colorbar with
            the same color range and colormap.

        Raises
        ------
        TypeError
            If `func` is not callable, if `scale` is not an integer (bool
            included), if `colorbar` is neither None, True nor False, or if
            `flag_cbar` is passed.
        ValueError
            If `scale` is less than 1, if `func` returns values that are
            not numbers or whose shape is none of (m,), (m, 1) and (1, m),
            if `shading` is neither 'flat' nor 'gouraud', if `c`,
            `facecolors`, `triangles` or `mask` is passed, if both `z_min`
            and `vmin` (or `z_max` and `vmax`) are passed, or if no
            triangle can be painted. Nothing is added to the diagram in
            these cases. Exceptions raised by `func` itself are propagated
            as they are, and nothing is added either.

        See Also
        --------
        contour : Contours interpolated from the values of the points.
        tripcolor : The triangles joining measured compositions painted
            from their values.
        ternary_diagram.utils.get_triangular_lattice : The regular
            triangular lattice used by this method.

        Notes
        -----
        `func` receives all the evaluation points at once, so it must work
        on arrays. Wrap a function that only accepts scalars with
        ``numpy.vectorize`` (``td.heatmapf(numpy.vectorize(f))``), which
        calls it once per point. A machine learning model that predicts
        from the compositions can be passed as
        ``lambda a, b, c: model.predict(np.column_stack([a, b, c]))``.

        The evaluation points are the ``scale ** 2`` centroids of the small
        triangles with ``shading='flat'``, and the
        ``(scale + 1) * (scale + 2) // 2`` lattice points with
        ``shading='gouraud'``. Use ``'flat'`` for a function that is not
        defined on the edges of the diagram (for example, one that divides
        by a component or takes its logarithm), since the centroids never
        lie on the edges. The 2-D coordinates of the evaluation points are
        recorded in ``x_["heatmapf"]`` and ``y_["heatmapf"]``.

        The default ``scale=50`` paints 2,500 small triangles. The number
        of triangles grows as ``scale ** 2``: ``scale=100`` paints 10,000
        of them, which still takes well under a second apart from
        evaluating `func`, but each triangle is written as its own polygon
        when the figure is saved in a vector format (PDF, SVG), so the file
        size and the saving time grow in the same way, especially in SVG,
        which is not compressed (roughly 0.4 MB for ``scale=50`` and
        1.5 MB for ``scale=100``). Save in a
        raster format (PNG) or pass ``rasterized=True`` for large values of
        `scale`.

        The triangles are drawn with ``zorder=-1`` by default: behind the
        contours of :meth:`contour`, the polygons of :meth:`fill`, the
        grid, the border, the tie lines of :meth:`plot` and the points of
        :meth:`scatter`, whatever the order of the calls. Pass `zorder` to
        change it. Thin lines may appear between the triangles depending
        on the renderer; pass ``edgecolors="face"`` to hide them.

        Examples
        --------
        Paint a function over the whole diagram, which adds a colorbar.

        >>> import matplotlib.pyplot as plt
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> mesh = td.heatmapf(lambda a, b, c: a * b * c)
        >>> type(mesh).__name__
        'PolyCollection'
        >>> len(mesh.get_paths())
        2500
        >>> mesh.colorbar is not None
        True

        Leave the region where the first component is below 0.3 unpainted
        by returning NaN there, and overlay measured points with the same
        color range. The later call passes ``colorbar=False`` so that only
        one colorbar is added.

        >>> import matplotlib.pyplot as plt
        >>> import numpy as np
        >>> from ternary_diagram import TernaryDiagram
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> mesh = td.heatmapf(
        ...     lambda a, b, c: np.where(a < 0.3, np.nan, a),
        ...     scale=20,
        ...     z_min=0,
        ...     z_max=1,
        ...     shading="gouraud",
        ... )
        >>> type(mesh).__name__
        'TriMesh'
        >>> points = td.scatter(
        ...     [[6, 3, 1], [5, 1, 4]], z=[0.6, 0.5], z_min=0, z_max=1,
        ...     colorbar=False,
        ... )

        Wrap a function that only accepts scalars with ``numpy.vectorize``.

        >>> import math
        >>> import matplotlib.pyplot as plt
        >>> import numpy as np
        >>> from ternary_diagram import TernaryDiagram
        >>> def scalar_func(a, b, c):
        ...     return math.sqrt(a * b)
        >>> fig, ax = plt.subplots(layout="constrained")
        >>> td = TernaryDiagram(["Li2O", "La2O3", "TiO2"], ax=ax)
        >>> mesh = td.heatmapf(np.vectorize(scalar_func), scale=10)
        >>> len(mesh.get_paths())
        100
        """  # noqa: E501
        colorbar = check_optional_bool(colorbar, "colorbar")
        plotter = _HeatmapfPlotter(
            func,
            ax=self.ax,
            scale=scale,
            z_min=z_min,
            z_max=z_max,
            shading=shading,
            colorbar=colorbar,
            post_draw_context=self.__post_draw_context,
            **kwargs,
        )
        self._append_x_y(plotter)
        return plotter.collection_

    def colorbar(
        self,
        mappable,
        shrink: float = 0.8,
        format="%.1f",
        label: str = "",
        orientation: str = "vertical",
        location: str = "right",
        **kwargs,
    ) -> matplotlib.colorbar.Colorbar:
        """Draw a colorbar.

        This is a wrapper of `matplotlib.pyplot.colorbar`.

        See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.colorbar.html

        Parameters
        ----------
        mappable : matplotlib.cm.ScalarMappable
            The object that contains the colorbar data.

        shrink : float, optional
            how much to shrink the colorbar, by default 0.8

        format : str, optional
            float format, by default '%.1f'

        label : str, optional
            bar label, by default ''

        orientation : str, optional
            bar orientation, by default 'vertical'

        location : str, optional
            location, by default 'right'

        kwargs : parameter of `matplotlib.pyplot.colorbar`, optional
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.colorbar.html

        Returns
        -------
        matplotlib.colorbar.Colorbar
            colorbar object
        """  # noqa: E501

        # draw colorbar
        cbar = _BasePlotter.colorbar(
            mappable,
            shrink=shrink,
            format=format,
            label=label,
            orientation=orientation,
            location=location,
            ax=self.ax,
            **kwargs,
        )
        self.__post_draw_context.register_colorbar(cbar)
        return cbar

    def _append_x_y(self, plotter) -> None:
        """append x, y data

        Parameters
        ----------
        plotter : _BasePlotter
            plotter

        Raises
        ------
        TypeError
            "plotter must inherit `_BasePlotter`"
        """
        if not isinstance(plotter, _BasePlotter):
            raise TypeError("plotter must inherit `_BasePlotter`")

        self.x_[plotter.name].append(plotter.x_)
        self.y_[plotter.name].append(plotter.y_)


class _BasePlotter:
    def __init__(
        self,
        vector: ArrayLike,
        ax: Optional[matplotlib.axes.Axes] = None,
        z: Optional[ArrayLike] = None,
        z_min: Optional[Number] = None,
        z_max: Optional[Number] = None,
        *,
        post_draw_context: PostDrawContext,
        **kwargs,
    ):
        """
        This is a base class for the wrapper of `matplotlib.pyplot.` functions.

        Parameters
        ----------
        vector : ArrayLike
            vector

        ax : Optional[matplotlib.axes.Axes], optional
            , by default None

        z : Optional[ArrayLike], optional
            , by default None

        z_min : Optional[Number], optional
            , by default None

        z_max : Optional[Number], optional
            , by default None

        post_draw_context : PostDrawContext
            State of the processing after drawing, shared by all the plots
            of the ternary diagram. ``_post_draw`` reads and updates it.
        """
        self.vector: np.ndarray = check_2d_vector(vector)
        self.ax: matplotlib.axes.Axes = check_ax(ax)
        self.__post_draw_context = post_draw_context
        self.kwargs: dict = kwargs
        self.z = (
            np.asarray(z).ravel() if z is not None else None
        )  # convert to 1-d np.ndarray

        # TODO: check
        if self.z is not None:
            self.z_min = z_min
            self.z_max = z_max

        # get_figure
        self.fig = self.ax.figure

        # 3次元ベクトルをx, y座標に落とし込む．
        self.__x, self.__y = three2two(self.vector)

    def _set_default_params(self, **kwargs):
        """
        set default params

        Each keyword argument is stored in ``self.kwargs`` only when the
        user has not specified it, so the user's value always takes
        precedence. For example, passing ``zorder=2`` sets ``zorder`` to 2
        unless the user passed ``zorder``.
        """
        for k, v in kwargs.items():
            if k not in self.kwargs:
                self.kwargs[k] = v

    def _merge_alias(self, value: Any, name: str, alias: str) -> Any:
        """
        merge the matplotlib name `alias` in kwargs into `name`

        `alias` is removed from ``self.kwargs``. Its value is returned when
        only `alias` is specified, and `value` is returned otherwise. For
        example, passing ``self.z_min``, ``"z_min"`` and ``"vmin"`` gives
        the lower limit of the color scale from either ``z_min`` or
        ``vmin``.

        Raises
        ------
        ValueError
            when both `name` and `alias` are specified.
        """
        alias_value = self.kwargs.pop(alias, None)
        if alias_value is None:
            return value
        if value is not None:
            raise ValueError(
                f"`{name}` and `{alias}` cannot be specified at the same time."
            )
        return alias_value

    @property
    def x_(self) -> np.ndarray:
        # TODO: docstring
        return self.__x

    @x_.setter
    def x_(self, _x):
        raise AttributeError("x_ is read-only")

    @property
    def y_(self) -> np.ndarray:
        # TODO: docstring
        return self.__y

    @y_.setter
    def y_(self, _y):
        raise AttributeError("y_ is read-only")

    @property
    @abstractmethod
    def name(self) -> str:
        """Plotter name"""
        ...

    @property
    def collection_(self):
        return self.__collection

    @collection_.setter
    def collection_(self, _collection):
        self.__collection = _collection

    @staticmethod
    def colorbar(
        mappable: Optional[Union[matplotlib.cm.ScalarMappable, Any]] = None,
        shrink: float = 0.8,
        format="%.1f",
        label: str = "",
        orientation: str = "vertical",
        location: str = "right",
        ax: Optional[matplotlib.axes.Axes] = None,
        **kwargs,
    ) -> matplotlib.colorbar.Colorbar:
        """Draw a colorbar.

        This is a wrapper of `matplotlib.pyplot.colorbar`.

        See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.colorbar.html

        Parameters
        ----------
        mappable : Optional[Union[matplotlib.cm.ScalarMappable, Any]]
            The object that contains the colorbar data.

        shrink : float, optional
            how much to shrink the colorbar, by default 0.8

        format : str, optional
            float format, by default '%.1f'

        label : str, optional
            bar label, by default ''

        orientation : str, optional
            bar orientation, by default 'vertical'

        location : str, optional
            location, by default 'right'

        ax : Optional[matplotlib.axes.Axes], optional
            axes object, by default None

        kwargs : parameter of `matplotlib.pyplot.colorbar`, optional
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.colorbar.html

        Returns
        -------
        matplotlib.colorbar.Colorbar
            colorbar object
        """  # noqa: E501

        # check `ax`
        ax = check_ax(ax)

        # draw colorbar
        return ax.figure.colorbar(
            mappable,
            ax=ax,
            shrink=shrink,
            format=format,
            label=label,
            orientation=orientation,
            location=location,
            **kwargs,
        )

    def _post_draw(
        self,
        *,
        mappable: Optional[matplotlib.cm.ScalarMappable] = None,
        colorbar: Optional[bool] = None,
    ) -> Optional[matplotlib.colorbar.Colorbar]:
        """Run the processing after drawing, in one place for all plotters.

        Every plotter calls this exactly once, at the end of ``__init__``.
        In order, it decides whether to add a colorbar and adds and
        registers it, warns about the colorbar, decides whether to adjust
        the figure layout and adjusts it, and warns about the layout. Each
        warning is issued only when the decision asks for it and only the
        first time for its reason in the ternary diagram. Exceptions and
        warnings from matplotlib are not caught.

        Parameters
        ----------
        mappable : Optional[matplotlib.cm.ScalarMappable], optional
            The plot colored by values, which a colorbar describes. None
            for a plot that is not colored by values, which never gets a
            colorbar, by default None
        colorbar : Optional[bool], optional
            Whether the user asked to add a colorbar. None means that it
            was not specified, by default None

        Returns
        -------
        Optional[matplotlib.colorbar.Colorbar]
            The colorbar added and registered to the ternary diagram, or
            None when no colorbar is added.
        """
        context = self.__post_draw_context

        colorbar_action = decide_colorbar(
            colorbar,
            has_mappable=mappable is not None,
            has_existing=context.has_colorbar(),
        )
        cbar = None
        if colorbar_action is not ColorbarAction.SKIP:
            cbar = self.colorbar(mappable, ax=self.ax)
            context.register_colorbar(cbar)
        if colorbar_action is ColorbarAction.ADD_AND_WARN and (
            context.first_time(COLORBAR_WARNING_KEY)
        ):
            warn_external(colorbar_warning_message(self.name))

        layout_action = decide_layout(
            context.tight_layout, get_layout_state(self.fig)
        )
        if layout_action is not LayoutAction.SKIP:
            self.fig.tight_layout()
        if layout_action is LayoutAction.APPLY_AND_WARN and (
            context.first_time(LAYOUT_WARNING_KEY)
        ):
            warn_external(layout_warning_message())

        return cbar


class _ScatterPlotter(_BasePlotter):
    def __init__(
        self,
        vector,
        ax=None,
        z=None,
        z_min=None,
        z_max=None,
        annotations=None,
        colorbar: Optional[bool] = None,
        *,
        post_draw_context: PostDrawContext,
        auto_latex_notation: Optional[bool] = None,
        default_auto_latex_notation: bool = True,
        **kwargs,
    ):
        super().__init__(
            vector=vector,
            ax=ax,
            z=z,
            z_min=z_min,
            z_max=z_max,
            post_draw_context=post_draw_context,
            **kwargs,
        )

        # default options
        self._set_default_params(
            zorder=DEFAULT_ZORDER_SCATTER,
        )

        # easy annotation 右上に簡易annotation
        if annotations is not None:
            if len(annotations) != len(self.x_):
                raise ValueError(
                    f"The length of `annotations` ({len(annotations)}) "
                    f"must be equal to the number of points ({len(self.x_)})."
                )
            for x, y, txt in zip(self.x_, self.y_, annotations):
                txt = _resolve_annotation_text(
                    txt,
                    auto_latex_notation,
                    default=default_auto_latex_notation,
                    func="scatter",
                    context=post_draw_context,
                )
                self.ax.annotate(
                    # matplotlib shows the other objects with str()
                    cast(str, txt),
                    xy=(x, y),
                    xytext=(x + 0.02, y + 0.02),
                    fontsize=8,
                    color="#262626",
                )

        # when z is None
        if self.z is None:
            # not colored by values, so no colorbar
            mappable = None
            # To change color by each point
            self.collection_ = self.ax.scatter(self.x_, self.y_, **self.kwargs)
            # for i_data in range(len(self.x_)):
            #     self.ax.scatter(self.x_[i_data], self.y_[i_data], **self.kwargs)  # noqa: E501
        else:
            if "c" in self.kwargs:
                raise ValueError(
                    "`c` cannot be used together with `z` "
                    "because the colors are determined by `z`."
                )
            if "cmap" not in self.kwargs:
                self.kwargs["cmap"] = DEFAULT_CMAP
            self.collection_ = self.ax.scatter(
                self.x_,
                self.y_,
                c=self.z,
                vmin=self._merge_alias(self.z_min, "z_min", "vmin"),
                vmax=self._merge_alias(self.z_max, "z_max", "vmax"),
                **self.kwargs,
            )
            mappable = self.collection_
        self._post_draw(mappable=mappable, colorbar=colorbar)

    @property
    def name(self):
        return "scatter"


class _ContourPlotter(_BasePlotter):
    def __init__(
        self,
        vector,
        ax=None,
        z=None,
        z_min=None,
        z_max=None,
        fill: bool = True,
        colorbar: Optional[bool] = None,
        *,
        post_draw_context: PostDrawContext,
        **kwargs,
    ):
        super().__init__(
            vector,
            ax=ax,
            z=z,
            z_min=z_min,
            z_max=z_max,
            post_draw_context=post_draw_context,
            **kwargs,
        )
        if self.z is None:
            raise ValueError("`z` is required to draw a contour map.")

        # default options
        self._set_default_params(
            cmap=DEFAULT_CMAP,
            zorder=DEFAULT_ZORDER_CONTOUR,
        )

        triangulation = Triangulation(self.x_, self.y_)
        if "levels" in self.kwargs:
            # user-specified levels take precedence over the automatic ones.
            if self.z_min is not None or self.z_max is not None:
                raise ValueError(
                    "`levels` cannot be specified together with "
                    "`z_min` or `z_max`."
                )
            levels = self.kwargs.pop("levels")
        else:
            levels = self._auto_levels()
        if fill:
            self.collection_ = self.ax.tricontourf(
                triangulation,
                self.z,
                levels=levels,
                **self.kwargs,
            )
        else:
            self.collection_ = self.ax.tricontour(
                triangulation,
                self.z,
                levels=levels,
                **self.kwargs,
            )

        self._post_draw(mappable=self.collection_, colorbar=colorbar)

    def _auto_levels(self) -> np.ndarray:
        """levels spanning from `z_min` (or min of z) to `z_max` (or max of z)"""
        # 等高線の線を引く場所，すなわち，色の勾配を表す配列．
        N_LEVELS = 101  # 勾配をどれだけ細かくするかの変数．
        levels: np.ndarray = np.linspace(
            start=self.z_min if self.z_min is not None else np.min(self.z),  # type: ignore[arg-type]
            stop=self.z_max if self.z_max is not None else np.max(self.z),  # type: ignore[arg-type]
            num=N_LEVELS,
        )
        # solve issue#7
        # matplotlib requires strictly increasing levels. Checking the
        # differences (not `levels.std() == 0`) also catches constant `z`,
        # whose std can be a rounding error like 8.9e-16 instead of 0.
        if not np.all(np.diff(levels) > 0):
            OFFSET = 0.001
            levels = np.linspace(
                levels[0] - OFFSET * (N_LEVELS // 2),
                levels[-1] + OFFSET * (N_LEVELS // 2),
                N_LEVELS,
            )
        return levels

    @property
    def name(self):
        return "contour"


class _LinePlotter(_BasePlotter):
    def __init__(
        self,
        vector,
        ax=None,
        *,
        post_draw_context: PostDrawContext,
        **kwargs,
    ):
        super().__init__(
            vector,
            ax=ax,
            z=None,
            z_min=None,
            z_max=None,
            post_draw_context=post_draw_context,
            **kwargs,
        )

        # default options
        self._set_default_params(
            zorder=DEFAULT_ZORDER_PLOTS,
        )

        # plot
        self.collection_: List[matplotlib.lines.Line2D] = self.ax.plot(
            self.x_, self.y_, **self.kwargs
        )
        self._post_draw()

    @property
    def name(self):
        return "plot"


class _AnnotatePlotter(_BasePlotter):
    def __init__(
        self,
        text,
        vector,
        ax=None,
        *,
        post_draw_context: PostDrawContext,
        auto_latex_notation: Optional[bool] = None,
        default_auto_latex_notation: bool = True,
        **kwargs,
    ):
        vector = check_1d_vector(vector, scale=False)
        super().__init__(
            vector,
            ax=ax,
            z=None,
            z_min=None,
            z_max=None,
            post_draw_context=post_draw_context,
            **kwargs,
        )

        if "xytext" not in kwargs:
            kwargs["xytext"] = (self.x_[0] + 0.02, self.y_[0] + 0.02)
        if "fontsize" not in kwargs:
            kwargs["fontsize"] = 8

        text = _resolve_annotation_text(
            text,
            auto_latex_notation,
            default=default_auto_latex_notation,
            func="annotate",
            context=post_draw_context,
        )
        # annotate
        self.collection_ = self.ax.annotate(
            text=text, xy=(self.x_[0], self.y_[0]), **kwargs
        )

        self._post_draw()

    @property
    def name(self):
        return "annotate"


class _FillPlotter(_BasePlotter):
    def __init__(
        self,
        vector: ArrayLike,
        ax: Optional[matplotlib.axes.Axes] = None,
        *,
        post_draw_context: PostDrawContext,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            vector,
            ax=ax,
            z=None,
            z_min=None,
            z_max=None,
            post_draw_context=post_draw_context,
            **kwargs,
        )

        # a polygon needs at least 3 vertices; checked before drawing
        n_vertices = len(self.x_)
        if n_vertices < 3:
            raise ValueError(
                "`vector` must have at least 3 vertices to draw a polygon, "
                f"but got {n_vertices}."
            )

        # default options (colors are left to matplotlib's color cycle)
        self._set_default_params(
            zorder=DEFAULT_ZORDER_FILL,
        )

        # fill
        self.collection_: List[matplotlib.patches.Polygon] = self.ax.fill(
            self.x_, self.y_, **self.kwargs
        )
        self._post_draw()

    @property
    def name(self) -> str:
        return "fill"


#: Default alignment of ``text``: (canonical name, alias, value). Each value
#: is set only when neither the canonical name nor the alias is given in
#: the kwargs or in ``fontdict``.
_TEXT_ALIGNMENT_DEFAULTS: Tuple[Tuple[str, str, str], ...] = (
    ("horizontalalignment", "ha", "center"),
    ("verticalalignment", "va", "center"),
)


class _TextPlotter(_BasePlotter):
    def __init__(
        self,
        text: str,
        vector: ArrayLike,
        ax: Optional[matplotlib.axes.Axes] = None,
        *,
        auto_latex_notation: bool,  # resolved by TernaryDiagram.text
        post_draw_context: PostDrawContext,
        **kwargs: Any,
    ) -> None:
        # a single composition; checked before drawing
        vector = check_1d_vector(vector, scale=False)
        super().__init__(
            vector,
            ax=ax,
            z=None,
            z_min=None,
            z_max=None,
            post_draw_context=post_draw_context,
            **kwargs,
        )

        # default alignment, unless given by either name in kwargs or
        # fontdict (the user's value always takes precedence)
        fontdict = self.kwargs.get("fontdict") or {}
        for name, alias, value in _TEXT_ALIGNMENT_DEFAULTS:
            if not any(
                key in self.kwargs or key in fontdict for key in (name, alias)
            ):
                self.kwargs[name] = value
        # default options (the font size is left to matplotlib)
        self._set_default_params(
            zorder=DEFAULT_ZORDER_TEXT,
        )

        # text
        # format the chemical formulas of a str, like `annotate`. A text
        # other than str is passed as it is and converted by matplotlib,
        # although the stub of `Axes.text` accepts only str.
        label = _format_text(text, auto_latex_notation)
        self.collection_: matplotlib.text.Text = self.ax.text(
            self.x_[0],
            self.y_[0],
            label,  # type: ignore[arg-type]
            **self.kwargs,
        )
        self._post_draw()

    @property
    def name(self) -> str:
        return "text"


class _MeshPlotter(_BasePlotter):
    """Base of the plotters that paint triangles with ``Axes.tripcolor``.

    Subclasses initialize the base class, prepare a triangulation and the
    values, call ``_draw_mesh`` and then call ``_post_draw`` once at the
    end of ``__init__``.
    """

    def _draw_mesh(
        self,
        triangulation: Triangulation,
        values: np.ndarray,
        *,
        on_faces: bool,
        shading: Shading,
    ) -> MeshCollection:
        """Paint the paintable triangles of `triangulation`.

        Every exception of this spec is raised before matplotlib is called,
        so nothing is added to the Axes when one is raised.

        Parameters
        ----------
        triangulation : Triangulation
            A new triangulation created by the plotter. Its mask is
            replaced by the triangles that cannot be painted.
        values : np.ndarray
            Float values that determine the colors, one per triangle if
            `on_faces` is true, otherwise one per point.
        on_faces : bool
            Whether `values` are given per triangle (true) or per point
            (false).
        shading : Shading
            ``'flat'`` or ``'gouraud'``, already checked.

        Returns
        -------
        MeshCollection
            A ``PolyCollection`` for ``'flat'`` and a ``TriMesh`` for
            ``'gouraud'``.
        """
        z_min = self._merge_alias(self.z_min, "z_min", "vmin")
        z_max = self._merge_alias(self.z_max, "z_max", "vmax")
        mask = unpaintable_mask(triangulation, values, on_faces=on_faces)
        if self.kwargs.get("norm") is not None and (
            z_min is None and z_max is None
        ):
            # the range is left to the norm given by the user
            color_range: dict = {}
        else:
            vmin, vmax = default_color_range(values, z_min, z_max)
            color_range = {"vmin": vmin, "vmax": vmax}
        self._set_default_params(
            cmap=DEFAULT_CMAP,
            zorder=DEFAULT_ZORDER_HEATMAP,
        )

        triangulation.set_mask(mask)
        masked = np.ma.masked_invalid(values)
        if on_faces:
            return self.ax.tripcolor(
                triangulation,
                facecolors=masked,
                shading=shading,
                **color_range,
                **self.kwargs,
            )
        return self.ax.tripcolor(
            triangulation,
            masked,
            shading=shading,
            **color_range,
            **self.kwargs,
        )


class _TripcolorPlotter(_MeshPlotter):
    def __init__(
        self,
        vector: ArrayLike,
        ax: Optional[matplotlib.axes.Axes] = None,
        z: Optional[ArrayLike] = None,
        z_min: Optional[Number] = None,
        z_max: Optional[Number] = None,
        shading: Shading = "flat",
        colorbar: Optional[bool] = None,  # checked by TernaryDiagram
        *,
        post_draw_context: PostDrawContext,
        **kwargs: Any,
    ) -> None:
        shading = check_shading(shading)
        check_mesh_kwargs(
            kwargs, func="tripcolor", color_source="z", fixed_lattice=False
        )
        # not passed to matplotlib as kwargs
        triangles = kwargs.pop("triangles", None)
        mask = kwargs.pop("mask", None)
        super().__init__(
            vector,
            ax=ax,
            z=z,
            z_min=z_min,
            z_max=z_max,
            post_draw_context=post_draw_context,
            **kwargs,
        )

        n_points = len(self.x_)
        if self.z is None:
            raise ValueError(
                "`z` is required to draw `tripcolor`: pass one value per "
                f"composition ({n_points} values)."
            )
        if self.z.size != n_points:
            raise ValueError(
                f"`z` must have one value per composition ({n_points}), "
                f"but got {self.z.size}."
            )
        values = self.z.astype(float)
        triangulation, n_unused = triangulate(
            self.x_, self.y_, triangles, mask
        )
        if n_unused > 0:
            warn_external(
                duplicate_points_message(n_unused), category=UserWarning
            )

        self.collection_ = self._draw_mesh(
            triangulation, values, on_faces=False, shading=shading
        )
        self._post_draw(mappable=self.collection_, colorbar=colorbar)

    @property
    def name(self) -> str:
        return "tripcolor"


class _HeatmapfPlotter(_MeshPlotter):
    def __init__(
        self,
        func: HeatmapFunc,
        ax: Optional[matplotlib.axes.Axes] = None,
        scale: int = DEFAULT_HEATMAPF_SCALE,
        z_min: Optional[Number] = None,
        z_max: Optional[Number] = None,
        shading: Shading = "flat",
        colorbar: Optional[bool] = None,  # checked by TernaryDiagram
        *,
        post_draw_context: PostDrawContext,
        **kwargs: Any,
    ) -> None:
        shading = check_shading(shading)
        check_mesh_kwargs(
            kwargs, func="heatmapf", color_source="func", fixed_lattice=True
        )
        # exceptions about `scale` are propagated as they are
        vertices, triangles = get_triangular_lattice(scale)
        on_faces = shading == "flat"
        # flat: centroids of the small triangles (never on the edges),
        # gouraud: lattice points (including the edges and the vertices)
        points = vertices[triangles].mean(axis=1) if on_faces else vertices
        values = evaluate_function(func, points)
        super().__init__(
            points,
            ax=ax,
            z=values,
            z_min=z_min,
            z_max=z_max,
            post_draw_context=post_draw_context,
            **kwargs,
        )

        vx, vy = three2two(vertices)
        triangulation = Triangulation(vx, vy, triangles)
        self.collection_ = self._draw_mesh(
            triangulation, values, on_faces=on_faces, shading=shading
        )
        self._post_draw(mappable=self.collection_, colorbar=colorbar)

    @property
    def name(self) -> str:
        return "heatmapf"


if __name__ == "__main__":
    pass
