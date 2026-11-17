"""Unit tests of ``ternary_diagram._mesh`` (no figure is created)."""

from __future__ import annotations

import typing

import matplotlib.collections
import numpy as np
import pytest
from matplotlib.tri import Triangulation

from ternary_diagram import _mesh
from ternary_diagram._mesh import (
    DEFAULT_HEATMAPF_SCALE,
    SHADINGS,
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

AUTO_TRIANGULATION_MESSAGE = "Cannot triangulate the compositions"
NO_TRIANGLE_MESSAGE = "No triangle can be painted"

# The 3 corners of a triangle and 1 point inside it.
X4 = np.array([0.0, 1.0, 0.5, 0.5])
Y4 = np.array([0.0, 0.0, 1.0, 0.3])


def _four_point_triangulation(mask=None) -> Triangulation:
    return Triangulation(X4.copy(), Y4.copy(), mask=mask)


# ---------------------------------------------------------------------------
# Constants and type aliases
# ---------------------------------------------------------------------------


def test_constants():
    assert SHADINGS == ("flat", "gouraud")
    assert DEFAULT_HEATMAPF_SCALE == 50


def test_type_aliases_are_usable_at_runtime():
    assert typing.get_args(Shading) == ("flat", "gouraud")
    assert set(typing.get_args(MeshCollection)) == {
        matplotlib.collections.PolyCollection,
        matplotlib.collections.TriMesh,
    }
    # HeatmapFunc takes the 3 components as 3 arrays.
    args, _ = typing.get_args(_mesh.HeatmapFunc)
    assert args == [np.ndarray, np.ndarray, np.ndarray]


def test_module_imports_nothing_from_the_package():
    source = open(_mesh.__file__, encoding="utf-8").read()
    assert "from ternary_diagram" not in source
    assert "import ternary_diagram" not in source
    assert "from ." not in source


# ---------------------------------------------------------------------------
# check_shading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_check_shading_accepts(shading):
    assert check_shading(shading) == shading


@pytest.mark.parametrize(
    "shading", ["Flat", "nearest", "auto", "", None, 1, ["flat"]]
)
def test_check_shading_rejects(shading):
    with pytest.raises(ValueError, match="'flat' or 'gouraud'") as excinfo:
        check_shading(shading)
    assert repr(shading) in str(excinfo.value)


# ---------------------------------------------------------------------------
# check_mesh_kwargs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixed_lattice", [True, False])
def test_check_mesh_kwargs_accepts_other_kwargs(fixed_lattice):
    kwargs = {"alpha": 0.5, "edgecolors": "face", "cmap": "viridis"}
    assert (
        check_mesh_kwargs(
            kwargs,
            func="tripcolor",
            color_source="z",
            fixed_lattice=fixed_lattice,
        )
        is None
    )


def test_check_mesh_kwargs_accepts_triangles_and_mask_without_fixed_lattice():
    kwargs = {"triangles": [[0, 1, 2]], "mask": [False]}
    check_mesh_kwargs(
        kwargs, func="tripcolor", color_source="z", fixed_lattice=False
    )


@pytest.mark.parametrize("func", ["tripcolor", "heatmapf"])
def test_check_mesh_kwargs_rejects_flag_cbar(func):
    with pytest.raises(TypeError, match="Use `colorbar` instead") as excinfo:
        check_mesh_kwargs(
            {"flag_cbar": False},
            func=func,
            color_source="z",
            fixed_lattice=False,
        )
    assert f"`{func}` does not accept `flag_cbar`" in str(excinfo.value)


@pytest.mark.parametrize("name", ["c", "facecolors"])
@pytest.mark.parametrize(
    "func, color_source", [("tripcolor", "z"), ("heatmapf", "func")]
)
def test_check_mesh_kwargs_rejects_color_kwargs(name, func, color_source):
    with pytest.raises(ValueError) as excinfo:
        check_mesh_kwargs(
            {name: "red"},
            func=func,
            color_source=color_source,
            fixed_lattice=func == "heatmapf",
        )
    message = str(excinfo.value)
    assert f"`{name}` cannot be used together with `{color_source}`" in message


@pytest.mark.parametrize("name", ["triangles", "mask"])
def test_check_mesh_kwargs_rejects_lattice_kwargs_with_fixed_lattice(name):
    with pytest.raises(ValueError, match="Return NaN from `func`") as excinfo:
        check_mesh_kwargs(
            {name: [0]},
            func="heatmapf",
            color_source="func",
            fixed_lattice=True,
        )
    assert f"`{name}` cannot be specified for `heatmapf`" in str(excinfo.value)


def test_check_mesh_kwargs_checks_flag_cbar_first():
    # flag_cbar is reported before the other problems.
    with pytest.raises(TypeError):
        check_mesh_kwargs(
            {"c": "red", "mask": [0], "flag_cbar": True},
            func="heatmapf",
            color_source="func",
            fixed_lattice=True,
        )


def test_check_mesh_kwargs_does_not_change_kwargs():
    kwargs = {"c": "red", "flag_cbar": True, "alpha": 0.5}
    before = dict(kwargs)
    with pytest.raises(TypeError):
        check_mesh_kwargs(
            kwargs, func="tripcolor", color_source="z", fixed_lattice=False
        )
    assert kwargs == before

    kwargs = {"alpha": 0.5, "triangles": [[0, 1, 2]]}
    before = dict(kwargs)
    check_mesh_kwargs(
        kwargs, func="tripcolor", color_source="z", fixed_lattice=False
    )
    assert kwargs == before


# ---------------------------------------------------------------------------
# triangulate
# ---------------------------------------------------------------------------


def test_triangulate_automatically():
    tri, n_unused = triangulate(X4, Y4)
    assert isinstance(tri, Triangulation)
    assert tri.triangles.shape == (3, 3)
    assert n_unused == 0
    assert isinstance(n_unused, int)
    assert tri.mask is None
    np.testing.assert_array_equal(tri.x, X4)
    np.testing.assert_array_equal(tri.y, Y4)


def test_triangulate_covers_only_the_convex_hull():
    # 5 points whose convex hull is the triangle of the first 3 points.
    x = np.array([0.0, 1.0, 0.5, 0.5, 0.4])
    y = np.array([0.0, 0.0, 1.0, 0.3, 0.2])
    tri, _ = triangulate(x, y)
    corners_x = x[tri.triangles]
    corners_y = y[tri.triangles]
    areas = 0.5 * np.abs(
        (corners_x[:, 1] - corners_x[:, 0])
        * (corners_y[:, 2] - corners_y[:, 0])
        - (corners_x[:, 2] - corners_x[:, 0])
        * (corners_y[:, 1] - corners_y[:, 0])
    )
    assert areas.sum() == pytest.approx(0.5)


def test_triangulate_counts_duplicated_points():
    x = np.append(X4, X4[3])
    y = np.append(Y4, Y4[3])
    tri, n_unused = triangulate(x, y)
    assert n_unused == 1
    assert tri.triangles.shape == (3, 3)


def test_triangulate_applies_mask_after_automatic_triangulation():
    mask = [True, False, False]
    tri, n_unused = triangulate(X4, Y4, mask=mask)
    np.testing.assert_array_equal(tri.mask, mask)
    assert n_unused == 0


def test_triangulate_does_not_wrap_mask_errors():
    with pytest.raises(ValueError) as excinfo:
        triangulate(X4, Y4, mask=[True])
    assert AUTO_TRIANGULATION_MESSAGE not in str(excinfo.value)


def test_triangulate_with_triangles():
    triangles = [[0, 1, 2]]
    tri, n_unused = triangulate(X4, Y4, triangles=triangles)
    np.testing.assert_array_equal(tri.triangles, triangles)
    # Points not used by the given triangles are not reported.
    assert n_unused == 0
    assert tri.mask is None


def test_triangulate_with_triangles_and_mask():
    triangles = [[0, 1, 3], [1, 2, 3], [2, 0, 3]]
    mask = [False, True, False]
    tri, n_unused = triangulate(X4, Y4, triangles=triangles, mask=mask)
    np.testing.assert_array_equal(tri.triangles, triangles)
    np.testing.assert_array_equal(tri.mask, mask)
    assert n_unused == 0


def test_triangulate_leaves_validation_of_triangles_to_matplotlib():
    with pytest.raises(ValueError) as excinfo:
        triangulate(X4, Y4, triangles=[[0, 1, 9]])
    assert AUTO_TRIANGULATION_MESSAGE not in str(excinfo.value)
    assert excinfo.value.__cause__ is None


@pytest.mark.parametrize(
    "x, y, cause_type",
    [
        pytest.param([0.0, 1.0], [0.0, 0.0], ValueError, id="2 points"),
        pytest.param(
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0, 1.0],
            ValueError,
            id="2 distinct points",
        ),
        pytest.param(
            [0.0, 0.5, 1.0], [0.0, 0.5, 1.0], RuntimeError, id="collinear"
        ),
    ],
)
def test_triangulate_wraps_automatic_triangulation_errors(x, y, cause_type):
    with pytest.raises(ValueError, match=AUTO_TRIANGULATION_MESSAGE) as exc:
        triangulate(np.array(x), np.array(y))
    assert "at least 3 distinct" in str(exc.value)
    assert "straight line" in str(exc.value)
    assert isinstance(exc.value.__cause__, cause_type)
    assert AUTO_TRIANGULATION_MESSAGE not in str(exc.value.__cause__)


