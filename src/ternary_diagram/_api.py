"""
Copyright © 2021 yu9824
"""

# deprecated from python>=3.9
from typing import Tuple, List  # isort: skip

from abc import abstractmethod
from collections import defaultdict
from collections.abc import Mapping
from numbers import Number
from typing import Any, Optional, Union

import matplotlib
import matplotlib.axes
import matplotlib.cm
import matplotlib.collections
import matplotlib.colorbar
import matplotlib.figure
import matplotlib.lines
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
    resolve_renamed_parameter,
    warn_external,
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
    check_1d_vector,
    check_2d_vector,
    check_ax,
    check_optional_bool,
    get_label,
    three2two,
)

# default parameters
DEFAULT_CMAP = "rainbow"
DEFAULT_ZORDER_CONTOUR = 0
DEFAULT_ZORDER_GRIDS = 1
DEFAULT_ZORDER_PLOTS = 2
DEFAULT_ZORDER_SCATTER = 3


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
            generated. If False, the material is displayed as it is.
            , by default True

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

    def scatter(
        self,
        vector: ArrayLike,
        z: Optional[ArrayLike] = None,
        z_min: Optional[Number] = None,
        z_max: Optional[Number] = None,
        annotations: Optional[List[str]] = None,
        colorbar: Optional[bool] = None,
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

        kwargs : parameter of `matplotlib.pyplot.scatter`, optional
            For example, `marker='x'`, `facecolor='blue'` etc.

            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.scatter.html.


        Returns
        -------
        matplotlib.collections.PathCollection
            A collection of scatter points.
        """  # noqa: E501

        colorbar = _resolve_colorbar_arg("scatter", colorbar, kwargs)
        plotter = _ScatterPlotter(
            vector=vector,
            ax=self.ax,
            z=z,
            z_min=z_min,
            z_max=z_max,
            annotations=annotations,
            colorbar=colorbar,
            post_draw_context=self.__post_draw_context,
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
        self, text: str, vector: ArrayLike, **kwargs
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

        kwargs : parameter of matplotlib.pyplot.annotate, optional
            See https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.annotate.html


        Returns
        -------
        matplotlib.text.Annotation
            An annotation.
        """  # noqa: E501
        plotter = _AnnotatePlotter(
            text,
            vector,
            ax=self.ax,
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
                txt = get_label(txt)
                self.ax.annotate(
                    txt,
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

        # check_text
        try:
            text = get_label(text)
        except ValueError:
            pass
        # annotate
        self.collection_ = self.ax.annotate(
            text=text, xy=(self.x_[0], self.y_[0]), **kwargs
        )

        self._post_draw()

    @property
    def name(self):
        return "annotate"


if __name__ == "__main__":
    pass
