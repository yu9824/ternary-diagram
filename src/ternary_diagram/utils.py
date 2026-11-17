from __future__ import annotations

import re
from math import isfinite, sqrt
from numbers import Integral, Real
from typing import Callable, Union

import matplotlib.axes
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import ArrayLike

#: Format of the tick labels accepted by :func:`get_tick_formatter`: a name
#: (``"percent"`` or ``"fraction"``), a format string or a callable that
#: takes a value in [0, 1] and returns its label.
TickFormat = Union[str, Callable[[float], str]]


def check_ax(ax: matplotlib.axes.Axes | None) -> matplotlib.axes.Axes:
    """Return the Axes to draw on.

    Parameters
    ----------
    ax : matplotlib.axes.Axes or None
        Axes to draw on. If None, the current Axes (``plt.gca()``) is used,
        which creates a figure and an Axes when there is none.

    Returns
    -------
    matplotlib.axes.Axes
        `ax` itself if it is an Axes, otherwise the current Axes.

    Raises
    ------
    TypeError
        If `ax` is neither None nor a ``matplotlib.axes.Axes``.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> from ternary_diagram.utils import check_ax
    >>> fig, ax = plt.subplots(layout="constrained")
    >>> check_ax(ax) is ax
    True
    >>> check_ax(None) is ax
    True
    >>> check_ax(fig)
    Traceback (most recent call last):
        ...
    TypeError: `ax` is None or Axes object.
    This `ax` is (<class 'matplotlib.figure.Figure'>).
    """
    if ax is None:
        ax = plt.gca()
    elif isinstance(ax, matplotlib.axes.Axes):
        pass
    else:
        raise TypeError(
            "`ax` is None or Axes object.\nThis `ax` is ({}).".format(
                ax.__class__
            )
        )
    return ax


def check_2d_vector(vector: ArrayLike, scale: bool = True) -> np.ndarray:
    """Check the shape of compositions and normalize each row.

    Parameters
    ----------
    vector : array-like of shape (n, 3)
        Compositions, one per row. Each row gives the amounts of the three
        components in the order top, bottom-left, bottom-right
        (counterclockwise from the top vertex).
    scale : bool, optional
        Whether to divide each row by its sum so that it sums to 1. A row
        whose sum is 0 becomes NaN. If False, the values are returned as
        they are, by default True

    Returns
    -------
    numpy.ndarray of shape (n, 3)
        The compositions, normalized if `scale` is True.

    Raises
    ------
    ValueError
        If `vector` is not two-dimensional with three columns.

    Examples
    --------
    >>> from ternary_diagram.utils import check_2d_vector
    >>> check_2d_vector([[1, 1, 2], [3, 0, 1]])
    array([[0.25, 0.25, 0.5 ],
           [0.75, 0.  , 0.25]])
    >>> check_2d_vector([[1, 1, 2]], scale=False)
    array([[1, 1, 2]])
    >>> check_2d_vector([1, 1, 2])
    Traceback (most recent call last):
        ...
    ValueError: `vector`'s shape must be (n, 3), but got (3,).
    """
    arr_vector = np.asarray(vector)
    if arr_vector.ndim != 2 or arr_vector.shape[1] != 3:
        raise ValueError(
            "`vector`'s shape must be (n, 3), but got {}.".format(
                arr_vector.shape
            )
        )
    if scale:
        arr_vector = arr_vector / np.sum(
            arr_vector, axis=1, keepdims=True
        )  # 今回keepdims = Trueは.reshape(-1, 1)と同義
    return arr_vector