@pytest.mark.parametrize("error_type", [ValueError, RuntimeError])
def test_triangulate_chains_the_original_exception(monkeypatch, error_type):
    original = error_type("original error from qhull")

    def fail(*args, **kwargs):
        raise original

    monkeypatch.setattr(_mesh, "Triangulation", fail)
    with pytest.raises(ValueError, match=AUTO_TRIANGULATION_MESSAGE) as exc:
        triangulate(X4, Y4)
    assert exc.value.__cause__ is original


def test_triangulate_does_not_change_arguments():
    x = X4.copy()
    y = Y4.copy()
    triangles = np.array([[0, 1, 3], [1, 2, 3], [2, 0, 3]])
    mask = np.array([False, True, False])
    triangles_before = triangles.copy()
    mask_before = mask.copy()

    triangulate(x, y)
    triangulate(x, y, mask=mask)
    triangulate(x, y, triangles=triangles, mask=mask)

    np.testing.assert_array_equal(x, X4)
    np.testing.assert_array_equal(y, Y4)
    np.testing.assert_array_equal(triangles, triangles_before)
    np.testing.assert_array_equal(mask, mask_before)


# ---------------------------------------------------------------------------
# unpaintable_mask
# ---------------------------------------------------------------------------


def _triangles_with_vertex(tri: Triangulation, vertex: int) -> np.ndarray:
    return (tri.triangles == vertex).any(axis=1)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_unpaintable_mask_point_values(bad):
    tri = _four_point_triangulation()
    # Point 1 is a corner used by 2 of the 3 triangles.
    values = np.array([1.0, bad, 3.0, 4.0])
    mask = unpaintable_mask(tri, values, on_faces=False)
    assert mask.dtype == bool
    np.testing.assert_array_equal(mask, _triangles_with_vertex(tri, 1))
    assert mask.sum() == 2


