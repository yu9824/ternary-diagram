import time

import numpy as np
import pytest
from matplotlib.collections import PolyCollection, TriMesh

from ternary_diagram.utils import get_triangular_lattice, three2two


def _top_component(a, b, c):
    return a


def test_heatmapf_default_returns_poly_collection(td):
    n_collections = len(td.ax.collections)

    mesh = td.heatmapf(_top_component)

    # 既定は flat、scale=50 (default: flat with scale=50 -> 50**2 triangles)
    assert isinstance(mesh, PolyCollection)
    assert len(mesh.get_paths()) == 2500
    assert len(td.ax.collections) == n_collections + 1
    assert td.ax.collections[-1] is mesh


def test_heatmapf_gouraud_returns_tri_mesh(td):
    n_collections = len(td.ax.collections)

    mesh = td.heatmapf(_top_component, shading="gouraud")

    assert isinstance(mesh, TriMesh)
    # 既定の scale=50 の格子点 (the lattice points of the default scale=50)
    assert len(mesh.get_array()) == 51 * 52 // 2 == 1326
    assert len(mesh.get_paths()) == 2500
    assert len(td.ax.collections) == n_collections + 1
    assert td.ax.collections[-1] is mesh


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_calls_function_once(td, shading):
    calls = []

    def func(a, b, c):
        calls.append((a, b, c))
        return a

    td.heatmapf(func, scale=4, shading=shading)

    assert len(calls) == 1


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_records_evaluation_points(td, shading):
    scale = 4
    vertices, triangles = get_triangular_lattice(scale)
    # flat は小三角形の重心、gouraud は格子点 (flat: centroids of the small
    # triangles, gouraud: lattice points)
    points = (
        vertices[triangles].mean(axis=1) if shading == "flat" else vertices
    )

    td.heatmapf(_top_component, scale=scale, shading=shading)

    x, y = three2two(points)
    assert len(td.x_["heatmapf"]) == 1
    assert len(td.y_["heatmapf"]) == 1
    np.testing.assert_allclose(td.x_["heatmapf"][0], x)
    np.testing.assert_allclose(td.y_["heatmapf"][0], y)


# ---------------------------------------------------------------------------
# heatmapf 固有の挙動 (behavior specific to heatmapf)
# ---------------------------------------------------------------------------

SCALE = 4
TOP_VERTEX_HEIGHT = np.sqrt(3) / 2


def _record_calls(calls, func=_top_component):
    """Wrap `func` so that each call appends its arguments to `calls`."""

    def recording(*args, **kwargs):
        calls.append((args, kwargs))
        return func(*args, **kwargs)

    return recording


def _painted_triangles(mesh, scale):
    """Lattice indices of the 3 vertices of each painted small triangle.

    Both a PolyCollection (flat) and a TriMesh (gouraud) return one path per
    painted triangle from ``get_paths()``; masked triangles have no path.
    """
    vertices, _ = get_triangular_lattice(scale)
    x, y = three2two(vertices)
    painted = []
    for path in mesh.get_paths():
        corners = path.vertices[:3]
        distances = np.hypot(
            corners[:, [0]] - x[np.newaxis, :],
            corners[:, [1]] - y[np.newaxis, :],
        )
        np.testing.assert_allclose(distances.min(axis=1), 0.0, atol=1e-12)
        painted.append(tuple(distances.argmin(axis=1)))
    return painted


def _as_set(triangles):
    return {frozenset(int(i) for i in t) for t in triangles}


def _assert_nothing_added(td, n_collections, n_axes):
    assert len(td.ax.collections) == n_collections
    assert len(td.ax.figure.axes) == n_axes
    assert "heatmapf" not in td.x_


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_passes_three_1d_arrays_summing_to_one(td, shading):
    calls = []

    td.heatmapf(_record_calls(calls), scale=SCALE, shading=shading)

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert kwargs == {}
    assert len(args) == 3
    for arg in args:
        assert isinstance(arg, np.ndarray)
        assert arg.ndim == 1
        assert arg.shape == args[0].shape
        assert np.issubdtype(arg.dtype, np.floating)
    np.testing.assert_allclose(args[0] + args[1] + args[2], 1.0)


def test_heatmapf_flat_evaluates_only_inside_the_triangle(td):
    calls = []

    td.heatmapf(_record_calls(calls), scale=SCALE, shading="flat")

    ((args, _),) = calls
    points = np.column_stack(args)
    # 小三角形ごとに 1 点、辺上と頂点では評価しない (one point per small
    # triangle, never on the edges or at the vertices)
    assert points.shape == (SCALE**2, 3)
    assert (points > 0).all()
    assert len(np.unique(points.round(12), axis=0)) == SCALE**2