def check_1d_vector(vector: ArrayLike, scale: bool = True) -> np.ndarray:
    """Check a single composition and return it as a row of a 2D array.

    Parameters
    ----------
    vector : array-like of shape (3,)
        One composition: the amounts of the three components in the order
        top, bottom-left, bottom-right (counterclockwise from the top
        vertex). Any array-like with exactly three elements is accepted,
        because it is flattened first.
    scale : bool, optional
        Whether to divide the composition by its sum so that it sums to 1.
        A composition whose sum is 0 becomes NaN. If False, the values are
        returned as they are, by default True

    Returns
    -------
    numpy.ndarray of shape (1, 3)
        The composition as the only row, normalized if `scale` is True.

    Raises
    ------
    ValueError
        If `vector` does not have exactly three elements.

    Examples
    --------
    >>> from ternary_diagram.utils import check_1d_vector
    >>> check_1d_vector([2, 2, 4])
    array([[0.25, 0.25, 0.5 ]])
    >>> check_1d_vector([1, 2, 3], scale=False)
    array([[1, 2, 3]])
    >>> check_1d_vector([1, 2])
    Traceback (most recent call last):
        ...
    ValueError: `vector`'s length must be 3.
    """
    vector = np.array(vector).ravel()
    if len(vector) == 3:
        return check_2d_vector(np.array([vector]), scale=scale)
    else:
        raise ValueError("`vector`'s length must be 3.")


def check_optional_bool(value: object, name: str) -> bool | None:
    """Check that a value is None, True or False.

    Parameters
    ----------
    value : object
        The value passed to the argument being checked. ``None``, ``bool``
        and ``numpy.bool_`` are accepted.
    name : str
        The name of the argument being checked, shown in the error message.

    Returns
    -------
    bool or None
        ``None`` if `value` is ``None``, otherwise `value` converted to
        the built-in ``bool``.

    Raises
    ------
    TypeError
        If `value` is neither ``None``, ``bool`` nor ``numpy.bool_``.

    Examples
    --------
    >>> from ternary_diagram.utils import check_optional_bool
    >>> import numpy as np
    >>> print(check_optional_bool(None, "tight_layout"))
    None
    >>> check_optional_bool(False, "tight_layout")
    False
    >>> check_optional_bool(np.bool_(True), "tight_layout")
    True
    >>> check_optional_bool(1, "tight_layout")
    Traceback (most recent call last):
        ...
    TypeError: `tight_layout` must be None, True or False, but got 1.
    """
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    raise TypeError(
        f"`{name}` must be None, True or False, but got {value!r}."
    )


def check_bool(value: object, name: str) -> bool:
    """Check that a value is True or False.

    Parameters
    ----------
    value : object
        The value passed to the argument being checked. Only ``bool`` and
        ``numpy.bool_`` are accepted.
    name : str
        The name of the argument being checked, shown in the error message.

    Returns
    -------
    bool
        `value` converted to the built-in ``bool``.

    Raises
    ------
    TypeError
        If `value` is neither ``bool`` nor ``numpy.bool_``, including
        ``None``, ``0``, ``1`` and strings.

    Examples
    --------
    >>> from ternary_diagram.utils import check_bool
    >>> import numpy as np
    >>> check_bool(True, "visible")
    True
    >>> check_bool(np.bool_(False), "visible")
    False
    >>> check_bool(None, "visible")
    Traceback (most recent call last):
        ...
    TypeError: `visible` must be True or False, but got None.
    >>> check_bool("yes", "visible")
    Traceback (most recent call last):
        ...
    TypeError: `visible` must be True or False, but got 'yes'.
    """
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    raise TypeError(f"`{name}` must be True or False, but got {value!r}.")