def test_unpaintable_mask_finite_point_values():
    tri = _four_point_triangulation()
    mask = unpaintable_mask(
        tri, np.array([1.0, 2.0, 3.0, 4.0]), on_faces=False
    )
    np.testing.assert_array_equal(mask, [False, False, False])


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_unpaintable_mask_face_values(bad):
    tri = _four_point_triangulation()
    mask = unpaintable_mask(tri, np.array([1.0, bad, 3.0]), on_faces=True)
    np.testing.assert_array_equal(mask, [False, True, False])


@pytest.mark.parametrize("on_faces", [True, False])
def test_unpaintable_mask_combines_existing_mask(on_faces):
    tri = _four_point_triangulation(mask=[True, False, False])
    if on_faces:
        values = np.array([1.0, 2.0, np.nan])
        expected = [True, False, True]
    else:
        values = np.array([1.0, 2.0, 3.0, 4.0])
        expected = [True, False, False]
    mask = unpaintable_mask(tri, values, on_faces=on_faces)
    np.testing.assert_array_equal(mask, expected)


@pytest.mark.parametrize(
    "values, on_faces, existing",
    [
        pytest.param(np.full(4, np.nan), False, None, id="all points nan"),
        pytest.param(np.full(3, np.inf), True, None, id="all faces inf"),
        pytest.param(
            np.array([1.0, 2.0, 3.0, 4.0]),
            False,
            [True, True, True],
            id="all masked",
        ),
        pytest.param(
            np.array([1.0, np.nan, 3.0]),
            True,
            [True, False, True],
            id="masked or nan",
        ),
        pytest.param(
            # The inner point is shared by every triangle.
            np.array([1.0, 2.0, 3.0, np.nan]),
            False,
            None,
            id="shared point nan",
        ),
    ],
)
def test_unpaintable_mask_raises_when_nothing_is_paintable(
    values, on_faces, existing
):
    tri = _four_point_triangulation(mask=existing)
    with pytest.raises(ValueError, match=NO_TRIANGLE_MESSAGE):
        unpaintable_mask(tri, values, on_faces=on_faces)