def test_heatmapf_gouraud_evaluates_on_lattice_points(td):
    calls = []

    td.heatmapf(_record_calls(calls), scale=SCALE, shading="gouraud")

    ((args, _),) = calls
    points = np.column_stack(args)
    assert points.shape == ((SCALE + 1) * (SCALE + 2) // 2, 3)
    assert len(np.unique(points.round(12), axis=0)) == len(points)
    # 三角形の頂点を含む (including the vertices of the triangle)
    for vertex in np.eye(3):
        assert np.isclose(points, vertex).all(axis=1).any()
    # 格子点だけ (lattice points only: each component is a multiple of 1/n)
    np.testing.assert_allclose(
        points * SCALE, np.round(points * SCALE), atol=1e-12
    )


def test_heatmapf_flat_first_argument_is_top_component(td):
    mesh = td.heatmapf(_top_component, scale=SCALE, shading="flat")

    # 塗った小三角形の重心の高さ (height of the centroid of each painted
    # triangle): the top component equals y / (sqrt(3) / 2)
    centroid_y = np.array(
        [path.vertices[:3, 1].mean() for path in mesh.get_paths()]
    )
    values = np.asarray(mesh.get_array())
    np.testing.assert_allclose(values, centroid_y / TOP_VERTEX_HEIGHT)
    # 上ほど値が大きい (larger values higher up)
    assert values[centroid_y.argmax()] > values[centroid_y.argmin()]


def test_heatmapf_gouraud_first_argument_is_top_component(td):
    mesh = td.heatmapf(_top_component, scale=SCALE, shading="gouraud")

    # gouraud の値は評価点 (= 格子点) ごと (one value per lattice point)
    y = td.y_["heatmapf"][0]
    values = np.asarray(mesh.get_array())
    np.testing.assert_allclose(values, y / TOP_VERTEX_HEIGHT)
    np.testing.assert_allclose(values[y.argmax()], 1.0)
    np.testing.assert_allclose(values[y.argmin()], 0.0)


def _asymmetric(a, b, c):
    return a + 2 * b**2 + 3 * c**3


def test_heatmapf_flat_colors_are_function_values_at_centroids(td):
    vertices, _ = get_triangular_lattice(SCALE)

    mesh = td.heatmapf(_asymmetric, scale=SCALE, shading="flat")

    painted = np.asarray(_painted_triangles(mesh, SCALE))
    assert len(painted) == SCALE**2
    centroids = vertices[painted].mean(axis=1)
    expected = _asymmetric(*centroids.T)
    np.testing.assert_allclose(np.asarray(mesh.get_array()), expected)


@pytest.mark.parametrize("shape", ["column", "row"])
@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_accepts_2d_column_or_row(td, shading, shape):
    def func(a, b, c):
        values = _asymmetric(a, b, c)
        return values[:, np.newaxis] if shape == "column" else values[None]

    mesh = td.heatmapf(func, scale=SCALE, shading=shading)

    reference = td.heatmapf(
        _asymmetric, scale=SCALE, shading=shading, colorbar=False
    )
    assert len(mesh.get_paths()) == len(reference.get_paths())
    np.testing.assert_allclose(
        np.asarray(mesh.get_array()), np.asarray(reference.get_array())
    )


@pytest.mark.parametrize(
    "func",
    [
        # スカラーを返す (returns a scalar)
        lambda a, b, c: 1.0,
        # 要素数が違う (wrong number of values)
        lambda a, b, c: a[:-1],
        # 2 列 (2 columns)
        lambda a, b, c: np.column_stack([a, b]),
        # 数値でない (not numeric)
        lambda a, b, c: np.array(["x"] * len(a)),
    ],
    ids=["scalar", "wrong-length", "two-columns", "non-numeric"],
)
@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_invalid_return_value_raises_and_adds_nothing(
    td, func, shading
):
    n_collections = len(td.ax.collections)
    n_axes = len(td.ax.figure.axes)
    n_points = (
        SCALE**2 if shading == "flat" else (SCALE + 1) * (SCALE + 2) // 2
    )

    with pytest.raises(ValueError, match="numpy.vectorize") as excinfo:
        td.heatmapf(func, scale=SCALE, shading=shading)

    assert f"{n_points} numeric values" in str(excinfo.value)
    _assert_nothing_added(td, n_collections, n_axes)


@pytest.mark.parametrize("func", [None, 1.0, "a", np.ones(3)])
def test_heatmapf_non_callable_raises_type_error(td, func):
    n_collections = len(td.ax.collections)
    n_axes = len(td.ax.figure.axes)

    with pytest.raises(TypeError, match="must be callable"):
        td.heatmapf(func, scale=SCALE)

    _assert_nothing_added(td, n_collections, n_axes)


class _UserError(Exception):
    pass


@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_propagates_exception_from_function(td, shading):
    n_collections = len(td.ax.collections)
    n_axes = len(td.ax.figure.axes)
    error = _UserError("model failed")

    def func(a, b, c):
        raise error

    with pytest.raises(_UserError) as excinfo:
        td.heatmapf(func, scale=SCALE, shading=shading)

    # 置き換えずにそのまま (the very same exception, not replaced)
    assert excinfo.value is error
    _assert_nothing_added(td, n_collections, n_axes)


@pytest.mark.parametrize(
    "scale, error, match",
    [
        (0, ValueError, "1 or greater"),
        (-1, ValueError, "1 or greater"),
        (2.5, TypeError, "must be an integer"),
        (True, TypeError, "must be an integer"),
    ],
)
def test_heatmapf_invalid_scale_raises_and_adds_nothing(
    td, scale, error, match
):
    n_collections = len(td.ax.collections)
    n_axes = len(td.ax.figure.axes)
    calls = []

    with pytest.raises(error, match=match):
        td.heatmapf(_record_calls(calls), scale=scale)

    assert calls == []
    _assert_nothing_added(td, n_collections, n_axes)


def _nan_near_top(a, b, c):
    # 上の頂点の近くだけ定義されない (undefined only near the top vertex)
    return np.where(a > 0.6, np.nan, a + b)


@pytest.mark.parametrize("bad", [np.nan, np.inf])
@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_skips_triangles_with_non_finite_value(td, shading, bad):
    vertices, triangles = get_triangular_lattice(SCALE)

    def func(a, b, c):
        return np.where(a > 0.6, bad, a + b)

    mesh = td.heatmapf(func, scale=SCALE, shading=shading)

    if shading == "flat":
        # 重心で定義されない小三角形 (triangles whose centroid is undefined)
        undefined = vertices[triangles].mean(axis=1)[:, 0] > 0.6
    else:
        # 定義されない格子点を頂点に持つ小三角形 (triangles with an
        # undefined lattice point as a vertex)
        undefined = (vertices[triangles][:, :, 0] > 0.6).any(axis=1)
    expected = _as_set(triangles[~undefined])
    assert 0 < len(expected) < len(triangles)
    assert _as_set(_painted_triangles(mesh, SCALE)) == expected
    assert np.isfinite(np.ma.compressed(mesh.get_array())).all()


def test_heatmapf_nan_leaves_more_unpainted_with_gouraud(td):
    # gouraud は頂点 1 つでも NaN なら塗らない (gouraud skips a triangle if
    # any of its vertices is NaN, so fewer triangles are painted than flat)
    flat = td.heatmapf(_nan_near_top, scale=SCALE, shading="flat")
    gouraud = td.heatmapf(
        _nan_near_top, scale=SCALE, shading="gouraud", colorbar=False
    )

    assert _as_set(_painted_triangles(gouraud, SCALE)) < _as_set(
        _painted_triangles(flat, SCALE)
    )


@pytest.mark.parametrize("bad", [np.nan, np.inf])
@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_always_non_finite_raises_and_adds_nothing(td, shading, bad):
    n_collections = len(td.ax.collections)
    n_axes = len(td.ax.figure.axes)

    with pytest.raises(ValueError, match="No triangle can be painted"):
        td.heatmapf(
            lambda a, b, c: np.full_like(a, bad), scale=SCALE, shading=shading
        )

    _assert_nothing_added(td, n_collections, n_axes)


@pytest.mark.parametrize(
    "kwargs",
    [{"triangles": [[0, 1, 2]]}, {"mask": np.zeros(SCALE**2, dtype=bool)}],
    ids=["triangles", "mask"],
)
@pytest.mark.parametrize("shading", ["flat", "gouraud"])
def test_heatmapf_rejects_triangles_and_mask(td, kwargs, shading):
    n_collections = len(td.ax.collections)
    n_axes = len(td.ax.figure.axes)
    (name,) = kwargs
    calls = []

    with pytest.raises(ValueError, match=f"`{name}` cannot be specified") as e:
        td.heatmapf(
            _record_calls(calls), scale=SCALE, shading=shading, **kwargs
        )

    assert "Return NaN" in str(e.value)
    assert calls == []
    _assert_nothing_added(td, n_collections, n_axes)


def test_heatmapf_scale_100_flat_draws_within_one_second(td):
    def light(a, b, c):
        return a * b + np.sin(c)

    start = time.perf_counter()
    mesh = td.heatmapf(light, scale=100)
    elapsed = time.perf_counter() - start

    assert len(mesh.get_paths()) == 100**2
    # 図の保存を除く (excluding saving the figure); about 0.05 s with
    # matplotlib 3.10, so 1 s leaves room for slow CI machines
    assert elapsed < 1.0, f"heatmapf(scale=100) took {elapsed:.3f} s"