def three2two(vector: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    """Convert compositions to 2D coordinates on the ternary diagram.

    The triangle has the vertices top ``(0.5, sqrt(3) / 2)``, bottom-left
    ``(0, 0)`` and bottom-right ``(1, 0)``, which correspond to the first,
    second and third components.

    Parameters
    ----------
    vector : array-like of shape (n, 3)
        Compositions whose rows sum to 1, one per row, in the order top,
        bottom-left, bottom-right (counterclockwise from the top vertex).
        The rows are not normalized here; pass the output of
        :func:`check_2d_vector` to convert amounts that do not sum to 1.

    Returns
    -------
    x : numpy.ndarray of shape (n,)
        Horizontal coordinates of the compositions.
    y : numpy.ndarray of shape (n,)
        Vertical coordinates of the compositions.

    Examples
    --------
    >>> from ternary_diagram.utils import check_2d_vector, three2two
    >>> x, y = three2two([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    >>> x
    array([0.5, 0. , 1. ])
    >>> y
    array([0.8660254, 0.       , 0.       ])
    >>> three2two(check_2d_vector([[2, 2, 4]]))
    (array([0.625]), array([0.21650635]))
    """
    arr_vector = np.asarray(vector)
    return (
        (2.0 * arr_vector[:, 2] + arr_vector[:, 0]) / 2.0,
        sqrt(3.0) / 2.0 * arr_vector[:, 0],
    )


def get_label(compound_name: str) -> str:
    """Write every number in a compound name as a LaTeX subscript.

    Each number, a run of digits with an optional decimal part such as
    ``2`` or ``0.5``, is wrapped in ``$_{`` and ``}$`` wherever it appears.
    The text is not checked to be a chemical formula, so the numbers of
    other words (``"Sample 1"``) and of text already written in mathtext
    are converted as well. The vertex labels are formatted with this
    function when ``auto_latex_notation`` of ``TernaryDiagram`` is True.
    To convert only the words that look like chemical formulas, use
    :func:`to_latex_notation`.

    Parameters
    ----------
    compound_name : str
        Name of a compound, such as ``"Li2O"`` or ``"(LiLa)0.5TiO3"``.

    Returns
    -------
    str
        `compound_name` with every number written as a subscript.

    Raises
    ------
    ValueError
        If `compound_name` is not a str.

    Examples
    --------
    >>> from ternary_diagram.utils import get_label
    >>> get_label("Li2O")
    'Li$_{2}$O'
    >>> get_label("(LiLa)0.5TiO3")
    '(LiLa)$_{0.5}$TiO$_{3}$'
    >>> get_label("Sample 1")
    'Sample $_{1}$'
    """
    if not isinstance(compound_name, str):
        raise ValueError("The `compound_name` must be string.")

    f = "$_{"
    b = "}$"
    n_name = len(compound_name)

    # convert str to list
    # (add empty string to the end of the list to add b to the last letter.)
    lst_compound_name = list(compound_name) + [""]

    # find the number in the compound name.
    i = 0
    while i < n_name:
        # if you met a number, find the end of the number.
        letter = compound_name[i]
        if letter.isdigit():
            j = i + 1
            while j < n_name + 1:
                try:
                    float(compound_name[i:j])
                except ValueError:
                    break
                else:
                    j += 1
            j -= 1
            lst_compound_name[i] = f + lst_compound_name[i]
            lst_compound_name[j] = b + lst_compound_name[j]
            i = j
        i += 1
    return "".join(lst_compound_name)


#: A word made only of element-like symbols (an upper case letter and an
#: optional lower case letter), numbers and parentheses, starting with a
#: symbol or an opening parenthesis.
_CHEMICAL_FORMULA = re.compile(
    r"\(*[A-Z][a-z]?(?:[A-Z][a-z]?|\d+(?:\.\d+)?|[()])*"
)


def is_chemical_formula(word: str) -> bool:
    """Tell whether a word looks like a chemical formula.

    A word looks like a chemical formula when it is made only of
    element-like symbols (an upper case letter followed by at most one lower
    case letter, such as ``Li`` or ``O``), numbers (``2``, ``0.5``) and
    balanced parentheses, and starts with a symbol or an opening
    parenthesis. The symbols are not checked against the periodic table, so
    placeholder materials such as ``AB2`` also look like chemical formulas.

    Parameters
    ----------
    word : str
        A word without white space, such as ``"Li2O"``.

    Returns
    -------
    bool
        True if `word` looks like a chemical formula.

    Raises
    ------
    TypeError
        If `word` is not a str.

    Examples
    --------
    >>> from ternary_diagram.utils import is_chemical_formula
    >>> is_chemical_formula("Li2O")
    True
    >>> is_chemical_formula("(LiLa)0.5TiO3")
    True
    >>> is_chemical_formula("Sample")
    False
    >>> is_chemical_formula("1")
    False
    """
    if not isinstance(word, str):
        raise TypeError(f"`word` must be a str, but got {word!r}.")
    if _CHEMICAL_FORMULA.fullmatch(word) is None:
        return False
    depth = 0
    for letter in word:
        if letter == "(":
            depth += 1
        elif letter == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def to_latex_notation(text: str) -> str:
    """Write the numbers of the chemical formulas in a text as subscripts.

    The text is split at white space, and each word that looks like a
    chemical formula (see :func:`is_chemical_formula`) is converted by
    :func:`get_label`. The other words and the white space are kept as
    they are. A text containing ``$`` is returned unchanged, because it is
    already written in mathtext.

    Parameters
    ----------
    text : str
        A text such as a label of a point, like ``"LiF + Li2O"``.

    Returns
    -------
    str
        `text` with the chemical formulas in LaTeX notation.

    Raises
    ------
    TypeError
        If `text` is not a str.

    Examples
    --------
    >>> from ternary_diagram.utils import to_latex_notation
    >>> to_latex_notation("Li2O")
    'Li$_{2}$O'
    >>> to_latex_notation("LiF + Li2O")
    'LiF + Li$_{2}$O'
    >>> to_latex_notation("Sample 1")
    'Sample 1'
    >>> to_latex_notation("$x_1$")
    '$x_1$'
    """
    if not isinstance(text, str):
        raise TypeError(f"`text` must be a str, but got {text!r}.")
    if "$" in text:
        return text
    return "".join(
        get_label(word) if is_chemical_formula(word) else word
        for word in re.split(r"(\s+)", text)
    )


def get_tick_values(step: float, endpoints: bool = False) -> np.ndarray:
    """Return the values of the ticks or the grid lines for an interval.

    The values are the multiples of `step` in the open interval (0, 1) in
    ascending order, rounded to 12 decimal places to suppress
    floating-point errors.

    Parameters
    ----------
    step : float
        Interval between the values as a fraction in the range
        ``0 < step <= 1``. ``bool`` is not accepted.
    endpoints : bool, optional
        Whether to add 0 and 1 at both ends, by default False

    Returns
    -------
    numpy.ndarray
        One-dimensional array of the values as floats in ascending order.
        It is empty when `step` is 1 and `endpoints` is False.

    Raises
    ------
    TypeError
        If `step` is not a real number (``bool`` is rejected), or if
        `endpoints` is neither True nor False.
    ValueError
        If `step` is not finite or not in the range ``0 < step <= 1``.

    Examples
    --------
    >>> from ternary_diagram.utils import get_tick_values
    >>> get_tick_values(0.25).tolist()
    [0.25, 0.5, 0.75]
    >>> get_tick_values(0.1).tolist()
    [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    >>> len(get_tick_values(0.05))
    19
    >>> get_tick_values(0.25, endpoints=True).tolist()
    [0.0, 0.25, 0.5, 0.75, 1.0]
    >>> get_tick_values(1).tolist()
    []
    >>> get_tick_values(0)
    Traceback (most recent call last):
        ...
    ValueError: `step` must satisfy 0 < step <= 1, but got 0.
    """
    if isinstance(step, (bool, np.bool_)) or not isinstance(step, Real):
        raise TypeError(f"`step` must be a real number, but got {step!r}.")
    # Also rejects nan and +-inf without converting huge ints to float.
    if not (0 < step <= 1):
        raise ValueError(
            f"`step` must satisfy 0 < step <= 1, but got {step!r}."
        )
    with_endpoints = check_bool(endpoints, "endpoints")

    step = float(step)
    # One extra multiple so that the last one below 1 is never missed.
    n_multiples = int(np.ceil(1.0 / step)) + 1
    multiples = np.round(np.arange(1, n_multiples + 1) * step, 12)
    values = multiples[(multiples > 0.0) & (multiples < 1.0)]
    if with_endpoints:
        return np.concatenate(([0.0], values, [1.0]))
    return values


def _check_component(component: object) -> int:
    # bool is rejected although True == 1, and so are floats such as 1.0.
    if (
        isinstance(component, (bool, np.bool_))
        or not isinstance(component, Integral)
        or component not in (0, 1, 2)
    ):
        raise ValueError(
            f"`component` must be 0, 1 or 2, but got {component!r}."
        )
    return int(component)


def _iso_compositions(
    values: ArrayLike, component: int, zero: int
) -> np.ndarray:
    """Compositions where `component` equals `values` and `zero` is 0."""
    arr_values = np.atleast_1d(np.asarray(values, dtype=float))
    if arr_values.ndim != 1:
        raise ValueError(
            "`values` must be a scalar or one-dimensional, but got shape "
            f"{arr_values.shape}."
        )
    compositions = np.zeros((len(arr_values), 3))
    compositions[:, component] = arr_values
    compositions[:, 3 - component - zero] = 1.0 - arr_values
    return compositions


def get_edge_points(
    values: ArrayLike, component: int
) -> tuple[np.ndarray, np.ndarray]:
    """Return the points for values on the edge of a component's ticks.

    The ticks of component ``k`` are on the edge where component
    ``(k + 1) % 3`` is 0: the right edge for component 0 (top vertex), the
    left edge for component 1 (bottom-left vertex) and the bottom edge for
    component 2 (bottom-right vertex). Along each edge the values increase
    counterclockwise, from 0 at the vertex of component ``(k + 2) % 3`` to
    1 at the vertex of component ``k``. The points are computed with
    :func:`three2two`.

    Parameters
    ----------
    values : ArrayLike
        Values of `component` as fractions in [0, 1], given as a scalar or
        a one-dimensional sequence.
    component : int
        Index of the component in the order of the vertices: 0 (top),
        1 (bottom left) or 2 (bottom right).

    Returns
    -------
    x : numpy.ndarray
        x coordinates of the points, a one-dimensional array with one
        element per value.
    y : numpy.ndarray
        y coordinates of the points, with the same shape as `x`.

    Raises
    ------
    ValueError
        If `component` is not 0, 1 or 2 (``bool`` and floats are
        rejected), or if `values` has more than one dimension.

    Examples
    --------
    >>> from ternary_diagram.utils import get_edge_points
    >>> x, y = get_edge_points([0.0, 0.5, 1.0], 2)
    >>> x.tolist(), y.tolist()
    ([0.0, 0.5, 1.0], [0.0, 0.0, 0.0])
    >>> x, y = get_edge_points([0.0, 1.0], 0)
    >>> x.round(3).tolist(), y.round(3).tolist()
    ([1.0, 0.5], [0.0, 0.866])
    >>> get_edge_points([0.5], 3)
    Traceback (most recent call last):
        ...
    ValueError: `component` must be 0, 1 or 2, but got 3.
    """
    k = _check_component(component)
    return three2two(_iso_compositions(values, k, zero=(k + 1) % 3))


def get_grid_segments(
    values: ArrayLike, component: int
) -> tuple[np.ndarray, np.ndarray]:
    """Return the end points of the iso-composition lines of a component.

    The line where `component` (``k``) equals a value runs between two
    edges. It starts on the edge where component ``(k + 1) % 3`` is 0,
    which carries the ticks of `component` (see :func:`get_edge_points`),
    and ends on the edge where component ``(k + 2) % 3`` is 0. The points
    are computed with :func:`three2two`.

    Parameters
    ----------
    values : ArrayLike
        Values of `component` on the lines as fractions in [0, 1], given as
        a scalar or a one-dimensional sequence.
    component : int
        Index of the component in the order of the vertices: 0 (top),
        1 (bottom left) or 2 (bottom right).

    Returns
    -------
    xs : numpy.ndarray
        x coordinates of the end points, an array of shape ``(n, 2)`` where
        ``n`` is the number of values. Row ``i`` is the line of the
        ``i``-th value: column 0 is its start on the tick edge and column 1
        its end.
    ys : numpy.ndarray
        y coordinates of the end points, with the same layout as `xs`.

    Raises
    ------
    ValueError
        If `component` is not 0, 1 or 2 (``bool`` and floats are
        rejected), or if `values` has more than one dimension.

    Examples
    --------
    >>> from ternary_diagram.utils import get_grid_segments
    >>> xs, ys = get_grid_segments([0.5], 2)
    >>> xs.round(3).tolist(), ys.round(3).tolist()
    ([[0.5, 0.75]], [[0.0, 0.433]])
    >>> xs, ys = get_grid_segments([0.25, 0.5, 0.75], 0)
    >>> xs.shape, ys.shape
    ((3, 2), (3, 2))
    """
    k = _check_component(component)
    start_x, start_y = get_edge_points(values, k)
    end_x, end_y = three2two(_iso_compositions(values, k, zero=(k + 2) % 3))
    return np.column_stack((start_x, end_x)), np.column_stack((start_y, end_y))


def get_axis_label_position(
    component: int, pad: float
) -> tuple[float, float, float]:
    """Return the position and rotation of the axis title of a component.

    The title is placed outside the edge that carries the ticks of
    `component` (see :func:`get_edge_points`): at the midpoint of the edge
    moved by `pad` along the outward unit normal of the edge. The rotation
    makes the text parallel to the edge and never upside down.

    Parameters
    ----------
    component : int
        Index of the component in the order of the vertices: 0 (top),
        1 (bottom left) or 2 (bottom right).
    pad : float
        Distance from the midpoint of the edge to the title in data
        coordinates, where each edge has length 1. Positive values move
        the title away from the triangle. ``bool`` is not accepted.

    Returns
    -------
    x : float
        x coordinate of the title.
    y : float
        y coordinate of the title.
    rotation : float
        Rotation of the title in degrees: 300 for the right edge
        (component 0), 60 for the left edge (component 1) and 0 for the
        bottom edge (component 2).

    Raises
    ------
    TypeError
        If `pad` is not a real number (``bool`` is rejected).
    ValueError
        If `component` is not 0, 1 or 2 (``bool`` and floats are
        rejected), or if `pad` is not finite.

    Examples
    --------
    >>> from ternary_diagram.utils import get_axis_label_position
    >>> get_axis_label_position(2, 0.15)
    (0.5, -0.15, 0.0)
    >>> x, y, rotation = get_axis_label_position(0, 0.15)
    >>> round(x, 3), round(y, 3), rotation
    (0.88, 0.508, 300.0)
    >>> x, y, rotation = get_axis_label_position(1, 0.15)
    >>> round(x, 3), round(y, 3), rotation
    (0.12, 0.508, 60.0)
    """
    k = _check_component(component)
    if isinstance(pad, (bool, np.bool_)) or not isinstance(pad, Real):
        raise TypeError(f"`pad` must be a real number, but got {pad!r}.")
    try:
        distance = float(pad)
    except OverflowError:
        # An int or a Fraction too large for a float
        distance = float("inf")
    if not isfinite(distance):
        raise ValueError(
            f"`pad` must be a finite real number, but got {pad!r}."
        )

    (mid_x,), (mid_y,) = get_edge_points([0.5], k)
    # The edge where component k+1 is 0 is opposite to the vertex of
    # component k+1, and the median from that vertex is perpendicular to
    # the edge, so it points along the outward normal.
    opposite = np.zeros((1, 3))
    opposite[0, (k + 1) % 3] = 1.0
    (vertex_x,), (vertex_y,) = three2two(opposite)
    median_length = float(np.hypot(mid_x - vertex_x, mid_y - vertex_y))
    rotation = (300.0, 60.0, 0.0)[k]
    return (
        float(mid_x + distance * (mid_x - vertex_x) / median_length),
        float(mid_y + distance * (mid_y - vertex_y) / median_length),
        rotation,
    )


def get_tick_formatter(fmt: TickFormat) -> Callable[[float], str]:
    """Return a function that turns a tick value into its label.

    Parameters
    ----------
    fmt : str or callable
        Format of the labels. The values given to the returned function
        are fractions in [0, 1]. One of:

        - ``"percent"``: the value as a percentage without unnecessary
          digits (0.1 -> ``"10"``, 0.025 -> ``"2.5"``, 1 -> ``"100"``).
        - ``"fraction"``: the value as a fraction (0.1 -> ``"0.1"``).
        - Any other str: a format string applied to the fraction.
          %-style (``"%.2f"``) is tried first, and {}-style
          (``"{:.0%}"``, ``"{x:.1f}"``) is used if it fails.
        - A callable that takes the fraction as a float. Its return value
          is converted with ``str``, and its exceptions propagate when the
          returned function is called.

    Returns
    -------
    callable
        Function that takes a value and returns its label as a str.

    Raises
    ------
    TypeError
        If `fmt` is neither a str nor a callable.
    ValueError
        If `fmt` is a str that is neither ``"percent"`` nor
        ``"fraction"`` and either contains neither ``%`` nor ``{`` or
        cannot format the trial value 0.5 in either style.

    Examples
    --------
    >>> from ternary_diagram.utils import get_tick_formatter
    >>> percent = get_tick_formatter("percent")
    >>> [percent(value) for value in (0.1, 0.025, 1.0)]
    ['10', '2.5', '100']
    >>> get_tick_formatter("fraction")(0.1)
    '0.1'
    >>> get_tick_formatter("%.2f")(0.1)
    '0.10'
    >>> get_tick_formatter("{:.0%}")(0.1)
    '10%'
    >>> get_tick_formatter("{x:.1f}")(0.1)
    '0.1'
    >>> get_tick_formatter(lambda value: f"{value * 100:.1f}%")(0.1)
    '10.0%'
    """
    if callable(fmt):
        func = fmt
        return lambda value: str(func(float(value)))
    if not isinstance(fmt, str):
        raise TypeError(f"`fmt` must be a str or a callable, but got {fmt!r}.")
    if fmt == "percent":
        return lambda value: format(round(float(value) * 100, 10), "g")
    if fmt == "fraction":
        return lambda value: format(round(float(value), 12), "g")

    accepted = (
        "'percent', 'fraction', a %-style or {}-style format string "
        "(e.g. '%.2f', '{:.0%}', '{x:.1f}') or a callable"
    )
    if "%" not in fmt and "{" not in fmt:
        raise ValueError(f"`fmt` must be {accepted}, but got {fmt!r}.")
    probe = 0.5
    try:
        fmt % probe
    except (TypeError, ValueError):
        pass
    else:
        return lambda value: fmt % float(value)
    try:
        fmt.format(probe, x=probe)
    except (TypeError, ValueError, KeyError, IndexError, AttributeError) as e:
        raise ValueError(
            f"`fmt` {fmt!r} cannot format the value {probe} as a %-style "
            f"or {{}}-style format string. `fmt` must be {accepted}."
        ) from e
    return lambda value: fmt.format(float(value), x=float(value))


def _lattice_indices(scale: int) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(i, j)`` of the points with ``i + j + k = scale``.

    The points are in descending ``i``, then descending ``j``. Both arrays
    are empty when `scale` is negative.
    """
    rows = np.arange(scale + 1, dtype=np.intp)
    row = np.repeat(rows, rows + 1)
    # k equals the position of the point within its row.
    k = np.arange(len(row), dtype=np.intp) - row * (row + 1) // 2
    return scale - row, row - k


def get_triangular_lattice(scale: int) -> tuple[np.ndarray, np.ndarray]:
    """Return a regular triangular lattice with `scale` parts on each edge.

    The lattice points are all the compositions whose components are
    multiples of ``1 / scale`` and sum to 1, and the small triangles cover
    the whole diagram without overlaps or gaps, all with the same area.

    Parameters
    ----------
    scale : int
        Number of parts into which each edge is divided, 1 or greater.
        Integer types of numpy are accepted, ``bool`` is not.

    Returns
    -------
    vertices : numpy.ndarray
        Compositions of the lattice points, a float array of shape
        ``((scale + 1) * (scale + 2) // 2, 3)``. Each row is
        ``(i, j, k) / scale`` with non-negative integers
        ``i + j + k = scale``, and the columns are in the order of the
        vertices of the diagram (top, bottom left, bottom right). The rows
        are in descending ``i``, then descending ``j``: from the top row to
        the bottom row of the diagram, and from left to right within a row.
    triangles : numpy.ndarray
        Small triangles as the row numbers of three `vertices`, an array of
        ``numpy.intp`` with shape ``(scale ** 2, 3)``. The
        ``scale * (scale + 1) // 2`` upward triangles come first, each as
        its top, bottom-left and bottom-right vertices, followed by the
        ``scale * (scale - 1) // 2`` downward triangles, each as its
        bottom, upper-right and upper-left vertices. Every triangle is
        counterclockwise in the coordinates of :func:`three2two`. Within
        each group the triangles are ordered from the top row to the bottom
        row of the diagram, and from left to right within a row.

    Raises
    ------
    TypeError
        If `scale` is not an integer (``bool`` is rejected).
    ValueError
        If `scale` is less than 1.

    Examples
    --------
    >>> from ternary_diagram.utils import get_triangular_lattice
    >>> vertices, triangles = get_triangular_lattice(1)
    >>> vertices.tolist()
    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    >>> triangles.tolist()
    [[0, 1, 2]]
    >>> vertices, triangles = get_triangular_lattice(2)
    >>> vertices.shape, triangles.shape
    ((6, 3), (4, 3))
    >>> for row in vertices.tolist():
    ...     print(row)
    [1.0, 0.0, 0.0]
    [0.5, 0.5, 0.0]
    [0.5, 0.0, 0.5]
    [0.0, 1.0, 0.0]
    [0.0, 0.5, 0.5]
    [0.0, 0.0, 1.0]
    >>> triangles.tolist()
    [[0, 1, 2], [1, 3, 4], [2, 4, 5], [4, 2, 1]]
    >>> get_triangular_lattice(0)
    Traceback (most recent call last):
        ...
    ValueError: `scale` must be 1 or greater, but got 0.
    """
    if isinstance(scale, (bool, np.bool_)) or not isinstance(scale, Integral):
        raise TypeError(f"`scale` must be an integer, but got {scale!r}.")
    if scale < 1:
        raise ValueError(f"`scale` must be 1 or greater, but got {scale!r}.")
    n = int(scale)

    def index(i: np.ndarray, j: np.ndarray) -> np.ndarray:
        # Row number in `vertices` of the point (i, j, n - i - j).
        row = n - i
        return row * (row + 1) // 2 + row - j

    i, j = _lattice_indices(n)
    vertices = np.stack((i, j, n - i - j), axis=1) / n

    # Upward triangles on the bases (i, j, k) with i + j + k = n - 1.
    bi, bj = _lattice_indices(n - 1)
    upward = np.stack(
        (index(bi + 1, bj), index(bi, bj + 1), index(bi, bj)), axis=1
    )
    # Downward triangles on the bases (i, j, k) with i + j + k = n - 2.
    bi, bj = _lattice_indices(n - 2)
    downward = np.stack(
        (index(bi, bj + 1), index(bi + 1, bj), index(bi + 1, bj + 1)),
        axis=1,
    )
    triangles = np.concatenate((upward, downward)).astype(np.intp)
    return vertices, triangles


if __name__ == "__main__":
    from doctest import testmod

    testmod(verbose=True)