def test_unpaintable_mask_does_not_change_arguments():
    existing = np.array([True, False, False])
    tri = _four_point_triangulation(mask=existing.copy())
    triangles_before = tri.triangles.copy()
    values = np.array([1.0, np.nan, 3.0, 4.0])
    values_before = values.copy()

    mask = unpaintable_mask(tri, values, on_faces=False)

    np.testing.assert_array_equal(tri.mask, existing)
    np.testing.assert_array_equal(tri.triangles, triangles_before)
    np.testing.assert_array_equal(values, values_before)
    # The result is a new array, not the mask of the triangulation.
    assert mask is not tri.mask
    assert not np.shares_memory(mask, tri.mask)
    mask[:] = False
    np.testing.assert_array_equal(tri.mask, existing)


# ---------------------------------------------------------------------------
# default_color_range
# ---------------------------------------------------------------------------


def test_default_color_range_uses_finite_min_and_max():
    values = np.array([np.nan, 2.0, -np.inf, 5.0, -1.0, np.inf])
    assert default_color_range(values, None, None) == (-1.0, 5.0)


def test_default_color_range_one_side():
    values = np.array([np.nan, 2.0, 5.0, -1.0])
    assert default_color_range(values, 0.0, None) == (0.0, 5.0)
    assert default_color_range(values, None, 3.0) == (-1.0, 3.0)


def test_default_color_range_both_sides():
    values = np.array([np.nan, 2.0, 5.0, -1.0])
    assert default_color_range(values, 0.5, 1.5) == (0.5, 1.5)
    # Nothing has to be filled, so no finite value is needed.
    assert default_color_range(np.full(3, np.nan), 0.5, 1.5) == (0.5, 1.5)


@pytest.mark.parametrize(
    "z_min, z_max", [(None, None), (0.0, None), (None, 1.0)]
)
def test_default_color_range_without_finite_values(z_min, z_max):
    with pytest.raises(ValueError, match=NO_TRIANGLE_MESSAGE):
        default_color_range(np.array([np.nan, np.inf]), z_min, z_max)


def test_default_color_range_returns_python_floats():
    vmin, vmax = default_color_range(np.array([1, 2, 3]), None, None)
    assert (vmin, vmax) == (1.0, 3.0)
    assert type(vmin) is float
    assert type(vmax) is float


