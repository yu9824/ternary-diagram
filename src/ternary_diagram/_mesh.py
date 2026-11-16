"""Computation and validation for the plots that paint triangles.

The functions here validate the arguments of ``tripcolor`` and
``heatmapf``, triangulate the compositions, find the triangles that cannot
be painted, compute the default color range, evaluate the function of
``heatmapf`` and build the message of the warning about duplicated
compositions. None of them draws, warns or changes its arguments: they
only read the arguments and return new objects.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Callable, Final, Literal, Union, cast

import matplotlib.collections
import numpy as np
from matplotlib.tri import Triangulation
from numpy.typing import ArrayLike

__all__ = (
    "DEFAULT_HEATMAPF_SCALE",
    "HeatmapFunc",
    "MeshCollection",
    "SHADINGS",
    "Shading",
    "check_mesh_kwargs",
    "check_shading",
    "default_color_range",
    "duplicate_points_message",
    "evaluate_function",
    "triangulate",
    "unpaintable_mask",
)

# Type aliases are evaluated at runtime, so they use the typing forms that
# work on Python 3.9.
Shading = Literal["flat", "gouraud"]
HeatmapFunc = Callable[[np.ndarray, np.ndarray, np.ndarray], ArrayLike]
MeshCollection = Union[
    matplotlib.collections.PolyCollection, matplotlib.collections.TriMesh
]

SHADINGS: Final[tuple[str, ...]] = ("flat", "gouraud")
DEFAULT_HEATMAPF_SCALE: Final[int] = 50

_NO_PAINTABLE_TRIANGLE_MESSAGE: Final[str] = (
    "No triangle can be painted: all values are NaN or infinite, "
    "or all triangles are masked."
)


def check_shading(shading: object) -> Shading:
    """Check the shading of a plot that paints triangles.

    Parameters
    ----------
    shading : object
        The shading given by the user.

    Returns
    -------
    Shading
        ``shading`` itself.

    Raises
    ------
    ValueError
        If ``shading`` is neither ``'flat'`` nor ``'gouraud'``.
    """
    if isinstance(shading, str) and shading in SHADINGS:
        return cast(Shading, shading)
    raise ValueError(
        f"`shading` must be 'flat' or 'gouraud', but got {shading!r}."
    )


def check_mesh_kwargs(
    kwargs: Mapping[str, object],
    *,
    func: str,
    color_source: str,
    fixed_lattice: bool,
) -> None:
    """Reject the keyword arguments that conflict with painting triangles.

    The checks are done in this order: ``flag_cbar``, ``c`` and
    ``facecolors``, then ``triangles`` and ``mask`` when the lattice is
    fixed. ``kwargs`` is not changed.

    Parameters
    ----------
    kwargs : Mapping[str, object]
        The keyword arguments given by the user.
    func : str
        Name of the public method, used in the messages.
    color_source : str
        Name of the argument that determines the colors, such as ``'z'`` or
        ``'func'``.
    fixed_lattice : bool
        Whether the plot always uses a regular triangular lattice, so that
        ``triangles`` and ``mask`` cannot be given.

    Raises
    ------
    TypeError
        If ``kwargs`` contains the old name ``flag_cbar``.
    ValueError
        If ``kwargs`` contains ``c`` or ``facecolors``, or ``triangles`` or
        ``mask`` while ``fixed_lattice`` is true.
    """
    if "flag_cbar" in kwargs:
        raise TypeError(
            f"`{func}` does not accept `flag_cbar`. Use `colorbar` instead."
        )
    for name in ("c", "facecolors"):
        if name in kwargs:
            raise ValueError(
                f"`{name}` cannot be used together with `{color_source}` "
                f"because the colors are determined by `{color_source}`."
            )
    if fixed_lattice:
        for name in ("triangles", "mask"):
            if name in kwargs:
                raise ValueError(
                    f"`{name}` cannot be specified for `{func}` because it "
                    "always uses a regular triangular lattice. Return NaN "
                    "from `func` to leave regions unpainted."
                )


def triangulate(
    x: np.ndarray,
    y: np.ndarray,
    triangles: ArrayLike | None = None,
    mask: ArrayLike | None = None,
) -> tuple[Triangulation, int]:
    """Triangulate the points on a ternary diagram.

    Parameters
    ----------
    x, y : np.ndarray
        Two-dimensional coordinates of the points, shape ``(n,)``.
    triangles : ArrayLike or None, optional
        Indices of the 3 points of each triangle, shape ``(ntri, 3)``. If
        None, the points are triangulated automatically (Delaunay), which
        covers only the inside of their convex hull, by default None
    mask : ArrayLike or None, optional
        Boolean array of shape ``(ntri,)`` telling which triangles are not
        painted. If None, no triangle is masked, by default None

    Returns
    -------
    triangulation : Triangulation
        A new triangulation with ``mask`` applied.
    n_unused : int
        Number of points used by no triangle, such as duplicated points
        dropped by the automatic triangulation. It is 0 when ``triangles``
        is given.

    Raises
    ------
    ValueError
        If the automatic triangulation fails because there are fewer than 3
        distinct, finite points or all of them are on one straight line. The
        original exception is chained. Errors in validating ``triangles`` or
        ``mask`` are raised by matplotlib as they are.
    """
    if triangles is not None:
        return Triangulation(x, y, triangles, mask), 0

    try:
        triangulation = Triangulation(x, y)
    except (ValueError, RuntimeError) as err:
        raise ValueError(
            "Cannot triangulate the compositions automatically: at least 3 "
            "distinct, finite compositions that are not all on one straight "
            "line are required."
        ) from err
    if mask is not None:
        triangulation.set_mask(mask)
    n_unused = len(x) - np.unique(triangulation.triangles).size
    return triangulation, int(n_unused)


def unpaintable_mask(
    triangulation: Triangulation, values: np.ndarray, *, on_faces: bool
) -> np.ndarray:
    """Find the triangles that cannot be painted.

    Parameters
    ----------
    triangulation : Triangulation
        The triangulation to paint. Its mask is read but not changed.
    values : np.ndarray
        Values that determine the colors. One value per triangle if
        ``on_faces`` is true, otherwise one value per point.
    on_faces : bool
        Whether ``values`` are given per triangle (true) or per point
        (false).

    Returns
    -------
    np.ndarray
        A new boolean array of shape ``(ntri,)``. A triangle is true if its
        value is not finite (``on_faces=True``), if any of its 3 points has a
        value that is not finite (``on_faces=False``), or if it is already
        masked in ``triangulation``.

    Raises
    ------
    ValueError
        If no triangle can be painted.
    """
    # ``~`` already returns a new array, so ``bad`` shares no memory with
    # ``values``.
    bad = ~np.isfinite(np.asarray(values, dtype=float))
    if on_faces:
        unpaintable = bad
    else:
        unpaintable = bad[triangulation.triangles].any(axis=1)
    if triangulation.mask is not None:
        unpaintable = unpaintable | np.asarray(triangulation.mask, dtype=bool)
    if unpaintable.all():
        raise ValueError(_NO_PAINTABLE_TRIANGLE_MESSAGE)
    return unpaintable


def default_color_range(
    values: np.ndarray, z_min: float | None, z_max: float | None
) -> tuple[float, float]:
    """Fill the unspecified sides of the color range.

    Parameters
    ----------
    values : np.ndarray
        Values that determine the colors.
    z_min : float or None
        Lower limit of the color range given by the user. If None, the
        minimum of the finite values is used.
    z_max : float or None
        Upper limit of the color range given by the user. If None, the
        maximum of the finite values is used.

    Returns
    -------
    tuple[float, float]
        The lower and upper limits. A given limit is returned as it is.

    Raises
    ------
    ValueError
        If a limit has to be filled but no value is finite.
    """
    if z_min is not None and z_max is not None:
        return z_min, z_max

    array = np.asarray(values, dtype=float)
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        raise ValueError(_NO_PAINTABLE_TRIANGLE_MESSAGE)
    vmin = float(finite.min()) if z_min is None else z_min
    vmax = float(finite.max()) if z_max is None else z_max
    return vmin, vmax


def evaluate_function(func: object, points: np.ndarray) -> np.ndarray:
    """Evaluate a function at all the points with a single call.

    Parameters
    ----------
    func : object
        The function given by the user, called as ``func(a, b, c)``.
    points : np.ndarray
        Compositions of the evaluation points, shape ``(m, 3)``. It is not
        changed even if ``func`` changes its arguments.

    Returns
    -------
    np.ndarray
        A new float array of shape ``(m,)``. Masked values returned by
        ``func`` become NaN.

    Raises
    ------
    TypeError
        If ``func`` is not callable.
    ValueError
        If ``func`` returns values that cannot be converted to numbers, or
        an array whose shape is none of ``(m,)``, ``(m, 1)`` and ``(1, m)``.
        Exceptions raised by ``func`` itself are propagated as they are.
    """
    if not callable(func):
        raise TypeError(f"`func` must be callable, but got {func!r}.")

    n_points = len(points)
    # Each column is copied into a new contiguous array, so ``func`` cannot
    # change ``points`` through its arguments.
    a, b, c = (np.array(points[:, i], dtype=float) for i in range(3))
    raw = func(a, b, c)

    expected = (
        f"`func` must return {n_points} numeric values (an array of shape "
        f"({n_points},))"
    )
    hint = "If `func` only accepts scalars, wrap it with `numpy.vectorize`."
    try:
        values = np.ma.asarray(raw, dtype=float).filled(np.nan)
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"{expected}, but returned {type(raw).__name__!r} that cannot "
            f"be converted to numbers. {hint}"
        ) from err
    if values.shape not in ((n_points,), (n_points, 1), (1, n_points)):
        raise ValueError(
            f"{expected}, but returned an array of shape {values.shape}. "
            f"{hint}"
        )
    # ``filled`` may return a view of the array returned by ``func``.
    return np.array(values.reshape(n_points), dtype=float)


def duplicate_points_message(n_unused: int) -> str:
    """Build the message of the warning about duplicated compositions.

    Parameters
    ----------
    n_unused : int
        Number of points that the triangulation did not use.

    Returns
    -------
    str
        The message of the warning.
    """
    if n_unused == 1:
        subject, verb = "point was", "it has"
    else:
        subject, verb = "points were", "they have"
    return (
        f"{n_unused} composition {subject} not used because {verb} the "
        "same composition as another point after normalization; only the "
        "value of one of them is drawn. Aggregate the `z` values of "
        "duplicated compositions (for example, by averaging them) before "
        "calling `tripcolor`."
    )