def test_default_color_range_does_not_change_values():
    values = np.array([np.nan, 2.0, 5.0])
    before = values.copy()
    default_color_range(values, None, None)
    np.testing.assert_array_equal(values, before)


# ---------------------------------------------------------------------------
# duplicate_points_message
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_unused", [1, 3])
def test_duplicate_points_message(n_unused):
    message = duplicate_points_message(n_unused)
    assert str(n_unused) in message
    assert "same composition" in message
    assert "aggregate" in message.lower()
    assert "`tripcolor`" in message


# ---------------------------------------------------------------------------
# evaluate_function
# ---------------------------------------------------------------------------

# 4 evaluation points; each row sums to 1.
POINTS = np.array(
    [
        [1.0, 0.0, 0.0],
        [0.5, 0.25, 0.25],
        [0.2, 0.3, 0.5],
        [0.0, 0.0, 1.0],
    ]
)
M = len(POINTS)
VECTORIZE_MESSAGE = "numpy.vectorize"


def test_evaluate_function_calls_func_once_with_the_columns():
    calls = []

    def func(*args):
        calls.append(tuple(np.array(arg, copy=True) for arg in args))
        return args[0] + 2 * args[1] + 3 * args[2]

    values = evaluate_function(func, POINTS)

    assert len(calls) == 1
    (args,) = calls
    assert len(args) == 3
    for i, arg in enumerate(args):
        assert arg.shape == (M,)
        assert arg.dtype == float
        np.testing.assert_array_equal(arg, POINTS[:, i])
    np.testing.assert_allclose(
        values, POINTS[:, 0] + 2 * POINTS[:, 1] + 3 * POINTS[:, 2]
    )


def test_evaluate_function_passes_copies_of_the_columns():
    received = []

    def func(a, b, c):
        received.extend([a, b, c])
        return a + b + c

    evaluate_function(func, POINTS)

    for arg in received:
        assert isinstance(arg, np.ndarray)
        assert arg.flags.c_contiguous
        assert not np.shares_memory(arg, POINTS)


def test_evaluate_function_does_not_change_points_when_func_mutates_args():
    points = POINTS.copy()

    def func(a, b, c):
        a[:] = -1.0
        b *= 10.0
        c.fill(np.nan)
        return np.zeros(len(a))

    evaluate_function(func, points)

    np.testing.assert_array_equal(points, POINTS)


@pytest.mark.parametrize(
    "wrap",
    [
        lambda v: v,
        lambda v: v.reshape(-1, 1),
        lambda v: v.reshape(1, -1),
        lambda v: v.tolist(),
        lambda v: v.astype(np.float32),
        lambda v: v.astype(int),
    ],
    ids=["(m,)", "(m, 1)", "(1, m)", "list", "float32", "int"],
)
def test_evaluate_function_accepts_shapes(wrap):
    expected = np.array([1.0, 2.0, 3.0, 4.0])

    values = evaluate_function(lambda a, b, c: wrap(expected), POINTS)

    assert isinstance(values, np.ndarray)
    assert not isinstance(values, np.ma.MaskedArray)
    assert values.shape == (M,)
    assert values.dtype == float
    np.testing.assert_array_equal(values, expected)


@pytest.mark.parametrize("shape", [(1,), (1, 1)])
def test_evaluate_function_accepts_shapes_for_one_point(shape):
    values = evaluate_function(lambda a, b, c: np.full(shape, 7.0), POINTS[:1])
    assert values.shape == (1,)
    np.testing.assert_array_equal(values, [7.0])


def test_evaluate_function_returns_a_new_array():
    returned = np.array([1.0, 2.0, 3.0, 4.0])

    values = evaluate_function(lambda a, b, c: returned, POINTS)

    assert not np.shares_memory(values, returned)
    values[0] = 100.0
    np.testing.assert_array_equal(returned, [1.0, 2.0, 3.0, 4.0])


def test_evaluate_function_keeps_nan():
    values = evaluate_function(
        lambda a, b, c: np.array([1.0, np.nan, np.inf, 4.0]), POINTS
    )
    np.testing.assert_array_equal(values, [1.0, np.nan, np.inf, 4.0])


@pytest.mark.parametrize("shape", [(M,), (M, 1), (1, M)])
def test_evaluate_function_turns_masked_values_into_nan(shape):
    data = np.array([1.0, 2.0, 3.0, 4.0]).reshape(shape)
    mask = np.array([False, True, False, True]).reshape(shape)
    returned = np.ma.MaskedArray(data, mask=mask)

    values = evaluate_function(lambda a, b, c: returned, POINTS)

    assert not isinstance(values, np.ma.MaskedArray)
    np.testing.assert_array_equal(values, [1.0, np.nan, 3.0, np.nan])
    # The masked array returned by ``func`` is not changed.
    np.testing.assert_array_equal(returned.data, data)
    np.testing.assert_array_equal(returned.mask, mask)


@pytest.mark.parametrize(
    "returned",
    [
        1.0,
        np.float64(1.0),
        np.zeros(M + 1),
        np.zeros(M - 1),
        np.zeros((M, 2)),
        np.zeros((2, M)),
        np.zeros((M, 1, 1)),
        np.zeros((0,)),
    ],
    ids=[
        "scalar",
        "numpy-scalar",
        "(m + 1,)",
        "(m - 1,)",
        "(m, 2)",
        "(2, m)",
        "(m, 1, 1)",
        "empty",
    ],
)
def test_evaluate_function_rejects_shapes(returned):
    with pytest.raises(ValueError, match=VECTORIZE_MESSAGE) as excinfo:
        evaluate_function(lambda a, b, c: returned, POINTS)
    message = str(excinfo.value)
    assert f"must return {M} numeric values" in message
    assert str(np.shape(returned)) in message


@pytest.mark.parametrize(
    "returned",
    [
        "abc",
        ["a", "b", "c", "d"],
        np.array(["a", "b", "c", "d"]),
        {"a": 1},
        [[1.0, 2.0], [3.0]],
    ],
    ids=["str", "list-of-str", "str-array", "dict", "ragged"],
)
def test_evaluate_function_rejects_values_that_are_not_numbers(returned):
    with pytest.raises(ValueError, match=VECTORIZE_MESSAGE) as excinfo:
        evaluate_function(lambda a, b, c: returned, POINTS)
    assert f"must return {M} numeric values" in str(excinfo.value)
    # The error of the conversion is chained.
    assert isinstance(excinfo.value.__cause__, (TypeError, ValueError))


@pytest.mark.parametrize("func", [None, 1.0, "sum", np.zeros(3)])
def test_evaluate_function_rejects_objects_that_are_not_callable(func):
    with pytest.raises(TypeError, match="`func` must be callable"):
        evaluate_function(func, POINTS)


def test_evaluate_function_does_not_call_func_twice_on_error():
    calls = []

    def func(a, b, c):
        calls.append(1)
        return np.zeros(len(a) + 1)

    with pytest.raises(ValueError, match=VECTORIZE_MESSAGE):
        evaluate_function(func, POINTS)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "error", [ZeroDivisionError("boom"), ValueError("boom"), TypeError("x")]
)
def test_evaluate_function_propagates_exceptions_of_func(error):
    def func(a, b, c):
        raise error

    with pytest.raises(type(error)) as excinfo:
        evaluate_function(func, POINTS)
    assert excinfo.value is error
    assert excinfo.value.__cause__ is None


def test_evaluate_function_works_with_numpy_vectorize():
    def scalar_only(a, b, c):
        if not isinstance(a, float):
            raise TypeError("scalars only")
        return a - c

    values = evaluate_function(np.vectorize(scalar_only), POINTS)

    np.testing.assert_allclose(values, POINTS[:, 0] - POINTS[:, 2])
